# T22-v4 check-added agg_agg general-query feasibility protocol

Written before running the v4 experiments on 20 October 2026. This is a
development-case engineering experiment, not an independent evaluation or a
change to the research contract, semantic specification, or v3 results.

## Objective

Try to obtain a supported non-vacuity SAT and prefix/tail UNSAT for the existing
N=8 check-added `agg_agg` ACIR within 300 seconds per query. If that fails,
preserve a smaller, source-linked SMT instance reproducing a general-query
resource failure under the same cvc5 mode, 4 GiB virtual-memory cap, and
300-second limit. Do not run the independent transfer case.

## Reduction and evidence rules

Use the byte-preserved v3 `nonvacuous.smt2` as input. For the blocker search,
retain its final non-vacuity assertion and selected original constraint
assertions without editing any retained assertion. Remove unused SMT
definitions and declarations by transitive dependency. A reduced instance is
an **easier subproblem**, not an equivalent verification query: UNSAT on it
would be sound for the original; SAT or timeout only diagnoses solver work and
does not decide the original query. Record the exact retained original
assertion indices, hashes, solver command, stdout/stderr, exit status, peak
RSS, elapsed time and timeout flag. Search with short limits, then confirm any
candidate at 300 seconds. A short-limit timeout alone is not a 300-second
blocker. Preserve the original v3 query and records unchanged.

Also attempt a constructive non-vacuity query by fixing a concrete stream
pattern (first inner stream active with kind 2 and zero following words;
second stream inactive). Substitute those fixed values exactly into the ACIR
cone, retaining all surviving constraints in the target component. SAT would
imply SAT for the unspecialized cone only conditional on satisfiability of
omitted and split-off components, as in v3. It is not a proof witness or a
committed consumer effect. Any fixed values are a search restriction and are
not added to the specification.

Classification remains `VIOLATION`, `VERIFIED_WITHIN_SCOPE`, or `UNKNOWN`.
The v4 task may complete with an `UNKNOWN` and a minimized blocker. Preserve
all raw outputs under ignored `results/raw/T22/34_v4_general/` and summarize
them in a new immutable `reports/T22-v4.md`. Update README and the living
checkpoint in the same turn.
