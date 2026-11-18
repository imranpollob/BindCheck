# S2a — Precision fixes for freeze 3 (DEV only)

Status: PARTIAL

Verdict/outcome: CANDIDATE_PREPARED_FULL_SPENT_RERUN_UNAVAILABLE

## What was done

Implemented general, repository-independent precision fixes in the frozen
analyzer and added 18 development-only regressions:

- Solidity public-vector recovery now masks comments and strings, rejects proof
  arrays as public-input vectors, preserves unresolved fixed-array positions,
  chooses the call-specific vector in multi-verifier consumers, and requires
  receiver/type evidence before matching a verifier.
- P1 recovery now distinguishes caller-funded `msg.value`, caller-owned balance
  debits, state-derived values, and non-asset methods named `transfer`.
- P3 can credit the exact generated verifier's `checkField` guard instead of an
  unrelated verifier, while unresolved correspondence fails closed.
- P4 recognizes a generated gnark full-input scalar-field loop, propagates an
  exact base verifier's guard to its wrapper, and excludes CTF/write-up/example
  paths from application findings.
- Circom fixed multidimensional arrays are flattened with public outputs before
  public inputs. Noir scalar/array public types are flattened; unresolved
  user-defined composites fail closed rather than being guessed.
- Honk/UltraHonk arity recovery handles `NUMBER_OF_PUBLIC_INPUTS`, explicit
  pairing-point/aggregation reservations, and generated wrappers whose arity
  constant is in an exactly imported verification-key file. This does not add
  the S2b Honk canonicality rule.

No repository name, file name, warning ID, expected verdict, or Freeze 3 tag
is encoded in analyzer logic. No Freeze 3 declaration or tag was created.

AI disclosure: OpenAI Codex, GPT-5, executed the task; the human author must
review the code, labels, and research claims before use.

## Evidence (paths, hashes, commands, exit codes, tool versions)

### Analyzer and tests

- Candidate content hash (computed, not declared):
  `BINDCHECK_ZK_CONTENT_SHA256=91e331c940c7dbbf0411c88337ef21c9418ac083658fffcf52d7c4f2998c4939`.
- Hash command: `python3 -m bindcheck_zk.freeze` — exit 0.
- `python3 -m compileall -q bindcheck_zk tests/s2a` — exit 0.
- `git diff --check` — exit 0.
- Focused command:
  `BINDCHECK_CIRCOM=/home/pollmix/Coding/bc/BindCheck/tools/circom-src/target/release/circom python3 -m unittest tests.s2a.test_precision_fixes -v`
  — 18 tests, exit 0; log: `results/raw/S2a/tests/s2a-suite.log`.
- Prescribed aggregate command:
  `BINDCHECK_CIRCOM=/home/pollmix/Coding/bc/BindCheck/tools/circom-src/target/release/circom python3 -m unittest tests.test_bindcheck_zk_cli tests.test_bindcheck_zk_controls tests.soundness.test_verdict_soundness tests.soundness.test_followup tests.coverage.test_rules tests.freeze2.test_p4_key tests.s2a.test_precision_fixes -v`
  — 56 tests, one failure, exit 1; log:
  `results/raw/S2a/tests/full-suite.log`. The sole failure is COV-01 include
  resolution: this worktree has no pinned `node_modules/circomlib`, so Circom
  reports `error[P1014] ... circomlib/circuits/comparators.circom ... not been found`.
- Versions: Python 3.12.12; Git 2.43.0; the required executable exists, but
  `.../circom --version` reports `circom compiler 2.2.3`, not the completion
  criterion's Linux Circom 2.1.9.

### Development measurements

The unchanged original-DEV runner was imported only to redirect its raw root
into S2a's owned directory, then invoked offline with retained checkouts:

```text
BINDCHECK_CIRCOM=/home/pollmix/Coding/bc/BindCheck/tools/circom-src/target/release/circom
python3 scripts/run_bindcheck_zk_full_dev.py --phase after --skip-fetch
  --analyze-jobs 3 --raw-task T24
  --checkout-root /home/pollmix/Coding/bc/BindCheck/feasibility/work/full-dev
```

The logical command completed with exit 0: 56 rows, 46 with triples, 0
crashes, 19 successful builds, and 57 failed builds. Evidence:
`results/raw/S2a/T24/after-20261118T023015Z-1613543/`.

