# D2 Steps 11–14 downstream dependency audit

Date: 2026-11-02

Status: **READ_ONLY_AUDIT_COMPLETE / STEPS_11_14_NOT_EXECUTED / GATE_B_NOT_EVALUATED**

Research verdict: **UNKNOWN**

Controlling disposition: `protocols/d2/d2-11-14-dependency-disposition-v1.json`, SHA-256 `d2acbf45720baf425fc7b71847b75de1db48195b1ca4a4604aaa0e069c6fdf78`.

## Outcome

The D2-07 authorization ends at the exposed, mechanical Steps 8–10 prototype. It does not authorize Step 11 compatibility implementation, Step 12 benchmark finalization, Step 13 causal execution, or Step 14 comparison/freeze. This audit therefore performed no Step 11–14 run and created no raw namespace, score, proof/replay record, freeze, or Gate B decision.

Mechanically, the project can plan Step 11 against the exposed blocker inventory, prepare unresolved Step 12 fields and an opaque custodian handoff, specify the Step 13 evidence chain, and preflight Step 14 readiness. Executing any of those steps requires the applicable new authorization phase defined below. Unused capacity under the D2-07 numerical cap is not transferable authority.

## Authority and evidence bindings

The audit follows `docs/research-contract.md` revision 3 and Steps 11–14 of `../bindcheck-agent-playbook.md`. The following bytes control this disposition:

| Step | Report SHA-256 | Protocol SHA-256 | Authoritative seal | Independent verification |
| --- | --- | --- | --- | --- |
| 7 | `fcdff01dbadade6f7f28116e46ee2c6016fb2945767492c822acaef87a60f07a` | `3aab079da6c441a6a6bb95bc97e6d8e5dbeacf65472fb7902a96b905635303af` | `b9f0f1eb6b9aa1bb3ea8aaf1fba3c3939b3d70a787a57be92f3c4154fad50558` | PASS, 623/623, zero mismatches; verification SHA `c6191d8f2baa5817eb875c4287cbe8e73e23ebb8e55b6c6cb7f5364cf8cbb1d5` |
| 8 | `aaca4aa036a0604febd6869604e8dfcfc3709a72a15c8fa588717309316fd2cd` | `b529f9c12ca695cf4737a0f01f10f9f357216fea0f7505a42fc381614c6b04ba` | `d2195d93fc6e51458a994ecc63838935fb36bad275379ef15e43ca2f9c112343` | PASS, 92/92, zero mismatches; verification SHA `227b3f38fb4e4b2a742f5a9830445e612f6b09c04d4c31a294d18ccc8b917406` |
| 9 | `f7254e4ccb510a8ccfea9954cfd341c81620084147159a81dfa52c3f6595cf03` | `2a833bc150a21bfc82dc9847fe36c0f6e92e85a592cac771836bb9b0a717b04a` | `c678085afa6a73d0f8115d10055fb753bd024a174a38618cb0e5e6943661e8bd` | PASS, 40/40, zero mismatches; verification SHA `e7bf4373b5255bb4feda70e8c130e1250169b747b608739726524cdf1375d274` |
| 10 corrected run-02 | `848acceef83d32d5054e37686ff5bc3b94baa45c5618490a0fe8e41bb9db018a` | `910ce6464a947fa552be08d34a596d97b179669401305adc577676d5172ce3ec` | `c5bb3163283c7b16a0d341067c6f2c3f8fa9965d85ab13dc761d4e948fcf21e6` | PASS, 9/9, zero mismatches |

The corrected Step 10 module SHA-256 is `03251cd3b865a97c0c64736e6358749f786ad9d72c4983c8b9256d46acf8c373`; its run-02 summary SHA-256 is `0ebf8ca1f555701a6cbc942b0140df1440e7e5e60eb4daec87fd4bffb1dc42ab`. Run-01 remains preserved and passed its original seal, but it is superseded because the subsequent self-audit found condition-shape and mapping replay gaps and over-derived caller-linked relations. It is not controlling downstream evidence.

The current evidence is deliberately narrow:

- Step 8 establishes deterministic identities, provenance, and bounded mappings, not reviewed logical semantics or general equivalence.
- Step 9 has ten synthetic E0 rows; every effective state is `UNKNOWN`, and neither equal-input arm carries a security or comparative result.
- Corrected Step 10 exports zero relational `producer_guarantee` facts and zero derived eligible `consumer_used` facts. Both caller-linked producer authorization and consumer-effect relations are `MAY`, `OVER_APPROXIMATION`, `ANNOTATED` candidates.
- Dynamic addresses and paths, disjunction, ambiguous or unbound mappings, unsupported external calls, aggregation, splitting, and deferral remain `UNKNOWN`.
- Historical exposed E3/E4 evidence predates the new identity/P/O/E chain and cannot be relabeled as validation of that chain.

## Scope determination

