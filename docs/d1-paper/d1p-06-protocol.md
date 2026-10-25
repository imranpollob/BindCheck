# D1P-06 native-macOS Track A protocol

Status: **prospective freeze protocol**. Research verdict: **UNKNOWN**.

## 1. Revision and scope

This protocol supersedes only D1P-06's initially requested Linux execution
platform. The interrupted preparation found no local Docker, Podman, Lima,
Colima, QEMU, or cached Linux image, and this session could not reach the
recorded Tailscale/SSH host. No D1P-06 solver query or Linux helper campaign
was started. The serialization-only input-preparation work is retained.

At the planner's direction, this Mac becomes the D1P-06 reference environment.
All newly measured arms run natively on it with one pinned cvc5 binary and one
resource policy. Results may be compared with each other within this campaign.
Historical Linux observations are background only; there is no direct timing,
memory, or performance-parity claim across platforms.

Track A tests whether the validated 25-cell producer-side decomposition helps
the six original T22-v5 obligations. It does not test consumer direction,
joint producer/consumer semantics, proof behavior, replay, or D1 security.

## 2. Frozen inputs and derivations

The input manifest must bind and recheck:

- the two unchanged D1P-04 controls;
- six exact D1P-02 historical combined queries `C AND G`;
- all 150 D1P-04 specialized queries already validated by D1P-05;
- six goal-only diagnostics, retaining the exact field header, required
  declarations, producer-specification walk, original goal and trailer while
  excluding all producer constraints; and
- two cone-only diagnostics, retaining the complete ordered selected-cone
  producer prefix byte-for-byte and appending only `check-sat`.

Here `C` is the selected producer cone, not the full producer relation.
Goal-only and cone-only observations are diagnostics and never discharge or
add to the cost of a combined obligation. Derivation audits record the parent,
retained/removed blocks, assertion counts, byte ranges and hashes. The combined
and specialized inputs are copied into the fresh D1P-06 namespace without a
byte change.

## 3. Native resource policy and preflight

The runner reuses the tested D1P-05 `libproc` implementation. Every solver
root and recursively observed descendant is sampled every 0.05 seconds.
Observed resident bytes are summed, and an observation strictly above
4,294,967,296 bytes triggers `SIGKILL` for the process group. The same group
termination applies on timeout.

This is a **sampled RSS cutoff**, not a hard address-space cap. Allocation may
overshoot between samples, and short-lived allocations or descendants may be
missed. Peak values are observed peaks only. This differs materially from the
historical Linux `RLIMIT_AS` policy.

Before the freeze, harmless helpers must pass ordinary launch/output,
timeout/process-tree cleanup, sampled tree-memory cutoff/cleanup, intentional
monitor-failure cleanup, and structured missing-executable handling. Preflight
also verifies every input hash, D1P-05 partition eligibility, platform,
solver binary, linked-library identities where files are available, Python,
CPU, RAM, OS, arguments, runner, protocol, and resource policy. No solver query
runs before the freeze.

## 4. Fixed schedule and equal budgets

Execution is sequential and one-attempt. The order is:

1. unchanged known-equivalence control, expected UNSAT;
2. unchanged deliberate-mismatch control, expected SAT;
3. six goal-only diagnostics in family/query order;
4. two cone-only diagnostics in family order;
5. six exact combined queries in family/query order; and
6. six partitioned logical obligations in the same family/query order, each
   using cells 00 through 24 in manifest order.

Family order is `check_added`, `running_flag`; query order is `nonvacuous`,
`prefix`, `tail`. The expectations—never substituted for observations—are SAT
for goal-only and cone-only, SAT for combined nonvacuity, and UNSAT for
combined prefix/tail.

Controls receive at most two calls, 30 seconds each and 60 seconds aggregate.
The primary matrix receives at most 164 calls and 6,000 seconds aggregate:

| Arm | Logical slots | Calls | Per-call limit | Per-slot limit | Aggregate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Goal-only | 6 | 6 | 300 s | 300 s | 1,800 s |
| Cone-only | 2 | 2 | 300 s | 300 s | 600 s |
| Combined | 6 | 6 | 300 s | 300 s | 1,800 s |
| Partitioned | 6 | at most 150 | 12 s | 300 s | 1,800 s |

Per-call launch time and per-slot bookkeeping/transformation overhead are
charged to the corresponding slot. Partitioned and unsplit combined methods
therefore have the same 300-second allowance per logical obligation. Calls
are never retried, reordered, tuned, or moved to another solver.

## 5. Outcomes and stopping rules

A parsed result requires exit zero and complete stdout/stderr records. Timeout,
sampled memory cutoff, solver UNKNOWN, crash, missing/malformed output, or
budget exhaustion is unresolved. A partition is UNSAT only if all 25 cells
are UNSAT. A partition is SAT only when a cell returns SAT and the existing
query's witness output is preserved; later cells in that logical slot may then
be marked unrun. Such SAT is a solver result over the selected cone, not a
validated full-ACIR model, proof, replay, consumer effect, or D1 violation.

A failed control, identity/input corruption, launch/monitor infrastructure
failure, or contradiction between D1P-05-validated equivalent combined and
partitioned formulas stops the campaign and preserves remaining rows as unrun.
UNKNOWN versus a resolved result is not a contradiction. Expectations are not
stopping or validation oracles.

The report must give six combined-versus-partition rows, cell result counts,
observed resource use and overhead, plus separate goal-only and cone-only
diagnostics. Historical Linux six-query timeouts appear only as background.
Regardless of Track A outcomes, the D1 security verdict remains UNKNOWN.
