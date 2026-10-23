# BindCheck

BindCheck investigates whether the guarantees of an accepted zero-knowledge proof justify the effects a blockchain application executes. The current D1 direction is **consumer-directed extraction and checked summary refinement** across producer constraints, public-input decoding, and consumer effects. This remains a research hypothesis. The new method is not implemented or validated yet.

D1 development uses the isolated `/home/pollmix/Coding/BindCheck-d1` worktree on `research/d1`. Start with the [D1 brief](docs/d1/brief.md), [development roadmap](docs/d1/roadmap.md), and [workspace preservation guide](docs/d1/workspace.md). [D1-00](reports/D1-00.md) records preparation and preservation checks.

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
- No held-out application result or general research contribution has been established.

**D1-01 reporting closure is complete; research results remain UNKNOWN. Next: D1-02 screens independent non-Payy targets** without waiting for solver success. New joint semantics and equal-information baselines precede consumer-directed optimization. The two principal properties remain authorization and coverage.

D1-00 ran preservation and documentation checks only. D1-01 validated the saved check-added records and ran only the three missing running-flag slots. No D1 method-feasibility or novelty claim follows from preparation or reporting closure.

## Evidence hierarchy

1. `docs/research-contract.md` — current research decisions.
2. This README — current task status.
3. `reports/Txx.md` and `reports/D1-xx.md` — tracked evidence summaries.
4. `results/raw/Txx/` and `results/raw/D1-xx/` — ignored, regenerable raw logs.
5. The research guide and dated updates — historical context.

## Repository layout

The principal directories are `circuits/` and `contracts/` for the small fixture, `bindcheck/` for the checker and specification, `payy-harness/` and `payy-consumer/` for the Payy experiment, `scripts/` for task runners, `reports/` for tracked evidence summaries, and `docs/` for current and historical-facing documentation. Generated proof data, downloaded dependencies, compiler output, and raw logs are ignored and must be regenerated on a fresh checkout.