The spent-family harness could not be rerun unchanged. Its one-shot Freeze-2
checkouts were intentionally removed by the prior harness; 277 retained family
evidence directories remain, but they are warning/evidence packets rather than
full checkouts. The task forbids network acquisition. Therefore no valid S2a
278-family ledger or recomputed Set H precision is claimed.

### Honk layout audit

- `results/raw/S2a/honk-layout-audit.json`: 89 generated Honk records (79
  unique retained sources) containing `NUMBER_OF_PUBLIC_INPUTS` were inspected.
- `results/raw/S2a/honk-import-audit.json`: all seven import-split wrappers in
  the retained packets resolve after the general import join (arity 19 for one
  FinCube wrapper; 19, 20, and 22 for six Puckapao normal/ZK wrappers).
- Payy DEV-H05 and DEV-H06 each recover eight effective arities:
  `agg_agg=33`, `agg_final=1003`, `agg_utxo=1005`, `migrate=0`, `mint=3`,
  `points=13`, `signature=2`, and `utxo=9`. The nonzero old-layout values each
  subtract 16 pairing-point words.
- The retained Semaphore-Noir verifier recovers arity 4.
- `python3 scripts/check_holdout.py warptoad/warp-toad` returned
  `FORBIDDEN ... reserved held-out v3 family ...` and exit 1. The repository
  was not opened, despite the task document describing WarpToad as DEV.

## Results (tables; exact counts)

### Original 56 DEV rows

Counts below include only applicable cells. Freeze-2 is the controlling
baseline at
`results/raw/coverage/after-20261109T165844Z-58315/per-row-ledger.json`.

| Pattern | Freeze-2 applicable | Freeze-2 V | Freeze-2 verified | Freeze-2 unknown | S2a applicable | S2a V | S2a verified | S2a unknown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| P1 | 17 | 6 | 0 | 11 | 17 | 6 | 0 | 11 |
| P2 | 27 | 0 | 0 | 27 | 27 | 0 | 0 | 27 |
| P3 | 23 | 6 | 7 | 10 | 23 | 6 | 7 | 10 |
| P4 | 46 | 6 | 16 | 24 | 46 | 6 | 15 | 25 |
| P5 | 46 | 0 | 4 | 42 | 46 | 0 | 3 | 43 |
| **All** | **159** | **18** | **27** | **114** | **159** | **18** | **25** | **116** |

Every changed original-DEV cell is listed below, including reason-only changes:

| Row/pattern | Freeze-2 → S2a | Reason |
| --- | --- | --- |
| DEV-F02 P5 | UNKNOWN → UNKNOWN | Added exact `VERIFIER_CALL_CORRESPONDENCE_UNRESOLVED` to the missing-circuit reason. |
| DEV-F06 P5 | UNKNOWN → UNKNOWN | Dynamic vector length and public order remain unresolved; ambiguity is no longer guessed. |
| DEV-F08 P5 | UNKNOWN → UNKNOWN | The specific call's public vector is unresolved; other verifier candidates do not certify it. |
| DEV-F10 P5 | UNKNOWN → UNKNOWN | The recovered Noir interface is incomplete, so meaning remains unresolved. |
| DEV-F11 P5 | UNKNOWN → UNKNOWN | The dynamic vector length is unresolved. |
| DEV-F12 P5 | VERIFIED_WITHIN_SCOPE → UNKNOWN | `Gaffine` is a user-defined Noir composite; its field flattening is not source-established. |
| DEV-F15 P4 | VERIFIED_WITHIN_SCOPE → UNKNOWN | Conflicting verifier-source evidence includes a missing canonicality guard; the aggregate now fails closed. |
| DEV-F33 P5 | UNKNOWN → UNKNOWN | The dynamic vector length is unresolved. |
| DEV-F45 P5 | UNKNOWN → UNKNOWN | Multiple verifier candidates remain ambiguous after call-specific selection. |

### Spent families (separate from original DEV)

The Freeze-2 run produced 277 family results; one of the predeclared 278 was
exposed/excluded before analysis. Applicable-cell baseline counts are shown for
context. S2a counts are deliberately `NOT_RECOMPUTED`.

| Pattern | Freeze-2 applicable | Freeze-2 V | Freeze-2 verified | Freeze-2 unknown among applicable | S2a |
| --- | ---: | ---: | ---: | ---: | --- |
| P1 | 63 | 17 | 2 | 44 | NOT_RECOMPUTED |
| P2 | 113 | 0 | 3 | 110 | NOT_RECOMPUTED |
| P3 | 86 | 33 | 19 | 34 | NOT_RECOMPUTED |
| P4 | 246 | 18 | 92 | 136 | NOT_RECOMPUTED |
| P5 | 246 | 38 | 2 | 206 | NOT_RECOMPUTED |

