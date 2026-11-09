# E1 benchmark and comparative measurement

**Objective and status.** This lane froze a case inventory and location-sensitive scorer before running the committed comparison arms. Freeze 2 and its circuit-withheld ablation are measured below. Full source revisions for every public pair are pinned and audited below, with structural and build blockers kept explicit. A paper-level human-accepted comparative result remains **MISSING** because every public card still has a blank reviewer decision. No claimed E4 result or superiority follows from this campaign.

## Authority and population

The research contract controls the three security verdicts, the E0–E4 ladder, and treatment of unavailable inputs. The old [README](../../README.md) still names prior analyzer hashes and describes the D1 Noir line as current; the later [freeze declaration](../../docs/FREEZE-2026-11-09.md) and [environment record](environment.json) identify the Circom/Solidity analyzer actually measured here. This report does not rewrite historical results.

The [manifest](../../benchmark/manifest.json), [case files](../../benchmark/cases/), [source locks](../../benchmark/cases/), and [metrics](metrics.json) contain [68](metrics.json) case directories: [46](metrics.json) synthetic, [6](metrics.json) exposed DEV-history revisions, and [16](metrics.json) public-report pairs. The public pairs account for [32](metrics.json) revision slots; every card decision is PENDING. The synthetic labels are AI-PROPOSED and the same team authored arm C. The DEV-history labels are AI-PROPOSED and EXPOSED. Neither group is independent held-out ground truth.

The artifact audit corrected an initial manifest classification after the native runs, without changing a label or score rule. The zkDrops [verifier source](</Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev/DEV-H01--a16z__zkdrops--4002962fb632/contracts/compiled/MerkVerifier.sol>) says it is snarkJS-generated and declares PlonkVerifier. The final [case metadata](../../benchmark/cases/DEV-H01/case.json) therefore calls this PLONK, outside the requested Groth16 subset. The [protocol ledger](metrics.json) identifies [46](metrics.json) mock-verifier synthetic cases, [2](metrics.json) PLONK DEV revisions, [2](metrics.json) DEV revisions with no matched verifier, [2](metrics.json) UltraHonk DEV revisions, and [16](metrics.json) public pairs with unresolved protocol correspondence. These are inventory facts, not vulnerability labels.

## Buildability and scoring boundary

The [freeze-1 build ledger](../../results/raw/bench/e1-build-20261109-verified/build.json) checks each source lock and DEV checkout revision, and records the Circom and Solidity commands, hashes, exit statuses, and stderr. [All 46](metrics.json) synthetic sources compile, but their verifier is a simplified mock/interface; this is not a real Groth16 proof path. [Both zkDrops revisions](metrics.json) compile with the pinned OpenZeppelin tarball whose SHA-512 integrity matches their package lock. [Both Semaphore revisions](metrics.json) lack the generated verifier artifact. [Both Payy revisions](metrics.json) use Noir/UltraHonk. At that checkpoint, [all 32](metrics.json) public revision slots were MISSING_ARTIFACT because their retained snapshots did not contain a selected circuit, verifier, and consumer triple. The new full-tree public audit below supersedes only that inventory finding. No source failure was converted to a miss.

The [scoring rules](../../benchmark/scoring-rules.json) and [scorer](../../benchmark/score.py) were committed at [aa4b7d7](../../benchmark/manifest.json) before these runs. DETECT requires the right pattern **and** source location. FALSE-ALARM requires a target binding warning on the repaired/legitimate revision. Unrelated native warnings stay separate. UNKNOWN, timeouts, setup failures, missing artifacts, and circuit-only conclusions earn no detection or miss. A completed vulnerable run without a correctly located finding is MISS; a completed repaired run without one is CLEAR. The [scorer regressions](../../results/raw/bench/verification-20261109.json) passed [4](../../results/raw/bench/verification-20261109.json) tests. The [per-case matrix](matrix.csv) retains every tool, case, side, reason, and source path.

Post-run scorer changes made the already-committed evidence-grade exclusion explicit and changed CSV line endings to LF. Re-executing the original committed scorer on the same observations produced a [logically identical matrix](../../results/raw/bench/matrix-equivalence.json); neither expected labels nor scoring policy changed.

## Exploratory tool by pattern results

Arm A is the committed consumer/verifier source screen plus a same-policy Foundry harness with a mock verifier; arm B retains native circuit-tool output; arm C adds the committed straightforward source joins to A and B. Their implementation is documented in [baselines/strong](../../baselines/strong/README.md). Slither default was invoked separately. None of the mock Foundry failures is treated as proof-backed validation.

