#!/usr/bin/env python3
"""Compile pinned source to AST and compare symbolic evaluation to Machine.

This is an offline component check.  It runs solc only to recover the pinned
AST, then interprets it with the existing concrete executor.  It never invokes
an SMT solver, proof tool, EVM, verifier contract, or live consumer.
"""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bindcheck_d1.frontends.consumer_boundary_v1 import Boundary, walk
from bindcheck_d1.frontends.consumer_execution_v1 import BoundaryChoices, Machine, Token
from bindcheck_d1.frontends.guard_frame_v1 import check_guard, check_use_site
from bindcheck_d1.model_v2 import Policy, Unsupported
from bindcheck_d1.symbolic_consumer_v2 import (
    MAX_V2_AMOUNT,
    PINNED_CONSUMER_REVISION,
    ConsumerAssignment,
    GuardBoundary,
    MintEntry,
    VerifierBoundary,
    build_transition,
)


IMPORT = re.compile(r'import\s+(?:[^;]*?\s+from\s+)?["\']([^"\']+)["\']\s*;')
PAYY_ROOTS = (
    "eth/contracts/rollup3/RollupV1.sol",
    "eth/contracts/noir/IVerifier.sol",
    "eth/contracts/IUSDC.sol",
)


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    return digest_bytes(Path(path).read_bytes())


def git_show(repository, revision, path):
    process = subprocess.run(
        ["git", "-C", str(repository), "show", f"{revision}:{path}"],
        check=False, capture_output=True,
    )
    if process.returncode:
        raise RuntimeError(process.stderr.decode(errors="replace"))
    return process.stdout


def normalize_import(current, imported):
    if imported.startswith("@"):
        return str(PurePosixPath(imported))
    return posixpath.normpath(posixpath.join(posixpath.dirname(current), imported))


def source_bytes(repository, oz_root, revision, name):
    if name.startswith("eth/"):
        return git_show(repository, revision, name)
    contracts = "@openzeppelin/contracts/"
    upgradeable = "@openzeppelin/contracts-upgradeable/"
    if name.startswith(contracts):
        return (oz_root / "contracts" / name[len(contracts):]).read_bytes()
    if name.startswith(upgradeable):
        return (oz_root / "upgradeable" / name[len(upgradeable):]).read_bytes()
    raise FileNotFoundError(name)


def collect_sources(repository, oz_root, revision):
    pending = list(PAYY_ROOTS)
    sources = {}
    while pending:
        name = pending.pop()
        if name in sources:
            continue
        raw = source_bytes(repository, oz_root, revision, name)
        text = raw.decode()
        sources[name] = text
        for imported in IMPORT.findall(text):
            resolved = normalize_import(name, imported)
            if resolved not in sources:
                pending.append(resolved)
    return sources


def compile_boundary(solc, sources, output):
    request = {
        "language": "Solidity",
        "sources": {name: {"content": content} for name, content in sources.items()},
        "settings": {
            "optimizer": {"enabled": True, "runs": 200},
            "viaIR": True,
            "evmVersion": "shanghai",
            "outputSelection": {"*": {"": ["ast"], "*": ["metadata"]}},
        },
    }
    argv = [str(solc), "--standard-json"]
    process = subprocess.run(argv, input=json.dumps(request).encode(), capture_output=True,
                             check=False, timeout=120)
    output.mkdir(parents=True, exist_ok=False)
    (output / "solc.stdout.json").write_bytes(process.stdout)
    (output / "solc.stderr").write_bytes(process.stderr)
    if process.returncode:
        raise RuntimeError(f"solc exit {process.returncode}")
    compiled = json.loads(process.stdout)
    errors = [item for item in compiled.get("errors", []) if item.get("severity") == "error"]
    if errors:
        raise RuntimeError(json.dumps(errors, indent=2))
    units = []
    for name, source in sources.items():
        ast = compiled.get("sources", {}).get(name, {}).get("ast")
        if ast is None:
            raise RuntimeError(f"missing AST: {name}")
        units.append((name, ast, source.encode()))
    return Boundary(units), {
        "argv": argv,
        "exit_status": process.returncode,
        "stdout_sha256": digest(output / "solc.stdout.json"),
        "stderr_sha256": digest(output / "solc.stderr"),
        "warning_count": len(compiled.get("errors", [])),
    }


def one(boundary, kind, name, **attributes):
    found = [node for node in boundary.nodes.values()
             if node.get("nodeType") == kind and node.get("name") == name
             and all(node.get(key) == value for key, value in attributes.items())]
    if len(found) != 1:
        raise Unsupported("D1P08_SELECTION_AMBIGUOUS", f"{kind}/{name}: {len(found)}")
    return found[0]


