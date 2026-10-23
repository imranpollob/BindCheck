# D1 development plan

Date: **23 October 2026**. Status: **D1-00 through D1-03 complete; D1-04 NEXT**.

This is the execution roadmap for the isolated D1 worktree. The [research contract](../research-contract.md) controls scope and claims; [D1-00](../../reports/D1-00.md) records preservation and validation.

## 1 Decision

**Continue from `/home/pollmix/Coding/BindCheck`, using an isolated D1 branch/worktree and a new analysis core inside that repository. Do not start an unrelated empty project.**

The existing repository contains useful proof-generation and consumer-replay harnesses, exact historical cases, solver infrastructure, and regressions for previous analysis mistakes. Rebuilding these would consume time without answering the new scientific question. However, the current tail checker should not become the D1 architecture simply by accumulating more special cases.

The intended arrangement is:

- Existing checkout: preserve the staged work, historical scripts, reports, and raw evidence.
- Created development worktree: `/home/pollmix/Coding/BindCheck-d1`, on a new `research/d1` branch in the **same Git repository**. Created during D1-00; shared history, separate working files and index.
- New D1 package: isolated from frozen T21/T22 implementations, with adapters for reusable components.
- Literature repository: continues to hold the reviewed prior work and proposals. Copy a versioned D1 brief and its source hash into the development worktree so execution does not depend on a sibling directory.

Worktrees share Git history but do not automatically inherit staged changes, ignored toolchains, proof fixtures, or raw logs. Reuse must therefore be explicit and reproducible. Do not copy the entire old working directory or rely on incidental caches.

## 2 What the current checkout actually provides

Read-only intake observed HEAD `41093d1905e44af347e1d39cd6718728d4157c77` on `main`. Three changes were staged: modified `README.md`, added `docs/research-and-work-summary.md`, and added `scripts/t22_v5_audit.py`. That earlier intake was read-only. D1-00 subsequently created the new branch/worktree and carried these changes into its index; the original checkout and staged state remain unchanged. New documentation is unstaged in the D1 worktree.

| Existing component | Decision | Reason and condition |
|---|---|---|
| `docs/research-contract.md` and `AGENTS.md` | Retain; add a dated D1 contract revision in the development branch | Authorization, coverage, noncircular specifications, and explicit UNKNOWN already fit D1. Sharpen the contribution and supported fragment rather than replace these principles. |
| `payy-harness/`, `payy-consumer/`, T08–T20 records | Reuse as development/replay infrastructure | They document a known case and its controls. Recheck prerequisites and hashes before relying on executability. They provide neither a new defect nor independent transfer evidence. |
| `scripts/t22_v3_tailspec.py` | Reuse selected mechanics through tested adapters | It contains ACIR parsing, dependency traversal, field encoding, solver execution, and audit behavior. Its stated target is the tail property; stream mappings and derivations are analyst assumptions. It is not an existing joint producer/consumer extractor. |
| `scripts/t22_v3_checks.py` | Preserve and port relevant regressions | Covers dropped implied constraints, skipped slots, component pruning, and unsupported black-box behavior. These are important soundness regressions, not an independent evaluation corpus. |
| `scripts/t22_v5_compact.py` and protocol | Preserve as a frozen engineering baseline | The implementation explicitly requires the particular two-stream semantic specification and N=8. The compact specification encoding is not a proved producer summary. |
| `bindcheck/checker.js` | Keep as a trace oracle/baseline adapter | Its header explicitly limits it to observed executions. `NO_VIOLATION` on one trace must not become `VERIFIED_WITHIN_SCOPE` over untested executions. |
| T07 direct Foundry baseline | Retain as a serious competitor | Its report records agreement on 132 executions and no demonstrated checker advantage on that property. This was read, not rerun during intake. |
| T21 source-pattern detector | Freeze as historical comparison | In-sample pattern rules cannot supply D1's claimed automatic semantic recovery. |
| Historical task runners | Reuse cautiously in fresh output namespaces | Some runners delete files in their task output directory before rerunning. Never execute them against the sole preserved historical evidence. |

The current research contract is broadly aligned with D1. The important change is the **method claim and development priority**: from continuing a tail-query solver campaign to testing whether consumer-directed extraction and checked refinement add value over strong baselines. The source checkout README prioritized the summary/encoding repair and deferred transfer. The D1 worktree now adds early, independent target-availability screening and a finite stop decision.

## 3 Research objective and first supported scope

**Objective:** recover the relationship between actual producer constraints and consumer effects, then check independently specified authorization and obligation coverage using consumer-directed, proved summaries and counterexample refinement.

**Novelty hypothesis:** the consumer observations help select useful relations and refinements, improving solved obligations, precision, or total analyst/computation cost beyond an equally informed modular verifier. Modular summaries, specifications, and selective unfolding themselves are prior work. See [D1 brief](brief.md) and [versioned proposal and bibliography](reference-proposal.md).

