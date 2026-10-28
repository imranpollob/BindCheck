# WT-S01 — K2 local-root admission removed (WarpToad consumer, M-SRC reuse)

- Family: WarpToad consumer (solc 0.8.29). Operator: remove admission guard.
  Injected mutation based on documented reliance (`main.nr:56-58`: the
  producer performs no root membership on the same-root branch). No claim
  any WarpToad release lacked K2.
- Change: `require(isValidLocalRoot(_localRoot), ...)` removed; producer,
  VK, and verifier unchanged.
- Ground truth: O2/SRC-EVM. Expected effect: a mint against an
  attacker-built tree (root never admitted) succeeds; the identical input
  reverts at K2 on the pinned consumer.
- Reachability: D1P-19 real-proof polarity (M-SRC mint + pinned K2
  rejection) is the existence proof; reused, not re-run.
- Compile check here is solc with vendored deps (see package README).