All cells below are **AI-PROPOSED** only, including synthetic mock verifiers and the exposed PLONK pair. Each cell is DETECT / MISS / FALSE-ALARM / CLEAR / UNKNOWN / ERROR. Pattern denominators and every cell come from [metrics.json](metrics.json). PENDING public rows have [32 UNKNOWN](metrics.json) outcomes per tool and have no accepted pattern denominator. The HUMAN-ACCEPTED headline has no labeled row, so its precision and decided rate are **MISSING**.

| Tool | P1 ([20](metrics.json)) | P3 ([16](metrics.json)) | P5 ([4](metrics.json)) | R-COMMITMENT ([4](metrics.json)) | R-EXTENT ([6](metrics.json)) | R-MASK ([2](metrics.json)) |
|---|---|---|---|---|---|---|
| A | [10/0/1/9/0/0](metrics.json) | [4/3/1/6/2/0](metrics.json) | [0/2/0/2/0/0](metrics.json) | [0/2/0/2/0/0](metrics.json) | [0/0/0/0/6/0](metrics.json) | [0/0/0/0/2/0](metrics.json) |
| B | [0/0/0/0/20/0](metrics.json) | [0/0/0/0/16/0](metrics.json) | [0/0/0/0/4/0](metrics.json) | [0/0/0/0/4/0](metrics.json) | [0/0/0/0/6/0](metrics.json) | [0/0/0/0/2/0](metrics.json) |
| C | [10/0/0/10/0/0](metrics.json) | [4/3/1/6/2/0](metrics.json) | [0/2/0/2/0/0](metrics.json) | [0/2/0/2/0/0](metrics.json) | [0/2/0/2/2/0](metrics.json) | [0/1/0/1/0/0](metrics.json) |
| Slither default | [0/0/0/0/20/0](metrics.json) | [0/0/0/0/16/0](metrics.json) | [0/0/0/0/4/0](metrics.json) | [0/0/0/0/4/0](metrics.json) | [0/0/0/0/6/0](metrics.json) | [0/0/0/0/2/0](metrics.json) |
| Circomspect | [0/0/0/0/20/0](metrics.json) | [0/0/0/0/16/0](metrics.json) | [0/0/0/0/4/0](metrics.json) | [0/0/0/0/4/0](metrics.json) | [0/0/0/0/6/0](metrics.json) | [0/0/0/0/2/0](metrics.json) |
| Picus | [0/0/0/0/20/0](metrics.json) | [0/0/0/0/16/0](metrics.json) | [0/0/0/0/4/0](metrics.json) | [0/0/0/0/4/0](metrics.json) | [0/0/0/0/6/0](metrics.json) | [0/0/0/0/2/0](metrics.json) |
| zkFuzz | [0/0/0/0/20/0](metrics.json) | [0/0/0/0/16/0](metrics.json) | [0/0/0/0/4/0](metrics.json) | [0/0/0/0/4/0](metrics.json) | [0/0/0/0/6/0](metrics.json) | [0/0/0/0/2/0](metrics.json) |
| ZKAP | [0/0/0/0/20/0](metrics.json) | [0/0/0/0/16/0](metrics.json) | [0/0/0/0/4/0](metrics.json) | [0/0/0/0/4/0](metrics.json) | [0/0/0/0/6/0](metrics.json) | [0/0/0/0/2/0](metrics.json) |
| BindCheck freeze 1 | [8/0/1/8/3/0](metrics.json) | [4/2/0/5/5/0](metrics.json) | [0/1/0/1/2/0](metrics.json) | [0/0/0/0/4/0](metrics.json) | [0/0/0/0/6/0](metrics.json) | [0/0/0/0/2/0](metrics.json) |

Native results are deliberately distinct from binding verdicts. [Circomspect ran 56 invocations](metrics.json), with [45 exit-zero and 11 exit-one](metrics.json); exit one can include a diagnostic. [Picus ran 48 invocations](metrics.json), all [exit eight](metrics.json) under its circuit question, and [all 48 private temporary directories were removed](metrics.json). [zkFuzz completed 46 synthetic invocations](metrics.json), while its historical attempts had [4 initial parser/setup errors](metrics.json); the [2 zkDrops retries](metrics.json) with an include path timed out under the fixed process-group cap, and Semaphore's old Circom syntax remains unsupported. [Slither produced successful JSON on 48 sources](metrics.json); its other [4](metrics.json) local attempts failed compilation/setup. These tools' native diagnostics do not decide a circuit–contract binding. ZKAP had [0 invocations](metrics.json): [Docker and Colima are absent](environment.json), and the pinned [resource preflight](../redteam/manifests/zkap-preflight.json) records host capacity below its upstream requirements.

