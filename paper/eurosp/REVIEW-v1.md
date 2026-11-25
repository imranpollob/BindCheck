# REVIEW-v1: simulated EuroS&P program-committee review of draft v1

**Reviewed:** the current `main.tex` and `sections/*.tex` after commit `22b5a6a`, which folded in the v2 eval results (R1 4/14, R2 2/8, B2 22/27). I also used `build/main.pdf`: 12 pages, built 2026-11-25 01:09, the same mtime as the latest section edits. `TODO.md` (state at 01:09) and `../EUROSP-STYLE.md` were inputs as well.

**How:** I used the ARS `academic-paper-reviewer` skill in full mode with a 5-seat panel. You accepted the Phase 0 cards, and the seats then ran inline as personas. All five seat reports are appended at the end of this file.

**DEMO rule:** red `\DEMO{}` text is treated as if it comes out as written. Every DEMO claim that would be fatal if it came out weaker is flagged in §2b.

**Scores:** 1 = Reject, 2 = Weak Reject, 3 = Weak Accept, 4 = Accept, 5 = Strong Accept. They are uncalibrated (NOT_CALIBRATED).

---

## 1. Scores and decisions

Each seat is scored on two bases:
- **As written:** every `\DEMO` comes out exactly as written. This is the basis you asked for.
- **Measured only:** DEMO text is ignored, which is the paper's state today.

| Seat | Persona | As written | Measured only | Confidence |
|---|---|---|---|---|
| EIC | EuroS&P PC member / area chair, software and blockchain security | 3 Weak Accept | 2 Weak Reject | 4/5 |
| R1 | Security-evaluation methodologist (benchmarks, LLM-eval hygiene, annotation) | 2 Weak Reject | 2 Weak Reject | 4/5 |
| R2 | ZK-application security researcher (Circom/Noir/halo2, zkVM integration) | 3 Weak Accept | 3 Weak Accept | 4/5 |
| R3 | Audit practitioner and LLM-agent tool builder | 3 Weak Accept | 2 Weak Reject | 3/5 |
| DA | Devil's Advocate (fixed seat) | 2 Weak Reject | 1 Reject | 4/5 |
| **Mean** | | **2.6** | **2.0** | |

Why some seats don't move when DEMO comes true:
- **R1 and the DA stay at 2 as written.** Their blockers are not things DEMO text resolves: the missing plain-LLM comparator (weakness 1), the v3 sentence, which is test-tuned *as written* (weakness 3), and the scope and definition problems (weaknesses 5 and 6).
- **R2 is the same on both bases.** It scores the definition and measurement, which are measured.

**Overall decision**
- **As written: borderline, Weak Reject leaning Weak Accept (mean 2.6).** The three E4 new flaws and the validator lift the EIC and R3 to Weak Accept. It becomes a clear Weak Accept once the v3 sentence is deleted and weakness 1 is addressed (§2c, paths A and B).
- **Measured only: Weak Reject (mean 2.0).** That is Major Revision in journal terms: a likely reject with an invitation to resubmit.

The panel agrees on one point: **the definition and the measurement study are a solid EuroS&P contribution, and the detector, as measured, is not.**
- The measured part of the tool contribution is 6/22 strict on real flaws, with no shown gain over the same model without the procedure: 4 vs 3 on R1, and no comparator on R2 or B2.
- The parts that would carry the tool are all DEMO or TODO: RQ3 new flaws, the E2/E4 validator, and v3.
- The panel splits on how much the definition and measurement alone are worth. R2 and R3 would accept a paper that leads with them. The EIC and R1 say the paper as framed promises a working detector and does not deliver one.

**DA CRITICAL adjudication (visible, as the skill requires):**

| DA issue | Ruling | Corroborated by |
|---|---|---|
| DA-1: recall not shown above the plain-LLM ablation | validated | R1-M1 |
| DA-2: the v3 DEMO would be test-tuned | validated | R1-M2 |
| DA-3: RQ3 is the only real-world validation, and it is all DEMO | validated as conditional | EIC-W2 |

All three block an Accept until they are fixed.

---

## 2. Top 10 weaknesses, ranked by likelihood of causing rejection

Each item has its source seats, its location, and a concrete fix.

### 1. The detector is not shown to beat the bare model on real flaws
*Seats: DA-1, R1-M1, EIC-W1. Rejection risk: very high.*
- Strict recall on R1 is 4/14 vs 3/14 for the plain LLM (Table 6). An exact McNemar test gives p = 1.0 for any split with a difference of 1.
- The plain-LLM arm is "–" on R2, the only clean held-out set, and absent on B2.
- Every "BindCheck finds what others miss" statement is therefore measured only against Slither, Mythril and the circuit linters. §3.1 ("Why neither layer suffices") and Table 5 argue that those tools are structurally blind to the property, so the comparison shows the definition, not the tool.
- The text even concedes this: "The procedure mainly makes the model look in the right place. It does not yet make it name the right mechanism." (`evaluation.tex:172–173`)
- **B2 cannot fill the gap as it stands.** The abstract now leads with 22/27, but:
  - the 27 mutants were written by the authors from the same five-pattern taxonomy that BindCheck's playbooks encode (DA-4; TODO gap 1 also calls them "author-made");
  - the hosts are small, and one is a proof of concept;
  - the honest path is checked on only 1 of 3 hosts (E9 pending);
  - the clean-host false-alarm scan is pending (E10);
  - B2 has no plain-LLM row.

  A PC member will read 22/27 as "the procedure recognises its own patterns" until the plain-LLM row exists. The planned B3 (E12: real hosts, operators derived from LABELS-v1, decoys and clean controls, blind for v3) is the right structural fix.

**Fix.**
- Run the plain-LLM arm on R2 and B2, three runs each, on the same snapshots and model. This costs about \$1 per target, roughly \$100 in total.
- Report paired results with an exact McNemar test.
- On B2, if BindCheck keeps 22/27 and the plain LLM has no hits that BindCheck lacks, the plain LLM must score ≤ 16/27 for p < 0.05 (b ≥ 6, c = 0 gives p = 0.031).
- This reverses the author decision "no new LLM baseline" in TODO E8 and note 3. The panel considers this arm the single most valuable experiment in the backlog. If the author still declines, Table 6 and Table 7 must say why, and the abstract must stop implying superiority on real flaws (→ RV1).

