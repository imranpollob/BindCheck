# BindCheck

BindCheck investigates whether the guarantees of an accepted zero-knowledge proof justify the effects a blockchain application executes. Under D1 research contract revision 3, the prospective target includes a **taxonomy of proof-to-execution binding failures** and **actionable cross-layer diagnostics**, alongside automated discovery and end-to-end validation from producer constraints, public-input decoding, and consumer effects. Consumer-directed selection and refinement remain a secondary efficiency question (RQ5), not an established advantage. D1P-30 supplies bounded development-case E4 validations and D1P-31 supplies a 30-mutant development benchmark, but comparative baselines, supported held-out transfer, and the overall capability claim have not been established.

The current integration checkout is the linked worktree
`/Users/imranpollob/Coding/bc/bindcheck-d1-paper` on `d1-paper`, currently at
base revision `544656abbfb535dcbe0f1157087240464f38cb0b` plus the uncommitted
D2 Steps 0–20 development, documentary, and artifact records. The current
bounded state is identified by the authoritative reports and seals summarized
below, not by the base commit alone. After Step 8, the live D2-01 replay has
exactly one expected mismatch among 8,134 members; an in-memory overlay of the
historical byte passes 8,134/8,134 and is not current-checkout equivalence.
This state includes
the corrected D1P-42 extent work, D1P-43 typed role work, integrated
D1P-33/D1P-36 transfer scans, D1P-34 application-neutral v1.1 freeze, D1P-35
v1.2 format/location change, D1P-31 evaluation/contract revision, D1P-30 tool,
mutation benchmark,
D1P-22 baselines, D1P-21A/B, D1P-20, D1P-19, D1P-17, and the merged Lane C
taxonomy/extraction work. The linked
worktree was originally established from `chatgpt-codex` revision
`cce1a966eb84e8e9819c6f658ca4ce07fd670036`.
[D1P-00](reports/D1P-00.md) records the branch/worktree baseline and the
source-inspected selective-reuse review of `claude-code`; the
[integration plan](docs/d1-paper/integration-plan.md) controls prospective
paper integration. The earlier independent Linux checkout description remains
historical context in the [workspace preservation guide](docs/d1/workspace.md).
Start with the [D1 brief](docs/d1/brief.md) and [development roadmap](docs/d1/roadmap.md).
[D1-00](reports/D1-00.md) records the original D1 preparation and preservation checks.

Start with the [research contract](docs/research-contract.md). It is authoritative for the research questions, threat model, scope, specification boundary, and evidence rules. The [living project checkpoint tree](docs/project-status.md) shows the path from current work to a possible paper submission without replacing the underlying evidence. The [Payy case study](docs/payy-case-study.md) gives the pinned versions, commands, expected outcomes, evidence locations, and limits for the independently built local reproduction of a publicly disclosed message-tail flaw.

[D1P-INT1](paper/contract-revision-proposal.md) applies the approved capability-framing revision prospectively on 27 October 2026. It adds automated-discovery and automated-validation research questions, the E0–E4 evidence ladder, generic/default plus same-policy baseline arms, and a four-part capability gate. [Revision 1](docs/history/research-contract-2026-10-23.md) is preserved byte-for-byte. No earlier result is relabeled or rerun; D1P-07, D1P-09, D1P-10, D1-01/T22 and the historical synthetic results remain evidence about the former efficiency hypothesis, now secondary RQ5, and do not count as capability evidence.

D1P-31 applies research contract revision 3 prospectively on 28 October 2026.
It adds the taxonomy and actionable-diagnostics candidate contributions and
the approved core boundary-analysis claim. [Revision 2](docs/history/research-contract-2026-10-27.md)
is preserved byte-for-byte. No prior report, evidence grade, or verdict is
relabeled or rerun.

For a shareable introduction to the project and completed work, use the [research and work summary](docs/research-and-work-summary.md), dated 22 October 2026. It separates demonstrated results and open research claims at that historical checkpoint; the D1 roadmap now controls the next task.

The [research guide](BindCheck_Research_Guide.md) and [16 October progress update](2026-10-16-research-update.md) are historical planning and progress records. They remain useful context, but their evidence status and schedules may have been superseded.

The principal directories are `circuits/` and `contracts/` for the small fixture, `bindcheck/` for the checker and specification, `payy-harness/` and `payy-consumer/` for the Payy experiment, `scripts/` for task runners, and `reports/` for evidence reviews. Generated proof data and raw logs are normally under the ignored `results/raw/` tree and are absent from a fresh checkout unless separately retained. Preserve and verify existing sealed namespaces; never overwrite them or describe missing bytes as regenerated evidence. Only a task-documented command may create a new, separately named namespace.

## `bindcheck-zk` CLI

The unified Circom/Noir and Solidity development analyzer is documented in
[TOOL-REPORT.md](TOOL-REPORT.md). It operates on local inputs only and emits
one JSON document per command:

```text
./bindcheck-zk analyze <repo-dir> [--circuit <path>]... [--consumer <path>]...
./bindcheck-zk analyze-bundle <sourcify-or-artifact-directory>
./bindcheck-zk baseline {slither,circomspect,picus,zkap} <repo-dir> ...
./freeze.sh
```

Missing artifacts, unsupported constructs, ambiguous matches, build failures,
and timeouts are `UNKNOWN`. `VERIFIED_WITHIN_SCOPE` names only the recorded
property and parsed artifacts; it is not an application safety verdict. The
current analyzer content hash is
`d8510859b918a5166d0f1629cf0d883e965fa0acb1be92a34987c24f1967ae13`.
It has been validated on 105 prospective controls and all 56 DEV rows without
path hints. EVAL remains unanalyzed and no dataset/freeze tag has been created;
the frozen 278-family sample has only passed a commit-metadata availability
check.

## Current status

- [T26](reports/T26.md) completes the one-shot evaluation harness without
  changing `bindcheck_zk/`. Exact preregistered selection yields 278 EVAL-only
  families; annotated dataset/analyzer/environment gates, at-most-once attempt
  markers, fixed budgets, shallow SHA fetches, per-family cleanup, four-verdict
  summaries with family bootstrap intervals, blind adjudication, and strict
  vulnerable/fixed recall orchestration are tested. A real five-family DEV
  fetch→analyze→baseline→summarize run completed with one E1 `VIOLATION`, four
  `UNKNOWN`, and zero retained clones; all baseline outputs remain `UNKNOWN`.
  A metadata-only pass resolved all 278/278 sampled commits, with zero clone or
  analysis. Recall expectations, human EVAL review, both tags, and the
  one-shot held-out run remain pending; capability and security remain
  `UNKNOWN`. Exact operating commands are in [eval/README.md](eval/README.md).
`2741c40e8acdd86d2a15aca1cfd9f1ef989558c749e25ec4d926c3a483fb94bd`.
It has been validated on 122 prospective controls and all 56 DEV rows without
path hints. EVAL remains unopened and no freeze tag has been created.

