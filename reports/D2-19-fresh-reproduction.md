# D2-19 fresh reproduction report (`fresh-evaluator-02`)

## Reproduction judgment

The documented partial-development-artifact workflow reproduced successfully on the current host and current source workspace. All four requested profiles exited 0 and returned `PASS`. The result preserves the package status `PARTIAL_DEVELOPMENT_ARTIFACT / FINAL_ARTIFACT_BLOCKED`, Gate A `INCONCLUSIVE`, Gate B `NOT_EVALUATED`, Gate C `NOT_REACHED`, and research verdict `UNKNOWN`. It does not establish a final artifact, a scored result, or a submission-ready paper.

This was a fresh AI evaluator session on the same host and checkout. It was **not** a fresh container, clean-machine portability test, anonymous evaluator run, or independent human replication. The retained-evidence route depended on the current workspace and local Git history. No network access was used.

## Scope, bindings, and environment

- Working directory: `/Users/imranpollob/Coding/bc/bindcheck-d1-paper`
- Reproduction date and timezone supplied to the evaluator: 2026-11-02, America/Detroit.
- Fresh output namespace: `artifact/work/fresh-evaluator-02`; it was checked absent before the mechanical command.
- Interpreter: Python 3.14.7, satisfying the README's Python 3.10-or-newer requirement.
- Git: 2.51.0.
- Host reported by `uname -srm`: Darwin 27.0.0 arm64.
- Python dependencies for these profiles: standard library only. `pytest` and `pycryptodome` were not needed by the requested profiles.
- Workspace dependencies: exact current source workspace, local Git metadata/object access, and retained development inputs. The historical D2-01 overlay used Git object `544656abbfb535dcbe0f1157087240464f38cb0b` in memory.

Before any profile ran, the evaluator executed:

```text
shasum -a 256 artifact/reproduce.py artifact/SHA256SUMS
```

| Bound file | Required SHA-256 | Observed pre-run SHA-256 | Result |
|---|---|---|---|
| `artifact/reproduce.py` | `1973a850466aee837fbd05c14bac216f424c95db3fa0eb6c0c1d3f3bbe9d6d91` | `1973a850466aee837fbd05c14bac216f424c95db3fa0eb6c0c1d3f3bbe9d6d91` | Match |
| `artifact/SHA256SUMS` | `7d11a8d8f646f0f08c756ab58f193c9ce52e8c3b16efd9f53ce790847081dc38` | `7d11a8d8f646f0f08c756ab58f193c9ce52e8c3b16efd9f53ce790847081dc38` | Match |

The same command was repeated after all profiles and before this report was written; both digests remained identical.

## Commands and runtimes

Runtimes are `/usr/bin/time -p` real times. The total measured real time for the four top-level profiles was 7.94 seconds. These timings are same-host observations, not performance guarantees.

| Profile | Exact command | Exit | Real time | Observed versus expected |
|---|---|---:|---:|---|
| Metadata | `python3 artifact/reproduce.py metadata` | 0 | 0.15 s | `PASS`; all declared metadata assertions matched. |
| Retained verification | `python3 artifact/reproduce.py verify-retained --source current-workspace` | 0 | 3.81 s | `PASS`; the one live D2-01 mismatch was the expected quarantined mismatch, and the historical overlay and retained seals passed. |
| Recompute | `python3 artifact/reproduce.py recompute --source current-workspace` | 0 | 2.67 s | `PASS`; selected results for D2-00 through D2-10, downstream dispositions, and Step 18 matched `expected-results-v1.json`. |
| Mechanical rerun | `python3 artifact/reproduce.py rerun-mechanical --source current-workspace --run-id fresh-evaluator-02` | 0 | 1.31 s | `PASS`; Gate A remained blocked, and fresh D2-08 through D2-10 categorical/count fields matched. |

No top-level profile failed. The mechanical runner does not report per-subprocess elapsed times, so only its aggregate 1.31-second runtime is available; this is a reporting limitation, not a reproduction failure.

## Metadata profile: expected and observed

The metadata profile verified ten artifact-owned checksummed files and 53 controlling manifest bindings. It also checked the exact status boundary, schema/status documents, absence of reserved data and final-release claims, and the Step 18 records.

