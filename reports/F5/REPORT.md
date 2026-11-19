# F5 — Reject missing or duplicate oracle policy rule ids (XR4-01)

**Status:** DONE. **Author:** the orchestrator (Claude Code, Claude Opus 5.5),
2026-11-18. Small fix made directly by the reviewer; to be checked by XR4.

## Change

`reports/XR4/GATE.md` (XR4-01): F4 keys single-use replay and obligation
accounting by rule `id`. Two rules sharing an id collapse into one attribution
and revive the XR3-01 false E4.

- `oracle/runner.py`: `_check_rule_ids`, called from `_validate_manifest`.
  Every rule in `protected_effects`, `required_obligations`,
  `protected_view_effects` and `view_obligations` needs a non-empty string id,
  unique across the whole policy. Otherwise `OracleError` before any command runs.
- `oracle/evm_runner.cjs`: `assertUniqueRuleIds`, the same rule, checked on the
  driver spec before any trial (defence in depth); exported for tests.
- `tests/oracle/test_oracle_gates.py`: 8 new tests (duplicate within a list,
  duplicate across lists, missing/empty/blank id, distinct ids accepted, every
  committed manifest validates, driver refuses duplicates).

## Evidence

| Check | Result |
|---|---|
| `python3 -m pytest tests/oracle -q` | 44 passed |
| Revert proof: Python check replaced by `pass` | 5 rejection tests fail; 3 accept tests pass |
| Revert proof: driver check neutered (scratch copy via `ORACLE_TEST_DRIVER`) | `test_xr4_01_driver_refuses_duplicate_ids` fails |
| `python3 -m oracle run` on a copy of `f4_mixed_rules` with B's id set to A's | refused: `policy rule id 'single_A' is used by both protected_effects[0] and protected_effects[1]` |
| End-to-end on local Anvil (no fork, no public RPC) with the new driver | ZKredential original `CALLER-attacker` E4, repaired none; RacePass original `FREE_ARG-credHash` E4, repaired none; synthetic replay `REPLAY` E4; AZ1 faulty `FREE_ARG-numRealRows` E4, fixed none; f4_mixed_rules none — all unchanged |

Raw outputs: ignored `results/raw/F4/F5-*`. The analyzer is untouched (freeze 3).
