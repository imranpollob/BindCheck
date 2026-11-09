# E1 benchmark and comparative measurement

**Objective and status.** This lane froze a case inventory and location-sensitive scorer before running the committed comparison arms. The exploratory measurement is complete for locally available inputs. A paper-level Circom/Groth16 benchmark and human-accepted comparative result remain **MISSING**: every public card still has a blank reviewer decision, the retained public snapshots do not make a matched triple, and the development pair with a buildable verifier uses PLONK. No claimed E4 result or superiority follows from this campaign.

## Authority and population

The research contract controls the three security verdicts, the E0–E4 ladder, and treatment of unavailable inputs. The old [README](../../README.md) still names prior analyzer hashes and describes the D1 Noir line as current; the later [freeze declaration](../../docs/FREEZE-2026-11-09.md) and [environment record](environment.json) identify the Circom/Solidity analyzer actually measured here. This report does not rewrite historical results.

The [manifest](../../benchmark/manifest.json), [case files](../../benchmark/cases/), [source locks](../../benchmark/cases/), and [metrics](metrics.json) contain [68](metrics.json) case directories: [46](metrics.json) synthetic, [6](metrics.json) exposed DEV-history revisions, and [16](metrics.json) public-report pairs. The public pairs account for [32](metrics.json) revision slots; every card decision is PENDING. The synthetic labels are AI-PROPOSED and the same team authored arm C. The DEV-history labels are AI-PROPOSED and EXPOSED. Neither group is independent held-out ground truth.

The artifact audit corrected an initial manifest classification after the native runs, without changing a label or score rule. The zkDrops [verifier source](</Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev/DEV-H01--a16z__zkdrops--4002962fb632/contracts/compiled/MerkVerifier.sol>) says it is snarkJS-generated and declares PlonkVerifier. The final [case metadata](../../benchmark/cases/DEV-H01/case.json) therefore calls this PLONK, outside the requested Groth16 subset. The [protocol ledger](metrics.json) identifies [46](metrics.json) mock-verifier synthetic cases, [2](metrics.json) PLONK DEV revisions, [2](metrics.json) DEV revisions with no matched verifier, [2](metrics.json) UltraHonk DEV revisions, and [16](metrics.json) public pairs with unresolved protocol correspondence. These are inventory facts, not vulnerability labels.

## Buildability and scoring boundary

The [build ledger](../../results/raw/bench/e1-build-20261109-verified/build.json) checks each source lock and DEV checkout revision, and records the Circom and Solidity commands, hashes, exit statuses, and stderr. [All 46](metrics.json) synthetic sources compile, but their verifier is a simplified mock/interface; this is not a real Groth16 proof path. [Both zkDrops revisions](metrics.json) compile with the pinned OpenZeppelin tarball whose SHA-512 integrity matches their package lock. [Both Semaphore revisions](metrics.json) lack the generated verifier artifact. [Both Payy revisions](metrics.json) use Noir/UltraHonk. [All 32](metrics.json) public revision slots are MISSING_ARTIFACT because their retained snapshots do not contain a selected circuit, verifier, and consumer triple. No source failure was converted to a miss.

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

The [verification record](../../results/raw/bench/verification-20261109.json) reports successful lock, matrix-completeness, Picus-cleanup, scorer-test, compile, diff, and freeze checks. Its [case, file, matrix, and cleanup counts](../../results/raw/bench/verification-20261109.json) are derived by [verify.py](../../benchmark/verify.py). The [evidence index](evidence.json) seals the retained raw ledgers and tracked summaries with SHA-256 hashes.

After labels change, the single command

    /opt/homebrew/bin/python3 benchmark/rescore.py

regenerates [matrix.csv](matrix.csv) and [metrics.json](metrics.json) from the retained observations without rerunning a tool. The public reviewer must update the case label and expected pattern/location from the original card before doing so; AI proposals are not accepted labels.

The condition for the requested next run is not met: docs/FREEZE-2.md was absent from zk-integration when this report was finalized. There was no merge, freeze-2 measurement, or circuit-withheld ablation. Their results are **MISSING**; the current table must not be read as an ablation.

## Limits, failed approaches, and next task

The first [build attempt](../../results/raw/bench/e1-build-20261109/build.json) passed the same Solidity directory twice and caused ambiguous imports. The [corrected attempt](../../results/raw/bench/e1-build-20261109-corrected/build.json) exposed the missing OpenZeppelin dependency; the final run used the package-lock integrity check. The first zkFuzz [cargo build --release --locked attempt](../../results/raw/bench/zkfuzz-setup-20261109/build.stderr) failed because upstream had no Cargo.lock; the subsequently generated [lock and successful build](../../results/raw/bench/zkfuzz-setup-20261109/provenance.json) are retained. Cargo was run in the temporary zkFuzz source checkout. Every attempt remains separate raw evidence.

The scorer measures E1 pattern/location decisions, not actual proof acceptance or committed effects. The synthetic fixtures use mock verifiers, the strongest baseline's Foundry checks also substitute an always-true verifier, and the DEV pair's PLONK verifier lacks a checked circuit-to-key correspondence. The source snapshots are not full reproducible triples. These limits prevent a paper claim about precision, soundness, or comparative superiority on real Groth16 applications.

**Recommended next bounded task:** have the human reviewer resolve every [public card](</Users/imranpollob/Coding/bc/bindcheck-zk/review/recall/INDEX.md>) as accept, edit, or drop, then supply a pinned circuit, generated Groth16 verifier, and consumer with file hashes for each accepted pair. Completion means no blank decision among the [16 gate cards](../../gate/GATE-MANIFEST.csv) and a fresh build ledger that either compiles every accepted triple or records a specific MISSING/unsupported reason. Only then can the HUMAN-ACCEPTED headline be scored.
