# D1P-04 protocol corrections and SMT-specializer validation

Date: **25 October 2026**. Status: **prospective protocol frozen before solver
execution**. Research verdict: **UNKNOWN**.

D1P-04 validates a transformation of the six recovered T22-v5 SMT queries.
It is not a primary experiment, a D1 joint analysis, evidence of
consumer-direction effectiveness, or a change to any historical outcome.
D1P-03 and its offline evidence remain intact. A separately generated freeze
manifest must bind this protocol, the implementation, all parent/generated
queries, solver identity, configuration, and budgets before the first solver
call.

## 1. Corrections to the D1P-03 comparison design

These rules supersede D1P-03 prospectively; they do not relabel D1P-03 or any
older report.

### 1.1 Partition treatment is shared

Partitioning is an experimental factor, not a consumer-directed technique.
Every method in a comparison block receives the same treatment: all unsplit,
or, for N=8, all using the same frozen 25 cells in the same order. A comparison
must not attribute a gain to consumer direction when only that method receives
partitioning. Report unsplit and partitioned blocks separately.

### 1.2 Five Track B methods

Track B must compare five equal-information methods, adding the two controls
missing from D1P-03:

1. full monolithic joint analysis;
2. equal-information modular analysis;
3. ordinary goal-cone analysis, selected from the goal without consumer-
   directed ordering or refinement;
4. consumer-facts ablation, using the same producer relation and goals but
   withholding consumer-derived selection facts while retaining enough schema
   to state the property; and
5. consumer-directed checked-summary refinement.

There are seven V2 case/scope rows and four properties (AUTH, COVERAGE, DEFER,
NONVAC): 28 property slots per method, **140 method-slots** total.

For an unsplit block, every method gets 300 analysis seconds per property
slot and 4 GiB per process. Fixed methods use at most one call; modular and
refinement methods use at most five calls of at most 60 seconds. Thus the
unsplit ceiling is **364 solver calls**, **8,400 analysis seconds per method**,
and **42,000 analysis seconds total**. Concretization, rejected-candidate
checking, summary proof, refinement, extraction/selection, and internal solver
calls are charged to that method's 300-second slot and reported.

For a partitioned N=8 block, each method receives the same 25 cells and still
only 300 analysis seconds per property slot. Each cell has a 12-second
aggregate allowance. Fixed methods use at most one call per cell; modular and
refinement methods may use at most five internal calls per cell, still sharing
that cell's 12 seconds and the method-slot's 300 seconds. If every N=8 slot is
partitioned, the full five-method matrix has a **4,108-call ceiling** while the
total analysis-time ceiling remains **42,000 seconds**. No N=1000 partition is
defined.

### 1.3 Separate final validation

Each method has its own quota of at most one candidate for AUTH, COVERAGE, and
NONVAC in every case/scope: **21 candidates per method**, never a shared
first-come pool. Each candidate gets an equal, separate final-validation
allowance of one beta.14 concrete execution (600 seconds) and one consumer/
independent-oracle validation (600 seconds). This is at most 42 validation
calls and 25,200 validation seconds per method; five methods permit at most
105 candidates, 210 calls, and 126,000 validation seconds.

Record for every method and slot: analysis elapsed time, final-validation
elapsed time, and their sum. A candidate rejected by concrete validation
triggers refinement when the method and remaining analysis budget permit; the
rejection and cost remain charged. Final validation is not analysis budget and
cannot be transferred between methods or used to continue abstract search.
Real-proof validation remains a later, separately frozen gate with equal
method treatment; no new proof budget is created here.

### 1.4 Freeze and consistency rules

Before primary execution, freeze and hash every generator, extraction and
selection rule, policy, initial query, solver configuration, method budget,
validation rule, source and artifact. Adaptive queries are hashed and logged
before their individual execution. No method may receive a post-result rule or
additional fact.

Stop the comparison if an abstract method returns UNSAT while validated
full-relation analysis returns SAT for the same artifact, state, policy,
property, and bounds. That is a preservation conflict requiring investigation.
An abstract SAT candidate rejected by the full relation is a refinement event,
not a conflict. UNKNOWN versus SAT or UNSAT is unresolved versus resolved, not
a contradiction.

### 1.5 Semantic and claim corrections

- A successful zero-value mint still commits `mints[hash].spent := true`; it
  remains a protected effect in E. Amount zero does not erase occurrence
  identity or authorization/coverage requirements.
- Report a policy violation separately from demonstrated financial impact.
  A committed spent-write or zero-value effect may violate policy without an
  established token loss.
- Fixed-pre-state results quantify only over the declared admitted pre-state.
  They do not establish a reachable-history result.
