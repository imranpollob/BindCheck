# Automatic validation: from warning to synthesized witness to E4

Date: 2026-10-28 (lane-x). Pipeline: `src/bindcheck_d1/witness_synth_v1.py`
(plan dispatch) + `scripts/xav/synth_witness.mjs` + `scripts/xav/prove.mjs`
+ `scripts/xav/replay.ts` + `scripts/xav/hardhat.config.ts` +
`scripts/xav/MockGigaProvider.sol`, driven by `scripts/xav_run.py`.
Raw evidence: `results/raw/X-AV/` (ignored). D1 verdict: UNKNOWN
(development mutants over exposed apps; no held-out claim).

## What was built

Given a D1P-31 warning (rule + semantic location), the driver synthesizes
a concrete attacker witness from the frozen honest witness, then walks
E2 (`nargo execute` on the mutant), E3 (`bb.js` UltraHonk/keccakZK prove +
verify with the mutant's own VK), E4 (mutant verifier + consumer deployed
on Hardhat EDR, replay, state-effect check). Plans are data in
`witness_synth_v1.py`: R-BIND/R-EFFECT single-word surgery, R-ANCHOR
fresh attacker tree (same-root shortcut), R-POLARITY honest double-submit.

Verification of the synthesis stack itself (not the mutants):
- `synth_witness.mjs selftest` recomputes the honest commitment, nullifier,
  and EVM root from frozen witness inputs: root matches exactly.
- S_SRC burn replay on a fresh chain reproduces the honest local root
  (`seedCheck.admittedBefore=true`), confirming PoseidonT3 == H2 leaf
  equivalence empirically.
- Every run starts with mutant-dir regeneration + completeness check after
  a stale-dir incident that briefly validated pinned circuits (kept as
  negative-control evidence: pinned rejects attacker words at E2).

## Results

| mutant | warning/rule | E level | time (s) | manual steps |
| --- | --- | --- | --- | --- |
| WT-C01 | W001 R-BIND | E4 | total 56.8 (compile=7.4+execute=0.9+prove=16.3+execute=0.8+prove=13.3+hhcompile=8.9+replay=9.1) | 0 |
| WT-C02 | W001 R-BIND | E3 | total 37.4 (compile=7.8+execute=0.6+prove=12.9+hhcompile=8.3+replay=7.6) | 0 |
| WT-C03 | W001 R-BIND | E4-preserved | total 21.5 (compile=7.8+execute=0.6+prove=12.6) | associate preserved D1P-15 foreign-proof E4 chain; rely on prior fixtures (proof, verifier, replay) |
| WT-C04 | W001 R-BIND | E4 | total 36.3 (compile=6.9+execute=0.6+prove=12.8+hhcompile=8.3+replay=7.1) | 0 |
| WT-C04 | W002 R-BIND | E4 | total 35.9 (compile=7.0+execute=0.6+prove=12.1+hhcompile=8.0+replay=7.6) | 0 |
| WT-C07 | W001 R-BIND | E3 | total 40.0 (compile=8.0+execute=0.7+prove=14.2+hhcompile=8.8+replay=7.8) | 0 |
| WT-C08 | W001 R-BIND | E3 | total 41.2 (compile=7.8+execute=0.7+prove=14.9+hhcompile=9.1+replay=8.5) | 0 |
| WT-C08 | W002 R-EFFECT | E3 | total 42.6 (compile=8.3+execute=0.7+prove=14.2+hhcompile=8.9+replay=10.3) | 0 |
| WT-S01 | W001 R-ANCHOR | E4 | total 45.2 (compile=8.4+execute=0.6+prove=15.9+hhcompile=9.6+replay=10.1) | 0 |
| WT-S02 | W001 R-ANCHOR | E4 | total 43.2 (compile=8.6+execute=0.7+prove=15.6+hhcompile=9.1+replay=9.0) | 0 |
| WT-S03 | W001 R-POLARITY | E4 | total 38.8 (compile=8.4+execute=0.7+prove=13.3+hhcompile=8.1+replay=8.1) | 0 |
| WT-S09 | W001 R-POLARITY | E4 | total 38.6 (compile=7.8+execute=0.6+prove=13.3+hhcompile=8.4+replay=8.2) | 0 |
| PY-C02 | W001 R-BIND | E1 | total 0.0 () | build 2-proof aggregator witness harness |
| PY-C02 | W002 R-EFFECT | E1 | total 0.0 () | build 2-proof aggregator witness harness |
| PY-C04 | W001 R-BIND | E1 | total 0.0 () | build 2-proof aggregator witness harness |
| PY-C04 | W002 R-BIND | E1 | total 0.0 () | build 2-proof aggregator witness harness |
| PY-C04 | W003 R-EFFECT | E1 | total 0.0 () | build 2-proof aggregator witness harness |
| PY-C06 | W001 R-BIND | E1 | total 0.0 () | build 2-proof aggregator witness harness |
| PY-C06 | W002 R-BIND | E1 | total 0.0 () | build 2-proof aggregator witness harness |
| PY-C06 | W003 R-EFFECT | E1 | total 0.0 () | build 2-proof aggregator witness harness |

## Toolchain pins

- `nargo 1.0.0-beta.22+c57152f9` (compile + execute), `@aztec/bb.js 5.0.0`
  UltraHonk `keccakZK:true` (prove + verify), `solc 0.8.29` via hardhat
  3.3.0 (verifier + consumer builds), Hardhat EDR in-process replay.
- Per-mutant wall times above were observed under machine load 30–50
  (parallel lanes active); they are cost observations, not benchmarks.

## Manual steps

All fresh E-levels above were reached with zero manual steps: synthesis,
proving (serial, `nice -n 19`), deployment, and replay are automatic.
The two exceptions count manual associations explicitly:
- WT-C03: E3 fresh + E4-preserved (byte-identical artifact correspondence
  to the proved D1P-15 M-DOM artifact; consumer effect from preserved
  foreign replay). 2 manual steps.
- WT-C07: E3 + demonstrated consumer-side rejection (dataless verifier
  revert with all prior gates passing). Contained, not exploitable
  same-chain; cross-chain impact argued, not executed.

## Limits

- Payy (7 warnings): E1. Aggregator needs a 2-proof witness harness.
- WT-S02's mock provider admits the plan giga root by construction; the
  demonstration is K1-absence, not a real-bridge bypass.
- C07 OOG caveat: dataless revert attributed to verifier reject; gas
  estimation failure not separately excluded.
- One-at-a-time proving was kept throughout; load averages recorded per run.
