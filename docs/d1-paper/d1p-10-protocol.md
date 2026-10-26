# D1P-10 bounded producer-encoding feasibility protocol

Date frozen before any D1P-10 solver call: **25 October 2026**  
Task status at freeze: **PROSPECTIVE DEVELOPMENT STUDY**  
Research verdict: **UNKNOWN**

## 1. Objective and boundary

D1P-10 is a new in-sample development study of the historical check-added
N=8 **selected producer cone** only.  `C` means that 620-operation,
540-witness cone; it is not the full producer relation.  D1P-07, including
its six-obligation stop decision, results, queries, ledgers, and raw evidence,
remains immutable and is not continued or retuned.

The four logical obligations are:

1. `C` (cone satisfiability);
2. `C AND G_NV` (the original non-vacuity goal);
3. `C AND G_PRE` (the original prefix-violation goal); and
4. `C AND G_TAIL` (the original tail-violation goal).

The original check-added walk and three goal bytes are retained.  No payload
is fixed, authorization is not assumed, and unsupported full-producer,
recursive, proof, forwarding, decoder, consumer, or deployment semantics are
not removed.  The D1 security verdict remains UNKNOWN regardless of this
study's component results.

## 2. Arms

The comparison has at most three arms:

- **unchanged baseline**: the frozen check-added selected-cone encoding from
  D1P-06/D1P-07.  The constraint and goal bytes through `check-sat` remain
  byte-identical; only the post-solve `get-value` projection may be enlarged
  so a SAT assignment can be checked.
- **25 producer cells with conservative propagation**: the complete D1P-04
  producer-cell partition, with only D1P-09's exact substitution, unique
  affine-field reconstruction, and known-index read lowering.  Every full
  cell predicate, original goal, reconstruction equality, interface binding,
  and original range constraint is retained.  Nonzero activations are never
  replaced by one, disjunction members are never selected, and payloads are
  never fixed.
- **one profiled equivalent range encoding**: an unsplit re-encoding of the
  same cone, selected before main results from the fixed candidate pool below.
  All non-range constraints, memory semantics, interfaces, walk, and goals
  are unchanged in meaning.

An arm whose preservation obligation or pre-main validation fails is skipped
and reported; it is not repaired or replaced after primary output is seen.

## 3. Fixed profiling plan and candidate-selection rule

The three candidates replace each 32-bit binary decomposition with an exact
radix decomposition of base 4, 16, or 256.  One-bit ranges retain the binary
encoding.  Profiling uses exactly two obligations per encoding: `C` and
`C AND G_NV`.  The unchanged baseline is profiled on the same two obligations.
This is eight sequential calls, each with a 30-second allowance (240 seconds
planned; 10 calls/300 seconds is the hard phase ceiling).  No goal, case, or
payload is changed for profiling.

Only the three alternatives are ranked.  The frozen lexicographic rule is:

1. more resolved SAT/UNSAT profiling obligations;
2. lower aggregate elapsed time, with every unresolved call charged the full
   30-second allowance;
3. lower sum of observed peak process-tree RSS, with a missing observation
   ranked after every available value;
4. smaller aggregate profiling input bytes; and
5. fixed final order base 4, then base 16, then base 256.

The selected candidate is frozen after profiling.  No candidate is added,
removed, tuned, or re-profiled after primary results.  Profiling may select a
range representation; it does **not** show that range constraints are the
bottleneck.

## 4. Preservation arguments and validation obligations

### 4.1 Exact radix encoding

For base `B = 2^k`, each digit `d` is constrained by
`product(d-j, j=0..B-1) = 0`.  The pinned field has prime order greater than
`2^32`, and the roots `0..B-1` are distinct, so this equation holds exactly
when `d` is one of those canonical digits.  The equality
`x = sum(B^i*d_i)` therefore has an extension exactly when the canonical
field representative of `x` lies in `[0, 2^32)`.  Conversely, each value in
that interval has its ordinary radix expansion.  One-bit ranges retain the
same Boolean-root argument.  This is the universal preservation argument;
boundary solver controls are regressions, not its substitute.

