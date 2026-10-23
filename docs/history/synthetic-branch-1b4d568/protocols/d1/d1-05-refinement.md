# D1-05 Protocol: Consumer-Directed Refinement

**Version:** 1  
**Date:** 2026-10-23  
**Prerequisite:** D1-04 (fair baselines)

## Objective

Demonstrate consumer-directed abstraction-refinement (CEGAR) on the same
synthetic cases as D1-03/D1-04. The mechanism starts with a consumer-only
abstract model (no ACIR producer constraints), solves authorization goals,
concretizes SAT candidates against the full producer, and refines the abstract
model when candidates are spurious.

## Completion criteria

1. At least one spurious abstract candidate is rejected by concretization and
   the abstract model is refined without removing a real violation.
2. Clean controls preserved: synth-faulty still yields VIOLATION; synth-repaired
   still yields VERIFIED_WITHIN_SCOPE.
3. The mechanism difference from D1-04 baselines is stated with evidence.

## Mechanism

### CEGAR loop for auth_unmatched

```
iteration 0: abstract model (0 ACIR constraints)
  → solve auth_unmatched
  → if SAT: concretize candidate against full ACIR
    → if full SAT: CONFIRMED VIOLATION (replay with nargo)
    → if full UNSAT: SPURIOUS → refine (add relevant ACIR constraints)
  → if UNSAT: VERIFIED (abstract suffices)
iteration 1+: refined abstract model (selected ACIR constraints)
  → repeat
```

### Constraint selection (refinement)

When a candidate is spurious, identify which ACIR constraints to add:
1. Direct: all assert/range constraints mentioning witnesses in the model
2. Transitive (one hop): all constraints mentioning witnesses that appear in
   the directly-selected constraints

This targets the producer constraints that interact with the failing candidate.

### Concretization

Fix the candidate's message/permission witness values, encode ALL ACIR
constraints, check SAT. If satisfiable, the candidate is consistent with the
real producer. If unsatisfiable, the producer cannot produce those values.

## Cases

Same synthetic fixtures as D1-03/D1-04:
- `synth-faulty`: unconstrained message tail (26 ACIR asserts, 0 ranges)
- `synth-repaired`: tail forced to zero (35 ACIR asserts, 0 ranges)

## Expected behavior

- **synth-faulty:** Abstract model finds unauthorized burn (SAT). Concretization
  confirms (full ACIR also SAT because the faulty circuit doesn't constrain
  the tail). VIOLATION at iteration 0 with 0 refinement steps.

- **synth-repaired:** Abstract model finds unauthorized burn in tail (SAT).
  Concretization rejects (full ACIR forces tail to zero → UNSAT). Refine by
  adding tail-related constraints. Re-solve → UNSAT. VERIFIED after 1+
  refinement steps.

## Goals run

- `auth_unmatched`: CEGAR loop (the key demonstration)
- `cov_unmatched`: full encoder (same as D1-03, for comparison/controls)
- `nonvacuity`: full encoder (same as D1-03)

## Toolchain

Same as D1-03/D1-04: nargo 1.0.0-beta.14, cvc5 1.4.2 GPL, hash-pinned
T22-v3 FF builder.

## Measurements

- Iterations to convergence
- Constraints included at each iteration vs total
- Abstract solve time per iteration
- Concretization time
- Total CEGAR wall time vs D1-03 monolithic time
- Final verdict and evidence grade

## Limits

- CEGAR overhead (multiple solver calls) may make total time longer than
  monolithic on these small N=9 circuits.
- The speed advantage of fewer constraints is expected to manifest on larger
  circuits, not demonstrated here.
- Only auth_unmatched uses CEGAR; cov_unmatched and nonvacuity use the full
  encoder.
