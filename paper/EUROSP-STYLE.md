# EuroS&P style notes (mental model for BindCheck)

Compiled 2026-11-25. Sources: IEEE Xplore proceedings TOCs for EuroS&P 2025 (70 entries) and 2026 (95 entries), read through the user's own browser session. Full texts came from arXiv, author or lab PDFs, or Xplore's HTML view in that browser session; I did not log in anywhere.

**Caveats.** (a) I scanned titles only to pick papers. I found no 2025/2026 EuroS&P paper on ZK-circuit bug detection or LLM-agent smart-contract auditing, so the closest matches below are analogues. (b) I could not verify awards. "Well-cited" below means Xplore's "Cited by" count. (c) Reading depth: introductions, structure, contribution lists and evaluation setups were read closely. Body sections of the long papers were skimmed.

## 1. Papers read

| # | Paper | Year | Source read | Topic |
|---|---|---|---|---|
| 1 | CHARON: Polyglot Code Analysis for Detecting Vulnerabilities in Scripting Languages Native Extensions (Scholtes, Khodayari, Staicu, Pellegrino) | 2025 | https://ieeexplore.ieee.org/document/11129355 (Xplore HTML) | static analysis, vulnerability detection, ecosystem scan |
| 2 | LibAFLGo: Evaluating and Advancing Directed Greybox Fuzzing (Geretto, Jemmett, Giuffrida, Bos) | 2025 | https://download.vusec.net/papers/libaflgo_eurosp25.pdf | fuzzing, evaluation methodology |
| 3 | Cybersquatting in Web3: The Case of NFT (Ma, He, ..., Wang) | 2025 | https://arxiv.org/abs/2504.13573 | blockchain measurement |
| 4 | Commitment Attacks on Ethereum's Reward Mechanism (Sarenche, Tas, Monnot, Schwarz-Schilling, Preneel) | 2025 | https://arxiv.org/abs/2407.19479 | blockchain protocol attack and incentive analysis |
| 5 | CTINexus: Automatic Cyber Threat Intelligence Knowledge Graph Construction Using LLMs (Cheng, ..., Song, Gao) | 2025 | https://arxiv.org/abs/2410.21060 | LLM tool; well-cited (26 Xplore citations) |
| 6 | ARVO: Atlas of Reproducible Vulnerabilities for Open-Source Software (Mei, ..., Dolan-Gavitt) | 2026 | https://arxiv.org/abs/2408.02153 | vulnerability dataset, benchmark for LLM agents |
| 7 | High Impedance: Analysis of Publicly Disclosed Vulnerabilities in FPGA IP Cores (Chowdhury, Ackermann, Bugiel) | 2026 | https://ieeexplore.ieee.org/document/11624330 (Xplore HTML) | vulnerability-class characterization |
| 8 | SoK: Understanding the state of IoT-specific vulnerabilities via CVE characterization with LLIoT (Rezaei, ..., van Rijswijk-Deij) | 2026 | https://ieeexplore.ieee.org/document/11624213 (Xplore HTML) | characterization plus LLM classifier |
| 9 | The Unbearable Randomness of Fuzzing (Zhang, Malmain, Oliveri, Balzarotti, Francillon) | 2026 | Eurecom PDF, https://www.eurecom.edu/publication/8694/download/sec-publi-8694.pdf | fuzzing measurement/methodology |
| 10 | Security-by-Design for LLM-Based Code Generation (Wendlinger, Kowatsch, Böttinger, Sperl) | 2026 | https://arxiv.org/abs/2603.11212 | LLM and code security |

Skipped: no smart-contract detection tool, ZK bug paper or LLM-agent bug-finder was found in either program. Papers 3–4 are the nearest blockchain ones, and 5, 6, 8 and 10 are the nearest LLM ones.

## 2. Section structure and page share

EuroS&P uses two-column IEEE format. Observed length is 14–16 pages including references for full papers (CHARON 16, ARVO 14, Randomness 14). Some run 19–23 with appendices and long reference lists (FPGA 20, LibAFLGo 20, Commitment 23).