### 2. The new-flaw result (RQ3) is entirely DEMO, and with 2/8 recall it now carries the tool
*Seats: DA-3, EIC-W2, R3. Rejection risk: very high if it comes out weaker.*
- RQ3 is cited in the abstract, the intro, the contributions, the conclusion and Ethics.
- If the hunt yields zero E4-confirmed flaws, the tool has no real-world validation beyond 6/22.

**Fix.**
- Run E3 now, before more writing.
- Prepare an alternate abstract and contribution list for each outcome: 0 flaws, 1–2 flaws at E1/E2, or ≥ 1 flaw at E4.
- If the outcome is zero, reframe the paper (see §2c, path D).

### 3. Held-out integrity is internally contradicted
*Seats: DA-2, R1-M2. Rejection risk: high.*
- `evaluation.tex:227–228` says: "We inspected every positive that BindCheck missed, on development **and test** data."
- `evaluation.tex:174–175` then claims, as DEMO, that "v3 finds 9 of 14 and 5 of 8". Those are the same R1 and R2 items whose misses were just analysed, so the number would be test-tuned. It also contradicts E1b ("one run on a fresh held-out round 3").
- Separately, the abstract and intro call all 22 items "held-out", while §6.1 calls only R2 "our clean retest" and §7.3 says the benchmark builders saw an earlier version's test results.
- A methodologist will read this as leakage even though it is disclosed.

**Fix.**
- Delete the v3-on-R1/R2 sentence. Report v3 only on round 3.
- In the abstract and intro, write "6 of 22 test-set flaws (2 of 8 on the clean round 2)".
- Add one line in §6.3 saying that the miss analysis used test items and that therefore no later version is evaluated on R1 or R2 (→ RV2).

### 4. Novelty against the SNARK-bug SoK's integration layer is under-argued, and the bibliography is thin
*Seats: EIC-W3, R2-D3. Rejection risk: high, especially with a ZK-literate reviewer.*
- There are 17 references. The "first measurement" and "first to define" claims have no related-work matrix behind them.
- Chaliasos et al. already have an "integration" layer. Reviewers will ask whether binding flaws are a renamed subset of it.
- Missing related work:
  - LLM-driven specification and invariant inference for contracts. This is exactly what the paper says BindCheck does ("BindCheck infers that specification"): PropertyGPT (NDSS 2025) and SmartInv.
  - Recent circuit fuzzers: zkFuzz, and arXiv 2504.14881 "Towards Fuzzing ZK Proof Circuits".
  - Signature-replay and EIP-712 work on Ethereum.

**Fix.**
- Map the 103 (or 87) findings onto the SoK's categories and report how many the SoK's integration layer would cover and what it lacks: the effect side, and the statement-vs-effect relation.
- Add a related-work matrix with the columns: layer analysed / where the spec comes from / evidence level / real-world evaluation.
- Grow the bibliography to at least 35 verified entries (→ RV11; extends W4).

### 5. The headline count includes findings the threat model excludes
*Seats: R2-D1, DA-7. Rejection risk: medium–high.*
- §2.2 puts "soundness bugs inside a proof system" out of scope, and §3.2 excludes 16 P4 findings from the "core class".
- Yet the abstract, intro, contributions, the 81% severity figure, the "two thirds of families" takeaway and the conclusion all use 103.

**Fix.** Choose one of two options (→ RV3):
- (a) Headline 87. Recompute severity, families and prevalence on 87, and report the 16 adjacent findings separately.
- (b) Explicitly widen the scope in §2.2 and drop "core class".
- Option (a) is cleaner and costs nothing.

### 6. The definition is not yet precise enough for a definitional contribution
*Seats: R2-D2. Rejection risk: medium.*
- C1's clause "or the verifier accepts what it should reject" contradicts the threat-model assumption of a sound verifier. With γ = δ or an unchecked pairing, 𝒮(u) is not established at all, so "a function of 𝒮(u) and σ" is the wrong predicate for P4.
- "Bound" is defined without intent, yet §3.1 and §7.4 say binding depends on developer intent. As written, a deliberately open relayer fee is a binding flaw.
- `msg.sender`-as-recipient (Table 4: Taiko, Nocturne) needs a rule for when it is a flaw and when it is the intended policy.

**Fix.**
- Do T1 now and raise it to "must".
- Parameterize the definition by an intended policy Π: the effect fields allowed to be sender-chosen.
- Split the definition into (i) statement established (verifier sound for vk and the consumer checks the result), which covers P4, and (ii) effect determined by (𝒮, σ, Π).
- Show that C1–C3 is the negation of that property (→ RV4).

### 7. The trust story (evidence ladder) is claimed but not built
*Seats: R3-P1, DA-5. Rejection risk: medium; high if A3 slips.*
- The abstract says BindCheck "confirms warnings by replaying real proofs against unmodified contracts on a local chain". E2 (A2) and E4 (A3) are DEMO.
- E2 relies on a mock verifier. That shows a consumer-side unbound effect, not reachability with the real verifier, which matters for P5 and circuit-side cases.
- The ladder has no E3, which reviewers will ask about.
- RQ4 counts only confirmed warnings, so it never shows the validator rejecting a false positive.

**Fix.**
- Make the abstract wording conditional on what is built at submission.
- Explain the numbering (or renumber to E1/E2/E3).
- State the mock-verifier limitation in §5.4.
- Add a row to Table 9 with the number of unconfirmed warnings the validator attempted and how many it rejected (→ RV10).

### 8. Precision and analyst burden are missing
*Seats: R1-M4, R3-P2. Rejection risk: medium.*
- "Hard-neg. spec." counts only warnings at the flaw's location.
- There are no total warnings per target, no triaged precision, and no clean-host false-alarm figure (E10 pending). A tool that warns everywhere would look specific.

**Fix.**
- From the existing v2 outputs, report warnings per target and a triaged precision on R1 and R2. No new runs are needed; this is TODO gap 4.
- Land E10 (→ RV5).

### 9. Labeling validity rests on one DEMO κ, and the triage sample is unreported
*Seats: R1-M3. Rejection risk: medium.*
- The labels were LLM-proposed and adjudicated jointly by the same two raters, so the only independent check is DEMO D1.
- The 14-item random sample of "likely not binding" candidates was labeled, but its outcome is not reported. The 36 unlabeled candidates therefore have an unknown miss rate.
- "40%" is computed over a triage-enriched set.

**Fix.**
- Report how many of the 14 were binding, and extrapolate to the 36.
- Phrase prevalence as "of labeled proof-related findings".
- D1's rater must be outside the labeling loop.
- If κ for the pattern label comes out below about 0.6, report pattern results as indicative (→ RV7).

