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
    submit(["Submit paper [END GOAL]"])
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
    analysis --> t22["T22 ACIR and SMT [ACTIVE]"]
    t22 --> coneGate["Cone gate [DONE]"]
    t22 --> nineCases["Nine-case run [DONE]"]
    nineCases --> primaryResult["Primary result [UNKNOWN]"]
    primaryResult --> failureAnalysis["Failure analysis [DONE]"]
    failureAnalysis --> v3Rerun["Versioned v3 rerun [DONE]"]
    v3Rerun --> generalGate["General-query feasibility [NEXT]"]
    t22 --> transferCase["Independent transfer [WAITING]"]
    t22 --> sensitivity["Sensitivity checks [WAITING]"]

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

    class foundation,fixture,payy,sourceCheck,coneGate,nineCases,failureAnalysis,v3Rerun,tracking,livingTree done
    class analysis,t22 active
    class generalGate next
    class evaluation,history,heldOut,baselines,manuscript,claims,artifacts,draft,transferCase,sensitivity waiting
    class contribution,primaryResult unknown
```

## Immediate path

1. Done: the running-flag false positive and both `UNKNOWN` classes are explained in [T22 Section 3.2](../reports/T22.md).
2. Done: the [T22-v3 rerun and audit](../reports/T22-v3.md), frozen before output, returns 4 `VIOLATION` and 5 `UNKNOWN` (4/9 expected outcomes matched). Seven synthetic regressions and four SAT replays pass; the running-flag probe false positive is fixed, but its full case remains unresolved. Prior evidence and compiled inputs are unchanged.
3. Next: freeze a versioned general-query feasibility experiment on the check-added `agg_agg` development case. Require non-vacuity SAT and prefix/tail UNSAT within 300 seconds per query, or a preserved minimized blocker.
4. Run the independent transfer case only after the primary controls are acceptable, without tuning on its result.
5. Complete sensitivity checks and equal-information baselines.
6. Decide whether the evidence supports a defensible contribution and, if so, assemble the submission package.

The end goal does not imply that submission is currently justified. The
research contract's two principal properties remain unchanged, and T22 has no
completed verdict yet.

## Checkpoint log

| Date | Checkpoint | Status | Evidence and meaning |
| --- | --- | --- | --- |
| 2026-10-20 | T22-v2 single-case feasibility gate | `[DONE]` | [T22](../reports/T22.md): the known vulnerable Payy case produced a counterexample in 4.1 seconds after exact specialization reduced the probe from 587 opcodes and 523 witnesses to 0 opcodes and 1 witness. This is not the nine-case result. |
| 2026-10-20 | Living project checkpoint tree | `[DONE]` | This page and the corresponding `AGENTS.md` update establish the visual checkpoint routine. No research verdict changed. |
| 2026-10-20 | T22-v2 frozen nine-case primary run | `[DONE]` | [T22](../reports/T22.md): 2/9 outcomes matched, 6 were `UNKNOWN`, and the running-flag negative control returned a likely spurious `VIOLATION`. The evaluation task completed, but the T22 result remains `[UNKNOWN]`. |
| 2026-10-20 | T22-v2 failure diagnosis | `[DONE]` | [T22 Section 3.2](../reports/T22.md); raw evidence in ignored `results/raw/T22/32_v2_diagnosis/`. The running-flag `VIOLATION` is a confirmed analyzer false positive: the specialization drops the implied goal constraint, and original-ACIR subset certificates are UNSAT for all eight slots. Timeouts trace to the cvc5 `gb` mode, missing re-componentization and slot scheduling; the general queries remain unresolved. The `agg_utxo` contradiction is genuine but was handled as unsupported. No verdict changed; the primary result stays `[UNKNOWN]`. |
| 2026-10-20 | T22-v2 diagnosis correction and reproduction addendum | `[DONE]` | [T22 Section 3.2](../reports/T22.md), post-review corrections. Correction to the previous row: the `agg_utxo` contradiction rules out only the all-streams-inactive premise; it does not show that an empty prefix is impossible. The R3 wording was narrowed to match. An exact-command addendum (`11_commands_addendum.txt`) and three reproduction scripts were added; the original raw records are unchanged. No verdict or tree node changed; the v3 rerun remains `[NEXT]`. |
| 2026-10-20 | T22-v3 versioned encoding, primary rerun and audit | `[DONE]` | [T22-v3](../reports/T22-v3.md): frozen R1–R6 rerun completes with 4 `VIOLATION`, 5 `UNKNOWN`, 0 `VERIFIED_WITHIN_SCOPE` (4/9 matches). All seven regressions and four SAT replays pass; all nine source/compiled cases and 129 prior raw evidence files match v2/the diagnosis. The running-flag probe false positive is fixed, but general queries produce six timeouts and nine allocation failures. Overall T22 remains `[ACTIVE]`, its research result `[UNKNOWN]`, and independent transfer deferred. |

## Update rule

For every bounded task that changes project state, update the relevant node and
append one row above. Link to the report or evidence that supports the status.
Never remove an old row; corrections should be new rows that identify what
changed. Pure discussion or status checks do not create project checkpoints.
