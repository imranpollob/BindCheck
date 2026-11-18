# F1 — Analyzer soundness fixes from cross-model review

Status: DONE

Verdict/outcome: XR-03 through XR-06 fail closed on the originally reproduced controls. The XR-09 P5 control verifies both matched public-input vectors. New application-level security conclusions remain `UNKNOWN`.

AI disclosure: OpenAI Codex, GPT-6 family, implemented and tested this lane. The exact serving variant was unavailable. The author has yet to review the implementation and claims.

## What was done

- **XR-03.** P1 and the P4 result attached to a consumer triple return `UNKNOWN / VERIFIER_CALL_CORRESPONDENCE_UNRESOLVED` for a verifier that conflicts with the declared receiver type. This uses the existing P3/P5 source-correspondence classification. Standalone runtime diagnostics retain their own provenance.
- **XR-04.** P4 inherits a verified guard only for a single, directly imported base and a single wrapper entry point that forwards its fixed public vector unchanged to the unique base method. That method must check every vector word on entry. The overridden and conditional-bypass controls return `UNKNOWN / INHERITED_VERIFIER_GUARD_UNRESOLVED`. The revised S2a positive control derives the verdict from parsed source.
- **XR-05.** P5 requires a complete flattened circuit order and a known public count before verification. A length-guarded vector with an unsupported circuit interface returns `UNKNOWN / CIRCUIT_INTERFACE_INCOMPLETE`. The separate verifier/consumer count-mismatch check still runs when both counts are established.
- **XR-06.** The gnark Yul recognizer checks the loop as one shape. It requires zero initialization, the same induction variable throughout, an exclusive bound at the public-input length, a unit induction step, and exactly one 32-byte pointer advance after each check. Starting at one and advancing the pointer twice both lose full-position coverage.
- **XR-09 (P5).** Distinct public vectors have independent verifier-arity ambiguity checks. The tightened S2a control checks the exact result and the recovered two- and three-element vectors. Competing arities attached to the same recovered vector still produce `UNKNOWN`.

Changes are in [analyzer.py](../../bindcheck_zk/analyzer.py), [p4.py](../../bindcheck_zk/p4.py), [F1 tests](../../tests/f1/test_analyzer_soundness.py), the two requested [S2a test updates](../../tests/s2a/test_precision_fixes.py), and the [living project checkpoint](../../docs/project-status.md).

## Evidence

- Branch `sprint/F1`, clean starting revision `6c73566a88f2f974eddead90f3ed364570f8992d`. Baseline content SHA-256 `ce85c4b18e09d4fb2e7be606cc96d91c6564fd0fd42ba20ed2005344f1b193b5`. Candidate content SHA-256 `753c6e2a0f3f75255eb2fdc354402f3ef7aac1541206b0794a9d09cd7d485315`. Both hash commands exited 0. Per-file manifests are in `results/raw/F1/{baseline-hash,candidate-hash-verified}.txt`.
- Python 3.12.12, Git 2.43.0 and Circom 2.1.9. Circom binary SHA-256 `1bacd5583e2cc79dc1e2deaefc9c7438f21957968651c5f93dc71073c58435e3`. The analyzer verified circomlib 2.0.5 against the locked 144-file tree SHA-256 `d359bab216fc262b406f468d87774ec1b6661e4438b38851fcd6a0a2e1e8a57a`.
- The baseline XR-03–06 run exited 1 with four test methods and seven failing assertions. `results/raw/F1/tests-before.log` SHA-256 `cf17aaaac03de4079c95648a9f013f95b8da70d02832bff945e0c70365f14010`. A replay of the final tests against the archived baseline reproduced all seven false-safe verdicts, exit 1. `tests-before-final.log` SHA-256 `d2187241abf5ebab70066e768d5091ac09a3820656e9501a1d4bd23a05c973ee`. The strengthened pre-fix S2a test exited 1 with two failed subtests. `p5-multi-before.log` SHA-256 `5127831d03447cde26124910da821a98560988201a632d97ab8fdc17f1038dbe`.
- The final full suite passed **77 tests** in 26.760 s, exit 0. `results/raw/F1/full-suite-verified.log` SHA-256 `47d4bc6048fc36eddfab49fe57488e024d873f8d1915fa5028c7d7ec66733d4a`. The two direct AZ1 CLI invocations exited 0. Raw JSON SHA-256 is `2f9179d9fb9407d9e6396d00fdc77863de7e52463e116b665a64ca00d2c5e51f` for faulty and `8ae511649a4a3c7150a6fa313569635acf37216f616c9ae2199d8f6571aca6d6` for fixed.
- The runner wrapper changes the baseline executable and redirects logs to an ignored namespace. It enforces `--skip-fetch` and checks the 52 unique family names with the held-out guard before either run. The baseline is the relevant tracked files from a `git archive HEAD` with the same lock-matching circomlib tree as the candidate. Each invocation's command, source revision, raw JSON hash and exit status are in its run manifest. The pre-task checkpoint is preserved in `results/raw/F1/project-status.before.md`.