D2-07 authorized only Steps 8–10 development of the shared compiler-backed object/context identity representation and common versioned P/O/E interface, using exposed material labeled `UNREVIEWED_DEVELOPMENT_FIXTURE`. It expressly withheld reserved access and retroactive Gate A rescoring. The authorization contains no Step 11–14 execution permission.

Accordingly, the boundary for this task was documentary: two audit artifacts, read-only inspection, and hash/JSON/diff validation. Analyzer and baseline execution, proof/replay, scoring, freezing, reserved access, and changes to shared living status files were prohibited and did not occur.

## Per-step disposition

| Step | Status | Possible now | Principal blocker |
| --- | --- | --- | --- |
| 11 — frontend compatibility | `DEFERRED_OUTSIDE_AUTHORIZED_SCOPE` | Read the D2-02 ranking and prepare a non-executing priority/budget proposal | No exposed-development implementation authorization or frozen resource budget |
| 12 — protocol and benchmarks | `BLOCKED_HUMAN_CUSTODIAN_AND_OUTSIDE_AUTHORIZED_SCOPE` | Inspect blank materials and enumerate unresolved fields | Missing reviewed policy, checked labels/controls, named custodian, isolated workflow, and new authority |
| 13 — causal validation | `DEFERRED_OUTSIDE_AUTHORIZED_SCOPE_AND_INPUT_BLOCKED` | Reconcile historical records and specify the required evidence chain | No eligible actual producer guarantee, eligible derived consumer reliance, reviewed policy, frozen Step 12 interface, or execution authority |
| 14 — final comparison/freeze | `NOT_READY_NOT_EVALUATED` | Read-only readiness/hash preflight | Steps 8–13 are not reconciled; Gate B criteria, fair arms, causal validation, executable reserved protocol, custodian commitment, and separate run approval are absent |

### Step 11

After explicit authorization, Step 11 can address the exposed `UNSUPPORTED_CONSUMER_AST_REQUIRED` barrier affecting 13 variants across two lineages and the artifact-bound Payy mappings affecting 12 nested variants in one lineage. Those counts overlap and must not be added. Each different mutant byte needs its own mapping evidence. Operation-specific summaries must propagate uncertainty; parser completion alone is not decisive coverage, and occurrence or caller-supplied links cannot become supported semantic facts.

### Step 12

After explicit documentation authority, Step 12 can version protocol v3, blank forms, manifests, denominators, evidence-grade rules, and an opaque custodian-handoff schema. It cannot be finalized until exact policy bytes are authored or adopted by a human and reviewed by a different human, policy ambiguities such as `commitHash` are resolved, historical labels and substantive safe controls are independently checked, a custodian and isolated reserved workflow are named, and the Step 13 interface and Gate B criteria are frozen prospectively. No reserved identities, sources, labels, or annotations may enter developer access.

### Step 13

After separate causal-validation authority, Step 13 can construct a staged exposed-development driver, challenge paired attacker-controlled witnesses with authenticated context fixed, and attempt version-matched construction, proving, verification, consumer execution, repair contrast, and protected-state checks. Entry requires at least one hash-bound, independently reviewed `MUST`/`EXACT`/`DERIVED`/`SUPPORTED` producer guarantee from actual supported semantics and a conservatively justified derived consumer-reliance fact tied to the protected effect. It also requires reviewed policy, a frozen Step 12 procedure, human confirmation of ambiguous case assumptions, and legitimate pinned local resources. Historical E3/E4 records are development inputs, not a substitute.

### Step 14

Step 14 requires a separate no-feature-change authorization after Steps 8–13 are merged and independently checked. The integrated analyzer and all applicable baseline arms must consume frozen equal information and policies. Gate B criteria, resources, retries, denominators, forms, and stop rules must be approved before output. The custodian must provide an opaque commitment without revealing reserved identities. The present audit does not produce a release freeze or any Gate B result.

## Preliminary Gate B criterion table

| Criterion | Readiness | Basis |
| --- | --- | --- |
| Reproducible integration | `INCOMPLETE` | D2-01 is sealed historical integration, but the Steps 8–10 prototypes have not been exercised through a current integrated application pipeline. |
| Defensible extraction | `INCOMPLETE` | Identity/integrity controls pass, but actual producer-guarantee and consumer-reliance derivations and a general extraction-soundness result do not exist. |
| Meaningful property coverage | `NOT_DEMONSTRATED` | Step 9 is E0/`UNKNOWN`; corrected Step 10 exports no eligible guarantee or reliance; policy is not human-reviewed. |
| Fair comparisons | `BLOCKED` | Byte-parity plumbing exists, but reviewed-policy scoring and complete generic/default and same-policy baseline arms do not. |
| Working causal validation | `INCOMPLETE_HISTORICAL_ONLY` | Historical exposed E3/E4 infrastructure exists, but Step 13 has not validated the current identity/P/O/E chain. |
| Fully executable reserved protocol | `BLOCKED` | Protocol v3, checked policy/labels/controls, a named custodian, isolated inputs, and an opaque commitment do not exist. |