## Precision, decisions, and pairs

The exact numerator/denominator fields for a scatter plot are in [metrics.json](metrics.json). These are **AI-PROPOSED screening fractions**, not paper precision:

| Tool | Target-warning precision | Decided cases |
|---|---|---|
| A | [14/16](metrics.json) | [42/52](metrics.json) |
| C | [14/15](metrics.json) | [48/52](metrics.json) |
| BindCheck freeze 1 | [12/13](metrics.json) | [30/52](metrics.json) |
| B, Slither default, Circomspect, Picus, zkFuzz, ZKAP | [MISSING](metrics.json) | [0/52 each](metrics.json) |

Under the frozen AI expectations, [A has 3](metrics.json) apparent unsafe certifications and [BindCheck has 2](metrics.json), while [C has none](matrix.csv). The BindCheck rows are [ADV-V14 and ADV-V15](metrics.json): their policy asks for chain/contract domain binding, while BindCheck's narrow P3 positive says the locally recovered replay key is canonical and consumed. This is a **scope mismatch**, not evidence that P3's stated canonicality theorem is unsound. Human policy adjudication and a real verifier are required before an unsafe-certification claim. The other A row is [ADV-V13](metrics.json). No application-level safe verdict is inferred from a clean native circuit run.

Success means DETECT on the vulnerable revision and CLEAR on its repaired/legitimate partner. On [26 AI-proposed pairs](metrics.json), A discriminates [12](metrics.json), C [13](metrics.json), and BindCheck freeze 1 [10](metrics.json). BindCheck discriminates the [DEV-H01/H02 PLONK pair](metrics.json) while A and C warn on its repaired side [in the matrix](matrix.csv); this is outside the Groth16 headline. C has more source warnings than BindCheck on some synthetic vulnerable cases, but its join-only findings often lack a source location and therefore do not earn detection credit under the committed rules. The [matrix](matrix.csv) exposes those cases without upgrading a broad warning to a localized result.

## Freeze, ablation, and reproducibility

The measured analyzer's [content hash](environment.json) equals the declared freeze [8ea6d223](../../docs/FREEZE-2026-11-09.md). The [environment record](environment.json) contains exact executable hashes, Git revisions, stdout/stderr, and exit statuses for version probes. It records Python [3.15.0](environment.json), Slither [0.11.3](environment.json), solc [0.8.30](environment.json), Circom [2.2.3](environment.json), and the pinned Circomspect, Picus, and zkFuzz source revisions. The [zkFuzz provenance](../../results/raw/bench/zkfuzz-setup-20261109/provenance.json) records source commit, Cargo lock hash, built binary hash, and removal of its temporary checkout.

Dependency and zkFuzz setup used these pinned commands. The npm tarball's integrity comparison and both source revisions are retained in the [build ledger](../../results/raw/bench/e1-build-20261109-verified/build.json) and [zkFuzz provenance](../../results/raw/bench/zkfuzz-setup-20261109/provenance.json):

    npm pack @openzeppelin/contracts@4.4.1 --pack-destination results/raw/bench/deps-20261109 --json
    tar -xzf results/raw/bench/deps-20261109/openzeppelin-contracts-4.4.1.tgz -C results/raw/bench/deps-20261109/node_modules/@openzeppelin/contracts --strip-components=1
    git clone --filter=blob:none https://github.com/Koukyosyumei/zkFuzz.git results/raw/bench/zkfuzz-setup-20261109/src
    git -C results/raw/bench/zkfuzz-setup-20261109/src checkout --detach c58639d
    cargo build --release

