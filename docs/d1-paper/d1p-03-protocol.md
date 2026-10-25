# D1P-03 experiment protocol and offline validation

Date: **25 October 2026**. Status: **PROTOCOL READY FOR PLANNER REVIEW;
EXECUTION NOT AUTHORIZED**. Research verdict: **UNKNOWN**.

This protocol separates a frozen producer-side comparison (Track A) from a
future producer/decoder/consumer experiment (Track B). D1P-03 performs only
offline finite validation. It executes no SMT query, proof build, consumer
replay, held-out evaluation, or refinement implementation.

## 1. Source and semantic boundary

Pinned Payy B is
`dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36`. At that revision:

- `RollupV1.verifyRollup` requires `publicInputs.length == messages_length + 3`,
  where `messages_length` is stored in the selected verifier configuration.
  `verifyAllMessages` starts at public-input index 3 and scans exactly that
  configured interval.
- Consumer kind **0** advances by one word. Kind **2** calls `verifyMint`,
  reads four words including the kind, and returns `i + 4`. Kind **3** calls
  `verifyBurn`, reads five words, and returns `i + 5`. Kind **4** and every
  other kind revert. A kind 2 or 3 too close to the configured end can make
  the helper read beyond calldata and revert; the loop bound does not turn a
  truncated record into a successful short record.

This consumer decoder is not the frozen Track A producer specification. The
producer walk operates on two N=8 recursive-proof message arrays. An inactive
frame emits nothing. In an active frame it treats kinds 2, 3, and 4 as record
starts of length 4, 5, and 5; another kind ends export, and the check-added
source requires the remaining words to be zero. A record begun inside the
fixed eight-word array is emitted through position 7 even when its logical
length would extend past N. Consequently, producer kind 4 can be exported but
cannot participate in a successful consumer scan. Track B must encode that
disagreement; policy extraction must report unsupported kind 4 as UNKNOWN,
not infer that it creates no permission or obligation.

The frozen N=8 builder is `scripts/t22_v5_compact.py`, SHA-256
`39cb3731d6e2921ac0a59c21dbd5d18a7a91bec18628e0e6bb843382d766c792`.
The walk spec is `scripts/t22_specs/payy_agg_agg.json`, SHA-256
`dd7e17ed2c9cd74000182ea613184a53f86bd1944f86a5c5cc8016663a203e1c`.
Neither file is changed by this protocol.

Track B also retains pinned Payy A
`c4d2c9021b8fb9988816eb6987a734b830bfce15`. Its inspected `agg_agg` keeps
the same producer walk but lacks B's final outer-message tail-zero assertion;
its `agg_final` has the same forwarding structure with a revision-specific
`AGG_AGG_VERIFICATION_KEY_HASH`. Its `RollupV1.sol` bytes are identical to B.
Revision/key identities must never be mixed.

## 2. Track A: frozen six-query comparison

Let `G_q` be the frozen v5 goal for `q` in `{nonvacuous, prefix, tail}`.
Let `C` be the conjunction of only those printed-ACIR assertions selected by
the legacy backward witness cone from the outer messages, the two inner
message arrays, and the two activation expressions. **C is not the full
producer relation `R_v`.** Omitted components are only assumed satisfiable;
the printed-ACIR parser, unmodeled black boxes, recursion feasibility, and
cone soundness remain limitations.

The exact combined formulas are the six byte-identical D1P-02 queries:

| Artifact | Goal | SHA-256 |
| --- | --- | --- |
| check-added | nonvacuous | `c0312431ed84da5b55094fc4b27212f607789d143ad56b54db52359235b794b3` |
| check-added | prefix | `4ae2be7bcedcfe992966dc406d4cd8f2b43f1823fa49efd8fbfa14044631e781` |
| check-added | tail | `3621cdfca8269e404aca638a24aa852da0406be1013f2c29511df47b6ff0a7a1` |
| running-flag | nonvacuous | `af1ae83aafa43b9dbb06e110270dda0bff11c90371c2666143916fb067b21ff8` |
| running-flag | prefix | `6ac4b20422b09c0deea148b977159919d1542b7d587cdde38a9e9583671b82b4` |
| running-flag | tail | `4d80a119dfe1f781eb2a47cb60490143afc930eb150dec2b4da980370d900a3c` |

