"""Reusable validation-harness core for BindCheck automatic validation.

This module owns the evidence ladder (research contract rev 3, section 8)
and the corrected grading rules from the x-experiment evidence ledger. It
has NO application imports: WarpToad/Payy specifics live in the per-app
adapters (`scripts/xav_run.py`, `scripts/te04_part2.py`,
`scripts/te05_part2.py`, `scripts/xav/repair_check.py`). A new application
adds an adapter that calls into this core; see `docs/x-experiment/HARNESS.md`.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

# Evidence ladder, contract section 8. Only E4 is end-to-end validated.
E0 = "E0"  # no report
E1 = "E1"  # tool warning
E2 = "E2"  # model satisfying the ACTUAL compiled producer relation,
# decoder and consumer model
E3 = "E3"  # real proof of that assignment accepted by the pinned,
# unchanged verifier (for a mutant: its own matching key)
E4 = "E4"  # that proof accepted by the unchanged consumer from an
# admitted or reachable state, producing an unauthorized committed
# effect (or undischarged obligation), checked on state
E4_PRESERVED = "E4-preserved"  # fresh lower-leg correspondence + preserved chain

# Precise relabel for mock-verifier rows (ledger section 5): the mock
# stands in for proof acceptance, so the consumer-model leg is
# counterfactual and the contract's E2 is NOT met. Detection credit at E1.
E1_MOCK = "E1+mock"

E_ORDER = (E0, E1, E1_MOCK, E2, E3, E4, E4_PRESERVED)

# Stable warning key: (target, rule, public word, effect). Warning ids
# (W001, ...) and line-number locations are analyzer-version-specific and
# WILL change at the v2.0 freeze, so adjudication keys on this tuple and
# the v2.0 remap is mechanical. `seen_as` records the v1.1 id for audit.
WarningKey = tuple[str, str, str, str]


def warning_key(target: str, warning: dict[str, Any]) -> WarningKey:
    """Extract the stable (target, rule, word, effect) key.

    - R-BIND: word is the ABI leaf/range after `abi.`; effect `unbound`.
    - R-EFFECT: word is the paths range `messages[a..b]`; effect is the
      sorted effect kinds (line numbers excluded: volatile across versions).
    - R-CONSUMER: word is the evidence consumer path; effect
      `no-downstream-use`.
    - R-POLARITY: word `single-use`; effect is the polarity value.
    """
    rule = warning.get("rule", "?")
    ev = warning.get("evidence") or {}
    loc = warning.get("location", "")
    if rule == "R-BIND":
        word = loc.split("abi.")[-1] if "abi." in loc else loc
        return (target, rule, word, "unbound")
    if rule == "R-EFFECT":
        paths = ev.get("paths") or []
        if len(paths) == 1:
            word = paths[0]
        elif paths and all("[" in p for p in (paths[0], paths[-1])):
            # normalize `messages[0]`..`messages[999]` to `messages[0..999]`
            head = paths[0].split("[")[0]
            first = paths[0].split("[")[1].rstrip("]")
            last = paths[-1].split("[")[1].rstrip("]")
            word = f"{head}[{first}..{last}]"
        elif paths:
            word = "+".join(paths[:4]) + (f"+{len(paths) - 4}-more" if len(paths) > 4 else "")
        else:
            word = loc
        kinds = "+".join(sorted(ev.get("effect_kinds") or ["effect"]))
        return (target, rule, word, kinds)
    if rule == "R-CONSUMER":
        return (target, rule, str(ev.get("path", "?")), "no-downstream-use")
    if rule == "R-POLARITY":
        return (target, rule, "single-use", str(ev.get("polarity", "?")))
    return (target, rule, loc, "unknown")


# Adjudicated corrections over raw driver grades, keyed by WarningKey.
# Everything not listed keeps the driver's grade (with the E1+mock rule).
OVERRIDES: dict[WarningKey, tuple[str, str]] = {
    ("PY-C02", "R-BIND", "messages[0]..messages[999]", "unbound"):
        ("E3", "TE05: own-mutation mutant-keyed proofs (inner slot 009 + "
         "final), original/repaired ACVM rejection, onchain containment"),
    ("PY-C02", "R-EFFECT", "messages[0..999]",
     "storage-write+token-transfer+token-transfer-from"):
        ("E1", "TE05: same-transaction runs under both keys revert at "
         "consumer message policy, zero state change"),
    ("WT-S02", "R-CONSUMER", "giga_root", "no-downstream-use"):
        ("E4", "corrected setup (honest-seeded mock): mutant accepts "
         "unadmitted 0x1234, pinned reverts; v1.1 run as-run was a setup "
         "artifact"),
    ("PY-S01", "R-EFFECT", "messages[1..999]",
     "storage-write+token-transfer+token-transfer-from"):
        ("E4", "TE06: same real proof settles unregistered mint on mutant, "
         "reverts Mint value invalid on pinned; committed keys throughout"),
    ("PY-S01", "R-POLARITY", "single-use", "must-not-be-in"):
        ("E4", "TE06: same transaction as the W002 lift (unregistered mint "
         "settles once where admission is removed)"),
    ("PY-S03", "R-EFFECT", "messages[1..999]",
     "storage-write+token-transfer+token-transfer-from"):
        ("E4", "TE06: same real proof settles on both; mutant misdirects "
         "payout to note-kind-derived address, pinned pays recipient; no "
         "substitute registered either side"),
    ("PY-S02", "R-EFFECT", "messages[1..999]",
     "storage-write+token-transfer+token-transfer-from"):
        ("E3", "TE06: real proof verifies onchain and settles honestly; "
         "second settlement unprovable at circuit level (output-slot "
         "emptiness enforced agg_utxo:140); missing spent check is "
         "defense-in-depth removal, effect unreachable alone"),
    ("PY-S02", "R-POLARITY", "single-use", "must-not-be-in"):
        ("E3", "TE06: same basis as the W002 row (single settlement real; "
         "re-settlement circuit-blocked)"),
}

# Corrected totals over the 53 v1.1 warnings (ledger section 2).
# TE06 final: S01 pair + S03 lifted to E4; S02 pair E3 (re-settlement
# circuit-blocked); S04 stays E1+mock (infeasible by construction).
EXPECTED_CORRECTED = Counter({
    E4: 11, E4_PRESERVED: 1, E3: 7, E1_MOCK: 1, E1: 33,
})


# Legacy (mutant, warning-id) fallback for rows without warning objects.
# Warning ids are version-specific; prefer warning_key() whenever the
# warning object is available (check_ledger does).
LEGACY_OVERRIDES: dict[tuple[str, str], WarningKey] = {
    ("PY-C02", "W001"): ("PY-C02", "R-BIND", "messages[0]..messages[999]", "unbound"),
    ("PY-C02", "W002"): ("PY-C02", "R-EFFECT", "messages[0..999]",
                         "storage-write+token-transfer+token-transfer-from"),
    ("WT-S02", "W001"): ("WT-S02", "R-CONSUMER", "giga_root", "no-downstream-use"),
    ("PY-S01", "W002"): ("PY-S01", "R-EFFECT", "messages[1..999]",
                         "storage-write+token-transfer+token-transfer-from"),
    ("PY-S01", "W004"): ("PY-S01", "R-POLARITY", "single-use", "must-not-be-in"),
    ("PY-S03", "W002"): ("PY-S03", "R-EFFECT", "messages[1..999]",
                         "storage-write+token-transfer+token-transfer-from"),
    ("PY-S02", "W002"): ("PY-S02", "R-EFFECT", "messages[1..999]",
                         "storage-write+token-transfer+token-transfer-from"),
    ("PY-S02", "W004"): ("PY-S02", "R-POLARITY", "single-use", "must-not-be-in"),
}


def corrected_grade(row: dict[str, Any],
                    warning: dict[str, Any] | None = None) -> tuple[str, str]:
    """Return (grade, basis) for one raw driver result row."""
    if warning is not None:
        key = warning_key(row.get("mutant", ""), warning)
    else:
        key = LEGACY_OVERRIDES.get(
            (row.get("mutant", ""), row.get("warning", "")),
            (row.get("mutant", ""), row.get("rule", "?"),
             row.get("location", "?"), "unknown"))
    if key in OVERRIDES:
        return OVERRIDES[key]
    if row.get("E") == "E2 (mock-verifier-scoped)":
        return (E1_MOCK, "mock stands in for proof acceptance; not contract E2")
    return (row.get("E", E1), "driver grade stands")


def ledger_counts(results: list[dict[str, Any]],
                  warnings: dict[tuple[str, str], dict[str, Any]] | None = None,
                  ) -> Counter:
    """Grade every row and count. Raises on unexpected grades."""
    counts: Counter = Counter()
    for row in results:
        w = warnings.get((row.get("mutant", ""), row.get("warning", ""))) if warnings else None
        grade, _ = corrected_grade(row, w)
        if grade not in EXPECTED_CORRECTED:
            raise ValueError(f"unexpected grade {grade!r} for {row.get('mutant')} {row.get('warning')}")
        counts[grade] += 0  # ensure key exists even at zero
        counts[grade] += 1
    return counts


def check_ledger(results: list[dict[str, Any]],
                 warnings: dict[tuple[str, str], dict[str, Any]] | None = None,
                 ) -> dict[str, Any]:
    """Assert corrected counts match the ledger; return the graded table."""
    if len(results) != 53:
        raise AssertionError(f"expected 53 v1.1 warnings, got {len(results)}")
    counts = ledger_counts(results, warnings)
    if counts != EXPECTED_CORRECTED:
        raise AssertionError(f"corrected counts differ: {dict(counts)} != {dict(EXPECTED_CORRECTED)}")
    table = []
    for r in results:
        w = warnings.get((r.get("mutant", ""), r.get("warning", ""))) if warnings else None
        grade, basis = corrected_grade(r, w)
        table.append({"mutant": r.get("mutant"), "warning": r.get("warning"),
                      "rule": r.get("rule"), "driver_E": r.get("E"),
                      "key": list(warning_key(r.get("mutant", ""), w)
                                  if w else ("?", "?", "?", "?")),
                      "ledger_E": grade, "basis": basis})
    return {"counts": dict(counts), "rows": table}


def load_warnings(path: str) -> dict[tuple[str, str], dict[str, Any]]:
    """Load a warnings file into {(mutant, warning id): warning object}."""
    import json as _json
    from pathlib import Path as _Path
    items = _json.loads(_Path(path).read_text())["items"]
    return {(i["mutant"], i["warning"]["id"]): i["warning"] for i in items}


def mint_successes(report: dict[str, Any]) -> list[bool]:
    """Per-mint success flags from a replay report's steps."""
    out = []
    for step in report.get("steps", []):
        for key, value in step.items():
            if key.startswith("mint_") and isinstance(value, dict):
                out.append(value.get("status") in ("0x1", "success"))
    return out


def revert_reasons(report: dict[str, Any]) -> dict[str, str]:
    """Mint-tagged revert reasons from a replay report."""
    reasons = {}
    for entry in report.get("reverts", []):
        if isinstance(entry, dict):
            reasons.update(entry)
    for key, value in report.items():
        if key.startswith("revert_") and isinstance(value, str):
            reasons[key] = value[:200]
    return reasons
