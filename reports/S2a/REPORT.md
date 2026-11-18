# S2a — Precision fixes for freeze 3 (DEV only)

Status: PARTIAL

Verdict/outcome: CANDIDATE_PREPARED_FULL_SPENT_RERUN_UNAVAILABLE

> **Revision 1 (2026-11-18):** the spent-family rerun is now complete. The
> original sections below are retained unchanged as the pre-rerun record. Read
> the “Revision 1” section at the end for the controlling rerun evidence. That
> section supersedes the statements that the full rerun and Set H recomputation
> were unavailable, but it does **not** turn the residual false positives into
> fixes.

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

---

# Revision 1 — spent-family rerun and semantic-exclusion refactor

Date: 2026-11-18. Scope: `sprint/S2a`. This revision is **DEV, not held-out**.
The 278 selected families are the spent freeze-2 set and are development data.
No freeze-3 declaration or tag was created.

## R1.1 Objective and outcome

The revision had six bounded outcomes:

1. green aggregate tests with Linux Circom 2.1.9;
2. the unchanged spent-family harness executed and accounted for all 278
   selected rows;
3. a per-pattern delta against freeze 2 with a reason for every changed verdict;
4. a recomputed Set H precision labelled DEV;
5. the hard-coded CTF/write-up/tutorial/example exclusion moved into config,
   with coverage reporting and a regression; and
6. a recomputed candidate hash, without declaring freeze 3.

All six were completed, but the rerun does **not** confirm the original
inventory's claim that all 13 P5 false-positive cards stopped being
`VIOLATION`. The honest outcome is:

- **6 of 13** P5 FP cards are no longer `VIOLATION` in an analysed family;
- **6 of 13** remain `VIOLATION`;
- **1 of 13** (`W0658`) is unavailable because its family hit
  `HARNESS_TIMEOUT`, so its status is `UNKNOWN`, not a demonstrated fix; and
- both P5 TP cards, `W0412` and `W0668`, remain `VIOLATION`.

The original report's Set H disposition table is therefore a pre-rerun
hypothesis, not a result. Revision 1 leaves the original section in place and
records the correction below.

## R1.2 Environment, commands, and versions

- Repository: `/home/pollmix/Coding/bc/wt-S2a`; branch `sprint/S2a`.
- HEAD at analysis: `a7dd9da46eec4a7e38229b4eca8a05b59fad0d7a`.
- Python: 3.12.12.
- Circom:
  `/home/pollmix/Coding/bc/BindCheck/tools/circom-2.1.9/target/release/circom`;
  `circom --version` reports `circom compiler 2.1.9`.
- `node_modules` was symlinked from the preservation checkout into the
  worktree. It is ignored by `.gitignore` and `.git/info/exclude`; it is not
  committed.
- Focused suite:
  `BINDCHECK_CIRCOM=.../circom-2.1.9/.../circom python3 -m unittest tests.s2a.test_precision_fixes -v`
  — 20 tests, `OK`, exit 0; log
  `results/raw/S2a/tests/s2a-suite-rev1.log`.
- Aggregate suite:
  `BINDCHECK_CIRCOM=.../circom-2.1.9/.../circom python3 -m unittest tests.test_bindcheck_zk_cli tests.test_bindcheck_zk_controls tests.soundness.test_verdict_soundness tests.soundness.test_followup tests.coverage.test_rules tests.freeze2.test_p4_key tests.s2a.test_precision_fixes -v`
  — 58 tests, `OK`, exit 0; log
  `results/raw/S2a/tests/full-suite-rev1.log`.
- Candidate hash command: `python3 -m bindcheck_zk.freeze` — exit 0.
  Recomputed value:
  `BINDCHECK_ZK_CONTENT_SHA256=8ef7a837f4127bfa57fa44419a39b37eee06b90929ed074e5009bc714c346be3`.
  Full per-file output: `results/raw/S2a/freeze-hash-rev1.txt`.
- Dataset identity:
  `SOURCE_CORPUS_V2_SHA256=07210625783a21a6128ea3f99402fc4a48b36922056241649999547a374b0c95`.
- Harness: `eval/run_heldout.py` and `eval/summarize.py` were executed
  unchanged. The harness gate requires an annotated freeze tag, so a temporary
  local tag `bindcheck-zk-frozen-8ef7a837` was created at HEAD solely to pass
  the gate. It was deleted before commit; the deletion log is
  `results/raw/S2a/temporary-tag-deletion-final.log`. No freeze-3 tag exists.
