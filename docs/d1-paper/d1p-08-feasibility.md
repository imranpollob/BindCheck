# D1P-08 consumer-direction feasibility assessment

Date: **25 October 2026**. Status: **PROPOSAL FOR PLANNER REVIEW; NOT A JOINT
METHOD IMPLEMENTATION**. No solver query, proof, replay, or Track A rerun is
part of this assessment.

## Baseline for counts

Ordinary T22 goal-cone slicing retained **620 ACIR opcodes / 540 witnesses**
for check-added and **627 opcodes / 555 witnesses** for running-flag. Their
SMT producer blocks contain 2,242 and 1,985 assertions respectively. These are
selected cones, not the full producer relation. Every row below reports the
conservative D1P-08 estimate against those cones: retain the entire applicable
cone and remove **zero** producer opcodes/witnesses unless a future checked
summary proves omission sound. Adding a consumer guard is not by itself a
license to omit any producer constraint.

## Candidate facts

| Candidate fact | Source and applicability | Information beyond ordinary goal-cone slicing | Applicable positions and conservative count | Potential elimination or summary | Soundness still required |
| --- | --- | --- | --- | --- | --- |
| Exact consumer decoding and bounds | Payy B `RollupV1.sol:328-354,384-475`; exact registered length and outer public-input vector | The consumer accepts only kind widths 0→1, 2→4, 3→5; kind 4/other and truncated records revert. This differs from the producer walk. | N=8 outer message offsets 0–7. Retain 620/540 or 627/555; remove 0/0. | There are exactly **11** successful N=8 kind-shape traces (compositions of 8 from widths 1, 4, and 5). Intersecting the producer relation with those traces can remove consumer-reverting cases and expose smaller path summaries. | Prove exact outer-vector mapping, complete path coverage/disjointness, Solidity bounds semantics, and that case pruning is conditioned on successful consumer return. Do not fix payload values. |
| Prover, key, root, signature, verifier, and height guards | `RollupV1.sol:152-155,323-369,725-851`; only the configured verifier/key, current state, admitted caller, signature result/post-state, accepted proof, and increasing height | Attacker feasibility and commit/revert conditions are absent from a producer-only slice. | All records; no record-specific opcode subset. Retain 620/540 or 627/555; remove 0/0. | Reject non-committing consumer cases early; summarize all prior writes under one final commit predicate. | Bind the exact key, verifier address, proof, public vector, signature inputs, and guard state; justify attacker capabilities and fixed pre-state. Proof soundness remains external. |
| Mint registry guards and protected spent writes | `RollupV1.sol:406-439`; kind 2 records, exact note-kind/value/hash lookup, initially supported registry state | Adds sequential registry state, duplicate rejection, and the effect that a matching entry becomes spent. A default zero entry permits a zero-value mint and its spent write remains protected. | Successful N=8 traces can start mint records at offsets **0–4**, with at most **two** mint occurrences. Retain both cones completely; remove 0/0. | A consumer path summary can replace repeated registry interpreter steps on the consumer side and can eliminate paths with a failed second lookup. | Prove the summary equivalent for ordered mapping reads/writes and outer rollback. Preserve zero-value effects and occurrence identity; do not infer `P` or `O` from the registry. |
| Burn decoding, token guards, and committed transfers | `RollupV1.sol:409-475,504-534`, ordinary OZ 5.0.1 token adapter; kind 3, no substitution, exact supported token, funded V2 state | Adds low-160 recipient equality, sequential balances, call success/failure, and the distinction between an attempted burn and committed `E`. | Successful N=8 traces can start a burn at offsets **0–3** and contain at most **one** burn. Retain both cones completely; remove 0/0. | Summarize one supported transfer per N=8 trace; paths with failed transfers remain successful consumer scans but contribute no transfer effect. | Prove deployed-token/code correspondence, exact call/return semantics, funding/value scope, no substitution, state sequencing, and rollback. A failed call is not silently an effect. |
| Reverts and effect-bearing positions | `RollupV1.sol:349-369` plus message helpers; applies to every message effect and all later guards | Makes every candidate `E` conditional on the whole outer call returning, not merely on decoding a record. | Mint positions 0–4; burn positions 0–3; header/message vector positions 0–10. Retain both cones completely; remove 0/0. | One atomic commit predicate can guard the final effect multiset and avoid treating intermediate writes/events as committed evidence. | Validate every reverting and unsupported edge, token state rollback, guard-frame state, and no postlude omitted by the AST closure. Fixed-pre-state only. |
| `agg_agg` → `agg_final` → consumer forwarding and full relation | Payy B `agg_agg/main.nr:14-114`; `agg_final/main.nr:7-38`; `RollupV1.sol:314-369`. Applies only with revision/key-matched recursive verification and exact outer ABI mapping. | Connects logical producer-frame occurrences to the exact outer vector consumed by Solidity; ordinary slicing alone does not establish this correspondence. | The full producer opcode/witness count is **not yet inventoried**. The 620/540 and 627/555 cones cannot stand in for it; no safe removal count exists. | A proved forwarding summary could expose only the frame/message facts required by the 11 consumer traces while retaining a full-relation validation obligation. | Typed ACIR/ABI bindings, logical-frame activation/certification, both key hashes, recursive proof soundness, all 1,000 forwarded messages, N=8 embedding/padding, and occurrence mapping must be proved. The historical selected cone is insufficient. |

## Proposed transformation beyond ordinary slicing

The concrete candidate is **consumer-success trace intersection**:

1. Enumerate the 11 exact N=8 successful consumer control-flow shapes over
   kind widths 1, 4, and 5. Payloads remain symbolic.
2. For each shape, add its decoding/bounds predicates, applicable registry or
   token-state guards, the final verifier/height commit predicate, and the
   relevant authorization/coverage goal to an equal-information producer
   query.
3. Keep all producer constraints initially. Hash and validate every generated
   query. Compare against an ordinary goal-cone control using the same case
   treatment and budget.
4. Only after proving a full-producer-relation implication for a checked
   summary may a later refinement step omit producer constraints. Validate any
   abstract candidate against the full relation; rejection triggers refinement.

This is beyond dependency slicing because the partition comes from the actual
consumer control flow, state guards, and commit semantics rather than a
backward producer dependency graph. It currently claims **zero** producer
opcode/witness removal. The 11-shape count does not establish a performance
benefit, and the absence of an immediate large reduction does not refute the
method.

No proposed transformation fixes dynamic note kinds, amounts, hashes,
recipients, roots, or proofs. No transformation assumes the authorization
relation it is meant to test.

## Required integration before a joint experiment

The minimum remaining work is to build and offline-validate a **forwarding and
occurrence-mapping certificate**, not to run the solver yet. It must connect:

1. active, certified logical frames in the full pinned `agg_agg` relation;
2. their ordered message occurrences and payload fields;
3. `agg_final`'s exact key-bound recursive public-input vector;
4. the outer three-header-plus-message vector passed to `RollupV1`;
5. each symbolic consumer effect occurrence, including low-160 recipients,
   mint spent writes, failed transfers, and outer rollback; and
6. independently sourced analyst `P` and `O`, with exact multiplicity and
   injective matching against committed `E`.

The certificate must fail closed on unsupported kind 4, substitution,
unmodeled tokens, unresolved caller/signature/verifier facts, padding or frame
ambiguity, missing proof/key correspondence, and any mismatch between N=8
analysis and N=1000 deployed forwarding. Only after this gate should both
planners decide whether the 11-trace transformation justifies implementing and
testing the joint method.

