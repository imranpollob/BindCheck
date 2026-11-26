# B3 static-tool results (frozen rule)

**TEST benchmark. Never share this file or its numbers with a tool-building lane.**

- Date: 2026-11-25
- Rule: `MATCHING.md`, frozen 2026-11-25T08:02:28Z (sha256 `8bea1697…0e36`, unchanged and matching `results/raw/B3/FREEZE-matching.txt`). No amendment was made.
- Scorer: `analyze_static.py` (sha256 `c7b3742e…bed`).
- Raw outputs (ignored, not committed):
  - `results/raw/B3/static-1/` holds the frozen run.
  - `results/raw/B3/static-1-mythril-diag/` holds the Mythril rerun with identical flags plus `-v 4`.
  - `results/raw/B3/static-1/analysis/*.tsv` holds the scored tables. sha256: `matches.tsv` `3731b262…e13`, `summary.tsv` `2d303ef7…02`, `false-alarms.tsv` `7c6e6f75…ae`, `targets.tsv` `69f9fb9c…ed`, `other-new.tsv` `97095afb…5e`.

## Main finding

**Mythril under the frozen settings analysed almost nothing.**
- 24 of the 26 Solidity mutant targets, and every clean host contract, are **unsupported**: Mythril never deployed the contract, so it never executed a function.
- The 2 runs that did deploy (DK-S01's withdraw verifier and DV-S05's DealVerifier) reached under 5% coverage with a single message-call iteration.
- The original logs show exit 0, `success: true` and 0 issues for all of them. That is **not** a clean result.

Neither a larger `--max-depth` nor a larger `--create-timeout` fixes contract creation, so this is not a resource limit (see "Limiter test").

## Tool versions and exact settings
| Tool | Version | Settings |
|---|---|---|
| Slither | 0.11.3 (pyenv 3.12.12) | default detectors, `--json`, `--filter-paths "node_modules\|lib/\|test\|mocks\|script"` (plus `certora` on xchain); per-host commands in `run_static.sh` |
| Mythril | 0.24.8 (`results/raw/B3/mvenv`) | see the next table |
| circomspect | `tools/circomspect-src` release build (no `--version` flag) | default level; zkerc20 `circuit.circom`; davinci `-L node_modules deal.circom partial.circom` |
| `nargo check` | 1.0.0-beta.22 | dark `--workspace` in `circuits/`; kakushi in `shielded_withdraw` |
| Picus | not run | no Racket runtime locally, so **unsupported** for every target |

All runs used `systemd-run --user --scope -p MemoryMax=8G`, one at a time.

Mythril settings, frozen (`MATCHING.md` §8). Defaults were read from `mythril/interfaces/cli.py` in the venv, not assumed.

| Setting | Value | Source |
|---|---|---|
| `--execution-timeout` | 300 s | set |
| `--max-depth` | 22 | set (Mythril default 128) |
| `--transaction-count` (`-t`) | 2 | Mythril default |
| `--create-timeout` | 30 s | Mythril default |
| `--solver-timeout` | 25000 ms | Mythril default for `analyze` |
| `--no-onchain-data`, `-o json` | — | set |
| outer wall clock | `timeout 420` | set |
| solc | per host via `--solv` (0.8.27 zkerc20, 0.8.28 dark/davinci/kakushi, 0.8.30 dark verifier, 0.8.34 xchain); remappings, viaIR and optimizer via `--solc-json` | `run_static.sh` |

## Mutants, per tool and pattern (raw counts; Wilson 95% on loose/supported)
Unsupported counts are split: `layer` means the tool cannot analyse that side (§3 gate); `run` means the analysis failed.

