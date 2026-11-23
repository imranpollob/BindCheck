# Validation sample of LIKELY-NOT triage rows (delta)

**Date:** 2026-11-23. **Source:** `triage/triage_delta.csv`, sha256 `a6d32b90a965af1efa14e6d6e3fb19975bc67c08eb4b061abec0b8eb1abbf955`. It has 11 rows (the BORDERLINE rows with an empty flag in `merged/delta_candidates.csv`), of which 1 is `LIKELY-NOT`.

This sample is drawn separately from `triage/SAMPLE.md`, which is not modified. Human raters label every `UNSURE` delta row (10), plus the sampled `LIKELY-NOT` row below. There are no `LIKELY-BINDING` delta rows.

## Procedure (reproducible, same as SAMPLE.md)

- **Seed:** `20261123`
- **Population:** n = 1 `LIKELY-NOT` finding_key, sorted alphabetically (Python default string order).
- **Sample size:** k = ceil(0.25 × 1) = 1. Because of the ceiling, the sample is the whole population.
- **Interpreter:** CPython 3.12.3 (`random.sample`, Mersenne Twister).
- **Draw time:** after all 11 rows were final.

```python
import csv, math, random
rows = list(csv.DictReader(open("triage/triage_delta.csv")))
ln = sorted(r["finding_key"] for r in rows if r["triage"] == "LIKELY-NOT")
k = math.ceil(0.25 * len(ln))          # 1
random.seed(20261123)
sample = random.sample(ln, k)
```

## Sampled finding_keys (1)

| # | finding_key | group_id |
|---|---|---|
| 1 | `quantstamp-hinkal-protocol-2023-10-HNKL-30` | G0637 |

## Caveat on the trust rule

Two delta rows are owner-trust findings: G0629 (HNKL-7) and G0653 (HIN-12). The task brief said that admin or owner-trust issues are LIKELY-NOT under PROTOCOL v1.2. However:

- PROTOCOL.md v1.2 adds only the liveness, gas/memory, circuit-internal and off-chain DROP classes.
- The main pass applied Rule 9 (`triage/notes.md`), which rates such rows UNSURE (e.g. Railgun CVF-23, PrivacyBoost VK registry).

For consistency with `triage.csv`, both rows are UNSURE. If the author decides they should be LIKELY-NOT, the LN population becomes 3, k = ceil(0.75) = 1, and this draw must be redone.
