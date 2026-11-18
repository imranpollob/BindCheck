# S2a2 — Residual P5 false positives on pinned development code

Status: DONE

Verdict/outcome: Six reproduced P5 warnings now return `UNKNOWN`. W0658 remains `UNKNOWN` after the longer retry.

## What was done

- Reproduced six warnings at the recorded Set H locations using the unhinted harness invocation on the pinned checkouts. Copied the real source subsets and confirmed that each fixture produced the same set of distinct P5 violation messages at the same location before changing the analyzer.
- Fixed proof-only argument forwarding, required a recovered verifier arity for circuit-side count warnings, and limited prebuilt Circom artifact reuse to sibling R1CS/SYM pairs. Marked symbolic output extents incomplete until compilation resolves them.
- Repeated the unhinted runs and checked the exact target locations, including every retained triple at each location. The six rerun cards all remain unresolved at E1. No proof or consumer execution was performed.
- Changed `bindcheck_zk/analyzer.py`, `bindcheck_zk/circuits.py`, and `bindcheck_zk/solidity.py`. Added the regressions and pinned sources under `tests/s2a2/` and updated the living checkpoint.

AI disclosure: OpenAI Codex, GPT-6 family. The exact model variant was unavailable to the session. These checks do not constitute independent human annotation.

## Evidence

Base revision `c82eac653fd53daf71dc0eb013849f3be42dd1ba` on `sprint/S2a2`. The base analyzer hash was `754b8bb8a2fb241391980a9e59525f18aefbd6f96546e9fe43c78cb4bebff2ab`.

`python3 -m bindcheck_zk.freeze` exited 0 and computed the candidate hash `1f5342cdca3ce1ce1d31d4493ee0dd9c9a05da287c10cb3415f1fc13dbde90ed`. The per-file manifest is `results/raw/S2a2/candidate-hash.txt`. No freeze was declared.

Python 3.12.12, Git 2.43.0, and Linux Circom 2.1.9. The compiler binary SHA-256 is `1bacd5583e2cc79dc1e2deaefc9c7438f21957968651c5f93dc71073c58435e3`. The harness verified the pinned circomlib 2.0.5 tree at `d359bab216fc262b406f468d87774ec1b6661e4438b38851fcd6a0a2e1e8a57a` (144 files) before exposing it to the local checkouts.

Run these commands from the worktree root.

```sh
export BC=/home/pollmix/Coding/bc
export BINDCHECK_CIRCOM="$BC/BindCheck/tools/circom-2.1.9/target/release/circom"
export GIT_OPTIONAL_LOCKS=0 GIT_NO_LAZY_FETCH=1 GIT_ALLOW_PROTOCOL=file
python3 results/raw/S2a2/run_cards.py before
python3 results/raw/S2a2/run_cards.py before-long --only W0658 --long
python3 results/raw/S2a2/run_cards.py fixtures-before --fixtures --only W0016,W0220,W0253,W0333,W0349,W0461
python3 results/raw/S2a2/run_cards.py after --only W0016,W0220,W0253,W0333,W0349,W0461
python3 results/raw/S2a2/run_cards.py fixtures-after --fixtures --only W0016,W0220,W0253,W0333,W0349,W0461
python3 results/raw/S2a2/run_cards.py after-long --only W0658 --long
python3 results/raw/S2a2/replay_p5_tp.py
python3 results/raw/S2a2/run_full_dev.py --phase before --skip-fetch --analyze-jobs 3 --raw-task T24 \
  --checkout-root "$BC/BindCheck/feasibility/work/full-dev"
python3 results/raw/S2a2/run_full_dev.py --phase after --skip-fetch --analyze-jobs 3 --raw-task T24 \
  --checkout-root "$BC/BindCheck/feasibility/work/full-dev"
python3 -m unittest tests.test_bindcheck_zk_cli tests.test_bindcheck_zk_controls \
  tests.soundness.test_verdict_soundness tests.soundness.test_followup \
  tests.coverage.test_rules tests.freeze2.test_p4_key tests.s2a.test_precision_fixes \
  tests.s2a2.test_residual_p5 -v
git diff --check
```

