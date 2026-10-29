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

## Results — v1 (D1P-31, history)

The v1 table below is preserved unchanged as history.

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

## Results — v1.1 (D1P-34, 53 warnings)

Date: 2026-10-28 (lane-x). BindCheck v1.1 frozen (`bindcheck-v1.1`);
frozen files untouched. Rule identities changed vs v1: missing-anchor
cases now emit R-CONSUMER (WT-S01/S02/S03); new detections WT-S06
(max_fee unbound), PY-S01, PY-S02. Plans dispatch by warning shape
(rule + location + evidence path spelling), not mutant name
(`witness_synth_v1.plan_for`). Payy consumer rows run the new
mock-verifier harness (`scripts/xav/payy_replay.ts` + `XAVProxy.sol` +
driver `run_payy`): pinned solc 0.8.20, anvil, ERC1967-style proxy,
ECDSA validator signatures; MockVerifier stands in for proof acceptance,
so these rows cap at E2 (mock-verifier-scoped), never E4. Raw evidence:
`results/raw/X-AV/v11/` (+ `v11-fix/` correction run; `v11-probe/`
harness development). Start load 8.50; serial, `nice -n 19`, no competing
lane provers. D1 verdict: UNKNOWN (development mutants, exposed apps).

| target | warning/rule | E level | time (s) | manual steps |
| --- | --- | --- | --- | --- |
| WT-C01 | W001 R-BIND | E4 | total 26.2 | 0 |
| WT-C02 | W001 R-BIND | E3 | total 18.0 | 0 |
| WT-C03 | W001 R-BIND | E4-preserved | total 11.7 | associate preserved D1P-15 foreign-proof E4 chain; rely on prior fixtures (2 steps) |
| WT-C04 | W001 R-BIND | E4 | total 17.3 | 0 |
| WT-C04 | W002 R-BIND | E4 | total 18.1 | 0 |
| WT-C07 | W001 R-BIND | E3 | total 18.7 | 0 |
| WT-C08 | W001 R-BIND | E3 | total 19.4 | 0 |
| WT-C08 | W002 R-EFFECT | E3 | total 20.7 | 0 |
| WT-S01 | W001 R-CONSUMER | E4 | total 18.7 | 0 |
| WT-S02 | W001 R-CONSUMER | E4 | total 19.1 | 0 |
| WT-S03 | W001 R-CONSUMER | E4 | total 19.4 | 0 |
| WT-S06 | W001 R-CONSUMER | E4 | total 19.3 | 0 |
| WT-S09 | W001 R-POLARITY | E4 | total 19.9 | 0 |
| PY-S01 | W002 R-EFFECT :842 | E2 (mock-verifier-scoped) | replay 1.5 | 0; unregistered mint settled |
| PY-S01 | W004 R-POLARITY :357 | E2 (mock-verifier-scoped) | replay 0.9 | 0; unregistered mint settled |
| PY-S02 | W002 R-EFFECT :850 | E2 (mock-verifier-scoped) | replay 1.1 | 0; registered mint settled twice |
| PY-S02 | W004 R-POLARITY :357 | E2 (mock-verifier-scoped) | replay 1.1 | 0; registered mint settled twice |
| PY-S03 | W002 R-EFFECT :851 | E2 (mock-verifier-scoped) | replay 1.1 | 0; burn paid noteKind-derived address, recipient 0 |
| PY-S04 | W002 R-EFFECT :853 | E2 (mock-verifier-scoped) | replay 1.0 | 0; dead kind-4 settled as burn, recipient +1000 |
| PY-C01/C03/C04/C05/C06/C07, PY-S05 | all R-BIND/R-EFFECT/R-CONSUMER (23 rows) | E1 | compile-only | real inner-proof vector (Rust stack) |
| PY-S01/S02 | W001 R-BIND, W003 R-CONSUMER (4 rows) | E1 | compile-only | real inner-proof vector (Rust stack) |
| PY-S03/S04 | W001 R-BIND, W003 R-CONSUMER (4 rows) | E1 | compile-only | real inner-proof vector (Rust stack) |
| PY-C02 | W001 R-BIND circuit | E4 | replay 10.0 (+ agg_final prove ~15, solc 3.5) | 0; forged burn words proved through mutant agg_agg→agg_final chain, verified onchain, acted on by consumer (see W002) |
| PY-C02 | W002 R-EFFECT :850 | E4 | replay 10.0 | 0; real mutant verifier + pinned consumer on anvil: block settles, forged kind-3 burn pays 7 MockUSDC to 0xdead (0→7), rollup 100→93; pinned-keyed verifier rejects same block (`SumcheckFailed()`); zero mock components on proof path |
| PY-C02 | W003 R-CONSUMER :357 commit_hash | E1 | n/a | by-design offchain (Celestia) commitment; no experiment |

Counts: 53 rows — E4: 10, E4-preserved: 1, E3: 4, E2 (mock-verifier-scoped):
6, E1: 32 (23 circuit rows for other mutants + 4 S01/S02 mint shapes + 4
S03/S04 shapes + C02 W003 by-design commit_hash). All E-levels with zero
manual steps except the counted WT-C03 association (2 steps). One
honesty note: the TE04 replay ran at default priority (oversight; load
~5.6, serial, no competing lane provers); the bb re-prove was repeated
under `nice -n 19` and verifies with identical public inputs.

