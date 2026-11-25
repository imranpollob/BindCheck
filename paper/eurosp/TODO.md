# Paper backlog (EuroS&P draft v1, 2026-11-25)

Every red `\TODO{ID}{...}` in the LaTeX has a row here with the same ID. Red `\DEMO{...}` text holds the *expected* results. Replace it with measured values as each row closes. Values we lack entirely are `\TBD`.

**Types:**
- E: experiment
- F: figure/plot
- A: algorithm/implementation
- T: theory/definition
- W: writing/decision
- D: data/labels

**Priority:**
- must: the paper is not credible without it
- nice: strengthens the paper

**Status:** open / running / done.

| ID | Type | Prio | Section | What | DEMO text it replaces | Blocked on | Status |
|---|---|---|---|---|---|---|---|
| E1 | E | must | §6, App | BindCheck v2 frozen run on B1 (round 1 + round 2) and B2; cost/time on test; per-item table | Table 4 tool row, Table 5 tool row, RQ2 text, abstract and intro numbers | – | done (eval d6beff4c): R1 4/14, R2 2/8, B2 22/27 |
| E2 | E | must | §6.6 | 3 independent runs on B1 and B2; min/median/max | variance paragraph | E1 | open |
| E3 | E | must | §6.3, Ethics | Hunt on non-dev audited commits (lead: safe-recovery-noir); triage; E4 confirm; disclose | RQ3 text, Table 6, abstract, conclusion | author: hunt scope + disclosure | open |
| A1 | A | nice | §5.3 | AST-based extractor (Solidity/Circom public-input index resolution) | extractor sentence | – | open |
| A2 | A | must | §5.4, §6.4 | Automatic harness generation from ledger rows (E2) | E2 paragraph, RQ4 | – | open |
| A3 | A | must | §5.4, §6.4 | E4 oracle: honest proof + attacker replay on local Anvil | E4 paragraph, RQ4 | – | open |
| E5 | E | must | §6.4 | Run the validator on all confirmed test warnings; E1/E2/E4 shares | RQ4 text | A2, A3 | open |
| E6 | E | must | §6.6 | Contamination split: detection by report date vs. model cutoff | contamination bullet 3 | E1 | open |
| E7 | E | nice | §5.5 | Open-weight brain on B1/B2 (lab machine) | – | labmate PC | open |
| E8 | E | must | §6.2 | Static tools on round-2 targets (no new LLM baseline, per author) | Table 4 round-2 column | – | running |
| E1b | E | must | §6.2 | v3 (A1–A3 + zkVM guest-side support) built on dev only; one run on a fresh held-out round 3 (e.g. acquire4-pinned items with Pass 2) | v3 sentence | A1–A3; round-3 labels | open |
| E10 | E | must | §6.2 | BindCheck on the 3 clean B2 hosts (false-alarm rate) | clean-host sentence | – | running |
| E11 | E | must | §6.3 | Classify all 16 test misses by cause, with counts | miss analysis | – | open |
| D1 | D | must | §4.1, §7.2 | Independent blind relabel of 30 stratified items; κ for binding and pattern | κ sentences | second rater | open |
| D2 | D | must | §4.5 | Normalize yearly counts by in-scope reports per year | trend sentence | – | open |
| D3 | D | must | §4.5 | Which layer(s) each FULL binding item needs (consumer / circuit / both) | layers paragraph | – | open |
| D4 | D | nice | §4.5, §7.1 | Classify fix commits of FULL binding items | fixes paragraph, developer checklist | – | open |
| D6 | D | nice | §7.1 | Per core finding, which construction (typed statements / effect commitments / pinning) would have prevented it | construction percentages | – | open |
| D5 | D | nice | §4.4 | Unbound value per pattern from LABELS-v1 | P1/P2 sentence | – | open |
| F1 | F | must | §1 | Fig. 1 from a real, already-fixed audited case (dev split), in three panels: circuit, consumer, attack | Fig. 1 | author picks the case | open |
| T1 | T | nice | §3.1 | Short formal property over (R, pi, delta); C1–C3 as its negation | – | – | open |
| W1 | W | must | title | Title | – | author | open |
| W2 | W | must | all | Official EuroS&P 2027 template (zip sha256 5f074285…; IEEEtran.cls V1.8b + class options copied); build via local docker image `authguard-paper-tex:2022`; body ≤13 pages | – | – | done |
| W3 | W | must | §3.2 | Confirm the P4 split (17 core + 16 adjacent) | – | author | open |
| W4 | W | must | §8, refs | Literature search; verify every citation (several marked VERIFY) | – | – | open |
| W5 | W | must | Open Science | Anonymized artifact link | – | – | open |
| W6 | W | nice | §4.1 | Coverage statement for missing sources | – | – | open |
| W7 | W | nice | App A | Condense the labeling guide | – | – | open |
| W8 | W | must | App B | Matching rules appendix | – | – | open |
| E9 | E | must | §6.1 | Honest-path check (honest proof accepted) for the privacy-vault and red-packet B2 hosts | B2 honest-path sentence | – | open |

## Reviewer-perspective gaps found in draft v1 (top-venue check)
1. **Small n.** The headline rests on 8 held-out positives. B2 (27) helps, but the mutants are author-made. Consider growing round 2 (more Pass-2 items from the test families) → candidate E10.
2. **No per-pattern recall on real flaws.** Only B2 has a per-pattern breakdown. The text should state this.
3. **Component comparison.** We report the plain LLM vs. BindCheck. A reviewer may ask what the tools vs. the procedure contribute. Decided: no new LLM ablation runs (author); answer in the discussion if asked.
4. **Hard-negative and false-positive story.** Report the total non-matching warning volume (dev: ~1.8 per snapshot) and a triaged precision on test → candidate E11 (triage all test warnings).
5. **Figure 1 must be real** (F1). A synthetic Fig. 1 is a known weak signal.
6. **Fixed in v1 after the advisor check (2026-11-25):**
   - funnel numbers now come from FUNNEL.md and MANIFEST.md (8,578 / 343 / 698 / 662 / 300 / 264);
   - round 2 is described as "inaccessible to the tool builder", not "located after freeze";
   - the check split is disclosed as not a clean holdout;
   - the v1.1 scoring amendment is disclosed in full;
   - the B2 honest-path claim is limited to one host;
   - the trend claim is softened;
   - the L024 wording is neutral;
   - the Wilson interval is corrected;
   - E2/E4 are drawn dashed in Fig. 4.
