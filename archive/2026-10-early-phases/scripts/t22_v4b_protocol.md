# T22-v4b Boolean-rank follow-up, check-added agg_agg only

The v4 assertion-prefix diagnostic was frozen and run first. It showed that
the non-vacuity goal alone exceeded short solver limits. This follow-up is a
new encoding experiment, frozen before its output is inspected; it does not
change the v3 analyzer, v3 results, protocol policy, N=8 artifact, or
specification.

Build the same ACIR cone with the same v3 parser, pruning, and finite-field
encoder. Replace only the specification-side emitted-word count and indexed
lookup: maintain a Boolean one-hot count after each emitted word (with an
overflow bucket), and use the count before that word as its prefix position.
The original count is a sum of 0/1 field terms with at most 16 terms, so the
one-hot Boolean count is exact: no field wrap can occur. The same `walk`
emission predicates, activation predicates, message words and ACIR constraints
remain. Test non-vacuity, prefix, and tail sequentially, each with 300 seconds
and 4 GiB. Save SMT, solver records and model values. A SAT needs a model
replay of the specification goal and retains v3's omitted-component
assumption. An UNSAT result may support a bounded conclusion only if the
Boolean rank rewrite and selected ACIR constraints are reviewed.

Do not run independent transfer. If any query remains unresolved, the full
check-added case stays `UNKNOWN`.
