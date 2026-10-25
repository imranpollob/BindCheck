# D1P-07 race-safe native-macOS Track A protocol

Status: **prospective execution protocol**. Research verdict: **UNKNOWN**.

## 1. Scope and fresh-campaign authority

D1P-07 preserves D1P-06's protocol, freeze, partial call files, stopped ledger,
report and living checkpoint. It creates a new runner, resource policy, helper
preflight, execution freeze, raw namespace and tracked ledger. No D1P-06 file
is an execution output for D1P-07.

This task explicitly authorizes a fresh campaign beginning at call 1. Both
controls and every scheduled Track A query may be repeated once in D1P-07.
D1P-06 timings and partial results are not imported into the new comparison.
The 166 D1P-06 input hashes, cvc5 binary, order and budgets remain unchanged.
There is no query change, solver tuning, within-campaign retry, proof build,
consumer replay, Track B expansion or held-out evaluation.

Track A tests producer-side decomposition of the six original T22-v5
obligations. It does not test consumer-direction effectiveness or establish a
D1 security verdict.

## 2. Process-exit and cleanup rules

The runner retains the D1P-05 macOS `libproc` process-tree RSS sampler but
replaces its D1P-06 launch/wait/cleanup path.

- `Popen.poll()` is checked before sampling.
- If a sample reports the root missing, the runner calls `wait()` with a
  0.25-second bound. Only a confirmed/reaped exit is normal completion.
- If the bounded exit confirmation expires or raises, the event is a genuine
  monitoring failure and triggers bounded termination.
- Termination first attempts process-group `SIGKILL`, catches
  `PermissionError`, `ProcessLookupError` and other errors, then waits at most
  0.25 seconds. If still live it attempts direct child kill and waits at most
  another 0.25 seconds. It never calls unbounded `wait()`.
- Cleanup errors, fallback actions, reap status and failure are recorded.
  Any cleanup error is an infrastructure failure for the campaign even when
  direct fallback safely reaps the child.
- Every call path writes stdout, stderr and structured JSON. Execution catches
  unexpected runner exceptions, writes the campaign ledger, and marks every
  remaining scheduled call unrun.
- Peak RSS and process counts are JSON null when no sample exists. Zero is
  never substituted for an unavailable observation.

## 3. Required pre-freeze regressions

Unit tests and the fresh helper gate use harmless Python processes, not cvc5.
They cover rapid exit, exit during sampling, live-process monitor failure,
denied process-group cleanup with bounded direct-kill fallback, structured
launch failure, timeout/descendant cleanup and sampled tree-memory cleanup.
Failures must retain all three log/record files and leave no observed helper
survivor. The helper gate is infrastructure evidence only.

The freeze follows only after the focused tests, complete D1 suite, helper
gate, 166/166 query hashes, solver identity, platform/library inventory and
resource policy pass.

## 4. Inputs, schedule and budgets

The exact D1P-06 input manifest is reused byte-for-byte:

- two unchanged expected-UNSAT/SAT controls;
- six goal-only diagnostics;
- two selected-producer-cone-only diagnostics;
- six exact historical combined queries; and
- six partitioned logical obligations with 25 D1P-05-validated cells each.

`C` remains the selected producer cone, not the full producer relation.
Diagnostics never discharge combined obligations and are not additive solve
costs. The order remains controls; goal-only; cone-only; combined; partitioned,
with `check_added` before `running_flag`, `nonvacuous`, `prefix`, `tail`, and
cells 00 through 24.

The fresh controls receive 30 seconds each and 60 seconds aggregate. The
primary campaign permits 164 calls and 6,000 seconds aggregate. Goal-only,
cone-only and combined slots each receive 300 seconds. Each partitioned
logical slot receives the same 300 seconds total, with at most 12 seconds per
cell. Launch and per-slot bookkeeping overhead is charged to its slot. Calls
are sequential and one-attempt.

## 5. Outcomes and stopping

A usable result requires a structured call record, exit zero, parsed first
stdout result and complete logs. Timeout, sampled RSS cutoff, solver UNKNOWN,
process error, malformed output or budget exhaustion is unresolved. A
partition is UNSAT only after 25 UNSAT cells. It is SAT only after a cell SAT
with preserved witness output; remaining cells in that logical slot may then
be unrun. Solver SAT is not validated full-ACIR evidence, a proof, replay,
consumer effect or D1 violation.

A failed control, corrupt identity, genuine launch/monitor/cleanup failure, or
contradiction between D1P-05-validated equivalent combined and partitioned
formulas stops the campaign. UNKNOWN versus a resolved result is not a
contradiction. All evidence and remaining unrun rows are preserved.

The report compares only fresh D1P-07 Mac results in six rows and reports
goal-only/cone-only diagnostics separately. Historical Linux timeouts remain
background. D1P-06 can explain why this runner exists but supplies no timing
or outcome to the comparison. The D1 security verdict remains UNKNOWN.
