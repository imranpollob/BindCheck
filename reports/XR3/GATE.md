# XR3 — final oracle gate before S5

**Status:** DONE (read-only code review; S5 oracle gate blocked)

**AI disclosure:** OpenAI Codex, GPT-6 family; the exact serving model ID was not exposed. This is AI source review, not independent human policy annotation. The new finding below is a source-level counterexample and a focused helper result, not a new EVM E4 trial.

## Scope and evidence

Reviewed `oracle/evm_runner.cjs`, `oracle/runner.py`, `oracle/README.md`, `tests/oracle/test_oracle_gates.py`, the controlling research contract, and the XR, XR2, F2, and F3 reports at `5991af86726c4eff5ce6dd8878e87fbc6cead586` (`sprint/XR3`). The working tree was clean before this report. The current driver and runner SHA-256 values are `2ed174707d69740e65a48d5eb21401450fee83d261a8ce150151171247bc23d6` and `1c8753ad7adbd201ebbdb3335e6d3f40e0859a33e0f38d2428ec6fe2b2b6e9b0`, matching F3's stated current hashes. Test-file SHA-256: `817821e0d68c84431d517a98368bfab2a6b8a9d3725c3733aa61404fe65ea8c5`.

`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/oracle -q` exited **0: 25 passed in 1.90 s**. Versions: Python 3.12.12, pytest 9.0.1, Node v24.19.0. The focused in-memory Node helper call below exited 0 and produced one `single_use_exceeded` for a rule with no matching effect. No Anvil run was attempted. F3's reviewer EVM section reports three before/after controls and 17 patched manifest runs, but their ignored raw result directories are absent from this worktree (`results/raw/F3/` contains only `.driver`); those are recorded reviewer results, not independently rechecked receipts here.

## Original findings at the current code

| Finding | Status | Current file:line | Reason and held-out implication |
| --- | --- | --- | --- |
| XR-01 | **CLOSED** within the declared standard-token model | `oracle/evm_runner.cjs:563-613,784-793,847-869` | A mint-shaped ERC-20 log needs the exact recipient balance delta; ERC-721 needs new ownership and a +1 balance. Failure yields `UNKNOWN`. This closes the fake-log and pre-owned-token controls recorded by F2/F3. Corroboration still relies on standard atomic token behavior; arbitrary deceptive token views are outside the contract's initial scope. |
| XR-02 | **CLOSED** for declared checks | `oracle/evm_runner.cjs:513-555,776-782,870-876` | The mutated call trace must match the consumer address and calldata, with a distinct direct call for every declared verifier, exact ABI calldata, and true output. F3's skipped-second-verifier control is reported `UNKNOWN`. Correct and complete `verifier_checks` remain a manifest-authoring obligation; the trace does not prove semantic use of returned booleans. |
| XR-07 | **CLOSED** for declared event obligations | `oracle/evm_runner.cjs:222-284,342-360,806-830,1163-1170` | Exact value/token ID matching and global occurrence allocation prevent the original underpayment and event-reuse errors. The honest and mutated ledgers use the same allocator. Obligations expressed as events inherit the declared standard-token/event model; this is not general storage-obligation extraction. |
| XR-08 | **PARTIAL** | `oracle/runner.py:74-103,150-179,363-403`; `oracle/README.md:15-19` | The runner rejects explicit forbidden flags and non-loopback URL tokens in manifest argv/env and constructs its own loopback Anvil. Wrapper scripts, inherited environment, and redirects can bypass the token screen. This affects the stated command/network safety boundary, **not an oracle false-E4 path** in a project-authored held-out manifest under owned-local execution. It is not a network sandbox. |
| XR-09 | **PARTIAL** | `tests/oracle/test_oracle_gates.py:125-263`; `oracle/evm_runner.cjs:853-877` | Pytest now collects 25 oracle tests, including F3 helper controls. It does not execute the final `runTrial` verdict branches or the owned-local EVM controls. Reverting the helper fixes is caught; disconnecting a helper from the E4 gate could still leave pytest green. This is a detection gap, not itself a false-E4 path. F3's separate EVM evidence covers the original controls as reported. |
| XR2-01 | **CLOSED** | `oracle/evm_runner.cjs:926-957,1147-1162,760-768` | Every declared/policy-referenced view must have bigint before and after observations; a failed honest or mutated read makes trials `UNKNOWN / VIEW_READ_FAILED`. F3 reports the late-view before/after EVM control. |

F2's claim that each of its five fixes had a test needs the XR2/F3 qualification: the original F2 implementation left XR-01, XR-02, XR-07 and XR-09 partial, and F3 added the stricter gates and focused tests. The current contract is revision 4; the earlier reports explicitly used revision 3. This review applies the current contract prospectively and does not relabel their historical results.

## New finding

### XR3-01 — High — A repeatable effect triggers an unrelated single-use rule

**File:line:** `oracle/evm_runner.cjs:324-331,367-376,795-814,853-876`.