## Current status

- [T25](reports/T25.md) completes applicability/decision-rate reporting and
  the final DEV-only analyzer change before held-out execution. The three
  research verdicts are unchanged; `NOT_APPLICABLE` is a separate
  applicability value, and every `UNKNOWN` has a fixed reason code. All 122
  controls and 56 unhinted DEV rows pass with zero crashes. Among applicable
  rows, decided rates are P1 47.1%, P2 3.7%, P3 69.6%, P4 50.0%, and P5 8.7%;
  the low P2/P5 rates remain explicit. One new P1 balance-write warning is a
  true source property, the only expanded warning is an unchanged ambiguous
  F38 group, and three diagnostic false positives were removed before the
  controlling run. The [schema note](SCHEMA.md),
  [before/after ledger](reports/T25-full-dev-ledger.csv), and
  [warning changes](reports/T25-warning-adjudication.csv) preserve the exact
  result. EVAL/private P4 data remained unopened; no RPC, transaction, tag,
  merge, or push occurred. The exact-hash held-out run is next.
- [T24](reports/T24.md) completes the unhinted full-DEV coverage and warning
  adjudication task. All 56 rows complete with zero crashes; rows with at least
  one discovered triple rise from 11/56 to 46/56, and circuit-build success
  rises from 19/88 to 45/76. All 105 controls pass. The final 15 grouped
  warnings are author-reviewed as 13 true source properties and two unclear,
  with zero retained false positives; failures, caps, unsupported paths, and
  ambiguous correspondence remain `UNKNOWN`. The tracked
  [per-row ledger](reports/T24-full-dev-ledger.csv) and
  [adjudication table](reports/T24-warning-adjudication.csv) preserve the exact
  evidence. No EVAL/recall case, RPC, P4 address, transaction, contact,
  disclosure, or tag was used. Independent author review and the one-shot
  unchanged-hash held-out run are next.
- [T23](reports/T23.md) completes the unified `bindcheck-zk` construction and
  DEV validation task. All 74 prospective development controls pass (24
  inherited Track B plus 50 new P1--P5 controls), and the fixed three-case DEV
  run matches the declared P1 outcomes: SPSC `VERIFIED_WITHIN_SCOPE`, RacePass
  `VIOLATION`, and ZKredential `VIOLATION`, all E1 in this run. Slither,
  Circomspect, and Picus retain native diagnostics in the same JSON envelope;
  ZKAP is explicitly unavailable, and no baseline diagnostic is promoted to a
  cross-layer verdict. The held-out corpus was not read or run. Independent
  author review, exact-hash operational freeze, and one held-out execution are
  next; capability and ecosystem security remain `UNKNOWN`.
- [Integration dataset v2](dataset/REPORT-v2.md) completes the bounded,
  consumer-first, data-only inventory at revision `7353297`: 5,024 rows
  preserve all 897 v1 rows and add 4,127 EVAL rows, yielding 1,384 in-scope
  EVAL-only families after family deduplication. Exact consumer-source matches
  to the passive Sourcify export identify 277 verified deployments linked to
  86 GitHub repositories and make `verified-deployed` the strongest maturity
  stratum for 38 canonical EVAL families. The public recall inventory grows
  from 20 to 27 strict integration cases (47 total), and the greater-than-300
  threshold triggers a preregistered maturity-stratified sample plan. The
  append-only check preserves all old columns and all three duplicated v1
  `(repository, commit)` keys caused by repository renames; new family labels
  live only in `v2_*` columns. No analyzer, RPC, transaction, P4-seeded trace,
  or vulnerability search ran. Human label review and the EVAL tag remain
  pending, so this is not performance, prevalence, or security evidence.
- [Integration dataset v1](dataset/REPORT.md) freezes a 897-row source ledger
  (890 repositories; 56 DEV and 841 inventory-only EVAL), 774 conservative
  families, and a 40-case public recall set. No analyzer read an EVAL row.
  DEV-only Track B matches 24/24 prospectively declared controls, clears the
  SPSC recipient commitment false positive using a compiled-R1CS path, and
  retains the two prior E4 `VIOLATION` results. A passive Sourcify census finds
  1,027 exact-runtime verifier deployments; 43 have the default-G2-twice
  bytecode signature associated with `gamma == delta`. Their consumers and TVL
  are unresolved, so they remain private E1/`UNKNOWN` and deployment-specific
  work stopped without proof calls or transactions. This is dataset/tool
  feasibility, not EVAL performance or ecosystem prevalence.
- [Feasibility v2](feasibility/v2/REPORT.md) replaces the earlier zero-hit
  interpretation with a working Solidity-first screen and targeted real-proof
  validation. Across 50 exact repository revisions it screens 4,251 Solidity
  files and 42,668 functions, then reaches two local E4 `VIOLATION` results:
  RacePass reuses the same real age/KYC proofs to mint passes to two
  caller-selected recipients, and ZKredential uses a proof for one wallet to
  mint a caller-selected amount to another caller through unchanged contracts.
  The exact historical zkDrops vulnerable parent also reaches E4, while the P3
  source check fires on both zkDrops and Semaphore vulnerable revisions. A P4
  source census finds 16 default `gamma == delta` verifier files, one
  duplicate-IC file, and 33 verifier files without a detected public-input
  guard; all P4 entries remain E1/`UNKNOWN` because deployment correspondence
  was not established and none was tested. These are local/tool-feasibility
  results, not ecosystem prevalence, deployed exposure, independent-human
  validation, or a completed capability gate.
- [D2-20](reports/D2-20-review.md) completes a documentary evidence audit with
  status `EVIDENCE_AUDIT_COMPLETE_NO_NEW_EXPERIMENT`. Three PDF-only reviews
  reduce to 12 concerns: one future
  writing improvement, four existing-data analyses, five new experiments, and
  two enduring limitations. All 12 record zero factual contradiction to the
  qualified Step 18 status manuscript, so no manuscript correction, scored
  row, evidence grade, gate result, or verdict changed. Research remains
  **UNKNOWN**.
- [D2-19](reports/D2-19-artifact.md) supplies a
  **PARTIAL_DEVELOPMENT_ARTIFACT / FINAL_ARTIFACT_BLOCKED** package. A
  [fresh same-host evaluator](reports/D2-19-fresh-reproduction.md) reproduced
  all four requested profiles with zero unexpected mismatch. This is an
  engineering reproduction in a fresh AI session on the same checkout, not a
  sidecar, clean-container, fresh-machine, anonymous, or independent-human
  replication. No reviewed sidecar was supplied, and portable D2-01/D2-06
  container execution remains blocked.
- [D2-18](reports/D2-18-paper.md) completes the
  [evidence-led status manuscript](paper/d2-status-draft.md), claim map,
  versioned claim ledger, related-work matrix, source record, and IEEE S&P 2027
  readiness checklist. It centers `UNKNOWN`, Gate A `INCONCLUSIVE`, and the
  absence of scored, transfer, and human-review evidence. It is explicitly
  **NOT_SUBMISSION_READY**.
