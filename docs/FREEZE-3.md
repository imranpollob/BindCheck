# Analyzer freeze 3 — 2026-11-18

```text
BINDCHECK_ZK_CONTENT_SHA256=753c6e2a0f3f75255eb2fdc354402f3ef7aac1541206b0794a9d09cd7d485315
```

This declaration supersedes [freeze 2](FREEZE-2.md) (`92789fad12050a3058a21cc5c2326e7d41604ad5ade0f09f72a35789437e6c1a`) for prospective held-out v3 analyzer measurements. Freeze-2 measurements keep their original hash. S0 verified the analyzer at commit `9d340eb362090415b9c68b7eeab720a1bc3a0a74`. The reviewer creates and pushes the `freeze-3` tag after reviewing S0. [Revision 4](research-contract.md) and [S0 handoff](../reports/S0/REPORT.md)

## Contents

- S2a recovers call-specific public vectors, distinguishes proof arrays and caller-funded or state-derived values, and reports configured semantic exclusions in coverage. Circom arrays and supported Noir interfaces have flattened public orders. Honk/UltraHonk arity accounts for explicit pairing-point and aggregation reservations, including supported import-split layouts. S2b Honk canonicality is deferred. [S2a](../reports/S2a/REPORT.md)
- S2a2 narrows P5 circuit/verifier matching, proof-only argument forwarding and compiled-artifact reuse. Six residual development warnings became `UNKNOWN`. Two count-mismatch controls retained `VIOLATION` on their retained inputs. [S2a2](../reports/S2a2/REPORT.md)
- P1-EXTENT checks binding beyond discharge in the supported fixed-row settlement fragment. The AZ1 faulty/fixed development controls distinguish an unchecked shorter prefix from an enforced neutral tail at E1. The verified-source V3 assembly path remains `UNKNOWN`. [S2c](../reports/S2c/REPORT.md)
- F1 addresses receiver/implementation mismatch, inherited guard forwarding, incomplete P5 circuit order and gnark loop-position coverage. P5 resolves verifier arity per recovered vector. XR identified the failures and XR2 closed the four original analyzer findings, XR-03 through XR-06. XR2 found no new path to a false `VERIFIED_WITHIN_SCOPE` in the changes it reviewed. [XR](../reports/XR/FINDINGS.md), [F1](../reports/F1/REPORT.md) and [XR2](../reports/XR2/REVERIFY.md)
- The relational module remains outside this freeze. The separate E4 execution oracle has its own F3/XR3 gate. The reviewer accepted analyzer-only freeze preparation while the oracle findings remain open. [Reviewer decision](orchestration/DECISIONS.md)

## Validation and toolchain pins

From the worktree root, with `BC=/home/pollmix/Coding/bc`:

```sh
python3 -m bindcheck_zk.freeze
BINDCHECK_CIRCOM="$BC/BindCheck/tools/circom-2.1.9/target/release/circom" \
  python3 -m unittest tests.test_bindcheck_zk_cli tests.test_bindcheck_zk_controls \
  tests.soundness.test_verdict_soundness tests.soundness.test_followup \
  tests.coverage.test_rules tests.freeze2.test_p4_key tests.s2a.test_precision_fixes \
  tests.s2a2.test_residual_p5 tests.s2c.test_extent tests.f1.test_analyzer_soundness -v
```

The hash command exited 0. All **77 analyzer tests** passed in 26.873 seconds, exit 0. Logs and SHA-256 digests are recorded in the [S0 handoff](../reports/S0/REPORT.md).

| Component | S0 validation environment |
| --- | --- |
| Host and runtime | Linux x86_64, Python 3.12.12, Git 2.43.0 |
| Circom | 2.1.9, source revision `2eaaa6dface934356972b34cab64b25d382e59de` per T0. Local executable SHA-256 `1bacd5583e2cc79dc1e2deaefc9c7438f21957968651c5f93dc71073c58435e3` |
| Offline include library | circomlib 2.0.5, 144 files, tree SHA-256 `d359bab216fc262b406f468d87774ec1b6661e4438b38851fcd6a0a2e1e8a57a`. S0 verified the installed tree with the analyzer's lock check. |
| npm lock | snarkjs 0.7.6, circomlibjs 0.1.7. Root lockfile SHA-256 `63679f1efedd00cc480f9b78e4a04009341913610af82c9b0cf205ebd4740006`. Additional generator and proving tool versions are recorded separately in T0. |

Pin sources are the [vendor lock](../bindcheck_zk/vendor-lock.json), [npm lock](../package-lock.json) and [Linux toolchain record](../reports/T0/REPORT.md).

## DEV — development data, not held-out

Each row below covers all 56 original DEV rows. Freeze 2's table used applicable cells only. The counts below are F1's recorded candidate results at the hash above. [F1 DEV measurements](../reports/F1/REPORT.md#original-56-dev-rows)

| Pattern | VIOLATION | VERIFIED_WITHIN_SCOPE | UNKNOWN |
| --- | ---: | ---: | ---: |
| P1 | 6 | 0 | 50 |
| P2 | 0 | 0 | 56 |
| P3 | 6 | 7 | 43 |
| P4 | 6 | 15 | 35 |
| P5 | 1 | 3 | 52 |
| P1-EXTENT | 0 | 0 | 56 |

F1 observed 372 triples across 46 rows, 37 successful circuit builds or loads, and 39 build failures including three build timeouts. All 56 analyzer runs completed. No row-level verdict or applicability changed in F1, though two detailed P4 results in DEV-F20 fell to `UNKNOWN` after the verifier correspondence check. S0 reran the tests and carried forward these DEV counts from F1. [F1 results](../reports/F1/REPORT.md)

## Evaluation rules

Reserve the 1,106 unspent families for the one-shot v3 run. Record the preregistered population, attempted families, coverage and failures. Keep the analyzer fixed and exclude any subsequently exposed cases from claims of held-out transfer. Any change under `bindcheck_zk/` requires a new freeze declaration. Oracle E4 confirmations remain gated on F3 and XR3. The benchmark and measurement framing of freeze 2 still applies. [Research contract](research-contract.md) and [S0 mandate](orchestration/S0-contract-rev4-freeze3.md)