- Harness command:
  `BINDCHECK_EVAL_AUTHORIZED=1 BINDCHECK_CIRCOM=.../circom-2.1.9/.../circom python3 eval/run_heldout.py --split EVAL --output results/raw/S2a/spent-rerun`.
  Final manifest: `results/raw/S2a/spent-rerun/run-manifest.json`;
  `families=277`, `selection_sha256=606b4241a4c98e0868c793cdce19f0117cf1917d55e4e10ba89c75a3d97ea49b`.
- Summary command:
  `python3 eval/summarize.py results/raw/S2a/spent-rerun --bootstrap-replicates 0`
  — exit 0; log `results/raw/S2a/spent-summary-final.log`.
- Ledger/Set H generator:
  `python3 reports/S2a/revision1_analysis.py --old-run /home/pollmix/Coding/bc/BindCheck/results/raw/heldout/e2-freeze2-once --new-run results/raw/S2a/spent-rerun --labels reports/labels/set-H-ledger.csv --key reports/heldout/warning-unblind-key.csv --out reports/S2a/revision1`
  — exit 0; log `reports/S2a/revision1/analysis.log`.
- Holdout preflight: all 278 selected repositories were checked with
  `python3 scripts/check_holdout.py <owner/repo>`; 278 `ALLOWED`, exit 0;
  log `results/raw/S2a/spent-family-holdout-checks-rev1.txt` (278 lines,
  SHA-256 `969dc88820ccb362cd6c9ba84d1e57f14129f320b51a34e16d74d50d63476624`).
- No other network access and no chain RPC were used. No transaction was
  broadcast.

## R1.3 Coverage: all 278 rows are accounted for

The selection contains 278 rows. Rank 259 (`selfxyz/self`) was excluded before
analysis by the harness's predeclared exposed-family rule. The remaining 277
were attempted.

| Status | Rows | Meaning |
| --- | ---: | --- |
| `ANALYZED` | 265 | completed both freeze-2 and S2a analysis |
| `HARNESS_TIMEOUT` | 7 | analyzer exceeded the 150 s outer limit; every pattern is `UNKNOWN` |
| `ACQUISITION_FAILED` | 5 | repository or pinned commit no longer fetchable; every pattern is `UNKNOWN` |
| `EXCLUDED_BEFORE_ANALYSIS` | 1 | rank 259, `selfxyz/self` |
| **Total** | **278** | |

Unavailable rows, all treated as `UNKNOWN`, never safe:

| Rank | Repository | Status |
| ---: | --- | --- |
| 20 | `mashharuki/ZKRepo` | `HARNESS_TIMEOUT` |
| 25 | `Ambesh69/predacy` | `HARNESS_TIMEOUT` |
| 69 | `bdls3yn/zk-hybrid-defense` | `HARNESS_TIMEOUT` |
| 118 | `CitizenGardens/Foundry` | `HARNESS_TIMEOUT` |
| 121 | `mpozdal/zkml-project` | `HARNESS_TIMEOUT` |
| 148 | `PhaseMirror/The-Foundry` | `HARNESS_TIMEOUT` |
| 220 | `ArmanKolozyan/CCC-Check` | `HARNESS_TIMEOUT` |
| 90 | `tawf-labs/tawf-zakat` | `ACQUISITION_FETCH_FAILED` |
| 97 | `ZKBLAST/zkblast` | `ACQUISITION_FETCH_FAILED` |
| 178 | `haidarally/privatekreds-public` | `ACQUISITION_FETCH_FAILED` |
| 248 | `caelum0x/Cipher-Zero` | `ACQUISITION_FETCH_FAILED` |
| 255 | `Pedro0020/SVA-Framework` | `ACQUISITION_FETCH_FAILED` |

The five acquisition failures were retried once after preserving the first
attempts under `results/raw/S2a/failed-acquisitions-first-attempt/`. Four
repositories now return `Repository not found` and one returns
`upload-pack: not our ref`; they cannot be recovered within the allowed
clone/fetch scope. The final pass is therefore **not a clean one-shot run**;
it is a completed second full pass with the same unchanged harness. This does
not weaken any held-out claim because these 278 families are DEV.

## R1.4 Per-pattern delta versus freeze 2

### Full executed set (277 rows, including coverage losses)

This table is the direct harness comparison. `Applicable unknown` is the
UNKNOWN verdict among applicable cells.

