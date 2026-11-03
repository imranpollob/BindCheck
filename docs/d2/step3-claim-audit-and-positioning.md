# D2 Step 3 claim audit and positioning

**Version:** D2-03-v1, 2 November 2026

**Scope:** documentary audit through D2-01; no analyzer, manuscript, README,
living-status, reserved-data, proof, replay, or baseline execution

**Research verdict:** `UNKNOWN`

The machine-readable source of record for this audit is
[`claim-ledger-v1.json`](claim-ledger-v1.json). This prose gives the required
version boundaries, authorization-language corrections, and manuscript edit
map. It does not change any historical result.

## 1. Result versions that must stay separate

| Record | Exact scope | Result that may be quoted | Evidence/exposure | Prohibited merge |
|---|---|---|---|---|
| D1P-34 v1.1 benchmark | 30 exposed mutants, historical analyzer | 16 detected / 14 unsupported / 0 misses / 53 warning objects | E1 development | Do not combine with corrected or integrated counts; warning objects are not distinct defects. |
| D1P-42 corrected static-only benchmark | Same 30 exposed mutants, corrected extent-capable static analyzer | 11 / 19 / 0 / 13 | E1 development | Do not call it the current integrated tool. |
| D2-01 integrated benchmark | Same 30 exposed mutants, static/extent plus typed role interface | 17 / 13 / 0 / 26, of which 23 warning objects are associated | E1 development | The six added detections are exactly the predeclared `R-ROLE` targets; zero misses is not a population estimate. |
| D1P-41 preliminary ablation | Eight exposed positives plus one control, older assumptions | producer 3/8; consumer 3/8; union 6/8; full 6/8 | E1 development, historical | Do not silently change its denominator or use it as the current ablation. |
| D1P-43 successor ablation | Seven supported exposed positives, one `UNKNOWN` positive, one control | producer 3/7; consumer 2/7; union 5/7; full 7/7 | E1 development, current corrected successor | Do not rewrite D1P-41 or infer an external-baseline advantage. |
| D2-01 exact Payy pair | Earlier and check-added revisions only | earlier: `R-EXTENT` plus `R-CONSUMER`; check-added: no `R-EXTENT`, separate `R-CONSUMER` | E1 historical-development analysis | Do not transfer exact-pair support to the 12 Payy benchmark mutants, which remain unsupported. |
| T15–T19 Payy chain | Known disclosed earlier tail mechanism | historical E4 with repair contrast | E4 historical development | It was hand-built after disclosure; it is not automatic discovery, a current-warning validation, or held-out evidence. |
| TE06 ledger | 53 historical v1.1 warning rows | 11 E4, 1 preserved E4, 7 E3, 1 E1+mock, 33 E1 | mixed historical development | It is neither 53 defects nor validation of D2-01 stable warning IDs. |
| D1P-33/D1P-36 scans | 12 attempts over 8 unique independent projects | 0 supported analyses; no rule ran | `UNKNOWN`, applicability blockers | Do not call unsupported attempts misses, negatives, or transfer results. |

The D2-01 49-row reconciliation table is also not a sample size. It contains
30 benchmark rows, 9 D1P-41 rows, 8 D1P-43 target rows, and 2 exact Payy rows,
with cases recurring across those datasets.

## 2. Current contribution versus proposed contribution

### Current, supportable statement

> BindCheck currently provides a bounded integrated development interface that
> associates compiled producer binding and extent facts, plus source-derived
> role facts, with checked consumer guard, state, and modeled-effect facts. It
> emits E1 diagnostics with explicit support gates, provenance, and stable
> warning identities. On the corrected seven-positive exposed ablation, the
> typed full arm detects 7/7 supported targets while the unjoined union detects
> 5/7. These are known development cases and do not establish authorization,
> novelty, security, transfer, or the contract's capability gate.

### Proposed contribution, still to be tested

> The proposed contribution is automated, artifact-derived discovery of a
> relational proof-to-execution authorization mismatch and automated causal
> validation to E4, distinguished under equal information from circuit-only,
> contract-only, simple-composition, and same-policy baselines, then transferred
> to a frozen held-out family without a defect-specific rule.

The current implementation is evidence that the candidate method can be
instantiated on exposed cases. It is not evidence that the proposed
contribution is novel or general.

