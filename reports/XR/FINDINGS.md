# XR — Cross-model review of S4 and S2a

Status: DONE (read-only code review; no E4 rerun)
Verdict/outcome: REVIEW_FINDINGS — eight implementation findings and one test-gap finding below. These are review findings, not new `VIOLATION` or E4 results for ZKredential or RacePass.

AI disclosure: OpenAI Codex, GPT-6 family (the exact runtime model ID was not exposed to this session). The reviewer inspected the code and reports and ran the commands listed below. AI review is not independent human policy annotation.

## Scope and evidence

Reviewed `oracle/`, `tests/oracle/`, `reports/S4/REPORT*.md`, the oracle case manifests/policies, `findings/{zkredential,racepass}/policy.md`, `git diff pre-sprint-freeze2 -- bindcheck_zk/ tests/s2a/`, and `reports/S2a/REPORT.md`. The controlling contract is `docs/research-contract.md` revision 3, especially §§6 and 8. The worktree was clean at review start. No third-party checkout was opened, no live or forked chain was contacted, and no code was edited.

- Reviewed HEAD: `c82eac653fd53daf71dc0eb013849f3be42dd1ba` (`sprint/XR`); baseline tag `pre-sprint-freeze2`: `bc8c96702f14d4236f2935bfafa2090e42648499`.
- `python3 -m pytest tests/oracle tests/s2a -q` exited 0: **20 passed, 2 subtests passed** in 0.21 s. No Python tests were collected from `tests/oracle/`. Versions: Python 3.12.12, pytest 9.0.1, Node v24.19.0; `anvil` is present at `/home/pollmix/.foundry/bin/anvil` but no Anvil run was attempted.
- Three isolated, read-only `python3 - <<'PY'` checks exited 0: `analyze_p1` returned `VERIFIED_WITHIN_SCOPE` for a verifier correspondence classified `mismatch`; `analyze_p5` returned `VERIFIED_WITHIN_SCOPE` for an incomplete circuit interface; `canonical_guard_positions` returned `all_positions=True` for a Yul loop starting at 1 and checking only the first `n-1` words. These calls constructed objects/strings in memory and changed no source file.
- Source SHA-256: `oracle/evm_runner.cjs` `e44d48dff5166a80f3ecfdc3e57169ed312d9239726c172c6be1a999012c3891`; `oracle/runner.py` `9ac6ad0b4c22d29c1b97f4456ecefc7195a0ef4c59c4b33cafa36c488b97b2d0`; `bindcheck_zk/analyzer.py` `7f8ce25e310a9accccdd4dc5a8789c0d797e43c340467b1f08635e2411949e38`; `bindcheck_zk/p4.py` `75139c8bfa874752906974e6c22eea90327e1dfc7510fbf6c5ca057a3541466e`.

## Findings (most severe first)

### XR-01 — High — A `Transfer` log is treated as a committed token effect

**File:line:** `oracle/evm_runner.cjs:171-197`, `:530`, `:578-595`.

**Claim broken:** `E4-CONFIRMED` requires an unauthorized *committed* protected effect, checked on state (`docs/research-contract.md` §8). The driver classifies any receipt log with the ERC-20/721 `Transfer` topic as such an effect. It records `debug_traceTransaction` and balance deltas but does not use either to validate the event before issuing E4.

**Concrete scenario:** A local consumer accepts a valid proof, emits `Transfer(0x0, attacker, 1)` from a contract without changing token balances or ownership, and returns successfully. A recipient-entitlement policy expects the proof wallet. `extractEffects` creates a mint, `evaluatePolicy` sees the attacker recipient, the direct verifier check returns true, and the trial becomes `E4-CONFIRMED` despite no protected token effect committing. The current two real-case outcomes were not rerun or invalidated by this conditional scenario.

**Confidence:** Confirmed by reading the complete verdict path. **Suggested fix:** Require a policy-declared asset/contract identity and corroborate each claimed protected effect with before/after state or a trusted token implementation; otherwise report `UNKNOWN`.

### XR-02 — High — Direct verifier success is not linked to the mutated call

**File:line:** `oracle/evm_runner.cjs:390-405`, `:445`, `:473-505`, `:521-595`.

**Claim broken:** E4 says the *mutated transaction* passed the unchanged verifier and consumer. `verifierAccepts` calls manifest-declared verifiers with the original proof/public data before mutation. No trace or call-level check establishes that the mutated consumer transaction invoked those same verifiers with the mutated arguments. For `ALIAS`, the altered public vector is expressly different from the one directly checked.

**Concrete scenario:** A manifest's `FREE_ARG` selects a consumer branch that skips verification and emits an unauthorized mint; the honest branch verifies normally. The standalone original-proof check is true, the mutated call succeeds, and the emitted log violates the policy, so the driver reports `E4-CONFIRMED` without verifier acceptance on the mutated path. The same gap applies if the consumer calls a different verifier instance or passes different public values.

