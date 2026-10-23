# BindCheck project checkpoints

This is the living visual index from the current research state to a paper
submission. It is a navigation aid, not an evidence source. The
[research contract](research-contract.md), [README](../README.md), and linked
task reports remain authoritative.

Status labels mean:

- `[DONE]` — the bounded task is complete at its stated evidence level;
- `[ACTIVE]` — work is underway;
- `[NEXT]` — the immediate gate;
- `[WAITING]` — depends on earlier work; and
- `[UNKNOWN]` — the research verdict is not established.

```mermaid
flowchart TD
    submit(["Submit paper [WAITING]"])
    contribution["Defensible contribution [UNKNOWN]"]
    submit -->|"Requires"| contribution
    submit -->|"Requires"| manuscript["Paper package [WAITING]"]
    submit -.->|"Tracks"| tracking["Visual checkpoints [DONE]"]

    contribution --> foundation["Evidence foundation [DONE]"]
    contribution --> analysis["Analysis method [ACTIVE]"]
    contribution --> evaluation["Generalization evidence [WAITING]"]

    foundation --> fixture["T01-T07 fixture [DONE]"]
    foundation --> payy["T08-T20 Payy [DONE]"]

    analysis --> sourceCheck["T21 source check [DONE]"]
    analysis --> t22["T22 remaining evaluation [WAITING]"]
    t22 --> coneGate["Cone gate [DONE]"]
    t22 --> nineCases["Nine-case run [DONE]"]
    nineCases --> primaryResult["Primary result [UNKNOWN]"]
    primaryResult --> failureAnalysis["Failure analysis [DONE]"]
    failureAnalysis --> v3Rerun["Versioned v3 rerun [DONE]"]
    v3Rerun --> generalGate["General-query feasibility [DONE]"]
    generalGate --> generalResult["Check-added general result [UNKNOWN]"]
    generalResult --> acirSummary["ACIR-backed summary gate [WAITING]"]
    t22 --> transferCase["Independent transfer [WAITING]"]
    t22 --> sensitivity["Sensitivity checks [WAITING]"]

    analysis --> d1["D1 investigation [ACTIVE]"]
    d1 --> d100["D1-00 preserve and align [DONE]"]
    d100 --> d101["D1-01 T22 reporting closure [DONE]"]
    d100 --> d102["D1-02 target selection [DONE]"]
    d101 --> d103["D1-03 joint semantics [DONE]"]
    d102 --> d103
    d103 --> d104["D1-04 fair baselines [DONE]"]
    d104 --> d105["D1-05 checked refinement [DONE]"]
    d105 --> d106["D1-06 frozen comparison [NEXT]"]
    d106 --> d107["D1-07 independent transfer [WAITING]"]
    d107 --> d108["D1-08 full evaluation [WAITING]"]
    d101 -.-> t22
    d106 -.-> acirSummary
    d107 -.-> transferCase
    d108 -.-> evaluation

    evaluation --> history["Historical cases [WAITING]"]
    evaluation --> heldOut["Held-out families [WAITING]"]
    evaluation --> baselines["Equal-info baselines [WAITING]"]

    manuscript --> claims["Claims and limits [WAITING]"]
    manuscript --> artifacts["Artifact package [WAITING]"]
    manuscript --> draft["Write and revise [WAITING]"]

    tracking --> livingTree["Living tree added [DONE]"]

    classDef done fill:#CDF4D3,stroke:#66D575
    classDef active fill:#C2E5FF,stroke:#3DADFF
    classDef next fill:#FFECBD,stroke:#FFC943
    classDef waiting fill:#D9D9D9,stroke:#B3B3B3
    classDef unknown fill:#FFE0C2,stroke:#FF9E42

    class foundation,fixture,payy,sourceCheck,coneGate,nineCases,failureAnalysis,v3Rerun,generalGate,tracking,livingTree,d100,d101,d102,d103,d104,d105 done
    class analysis,d1 active
    class evaluation,history,heldOut,baselines,manuscript,claims,artifacts,draft,transferCase,sensitivity,submit,t22,acirSummary,d107,d108 waiting
    class d106 next
    class contribution,primaryResult,generalResult unknown
```

