"""Conservative constant propagation for a parsed, selected ACIR component.

This is a solver-free selective adaptation of the Claude-worktree propagation
prototype (SHA-256 0957b5f15e11c255577e6b6603bb52b742f326e55fbce6425f1cd29ab484e7f2).
It deliberately omits that prototype's small-domain inference.  An original
constraint is only retained, discharged after exact ground evaluation, or used
to reconstruct one uniquely determined field witness.  A memory read is
lowered only when its index and every preceding write index are known.

The caller must retain the complete case predicate.  ``fixed`` values are
valid only when separately shown to be logical consequences of that predicate.
No solver, process-launch, or SMT serialization interface exists here.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from .model_v2 import FIELD_MODULUS as P


class Contradiction(ValueError):
    def __init__(self, location: Any, reason: str):
        super().__init__(f"{location}: {reason}")
        self.location = location
        self.reason = reason


class UnsupportedOpcode(ValueError):
    pass


def normalize(expression: Iterable[tuple[int, list[int]]]) -> dict[tuple[int, ...], int]:
    result: dict[tuple[int, ...], int] = defaultdict(int)
    for coefficient, witnesses in expression:
        monomial = tuple(sorted(witnesses))
        result[monomial] = (result[monomial] + coefficient) % P
    return {monomial: coefficient for monomial, coefficient in result.items()
            if coefficient}


def substitute(poly: dict[tuple[int, ...], int], values: dict[int, int]) -> dict[tuple[int, ...], int]:
    result: dict[tuple[int, ...], int] = defaultdict(int)
    for monomial, coefficient in poly.items():
        rest = []
        for witness in monomial:
            if witness in values:
                coefficient = coefficient * values[witness] % P
            else:
                rest.append(witness)
        if coefficient:
            result[tuple(rest)] = (result[tuple(rest)] + coefficient) % P
    return {monomial: coefficient for monomial, coefficient in result.items()
            if coefficient}


def polynomial_witnesses(poly: dict[tuple[int, ...], int]) -> set[int]:
    return {witness for monomial in poly for witness in monomial}


def expression_witnesses(expression: Iterable[tuple[int, list[int]]]) -> set[int]:
    return {witness for _, witnesses in expression for witness in witnesses}


def opcode_witnesses(opcode: tuple) -> set[int]:
    kind = opcode[0]
    if kind in ("assert", "range"):
        return expression_witnesses(opcode[1])
    if kind == "init":
        return set().union(*(expression_witnesses(item) for item in opcode[2])) \
            if opcode[2] else set()
    if kind in ("read", "write"):
        return expression_witnesses(opcode[2]) | expression_witnesses(opcode[3])
    raise UnsupportedOpcode(kind)


def substituted_opcode_witnesses(opcode: tuple, values: dict[int, int]) -> set[int]:
    """Witnesses left after exact substitution in one retained memory opcode."""
    kind = opcode[0]
    expressions = opcode[2] if kind == "init" else (opcode[2], opcode[3])
    result: set[int] = set()
    for expression in expressions:
        result |= polynomial_witnesses(substitute(normalize(expression), values))
    return result


def _json_location(value: Any) -> str | int:
    if isinstance(value, int):
        return value
    if isinstance(value, tuple):
        return ":".join(str(item) for item in value)
    return str(value)


@dataclass(frozen=True)
class Residual:
    assertions: dict[Any, dict[tuple[int, ...], int]]
    ranges: dict[int, tuple[dict[tuple[int, ...], int], int]]
    memory: tuple[int, ...]


class State:
    """Exact propagation state over an ordered selected component."""

    SUPPORTED = frozenset(("assert", "range", "init", "read", "write"))

    def __init__(
        self,
        indexed_opcodes: Iterable[tuple[int, tuple]],
        fixed: dict[int, int],
        fixed_basis: dict[int, str],
        protected_witnesses: Iterable[int] = (),
    ) -> None:
        self.indexed_opcodes = tuple(indexed_opcodes)
        self.opcodes = {index: opcode for index, opcode in self.indexed_opcodes}
        unsupported = [(index, opcode[0]) for index, opcode in self.indexed_opcodes
                       if opcode[0] not in self.SUPPORTED]
        if unsupported:
            raise UnsupportedOpcode(str(unsupported[:8]))
        if set(fixed) != set(fixed_basis):
            raise ValueError("every initial fixed value needs a case-implication basis")

        self.values = {witness: value % P for witness, value in fixed.items()}
        self.assignment_reason: dict[int, dict[str, Any]] = {
            witness: {"rule": "case_implied_constant", "basis": fixed_basis[witness]}
            for witness in fixed
        }
        self.protected = frozenset(protected_witnesses)
        self.polys: dict[Any, dict[tuple[int, ...], int]] = {}
        self.ranges: dict[int, tuple[dict[tuple[int, ...], int], int]] = {}
        self.memory: list[int] = []
        self.resolved_reads: dict[int, dict[tuple[int, ...], int]] = {}
        self.occurrences: dict[int, set[Any]] = defaultdict(set)
        self.events: list[dict[str, Any]] = []
        self._event_keys: set[tuple[Any, ...]] = set()

        for index, opcode in self.indexed_opcodes:
            kind = opcode[0]
            if kind == "assert":
                self._add_poly(index, normalize(opcode[1]))
            elif kind == "range":
                poly = normalize(opcode[1])
                self.ranges[index] = (poly, opcode[2])
                for witness in polynomial_witnesses(poly):
                    self.occurrences[witness].add(("range", index))
            else:
                self.memory.append(index)

    def _event(self, unique: tuple[Any, ...], **event: Any) -> None:
        if unique not in self._event_keys:
            self._event_keys.add(unique)
            self.events.append(event)

    def _add_poly(self, key: Any, poly: dict[tuple[int, ...], int]) -> None:
        self.polys[key] = poly
        for witness in polynomial_witnesses(poly):
            self.occurrences[witness].add(key)

    def assign(self, witness: int, value: int, reason: dict[str, Any]) -> bool:
        value %= P
        if witness in self.values:
            if self.values[witness] != value:
                raise Contradiction(reason.get("source", "assignment"),
                                    f"w{witness} has conflicting constants")
            return False
        self.values[witness] = value
        self.assignment_reason[witness] = reason
        self._event(("assign", witness), action="reconstruct_witness",
                    witness=witness, value=str(value), reason=reason,
                    protected_interface=witness in self.protected)
        return True

    def run(self) -> "State":
        changed = True
        while changed:
            changed = self._fixpoint()
            changed = self._memory_pass() or changed
        self._check_ranges()
        return self

    def _fixpoint(self) -> bool:
        any_change = False
        changed = True
        while changed:
            changed = False
            for key in list(self.polys):
                poly = substitute(self.polys[key], self.values)
                self.polys[key] = poly
                unknown = polynomial_witnesses(poly)
                if not unknown:
                    constant = poly.get((), 0) % P
                    if constant:
                        raise Contradiction(_json_location(key),
                                            f"ground assertion is nonzero ({constant})")
                    self._event(("ground_assert", key), action="discharge_assertion",
                                source=_json_location(key),
                                rule="exact substitution produced field zero")
                    continue
                if len(unknown) != 1:
                    continue
                witness = next(iter(unknown))
                # The remaining polynomial must be affine in exactly this one
                # witness.  A squared/product occurrence is never linearized.
                if any(len(monomial) > 1 for monomial in poly):
                    continue
                coefficient = poly.get((witness,), 0)
                if not coefficient:
                    continue
                value = (-poly.get((), 0)) * pow(coefficient, P - 2, P) % P
                reason = {
                    "rule": "unique_affine_field_solution",
                    "source": _json_location(key),
                    "coefficient": str(coefficient),
                    "constant": str(poly.get((), 0)),
                }
                if self.assign(witness, value, reason):
                    changed = any_change = True
                self.polys[key] = {}
                self._event(("linear_assert", key), action="eliminate_assertion_with_reconstruction",
                            source=_json_location(key), witness=witness,
                            rule="unique nonzero affine coefficient over the pinned field")
        return any_change

    def _memory_pass(self) -> bool:
        blocks: dict[int, list[dict[tuple[int, ...], int]]] = {}
        dirty: set[int] = set()
        changed = False
        for index in self.memory:
            opcode = self.opcodes[index]
            kind, block = opcode[0], opcode[1]
            if kind == "init":
                blocks[block] = [normalize(expression) for expression in opcode[2]]
                dirty.discard(block)
                continue
            if block not in blocks:
                raise Contradiction(index, f"memory block b{block} used before INIT")
            if block in dirty:
                continue
            index_expression = opcode[3] if kind == "read" else opcode[2]
            index_poly = substitute(normalize(index_expression), self.values)
            if polynomial_witnesses(index_poly):
                if kind == "write":
                    dirty.add(block)
                    self._event(("dirty", index), action="retain_memory_suffix",
                                source=index, block=block,
                                rule="write index remains symbolic")
                continue
            offset = index_poly.get((), 0)
            if offset >= len(blocks[block]):
                raise Contradiction(index,
                                    f"memory index {offset} outside b{block}[0:{len(blocks[block])}]")
            if kind == "write":
                blocks[block][offset] = normalize(opcode[3])
                continue
            if index in self.resolved_reads:
                continue
            equality: dict[tuple[int, ...], int] = defaultdict(int)
            for monomial, coefficient in normalize(opcode[2]).items():
                equality[monomial] = (equality[monomial] + coefficient) % P
            for monomial, coefficient in blocks[block][offset].items():
                equality[monomial] = (equality[monomial] - coefficient) % P
            equality = {monomial: coefficient for monomial, coefficient in equality.items()
                        if coefficient}
            self.resolved_reads[index] = equality
            self._add_poly(("memory_read", index), equality)
            self._event(("read", index), action="replace_memory_read_with_equality",
                        source=index, block=block, offset=str(offset),
                        rule="read index and every preceding write index are exact constants")
            changed = True
        return changed

    def _check_ranges(self) -> None:
        for index, (poly, bits) in self.ranges.items():
            if bits >= 254:
                self._event(("range_field_bound", index), action="discharge_range",
                            source=index, value="field-domain", bits=bits,
                            rule="every canonical field value is below 2^254")
                continue
            residual = substitute(poly, self.values)
            if polynomial_witnesses(residual):
                continue
            value = residual.get((), 0)
            if bits < 254 and value >= 1 << bits:
                raise Contradiction(index, f"{value} violates {bits}-bit range")
            self._event(("range", index), action="discharge_range",
                        source=index, value=str(value), bits=bits,
                        rule="exact substituted value is inside the unsigned range")

    def residual(self) -> Residual:
        assertions = {
            key: substitute(poly, self.values) for key, poly in self.polys.items()
        }
        assertions = {key: poly for key, poly in assertions.items()
                      if polynomial_witnesses(poly)}
        ranges = {}
        for index, (poly, bits) in self.ranges.items():
            residual = substitute(poly, self.values)
            if bits < 254 and polynomial_witnesses(residual):
                ranges[index] = (residual, bits)
        memory = tuple(index for index in self.memory
                       if not (self.opcodes[index][0] == "read"
                               and index in self.resolved_reads))
        return Residual(assertions, ranges, memory)

    def audit(
        self,
        original_witnesses: Iterable[int],
        case_predicate_witnesses: Iterable[int],
        case_predicate: str,
    ) -> dict[str, Any]:
        residual = self.residual()
        relation_witnesses: set[int] = set()
        for poly in residual.assertions.values():
            relation_witnesses |= polynomial_witnesses(poly)
        for poly, _ in residual.ranges.values():
            relation_witnesses |= polynomial_witnesses(poly)
        for index in residual.memory:
            relation_witnesses |= substituted_opcode_witnesses(
                self.opcodes[index], self.values
            )
        case_witnesses = set(case_predicate_witnesses)
        original_witness_set = set(original_witnesses)
        free_extension_witnesses = sorted(
            original_witness_set - relation_witnesses - case_witnesses - set(self.values)
        )
        interface_equalities = [
            {
                "witness": witness,
                "value": str(self.values[witness]),
                "reason": self.assignment_reason[witness],
            }
            for witness in sorted(self.protected & set(self.values))
        ]
        retained_interface_relations = [
            _json_location(key) for key, poly in residual.assertions.items()
            if polynomial_witnesses(poly) & self.protected
        ]
        original_counts = Counter(opcode[0] for _, opcode in self.indexed_opcodes)
        residual_original_assertions = sum(isinstance(key, int)
                                           for key in residual.assertions)
        derived_assertions = len(residual.assertions) - residual_original_assertions
        memory_counts = Counter(self.opcodes[index][0] for index in residual.memory)
        residual_original_count = (
            residual_original_assertions + len(residual.ranges) + len(residual.memory)
        )
        reason_counts = Counter(event["action"] for event in self.events)
        return {
            "status": "SIMPLIFIED_FEASIBILITY_UNKNOWN",
            "case_predicate_retained_verbatim": case_predicate,
            "case_predicate_witnesses": sorted(case_witnesses),
            "initial_case_implied_values": {
                str(w): str(self.values[w]) for w, reason in self.assignment_reason.items()
                if reason["rule"] == "case_implied_constant"
            },
            "assigned_values": {str(w): str(self.values[w]) for w in sorted(self.values)},
            "assignment_reasons": {str(w): self.assignment_reason[w]
                                   for w in sorted(self.assignment_reason)},
            "reconstruction_rule": (
                "extend a residual model with each recorded fixed/uniquely solved witness; "
                "memory-read equalities are retained or used by the same affine rule"
            ),
            "original": {
                "opcodes": len(self.indexed_opcodes),
                "opcode_counts": dict(sorted(original_counts.items())),
                "witnesses": len(set(original_witnesses)),
                "range_constraints": original_counts["range"],
            },
            "residual": {
                "original_opcodes": residual_original_count,
                "original_assertions": residual_original_assertions,
                "derived_memory_equalities": derived_assertions,
                "range_constraints": len(residual.ranges),
                "memory_opcode_counts": dict(sorted(memory_counts.items())),
                "relation_witnesses": len(relation_witnesses),
                "with_case_and_reconstruction_witnesses": len(
                    relation_witnesses | case_witnesses | set(self.values) |
                    set(free_extension_witnesses)
                ),
                "retained_interface_relations": retained_interface_relations,
                "retained_interface_equalities": interface_equalities,
                "retained_interface_free_witnesses": sorted(
                    self.protected & set(free_extension_witnesses)
                ),
                "free_extension_witnesses": free_extension_witnesses,
                "free_extension_rule": (
                    "these original witnesses no longer constrain the specialized residual; "
                    "retain them at any interface/goal and extend a model with arbitrary "
                    "canonical field values"
                ),
            },
            "reduction_reason_counts": dict(sorted(reason_counts.items())),
            "events": self.events,
        }