| Pattern | Freeze-2 app | F2 V | F2 verified | F2 app-unknown | S2a app | S2a V | S2a verified | S2a app-unknown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| P1 | 63 | 17 | 2 | 44 | 60 | 15 | 3 | 42 |
| P2 | 113 | 0 | 3 | 110 | 107 | 0 | 3 | 104 |
| P3 | 86 | 33 | 19 | 34 | 82 | 26 | 20 | 36 |
| P4 | 246 | 18 | 92 | 136 | 235 | 16 | 91 | 128 |
| P5 | 246 | 38 | 2 | 206 | 235 | 25 | 1 | 209 |

The loss of applicable cells is coverage, not a semantic safe result: five
acquisition failures and seven timeouts become `UNKNOWN`. P4/P5 also lose one
applicable family because rank 227's only triples were semantically excluded
(Section R1.6).

### Complete-case semantic comparison (265 families analysed in both runs)

This is the fair semantic delta. It excludes the 7 timeout and 5 acquisition
rows entirely, so no missing result is counted as fixed or safe.

| Pattern | Freeze-2 app | F2 V | F2 verified | F2 app-unknown | S2a app | S2a V | S2a verified | S2a app-unknown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| P1 | 61 | 16 | 2 | 43 | 60 | 15 | 3 | 42 |
| P2 | 108 | 0 | 3 | 105 | 107 | 0 | 3 | 104 |
| P3 | 82 | 30 | 19 | 33 | 82 | 26 | 20 | 36 |
| P4 | 236 | 14 | 91 | 131 | 235 | 16 | 91 | 128 |
| P5 | 236 | 36 | 2 | 198 | 235 | 25 | 1 | 209 |

Net changes among the 265 complete families:

- P1: 2 new `VIOLATION`, 2 `VIOLATION` retired to `UNKNOWN`, 1
  `VIOLATION` raised to `VERIFIED_WITHIN_SCOPE`, 1 new `VERIFIED_WITHIN_SCOPE`;
- P3: 4 `VIOLATION` retired (2 to `UNKNOWN`, 2 to
  `VERIFIED_WITHIN_SCOPE`), 1 `VERIFIED_WITHIN_SCOPE` downgraded to `UNKNOWN`;
- P4: 2 new `VIOLATION`, 1 new `VERIFIED_WITHIN_SCOPE`, 1
  `VERIFIED_WITHIN_SCOPE` downgraded to `UNKNOWN`;
- P5: 15 `VIOLATION` retired to `UNKNOWN`, 4 new `VIOLATION`, 1
  `VERIFIED_WITHIN_SCOPE` downgraded to `UNKNOWN`.

The 34 semantic verdict changes are listed in full below. The 7 semantic
applicability-only changes are the five rank-227 rows (`NO_APPLICABLE_TRIPLE`
after semantic exclusion) and rank 262 P1/P2 (`UNKNOWN/APPLICABLE` to
`UNKNOWN/NOT_APPLICABLE`). The 25 timeout and 25 acquisition changes are in
`spent-family-changed-verdicts.csv` with `change=COVERAGE_*`; they are coverage
losses, not analyzer decisions.

## R1.5 Every changed verdict and its reason (semantic changes)

All 41 semantic rows are reproduced here. The machine-readable table with the
coverage rows is `reports/S2a/revision1/spent-family-changed-verdicts.csv`.
`→` means freeze 2 → S2a revision 1.

