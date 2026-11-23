# Validation sample of LIKELY-NOT triage rows

**Date:** 2026-11-23. **Source:** `triage/triage.csv`, sha256 `a5ae1556b2791985dea8a6eb73036023ad75c6ad9ad8d051ee84c85c0fae82c1`. It has 201 rows, of which 49 are `LIKELY-NOT`.

Human raters label every `LIKELY-BINDING` (86) and `UNSURE` (66) row, plus the 13 `LIKELY-NOT` rows sampled below. The triage miss rate is the share of these 13 that humans label binding, reported with a Wilson interval. If it exceeds 10%, humans label all 49 `LIKELY-NOT` rows (TRIAGE.md, "Validation").

## Procedure (reproducible)

- **Seed:** `20261123`
- **Population:** n = 49 `LIKELY-NOT` finding_keys, sorted alphabetically (Python default string order).
- **Sample size:** k = ceil(0.25 × 49) = 13. Rounding up is a choice made here; TRIAGE.md does not fix the rounding rule.
- **Interpreter:** CPython 3.12.3 (`random.sample`, Mersenne Twister). Keys are listed in draw order.
- **Draw time:** after the final triage revision (the uniform trust and skipped-verification rules in notes.md). An earlier provisional draw, made before that revision, was discarded.

```python
import csv, math, random
rows = list(csv.DictReader(open("triage/triage.csv")))
ln = sorted(r["finding_key"] for r in rows if r["triage"] == "LIKELY-NOT")
k = math.ceil(0.25 * len(ln))          # 13
random.seed(20261123)
sample = random.sample(ln, k)
```

## Sampled finding_keys (13)

| # | finding_key | group_id |
|---|---|---|
| 1 | `zksecurity-openvm-2026-06-08` | G0133 |
| 2 | `veridise-succinct-sp1-call-contract-2025-07-V-SP1CC-VUL-013` | G0398 |
| 3 | `zellic-nori-bridge-2026-07-3.3` | G0362 |
| 4 | `veridise-risczero-boundless-2025-04-V-BML-VUL-005` | G0370 |
| 5 | `openzeppelin-jovay-rollup-contracts-2025-10-T-layer-chainid` | G0498 |
| 6 | `openzeppelin-linea-prover-2024-06-T-verifier-regress` | G0464 |
| 7 | `veridise-semaphore-2023-01-V-SEM-VUL-009` | G0544 |
| 8 | `hexens-avacloud-circuits-audit-2025-04-ETRP-18` | G0541 |
| 9 | `veridise-risczero-steel-2024-10-V-STL-VUL-004` | G0409 |
| 10 | `tob-succinct-2023-02-4` | G0448 |
| 11 | `zellic-ibc-eureka-2025-03-3.1` | G0440 |
| 12 | `zellic-singularity-2024-04-3.10` | G0038 |
| 13 | `c4-succinct-2025-09-M-01` | G0191 |
