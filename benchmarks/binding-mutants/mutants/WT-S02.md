# WT-S02 — K1 giga-root admission removed (WarpToad consumer)

- Family: WarpToad consumer. Operator: remove admission guard.
- Change: `require(isValidGigaRoot(_gigaRoot), ...)` removed.
- Ground truth: giga-root admission unbound. Expected effect: mint with
  an arbitrary `_gigaRoot` passes the consumer (proof still must verify
  against that root's witnesses circuit-side — the break is consumer-side
  admission, joint verdict needs a matching circuit witness).
- Reachability (cheap): solc compile + structural diff audit (guard gone,
  effects intact). No consumer execution run in this benchmark.
