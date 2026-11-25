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
| A1 | A | must | §5.3 | Deterministic ledger extractor (sinks, PI provenance classes, statement interfaces incl. zkVM journal, cross-layer join) feeding mandatory rows | extractor sentence | – | running (mvp-build3 t5q, freeze 11-28 12:00) |
| A2 | A | must | §5.4, §6.4 | Differential binding oracle: same PI + state, attacker-varied value ⇒ different effect (E2, recording mock verifier) | E2 paragraph, RQ4 | – | running (mvp-validator t5r) |
| A3 | A | must | §5.4, §6.4 | E4 oracle: honest proof + attacker replay on local Anvil | E4 paragraph, RQ4 | – | running (mvp-validator t5r) |
| E5 | E | must | §6.4 | Run the validator on all confirmed test warnings; E1/E2/E4 shares | RQ4 text | A2, A3 | open |
| E6 | E | must | §6.6 | Contamination split: detection by report date vs. model cutoff | contamination bullet 3 | E1 | open |
| E7 | E | nice | §5.5 | Open-weight brain on B1/B2 (lab machine) | – | labmate PC | open |
| E8 | E | must | §6.2 | Static tools on round-2 targets (no new LLM baseline, per author) | Table 4 round-2 column | – | partial (ff6c7fe8): Slither R2 done (0/8 strict, 3/8 loose; fixed 6/6, HN 8/8); Mythril 1/22, circomspect 0/22 killed by memory reaper; resume via mvp/eval/RESULTS-followup notes; Picus not run |
| E1b | E | must | §6.2 | v3 (A1–A3 + zkVM guest-side support) built on dev only; one run on a fresh held-out round 3 (e.g. acquire4-pinned items with Pass 2) | v3 sentence | A1–A3; round-3 labels | open |
| E10 | E | must | §6.2 | BindCheck on the 3 clean B2 hosts (false-alarm rate) | clean-host sentence | – | partial (ff6c7fe8): orc 0, redpacket 0, privacyvault 3 (time cap); triaged 67c4009c: 1 real-but-policy (borrow amount), 2 plausible P3 aliasing → E4 confirm; done |
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
| E12 | E | must | §6.1–6.2 | B3: fresh mutants (≥35, 5 real hosts incl. zkVM + Noir, operators derived from LABELS-v1, decoys + clean controls); blind for v3 | B2-only per-pattern claims | – | running (mutants3 t5s) |
| D7 | D | must | §6.2 | Round 3: pin-check the 11 unused test-split binding items + HNs; Pass-2 labels; freeze list before v3 freeze | v3 held-out sentence | rater capacity | open |
| E9 | E | must | §6.1 | Honest-path check (honest proof accepted) for the privacy-vault and red-packet B2 hosts | B2 honest-path sentence | – | open |

