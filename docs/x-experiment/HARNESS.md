# Validation-harness architecture: core vs per-application adapters

Date: 2026-10-30 (lane-x-muse). The E-level ladder and evidence rules are
the reusable part; everything else is per-application. Porting to a new
application means writing a new adapter, not flipping a switch.

## Reusable core (`src/bindcheck_d1/xav_core.py`)

- Evidence-ladder grades E0/E1/E2/E3/E4/E4-preserved with contract-§8
  definitions, plus the precise `E1+mock` relabel (mock-verifier rows do
  not meet E2).
- `corrected_grade` / `check_ledger`: deterministic adjudication of raw
  driver rows to ledger grades, asserting the corrected 53-warning totals
  (8 E4, 1 preserved, 5 E3, 6 E1+mock, 33 E1).
- Effect predicates: `mint_successes`, `revert_reasons` over replay
  reports. Verdicts (`VIOLATION` / `VERIFIED_WITHIN_SCOPE` / `UNKNOWN`)
  stay with the analysis layer, not the harness.

## Per-application adapters (not reusable)

| adapter | owns |
|---|---|
| `scripts/xav_run.py` `stage_build`/`run_one` + `plan_for` shapes | WarpToad nargo/bb.js-UltraHonk/Hardhat-EDR route, honest TOML, anchor/aztec synthesis |
| `scripts/xav_run.py` `run_payy`/`payy_experiments` | Payy solc-0.8.20/anvil mock-verifier consumer route (caps at E1+mock) |
| `scripts/te04_part2.py`, `scripts/te05_part2.py` + `te04/te05_replay.ts` | Payy real-verifier route (Rust-stack inner proofs in, bb Solidity verifier + pinned consumer on anvil) |
| `scripts/xav/repair_check.py` | per-row minimal-repair staging + attack-fails/honest-succeeds checks |
| `payy-harness/tc02_tail.rs` | Payy inner-proof witness construction (cargo/Rust stack) |

## What a new application requires

1. Frozen honest material: witness/inputs, artifact + verification key,
   admitted initial state, and a funded/registered baseline.
2. Shape-based synthesis plans (rule + location + evidence spelling,
   never mutant identity), written BEFORE unseen warnings are inspected;
   anything unconstructible reports E1 with the missing prerequisite.
3. A circuit route producing real proofs under the variant's own key
   (nargo/bb.js here; the app's own stack for others) with native verify
   + tamper control.
4. A consumer route deploying the UNCHANGED consumer from an admitted
   state and checking effects ON STATE (not log text).
5. A verifier strategy with matching keys per variant. A mock stands in
   for proof acceptance only with an E1+mock cap, self-labeling reports,
   and disclosure that E2 is not met.
6. Same-transaction original-vs-defective (+repaired) contrasts with
   matching keys and identical initial state; cross-key failure is not a
   contrast. Mock-seeded trusted history must be audited (cf. WT-S02).
7. A repair check per E4 row (attack fails + honest succeeds on the
   repaired target; remaining structural warnings reported, not hidden).
8. Policy scope in writing before judging effects (covered path vs
   faucet/dev affordances; legitimate substitute mechanisms excluded by
   checking they were inactive, not by assumption).
