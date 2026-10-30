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

# Adjudicated corrections over the raw v1.1 driver grades. Keys are
# (mutant, warning id); values are the ledger grade with its basis.
# Everything not listed keeps the driver's grade (with the E1+mock rule).
OVERRIDES: dict[tuple[str, str], tuple[str, str]] = {
    ("PY-C02", "W001"): ("E3", "TE05: own-mutation mutant-keyed proofs "
                         "(inner slot 009 + final), original/repaired "
                         "ACVM rejection, onchain containment"),
    ("PY-C02", "W002"): ("E1", "TE05: same-transaction runs under both "
                         "keys revert at consumer message policy, zero "
                         "state change"),
    ("WT-S02", "W001"): ("E4", "corrected setup (honest-seeded mock): "
                         "mutant accepts unadmitted 0x1234, pinned reverts; "
                         "v1.1 run as-run was a setup artifact"),
}

# Corrected totals over the 53 v1.1 warnings (ledger section 2).
EXPECTED_CORRECTED = Counter({
    E4: 8, E4_PRESERVED: 1, E3: 5, E1_MOCK: 6, E1: 33,
})


def corrected_grade(row: dict[str, Any]) -> tuple[str, str]:
    """Return (grade, basis) for one raw driver result row."""
    key = (row.get("mutant", ""), row.get("warning", ""))
    if key in OVERRIDES:
        return OVERRIDES[key]
    if row.get("E") == "E2 (mock-verifier-scoped)":
        return (E1_MOCK, "mock stands in for proof acceptance; not contract E2")
    return (row.get("E", E1), "driver grade stands")


def ledger_counts(results: list[dict[str, Any]]) -> Counter:
    """Grade every row and count. Raises on unexpected grades."""
    counts: Counter = Counter()
    for row in results:
        grade, _ = corrected_grade(row)
        if grade not in EXPECTED_CORRECTED:
            raise ValueError(f"unexpected grade {grade!r} for {row.get('mutant')} {row.get('warning')}")
        counts[grade] += 0  # ensure key exists even at zero
        counts[grade] += 1
    return counts


def check_ledger(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Assert corrected counts match the ledger; return the graded table."""
    if len(results) != 53:
        raise AssertionError(f"expected 53 v1.1 warnings, got {len(results)}")
    counts = ledger_counts(results)
    if counts != EXPECTED_CORRECTED:
        raise AssertionError(f"corrected counts differ: {dict(counts)} != {dict(EXPECTED_CORRECTED)}")
    table = [{"mutant": r.get("mutant"), "warning": r.get("warning"),
              "rule": r.get("rule"), "driver_E": r.get("E"),
              "ledger_E": corrected_grade(r)[0], "basis": corrected_grade(r)[1]}
             for r in results]
    return {"counts": dict(counts), "rows": table}


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