- The [Steps 11–14 dependency audit](reports/D2-11-14-dependency-audit.md) and
  [Steps 15–17 readiness audit](reports/D2-15-17-readiness-audit.md) are
  read-only dispositions: the scientific steps were **not executed**, Gate B
  is **NOT_EVALUATED**, and Gate C is **NOT_REACHED**. They add no score,
  reserved result, human judgment, or frozen release.
- [D2-07](reports/D2-07.md) completes Gate A only through the authoritative
  recovery packet: Gate A is **INCONCLUSIVE**, the objective subset and score
  table are empty, and zero analyzer or baseline arm was scored. The separately
  authorized [D2-08](reports/D2-08.md), [D2-09](reports/D2-09.md), and corrected
  [D2-10](reports/D2-10.md) work is bounded mechanical development evidence
  labeled `UNREVIEWED_DEVELOPMENT_FIXTURE`. Corrected D2-10 run-02 contains
  zero producer guarantees and zero eligible derived consumer-use facts. These
  steps remain unscored and **UNKNOWN**.
- [D2-05](reports/D2-05.md) is a completed
  `DRAFT_UNSEALED_DO_NOT_SCORE` protocol, while [D2-06A](reports/D2-06A.md) and
  [D2-06B](reports/D2-06B.md) complete construction and smoke testing only.
  Their baseline, transformation, comparator, and same-policy records are not
  comparative scores or security results.
- [D2-00](reports/D2-00.md) completes only the coordination and integrity
  foundation. Its manifest and seal controls are infrastructure evidence, not
  analyzer correctness or capability evidence.
- [D2-04](reports/D2-04.md) freezes taxonomy codebook v0.3.0 after auditing
  the exposed Lane-X seed pilot. It supplies blank primary-evidence packets,
  blank rating forms, a fresh-family sampling and independent-human annotation
  procedure, and a known-answer-tested multilabel agreement implementation.
  It creates no labels or agreement result: the prior author/AI comparison is
  development history, not inter-rater validation, and the taxonomy claim
  remains **UNKNOWN** pending a human-owned corpus freeze and fresh annotation.
- [D2-03](reports/D2-03.md) versions 22 current, stale, overstated, and
  unresolved claims; keeps D1P-41 and D1P-43 denominators separate; and
  refreshes primary-source positioning for ZKAP, CIVER, CCC-Check, SmartAxe,
  and the still-unresolved ELSA overlap. It narrows current `R-ROLE` evidence
  to E1 effect-role correspondence rather than policy authorization and defines
  equal-information distinguishing experiments. No novelty or capability claim
  is established.
- [D2-02](reports/D2-02.md) inventories the complete allowlisted exposed
  development population: three pinned revisions in two repositories and two
  architectural lineages, all analyzable as exact pairs. It keeps 30 authored
  variants and historical transfer attempts out of that denominator. Thirteen
  variants fail closed at the named consumer-AST gate; the 12 historical
  attempts cover eight unique projects but have no adjudicated family count.
  These bounded counts are not ecosystem prevalence or supported transfer.
- [D2-01](reports/D2-01.md) freezes and runs one integrated development
  interface over the corrected static/extent and typed-role analyses without
  adding a rule. On 30 exposed mutants it records **17 detected / 13
  unsupported / 0 misses / 26 warning objects**, with all six added detections
  restricted to predeclared `R-ROLE` associations. The corrected successor
  ablation is producer 3/7, consumer 2/7, union 5/7, and full 7/7, plus one
  `UNKNOWN` positive and one matching clean control; all eight role-target
  outcomes match. The 49-row table keeps those datasets and the exact Payy
  pair separate. Payy earlier emits `R-EXTENT` plus `R-CONSUMER`; check-added
  emits no `R-EXTENT` but retains a separate `R-CONSUMER` warning. The first
  sealed attempt is preserved `PARTIAL/UNKNOWN` after a sandbox cache-lock
  denial; the separately named recovery run uses the identical 8,134-file
  seal, passes all eight completion checks in 82.167 seconds, and remains
  **E1 / UNKNOWN**. This is exposed development evidence, not held-out
  transfer, capability, prevalence, security, or a D1 verdict.
- [D1P-42](reports/D1P-42.md) supplies an exact, replay-checked Payy recursive
  public-input certificate (1,005 inner words, two verified configuration
  constants, and 1,003 consumer words), per-word producer binding and consumer
  reliance conditions, and the development-only `R-EXTENT` rule. Independent
  synthetic controls establish all-path versus prefix-only binding and matching
  versus wider consumer reliance. Payy earlier now warns for
  `active_messages_count <= word_offset < messages_length`; check-added does not
  because its tail-zero constraints bind all message words. WT-C02's `max_fee`
  concern is **not a counting bug**: pinned has three proof-enforced plus three
  Brillig inventory occurrences and the mutant has zero of each. The unchanged
  30-mutant rerun remains **11 detected / 19 unsupported / 0 misses / 13 warning
  objects**. This is an unfrozen bounded implementation over development cases;
  no held-out, capability, security, or D1 verdict follows.
- [D1P-40](reports/D1P-40-correctness-audit.md) audits producer memory facts,
  exact public-input mapping, consumer effect dependencies and R-ANCHOR on
  compiled synthetic controls, then repairs five confirmed extraction defects.
  Dynamic MemoryInit dependencies now fail closed unless exact, shorter
  verifier arrays no longer invent a selector prefix, token effects require
  standard method identity plus signature, literal loop bounds exclude
  unreachable tail words, and anchor candidates precede guard matching. The
  30-mutant rerun changes **16 detected / 14 unsupported / 0 misses / 53
  warnings** to **11 / 19 / 0 / 13**: all five reclassified detections are Payy
  and all 13 surviving warnings retain their WarpToad identities. Payy's exact
  1,005-to-1,003 mapping and `messages[1..999]` dynamic-memory dependencies are
  **UNKNOWN**, not safe or missed. No held-out project, solver, proof,
  validation, live-chain action, capability, security, or D1 verdict follows.
- [D1P-36](reports/D1P-36.md) runs frozen BindCheck v1.2 once on eight
  projects: the four D1P-33 reserved targets as an explicit second attempt and
  four previously unseen, non-reserved candidates opened only after the v1.2
  freeze. Every analysis fails closed before an R-* rule completes: NullProof's
  beta.19 producer decodes but needs an unambiguous compiler-AST consumer
  relation; beta.3 and beta.25 remain unsupported; zkt-research/e-voting stop
  on `MultiScalarMul`; ZKPassport stops on `RecursiveAggregation`; and two
  beta.21 targets expose a named MemoryOp encoding gap. The result is **0
  supported, 8 unsupported, 0 warnings, and 0 validations**. Unsupported is
  not a miss or safety evidence. All frozen files remain byte-identical; no
  finding, disclosure, maintainer contact, live-chain action, capability,
  security, or D1 verdict follows.