def make_machine(boundary):
    entry = one(boundary, "FunctionDefinition", "verifyRollup")
    guard = one(boundary, "FunctionDefinition", "verifyValidatorSignatures")
    retained = one(boundary, "VariableDeclaration", "validatorSetIndex", stateVariable=True)["id"]
    protected = sorted(node["id"] for node in boundary.nodes.values()
                       if node.get("stateVariable") and node["id"] != retained)
    calls = [node for node in walk(entry["body"])
             if node.get("nodeType") == "FunctionCall"
             and node["expression"].get("referencedDeclaration") == guard["id"]]
    if len(calls) != 1:
        raise Unsupported("D1P08_GUARD_USE_SITE", str(len(calls)))
    context = {
        "policy_sha256": digest(ROOT / "protocols/d1/d1-03-joint-semantics-v2.md"),
        "bounds_sha256": digest(ROOT / "protocols/d1/d1-03-joint-semantics-v2.json"),
        "assumptions_sha256": digest(ROOT / "protocols/d1/d1-03-joint-semantics.md"),
    }
    frame = check_guard(boundary, guard["id"], protected)
    certificate = check_use_site(boundary, entry["id"], calls[0]["id"], frame, context)
    token_fn = one(boundary, "FunctionDefinition", "executeBurnToAddress")
    transfers = [node["referencedDeclaration"] for node in walk(token_fn["body"])
                 if node.get("nodeType") == "MemberAccess" and node.get("memberName") == "transfer"]
    verifiers = [node["referencedDeclaration"] for node in walk(entry["body"])
                 if node.get("nodeType") == "MemberAccess" and node.get("memberName") == "verify"]
    if len(transfers) != 1 or len(verifiers) != 1:
        raise Unsupported("D1P08_EXTERNAL_BOUNDARY", f"{len(transfers)}/{len(verifiers)}")
    machine = Machine(
        boundary,
        entry["id"],
        frame_certificate=certificate,
        context=context,
        verifier_declaration=verifiers[0],
        transfer_declaration=transfers[0],
    )
    roots = {name: one(boundary, "VariableDeclaration", name, stateVariable=True)["id"]
             for name in ("rootHash", "blockHeight", "mints", "tokens", "provers",
                          "zkVerifiers", "validatorSetIndex", "substitutedBurns")}
    return machine, roots, certificate


def burn(amount=7, note_hash=42, recipient=0xDEAD, note_kind=0x4B):
    return [3, note_kind, amount, note_hash, recipient]


def mint(note_kind=0x4B, amount=100, note_hash=42):
    return [2, note_kind, amount, note_hash]


def run_case(machine, roots, case):
    n = case.get("n", 8)
    messages = case["messages"]
    if len(messages) != n:
        raise ValueError(case["name"])
    contract, token_address, sender, verifier_address = 0xC0, 0x70, 0xA0, 0xB0
    funds = case.get("funds", n * MAX_V2_AMOUNT)
    registry = deepcopy(case.get("mints", {}))
    words = [0x11, 0x12, 0x13, *messages]
    guard = case.get("guard", True)
    caller_authorized = case.get("caller", True)
    verifier_accepts = case.get("verifier", True)
    height = case.get("height", 2)
    token_map = deepcopy(case.get("token_map", {0x4B: token_address}))
    state = {
        roots["rootHash"]: 0x11,
        roots["blockHeight"]: 1,
        roots["validatorSetIndex"]: 0,
        roots["mints"]: {key: {"note_kind": value.note_kind,
                               "amount": value.amount, "spent": value.spent}
                          for key, value in registry.items()},
        roots["tokens"]: token_map,
        roots["provers"]: ({sender: 1} if caller_authorized else {}),
        roots["zkVerifiers"]: {1: {"enabled": True, "messages_length": n,
                                    "verifier": verifier_address}},
        roots["substitutedBurns"]: {},
    }
    token = Token(token_address, {contract: funds}, funds)
    concrete = machine.execute(
        [height, 1, b"proof", words, 0, ()], state, token,
        sender=sender, contract=contract,
        choices=BoundaryChoices(guard, {roots["validatorSetIndex"]: 7}, verifier_accepts),
    )
    assignment = ConsumerAssignment(
        tuple(words), height, 0x11, 1, sender, contract,
        GuardBoundary(
            caller_authorized, guard,
            "ASSUMED_OWNED_REGISTERED_PROVER" if caller_authorized else "",
            "ASSUMED_OWNED_VALIDATOR_QUORUM" if guard else "",
            tuple(
                item for enabled, item in (
                    (caller_authorized, "registered prover caller"),
                    (guard, "validator quorum signatures"),
                ) if enabled
            ),
            7 if guard else None,
        ),
        VerifierBoundary(
            1, verifier_address, n, True, verifier_accepts, 1,
            "payy-B-agg-final", "FULL_PRODUCER_RELATION", b"proof", True,
        ),
        0,
        token,
        registry,
        token_map,
        {},
    )
    symbolic = build_transition(n).evaluate(assignment, Policy((), (), "comparison policy"))

    concrete_mints = concrete.state.get(roots["mints"], {})
    comparisons = {
        "outcome": symbolic.outcome == concrete.outcome,
        "root": symbolic.state_root == concrete.state.get(roots["rootHash"], 0x11),
        "height": symbolic.block_height == concrete.state.get(roots["blockHeight"], 1),
        "validator_set_index": symbolic.validator_set_index
                               == concrete.state.get(roots["validatorSetIndex"], 0),
        "balances": symbolic.token.balances == concrete.token.balances,
        "mint_spent": all(
            symbolic.mints.get(key, MintEntry(0, 0, False)).spent == value.get("spent", False)
            for key, value in concrete_mints.items()
        ) and all(
            concrete_mints.get(key, {}).get("spent", False) == value.spent
            for key, value in symbolic.mints.items()
        ),
        "burn_effect_count": sum(effect.key.kind == "burn" for effect in symbolic.effects)
                             == len(concrete.transfers),
        "mint_effect_count": sum(effect.key.kind == "mint" for effect in symbolic.effects)
                             == sum(event["event"] == "Minted" for event in concrete.events),
        "rollback_empty_effects": concrete.outcome == "RETURN" or (
            not symbolic.effects and not concrete.transfers and not concrete.events and not concrete.writes
        ),
    }
    if not all(comparisons.values()):
        raise AssertionError((case["name"], comparisons, symbolic, concrete))
    return {
        "name": case["name"],
        "n": n,
        "symbolic_outcome": symbolic.outcome,
        "concrete_outcome": concrete.outcome,
        "symbolic_reason": symbolic.reason,
        "concrete_reason": concrete.reason,
        "comparisons": comparisons,
        "effects": len(symbolic.effects),
        "burn_attempts": list(symbolic.burn_attempts),
        "admitted_v2": symbolic.admission.admitted,
        "admission_reasons": list(symbolic.admission.reasons),
        "security_verdict": symbolic.security_verdict,
    }


