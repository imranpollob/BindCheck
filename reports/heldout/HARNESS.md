# E2 harness correction — DEV validation

**Objective/status.** Complete the evaluation harness correction before held-out analysis. The evaluator now keeps the research contract's three verdicts separate from applicability and reports each P1–P5 pattern independently. This is a DEV harness result, not a held-out or security finding.

The precommitted oracle is commit `9e80ef8f7c6ebf89816d115ef16841bf98dca8f5` in [test_eval_harness.py](../../tests/test_eval_harness.py). The implementation is [common.py](../../eval/common.py), [summarize.py](../../eval/summarize.py), and [run_heldout.py](../../eval/run_heldout.py). No file under `bindcheck_zk/` changed. The user instruction to leave `README.md` and `docs/project-status.md` untouched controls over the project checkpoint instruction in `AGENTS.md`.

`aggregate_payload_verdict` now accepts one pattern. The normalized record retains that pattern's verdict, applicability, reasons, unresolved triple reasons, and unknown reason codes. Missing or failed tool output is `UNKNOWN` with unknown applicability. The summary includes a verdict-by-applicability matrix and reason counts per pattern; baseline tool status is reported in a separate scope. `NOT_APPLICABLE` is never emitted as a verdict. A private `TMPDIR` is created for each Picus invocation and removed when it ends; the command runner already uses a process group and terminates it on timeout.

**DEV validation.** The exact command was:

```sh
BINDCHECK_CIRCOM=/Users/imranpollob/Coding/bc/bindcheck-zk/tools/circom-src/target/release/circom PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3 eval/run_heldout.py --split DEV --max-families 1 --output results/raw/heldout/dev-harness-v2
PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3 eval/summarize.py results/raw/heldout/dev-harness-v2 --bootstrap-replicates 0
```

Both commands exited `0`; the [run manifest](../../results/raw/heldout/dev-harness-v2/run-manifest.json), [family result](../../results/raw/heldout/dev-harness-v2/families/001-0b92f4aa164b/family-result.json), and [summary](../../results/raw/heldout/dev-harness-v2/summary.json) are retained under ignored raw evidence. The selected DEV family and pinned revision are in [selected-families.csv](../../results/raw/heldout/dev-harness-v2/selected-families.csv). Its checkout was deleted after analysis. The summary records P3 as `VIOLATION/APPLICABLE` and P1, P2, P4, P5 as `UNKNOWN/APPLICABLE`, each with its own reason codes. These are source-level analyzer outputs; they were not adjudicated as findings. Circomspect, Picus, and ZKAP were unavailable, while Slither failed; all remain `UNKNOWN` with unknown applicability in the [family result](../../results/raw/heldout/dev-harness-v2/families/001-0b92f4aa164b/family-result.json). No Picus process ran in this smoke test, so temporary-directory cleanup was exercised only by code inspection and not by a live Picus invocation.

The [verification record](../../results/raw/heldout/harness-verification.json) contains exact argv, working directory, outputs, exit statuses, Python/Git versions, and source revision for the test, compile, and diff checks; its SHA-256 is `a0719bba6e7bc179decdb5d58026906d3a0934d42f8c8a4431d0bfbdd32aff6b`. The tests, compile check, and diff check all exited `0`. No EVAL analysis or EVAL checkout was used.

**Limitations and next task.** The normalization of baseline native findings still requires source-level adjudication; a baseline `UNKNOWN` is not a miss. The next bounded task is the passive verifier census: commit synthetic classification expectations before processing the source corpus, then emit a per-verifier evidence ledger and per-class counts with explicit missing-source denominators.