| Tool | Pattern | Supported | Loose | Strict | Mechanism | UNKNOWN | Unsupported (layer + run) | Loose 95% CI |
|---|---|---|---|---|---|---|---|---|
| Slither | P1 | 4 | 0 | 0 | 0 | 0 | 4 + 0 | 0.00–0.49 |
| Slither | P2 | 3 | 0 | 0 | 0 | 0 | 4 + 0 | 0.00–0.56 |
| Slither | P3 | 6 | 2 | 0 | 0 | 0 | 2 + 0 | 0.10–0.70 |
| Slither | P4 | 7 | 0 | 0 | 0 | 0 | 0 + 1 (DK-S01) | 0.00–0.35 |
| Slither | P5 | 5 | 0 | 0 | 0 | 0 | 1 + 0 | 0.00–0.43 |
| Mythril | P1 | 0 | 0 | 0 | 0 | 0 | 4 + 4 | – |
| Mythril | P2 | 0 | 0 | 0 | 0 | 0 | 4 + 3 | – |
| Mythril | P3 | 0 | 0 | 0 | 0 | 0 | 2 + 6 | – |
| Mythril | P4 | 2 | 0 | 0 | 0 | 0 | 0 + 6 | 0.00–0.66 |
| Mythril | P5 | 0 | 0 | 0 | 0 | 0 | 1 + 5 | – |
| circomspect | P1 | 3 | 0 | 0 | 0 | 0 | 5 + 0 | 0.00–0.56 |
| circomspect | P2 | 1 | 0 | 0 | 0 | 0 | 6 + 0 | 0.00–0.79 |
| circomspect | P3 | 1 | 0 | 0 | 0 | 0 | 7 + 0 | 0.00–0.79 |
| `nargo check` | P1 | 1 | 0 | 0 | 0 | 0 | 7 + 0 | 0.00–0.79 |
| `nargo check` | P2 | 2 | 1 | 0 | 0 | 0 | 5 + 0 | 0.09–0.91 |
| `nargo check` | P3 | 1 | 0 | 0 | 0 | 0 | 7 + 0 | 0.00–0.79 |
| Picus | all | 0 | 0 | 0 | 0 | 0 | 0 + 5 Circom `-C` (no runtime), 32 layer | – |

circomspect and `nargo check` support no P4 or P5 mutants. No static tool supports `XC-G01` or `XC-G02` (§3).

Mutant-level results:
- **Loose matches:**
  - Slither ZK-S01: new `uninitialized-state` in `TransactionKeeper._checkProof`.
  - Slither KK-S03: new `uninitialized-state` in `KakushiPool._spend`.
  - `nargo check` KK-C02: new `unused variable commitment` at the edited line 68.

  None is on the pre-registered mechanism list, so none is strict.
- **No strict and no mechanism-level hit** for any tool on any mutant.
- **Slither DK-S01** is unsupported: Slither crashes on the Honk withdraw verifier (an `AssertionError` in constant folding) on both the clean and mutant trees, and the edit is in that verifier. The DarkVault part ran on both trees (added this session) and has no new warning.
- **Mythril DK-S01 and DV-S05** are supported but `none`, under the frozen rule. Their runs had 1 open state after creation, 1 message-call iteration, and 2.4–4.8% coverage. A `none` from runs this shallow is weak evidence. DK-S01's DarkVault part never deployed (see the next table).

Other new warnings (`other-new.tsv`) are listed and pending human triage; they are not dropped.
- Slither `uninitialized-state` (ZK-S01 file-level; KK-S03 file-level and `isSpent`).
- circomspect unused-signal warnings: ZK-C01 line 14 (`sender` is now unused), ZK-C03 lines 34 and 52, ZK-C04 line 25, DV-C01 line 130.
- nargo `unused variable` on DK-C01, DK-C02, KK-C01 and KK-C02.

Several of the circomspect ones look like direct symptoms of the mutation, but they are outside the ±3-line window. They are also on the P2 list, while those mutants are P1 or P3, so under the frozen rule they are neither loose nor mechanism-level. This is recorded rather than re-scored.

## Mythril per-target creation status and coverage
Creation status and coverage come from the `-v 4` rerun with identical analysis flags. The issue sets of the rerun match the original run on all 38 originally run targets. Coverage lists the % reported per bytecode, in log order. Targets that were never run by design (non-edited parts) are omitted.

