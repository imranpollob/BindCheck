# BindCheck agent instructions

## Authority and current status

Read these sources in order before changing the project:

1. `docs/research-contract.md` — authoritative research question, threat model, scope, semantics, and evidence rules.
2. `README.md` — current implementation and task status.
3. `reports/Txx.md` and `reports/D1-xx.md` — immutable evidence records for completed tasks.
4. `BindCheck_Research_Guide.md` and dated research updates — historical planning context only.

If these sources disagree, follow the higher-ranked source and report the disagreement. Do not silently rewrite an older report to match a later conclusion.

## Working rules

- Work on one bounded task with explicit completion criteria.
- Preserve prior reports and raw evidence. Put new raw logs under ignored `results/raw/Txx/` or `results/raw/D1-xx/` and summarize them in tracked task reports.
- Record exact commands, tool versions, source revisions, hashes, exit statuses, assumptions, and unsupported behavior.
- Use only `VIOLATION`, `VERIFIED_WITHIN_SCOPE`, or `UNKNOWN` according to the research contract. Never treat a timeout, build failure, unsupported feature, or missing artifact as safe.
- Keep implementation facts separate from protocol-policy specifications. Do not encode the expected verdict or missing constraint in a specification.
- Validate central findings with real constraints/proofs and committed local effects where feasible. A mocked verifier cannot carry an end-to-end security claim.
- Preserve family-level separation between development and held-out cases. Do not tune rules on a held-out result and still call that result held out.
- Prefer primary sources and pinned artifacts. Label reported, source-confirmed, model-confirmed, locally reproduced, and repair-validated evidence accurately.
- AI output is not independent annotation. Authors must inspect generated code, labels, citations, and claims.

## Living project checkpoint

After each bounded project task that changes the research state, update
`docs/project-status.md` in the same turn:

- add or update the task under the relevant Mermaid branch;
- use only `[DONE]`, `[ACTIVE]`, `[NEXT]`, `[WAITING]`, or `[UNKNOWN]` for
  project-progress labels;
- append one dated row to the checkpoint log with links to the controlling
  report or evidence;
- preserve prior checkpoint rows and completed nodes; and
- never let the diagram claim more than the research contract, README, and
  immutable reports support.

Conversation-only, status-only, and failed turns do not get a new checkpoint
unless they materially change project state. If a task remains incomplete,
update its existing node rather than marking it done.

## Safety and repository hygiene

- Defensive experiments are limited to owned local execution with synthetic assets unless the user explicitly expands the scope.
- Do not broadcast transactions, test live third-party systems, contact maintainers, or disclose findings without explicit authorization.
- Do not commit downloaded toolchains, dependencies, generated proofs, compiler output, raw logs, caches, or secrets. Add a pinned fetch/checksum step instead.
- Do not commit, push, rewrite history, or delete prior evidence unless explicitly requested.
- Preserve unrelated user changes and avoid editing ignored third-party checkouts under `tools/cases/`.

## Task handoff

Every completed task should provide:

- objective and status;
- files changed;
- commands and observed results;
- evidence locations;
- assumptions and limitations;
- failed approaches or unexpected observations; and
- one recommended next task with a measurable completion criterion.

## D1 workspace

Follow `docs/d1/roadmap.md` after the research contract and README. The source checkout `/home/pollmix/Coding/BindCheck` and `results/raw/D1-00/baseline-results/` are preservation references, not experiment output locations. Do not run legacy cleanup scripts against either. The copied user changes remain staged; D1-00 documentation remains unstaged. Read `docs/d1/workspace.md` before dependency setup or reruns.
