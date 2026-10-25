# D1P-09 binding and offline propagation feasibility

Date: **25 October 2026**. Scope: **check-added N=8, AUTH and NONVAC
preparation only**. This note does not define or execute a joint query.

## Evidence boundary

The exact recovered producer inputs remain the printed check-added ACIR and ABI
from evidence commit `7d098cd393c5cc8609765b663d393fcaebf24aeb`.
The printed input has 1,242 non-recursive listed operations plus two separately
parsed recursive calls. The historical selected cone used by T22 contains
**620 operations and 540 witnesses**: 546 assertions, 58 range constraints, 15
reads, and one memory initialization.

A locally preserved full serialized N=8 producer artifact also exists in the
T22 scratch tree. Its source SHA-256 is the recorded check-added
`af9df507...`, its ABI exactly equals the recovered ABI, and its artifact
SHA-256 is `e7b5731c...`. Typed decoding finds **1,303 opcodes** and current
witness index 3,508: 1,135 assertions, 91 Brillig calls, 58 ranges, 15 memory
operations, one memory initialization, one Poseidon permutation, and two
recursive aggregations. The independent checker accepts 1,280 producer
boundary equalities. This artifact was not part of evidence commit `7d098cd3`
and does not turn the 620-operation cone into the full relation.

No matching compiled N=8 `agg_final` artifact was found in the recorded
locations. The one authorized isolated reconstruction compile preserved the
complete word-boundary transformation:

- `messages: [Field; 1000]` and `0..1000` become 8;
- both `1005` public-input array lengths become 13; and
- no other pinned source byte is deliberately changed.

The pinned beta.14 Nargo process exited 101 after 0.0126 seconds because it
could not lock the external local dependency cache under the sandbox policy.
It emitted no artifact. The exact N=8 forwarding constraints, verification
key, proof, and deployed registration therefore remain absent. The checked
N=1000 `agg_final` artifact (`89c1d5d...`, 1,630 replayed equalities) is
background evidence only; it is not substituted for N=8.

## Interface map and evidence grades

| Producer output | Forwarder | Consumer position | Grade |
| --- | --- | --- | --- |
| `old_root`, `w1272` | `agg_final.old_root` | `publicInputs[0]` | N=8 producer mechanically checked; N=8 forwarding source-supported only; consumer source-supported |
| `new_root`, `w1273` | `agg_final.new_root` | `publicInputs[1]` | Same |
| `commit_hash`, `w1274` | `agg_final.commit_hash` | `publicInputs[2]` | Same |
| `messages[i]`, `w(1275+i)` | `agg_final.messages[i]` | `publicInputs[3+i]` | Same, for `0 <= i < 8` |

The N=8 producer certificate and frozen specification mechanically locate
frame-0 selected message expressions at `w511..w518`, frame-1 selected
recursive-public-input expressions at `w2293..w2300`, and activation roots at
`w508` and `w1143`. They do not prove that the full producer relation realizes
an assumed concatenation for an arbitrary case. The pinned `agg_final` source
directly constructs two key words followed by the three headers and all
messages; the N=1000 artifact confirms that structure at N=1000 only.

Permissions `P` remain inner-frame occurrences. Obligations `O` remain
analyst policy. Effects `E` remain committed consumer spent-writes and
successful funded ordinary-token transfers after the whole call succeeds.
Equality or positional forwarding does not identify `P` with `E`, establish
authorization, or justify N=8/N=1000 equivalence.

## Exact successful N=8 decoding shapes

The consumer decoder has widths 0→1, 2→4, and 3→5. The exact successful
kind sequences whose widths sum to eight are:

| ID | Reached kinds | Fixed positions | Payload treatment |
| --- | --- | --- | --- |
| 00 | `0 0 0 0 0 0 0 0` | 0–7 | all-padding; no payload |
| 01 | `0 0 0 0 2` | 0,1,2,3,4 | positions 5–7 symbolic |
| 02 | `0 0 0 2 0` | 0,1,2,3,7 | positions 4–6 symbolic |
| 03 | `0 0 0 3` | 0,1,2,3 | positions 4–7 symbolic |
| 04 | `0 0 2 0 0` | 0,1,2,6,7 | positions 3–5 symbolic |
| 05 | `0 0 3 0` | 0,1,2,7 | positions 3–6 symbolic |
| 06 | `0 2 0 0 0` | 0,1,5,6,7 | positions 2–4 symbolic |
| 07 | `0 3 0 0` | 0,1,6,7 | positions 2–5 symbolic |
| 08 | `2 0 0 0 0` | 0,4,5,6,7 | positions 1–3 symbolic |
| 09 | `2 2` | 0,4 | positions 1–3 and 5–7 symbolic |
| 10 | `3 0 0 0` | 0,5,6,7 | positions 1–4 symbolic |