The exact campaign entrypoints were:

    /opt/homebrew/bin/python3 benchmark/build.py --output results/raw/bench/e1-build-20261109-verified --dependency-root results/raw/bench/deps-20261109/node_modules --dependency-tarball results/raw/bench/deps-20261109/openzeppelin-contracts-4.4.1.tgz
    PYTHONPATH=. BINDCHECK_STRONG_CIRCOM=/Users/imranpollob/Coding/bc/bindcheck-zk/tools/circom-src/target/release/circom BINDCHECK_STRONG_CIRCOMSPECT=/Users/imranpollob/Coding/bc/bindcheck-zk/tools/circomspect-src/target/release/circomspect BINDCHECK_STRONG_PICUS=/Users/imranpollob/Coding/bc/bindcheck-zk/tools/picus-src/run-picus /opt/homebrew/bin/python3 -m baselines.strong.run_campaign --campaign synthetic --output results/raw/bench/e1-synthetic-abc-20261109 --jobs 4 --a-budget 120 --b-budget 180
    BINDCHECK_CIRCOM=/Users/imranpollob/Coding/bc/bindcheck-zk/tools/circom-src/target/release/circom PYTHONPATH=. /opt/homebrew/bin/python3 -m baselines.strong.run_bindcheck --output results/raw/bench/e1-synthetic-bindcheck-freeze1-20261109 --timeout 120
    /opt/homebrew/bin/python3 benchmark/run_local.py --output results/raw/bench/e1-local-20261109 --jobs 3 --dependency-root results/raw/bench/deps-20261109/node_modules
    /opt/homebrew/bin/python3 benchmark/run_zkfuzz.py --binary results/raw/bench/zkfuzz-setup-20261109/src/target/release/zkfuzz --output results/raw/bench/e1-zkfuzz-20261109 --jobs 4 --timeout 120
    /opt/homebrew/bin/python3 benchmark/run_zkfuzz.py --binary results/raw/bench/zkfuzz-setup-20261109/src/target/release/zkfuzz --output results/raw/bench/e1-zkfuzz-h-retry-20261109 --jobs 2 --timeout 120 --ids DEV-H01 DEV-H02 --include-root /Users/imranpollob/Coding/bc/bindcheck-zk/node_modules

The [native manifests](../../results/raw/bench/e1-synthetic-abc-20261109/arm-A-manifest.json), [BindCheck manifest](../../results/raw/bench/e1-synthetic-bindcheck-freeze1-20261109/manifest.json), [local run ledger](../../results/raw/bench/e1-local-20261109/runs.json), [zkFuzz primary](../../results/raw/bench/e1-zkfuzz-20261109/runs.json) and [retry](../../results/raw/bench/e1-zkfuzz-h-retry-20261109/runs.json) retain per-invocation commands, hashes, timeouts, and output paths. Private Picus TMPDIRs and process-group timeout behavior are implemented in the committed [arm B runner](../../baselines/strong/arm_b.py); their cleanup receipts are in the native outputs and [metrics](metrics.json). No live network transaction, deployed contract call, or maintainer contact occurred.

The [verification record](../../results/raw/bench/verification-20261109.json) reports successful lock, matrix-completeness, Picus-cleanup, scorer-test, compile, diff, and freeze checks. Its [case, file, matrix, and cleanup counts](../../results/raw/bench/verification-20261109.json) are derived by [verify.py](../../benchmark/verify.py). The original [freeze-1 evidence index](evidence.json) is preserved as a historical seal; the expanded [freeze-2/public index](evidence-f2.json) hashes the new scored artifacts, manifests, and raw ledgers.

After labels change, the single command

    /opt/homebrew/bin/python3 benchmark/rescore.py

regenerates [matrix.csv](matrix.csv) and [metrics.json](metrics.json) from the retained observations without rerunning a tool. The public reviewer must update the case label and expected pattern/location from the original card before doing so; AI proposals are not accepted labels.

## Freeze 2 and circuit-withheld ablation (2026-11-09 addendum)

The declared [freeze 2](../../docs/FREEZE-2.md) was merged from `zk-integration` at merge commit `05e33e7`. The measured [content-hash check](../../results/raw/bench/f2-freeze-check.json) returned `92789fad12050a3058a21cc5c2326e7d41604ad5ade0f09f72a35789437e6c1a`. The committed [scorer](../../benchmark/score.py) and [rules](../../benchmark/scoring-rules.json) were unchanged. The first [756 freeze-1 matrix rows](matrix.csv) remain byte-identical to commit `3928653` (SHA-256 `21127c09be9e81a5237df6ff02d96da71b9d65e17af69b4075a25c5a6854ed8f`); new rows follow them.

The [freeze-2 run ledger](../../results/raw/bench/e1-freeze2-20261109/runs.json) covers the same [52](metrics.json) synthetic and exposed DEV cases run at freeze 1. It stores both full-input and circuit-withheld commands, stdout hashes, statuses, and the exact file list withheld from each input. The ablation removed [66 `.circom` and 58 `.nr` files](../../results/raw/bench/e1-freeze2-20261109/runs.json), plus any matching circuit artifact suffixes, from temporary projections; [all 52](../../results/raw/bench/e1-freeze2-20261109/runs.json) projections were deleted. All [104](../../results/raw/bench/e1-freeze2-20261109/runs.json) analyzer invocations completed. The [per-case, per-pattern file](freeze-patterns.csv) gives P1–P5 verdicts for all three modes and links each raw result.

