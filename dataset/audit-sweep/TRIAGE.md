# BORDERLINE triage protocol (pre-labeling)

**Version:** v1. **Date:** 2026-11-23. **Owner:** the orchestrator.

## Why this step exists

The sweep produced 204 unique BORDERLINE candidates. Full human labeling at about 10 minutes each would take about 34 hours. Triage **orders** the candidates so that human effort goes where the binding question is live. **Triage never removes a candidate.** It is an AI pre-screen, and its error rate is measured by humans (see "Validation" below).

## Scope

- **Input:** rows in `merged/candidates.csv` with `group_best_decision = BORDERLINE`.
- **Out of triage:** `KEEP` rows, `scope-question` rows and `agents-disagree` rows. Humans label all of these in full.

## Rubric

For each candidate, read the finding's description and impact in the source report: the local file from `merged/in_reports.csv` or `merged/rescreen2_targets.csv`, or the `report_url`. Then judge the three criteria from PROTOCOL §2 separately:

| Criterion | Values |
|---|---|
| C1. A ZK proof is accepted, or a verifier accepts what it should reject | `met` / `unclear` / `fails` |
| C2. A consumer commits an effect after acceptance | `met` / `unclear` / `fails` |
| C3. A value deciding who, how much, what, which policy, which state or how often is not fixed by the proved statement | `met` / `unclear` / `fails` |

**Triage outcome:**

- **`LIKELY-BINDING`**: all three are `met`, or two are `met` and one is `unclear` with a concrete reason to expect it holds.
- **`LIKELY-NOT`**: any criterion `fails`, including the PROTOCOL v1.2 DROP classes (liveness only; gas or memory; circuit-internal with no effect on the public interface; off-chain only).
- **`UNSURE`**: anything else.

Also record:

- `proposed_pattern` (P1–P5/OTHER);
- a reason of at most 25 words;
- `proof_system_soundness`: `yes` if the finding is a soundness bug inside the proof system or a recursion verifier rather than an integration issue. This field informs the author's pending scope decision; it does not change the outcome.

## Validation (what makes this defensible)

Human raters label:

- every `LIKELY-BINDING` and `UNSURE` candidate; and
- a **seeded random 25% sample of `LIKELY-NOT`** (seed recorded in `triage/SAMPLE.md`).

The paper reports the triage miss rate as (`LIKELY-NOT` sampled items that humans label binding) / (`LIKELY-NOT` sampled), with a Wilson interval. If that rate is above 10%, humans label all remaining `LIKELY-NOT` items.

## Output: `triage/triage.csv`

```
group_id,finding_key,c1,c2,c3,triage,proposed_pattern,proof_system_soundness,reason,source_checked
```

`source_checked` is `yes` if the report text was read, or `quote-only` if only the logged quote was available.
