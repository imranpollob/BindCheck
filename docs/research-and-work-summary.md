# BindCheck: research and work summary

**Snapshot:** 22 October 2026 (America/Detroit).  
**Audience:** a researcher, supervisor, or collaborator joining the project.  
**Overall state:** a local real-proof reproduction and repair check are established; the automated analysis is still under development. Generalization and a defensible new research contribution remain unestablished.

This is a shareable overview of the research question, completed work, evidence limits, and next task. The [research contract](research-contract.md) remains authoritative for scope and semantics; the [README](../README.md) and linked task reports control implementation status and experimental claims. This summary was checked against those files and the available local T22-v5 records. No proof generation, solver experiment, or consumer execution was rerun for this documentation review.

## 1. What the project is trying to answer

A zero-knowledge proof establishes that some values satisfy the rules encoded in a circuit. An application then reads the proof's public values and performs actions, such as consuming a deposit, transferring tokens, or accepting a new state root. A valid proof does not automatically establish that those actions are justified or that every required action occurred.

**BindCheck asks whether a specification-assisted analysis can check the connection between what the proof actually establishes and what the consuming application actually commits.** The initial submission scope is batched ZK applications with a **Noir/ACIR producer and a Solidity/EVM consumer**. ACIR is the compiled constraint representation used for the current circuit analysis. The earlier Circom fixture is a development testbed, not a change to that current scope.

The research contract defines two principal properties:

| Property | Plain-language question | Example failure |
| --- | --- | --- |
| Authorization | Is every protected effect justified by a compatible proof-backed or otherwise explicitly permitted authorization? | A contract pays a withdrawal represented only by an unconstrained public message. |
| Coverage | Does every required obligation get discharged, validly cancelled, or preserved as a permitted pending obligation? | A new balance state is accepted while a required backing deposit is left unconsumed. |

Matching must preserve identity, asset, amount, beneficiary, domain, and multiplicity where the policy requires them. Aggregation, splitting, padding, and deferral need explicit rules; matching totals alone is insufficient. Coverage is a safety property, not a guarantee that a pending action eventually executes.

The analyst may describe semantic roles, intended obligations, permitted transformations, and environmental assumptions. The checker should recover implementation facts from artifacts. A specification must not supply the expected verdict, assert the missing constraint, or assume the very connection being tested. Manual implementation summaries must be marked `ASSUMED` and excluded from automatic-recovery claims.

The four research questions are whether this model represents real failures and valid designs; whether the method detects failures across independent families; what it adds beyond existing analyses with equivalent information; and how much specification, onboarding, correction, and computation it costs. These are open research questions, not completed contributions. See [contract §§2–9](research-contract.md).

## 2. What has been built and demonstrated