On the frozen **AI-PROPOSED** scoring target, freeze 1 and freeze 2 have [identical outcomes on all 52 cases](metrics.json). Counts below are DETECT / MISS / FALSE-ALARM / CLEAR / UNKNOWN / ERROR; the same [buildability gate](../../results/raw/bench/e1-build-20261109-verified/build.json) applies to both freezes. The circuit-withheld mode has no scored decision. These are exploratory mock-verifier and exposed DEV results, not human-accepted Groth16 measurements.

| Frozen target | Freeze 1 | Freeze 2 | Freeze 2 without circuit |
|---|---:|---:|---:|
| P1 | [8/0/1/8/3/0](metrics.json) | [8/0/1/8/3/0](metrics.json) | [0/0/0/0/20/0](metrics.json) |
| P3 | [4/2/0/5/5/0](metrics.json) | [4/2/0/5/5/0](metrics.json) | [0/0/0/0/16/0](metrics.json) |
| P5 | [0/1/0/1/2/0](metrics.json) | [0/1/0/1/2/0](metrics.json) | [0/0/0/0/4/0](metrics.json) |
| R-COMMITMENT | [0/0/0/0/4/0](metrics.json) | [0/0/0/0/4/0](metrics.json) | [0/0/0/0/4/0](metrics.json) |
| R-EXTENT | [0/0/0/0/6/0](metrics.json) | [0/0/0/0/6/0](metrics.json) | [0/0/0/0/6/0](metrics.json) |
| R-MASK | [0/0/0/0/2/0](metrics.json) | [0/0/0/0/2/0](metrics.json) | [0/0/0/0/2/0](metrics.json) |

For the scatter data, freeze 1 and freeze 2 each have [12/13 target-warning precision and 30/52 decided cases](metrics.json); each discriminates [10/26 AI-proposed pairs](metrics.json). The circuit-withheld mode has [0/52 decided cases](metrics.json) and precision **MISSING**. The [apparent unsafe-certification IDs](metrics.json) are ADV-V14 and ADV-V15 in both full-input freezes.

Across [all 52 inputs per pattern](metrics.json), the [per-pattern transitions](metrics.json) are: P1 retains [16 VIOLATION, 11 VERIFIED_WITHIN_SCOPE, 25 UNKNOWN](metrics.json) between freezes; P3 retains [4, 7, 41](metrics.json); P5 retains [2 VIOLATION and 50 UNKNOWN](metrics.json); P2 and P4 remain [52 UNKNOWN each](metrics.json). With circuit input withheld, every P1, P3, and P5 positive becomes UNKNOWN ([16 and 11](metrics.json), [4 and 7](metrics.json), and [2](metrics.json), respectively); P2 and P4 remain UNKNOWN. This shows that the positive decisions observed here depend on the circuit input. It does not show circuit dependence for P2 or P4, because neither had a positive full-input decision.

Freeze 2's declared P4 source-key correction is therefore not exercised by the [current E1 case set](freeze-patterns.csv); the unchanged E1 outcomes do not measure that correction.

The two apparent unsafe-certification rows require a narrower reading. The [frozen AI expectation](../../benchmark/cases/ADV-V14/case.json) tags ADV-V14 and [ADV-V15](../../benchmark/cases/ADV-V15/case.json) as P3 vulnerable at `circuit.circom`; the underlying policy asks for chain/contract domain binding, a P2 obligation. The [per-pattern output](freeze-patterns.csv) is identical for each case:

| Pattern | Freeze 1 | Freeze 2 | Circuit withheld |
|---|---|---|---|
| P1 | [UNKNOWN](freeze-patterns.csv) | [UNKNOWN](freeze-patterns.csv) | [UNKNOWN](freeze-patterns.csv) |
| P2 (domain binding) | [UNKNOWN](freeze-patterns.csv) | [UNKNOWN](freeze-patterns.csv) | [UNKNOWN](freeze-patterns.csv) |
| P3 (canonical replay key) | [VERIFIED_WITHIN_SCOPE](freeze-patterns.csv) | [VERIFIED_WITHIN_SCOPE](freeze-patterns.csv) | [UNKNOWN](freeze-patterns.csv) |
| P4 | [UNKNOWN](freeze-patterns.csv) | [UNKNOWN](freeze-patterns.csv) | [UNKNOWN](freeze-patterns.csv) |
| P5 | [UNKNOWN](freeze-patterns.csv) | [UNKNOWN](freeze-patterns.csv) | [UNKNOWN](freeze-patterns.csv) |

