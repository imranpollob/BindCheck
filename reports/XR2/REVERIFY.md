# XR2 — independent re-verification of F1 and F2

Status: DONE (read-only source review; focused local tests; no full oracle replay)

AI disclosure: OpenAI Codex, GPT-6 family. The exact serving model ID was not exposed. This is AI code review, not independent human policy annotation.

## Scope and result

Reviewed at `aac072f1bdfd4845d0912c9548ebaa5f9d6f5f21` against `docs/research-contract.md` revision 3, `reports/XR/FINDINGS.md`, and the F1/F2 reports. The table judges whether each *original* failure mode is closed. A `PARTIAL` result does not invalidate a retained real-case result by itself; the scenarios below are conditional source-level counterexamples, not locally reproduced E4 cases.

| Finding | Status | Current file:line | Reason |
| --- | --- | --- | --- |
| XR-01 | **PARTIAL** | `oracle/evm_runner.cjs:512-545,715-720,774-802` | ERC-20 requires an exact recipient balance delta, so the original fake ERC-20 log is barred. ERC-721 checks only `ownerOf` **after** the transaction. A zero-to-recipient `Transfer` for a token the recipient already owned can pass corroboration without an ownership change; with an entitlement mismatch and a true verifier call it can reach E4. |
| XR-02 | **PARTIAL** | `oracle/evm_runner.cjs:459-504,703-710,797-802` | A branch that never calls a declared verifier cannot reach E4. The new trace check accepts **any one** declared verifier address returning `1`; it discards call input and does not establish that all required verifiers accepted the arguments used by the consumer. A two-verifier path can call one successfully, skip the other, commit a policy-violating effect, and pass this gate. |
| XR-03 | **CLOSED** | `bindcheck_zk/analyzer.py:1014-1021,1829-1842` | P1 and triple P4 explicitly become `UNKNOWN / VERIFIER_CALL_CORRESPONDENCE_UNRESOLVED` when receiver and implementation mismatch. F1's exact control passes. |
| XR-04 | **CLOSED** | `bindcheck_zk/analyzer.py:318-381,384-423` | Propagation now requires a directly imported single base, exact forwarding wrapper, one base method, and guards for every fixed-vector position at method entry. Override and conditional-bypass controls remain `UNKNOWN`. This is a narrow lexical recognizer, not a general dispatch proof. |
| XR-05 | **CLOSED** | `bindcheck_zk/analyzer.py:1473-1510` | Incomplete circuit count or order returns `UNKNOWN` before either P5 safe branch. The guarded dynamic `Gaffine` control passes. |
| XR-06 | **CLOSED** | `bindcheck_zk/p4.py:224-260` | The gnark loop is matched as a whole: zero-initialized Yul `let`, exclusive `lt(i,s)`, unit index increment, one 32-byte pointer advance, and the exact helper call. The start-at-one and double-step controls fail closed. |
| XR-07 | **PARTIAL** | `oracle/evm_runner.cjs:222-253,312-330,1080-1086` | Exact `value`/`token_id` and the honest occurrence count close the underpayment and one-versus-two-events controls. Counts are computed independently for each obligation ID. Two same-shaped policy obligations can both count the *same* event, so the claimed multiset discharge is not globally occurrence preserving. This can conceal an underdischarged honest or mutated path. |
| XR-08 | **PARTIAL** | `oracle/runner.py:80-101,148-177,350-360` | Direct `--fork-url`, `--broadcast`, `--unlocked`, and literal non-loopback URL tokens in manifest argv/env are rejected before launch. A `prepare` wrapper script can construct a URL internally, use an inherited env var (explicitly unscanned at lines 165-168), or follow a loopback redirect. The report correctly describes a command-token denylist; it is not a no-network guarantee. No such command was run here. |
| XR-09 | **PARTIAL** | `tests/oracle/test_oracle_gates.py:1-12,36-60,125-205`; `oracle/runner.py:243-261` | Pytest now collects 19 oracle tests, and source assertions cover command tokens plus pure verifier/obligation helpers. XR-01's E4 verdict gate and the owned-local fake-effect/skip-verifier controls are not exercised by this pytest suite. Node-backed tests require pinned ethers and may skip if unavailable. Thus a reverted corroboration/verdict gate can still pass the standard pytest command. |

**Gate verdict: `FREEZE-3 BLOCKED: XR-01 and XR-02 remain PARTIAL; XR2-01 is a new high-severity false-E4 path.`**

## New finding