| Paper | Observed sections |
|---|---|
| CHARON | Intro; Background & Motivation (with a motivating example and a threat table); CHARON design (preprocess, graph linking, queries, implementation); Empirical Evaluation; Discussion |
| LibAFLGo | Intro; Background; Issues in Directed Fuzzing Studies; Design; Existing Fuzzers on LibAFLGo; Evaluation; Related Work; Conclusion; appendix tables |
| Cybersquatting | Intro; Background; Study Design; Detection results; Characterization; Actors and financial impact; Discussion; Related Work; Conclusion |
| Commitment Attacks | Intro (consensus, incentives, contributions); Related Work; Preliminaries; Simple Attack; Strong Simple Attack; Extended Attack; Staking Pools; DAG Votes defense; Conclusion; Responsible Disclosure |
| CTINexus | Intro; Background & Motivating Example; Overview; Design; Evaluation (RQ1–RQ6); Discussion; Related Work; Conclusion |
| ARVO | Intro; Background & Related Work; Reproducibility; ARVO; Dataset; Case Studies; Discussion (limitations); Conclusion; Open Science; Ethics |
| FPGA IP cores | Intro; Background; Related Work (§3); Motivation & RQs; Methodology; Results (8 subsections, one per RQ theme); Threats to Validity; Discussion; Conclusion |
| LLIoT SoK | Intro; Systematization of prior work; Methodology; Taxonomy and expert review; Large-scale classification; IoT vs non-IoT characteristics; Discussion (recommendations, limitations, future work); Conclusion; appendices (prompt, review UI) |
| Randomness | Intro; Background; Methodology; Experiment results; Discussion; Conclusion |
| SCS-Code | Intro; Related Work; Theoretical Background; Concept Representation (analysis and method); Comparative Evaluation; Discussion; Conclusion |

**Common pattern (approximate share of body pages):** Intro 8–12% · Background / motivating example 8–15% · Core design or study method 20–35% · Evaluation / results 30–45% · Discussion + limitations 5–10% · Related work 3–6% · Conclusion ~3%.

- Contribution-heavy papers (tools, datasets) put the design section before the evaluation.
- Measurement and characterization papers put method and results first and push most of the analysis into one long "Results/Characterization" run. FPGA has 8 results subsections and LLIoT has 4 analysis subsections.
- Every paper has a motivating example or concrete case before the design. CHARON uses a real `dulwich` cross-language overflow as Fig. 1, and CTINexus uses a real CTI report as Fig. 1.

## 3. How introductions are built

The intros are 1–2 pages and follow a fixed arc.

1. **Hook.** Start with scale or stakes. Examples are ARVO's NVD count (about 40,000 vulnerabilities in 2024), the NFT market over $10B, and IoT growing to 31B devices.
2. **Gap through prior work.** Name the specific limitation of prior work, ideally with numbers.
   - Cybersquatting shows false negatives and false positives of the prior Levenshtein approach with concrete names (Azuki, CryptoCars/CryptoDads).
   - ARVO says 63% of historical OSS-Fuzz builds fail and the prior best reproduces 37%.
   - LibAFLGo lists "three critical issues": baseline, methodology, analysis stack.
   - CTINexus lists drawbacks of prior methods as (1) lack of generalizability and (2) inaccuracy.
3. **"This work" paragraph.** An informal overview with headline numbers. CHARON states 11.8K packages, 5,813 confirmed flows in 116 packages, and about 6x more true positives. Cybersquatting states 220K collections, 8,019 squatting collections, and $59.26M.
4. **Contribution list.** A bullet list of 3–5 items (CHARON has 4, ARVO has 4). Items are nouns plus numbers: a system or technique, a dataset, a measured result, and an exploit or PoC count. "First" claims are common ("the first inter-procedural, polyglot static analysis"). Sections are often cross-referenced ("see §5").
5. **Results preview and impact.** Numbers appear in the abstract, intro and evaluation. ARVO also reports uptake: Google is integrating it, and AIxCC teams used it.
6. **"We found X bugs" framing.** Papers report counts of confirmed items, not raw alerts. CHARON separates 17,268 flows from 5,813 manually confirmed and 63 PoCs. The framing is count, then verification level, then impact (advisories issued, maintainers contacted).