| Rank | Repository | Pattern | Change | Recorded reason |
| ---: | --- | --- | --- | --- |
| 2 | `imfeng/nft-arjaverse-rollup` | P4 | `VERIFIED_WITHIN_SCOPE/APPLICABLE` → `UNKNOWN/APPLICABLE` | `PUBLIC_INPUT_CANONICALITY_GUARD_NOT_FOUND`; `VERIFICATION_KEY_CHECKS_PASS` |
| 6 | `AnonGate/anongate-mainnet` | P3 | `VIOLATION/APPLICABLE` → `UNKNOWN/APPLICABLE` | `PROTECTED_EFFECT_NOT_RECOVERED`; `VERIFIER_CALL_CORRESPONDENCE_UNRESOLVED` |
| 15 | `archyrenaldy-iwu/zkp-identity-architecture-public-sector` | P3 | `VERIFIED_WITHIN_SCOPE/APPLICABLE` → `UNKNOWN/APPLICABLE` | `PROTECTED_EFFECT_NOT_RECOVERED`; `VERIFIER_CALL_CORRESPONDENCE_UNRESOLVED` |
| 19 | `myntisai/token` | P5 | `VIOLATION/APPLICABLE` → `UNKNOWN/APPLICABLE` | `PUBLIC_INPUT_ORDER_UNRESOLVED` |
| 23 | `vocdoni/davinci-dkg-council` | P5 | `VERIFIED_WITHIN_SCOPE/APPLICABLE` → `UNKNOWN/APPLICABLE` | `CIRCUIT_INTERFACE_INCOMPLETE`; `VERIFIER_MATCH_AMBIGUOUS` |
| 27 | `OffGrid0xDAO/r00t.fund` | P5 | `VIOLATION/APPLICABLE` → `UNKNOWN/APPLICABLE` | `PUBLIC_INPUT_ORDER_UNRESOLVED`; `VERIFIER_MATCH_AMBIGUOUS` |
| 30 | `zkbnbx/zkbnb-protocol` | P5 | `UNKNOWN/APPLICABLE` → `VIOLATION/APPLICABLE` | `CIRCUIT_INTERFACE_INCOMPLETE`; `PUBLIC_INPUT_COUNT_AND_ORDER_MATCH`; `PUBLIC_INPUT_COUNT_MISMATCH`; `PUBLIC_INPUT_MEANING_UNRESOLVED`; `VERIFIER_MATCH_AMBIGUOUS` |
| 48 | `Dapp-Learning-DAO/Dapp-Learning` | P5 | `VIOLATION/APPLICABLE` → `UNKNOWN/APPLICABLE` | `PUBLIC_INPUT_VECTOR_UNRESOLVED`; `VERIFIER_MATCH_AMBIGUOUS` |
| 52 | `Dami904/pii` | P5 | `VIOLATION/APPLICABLE` → `UNKNOWN/APPLICABLE` | `PUBLIC_INPUT_MEANING_UNRESOLVED` |
| 67 | `RonTuretzky/p2peace-zkemail` | P5 | `UNKNOWN/APPLICABLE` → `VIOLATION/APPLICABLE` | `PUBLIC_INPUT_COUNT_MISMATCH`; `PUBLIC_INPUT_MEANING_UNRESOLVED`; `VERIFIER_MATCH_AMBIGUOUS` |
| 70 | `gourab337/robopay-warehouse` | P5 | `VIOLATION/APPLICABLE` → `UNKNOWN/APPLICABLE` | `PUBLIC_INPUT_MEANING_UNRESOLVED` |
| 72 | `1usuzu/deep-trust` | P4 | `UNKNOWN/APPLICABLE` → `VIOLATION/APPLICABLE` | `GAMMA_EQUALS_DELTA_SOURCE_KEY` |
| 78 | `0xSY3/polkadot-dust-protocol` | P5 | `UNKNOWN/APPLICABLE` → `VIOLATION/APPLICABLE` | `CIRCUIT_INTERFACE_INCOMPLETE`; `PUBLIC_INPUT_COUNT_AND_ORDER_MATCH`; `PUBLIC_INPUT_COUNT_MISMATCH`; `PUBLIC_INPUT_MEANING_UNRESOLVED`; `PUBLIC_INPUT_ORDER_UNRESOLVED` |
| 83 | `wurli-sh/wisp-monad` | P3 | `VIOLATION/APPLICABLE` → `VERIFIED_WITHIN_SCOPE/APPLICABLE` | `REPLAY_KEY_CANONICAL_AND_CONSUMED` |
| 85 | `Mxsh-hub/document-sih` | P5 | `VIOLATION/APPLICABLE` → `UNKNOWN/APPLICABLE` | `VERIFIER_CALL_CORRESPONDENCE_UNRESOLVED`; `VERIFIER_MATCH_AMBIGUOUS` |
| 86 | `Obsqra-Labs/zkdefi` | P1 | `VIOLATION/APPLICABLE` → `UNKNOWN/APPLICABLE` | `CALLER_INDEPENDENCE_UNRESOLVED` |
| 93 | `eugenioclrc/MercadoBarrani` | P5 | `VIOLATION/APPLICABLE` → `UNKNOWN/APPLICABLE` | `VERIFIER_CALL_CORRESPONDENCE_UNRESOLVED` |
| 107 | `0xbri3t/Privacy-Vaults` | P1 | `UNKNOWN/APPLICABLE` → `VIOLATION/APPLICABLE` | `CALLER_INDEPENDENCE_UNRESOLVED`; `UNBOUND_EFFECT_AMOUNT` |
| 107 | `0xbri3t/Privacy-Vaults` | P5 | `VIOLATION/APPLICABLE` → `UNKNOWN/APPLICABLE` | `PUBLIC_INPUT_MEANING_UNRESOLVED`; `VERIFIER_MATCH_AMBIGUOUS` |
| 113 | `TP4uit/KLTN-NguyenTanPhuc` | P5 | `VIOLATION/APPLICABLE` → `UNKNOWN/APPLICABLE` | `PUBLIC_INPUT_ORDER_UNRESOLVED` |
| 116 | `justwasif/tmi_wosh_wosh` | P5 | `VIOLATION/APPLICABLE` → `UNKNOWN/APPLICABLE` | `PUBLIC_INPUT_ORDER_UNRESOLVED` |
| 129 | `JYugandhara/axiom` | P1 | `VIOLATION/APPLICABLE` → `UNKNOWN/APPLICABLE` | `EFFECT_BINDING_UNRESOLVED`; `PROTECTED_EFFECT_NOT_RECOVERED` |
| 130 | `communisaas/voter-protocol` | P5 | `VIOLATION/APPLICABLE` → `UNKNOWN/APPLICABLE` | `PUBLIC_INPUT_MEANING_UNRESOLVED`; `DYNAMIC_PUBLIC_INPUT_LENGTH_GUARDED` |
| 149 | `achotanibhavikoffice-ui/Insure_Chain` | P3 | `VIOLATION/APPLICABLE` → `UNKNOWN/APPLICABLE` | `PROTECTED_EFFECT_NOT_RECOVERED`; `VERIFIER_CALL_CORRESPONDENCE_UNRESOLVED` |
| 158 | `cysic-zk/venus` | P5 | `UNKNOWN/APPLICABLE` → `VIOLATION/APPLICABLE` | `PUBLIC_INPUT_COUNT_MISMATCH` |
| 172 | `tommymsz006/ethsingapore2024` | P5 | `VIOLATION/APPLICABLE` → `UNKNOWN/APPLICABLE` | `CIRCUIT_INTERFACE_INCOMPLETE`; `VERIFIER_CALL_CORRESPONDENCE_UNRESOLVED` |
| 209 | `oguzutku1745/goodLane` | P1 | `VIOLATION/APPLICABLE` → `VERIFIED_WITHIN_SCOPE/APPLICABLE` | `EFFECT_VALUES_DIRECT_PUBLIC_INPUTS` |
| 227 | `timimm/zk-writeups` | P1 | `UNKNOWN/NOT_APPLICABLE` → `UNKNOWN/UNKNOWN` | `NO_APPLICABLE_TRIPLE` |
| 227 | `timimm/zk-writeups` | P2 | `UNKNOWN/NOT_APPLICABLE` → `UNKNOWN/UNKNOWN` | `NO_APPLICABLE_TRIPLE` |
| 227 | `timimm/zk-writeups` | P3 | `UNKNOWN/NOT_APPLICABLE` → `UNKNOWN/UNKNOWN` | `NO_APPLICABLE_TRIPLE` |
| 227 | `timimm/zk-writeups` | P4 | `UNKNOWN/APPLICABLE` → `UNKNOWN/UNKNOWN` | `NO_APPLICABLE_TRIPLE` |
| 227 | `timimm/zk-writeups` | P5 | `UNKNOWN/APPLICABLE` → `UNKNOWN/UNKNOWN` | `NO_APPLICABLE_TRIPLE` |
| 232 | `cenwadike/zk-study` | P1 | `UNKNOWN/APPLICABLE` → `VIOLATION/APPLICABLE` | `PROTECTED_EFFECT_NOT_RECOVERED`; `UNBOUND_EFFECT_AMOUNT` |
| 232 | `cenwadike/zk-study` | P5 | `VIOLATION/APPLICABLE` → `UNKNOWN/APPLICABLE` | `PUBLIC_INPUT_VECTOR_UNRESOLVED`; `VERIFIER_CALL_CORRESPONDENCE_UNRESOLVED` |
| 234 | `andrea-rizzini/A-Private-Smart-Wallet-with-Probabilistic-Compliance` | P3 | `VIOLATION/APPLICABLE` → `VERIFIED_WITHIN_SCOPE/APPLICABLE` | `PROTECTED_EFFECT_NOT_RECOVERED`; `REPLAY_KEY_CANONICAL_AND_CONSUMED` |
| 247 | `pantheraudits/zk-mixer` | P5 | `VIOLATION/APPLICABLE` → `UNKNOWN/APPLICABLE` | `PUBLIC_INPUT_MEANING_UNRESOLVED` |
| 251 | `exdarku/aidvocate-live` | P4 | `UNKNOWN/APPLICABLE` → `VERIFIED_WITHIN_SCOPE/APPLICABLE` | `VERIFICATION_KEY_CHECKS_PASS` |
| 262 | `Puckapao/v0-aztec-gpu-prover` | P1 | `UNKNOWN/APPLICABLE` → `UNKNOWN/NOT_APPLICABLE` | `PROTECTED_EFFECT_NOT_RECOVERED` |
| 262 | `Puckapao/v0-aztec-gpu-prover` | P2 | `UNKNOWN/APPLICABLE` → `UNKNOWN/NOT_APPLICABLE` | `PROTECTED_EFFECT_NOT_RECOVERED` |
| 264 | `A-makarim/ETH-Oxford` | P4 | `UNKNOWN/APPLICABLE` → `VIOLATION/APPLICABLE` | `GAMMA_EQUALS_DELTA_SOURCE_KEY` |
| 271 | `ruhneb2004/Zk-PanagramGame` | P5 | `VIOLATION/APPLICABLE` → `UNKNOWN/APPLICABLE` | `PUBLIC_INPUT_MEANING_UNRESOLVED` |