## 3. Authorization-language audit

Authorization belongs at the reviewed `P`/`O`/`E` policy layer. A permission
record and a committed-effect record must be compatible in every relevant
field: identity, asset, quantity, beneficiary, domain, state version,
activation condition, and permitted discharge rule. The following shortcuts
are invalid.

| Invalid shortcut | Why it is wrong | Safe wording |
|---|---|---|
| “The proof constrains the amount, so it authorizes the mint.” | The amount may not be bound to the authenticated note/object, asset, beneficiary, domain, or state transition. | “The amount is proof-constrained and reaches a modeled mint operand; authorization is not yet established.” |
| “The producer and consumer role names match, so the effect is authorized.” | Current role atoms are bounded source-derived facts and name matching does not prove identity/context binding or policy compatibility. | “The role-correspondence diagnostic found no mismatch under the current inference.” |
| “`R-ROLE` `effect-authorization` proves authorization.” | That warning kind is an E1 diagnostic label. D1P-43 explicitly says it does not prove a minimal causal authorization slice. | Prefer “effect-role correspondence” in paper prose; reserve authorization for policy-reviewed E4. |
| “An accepted proof shows an unauthorized effect.” | Acceptance is E3. The unchanged consumer must commit a protected effect from an admitted/reachable state and the reviewed policy must lack a compatible permission for E4. | “The proof was accepted” at E3; “end-to-end validated mismatch” only at E4. |
| “The consumer uses the word, so the circuit authorizes the effect.” | Dependence/occurrence is not permission. A word can be used under the wrong identity, branch, domain, polarity, beneficiary, or state map. | “The word influences the modeled effect; the required relationship remains to be checked.” |
| “No warning means the effect is authorized.” | Silence may reflect unsupported facts, unknown roles, an absent rule, or a supported E0 observation. | “No current rule fired; verdict remains `UNKNOWN` unless the complete `VERIFIED_WITHIN_SCOPE` conditions hold.” |
| “The repair control is safe.” | The exact contrast supports only the exercised property/witness. Other warnings or defects may remain. | “The repair blocks the exercised candidate while preserving the stated honest control.” |

This audit also affects the manuscript's phrase “effect at risk.” At E1 the
tool may name a modeled effect associated with a word. “At risk” implies a
policy and reachability judgment and should be used only when that stronger
evidence is stated nearby.

## 4. Manuscript annotations

The draft is a historical D1P-P07 snapshot. The line references below target
the current tracked bytes; they are an edit plan, not edits to the manuscript.