- The short card runs use `eval/run_heldout.py::prepare_pinned_vendor` and `run_tool_once` to invoke `./bindcheck-zk analyze <absolute-checkout>` at 150 s with the harness environment. They run only the BindCheck analyzer and use `reports/S2a/revision1_analysis.py::match_result` for Set H matching. The five non-timeout families exited 0 before and after. JSON, per-invocation commands, stdout hashes, exit statuses and elapsed times are in `results/raw/S2a2/{before,after}/`.
- Each fixture has a `SOURCE.txt` with the pinned upstream commit, original paths and SHA-256 hashes. All 42 fixture source copies match their Git blobs byte-for-byte. Evidence is in `fixture-provenance.log`. W0461 additionally stages R1CS/SYM generated from the real key-generation circuit with Circom 2.1.9 under ignored `fixture-work/W0461/`. This recreates the same basename collision without tracking generated constraint or symbol files.
- Baseline, candidate, baseline fixture, and candidate fixture summaries have SHA-256 hashes `a33ba6b0dee56701e427388959e946fc5c778849fd8f4e2a3083a6944aecc934`, `8a4c93fcd7940ad60ca0eacfa6cbee586a0b10f1237dcdd95bbae3831c1c0da0`, `98db444af33b0beb56a56368655db66e4f2041f6648e136481ffe6b6de861599`, and `8a4c93fcd7940ad60ca0eacfa6cbee586a0b10f1237dcdd95bbae3831c1c0da0`, respectively. The baseline comparison checked the set of exact violation messages. Fixture differences in the number of candidate triples are expected with fewer source files.
- The Freeze 2 module list plus the S2a and S2a2 regressions passed 61/61, exit 0. The log is `results/raw/S2a2/full-suite.log` (SHA-256 `18ce40e6e7553dfde0f1fd39d927ff93d2e2f2501b04d6fa92f7cc06563d685b`).

## Results

| Card and pinned source | Reproduced | Root cause | Fix or limitation | Candidate verdict at card |
| --- | --- | --- | --- | --- |
| W0016 · `0589519133e9e8398fbb3c3bdf5fc8465996a49a` · `GovernorL1.sol:155` | Y, 4 vs. 1 and 4 vs. 3 | The four-word call at lines 184–193 targets a dynamically sized UltraPlonk ABI. The local verification key stores 4 at `plonk_vk.sol:14`, but the extractor recovers no fixed arity from that layout. Heuristic matching compares other circuit entry points. The Noir parser also treats the private name `public_inputs` as a visibility marker and omits the explicit public return (`circuits.py::parse_noir`, lines 157–204). | Gate circuit-side count warnings on a recovered verifier arity (`analyzer.py:1393–1406`). UltraPlonk layout and exact Noir producer linkage remain unsupported here. | `UNKNOWN` / `CIRCUIT_VERIFIER_CORRESPONDENCE_UNRESOLVED` |
| W0220 · `9ded99d1aa483770cc816d0f0df2c8bd26134421` · `hackergroup.sol:175` | Y, 8 vs. 4 | `_ccipReceive` decodes a `uint256[8] proof` and forwards it through `submit`. The nested `ISemaphore.verifyProof` call passes separate scalar statement arguments and the proof. `public_vector` rejected the proof as a public vector but kept its base, so the helper projection converted it into a synthetic one-argument call and recovered length 8 from the ABI decode (`solidity.py:332–337`, `analyzer.py::discover_consumers`). | Preserve the helper call with an unresolved vector, and exclude the proof base from public-vector shape extraction. | `UNKNOWN` / `PUBLIC_INPUT_VECTOR_UNRESOLVED` |
| W0253 · `9ded99d1aa483770cc816d0f0df2c8bd26134421` · `hackergroup.sol:109` | Y, 8 vs. 4 | Same helper projection as W0220. `submitPublic` forwards its fixed-size proof parameter through `submit`, where the caller's parameter type restored the misleading shape. | Same proof-only forwarding fix. | `UNKNOWN` / `PUBLIC_INPUT_VECTOR_UNRESOLVED` |
| W0333 · `3cdcfd78595d454eb4670009a332d28be43791a1` · `TransferContract.sol:296` | Y, 4 vs. 2 | The mint function passes four words and the mutable `vk_theta_mint` to a reusable library at line 325. `Groth16Verifier.sol:171` computes required length from that key's IC array. The two-public-input `HZKA_psi.circom:128` is a separate audit circuit, heuristically paired with mint. | Same circuit-side arity gate. The configured mint key and its producer relation remain unresolved. | `UNKNOWN` / `CIRCUIT_VERIFIER_CORRESPONDENCE_UNRESOLVED` |
| W0349 · `9aa1970e1a80ba8d8bfa6ed16e316303e1b1fa69` · `AutoBattler.sol:81` | Y, 5 vs. 1 | The call at line 109 uses the inherited `battleVerifier` declared in `IAutoBattler.sol:56`. The army and battle implementations share a generated contract declaration and dynamic verify ABI. Their keys store 1 and 5, respectively, at line 14. Heuristic correspondence admitted the army circuit for the battle call. | Same circuit-side arity gate. The separately recovered five-word battle candidate still has unresolved element meaning. | `UNKNOWN` / `PUBLIC_INPUT_MEANING_UNRESOLVED` and `CIRCUIT_VERIFIER_CORRESPONDENCE_UNRESOLVED` |
| W0461 · `8a8ed58e6c35bab23c6ff9ffab6922da1ba11dbd` · `Tazza.sol:61` | Y, 18 vs. 2 | `circuits.py::attach_or_build` selected `key_generation/circuit.r1cs` for `create_shuffled_deck/circuit.circom` using the shared stem. The deck declares `D[2][2][n]` and `h[2]`, with `n=4`. The source parser also skipped the symbolic output extent. | Reuse sibling pairs only and require compiled metadata for symbolic output extents (`circuits.py:90–103,554–565`). Recompilation yielded 16 outputs and 2 public inputs, matching the verifier declaration and consumer count. Consumer element order remains unresolved. | `UNKNOWN` / `PUBLIC_INPUT_ORDER_UNRESOLVED` |
| W0658 · `c71874104b63a7c656b6d3c9299c71a2e4c653a7` · `DataPointerRegistry.sol:61` | N, 150 s harness timeout | The longer baseline exceeded the analyzer's internal budget before recovering any triple. Repeated stack samples put the time in pre-build circuit ranking, `analyzer.py::_match_score` → `_verifier_correspondence` → `_declaration_shapes` → Solidity parsing. | Accepted timeout limitation. | `UNKNOWN` / `RUN_TIMEOUT` |

