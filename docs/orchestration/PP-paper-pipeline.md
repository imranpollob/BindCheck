# PP — Reproducible paper tables, figures and artifact README

## Context (read first)

Academic paper (IEEE EuroS&P 2027) on BindCheck, a static analyzer for
zero-knowledge binding flaws. This task is pure data plumbing and
documentation: no analyzer changes, no network.

**Goal.** Every number in the paper must come from a tracked file by one
command, so authors and artifact reviewers can regenerate it. Hand-copied
numbers are the most common source of errors in papers.

**Branch / worktree:** `sprint/PP`, `$BC/wt-PP`.

**Owns:** `scripts/paper/`, `paper/generated/`, `ARTIFACT.md`, `reports/PP/`,
`Makefile` (a `paper-tables` target only; create the file if it is missing).

**Must not edit:** anything else. Read-only for all reports and CSVs.

## Steps

1. Inventory the tracked evidence the paper will cite. At minimum:
   - `reports/R1/incidents.csv` (incident census);
   - `reports/R2/findings.csv` (audit census);
   - `reports/AZ1/REPORT.md` tables (tool × target × verdict, testbed);
   - `reports/S2a/revision1/*` (DEV ledger, Set-H precision);
   - `reports/S4/*` (oracle operator × case matrix, runtimes);
   - `reports/labels/*`, `reports/heldout/*` (freeze-2 numbers, labelled as spent/DEV);
   - `docs/FREEZE-2.md` (hashes).
   List each source with path, row count and sha256 in `reports/PP/INVENTORY.md`.
2. `scripts/paper/build.py` (stdlib Python 3.12, or pandas only if it is
   already installed): one function per table or figure. Each writes
   `paper/generated/<name>.tex` (booktabs `tabular`, no float wrapper) and a
   `<name>.json` with the raw numbers plus source paths and hashes.
   Initial set:
   - T-incidents: R1 cases by class (P1–P5, other), with loss totals;
   - T-audits: R2 binding findings by severity, and "needs circuit" share;
   - T-aztec-tools: AZ1 tool × target × verdict;
   - T-dev-precision: per-pattern DEV numbers, freeze 2 vs current candidate,
     labelled "DEV, not held-out";
   - T-oracle: S4 operator × case matrix;
   - T-generators: placeholder that reads `reports/S1/generators.csv` if it
     exists, else emits a clearly marked TODO table.
   Parse markdown tables only where no CSV exists, and note that in the JSON.
3. `\newcommand` macros file `paper/generated/numbers.tex` for every scalar the
   text cites (e.g. `\AztecLossUSD`, `\RoneCases`), each with a comment giving
   its source.
4. `make paper-tables` runs it all. Running it twice must give byte-identical output.
5. A `scripts/paper/check.py` that fails if a generated file is stale relative
   to its sources (hash mismatch).
6. `ARTIFACT.md`: how an artifact reviewer installs the toolchain
   (`scripts/setup_linux_tools.sh`), runs the analyzer tests, the AZ1 testbed
   (`prototypes/az1/run.sh`), the oracle, and `make paper-tables`. State
   expected runtimes and outputs. Mark any step that needs data the public
   artifact cannot ship (e.g. `dataset/onchain-census.csv` stays private).
   Never print addresses from it.

## Environment limits

No network. Do not `git commit` or push; leave changes in the working tree for
the reviewer.

## Completion criteria

- `make paper-tables` works from a clean checkout and is deterministic.
- Every generated number traces back to a source file and hash.
- Any count that disagrees with the number a report states in prose goes in
  `reports/PP/DISCREPANCIES.md`. Do not "fix" the reports.
- `reports/PP/REPORT.md` in the handoff template, with the AI disclosure.
- Final line of your session: `PP DONE` or `PP BLOCKED: <reason>`.
