# Held-out baseline tool setup

**Objective/status.** Prepare the already pinned local tools for the later gated run. No EVAL checkout or analyzer was used here. The first DEV harness smoke left Circomspect and Picus unavailable because this worktree had no local `tools/` paths; the [DEV result](../../results/raw/heldout/dev-harness-v2/families/001-0b92f4aa164b/family-result.json) remains preserved as setup evidence and is not a baseline miss.

The local ignored paths now contain copies of the Circom and Circomspect release binaries, and copies of the Picus source runner and its writable Racket package home, from the integration toolchain. The [tool provenance record](../../results/raw/heldout/dev-tools-smoke/provenance.json) gives matching source/local SHA-256 values and source revisions: Circom `7d0bd3cc…` from `ad44e915a12bb047b05745c2884aad9cc8326bc6`; Circomspect `c45398fc…` from `50010b623ed4f3bff9d1b0363cfe952385b47af3`; Picus runner `b34c0b65…` from `138b151d3a388e5b6c040c163e0a1db04f2ceda6`. The [circomlib tree pin](../../bindcheck_zk/vendor-lock.json) is the same ignored local copy used by the prebuild. No toolchain, dependency, or generated artifact was committed.

Local smoke commands and observed outcomes:

| Tool | Command and result |
| --- | --- |
| Circom | [`tools/circom-src/target/release/circom --version`: `circom compiler 2.2.3`, exit `0`](../../results/raw/heldout/dev-tools-smoke/circom.json) |
| Circomspect | [`tools/circomspect-src/target/release/circomspect --help`: exit `0`](../../results/raw/heldout/dev-tools-smoke/circomspect.json) |
| Picus | [`tools/picus-src/run-picus --help`: exit `0`, private `TMPDIR` removed](../../results/raw/heldout/dev-tools-smoke/picus-help.json) |
| Slither | [`slither --version`: `0.11.3`, exit `0`](../../results/raw/heldout/dev-tools-smoke/slither.json) |

The Picus help smoke used a private ignored temporary directory, a [20-second cap](../../results/raw/heldout/dev-tools-smoke/picus-help.json), and the evaluator's process-group timeout runner. This confirms the launcher starts; it is not a circuit analysis. ZKAP is still unavailable locally. The evaluator must record it as `UNKNOWN`, not as a miss. Tool usability on actual pinned family source is determined only by the later command records.

**Next task.** Complete the build-only preflight on the full preregistered family draw and verify its summary reports no remaining temporary checkouts. The held-out analyzer remains gated on the separate freeze-2 declaration.
