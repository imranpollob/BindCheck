# Held-out build-only preflight

**Objective/status.** Completed the preregistered pinned-checkout and Circom compilation preflight on the [selected family draw](selected-families.csv), before any EVAL analyzer or arm C run. The controlling pass is [prebuild v2](../../results/raw/heldout/prebuild-v2/summary.json); the aborted setup pass and its missing-dependency correction remain separately documented in [PREBUILD-SETUP.md](PREBUILD-SETUP.md). The exact [summary](prebuild-summary.json) and one-row-per-family [status and failure ledger](prebuild-status.csv) are tracked copies/derivatives of the ignored raw records. The latter gives a raw-record path, pinned revision, attempts, exit statuses, timeout flags, and compiler diagnostics for each family.

| Family preflight status | Families | Meaning |
| --- | ---: | --- |
| `BUILT` | [163](prebuild-summary.json) | At least one capped recorded entry circuit produced both R1CS and symbol files. |
| `BUILD_FAILED` | [46](prebuild-summary.json) | A recorded entry was attempted, but no attempt produced both files within the cap. |
| `NO_ENTRY_CIRCOM` | [68](prebuild-summary.json) | No existing recorded `.circom` path had a detected main component. |
| `EXPOSED_EXCLUDED` | [1](prebuild-summary.json) | Preregistered rank [259](prebuild-status.csv), `selfxyz/self`, was not acquired or compiled. |
| Total draw | [278](prebuild-summary.json) | No replacement family. |

These are build-only outcomes, not security verdicts or later analyzability. `BUILD_FAILED` and `NO_ENTRY_CIRCOM` are not BindCheck or arm C misses. The [family ledger](prebuild-status.csv) records the failure cause for every non-build row. For example, the [rank 34 raw record](../../results/raw/heldout/prebuild-v2/families/034-d68515b64d50/prebuild.json) shows unresolved bare Circom imports, including `poseidon.circom`; the prebuild used the analyzer's include resolver on preregistered corpus paths and did not add a new search path. Other compiler errors and timeouts are retained per attempt in the [raw family records](../../results/raw/heldout/prebuild-v2/families/).

The [summary](prebuild-summary.json) reports [zero remaining temporary checkouts](prebuild-summary.json). Every one of the [278 family records](prebuild-status.csv) marks its checkout deleted; generated R1CS and symbol files were discarded after each attempt. No downloaded checkout, dependency, or generated proof was committed.

## Reproduction and limits

The controlling command, run from this worktree, was:

```sh
PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3 eval/prebuild_heldout.py --output results/raw/heldout/prebuild-v2 --circom /Users/imranpollob/Coding/bc/bindcheck-zk/tools/circom-src/target/release/circom --jobs 2 > results/raw/heldout/prebuild-v2-run.log 2>&1
```

It exited [0](../../results/raw/heldout/prebuild-v2/command-record.json). The [command record](../../results/raw/heldout/prebuild-v2/command-record.json) retains the script and log hashes, Python version, and Git version. The [summary](prebuild-summary.json) pins the draw SHA-256, source-ledger SHA-256, Circom binary SHA-256, pinned `circomlib` tree SHA-256, [two workers](prebuild-summary.json), [at most two builds per family](prebuild-summary.json), and a [30-second timeout per build](prebuild-summary.json). Full argv, stdout, stderr, elapsed time, and exit status for each compiler attempt are in the per-family raw `prebuild.json` files referenced by the [status ledger](prebuild-status.csv). The prebuild script is [prebuild_heldout.py](../../eval/prebuild_heldout.py), and the acquisition routine is [run_heldout.py](../../eval/run_heldout.py).

**Unexpected observation and next task.** The first pass lacked the pinned local Circom dependency and was stopped; the controlling pass used the matching vendor tree. The remaining build failures are recorded without substitution or retry. The next measurable task is to wait for a committed `docs/FREEZE-2.md` on `zk-integration`, merge that frozen revision, record its analyzer hash in a preregistration addendum, create the required annotated local tags, pass the EVAL gate, then execute the full draw once. Until that declaration exists, no held-out analyzer or arm C run is authorized by this protocol.
