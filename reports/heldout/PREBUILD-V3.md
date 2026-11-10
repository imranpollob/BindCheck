# Controlling held-out build-only preflight

**Objective/status.** The dependency-corrected, build-only preflight completed on every row of the [preregistered draw](selected-families.csv), before any EVAL analyzer or arm C run. This v3 pass supersedes v2 **for build-only counts**; the [v2 report](PREBUILD.md), [setup correction](PREBUILD-VENDOR-CORRECTION.md), and raw passes remain preserved. The tracked [v3 summary](prebuild-summary-v3.json) is byte-identical to the raw [v3 summary](../../results/raw/heldout/prebuild-v3/summary.json). The [per-family v3 ledger](prebuild-status-v3.csv) carries the pinned revision, dependency setup, compile attempts and exit statuses, failure cause, checkout deletion status, and path to each full raw record.

| Family status | Count | Interpretation |
| --- | ---: | --- |
| `BUILT` | [163](prebuild-summary-v3.json) | At least one recorded entry circuit produced both R1CS and symbol files. |
| `BUILD_FAILED` | [46](prebuild-summary-v3.json) | No attempted entry circuit produced both files within the cap. |
| `NO_ENTRY_CIRCOM` | [68](prebuild-summary-v3.json) | No recorded existing Circom path was recognized as an entry circuit. |
| `EXPOSED_EXCLUDED` | [1](prebuild-summary-v3.json) | Exposed rank [259](prebuild-status-v3.csv) was neither cloned nor compiled. |
| Total | [278](prebuild-summary-v3.json) | No substituted families. |

There were [zero acquisition-failure or preflight-error statuses](prebuild-status-v3.csv). Dependency setup was [linked pinned vendor for 276 acquired families](prebuild-status-v3.csv), [preserved an existing matching vendor for 1](prebuild-status-v3.csv), and was [not performed for the 1 exposed exclusion](prebuild-status-v3.csv). The existing dependency's tree hash matched the [pinned vendor SHA-256](../../results/raw/heldout/prebuild-v3/families/069-174f9c00bd4f/dependency-setup.json). All [278 family records](prebuild-status-v3.csv) mark their checkouts deleted, and the [summary records zero remaining checkouts](prebuild-summary-v3.json).

The [v2-to-v3 comparison](../../results/raw/heldout/prebuild-v3/v2-v3-comparison.json) finds [zero family status changes](../../results/raw/heldout/prebuild-v3/v2-v3-comparison.json). The vendor link fixed the copied DEV-F34 Circomspect import check, but it did not change this sample's build-status funnel. Build failures still include source import and compiler errors; exact diagnostic excerpts and the full raw JSON locations are in the [family ledger](prebuild-status-v3.csv). A failed or absent build is coverage information, never a safe verdict, vulnerability label, or miss for any tool.

The exact command was:

```sh
PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3 eval/prebuild_heldout.py --output results/raw/heldout/prebuild-v3 --circom /Users/imranpollob/Coding/bc/bindcheck-zk/tools/circom-src/target/release/circom --jobs 2 > results/raw/heldout/prebuild-v3-run.log 2>&1
```

It exited [0](../../results/raw/heldout/prebuild-v3/command-record.json). The [command record](../../results/raw/heldout/prebuild-v3/command-record.json) contains the exact argv, working directory, Python/Git versions, script SHA-256, log SHA-256, and observed exit status. The [summary](prebuild-summary-v3.json) records the source and draw hashes, Circom binary and vendor tree hashes, [two workers](prebuild-summary-v3.json), [at most two compiler attempts per family](prebuild-summary-v3.json), and the [30-second per-attempt cap](prebuild-summary-v3.json). Full compiler argv, stdout, stderr, elapsed time, exit status, and timeout flag live in the ignored [raw family records](../../results/raw/heldout/prebuild-v3/families/).

**Assumptions and next task.** The preflight reads the corpus's recorded circuit paths; the later analyzer may discover other paths and can be analyzable even when this build-only result is `NO_ENTRY_CIRCOM`. The sample is a convenience source corpus, not a population estimate. The next task begins only after `docs/FREEZE-2.md` is committed on `zk-integration`: merge it locally, record the analyzer content hash in a dated preregistration addendum, create the annotated dataset and freeze tags, pass the EVAL gate, and execute the one-shot analyzer and arm C run on the unmodified draw.