| Claim | Expected | Observed | Result |
|---|---|---|---|
| Artifact status | `PARTIAL_DEVELOPMENT_ARTIFACT / FINAL_ARTIFACT_BLOCKED` | Same | Match |
| Research verdict | `UNKNOWN` | `UNKNOWN` (enforced by the profile) | Match |
| Gates | A `INCONCLUSIVE`; B `NOT_EVALUATED`; C `NOT_REACHED` | Same (enforced by the profile) | Match |
| Release/data claims | Reserved data `false`; frozen release `false`; final paper artifact `false` | Same (enforced by the profile) | Match |
| Own checksum table | All listed files valid | `PASS`, 10 checked files | Match |
| Controlling-file manifest | All bindings valid | `PASS`, 53 checked bindings | Match |
| Step 18 ledger | 20 claims: 13 supported, 3 contradicted, 4 unresolved | 20: 13 supported, 3 contradicted, 4 unresolved | Match |
| Step 18 claim map / closest works / primary sources | 17 / 5 / 11 | 17 / 5 / 11 | Match |
| Step 18 readiness | Gate A `INCONCLUSIVE`; verdict `UNKNOWN`; `NOT_SUBMISSION_READY` | Same (enforced by the profile) | Match |

## Current-workspace retained verification

The expected top-level outcome was `PASS`; the observed outcome was `PASS`. The live D2-01 replay's `EXPECTED_FAIL` is an expected evidence state, not a profile failure.

| Retained check | Expected | Observed | Result |
|---|---|---|---|
| D2-01 live replay | 8,134 files; exactly one mismatch at `src/bindcheck_d1/role_binding.py`; status `EXPECTED_FAIL` | 8,134 files; one `CONTENT_MISMATCH` at that path; `EXPECTED_FAIL` | Match |
| Live mismatched byte | Expected size 41,698 and SHA-256 `a516f0e339f6fec23fcd96efb52821e9933feb6837e740c99a6d5dbee7bd9028`; current checkout intentionally differs | Observed size 43,263 and SHA-256 `5bb3012b7d192e75e266cc3f5265e024046e8614c0cb63891c7acd5271eeaa71` | Expected difference observed |
| Historical overlay replay | Git object `544656abbfb535dcbe0f1157087240464f38cb0b`; 8,134/8,134; `PASS`; not current-checkout equivalence | `PASS`, 8,134 checked; overlay SHA-256 `a516f0e...9028`; source `IMMUTABLE_GIT_OBJECT_IN_MEMORY`; equivalence `false` | Match |
| Independent wrapper cross-check | Live `EXPECTED_FAIL` with one mismatch; overlay `PASS` with 8,134 files; wrapper `PASS` | Exactly those values; wrapper `PASS` | Match |
| D2-00 pre-report byte | `UNAVAILABLE_RETENTION_GAP_NOT_RECONSTRUCTED` | Same in overlay and wrapper results | Match; gap retained |
| D2-01 external-input manifest | 9 files and valid manifest | `PASS`, 9 files; manifest SHA-256 `990de3bbcc78c696f15f54eed24166d6eddcabdff0c1ac18c4ab5658a51d6c5a` | Match |
| D2-07 authoritative seal | Exact retained seal; 623 files; no mismatch | `PASS`, 623 files, zero mismatches; seal SHA-256 `b9f0f1eb6b9aa1bb3ea8aaf1fba3c3939b3d70a787a57be92f3c4154fad50558` | Match |
| D2-08 seal | Exact retained seal; 92 files; no mismatch | `PASS`, 92 files, zero mismatches; seal SHA-256 `d2195d93fc6e51458a994ecc63838935fb36bad275379ef15e43ca2f9c112343` | Match |
| D2-09 seal | Exact retained seal; 40 files; no mismatch | `PASS`, 40 files, zero mismatches; seal SHA-256 `c678085afa6a73d0f8115d10055fb753bd024a174a38618cb0e5e6943661e8bd` | Match |
| D2-10 corrected-run seal | Exact retained seal; 9 files; no mismatch | `PASS`, 9 files, zero mismatches; seal SHA-256 `c5bb3163283c7b16a0d341067c6f2c3f8fa9965d85ab13dc761d4e948fcf21e6` | Match |
| Headline bindings | All nine headline hashes valid | `headline_hashes: 9`, profile `PASS` | Match |

## Recomputed tables and claims

The recomputation profile first repeated retained verification, then compared the following selected values to `artifact/expected-results-v1.json` using exact equality. Its stdout returned all twelve step names, `status: PASS`, `downstream_dispositions: PASS`, and `research_verdict: UNKNOWN`. Thus every vector below is both the declared expected vector and the exact observed vector accepted by the reproducer.

