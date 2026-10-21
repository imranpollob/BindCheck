# T22-v3 frozen primary protocol

Written on 20 October 2026 before executing the new analyzer, including its
synthetic regressions. This is a local freeze, not independent preregistration.
The freeze manifest hashes this file, all four v3 scripts and the unchanged
primary specifications before any v3 output is inspected.

## Scope and completion criteria

Implement R1–R6 from T22 Section 3.2 in separate files; preserve v2 and its
evidence. Run all nine N=8 development cases with their unchanged expectations.
Record every verdict, query cause, tool status and SAT target audit. Do not run
the independent Aztec transfer case. Completing this rerun does not complete
T22's transfer, sensitivity or equal-information evaluation.

## Encoding and assumptions

- R1: substitute implied constants in the goal as well as ACIR assertions.
- R2: recompute target components after substitution. SAT assumes all omitted
  components, including those split off by substitution, are satisfiable.
- R3: exact all-inactive contradictions refute only that probe premise, then
  issue nonvacuity, prefix and tail queries. They do not exclude L=0 generally.
- R4: probe slots 0 through 7, stopping only at a supported, audited SAT.
  Other slots' UNSAT/UNKNOWN results cannot hide an unchecked later slot.
- R5: cvc5 1.4.2 with CoCoA, `--ff-solver=split`, explicitly selected.
- R6: black-box outputs count as occurrences during dangling-definition
  pruning. SAT probes conservatively warn on any black-box output in the
  original target/activation cone, including outputs removed by substitution.

The semantic specifications, walk rules, source transformations, bounds and
expectations are identical to v2. Recursive-proof feasibility is assumed, not
established. No proofs or consumer transactions are generated in this task.
Results remain conditional producer-side constraint results.

## Resources, scheduling and gate

Use the existing pinned Payy revisions and Noir beta.14. Sequential cases,
sequential queries, 4 GiB virtual-memory limit inherited by each child, 60 s
per probe slot and 300 s per general query. All general queries are issued
even if the first is unresolved; no retry or changed solver mode in the
primary run. Record solver stdout, stderr, exit status and timeout separately.
The wall time of a case can exceed 900 seconds.

Run the seven synthetic soundness regressions first with real cvc5. They do
not read Payy or independent cases. If they fail, preserve the failed frozen
attempt and do not launch the primary run without a new versioned freeze.
If they pass, run `T22_RUN_ID=33_v3_primary TLIMIT=300 bash scripts/t22_v3.sh`.
Exit 1 for mismatches is an evaluation outcome, not a run failure.

Afterward, re-check every SAT probe from saved SMT/solver records, requiring
no substituted-goal witness in `implied`, the target component to have been
encoded, and a nonzero returned message value. This is a mechanical target
audit, not proof of satisfiability of omitted constraints. Preserve v2 and
diagnosis hashes before and after. Compare the compiled ACIR/ABI/source of
all nine cases against v2. No tuning after results within this version.

## Frozen expectations (in-sample, not independent labels)

| Case | Expected |
| --- | --- |
| A agg_agg (earlier) | VIOLATION |
| B agg_agg (check added) | VERIFIED_WITHIN_SCOPE |
| agg_utxo (A=B) | VERIFIED_WITHIN_SCOPE |
| m1 B: guard > instead of >= | VIOLATION |
| m2 B: loop skips last slot | VIOLATION |
| m3 B: helper call deleted | VIOLATION |
| m4 B: different idiom (flag) | VERIFIED_WITHIN_SCOPE |
| m5 utxo: tail loop deleted | VIOLATION |
| m6 utxo: else-branch idiom | VERIFIED_WITHIN_SCOPE |

UNKNOWN remains unresolved. A negative control changing from a false positive
to UNKNOWN removes that observed false positive but does not verify the control.
