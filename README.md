# BindCheck

BindCheck investigates whether the guarantees of an accepted zero-knowledge proof justify the effects a blockchain application executes. The current D1 direction is **consumer-directed extraction and checked summary refinement** across producer constraints, public-input decoding, and consumer effects. This remains a research hypothesis. The new method is not implemented or validated yet.

This checkout is an independent Git repository at `/home/pollmix/Coding/BindCheck-d1 (copy)` on `chatgpt-codex`; its index and objects are independent of the original repository and sibling worktree. Start with the [D1 brief](docs/d1/brief.md), [development roadmap](docs/d1/roadmap.md), and [workspace preservation guide](docs/d1/workspace.md). [D1-00](reports/D1-00.md) records preparation and preservation checks.

Start with the [research contract](docs/research-contract.md). It is authoritative for the research questions, threat model, scope, specification boundary, and evidence rules. The [living project checkpoint tree](docs/project-status.md) shows the path from current work to a possible paper submission without replacing the underlying evidence. The [Payy case study](docs/payy-case-study.md) gives the pinned versions, commands, expected outcomes, evidence locations, and limits for the independently built local reproduction of a publicly disclosed message-tail flaw.

For a shareable introduction to the project and completed work, use the [research and work summary](docs/research-and-work-summary.md), dated 22 October 2026. It separates demonstrated results and open research claims at that historical checkpoint; the D1 roadmap now controls the next task.

The [research guide](BindCheck_Research_Guide.md) and [16 October progress update](2026-10-16-research-update.md) are historical planning and progress records. They remain useful context, but their evidence status and schedules may have been superseded.

The principal directories are `circuits/` and `contracts/` for the small fixture, `bindcheck/` for the checker and specification, `payy-harness/` and `payy-consumer/` for the Payy experiment, `scripts/` for task runners, and `reports/` for evidence reviews. Generated proof data and raw logs are under the ignored `results/raw/` tree and must be regenerated on a fresh checkout.

## Current status

- T15–T19 locally reproduce the public Payy message-tail mechanism with real proofs and committed token-balance effects, then validate the repair and an honest control.
- T20 maps those claims to pinned source and advisory evidence.
- T21 is an in-sample, source-pattern prototype; it does not establish generalization.
- T22-v2 passes the single-case feasibility gate: the bounded earlier Payy `agg_agg` case yields a cvc5 counterexample in 4.1 seconds after exact specialization reduces the probe from 587 opcodes/523 witnesses to 0/1. Its frozen nine-case primary evaluation then fails: 2/9 outcomes match, 6 are `UNKNOWN`, and the equivalent running-flag negative control produces a likely spurious `VIOLATION`. T22 remains incomplete and no general detector claim is supported.
- The T22-v2 failure diagnosis (report Section 3.2) explains all three failure classes against the same ACIR without changing any result:
  - **Running-flag `VIOLATION` (false positive):** confirmed as an analyzer false positive. Specialization discards the implied constraint `messages[k] = 0` for the goal witness, while subset certificates from the original ACIR are UNSAT for all eight slots.
  - **Timeouts:** traced to the default cvc5 finite-field mode on range-bit decompositions, missing re-componentization, and a slot schedule that skips the violating slot. The general queries remain an open scalability limit.
  - **`agg_utxo` contradictions:** genuine (the first proof can never be padding), but handled as unsupported, so no general query was issued.