Start with one bounded arithmetic/array producer, its actual public-input decoder, and a non-reentrant settlement path. Freeze compiler versions, field, batch bounds, call semantics, initial states, and history length. Use the existing N=8 controls for historical comparisons; a smaller fixture is useful for correctness testing but does not discharge those controls.

The initial prototype may analyze a single transition from an explicitly admitted state with a locally replayable initialization. Label its guarantee accordingly. General bounded history exploration is a separate increment; a guarantee over one chosen pre-state is not a guarantee over all reachable states.

Initial protected effects are transfers or state writes with asset, amount, beneficiary, domain, and occurrence identity. Represent authorization and coverage separately. Start with explicit one-occurrence discharge; add splitting, aggregation, and deferral only with defined policy semantics and controls. An unimplemented transformation yields UNKNOWN, not a false violation.

No general EVM verifier, arbitrary recursion solver, second circuit language, frontend dashboard, or broad vulnerability campaign is needed for the initial decision. Unsupported assembly, proxies, reentrancy, token behavior, or cryptographic operations remain visible scope limits.

## 4 Proposed implementation structure

Use Python for the new analysis orchestration because the existing ACIR/solver code is Python. Keep Rust and Foundry at the proof/replay boundary. This is a repository-local engineering choice, not a research contribution. This is a proposed layout, not implemented code. Pin runtime/toolchain dependencies before D1-01 execution or D1-03 implementation; D1-00 only used Git and Python standard-library filesystem tools.

```text
src/bindcheck_d1/
  artifacts.py                 versioned identities, hashes, source locations
  policy.py                    permissions, obligations, legal transformations
  result.py                    verdict, scope, evidence grade, reason codes
  ir.py                        producer relations, decoding, transitions, effects
  frontends/acir.py             supported producer extraction
  frontends/solidity.py         bounded consumer extraction
  analysis/observations.py     effects and backward dependencies
  analysis/summaries.py        summary obligations, discharge, provenance
  analysis/refinement.py       candidate concretization and refinement
  backends/                    solver adapters and resource accounting
  replay/                      original-proof and consumer replay adapters
cases/d1/                      manifests and policies; no expected labels in input
protocols/d1/                  frozen experiments and baseline configuration
tests/d1/                      meaningful semantic and soundness regressions
reports/D1-xx.md                one evidence report per bounded task
results/raw/D1-xx/             ignored logs and generated artifacts
```

Each module has a specific contract:

1. **Artifact intake** ties source, compiled relation, ABI, program/key, and consumer configuration together. Missing correspondence is a result limitation, not a guessed association.
2. **Producer extraction** exposes exact field constraints and supported operations with locations. Preserve the old parser as a version-pinned adapter initially; audit skipped functions, unsupported operations, and printed-ACIR assumptions before broadening its scope.
3. **Consumer extraction** uses pinned compiler output to recover decoding, guards, loop bounds, verifier arguments, and supported effect expressions. Begin with a documented Solidity AST subset and explicit external-call model. Compiled-artifact correspondence remains a stated compiler assumption; trace agreement tests alone do not prove translation correctness.
4. **Boundary IR** represents field values, integers/bitvectors, bytes, state, and occurrence records distinctly. Canonicality and range facts become obligations before crossing representations. Unsupported mixed-theory combinations return UNKNOWN.
5. **Summary checker** establishes a summary from a component relation under explicit preconditions. Each caller must establish those preconditions. A supplied semantic policy cannot silently assert an implementation summary. Cache keys include all artifact, policy, bound, and assumption identities.
6. **Refinement engine** starts from consumer observations, solves a conservative abstraction, checks candidates against retained concrete relations, and chooses the responsible summary to strengthen or unfold. Abstract SAT alone is not a confirmed counterexample.
7. **Replay adapter** produces the real proof where feasible and executes the unchanged consumer with the modeled roles and initialization. Rejected candidates remain rejected candidates.

The new result envelope retains the research contract's three verdicts: `VIOLATION`, `VERIFIED_WITHIN_SCOPE`, and `UNKNOWN`. Attach separate `evidence_level`, assumptions, bounds, non-vacuity result, provenance, and reason codes. For example, `SPECIFICATION_UNRESOLVED` is a reason for UNKNOWN, not a fourth verdict. A concrete model violation and a real-proof replay are different evidence grades. A legacy trace pass is only an observation.

## 5 Ordered development tasks and completion criteria