- [D1P-35](reports/D1P-35.md) freezes BindCheck v1.2 on base `d981c64...`.
  Development-only builds of one synthetic circuit validate beta.15–18 as the
  existing beta.14 bincode layout and beta.19–21 as compact MessagePack with
  `current_witness_index`; public leaves and occurrence counts match beta.14
  and beta.22. Beta.3 remains a named unsupported distinct schema. Reporting
  now recovers unique verifier-call lines and selects the already recognized
  vulnerable payout effect. The unchanged 35-target D1P-34 rerun preserves
  every warning identity and **16 detected / 14 unsupported / 0 misses** while
  reducing emitted `:?` warning locations from six to zero. The rule
  conditions, thresholds, use counting, effect table and beta.14/beta.22/
  Solidity frontends are unchanged. This bounded format/location change does
  not establish support for every opcode schema, held-out capability,
  performance, security, or a D1 verdict.
- [D1P-33](reports/D1P-33.md) runs the first custodian-reserved held-out scan
  with frozen BindCheck v1.1 at exact commit `4382ee6...` / tag
  `bindcheck-v1.1`. All four projects are pinned and built locally: NullProof,
  privacy-preserving-IP-NFT, zkt-research, and ZKPassport's `outer_count_4`
  route. The one allowed analysis per project fails closed: beta.19, beta.3,
  and beta.21 are unsupported compiler identities, while beta.22 ZKPassport
  stops on named `RecursiveAggregation`. Thus the run records **0 supported,
  4 unsupported, 0 warnings, and 0 validations**; unsupported is not a miss or
  safety evidence. All 60 protected `src/`/`protocols/` files remain
  byte-identical to the tag. No tool/rule/effect-table change, maintainer
  contact, public disclosure, fork/live chain, capability conclusion,
  security finding, or D1 verdict follows.
- [D1P-34](reports/D1P-34.md) freezes application-neutral BindCheck v1.1 at
  base commit `9e9e71f3...` plus exact file hashes (no commit was permitted).
  That frozen tree is now recorded prospectively at commit `4382ee6...` and
  tag `bindcheck-v1.1`; the D1P-34 evidence itself is unchanged.
  The name/regex Solidity profile is removed: analysis now requires a
  source-hash-checked compiler-AST relation, recognizes the verifier by its
  proof-bytes/public-array interface, propagates word sources, guards, storage
  identities, replay writes, and shared signature-based effects, and fails
  closed without AST facts. Black-box outputs and memory-operation expressions
  now count as proof-enforced uses; Brillig is inventoried separately and
  `MemoryInit` remains definition-only. Full-size 1,005-leaf Payy artifacts
  replace N=8 in the five-target rerun and generic effects recover burn token
  calls. On the unchanged 30 mutants v1.1 records **16 detected, 14 unsupported,
  0 misses**, with 20 related and 33 unrelated warning objects; 0 are confirmed
  false. The unchanged validation index yields one preserved E4 and 52 E1.
  All data are exposed development data; no held-out transfer, capability,
  performance, vulnerability, security, or D1 verdict follows.
- [D1P-31](reports/D1P-31.md) evaluates frozen BindCheck v1 on all 30
  development binding mutants plus the five D1P-30 targets. It detects the
  named mutation in 13/30, records 16/30 as unsupported, and has one supported
  miss (PY-S02); the supported subset is 13/14. All 13 detections localize the
  named semantic boundary. Twenty-two warning objects are unrelated inherited
  Payy tail findings, not mutant detections or false positives. All 38 mutant
  warnings are passed to validation in operator-class order: comment/metadata-
  equivalent WT-C03 and WT-S01 reuse preserved E4 with two counted manual
  inputs each, while 36 remain E1 for lack of a route. Zero new proofs and zero
  proving seconds run. The benchmark is exposed development data, so held-out
  transfer, the capability gate, and the D1 verdict remain UNKNOWN.
- [D1P-30](reports/D1P-30.md) delivers the first working `bindcheck analyze`
  / `bindcheck validate` CLI. Generic ACIR/consumer-role rules emit no warning
  on pinned WarpToad or Payy check-added, emit R-BIND on **INJECTED** M-DOM,
  R-ANCHOR on **INJECTED** M-SRC, and grouped R-BIND/R-EFFECT warnings on
  Payy earlier. The two WarpToad warnings reach fresh owned-local E4 with new
  real proofs and state-checked effects; Payy automatically audits its exact
  preserved T15/T16/T18 E4 chain. The two negative controls have 0/2 false
  warnings in this bounded scope. Validation adapters and consumer relation
  paths are counted manual inputs; no baseline arms or held-out transfer ran,
  so the capability gate and D1 verdict remain UNKNOWN.
- [D1P-21B](docs/extraction/d1p-21b-variant-extraction.md) completes campaign
  gate 2 for the bounded WarpToad fragment. It derives pinned and M-SRC
  consumer relations from their own solc artifacts, binds `S_DOM` from the
  admitted state instead of a fixture constant, validates the extracted
  paths against prior executions/controls, and keeps policy/role inputs
  separate and manual. This is variant-specific extraction, not the D1P-30
  obligation discovery or a security result.
- [D1P-21A](reports/D1P-21A.md) passes campaign gates 1 and 3 without a
  solver campaign. Four new one-shot 9,152-byte proofs execute exact-state
  honest transitions for pinned + `S_DOM`, **INJECTED** M-DOM + `S_DOM`,
  pinned + `S_SRC`, and **INJECTED** M-SRC + `S_SRC` under each variant's
  correct artifact/VK/verifier/consumer pairing. All four verifiers accept,
  mints succeed, nullifiers are consumed, and recipient/supply deltas are
  `5e18` with zero relayer mint. M-DOM is independently decoded: its own ABI
  derives private contract witness 59, all 86 L1 Poseidon2 calls and 77 exact
  BN254 regions pass provenance/locality checks, and an exhaustive decoded
  delta from pinned is frozen. `S_DOM` admission is privileged/synthetic; no
  cross-chain, policy, solver-campaign, performance, vulnerability, automatic-
  discovery, or D1 verdict follows. D1 remains UNKNOWN.
- [D1P-20](docs/extraction/d1p-20-extracted-solver-model.md) replaces the
  manual consumer summary with the D1P-18 extracted `WarpToadCore.mint`
  relation for the tested fragment while retaining G1–G5 and role mapping as
  separate manual policy inputs. The full and T-ARITH queries parse, five
  archived executions and all eight D1P-14D controls match, and no primary
  solver query or proof runs. This is an extracted implementation-model
  component, not automatic obligation discovery, E4 validation, performance,
  or a security result.