| Target | Seconds | Contract created | Open states after creation | Msg-call iterations | Coverage % | Status |
|---|---|---|---|---|---|---|
| `CLEAN-zkerc20` | 47 | NO | 0 | 0 | 1.98/1.27/1.71 | unsupported |
| `ZK-S01`..`ZK-S05`, `ZK-D01` | 46–49 | NO | 0 | 0 | 1.98/1.27/1.71–1.72 | unsupported |
| `CLEAN-dark` | 9 | NO | 0 | 0 | 4.59 | unsupported |
| `DK-S01` (DarkVault, added) | 9 | NO | 0 | 0 | 4.59 | unsupported |
| `DK-D01` | 10 | NO | 0 | 0 | 4.60 | unsupported |
| `CLEAN-dark@verifier` | 67 | yes | 1 | 1 | 1.68/2.61 | ok |
| `DK-S01@verifier` | 31 | yes | 1 | 1 | 2.41/4.81 | ok |
| `CLEAN-davinci` | 63 | NO | 0 | 0 | 0.93/0.26/1.26 | unsupported |
| `DV-S01`..`DV-S04` | 61–62 | NO | 0 | 0 | 0.93/0.26/1.26 | unsupported |
| `CLEAN-davinci@dealverifier` | 34 | yes | 1 | 1 | 0.28/2.85 | ok |
| `DV-S05@dealverifier` | 34 | yes | 1 | 1 | 0.28/2.85 | ok |
| `CLEAN-kakushi` | 21 | NO | 0 | 0 | 2.93/1.64 | unsupported |
| `KK-S01`..`KK-S08` | 21–22 | NO | 0 | 0 | 2.93–2.97/1.64 | unsupported |
| `CLEAN-xchain` (Connector) | 10 | NO | 0 | 0 | 2.17 | unsupported |
| `XC-S01`..`XC-S07` (Connector; XC-S04 added) | 9–10 | NO | 0 | 0 | 2.17–2.30 | unsupported |
| `CLEAN-xchain@adapter` | 4 | NO | 0 | 0 | 21.96 | unsupported |
| `XC-S04@adapter` | 3 | NO | 0 | 0 | 26.09 | unsupported |
| `XC-S07@adapter` | 4 | NO | 0 | 0 | 22.74 | unsupported |
| `XC-D01@adapter` | 4 | NO | 0 | 0 | 22.74 | unsupported |

**Fast xchain runs (3–10 s), listed explicitly:**
- Connector: `CLEAN-xchain` and `XC-S01`..`XC-S07`.
- Adapter: `CLEAN-xchain@adapter`, `XC-S04@adapter`, `XC-S07@adapter` and `XC-D01@adapter`.

All of them failed contract creation. The dark DarkVault runs (9–10 s) failed the same way. They were fast because nothing was explored, not because a timeout cut exploration short.

### Limiter test (post-hoc, diagnostic only; not scored)
`CLEAN-xchain@adapter` was rerun with one flag changed at a time (`results/raw/B3/static-limiter/`):
- `--max-depth 128`: still no contract created, 4 s, coverage 21.96%.
- `--create-timeout 120`: still no contract created, 4 s, coverage 21.96%.

Creation ends after about 100 instructions in under 1 s. A higher execution timeout (as t3z asked) therefore cannot change the outcome. The cause is under investigation; see "Post-hoc arm" below.

## Detecting a vacuous Mythril run
Exit code, `success: true` and `"issues": []` do not show that anything was analysed. The signature appears only at verbosity `-v 4` or higher (`myth -v 4 analyze …`). At default verbosity the warning is not printed, so **default-verbosity logs cannot be classified after the fact**.

Vacuous (no contract deployed, so no function executed):
```
mythril.laser.ethereum.svm [INFO]: Finished contract creation, found 0 open states
mythril.laser.ethereum.svm [WARNING]: No contract was created during the execution of contract creation Increase the resources for creation execution (--max-depth or --create-timeout) ...
```
Weak (deployed but shallow): `found 1 open states` followed by only `Starting message call transaction, iteration: 0`, together with low `Achieved N% coverage for code: …` lines.

