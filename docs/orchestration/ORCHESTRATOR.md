# Orchestrator brief (for a local Claude Code session)

Read this file first when you start as the orchestrator. Then read
`docs/orchestration/README.md`, `docs/sprint-eurosp-2027.md`, `AGENTS.md` and
`docs/research-contract.md`, in that order.

## Your role

- You are the **reviewer and orchestrator** of the BindCheck paper. You do not
  do the task work.
- **Write task prompts.** Each prompt is a file
  `docs/orchestration/<ID>-<name>.md` with these parts:
  - the goal for the paper;
  - the branch, the paths it owns, and the paths it must not edit;
  - the steps;
  - the output;
  - the completion criteria;
  - the time box.
- **The human author runs AI coders.** Each coder runs in its own git worktree
  `$BC/wt-<ID>` (BC=~/Coding/bc), on branch `sprint/<ID>`.
- **Review each pushed branch** when the human says "<ID> pushed". Check it
  against the prompt's completion criteria, the research contract and
  `AGENTS.md`. Reply with one of:
  - `ACCEPT`;
  - `REVISE: <numbered list>`;
  - `STOP: <reason>`.
- **Think like an A\* reviewer.** The paper must make reviewers learn something
  new and care about the problem. Ask "who loses money if this flaw exists?"
  before you ask "is the tool good?".
- **Write in ASD-STE100 style** when the author asks: short sentences, active
  voice, simple words.

## Current state (18 Nov 2026)

**Venue and branches:**

- **Target:** IEEE EuroS&P 2027. Registration 25 Nov, submission 2 Dec
  (AoE). The S&P 2027 Cycle 2 submission was withdrawn.
- **Integration branch:** `main` (since 18 Nov; old state tagged `pre-sprint-freeze2`). Task branches: `sprint/R1`,
  `sprint/R2`, `sprint/S1`, `sprint/S2a`, `sprint/S4`, `sprint/T0`.

**Problem-significance review (17 Nov):**

| Class | Evidence |
|---|---|
| P4 (verifier layer) | Real public losses in 2026: FoomCash about $2.26M, Veil Cash about $5.7K (both γ = δ). ZKSwap 2025 lost about $5M through a test verifier that always returned true. The γ = δ class is already public (Zeto #186, the zkjac scanner). BindCheck did not discover these incidents. |
| P1, P2, P3 (binding) | Many known at-risk bugs (Semaphore #90, zkDrops, Nightfall, Aztec 2.0, StealthDrop). No public money loss found yet. |
| Honk lead | Partly known. Xion PR #608 (merged 4 Sep 2026) says native bb UltraHonk verification reduces public inputs mod r, so X + r verifies. The Solidity verifier is untested. |
| Our evidence | Z1 (ZKredential) and R1 (RacePass) are E4 but are in hackathon or demo code: no deployment, no funds. The freeze-2 held-out run has no reproduced flaw. `RELATED-WORK.md` §5.1 says no DEV P1/P3 violation needs the circuit. |

**Reviewer verdict today:** weak reject. The reason is significance, not
method.

**Gate on 21 Nov, decided by R1, R2 and S1:**

- **Continue the binding paper** if R2 shows the class is frequent in audits of
  funded protocols, **and** S1 or held-out v3 gives at least one real target.
- **Otherwise switch to Plan B:** a measurement paper on the ZK verifier and
  deployment layer (γ = δ, test verifiers, canonical-input behaviour per
  generator).

## Assets

- **Untouched held-out pool:** 1,106 dataset-v2 EVAL families were never
  analyzed. 391 of them are labelled audited or deployed (99 Noir). Guard:
  `python3 scripts/check_holdout.py <owner/repo>`.
- **Analyzer:** freeze 2 (`92789fad…`). The P4 G2 constant is already fixed in
  freeze 2.
- **Raw evidence:** `$BC/BindCheck/results/raw/`, about 13 GB, the only copy.
  It is read-only. S2a links to it.

## Open human decisions

| ID | Decision |
|---|---|
| H1 | Local fork replay of public transactions, nothing broadcast. Needed by 21 Nov. |
| H3 | The advisor sends the Z1 and R1 disclosures. Record the dates. |
| H4 | Ask the ZKAP authors for their artifact. |
| H5 | Linux toolchains. The T0 agent does this. |
| H6 | Read-only balance queries on deployed consumers, to state value at risk. |
| — | The main checkout `$BC/BindCheck` has uncommitted changes. Review `git status` with the author. Do not discard anything. |

## Rules you must keep

- Never let an agent open a FORBIDDEN (reserved held-out) family.
- No live transactions, no maintainer contact, and no disclosure without the
  human. Disclosures go through the advisor.
- Never count UNKNOWN as safe. Never tune on held-out data and still call it
  held-out.
- Do not commit, push or delete evidence unless the human asks. A stop hook may
  ask you to commit and push your own orchestration files; that is allowed.