| Step | Expected vector | Observed vector/result |
|---|---|---|
| D2-00 | Self-test `PASS`; five focused unit tests; pre-tamper verification `PASS`; post-tamper verification `FAIL` | Same; exact comparator passed |
| D2-01 | `COMPLETE`, verdict `UNKNOWN`, 49 rows; static targets/detected/unsupported/misses/warnings = 30/11/19/0/13; integrated = 30/17/13/0/26 with 23 associated warnings; ablation detections producer/consumer/unjoined/full = 3/2/5/7; unknown example `E8`; Payy earlier `true`, check-added `false`; all completion checks true; retained replay values as above | Same; exact comparators passed |
| D2-02 | Verdict `UNKNOWN`; candidates/repositories/lineages/current variants = 3/2/2/30; consumer-AST-blocked 13; nested-mapping 12; historical attempts/unique projects/repeats = 12/8/4 | Same; exact object comparison passed |
| D2-03 | Verdict `UNKNOWN`; 22 claims; five closest works | Same; exact comparison passed |
| D2-04 | `FROZEN_PRE_ANNOTATION`; verdict `UNKNOWN`; zero human ratings; no agreement result; annotation form `BLANK_NO_JUDGMENTS` with no filled rater, relevance, cause, consequence, or role judgment | Same; all blank-form assertions passed |
| D2-05 | `DRAFT_UNSEALED_DO_NOT_SCORE`; verdict `UNKNOWN`; scoring unauthorized; zero score rows and no score-row field | Same; assertions passed |
| D2-06A | `COMPLETE_CONSTRUCTION_SMOKE_ONLY`; verdict `UNKNOWN`; unscored; 78 baseline arms; 72 `SUPPORTED`, 6 `UNKNOWN`; transformations planned/attempted/rejected/controlled/eligible = 6/4/2/4/4; `UNRESOLVED_EQUAL_POLICY_INTERFACE` | Same; exact object comparison passed |
| D2-06B | `CONSTRUCTION_SMOKE_ONLY_UNSEALED_DO_NOT_SCORE`; verdict `UNKNOWN`; unscored; two cases; adapter smoke `PASS`; pinned/MSRC native exits 0/1; both scoring denominators null | Same; exact object comparison passed |
| D2-07 | `BLOCKED_BEFORE_SCORE`; verdict `UNKNOWN`; Gate A `INCONCLUSIVE`; 13 candidate cases, 6 internal arms, 11 external inventory entries, 0 scored arms; four declared blocker codes | Same; exact object comparison passed |
| D2-08 | `PASS_MECHANICAL_ONLY`; verdict `UNKNOWN`; unscored; five bundles, five identities/bundle, ten facts/bundle, four mappings, five negative fixtures; name-influence audit `PASS` | Same; exact object comparison passed |
| D2-09 | `COMPLETE_MECHANICAL_FIXTURE_ONLY`; verdict `UNKNOWN`; ten cases and ten equal-input parity cases; mechanical states 1 `ESTABLISHED`, 2 `MISMATCH_CANDIDATE`, 7 `UNKNOWN`; effective states 10 `UNKNOWN`; zero score rows | Same; exact object comparison passed |
| D2-10 | Authoritative run `results/raw/D2-10/run-02`; `PASS`; verdict `UNKNOWN`; 16 facts; producer guarantees 0; eligible derived consumer-use facts 0; `UNKNOWN_UNREVIEWED_DEVELOPMENT_FIXTURE`; identity chain `PASS`; 7 semantic controls, 3 adversarial controls, 5 D1P40 regressions; equal-input semantic parity true | Same; exact object comparison passed |

The four D2-07 blocker codes expected and observed were:

1. `DISTINCT_HUMAN_POLICY_REVIEW_MISSING`
2. `FAIR_SAME_POLICY_ARM_INCOMPLETE`
3. `HUMAN_POLICY_AUTHOR_OR_ADOPTION_MISSING`
4. `STRONG_FULL_POE_INTERFACE_NOT_EQUAL`

The downstream exact comparisons also passed:

| Disposition | Expected | Observed |
|---|---|---|
| Steps 11-14 | `READ_ONLY_AUDIT_COMPLETE / STEPS_11_14_NOT_EXECUTED / GATE_B_NOT_EVALUATED` | Exact match; recomputation returned `downstream_dispositions: PASS` |
| Steps 15-17 | `READ_ONLY_AUDIT_COMPLETE / STEPS_15_17_NOT_EXECUTED / GATE_C_NOT_REACHED` | Exact match; recomputation returned `downstream_dispositions: PASS` |
| Step 18 | Verdict `UNKNOWN`; Gate A `INCONCLUSIVE`; `NOT_SUBMISSION_READY`; 20 ledger claims, status split 13/3/4, 17 claim-map entries, five closest works, eleven primary-source records | Exact match; profile `PASS` |

This profile recomputed selected categorical/count results. Per the README, it did not rerun compilers, analyzers, baselines, proofs, or human judgments.

