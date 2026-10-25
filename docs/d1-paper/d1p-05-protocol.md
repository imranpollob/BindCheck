# D1P-05 macOS equivalence-validation protocol

Date: **25 October 2026**. Status: **prospective; freeze before solver calls**.
Research verdict: **UNKNOWN**.

D1P-05 is a non-primary rerun of the unchanged D1P-04 equivalence queries.
It may establish only whether each emitted specialized goal is equivalent to
its frozen parent goal under the corresponding cell and original producer-walk
definitions. It is not a parent satisfiability experiment, consumer-directed
method evaluation, proof build, consumer replay, or D1 security verdict.

## 1. Immutable inputs

The D1P-04 report, protocol, specializer, failed validator, abort ledger,
execution freeze, artifact manifest, and all 152 generated SMT files remain
unchanged. D1P-05 reads the tracked D1P-04 artifact manifest and independently
hashes both controls and all 150 equivalence queries before execution. A
manifest, query, solver, runner, policy, platform, or configuration mismatch
stops before a solver call and is recorded as an infrastructure failure.

The fixed order is:

1. known-equivalence control, expected UNSAT;
2. deliberate-mismatch control, expected SAT; and
3. the 150 cell queries in D1P-04 artifact-manifest order, expected UNSAT.

## 2. macOS resource policy

The D1P-04 `RLIMIT_AS` child hook is not used. The D1P-05 parent process uses
macOS `/usr/lib/libproc.dylib` directly:

- `proc_listchildpids` recursively identifies the solver root and descendants;
- `proc_pidinfo` with `PROC_PIDTASKINFO` reads each present process's resident
  bytes; and
- each sample sums resident bytes over the observed process tree.

The frozen production sampling interval is **0.05 seconds** and the cutoff is
**4,294,967,296 observed resident bytes**. An observed value strictly above
the cutoff causes `SIGKILL` to the solver's process group. The 30-second call
deadline also causes process-group `SIGKILL`. Every record includes sample
count, observed peak process-tree RSS, peak process count, timeout/cutoff state,
and stdout/stderr hashes.

This is sampled resident-memory enforcement, **not a hard address-space cap**.
Allocation can grow between samples, so the process tree can overshoot 4 GiB
before it is observed and killed. Short-lived descendants can also exist
between samples. These differences from `RLIMIT_AS` must accompany every
result and prevent timing/resource equivalence claims with the historical
Linux campaigns.

Failure to load libproc, enumerate children, read a live root, or obtain a
valid process record is a monitoring/infrastructure failure. The runner kills
the affected process group, stops the campaign, preserves completed evidence,
and marks the remaining fixed schedule unrun.

## 3. Pre-freeze infrastructure gate

Before the execution freeze and without invoking cvc5, harmless Python helpers
must demonstrate:

1. ordinary launch, output capture, RSS sampling, and normal exit;
2. 30-second-policy mechanics at a shorter helper timeout and process-group
   cleanup of a helper plus its child;
3. aggregate process-tree RSS observation, a deliberately low helper cutoff,
   process-group termination, and cleanup;
4. intentional monitoring failure, automatic termination, and cleanup; and
5. a missing executable recorded automatically as a structured launch error.

These are runner infrastructure checks only and establish no SMT, research, or
security result. Any failed infrastructure check blocks the execution freeze.

## 4. Execution limits and stopping rules

- Sequential execution; no parallel calls.
- At most 152 solver calls, one attempt per query in this new campaign.
- At most 30 seconds per call and 4,560 solver wall-seconds in aggregate.
- No retries, solver tuning, alternate query bytes, or alternate solver after
  the freeze.
- Either failed control stops the campaign.
- A cell SAT result is an equivalence counterexample and stops the campaign.
- A cell timeout, solver UNKNOWN, or observed memory cutoff makes that cell
  unusable but does not reorder or stop the remaining fixed schedule.
- A launch, monitoring, malformed-output, nonzero-exit, hash, or other
  infrastructure/execution failure stops the campaign and records later calls
  as unrun.

The runner writes per-call JSON/stdout/stderr and a raw checkpoint after each
attempt. Launch exceptions are records, not uncaught omissions. A final raw
ledger and byte-identical tracked ledger account for all 152 planned calls.

## 5. Eligibility and interpretation

Complete-partition eligibility requires both controls to return their expected
answers, every one of the 150 equivalence queries to return UNSAT with exit
zero, and all 150 D1P-04 producer-prefix audits to remain true. A missing,
timed-out, UNKNOWN, memory-cutoff, errored, SAT, or unrun cell is ineligible.

Even full eligibility establishes only the exact SMT transformation. It does
not establish any parent query's satisfiability, producer-cone soundness,
consumer-direction effectiveness, joint producer/consumer semantics, real-
proof feasibility, financial impact, or D1 authorization/coverage verdict.
The research verdict remains UNKNOWN, and primary work remains separately
reviewed and Linux-only.
