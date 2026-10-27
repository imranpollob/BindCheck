# Proposed research-contract revision 2: capability framing

**Status:** PROPOSAL, drafted 27 October 2026 (D1P-D03). **Not applied.**
Until it is, contract revision 1 (23 October 2026) controls all work.

**Application rule.** A single integrator applies this revision to the
canonical [`docs/research-contract.md`](../docs/research-contract.md), after
review and under the contract's §11 change control. The previous version is
preserved byte-for-byte under `docs/history/` first. **No lane edits the
canonical contract directly**; lanes propose changes in files like this one.

**Source of the decision:** planner decision recorded in the D1P-D03 task.
The target contribution becomes *capability: automated discovery and
validation of proof-to-execution mismatches*. Efficiency becomes a
secondary, untested question.

---

## 1. Rationale

Revision 1 frames the possible novelty as a **measurable advantage** of
consumer-directed extraction and refinement over equal-information
monolithic and modular analysis (§1, RQ2). The evidence gathered under that
framing is null or negative:

- D1P-07: all six N=8 combined producer obligations are `UNKNOWN`. The
  25-cell partition resolves 58 of 150 cells but zero of six obligations.
- D1P-09: consumer reached-kind shapes remove only 4–8 of 620 selected-cone
  operations.
- D1P-10: the unchanged baseline times out on all four obligations, and both
  transformed arms fail their validation gates.
- Historical synthetic line: refinement selected all constraints and was
  3–9% slower than monolithic solving.

These results do not refute a capability claim. They do show that an
efficiency claim currently has no support. The planners therefore move the
target to capability and keep efficiency as a secondary question. **The
earlier hypothesis and its results are preserved, not withdrawn** (§4).

## 2. Proposed text changes

### 2.1 §1 Paper thesis: replace the second and third paragraphs

> BindCheck D1 investigates whether a tool can **automatically discover**
> proof-to-execution mismatches from the actual producer constraints,
> public-input decoding and consumer effects, and **automatically validate**
> them end to end. End-to-end validation means a real proof, accepted by the
> unchanged verifier and consumer from an admitted or reachable state,
> producing a committed effect that the reviewed policy does not authorize,
> or omitting a required one.
>
> The possible novelty lies in that discovery-and-validation capability,
> demonstrated against generic and same-policy baselines. Integration
> failures, rich semantic specifications, modular summaries, selective
> unfolding, and the authorization/coverage (`P`/`O`/`E`) terminology and a
> formal transition model are prior work or framing, **not contributions by
> themselves** (CIVER, Coda, CCC-Check, the SNARK SoK). The specific advance
> over prior work must be demonstrated, not asserted. A new ACIR adapter,
> known-case reproduction, or more solver tuning alone does not establish a
> contribution.
>
> Whether consumer-directed selection and refinement also give a
> **measurable efficiency advantage** is a secondary question (RQ5). It was
> the primary hypothesis of revision 1 and is retained with its results.

### 2.2 §2 Research questions: replace the list

- **RQ1 — Semantic fidelity** *(unchanged)*: can supported extraction
  faithfully connect the compiled producer relation, exact public-input
  decoding and consumer effects?
- **RQ2 — Automated discovery** *(new primary)*: does BindCheck
  automatically derive the relevant obligations and producer facts from the
  artifacts, and report candidate mismatches, with manual inputs counted
  (§6)? "Automatically derived" must be demonstrated by an experiment. The
  current WarpToad obligations O1 (DOM-AZ) and O2 (SRC-EVM), defined in
  [`docs/d1-paper/d1p-b02-discriminating.md`](../docs/d1-paper/d1p-b02-discriminating.md)
  §§1–2, are planner-written and do not count as derived. *(Application
  note: when this text is applied to `docs/research-contract.md`, the link
  becomes `d1-paper/d1p-b02-discriminating.md`.)*
- **RQ3 — Automated validation** *(new primary)*: does BindCheck take its
  candidates to an end-to-end validated mismatch (E4, §8) without
  hand-performed steps, or with those steps counted and disclosed?
- **RQ4 — Comparative capability and transfer** *(merges old RQ3 and RQ4)*:
  which E1–E4 results does BindCheck obtain that generic/default and
  same-policy baselines do not, at what analyst and computational cost, on
  development cases and on an independently developed held-out family,
  without a new defect-specific rule?
- **RQ5 — Efficiency** *(old RQ2, secondary, untested)*: does
  consumer-directed summary selection and refinement improve solved
  obligations, precision or total cost over equal-information monolithic,
  goal-cone and modular baselines?

The existing sentence on prevalence is retained.

### 2.3 §3 Candidate contributions: replace the list

1. **Capability.** Automated discovery of proof-to-execution mismatch
   candidates and automated end-to-end validation to E4, with the
   specific advance over prior work demonstrated.