The W0461 deck compile exited 0 with 33,192 nonlinear constraints. R1CS SHA-256 `485b260e3a3f2686c062f7a10f07b0701d9e29b292c9653170fc87359d49a403`, SYM SHA-256 `6bfa95b4b2a7bea80b2ffdd1cbece95adf5729b322b862501530c34120f412dc`. The no-compiler regression returns `UNKNOWN` for the incomplete interface.

### P5 positive controls

Hash-checked retained Solidity was parsed again and combined with the recorded circuit interface facts, match candidates and compiled-availability flags from S2a revision 1. The candidate P5 rule reproduced every original exact-site verdict, reason, message and fact list. The Set H matcher located both cards at their recorded sites.

| Card | Pinned commit | Exact-site replay |
| --- | --- | --- |
| W0412 | `6b71cf2ae3c1d9c621c3a49368ac17988f3e477e` | `VIOLATION`, 6 vs. 7, in `Auction.sol:53` |
| W0668 | `ebe8fa1a63c0d001091a8d7d0100bc4c5df54252` | `VIOLATION`, 4 vs. 5, in `LTVOracle.sol:93` |

Replay exited 0. Evidence is `results/raw/S2a2/p5-tp-replay.json`, SHA-256 `f65a84a6f221d8aee6384f68d35638d412bf149529df0463bf783f02f760b4b4`. The prior harness deleted both full checkouts, and the packets omit the circuit source bytes. This verifies P5 decision preservation on the retained inputs. It leaves repository-wide rediscovery and circuit re-extraction unverified for both TP cards.

### Original 56 DEV rows