| RV1 | E | must | §6.2, Tables 6–7 | Plain-LLM arm (same model and snapshots, no skills or tools) on R2 and B2, 3 runs each. Report paired results with an exact McNemar test (B2 target: plain ≤ 16/27 for p < 0.05). This reverses the "no new LLM baseline" decision; if still declined, state why in the captions. | Table 6 R2 "–" cell; B2 has no plain-LLM row | author decision | open |
| RV2 | W | must | abstract, §1, §6.2–6.3 | Delete "v3 finds 9 of 14 and 5 of 8" (it would be test-tuned after the §6.3 miss analysis). Report v3 only on round 3 (E1b). Say "test-set" for R1+R2 and "clean" only for R2. Add a line in §6.3 that the miss analysis used test items. | v3 sentence | – | open |
| RV3 | W | must | abstract, §1, §4, §9 | Headline 87 core findings, with the 16 adjacent proof-system findings separate. Recompute severity (81%), families (44/68) and prevalence on 87, or widen the scope in §2.2. | – | W3 | open |
| RV4 | T | must | §3.1 | Policy-parameterized definition: intended policy Π (sender-choosable fields); "statement established" clause for P4 consistent with the sound-verifier assumption; rule for `msg.sender`; prove C1–C3 is the negation. Supersedes and promotes T1. | – | – | open |
| RV5 | E | must (partial: AI triage done, eval 7b5fa137; hand-verify) | §6.2 | From the existing v2 outputs: total warnings per target, triaged precision on R1/R2, and warnings-per-true-positive. No new runs. | – | – | open |
| RV6 | W | must | §6.1, Table 6 | Reconcile fixed-version counts (6 described vs 12/12 "both rounds") and the scan count (48 in the cost comment vs 42 targets). Describe R2 fixed versions if they exist. | – | – | open |
| RV7 | D | must | §4.1–4.2 | Report the outcome of the 14-item triage sample and extrapolate to the 36 unlabeled candidates. Phrase prevalence over the enriched set. | – | – | open |
| RV8 | E | nice | §6.2 | Non-LLM "binding taint" baseline: a Slither custom detector (calldata or `msg.sender` → transfer/mint/write argument not among the verifier-call inputs) on B1 and B2. It answers "is a trivial rule enough?" and gives a deterministic floor. | – | – | open |
| RV9 | W | must | §1, §6.2 takeaway | Remove "most misses sit in zkVM guest programs" and "most misses are zkVM guest-side…" until E11 gives counts. Only the 6 R2 misses are classified (3 guest-side), and the 10 R1 misses are not. | – | E11 | open |
| RV10 | W | must | abstract, §5.4, §6.5 | Validator wording: make the abstract conditional on A2/A3 status; explain the E3 gap or renumber; state the mock-verifier limit of E2; add the count of unconfirmed warnings attempted and rejected to Table 9. | E2/E4 paragraphs, RQ4 text | A2, A3 | open |
| RV11 | W | must | §8, §1 | Related-work matrix (layer / spec source / evidence / real-world eval). Map the findings onto the Chaliasos et al. categories to quantify overlap with their integration layer. Add PropertyGPT, SmartInv and zkFuzz (verified via index) and signature-replay/EIP-712 work. At least 35 references. | – | W4 | open |
| RV12 | W | must | §6.6 | Fix the rendering bug at `evaluation.tex:328`: "The" sits inside the `% src:` comment, so the PDF reads "static analyzers" mid-sentence. Move the comment to its own line. | – | – | open |
| RV13 | F | nice | §3, §5 | Fix label collisions in Fig. 2 ("attacker-chosen (no entry in 𝒮)") and Fig. 3 ("coverage re-prompt"); enlarge Fig. 3 text; keep the P1 listing in one column or drop it. | – | – | open |
| RV14 | W | must | §4.5 | Year counts sum to 97, not 103 (13+20+39+9+16). Find the missing 6 or correct them. | – | – | open |
| RV15 | W | nice | §4 | Disambiguate "68": audit sources (§4.1, Table 2) vs project families (§4.2). | – | – | open |
| RV16 | W | must | Ethics | Disclosure timeline and embargo for N1–N3; what the artifact withholds for unfixed live versions; a sentence on relabeling and naming auditors' public findings. | – | E3 | open |
| RV17 | W | must | §5.5, Open Science | Exact model snapshot ID and run dates. Ship all transcripts in the artifact. | – | – | open |
| RV18 | E | nice | §6.2, §7 | Component contribution from existing transcripts (no new runs): tool-call counts per scan, and ledger rows whose verdict changed after a tool answer. | – | – | open |
| RV19 | W | nice | §3.2, Table 4, §6.2 | Notation x+r vs x+p. Put the location-level numbers (8 vs 5) in Table 6 as a "loose" row. Use ○ for BindCheck's circuit/guest and proof→effect coverage in Table 5. | – | – | open |
| RV20 | W | must | §6.1 | Pre-register the round-3 protocol before the v3 freeze: target ≥ 25 real positives (D7 gives 11, so grow it or pool with E12/B3 and report the parts separately), matching rules, plain-LLM arm, 3 runs. Commit it like the v1.1 scoring rules. | v3 held-out sentence | E1b, D7, E12 | open |
| RV21 | E | done (eval 7b5fa137: v2 6/13 strict vs assisted fuzz 5/13) | §6.2 | BindCheck vs the hand-wired fuzzer on the same 13 EVM-side flaws, from existing per-item results (path A in §2c). | – | E1 per-item table | open |
| RV22 | W | must | abstract, §1, Contributions | Alternate abstract and contribution list for each RQ3 outcome (0 / E1–E2 only / ≥ 1 at E4), so the paper is ready whichever way E3 lands. | abstract and contribution DEMO | E3 | open |

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
