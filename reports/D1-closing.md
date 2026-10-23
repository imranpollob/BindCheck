# D1 Closing Report: Consumer-Directed Proof-to-Effect Analysis

**Status:** CLOSED — feasibility gate not passed  
**Date:** 2026-10-23  
**Scope:** D1-00 through D1-06  
**Branch:** `research/d1` (worktree `/home/pollmix/Coding/BindCheck-d1`)

## Summary

The D1 investigation tested whether consumer-directed extraction and
checked summary refinement (CEGAR) adds value over strong baselines for
verifying that zero-knowledge proof effects are authorized by actual
producer constraints. After seven bounded tasks, the answer is: **the
mechanism is correct and sound, but it does not support the claimed
contribution.** Three of five roadmap stop criteria are met. The
feasibility gate is not passed. D1 is closed with an honest negative
result.

## What was attempted

**Research question:** Does consumer-directed, proved summary refinement
improve solved obligations, precision, or total cost beyond an equally
informed monolithic verifier or Foundry testing?

**Method:** Start from consumer effects (authorization and coverage
obligations), construct an abstract model with zero ACIR constraints,
solve, concretize SAT candidates against the full producer constraint set,
and refine by adding reachable constraints when concretization rejects a
spurious candidate.

**Scope:** Noir/ACIR producers, Solidity/EVM consumers, N=9 synthetic
batch settlement circuits (3-word uniform stride, pad/mint/burn), with
N=8 Payy historical controls.

## What was achieved

| Task | Result | Evidence grade |
|------|--------|----------------|
| D1-00 | Isolated worktree, preservation checks, aligned contract | Administrative |
| D1-01 | All six N=8 T22 slots accounted (all UNKNOWN at 300s/4GiB) | CONCRETE_TIMEOUT |
| D1-02 | Two-family screen + Semaphore-Noir selected with qualifications | Source-confirmed, not built |
| D1-03 | Joint semantics: synth-faulty→VIOLATION, synth-repaired→VERIFIED | CONCRETE_MODEL_REPLAYED |
| D1-04 | Three baselines: Foundry fastest for bugs; monolithic identical | CONCRETE_MODEL_REPLAYED |
| D1-05 | CEGAR: spurious candidates rejected; same verdicts as monolithic | CONCRETE_MODEL_REPLAYED |
| D1-06 | Frozen comparison: CEGAR ties monolithic ±9%; gate not passed | Aggregated evidence |

**Correct implementations delivered:**

1. Joint-semantics pipeline (`src/bindcheck_d1/`) with ACIR extraction,
   propagation, policy encoding, and cvc5 finite-field solving.
2. CEGAR refinement engine (`src/bindcheck_d1/analysis/refinement.py`)
   with abstract solving, concretization, and witness-directed refinement.
3. 16 regression tests covering constraint counts, spurious rejection,
   confirmed/verified iterations, concretization, and preservation.
4. Reproducible experiment scripts with hash-pinned encoders.

## What blocked progress

### Primary blocker: solver scalability

The cvc5 1.4.2 finite-field solver (`--ff-solver=split`) times out at
300 seconds on all six N=8 Payy queries. This is a solver-level limit,
not a method-level problem — it affects all SMT-based approaches equally.
CEGAR operates above the solver and cannot make individual solver calls
faster. The N=8 circuits have RANGE-bit decompositions that dominate
solving time.

### Secondary: no selective refinement on small circuits

On N=9 synthetic circuits (26/35 ACIR constraints), the one-hop
transitive closure from 18 model witnesses covers all constraints. The
refinement adds every constraint in a single step, making iteration 1
equivalent to monolithic solving. The hypothesized advantage (selective
constraint selection) requires circuits where the transitive closure
covers only a fraction of constraints. This was not demonstrated.

### Tertiary: no transfer evidence

The selected independent target (hashcloak Semaphore-Noir) was not built,
proved, or analyzed. The bb CLI is unpinned, artifact/VK correspondence
is unvalidated, and the proving path is untested. Transfer was blocked by
the feasibility gate failure.

## What was learned

1. **Consumer-directed CEGAR is correct.** The concretization check
   reliably rejects over-approximation errors. Both synthetic cases
   demonstrate spurious candidate rejection before confirmation or
   verification.

2. **Foundry testing is a strong baseline for bug finding.** On
   synthetic cases, Foundry finds the violation in <1 ms with ~40 LOC
   of test code. The pipeline's advantage is formal UNSAT verification
   and automatic ACIR extraction, not faster bug finding.