### 10. Internal inconsistencies and number/claim mismatches
*Seats: R1-M5/M8, DA-6, R2-D4, EIC-W4. Rejection risk: low–medium alone, but they erode trust.*

| # | Location | Problem |
|---|---|---|
| a | `evaluation.tex:31–36` vs Table 6 | 6 fixed versions are described (R1 only), but BindCheck's fixed-version specificity is 12/12 "both rounds". The cost comment's "48 scans" also does not match 26 + 16 = 42 targets. |
| b | `intro.tex:83–84`; takeaway box `evaluation.tex:222–223` | "most misses sit in zkVM guest programs": only the 6 R2 misses of the 16 test misses are classified so far, and 3 of them are guest-side. The takeaway's "most" covers only R2 (4 of 6 including the cross-deployment miss), and the 10 R1 misses are unclassified (E11). |
| c | `study.tex:178–180` | Year counts are 13+20+39+9+16 = 97, not 103. |
| d | §4 | "68" is used for both audit sources (§4.1) and project families (§4.2). |
| e | §3.2, Table 1 vs Table 4 | x+r vs x+p. |
| f | `evaluation.tex:172` | "location level (8 vs. 5)" appears in no table. |
| g | Table 5 | BindCheck gets ✓ for Circuit and Proof→effect, although guest-side flaws are its main miss and the validator is unbuilt. Use ○. |
| h | `evaluation.tex:328` | **Rendering bug:** the sentence-initial "The" sits inside the `% src:` comment, so the PDF reads "…\$0.28 per scan. static analyzers run…" (confirmed in `build/main.pdf`, p. 9). |
| i | Fig. 2 and Fig. 3 | Label collisions: "attacker-chosen (no entry in 𝒮)" overlaps the effect-ledger box, and "coverage re-prompt" overlaps the nodes. |
| j | §3.2 | The P1 listing breaks across columns. |
| k | §6 | The RQ list starts at RQ2 without pointing back to RQ1 in §4. |

**Fix:** RV6, RV9, RV12–RV15, RV19.

### 2b. DEMO claims that would be fatal (or major) if they come out weaker

| DEMO claim | Location | If weaker | Severity |
|---|---|---|---|
| Three new flaws, all E4, disclosed; 2 acknowledged, 1 fixed | abstract, §1, §6.4, Table 8, §9, Ethics | The tool has no real-world validation, and the abstract, contributions and ethics statement must change | **Fatal** |
| v3 finds 9/14 and 5/8 | `evaluation.tex:174–175` | Fatal **even if it comes out as written**, because it would be measured on analysed test items. Delete it. | **Fatal** |
| E2 auto-harness and E4 real-proof replay; RQ4 26/31 at E2, 16/31 at E4 | abstract, §5.4, §6.5, Table 9 | The abstract's "confirms warnings by replaying real proofs" becomes false, and RQ4 disappears | **Fatal for the abstract, major for the paper** |
| 61% of FULL findings need both layers; 23% consumer-only | §4.5 | §5 is motivated by "decided by comparing two artifacts". If most are consumer-decidable, a non-LLM taint rule becomes the obvious missing baseline (DA-8) | Major |
| κ = 0.78 (binding) and 0.71 (pattern) | §4.1, §7.3 | κ below about 0.6 undermines the taxonomy counts | Major |
| No warning on the three clean B2 hosts | §6.2 | False alarms on clean hosts make 22/27 uninterpretable | Major |
| Three runs: 2–3/8 and 21–23/27 | §6.7 | A wider band (e.g., 1–3/8) makes R2 indistinguishable from the plain LLM | Major |
| Post-cutoff detection not lower | §6.7 | Contamination becomes an open threat for the only real-flaw results | Major |
| 70% of fixes add the value to the statement | §4.5 | The "analogy is predictive" claim (§3.2) must be softened | Minor |
| Rate rises from 0.21 to 0.34 per report | §4.5 | Trend claim dropped | Minor |
| Typed statements prevent 41%, effect commitments 63% | §7.2 | Discussion only | Minor |
| Most P1 are recipient/fee; most P2 are roots | §4.4 | Descriptive only | Minor |
| AST extractor | §5.3 | No numbers depend on it, except v3 | Minor |

### 2c. Devil's-advocate deep-dive: what the held-out 2/8 means and what would flip the paper to accept

**What 2/8 says.**
- On the only clean set, strict recall is 2/8 with a 95% Wilson interval of 0.07–0.59. Mechanism-level recall is 4/8 (0.22–0.78).
- The data cannot distinguish BindCheck from 1/8 or 4/8. §7.3 reports ±1–2 items of run-to-run variance, which is 12–25 points on n = 8.
- On all test flaws the figures are 6/22 (0.13–0.48) strict and 9/22 (0.23–0.61) mechanism. A PC member will round this to "about one in four real flaws".

**Where the six round-2 misses come from** (§6.3):
- 3 are zkVM guest or host-config Rust.
- 1 is a cross-deployment chain-ID or address flaw with no warning.
- 2 are found at the mechanism level only.

Scoped to EVM and Circom consumers, R2 would be 2/5 strict and 4/5 mechanism. *This is derived:* it assumes neither strict hit is one of the three guest-side items, which §6.3 implies but which must be confirmed against the per-item results. That scoping is also **post hoc**, so it can be reported only as a labeled secondary analysis, never as the headline. It is still useful honesty: it says the class's zkVM half is out of reach today, which the conclusion already concedes.

**What the PC will do with it.** No PC will accept a detector on 2/8 alone. The acceptance case has to rest on something else.

**Flip paths, ordered by cost:**

- **A. Writing only; moves the DA from 1.5 to 2 and the EIC from 2 to 2.5.**
  - Lead the abstract with the definition and the measurement.
  - State "6 of 22 test-set flaws (2 of 8 clean; 9 of 22 at the mechanism level)" plainly.
  - Delete the v3-on-R1/R2 sentence.
  - Use ○ for BindCheck's circuit and guest coverage in Table 5.
  - Add the post-hoc scoped analysis, labeled as such.
  - **Compare BindCheck with the hand-wired fuzzer on the same 13 EVM-side flaws**, using existing per-item results. If BindCheck has ≥ 5 of those 13 strict, the framing "matches an expert-wired fuzzer at \$0.84 and zero human minutes" is fair and strong. If it has fewer, report that.