| Task | Work and deliverables | Completion criterion |
|---|---|---|
| **D1-00 — Preserve and align** | Capture repository/index state and hashes; create isolated worktree; review and carry necessary staged work without touching the original index; add D1 brief, contract change log, README roadmap, and checkpoint entry | Original checkout and staged diff are unchanged; baseline is reproducible from a manifest; D1 scope, verdict semantics, task order, and provenance are explicit. No code is advertised as newly validated. |
| **D1-01 — Close the T22 reporting boundary (DONE)** | Audit existing v5 records against its six-query protocol; identify missing executions and prerequisites; run only needed permitted primary queries in a fresh namespace if inputs are available; write a versioned closure report | All six slots have an evidenced outcome or an explicit missing/blocked designation. Keep 300 seconds/query and 4 GiB. UNKNOWN is a valid closure outcome; do not prolong the old campaign to obtain a favorable verdict. |
| **D1-02 — Independent target intake** | Screen two non-Payy families for usable source/license, public-input/consumer correspondence, honest proving path, policy source, and architectural independence | At least one plausible transfer target is selected before algorithm tuning. Record failures and unresolved availability. Screening is not a successful build or transfer result. |
| **D1-03 — Minimal joint semantics** | Implement artifact/result/policy schemas and a small boundary IR; extract one producer/consumer path; construct a direct joint query and independent replay oracle | A real-constraint faulty development case has a concrete model and executable replay; an honest/repaired case has non-vacuity and a scoped no-violation result. Unsupported operations and missing assumptions reliably produce UNKNOWN. Synthetic success is labeled synthetic. |
| **D1-04 — Baselines before optimization** | Run direct Foundry tests, monolithic joint solving, and a straightforward CIVER-style summary adaptation on the same facts, bounds, and policy | Comparable result matrix and measured preparation, annotation, query, proving, and replay costs. The modular adaptation is labeled as an adaptation, not a reproduction of CIVER unless actually reproduced. |
| **D1-05 — Consumer-directed refinement** | Add observation-directed summary selection, proof obligations, candidate concretization, and targeted unfolding; state the preservation argument | Demonstrate at least one spurious abstract candidate being rejected/refined without removing a real violation, and preserve clean controls. Show what mechanism differs from D1-04. |
| **D1-06 — Frozen feasibility comparison** | Test D1-05 against D1-04, including the N=8 repaired and running-flag controls and meaningful legitimate behaviors | Full-query outcomes are reported without substituting probes or relaxed queries. Demonstrate a useful checking/extraction advantage or conclude that the current method does not support the contribution. |
| **D1-07 — Independent transfer** | Freeze algorithm and policy procedure; apply to the selected independent family; record every manual adapter fact and correction | Honest/fixed controls and a meaningful boundary property work without new defect-specific rules. Any post-result tuning converts this family to development data and requires a new holdout. |
| **D1-08 — Full evaluation, conditional** | Expand to at least three independent families or narrow the claim; freeze protocols, ablations, artifact replay, and evidence grading | Defensible results on scope, precision, UNKNOWN, cost, transfer, controls, and strongest baselines; no inflated count from related variants. |

D1-02 is logically independent of the T22 audit and should not wait for a successful solver result. After selection, honest-path setup can proceed with recorded effort; distinguish this from defect-specific analysis and tuning. This plan does not authorize delegating to other agents or contacting maintainers.

### Acceptance tests that matter

- Preserve the regression where specialization previously discarded an implied zero constraint.
- Check the last slot, duplicate occurrences, legitimate ignored padding, and caller-enforced bounds.
- Reject summary reuse when source, key, policy, bounds, or preconditions change.
- Distinguish a non-vacuous clean case from an inconsistent model that trivially yields UNSAT.
- Preserve field-versus-integer and byte-decoding differences; do not silently normalize them away.
- Check rollback and committed effects rather than counting a reverted transfer as executed.
- Confirm that a case label or expected verdict cannot reach the analyzer's input.
- Use independent small finite examples to validate encodings, plus actual-constraint/proof controls. Finite checks do not prove arbitrary extraction fidelity.

## 6 Effort budget and stop decisions

Use the proposal's **ten-researcher-day initial feasibility budget** as a decision budget, not a promise to finish D1-00 through D1-07. New consumer extraction and independent proving paths may make full transfer impossible in that period. If so, report that the gate was not achieved; do not redefine completion after seeing results.

| Budget slice | Required decision evidence |
|---|---|
| Days 1–2 | Preserved baseline, aligned D1 brief, and honest T22 closure/missing-evidence inventory |
| Days 1–3, independent intake work | At least one plausible independent target, or an explicit availability blocker |
| Days 3–7 | Small faithful joint model and strongest simple baselines; one measured refinement experiment only if prerequisites pass |
| Days 8–10 | Frozen comparison and transfer attempt if ready; otherwise a documented decision on the missing prerequisite |

Continue beyond this gate only when the repaired controls, concrete faulty case, baseline comparison, and transfer evidence support further investment. Initial scaffolding is not a pass. Close unfinished old results as UNKNOWN and give any new summary encoding a separate protocol and identity.