The frozen scorer flags the P3 MISS on each vulnerable case as apparent unsafe certification because its expected-pattern field is P3. BindCheck did **not** certify P2 or the application-level domain-binding policy. The labels and scoring rules remain frozen; the mismatch is exposed here for human adjudication. The synthetic verifier is a mock, so this is not an end-to-end exploit or proof of unsoundness.

## Pinned public triples and current tool runs

The [public manifests](../../benchmark/public-triples/) pin both revisions of every [gate pair](../../gate/GATE-MANIFEST.csv) to an exact repository commit and SHA-256 for each present circuit, verifier, consumer, intermediary, and target source. They retain the exact compile commands, stdout/stderr hashes, exit statuses, dependency lock hashes, and a structural blocker where a Circom/Groth16 source triple cannot be established. The [fetch](../../results/raw/bench/public-fetch-20261109/fetch.json) and [checkout](../../results/raw/bench/public-fetch-20261109/checkouts.json) ledgers cover [26 distinct repository commits](metrics.json); [16 pairs and 32 revision slots](metrics.json) are represented. The source correspondence is established only at the source-call level; no proving-key/verifying-key identity or real proof acceptance is shown. The manifest's proposed pattern/location is explicitly **unscored** and every case label remains **PENDING**.

| Pair | Vulnerable / repaired buildability | Source correspondence or exact blocker |
|---|---|---|
| [GATE-14](../../benchmark/public-triples/GATE-14/manifest.json) | structural / structural | MACI has a verifier template and dynamic VK, with no committed tallyVotes-specific generated verifier; the gate card points at a different processMessages fix. |
| [GATE-15](../../benchmark/public-triples/GATE-15/manifest.json) | OK / OK | Self disclosure main, named Groth16 verifier, and hub consumer compile; key identity unproved. |
| [GATE-20](../../benchmark/public-triples/GATE-20/manifest.json) | structural / structural | Membership template has no main and no matched verifier/consumer; committed VAnchor verifiers are for other circuits. |
| [GATE-21](../../benchmark/public-triples/GATE-21/manifest.json) | structural / structural | Semaphore verifier symlink target and required verification key are absent from the pinned tree. |
| [GATE-22](../../benchmark/public-triples/GATE-22/manifest.json) | structural / structural | All three sources compile, but the generated zkDrops verifier is **PLONK**, outside Groth16. |
| [GATE-24](../../benchmark/public-triples/GATE-24/manifest.json) | structural / structural | Payy uses Noir/UltraHonk, outside Circom/Groth16. |
| [GATE-28](../../benchmark/public-triples/GATE-28/manifest.json) | timeout / timeout | EmailAuth source triple present; Circom compile reached the bounded timeout. |
| [GATE-29](../../benchmark/public-triples/GATE-29/manifest.json) | timeout / timeout | Same source-linked EmailAuth family; Circom compile timed out. |
| [GATE-30](../../benchmark/public-triples/GATE-30/manifest.json) | timeout / timeout | Same source-linked EmailAuth family; Circom compile timed out. |
| [GATE-31](../../benchmark/public-triples/GATE-31/manifest.json) | timeout / failed | Repaired revision's locked package URL returned [HTTP 402](../../results/raw/bench/public-deps-20261109/zkemail__ether-email-auth/4e2f119a428b/stderr); the circuit and consumer imports are unresolved. |
| [GATE-32](../../benchmark/public-triples/GATE-32/manifest.json) | timeout / timeout | Same source-linked EmailAuth family; Circom compile timed out. |
| [GATE-33](../../benchmark/public-triples/GATE-33/manifest.json) | timeout / timeout | Same source-linked EmailAuth family; Circom compile timed out. |
| [GATE-36](../../benchmark/public-triples/GATE-36/manifest.json) | OK / OK | Semaphore main, embedded-key verifier, and SemaphoreCore consumer compile with locked circomlib; key identity unproved. |
| [GATE-38](../../benchmark/public-triples/GATE-38/manifest.json) | structural / structural | Neither revision has a Circom source or generated Groth16 verifier; only a test mock is present. |
| [GATE-40](../../benchmark/public-triples/GATE-40/manifest.json) | timeout / failed | Repaired revision's locked archive URL returned [HTTP 404](../../results/raw/bench/public-deps-20261109/zkemail__ether-email-auth/984b5919a9be/stderr); the circuit and consumer imports are unresolved. |
| [GATE-47](../../benchmark/public-triples/GATE-47/manifest.json) | timeout / timeout | Self register-ID main, named verifier, and hub consumer are pinned; the main circuit compile timed out. |