One-line classifier for a directory of Mythril logs (B1, B2, test set). Replace `DIR`:
```sh
for f in DIR/*.log; do if grep -q -e 'No contract was created' -e 'found 0 open states' "$f"; then echo "VACUOUS $f"; elif grep -q -E 'found [1-9][0-9]* open states' "$f"; then echo "DEPLOYED $f $(grep -c 'iteration:' "$f") iterations"; else echo "UNCLASSIFIABLE(no -v4) $f"; fi; done
```
`UNCLASSIFIABLE` means the log was written below `-v 4`. Rerun that target with the same flags plus `-v 4` before reading its result.
`analyze_static.py --mythril-log DIR` applies this automatically and scores a no-creation run as `unsupported:no-contract-created`. Under §3 that is an analysis failure: unsupported, never a miss, never "0 findings".

**B2 and the test-set Mythril runs:** their logs were written at default verbosity, so whether they are vacuous is **UNKNOWN**. Each needs a `-v 4` rerun with its own frozen flags before its Mythril numbers can be read as anything but unsupported or unknown.

## Clean hosts and decoys (§5)
Binding warnings are detectors on any pattern's mechanism list. On decoys only new warnings are counted; on clean hosts the absolute count is reported.

| Tool | Target | Status | Binding warnings |
|---|---|---|---|
| Slither | CLEAN-zkerc20 | ok | 3: `unused-return` in `Node._commitment`, `Node._receiveMessage`, `TransactionKeeper._hash` |
| Slither | CLEAN-dark | DarkVault ok; verifier crashed | 0 (DarkVault part only) |
| Slither | CLEAN-davinci | ok | 6: `unused-return` in `CouncilCurve.add`, `CouncilCurve.mul`, `CouncilManager.deal`, `CouncilManager.submitPartial`, `CouncilManager.submitRequest`, `CouncilOps._freeze` |
| Slither | CLEAN-kakushi | ok | 2: `arbitrary-send-eth` in `KakushiPool.withdraw`, `missing-zero-check` in `PrivateCallExecutor.execute` |
| Slither | CLEAN-xchain | ok | 0 |
| Slither | decoys ZK-D01, DK-D01, XC-D01 | ok | 0 new each |
| Mythril | CLEAN-dark, CLEAN-davinci | host contract not deployed; verifier part ok | 0, **covering only the verifier part**; the host contracts are not measurable |
| Mythril | CLEAN-zkerc20, CLEAN-kakushi, CLEAN-xchain | no contract created | unsupported |
| Mythril | decoys ZK-D01, DK-D01, XC-D01 | no contract created | unsupported |
| circomspect | CLEAN-zkerc20 | ok | 2 (unused/unconstrained output at lines 108, 115) |
| circomspect | CLEAN-davinci | ok | 4 (`<--` at `deal.circom` 60 and 83; unused at 57 and 63) |
| circomspect | DV-D01 | ok | 0 new |
| `nargo check` | CLEAN-dark, CLEAN-kakushi | ok | 0 (no list, so no binding warnings possible) |
| `nargo check` | KK-D01 | ok | 0 binding; 1 new non-binding `unused variable` |

Decoy false-alarm rate:
- Slither: 0 of 3 supported decoys (Wilson 0.00–0.56).
- circomspect: 0 of 1.
- `nargo check`: 0 of 1.
- Mythril: no supported decoy.

**KB triage (§6): not performed.** Matching a warning to KB-1 or KB-2 needs the human triager, and AI output is not independent annotation. Candidates on the KB hosts:
- zkerc20 Slither `unused-return` ×3;
- xchain: none.

## How `analyze_static.py` differs from the B2 scorer
- It reads `make_mutants.py`'s v3 records.
- It adds the §2 accepted-locations table (`EXTRA_LOC`) and matches file basenames case-insensitively.
- It unions warnings over the analysis parts (xchain Connector + adapter; dark DarkVault + verifier; davinci CouncilManager + DealVerifier). Mutant status comes from the part that holds the edited file.
- It decides support from JSON `success` and, for Mythril, from creation status, not from exit codes. Slither's normal exit with findings is 255.
- It adds the mechanism-level column (§4) and §5 false alarms.
- The circomspect parser is general: any circuit file, with messages mapped to `CS-ASSIGN`, `CS-UNUSED` or `CS-OTHER`. P2's B2 list ("signal assignment `<--`, unused signals/outputs") maps to `CS-ASSIGN` and `CS-UNUSED`.
- Circuit delta: mutant warning lines are mapped back to baseline lines through the diff before the ±3 region compare, so a deletion does not make every later warning look new.

