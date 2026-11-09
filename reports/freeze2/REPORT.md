# Freeze 2 — DEV results (orchestrator addendum to Lane C)

**Analyzer:** `BINDCHECK_ZK_CONTENT_SHA256=92789fad12050a3058a21cc5c2326e7d41604ad5ade0f09f72a35789437e6c1a`
(commit `3265a0e2` on `zk-coverage`). Lane C's candidate `a9ec7cb9…` is an
intermediate and is not used for any evaluation.

**What changed after Lane C.** The paper lane found that `BN254_G2` in
`bindcheck_zk/p4.py` dropped the digit group `3681` in y.c1, so the point was
off the curve and never matched real snarkjs output. The VERIFIED rule also
rejected only gamma = delta = that constant. Fix: corrected constant (on-curve
test plus match against a snarkjs 0.7.6 export), and any fully parsed
gamma == delta is now `VIOLATION / GAMMA_EQUALS_DELTA_SOURCE_KEY`
(A = alpha, B = beta, C = -vk_x satisfies the pairing check for every public
input). A runtime screening result no longer overrides a source violation.
Controls: `tests/freeze2/test_p4_key.py`; `P4-02` now expects the violation.
Motivation is a DEV source reading; no gate, EVAL or held-out outcome was used.

**Tests.** `tests.test_bindcheck_zk_cli`, `tests.test_bindcheck_zk_controls`,
`tests.soundness.test_verdict_soundness`, `tests.soundness.test_followup`,
`tests.coverage.test_rules`, `tests.freeze2.test_p4_key`: 38 tests OK
(Python 3.15, `BINDCHECK_CIRCOM` = Circom 2.2.3).

**Run.** Unhinted, same command as Lane C:
`results/raw/coverage/after-20261109T165844Z-58315` (manifest SHA-256 in
[dev-summary.json](dev-summary.json)); 56 rows, 46 with triples, 0 crashes,
45/76 builds OK, 1 timeout (same as freeze 1). Lane C's two extra timeouts
(DEV-F09, DEV-F45) did not recur.

## Freeze 1 → freeze 2, applicable cells only

| Pattern | Applicable | VIOLATION | VERIFIED_WITHIN_SCOPE | UNKNOWN | Decided |
| --- | ---: | ---: | ---: | ---: | ---: |
| P1 | 17 | 5 → 6 | 0 → 0 | 12 → 11 | 5 → 6 |
| P2 | 27 | 0 → 0 | 0 → 0 | 27 → 27 | 0 → 0 |
| P3 | 23 | 6 → 6 | 7 → 7 | 10 → 10 | 13 → 13 |
| P4 | 46 | 0 → 6 | 17 → 16 | 29 → 24 | 17 → 22 |
| P5 | 46 | 0 → 0 | 4 → 4 | 42 → 42 | 4 → 4 |
| **All** | **159** | **11 → 18** | **28 → 27** | **120 → 114** | **39 → 45** |

## Changed verdicts (8) — [changed-verdicts.csv](changed-verdicts.csv)

| Row | Pattern | Freeze 1 → freeze 2 | Source |
| --- | --- | --- | --- |
| DEV-F08 zkp2p/zk-p2p | P4 | UNKNOWN → VIOLATION | 4 verifiers incl. `contracts-ramp/contracts/verifiers/paylah_send_verifier.sol`: gamma = delta = generator |
| DEV-F09 zk-poll | P4 | **VERIFIED → VIOLATION** | `contracts/verifiers/ECDSASemaphoreVerifier{2,16}.sol`: `vk.gamma2` = `vk.delta2` = generator |
| DEV-F10 0xFable | P4 | UNKNOWN → VIOLATION | `Draw/DrawHand/PlayVerifier.sol`: gamma = delta = generator |
| DEV-F14 meridian-link | P4 | **VERIFIED → VIOLATION** | `evm-bridge/contracts/SolDepositVerifier.sol`: gamma = delta = generator |
| DEV-F29 VEILPAY | P4 | UNKNOWN → VERIFIED | Lane C wrapper rule (see ../coverage/REPORT.md) |
| DEV-F34 zk_voting | P4 | UNKNOWN → VIOLATION | `contracts/Verifier.sol`: gamma = delta = generator |
| DEV-F44 proof-of-twitter | P1 | UNKNOWN → VIOLATION | Lane C inherited `_mint` rule |
| DEV-F48 qwer | P4 | UNKNOWN → VIOLATION | `privatecrypmix/.../Verifier.sol`: `verifyingKey.gamma` = `.delta` = generator |

The orchestrator checked all six P4 violations by reading the pinned source:
every flagged file has all four gamma and delta coordinates equal. The two
bold rows were unsafe certifications under freeze 1 and are corrected here.
These are source-key findings (E1); deployment correspondence and executed
forged proofs are not established by this report.
