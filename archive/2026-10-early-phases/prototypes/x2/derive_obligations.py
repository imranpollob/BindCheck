"""X2 (lane-x exploratory): generic P/O/E-template obligation derivation.

Derives mismatch-candidate obligations from an extracted consumer relation
(D1P-18 schema) plus the relation's own verifier-boundary expression.
No application names, no defect-specific rules, no planner obligation text.

Template rules (the only rules; they mention IR shapes, never a case):
  R1 EFFECT   : every committed `erc20_mint` occurrence on a success path is
                a protected effect; record its amount/beneficiary IR symbols.
  R2 ADMIT    : every IR subterm `select(storage S, symbol X)` that guards a
                path (positively on success, negated on a revert path) is an
                admission check binding word X to admitted set S.
  R3 CANDIDATE: for each (effect, admission) pair, emit the candidate query
                "consumer succeeds AND effect amount != 0 AND guarded word
                is outside the admitted set". Word positions come from the
                verifier-boundary argument order in the relation itself.

Manual inputs (counted by the caller, never hidden): the admitted-state
values for each storage set, the environment (chain id), and the shared
effect-model table already inside the extracted relation.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def _symbols(node, acc):
    if isinstance(node, dict):
        if node.get("op") == "symbol":
            acc.update(a for a in node.get("args", []) if isinstance(a, str))
        for v in node.values():
            _symbols(v, acc)
    elif isinstance(node, list):
        for v in node:
            _symbols(v, acc)
    return acc


def _admission_checks(node, negated, acc):
    """Collect (storage, symbol) from select(storage, symbol) subterms."""
    if isinstance(node, dict):
        if node.get("op") == "select":
            args = node.get("args", [])
            if len(args) == 2 and isinstance(args[0], dict) and args[0].get("op") == "storage":
                syms = _symbols(args[1], set())
                for s in syms:
                    acc.add((args[0]["args"][0], s, negated))
        child_neg = negated or node.get("op") == "not"
        for v in node.values():
            _admission_checks(v, child_neg, acc)
    elif isinstance(node, list):
        for v in node:
            _admission_checks(v, negated, acc)
    return acc


def word_positions(relation):
    """calldata symbol -> public-word index, from verifier-boundary order.

    Every bytes32(...) argument occupies one word slot in order, including
    non-calldata slots (e.g. block.chainid); only calldata slots are named.
    """
    expr = relation["verifier_boundary"]["expression"]
    slots = re.findall(r"bytes32\(([^()]*(?:\([^()]*\))?[^()]*)\)", expr)
    positions = {}
    for i, slot in enumerate(slots):
        m = re.search(r"calldata\.(_\w+)", slot)
        if m and m.group(1) != "_poof":
            positions[m.group(1)] = i
    return positions


def derive(relation):
    positions = word_positions(relation)
    effects, admissions = [], set()
    for path in relation["paths"]:
        for guard in path.get("guards_ir", []):
            _admission_checks(guard, False, admissions)
        if path["status"] != "success":
            continue
        for mint in path["committed"].get("mints", []):
            effects.append({
                "path": path["id"],
                "amount_symbols": sorted(_symbols(mint.get("amount_ir", {}), set())),
                "beneficiary_symbols": sorted(_symbols(mint.get("beneficiary_ir", {}), set())),
                "location": mint.get("location"),
            })
    def bare(sym):
        return sym[len("calldata."):] if sym.startswith("calldata.") else sym

    obligations = []
    for eff in effects:
        for amount_sym in eff["amount_symbols"]:
            if bare(amount_sym) not in positions:
                continue
            for storage, guard_sym, _neg in sorted(admissions):
                if bare(guard_sym) in positions:
                    obligations.append({
                        "rule": "R3_CANDIDATE",
                        "effect_path": eff["path"],
                        "effect_location": eff["location"],
                        "amount_symbol": amount_sym,
                        "amount_word": positions[bare(amount_sym)],
                        "guard_storage": storage,
                        "guard_symbol": guard_sym,
                        "guard_word": positions[bare(guard_sym)],
                        "goal": "consumer_success AND amount_word != 0 AND guard_word NOT IN admitted(guard_storage)",
                    })
    unique, seen = [], set()
    for o in obligations:
        key = (o["amount_word"], o["guard_word"], o["guard_storage"])
        if key not in seen:
            seen.add(key)
            unique.append(o)
    return {
        "unique_obligations": unique,
        "word_positions": positions,
        "effects": effects,
        "admission_checks": sorted(
            ({"storage": s, "symbol": y} for s, y, _ in admissions),
            key=lambda d: (d["storage"], d["symbol"]),
        ),
        "obligations": obligations,
        "manual_inputs": [
            "admitted-state values for each guard storage set (contract 6.2 input)",
            "environment chain_id (contract 6.2 input)",
            "shared effect-model table embedded in the extracted relation",
        ],
    }


if __name__ == "__main__":
    rel = json.loads(Path(sys.argv[1]).read_text())
    print(json.dumps(derive(rel), indent=1))