### Set H false-positive inventory

All 55 `final=FP` cards are accounted for. “Regression” below means a general
development fixture exercises the cause; it is not a substitute for the
unavailable full-card rerun.

| Tool/pattern | Cards | Root cause and responsible code path | Disposition |
| --- | --- | --- | --- |
| bindcheck-zk P1 | W0036 | Caller-funded `msg.value` treated as an unbound victim value; `analyzer.py::_caller_funded` / `analyze_p1`. | General fix + regression. |
| bindcheck-zk P1 | W0294 | Values selected from stored batch state were treated as caller-selected; `analyzer.py::_state_derived`. | General fail-closed fix + regression. |
| bindcheck-zk P1 | W0324 W0679 | Wrong verifier/circuit correspondence hid proof-bound identities; `analyzer.py::_verifier_correspondence` and `make_triples`. | Exact type/call correspondence fix + regression. |
| bindcheck-zk P1 | W0725 | A debit capped by and applied to `balances[msg.sender]` was treated as third-party spending; `analyzer.py::_self_balance_debit_bound`. | General fix + regression. |
| bindcheck-zk P1 | W0765 | A domain method named `transfer` was treated as an asset transfer; `solidity.py::effect_roles`. | Receiver-type asset check + regression. |
| bindcheck-zk P3 | W0007 W0153 W0618 W0724 | The exact generated verifier's all-position `checkField` scalar guard was not credited; `analyzer.py::_verifier_correspondence`, `p4.py::canonical_guard_positions`, and P3 analysis. | Exact correspondence/guard regression. |
| bindcheck-zk P3 | W0296 W0482 | Replay-key equality/copy into the verifier vector was lost through wrong vector/call selection; `solidity.py::public_vector` and `analyzer.py::make_triples`. | Call-specific vector regression. |
| bindcheck-zk P4 | W0102 | Wrapper inherited the checked verifier but the guard was not propagated; `analyzer.py::_propagate_inherited_verifier_guards`. | General inheritance fix + regression. |
| bindcheck-zk P4 | W0245 | Generated gnark Yul loop guarded every public input but was not recognized; `p4.py::canonical_guard_positions`. | Exact loop-shape fix + regression. |
| bindcheck-zk P4 | W0691 | CTF/write-up source was treated as application code; `analyzer.py::_semantic_excluded`. | General semantic exclusion + regression. |
| bindcheck-zk P5 | W0220 W0253 | The eight-word proof array was counted as public inputs; `solidity.py::public_vector`. | Proof-array rejection + regression. |
| bindcheck-zk P5 | W0016 W0333 W0349 W0430 W0728 | A different circuit/verifier, or the wrong array argument, supplied the count; `analyzer.py::_verifier_correspondence`, `make_triples`, and `solidity.py::public_vector`. | Exact receiver/ABI/call-vector fix + regression. |
| bindcheck-zk P5 | W0658 | Two verifier calls in one consumer shared the wrong public vector; `analyzer.py::make_triples`. | Per-call vector fix + regression. |
| bindcheck-zk P5 | W0461 W0619 | Circom public outputs or multidimensional output extent were omitted; `circuits.py::parse_circom`. | Output-first product flattening + regression. |
| bindcheck-zk P5 | W0662 | A Noir `Gaffine` composite was counted as one field; `circuits.py::parse_noir`. | Accepted fail-closed limitation: UNKNOWN until struct field layout is resolved. |
| bindcheck-zk P5 | W0672 W0776 | Old Honk totals included 16 pairing-point words not supplied by the external caller; `solidity.py::verifier_declarations`. | Explicit reserved-layout subtraction + regressions. |

Arm-C is a separate baseline implemented under `baselines/strong/`, outside
S2a's owned `bindcheck_zk/` paths. Its 27 FP cards are accepted S2a
limitations, not silently claimed as fixes:

| Arm-C kind | Cards | Root cause / responsible path |
| --- | --- | --- |
| A_CALL_VALUE_UNBOUND | W0227 W0360 | State-derived payout or caller-owned gas value; emitted in `solidity_scan.py` call-value logic. |
| A_EFFECT_AMOUNT_UNBOUND | W0008 W0138 W0175 W0378 W0409 | Proof-bound, fixed/state-derived, test-script, or no-proof timeout amounts; `solidity_scan.py` effect-role logic and `arm_c.py` suppression/composition. |
| A_EFFECT_IDENTITY_UNBOUND | W0597 | Unbound sender can affect only its own balance while recipient/amount are proof-bound; same effect-role path. |
| A_EFFECT_RECIPIENT_UNBOUND | W0118 W0293 W0306 W0536 W0686 | Recipient bound directly, by a proved hash, or by stored authorization; same effect-role path. |
| A_REPLAY_KEY_UNBOUND | W0149 W0235 W0285 W0287 W0334 W0442 W0454 W0505 W0593 W0601 | Replay key is the verified vector element/equality, or code is excluded/comment-only; `solidity_scan.py` replay scan and `arm_c.py` suppression. |
| A_STATE_WRITE_VALUE_UNBOUND | W0263 | Written fields are proved, mapped from proved values, or protocol state; effect-role path. |
| A_VERIFIER_ARITY_MISMATCH | W0722 | Correct two-input verifier arity was available from IC/signature evidence; Arm-C arity composition. |
| C_EFFECT_NOT_PROOF_BOUND | W0249 W0475 | Card lacked a captured source location; inspected consumers bind their effects, but the baseline warning is not target-specific; `arm_c.py` C-warning composition. |

Set H precision is therefore **not recomputed**. The Freeze-2 bindcheck-zk
values remain P1 9/15, P3 9/15, canonicality-P4 7/10, and P5 2/15. The new
regressions show both minimized P5 true-mismatch controls remain
`VIOLATION`, but the required 15-card P5 rerun was unavailable, so this report
does not claim that all 13 FP cards changed verdict.

## Assumptions and limitations

- No timeout, missing checkout, missing dependency, unsupported type, or
  unresolved correspondence was converted to `VERIFIED_WITHIN_SCOPE`.
- The original-DEV rerun is current for this candidate. The spent-family table
  is baseline-only; it cannot support a candidate precision claim.
- The retained warning packets are sufficient to audit generated Honk layout
  declarations, but not to reproduce the unchanged full-family analyzer run.
- WarpToad's current holdout classification overrides the task document's DEV
  wording. No WarpToad source was read.
- Honk arity/position count is implemented; Honk canonicality remains S2b.
- Noir user-defined public composites intentionally remain UNKNOWN.
- `docs/project-status.md` was not changed because the S2a task restricts
  outputs to its owned paths; the reviewer should update the living checkpoint
  after accepting/merging this partial task.

## Failed approaches / surprises

- The first Honk audit encountered an artifact directory whose name ended in
  `.sol`; it was rerun with an `is_file()` guard. No result from the failed run
  was used.
- Direct per-file parsing left seven newer wrappers unresolved because their
  constants live in imported key files. A general exact-import join fixed all
  seven retained cases.
- The prescribed aggregate test suite is not green in this worktree because
  the pinned circomlib tree is absent and the supplied Circom version differs
  from the required version.
- The prior one-shot spent-family harness removed its checkouts by design. A
  no-network task cannot reconstruct the 278-family rerun.

## Held-out hygiene statement (which families were read; confirm no unused EVAL family was opened)

Before opening any third-party repository, `python3 scripts/check_holdout.py
<owner/repo>` was run. All 56 original DEV rows and every repository
represented by the 278 predeclared spent families returned `ALLOWED`; logs are
`results/raw/S2a/original-dev-holdout-checks.txt` and
`results/raw/S2a/spent-family-holdout-checks.txt`. Set H's 44 distinct
repositories were likewise checked before source inspection. WarpToad returned
`FORBIDDEN` and was not opened. No unused EVAL/held-out-v3 family was opened,
cloned, built, or analyzed. All work was local and offline; no transaction was
broadcast and no live system or maintainer was contacted.

## Recommended next task (one, with a measurable completion criterion)

Reviewer task: in an authorized environment that has the pinned Linux Circom
2.1.9, pinned circomlib tree, and restored 278 spent-family checkouts, rerun the
unchanged aggregate suite and full spent ledger. Accept the candidate only if
all tests pass, all 278 rows receive an accounted status, every changed verdict
has a ledger reason, the 13 P5 FP cards are no longer `VIOLATION`, and both P5
TP cards remain `VIOLATION`.