## Immediate path

1. Done: the running-flag false positive and both `UNKNOWN` classes are explained in [T22 Section 3.2](../reports/T22.md).
2. Done: the [T22-v3 rerun and audit](../reports/T22-v3.md), frozen before output, returns 4 `VIOLATION` and 5 `UNKNOWN` (4/9 expected outcomes matched). Seven synthetic regressions and four SAT replays pass; the running-flag probe false positive is fixed, but its full case remains unresolved. Prior evidence and compiled inputs are unchanged.
3. Done: [T22-v4](../reports/T22-v4.md) preserves a 22.5 KB, one-assertion non-vacuity goal that times out at 300 seconds with 93,696 KiB peak RSS. A fixed-stream ACIR branch returns conditional SAT in 79.9 seconds, while non-vacuity, prefix and tail in the full Boolean-rank query remain `UNKNOWN` after three 300-second timeouts. The check-added case has no verified verdict.
4. Done: [D1-00](../reports/D1-00.md) creates the isolated worktree, preserves staged work and historical evidence, and aligns the contract and [roadmap](d1/roadmap.md).
5. Done: [D1-01](../reports/D1-01.md) accounts for all six T22-v5 slots: three validated historical check-added timeouts and three new running-flag timeouts at 300 seconds/4 GiB. Reporting closure is complete, all six results remain UNKNOWN, and the original successful-solver milestone is unmet. No extended campaign or whole-system guarantee follows.
6. Active: [D1-02](../reports/D1-02.md) screens pinned WarpToad and 0xbow Privacy Pools sources. The two-family availability screen is complete, but neither satisfies the full initial Noir/ACIR batched-settlement fragment. Initial-scope selection remains unresolved; no build/proof/replay or held-out transfer result follows. A separately bounded continuation or explicit scope decision is next.
7. Done: [D1-02 continuation](../reports/D1-02-continuation-01.md) selects hashcloak Semaphore-Noir, with qualifications, as the reserved initial-scope transfer target; Aztec v6.0.0 is not selected. Nothing was built or proved.
8. Done: [D1-03](../reports/D1-03.md) validates the joint-semantics pipeline on authored synthetic fixtures. synth-faulty yields VIOLATION with a replayed concrete model (unauthorized burn in the unconstrained message tail); synth-repaired yields VERIFIED_WITHIN_SCOPE with a replayed non-vacuity witness. 15 regression tests pass. Consumer contract not exercised; solver times within limits.
9. Done: [D1-04](../reports/D1-04.md) baseline comparison: Foundry tests (7 pass, <1 ms), monolithic joint solving (identical to D1-03), and manual summary (faster SAT but UNKNOWN on repaired UNSAT). Pipeline advantage is formal UNSAT + automatic extraction. **Review checkpoint reached.**
10. Done: [D1-05](../reports/D1-05.md) adds consumer-directed abstraction-refinement (CEGAR): abstract (0 ACIR constraints) → concretize → refine. Both synthetic cases reject a spurious abstract candidate via concretization; synth-faulty confirms VIOLATION at iteration 1 (11.75 s); synth-repaired proves VERIFIED at iteration 1 (107.3 s). Refinement is coarse-grained (all constraints in one step) on these small circuits. 16 regression tests pass. The concretization check is the new mechanism.
11. Next: D1-06 frozen feasibility comparison, then independent transfer. Full evaluation and submission remain conditional on the feasibility decision.

The end goal does not imply that submission is currently justified. The
research contract's two principal properties remain unchanged, and unresolved T22 results remain UNKNOWN. D1 preparation, reporting closure, synthetic pipeline validation, baseline comparison, and consumer-directed refinement are complete. The CEGAR mechanism works correctly and the concretization check is a genuine new mechanism, but provides no measurable speed advantage on these small synthetic circuits. Foundry testing remains a strong baseline for bug finding. No method-evaluation result on real cases, no selective refinement advantage, and no generalization evidence has been established.

## Checkpoint log