| Work | Achieved | Evidence and limit |
| --- | --- | --- |
| **T01–T05: controlled fixture** | Built a four-slot Circom deposit circuit, generated real Groth16 proofs, integrated a generated Solidity verifier, and added deposit-backing semantics. A deliberately shortened consumer loop accepted a 390-unit credit while consuming only 350 units of backing. A repair rejected the omitted active row while preserving legitimate padding. | [T01](../reports/T01.md), [T04](../reports/T04.md), [T05](../reports/T05.md). Self-authored example with a publicly recomputable toy setup; no production cryptographic-soundness claim. |
| **T06–T07: trace checker and baseline** | Built a JavaScript checker over observed executions with a manual specification. It agreed with a direct Foundry property on all 132 enumerated executions: 22 violations, 10 executions without the observed violation, and 100 unchanged reverts. | [T06](../reports/T06.md), [T07](../reports/T07.md). One bounded fixture space. The direct baseline was shorter and needed no exporter; no advantage over it was established. |
| **T08–T14: Payy integration** | Selected an independently authored application, reconstructed the relevant artifact chain, generated new proofs, verified them natively and in Solidity, and exercised zero-message and legitimate mint settlement through the real local consumer. Documented a mint obligation and direct property checks. | [T09](../reports/T09.md), [T10](../reports/T10.md), [T12](../reports/T12.md), [T13](../reports/T13.md), [T14](../reports/T14.md). The originally supplied proof fixture was unsuitable; newly generated matching artifacts established the pipeline. |
| **T15–T20: historical mechanism and repair** | Carried a synthetic, unbacked burn record from an unconstrained circuit tail through recursive proof generation to an actual local token transfer. Confirmed that the later circuit rejects that witness and still accepts an honest mint. Mapped the result to the public advisory and exact source revisions. | [T15](../reports/T15.md), [T16](../reports/T16.md), [T18](../reports/T18.md), [T19](../reports/T19.md), [T20](../reports/T20.md). Local reproduction of a known issue, not a new discovery or a live-deployment claim. |
| **T21: source-pattern prototype** | Implemented a restricted Noir source analyzer that distinguishes the known missing-tail check from the repaired and sibling forms, and checks authored variants. | [T21](../reports/T21.md). Patterns were developed after reading these sources. Agreement is in-sample; no generalization or complete circuit semantics was established. |
| **T22: constraint-level analysis** | Built versioned ACIR-to-SMT analysis, diagnosed an analyzer false positive, repaired the probe encoding, reran nine bounded cases, and investigated general-query solver failures. | [T22](../reports/T22.md), [T22-v3](../reports/T22-v3.md), [T22-v4](../reports/T22-v4.md). Overall T22 remains incomplete. Details follow below. |

These are distinct components: an observed-execution checker, a source-pattern analyzer, and a producer-side constraint analyzer. They do not yet form a demonstrated general automatic pipeline that extracts both sides and proves the full research-contract property. Older reports preserve their original output labels; an old trace-level clean result or T21 source-pattern success must not be read as `VERIFIED_WITHIN_SCOPE` for the current full target.

## 3. The strongest concrete result: Payy

Payy's `agg_agg` circuit combines inner proofs and exports a 1,000-word public message array. At the earlier revision, it binds the used prefix to the inner messages but leaves the remaining outer words unconstrained. The final aggregation layer carries those words forward. The Solidity consumer can interpret the added tail as a burn and pay tokens.

The experiment used these exact revisions:

| Role | Payy commit |
| --- | --- |
| Earlier circuit, used for the candidate proof and local transfer | `c4d2c9021b8fb9988816eb6987a734b830bfce15` |
| Check-added circuit, used for repair validation | `dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36` |

In T18, a legitimate mint registration supplied 100 synthetic token units through the normal funding path. The candidate proof also carried a burn-shaped tail with no backing inner burn transaction. Settlement succeeded through the real verifier and consumer: the consumer's token balance changed **100 → 93**, and the designated burn address changed **0 → 7**, checked directly with `balanceOf`. The mint-only control left both balances unchanged at settlement.

At the check-added revision, the candidate failed the circuit's `assert_message_tail_zero` during witness generation, before a proof could be produced. A separate legitimate mint still settled using that revision's own key and verifier. This validates the repair against the specific candidate, not every possible circuit path.

All execution used locally owned prover, validator, and minter identities and a local test token. No authorization gate was bypassed. This does not establish an attack by an arbitrary unauthorized caller. The source issue was already publicly disclosed; deployment history and advisory release-label mapping remain unresolved. Read the [Payy case study](payy-case-study.md) for the complete reproducibility path and [T20](../reports/T20.md) for claim attribution.

## 4. Current detector results and why T22 is unfinished

T22 translates selected compiled constraints into solver queries. The current development suite uses **N=8 bounded variants**, not the full 1,000-word production array and not nine independent applications. `agg_utxo` is Payy's sibling aggregation circuit. The mutations and alternate coding forms test whether the analyzer handles missing checks and equivalent valid implementations.

The original v2 sweep matched only 2/9 expectations and produced a confirmed analyzer false positive on the running-flag control: specialization dropped an implied zero constraint from the queried goal. V3 fixed that probe error and recovered two previously missed mutations. Its complete frozen nine-case outcome is:

| Case | T22-v3 verdict |
| --- | --- |
| Earlier `agg_agg` | `VIOLATION` |
| Check-added `agg_agg` | `UNKNOWN` |
| Existing `agg_utxo` | `UNKNOWN` |
| Tail guard changed from `>=` to `>` | `VIOLATION` |
| Final tail slot skipped | `VIOLATION` |
| Tail helper deleted | `VIOLATION` |
| Equivalent running-flag control | `UNKNOWN` |
| `agg_utxo` tail loop deleted | `UNKNOWN` |
| `agg_utxo` else-branch control | `UNKNOWN` |

**Total: 4 `VIOLATION`, 5 `UNKNOWN`, 0 `VERIFIED_WITHIN_SCOPE`; 4/9 frozen expectations matched.** All nine cases compiled; seven solver regressions and four SAT-probe replays passed. The runner exited 1 because five expectations remained unmet. Six general queries timed out; nine failed allocation under the frozen 4 GiB cap. The `agg_utxo` analysis also retains unmodeled cryptographic dependencies. [T22-v3](../reports/T22-v3.md).

The four violations are constraint-model findings under stated assumptions, including satisfiability of omitted components. They are not four newly validated end-to-end exploits. UNSAT for an empty-prefix probe only rules out that restricted counterexample; it does not establish the complete prefix/tail property.

V4 investigated the check-added control. A fixed-stream branch gave conditional non-vacuity SAT in 79.9 seconds, but all three full Boolean-rank queries still timed out at 300 seconds each. Even a goal-only reduction with no ACIR assertions timed out. That reduction isolates an encoding difficulty; it does not decide the original circuit. The check-added verdict remains `UNKNOWN`. [T22-v4](../reports/T22-v4.md).

Here, **non-vacuity SAT** means the modeled premise admits at least one execution; **prefix/tail UNSAT** means the corresponding query found no violating assignment within its declared bounds and assumptions. Timeouts, allocation failures, unsupported dependencies, and missing artifacts never establish safety.

## 5. Work in progress beyond the latest report

The inspected repository was at `41093d1905e44af347e1d39cd6718728d4157c77`, which includes the [T22-v5 protocol](../scripts/t22_v5_protocol.md), [compact encoding](../scripts/t22_v5_compact.py), and [reduction script](../scripts/t22_v5_reduce.py). However, **there is no `reports/T22-v5.md`**, and `scripts/t22_v5_audit.py` is an existing untracked file. The README/checkpoint's last formally reported experiment is v4. This is an unfinished reporting and evaluation boundary, not a completed new milestone.

Saved local records under ignored `results/raw/T22/35_v5_compact/` show:

- The compact specification walk passed 65,536 category-vector comparisons. This checks the specification rewrite, not equivalence to the circuit.
- The three `primary_check_added/` general queries timed out at approximately 300 seconds each (solver exit `-9`).
- `reductions/prefix_320_confirmed.smt2.json` records a 300.459-second timeout for a reduction retaining 320 original ACIR assertions plus the goal. `31_blocker_audit.json` records a passing provenance audit, including 10 retained assertions connected to the goal.
- The 256-assertion neighboring reduction returned SAT in 154.377 seconds. The 320-assertion example is therefore a preserved bounded blocker, not a proven globally minimal blocker or a verdict on the full query.

These are observations from saved files, not newly rerun or formally promoted results. No running-flag primary output was found in this v5 evidence directory, although the protocol calls for both controls. A collaborator should reconcile the remaining protocol obligations and reporting before calling v5 complete. None of these records changes the formal v3/v4 verdicts.

## 6. What remains unproven, and the next task

