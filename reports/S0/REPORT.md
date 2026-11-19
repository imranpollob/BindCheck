# S0 — Research contract revision 4 and analyzer freeze-3 preparation

Status: DONE

Verdict/outcome: Analyzer hash matched and all 77 required tests passed. Revision 4 and the analyzer-only freeze declaration are ready for reviewer tagging. S0 produced no held-out or E4 result.

## What was done

- Updated the [research contract](../../docs/research-contract.md) prospectively and preserved its previous bytes in the [revision-3 archive](../../docs/history/research-contract-2026-10-28.md) (moved there by the reviewer). The original revision-3 path at the starting commit remains the base for its relative links.
- Prepared the [freeze declaration](../../docs/FREEZE-3.md) with the exact analyzer scope, pins, repeatable validation command and F1's 56-row DEV results. Updated the shared [project checkpoint](../../docs/project-status.md) as required by AGENTS.md and preserved its prior bytes in the raw directory.
- Left the working tree uncommitted for the reviewer. S0 made no code changes, created no tag and performed no push.

AI disclosure: OpenAI Codex, GPT-6 family, inspected repository evidence, ran the hash and tests, and drafted the documents. The exact serving variant was unavailable. Human author review is pending.

## Evidence

Worktree `/home/pollmix/Coding/bc/wt-S0`, branch `sprint/S0`, initial HEAD `9d340eb362090415b9c68b7eeab720a1bc3a0a74`. Initial `git status --short --branch` showed no changes. Commands below ran from this root. Raw logs are under ignored `results/raw/S0/`.

```sh
python3 -m bindcheck_zk.freeze > results/raw/S0/freeze.txt
BINDCHECK_CIRCOM=/home/pollmix/Coding/bc/BindCheck/tools/circom-2.1.9/target/release/circom \
  python3 -m unittest tests.test_bindcheck_zk_cli tests.test_bindcheck_zk_controls \
  tests.soundness.test_verdict_soundness tests.soundness.test_followup \
  tests.coverage.test_rules tests.freeze2.test_p4_key tests.s2a.test_precision_fixes \
  tests.s2a2.test_residual_p5 tests.s2c.test_extent tests.f1.test_analyzer_soundness \
  -v > results/raw/S0/suite.log 2>&1
python3 --version
git --version
uname -sm
/home/pollmix/Coding/bc/BindCheck/tools/circom-2.1.9/target/release/circom --version
sha256sum /home/pollmix/Coding/bc/BindCheck/tools/circom-2.1.9/target/release/circom
python3 -c 'from bindcheck_zk.circuits import _vendor_libraries; print(sorted(_vendor_libraries()))'
git show HEAD:docs/research-contract.md | cmp - docs/history/research-contract-2026-10-28.md
git show HEAD:docs/project-status.md | cmp - results/raw/S0/project-status.before.md
git diff --check
```

| Evidence | SHA-256 |
| --- | --- |
| Freeze command log, `results/raw/S0/freeze.txt` | `859fb5f0a30b22cb033a682db355e40b37fb33330a7ed41ab8865786e5d5faab` |
| Full test log, `results/raw/S0/suite.log` | `5a76faecff0740319382c46e725ab667d848c5ea5163e83c1c36412b0dfdfd3f` |
| Revision-3 archive | `956985e6da44ddc85f80fc0bc8f0bf93b02ca926e35dad27beb3ed6d3d576eae` |
| Checkpoint before editing, `results/raw/S0/project-status.before.md` | `df7981aa6296d94dd9a354ea5e90bfbf0643bf746b50514b9ed764b846fea76a` |

## Results

| Check | Observed result |
| --- | --- |
| Analyzer identity | `753c6e2a0f3f75255eb2fdc354402f3ef7aac1541206b0794a9d09cd7d485315`, exact S0 match, exit 0 |
| Full F1 module list | 10 modules, 77 tests passed in 26.873 seconds, exit 0 |
| Environment and library lock | Linux x86_64, Python 3.12.12, Git 2.43.0, Circom 2.1.9. The compiler digest matched T0 and the analyzer recognized the locked circomlib tree. Commands exited 0. [Pins](../../docs/FREEZE-3.md#validation-and-toolchain-pins) |
| Preservation | Both archived documents matched their starting Git blobs byte-for-byte. Both comparisons and the diff whitespace check exited 0. |

The [freeze-3 DEV table](../../docs/FREEZE-3.md#dev--development-data-not-held-out) reproduces F1's exact row counts for all six patterns. Its source is the F1 candidate run, after-ledger SHA-256 `33c1dce51ee65b979f67aab81bb28997b024a4c4f416e62b80931fe71de81707`. [F1](../F1/REPORT.md#original-56-dev-rows)

## Assumptions and limitations

S0 verified content identity and analyzer regressions. It carried forward F1's development measurements without rerunning the corpus. XR2 closed the four original analyzer findings within its review scope. Source-level checks, including AZ1 P1-EXTENT, retain their recorded evidence grades. Oracle E4 counts require the F3 fixes and a passing XR3 review. The older README status and hash describe earlier analyzer snapshots. Revision 4 and the freeze-3 declaration control prospectively. [XR2](../XR2/REVERIFY.md) and [reviewer decision](../../docs/orchestration/DECISIONS.md)

## Failed approaches / surprises

Both S0 gates passed on the first attempt. Two differences between planning records affect interpretation.

- XR2's overall gate verdict says freeze 3 was blocked by oracle findings. The subsequent reviewer decision authorizes freezing the analyzer independently and keeps the oracle gate closed. Both records retain their original wording. [XR2](../XR2/REVERIFY.md) and [decision log](../../docs/orchestration/DECISIONS.md)
- The earlier sprint plan identifies 391 audited or deployed families from the pool of 1,106. The S0 mandate specifies the 1,106 reserved families for the one-shot run. Revision 4 follows S0. S5 preregistration must identify the actual family manifest and distinguish any maturity-subset denominator from the full reserve. [Sprint plan](../../docs/sprint-eurosp-2027.md#untouched-held-out-pool) and [S0 mandate](../../docs/orchestration/S0-contract-rev4-freeze3.md)

## Held-out hygiene statement

S0 read repository-owned code, configuration, reports and test fixtures. The suite exercised synthetic controls, the AZ1 development pair and S2a2's retained development fixture packets. No external family checkout or unused EVAL family was opened. The 1,106-family pool remains reserved. S0 ran neither an oracle confirmation nor a held-out evaluation.

## Recommended next task

Reviewer acceptance and tagging. Completion requires the reviewer to verify the declared hash and revision-4 scope against this handoff, then create and push `freeze-3` at the accepted revision with the same analyzer content hash.