Enumeration covers all `5^8 = 390,625` equality/control-flow class vectors
over padding, mint, burn, representative unsupported kind, and producer kind
4. Exactly 18,751 decode successfully, 291,312 encounter an invalid reached
kind, and 80,562 truncate. Every successful vector satisfies exactly one
shape predicate; invalid and truncated vectors satisfy none. Because payload
positions are ignored by the decoder at those steps, their values remain
symbolic rather than being assigned representative constants.

These predicates describe successful structural decoding only. Root/height,
registry/token state, caller/signature, exact verifier key/vector, commit, and
outer rollback guards attach separately. A failed token transfer can leave the
scan successful while contributing no transfer effect. A later revert rolls
back earlier transfer effects and mint spent-writes. A zero-value matching mint
still has a protected `spent=true` effect.

## Conservative propagation

The implementation selectively adapts the exact-substitution and known-memory
ideas from Claude-worktree `analysis/propagate.py` SHA-256 `0957b5f1...`; it
does not import that worktree's synthetic encoder. It intentionally omits the
prototype's small-domain rule. Each original selected-cone constraint is:

1. retained after exact substitution;
2. discharged only when its exact ground field value is zero or its range
   value is in bounds; or
3. used to assign one witness only when a nonzero affine coefficient gives a
   unique field solution.

A memory read becomes an equality only when its index and all preceding write
indices are known. Symbolic writes retain the suffix. Eliminated interface
witnesses receive explicit reconstruction equalities, and the complete case
predicate is retained verbatim. The regression for T22's lost implied goal
equality verifies that an eliminated `w_goal = w_source` constraint survives
as an auditable interface reconstruction.

For producer cells, `activation != 0` is never changed to field value 1. The
length-5 `{3,4}` disjunction and truncated cell branches remain intact. Only
`inactive => activation=0` and `length_4 => first_word=2` are propagated. For
consumer shapes, only reached kind positions are fixed. No payload is fixed.

The baseline and every case use the same rules on the same check-added cone:

| Family | Cases | Original ops/witnesses/ranges | Residual original ops | Residual relation witnesses | With case/reconstruction witnesses | Residual ranges | Interface equalities | Contradictions / unsupported selected ops | Aggregate propagation |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| Unsplit baseline | 1 | 620 / 540 / 58 | 620 | 540 | 540 | 58 | 0 | 0 / 0 | 0.0041 s |
| Consumer shapes | 11 | 620 / 540 / 58 each | 612–616 | 532–536 | 540 | 56–58 | 2–8 | 0 / 0 | 0.0659 s |
| Producer cells | 25 | 620 / 540 / 58 each | 499–620 | 438–540 | 540 | 49–58 | 0–4 | 0 / 0 | 0.1425 s |

The per-case ledger is
`metadata/d1/d1p-09-propagation-audit.json`; the full event and assignment
audit is `results/raw/D1P-09/offline-07/propagation-audit-full.json`, SHA-256
`7c5b051686090944dcce40e69ce669f1481cd11bd3dd8d452afe715abb3041c1`.
It records why every discharge, reconstruction, and memory lowering occurs.

No case was proved feasible. No contradiction was found. “Residual relation
witnesses” excludes constants and now-free variables; the adjacent column puts
case values, exact reconstructions, and arbitrary free model extensions back,
so a smaller relation count cannot hide a lost equality or interface word.

Full-relation propagation is unsupported. The selected cone contains no
unsupported operation, but the full typed producer includes two recursive
aggregations, 91 Brillig hints, and Poseidon semantics outside this
propagator. The serialized and printed non-transformed assertion sets are also
not established equivalent. None is silently discarded from a full-relation
claim; there is no such claim.

## Feasibility conclusion

A concrete beyond-ordinary-slicing opportunity is demonstrated on the
historical cone: conditioning on exact consumer-success shapes fixes only
consumer-reached kind words and discharges **4–8 of 620 original operations**;
some shapes also remove one or two range constraints. This is a checked
case-conditioned simplification, not arbitrary payload specialization.

The reduction is small, does not cover the full producer relation, and has no
solver measurement. It neither proves consumer-direction advantage nor
refutes it. The producer 25-cell results are diagnostic comparisons and show a
separate, much larger asymmetry when the first stream is fixed to producer
kind 2; they are not evidence for consumer direction.

Both planners must decide whether this limited but concrete transformation is
enough to justify a full-relation propagation/forwarding implementation. The
exact N=8 `agg_final` artifact/key binding must be recovered first or remain an
explicit blocker. The research verdict remains **UNKNOWN**.

