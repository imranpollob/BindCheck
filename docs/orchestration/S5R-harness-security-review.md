# S5R — Security review of the reserve harness before the one-shot held-out run

## Research context and authorization (read first)

Authorized defensive research for an academic paper (IEEE EuroS&P 2027). You are
an independent reviewer. **Read-only review.** Do not run the evaluation, and do
not clone, fetch or open any reserve repository.

The held-out v3 run can be done exactly once. The harness change S5H
(`reports/S5H/REPORT.md`, including its "Reviewer changes" section) adds a
reserve entry point (`eval/reserve.py`), a narrow exception in the hold-out
guard (`scripts/check_holdout.py`) and a prebuild change
(`eval/prebuild_heldout.py`). Preregistration: `reports/S5/PREREG.md`;
manifest: `reports/S5/reserve-manifest.csv` (1,105 units).

**Branch / worktree:** `sprint/S5R`, `$BC/wt-S5R` (contains S5H). **Owns:**
`reports/S5R/` only. **Edit no code.** Review: `git diff origin/main -- eval/ scripts/ tests/s5h/`.

## Answer only these questions (file:line for each)

1. **Spent-family contamination.** Can any path select, acquire or analyze a
   unit whose (repository, commit) is among the 278 spent pairs in
   `reports/heldout/selected-families.csv`, or WarpToad, or any repository not on
   the manifest?
2. **Guard bypass.** Does the default `check_holdout.py` refusal remain
   unchanged for every caller other than the authorized reserve path? Can the
   permit be forged, reused for a non-manifest repository, or obtained without
   `reports/S5/AUTHORIZATION.json` and the `s5-reserve-run` tag at HEAD?
3. **Frozen analyzer.** Can the run proceed with analyzer files that differ from
   the `freeze-3` tag, or with a different content hash?
4. **Silent drops.** Can any unit end without exactly one funnel status? Are
   harness failures kept separate from `UNSUPPORTED`?
5. **One-shot integrity.** Can a partial run be resumed against a different
   manifest, gate or toolchain, or can outputs be overwritten so that a second
   attempt looks like the first?
6. **Historical path.** Is the original freeze-2 path (`select_families`,
   `check_eval_gate`, `run_heldout.py`) unchanged in behavior?

Run offline: `python3 -m unittest discover -s tests/s5h -v` and
`python3 tests/s5h/revert_proof.py`.

Report a finding only if it can contaminate, bypass, drop, or repeat the
one-shot run. Put anything else on one line under "Minor".

## Output and reporting

`reports/S5R/REVIEW.md`: answers 1–6, findings (severity, file:line, scenario,
confidence), and one gate line `HARNESS CLEAR FOR S5` or
`HARNESS BLOCKED: <list>`, with the AI disclosure.

Do not commit. Do not call `hc`. The orchestrator reads your terminal: print as
the final line exactly `FINAL: S5R DONE` (or `FINAL: S5R BLOCKED: <reason>`).
