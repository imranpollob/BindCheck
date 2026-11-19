# F4 — rule-bound single use and final-verdict tests

**Status:** DONE for the bounded F4 implementation and source-level gates; **oracle EVM re-review remains WAITING**. No new E4 is claimed. This report is prospective to the XR3 gate; earlier F2/F3 verdicts are unchanged.

**AI disclosure:** OpenAI Codex, GPT-6 family (exact serving model ID unavailable) authored the changes and tests. These are AI-generated code and test interpretations, not independent human policy annotation. An author must inspect the policy, code, and any future EVM receipts.

## Objective and result

Close XR3-01 without making a repeatable effect spend an unrelated single-use authorization, and exercise the exported final E4 verdict decision with chain-free recorded observations. The driver now attributes each protected mint occurrence to exactly one rule. It derives the canonical `key_pub` for that matched rule, requires that rule and key in both the honest prelude and mutated transaction, and returns `UNKNOWN / EFFECT_RULE_AMBIGUOUS` when a protected effect matches multiple rules. Missing rule keys return `UNKNOWN / AUTHORIZATION_KEY_UNRESOLVED`. The prelude's protected effects receive the same standard-token state corroboration; an uncorroborated prelude cannot establish consumption.

`decideTrial` is the pure exported final verdict function. `runTrial` gathers tx, view, effect, verifier, prelude, obligation, and policy observations, then calls it. The existing E4 gates retain their order; the function also fails closed when the honest transaction failed or protected-effect attribution is absent. The runner accepts the F4 owned output namespace so the reviewer can run the new control.

The new manifest has disjoint token roles: single-use rule A matches `token_a`, repeatable rule B matches `token`, and `ReplayConsumer` mints only B on both the honest prelude and `REPLAY`. Its entitlement-only policy gives no expected verdict. The manifest passed `_validate_manifest`; the existing synthetic Solidity compiled. No Anvil trial ran in this lane.

## Files and provenance

- `oracle/evm_runner.cjs`: rule attribution and key accounting, prelude observation, pure verdict gate.
- `oracle/runner.py`: F4 output prefixes.
- `tests/oracle/test_oracle_gates.py`: final-verdict regressions, attribution, manifest and output validation.
- `tests/oracle/f4_mixed_rules.manifest.json` and `tests/oracle/f4_mixed_rules.policy.json`: owned-local mixed-rule control.
- `reports/F4/REPORT.md` and `docs/project-status.md`: current handoff and living checkpoint.
- Ignored raw scratch evidence: `results/raw/F4/reversion_probe.py`, `results/raw/F4/reversion.log`, and surgical driver copies in the same directory. No historical report or raw evidence was changed.

Base revision: `726938fac6d7361e68b0e9c1374adc149357f16f`. Base driver SHA-256: `2ed174707d69740e65a48d5eb21401450fee83d261a8ce150151171247bc23d6` (`git show HEAD:oracle/evm_runner.cjs`). Current driver SHA-256: `07131fb34663c1021f721c2f96c87f6f6e09e53a436ff522485c03ab6dc2d08a`; runner: `27395f6f429feca0cb8e860014957d4894d8b5e12d30676e48919317b501b269`; test file: `cda698d61ade32a26d0beb83f15eee2c0c72400eb37fba8bc1a2384df01ebf1e`; manifest: `02e86c40c9ba82b5e0ceca4a3f839fd74199ff1a51fdc4f0b90b9b36505c8fb1`; policy: `c5f5b750072ad7fe55a3a3ab38ef82fa9eedce69ac3fe90ac87412ef49007c05`.

## Commands and observed results

Environment: Python 3.12.12, pytest 9.0.1, Node v24.19.0, Forge 1.4.1-stable (`cf7746048646f2ecff48246dd61e265e49ab16f0`), Solc 0.8.20 for the synthetic fixture. Existing offline ethers 6.13.4 was used from `results/raw/F3/.driver/`; no network install occurred.

| Exact command | Exit | Observation |
| --- | ---: | --- |
| `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/oracle -q` | 0 | 36 passed in 3.03 s; includes `_validate_manifest` and F4 output-prefix checks. |
| `forge build --root tests/oracle/synthetic` | 0 | One Solidity file compiled with Solc 0.8.20. |
| `node --check oracle/evm_runner.cjs` | 0 | Syntax valid. |
| `git diff --check` | 0 | No whitespace errors. |
| `python3 results/raw/F4/reversion_probe.py > results/raw/F4/reversion.log` | 0 | All eight surgical reversion probes produced one failing pytest each. |