Abstracts are a single paragraph of 200–250 words in the order problem, gap, approach, headline numbers, implication.

## 4. Tone and writing style

- **Claim strength.** Strong but anchored: "first" claims are used with "to the best of our knowledge" (Randomness, LLIoT). Numbers carry the claims. Negative or surprising findings are stated plainly (LibAFLGo: no directed policy beat non-directed LibAFL overall).
- **Hedging.** Placed on limits, not on results. CHARON states its false positive rate (about 66%) openly, attributes 99.9% of FPs to standard static-analysis issues and the Joern engine, and does not oversell. ARVO has a dedicated Limitations subsection.
- **Person.** "We" throughout. Passive voice appears only in method steps.
- **Takeaway boxes.** Used sparingly. LibAFLGo ends the evaluation with a "Takeaways" subsection of three numbered observations. Others use a bold lead sentence per finding.
- **RQ style.** Used by tool and evaluation papers (CTINexus RQ1–RQ6, LibAFLGo Q1–Q3). Characterization papers (FPGA) group RQs by theme ("Disclosure of IP Core Vulnerabilities...") and map each RQ to a Results subsection. RQs are questions, not hypotheses.
- **Reproducibility language.** Counts, dates and versions are stated (CHARON: npm/PyPI snapshot May 2021, 4,421 LoC, Joern engine).

## 5. Figures and tables

- **Counts.** Roughly 5–9 figures and 6–14 tables per paper. Cybersquatting has about 13 figures and 8 tables. ARVO has 5 figures and 4 tables. LibAFLGo has 1 figure and 14 tables.
- **Figure 1 is almost always one of:** an overview of the problem with a real example (CHARON: vulnerable cross-language flow; CTINexus: the knowledge graph produced by prior tools versus the proposed tool; Cybersquatting: NFT lifecycle), or a schematic of the workflow (LibAFLGo). A system architecture is usually Fig. 2.
- **Comparison and capability matrices.** Used to position against prior work. ARVO Table 1 compares datasets by type, size and features. LibAFLGo Tables 1–2 summarize prior papers' prototype features and experiment choices. FPGA and LLIoT systematize prior work in a table or taxonomy.
- **Result tables.** Per-benchmark tables with median and statistical columns (LibAFLGo hazard ratios), top-k tables for measurements (Cybersquatting top-5 collections, top-5 scam campaigns), and ablation tables for LLM tools (CTINexus Tables III–IX on example counts, permutation, merging threshold, backbone model).
- **Algorithms and pseudocode** appear in analysis tools (CHARON Algorithms 1–2). Per-class summary tables are common (CHARON Table 4 by vulnerability type and Table 7 of exploitability).

## 6. Evaluation conventions