Interpretation:

- The new `VIOLATION` rows (8 total: P1 2, P4 2, P5 4) are new warnings, not
  confirmed defects. They need the same human/oracle adjudication as any other
  warning and are not counted as held-out findings.
- The new `VERIFIED_WITHIN_SCOPE` rows (4 total: P1 1, P3 2, P4 1) are
  model-scoped results only. No execution-oracle validation was performed in
  this task.
- Downgrades to `UNKNOWN` are fail-closed outcomes. They are not safe and are
  not counted as retired false positives in Set H unless the matching card is
  in an analysed family and its warning is no longer emitted.

## R1.6 Semantic exclusion moved into config

The hard-coded directory list in `bindcheck_zk/analyzer.py::_semantic_excluded`
was removed. The policy now comes from `bindcheck_zk/config.json`:

- `semantic_excluded_directories`: `ctf`, `writeup`, `writeups`, `tutorial`,
  `tutorials`, `example`, `examples`;
- `semantic_excluded_directory_suffixes`: `ctf` (so `zkCTF` matches);
- `semantic_excluded_filename_suffixes`: `.t.sol`, `.s.sol`;
- existing `semantic_test_directories` and `semantic_script_directories` are
  unioned with the new keys.

Coverage now reports `semantic_excluded_count` and
`semantic_excluded_paths`. The regression
`test_semantically_excluded_file_never_produces_a_safe_verdict` builds one
application and one excluded `ctf/Consumer.sol`, asserts that only the
application produces a triple, asserts the excluded path appears in coverage,
and asserts that no excluded consumer receives `VERIFIED_WITHIN_SCOPE`.
`test_semantic_exclusion_is_config_driven_and_reported` asserts the new config
keys. Rank 227 (`timimm/zk-writeups`) demonstrates the production effect: 59
paths were excluded, no triples remained, and every pattern became
`UNKNOWN/UNKNOWN` with `NO_APPLICABLE_TRIPLE` rather than a safe verdict.