`nonvacuous` asks for a total emitted length from 1 through 8. `prefix` asks
for a mismatch between an emitted word and the same-rank outer message, and
also treats a ninth emitted word as a mismatch. `tail` asks for a nonzero
outer message at or after the final emitted rank when that rank is at most 8.

Four diagnostic forms are kept distinct:

| Form | Formula | Interpretation | Anticipated result, not an observation |
| --- | --- | --- | --- |
| Goal-only | `G_q` | Specification satisfiability without ACIR | SAT for all three goals |
| Producer-cone-only | `C` | Selected-cone satisfiability without a goal | SAT for both artifacts |
| Combined | `C ∧ G_q` | Exact historical query bytes | nonvacuous SAT; prefix and tail UNSAT for each repaired idiom |
| Partitioned | `C ∧ G_q ∧ cell_ab`, with sound cell specialization | Diagnostic decomposition of the same combined formula | disjunction matches combined; individual expectations depend on the cell |

These labels are hypotheses used to interpret diagnostics. They are not
verdicts and must not be encoded as assumptions. Historically, all six
combined queries timed out and remain UNKNOWN. The older v3-derived
**goal-only reduction** also timed out; the later v5 **specification-only**
queries returned SAT. Neither result decides `C ∧ G_q`.

### 2.1 The 25 cells

For one stream, `a` is its activation Boolean, `w0..w7` its words, and
`V = {2,3,4}` the producer-valid record kinds. The five predicates are:

| Cell | Predicate | Observed emitted length |
| --- | --- | ---: |
| `inactive` | `¬a` | 0 |
| `active_empty` | `a ∧ w0 ∉ V` | 0 |
| `length_4` | `a ∧ w0 = 2 ∧ w4 ∉ V` | 4 |
| `length_5` | `a ∧ w0 ∈ {3,4} ∧ w5 ∉ V` | 5 |
| `truncated_8` | `a ∧ ((w0=2 ∧ w4∈V) ∨ (w0∈{3,4} ∧ w5∈V))` | 8 |

The two-stream partition is their Cartesian product, yielding exactly 25
cells. `truncated_8` includes a second producer record of logical combined
length 8, 9, or 10; only eight source-array positions are observed. Pair totals
can be 0, 4, 5, 8, 9, 10, 12, 13, or 16. A total above eight activates the
frozen prefix-overflow goal and cannot satisfy the frozen nonvacuous goal.

Partition specialization may replace only the producer-walk flag expressions
under the asserted cell predicate. It may not drop or add a selected ACIR
constraint, change `G_q`, fix message values, or supply a missing producer
binding. Every generated cell must carry the parent query hash, cell predicate,
specializer hash, and a mechanical byte/provenance audit.

## 3. Offline partition validation

`scripts/d1p_03_partition_check.py` has no solver or process-launch interface.
It reads the frozen walk spec and uses an independent literal transition as
the reference. Its finite alphabet is `{0,1,2,3,4}`: zero and representative
nonzero kind 1 separately cover the two producer-invalid/consumer-distinct
classes; 2, 3, and 4 are the three producer record kinds. All other field
values are equivalent to 1 for this producer walk.

The completed check exhaustively enumerates both activation values and all
`5^8` word-class vectors: **781,250 stream cases**. Every case matches exactly
one cell, and both the cell-specialized flags and the compact formula match
the literal transition. Cell counts are 390,625 inactive; 156,250
active-empty; 31,250 length-4; 62,500 length-5; and 140,625 truncated-8.
Within truncated-8, logical two-record lengths 8, 9, and 10 occur in 15,625,
62,500, and 62,500 cases.

The checker then covers all 25 cell pairs. It compares a rank-state evaluator
of the three frozen goals with closed specialized goals for every 8-bit
prefix-mismatch pattern and every 8-bit tail-nonzero pattern: **12,825 goal
cases**. All pass. Eight pair cells have emitted totals above eight. The raw
result is `results/raw/D1P-03/offline-check.json`.