Overall readiness is `INCOMPLETE_NOT_READY`. This is a preliminary dependency finding, not an official `PASS`, `FAIL`, or `INCOMPLETE` Gate B run. Gate B is **NOT_EVALUATED**.

## Human and custodian dependencies

The following roles or decisions remain external dependencies:

- a human policy author or explicit adopter, with primary-source provenance and exposure recorded;
- a different human reviewer for permissions, obligations, transformations, and assumptions before output;
- formal-method advisor/coauthor review of the property and supported fragment;
- independent primary-evidence checking of historical labels and substantive safe controls;
- two independent scorers plus a distinct adjudicator for the row-local judgments that need them;
- a user-named or confirmed reserved custodian who retains the blind boundary and authoritative seal;
- an isolated reserved-policy author assigned by that custodian;
- human confirmation of case-specific attacker capability, admissible initialization, policy, and legitimate resources;
- approval of exact Gate B criteria, budgets, retries, denominators, and stop rules before Step 14; and
- author inspection of all AI-generated artifacts, because agent review is not independent human review.

## Budget gap

D2-07 capped the combined Steps 8–10 mechanical and primary prototype at two researcher-days and eight machine-hours. Authoritative raw runner intervals are 0.137390 seconds for Step 8, 0.0723160419947817 seconds for Step 9, and 0.080048 seconds for corrected Step 10, totaling 0.2897540419947817 seconds. This sum excludes setup, tests, specification, review, and superseded-run time.

Human effort was null or explicitly not measured; zero cannot be imputed, so the researcher-day cap cannot be fully audited. More importantly, that cap neither authorizes nor budgets Steps 11–14. Each future phase needs prospectively frozen human, machine, dependency, network, retry, and storage budgets, including a stated reconciliation of any inherited cap.

## Stop rules

Future work must stop:

1. before Step 11–14 implementation or scientific execution without the matching effective authorization phase;
2. before any reserved identity, source, label, annotation, or evaluator output reaches developer access;
3. if `UNKNOWN`, unsupported behavior, failure, timeout, empty obligations, or unreviewed policy would be treated as safe or score-eligible;
4. if occurrence, dependency edges, names, or caller-supplied links would be promoted to derived guarantee/reliance without reviewed support;
5. if comparison arms do not consume byte-identical frozen facts, identities, policies, bounds, and validation opportunities;
6. if human roles, exposure, effort, or budget use would be imputed;
7. if Step 14 criteria, policy, labels, scoring, or denominators change after output; or
8. before release freeze if causal validation, executable reserved protocol, custodian commitment, or external authoritative-seal retention is absent.

## Exact future authorization phases

1. `PHASE_A_EXPOSED_COMPATIBILITY_AUTHORIZATION` covers Step 11 only. It must name the exposed barrier/lineages, semantic footprint, fail-closed rules, controls, and numeric resource budgets. It allows no scoring or reserved access.
2. `PHASE_B_PROTOCOL_HUMAN_CUSTODIAN_FINALIZATION` covers Step 12 and the Step 13 interface draft only. It requires named human roles and custodian isolation, checked label/control procedures, blank forms, an opaque reserved commitment, and prospective Gate B criteria.
3. `PHASE_C_EXPOSED_CAUSAL_VALIDATION_AUTHORIZATION` covers Step 13. It requires reviewed and hash-bound actual producer and consumer derivations, frozen policy/identity/effect chain, admissible state and attacker model, pinned legitimate resources, and final Step 12 validation rules.
4. `PHASE_D_GATE_B_FINAL_DEVELOPMENT_RUN_AUTHORIZATION` covers Step 14. It requires independently checked frozen Steps 8–13, fair executable arms, working causal validation, an executable reserved protocol, custodian commitment, sealed resources/procedures, and preapproved `PASS`/`FAIL`/`INCOMPLETE` criteria.

Each phase has its own entry and exit evidence in the controlling disposition protocol. Permission for one phase does not silently authorize the next.

## Verification and limits

This task created only the disposition protocol and this report. It did not create a `results/raw/D2-11-14*` namespace. It did not run analyzers, baselines, compilers, proofs, replay, scoring, or reserved-data operations; it did not freeze a release or change `README.md` or `docs/project-status.md`.

The protocol was JSON-parsed and checked for exact status, zero-execution boundary fields, corrected Step 10 v2/run-02 bindings, per-step dispositions, Gate B `NOT_EVALUATED`, and four future phases. Repository diff whitespace validation was run on the two owned files.

No reserved, transfer, capability, safety, prevalence, precision/recall, comparative, or venue-readiness claim follows. The research verdict remains `UNKNOWN`.