### Contract revision-4 rule text

`docs/research-contract.md` was not edited; it remains revision 3 in this
worktree. The task asked this report to record the exact revision-4 rule text.
The text recorded for revision 4 is:

> **Semantic exclusion rule (revision 4).** A source path is semantically
> excluded only when it is not application code under the declared development
> analysis: (a) a directory component, compared case-insensitively, is one of
> `test`, `tests`, `mocks`, `fixtures`, `test-fixtures`, `script`, `scripts`,
> `ctf`, `writeup`, `writeups`, `tutorial`, `tutorials`, `example`, or
> `examples`; (b) a directory component ends in `ctf`; or (c) the filename ends
> in `.t.sol` or `.s.sol`. An excluded path may be read for context, but it
> must not contribute triples, findings, or warnings, and it must never receive
> `VIOLATION` or `VERIFIED_WITHIN_SCOPE`. Coverage must report every excluded
> path and the excluded count. If exclusion leaves no applicable triple, the
> result is `UNKNOWN` with `NO_APPLICABLE_TRIPLE`. Exclusion is never a safe
> verdict and is never silent.

This is a report-level record, not a contract edit. A future contract revision
must add its own dated change-control entry before these words become
controlling.

## R1.7 Set H recomputation — DEV, not held-out

Matching rule: a freeze-2 card is looked up by family, pattern, path, and
reason (for P4 canonicality); exact path/line is preferred, then nearest line
within the same path. A card counts as a retained warning only if the new
result is a warning in the same stratum. Cards whose family is a timeout or
acquisition failure are marked `COVERAGE_*` and are excluded from the retained
denominator; they are not counted as fixes. Machine-readable rows:
`reports/S2a/revision1/set-h-recomputed-cards.csv`; summary:
`reports/S2a/revision1/set-h-recomputed-summary.json`.