The local reproduction establishes that the motivating failure mechanism is real under its stated setup. It does **not** establish that BindCheck could discover an unknown instance. Payy and all authored fixtures are development cases. There is no held-out application result, completed general soundness theorem, or demonstrated advantage over equal-information circuit-only, cross-boundary, or generic-verification baselines. The simple T07 baseline comparison found no advantage; T14 likewise found the manually specified mint property expressible directly in Solidity.

The contract's broader goals still require automatic implementation-fact recovery, supported consumer semantics, independent historical-case feasibility, frozen held-out families, property-specific negative controls, specification-sensitivity tests, and measured analyst and computational cost. AI-authored annotations are not independent human validation. No prevalence or submission-readiness claim follows from the current case count.

**Recommended next bounded task: finish the T22 control-feasibility work and its v5 evidence handoff.** First reconcile the saved v5 artifacts with its frozen protocol, explicitly recording any missing run or deviation. Preserve them before any new encoding change. Then evaluate an ACIR-backed summary or solver encoding on the unchanged N=8 check-added and running-flag controls.

**Completion criterion:** produce non-vacuity SAT and prefix/tail UNSAT for **both controls**, within 300 seconds and 4 GiB per query, with a checked relationship to the unchanged ACIR and all assumptions exposed; or close the bounded attempt with a provenance-audited ACIR-bearing blocker and an explicit `UNKNOWN` outcome. Record all six planned query outcomes or explain each omission, exact commands, versions, hashes, exit statuses, and limitations in a new versioned report. Update README and the existing [project checkpoint](project-status.md) node/log when that research task is reported. Completing a blocker report does not complete T22.

Independent transfer remains deferred until the primary controls are acceptable. After that gate, the next research stages are independent cases, sensitivity and equal-information comparisons, and an evidence-based decision about the paper's contribution.

## 7. How to use and share this handoff

For orientation, **share this summary first**. Include the [research contract](research-contract.md) when the recipient needs to review scope, threat model, or evidence rules. For technical review or continuation, share the repository as well and use these entry points:

| Need | Start here |
| --- | --- |
| Research rules and the intended bounded formal target | [Research contract](research-contract.md) |
| Current status and task dependencies | [README](../README.md), [checkpoint tree](project-status.md) |
| Real-proof reproduction, prerequisites, and exact command sequence | [Payy case study](payy-case-study.md), then [T18](../reports/T18.md) and [T19](../reports/T19.md) |
| Detector results, frozen inputs, commands, tool versions, and audits | [T22-v3](../reports/T22-v3.md), [T22-v4](../reports/T22-v4.md), [v5 protocol](../scripts/t22_v5_protocol.md) |
| Implementations | [Trace checker](../bindcheck/checker.js), [source analyzer](../scripts/t21_tailcheck.py), [v3 ACIR analyzer](../scripts/t22_v3_tailspec.py) |
| Historical rationale | [Research guide](../BindCheck_Research_Guide.md), [16 October update](../2026-10-16-research-update.md); their old schedules and next steps are not the active queue |

Generated proofs, dependencies, and raw logs are ignored by Git. A clone includes reports and reproduction scripts, not the historical raw evidence; reviewing the exact saved runs requires a separately supplied evidence archive. Regenerated proofs can have different bytes. The full Payy reproduction was recorded on macOS arm64 and its fetch scripts use platform-specific downloads; T22's solver work was recorded on Linux. An independent clean-machine reproduction has not been established. Follow the linked prerequisites rather than assuming one command reproduces everything on any machine.

**Contract assessment:** no substantive change to `research-contract.md` is needed for this handoff. Its scope, two properties, evidence rules, and T22/independent-case gate still fit the reported state. Its purpose is to keep research decisions stable, so changing experimental progress belongs in reports, README, and this dated overview. Any future semantic change must follow the contract's dated change-control rule.

**Owner action:** send this file for a project overview; add the contract and repository for a technical handoff. If the recipient will continue the experiments, include the existing v5 work and available raw evidence with their provenance, and ask them to start with the bounded control-feasibility task above. Authors should review the claims and annotations before using them in a paper or presenting them as independently validated results.