The unchanged runner was imported to redirect its output into S2a2's raw namespace. Both phases used the same 56 retained revisions, Circom 2.1.9 and `--skip-fetch`. The before phase used an untouched analyzer snapshot extracted from HEAD. Both phases exited 0 and completed all 56 rows with 46 rows containing triples and zero crashes. The controlling ledgers are in `results/raw/S2a2/T24/before-20261118T200742Z-2/` and `results/raw/S2a2/T24/after-20261118T200539Z-3/`, with ledger SHA-256 hashes `a1ac0511960a0137d2f72a075a6219d0b5e6e0e030894ec0c0c80494ea8379b8` and `44063fb4c0751d53f390f7b5b684d9177120fa96f4c96406e03229a7b0ded963`.

| Pattern | Unchanged `VIOLATION` rows | Unchanged `VERIFIED_WITHIN_SCOPE` rows | Unchanged `UNKNOWN` rows |
| --- | ---: | ---: | ---: |
| P1 | 6 | 0 | 50 |
| P2 | 0 | 0 | 56 |
| P3 | 6 | 7 | 43 |
| P4 | 6 | 15 | 35 |
| P5 | 1 | 3 | 52 |

All 280 row-level verdict/applicability cells and all per-row violation site/reason sets are unchanged. The harness build-success tally changed from 41 to 37, and build failures from 35 to 39. DEV-F24 and DEV-F41 had sibling R1CS files without matching SYM files. DEV-F28 and DEV-F40 had same-stem pairs in separate build directories. All four fallback builds failed with missing includes. These cases require stronger artifact association or dependency resolution for compiled coverage.

`python3 results/raw/S2a2/compare_dev.py results/raw/S2a2/T24/before-20261118T200742Z-2 results/raw/S2a2/T24/after-20261118T200539Z-3` exited 0. The detailed comparison is `results/raw/S2a2/dev-delta.json` (SHA-256 `d6d888bee965ecebf20218f3a0c3ad0065838c66f6ba7e1721fa51bdcbdd8ae9`).

## Assumptions and limitations

- Results are source-level development diagnostics. The six warning retirements show fail-closed behavior on the affected cards. They do not establish application safety, prove transfer, or recompute precision on the entire 15-card Set H subset.
- A sibling R1CS/SYM pair is a local association heuristic. Fresh builds provide stronger provenance. The current implementation does not establish build/source identity for pre-existing sibling pairs.
- W0658 has no regression fixture because there was no exact-site baseline warning under either observed budget. A reduced file subset cannot substitute for the whole-checkout timeout.

## Failed approaches and unexpected observations

- The 150 s W0658 harness run had no stdout and was terminated at 150.110 s. With the 300 s outer cap, both profiled invocations returned analyzer exit 2 and `RUN_TIMEOUT` with zero triples. Baseline elapsed 223.706 s, with 8/8 samples in circuit ranking. Candidate elapsed 260.364 s, with 10/10 samples in the same stage. The analyzer does not enforce its 120 s deadline inside ranking. Both runs also recorded a Circom timeout after the internal budget had elapsed. These runs overlapped other local jobs and were diagnostic timing samples. The raw JSON and profiles are under `results/raw/S2a2/{before-long,after-long}/PhaseMirror__The-Foundry/`. Candidate JSON SHA-256 `05b6a48025597a212947ac4bc0d6dc49bf321732b93d30263cd18f60c65a7bb0`, profile SHA-256 `7dae6ec4b0fc19818023afc912844d5164d1c7c5dbd1fdb6abd6fa1801d71d6d`.
- The herdr-core CLI could not open its lock under the workspace sandbox. The long jobs used sandboxed command sessions. An initial DEV wrapper attempted to assign Zsh's read-only `status` variable after the runner had written a complete manifest. A fresh clean-exit before run supplied confirmation.
- README's CLI hash and unopened-EVAL statement describe earlier analyzer work. The later S2a revision-1 report controls the spent-family DEV history for this lane. Historical records were preserved.

## Held-out hygiene statement

The six pre-cloned development families, two spent TP families and all 52 distinct original DEV repositories (56 pinned rows) passed `scripts/check_holdout.py` before being read. Only the six scoped checkouts, retained TP packets and original DEV checkouts were used. No unused EVAL family was opened. The lane used local sources and no network, chain RPC, transaction broadcast, or disclosure.

## Recommended next task

Restore the two guard-allowed TP checkouts offline at their pinned commits and require an unhinted Set H rerun to match `VIOLATION` at both recorded source locations. Preserve the fresh raw outputs alongside the existing decision replay.