Each reversion probe changes one gate in an ignored scratch copy of the current driver to its pre-F4 or pre-fix behavior. `ORACLE_TEST_DRIVER` makes the same pytest assertion load that copy; the tracked driver is never reverted. This establishes that the test reaches the final decision path, while remaining source-level evidence rather than an EVM replay.

| Regression | Surgical reversion | Result against scratch copy |
| --- | --- | --- |
| XR-01 fake mint log | Bypass state corroboration in `decideTrial` | 1 failed; fake log would reach E4. |
| XR-02 missing/mismatched verifier call | Bypass verifier-path gate | 1 failed; unsupported path would reach E4. |
| XR-07 underpayment | Suppress underpaid-obligation violation | 1 failed; E4 would be lost. |
| XR-07 occurrence | Count each obligation independently, allowing one effect to satisfy two | 1 failed; one obligation would be falsely discharged. |
| XR2-01 failed view read | Bypass view-read gate | 1 failed; failed read would reach E4. |
| XR3-01 mixed rules | Restore global any-effect trigger for each single-use rule | 1 failed; B-only replay would falsely reach E4. |
| Honest transaction | Bypass honest-success gate | 1 failed; failed honest path would reach E4. |
| Ambiguous match | Bypass ambiguity gate | 1 failed; ambiguity would reach E4. |

The separate per-rule test also verifies that a rule using public index 1 reports canonical key `9` when its input is `r + 9`, even if another single-use rule uses index 0 and key `7`.

## Assumptions, limits, and reviewer action

This remains a local synthetic control under the standard atomic token model. The chain-free objects exercise final verdict logic and policy accounting; they do not establish E3 or E4. The pinned proof fixture's verifier is a synthetic canonicality control, so it cannot establish a real-proof E4 claim. F3's recorded EVM receipts were not independently rechecked here. No held-out family, live deployment, public RPC, fork, transaction broadcast, or third-party system was used. No failed implementation approach remained; the runner output allowlist initially omitted F4 and was corrected before handoff.

**Recommended next bounded task:** In a host where Anvil binds loopback, run `python3 -m oracle run tests/oracle/f4_mixed_rules.manifest.json --out results/raw/F4/reviewer-mixed-rules-<unused-id>` and require honest success plus `REPLAY` `NOT_CONFIRMED` with no A violation. Run the existing `tests/oracle/replay.manifest.json` into a distinct F4 output directory and require its genuine A replay to remain `E4-CONFIRMED`. Then repeat the 17 F3 re-confirmation manifests, review their receipts against policy, and have XR3 re-review the oracle before any held-out or paper E4 counting. Record exact hashes, commands, receipts and verdicts in fresh ignored F4 output and a tracked follow-up report. The oracle gate remains `UNKNOWN` until that review passes.

## Reviewer EVM evidence (added by the orchestrator, 2026-11-18)

Run outside the Codex sandbox on local Anvil 1.4.1 (chain 31337, no fork, no
public RPC). Baseline: detached worktree at base `726938f` with only the
`f4_mixed_rules` manifest/policy copied in (raw: `results/raw/F3/F4-before-*`
there). Patched: `results/raw/F4/after-*` (ignored).

| Control | Base oracle (`726938f`) | F4 |
|---|---|---|
| Mixed rules: single-use A never fires, repeatable B replayed | `E4-CONFIRMED` on `REPLAY` (the XR3-01 false E4) | `NOT_CONFIRMED` |

Re-confirmation on F4 (all 18 manifests exited 0; honest tx succeeded in every
variant): ZKredential original `CALLER-attacker` E4, repaired none; RacePass
original `FREE_ARG-credHash` E4, repaired none; synthetic alias `ALIAS-0`,
replay `REPLAY` (genuine single-use double spend still confirmed), obligation
`FREE_ARG-skipFee`, view obligation `FREE_ARG-numRealRows`, AZ1 faulty
`FREE_ARG-numRealRows`; all fixed/bound/repaired variants none; neg_underpay
`FREE_ARG-feeAmount`; F3 controls and neg_fakeeffect/neg_skipverify remain
`UNKNOWN` with their gate reasons. No earlier verdict changed.
