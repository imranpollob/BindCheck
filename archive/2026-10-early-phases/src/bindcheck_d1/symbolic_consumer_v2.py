"""Minimal symbolic Payy consumer transition for the D1 v2 fragment.

This module builds an inspectable expression graph and evaluates that graph on
concrete assignments.  It is not an SMT encoder, a proof verifier, or a claim
of equivalence with unrestricted EVM execution.  The implementation keeps the
existing concrete token/admission and occurrence-policy foundations as its
concrete oracle boundary.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

from .consumer_scope_v2 import Admission, assess as assess_scope
from .frontends.consumer_execution_v1 import Result as ConcreteResult
from .frontends.consumer_execution_v1 import Token
from .model_v2 import (
    Artifact,
    EvidenceGrade,
    FIELD_MODULUS,
    Key,
    Occurrence,
    Policy,
    Provenance,
    Unsupported,
)
from .policy_v2 import TraceAssessment, assess_trace


UINT256 = 2**256
ADDRESS_MODULUS = 2**160
MAX_V2_AMOUNT = 2**64 - 1
PINNED_CONSUMER_REVISION = "dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36"
PINNED_CONSUMER_PATH = "eth/contracts/rollup3/RollupV1.sol"
PINNED_CONSUMER_SHA256 = "7062065cc95f447fea8bb28242d51c836c3cf9e39f1625180ecf9c240a5ffd8f"


class EvaluationError(ValueError):
    """A malformed concrete assignment, not a modeled Solidity revert."""


@dataclass(frozen=True)
class Expr:
    """Small, solver-neutral expression IR used by the symbolic transition."""

    op: str
    args: tuple[Any, ...]
    sort: str

    def evaluate(self, environment: dict[str, Any]) -> Any:
        return self._evaluate(environment, {})

    def _evaluate(self, environment: dict[str, Any], cache: dict[int, Any]) -> Any:
        identity = id(self)
        if identity in cache:
            return cache[identity]
        op = self.op
        if op == "const":
            result = self.args[0]
        elif op == "input":
            name = self.args[0]
            if name not in environment:
                raise EvaluationError(f"missing symbolic input: {name}")
            result = environment[name]
        elif op == "not":
            result = not _bool(_eval(self.args[0], environment, cache))
        elif op == "and":
            result = True
            for value in self.args:
                if not _bool(_eval(value, environment, cache)):
                    result = False
                    break
        elif op == "or":
            result = False
            for value in self.args:
                if _bool(_eval(value, environment, cache)):
                    result = True
                    break
        elif op == "ite":
            condition, yes, no = self.args
            result = _eval(yes if _bool(_eval(condition, environment, cache)) else no,
                           environment, cache)
        elif op == "eq":
            result = _eval(self.args[0], environment, cache) == _eval(self.args[1], environment, cache)
        elif op == "lt":
            result = _int(_eval(self.args[0], environment, cache)) < _int(_eval(self.args[1], environment, cache))
        elif op == "le":
            result = _int(_eval(self.args[0], environment, cache)) <= _int(_eval(self.args[1], environment, cache))
        elif op == "add":
            result = sum(_int(_eval(value, environment, cache)) for value in self.args)
        elif op == "sub":
            left = _int(_eval(self.args[0], environment, cache))
            right = _int(_eval(self.args[1], environment, cache))
            if left < right:
                raise EvaluationError("symbolic unsigned subtraction underflow")
            result = left - right
        elif op == "low160":
            result = _int(_eval(self.args[0], environment, cache)) % ADDRESS_MODULUS
        elif op == "length":
            result = len(_eval(self.args[0], environment, cache))
        elif op == "sequence_get":
            sequence = _eval(self.args[0], environment, cache)
            index = _int(_eval(self.args[1], environment, cache))
            if not 0 <= index < len(sequence):
                raise EvaluationError(f"symbolic calldata bounds: {index}/{len(sequence)}")
            result = sequence[index]
        elif op == "map_get":
            mapping = _eval(self.args[0], environment, cache)
            key = _eval(self.args[1], environment, cache)
            result = mapping.get(key, _eval(self.args[2], environment, cache))
        elif op == "map_store":
            mapping = dict(_eval(self.args[0], environment, cache))
            mapping[_eval(self.args[1], environment, cache)] = _eval(self.args[2], environment, cache)
            result = mapping
        else:
            raise EvaluationError(f"unsupported symbolic operation: {op}")
        cache[identity] = result
        return result

    def inputs(self) -> frozenset[str]:
        names: set[str] = set()
        seen: set[int] = set()

        def visit(value: Any) -> None:
            if not isinstance(value, Expr) or id(value) in seen:
                return
            seen.add(id(value))
            if value.op == "input":
                names.add(value.args[0])
            for child in value.args:
                visit(child)

        visit(self)
        return frozenset(names)

    def node_count(self) -> int:
        seen: set[int] = set()

        def visit(value: Any) -> None:
            if not isinstance(value, Expr) or id(value) in seen:
                return
            seen.add(id(value))
            for child in value.args:
                visit(child)

        visit(self)
        return len(seen)


def _eval(value: Any, environment: dict[str, Any], cache: dict[int, Any]) -> Any:
    return value._evaluate(environment, cache) if isinstance(value, Expr) else value


def _bool(value: Any) -> bool:
    if type(value) is not bool:
        raise EvaluationError(f"expected bool, got {type(value).__name__}")
    return value


def _int(value: Any) -> int:
    if type(value) is not int:
        raise EvaluationError(f"expected int, got {type(value).__name__}")
    return value


def const(value: Any, sort: str | None = None) -> Expr:
    if sort is None:
        sort = "bool" if type(value) is bool else "int"
    return Expr("const", (value,), sort)


def inp(name: str, sort: str) -> Expr:
    return Expr("input", (name,), sort)


def neg(value: Expr) -> Expr:
    if value.op == "const":
        return const(not value.args[0], "bool")
    return Expr("not", (value,), "bool")


def conjunction(*values: Expr) -> Expr:
    flat: list[Expr] = []
    for value in values:
        if value.op == "const" and value.args[0] is False:
            return const(False, "bool")
        if value.op == "const" and value.args[0] is True:
            continue
        flat.extend(value.args if value.op == "and" else (value,))
    return const(True, "bool") if not flat else Expr("and", tuple(flat), "bool")


def disjunction(*values: Expr) -> Expr:
    flat: list[Expr] = []
    for value in values:
        if value.op == "const" and value.args[0] is True:
            return const(True, "bool")
        if value.op == "const" and value.args[0] is False:
            continue
        flat.extend(value.args if value.op == "or" else (value,))
    return const(False, "bool") if not flat else Expr("or", tuple(flat), "bool")


def equal(left: Expr, right: Expr) -> Expr:
    return Expr("eq", (left, right), "bool")


def less(left: Expr, right: Expr) -> Expr:
    return Expr("lt", (left, right), "bool")


def less_equal(left: Expr, right: Expr) -> Expr:
    return Expr("le", (left, right), "bool")


def add(*values: Expr) -> Expr:
    return Expr("add", tuple(values), "int")


def subtract(left: Expr, right: Expr) -> Expr:
    return Expr("sub", (left, right), "int")


def choose(condition: Expr, yes: Expr, no: Expr) -> Expr:
    return Expr("ite", (condition, yes, no), yes.sort)


def length(value: Expr) -> Expr:
    return Expr("length", (value,), "int")


def sequence_get(sequence: Expr, index: Expr) -> Expr:
    return Expr("sequence_get", (sequence, index), "int")


def map_get(mapping: Expr, key: Expr, default: Expr) -> Expr:
    return Expr("map_get", (mapping, key, default), default.sort)


def map_store(mapping: Expr, key: Expr, value: Expr) -> Expr:
    return Expr("map_store", (mapping, key, value), "map")


def low160(value: Expr) -> Expr:
    return Expr("low160", (value,), "int")


@dataclass(frozen=True)
class MintEntry:
    note_kind: int
    amount: int
    spent: bool = False


@dataclass(frozen=True)
class GuardBoundary:
    """Concrete choices at guard boundaries plus their evidentiary basis."""

    caller_authorized: bool | None
    signatures_accepted: bool | None
    caller_basis: str = ""
    signatures_basis: str = ""
    attacker_capabilities: tuple[str, ...] = ()
    validator_set_index_after: int | None = None

    def unresolved(self) -> tuple[str, ...]:
        reasons = []
        if self.caller_authorized is None:
            reasons.append("PROVER_GUARD_UNRESOLVED")
        elif self.caller_authorized and not self.caller_basis:
            reasons.append("PROVER_GUARD_BASIS_MISSING")
        if self.signatures_accepted is None:
            reasons.append("SIGNATURE_GUARD_UNRESOLVED")
        elif self.signatures_accepted and not self.signatures_basis:
            reasons.append("SIGNATURE_GUARD_BASIS_MISSING")
        if self.signatures_accepted is True and self.validator_set_index_after is None:
            reasons.append("VALIDATOR_STATE_POST_UNRESOLVED")
        if (self.caller_authorized is True or self.signatures_accepted is True) and not self.attacker_capabilities:
            reasons.append("ATTACKER_CAPABILITY_MISSING")
        return tuple(reasons)


@dataclass(frozen=True)
class VerifierBoundary:
    """Exact verifier call identity and explicit proof-soundness boundary."""

    requested_key_hash: int
    registered_verifier: int
    registered_messages_length: int
    enabled: bool
    accepted: bool | None
    relation_key_hash: int
    relation_id: str
    relation_scope: str
    proof_bytes: bytes = b""
    proof_soundness_assumed: bool = False

    def __post_init__(self) -> None:
        for value in (self.requested_key_hash, self.relation_key_hash):
            if type(value) is not int or not 0 <= value < UINT256:
                raise Unsupported("VERIFIER_KEY_WORD", repr(value))
        if type(self.registered_verifier) is not int or not 0 < self.registered_verifier < ADDRESS_MODULUS:
            raise Unsupported("VERIFIER_ADDRESS", repr(self.registered_verifier))
        if type(self.registered_messages_length) is not int or not 0 <= self.registered_messages_length < 2**32:
            raise Unsupported("VERIFIER_MESSAGE_LENGTH", repr(self.registered_messages_length))
        if self.relation_scope not in ("FULL_PRODUCER_RELATION", "SELECTED_CONE_ABSTRACTION"):
            raise Unsupported("VERIFIER_RELATION_SCOPE", self.relation_scope)
        if not self.relation_id:
            raise Unsupported("VERIFIER_RELATION_ID_MISSING", "")


@dataclass
class ConsumerAssignment:
    public_inputs: tuple[int, ...]
    height: int
    current_root: int
    current_height: int
    sender: int
    contract: int
    guards: GuardBoundary
    verifier: VerifierBoundary
    current_validator_set_index: int
    token: Token
    mints: dict[int, MintEntry] = field(default_factory=dict)
    token_by_note_kind: dict[int, int] = field(default_factory=dict)
    substituted_burns: dict[int, int] = field(default_factory=dict)


@dataclass(frozen=True)
class SymbolicEffect:
    step: int
    kind: str
    condition: Expr
    note_kind: Expr
    amount: Expr
    note_hash: Expr
    recipient: Expr | None
    cursor: Expr
    source_location: str
    success: Expr | None = None


@dataclass(frozen=True)
class FailureCase:
    reason: str
    condition: Expr


@dataclass(frozen=True)
class VerifierClaim:
    call_reached: bool
    accepted: bool
    verification_key_hash: int
    relation_key_hash: int
    verifier_address: int
    public_inputs: tuple[int, ...]
    public_inputs_sha256: str
    proof_sha256: str
    relation_id: str
    relation_scope: str
    proof_soundness_assumed: bool
    sound_binding_established: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class SymbolicConsumerResult:
    outcome: str
    reason: str
    state_root: int
    block_height: int
    validator_set_index: int
    mints: dict[int, MintEntry]
    token: Token
    effects: tuple[Occurrence, ...]
    permissions: tuple[Occurrence, ...]
    obligations: tuple[Occurrence, ...]
    trace_assessment: TraceAssessment | None
    admission: Admission
    burn_attempts: tuple[dict[str, Any], ...]
    verifier_claim: VerifierClaim
    attacker_capabilities: tuple[str, ...]
    unsupported_reasons: tuple[str, ...]
    security_verdict: str = "UNKNOWN"
    evidence: str = "SYMBOLIC_EXPRESSIONS_EVALUATED_ON_CONCRETE_ASSIGNMENT"


@dataclass(frozen=True)
class SymbolicTransition:
    n: int
    domain: str
    commit: Expr
    scan_success: Expr
    final_cursor: Expr
    final_mint_note_kind: Expr
    final_mint_amount: Expr
    final_mint_spent: Expr
    final_balances: Expr
    effects: tuple[SymbolicEffect, ...]
    burn_attempts: tuple[SymbolicEffect, ...]
    failures: tuple[FailureCase, ...]
    unsupported: tuple[FailureCase, ...]

    def expression_stats(self) -> dict[str, Any]:
        roots = (
            self.commit,
            self.scan_success,
            self.final_cursor,
            self.final_mint_spent,
            self.final_balances,
            *(effect.condition for effect in self.effects),
        )
        inputs = set()
        nodes = 0
        for root in roots:
            inputs.update(root.inputs())
            nodes += root.node_count()
        return {
            "length": self.n,
            "root_expression_node_sum": nodes,
            "input_symbols": sorted(inputs),
            "effect_templates": len(self.effects),
            "burn_attempt_templates": len(self.burn_attempts),
            "failure_conditions": len(self.failures),
            "unsupported_conditions": len(self.unsupported),
            "note": "node sum counts shared subexpressions once per root, not globally",
        }

    def evaluate(self, assignment: ConsumerAssignment, policy: Policy) -> SymbolicConsumerResult:
        return evaluate_transition(self, assignment, policy)


def _word(sequence: Expr, index: Expr, guard: Expr) -> Expr:
    # Lazy ite keeps inactive/out-of-bounds record fields from being read.
    return choose(guard, sequence_get(sequence, index), const(0))


def build_transition(n: int, *, domain: str = "payy-rollup-v2") -> SymbolicTransition:
    """Build a bounded symbolic transition for exactly ``n`` message words.

    The builder is configurable.  V2 admission remains restricted to N=8 or
    N=1000 by ``consumer_scope_v2``; constructing another N does not broaden
    that research scope.
    """

    if type(n) is not int or n <= 0 or n >= 2**32:
        raise Unsupported("SYMBOLIC_MESSAGE_LENGTH", repr(n))
    words = inp("public_inputs", "sequence")
    actual_length = length(words)
    end = const(n + 3)
    cursor = const(3)
    configured = inp("configured_length", "int")
    caller = inp("caller_authorized", "bool")
    key_enabled = inp("key_enabled", "bool")
    signatures = inp("signatures_accepted", "bool")
    verifier_accepts = inp("verifier_accepts", "bool")
    current_root = inp("current_root", "int")
    current_height = inp("current_height", "int")
    new_height = inp("new_height", "int")
    initial_root = _word(words, const(0), less(const(0), actual_length))

    mint_note_kind = inp("mint_note_kind", "map")
    mint_amount = inp("mint_amount", "map")
    mint_spent = inp("mint_spent", "map")
    token_by_note_kind = inp("token_by_note_kind", "map")
    balances = inp("token_balances", "map")
    token_address = inp("token_address", "int")
    contract = inp("contract", "int")

    length_ok = equal(actual_length, add(configured, const(3)))
    configured_ok = equal(configured, const(n))
    root_ok = equal(initial_root, current_root)
    live = conjunction(caller, key_enabled, configured_ok, length_ok, root_ok, signatures)
    failures: list[FailureCase] = [
        FailureCase("PROVER_GUARD_REVERT", neg(caller)),
        FailureCase("VERIFIER_DISABLED", conjunction(caller, neg(key_enabled))),
        FailureCase("PUBLIC_INPUT_LENGTH", conjunction(caller, key_enabled, configured_ok, neg(length_ok))),
        FailureCase("ROOT_MISMATCH", conjunction(caller, key_enabled, configured_ok, length_ok, neg(root_ok))),
        FailureCase("SIGNATURE_GUARD_REVERT", conjunction(caller, key_enabled, configured_ok, length_ok, root_ok, neg(signatures))),
    ]
    unsupported: list[FailureCase] = []
    effects: list[SymbolicEffect] = []
    attempts: list[SymbolicEffect] = []

    for step in range(n):
        before_live = live
        before_cursor = cursor
        active = conjunction(before_live, less(before_cursor, end))
        kind = _word(words, before_cursor, active)
        is_zero = equal(kind, const(0))
        is_mint = equal(kind, const(2))
        is_burn = equal(kind, const(3))
        recognized = disjunction(is_zero, is_mint, is_burn)

        mint_path = conjunction(active, is_mint)
        mint_fit = less(add(before_cursor, const(3)), actual_length)
        mint_kind = _word(words, add(before_cursor, const(1)), conjunction(mint_path, mint_fit))
        mint_value = _word(words, add(before_cursor, const(2)), conjunction(mint_path, mint_fit))
        mint_hash = _word(words, add(before_cursor, const(3)), conjunction(mint_path, mint_fit))
        mint_checks = conjunction(
            mint_fit,
            equal(map_get(mint_amount, mint_hash, const(0)), mint_value),
            equal(map_get(mint_note_kind, mint_hash, const(0)), mint_kind),
            neg(map_get(mint_spent, mint_hash, const(False, "bool"))),
        )
        mint_exec = conjunction(mint_path, mint_checks)

        burn_path = conjunction(active, is_burn)
        burn_fit = less(add(before_cursor, const(4)), actual_length)
        burn_kind = _word(words, add(before_cursor, const(1)), conjunction(burn_path, burn_fit))
        burn_value = _word(words, add(before_cursor, const(2)), conjunction(burn_path, burn_fit))
        burn_hash = _word(words, add(before_cursor, const(3)), conjunction(burn_path, burn_fit))
        burn_recipient_word = _word(words, add(before_cursor, const(4)), conjunction(burn_path, burn_fit))
        recipient = low160(burn_recipient_word)
        target = map_get(token_by_note_kind, burn_kind, const(0))
        target_supported = equal(target, token_address)
        sender_balance = map_get(balances, contract, const(0))
        transfer_success = conjunction(
            burn_path,
            burn_fit,
            target_supported,
            neg(equal(recipient, const(0))),
            less_equal(burn_value, sender_balance),
        )
        after_sender = map_store(balances, contract, subtract(sender_balance, burn_value))
        recipient_balance = map_get(after_sender, recipient, const(0))
        transferred = map_store(after_sender, recipient, add(recipient_balance, burn_value))

        failures.extend((
            FailureCase(f"INVALID_KIND_AT_STEP_{step}", conjunction(active, neg(recognized))),
            FailureCase(f"TRUNCATED_MINT_AT_STEP_{step}", conjunction(mint_path, neg(mint_fit))),
            FailureCase(f"MINT_REGISTRY_REJECT_AT_STEP_{step}", conjunction(mint_path, mint_fit, neg(mint_checks))),
            FailureCase(f"TRUNCATED_BURN_AT_STEP_{step}", conjunction(burn_path, neg(burn_fit))),
        ))
        unsupported.append(FailureCase(
            f"TOKEN_TARGET_UNSUPPORTED_AT_STEP_{step}",
            conjunction(burn_path, burn_fit, neg(target_supported)),
        ))

        mint_spent = choose(mint_exec, map_store(mint_spent, mint_hash, const(True, "bool")), mint_spent)
        balances = choose(transfer_success, transferred, balances)
        branch_ok = disjunction(is_zero, conjunction(is_mint, mint_checks), conjunction(is_burn, burn_fit))
        live = conjunction(before_live, disjunction(neg(active), branch_ok))
        cursor = choose(
            active,
            choose(is_zero, add(before_cursor, const(1)),
                   choose(is_mint, add(before_cursor, const(4)),
                          choose(is_burn, add(before_cursor, const(5)), before_cursor))),
            before_cursor,
        )
        effects.append(SymbolicEffect(
            step, "mint", mint_exec, mint_kind, mint_value, mint_hash, None,
            before_cursor, "RollupV1.sol:418-440", None,
        ))
        burn_effect = SymbolicEffect(
            step, "burn", transfer_success, burn_kind, burn_value, burn_hash,
            recipient, before_cursor, "RollupV1.sol:442-534", transfer_success,
        )
        effects.append(burn_effect)
        attempts.append(SymbolicEffect(
            step, "burn", conjunction(burn_path, burn_fit, target_supported),
            burn_kind, burn_value, burn_hash, recipient, before_cursor,
            "RollupV1.sol:442-534", transfer_success,
        ))

    scan_success = conjunction(live, neg(less(cursor, end)))
    post_verifier = conjunction(scan_success, verifier_accepts)
    height_ok = less(current_height, new_height)
    commit = conjunction(post_verifier, height_ok)
    failures.extend((
        FailureCase("PROOF_VERIFIER_REVERT", conjunction(scan_success, neg(verifier_accepts))),
        FailureCase("HEIGHT_GUARD_REVERT", conjunction(post_verifier, neg(height_ok))),
    ))

    committed_effects = tuple(SymbolicEffect(
        effect.step,
        effect.kind,
        conjunction(commit, effect.condition),
        effect.note_kind,
        effect.amount,
        effect.note_hash,
        effect.recipient,
        effect.cursor,
        effect.source_location,
        effect.success,
    ) for effect in effects)
    return SymbolicTransition(
        n=n,
        domain=domain,
        commit=commit,
        scan_success=scan_success,
        final_cursor=cursor,
        final_mint_note_kind=mint_note_kind,
        final_mint_amount=mint_amount,
        final_mint_spent=mint_spent,
        final_balances=balances,
        effects=committed_effects,
        burn_attempts=tuple(attempts),
        failures=tuple(failures),
        unsupported=tuple(unsupported),
    )


def _word_bytes(words: tuple[int, ...]) -> bytes:
    return b"".join(value.to_bytes(32, "big") for value in words)


def _verifier_claim(assignment: ConsumerAssignment, *, call_reached: bool = False) -> VerifierClaim:
    verifier = assignment.verifier
    reasons = []
    if verifier.requested_key_hash != verifier.relation_key_hash:
        reasons.append("VERIFICATION_KEY_RELATION_MISMATCH")
    if verifier.relation_scope != "FULL_PRODUCER_RELATION":
        reasons.append("SELECTED_CONE_IS_NOT_FULL_RELATION")
    if not verifier.proof_soundness_assumed:
        reasons.append("PROOF_SOUNDNESS_NOT_ADMITTED")
    accepted = call_reached and verifier.accepted is True
    established = accepted and not reasons
    return VerifierClaim(
        call_reached=call_reached,
        accepted=accepted,
        verification_key_hash=verifier.requested_key_hash,
        relation_key_hash=verifier.relation_key_hash,
        verifier_address=verifier.registered_verifier,
        public_inputs=assignment.public_inputs,
        public_inputs_sha256=sha256(_word_bytes(assignment.public_inputs)).hexdigest(),
        proof_sha256=sha256(verifier.proof_bytes).hexdigest(),
        relation_id=verifier.relation_id,
        relation_scope=verifier.relation_scope,
        proof_soundness_assumed=verifier.proof_soundness_assumed,
        sound_binding_established=established,
        reasons=tuple(reasons),
    )


def _source_provenance(location: str) -> Provenance:
    return Provenance(
        Artifact(f"git:{PINNED_CONSUMER_REVISION}:{PINNED_CONSUMER_PATH}", PINNED_CONSUMER_SHA256),
        location,
        EvidenceGrade.EXTRACTED,
    )


def _asset(note_kind: int) -> str:
    return f"payy-note-kind:{note_kind:064x}"


def _validate_assignment(plan: SymbolicTransition, assignment: ConsumerAssignment) -> tuple[str, ...]:
    reasons = list(assignment.guards.unresolved())
    if assignment.verifier.accepted is None:
        reasons.append("VERIFIER_ACCEPTANCE_UNRESOLVED")
    if assignment.verifier.registered_messages_length != plan.n:
        reasons.append("SYMBOLIC_PLAN_CONFIGURATION_MISMATCH")
    if assignment.substituted_burns:
        reasons.append("SUBSTITUTION_UNSUPPORTED")
    for name, value in (
        ("height", assignment.height),
        ("current_root", assignment.current_root),
        ("current_height", assignment.current_height),
    ):
        if type(value) is not int or not 0 <= value < UINT256:
            reasons.append(f"INVALID_{name.upper()}")
    if type(assignment.sender) is not int or not 0 < assignment.sender < ADDRESS_MODULUS:
        reasons.append("INVALID_SENDER")
    if type(assignment.contract) is not int or not 0 < assignment.contract < ADDRESS_MODULUS:
        reasons.append("INVALID_CONTRACT")
    if type(assignment.current_validator_set_index) is not int or not 0 <= assignment.current_validator_set_index < UINT256:
        reasons.append("INVALID_VALIDATOR_SET_INDEX")
    if (assignment.guards.validator_set_index_after is not None and
            (type(assignment.guards.validator_set_index_after) is not int or
             not 0 <= assignment.guards.validator_set_index_after < UINT256)):
        reasons.append("INVALID_VALIDATOR_SET_INDEX_POST")
    if not isinstance(assignment.public_inputs, tuple) or any(
            type(value) is not int or not 0 <= value < UINT256 for value in assignment.public_inputs):
        reasons.append("INVALID_PUBLIC_INPUT_WORD")
    try:
        assignment.token.validate()
    except Unsupported as error:
        reasons.append(error.reason)
    for key, entry in assignment.mints.items():
        if type(key) is not int or not 0 <= key < UINT256 or not isinstance(entry, MintEntry):
            reasons.append("INVALID_MINT_REGISTRY")
            break
        if any(type(value) is not int or not 0 <= value < UINT256 for value in (entry.note_kind, entry.amount)):
            reasons.append("INVALID_MINT_REGISTRY")
            break
    return tuple(dict.fromkeys(reasons))


def _environment(assignment: ConsumerAssignment) -> dict[str, Any]:
    return {
        "public_inputs": assignment.public_inputs,
        "configured_length": assignment.verifier.registered_messages_length,
        "caller_authorized": assignment.guards.caller_authorized,
        "key_enabled": assignment.verifier.enabled,
        "signatures_accepted": assignment.guards.signatures_accepted,
        "verifier_accepts": assignment.verifier.accepted,
        "current_root": assignment.current_root,
        "current_height": assignment.current_height,
        "new_height": assignment.height,
        "mint_note_kind": {key: value.note_kind for key, value in assignment.mints.items()},
        "mint_amount": {key: value.amount for key, value in assignment.mints.items()},
        "mint_spent": {key: value.spent for key, value in assignment.mints.items()},
        "token_by_note_kind": assignment.token_by_note_kind,
        "token_balances": assignment.token.balances,
        "token_address": assignment.token.address,
        "contract": assignment.contract,
    }


def _scope(plan: SymbolicTransition, assignment: ConsumerAssignment, result: ConcreteResult) -> Admission:
    roots = {name: name for name in ("rootHash", "mints", "tokens", "substitutedBurns")}
    state = {
        "rootHash": assignment.current_root,
        "mints": {key: {"note_kind": value.note_kind, "amount": value.amount, "spent": value.spent}
                  for key, value in assignment.mints.items()},
        "tokens": dict(assignment.token_by_note_kind),
        "substitutedBurns": dict(assignment.substituted_burns),
    }
    return assess_scope(
        n=plan.n,
        words=list(assignment.public_inputs),
        roots=roots,
        state=state,
        token=assignment.token,
        contract=assignment.contract,
        execution=result,
    )


def evaluate_transition(plan: SymbolicTransition, assignment: ConsumerAssignment,
                        policy: Policy) -> SymbolicConsumerResult:
    """Evaluate the symbolic graph without invoking a solver or child process."""

    verifier_claim = _verifier_claim(assignment)
    initial_token = deepcopy(assignment.token)
    initial_mints = deepcopy(assignment.mints)
    unresolved = list(_validate_assignment(plan, assignment))
    if unresolved:
        concrete = ConcreteResult("UNKNOWN", {}, initial_token, [], [], [], [], unresolved[0])
        admission = _scope(plan, assignment, concrete)
        return SymbolicConsumerResult(
            "UNKNOWN", unresolved[0], assignment.current_root, assignment.current_height,
            assignment.current_validator_set_index,
            initial_mints, initial_token, (), policy.permissions, policy.obligations,
            None, admission, (), verifier_claim, assignment.guards.attacker_capabilities,
            tuple(unresolved),
        )

    environment = _environment(assignment)
    try:
        cache: dict[int, Any] = {}
        evaluate = lambda expression: expression._evaluate(environment, cache)
        active_unsupported = tuple(case.reason for case in plan.unsupported
                                   if _bool(evaluate(case.condition)))
        if active_unsupported:
            concrete = ConcreteResult("UNKNOWN", {}, initial_token, [], [], [], [], active_unsupported[0])
            admission = _scope(plan, assignment, concrete)
            return SymbolicConsumerResult(
                "UNKNOWN", active_unsupported[0], assignment.current_root, assignment.current_height,
                assignment.current_validator_set_index,
                initial_mints, initial_token, (), policy.permissions, policy.obligations,
                None, admission, (), verifier_claim, assignment.guards.attacker_capabilities,
                active_unsupported,
            )

        verifier_claim = _verifier_claim(
            assignment, call_reached=_bool(evaluate(plan.scan_success)))
        committed = _bool(evaluate(plan.commit))
        attempts = []
        for attempt in plan.burn_attempts:
            if not _bool(evaluate(attempt.condition)):
                continue
            amount = _int(evaluate(attempt.amount))
            recipient = _int(evaluate(attempt.recipient))
            # This expression uses the sequential balance state at this step,
            # independently of whether a later outer guard rolls it back.
            success = _bool(evaluate(attempt.success))
            attempts.append({"kind": "token", "arguments": [recipient, amount],
                             "success": success, "committed": committed and success})

        if not committed:
            reason = next((case.reason for case in plan.failures
                           if _bool(evaluate(case.condition))), "TRANSITION_REVERTED")
            concrete = ConcreteResult("REVERT", {}, initial_token, [], [], [], attempts, reason)
            admission = _scope(plan, assignment, concrete)
            assessment = assess_trace(policy, (), committed=False)
            return SymbolicConsumerResult(
                "REVERT", reason, assignment.current_root, assignment.current_height,
                assignment.current_validator_set_index,
                initial_mints, initial_token, (), policy.permissions, policy.obligations,
                assessment, admission, tuple(attempts), verifier_claim,
                assignment.guards.attacker_capabilities, (),
            )

        final_spent = evaluate(plan.final_mint_spent)
        final_note_kind = evaluate(plan.final_mint_note_kind)
        final_amount = evaluate(plan.final_mint_amount)
        mint_keys = set(initial_mints) | set(final_spent) | set(final_note_kind) | set(final_amount)
        final_mints = {
            key: MintEntry(final_note_kind.get(key, 0), final_amount.get(key, 0), final_spent.get(key, False))
            for key in mint_keys
        }
        final_token = deepcopy(initial_token)
        final_token.balances = evaluate(plan.final_balances)
        final_token.validate()

        occurrences = []
        for effect in plan.effects:
            if not _bool(evaluate(effect.condition)):
                continue
            note_kind = _int(evaluate(effect.note_kind))
            amount = _int(evaluate(effect.amount))
            note_hash = _int(evaluate(effect.note_hash))
            recipient = None if effect.recipient is None else _int(evaluate(effect.recipient))
            occurrences.append(Occurrence(
                (f"consumer-{effect.kind}", effect.step),
                Key(plan.domain, effect.kind, _asset(note_kind), amount, note_hash, recipient),
                _source_provenance(effect.source_location),
            ))
        effects = tuple(occurrences)
        assessment = assess_trace(policy, effects, committed=True,
                                  deferred=any(not item["success"] for item in attempts))
        concrete = ConcreteResult("RETURN", {}, final_token, [], [], [], attempts)
        admission = _scope(plan, assignment, concrete)
        return SymbolicConsumerResult(
            "RETURN", "", assignment.public_inputs[1], assignment.height,
            assignment.guards.validator_set_index_after,
            final_mints, final_token, effects, policy.permissions, policy.obligations,
            assessment, admission, tuple(attempts), verifier_claim,
            assignment.guards.attacker_capabilities, (),
        )
    except (EvaluationError, Unsupported) as error:
        reason = getattr(error, "reason", "SYMBOLIC_EVALUATION_ERROR")
        concrete = ConcreteResult("UNKNOWN", {}, initial_token, [], [], [], [], reason)
        admission = _scope(plan, assignment, concrete)
        return SymbolicConsumerResult(
            "UNKNOWN", reason, assignment.current_root, assignment.current_height,
            assignment.current_validator_set_index,
            initial_mints, initial_token, (), policy.permissions, policy.obligations,
            None, admission, (), verifier_claim, assignment.guards.attacker_capabilities,
            (reason,),
        )


def policy_occurrence(identity: tuple[str, int], *, domain: str, kind: str,
                      note_kind: int, amount: int, note_hash: int,
                      recipient: int | None, rationale_path: str,
                      rationale_sha256: str, location: str) -> Occurrence:
    """Create an explicit analyst-policy occurrence; never an extracted fact."""

    return Occurrence(
        identity,
        Key(domain, kind, _asset(note_kind), amount, note_hash, recipient),
        Provenance(Artifact(rationale_path, rationale_sha256), location, EvidenceGrade.POLICY),
    )