- [D1P-19](reports/D1P-19.md) completes the remaining bounded B02
  prerequisites without a solver campaign. An artifact-specific P1 extractor
  checks locality and straight-line functionality for all 77 compiled BN254
  Poseidon regions while retaining exact arithmetic. The **INJECTED** M-SRC
  consumer mutation uses the unchanged pinned artifact/VK/verifier: one new
  real proof mints through M-SRC, and the identical valid proof reaches and
  fails the pinned K2 local-root guard with no state change. Hash-recorded
  `S_DOM`/`S_SRC`, complete pinned/M-DOM/M-SRC provenance, and the P6
  term/function/domain audit pass. The future O1/O2 protocol and L1 functional
  Poseidon2 layer remain draft and unfrozen; D1P-20 and D1P-21A subsequently
  supply the extracted-consumer component and exact-state gates, but campaign
  freezing still requires separate review.
  No security, cross-chain, performance, automatic-discovery or D1 verdict
  follows; D1 remains UNKNOWN.
- [D1P-17](reports/D1P-17-consumer-backends.md) closes the bounded consumer-
  arithmetic backend study. **T-ARITH kept as a shared over-approximation;
  T-OVF retired: multiplication equivalence unresolved, no demonstrated
  benefit; Q3 termination cause still unidentified.** T-ARITH Q1 resolves
  only the producer-dropped abstract diagnostic as UNSAT; the full-producer
  call and the remaining primary calls stay UNKNOWN. This is not a solver-
  advantage, semantic-equivalence, capability or security result.
- Merged Lane C work introduces taxonomy protocol v0.2.0 and the bounded
  [D1P-16 extraction feasibility](docs/extraction/d1p-16-feasibility.md) /
  [D1P-18 hardening](docs/extraction/d1p-18-hardening.md) records. The pinned
  `WarpToadCore.mint` extractor recovers 22 terminal families and reports
  **22/22 combined structural/control coverage**. That phrase does not mean 22
  EVM executions: five archived executions select only `p02`, `p06`, `p18`,
  and `p21`; the rest are covered by structural inspection, rollback checks,
  and deterministic semantic/source-mutation controls. Taxonomy design,
  reservation, annotation, and tool-capability evidence remain separate.
- [D1P-15](reports/D1P-15.md) mechanically attributes all 86 beta.22
  Poseidon2 permutation opcodes to complete H3 construction boundaries and
  resolves `44` versus `86` as two top-level hashes plus both compiled
  orientation candidates at each of 42 Merkle levels. Locked reference
  implementations match 172 `nargo execute` permutation tuples across the
  D1P-12R and D1P-14A honest inputs. The **INJECTED** M-DOM mutation compiles
  with its own artifact, distinct VK and generated verifier; real proofs mint
  both an honest configured-contract note and a foreign-contract note through
  the unchanged owned-local consumer, while the pinned repaired circuit
  rejects the foreign semantic input. Synthetic privileged root admission is
  recorded and makes no cross-chain, deployed-defect, automatic-discovery,
  performance or security claim. P2 and P5 are complete for this scope; D1P-19
  subsequently completes the bounded P1, M-SRC/P3, P4 and P6 prerequisites.
  No solver ran and D1 remains UNKNOWN.
- [D1P-INT1](paper/contract-revision-proposal.md) applies research contract
  revision 2 prospectively and archives revision 1 byte-for-byte under
  `docs/history/`. The target contribution is now automated discovery plus E4
  end-to-end validation, compared with generic/default and same-policy
  baselines and transferred to a frozen held-out family. Efficiency is
  retained as secondary RQ5. No historical report, evidence level or verdict
  changes, and no experiment is rerun.
- [D1P-00](reports/D1P-00.md) establishes the clean `d1-paper` linked
  worktree and an integration baseline without merging or porting code. The
  Codex V2/typed-consumer line remains the base; the Claude refinement loop is
  a selective reimplementation candidate, not a branch-merge candidate. The
  exact six-query N=8 input bundle is locally missing. An isolated Python
  baseline passes 27 tests but has four import errors because
  `pycryptodome==3.23.0` could not be installed through the sandboxed package
  index; this is not a 119-test pass. Research status remains UNKNOWN.
- [D1P-01](reports/D1P-01.md) installs the exact pinned Python dependency and
  completes the local baseline: 119 pre-change tests and 124 post-change tests
  pass with no failures or errors. A path-neutral, provenance-checked intake
  now rejects missing or mismatched inputs before generation and enforces a
  serialization-only no-solver boundary. Its five focused controls and the
  separate 65,536-vector compact-walk self-check pass. The exact two N=8
  ACIR/ABI pairs remain absent from recorded local evidence roots, so artifact
  recovery is BLOCKED, none of the six query hashes is newly reproduced, and
  research status remains UNKNOWN.
- [D1P-02](reports/D1P-02.md) resolves that local artifact blocker without
  rewriting D1P-01: four inputs imported from evidence commit `7d098cd3...`
  independently match the frozen D1-01 manifest, and the unchanged
  serialization-only adapter reproduces all six historical v5 query hashes in
  a fresh ignored namespace. No solver process or solver record exists. This
  is a byte-reproducibility result only; all six historical timeout outcomes
  and the D1 research verdict remain UNKNOWN.
- [D1P-03](reports/D1P-03.md) supplies the no-execution
  [experiment protocol](docs/d1-paper/d1p-03-protocol.md). It corrects the
  actual consumer scan to configurable length, kind-0 advance, four-word kind
  2, five-word kind 3, and revert for all other kinds, distinct from the frozen
  producer walk. A solver-free checker exhaustively validates 781,250 stream
  cases, all 25 cell pairs, and 12,825 goal cases, including overflow and
  truncated records. The check establishes only partition/rewrite equivalence.
  Track A execution and the unimplemented Track B joint solver remain pending
  both planners' decisions; research status is UNKNOWN.
- [D1P-04](reports/D1P-04.md) corrects the prospective comparison protocol and
  emits six parents × 25 cells as 150 specialized queries plus 150 producer-
  free two-direction equivalence queries. All 150 complete ordered producer
  prefixes are byte-identical to their parents, and six focused tests plus
  the complete 134-test D1 suite pass without solver calls. SMT equivalence is
  nevertheless **unestablished**: macOS rejected the frozen 4 GiB pre-exec
  address-space limit before the first control could launch cvc5. The no-retry
  rule left 0/150 cells validated and all 150 ineligible for primary use.
  Task reporting is complete, validation is incomplete, and the D1 research
  verdict remains UNKNOWN.
- [D1P-05](reports/D1P-05.md) preserves D1P-04 and executes the unchanged
  equivalence suite with a macOS libproc process-tree RSS monitor. Both
  controls pass and all 150 cell queries return UNSAT with exit zero; all 150
  producer-prefix audits remain true. The complete partition is now eligible
  for later primary use at the transformation-evidence level. The 50 ms RSS
  sampling can overshoot and is not a hard address-space cap; observed timing
  is non-primary macOS evidence. No parent satisfiability, consumer-direction,
  proof, consumer, or D1 verdict follows. The research verdict remains UNKNOWN.