| Location | Present issue | Status | Required revision |
|---|---|---|---|
| `paper/draft.md:5-48` | Status summary stops at D1P-41/D1P-40 and says Milestone 2 is pending. | contradicted | Add a new versioned D2 checkpoint. Do not rewrite D1P-41; state D1P-42, D1P-43, and D2-01 separately. |
| `paper/draft.md:54-60` | Pending marker treats path-conditional binding and role correspondence as unimplemented. | contradicted | Replace with remaining Step 8/9 work: compiler-backed object/context identity and relational authorization; keep fair comparison and held-out work pending. |
| `paper/draft.md:110-129` | Claims ledger uses 11/19/0 as current, Payy static `UNKNOWN`, 6/8 as current ablation, and a novelty statement. | mixed/stale | Rebuild from `claim-ledger-v1.json`; use the three-version benchmark table and two-version ablation table. Make novelty and generality unresolved. |
| `paper/draft.md:159-177` | “Property of neither component alone” is categorical; two-condition summary omits identity/asset/beneficiary/domain/quantity compatibility. | overstated | Use the qualified relational statement in §2 above and the full authorization fields. |
| `paper/draft.md:181-219` | Abstract contains obsolete 11/19/0, Payy `UNKNOWN`, “novelty only for the join,” and future-role claims. | contradicted/unresolved | Remove final-result prose. Until Gate A, use a methods/plan abstract or explicitly label current exposed E1 observations and unresolved contribution. |
| `paper/draft.md:240-246` | Claims these failures are invisible to either side in isolation. | overstated | Say some relationship- or effect-specific judgments require both sides; acknowledge one-sided tools detect several mechanisms. |
| `paper/draft.md:283-298` | “No circuit-only analysis can find a defect” and similar absolutes conflate defect detection with cross-boundary localization. | overstated | Say a circuit-only analysis receives identical producer bytes in M-SRC and cannot distinguish the consumer mutation from that input alone; do not generalize to all defects/tools. |
| `paper/draft.md:302-344` | Tool description is centered on v1.1/v1.2 and omits the D2 integrated interface, support states, stable IDs, `R-EXTENT`, and `R-ROLE`. | stale | Add a versioned implementation subsection. Preserve historical tool descriptions where their experiments rely on them. |
| `paper/draft.md:346-445` | Contributions mix completed E1 implementation, historical E4, candidate novelty, and generality. | overstated | Split “current implementation/evidence” from “proposed evaluated contribution” exactly as §2. |
| `paper/draft.md:371-402` | Payy mapping and role work are pending; novelty rests on bounded absence search. | contradicted/unresolved | Replace with exact-pair support and mutant unsupported rows; turn novelty into a Gate A question. |
| `paper/draft.md:1538-1650` | Development results call D1P-40 prospective v1.3 current and treat Payy as `UNKNOWN`. | stale | Add a version column and report D1P-42 static-only and D2-01 integrated results without deleting historical rows. |
| `paper/draft.md:1890-2120` | Novelty/ablation discussion uses D1P-41 6/8 as final current result. | stale | Keep D1P-41 as historical preliminary; add D1P-43 3/7, 2/7, 5/7, 7/7 plus one `UNKNOWN` and control. State that external fair comparisons have not run. |
| `paper/draft.md:2554-2694` | Related work omits ELSA, says CCC full text was not read, says SmartAxe artifact was unavailable, and can read as an absence proof. | stale/unresolved | Use `related-work-matrix-v1.json` and the companion prose; add access status and a smallest distinguishing experiment for each closest work. |
| `paper/draft.md:2638-2642` | “A circuit-only tool cannot know” is broader than the input-bound argument supports. | overstated | Say an analysis given only fixed producer bytes cannot distinguish two consumers that differ only in consumer semantics; allow specifications/adaptations and count them. |
| `paper/draft.md:2668-2673` | SmartAxe summary underplays its cross-program semantic join and says the artifact could not be obtained. | contradicted/stale | Treat SmartAxe as a close structural analogue; cite the author PDF and public artifact index. Native applicability remains empirical. |
| `paper/draft.md:2687-2694` | “No verified automated tool” remains a negative literature claim. | unresolved | Replace with a scoped inspected-source statement, explicitly flag ELSA as unresolved, and avoid exhaustive absence. |
| `paper/draft.md:2820-2839` | Role correspondence is said not to exist; automated join is stated as “our claim.” | contradicted/unresolved | Describe bounded `R-ROLE`; move compiler-backed identity and authorization to future work; call the join a candidate contribution. |
| `paper/draft.md:2927-2968` | Conclusion uses stale current counts and final novelty language. | contradicted/unresolved | Convert to a status-and-next-test conclusion until Gate A/B/C results exist. No final capability or novelty result. |
| `paper/draft.md:2999-3047` | Evidence map lacks D1P-42/D1P-43/D2-01 and retains obsolete pending rows and historical TE05 totals. | stale | Add versioned rows, final TE06 totals, exact Payy pair, and 49-row composition; preserve historical rows with labels. |
| `paper/draft.md:3102-3178` | References/status are stale for CCC-Check, SmartAxe, ZKAP, and ELSA. | stale | Cite direct primary URLs from the related-work companion and state exactly which full text/artifact was accessible. |

## 5. Claim discipline for the next experiments

Before Gate A, manuscript prose may say that the exposed typed ablation
motivates a comparison. It may not say that BindCheck is first, novel, more
capable, secure, general, precise, or effective. After Gate A, any statement
must name:

1. the exact tool version and sealed bytes;
2. the dataset and prior-exposure class;
3. native versus adapted baseline status;
4. the information/specification budget for every arm;
5. the result grade (`E1` through `E4`) and verdict;
6. unsupported, unresolved, irrelevant-warning, and correction counts; and
7. whether the result distinguishes a relationship from a naming or frontend
   artifact.

The smallest defensible paper claim is the one that survives those fields.