- **B. About \$100 of LLM runs; the biggest controlled-evidence gain (RV1).**
  - Run the plain LLM on R2 and B2, three runs each.
  - On B2, a plain-LLM score of ≤ 16/27 with no hits that BindCheck lacks gives McNemar p ≈ 0.03 and shows that the procedure matters on controlled data.
  - If the plain LLM is close to 22/27, B2 shows nothing about the procedure, and the paper must say so. The tool then rests on RQ3 alone.
- **C. RQ3 lands: at least one previously unknown flaw confirmed at E4 with disclosure acknowledged.** This is the single strongest flip. It is what lifts the EIC and R3 from 2 to 3 in the as-written column of §1. Three such flaws, as written, bring the panel to the borderline (mean 2.6) even with 2/8. Adding A and RV2 makes it a clear Weak Accept.
- **D. Fallback if B and C both come out weak.**
  - Recast the paper as a definition and measurement paper. EuroS&P accepts characterization papers; the style file cites FPGA-IP and LLIoT.
  - Present BindCheck as a reference prototype and the assisted-fuzzer result (0 → 5/13 once the spec is given) as the key tool finding: "the missing piece is the spec".
  - In this framing 2/8 is a limitation, not a claim. This is likely a Weak Accept on the strength of §3–§4, provided weaknesses 4–6 and 9 are fixed.
- **E. For a resubmission cycle: a pre-registered round 3 with ≥ 25 positives** (extends E1b; RV20).
  - Even 10/25 has an interval of 0.23–0.59, which clearly excludes "near zero".
  - With a plain-LLM arm on the same items, the paired test has real power.
  - D7 (round 3) has 11 positives. That is better than 8 but still wide: 6/11 → 0.28–0.79. Pool it with E12 (B3, ≥ 35 fresh mutants on real hosts) for the v3 claim, and report the real and mutant parts separately.

**Minimum set the panel would accept:** A + B, plus either C (≥ 1 at E4) or D. Without B or C, the DA's counter-argument stands and the paper is a Weak Reject.

---

## 3. Per-section notes

**Title and abstract**
- There is no title (W1).
- The abstract follows the venue order. Fix weaknesses 1, 3, 5 and 7 here: use 87 vs 103, say "test-set" rather than "held-out", and make the validator claim conditional.
- "Existing tools do not see them" is fair for the non-LLM tools only.

**§1 Introduction**
- The arc is strong (hook, gap, "This is not input validation", this work, contributions).
- Fig. 1 is synthetic and DEMO; F1 (a real dev-split case in three panels) is a known PC signal.
- "5 of 13, against 0" is a good hook. Add the 87 core figure.
- Drop "most misses sit in zkVM guest programs" until E11 is done.
- The contributions bullet "including three new flaws confirmed at E4" should not appear until it is true.

**§2 Background and threat model**
- Clear. The out-of-scope list contradicts the 103 headline (weakness 5).
- Add one sentence on relayers and intended open fields (feeds RV4).

**§3 Definition and taxonomy**
- This is the best part of the paper.
- Needs T1 and the policy parameter (weakness 6).
- "The analogy is predictive" depends on D4.
- The P1 listing nearly duplicates Fig. 1. Drop it, or make Fig. 1 the real case and keep the listing.
- Table 1 is cramped; its column widths force 2–3-line cells.

**§4 Measurement**
- The funnel and severity arithmetic check out: Table 3 rows and columns sum, 56/69 = 81%, 103/255 = 40%, and 264 − 4 − 5 = 255.
- Fix the year sum (97), the "68" ambiguity, and the missing triage-sample outcome.
- Table 4 (real cases) is excellent and should move nearer Fig. 1 or be cross-referenced from §1.
- Five takeaway boxes in total (four here) is above venue norms; keep at most one per RQ.

**§5 Design**
- Clear. Fig. 4 (controller) is helpful.
- The "Where the skills come from" disclosure is good practice.
- §5.4 needs the mock-verifier caveat and an explanation of the E3 gap.
- §5.5 needs the exact model snapshot and date (RV17).
- Fig. 3 is tiny after `\resizebox` and has a label collision.

**§6 Evaluation**
- See weaknesses 1–3, 7, 8 and 10.
- The case study (§6.3) is good: keep it and pair it with a miss case.
- Add the per-item appendix (E1, App. C).
- Table 6's "Sup. (R1)" column should also show R2.
- The capability table (Table 5) could merge into the related-work matrix, which saves space.
- The "The" rendering bug is at l.328.

**§7 Discussion**
- §7.1 and §7.2 overlap (checklist vs. by-construction); merge them.
- The threats section is honest.
- "Leakage" should also mention the test-miss analysis.
- Limitations should state the zkVM-guest gap with the count from E11.

**§8 Related work**
- Too thin for the "first" claims (weakness 4).
- The "Cross-chain verification" paragraph is a good addition. Its citation (`bridge-sok`) was verified: ICBC 2023, DOI 10.1109/ICBC56567.2023.10174993.

**§9 Conclusion**
- Fine. "Guest-side zkVM binding is the main open problem" is the right note.

**Ethics and Open Science**
- Add a disclosure timeline and embargo policy for N1–N3.
- Add a sentence on relabeling and naming audit firms' public findings.
- Confirm that no exploit details for unfixed live versions go into the artifact.
- The anonymized artifact link is missing (W5).

**Appendices**
- B (matching rules, judge prompt hash) is needed to interpret "strict" (W8).
- C (per-item table) is needed for path A in §2c.

**Bibliography** (citation check, web, 2026-11-25)

| Entry | Result |
|---|---|
| `zkap` | Author list verified (8 authors, USENIX Security 2024). Drop the "VERIFY" note. |
| `zkfuzz` | Authors and arXiv 2504.11961 verified. The authors' page suggests IEEE S&P 2026 [venue unverified]. Update the entry if confirmed. |
| `llm4vuln` | arXiv 2401.16185 verified. Replace "and others" with the full list: Sun, Wu, Xue, Liu, Ma, Zhang, Liu, Li (v4; the v1 list differs). |
| `bridge-sok` | Verified (ICBC 2023, DOI above). |

All four "VERIFY" notes currently render in the PDF reference list as "vERIFY". Remove them before submission.

---

## 4. Page count (body limit 13; at least 10 wanted)