- [D1P-06](reports/D1P-06.md) prepares and freezes the equal-budget Track A
  matrix on the planner-selected native Mac reference. The byte gate passes
  for all 166 inputs, all eight harmless-helper preflight checks pass, and the
  complete D1 suite passes 147/147. Both solver controls pass and one goal-only
  diagnostic returns usable SAT. The next goal-only call writes SAT text but
  hits a monitor/process-exit cleanup race before its exit/resource record is
  complete. The frozen infrastructure-stop rule leaves all six combined
  queries and all 150 cells unrun. Track A effectiveness is therefore
  unestablished and the D1 verdict remains UNKNOWN.
- [D1P-07](reports/D1P-07.md) repairs the process-exit race and completes a
  fresh frozen campaign from call 1. Focused tests pass 7/7, the complete D1
  suite passes 154/154, all 13 helper checks pass, and all 166 solver calls
  receive structured records. All six combined and all six partitioned
  logical obligations remain UNKNOWN: partitioning resolves 58/150 cells
  UNSAT but leaves 92 timeouts, improving zero complete obligations. Goal-only
  diagnostics are 6/6 SAT and both cone-only diagnostics time out. This is
  producer-side partial-progress evidence, not consumer-direction or D1
  security evidence; the D1 verdict remains UNKNOWN.
- [D1P-08](reports/D1P-08.md) verifies the D1P-07 cell split without rerunning
  Track A: 58 literal-false goals are UNSAT, while 42 literal-true and 50
  nontrivial goals time out; all six goal-only diagnostics are SAT and both
  cone-only diagnostics time out. A minimal solver-neutral symbolic consumer
  now preserves exact decoding, guards, sequential effects, rollback, V2
  admission, and occurrence matching. Thirteen focused and all 167 D1 tests
  pass; 12 symbolic/concrete source-bound cases match. The proposed next gate
  is an offline forwarding/occurrence certificate plus 11 exact N=8 consumer
  trace predicates. No joint solver, proof, replay, or D1 verdict follows.
- [D1P-09](reports/D1P-09.md) inventories the exact N=8 producer, forwarding,
  and consumer boundary; generates all 11 successful consumer decoding shapes;
  and applies one conservative propagation implementation to the unspecialized
  620/540 check-added cone, all 11 consumer shapes, and all 25 producer cells.
  The shape partition is exhaustive/disjoint over 390,625 control-flow classes,
  12 focused and 179 complete D1 tests pass, and consumer kind facts discharge
  4–8 original cone operations without fixing payloads. The one authorized
  isolated N=8 `agg_final` compile fails before output when Nargo cannot lock
  its external cache, so exact N=8 forwarding/key correspondence and all
  full-relation claims remain blocked. No solver, proof, replay, joint encoder,
  AUTH/NONVAC result, or D1 verdict follows.
- [D1P-10](reports/D1P-10.md) completes a newly frozen, in-sample feasibility
  study of only the 620/540 check-added selected producer cone. Eight
  30-second profiling calls all time out; the predeclared RSS tie-break selects
  radix 4, not a measured solver advantage. Both controls and the T22
  lost-equality regression pass, but only 12/25 exact propagation XOR checks
  return UNSAT, 13 time out, and all four radix-4 boundary controls time out.
  Both transformed arms are therefore ineligible and remain unrun. The four
  eligible unchanged-baseline obligations each time out at 300 seconds.
  Total observed solver-call wall is 1,954.640027 seconds across 44 calls;
  there is no SAT model, solved obligation, validated encoding improvement,
  proof, replay, or D1 security result. The research verdict remains UNKNOWN.
- [D1P-11](reports/D1P-11.md) completes a prospective, bounded screening of
  the entire permitted development pool: four applications in four families,
  below the 12-application/six-family/four-hour ceilings. Semaphore-Noir and
  discovery-only leads remain protected and outside the denominator. The
  screen retains WarpToad as the first tractable candidate, 0xbow Privacy
  Pools as contingent on an explicit Circom/aggregation scope decision, and
  Payy only for calibration; it excludes the Aztec v6 epoch rollup as too
  broad for the current fragment. The ledger records both all-output and
  subset consumer use, concrete joint obligations, audit evidence separately
  from policy, artifacts and unresolved assumptions. No solver, build, proof,
  replay, vulnerability validation, live-chain test, or held-out evaluation
  ran. All four application verdicts and the D1 result remain UNKNOWN.
- [D1P-12](reports/D1P-12.md) completes the bounded WarpToad executable-
  fixture gate with an exact setup blocker. Five surviving D1P-11 source files
  match 5/5 recorded SHA-256 values in a fresh ignored workspace, but the full
  pinned checkout, lockfile, circuit dependencies, compiled artifact/ABI,
  matching VK/generated verifier and declared Noir beta.22/bb.js 5.0.0 route
  are unavailable. Direct Git retrieval cannot resolve GitHub under the
  environment policy and browser-origin access was not granted. The existing
  ACIR reader is version-locked to Noir beta.14, outside the declared beta.22
  Noir JS route; the absent artifact prevents an exact compatibility check.
  A setup-only checker, frozen two-attempt protocol, manifest and source-level
  eleven-input/hash-dependence analysis are preserved. Zero builds, proofs,
  consumer executions or solver calls ran; no effects or performance were
  measured, and the D1 verdict remains UNKNOWN.
- [D1P-12R](reports/D1P-12R.md) preserves D1P-12 and completes the owned-local
  WarpToad development fixture at the exact pinned revision. The committed
  beta.22 artifact deterministically yields a saved 1,888-byte VK and a
  Solidity verifier byte-identical to the committed verifier; exact solc
  0.8.29 compiles it. One real 9,152-byte UltraHonk `keccakZK` proof is
  accepted by bb.js and the generated verifier, then the unchanged `mint`
  consumes the nullifier and splits 5e18 raw units between an ordinary named
  relayer and recipient with a nonzero fee. Identical proof/calldata replay is
  rejected. All 22 `P`/`P+1` public-word probes revert with
  `ValueGeFieldOrder()`, so this verifier rejects rather than reduces
  noncanonical words. The historical circuit artifact was behavior-validated,
  not independently rebuilt from source; no cross-chain, performance,
  protocol-policy, vulnerability or D1 verdict follows. D1 remains UNKNOWN.