| Date | Checkpoint | Status | Evidence and meaning |
| --- | --- | --- | --- |
| 2026-10-20 | T22-v2 single-case feasibility gate | `[DONE]` | [T22](../reports/T22.md): the known vulnerable Payy case produced a counterexample in 4.1 seconds after exact specialization reduced the probe from 587 opcodes and 523 witnesses to 0 opcodes and 1 witness. This is not the nine-case result. |
| 2026-10-20 | Living project checkpoint tree | `[DONE]` | This page and the corresponding `AGENTS.md` update establish the visual checkpoint routine. No research verdict changed. |
| 2026-10-20 | T22-v2 frozen nine-case primary run | `[DONE]` | [T22](../reports/T22.md): 2/9 outcomes matched, 6 were `UNKNOWN`, and the running-flag negative control returned a likely spurious `VIOLATION`. The evaluation task completed, but the T22 result remains `[UNKNOWN]`. |
| 2026-10-20 | T22-v2 failure diagnosis | `[DONE]` | [T22 Section 3.2](../reports/T22.md); raw evidence in ignored `results/raw/T22/32_v2_diagnosis/`. The running-flag `VIOLATION` is a confirmed analyzer false positive: the specialization drops the implied goal constraint, and original-ACIR subset certificates are UNSAT for all eight slots. Timeouts trace to the cvc5 `gb` mode, missing re-componentization and slot scheduling; the general queries remain unresolved. The `agg_utxo` contradiction is genuine but was handled as unsupported. No verdict changed; the primary result stays `[UNKNOWN]`. |
| 2026-10-20 | T22-v2 diagnosis correction and reproduction addendum | `[DONE]` | [T22 Section 3.2](../reports/T22.md), post-review corrections. Correction to the previous row: the `agg_utxo` contradiction rules out only the all-streams-inactive premise; it does not show that an empty prefix is impossible. The R3 wording was narrowed to match. An exact-command addendum (`11_commands_addendum.txt`) and three reproduction scripts were added; the original raw records are unchanged. No verdict or tree node changed; the v3 rerun remains `[NEXT]`. |
| 2026-10-20 | T22-v3 versioned encoding, primary rerun and audit | `[DONE]` | [T22-v3](../reports/T22-v3.md): frozen R1–R6 rerun completes with 4 `VIOLATION`, 5 `UNKNOWN`, 0 `VERIFIED_WITHIN_SCOPE` (4/9 matches). All seven regressions and four SAT replays pass; all nine source/compiled cases and 129 prior raw evidence files match v2/the diagnosis. The running-flag probe false positive is fixed, but general queries produce six timeouts and nine allocation failures. Overall T22 remains `[ACTIVE]`, its research result `[UNKNOWN]`, and independent transfer deferred. |
| 2026-10-20 | T22-v4 check-added general-query feasibility | `[DONE]` | [T22-v4](../reports/T22-v4.md): a one-assertion, 18-variable reduction of the original non-vacuity goal still times out at 300 seconds (93,696 KiB peak RSS). Exact fixed-stream specialization yields conditional non-vacuity SAT in 79.9 seconds; the three full Boolean-rank queries each time out at 300 seconds. The bounded feasibility task is complete with a preserved blocker, while the check-added verdict and overall T22 remain `[UNKNOWN]`/`[ACTIVE]`; independent transfer stays deferred. |
| 2026-10-23 | D1-00 isolated worktree and research alignment | `[DONE]` | [D1-00](../reports/D1-00.md), [baseline](../metadata/d1/baseline.json), and [validation](../metadata/d1/d1-00-validation.json): preserve source index/staged patch, original files, historical reports, and an independent raw-evidence copy. Revise the prospective contract and roadmap; old verdicts remain unchanged. D1-01 reporting closure and D1-02 intake are next; old transfer deferral is replaced by early availability screening, not a transfer claim. |
| 2026-10-23 | D1-01 T22-v5 reporting closure | `[DONE]` | [D1-01](../reports/D1-01.md), [six-slot matrix](../metadata/d1/d1-01-query-matrix.json), and [execution manifest](../metadata/d1/d1-01-execution-manifest.json): validate three preserved check-added timeouts and execute three missing running-flag queries once at 300 seconds/4 GiB. All six remain UNKNOWN; non-vacuity and the original successful-solver milestone are unresolved. Specification/reduction audits do not establish encoding soundness. Prior evidence and original/source indexes are preserved. D1-02 intake is next and has not started. |
| 2026-10-23 | D1-02 two-family availability screen; selection unresolved | `[ACTIVE]` | [D1-02](../reports/D1-02.md), [intake matrix](../metadata/d1/d1-02-intake.json), and [protocol](../protocols/d1/d1-02-intake.json): inspect 65 pinned source files from WarpToad and 0xbow Privacy Pools, with licenses, public-input/consumer mappings, policy provenance, honest-path sources and blockers. WarpToad is single-claim Noir; 0xbow batches Circom proofs with additional modeling requirements. No initial-scope target selected; no build/proof/replay run. Preserve all 49 D1-01 raw files and six fixed deliverables; archive all nine sealed checkpoint versions before living-document updates. D1-03 not started. |
| 2026-10-23 | D1-02 continuation 01: initial-scope target selected with qualifications | `[DONE]` | [Continuation report](../reports/D1-02-continuation-01.md), [intake](../metadata/d1/d1-02-continuation-01-intake.json), [protocol](../protocols/d1/d1-02-continuation-01.json): 46 pinned files from hashcloak Semaphore-Noir and Aztec v6.0.0. Semaphore-Noir (Noir recursive batch, per-item nullifier writes, Hardhat in-process honest route in source) is selected; its bb CLI pin, artifact/VK correspondence, prefix semantics and batch policy remain open. Aztec is not selected. Incidental exposure is disclosed. 0 builds/proofs/solver runs; verdict UNKNOWN. D1-02 is DONE; D1-03 is ACTIVE. |
| 2026-10-23 | D1-03 joint semantics on synthetic fixtures | `[DONE]` | [D1-03 report](../reports/D1-03.md), [protocol v2](../protocols/d1/d1-03-joint-semantics.md), [results](../results/raw/D1-03/synthetic/summary.json): authored faulty/repaired producers (N=9, 3-word stride, 0 RANGE). synth-faulty→VIOLATION (CONCRETE_MODEL_REPLAYED, AUTH-UNMATCHED SAT at slot 0, nargo replay pass); synth-repaired→VERIFIED_WITHIN_SCOPE (CONCRETE_MODEL_REPLAYED, all AUTH/COV UNSAT, NONVAC SAT_REPLAYED). 15 regression tests pass. Consumer contract not exercised. D1-03 is DONE; D1-04 is NEXT. |
| 2026-10-23 | D1-04 equal-information baselines | `[DONE]` | [D1-04 report](../reports/D1-04.md), [protocol](../protocols/d1/d1-04-baselines.md), [results](../results/raw/D1-04/baseline_results.json): B1 Foundry (7 tests, <1 ms, finds VIOLATION); B2 monolithic (identical to D1-03, propagation neutral); B3 manual summary (faulty SAT 1.0 s, repaired UNKNOWN 60 s timeout). Pipeline advantage: formal UNSAT + automatic extraction; no speed advantage on SAT. Honest assessment: no clear advantage over Foundry for bug finding on synthetic cases. **Review checkpoint reached.** D1-04 is DONE; D1-05 is NEXT. |
| 2026-10-23 | D1-05 consumer-directed refinement | `[DONE]` | [D1-05 report](../reports/D1-05.md), [protocol](../protocols/d1/d1-05-refinement.md), [results](../results/raw/D1-05/synthetic/summary.json): CEGAR loop (abstract → concretize → refine). Both cases reject a spurious abstract candidate at iteration 0; synth-faulty confirms VIOLATION at iteration 1 (11.75 s, replayed); synth-repaired proves UNSAT at iteration 1 (107.3 s) → VERIFIED_WITHIN_SCOPE. Refinement coarse-grained on N=9 (all constraints in one step). 16 tests pass. Concretization is the new mechanism. D1-05 is DONE; D1-06 is NEXT. |

## Update rule

For every bounded task that changes project state, update the relevant node and
append one row above. Link to the report or evidence that supports the status.
Never remove an old row; corrections should be new rows that identify what
changed. Pure discussion or status checks do not create project checkpoints.
