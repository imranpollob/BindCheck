# D1P-19 — draft O1/O2 campaign protocol

Date: 27 October 2026  
Status: **DRAFT — NOT FROZEN, NOT AUTHORIZED FOR SOLVER EXECUTION**  
Depends on: D1P-B02 revision 2, D1P-15, D1P-19, D1P-20, and planner review  
Research verdict: **UNKNOWN**

This document records a prospective O1/O2 campaign shape. It does not reserve
slots, choose final budgets, hash queries, or authorize a solver run. Freezing
waits for D1P-20 and explicit planner review.

## 1. Hash layers

### L0 — current encoder behavior

The current `joint_warptoad.py` encoding retains the beta.22 arithmetic/range
constraints, including all compiler-lowered BN254 Poseidon arithmetic. For each
of the 86 `Poseidon2Permutation` opcodes it declares the four output witnesses
but emits no relation between those outputs and the four inputs. Thus all 344
Poseidon2 output words are independent havoc values, even when two opcodes have
identical input vectors. L0 adds no functionality, ground-instance, collision,
preimage, injectivity, surjectivity, or permutation axiom.

### L1 — functional uninterpreted permutations

L1 changes only the treatment of the 86 Poseidon2 opcodes. Introduce one shared
width-4 function for the pinned Poseidon2 permutation and constrain each
opcode's four output witnesses to its application on that opcode's ordered
four-input vector. A scalar SMT realization may use four lane functions
`P2_0..P2_3 : F^4 -> F`; these four functions are one tuple-valued construction,
not four independently selected hashes.

Consequences relative to L0:

- identical ordered four-input vectors have identical four-output vectors;
- different inputs may have identical outputs, including identical lane 0;
- no injectivity, collision resistance, preimage resistance, bijectivity, or
  range fact is added; and
- every initialization, absorption, domain-separator, and output-lane boundary
  remains the D1P-15 checked boundary rather than a desired policy clause.

BN254 Poseidon remains exact compiler-lowered field arithmetic in plain L1.
D1P-19 P1 supplies checked region boundaries and functionality, but no BN254
abstraction is silently applied. Any later replacement of one of those regions
by a function application must be a separately checked transformation that
preserves its boundary inputs, output, and all outside uses.

## 2. Obligations, variants, and admitted states

The campaign family would contain four variant-obligations:

| Obligation | Repaired variant | Injected/mechanism-derived variant | State |
|---|---|---|---|
| O1 / DOM-AZ | pinned artifact, VK, verifier, consumer | M-DOM artifact with its own VK/verifier; pinned consumer | frozen `S_DOM` |
| O2 / SRC-EVM | pinned artifact, VK, verifier, consumer | unchanged pinned producer/VK/verifier paired with M-SRC consumer | frozen `S_SRC` |

The D1P-19 provenance record is the identity gate. `S_DOM` is synthetic
fixed-pre-state admitted-tree evidence and makes no Aztec insertion, bridge,
sequencing, adapter, or cross-chain reachability claim. `S_SRC` contains two
actual owned-local burns with distinct amounts and recorded LazyIMT roots.

Every arm for one variant-obligation receives the same canonical `Omega`,
scope predicate, policy, admitted state, term inventory, and hash layer. A
mutation is a distinct system under test, never an ablation.

## 3. Proposed comparison arms

Subject to planner approval, each variant-obligation would use the B01/B02
arms: monolithic (`MONO`), goal-cone (`GC`), consumer-directed (`CD`), the
same machinery without consumer-derived selection facts (`CF-ABL`), and
consumer-directed selection without propagation (`CD-NOPROP`). All ablations
retain every consumer guard as a semantic constraint. Final budgets, order,
repetitions, memory policy, concretization allowance, and stopping rules are
left blank until D1P-20 and planner review; this draft cannot be used as a
freeze manifest.

## 4. Outcome interpretation and validation

Plain L0 or L1 `SAT` is only an abstraction candidate. It must be replayed
against exact hashes and the concrete variant through the accepted validation
route. A pinned-variant SAT model may be spurious because an uninterpreted
function may collide on distinct inputs. It is never reported directly as an
end-to-end vulnerability.

Any construction no-collision run is a separately named variant, for example
`L1+NC_constr`; it is not called plain L1. It is eligible only if:

1. the D1P-19 P6 construction-identity/domain audit still passes against the
   exact frozen inputs;
2. the query term set equals the D1P-19 program/ground-term inventory after an
   independent recomputation;
3. the B02 §3.3 conditional extraction/collision argument is accepted for the
   exact artifact/VK/verifier variant; and
4. `NC_constr` ranges over complete H3/H1/H2/H3 constructions, never raw
   Poseidon2 output lanes or cross-construction pairs.

Such an UNSAT can support only the predeclared conditional result class and
assumptions. It is not an unconditional cryptographic proof. SAT still requires
exact-hash concretization and V-EXEC. Any required real proof uses the
variant's recorded artifact/key/verifier pairing and a bounded, separately
authorized proof budget.

## 5. Freeze gate

Before any solver launch, the final protocol must record and hash:

- D1P-20's remaining planner-required inputs;
- exact `Omega`, policy, variant, admitted-state, and public-layout identities;
- L0/L1/optional-no-collision layer names and checked transformations;
- the exact term-set equality certificate against D1P-19 P6;
- all arms, budgets, order, repetitions, controls, resource policy, and stop
  conditions; and
- candidate-validation and claim-language rules.

No element above is frozen by D1P-19. No solver was run while preparing this
draft.