`runTrial` sets one global `single_use_double_spend` flag when a prelude ran and the mutation emits **any** protected mint. `evaluatePolicy` then adds `single_use_exceeded` for **every** rule with `single_use`, even when that rule matched no effect. The authorization key is likewise taken from the first single-use rule, with no effect-to-key association.

**Failure scenario:** A policy has a single-use protected effect A and a separate repeatable protected effect B. The honest prelude and `REPLAY` each commit only B, which the policy permits repeatedly; A is never emitted. If B is state-corroborated and the declared verifier accepts on the replay path, `doubleSpend` is true, the A rule reports a violation, and the trial reaches `E4-CONFIRMED` despite no A double spend and no other policy violation. A project-authored held-out manifest can contain multiple protected-effect rules, so this can produce a false E4 in S5; it is not limited to the command safety boundary.

**Focused check:** An in-memory `evaluatePolicy` call with A (`single_use`) and B (repeatable), one B effect, and the exact `runTrial` context flag `single_use_double_spend:true` exited 0 and returned `[{'rule':'single_A','type':'single_use_exceeded',...}]`. This verifies the helper's false violation and the source shows the E4 path. It does not demonstrate a full EVM transaction. **Confidence:** high for the source path; conditional on a multi-rule held-out policy and successful, state-corroborated replay. No current F3 fixture is claimed affected.

## Other false-E4 boundaries checked

- **Effect/state:** protected mint logs are corroborated before E4; failed reads return `UNKNOWN` (`evm_runner.cjs:784-793,847-869`). The new single-use path can still use a *real* B state change while falsely attributing it to A.
- **Mutated verifier:** every declared verifier call is matched on the mutated consumer trace; missing or mismatched calls return `UNKNOWN` (`:513-555,776-782,870-876`). Manifest completeness and proof/artifact correspondence require review outside this generic trace matcher.
- **Obligations:** value and token ID matching plus global occurrence allocation prevent one observed effect from discharging two clauses (`:222-284,342-360`). No new allocator false-E4 path was established under the declared event model.
- **Views:** absent/failed before or after reads are rejected, not replaced by zero (`:926-957,760-768,1147-1162`).
- **Honest transaction:** `main` records `honest.succeeded` and exits with code 3 if false (`:1149-1175,1204-1216`); `runner.py:178-188,398-415` converts that driver failure to top-level `UNKNOWN`. Honest setup-step return values are not checked at `evm_runner.cjs:1140-1145`, but the same steps are checked on each fresh trial at `:645-668`; no deterministic false-E4 scenario was established from this asymmetry. It merits a fail-closed test.
- **Trial isolation:** every trial constructs a new resolver and deployments (`:635-645`); `env` shares only honest reference observations and proof data (`:1124-1130,1163-1170`), and the global nonce map tracks signer nonces. No effect-state leak between operators was found.

`rg -n -i 'zkredential|racepass|az1|synthetic|case_id|repository|repo|manifest\.case|variant\.name' oracle/*.cjs oracle/*.py` found no case-name or repository-dependent verdict branch. Matches were output metadata, generic source staging, paths/comments, and the driver spec's `case_id` field.

## Test reversion check

| Fix | Would `tests/oracle/test_oracle_gates.py` fail if the fix were reverted? |
| --- | --- |
| XR-01 | **Helper yes:** `:225-238` reject the pre-owned ERC-721 result. **Final E4 wiring no:** no pytest transaction exercises `uncorroborated` at `evm_runner.cjs:847-869`; F3's recorded EVM control is separate. |
| XR-02 | **Helper yes:** `:181-222,241-248` reject skipped, false, mismatched, and nested calls. **Final E4 wiring no:** removal of the `verifierPath` verdict condition is not exercised by pytest. |
| XR-07 | **Helper yes:** `:157-178,257-263` check value and global allocation. **Full policy/trial wiring no:** no pytest trial asserts the E4 result for an underpaid obligation. |
| XR-08 | **Helper yes:** `:36-60` cover literal tokens. **Call site no:** removing `_assert_local_only_command` from `_command` would not fail these direct helper tests. |
| XR2-01 | **Helper yes:** `:251-254` rejects a missing view baseline. **Final propagation no:** no pytest trial checks that `VIEW_READ_FAILED` prevents E4. |
| XR-09 | The suite is present and green, but does not cover those final verdict connections or XR3-01. |

## Gate and handoff

**ORACLE BLOCKED: XR3-01**

Only `reports/XR3/GATE.md` changed. No code, historical report, source checkout, or held-out family was edited or opened. No network, Anvil, fork, broadcast, or third-party system was used. The primary limitation is that this lane cannot provide an EVM replay of XR3-01; the relevant F3 EVM receipts are unavailable in this checkout, so F3's results are cited as reported evidence. No attempted approach failed; pytest and the focused helper check both exited 0.

**Recommended next task:** bind replay/single-use accounting to the specific protected effect and its canonical authorization key, then add a two-rule owned-local negative control. Completion criterion: two B-only executions return `NOT_CONFIRMED` while a genuine second A effect under the same key confirms, with `tests/oracle` green and the retained F3 re-confirmation matrix unchanged.
