# Recall card 23 — nightfall-nullifier-field-alias

`nightfall-nullifier-field-alias`

| Field | Value |
|---|---|
| Repository | EYBlockchain/nightfall |
| DSL (ledger) | Circom/Solidity or generated Groth16 verifier |
| Ledger pattern / impact | replay-key field alias / proof-to-execution mismatch |
| Class v1 → v2 | `integration` → `integration` |
| Vulnerable → fixed | MISSING (not-publicly-pinned) → MISSING (not-publicly-pinned) |
| Exposure | not exposed by C2 |
| L4 proposal | **DROP-CANDIDATE (source and pins MISSING)** |

## 1. Source report (verbatim)

> **MISSING** — https://github.com/EYBlockchain/nightfall/issues/95 returns HTTP 404 (repository not found via API or web on 2026-11-08); Wayback availability API returns no snapshot.

<sub>Source: MISSING</sub>

## 2. Vulnerable vs fixed code

_No pinned source revision: vulnerable and fixed code are **MISSING**._


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** unclear (source unavailable)
- **Consumer consequence:** unclear
- **Fix locus:** MISSING
- **P1–P5 mappable:** unclear (ledger pattern says P3-like field alias)
- **Research-contract scope:** unclear
- **Relational class:** VERIFIER-CONSUMER — as ledger pattern; source MISSING
- **Proposed expected pattern:** `P3`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `MISSING`
- **Location basis:** no pinned revision
- **Concerns:**
  - Primary source unreachable; vulnerable/fixed pins not-publicly-pinned; repository family is EVAL 'unavailable' in source-corpus-v2.

## 4. Reviewer decision

| Field | Fill in |
|---|---|
| Decision | ☐ ACCEPT  ☐ EDIT  ☐ DROP |
| Strict scope (keep / demote) | |
| expected_pattern (P1–P5 or NONE) | |
| expected_location_regex | |
| Accept candidate commit? (if shown) | ☐ yes ☐ no ☐ n/a |
| Reviewer | |
| Date | |
| Notes | |