Thus [4 revision slots are BUILD_OK, 14 BUILD_TIMEOUT, 2 BUILD_FAILED, and 12 STRUCTURAL_BLOCKED](metrics.json). The [role-level build statuses](metrics.json) preserve successes within a blocked triple: for example, both [zkDrops revisions](../../benchmark/public-triples/GATE-22/manifest.json) compile, but are PLONK. A timeout is neither a successful build nor a vulnerability verdict. The [GATE-31](../../benchmark/public-triples/GATE-31/manifest.json) and [GATE-40](../../benchmark/public-triples/GATE-40/manifest.json) failed-side manifests retain the exact missing imports and failed locked dependency commands. The [GATE-36 dependency receipt](../../results/raw/bench/public-deps-20261109/gate36/receipt.json) checks circomlib's integrity against the lock. Email and Self dependency attempts, including the initial Node engine failure and fixed URL failures, remain in the [dependency ledgers](../../results/raw/bench/public-deps-20261109/).

The [pinned public run ledgers](../../results/raw/bench/e1-public-20261109/) cover all [32 revision slots](metrics.json) with A/B/C, Slither default, Circomspect, Picus, zkFuzz, ZKAP availability, and BindCheck freeze 2. [Eight outer command exit statuses](metrics.json) are **MISSING**: four EmailAuth outputs were recovered after an interrupted parent campaign and four identical vulnerable-commit outputs were reused for other gate rows. The native outputs and source-hash equality are retained in the [EmailAuth recovery ledger](../../results/raw/bench/e1-public-20261109/runs-email.json); no exit code was inferred. Slither retries with explicit compiler/include paths are retained in the [Self](../../results/raw/bench/e1-public-20261109/slither-self-retry2.json) and [EmailAuth](../../results/raw/bench/e1-public-20261109/slither-email-retry2.json) ledgers. Native Slither findings have no binding-property interface, so they remain UNKNOWN. ZKAP's [32 unavailable slots](metrics.json) follow the recorded [host preflight](../redteam/manifests/zkap-preflight.json). Every [public Picus invocation's private temporary directory was removed](../../results/raw/bench/verification-freeze2-public-20261109.json).

The full-tree arm B selection cap omitted the register-ID main on [GATE-47](../../benchmark/public-triples/GATE-47/manifest.json), so a [targeted supplemental run](../../results/raw/bench/e1-public-targeted-20261109/runs.json) projected that exact circuit/verifier/consumer with local include closure and reran the arms on both revisions. Its B coverage lists the register-ID main; the supplemental result is not silently substituted for the full-tree matrix. BindCheck freeze 2 reports `ANALYSIS_FAILED` for the [EmailAuth](../../results/raw/bench/e1-public-20261109/GATE-28/vulnerable/bindcheck.stdout) and [Self](../../results/raw/bench/e1-public-20261109/GATE-15/vulnerable/bindcheck.stdout) worktrees when its include-link staging fails inside the temporary directory. This is an analyzer setup bug, recorded here without modifying `bindcheck_zk/` and scored UNKNOWN.

The [new pinned-public matrix rows](matrix.csv) contain [288 PENDING/UNKNOWN outcomes](../../results/raw/bench/verification-freeze2-public-20261109.json): each of the [nine tools](../../results/raw/bench/verification-freeze2-public-20261109.json) has [32](metrics.json) slots. The original snapshot-only PENDING rows remain in the frozen prefix; the `-pinned` tool names and `BindCheck-F2` distinguish these new runs. The [raw BindCheck per-pattern file](public-patterns.csv) contains [one P3 VIOLATION, one P3 VERIFIED_WITHIN_SCOPE, six P4 VERIFIED_WITHIN_SCOPE, and two P5 VERIFIED_WITHIN_SCOPE](metrics.json) across the public slots; P1/P2 remain UNKNOWN throughout. These are **unscored native outputs**, including observations on structurally blocked revisions, and cannot be called detections, safe certifications of a complete application, precision, or pair discrimination. The HUMAN-ACCEPTED precision/decided-rate scatter point and unsafe-certification count remain **MISSING** until reviewer labels and buildable in-scope triples exist.