## Not done or limitations
- Picus was not run.
- KB triage is pending a human.
- The Slither dark verifier crash is a tool limitation.
- The circuit ±3 window and the frozen detector lists exclude several symptom-like circomspect warnings (listed above).
- Honest-path and kill-test status is in `README.md`.

## Post-hoc arm: Mythril on locally deployed contracts (NOT pre-registered)
This arm does not change the frozen result above. It was added after the frozen result was seen, at t3z's request, so that the baseline is not vacuous. It runs on a local Anvil node only (127.0.0.1:8545, Anvil test key #0); nothing touched a public network.

**Method.** The scorer and driver hashes were frozen at 2026-11-26T01:24:04Z, before any mutant run finished, in `results/raw/B3/static-2-mythril-anvil/FREEZE-scorer.txt`.
- **Deployment.** `anvil/deploy.py` resets Anvil, then deploys each target from the tree's own forge artifacts (`out/`), with constructor arguments, the same for clean and mutant.
  - Consumers are wired to `anvil/AcceptAll.sol`, a permissive stub that returns 1 for any call, for verifiers, hashers and the root oracle. dark uses its own `MockUSDG`.
  - Verifier contracts (dark Honk withdraw verifier, davinci DealVerifier, zkerc20 Groth16Verifier) are deployed and analysed standalone. The dark verifier is compiled with solc 0.8.30 (optimizer 200) and its libraries are linked and deployed.
  - zkerc20's `ZKERC20` is created by `Node` and analysed at its own address.
- **Analysis.** `anvil/run_mythril.py` runs `myth -v 4 analyze -a ADDR --rpc 127.0.0.1:8545 --execution-timeout 300 --max-depth 128 -t 2 -o json` under `timeout 420` and `MemoryMax=8G`.
  - These are Mythril's default depth and transaction count. It is not run with `--no-onchain-data`, because it must read the local chain.
  - Anvil runs as `anvil --host 127.0.0.1 --port 8545 --chain-id 31337 --disable-code-size-limit --gas-limit 100000000`.
  - It makes one fresh deployment per analysed part. Each clean host is run twice (`CLEAN-<host>#2`) to measure run-to-run noise.
- **Scoring.** Scored by `anvil/analyze_anvil.py`: mechanism-level plus the raw new-issue delta against the union of the two clean runs. Issues are keyed by (part, SWC, entry-point function). Loose and strict are **not computable**: GT functions are often internal, and address mode has no source map.
- **Probe (CLEAN-xchain Connector).** At depth 22, 16.5% coverage and 10 issues in 36 s. At depth 128, 42.6% coverage and 17 issues in 313 s. Under the frozen run the same contract never deployed, at 2.2% coverage.

**Results (post-hoc; finished 2026-11-26 UTC, 53 of 53 runs, 0 deploy failures).** Output: `results/raw/B3/static-2-mythril-anvil/analysis/{summary,mutants,targets,noise,false-alarms}.tsv`.
- **Mechanism-level: 0 of 26** Solidity mutants. All 26 are supported (deployed, success, ≥1 message call).

  | Pattern | Supported | Mechanism-level | Any new issue | Wilson 95% (mech) | Finished under budget | Reached 300 s budget |
  |---|---|---|---|---|---|---|
  | P1 | 4 | 0 | 0 | 0.00–0.49 | 3 | 1 |
  | P2 | 3 | 0 | 0 | 0.00–0.56 | 1 | 2 |
  | P3 | 6 | 0 | 0 | 0.00–0.39 | 2 | 4 |
  | P4 | 8 | 0 | 1 | 0.00–0.32 | 4 | 4 |
  | P5 | 5 | 0 | 0 | 0.00–0.43 | 4 | 1 |
  | **All** | **26** | **0** | **1** | 0.00–0.13 | 14 | 12 |

