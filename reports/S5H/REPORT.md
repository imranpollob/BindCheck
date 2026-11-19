# S5H — Reserve harness entry point

**Status:** DONE for offline harness code and tests, 2026-11-19. The held-out reserve run was **not executed**. No reserve repository was opened, acquired, fetched, cloned, prebuilt, or analyzed. No authorization record was created.

## Objective and changes

Add a separate entry point for the preregistered 1,105 (repository, commit) reserve units without changing the historical `select_families` or `check_eval_gate` route.

| File | Change |
| --- | --- |
| `eval/reserve.py:27` | Pin the S5 manifest, freeze-3 analyzer, and Linux Circom digests. |
| `eval/reserve.py:37` | Check manifest hash, exactly 1,105 rows, distinct unit IDs and pairs, spent-pair exclusion, WarpToad exclusion, and the 390-unit reporting stratum. Emit the stratum count. |
| `eval/reserve.py:67` | Require `freeze-3` at HEAD, the exact `python3 -m bindcheck_zk.freeze` content hash, and an author record with matching manifest hash and nonblank approval fields. |
| `eval/reserve.py:100` and `scripts/check_holdout.py:51` | Allow a manifest repository only through the reserve entry point after the gate. The ordinary guard CLI and its default refusal are unchanged. The permit rechecks the mutable gate and manifest at use time. |
| `eval/reserve.py:121` | Persist one status for every unit and check the final count and unique IDs before writing `results/raw/S5/funnel.json`. Resume checks repository and commit. |
| `eval/reserve.py:162` | Reuse pinned acquisition, vendor setup, Circom prebuild, analyzer and comparison arms on the same checkout. Classify acquisition failure, build failure, timeout, unsupported/incomplete analyzer, or analyzable triple. Clean up the checkout. |
| `eval/reserve.py:199` | Require explicit, digest-pinned Linux Circom and lock any resumed output to the same gate and toolchain. All reserve output is under `results/raw/S5/`. |
| `eval/prebuild_heldout.py:46` | Extract the existing Circom build routine for use on an already acquired checkout. Add `--sample`; the historical sample remains the default. Direct selection of the reserve through this historical prebuild command is refused, with a pointer to the gated entry point. `--circom` remains required and has no macOS default. |
| `tests/s5h/test_reserve.py:1` | Offline manifest, gate, guard, CLI, and full-funnel tests. |
| `tests/s5h/revert_proof.py:1` | In-memory guard-removal probes. No checkout source is edited by the probes. |
| `docs/project-status.md:158` | Mark S5H code complete and the S5 run waiting; append a dated checkpoint. |

The authorization record is deliberately absent. A future run must be invoked with `python3 eval/reserve.py --circom /home/pollmix/Coding/bc/BindCheck/tools/circom-2.1.9/target/release/circom` only after the author provides the record and the freeze-3 HEAD gate is satisfied. This is a command specification, not an executed command.

## Commands and observed results

- Starting revision: `ad82822809b45b6761cc7ba62c9e7f93a2e1ed00`, branch `sprint/S5H`; starting working tree clean. Python 3.12.12; Git 2.43.0.
- `sha256sum reports/S5/reserve-manifest.csv` exited 0 and matched `b1752eede4ccabaf5dea45d827fbdd0c388346349a51129b2ace125322374278`.
- `sha256sum /home/pollmix/Coding/bc/BindCheck/tools/circom-2.1.9/target/release/circom` exited 0 and matched `1bacd5583e2cc79dc1e2deaefc9c7438f21957968651c5f93dc71073c58435e3`.
- `python3 -m unittest discover -s tests/s5h -v` exited 0: **18 tests passed**. These use local CSV copies, mocked git/freeze results, a fake runner, and temporary output only. The manifest count test observed 1,105 units and a 390-unit stratum. A synthetic stage test checked all five funnel statuses without creating a checkout.
- `python3 tests/s5h/revert_proof.py` exited 0: **15/15 in-memory removal probes detected** by the corresponding refusal or no-drop test. The probes cover manifest hash, row count, spent pair, WarpToad, duplicate pair, 390 count, tag, analyzer hash, missing/incorrect/blank authorization, default guard, reserve permit, funnel completeness, and explicit Circom CLI.
- The F1 regression command from `reports/F1/REPORT.md` first exited 1: 77 tests ran, with one Circom control failing and one test skipped because `BINDCHECK_CIRCOM` was unset (`CIRCOM_NOT_AVAILABLE`). The same command with `BINDCHECK_CIRCOM=/home/pollmix/Coding/bc/BindCheck/tools/circom-2.1.9/target/release/circom` exited 0: **77 tests passed** in 26.728 s. It ran the ten modules `tests.test_bindcheck_zk_cli`, `tests.test_bindcheck_zk_controls`, `tests.soundness.test_verdict_soundness`, `tests.soundness.test_followup`, `tests.coverage.test_rules`, `tests.freeze2.test_p4_key`, `tests.s2a.test_precision_fixes`, `tests.s2a2.test_residual_p5`, `tests.s2c.test_extent`, and `tests.f1.test_analyzer_soundness`.
- `git diff --check` exited 0.

