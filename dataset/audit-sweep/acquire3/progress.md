# Acquisition pass 3 (delta): progress

**Date:** 2026-11-23. **Output:** `acquisition.csv` (17 rows, the same schema as pass 2). **Status:** complete.

| Source | Rows | PINNED-PAIR | PINNED | PARTIAL | PRIVATE-OR-MISSING |
|---|---|---|---|---|---|
| Quantstamp Hinkal 2023 | 8 | 0 | 0 | 0 | 8 |
| Quantstamp Hinkal 2026 | 6 | 0 | 0 | 6 | 0 |
| Quantstamp Datachain zkDCAP | 2 | 2 | 0 | 0 | 0 |
| Hacken Zilliqa | 1 | 0 | 0 | 1 | 0 |
| **Total** | **17** | **2** | **0** | **7** | **8** |

**Fix confidence:**

| Fix confidence | Rows |
|---|---|
| `named-in-report` | 14 |
| `none-found` (acknowledged, unfixed) | 3: G0639, G0642, G0652 |

Of the 14 `named-in-report` fixes, 3 resolve publicly (zkDCAP ×2, Zilliqa). The other 11 are Hinkal SHAs that cannot be resolved.

**Triage of the delta rows:** see `triage/triage_delta.csv`, which has 11 BORDERLINE rows: LB 0, LN 1, U 10.
