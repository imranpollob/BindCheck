# D1 workspace and preservation

## Current D1 paper integration workspace

Use `/Users/imranpollob/Coding/bc/bindcheck-d1-paper`, branch `d1-paper`.
It is a linked worktree of `/Users/imranpollob/Coding/bc/BindCheck` and was
reattached on 25 October 2026 at
`cce1a966eb84e8e9819c6f658ca4ce07fd670036`, exactly the reviewed
`chatgpt-codex` tip. The selective-reuse source is
`/Users/imranpollob/Coding/bc/bindcheck-claude-code`, branch `claude-code`, at
`9d90b93e00a8fe96d0fcd56261f9ee41d392cab5`. Do not merge those branches;
follow the [D1 paper integration plan](../d1-paper/integration-plan.md) and port
only reviewed components under new tasks.

The destination branch and worktree registration existed before D1P-00. The
registered directory was absent and prunable, while the branch contained no
commits beyond `chatgpt-codex`. `git worktree add --force ... d1-paper`
reattached it without moving the ref. Worktrees share Git objects and
administrative metadata but have separate indexes and working files. The
linked worktree is not an independent backup.

Ignored proof bundles, toolchains, build products and historical raw results
are not present in the integration worktree. Some T13/T16/T18/T19 replay
inputs and toolchains are present only in the preservation checkout
`/Users/imranpollob/Coding/bc/BindCheck`. Do not make new experiments depend
directly on those mutable caches: copy exact required bytes to a new ignored
D1P namespace, verify their recorded hashes, and write a manifest first. The
exact two v5 printed ACIR/ABI pairs and six N=8 query files were not found
locally during D1P-00.

D1P-01 rechecked only the evidence roots named by the prior reports and this
guide; the four exact inputs and six-query bundle remain absent. Its
path-neutral adapter is `scripts/d1p_01_n8_intake.py`. It validates the frozen
D1-01 manifest and all inputs before creating output, and its query sink cannot
launch or return a solver result. Artifact recovery is **BLOCKED** pending the
archive request in `reports/D1P-01.md`; do not compile or substitute a local
reconstruction without a separately authorized task and distinct provenance.
The isolated `.venv-d1p-00` now contains exactly PyCryptodome 3.23.0, and the
documented 119-test baseline passes. D1P-00's earlier incomplete test result
remains historical evidence.

Before D1P-00 changed living documents, their exact starting bytes were copied
to `results/raw/D1P-00/prior-checkpoint/`. See
[D1P-00](../../reports/D1P-00.md) for hashes, tool availability and the local
unit-test dependency blocker.

## Historical D1 worktree

The original D1-00 instruction was to use `/home/pollmix/Coding/BindCheck-d1`,
branch `research/d1`. It was a Git worktree of
`/home/pollmix/Coding/BindCheck` at base commit
`41093d1905e44af347e1d39cd6718728d4157c77`. The statements below preserve
that historical workspace and later detachment chronology; they are not
instructions to recreate an old index or redirect current integration work.

## Carried work

At the D1-00 checkpoint, the source checkout had exactly three staged changes: `README.md`, `docs/research-and-work-summary.md`, and `scripts/t22_v5_audit.py`. Their binary staged patch was applied with `git apply --index`. D1 documentation was unstaged then, so `README.md` was both staged and modified. D1-00 performed no commit, stash, push, or reset. These are historical observations, not instructions to reconstruct that index.

D1-02 starts from a clean worktree at reviewed D1-01 commit `30fb03ee78bb732169442047d8c9b5b16d2412e0`. Inspect current Git state before each task; do not restore an old index to hide later work.

The original checkout's HEAD, working files, index bytes, staged/unstaged patches, and status were checked against the captured baseline. Shared Git worktree metadata necessarily changed when the worktree was registered. Filesystem access times and administrative metadata are not preservation claims.

## Evidence locations

- [baseline.json](../../metadata/d1/baseline.json): source/worktree identity, index and patch hashes, inventory hash, counts.
- [historical-evidence.json](../../metadata/d1/historical-evidence.json): hashes for historical reports and raw artifacts.
- `results/raw/D1-00/source-inventory.json`: complete original file/symlink inventory excluding `.git` entries, including ignored tools and build artifacts.
- `results/raw/D1-00/baseline-results/`: independent copies of all 403 original raw-evidence files (123,791,761 regular-file bytes). Never use this as an experiment output directory.
- `results/raw/D1-00/{staged.patch,unstaged.patch,original.index}`: captured local state. Do not copy the saved index over a live index.
- [original contract](../history/research-contract-2026-10-20.md): exact pre-D1 contract, controlling interpretation of historical results.
- [literature-inputs.json](../../metadata/d1/literature-inputs.json): exact source hashes for the proposal, figures, and archival planning inputs.

