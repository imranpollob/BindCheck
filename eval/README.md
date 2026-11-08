# One-shot held-out evaluation harness

This directory orchestrates the frozen `bindcheck-zk` JSON interface; it does
not modify the analyzer. EVAL analysis is an at-most-once operation. A failed,
timed-out, or interrupted acquisition/tool attempt becomes coverage
`UNKNOWN`; the harness never retries with path hints, a larger budget, or
different settings after seeing a result.

## Before the real run

1. Complete and record the required human review of EVAL eligibility, family
   membership, and maturity labels, including the 38 `verified-deployed`
   families, all inventory-incomplete rows, and the complete 278-family draw.
   Any correction must happen before analysis and requires a new ledger hash
   and documented sample refresh.
2. Independently review the 16 rows in `recall-expectations.csv`. For each row,
   supply one expected `P1`–`P5` predicate, a vulnerable-revision source
   location regex, reviewer/date, and `review_status=REVIEWED`. These labels
   are ground truth and must not be derived from analyzer output.
3. Commit the reviewed ledgers, expectations, harness, and any documentary
   updates. Confirm that `git status --short` has no tracked changes and that
   `./freeze.sh` still prints the reviewed analyzer digest.
4. Create the annotated dataset tag. Substitute the reviewed hashes if any
   pre-analysis correction changed a ledger:

   ```sh
   git tag -a bindcheck-zk-dataset-v2-YYYYMMDD \
     -m "SOURCE_CORPUS_V2_SHA256=07210625783a21a6128ea3f99402fc4a48b36922056241649999547a374b0c95" \
     -m "RECALL_SET_V2_SHA256=709021bc34020e33d22dbb449066435f1a3938da5c148ae666fa9e3aa0a604f9"
   ```

   The runner verifies both the annotation and the bytes stored at this tag.
5. Create the annotated operational freeze tag at the same `HEAD`. Obtain the
   last two hashes with `./freeze.sh | tail -1` and
   `shasum -a 256 eval/recall-expectations.csv`:

   ```sh
   git tag -a bindcheck-zk-frozen-YYYYMMDD \
     -m "BINDCHECK_ZK_CONTENT_SHA256=d8510859b918a5166d0f1629cf0d883e965fa0acb1be92a34987c24f1967ae13" \
     -m "SOURCE_CORPUS_V2_SHA256=07210625783a21a6128ea3f99402fc4a48b36922056241649999547a374b0c95" \
     -m "RECALL_SET_V2_SHA256=709021bc34020e33d22dbb449066435f1a3938da5c148ae666fa9e3aa0a604f9" \
     -m "RECALL_EXPECTATIONS_SHA256=<reviewed-expectations-sha256>"
   ```

Do not push either tag from this task. The EVAL runners require the explicit
environment authorization in addition to both local tags and all matching
hashes. A lightweight tag, a tag away from `HEAD`, stale dataset bytes, an
analyzer hash mismatch, or missing authorization refuses execution.

## Real held-out command

This single command writes the complete 278-family selection before launching
the first analyzer, shallow-fetches each pinned SHA, runs BindCheck plus
Slither/Circomspect/Picus and ZKAP when installed, and deletes each checkout:

```sh
BINDCHECK_EVAL_AUTHORIZED=1 python3 eval/run_heldout.py --split EVAL
```

If the process is interrupted, run the exact same command. Completed work is
reused. A tool with a pre-existing `started` marker is recorded as
`INTERRUPTED_ATTEMPT` and is not executed again. Do not change settings or add
path hints after inspecting outputs.

The stable output directory is
`results/raw/T26/heldout-07210625783a/`. Summarization does not execute a tool:

```sh
python3 eval/summarize.py results/raw/T26/heldout-07210625783a
```

It writes `summary.json` and `summary.md`, with per-stratum and overall
applicable/decided/verdict counts, arbitrary UNKNOWN reason codes,
family-resampled 95% intervals, and the baseline comparison table.

Run strict vulnerable/fixed recall only after the same freeze:

```sh
BINDCHECK_EVAL_AUTHORIZED=1 python3 eval/run_recall.py --split EVAL
```

The recall summary reports predicate detection (expected pattern is a
`VIOLATION` on vulnerable and not on fixed), source-location match, successful
compiled-relation builds on both revisions, and E4 counts separately. Static
E1 output cannot silently become E4.

## Runtime and disk expectations

The five-family DEV dry run on 2026-11-06 observed 25–192 seconds per family
(median about 90 seconds), including filtered fetch/checkout, analysis, and
baseline adapters. Checkouts were 21–129 MB (median 85 MB); retained JSON was
3.2 MB total. At that rate, 278 families take roughly 7–8 hours sequentially.
Allow **8–20 hours** because repository hydration and Slither dominate and
held-out repositories may be larger. The fixed worst-case envelope is 300
seconds each for fetch and checkout, 150 seconds for BindCheck, and 150 seconds
per baseline (ZKAP is skipped when absent), or about 22.5 minutes per family
when all four baselines are installed, plus bounded repository initialization.

Only one checkout exists at a time. Provision at least **5 GB transient free
space** for an unusually large repository and **2 GB** for retained JSON/logs;
the observed DEV peak checkout was 129 MB. Disk exhaustion or a timeout is
`UNKNOWN`, not a reason to rerun with a different budget.

## Metadata-only and DEV validation

The metadata-only command applies the exact EVAL draw but performs neither a
clone nor analysis and does not require analysis authorization:

```sh
python3 eval/run_heldout.py --split EVAL --metadata-only
```

On 2026-11-06 it resolved all 278/278 sampled GitHub commit objects to their
exact pinned SHA. The five-family full DEV validation command is:

```sh
python3 eval/run_heldout.py --split DEV --max-families 5 \
  --output results/raw/T26/dev-dry-run-network
python3 eval/summarize.py results/raw/T26/dev-dry-run-network
```

Focused local tests, including EVAL refusal without environment/tag/hash,
selection quotas, resumability, recall scoring, future reason codes, and
Cohen's kappa, run with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_eval_harness -v
```

## Blind warning adjudication

Follow `ADJUDICATION.md`. The preparation command creates two independent
sheets without tool confidence or any other-rater field. Labels are exactly
`TP`, `FP`, or `unclear`; `adjudicate.py kappa` validates paired coverage and
computes Cohen's kappa after both sheets are sealed.