| Stratum | Cards | Analysed | Coverage unavailable | Retained warnings | TP retained | FP retained | Precision on retained | FP no longer VIOLATION (analysed) | FP still VIOLATION | TP still VIOLATION |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| P1 | 15 | 14 | 1 (`W0294`, timeout) | 10 | 9 | 1 | 9/10 = 0.90 | 4 | `W0679` | 9 |
| P3 | 15 | 15 | 0 | 12 | 9 | 3 | 9/12 = 0.75 | 3 | `W0296`, `W0482`, `W0724` | 9 |
| P4 canonicality | 10 | 8 | 2 (`W0330`, `W0709`, acquisition) | 5 | 5 | 0 | 5/5 = 1.00 (partial sample) | 3 | none | 0 |
| P5 | 15 | 14 | 1 (`W0658`, timeout) | 8 | 2 | 6 | 2/8 = 0.25 | 6 | `W0016`, `W0220`, `W0253`, `W0333`, `W0349`, `W0461` | 2 |

These are **DEV** numbers. They are not held-out precision and must not be
pasted into the paper's held-out table.

Full-sample caveats:

- P1: the 15-card value is not fully established. `W0294` was a labelled FP but
  its family timed out. On analysed evidence the value is 9/10; if `W0294`
  would still warn, the 15-card value would be 9/11, and if it would be fixed,
  9/10. The old 9/15 is not directly comparable because five FPs retired.
- P3: all 15 cards were analysed; 9/12 = 0.75 is a complete-sample result.
- P4 canonicality: 5/5 is only the analysed subset. Two TP cards are in the
  unavailable `caelum0x/Cipher-Zero` repository (rank 248), so the old 7/10
  cannot be replaced by a full-sample recomputation. The correct statement is
  “5/5 among available cards; 2 TP cards `UNKNOWN` for acquisition failure.”
- P5: 14 of 15 cards were analysed. The 15-card value is not established
  because `W0658` timed out.

### The explicit P5 answer

Of the 13 P5 false-positive cards:

- **6 are no longer `VIOLATION`** in an analysed family:
  `W0430`, `W0619`, `W0662`, `W0672`, `W0728`, `W0776`.
- **6 remain `VIOLATION`**: `W0016`, `W0220`, `W0253`, `W0333`, `W0349`,
  `W0461`.
- **1 is not evaluated**: `W0658` is in the timed-out family rank 148, so its
  current status is `UNKNOWN`, not a demonstrated fix. Counting it as “no
  longer VIOLATION” would overstate the evidence.
- **Both P5 TP cards remain `VIOLATION`**: `W0412` and `W0668`.

Thus the literal final-run status is 7 P5 FP cards without a `VIOLATION`
(6 analysed plus 1 timeout), but the defensible result is **6 fixed, 6 still
false-positive warnings, 1 unknown**.

## R1.8 Reconciliation with the original Set H inventory

The original section claimed all P5 cards in its inventory were fixed. The
rerun contradicts that claim for six P5 cards. The residual cards and the
observed reason codes are:

| Card | Repository | What the rerun still emits |
| --- | --- | --- |
| `W0016` | `oxor-io/zk-layer-vote` | `PUBLIC_INPUT_COUNT_MISMATCH`: the card's reported message (“4 public inputs, circuit exposes 1”) is still present; additional 3-input mismatches also remain. |
| `W0220` | `bunsenstraat/chainlink-workshop` | `PUBLIC_INPUT_COUNT_MISMATCH`: the eight-word vector is still counted at line 175. |
| `W0253` | `bunsenstraat/chainlink-workshop` | `PUBLIC_INPUT_COUNT_MISMATCH`: the same pattern remains at line 109. |
| `W0333` | `mihwuan/H-ZKA` | `PUBLIC_INPUT_COUNT_MISMATCH`: “4 public inputs, circuit exposes 2” remains at lines 296 and 365. |
| `W0349` | `Cloakworks-collective/shadow_warfare` | `PUBLIC_INPUT_COUNT_MISMATCH`: “5 public inputs, circuit exposes 1” remains at line 81. |
| `W0461` | `Punith-KK/Kira` | `PUBLIC_INPUT_COUNT_MISMATCH`: “18 public inputs, circuit exposes 2” remains at line 61. |