The tests' output is summarized here; no result under `results/raw/S5/` was produced. The test runner's temporary funnel was deleted with its temporary directory. There was no evaluation execution or security verdict.

## Revert proof

`tests/s5h/revert_proof.py` replaces one check at a time in memory, runs the corresponding test, and restores the implementation. Each mutated version makes its test fail. The result was 15 `DETECTED`, zero `MISSED`, exit 0. The first probe run exposed a test-harness mistake: it patched the guard module but not the function alias imported by `eval.reserve`; that run reported 14 detected and one missed, exit 1. The probe was corrected to patch the imported alias; the final 15/15 result is the controlling one. No reserve source was touched.

## Assumptions and limitations

- This is harness code only. The peeled `freeze-3` tag does not equal this worktree's HEAD (`d8fe1e15a91fcc344e5d2bba8c769a1dcaaf8775` versus `ad82822809b45b6761cc7ba62c9e7f93a2e1ed00`), and `reports/S5/AUTHORIZATION.json` is absent. The gate therefore cannot authorize a run here. The author must decide how to place this harness at a HEAD satisfying the frozen tag without changing the frozen analyzer content.
- `reports/S5/PREREG.md` says author approval is pending, while `docs/orchestration/S5-PROTOCOL-DRAFT.md` says the protocol was approved on 2026-11-19. The entry point follows the task brief's explicit `AUTHORIZATION.json` gate and does not infer approval from either sentence.
- The protocol draft mentions a 535-unit audited/deployed corpus count; the later pinned S5 manifest and preregistration state **390** after spent-family exclusions. The harness enforces 390 and does not edit either historical source.
- `eval/prebuild_heldout.py` already required `--circom` and had no macOS default at this starting revision. S5H added `--sample` and the reusable build routine. Reserve selection remains confined to `eval/reserve.py` so the historical prebuild command cannot bypass the reserve gate.
- An unexpected per-unit Python exception is recorded as funnel `UNSUPPORTED` with `HARNESS_INTERNAL_ERROR` in `reason` and `detail`, keeping the unit visible. This is a harness failure reason, not an application-support determination or a security verdict. A future reviewer should decide whether the preregistered funnel needs a separate harness-failure column before execution.
- The existing tool runner gives the comparison arms the same checkout. This task does not implement author adjudication, oracle E4 replay, or a contract-plus-verifier result table. Those are later, separately gated research steps; no end-to-end claim follows from this code.

## Next task

Author review of the gate and funnel semantics before any reserve execution. Completion criterion: reconcile the HEAD/tag placement and internal harness-failure reporting in a dated protocol decision, and supply a signed-off `AUTHORIZATION.json` with the pinned manifest hash, `approved_by`, and `approved_on`. Only then may a separate lane run the 1,105 units once and verify that the final funnel contains exactly 1,105 distinct unit results and 390 stratum results.

## Reviewer changes (orchestrator, 2026-11-19)

1. **Gate tag.** The original gate required `freeze-3` to equal HEAD, which cannot hold: `main` has oracle (F3–F5) and harness commits after freeze 3. The gate now requires (a) an annotated run tag `s5-reserve-run` at HEAD, and (b) `git diff --quiet freeze-3 HEAD -- bindcheck_zk freeze.sh`, i.e. analyzer files byte-identical to freeze 3, plus the existing content-hash check. New tests: analyzer files differing from freeze 3 refused; a run commit after freeze 3 accepted when analyzer files are unchanged.
2. **Harness failures are not "unsupported".** A runner exception is now `HARNESS_ERROR` (new funnel status), not `UNSUPPORTED`, so harness failures cannot inflate the application-support count. New test and revert probe.

Result: `python3 -m unittest discover -s tests/s5h` 21 passed; `tests/s5h/revert_proof.py` 17/17 DETECTED; the F1 analyzer suite passes with `BINDCHECK_CIRCOM` set; analyzer hash unchanged (`753c6e2a…`). The PREREG funnel list gains `HARNESS_ERROR` by amendment at approval time.