This enumeration establishes exhaustiveness and mutual exclusion for the
five semantic equivalence classes at N=8, and equivalence of the specialized
walk/goals over those classes. Pair coverage/exclusion follows from the
Cartesian product of the individually exhaustive/disjoint partitions, and all
25 products are checked nonempty. It does **not** establish ACIR
satisfiability, cone completeness, query serialization, solver behavior,
consumer execution, proof feasibility, reachable state, or a security verdict.
It does not generalize to N=1000 or a changed record grammar.

## 4. Track B: prospective joint experiment

Track B is a specification only. The joint symbolic solver, selection, and
refinement implementation do not yet exist.

### 4.1 P, O, and E

- `P` is an occurrence multiset of permissions from **active, certified
  logical producer frames**, keyed by `(frame_id, message_offset)`. Under the
  reviewed V2 policy, a supported kind-2 record supplies one mint permission
  and a supported kind-3 record one burn permission. Equal values in two
  frames remain two occurrences.
- `O` is a separately represented occurrence multiset of required immediate
  settlements. The V2 analyst policy classifies each supported active mint or
  burn as mandatory in the funded immediate-settlement family. This is a
  reviewed policy choice motivated by pinned documentation; it is not inferred
  from how the implementation happens to behave, and no generic rule sets
  `O := P`.
- `E` is the multiset of committed protected effects from an actual successful
  consumer transition: a mint is the committed `mints[hash].spent := true`
  occurrence after registry checks; a burn is a successful exact-token
  transfer occurrence with the decoded low-160 recipient and committed token
  state. An attempted or logged transfer is not `E`. Any outer revert discards
  all storage, token, event, and effect observations.