- **Raw new-issue delta:** 1 new issue in 26 mutants. DK-S01 (DarkVault part) gains `SWC-101` (integer arithmetic) at entry point `ideal_warn_timed(uint256,uint128) or owner()`. That SWC is not on the frozen P4 list, so it is not a mechanism-level hit. Every other mutant reproduces its clean issue set exactly.
- **Run-to-run noise: 0.** Both clean runs of every host and part give identical issue sets (symmetric difference 0 on all 10 host/part pairs), and the coverage figures agree to within 0.1 points.
- **Clean and decoy false alarms:** 0 binding-list issues (SWC-104/105) on any clean host or part. Decoys: XC-D01 0 new issues, ZK-D01 0, DK-D01 0 binding-list and 1 non-binding new issue (the same DarkVault `SWC-101` as DK-S01, so it is not specific to the DK-S01 edit).
- **Coverage and iterations (per target in `analysis/targets.tsv`).**

  | Host / part | Clean coverage % | Mutant coverage % | Seconds |
  |---|---|---|---|
  | xchain Connector | 42.6 | 42.5–43.5 | 313–315 |
  | xchain RiscZeroAdapter | 76.8 | 77.1–96.9 | 24–30 |
  | kakushi KakushiPool | 20.9 | 20.1–21.1 | 24–25 |
  | davinci CouncilManager | 18.1 | 18.2–18.3 | 304 |
  | davinci DealVerifier | 3.7 | 3.7 | 303 |
  | dark DarkVault | 42.1 | 42.1 | 310 |
  | dark Honk verifier | 19.5 | 35.8 | 17–18 |
  | zkerc20 Node | 50.6 | — | 310 |
  | zkerc20 ZKERC20 | 52.7 | 52.7–53.2 | 121–135 |
  | zkerc20 Groth16Verifier | 90.3 | 90.0–91.3 | 59–67 |

- **Exploration depth (budget caveat).** `grep -H "Starting message call transaction, iteration" *.log` gives, per target, whether a second transaction started and with how many open states. Three groups:
  - **Two transactions explored, under budget (6 mutants):** XC-S04 (adapter, tx-2 states 1) and ZK-S01..S05 (ZKERC20 tx-2 states 2; Groth16Verifier tx-2 states 1). **0 mechanism-level of 6.**
  - **Under budget but one transaction only (8 mutants):** KK-S01..S08, and both clean kakushi runs. Each finishes in about 25 s and never starts a second transaction, so no first transaction ended in an open state. This is not a harness fault: on a fresh deploy, a plain `cast send` `deposit(bytes32)` with 1 ETH succeeds on Anvil (status 0x1). The dead end is in Mythril's exploration.
  - **Reached the 300 s execution budget (12 mutants):** XC-S01, XC-S02, XC-S03, XC-S05, XC-S06, XC-S07 (Connector: tx 2 started with 0 states), DV-S01..S05 (CouncilManager and DealVerifier: tx 2 never started) and DK-S01 (DarkVault: tx 2 with 0 states). The outer `timeout 420` never fired (no exit 124), so the frozen anvil scorer counts them as `ok`. Under MATCHING.md's rule that a timeout with no finding is UNKNOWN, their conservative reading is **UNKNOWN**.
  - This grouping is a post-hoc interpretation. The scorer was not changed: the sha256 of all four `anvil/` files still matches `FREEZE-scorer.txt` (checked after the run).
- **Other limitations.** The kakushi runs make only one message-call iteration. All consumers see a stub verifier that accepts everything, so any check that depends on a real verifier result is not exercised. Loose and strict matches are not computable in address mode.
- **Reading.** Deploying the targets fixes the frozen arm's support problem (26/26 deployed, 0 clean noise). Even so, Mythril reached a non-empty second transaction for only 6 of the 26 mutants, and found 0 of those 6 at mechanism level. The remaining 20 either ran out of budget (12, UNKNOWN) or never got past one transaction (8). The evidence that Mythril misses B3's binding mutants after a real exploration therefore rests on 6 mutants (Wilson 95% 0.00–0.39), not on 26.