Raw files are ignored, preserved locally, and not included by an ordinary Git clone or commit. Preserve the whole D1-00 raw directory when backing up this task. D1-00 inventoried original toolchains/build caches without copying them. D1-01 subsequently provisioned a pinned local cvc5 copy for its bounded queries. This is not validation of a general build/proof environment. Provision pinned dependencies into the new worktree before execution; do not modify the original tools or make new runs depend on mutable original caches.

## Continuing work

Read the [contract](../research-contract.md), [README](../../README.md), and [roadmap](roadmap.md). Keep historical scripts and reports frozen; place new logs in `results/raw/D1-xx/` and new reports in `reports/D1-xx.md`. Some legacy runners clear their output directory, so adapt output paths before any reuse. The D1-00 backup is archival input, never a rerun target.

To audit this preparation again while the baseline remains unchanged:

```sh
cd /home/pollmix/Coding/BindCheck-d1
python3 scripts/d1_verify_workspace.py
```

The verifier reads the original checkout without refreshing its Git index and emits JSON on stdout. It does not restore, stage, rewrite, or repair anything. It is a D1-00 checkpoint verifier, not a perpetual CI test: subsequent authorized source/index/code changes can legitimately make its baseline comparisons fail. Preserve this run's result instead of updating the baseline to hide such changes.


## D1-01 seal and prospective updates

The D1-01 verifier likewise checks its task-start HEAD/index. After the reviewed
commit, a rerun reports those two expected Git-state differences; the archived
55/55 PASS is not rewritten. The completion review records the later 53/55
observation. Neither result authorizes changing the archived audit to force PASS.

The D1-01 seal includes three living documents (README, roadmap and project
status). D1-02 preserves exact copies of all nine sealed deliverables in
`results/raw/D1-02/prior-checkpoint/`, checked against the seal and reviewed
commit, before updating those three current paths. The 49 sealed D1-01 raw
files, six other deliverables, old seal and completed reports remain unchanged.
See [D1-02](../../reports/D1-02.md) for scope and provenance.

The separately versioned `scripts/d1_02_verify.py` checks the old checkpoint
against its archive/revision, classifies prospective document evolution, and
checks the current task's starting Git state and pinned source fetches. It
does not run a solver, claim a build, or replace either historical validation.
Write each new review output under a new D1-02 filename.

## 23 October 2026 copied-workspace reconciliation

The current session uses `/home/pollmix/Coding/BindCheck-d1 (copy)`, initially
clean at `481ee07e2155e4b4307b300470d6aa0155d411b3`. Its `.git` points to
`BindCheck/.git/worktrees/BindCheck-d1`, whose registered path is the sibling
`BindCheck-d1`. The copy has separate files but shares that worktree's index;
do not infer Git isolation from the directory name. This task uses read-only
Git commands with `GIT_OPTIONAL_LOCKS=0`, performs no index/ref/registration
mutation, and writes only into the copy.

The [reconciliation report](../../reports/D1-02-reconciliation-01.md) records
six restored files, exact sibling snapshots and matches to the pre-existing
protocol hashes. It archives all 12 D1-02 sealed deliverables before changing
living documents, checks 664 inherited raw files, and preserves unfinished
D1-03 setup. Its separately versioned offline auditor is
`scripts/d1_02_reconcile.py`; use a new output filename for every invocation.
Old checkpoint verifiers retain their historical path and HEAD assumptions.

## 23 October 2026 independent checkout

At the user's request, `/home/pollmix/Coding/BindCheck-d1 (copy)` now has its
own `.git` directory and branch `chatgpt-codex`, created at
`1b4d5683d87cd8f71b37e140d0b99c9fd21b856f`. This supersedes the copied-workspace
shared-index description above for future work in this folder. The sibling
`BindCheck-d1` remains registered with the original repository.

The independent repository contains copied Git objects and its own index; it
has no object alternates or shared worktree metadata. The existing origin URL
is retained. All local modifications, deletions, untracked files and raw
evidence were preserved during detachment; no commit or push was performed.
The prior gitfile, index, workspace guide, status and preservation manifest
are archived under `results/raw/workspace-detach/20261023T195925Z/`. Historical
reports and checkpoint identities continue to describe their original runs.