### XR2-01 — High — A failed pre-transaction view read becomes a zero baseline

**File:line:** `oracle/evm_runner.cjs:853-885,893-916,1067-1076,731-748,780-803`.

`readStateViews` silently omits a view when the call fails. `diffViews` then substitutes `0n` for that missing side. A view which reverts before the transaction but succeeds afterward is therefore reported as a positive state delta even when its underlying counter did not change. The fabricated delta can set `viewCommitted`, satisfy the honest-path obligation condition, and produce `undischarged_view_obligation` and E4 if the mutated path calls a verifier returning true.

Concrete conditional scenario: two getters are unavailable until an `initialized` bit is set. The shared admitted prestate has stored credit 150 and backing 100. The honest transaction sets backing to 150 and enables the getters; the mutated transaction only enables the getters. The honest read failures become zero baselines and appear to discharge a 150/150 obligation; the mutated read failures likewise appear to grant +150 credit with only +100 backing. The oracle can confirm a 50-unit shortfall without any committed credit increase. This is a source-confirmed path, not a run against the retained AZ1 fixture. Fail closed if either side of a required view is missing, and require explicit before/after observations for each view used in an E4 claim.

**Confidence:** High for the dataflow and gate, conditional for reaching it in a supplied scenario. No new `VERIFIED_WITHIN_SCOPE` analyzer path was found in the F1 changes. A case-name/repository grep of `oracle/*.cjs`, `oracle/*.py`, and `bindcheck_zk/*.py` found no case-specific verdict branch (only generic comments mentioning AZ1/synthetic controls). The F1 and F2 expected values have specific source-level explanations, but the oracle unit tests alone do not independently establish E4 behavior.

## Commands and observed results

- `git rev-parse HEAD` → `aac072f1bdfd4845d0912c9548ebaa5f9d6f5f21`; starting `git status --short` was empty.
- `python3 --version` → 3.12.12; `node --version` → v24.19.0; `python3 -m pytest --version` → 9.0.1.
- `export BC=/home/pollmix/Coding/bc; export BINDCHECK_CIRCOM=$BC/BindCheck/tools/circom-2.1.9/target/release/circom; export PYTHONDONTWRITEBYTECODE=1; python3 -m unittest tests.f1.test_analyzer_soundness` → exit 0, four tests passed.
- `python3 -m pytest tests/oracle -q` began, printed 12 dots and one skip, then was interrupted (exit 130) when the Node test helper reached `ensure_driver_deps`, which installs ethers if absent. The full suite was **not** verified here; no network access or full oracle run was authorized by this lane.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/oracle/test_oracle_gates.py -q -k 'local_command or validate or run_rejects'` → exit 0, 12 passed, seven deselected.
- `rg -n -i 'zkredential|racepass|az1|synthetic|neg_fakeeffect|neg_skipverify' oracle/*.cjs oracle/*.py bindcheck_zk/*.py` → no case-specific branch; matches were comments only. No third-party repository, held-out EVAL family, live deployment, local fork, or network target was opened.

Reviewed source SHA-256: `oracle/evm_runner.cjs` `96ad398988fff19923c61303a32077438e1ca1f6d2f2b04585353d1f1682cc6a`; `oracle/runner.py` `b1bd5af72bd97f84950725ea196a1b95f670e97aab4940f826fe8f5a34eb3d86`; `bindcheck_zk/analyzer.py` `3fe5291cc68bd571c06797aac5db20b7748a0a1733fd2ed4bea481c124c6ba6c`; `bindcheck_zk/p4.py` `1b27d211fc28327a3ce72f645aed32a79e548fa772502d8c68ec421d39118ce6`.

## Assumptions, limitations, and handoff

Only `reports/XR2/REVERIFY.md` was authored. This was a read-only code review, so no historical evidence or living status document was changed. F2's retained real-case replay results were read as reported, not independently rerun. The counterexamples are local-only scenarios and do not claim a flaw in ZKredential, RacePass, or AZ1. The full oracle pytest attempt was stopped because of the dependency installation path; no failure verdict was inferred from that incomplete run.

Recommended next task: repair the three false-E4 boundaries (ERC-721 pre/post ownership, required-verifier call evidence including actual inputs for every check, and complete view pre/post reads), then run owned-local negative controls for each. Completion criterion: all three controls return `UNKNOWN` or `NOT_CONFIRMED`, their pre-fix versions produce the predicted false E4, and the retained real-case E4 controls still pass under the same gate.