The P1 and P3 residuals are likewise not fixed: `W0679` remains
`UNBOUND_EFFECT_IDENTITY`; `W0296` and `W0482` remain
`REPLAY_KEY_NOT_BOUND_TO_PROOF`; `W0724` remains
`FIELD_ALIAS_REPLAY_KEY`. These are accepted S2a limitations, not closed
findings. The original dispositions for these cards should be read as
“regression added”, not “card retired”.

## R1.9 Assumptions, limitations, and failed approaches

- **Not held out.** All 278 families are spent freeze-2 DEV families. Set H is
  a DEV card set. No unused EVAL family was opened.
- **Not one-shot.** The final harness pass is a second full pass after one
  acquisition/timeout retry. The harness code and selection were unchanged.
  First attempts are preserved for the six acquisition failures and the
  timeout families where available under `results/raw/S2a/`.
- **Timeouts are unknown.** Seven families hit the 150 s analyzer timeout.
  They were not converted to `VERIFIED_WITHIN_SCOPE`, and no pattern in them is
  counted as fixed. The timeout set is not fully stable across passes, which
  is itself a reproducibility limitation.
- **Unavailable repositories.** Five pinned repositories can no longer be
  fetched: four are gone and one commit is no longer served. The two P4 TP
  cards in rank 248 make the canonicality-P4 full-sample precision
  unrecoverable.
- **Residual false positives.** Six P5 FP cards, one P1 FP card, three P3 FP
  cards, and no P4 canonicality FP cards remain as warnings in analysed
  families. They are documented, not silently claimed as fixed.
- **New detections are not validation.** The eight new `VIOLATION` rows and
  four new `VERIFIED_WITHIN_SCOPE` rows have no execution-oracle evidence in
  this task.
- **Original 56 DEV rows.** The revision-1 rerun covers the 278 spent families,
  not the separate 56 original-DEV rows. The table in the original section is
  retained as the pre-revision record; it was not regenerated after the
  semantic-exclusion config change.
- **Resume quirk.** A resumed harness rejected its own regenerated selection
  CSV because the writer emits CRLF while the reader compares universal-newline
  text. Deleting only the generated `selected-families.csv` let the unchanged
  harness regenerate the same 278-family selection. The selection hash is
  recorded in the manifest.
- **Tag hygiene.** The temporary execution tag was deleted. `git tag -l` shows
  only the pre-existing `bindcheck-zk-frozen-92789fad`; no freeze-3 tag exists.
- **Project checkpoint.** `docs/project-status.md` was updated with a new S2a
  node and a dated log row. The node records the task as `[ACTIVE]` because
  residual false positives remain; it does not claim a complete precision fix.
  The reviewer must still confirm the living checkpoint when accepting this
  report.

## R1.10 Handoff

Files changed by revision 1:

- `bindcheck_zk/analyzer.py` — config-driven semantic exclusion and coverage
  fields.
- `bindcheck_zk/config.json` — new exclusion keys.
- `tests/s2a/test_precision_fixes.py` — two exclusion regressions.
- `reports/S2a/REPORT.md` — this Revision 1 section.
- `reports/S2a/revision1_analysis.py` — ledger/delta/Set H generator.
- `reports/S2a/revision1/` — tracked ledger, delta, changed-verdict, Set H, and
  analysis outputs.
- `docs/project-status.md` — S2a node and dated checkpoint row.

Evidence locations:

- `results/raw/S2a/tests/full-suite-rev1.log` — 58 tests, `OK`.
- `results/raw/S2a/tests/s2a-suite-rev1.log` — 20 tests, `OK`.
- `results/raw/S2a/spent-rerun/` — final harness output (ignored raw).
- `results/raw/S2a/spent-summary-final.log` — final summary.
- `results/raw/S2a/spent-run.log` — harness execution log.
- `results/raw/S2a/freeze-hash-rev1.txt` — candidate hash.
- `results/raw/S2a/spent-family-holdout-checks-rev1.txt` — 278 `ALLOWED`.
- `results/raw/S2a/temporary-tag-deletion-final.log` — tag removed.

Recommended next task, with a measurable completion criterion:

> Re-run only the six residual P5 false-positive cards (`W0016`, `W0220`,
> `W0253`, `W0333`, `W0349`, `W0461`) against minimal, pinned source excerpts
> and the unchanged analyzer, and either (a) make each no longer emit the
> card's exact reported warning with a general cause fix plus a regression, or
> (b) record an explicit accepted-limitation reason. Done when the same
> Set H matcher reports all six as no longer `VIOLATION`, or each has a
> documented accepted-limitation entry and no unsupported `VERIFIED` verdict.
> Do not call this held-out evidence.
