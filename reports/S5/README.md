# S5 reserve manifest (pre-run, not executed)

- `reserve-manifest.csv`: 1,105 units = in-scope EVAL rows of `dataset/source-corpus-v2.csv`, minus the 278 freeze-2 spent (repository, commit) pairs in `reports/heldout/selected-families.csv`, minus `warptoad/warp-toad`. Unit key: (repository, commit). 1,105 distinct pairs; no overlap with the spent set (asserted).
- SHA-256 of the CSV: `b1752eede4ccabaf5dea45d827fbdd0c388346349a51129b2ace125322374278`.
- Audited/deployed stratum (`maturity` in `audited-production`, `deployed-address-in-docs`): **390** (148 + 242). Correction: an earlier figure of 535 counted spent families.
- Hold-out guard (`guard-check.txt`): all 1,105 repositories return FORBIDDEN, as expected for reserved v3 families. The guard is the control that prevents opening them outside the authorized run.
- 3 units have no recorded circuit path; they will be reported as unsupported.
- Not executed: no clone, prebuild, analyzer or oracle output exists for these units.