Run the commands from the worktree root. The two before-test commands ran before the implementation edits. The DEV wrapper and comparison script are in the ignored raw directory.

```sh
export BC=/home/pollmix/Coding/bc
export BINDCHECK_CIRCOM="$BC/BindCheck/tools/circom-2.1.9/target/release/circom"
export GIT_OPTIONAL_LOCKS=0 GIT_NO_LAZY_FETCH=1 GIT_ALLOW_PROTOCOL=file
python3 -m unittest tests.f1.test_analyzer_soundness -v
python3 -m unittest tests.s2a.test_precision_fixes.S2aPrecisionFixes.test_multiple_verifier_calls_use_their_own_vectors -v
PYTHONPATH="$PWD/results/raw/F1/baseline:$PWD" \
  python3 -P -m unittest tests.f1.test_analyzer_soundness -v
python3 -m unittest tests.test_bindcheck_zk_cli tests.test_bindcheck_zk_controls \
  tests.soundness.test_verdict_soundness tests.soundness.test_followup \
  tests.coverage.test_rules tests.freeze2.test_p4_key tests.s2a.test_precision_fixes \
  tests.s2a2.test_residual_p5 tests.s2c.test_extent tests.f1.test_analyzer_soundness -v
python3 results/raw/F1/check_pp.py
python3 -m bindcheck_zk.cli analyze prototypes/az1 --consumer contracts/SettlementFaulty.sol
python3 -m bindcheck_zk.cli analyze prototypes/az1 --consumer contracts/SettlementFixed.sol
sh results/raw/F1/dev.sh before
sh results/raw/F1/dev.sh after
python3 results/raw/F1/compare_dev.py \
  results/raw/F1/T24/before-20261118T203036Z-9 \
  results/raw/F1/T24/after-20261118T203323Z-4 results/raw/F1/dev-delta.json
python3 -m bindcheck_zk.freeze
git diff --check
```

## Results

| Review item | Baseline reproduced | Candidate |
| --- | --- | --- |
| XR-03 mismatched verifier | P1 and P4 both `VERIFIED_WITHIN_SCOPE` | Both `UNKNOWN` with correspondence reason |
| XR-04 override and bypass | P4 `VERIFIED_WITHIN_SCOPE` on both | `UNKNOWN` on both. The direct inherited positive remains verified. |
| XR-05 incomplete circuit interface | P5 `VERIFIED_WITHIN_SCOPE` for a guarded dynamic vector | P5 `UNKNOWN` with incomplete-interface reason |
| XR-06 start at one and double pointer advance | P4 `VERIFIED_WITHIN_SCOPE` for both | Both `UNKNOWN / PUBLIC_INPUT_CANONICALITY_GUARD_NOT_FOUND`. The full-loop S2a positive still passes. |
| XR-09 P5 multiple verifier calls | Both `UNKNOWN / VERIFIER_MATCH_AMBIGUOUS` | Both `VERIFIED_WITHIN_SCOPE / PUBLIC_INPUT_COUNT_AND_ORDER_MATCH` with their exact vectors |
| AZ1 P1-EXTENT | Faulty and fixed expectations from S2c | Faulty `VIOLATION / EXTENT_CALLDATA_PREFIX_SHORTER_THAN_COMMITMENT` (E1). Fixed `VERIFIED_WITHIN_SCOPE / EXTENT_TAIL_CHECKED_NEUTRAL` (E1). |