3. **Propagation is neutral on small circuits.** B2 (no propagation)
   produces identical results and times to D1-03 (with propagation).

4. **Manual summaries fail on UNSAT.** B3 (manual summary) finds the
   violation faster (0.96 s vs 11.38 s) but returns UNKNOWN on the
   repaired case (60 s timeout). The pipeline's formal UNSAT is its
   distinguishing result.

5. **The solver is the bottleneck.** No method-level improvement can
   address the fundamental finite-field solver scalability limit. Future
   work on this approach requires either a faster solver, a different
   theory encoding, or circuits that avoid RANGE-heavy decompositions.

6. **The Noir/ACIR batched-EVM population is small.** The D1-02 screen
   found very few licensed, maintained candidates with the required
   circuit structure.

## Stop criteria assessment

| Criterion | Met? | Evidence |
|-----------|------|----------|
| Modular adapter ties at comparable cost | **Yes** | D1-05 CEGAR ±9% of D1-03 monolithic |
| Most correspondence manually asserted | No | ACIR extraction is automatic |
| Fixed controls remain unresolved | **Yes** | All six N=8 queries UNKNOWN |
| Alleged attacks vanish under correct reachability | N/A | Synthetic violation is genuine |
| No independent honest proof path practical | **Partially** | Semaphore-Noir selected but not tested |

Three of five criteria met. The roadmap requires: "Continue beyond this
gate only when the repaired controls, concrete faulty case, baseline
comparison, and transfer evidence support further investment." Two of
four continuation conditions are not met.

## Conditions for reopening

D1 could be reopened if any of the following change:

1. **Solver improvement.** A cvc5 update, alternative finite-field
   solver, or different theory encoding resolves the N=8 timeouts.
   This would enable real-case evaluation and test whether CEGAR
   provides selective refinement on larger circuits.

2. **Larger circuits with sparse constraint reachability.** A circuit
   family where the transitive closure from candidate witnesses covers
   a small fraction of total constraints would test the selective
   refinement hypothesis. This must not be synthetic-benchmark tuning.

3. **Different proof system.** A circuit language or proof system where
   the constraint structure differs fundamentally from Noir/ACIR might
   change the scalability picture.

None of these conditions currently holds. The investigation is closed
at its natural stopping point.

## Evidence locations

```
reports/D1-00.md through D1-06.md     # task reports (immutable)
reports/D1-02-continuation-01.md      # target selection
protocols/d1/                         # frozen protocols
results/raw/D1-00/ through D1-05/    # raw evidence (ignored, regenerable)
metadata/d1/                          # manifests and matrices
src/bindcheck_d1/                     # implementation
tests/d1/                             # regression tests
cases/d1/                             # synthetic fixtures and policies
docs/d1/roadmap.md                    # development plan
docs/d1/brief.md                      # D1 brief
docs/research-contract.md             # research contract
```

## Implications for the broader research

The D1 negative result does not invalidate the broader BindCheck research
question (whether ZK proof guarantees justify consumer effects). It
establishes that consumer-directed CEGAR on finite-field SMT does not
currently provide a measurable advantage over monolithic solving or
Foundry testing on the available cases.

The T15–T20 Payy case study (local reproduction of the message-tail
mechanism with real proofs and committed effects) remains valid evidence.
The T22 nine-case evaluation remains UNKNOWN/incomplete. No general
method claim or held-out evaluation has been established.

Future directions that remain open:

- **T22 completion** if the solver scalability limit is addressed.
- **Alternative analysis methods** (D2+) that do not depend on
  finite-field SMT solving.
- **Broader case studies** with different proof systems or circuit
  structures.
- **The Semaphore-Noir transfer** if the feasibility gate conditions
  are met in a future investigation.

## Assumptions and limitations

- All results are on synthetic N=9 fixtures and historical N=8 controls.
  No real-circuit advantage or disadvantage has been demonstrated.
- Single solver (cvc5 1.4.2 GPL/CoCoA). Different solvers may change
  the scalability picture.
- No consumer contract was exercised (symbolic walk only).
- No Payy consumer analysis was performed (safety constraint from prior
  session).
- AI output is not independent annotation. All generated code, labels,
  and claims require human inspection.

## Handoff

D1 is closed. No immediate next task follows from this investigation.
The recommended next action for the broader project is a human decision
on whether to:

1. Pursue alternative analysis methods (D2+);
2. Investigate solver engineering separately;
3. Focus on the existing T15–T20 evidence for a narrower contribution; or
4. Close the research line.

This decision requires human judgment about research direction and
resource allocation. It is not a task that can be completed by
continuing the current implementation.
