# D1-06 Protocol: Frozen Feasibility Comparison

**Version:** 1  
**Date:** 2026-10-23  
**Prerequisite:** D1-05 (consumer-directed refinement)

## Objective

Test D1-05 CEGAR against D1-04 baselines. Include N=8 controls and meaningful
legitimate behaviors. Report full-query outcomes. Demonstrate a useful
checking/extraction advantage or conclude that the current method does not
support the contribution.

## Comparison scope

### Synthetic N=9 cases (existing data)

All timing and verdict data from D1-03 (monolithic), D1-04 (B1/B2/B3), and
D1-05 (CEGAR) on synth-faulty and synth-repaired. No new solver runs needed;
the frozen data is in `results/raw/D1-03/`, `results/raw/D1-04/`, and
`results/raw/D1-05/`.

### N=8 Payy controls (existing data)

D1-01 established that all six N=8 primary queries (3 check-added + 3
running-flag, each 300 s / 4 GiB) timed out. This is the authoritative result
for N=8 controls. No new N=8 runs are attempted; the solver scalability limit
is the blocker, not the analysis method.

### Meaningful legitimate behaviors

synth-repaired already covers legitimate behavior: all authorized effects are
properly matched, VERIFIED_WITHIN_SCOPE with non-vacuity SAT_REPLAYED. Both
B1 Foundry tests and the full encoder confirm no violation.

## Comparison dimensions

1. **Verdict correctness**: same verdicts across methods?
2. **Auth solve time**: D1-03 monolithic vs D1-05 CEGAR vs B1/B2/B3
3. **CEGAR overhead**: concretization + multi-iteration cost
4. **Constraint selectivity**: did CEGAR use fewer constraints?
5. **Scalability**: N=8 feasibility assessment
6. **Analyst effort**: LOC, manual facts, setup time

## Feasibility criteria (from roadmap §6)

Continue only when:
- Repaired controls produce correct verdicts ✓ (synthetic N=9)
- Concrete faulty case has replayed violation ✓ (synthetic N=9)
- Baseline comparison shows advantage ← to assess
- Transfer evidence supports investment ← not available

Stop if:
- Modular adapter ties at comparable cost ← to assess
- Fixed controls remain unresolved ← N=8 all UNKNOWN
- No independent honest proof/consumer path is practical ← to assess

## Deliverable

One comparison report with frozen tables, N=8 assessment, and an explicit
feasibility conclusion. No new solver runs unless a specific gap is identified.