### PP canonicality warning count

The [recomputed cards](../S2a/revision1/set-h-recomputed-cards.csv) show five exact-location retained TP warning cards, `W0018`, `W0186`, `W0513`, `W0603` and `W0755`. All five have `new_verdict=UNKNOWN` and `new_reason=PUBLIC_INPUT_CANONICALITY_GUARD_NOT_FOUND`. Two further original TP cards, `W0330` and `W0709`, were unavailable. The [revision-1 analysis](../S2a/revision1_analysis.py) sets `still_warning` for reason codes in `P4_WARNING_REASONS` and separately counts `tp_still_violation` from the exact verdict field. The [summary](../S2a/revision1/set-h-recomputed-summary.json) therefore correctly records five retained TP warnings and zero `VIOLATION` verdicts.

The source analyzer already emitted this reason with `UNKNOWN` at `pre-sprint-freeze2`. A fresh synthetic result gives the same verdict and warning flag through the same analysis code. A missing supported guard provides a warning without establishing that the effective verifier accepts a noncanonical word. The distinction explains the PP count. The PP scripts and historical reports were preserved. `results/raw/F1/pp-check.log` SHA-256 `195ddd62dbde8e78a8954017400d4b525120c827fd1aec6427cf04cd45bdf49b`, exit 0.

### Original 56 DEV rows

Both phases exited 0. All 56 analyzers ran to completion with zero crashes, zero row-level timeouts, and 372 identical triple identities across 46 rows. Each phase had 37 successful circuit builds or loads and 39 failed builds, including three circuit-build timeouts. No row changed its build-success or build-failure tally.

| Pattern | `VIOLATION` before and after | `VERIFIED_WITHIN_SCOPE` before and after | `UNKNOWN` before and after |
| --- | ---: | ---: | ---: |
| P1 | 6 | 0 | 50 |
| P2 | 0 | 0 | 56 |
| P3 | 6 | 7 | 43 |
| P4 | 6 | 15 | 35 |
| P5 | 1 | 3 | 52 |
| P1-EXTENT | 0 | 0 | 56 |

All 280 P1–P5 and all 56 P1-EXTENT row-level verdict and applicability cells are unchanged. The reason or unknown-code fields changed in the 12 cells below. The change affected 64 detailed triple results.

| Row | Pattern | Triple results affected | Reason for the cell change |
| --- | --- | ---: | --- |
| DEV-F02 | P4 | 4 | A conflicting verifier type replaces the source-key parse diagnostic. |
| DEV-F06 | P5 | 1 | An incomplete circuit interface replaces the generic order diagnostic. |
| DEV-F07 | P5 | 2 | The same interface gate replaces the remaining generic order diagnostics. The row already recorded an incomplete circuit interface. |
| DEV-F09 | P5 | 6 | The incomplete-interface gate replaces the generic order diagnostic. |
| DEV-F10 | P5 | 2 | The incomplete-interface gate replaces the generic order diagnostic for two triples. The separate count-mismatch violation still controls the row verdict. |
| DEV-F19 | P5 | 3 | The incomplete-interface gate identifies the source of uncertainty in three triples. |
| DEV-F20 | P4 | 6 | A conflicting verifier type replaces four unsupported key-layout diagnostics and two source-key verification results. |
| DEV-F20 | P5 | 6 | Unresolved vector associations bypass the function-wide arity comparison. In all six affected triples the declared receiver type conflicts with the verifier artifact. |
| DEV-F28 | P5 | 2 | The incomplete-interface gate identifies the source of uncertainty in two triples. |
| DEV-F30 | P5 | 27 | The per-vector check reaches the explicit failure to associate a unique vector with the verifier. The old function-wide ambiguity result is removed. |
| DEV-F39 | P5 | 3 | The per-vector check reaches the explicit failure to associate a unique vector with the verifier. The old function-wide ambiguity result is removed. |
| DEV-F48 | P5 | 2 | The incomplete-interface gate replaces the generic order diagnostic. |