**Confidence:** Confirmed by reading; conditional scenario, not observed in the current real manifests. **Suggested fix:** Establish verifier invocation and actual inputs on the mutated execution path (or prove it from the pinned consumer implementation) before granting E4. Keep the direct verifier call as an E3 preflight.

### XR-03 — High — P1 can verify against a known mismatched verifier

**File:line:** `bindcheck_zk/analyzer.py:626-628`, `:930-936`, `:965-966`, `:1053-1058`.

**Claim broken:** `VERIFIED_WITHIN_SCOPE` is issued despite unresolved artifact correspondence. S2a adds a mismatch check to P3/P5, but P1 only checks that some verifier and circuit objects exist. When no exact verifier is available, `make_triples` falls back to all verifier files, including one classified `mismatch`.

**Concrete scenario:** `Consumer` declares a `ProductionVerifier` receiver and forwards `[recipient, amount]` to it before a transfer. The repository contains only an unrelated `TutorialVerifier` implementation of the same arity and a two-public-value circuit. In an isolated call, `_verifier_correspondence` returned `mismatch` while `analyze_p1` returned `VERIFIED_WITHIN_SCOPE / EFFECT_VALUES_DIRECT_PUBLIC_INPUTS`. The actual production verifier/producer relation remains unresolved.

**Confidence:** Confirmed by the in-memory call and source inspection. **Suggested fix:** Apply the same exact-correspondence gate to P1 (and any P4 result attached to its triple); return `UNKNOWN` until the called implementation is identified.

### XR-04 — High — A base verifier's canonicality verdict is copied across an override

**File:line:** `bindcheck_zk/analyzer.py:317-347` (especially `:328-347`); existing regression `tests/s2a/test_precision_fixes.py:228-247`.

**Claim broken:** P4 `VERIFIED_WITHIN_SCOPE` can describe a base contract's guard rather than the wrapper's effective verification path. The propagation checks for inheritance and the token `verify(` anywhere in the wrapper, then replaces the wrapper's P4 result with the base's result. It does not establish method dispatch, override behavior, or that the inherited guard is reached.

**Concrete scenario:** A guarded `BaseVerifier.verify` is virtual; `Wrapper is BaseVerifier` overrides `verify` with an unguarded public-input path. The wrapper's own P4 result is `UNKNOWN`, but the single verified base is copied over it. The existing test explicitly expects unconditional copying from a constructed verified base, so it does not reject this override case.

**Confidence:** Confirmed by reading. **Suggested fix:** Propagate only after resolving the exact called method and proving there is no overriding or bypass path. Otherwise retain the wrapper's `UNKNOWN` result.

### XR-05 — Medium — P5 marks an incomplete circuit interface safe for a guarded dynamic vector

**File:line:** `bindcheck_zk/analyzer.py:1384-1409`; related incomplete Noir handling `bindcheck_zk/circuits.py:170-201`.

**Claim broken:** P5 can return `VERIFIED_WITHIN_SCOPE` when public element count and meaning from the circuit are unresolved. An unsupported public Noir composite has `public_count=None` and `order_complete=False`; the mismatch checks are skipped, then the dynamic-vector branch grants a safe verdict if the consumer length guard equals a verifier-declared arity.

**Concrete scenario:** A circuit public `Gaffine` (or another unsupported composite), a one-word verifier declaration, and a consumer dynamic `inputs` array guarded to length 1. The isolated `analyze_p5` call returned `VERIFIED_WITHIN_SCOPE / DYNAMIC_PUBLIC_INPUT_LENGTH_GUARDED` despite the unknown flattening of `Gaffine`.

**Confidence:** Confirmed by in-memory call. **Suggested fix:** Require `circuit.order_complete` and an established circuit public count before any P5 safe verdict, including the dynamic-vector branch; otherwise `UNKNOWN`.

### XR-06 — Medium — Gnark loop recognition can miss the last public input

**File:line:** `bindcheck_zk/p4.py:224-259`; regression `tests/s2a/test_precision_fixes.py:142-158`.

**Claim broken:** A canonicality guard is credited as covering all positions without proving the loop begins at zero and advances exactly once per word. The new regex accepts `for { let i := 1 } lt(i, s) { i := add(i, 1) }` with a pointer starting at `public_inputs.offset`.

**Concrete scenario:** With `s=n`, that loop checks the first `n-1` calldata words and leaves the last one unchecked; all four regex conditions still match. The in-memory check returned `canonical_guard_positions(...)["all_positions"] == True`, enabling a P4 safe result when the other source-key preconditions hold.

**Confidence:** Confirmed by in-memory call. **Suggested fix:** Parse and verify the induction variable's initialization, condition, update, and pointer progression together. Add a negative control starting at 1 and another with a skipped pointer step.

### XR-07 — Medium — Obligation discharge ignores quantity and multiplicity

**File:line:** `oracle/evm_runner.cjs:215-226`, `:278-299`; policy `tests/oracle/obligation.policy.json:20-34`.