- [D1P-13](reports/D1P-13.md) independently rebuilds the pinned WarpToad
  withdraw circuit with exact Noir beta.22. Rebuilt ACIR bytecode, decoded
  constraints, ABI, bb.js 5.0.0 VK and generated verifier all match the
  committed route; the only whole-JSON differences are seven nonsemantic
  diagnostic source paths. A separate fail-closed beta.22 MessagePack decoder
  classifies all 25,073 opcodes while the beta.14 decoder stays byte-unchanged.
  The D1P-12R honest inputs satisfy all 24,967 supported arithmetic/range
  constraints; 86 proof-enforced Poseidon2 permutations remain explicitly
  unsupported, separately from 20 Brillig witness-generation calls. Two
  predeclared mutation controls fail their named constraints, the focused
  set passes 58 tests/284 subtests and the complete D1 suite passes 197/312,
  and decoded witnesses 0–10 map
  exactly to the consumer order. No solver, joint encoder or new proof ran;
  this is correspondence/component evidence, not policy or security
  validation. D1 remains UNKNOWN.
- [D1P-14A](reports/D1P-14A.md) adds concrete fee-cap fixtures on the same
  exact-artifact, owned-local route. One new 9,152-byte proof with `max_fee`
  below amount succeeds at a frozen `0.1 gwei` base fee, consuming its
  nullifier and conserving `5e18` across an ordinary relayer
  (`194881000400000000`) and recipient (`4805118999600000000`). The unchanged
  proof and calldata are mined at `2 gwei` and revert at the pinned cap check
  because the computed fee is `2046250504200000000 > 1e18`; all consumer
  token/nullifier/root state rolls back. A second real proof with the
  proof-bound fee factor zero mints `4e18` to the recipient and zero to the
  relayer. Exactly two bounded proof attempts ran; no solver, encoder, fork,
  live-chain action, performance claim, policy validation or security verdict
  follows. D1 remains UNKNOWN.
- [D1P-14B](reports/D1P-14B.md) implements the first canonical WarpToad joint
  `AUTH-1`/`NONVAC-1` diagnostic encoder and occurrence-preserving `T_mint`
  lowering. The lowering matches the D1P-12R honest/replay cases and all
  D1P-14A fee controls; OpenZeppelin is resolved exactly to 5.6.1, and the
  D1P-12R real-proof anchor matches the modeled scope and DRAFT policy. The
  hash-complete manifest froze all three required queries, but each one-shot
  cvc5 process stopped on the same missing-parenthesis parse error before
  satisfiability checking. The no-refinement rule leaves Q1, Q2 and Q3
  `UNKNOWN`; no SAT validation, proof generation, consumer-direction result,
  policy validation or D1 verdict follows.
- [D1P-14C](reports/D1P-14C.md) preserves D1P-14B and repairs its SMT syntax,
  makes the consumer transition/effects independent of the unchanged policy,
  labels the summary `MANUAL / ASSUMED`, and derives G4/G5 from explicit mint
  occurrences and nullifier writes. All seven frozen queries pass both
  parenthesis and pinned-cvc5 parse preflights; 17 focused tests and 12
  subtests pass. C1 returns a model-validated conservation SAT in 24.335629
  seconds, but C2 times out at its single 60-second control slot. The required
  stop rule leaves C3, C4 and Q1–Q3 unrun. This is an exact sensitivity-control
  blocker, not Solidity equivalence, automatic discovery, a performance or
  vulnerability result; AUTH-1, NONVAC-1 and D1 remain `UNKNOWN`.
- [D1P-14D](reports/D1P-14D.md) preserves D1P-14B/C and replaces the symbolic
  sensitivity gate with eight deterministic regressions derived from the
  D1P-14A FC-POS fixture. All four existing implementation mutants are SAT for
  their designated G1/G3/G4/G5 predicates; the BASE summary is UNSAT for each
  corresponding predicate at identical fixed inputs. Twenty-one tests and
  twelve subtests pass, and all eleven frozen inputs pass parser preflight.
  The unlocked, byte-identical D1P-14C diagnostics remain `UNKNOWN`: Q1 and Q2
  time out at 300 seconds, while Q3 ends in a root-process monitor error after
  229.747027 seconds with no SAT/UNSAT output. No primary candidate, proof or
  V-EXEC runs. These are fixed-input encoder regressions, not search,
  performance, automatic-extraction, semantic-equivalence or vulnerability
  evidence; AUTH-1, NONVAC-1 and D1 remain `UNKNOWN`.
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
- [D1-02 continuation](reports/D1-02-continuation-01.md), recovered and checked by the [reconciliation audit](reports/D1-02-reconciliation-01.md), selects Semaphore-Noir with qualifications. D1-02 availability selection is complete; no proving or transfer result follows. Inherited D1-03 setup and its hash-matching protocol are preserved; [D1-03 preflight](reports/D1-03-preflight-01.md) identifies a conflict between freely failing transfers and the required verified repaired control. The authorized [v2 design](reports/D1-03-v2-design.md) now supplies explicit funded-token conditions, separate P/O policy and exact occurrence matching; 10 component tests and 8,892 finite checks pass. The [extraction gate](reports/D1-03-v2-extraction-01.md) adds a domain/policy core and compiled-artifact inventories with 23 passing regressions, but typed recursion/frame bindings and transition semantics were unimplemented at that checkpoint. [Typed bindings](reports/D1-03-typed-bindings-01.md) now decode all four artifacts and certify six recursive-call/frame mappings, with 27 passing controls. [Consumer-boundary audit](reports/D1-03-consumer-boundary-01.md) follows 19 function/modifier bodies and exposes unresolved signature/validator-set loops; nine controls pass after a preserved fixture-error correction. [Guard-frame work](reports/D1-03-guard-frame-01.md) adds 22 passing controls; its single artifact check predates dispatch/cache hardening, so final artifact validation is incomplete. The subsequently authorized [codebase review](reports/D1-codebase-review-01.md) validates the final guard checker against the pinned artifact within 120 seconds/4 GiB; all 81 Python controls pass in an isolated source/test copy. The legacy JavaScript suite is blocked by the missing installed `js-sha3` dependency. The new [consumer execution task](reports/D1-03-consumer-execution-01.md) adds concrete AST execution, ordered registry/token effects, rollback and separate v2 admission: 119 Python tests, 29 actual-artifact controls and 13 unchanged-Solidity component tests pass. Guard/verifier acceptance remains abstract; symbolic composition and joint gates remain incomplete. Historical replay proof/public-input bundles are absent from the inspected local raw directories, while the protocol permits zero new proofs. The task stops for replay/resource review; D1-03 stays UNKNOWN and D1-04 is blocked.
- [Proof recovery 01](reports/D1-03-proof-recovery-01.md) uses a newly authorized, separately frozen recovery budget. Pinned Rust/Linux bb and an isolated source copy are ready. Build 1 fails on missing libclang; local pinned libraries fix that prerequisite, but build 2 fails at final linking with `Cannot allocate memory` under 4 GiB. Both build slots are consumed. All 119 Python checks pass; no proof or full replay ran. D1-03 remains UNKNOWN. Review the [one-build GNU BFD proposal](docs/d1/proof-recovery-02-proposal.md) before another attempt. The v2 seeds and 28 primary query slots are unchanged.
- No held-out application result or general research contribution has been established.

