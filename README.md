# BindCheck

BindCheck is a research prototype for checking whether the guarantees of a zero-knowledge proof justify the effects an application performs after accepting it. The first testbed is batched deposits and withdrawals: Circom circuits, Solidity consumers, a specification-assisted checker, and local execution traces. The broader research question is whether proof-to-execution obligations can be recovered and checked across independent applications with useful accuracy and manageable analyst effort.

Start with the [research contract](docs/research-contract.md). It is authoritative for the research questions, threat model, scope, specification boundary, and evidence rules. The [living project checkpoint tree](docs/project-status.md) shows the path from current work to a possible paper submission without replacing the underlying evidence. The [Payy case study](docs/payy-case-study.md) gives the pinned versions, commands, expected outcomes, evidence locations, and limits for the independently built local reproduction of a publicly disclosed message-tail flaw.

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
- No held-out application result or general research contribution has been established.

The current task is a separately versioned T22-v3 encoding (repairs R1–R6 in report Section 3.2), frozen before any output is inspected and rerun on the same nine cases. The independent transfer case is still deferred. The two principal properties in the research contract remain unchanged.

## Evidence hierarchy

1. `docs/research-contract.md` — current research decisions.
2. This README — current task status.
3. `reports/Txx.md` — tracked evidence summaries.
4. `results/raw/Txx/` — ignored, regenerable raw logs.
5. The research guide and dated updates — historical context.

## Repository layout

The principal directories are `circuits/` and `contracts/` for the small fixture, `bindcheck/` for the checker and specification, `payy-harness/` and `payy-consumer/` for the Payy experiment, `scripts/` for task runners, `reports/` for tracked evidence summaries, and `docs/` for current and historical-facing documentation. Generated proof data, downloaded dependencies, compiler output, and raw logs are ignored and must be regenerated on a fresh checkout.