- [T22-v3](reports/T22-v3.md) completes the separately frozen R1–R6 repair, nine-case rerun and SAT audit: 4/9 outcomes match, with 4 `VIOLATION`, 5 `UNKNOWN`, and no `VERIFIED_WITHIN_SCOPE`. It recovers the `>`-guard and skipped-final-slot mutants; the running-flag probe false positive is fixed (all eight slots UNSAT), while its full case remains `UNKNOWN`. Six general queries time out and nine fail allocation under the frozen 4 GiB cap. All four SAT probes replay successfully, all nine compiled cases match v2, and prior evidence is unchanged. This is development-case evidence, not generalization.
- [T22-v4](reports/T22-v4.md) completes the separately versioned check-added `agg_agg` general-query feasibility task with a minimized blocker. Exact fixed-stream specialization gives a conditional non-vacuity SAT in 79.9 seconds, but all three full Boolean-rank general queries still time out at 300 seconds. A byte-preserved goal-only reduction of the original non-vacuity SMT has one assertion, 18 free variables and no ACIR assertions, yet also times out at 300 seconds with 93,696 KiB peak RSS. The check-added case and overall T22 remain `UNKNOWN`/incomplete; no safe verdict follows from these timeouts.
- [D1-01](reports/D1-01.md) closes the T22-v5 reporting boundary: all six N=8 primary slots are accounted for by three validated historical check-added timeouts and three new running-flag timeouts, each at 300 seconds and 4 GiB. All six remain `UNKNOWN`; the original successful-solver milestone is unmet and overall T22 remains incomplete. The unchanged [v5 protocol](scripts/t22_v5_protocol.md), compact specification self-check, and saved ACIR-bearing blocker audit establish no whole-system safety result. The [query matrix](metadata/d1/d1-01-query-matrix.json) and [execution manifest](metadata/d1/d1-01-execution-manifest.json) record the evidence; no `reports/T22-v5.md` or earlier verdict is rewritten.
- [D1-02](reports/D1-02.md) completes a bounded availability screen of pinned WarpToad and 0xbow Privacy Pools sources (65 files). Neither meets the entire initial Noir/ACIR batched-settlement fragment: WarpToad supplies a single-claim Noir path; 0xbow supplies Circom/Groth16 and batched consumption with additional modeling needs. At that historical checkpoint no target was selected and D1-02 remained ACTIVE. The recovered continuation below supersedes that task state. No build, proof, replay or transfer evaluation ran in the screen.
- [D1-02 continuation](reports/D1-02-continuation-01.md), recovered and checked by the [reconciliation audit](reports/D1-02-reconciliation-01.md), selects Semaphore-Noir with qualifications. D1-02 availability selection is complete; no proving or transfer result follows. Inherited D1-03 setup and its hash-matching protocol are preserved; [D1-03 preflight](reports/D1-03-preflight-01.md) identifies a conflict between freely failing transfers and the required verified repaired control. The authorized [v2 design](reports/D1-03-v2-design.md) now supplies explicit funded-token conditions, separate P/O policy and exact occurrence matching; 10 component tests and 8,892 finite checks pass. The [extraction gate](reports/D1-03-v2-extraction-01.md) adds a domain/policy core and compiled-artifact inventories with 23 passing regressions, but typed recursion/frame bindings and transition semantics were unimplemented at that checkpoint. [Typed bindings](reports/D1-03-typed-bindings-01.md) now decode all four artifacts and certify six recursive-call/frame mappings, with 27 passing controls. [Consumer-boundary audit](reports/D1-03-consumer-boundary-01.md) follows 19 function/modifier bodies and exposes unresolved signature/validator-set loops; nine controls pass after a preserved fixture-error correction. [Guard-frame work](reports/D1-03-guard-frame-01.md) adds 22 passing controls; its single artifact check predates dispatch/cache hardening, so final artifact validation is incomplete. The subsequently authorized [codebase review](reports/D1-codebase-review-01.md) validates the final guard checker against the pinned artifact within 120 seconds/4 GiB; all 81 Python controls pass in an isolated source/test copy. The legacy JavaScript suite is blocked by the missing installed `js-sha3` dependency. Full transition extraction and joint gates remain incomplete. D1-03 stays UNKNOWN; D1-04 is blocked.
- No held-out application result or general research contribution has been established.

**D1-01 reporting closure and D1-02 availability selection are complete; research results remain UNKNOWN. D1-03 is incomplete:** the authorized v2 design addresses the preflight conflict prospectively, but no full joint query, proof or settlement replay has run. Component checks are not joint verification. New joint semantics and equal-information baselines precede consumer-directed optimization. The two principal properties remain authorization and coverage.

D1-00 ran preservation and documentation checks only. D1-01 validated the saved check-added records and ran only the three missing running-flag slots. No D1 method-feasibility or novelty claim follows from preparation or reporting closure.

## Evidence hierarchy

1. `docs/research-contract.md` — current research decisions.
2. This README — current task status.
3. `reports/Txx.md` and `reports/D1-xx.md` — tracked evidence summaries.
4. `results/raw/Txx/` and `results/raw/D1-xx/` — ignored, regenerable raw logs.
5. The research guide and dated updates — historical context.

## Repository layout

The principal directories are `circuits/` and `contracts/` for the small fixture, `bindcheck/` for the checker and specification, `payy-harness/` and `payy-consumer/` for the Payy experiment, `scripts/` for task runners, `reports/` for tracked evidence summaries, and `docs/` for current and historical-facing documentation. Generated proof data, downloaded dependencies, compiler output, and raw logs are ignored and must be regenerated on a fresh checkout.

## Checking this checkout

The D1 Python controls were checked with Python 3.12.12 and PyCryptodome
3.23.0. The small upstream Noir test-source excerpts, provenance and MIT notice
are included under `tests/d1/fixtures/`; unit controls need no compiler download,
proof, solver, generated artifact or historical raw log. To set up and run them:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-d1.txt
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests/d1 -v
```

The legacy checker tests use `node --test bindcheck/test/checker.test.js`,
installed dependencies from `package-lock.json`, and the seven preserved T06
records under ignored `results/raw/T06/records/`. They cannot run on a fresh
clone without those inputs. The codebase review records a dependency setup
failure, not a passing JavaScript suite. No dependency installation occurred
during that frozen review.

Task-specific D1 experiment runners are frozen historical entrypoints,
not general test commands: they may refuse completed attempts or exhausted
budgets. The reusable `scripts/d1_guard_frame_check.py --output <fresh-path>`
needs the separately pinned solc/source artifacts and only checks a local
storage frame. Obtain any required experiment budget approval and freeze
inputs before using it. Its success is not a complete transition or security
verdict.

The [codebase review](reports/D1-codebase-review-01.md) explains the independent
checkout's inherited history. Exact synthetic-branch reports and protocol
versions are preserved under `docs/history/synthetic-branch-1b4d568/`; their
original full implementation remains in Git history. Their synthetic claims
do not complete this checkout's D1 gates.
