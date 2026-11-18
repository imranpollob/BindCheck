# S2a2 — Residual P5 false positives on real code (DEV only)

## Research context (read first)

Authorized **defensive** research for an academic paper (IEEE EuroS&P 2027).
Static-analyzer engineering on development data. No network, no live systems.

**Why this task exists.** S2a revision 1 (`reports/S2a/REPORT.md`, section
Revision 1, and `reports/S2a/revision1/set-h-recomputed-cards.csv`) left P5
Set-H precision at 2/8 on DEV. Six FP cards still warn. **W0220 and W0253 were
reported as fixed** by minimal-excerpt regressions, but they still warn on the
real code. The excerpts did not reproduce the real cause. This task works on
**pinned real code only**.

| Card | Repository @ commit | Location |
|---|---|---|
| W0016 | oxor-io/zk-layer-vote @ 0589519 | on-chain/contracts/GovernorL1.sol:155 |
| W0220 | bunsenstraat/chainlink-workshop @ 9ded99d | contracts/hackergroup.sol:175 |
| W0253 | bunsenstraat/chainlink-workshop @ 9ded99d | contracts/hackergroup.sol:109 |
| W0333 | mihwuan/H-ZKA @ 3cdcfd7 | HZKA/contracts/ordinary_chain/TransferContract.sol:296 |
| W0349 | Cloakworks-collective/shadow_warfare @ 9aa1970 | contracts/src/AutoBattler.sol:81 |
| W0461 | Punith-KK/Kira @ 8a8ed58 | hardhat/contracts/Tazza.sol:61 |
| W0658 (timeout) | PhaseMirror/The-Foundry @ c718741 | packages/contracts/DataPointerRegistry.sol:61 |

The reviewer has guard-checked these (all ALLOWED) and pre-cloned them at the
pinned commits under `results/raw/S2a2/checkouts/<owner>__<repo>/`.

**Branch / worktree:** `sprint/S2a2`, `$BC/wt-S2a2`.

**Owns:** `bindcheck_zk/` (except `extent.py`), `tests/s2a2/`, `reports/S2a2/`,
`results/raw/S2a2/`.

**Must not edit:** `findings/`, `oracle/`, `prototypes/`, `bindcheck_zk/extent.py`.
Lane S2c is adding `extent.py` plus a small hook in `analyzer.py`. Avoid
unrelated refactors of `analyzer.py`.

## Steps

1. For each card, run the analyzer on the pinned checkout exactly as the
   harness did (see the Set-H matcher in `reports/S2a/revision1_analysis.py`)
   and reproduce the warning first. Record the command and output.
2. Find the root cause in the analyzer, with code path and line, and the facts
   in the target code that trigger it.
3. Fix the **general** cause. Never condition on a repository, file, contract
   or card ID. The reviewer greps for that.
4. Regression: copy the minimal set of **real** files from the checkout into
   `tests/s2a2/fixtures/<card>/` (keep license headers, record the source path
   and commit in a `SOURCE.txt`). Before fixing, confirm the regression warns
   exactly as the real checkout does. If it does not, the excerpt is wrong.
5. After the fix, rerun the real checkout and the regression.
6. W0658: retry with a longer timeout. If it still times out, record UNKNOWN
   (timeout) and the stage where time is spent.
7. Check that both P5 TP cards (W0412, W0668) remain VIOLATION, and that the
   original 56 DEV rows change no VIOLATION into a non-VIOLATION without a
   reason (rerun as in the S2a report, `--skip-fetch`).
8. Full test suite as in `docs/FREEZE-2.md` with
   `BINDCHECK_CIRCOM=$BC/BindCheck/tools/circom-2.1.9/target/release/circom`.

A card you cannot fix safely becomes a documented **accepted limitation**, with
its reason. A fix must never turn an unresolved fact into
`VERIFIED_WITHIN_SCOPE`: fail closed to `UNKNOWN`.

## Environment limits

- No network. Do not `git commit` or push (the sandbox cannot write the git
  directory). Leave changes in the working tree; the reviewer commits them.
- Run `python3 scripts/check_holdout.py <owner/repo>` before opening any other
  third-party repository.

## Completion criteria

- One row per card: reproduced (Y/N), root cause and code path, fix or
  limitation, verdict after.
- Both P5 TPs still VIOLATION; full suite green; DEV delta with reasons.
- `reports/S2a2/REPORT.md` in the handoff template, with the AI disclosure and
  the candidate hash (`python3 -m bindcheck_zk.freeze`). Do not declare a freeze.
- Final line of your session: `S2a2 DONE` or `S2a2 BLOCKED: <reason>`.