2. **Justified implementation** *(unchanged in substance)*: a precisely
   supported boundary model, extraction provenance, an
   abstraction-preservation argument and explicit unresolved results.
   Authorization and coverage terminology alone is not a novelty claim.
3. **Comparative evidence.** Generic/default and same-policy baselines,
   development and held-out cases, ablations, and total
   analyst/proving/solver cost. These results do not yet exist.
4. **Efficiency** *(secondary)*: a measured advantage, if one is found.
   Revision 1's null and negative results are reported regardless.

### 2.4 §8 Required result categories: append

> **Evidence ladder.** Attach one level to every candidate. **E0** no
> report. **E1** tool warning. **E2** a model satisfying the actual
> compiled producer relation, decoder and consumer model. **E3** a real
> proof of that assignment accepted by the pinned, unchanged verifier.
> **E4** that proof accepted by the unchanged consumer from an admitted or
> reachable state, producing an unauthorized committed effect or an
> undischarged required obligation, checked on state.
>
> Only E4 is an **end-to-end validated mismatch**. Relevant E1 and E2 results
> earn detection credit at their level. The same validation process,
> budget and adjudication apply to BindCheck's and every baseline's
> candidates. For a mutant or historical variant, "unchanged" means the
> frozen variant under test with its own matching key and verifier.
>
> The three verdicts (`VIOLATION`, `VERIFIED_WITHIN_SCOPE`, `UNKNOWN`) and
> all existing rules in §8 are unchanged. E2 corresponds to the existing
> "concrete model violation". E4 corresponds to the existing "real-proof,
> original-consumer, reachable-effect replay".

### 2.5 §9 Evaluation commitments: append

- Run **both** a generic/default arm and a same-policy arm for every
  applicable baseline. Record *not applicable* with a reason where a tool
  has no property interface.
- Generic fuzzer invariants run on a target only with protocol
  justification from that target's source or documentation.
- Non-target reports are adjudicated separately and are never
  automatically false alarms.
- An honest fixture without a known defect is not a proven negative control.
- Development cases can show capability on those cases. They cannot show
  transfer, unbiased discovery or generality; those require a held-out
  family frozen before analysis.
- Baseline budgets are development caps never below BindCheck's per-case
  budget. Setup and proving are declared separately.

The preregistered details are in [`paper/baselines.md`](baselines.md).

### 2.6 §11 Next gate: replace the paragraph's target

> The capability gate passes only with (a) automated discovery of a
> mismatch candidate from artifacts with manual inputs counted, (b)
> automated validation to E4 on at least one development case, (c) a
> comparison under both baseline arms, and (d) transfer to a frozen
> held-out family without a new defect-specific rule. If these are not
> obtained within the decision budget, report the failed gate and decide
> explicitly whether to narrow or stop. A tie with a routine baseline,
> hand-supplied correspondence or hand-performed validation undermines
> the claimed contribution.

### 2.7 Unchanged

§4 system model and the authorization/coverage/conservation definitions,
§5 threat model and scope, §6 specification boundary, §7 bounded formal
target, the three verdicts, §10 AI-assisted research integrity, and the
evaluation commitments already in §9.

## 3. Proposed change-log row

| Date | Revision and reason | Effect on earlier results |
| --- | --- | --- |
| *[date applied]* | Revision 2, authorized by the planner decision recorded in D1P-D03. Move the target contribution from a measurable efficiency advantage to capability: automated discovery and end-to-end validation of proof-to-execution mismatches. Demote the old RQ2 to secondary RQ5. Add the E0–E4 evidence ladder, two-arm baselines and development-case scope rules. | No result is relabeled. D1P-07, D1P-09, D1P-10, D1-01/T22 and the historical synthetic-branch results keep their original meaning as evidence on the revision-1 efficiency hypothesis (now RQ5). No rerun is required. These results cannot be cited as capability evidence. Revision-1 bytes are archived under `docs/history/` before editing. |

## 4. Preservation of the earlier hypothesis

- The revision-1 efficiency hypothesis remains a named, testable question
  (RQ5). It is not deleted or reworded as a failure.
- Its results stay reported unchanged as limitations in
  [`paper/draft.md`](draft.md) §VI: D1P-07 and D1P-10 (no N=8 obligation
  resolved), D1P-09 (4–8 of 620 operations removed), and the historical
  synthetic refinement overhead.
- No earlier report, ledger or raw evidence is edited. The revision-1
  contract is archived byte-for-byte before the change, as was done for the
  original contract (`docs/history/research-contract-2026-10-20.md`).
- The paper distinguishes exploratory development work, including the
  revision-1 efficiency results, from prospectively frozen evaluation.

## 5. Items for the integrator

1. Rewrite the O1/O2 link in RQ2 to its repository-relative form once
   `docs/d1-paper/d1p-b02-discriminating.md` is integrated.
2. Apply §2 to the contract, archive revision 1, and add the §3 row.
3. Update README and `docs/project-status.md`, which are outside this
   lane's scope.