**Claim broken:** The oracle's S4c obligation claim is only an existence check, although the research contract's coverage rule preserves quantity and multiplicity. The `match` schema compares type, zero sender, contract role, and recipient, but never `value`, token ID, or occurrence count.

**Concrete scenario:** The honest transaction mints a `+1000` reward and a `+50` fee to treasury. A mutated transaction still mints the reward but pays only `+1` to treasury. The `fee-to-treasury` obligation is marked discharged and the trial is `NOT_CONFIRMED`, even if policy requires the 50-unit fee. A single matching event would likewise satisfy multiple same-shaped obligations.

**Confidence:** Confirmed by reading; the supplied synthetic mutation omits the fee entirely, so it does not exercise this case. **Suggested fix:** Represent amount and occurrence matching in the policy, and compare an occurrence-preserving effect multiset or mark unsupported quantitative obligations `UNKNOWN`.

### XR-08 — Medium — Manifest safety flags do not constrain preparatory commands

**File:line:** `oracle/runner.py:112-145`, `:166-198`, `:309-318`; `:330-359` for the internally launched local Anvil.

**Claim broken:** The S4 report's broad claim that manifests cannot fork or access a public chain is not enforced for `prepare`, `proof`, `transform`, or `build`. The validator checks `safety.local_only=true` and `fork_enabled=false`, while `_command` executes arbitrary manifest-provided argv, cwd, and environment.

**Concrete scenario:** A manifest with the required safety booleans and a `prepare` command invoking a tool with `--fork-url https://...` passes `_validate_manifest`; the command is launched before the driver starts its own local Anvil. The `run --fork-url` CLI guard does not cover this path. This review did not execute such a command or access a network.

**Confidence:** Confirmed by reading; exploitability depends on the execution environment and who may supply a manifest. **Suggested fix:** Treat manifests as trusted executable programs or run preparation in a network-restricted process sandbox with a command allowlist. Narrow the safety claim to the internally constructed Anvil/driver path until that boundary is enforced.

### XR-09 — Low — The requested pytest command does not test the oracle

**File:line:** `tests/oracle/` (no collected Python test module); `tests/s2a/test_precision_fixes.py:269-292`.

**Claim broken:** The stated test gate does not exercise the oracle's verdict logic. `python3 -m pytest tests/oracle tests/s2a -q` reports 20 passing tests, all from S2a; the multi-verifier test also accepts any P5 outcome other than `VIOLATION`, including `UNKNOWN`, so it does not establish correct call-specific matching.

**Concrete scenario:** A regression makes every oracle trial `E4-CONFIRMED` or makes P5 always `UNKNOWN`; the present pytest command can still pass. S4's recorded full Anvil runs provide separate development evidence but do not make this command an oracle regression suite.

**Confidence:** Confirmed by the pytest run and test inspection. **Suggested fix:** Add focused oracle unit controls for E4 gates and false-confirmation paths, then an owned-local integration gate; assert the intended P5 verdict and matched vector in the multi-verifier test.

## Checks that held up in this review

- The main `run --fork-url` option is explicitly rejected, manifests with false `local_only` or true `fork_enabled` are rejected, and the internally launched Anvil/driver RPC uses `127.0.0.1` (`oracle/runner.py:267-272`, `:330-359`).
- The current case policy JSON files state recipient or credential entitlements rather than expected verdicts; the driver does not branch on `case_id`, repository, contract, or variant names. The policy checks remain provisional human interpretations, as their `findings/*/policy.md` files disclose.
- A failed trial deployment setup becomes `UNKNOWN`, an Anvil/driver exception makes the run `UNKNOWN`, and a reverted mutated transaction does not become E4 (`oracle/evm_runner.cjs:420-442`, `:578-595`; `oracle/runner.py:376-397`).
- `ALIAS` adds the BN254 scalar modulus at the selected public-array index, and `REPLAY` submits the same honest arguments after a successful prelude; each trial gets fresh deployments (`oracle/evm_runner.cjs:416-419`, `:458-482`, `:507`).
- S2a explicitly records semantic exclusions in coverage, and its P3/P5 mismatch checks downgrade known mismatched verifier correspondence to `UNKNOWN`. No unused EVAL family was opened in this review.

## Assumptions, limits, and next task

The high findings are reachable code-path counterexamples; they do not establish that the two retained S4 real-case E4 results are false. This review did not rerun real proofs, inspect ignored S4 raw receipts, or adjudicate the provisional policies. The command-level checks above are isolated function checks, not EVM demonstrations. No network was available or used. No approach failed; a full Anvil rerun was unnecessary for the code-path findings.

**Recommended next task:** Repair XR-01 and XR-02 first, then run an owned-local negative control that emits a fake `Transfer` without state change and one that bypasses verification on a mutated branch. Completion criterion: both return `UNKNOWN` or `NOT_CONFIRMED` with explicit reasons, while the existing real-proof E4 cases still pass after receipt/state and verifier-path evidence is recorded.
