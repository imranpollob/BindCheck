# WT-S05 — root/anchor checks swapped (WarpToad consumer)

- Family: WarpToad consumer. Operator: swap root checks.
- Change: `_gigaRoot` is checked against `localRootHistory` and
  `_localRoot` against `gigaRootHistory`. Both requires still present.
- Ground truth: admission sets crossed. Expected effect: honest mints
  revert (roots live in the opposite sets) while an attacker who gets a
  value admitted into the wrong set passes — availability break plus
  targeted bypass shape.
- Reachability (cheap): solc compile + diff audit. Honest-execution
  break is predicted, not executed here.