The exact per-invocation commands, including retries, are in the [public run ledgers](../../results/raw/bench/e1-public-20261109/), [audit manifests](../../benchmark/public-triples/), and [dependency ledgers](../../results/raw/bench/public-deps-20261109/); tool versions are in the [version record](../../results/raw/bench/public-tools-20261109.json). The principal reproducibility entrypoints were:

    /opt/homebrew/bin/python3 benchmark/fetch_public.py
    /opt/homebrew/bin/python3 benchmark/checkout_public.py
    /opt/homebrew/bin/python3 benchmark/audit_public.py
    /opt/homebrew/bin/python3 benchmark/install_public_deps.py --repo zkemail/ether-email-auth --jobs 1
    /opt/homebrew/bin/python3 benchmark/install_public_deps.py --repo selfxyz/self --jobs 1
    /opt/homebrew/bin/python3 benchmark/install_g36_circomlib.py
    /opt/homebrew/bin/python3 benchmark/refresh_public_builds.py --ids 28 29 30 31 32 33 40 --jobs 1
    /opt/homebrew/bin/python3 benchmark/refresh_public_builds.py --ids 15 47 --jobs 1
    /opt/homebrew/bin/python3 benchmark/finalize_public.py
    /opt/homebrew/bin/python3 benchmark/run_public.py --ids 14 20 21 22 24 36 38 --runs-name runs-structural.json --jobs 1
    /opt/homebrew/bin/python3 benchmark/run_public.py --ids 14 20 21 22 24 36 38 --runs-name runs-structural-zkfuzz.json --only-zkfuzz --jobs 1
    /opt/homebrew/bin/python3 benchmark/run_public.py --ids 15 47 --runs-name runs-self.json --jobs 1
    /opt/homebrew/bin/python3 benchmark/finish_public_email.py
    /opt/homebrew/bin/python3 benchmark/run_public_targeted.py
    /opt/homebrew/bin/python3 benchmark/rescore.py
    /opt/homebrew/bin/python3 benchmark/verify_freeze2_public.py
    /opt/homebrew/bin/python3 benchmark/cleanup_public.py

The public runner was split by source family and retried after setup corrections; each actual invocation, status, and source is recorded in the ledgers rather than inferred from this command summary. The [verification receipt](../../results/raw/bench/verification-freeze2-public-20261109.json) checks the unchanged scorer, byte-identical freeze-1 matrix prefix, case coverage, PENDING boundary, and Picus cleanup. The [cleanup receipt](../../results/raw/bench/public-fetch-20261109/cleanup.json) verifies [111 pinned role hashes and removal of all 27 temporary worktrees](../../results/raw/bench/public-fetch-20261109/cleanup.json), including the manual source checkout; the bare fetch caches were removed and raw logs retained. A fresh `benchmark/rescore.py` run succeeded after cleanup.

## Limits, failed approaches, and next task

The first [build attempt](../../results/raw/bench/e1-build-20261109/build.json) passed the same Solidity directory twice and caused ambiguous imports. The [corrected attempt](../../results/raw/bench/e1-build-20261109-corrected/build.json) exposed the missing OpenZeppelin dependency; the final run used the package-lock integrity check. The first zkFuzz [cargo build --release --locked attempt](../../results/raw/bench/zkfuzz-setup-20261109/build.stderr) failed because upstream had no Cargo.lock; the subsequently generated [lock and successful build](../../results/raw/bench/zkfuzz-setup-20261109/provenance.json) are retained. Cargo was run in the temporary zkFuzz source checkout. Every attempt remains separate raw evidence.

The scorer measures E1 pattern/location decisions, not actual proof acceptance or committed effects. The synthetic fixtures use mock verifiers, the strongest baseline's Foundry checks also substitute an always-true verifier, and the DEV pair's PLONK verifier lacks a checked circuit-to-key correspondence. The new public source triples do not establish proving-key/verifying-key identity or real proof acceptance, and most revisions remain structurally blocked or build-unverified. These limits prevent a paper claim about precision, soundness, or comparative superiority on real Groth16 applications.

**Recommended next bounded task:** have the human reviewer resolve the [public cards](</Users/imranpollob/Coding/bc/bindcheck-zk/review/recall/INDEX.md>) as accept, edit, or drop, then transfer accepted pattern/location labels to the case metadata and run `benchmark/rescore.py`. Completion means no blank decision among the [16 gate cards](../../gate/GATE-MANIFEST.csv), human labels represented in the scored matrix, and a separate proof/key correspondence check for any public case promoted to an end-to-end Groth16 claim.
