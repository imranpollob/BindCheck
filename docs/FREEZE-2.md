# Analyzer freeze 2 — 2026-11-09

```
BINDCHECK_ZK_CONTENT_SHA256=92789fad12050a3058a21cc5c2326e7d41604ad5ade0f09f72a35789437e6c1a
```

Supersedes freeze 1 (`8ea6d223…`, docs/FREEZE-2026-11-09.md) for every
evaluation from here on: E1 benchmark rerun, the input-withheld circuit
ablation, E2 held-out run, and E3 validation all use this hash.

## Contents

- Lane C coverage rules (reports/coverage/REPORT.md): exact-import
  `Pausable` and lock modifiers, inherited `ERC721Enumerable._mint`
  recipient role, fail-closed verifier placeholders block P1 positives,
  guarded dynamic verifier wrappers for P4.
- P4 key fix (reports/freeze2/REPORT.md): corrected the off-curve BN254 G2
  generator constant; any parsed gamma == delta is
  `VIOLATION / GAMMA_EQUALS_DELTA_SOURCE_KEY`; runtime screening never
  overrides a source violation. Regression controls from real snarkjs 0.7.6
  output in tests/freeze2/.
- Relational module: still excluded.

## Validation

38 tests OK: tests.test_bindcheck_zk_cli, tests.test_bindcheck_zk_controls,
tests.soundness.test_verdict_soundness, tests.soundness.test_followup,
tests.coverage.test_rules, tests.freeze2.test_p4_key. Run with
`PATH=/opt/homebrew/bin:$PATH` and
`BINDCHECK_CIRCOM=$PWD/tools/circom-src/target/release/circom`.

## DEV (unhinted, 56 rows), applicable cells

| Pattern | Applicable | VIOLATION | VERIFIED_WITHIN_SCOPE | UNKNOWN |
| --- | ---: | ---: | ---: | ---: |
| P1 | 17 | 6 | 0 | 11 |
| P2 | 27 | 0 | 0 | 27 |
| P3 | 23 | 6 | 7 | 10 |
| P4 | 46 | 6 | 16 | 24 |
| P5 | 46 | 0 | 4 | 42 |
| All | 159 | 18 | 27 | 114 |

Decided 45/159 (freeze 1: 39/159). Two freeze-1 certifications were unsafe
(DEV-F09, DEV-F14 P4: gamma = delta) and are now violations. Raw run:
`bindcheck-zk-coverage/results/raw/coverage/after-20261109T165844Z-58315`.

## Rules (unchanged from freeze 1)

- Any change under `bindcheck_zk/` needs a new freeze declaration.
- A change motivated by a gate, EVAL, benchmark or adversarial outcome marks
  the affected cases EXPOSED and they leave the headline measurement.
- The `bindcheck-zk-frozen-<8hex>` tag is created at run time by the lane that
  runs the evaluation (its message carries the corpus and expectation hashes).
- Framing 2 stands: benchmark + measurement study; no comparative
  "detects better" claim.
