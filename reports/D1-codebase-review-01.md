# D1 codebase review 01

Date: 23 October 2026. **Software review completed with a legacy dependency
blocker. Current hardened guard artifact prerequisite DONE; overall D1-03
UNKNOWN/incomplete and D1-04 WAITING.**

## Objective, authorization and limits

The user requested: “Push it. check and verify the current codebase and push
again.” The initial push creates `origin/chatgpt-codex` at inherited commit
`1b4d5683d87cd8f71b37e140d0b99c9fd21b856f`. The current folder is independently
managed with its own `.git`, index and objects, as recorded by the detachment
manifest under `results/raw/workspace-detach/20261023T195925Z/`.

The [new protocol](../protocols/d1/d1-codebase-review-01.json), frozen at
20:03:55 UTC, authorizes a separate verification envelope, including the one
additional current guard artifact check recommended by
[guard frame 01](D1-03-guard-frame-01.md). Limits: 90 minutes; at most three
Python, two Node and three static verification invocations; exactly at most
one guard artifact invocation; each execution at most 120 seconds/4 GiB.
No dependency installations, compilations, primary solver queries, proofs,
settlement replays or held-out evaluation are permitted. Earlier consumed
budgets and their outcomes remain unchanged.

Completion criteria are preservation and coherent publishing, meaningful
software controls, a current-version guard artifact check, provenance/status
checks and matching remote/local branch identity after publishing. A missing
prerequisite is reported as a blocker rather than a passing test. This report
adds no claim that full transition semantics, a direct joint query or D1-03's
repair/replay/non-vacuity gates are complete.

## Review findings and changes

1. **Detached history differs from the copied files.** The inherited HEAD is
   the sibling synthetic research line, while this folder already contains the
   separately developed v2 fragment and lacks 62 of the sibling's tracked
   files. Preserve incoming deletions and all current local changes, rather
   than restoring or executing that other line. All 62 exact source-revision
   files are archived locally. Seven historical report/protocol versions are
   also copied byte-for-byte into
   [the tracked archive](../docs/history/synthetic-branch-1b4d568/README.md), with
   [source hashes](../metadata/d1/inherited-synthetic-archive-01.json).
   Original implementation and generated artifacts remain at their recorded
   Git revision. Their synthetic results do not discharge this checkout's
   prospective D1 gates. Generated outputs are excluded from new additions.
2. **Typed unit tests depended on an ignored compiler download.** The original
   `test_typed_bindings.py` reads upstream serialization snapshots from `build/`.
   Replace that dependency with three small verbatim upstream Rust test-source
   excerpts under `tests/d1/fixtures/noir_serialization/`, preserving the pinned
   revision, original/excerpt SHA-256, test vector values and MIT notice. These
   are upstream source fixtures, not newly generated circuits or proof data.
   Check the excerpt identity before decoding it. The original test and its
   old successful runs remain preserved in raw executable snapshots.
3. **Python setup was implicit.** Add
   [requirements-d1.txt](../requirements-d1.txt) with the already-installed,
   tested `pycryptodome==3.23.0`, document the Python 3.12 unit command and make
   the new runner exercise an isolated source/test tree. It has no ignored
   compiler source, build artifacts or raw logs. No package is installed here.
4. **The hardened guard lacked a current artifact result.** Add the reusable
   [guard entrypoint](../scripts/d1_guard_frame_check.py), writing exclusively
   to a fresh caller-selected directory and returning UNKNOWN on missing or
   unsupported inputs. The sealed historical entrypoint and checker remain
   unchanged. Use the
   [new bounded runner](../scripts/d1_codebase_review_run.py) with separate
   attempt snapshots and the newly authorized single guard slot.
5. **Current workspace/status text was stale.** Update README to identify the
   independent branch; retain old checkpoint rows/reports and prospectively
   record the newly discharged frame prerequisite. Add ignores for local
   Python environments and historical synthetic compiler/cache outputs.