**Measured from `build/main.pdf`** (12 pages total, built from the current sources):
- §1–§9 end about 45% of the way down the left column of p. 11, so **the body is ≈ 10.2 pages**.
- Ethics and Open Science bring it to ≈ 10.45 pages.
- References and Appendices A–C fill the rest of pp. 11–12.

**Assumption:** I have not checked whether EuroS&P 2027 counts Ethics and Open Science toward the 13 pages. Check the CFP.

**Headroom:** about 2.5 pages. The paper is above the 10-page floor and comfortably under 13.

**Where to add** (net estimate ≈ +1.5 pages):

| Addition | Est. pages |
|---|---|
| Real three-panel Fig. 1 (F1), replacing the current listing | +0.25 |
| Formal property and policy Π (T1/RV4) | +0.25 |
| Related-work matrix and the doubled bibliography (§8 only; references likely don't count) | +0.5 |
| Plain-LLM rows (R2, B2), a precision/warnings column and the fuzzer-subset comparison | +0.3 |
| Round-3 results or RQ3 table rows | +0.25 |
| Disclosure timeline in Ethics | +0.05 |

**Where to cut** (≈ −0.6 pages):

| Cut | Est. pages |
|---|---|
| Drop the P1 listing (it duplicates Fig. 1) | −0.15 |
| Merge Table 5 (capability) into the related-work matrix | −0.15 |
| Merge §7.1 into §7.2 | −0.2 |
| Trim "This is not input validation" (overlaps "Why neither layer suffices") | −0.1 |

**After the changes:** about 11–11.5 pages. Appendices B and C should stay in the appendix. The title-page footnote already says appendices are not peer-reviewed; per-item results there are fine.

---

## 5. New backlog rows (for TODO.md; I did not edit it)

| ID | Type | Prio | Section | What | DEMO text it replaces | Blocked on | Status |
|---|---|---|---|---|---|---|---|
| RV1 | E | must | §6.2, Tables 6–7 | Plain-LLM arm (same model and snapshots, no skills or tools) on R2 and B2, 3 runs each. Report paired results with an exact McNemar test (B2 target: plain ≤ 16/27 for p < 0.05). This reverses the "no new LLM baseline" decision; if still declined, state why in the captions. | Table 6 R2 "–" cell; B2 has no plain-LLM row | author decision | open |
| RV2 | W | must | abstract, §1, §6.2–6.3 | Delete "v3 finds 9 of 14 and 5 of 8" (it would be test-tuned after the §6.3 miss analysis). Report v3 only on round 3 (E1b). Say "test-set" for R1+R2 and "clean" only for R2. Add a line in §6.3 that the miss analysis used test items. | v3 sentence | – | open |
| RV3 | W | must | abstract, §1, §4, §9 | Headline 87 core findings, with the 16 adjacent proof-system findings separate. Recompute severity (81%), families (44/68) and prevalence on 87, or widen the scope in §2.2. | – | W3 | open |
| RV4 | T | must | §3.1 | Policy-parameterized definition: intended policy Π (sender-choosable fields); "statement established" clause for P4 consistent with the sound-verifier assumption; rule for `msg.sender`; prove C1–C3 is the negation. Supersedes and promotes T1. | – | – | open |
| RV5 | E | must | §6.2 | From the existing v2 outputs: total warnings per target, triaged precision on R1/R2, and warnings-per-true-positive. No new runs. | – | – | open |
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
| RV21 | E | must | §6.2 | BindCheck vs the hand-wired fuzzer on the same 13 EVM-side flaws, from existing per-item results (path A in §2c). | – | E1 per-item table | open |
| RV22 | W | must | abstract, §1, Contributions | Alternate abstract and contribution list for each RQ3 outcome (0 / E1–E2 only / ≥ 1 at E4), so the paper is ready whichever way E3 lands. | abstract and contribution DEMO | E3 | open |

---

## Appendix: how the review was run, limits, and advisory checks

**Panel.**
- The ARS `academic-paper-reviewer` v1.11.1 ran in full mode.
- Phase 0 (field analysis and cards) was accepted by the user on 2026-11-25.
- Phase 1/2 ran as five inline personas in **one model family, one context and one accountable human**. Every seat had read the whole manuscript, so there was no paper-blind Phase 1.
- This is role separation, not independence, and the seats' errors are likely correlated.

**Files** (all in the session scratchpad `/tmp/claude-1000/-home-pollmix-Coding-bc-BindCheck-paper-eurosp/0cec3955-be4a-4c4b-ac16-d946b6b0f563/scratchpad/`):
- `phase0-field-analysis.md` (cards)
- `seat-reports.md` (all five seat reports)
- `acronym.txt`
- `sugref.txt`

**Skill steps that did not run:**
- Sprint-contract conformance (`check_phase_conformance.py`), the panel synthesis checker (`check_panel_synthesis.py`), the reviewer claim check (`audit_panel_claims.py`) and the provenance artifact did not run, because `jsonschema` is not installed in this Python.
- The panel synthesis above is therefore unchecked by script.
- No separate author letter was written: this file is the author-facing document.

**Advisory attachments** (script output, not reviewer findings):
- *Acronym check* (`check_acronyms.py` on `pdftotext` of `build/main.pdf`). It flags undefined acronyms, mostly code identifiers and tool names. The ones worth defining at first use: **LLM, zkVM, EVM, AST, SDK, DKIM, FRI, MACI, PSE, EIP**, and the tier labels **FULL / LIGHT / PSS** (PSS is never expanded).
- *Suggested-reference check* (`verify_panel_recommendations.py`). All three R2 suggestions (PropertyGPT arXiv 2405.02580, SmartInv arXiv 2411.09217, zkFuzz arXiv 2504.11961) were found in an index. This shows they exist, not that they are relevant or that their metadata is right.

**Other limits.**
- Page estimates are read off the compiled PDF.
- The decision does not depend on any reviewer reading the external evidence files (`mvp/eval/*`, `dataset/*`); the `% src:` comments were not checked against them.
- Web use was limited to the citation checks listed in §3.

---

## Appendix: seat reports (Phase 1/2) (inline personas; Calibration Status: NOT_CALIBRATED)

Manuscript reviewed: the current `sections/*.tex` after commit 22b5a6a (v2 eval folded in), plus `build/main.pdf` (12 pp, built 01:09, same mtime as the latest source edits).

DEMO rule applied: an unmeasured `\DEMO` value is not itself a defect. Findings concern (a) DEMO claims that would be fatal if they came out weaker, and (b) defects in measured or non-DEMO text.

Provenance: all five seats ran in one model family (Claude Opus 5.5) and one context, with the same accountable human. Every seat had seen the whole manuscript and the other seats' focus cards, so there was no paper-blind Phase 1 and no context separation. This is persona separation, not independence.

---

### EIC: Journal-Fit Reviewer (EuroS&P PC, software/blockchain security)

**Recommendation: 3 Weak Accept as written (DEMO true) / 2 Weak Reject measured only. Confidence 4/5.**

**Summary.** The paper defines "binding flaws" between a ZK proof's statement and a consumer contract's effect and gives a five-pattern taxonomy. It measures the class in 103 auditor-reported findings drawn from 8,578 reports, and presents BindCheck, an LLM-driven ledger procedure with a planned validator.

**Strengths**
- S1. The problem framing is crisp, memorable and well matched to the venue. "A proof certifies a statement, not an effect" and the signature-misuse analogy (§3, Table 1) will travel. [§3.1–3.2]
- S2. The measurement pipeline is unusually transparent for an audit-mining paper: funnel, recall check 49/50, and severity table with arithmetic that adds up. [§4, Tables 2–3]
- S3. The evaluation reports a weak result honestly ("These numbers are modest") and discloses leakage and the scoring amendment. [§6.2, §7.3]

**Weaknesses**
- W1 (Major). The paper makes three contributions, and the one the venue weighs most for a tool paper, the detector, is the weakest. Strict recall is 6/22 on real flaws, and the gain over the same model without the procedure is 4 vs 3 of 14. As written, the measurement study carries the paper and the tool rides along. [§6.2, Table 6]
- W2 (Critical if weaker). RQ3 (three new E4-confirmed flaws) is entirely DEMO, yet it appears in the abstract, the intro, the contributions, the conclusion and Ethics. If the hunt yields zero, the abstract, the contribution list and the ethics statement all change, and the tool contribution has no real-world validation. [abstract l.20–21; §1 l.85–87; §6.4; Ethics]
- W3 (Major). The "first" claims rest on a 17-entry bibliography. The SoK of Chaliasos et al. already has an "integration" layer, and a reviewer from that community will ask what binding adds beyond it. No related-work matrix is given. [§8; §1 Contributions]
- W4 (Minor). Venue conventions are partly unmet. Fig. 1 is synthetic (F1). There is no title. RQ1 lives in §4 while the RQ list in §6 starts at RQ2. Takeaway boxes are used five times. [§1, §4, §6]

**Questions**
1. If RQ3 returns zero new flaws, what is the paper's headline?
2. How does "binding" differ from the SoK's integration-layer bugs, operationally?

---

### R1: Methodology (security-evaluation methodologist)

**Recommendation: 2 Weak Reject on both bases. Confidence 4/5.**

**Strengths**
- S1. The split is family-level and seeded, with forced-dev for families seen earlier. [§6.1]
- S2. Wilson intervals are reported and correct. I recomputed 4/14 → 0.12–0.55, 2/8 → 0.07–0.59 and 22/27 → 0.63–0.92. [Table 6, §6.2]
- S3. Unsupported targets are reported separately rather than counted as misses. [§6.1 Scoring]

**Weaknesses**
- M1 (Critical). The comparison that would show the procedure's value has no power and no clean arm.
  - R1 strict is 4/14 vs 3/14 for the plain LLM. An exact McNemar test gives p = 1.0 for any discordant split with a difference of 1.
  - The plain LLM was not run on R2 ("–") or on B2 (no row), so the only clean held-out set (R2) and the largest set (B2) have no ablation comparator.
  - Without these, "BindCheck finds what others miss" is shown only against non-LLM tools that the paper itself argues are structurally blind. [Table 6 row "Plain LLM"; Table 7; §6.2 l.168–173]
- M2 (Critical). The held-out integrity is internally contradicted.
  - §6.3 says "We inspected every positive that BindCheck missed, on development **and test** data". The DEMO at evaluation.tex:174–175 then claims "v3 finds 9 of 14 and 5 of 8", i.e., on the same R1/R2 items after their misses were analysed.
  - That number would be test-tuned and must not appear. It also contradicts E1b ("one run on a fresh held-out round 3").
  - Separately, R1 is called "held-out" in the abstract and intro ("6 of 22 held-out"), while §6.1 calls R2 "our clean retest" and §7.3 says the benchmark builders saw test results of an earlier version.
  - [evaluation.tex:174–176, 227–228; abstract l.18; intro l.80–81; discussion.tex:75–82]
- M3 (Major). The ground-truth labels are not independent.
  - LLM-proposed labels were adjudicated jointly by two raters, so the only agreement statistic is the DEMO κ.
  - The outcome of the 14-item random sample of "likely not binding" triage is not reported, so the 36 unlabeled candidates carry an unknown miss rate.
  - The prevalence "40%" is computed over a triage-enriched set.
  - [§4.1 l.26–29, 46–49; §4.2]
- M4 (Major). Specificity is location-scoped and precision is absent.
  - "Hard-neg. spec." counts only warnings *at the flaw's location*. There is no count of total warnings per target, no triaged precision, and no clean-host false-alarm rate (E10 pending).
  - A tool that warns everywhere would score well on this metric. [Table 6 caption; §6.2 l.165–166]
- M5 (Major). The benchmark description and the table disagree.
  - The B1 description lists 6 fixed versions (R1 only), but BindCheck's fixed-version specificity is 12/12 "both rounds". Either R2 has 6 fixed versions that are not described, or the count is wrong.
  - The cost comment's "48 scans" (\$40.4) does not match 26 + 16 = 42 described targets either.
  - [evaluation.tex:31–36 vs 130; l.328 comment]
- M6 (Major). There is one run per target, and the variance is DEMO. With n = 8, a ±1 swing changes R2 recall by 12.5 points. [§6.7]
- M7 (Minor). The LLM judge is the arbiter of "strict" hits. Its prompt and hash are deferred to an empty Appendix B (W8), and the re-judging stability ("one in twenty") lives only in §7.3. [§6.1; App. B]
- M8 (Minor). "Location level (8 vs. 5)" is cited in the text but appears in no table. [evaluation.tex:172]

**Questions**
1. Were any test-set misses discussed with the tool-building process after the v2 freeze?
2. What did the 14-item triage sample yield?
3. How many total warnings did BindCheck emit on R1 and R2?

---

### R2: Domain (ZK-application security)

**Recommendation: 3 Weak Accept on both bases, conditional on scope fixes. Confidence 4/5.**

**Strengths**
- S1. The class is real, and the examples ring true: Nocturne refund, Taiko bond receiver, vlayer chain ID, MACI tally, Anon Aadhaar index (Table 4). The P3 field-aliasing and re-randomization cases are the kind practitioners get wrong. [Table 4; §3.2 P3]
- S2. Putting circuit-internal under-constraints out of scope, and reporting the 48 such non-binding findings, positions the work cleanly against circuit tools. [§2.2; §4.2]

**Weaknesses**
- D1 (Critical). The scope of the headline count is inconsistent.
  - §2.2 puts "soundness bugs inside a proof system (transcript, polynomial commitment, or recursion constraints)" out of scope.
  - §3.2 P4 excludes 16 such findings "from the core class".
  - Yet the abstract, intro, contributions, the 81% severity figure, the "two thirds of families" takeaway and the conclusion all use 103, which includes those 16.
  - The core count (87) appears only in Table 2 and §7.2.
  - [abstract l.10–12; §1 l.46; §4.2–4.3; Table 2; background.tex:56–62]
- D2 (Major). The definition has three precision gaps.
  - (a) C1's second clause ("or the verifier accepts what it should reject") conflicts with the threat-model assumption that the attacker "cannot forge proofs for false statements of a sound verifier". If the verifier is unsound, 𝒮(u) is not established at all, so "a function of 𝒮(u) and σ" is not the right predicate for P4 cases such as γ = δ or an unchecked pairing result.
  - (b) The definition is intent-free ("function of 𝒮 and σ alone"), while the prose says binding "holds only when the developer's intent … agree[s]" and §7.4 admits deliberately open relayer fees. As stated, a deliberately unbound relayer fee is a binding flaw.
  - (c) `msg.sender`-as-recipient (Table 4, Taiko and Nocturne) is a value the sender controls by construction. The definition should say when using `msg.sender` is a flaw and when it is the intended policy.
  - [§3.1 Definition; §2.2 Assumptions; §7.4; T1 pending]
- D3 (Major). Novelty against prior integration-bug work is under-argued.
  - Chaliasos et al. classify bugs by layer including "integration", and the paper says so but does not quantify the overlap.
  - Missing: work on ZK circuit fuzzing beyond circuits (zkFuzz; arXiv 2504.11961), LLM-driven property and invariant inference for contracts (PropertyGPT, NDSS 2025; SmartInv), front-running measurement beyond Flash Boys, and replay and domain-separation work on Ethereum signatures (EIP-712 is mentioned only in §7.2).
  - [§8; §1]
- D4 (Minor). The notation changes from x+r (§3.2, Table 1) to x+p (Table 4, ZkDrops).
- D5 (Minor). The claim that the analogy is "predictive" rests on DEMO D4 (70% of fixes). If D4 comes out low, soften to "illustrative". [§3.2 l.83–85; §4.5]
- D6 (Minor). P5's boundary with liveness is well drawn, but the P1 versus P2 boundary for stored values is explicitly fuzzy (§7.3). One sentence on how stored records are assigned would help.

**Suggested references** (verified 2026-11-25 by web lookup unless marked)
- PropertyGPT: LLM-driven Formal Verification of Smart Contracts through Retrieval-Augmented Property Generation. NDSS 2025 (arXiv 2405.02580).
- SmartInv: Multimodal Learning for Smart Contract Invariant Inference. Wang, Pei, Yang. arXiv 2411.09217. The authors list it as S&P 2024; the venue is [UNVERIFIED].
- zkFuzz: Foundation and Framework for Effective Fuzzing of Zero-Knowledge Circuits. Takahashi, Kim, Jana, Yang. arXiv 2504.11961. Possibly IEEE S&P 2026 per the authors' page; the venue is [UNVERIFIED].
- Search lead [UNVERIFIED]: Ethereum signature-replay and EIP-712 misuse studies; front-running detection after Flash Boys (e.g., work by Torres et al.).

~~~yaml suggested-references
- title: "PropertyGPT: LLM-driven Formal Verification of Smart Contracts through Retrieval-Augmented Property Generation"
  authors: ["Liu, Y."]
  year: "2025"
  doi: null
  arxiv_id: "2405.02580"
- title: "SmartInv: Multimodal Learning for Smart Contract Invariant Inference"
  authors: ["Wang, S. J.", "Pei, K.", "Yang, J."]
  year: "2024"
  doi: null
  arxiv_id: "2411.09217"
- title: "zkFuzz: Foundation and Framework for Effective Fuzzing of Zero-Knowledge Circuits"
  authors: ["Takahashi, H.", "Kim, J.", "Jana, S.", "Yang, J."]
  year: "2025"
  doi: null
  arxiv_id: "2504.11961"
~~~

---

### R3: Practice (audit practitioner and LLM-agent tool builder)

**Recommendation: 3 Weak Accept as written / 2 Weak Reject measured only. Confidence 3/5.**

**Strengths**
- S1. The cost is realistic and stated: \$0.84 per test scan, a median of about 5 min, and a contrast with 5–45 min of manual harness wiring. [§6.6]
- S2. The developer checklist ("test with a malicious caller") and "binding by construction" (typed statements, effect hashes) are immediately actionable. [§7.1–7.2]

**Weaknesses**
- P1 (Critical if weaker). The evidence ladder is the trust story, and none of it is automated.
  - E2 (A2) and E4 (A3) are DEMO, yet the abstract states as fact that BindCheck "confirms warnings by replaying real proofs against unmodified contracts on a local chain".
  - E2 uses a mock verifier that "accepts exactly the honest public-input vector". That shows that the consumer is unbound relative to the mock. It does not show reachability with a real verifier, because circuit-side or encoding (P5) issues can make the mock accept vectors the real verifier would reject.
  - The ladder skips E3 without explanation.
  - RQ4 counts only *confirmed* warnings. It says nothing about how many false positives the validator filters out, which is the number an auditor wants.
  - [abstract l.16–17; §5.4; Table 9; Fig. 3]
- P2 (Major). Analyst burden is unknown: there is no warnings-per-target figure, no precision, and no triage time. An auditor needs "how many warnings do I read to find one bug". [§6.2, §6.5]
- P3 (Major). The brain is a commercial model with no version pin ("Claude Sonnet, high reasoning effort"), and the open-weight run is optional (E7). Exact reproducibility is impossible, so the artifact must ship every raw transcript, and the paper should state the model snapshot and the date. [§5.5; Open Science]
- P4 (Major). The design has three parts (procedure, deterministic tools, validator), and only "procedure+tools vs. nothing" is measured. The paper's own diagnosis that "the procedure mainly makes the model look in the right place" invites the question of what the tools add. The author has decided against new LLM ablation runs. At minimum, report tool-call counts and the rows a tool answer changed, from existing transcripts. [§6.2 l.172–173; TODO note 3]

**Stakeholder check** [§6.4; Ethics; Open Science]
- *Benefits:* developers and auditors (checklist, tool), the research community (dataset).
- *Who bears the cost:*
  - Maintainers of the three new-flaw projects. The disclosure timeline and embargo are not stated: there is no date, no response window, and no statement on publication if unfixed.
  - Auditors whose public reports are relabeled. Table 4 names firms and severities, which is fine for public reports, but the released labels effectively grade audit firms. A sentence on this belongs in Ethics.
  - End users of live versions scanned in the hunt ("current versions of the same projects"). The paper should confirm that no exploit details go into the artifact before fixes land.
- *Left out:* non-EVM consumers (zkVM hosts, off-chain verifiers) are excluded from E2/E4, and §7.4 says so.

---

### DA: Devil's Advocate

**Recommendation: 2 Weak Reject as written / 1 Reject measured only. Confidence 4/5.**

#### Strongest counter-argument (about 280 words)

Strip away the DEMO text and the tool contribution is this. On real audited flaws, BindCheck finds 4 of 14 (round 1) and 2 of 8 (round 2, the only clean set) at the claimed granularity. The 95% interval for round 2 is 0.07–0.59, so the data cannot distinguish BindCheck from a coin that lands heads one time in ten. The only LLM comparator that was run scores 3/14 on round 1, one fewer, and it was never run on round 2 or the mutants.

The headline that "existing analyzers find none" compares an LLM against Slither, Mythril and circuit linters. The paper itself argues these cannot see the property by construction (§3.1 "Why neither layer suffices", Table 5), so the comparison demonstrates the definition, not the tool.

The 22/27 on B2 comes from mutants the authors wrote into three small hosts (one a proof of concept), using the same five-pattern taxonomy the procedure's playbooks encode. That is a test of whether the procedure recognises its own patterns.

The evidence ladder that would make warnings trustworthy (E2, E4) does not exist yet. The new-flaw hunt has not been run. The one improvement claimed (v3: 9/14, 5/8) would be measured on test items whose misses the authors have already dissected.

A PC member can reasonably conclude that the strong contribution is the definition plus measurement, and that the tool is an unvalidated prototype whose real-world recall is statistically indistinguishable from the bare model. The paper would be stronger, and more honest, framed that way. As submitted, it oversells the tool in the abstract ("confirms warnings by replaying real proofs") and buries the 2/8.

#### Issue list

| # | Severity | Dimension | Issue | Evidence anchor |
|---|---|---|---|---|
| DA-1 | CRITICAL | validity | Real-flaw recall (2/8 clean; 6/22 total) is not shown to exceed the plain-LLM ablation. The comparator is missing on R2 and B2, and R1's 4 vs 3 has McNemar p = 1. | Table 6 rows "Plain LLM", "BindCheck"; §6.2 l.168–173 |
| DA-2 | CRITICAL | integrity | The v3 DEMO "9 of 14 and 5 of 8" would be measured on test items after a miss analysis of those items, which makes it test-tuned. | evaluation.tex:174–175, 227–228 |
| DA-3 | CRITICAL (if weaker) | contribution | RQ3 new flaws are all DEMO. With 2/8 recall, RQ3 is the only real-world evidence for the tool. Zero new flaws leaves the tool without validation. | §6.4; abstract l.20–21 |
| DA-4 | MAJOR | circularity | B2 mutants are author-written from the same taxonomy the playbooks encode, with no plain-LLM row. Small hosts favor any LLM. | §6.1 B2; Table 7 |
| DA-5 | MAJOR | overclaim | The abstract says the tool confirms warnings by real-proof replay, but A3 is unimplemented. | abstract l.16–17; design.tex:173–178 |
| DA-6 | MAJOR | overclaim | "Most misses sit in zkVM guest programs" (intro). Only the 6 R2 misses of the 16 test misses are classified (3 guest-side), and the 10 R1 misses are not (E11 pending). The takeaway box's "most" covers only R2 (4 of 6). | intro.tex:83–84; evaluation.tex:222–223, 227–231 |
| DA-7 | MAJOR | scope | The headline 103 includes 16 findings that §2.2 places out of scope. | Table 2; background.tex:56–62 |
| DA-8 | MAJOR | premise | The premise that "Binding flaws are decided by comparing two artifacts that no single analyzer reads together" (§5 opening) rests on DEMO D3 (61% need both layers). If most are consumer-decidable, a taint rule ("calldata → transfer recipient, not in verifier args") could be a strong non-LLM baseline that was never built. | design.tex:3–5; study.tex:191–195 |
| DA-9 | MINOR | consistency | Several internal inconsistencies, listed in the synthesis. | various |

#### Ignored alternative explanations
- BindCheck's B2 advantage may come from small host size rather than from the procedure. A plain LLM on B2 would test this.
- The 4 vs 3 on R1 may be run-to-run variance (§7.3 says ±1–2 items between runs).
- The "zero for non-LLM tools" result may say more about the choice of baselines than about the difficulty of the class. A 50-line Slither detector for "calldata-derived transfer target not in verifier-call arguments" is the obvious missing baseline.

#### Missing stakeholder perspectives
- The audit firms whose findings form the ground truth: severity ratings are taken at face value, and 34 of 103 are unrated.

#### What would flip DA to Accept (concise; the full plan is in §2c)
1. Run the plain-LLM arm on R2 and B2, three runs each. If BindCheck beats it on B2 with McNemar p < 0.05 (at 22/27 with no LLM-only hits, the plain LLM must score ≤ 16/27), the procedure is shown to matter.
2. Pre-register and run a fresh round 3 with ≥ 25 positives and report it once.
3. Land at least one E4-confirmed new flaw with disclosure status.
4. Reframe the abstract to lead with the definition and measurement, report 6/22 (9/22 mechanism) plainly, and drop every v3-on-R1/R2 number.

#### Observations (non-defects)
- The paper already discloses most of its leakage honestly, which a PC will credit.