## Fresh mechanical rerun

The fresh output directory contains 75 files and occupied 892 KiB according to `du -sk`. All seven captured stderr files were zero bytes. Each subprocess returned 0:

| Subprocess | Observed command payload | Return code |
|---|---|---:|
| Gate A validation | `scripts/d2_step7_gate_a.py --validate-only` | 0 |
| D2-08 validation | `scripts/d2_step8_identity.py --protocol protocols/d2/d2-08-compiler-identity-v1.json --validate-only` | 0 |
| D2-08 run | Same script/protocol with `--out .../artifact/work/fresh-evaluator-02/D2-08` | 0 |
| D2-09 validation | `scripts/d2_step9_authorization_boundary.py --protocol protocols/d2/d2-09-authorization-boundary-v1.json --validate-only` | 0 |
| D2-09 run | Same script/protocol with `--out .../artifact/work/fresh-evaluator-02/D2-09` | 0 |
| D2-10 validation | `scripts/d2_step10_typed_extraction.py --protocol protocols/d2/d2-10-typed-extraction-v2.json --validate-only` | 0 |
| D2-10 run | Same script/protocol with `--out .../artifact/work/fresh-evaluator-02/D2-10` | 0 |

The observed subprocess interpreter was `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`. The Gate A validation independently observed `BLOCKED_BEFORE_SCORE`, Gate A `INCONCLUSIVE`, verdict `UNKNOWN`, 13 candidate cases, 6 internal arms, 11 external entries, 0 scored arms, scoring authorization `false`, and the four blocker codes listed above. These match the declared expectations. It also reported `prior_attempt_current_verification: FAIL`, an empty objective subset, and row-local unresolved code `SUBJECTIVE_SCORER_ADJUDICATOR_UNAVAILABLE`; these preserve the block rather than authorizing scoring.

| Fresh fixture | Expected categorical/count result | Observed fresh result | Result |
|---|---|---|---|
| D2-08 | `PASS_MECHANICAL_ONLY`; `UNKNOWN`; unscored; bundles/identities/facts/mappings/negative fixtures = 5/5/10/4/5; audit `PASS` | Exactly those values | Match |
| D2-09 | `COMPLETE_MECHANICAL_FIXTURE_ONLY`; `UNKNOWN`; cases/parity = 10/10; mechanical 1 established, 2 candidates, 7 unknown; effective unknown 10; score rows 0 | Exactly those values | Match |
| D2-10 | `PASS`; `UNKNOWN`; facts 16; producer guarantees 0; eligible consumer-use 0; unknown-unreviewed result; identity `PASS`; controls 7/3; regressions 5; parity true | Exactly those values | Match |

The mechanical summary correctly labels these outputs `UNREVIEWED_DEVELOPMENT_FIXTURE`, `scored: false`, and research verdict `UNKNOWN`. Its comparison deliberately excludes timestamps, elapsed/runtime fields, human minutes, absolute and temporary paths, platform/Python strings, Git branch/dirty/commit metadata, raw compiler-log byte hashes, and fresh transitive seal hashes. No excluded field was used to claim equality.

## Sidecar and unsupported work

The sidecar profiles were **not executed** because no reviewed, safely extracted sidecar root was supplied. No sidecar, historical byte, or substitute file was fabricated or copied. Consequently this report makes no sidecar-portability claim.

D2-01 and D2-06A/06B full reruns remain intentionally unsupported by the package because their frozen protocols bind Darwin binaries, absolute user paths, and ignored inputs. Human annotation, policy adoption/review, scoring, and adjudication remain retained dependencies rather than reproducible computations. The known D2-00 pre-report retention gap remains explicitly unavailable and was not reconstructed.

## Failures, ambiguities, and limits

- Profile failures: none.
- Unexpected mismatches: none. The sole live D2-01 content mismatch was explicitly expected, and the exact historical byte passed the in-memory overlay replay.
- Unclear instructions affecting execution: none. The README clearly separated metadata, retained verification, recomputation, current-workspace mechanical rerun, and optional sidecar routes.
- Runtime granularity limitation: top-level profile runtimes were measured, but the runner exposes only subprocess return codes, not individual subprocess runtimes.
- Reproduction boundary: this is a same-host engineering reproduction in a fresh AI session. It is not a clean-container or fresh-machine replication and is not an independent human scientific review.
- Scientific boundary: the successful commands verify the partial development record and fresh unscored fixtures only. They do not change Gate A/B/C, research verdict, scoring status, or submission readiness.

Overall, the observed behavior is internally consistent with the README and machine-readable expected-results file, within the artifact's stated partial-development and same-workspace limits.