def cases():
    return [
        {"name": "padding-normal", "messages": [0] * 8},
        {"name": "burn-low160", "messages": burn(recipient=(1 << 160) + 0xDEAD) + [0] * 3},
        {"name": "zero-default-mint", "messages": mint(0, 0, 43) + [0] * 4},
        {"name": "duplicate-mint-rollback", "messages": mint() + mint(),
         "mints": {42: MintEntry(0x4B, 100, False)}},
        {"name": "late-truncation-rollback", "messages": burn() + [0, 0, 2]},
        {"name": "invalid-kind", "messages": [4] + [0] * 7},
        {"name": "prover-guard-reject", "messages": mint() + [0] * 4,
         "mints": {42: MintEntry(0x4B, 100, False)}, "caller": False,
         "guard": False},
        {"name": "signature-guard-reject", "messages": mint() + [0] * 4,
         "mints": {42: MintEntry(0x4B, 100, False)}, "guard": False},
        {"name": "verifier-reject-rollback", "messages": mint() + [0] * 4,
         "mints": {42: MintEntry(0x4B, 100, False)}, "verifier": False},
        {"name": "height-reject-rollback", "messages": mint() + [0] * 4,
         "mints": {42: MintEntry(0x4B, 100, False)}, "height": 1},
        {"name": "sequential-transfer-failure", "n": 10,
         "messages": burn() + burn(), "funds": 10},
        {"name": "self-transfer-occurrence", "messages": burn(recipient=0xC0) + [0] * 3},
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--oz-root", type=Path, required=True)
    parser.add_argument("--solc", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"fresh output required: {args.output}")
    version = subprocess.run([str(args.solc), "--version"], capture_output=True,
                             text=True, check=True, timeout=30)
    sources = collect_sources(args.source_repo, args.oz_root, PINNED_CONSUMER_REVISION)
    boundary, compilation = compile_boundary(args.solc, sources, args.output)
    machine, roots, certificate = make_machine(boundary)
    observations = [run_case(machine, roots, case) for case in cases()]
    result = {
        "task": "D1P-08",
        "scope": "offline symbolic-expression evaluation against existing concrete AST executor",
        "source_revision": PINNED_CONSUMER_REVISION,
        "source_repo": str(args.source_repo.resolve()),
        "consumer_sha256": digest_bytes(sources["eth/contracts/rollup3/RollupV1.sol"].encode()),
        "source_count": len(sources),
        "source_sha256": {name: digest_bytes(value.encode()) for name, value in sorted(sources.items())},
        "solc": {
            "path": str(args.solc.resolve()),
            "sha256": digest(args.solc),
            "version": version.stdout,
            **compilation,
        },
        "concrete_executor_sha256": digest(ROOT / "src/bindcheck_d1/frontends/consumer_execution_v1.py"),
        "symbolic_consumer_sha256": digest(ROOT / "src/bindcheck_d1/symbolic_consumer_v2.py"),
        "guard_certificate_cache_key": certificate["cache_key"],
        "cases": observations,
        "counts": {"cases": len(observations), "passed": len(observations), "failed": 0},
        "limitations": [
            "Concrete assignments test the component; they do not prove universal equivalence.",
            "Guard and verifier results are explicit abstract choices, not signatures or proofs.",
            "No EVM, proof, solver, joint encoder, or consumer replay ran.",
        ],
        "solver_calls": 0,
        "proof_calls": 0,
        "consumer_replays": 0,
        "research_verdict": "UNKNOWN",
    }
    result_path = args.output / "validation.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"counts": result["counts"], "solver_calls": 0,
                      "research_verdict": "UNKNOWN"}, indent=2))


if __name__ == "__main__":
    main()
