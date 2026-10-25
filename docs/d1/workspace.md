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

The D1P-04/05/06/07 tasks started from `d1-paper` HEAD
`2ad4f699d527490149f3704e6f6f228494f2d4bd`. D1P-08 and D1P-09 started from
current `d1-paper` HEAD `95e8ba144a3b0fd148a802d706394868397e4516`;
their files remain uncommitted by instruction. Do not reset or hide current or
historical work when continuing review.

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

D1P-02 resolves the local artifact-availability blocker prospectively. The
four files under `results/artifacts/d1-n8/` are byte-identical to evidence
commit `7d098cd393c5cc8609765b663d393fcaebf24aeb` and match the frozen D1-01
manifest. The unchanged adapter serialized 4/4 accepted inputs into 6/6
hash-matching v5 queries under `results/raw/D1P-02/generated/`, with zero
solver processes. See [D1P-02](../../reports/D1P-02.md) and the ignored
`results/raw/D1P-02/provenance.json`. Keep the artifact directory immutable;
future runs must use a new raw namespace and must not overwrite D1P-02.

D1P-03 adds a reviewed, no-execution experiment protocol at
`docs/d1-paper/d1p-03-protocol.md`. Its solver-free partition checker records
781,250 stream cases, 25 pair cells, and 12,825 goal cases under
`results/raw/D1P-03/offline-check.json`. It distinguishes the producer walk
from the actual configurable-length consumer decoder and preserves the six
historical UNKNOWN outcomes. Do not interpret the offline PASS as ACIR, solver,
proof, consumer, or security evidence. Both planners must resolve the listed
protocol decisions before any execution or Track B implementation.

D1P-04 places 150 specialized queries, 150 equivalence queries, and two
controls in the fresh ignored `results/raw/D1P-04/generated/` namespace. The
tracked artifact manifest records all output hashes and 150/150 byte-identical
ordered producer-prefix audits. The first control did not reach cvc5 because
native macOS rejected the frozen validator's 4 GiB `RLIMIT_AS` pre-exec
assignment. The controls-first/no-retry rule left both controls and all 150
cells unrun; see `metadata/d1/d1p-04-equivalence-ledger.json` and
[D1P-04](../../reports/D1P-04.md). Do not use any D1P-04 cell in primary work.
A separately authorized, new-version portable equivalence task must preserve
the query bytes, freeze a working limit mechanism, pass both controls, and
establish all 150 cells before the partition is eligible. Research verdict
remains UNKNOWN.

D1P-05 completes that prospective portability task without rewriting D1P-04.
The final pre-freeze harmless-helper gate passes launch, timeout, process-tree
RSS cutoff, cleanup, monitoring-failure, and structured launch-error checks.
The new runner then verifies all 152 D1P-04 input hashes, passes both controls,
and obtains UNSAT for all 150 equivalence cells. The D1P-05 tracked ledger is
`metadata/d1/d1p-05-equivalence-ledger.json`; raw helper and per-call evidence
is under the fresh ignored `results/raw/D1P-05/` namespace. The complete
partition is eligible for later primary use at the transformation-evidence
level only. The 50 ms libproc RSS policy can overshoot 4 GiB and is not a hard
address-space cap. Do not treat native macOS timings as primary comparison
data, and do not infer parent satisfiability, consumer effectiveness, proof or
D1 security from equivalence. Research verdict remains UNKNOWN.

D1P-06 makes this native Mac the prospective Track A reference without
rewriting D1P-05. The fresh input manifest checks two controls, six goal-only,
two cone-only, six byte-identical combined and 150 byte-identical specialized
queries. The final harmless-helper preflight passes and the sampled 50 ms
libproc policy, equal 300-second per-obligation budgets, solver, platform and
all input hashes are frozen before execution. Both controls and one goal-only
SAT complete. The next goal-only call writes SAT/witness text but hits a
process-exit monitor/cleanup race before a complete record, so it is UNKNOWN.
The frozen infrastructure-stop rule leaves all combined and partitioned calls
unrun. Preserve `results/raw/D1P-06/`, the tracked stopped ledger, and the
[D1P-06 report](../../reports/D1P-06.md). Do not resume or repeat consumed
calls without a new planner-approved protocol. Decomposition effectiveness and
the D1 verdict remain UNKNOWN.

D1P-07 supplies that separately versioned protocol and explicitly authorizes
a fresh call-1 campaign. It preserves every D1P-06 byte and reuses the exact
166 input hashes, solver, ordering and budgets. The new runner bounds exit
confirmation and both cleanup waits, catches termination errors, always emits
call/campaign records, and records missing memory samples as null. Seven
focused tests, 154 complete D1 tests and 13 preflight helper checks pass. The
fresh campaign attempts all 166 calls with no infrastructure failure: six
combined queries time out; the partitions return 58 UNSAT cells and 92
timeouts, leaving all six aggregates UNKNOWN. Preserve
`results/raw/D1P-07/` and the tracked ledger/report. Do not retune or extend
these Track A queries. No consumer-direction or D1 verdict follows.

D1P-08 does not rerun Track A. Its offline hash audit classifies the frozen
D1P-07 cells as 58 literal-false/UNSAT, 42 literal-true/timeouts, and 50
nontrivial/timeouts; six goal-only diagnostics are SAT and both cone-only
diagnostics time out. The new solver-neutral symbolic consumer reuses the V2
policy, admission, token and concrete-execution foundations, and keeps
decoding, guards, sequential state, verifier/key/vector binding, rollback,
unsupported behavior, P/O/E, and occurrence multiplicity explicit. Thirteen
focused and 167 complete D1 tests pass; 12 pinned-source symbolic/concrete
assignments match. Preserve `results/raw/D1P-08/` and the
[D1P-08 report](../../reports/D1P-08.md). The proposed 11-trace N=8
consumer-success intersection currently removes zero producer constraints;
an offline forwarding/full-relation occurrence certificate is the next gate.
Do not infer a joint-method benefit or D1 verdict from the component checks.

D1P-09 keeps that scope at check-added N=8 and prepares only AUTH/NONVAC. The
tracked binding manifest distinguishes a locally preserved full 1,303-opcode
producer artifact from the historical 620/540 selected cone. It records 1,280
checked producer-boundary equalities and an N=1000 forwarding certificate as
background, but no matching N=8 `agg_final` artifact exists. The one authorized
isolated compile preserves the exact 1000→8 and 1005→13 source diff, then exits
101 because Nargo cannot lock its external local cache; it creates no artifact
and is not retried. Preserve `results/raw/D1P-09/agg-final-compile/`.

The final offline output is `results/raw/D1P-09/offline-07/`. Eleven successful
consumer shapes are exhaustive/disjoint over 390,625 equality/control-flow
classes, retain the all-padding case, and fix no payload. One conservative
propagator runs on the unspecialized cone, all 11 shapes, and all 25 producer
cells; the full case predicate and interface reconstruction remain in every
reduction. Consumer shapes leave 612–616 original cone operations. Eleven
focused tests are supplemented by a free-extension regression, for 12 focused
and 179 complete D1 tests passing. Preserve the tracked D1P-09 manifests
and [report](../../reports/D1P-09.md). Full-relation propagation, exact N=8
forwarding/key binding, joint solving, proof/replay, AUTH/NONVAC, and the D1
verdict remain UNKNOWN. Both planners decide the next gate; do not
automatically retry compilation or build the joint encoder.

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