No production semantic module changes are made during this review. In
particular, the hardened frame checker's source hash remains the one tested by
its final historical synthetic run. No newly passing source inventory is
represented as a full consumer transition implementation.

## Commands and observed checks

Python 3.12.12; PyCryptodome 3.23.0; Node v24.19.0; Git 2.43.0. Exact commands,
input hashes, limits, stdout/stderr and statuses are preserved under
`results/raw/D1-review/codebase-01/`.

| Invocation | Observed outcome | Meaning |
|---|---|---|
| `python3 scripts/d1_codebase_review_run.py python`, python-01 | exit 0; 81 tests, 0.166120 s | Original controls pass in this provisioned checkout |
| `python3 scripts/d1_codebase_review_run.py node`, node-01 | exit 1; 0.116064 s | Setup fails on `MODULE_NOT_FOUND: js-sha3`; no successful JavaScript suite |
| `python3 scripts/d1_codebase_review_run.py python`, python-02 | exit 0; 81 tests, 0.166215 s | Same controls pass with pinned fixtures in isolated source/test tree |
| `python3 scripts/d1_codebase_review_run.py guard`, guard-01 | exit 0; 0.466938 s | Current hardened guard's local frame and use-site check pass |

No dependency installation, alternate implementation, missing-evidence skip
or repeated Node execution is used to turn the setup failure into a pass.
The legacy test requires both installed `js-sha3` from `package-lock.json` and
seven preserved T06 records. Its broader behavior remains unverified in this
review. Future setup must provision those inputs under its own approved limits.

The Python suite covers 23 v2 core controls, 27 typed decoder/binding controls,
nine transitive consumer controls and 22 guard controls. The isolated run
establishes that these unit controls no longer require the ignored Noir source
download; it does not establish a fresh toolchain build or artifact replay.

The current guard certificate follows seven function bodies and two loops,
checks four call arguments and protects 21 state roots, while retaining the
possible write to `validatorSetIndex` (declaration 292). Both normal return and
revert are retained; signature acceptance, termination and non-vacuity remain
unestablished. The artifact reports `security_verdict: UNKNOWN` and
`complete_consumer_transition: false`. This closes only the final-version
structural frame prerequisite, not the full D1-03 research gate. The prior
certificate, checker snapshots and reports remain immutable.

The first static check exits 1: its source-excerpt comparison accidentally
strips the space after `fn name()`, falsely reporting three mismatches. Preserve
that checker/version/result; compare the complete verbatim function span
instead, without changing fixtures or production code. The corrected static
check exits 0: 65 Python files and 37 JSON files parse, Foundry TOML parses,
eight current documents have valid local links, seven archived deliverables
and all 62 inherited deletions match source hashes, and all 1,205 prior files
match except the five explicitly changed paths. It also checks current local links,
fixture/archive provenance, completed-report preservation, source/test hashes
against the final execution snapshots, whitespace and new-file hygiene. The
[review metadata](../metadata/d1/d1-codebase-review-01.json) binds the exact
tracked deliverables and raw records. Historical exact-copy documents retain
source-revision-relative links; they are not rewritten for a different folder.

## Preservation, scope and next task

Preserve the incoming index/status, all pre-existing evidence, exact living
checkpoint documents and the inherited deleted-file bytes before edits. No
historical report, frozen protocol or security verdict is changed. The former
shared repository and registered sibling worktree are outside this review's
write scope. Publishing is limited to `chatgpt-codex`; no force push or rewrite
of the inherited history is authorized or needed.

**Next D1 task:** implement exact message traversal, registry and token effects,
and whole-transition rollback under v2, retaining validator-state and verifier
boundaries. Completion must include meaningful unsupported/rollback/duplicate/
last-slot controls and a checked relation suitable for composition; only then
may direct joint queries and candidate replay begin. All 28 primary slots are
unused. Do not start D1-04 before the full faulty/repaired, non-vacuity and
concrete replay gates pass. Stop after D1-04/D1-06 and before held-out work as
already required.