**D1-01 reporting closure and D1-02 availability selection are complete;
research results remain UNKNOWN. D1-03 is incomplete:** D1P-09 validates the
11-trace predicates and a small selected-cone propagation opportunity. D1P-10
does not turn that opportunity into a validated solver comparison: both
transformed arms fail their frozen pre-main gates and all four eligible
baseline obligations time out. D1P-11 consequently screens the four permitted
development applications instead of extending that tuning line. D1P-12
records the first WarpToad setup blocker; D1P-12R preserves it and completes a
real owned-local proof-to-mint chain from the exact committed artifact through
a regenerated VK/verifier, nonzero-fee effects, replay rejection and strict
public-field canonicality. D1P-13 then establishes exact pinned
source-to-bytecode/ABI/VK/verifier correspondence and checks every supported
arithmetic/range constraint on the honest witness, while leaving 86 Poseidon2
constraints uninterpreted. D1P-14A concretely exercises the nonzero fee cap,
an unchanged-proof over-cap revert, and the zero-fee branch with real proofs
and receipts. D1P-14B then freezes the first joint AUTH-1/NONVAC-1 encoding,
but a common SMT-LIB parenthesis defect makes all three one-shot processes
parser errors. D1P-14C repairs and preflights a fresh freeze, then stops at the
required sensitivity gate when C1 validates as SAT but C2 times out; C3, C4
and all three primary queries remain unrun. D1P-14D replaces that gate with
eight deterministic fixed-input polarity regressions, all of which pass, then
runs the unchanged primaries: Q1/Q2 time out and Q3 has a monitor error, so all
three diagnostics remain UNKNOWN. D1P-15 separately completes the pinned
Poseidon2 boundary inventory and the injected O1 M-DOM build/honest/foreign
fixture gates with its own key; it does not run or reinterpret those
diagnostics. D1P-17 keeps T-ARITH only as a shared over-approximation and
retires T-OVF because multiplication equivalence is unresolved with no
demonstrated benefit; its Q3 termination cause remains unidentified. The
merged Lane C extractor records 22/22 combined structural/control coverage,
not 22 EVM executions. D1P-19 completes the bounded B02 P1/P3/P4/P6
prerequisites and drafts—but does not freeze or run—the future O1/O2 campaign.
D1P-20 replaces the manual consumer implementation summary for the tested
mint fragment with the extracted relation while leaving policy manual and
running no primary campaign. D1P-21A then passes exact-state non-vacuity for
four pinned/injected pairings and independently inventories M-DOM's 86 L1
Poseidon2 calls and 77 exact BN254 regions. The controls use real proofs but
do not freeze or run O1/O2.
These are development artifact/component results, not general
policy validation, cross-chain evidence or a security result. The exact N=8 forwarding artifact/key,
full-producer propagation, joint query, proof, and accepted full settlement
replay remain absent. Offline component checks are not joint verification.
The two principal properties remain authorization and coverage.

Prospective work is governed by contract revision 3's capability gate:
automated artifact-derived discovery with manual inputs counted, automated E4
validation on a development case, both baseline arms, and transfer to a frozen
held-out family without a new defect-specific rule. None of those four gate
conditions is currently complete.

D1-00 ran preservation and documentation checks only. D1-01 validated the saved check-added records and ran only the three missing running-flag slots. No D1 method-feasibility or novelty claim follows from preparation or reporting closure.

## Evidence hierarchy

1. `docs/research-contract.md` — current research decisions.
2. This README — current task status.
3. `reports/Txx.md`, `reports/D1-xx.md`, and `reports/D2-*.md` — tracked evidence summaries.
4. `results/raw/Txx/`, `results/raw/D1-*`, and `results/raw/D2-*` — ignored task evidence, retained or freshly generated only as each controlling report permits; it is not assumed reconstructible.
5. `artifact/` — the partial D2 development artifact, expected results, bindings, and fail-closed reproducer; it is not a final paper artifact.
6. The research guide and dated updates — historical context.

## Repository layout

The principal directories are `circuits/` and `contracts/` for the small fixture, `bindcheck/` for the checker and specification, `payy-harness/` and `payy-consumer/` for the Payy experiment, `scripts/` for task runners, `reports/` for tracked evidence summaries, `docs/` for current and historical-facing documentation, and `artifact/` for the partial D2 development reproducer. Generated proof data, downloaded dependencies, compiler output, and raw logs are ignored and are not necessarily reconstructible. Preserve retained sealed evidence and write authorized reruns only to fresh task-specific namespaces.

## Checking this checkout

The D1P-10 complete unittest checkpoint used Python 3.13.7 and PyCryptodome
3.23.0 (189/189 passing). D1P-21A uses Python 3.13.9: its focused set passes
11 tests, and the complete D1 suite passes 231 tests plus 312 subtests. The
artifact-specific D1P-15/19/21A tests require the ignored evidence workspaces.
The small upstream Noir test-source
excerpts, provenance and MIT notice
are included under `tests/d1/fixtures/`; unit controls need no compiler download,
proof, solver, generated artifact or historical raw log. To set up and run them:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-d1.txt
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests/d1 -v
```

The current D2 development record has a non-destructive historical replay,
three foundation-schema seal checks, a corrected Step 10 validation route, and
four partial-artifact profiles:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/d2_d201_post_step8_replay.py
python3 scripts/d2_foundation.py verify \
  results/raw/D2-07-recovery-01/content-seal-v1.json
python3 scripts/d2_foundation.py verify \
  results/raw/D2-08/content-seal-v1.json
python3 scripts/d2_foundation.py verify \
  results/raw/D2-09/content-seal-v1.json
PYTHONPATH=src python3 scripts/d2_step10_typed_extraction.py \
  --protocol protocols/d2/d2-10-typed-extraction-v2.json --validate-only

python3 artifact/reproduce.py metadata
python3 artifact/reproduce.py verify-retained --source current-workspace
python3 artifact/reproduce.py recompute --source current-workspace
python3 artifact/reproduce.py rerun-mechanical \
  --source current-workspace --run-id <fresh-unused-id>

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv-d1p-00/bin/python -m unittest discover -s tests -v
```

The D2-01 wrapper must report a live `EXPECTED_FAIL` with exactly one mismatch
at `src/bindcheck_d1/role_binding.py`, followed by an in-memory historical
overlay `PASS` for 8,134/8,134 members; that pass is not current-checkout
equivalence. The D2-07, D2-08, and D2-09 seal checks pass 623/623, 92/92, and
40/40 respectively. Corrected D2-10 v2 validation passes its 17 bound inputs.
The recorded same-host Step 19 evaluator reports four of four profiles `PASS`,
while the sidecar and generic-container routes remain blocked. The current
repository suite passes 151/151 tests. A fresh mechanical artifact run requires
an unused run ID and creates output only below ignored `artifact/work/`.

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