**Stop or substantially narrow D1 if:** the modular adapter ties at comparable total cost; most producer/consumer correspondence is manually asserted; fixed controls remain unresolved within the supported fragment; alleged attacks vanish under correct reachability or caller assumptions; or no independent honest proof/consumer path is practical. The presence of sunk implementation effort does not change these criteria.

If proof/consumer paths and meaningful policies are available but static composition remains intractable or unnecessary, assess D2 separately. A switch is a research decision, not an automatic expansion of this task. Do not invest in D3 merely to escape a difficult solver instance.

## 7 Evaluation design to freeze before claims

**Common bug-finding comparison:** all methods receive the same policies, actor capabilities, initial states, valid-proof seeds, and implementation facts. Count distinct confirmed root causes and time to validated effects, including setup, proof generation, and manual effort. Do not claim superiority because a native baseline lacks a frontend that D1 was given.

**Verification comparison:** compare monolithic, generic modular, and consumer-directed queries under identical bounds. Report non-vacuity, solved obligations, conditional assumptions, UNKNOWN, wall time, memory, and extraction coverage. Foundry test success is not equivalent to a verification guarantee; compare the shared tasks and the different guarantees separately.

**Ablations:** consumer observation selection; checked summaries; refinement strategy; occurrence identity; state/caller constraints. Removing a semantic safeguard can change the property, so record resulting false candidates rather than presenting every ablation as a speed measurement.

**Generality:** Payy and its nine variants remain development data. A family already discussed through defect details is not fully blind; record exposure and reserve an untouched root cause or another family. Publish all attempted targets, exclusions, build failures, corrections, and failed candidate proofs.

**Research integrity:** only a human researcher can provide independent policy/label review. AI-generated labels are not independent annotations. Preserve exact commands, tool versions, hashes, query limits, raw results, and repair controls. Run on owned local environments and synthetic assets. No live-chain or external communication action is part of this plan.

## 8 Current task state and handoff

| Task | State | Dependency |
|---|---|---|
| D1-00 | DONE | Preservation and documentation checks in the task report |
| D1-01 | DONE | [Closure report](../../reports/D1-01.md): six accounted slots, three preserved plus three new timeouts; all UNKNOWN; original successful-solver milestone unmet |
| D1-02 | DONE | [Two-family screen](../../reports/D1-02.md) left selection unresolved; [continuation 01](../../reports/D1-02-continuation-01.md) selects hashcloak Semaphore-Noir with qualifications (unpinned bb CLI, unvalidated artifact/VK correspondence, unfrozen batch policy); Aztec v6.0.0 not selected. No build/proof run |
| D1-03 | DONE | [Report](../../reports/D1-03.md): synth-faulty→VIOLATION (replayed), synth-repaired→VERIFIED_WITHIN_SCOPE (replayed non-vacuity); 15 regression tests pass |
| D1-04 | NEXT | D1-03 faithful joint semantics |
| D1-05 | WAITING | D1-04 fair baseline and cost accounting |
| D1-06 | WAITING | D1-05 justified refinement; frozen comparison protocol |
| D1-07 | WAITING | Frozen mechanism and an independent honest proving path |
| D1-08 | WAITING | Feasibility and transfer justify a broader study |

**D1-03 is complete.** The joint-semantics pipeline validates on authored synthetic
fixtures: synth-faulty yields VIOLATION with a replayed model (unauthorized burn
in the unconstrained tail); synth-repaired yields VERIFIED_WITHIN_SCOPE with a
replayed non-vacuity witness. All 15 regression tests pass. See [D1-03 report](../../reports/D1-03.md).
The consumer contract (Solidity frontend) was not exercised; producer-side joint
encoding and nargo replay carry the verdicts. Solver times are within limits but
suggest scaling work for N=1000.

D1-02 closed through a [frozen continuation](../../reports/D1-02-continuation-01.md):
hashcloak Semaphore-Noir is the reserved transfer target with stated qualifications.

**Next: D1-04 baselines.** Stop for review after D1-04.

## 9 Provenance and limits

The original literature plan and assessment are preserved as archival inputs, identified by [literature-inputs.json](../../metadata/d1/literature-inputs.json). The [reference proposal](reference-proposal.md) and its figures are exact copies with local working links. The [baseline manifest](../../metadata/d1/baseline.json), [workspace guide](workspace.md), and [D1-00 report](../../reports/D1-00.md) identify the source checkout and carried changes. The original plan is superseded for task state by this roadmap; its scientific gates are retained.

Code facts and historical outcomes in Section 2 come from repository inspection and existing reports, not new executions. No fresh build, complete source audit, established novelty, or D1 evaluation success is claimed. New code directories above are planned, not created. The existing repository supplies reusable infrastructure, not an already implemented consumer-directed analyzer.