- **Baselines.** The strongest available prior tool or a modern re-implementation. LibAFLGo builds its own modern baseline (LibAFL) because old baselines produce "imaginary" gains. CHARON compares polyglot analysis with a single-language Joern taint analysis. CTINexus compares with three named prior tools.
- **Ground truth.** Manual verification is standard. CHARON uses semi-automatic clustering of data-flow prefixes, then manual review. CTINexus uses three PhD annotators with an arbiter and reports average Cohen's kappa 0.73. LLIoT builds an expert-validated ground-truth set, validates the LLM against it, then scales and reports 92% unanimity. ARVO uses developer patches as ground truth and measures 89.4% accuracy on located patches.
- **Statistics.** Required for fuzzing and LLM variance: repeated trials, survival analysis with hazard ratios (LibAFLGo), and a whole paper on the number of repetitions needed (Randomness).
- **New bug reporting.** Reports confirmed new findings with a verification level and PoCs. Disclosure and advisory status are stated (CHARON: reports to maintainers, community advisories, 9 Joern bugs reported and 6 patched).
- **Datasets released.** ARVO, LLIoT and FPGA release data. A new curated dataset with a stated annotation protocol is expected when existing ones are outdated (CTINexus: 150 reports from May 2023 onward).
- **Ethics and artifact sections.** ARVO has "Open Science" (code, data, evaluation data URLs) and "Ethics Considerations" (only public data used; reported to OSS-Fuzz) just before references. Commitment Attacks has a "Responsible Disclosure" section: they contacted the Ethereum Foundation, which supported the work. Threats to Validity is its own section in the characterization paper (FPGA) and a Limitations subsection elsewhere.

## 7. Related-work placement

Two layouts occur. In the late layout (LibAFLGo, CTINexus, Cybersquatting) it comes after Discussion and before Conclusion, at 0.5–1 page. In the early layout (Commitment Attacks §2, SCS-Code §2, FPGA §3, ARVO §2 "Background and Related Work") it comes right after the intro. Characterization and SoK papers use the early layout and add systematization of prior work as a main section. Prior work that is closest is also discussed inside the intro's gap paragraph, so the related-work section is rarely the only place a reviewer sees comparisons.

## 8. Reviewer-expectation checklist for BindCheck (vulnerability-class characterization + LLM-agent detector)

**Positioning**
- [ ] Define the vulnerability class precisely, with a taxonomy, a threat model, and one motivating real example as Figure 1 (the way CHARON uses `dulwich`).
- [ ] State exactly what prior detectors miss, with numbers or a concrete counter-example (as Cybersquatting does for Levenshtein).
- [ ] Contribution list of 3–5 bullets: characterization, tool, dataset, and a confirmed-findings count with verification level.

**Characterization part**
- [ ] Explicit data collection protocol with sources, dates, filtering counts and a funnel table (CHARON Table 3, FPGA's filter step).
- [ ] RQs grouped by theme, each mapped to one results subsection.
- [ ] Ground truth built by independent annotators with an arbiter, agreement reported (kappa), and a released dataset (CTINexus, LLIoT).
- [ ] Threats to Validity as a separate section.

**Tool part**
- [ ] Strongest feasible baselines, including a non-LLM static tool and a plain-LLM variant, run on identical inputs. A baseline must not be an outdated one (LibAFLGo's point).
- [ ] Ablations of the agent design (prompts, tools, model, number of examples) as in CTINexus.
- [ ] Repeated runs with variance and statistical tests, because LLM output is stochastic. Report cost and time per target.
- [ ] Report false positives honestly, with the FP rate and root causes (CHARON reports about 66%).
- [ ] Report a verified count: raw alerts, then manually confirmed, then PoC or committed effect. Never headline raw alerts.
- [ ] Separate development cases from held-out cases, and say which is which.

**Disclosure and artifacts**
- [ ] Disclosure status per finding (reported, confirmed, fixed, advisory or CVE where applicable), plus an Ethics section covering local-only experiments and no live-system testing.
- [ ] Open Science / artifact statement with code, dataset and prompts, plus pinned versions and hashes.
- [ ] Limitations section stating what the tool cannot see, in the style of ARVO and CHARON.

**Style**
- [ ] Abstract in the problem → gap → approach → numbers → implication order, with headline numbers in the abstract and intro.
- [ ] "First" claims only with a related-work table that supports them. Related work as a matrix of capabilities, with a short prose section either early or just before the conclusion.
- [ ] A takeaways line per RQ result. State null or negative findings plainly.

## Open items

- No award papers verified. If awards matter, check the EuroS&P 2025/2026 program pages for best-paper listings.
- Papers 1, 7 and 8 were read through Xplore HTML in the browser; the first two sections of each and the structure were read, not every body paragraph.