- Producer kind 4 is part of the producer grammar but unsupported by the V2
  policy/consumer success path. A policy occurrence involving kind 4 yields
  UNKNOWN; it is not silently discarded.
- Assumptions must separately record: `agg_agg` to `agg_final` value
  forwarding; recursive-proof/key correspondence and cryptographic soundness;
  producer grammar and N-bound truncation; padding activation/substitution;
  logical-frame/offset occurrence mapping; consumer decoding/rollback; and
  analyst-supplied P/O plus funded/no-substitution state policy.
- No T22 result automatically becomes a D1 authorization or coverage verdict.
  Track A is a selected producer-cone diagnostic, not the full producer/
  decoder/consumer relation.

Primary timed method comparisons must run on one frozen Linux environment.
Native macOS is permitted only for non-primary equivalence checks such as this
task, with exact platform, solver version, binary hash, arguments, and limits.
Track B implementation and real-proof validation remain future work and do not
block D1P-04 transformation validation.

## 2. Frozen transformation target

Parents are the exact six D1P-02 SMT files and their frozen SHA-256 identities.
For each family, all three parents have an identical byte prefix from byte zero
through the complete ordered selected-producer constraint encoding. The first
v5 walk definition starts immediately afterward. The specializer must locate
that boundary structurally and require the known parent hashes.

For each of the 25 D1P-03 cells and each parent, emit one specialized query in
a fresh ignored `results/raw/D1P-04/generated/` tree: **150 files**. Every
output must:

- retain the complete producer prefix byte-for-byte and in order;
- add the explicit two-stream cell predicate over the original activation and
  word witnesses;
- replace only the v5 walk/rank goal with the D1P-03 fixed-length form;
- use the original payload witnesses at the exact emitted rank: stream 0
  offsets `0..L0-1`, followed by stream 1 offsets `0..L1-1`;
- compare ranks 0..7 to the original outer-message witnesses for prefix;
- treat total emitted length above 8 as prefix overflow;
- implement tail over outer-message offsets from total length through 7, with
  false tail for total above 8; and
- never constrain payload values, remove/add a producer assertion, or change
  a frozen parent.

The artifact manifest records parent/output/generator hashes, cell predicate,
rank-to-stream/offset/payload mapping, producer-prefix offsets/hash/byte audit,
and the associated equivalence-query hash.

## 3. Equivalence formula

For each output construct a separate producer-free validation query:

```text
cell AND common_definitions AND
((original_goal AND NOT specialized_goal) OR
 (specialized_goal AND NOT original_goal))
```

This is the original/specialized XOR and checks both implication directions in
one call. `common_definitions` consists of the exact original v5 walk/rank
definitions plus declarations, with their original finite-field sorts, for
the outer messages, two stream arrays, and activation witnesses. It excludes
all producer assertions. The original goal is converted from the parent's
last assertion into a definition and is not also asserted. The specialized
goal and cell use the same original witnesses; no correspondence equality or
unconstrained auxiliary value is introduced.

UNSAT establishes goal equivalence within that cell for the emitted SMT
semantics. SAT is a counterexample and stops execution. Timeout/error leaves
equivalence unestablished and makes the cell unusable. Eligibility additionally
requires the producer-prefix byte audit. All 150 cells must be eligible before
the complete partition may be used in a primary experiment.

## 4. Authorized non-primary execution

Only these calls are authorized:

1. known-equivalence harness, expected UNSAT;
2. deliberate-mismatch harness, expected SAT; then
3. 150 cell-equivalence calls in frozen manifest order.

Maximum: **152 calls**, one attempt each, sequential, 30 seconds per call,
4,560 aggregate solver wall-seconds, and 4,294,967,296 bytes address space per
process. Use cvc5 with `--lang=smt2 --ff-solver=split`. There are no retries,
tuning, alternate solvers, primary queries, or unit-test solver calls.

The controls run first. A control failure, solver/configuration identity
mismatch, artifact/freeze mismatch, or equivalence SAT result stops all later
calls. A timeout, process error, malformed output, or nonzero exit also stops.
The ledger must identify every unrun cell. Complete stdout/stderr, argv, input
hash, start/end time, elapsed time, exit status, timeout status, and parsed
result are retained per call.

## 5. Interpretation and stop

D1P-04 succeeds only if both controls behave as designed, all 150 equivalence
queries return UNSAT within budget, every producer-prefix audit passes, and the
tracked ledger/manifest agree with raw logs. Task completion without those
conditions is not validation success.

Even complete success establishes only eligibility of this exact 25-cell SMT
transformation for later primary use. It does not establish satisfiability of
any parent/cell, cone completeness, whole-ACIR fidelity, proof feasibility,
consumer execution, method advantage, financial impact, or a D1 verdict.
Research verdict remains UNKNOWN. Stop after the report for planner review.
