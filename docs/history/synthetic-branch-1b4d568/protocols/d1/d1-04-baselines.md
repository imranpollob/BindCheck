# D1-04: Equal-Information Baselines

**Version:** 1  
**Date:** 2026-10-23  
**Prerequisite:** D1-03 DONE (synthetic pipeline validated)

## Objective

Run three baselines on the same synthetic cases, facts, bounds, and policy as D1-03.
Measure preparation cost, annotation cost, query time, and verdict correctness. The
comparison is informational for D1-05/D1-06; it does not yet test consumer-directed
refinement (that is D1-05).

## Baselines

### B1: Direct Foundry tests

Write a `SynthSettlement.sol` consumer that models the same record grammar (N=9, 3-word
stride, kinds 0/2/3) and a corresponding test that supplies concrete valid-proof seeds
and checks whether an unauthorized burn can be settled. This is the strongest simple
baseline: it tests the actual consumer code path with real inputs.

**Metric:** analyst time to write the test (measured in lines of code and manual
annotations), test execution time, and whether the test finds the VIOLATION / confirms
the repair.

### B2: Monolithic joint solving (no propagation)

Run the D1-03 joint encoder with propagation disabled (pass all constraints as residual).
Same solver, same timeout, same goals.

**Metric:** solver time per goal, verdict, and comparison with D1-03 propagated times.

### B3: Summary-based modular check (CIVER-style adaptation)

Manually write a producer summary as a set of field constraints that express "if
`authorized` is well-formed and compact, then `messages` equals `authorized` in the
active prefix and is zero in the tail." Compose this summary with the policy grammar
walk and check the same goals.

This is labeled an adaptation, not a reproduction of CIVER. CIVER works on circuit-level
summaries with abstraction refinement; here we manually specify the summary.

**Metric:** analyst annotation cost (LOC), solver time, verdict correctness, and whether
the summary must be updated when the circuit changes.

## Cases

Same as D1-03:
- `synth-faulty` (expected B1: VIOLATION detected, B2: VIOLATION, B3: VIOLATION)
- `synth-repaired` (expected B1: no violation found, B2: VERIFIED_WITHIN_SCOPE, B3: VERIFIED_WITHIN_SCOPE)

## Limits

- Solver: cvc5 1.4.2 GPL/CoCoA, `--ff-solver=split`, 60 s per query, 4 GiB
- Foundry: forge 1.4.1, solc 0.8.20, 600 s per test
- nargo: 1.0.0-beta.14

## Completion criterion

A table comparing all three baselines with D1-03 across: verdict, evidence grade,
solver/test time, analyst annotation LOC, and a judgment on whether the D1-03 pipeline
adds value over each baseline for these synthetic cases. An honest assessment may
conclude that the pipeline does not yet demonstrate an advantage.

## Stop for review

After D1-04, stop and present the comparison to the user before proceeding to D1-05.