Compatibility retains V2's exact key `(domain, kind, asset/note_kind, amount,
note_hash, decoded_recipient)`, with recipient absent for mint. Authorization
requires injective `E → P`; coverage independently requires injective `O → E`.
Exact-equality keys permit `Counter` multiplicity checks. Splitting,
aggregation, substitution, and deferral remain unsupported.

### 4.2 Required joint link

The relation must include, with checked artifact bindings:

1. the actual `agg_agg` relation and logical frame activation/certification;
2. `agg_final`'s direct forwarding of `old_root`, `new_root`, `commit_hash`,
   and every `messages[i]` into the recursive `agg_agg` public-input vector,
   preceded by the two pinned verification-key hashes;
3. the outer `agg_final` public inputs presented to `RollupV1` as three header
   words followed by the configured message array;
4. the actual consumer decoding described in Section 1, registry and token
   state updates, external verifier/token boundaries, later guards, and atomic
   rollback; and
5. the independent P/O policy and committed E matching goals.

The supported pre-state remains V2's funded standard-token/no-substitution
family: N is 8 or 1000; only note kind `0x4b` maps to the exact ordinary
OpenZeppelin 5.0.1 ERC20; initial rollup balance and total supply are
`N * (2^64-1)`; other balances are zero; burn amount is at most `2^64-1`;
decoded recipient is nonzero; mint entries start unspent; substitutions are
empty. Token-call success is derived from sequential state, never a free
Boolean. A failed transfer, unsupported token, substitution, truncated
consumer record, kind 4 policy occurrence, or unresolved guard/verifier path
is UNKNOWN.

### 4.3 Evidence grades

A solver SAT model is an abstract candidate. Executing it against actual ACIR
with `nargo execute` is **concrete-model evidence**, not a proof. Running a
consumer interpreter or a harness with an abstract/mocked verifier can confirm
decoding/state behavior, but is still not accepted proof-to-effect replay.

**Real-proof consumer replay** requires a revision- and verification-key-
matched `agg_final` proof, actual verifier acceptance, the unchanged consumer,
an admitted pre-state, normal outer return, and independently checked committed
storage/token effects. Available T13/T16/T18/T19 artifacts are N=1000 and are
a separate evidence grade from N=8 analysis. There is no N=8 real-proof bundle.
Concrete ACIR and committed-consumer validation may support a bounded
`VIOLATION` at **concrete-model** grade under the V2 protocol, but without a
real proof it is not a real-proof/end-to-end replay and cannot satisfy the
central motivating-result validation gate. It also provides no evidence for
`VERIFIED_WITHIN_SCOPE`.

## 5. Prospective execution matrix

D1P-03 consumes **zero** solver, proof, and replay calls. The following limits
apply only after both planners approve a hash-complete execution manifest.

### 5.1 Track A diagnostic matrix

All processes are sequential, use a 4,294,967,296-byte address-space limit,
one attempt, and no retry or changed configuration.

| Form | Logical slots | Calls per slot | Per-call wall cap | Aggregate wall cap |
| --- | ---: | ---: | ---: | ---: |
| Goal-only | 6 | 1 | 300 s | 1,800 s |
| Cone-only | 2 | 1 | 300 s | 600 s |
| Exact combined | 6 | 1 | 300 s | 1,800 s |
| 25-cell partitioned combined | 6 | 25 | 12 s | 1,800 s |
| **Track A total** | **20 logical** | **164 maximum** | — | **6,000 s** |

Each partitioned logical slot therefore receives the same **300 total solver
seconds** as its unsplit combined counterpart, not 25 times that budget.
Startup/encoding overhead is charged. Cells run in the fixed order shown in
Section 2.1 for the left stream, then the right stream, with artifact order
alternated between logical slots. No parallel calls are permitted.

### 5.2 Track B equal-information matrix

Retain the seven V2 case/scope rows: A-1000/S1, A-1000/S2, B-1000/S1,
B-1000/S2, A-8/FREE, B-8/FREE, and m4-8/FREE. Each has AUTH, COVERAGE,
DEFER, and NONVAC, for **28 property slots per method**.

| Method | Property slots | Calls per slot | Per-call cap | Per-method aggregate |
| --- | ---: | ---: | ---: | ---: |
| Monolithic joint | 28 | 1 | 300 s | 8,400 s |
| Equal-information modular | 28 | at most 5 | 60 s | 8,400 s |
| Consumer-directed/refinement | 28 | at most 5 | 60 s | 8,400 s |
| **Track B total** | **84 method-slots** | **308 calls maximum** | — | **25,200 s** |

The five consumer-directed calls mean one initial abstraction and at most four
refinements. The modular baseline receives the same extracted facts, proved
summaries, policy, assumptions, bounds, and total solver budget. Selection,
summary proof, validation, and failed setup time are charged to the method.
If an N=8 method-slot uses the 25-cell decomposition instead, it **replaces**
that slot's ordinary call schedule with at most 25 calls of 12 seconds and a
300-second aggregate cap. It is not an extra diagnostic allowance. If all 36
N=8 method-slots choose partitioning, Track B's call ceiling becomes 1,076 but
its 25,200-second aggregate remains unchanged. No N=1000 partition is defined.

Run one method-slot at a time. For each case/property, rotate method order
monolithic → modular → refinement, modular → refinement → monolithic, then
refinement → monolithic → modular. Alternate A/B order in successive rows.
Freeze all query hashes before the first primary call. Record wall time, peak
RSS, extraction/selection/refinement cost, assertions/opcodes/witnesses,
result, reason code, stdout/stderr, and every intermediate query hash.

### 5.3 Candidate and replay limits

At most one distinct candidate per AUTH, COVERAGE, and NONVAC case/scope is
validated, deduplicated by full model/artifact/policy identity: **21 candidates
maximum**. Each gets at most one beta.14 `nargo execute` call of 600 seconds
and one concrete consumer/oracle invocation of 600 seconds: 12,600 seconds
for each validation stage. No new real-proof generation is budgeted. Separately,
at most three already archived, hash-matched N=1000 proof replays (T13 control,
T16 control, T16 candidate) may receive one 600-second Foundry invocation
each, after a new manifest pairs source, verifier/key, proof, and inputs. They
cannot validate an N=8 candidate.

### 5.4 Result and stopping rules

- Any artifact, tool, query, policy, or source hash mismatch stops the matrix
  before a solver starts. A setup failure consumes its scheduled slot.
- Only a parsed SAT/UNSAT result with exit 0 and complete logs counts. Timeout,
  memory failure, crash, missing output, unsupported behavior, or validation
  failure is UNKNOWN for that slot.
- Partitioned SAT may stop that logical slot after preserving the model and
  unrun-cell ledger. Partitioned UNSAT requires all 25 cells to validate and
  return UNSAT. One missing, invalid, or timed-out cell leaves the aggregate
  UNKNOWN; it never discharges the cell or the unsplit formula.
- Goal-only and cone-only results diagnose components and never discharge a
  combined query. Track A never yields a joint authorization/coverage verdict.
- Track B VIOLATION requires an AUTH/COVERAGE SAT candidate plus concrete
  validation; its evidence grade must say whether real-proof committed-effect
  replay exists. The central motivating result additionally requires that
  real-proof grade. VERIFIED_WITHIN_SCOPE requires AUTH, COVERAGE, and DEFER
  UNSAT, replayed NONVAC SAT, justified abstraction/extraction, and every
  admitted-state gate. Otherwise the result is UNKNOWN.
- Stop the entire run on evidence corruption, policy drift, method-specific
  access to extra facts, an unfrozen query transformation, or evidence that a
  held-out family has been inspected. Do not retune after seeing a result.

## 6. Platform and artifact prerequisites

The exact N=8 inputs and six query bytes are locally available through D1P-02.
The current host is macOS 27.0.1 arm64. It has an arm64 cvc5 1.4.2 GPL/CoCoA
binary at the preservation checkout (SHA-256 `a083a7f5...`) and another
Homebrew cvc5 on PATH. Neither is the historical Linux x86_64 binary
`2406449e...`; timing parity therefore requires the recorded Linux binary,
its pinned libraries, and a compatible Linux host/VM. A native-arm64 run must
be reported as a new-platform semantic comparison, not historical timing
parity.

The preservation checkout also has beta.14 nargo/noirc (arm64 SHA-256
`a0528f1c...`), Forge 1.4.1, solc 0.8.20 (SHA-256 `5d98c9ed...`), pinned Payy
source, verifier binaries, and an arm64 bb 3.0.0 build (SHA-256 `b89b6a9a...`).
They are not provisioned as an isolated Track B toolchain in this worktree.
The PATH solc is 0.8.30 and must not be used. Forge dependencies and
revision-matched proof bundles must be copied into fresh ignored namespaces
and hash-manifested; mutable preservation caches cannot be direct inputs.
PyCryptodome 3.23.0 is installed only in `.venv-d1p-00`.

Track B additionally lacks a joint encoder, checked symbolic consumer
lowering, equal-information modular baseline, refinement implementation,
hash-complete query generator, and N=8 real-proof path. These are blockers,
not implicit assumptions.

## 7. Planner decisions still open

1. Authorize Track A, Track B, both, or neither; protocol review alone does
   not authorize the solver matrix.
2. Choose historical Linux timing parity or a newly labeled macOS arm64 run.
3. Approve or revise the 12-second fixed cell allocation, acknowledging its
   repeated-startup cost, while preserving the 300-second aggregate parity.
4. Approve the V2 immediate-obligation policy through independent human
   review; implementation behavior cannot supply that policy.
5. Decide whether kind 4 makes a Track B row unsupported immediately or is
   excluded by successful-consumer reachability before policy extraction.
6. Decide whether fixed admitted pre-state is the paper's theorem scope or a
   narrower search mode; it is not a reachable-history proof.
7. Decide what real-proof budget/path can validate a new candidate. The
   current zero-new-proof rule cannot validate an N=8 central result.
8. Approve the three-method call schedule and four-refinement ceiling before
   implementing any method, including how preprocessing cost is charged.
9. Decide whether N=1000 rows remain in the first comparison despite having
   no defined partition and materially larger constraints.
10. Resolve how a future paper presents the historical Track A negative
    scalability result separately from Track B method effectiveness.

Until these decisions and missing implementations are resolved, the next
state is planner review and the D1 research verdict remains UNKNOWN.
