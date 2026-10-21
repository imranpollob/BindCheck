# T22-v5 compact-walk general-query protocol

Frozen before the 300-second primary run on 20 October 2026. The bounded
question is whether a compact encoding of the **unchanged** N=8 semantic walk
lets cvc5 decide non-vacuity, prefix and tail on the existing check-added and
running-flag `agg_agg` ACIR, each under 300 seconds and 4 GiB. This is an
in-sample engineering task; independent transfer remains deferred.

The source and ABI are the v3 saved artifacts for
`b_agg_agg_check_added_` and `m4_b_different_idiom_flag_`. The semantic spec
is `scripts/t22_specs/payy_agg_agg.json`. The source revision and compiler
are those pinned in T22-v3. No changes are made to those artifacts, the spec,
the research contract or previous verdicts.

The compact encoding uses the same record-kind map (2 -> 4, 3/4 -> 5).
For one eight-word stream, only word 0 and a possible next record start at
position 4 or 5 can affect emitted positions. Thus its emitted length is
0, 4, 5 or 8. Exhaustively check all 4^8 vectors over the equivalence
classes {other, 2, 3, 4} against the v3 walk transition. This validates the
specification rewrite, **not** an ACIR circuit summary. The solver queries
retain the v3 selected ACIR cone and constraints unchanged. Record solver
stdout/stderr, exit status, elapsed time, query hash and 4 GiB cap for all
six queries. Treat timeout/allocation failure as `UNKNOWN`.

If a general query remains undecided, reduce it to the smallest useful
ACIR-bearing blocker: retain an original ACIR assertion connected to the
goal and byte-identical SMT lines, with dependency closure. Confirm the
candidate at 300 seconds/4 GiB, preserve the query and provenance audit,
and report that the milestone is unmet. A reduced timeout is a solver
diagnosis only, not a verdict. Preserve new raw output in ignored
`results/raw/T22/35_v5_compact/`; summarize in a new T22-v5 report and
update README and project status after the bounded task.