### 4.2 Conservative propagation

Under a retained complete cell predicate, every initial substitution is a
separately enumerated logical consequence.  Exact substitution preserves a
polynomial identity.  A ground zero assertion is a tautology.  Over the
pinned field, an affine equation `a*w+c=0` with `a != 0` is equivalent to the
recorded reconstruction `w=-c/a`.  A memory read is lowered only when its
index and every preceding write index are exact, so the retained equality is
the same ordered-array read.  Symbolic memory suffixes remain.  All 58 range
constraints are retained in this arm, even when a fixed value would permit a
ground discharge.  Every eliminated witness gets an explicit reconstruction
equality; original free-extension witnesses remain declared and arbitrary.

Before main execution, a solver XOR check must return UNSAT for each of the 25
producer cells, comparing the original cone with the serialized residual plus
reconstruction under the same cell predicate and shared range auxiliaries.
The T22 lost-equality regression must also return UNSAT with the reconstruction
present.  Any missing, timed-out, SAT, malformed, or errored validation makes
the propagation arm ineligible.

### 4.3 SAT validation

A SAT cell is only an existential selected-cone result after reconstructing a
complete assignment and checking it against the original 620 operations,
that cell's complete predicate, the applicable original goal, and the frozen
interface witness mapping.  The same local assignment check is applied to an
unsplit SAT result where a complete model is available.  An invalid or
incomplete model is UNKNOWN.  No SAT result is full-ACIR, proof-feasibility,
consumer-effect, or security evidence.

Aggregate partition UNSAT requires all 25 cells UNSAT.  A SAT aggregate
requires a validated SAT cell.  A timeout, missing result, invalid model, or
other unresolved cell leaves the aggregate UNKNOWN.

## 5. Frozen budgets and resource policy

Calls are sequential and one-attempt.  The pinned cvc5 1.4.2 arm64 GPL/CoCoA
binary and arguments `--lang=smt2 --ff-solver=split` are reused.  D1P-07's
race-safe process runner and native-macOS libproc process-tree RSS policy are
reused: 50 ms samples, termination after an observed value above 4 GiB,
bounded exit confirmation and cleanup.  This is not a hard address-space cap
and can overshoot or miss short-lived use.

Phase budgets are separate and unused time never transfers:

| Phase | Hard allowance |
| --- | ---: |
| Profiling | at most 10 calls x 30 seconds = 300 seconds |
| Controls and solver-based transformation validation | at most 70 calls x 30 seconds = 2,100 seconds |
| Main comparison | 4 obligations x 3 arms x 300 seconds = 3,600 seconds |
| Overall configured solver-wall ceiling | 6,000 seconds |

Every partitioned obligation shares one unsplit 300-second allowance.  Each
cell receives at most 12 seconds, and generation/setup/checking bookkeeping
inside execution is charged to the slot.  The runner's 50 ms enforcement and
bounded reap can make measured wrapper time slightly exceed a configured
deadline; no subsequent call may consume that overrun or unused time.

Transformation-validation time is recorded as its own phase and is added to
profiling and main time for end-to-end reporting.  A failed control, identity
mismatch, runner/monitor/cleanup failure, or budget exhaustion stops the
affected phase, preserves every record, and leaves required missing work
UNKNOWN.

## 6. Freeze and stopping rule

Before the main comparison, freeze the selected alternative, exact baseline,
all 100 propagated cell inputs, four alternative inputs, solver identity,
runner, protocol, resource policy, validation ledger, call order, and hashes.
Primary order is baseline obligations, propagated obligations/cells, then the
alternative obligations.  No new candidate, tuning, retry, or input change is
permitted after that freeze.

Stop at the declared budgets.  Do not perform forwarding reconstruction,
full-relation propagation, a joint encoder, proof build, consumer replay,
held-out evaluation, live-system interaction, commit, push, merge, or branch
change.

