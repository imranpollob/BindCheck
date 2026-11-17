# Orchestration: how this sprint runs

**Roles:**

- The **human author** runs AI coders, does the research tasks marked `H*`, and
  takes every policy, disclosure and scope decision.
- The **reviewer/orchestrator** (Claude, cloud session) writes task prompts,
  reviews every returned branch, and decides the next task.
- The **AI coders** execute one prompt each.

**Plan:** [`docs/sprint-eurosp-2027.md`](../sprint-eurosp-2027.md).

**Authority:** `docs/research-contract.md`, then `README.md`, then
`AGENTS.md`. A prompt never overrides them.

## Running a task

1. **Branch.** Start from `sprint/eurosp-2027-plan`:

   ```bash
   git switch -c sprint/<task-id> origin/sprint/eurosp-2027-plan
   ```

2. **Prompt the coder:**

   > Read `AGENTS.md`, then `docs/orchestration/<task-id>.md`, and execute it.

3. **Coder output.** The coder must finish with:
   - a task report at `reports/<task-id>/REPORT.md`, using the handoff template
     below;
   - tests passing;
   - raw logs under the ignored `results/raw/<task-id>/`;
   - a commit on the task branch.

   The coder must not touch files owned by another active task (see the table).
4. **Push** the branch, then tell the reviewer: "<task-id> pushed". The reviewer
   fetches it, reviews it against the prompt's completion criteria, and replies
   `ACCEPT`, `REVISE: <list>` or `STOP: <reason>`.
5. **Merge.** Only accepted branches are merged into `sprint/eurosp-2027-plan`.
   The human merges, or asks the reviewer to.

**Path note:** if the `bc/` folder sits at a new path on Mint, find the
hard-coded macOS paths and fix them once in a separate commit:

```bash
git grep -l "bc/bindcheck-zk/" -- '*.py' '*.sh'
```

## Active tasks and file ownership

| Task | Prompt | Status | Owns (may edit) | Must not edit |
|---|---|---|---|---|
| S1 | [S1-honk-canonicality.md](S1-honk-canonicality.md) | READY (priority 1) | `prototypes/s1-honk-canon/`, `reports/S1/` | `bindcheck_zk/` |
| S2a | [S2a-precision-fixes.md](S2a-precision-fixes.md) | READY (priority 2) | `bindcheck_zk/`, `tests/s2a/`, `reports/S2a/` | `findings/`, `oracle/` |
| S4 | [S4-execution-oracle.md](S4-execution-oracle.md) | READY (priority 2) | `oracle/`, `tests/oracle/`, `reports/S4/` | `bindcheck_zk/` |
| R1 | [R1-incident-census.md](R1-incident-census.md) | READY (priority 1) | `reports/R1/` | everything else |
| R2 | [R2-audit-census.md](R2-audit-census.md) | READY (priority 1) | `reports/R2/` | everything else |
| S0 | (reviewer) contract revision 4 | WAITING on H1 | `docs/research-contract.md` | — |
| S2b | canonicality rule | WAITING on S1 | — | — |
| S3 | circuit-targeted queries | WAITING on S2a | — | — |

## Gate on 21 Nov (problem significance)

R1, R2 and S1 decide which paper is written:

- **Continue the binding paper** if R2 shows binding flaws are frequent in
  audits of funded protocols, **and** S1 or held-out v3 gives at least one real
  target.
- **Otherwise switch to Plan B:** a measurement paper on the ZK verifier and
  deployment layer (γ = δ, test verifiers, canonical-input behaviour per
  generator). This layer has public 2026 losses.

## Human tasks

| ID | Task | Needed by |
|---|---|---|
| H1 | **Decide whether coders may replay public transactions on a local fork** (nothing ever broadcast). Yes/no plus any limits. | 21 Nov |
| H2 | **Say where the Honk lead came from**, if you know (file, run, chat). S1 step 0 searches for it anyway. | 18 Nov |
| H3 | **Ask the advisor today** to send the ZKredential and RacePass disclosures (`findings/*/disclosure-draft.md`) and record the dates. Confirm the advisor can give policy answers on 23–25 Nov and send new disclosures by 27 Nov. | 18 Nov |
| H4 | **Request the ZKAP artifact** from its authors (needed for the comparison). | 20 Nov |
| H6 | **Decide whether coders may do read-only value queries** (balance and `balanceOf` reads, no transactions) on deployed consumers found in held-out v3. Without this, the paper cannot state value at risk. | 22 Nov |
| H5 | **Check that coders can run the toolchains on Mint:** circom 2.1.9, snarkjs, nargo/bb, foundry, hardhat. The macOS binaries in `tools/` will not run; rebuild them from `tools/*-src` at the pinned versions. | 18 Nov |

## Handoff template (every `reports/<task-id>/REPORT.md`)

```text
# <task-id> — <title>
Status: DONE | PARTIAL | BLOCKED
Verdict/outcome: <enum from the prompt>
## What was done
## Evidence (paths, hashes, commands, exit codes, tool versions)
## Results (tables; exact counts)
## Assumptions and limitations
## Failed approaches / surprises
## Held-out hygiene statement (which families were read; confirm no unused EVAL family was opened)
## Recommended next task (one, with a measurable completion criterion)
```

## Rules for every coder

- **Held-out hygiene.** Never open, clone, build or analyze a family that is in
  the dataset v2 EVAL pool but not in `reports/heldout/selected-families.csv`.
  Those 1,106 families are the future held-out v3 set. Check this with
  `python3 scripts/check_holdout.py <owner/repo>` (ALLOWED/FORBIDDEN) before reading any
  third-party repository.
- **Local only.** Do not broadcast transactions, contact maintainers, or
  interact with live deployments.
- **Content limits.** Do not produce exploit-construction or forged-proof
  demonstration content beyond what local validation requires.
- **Unknown is not safe.** Unsupported, timeout or build failure means
  `UNKNOWN`, never safe.
- **AI disclosure.** Record which AI coder and model ran the task in the
  report, for the paper's AI disclosure.