**`VERIFIED_WITHIN_SCOPE` → `UNKNOWN`.** Both detailed downgrades are P4 in DEV-F20 at `contracts/SingleTxUnwrapWrapper.sol:130` (`_verifyProof`). They paired the same conflicting `contracts/verifiers/UnwrapGroth16Verifier.sol` with two candidate circuits, `circuits/circom/unwrap.circom` and `circuits/noir/src/main.nr`. Both now report `VERIFIER_CALL_CORRESPONDENCE_UNRESOLVED`. The row was already `UNKNOWN`.

The before ledger SHA-256 is `a89d34682e9390ba878cb927fb233d755a99a7baa1e083c01a1e762575909173` and its manifest SHA-256 is `ca81ab1efdcdd3a0056e7b0de909046df637c52a2cfdd36fc5290132ea96234f`. The after ledger SHA-256 is `33c1dce51ee65b979f67aab81bb28997b024a4c4f416e62b80931fe71de81707` and its manifest SHA-256 is `eceb626bf69cd4f6397fdcb5a335415459933daf298b189d8fa4d246017516fe`. The comparison exited 0. Its `results/raw/F1/dev-delta.json` SHA-256 is `5592a5e755756bb92c08fa43cac0a10166467ceda94efa52c4ac971df9ddf246`.

## Assumptions and limitations

- These are static DEV results under supported source patterns and the existing correspondence heuristics. They establish neither deployment identity nor proof-backed application effects. The AZ1 check here is the existing E1 control pair.
- The inheritance recognizer covers a narrow single-base, unchanged fixed-vector forwarding path. Overloaded or otherwise unresolved wrapper dispatch remains `UNKNOWN`. The gnark recognizer covers the matched Yul loop shape. Other compiler forms are outside this change.
- P5's guarded dynamic verdict remains limited to compatible length when element meaning is unavailable. The new circuit gate requires count and order recovery even for that limited verdict.
- The candidate hash is recorded for reviewer verification. No freeze was declared.

## Failed approaches and surprises

- The herdr-core terminal launch failed because the sandbox could not open its read-only core lock. The offline runs used sandboxed command sessions.
- The first baseline archive omitted the local circomlib tree and the requirements file from the hash manifest. It completed 56 rows with only 10 successful builds. The controlling baseline was rerun with both inputs restored. Its earlier log and run remain under `results/raw/F1/`.
- The first PP audit looked for the P4 stratum at the summary's top level and exited 1. The corrected audit reads the `strata` object and exits 0.

## Held-out hygiene statement

Both original DEV runs checked the same 52 repositories covering 56 pinned rows before inspecting their sources. The S2a2 tests used six retained fixture packets from five guard-allowed spent families. The PP audit read tracked S2a revision-1 evidence. AZ1 used the in-repository synthetic fixtures. No unused EVAL family was opened. No network, live system, broadcast, disclosure, commit or push occurred.

## Recommended next task

Replay the two retained P5 TP cards on approved, locally restored DEV checkouts. Completion requires both exact-site P5 count mismatches to remain `VIOLATION` at their pinned revisions.
