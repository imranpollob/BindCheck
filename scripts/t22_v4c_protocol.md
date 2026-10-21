# T22-v4c constructive branch follow-up

Written after the v4b full non-vacuity timeout and before this branch is run.
It implements the constructive branch already described in the initial v4
protocol. It is a separate follow-up so the frozen v4 and v4b files and their
results remain unchanged.

Use the pinned check-added N=8 ACIR, ABI and unchanged specification. Fix
stream 0 active with words `[2,0,0,0,0,0,0,0]` and stream 1 inactive with the
same recursively selected public words. This pattern emits four words under
the unchanged walk rule, so a SAT model of all surviving selected ACIR
constraints proves conditional non-vacuity. Fixing these values restricts
search; it does not add a protocol rule. Exact v3 polynomial propagation and
substitution may remove constraints but must retain all remaining selected
components. Use 4 GiB and 300 seconds, save SMT/model/solver record, and
report any timeout, contradiction or SAT with the omitted-component and
recursive-proof assumptions. The case remains `UNKNOWN` unless prefix and
tail are also decided soundly.