TC02 real-proof vector (evidence `results/raw/TC02/`, ignored; script
`payy-harness/tc02_tail.rs` tracked): mutant checkout = pristine c4d2c90
copy + PY-C02 `main.nr` (diff: exactly the `:74` export assert removed);
pinned nargo beta.14 compile; `bb write_vk` ultra_honk (CRS generated
locally, no network); mutant fixtures swapped; cold cargo build 489 s
(1.91.0, `--locked` accepted); harness proves real utxo→agg_utxo→agg_agg
chain then control / tail-burn@4-8 / active-attacker-mint@0-3. Mutant:
all three prove + natively verify (active public inputs carry the
attacker hash exactly; independent `bb verify` exit 0 "Proof verified
successfully"; 1-bit tamper → `Sumcheck failed` exit 1). Pristine pinned
contrast (second cold build 590 s): control/tail verify, active candidate
rejected at ACVM witness generation, 0.0 s, `Assertion failed: proof
message must be exported`, `main.nr:74:24` — the removed line. Incident:
first active hash `0xabab..ab` exceeded the BN254 modulus and ACVM
reduced it mod p (diagnosed from public inputs, fixed to low-byte
pattern, re-ran). Disk-full incident: two cargo targets filled the disk;
deleted both regenerable dirs (mutant evidence already captured),
rebuilt pinned with 9.1 G free.

TE04 E4, zero mock components on the proof path (scripts
`te04_part1.sh` + `te04_part2.py` + `scripts/xav/te04_replay.ts`;
evidence `results/raw/TE04/`, ignored; inputs under `build/TE04/`,
ignored): mutant-keyed agg_final (constant set to the mutant agg_agg VK
hash; flags `--scheme ultra_honk --oracle_hash keccak` per the repo's
generator) proves the TC02 tail-candidate inputs; native verify exit 0.
`bb write_solidity_verifier` for mutant and pinned keys (solc 0.8.29
runs=1 legacy: runs=200 output exceeds EIP-170; consumer stack stays on
pinned solc 0.8.20; `HonkVerifier` implements `IVerifier` directly;
`ZKTranscriptLib` deployed and linked). Anvil replay: MockUSDC (synthetic
asset), both verifiers, pinned RollupV1 behind XAVProxy, synthetic
validator key in `initialize`, honest mint registered (100). Mutant block
settles (height 1): mint spent, forged kind-3 burn pays 7 to 0xdead
(0→7), rollup 100→93. Same block under the pinned-keyed verifier reverts
inside the verifier: `SumcheckFailed()` (`0x9fc3a218`). Debugging trail:
TOML hex must be quoted (nargo parses bare `0x` as i64); `bb prove`
needs `-k` (own key); witness file is `target/agg_final.gz`; proof
bytes→fields is plain 32-byte chunking (`bytes_to_elements`); verifier
needs the proof note-kind as the consumer's kind (registered token).

## Toolchain pins

- `nargo 1.0.0-beta.22+c57152f9` (compile + execute), `@aztec/bb.js 5.0.0`
  UltraHonk `keccakZK:true` (prove + verify), `solc 0.8.29` via hardhat
  3.3.0 (verifier + consumer builds), Hardhat EDR in-process replay.
- v1.1 additions: pinned `solc 0.8.20` standard-json (Payy consumer +
  mocks + XAVProxy), `anvil` (foundry 1.4.1) local chain, ECDSA validator
  signatures over the raw `getSignatureMessageHash`, MockVerifier scoping
  (project's own `eth/test` pattern). `nargo beta.14+60ccd48e`,
  `bb 3.0.0-manual.20251030` used for the bounded PY-C02 probe only.
- Per-mutant wall times above were observed under machine load 30–50
  (v1; parallel lanes active); v1.1 WarpToad rows under load ~8.5 with no
  competing lane provers. Times are cost observations, not benchmarks.

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

- Payy v1.1 (40 warnings): 2 rows E4 (PY-C02, real verifier + pinned
  consumer, forged-burn drain demonstrated, pinned contrast
  `SumcheckFailed`); 6 rows E2 (mock-verifier-scoped) with unauthorized
  effects on state; 32 rows E1 (23 circuit rows owing Rust-stack inner
  proofs, 8 S01/S02/S03/S04 non-mint shapes, C02 W003 by-design offchain
  commit_hash). The mock stands in for proof acceptance, which is
  orthogonal to the demonstrated consumer defects.
- The validation harness is per-application, not generic: WarpToad rows
  use nargo/bb.js UltraHonk + Hardhat-EDR plans dispatched by warning
  shape; Payy consumer rows use the solc/anvil mock-verifier harness;
  Payy circuit rows use the Rust-stack real-proof route (TC02/TE04).
  Porting to a new application means writing a new consumer/circuit
  adapter, not flipping a switch; the E-level ladder and evidence rules
  are the reusable part.
- Cross-contamination incident (caught before reporting): shape dispatch
  initially sent PY-S01/S02 R-POLARITY rows down the WarpToad replay path
  and graded them E3 off WarpToad artifacts. Fixed by routing all PY-*
  rows to `run_payy` first (`v11-fix/` correction run re-graded them E2);
  the bogus E3s never left the worktree.
- v1 Payy (7 warnings): E1. Aggregator needs a 2-proof witness harness.
- WT-S02's mock provider admits the plan giga root by construction; the
  demonstration is K1-absence, not a real-bridge bypass.
- C07 OOG caveat: dataless revert attributed to verifier reject; gas
  estimation failure not separately excluded.
- One-at-a-time proving was kept throughout; load averages recorded per run.
