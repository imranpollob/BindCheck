# Lane P — paper draft status

**Branch** `zk-paper` · **Date** 2026-11-09 · **Base** `b0cdad7` (analyzer freeze `8ea6d223…`)
**Status:** first complete draft; compiles; **not submission-ready**.
45 `\MISSING` placeholders are listed below. Two findings from this lane (§4) need
human decisions before any result is reused.

> **S8 update (2026-11-18).** The A4 draft builds to 12 pages including references and appendices. The official EuroS&P template archive still needs comparison. The generator table, candidate analyzer and oracle design, related work, disclosure placeholders and page budget are documented in the [S8 handoff](../../reports/S8/REPORT.md). The current rendered PDF is the ignored `results/raw/S8/after/main.pdf`. The tracked PDF and the inventories below describe earlier drafts.

> **S8a update (2026-11-18, EuroS&P 2027 framing).** The abstract (`sections/abstract.tex`),
> introduction, new motivating example (`sections/motivating.tex`, `figures/f0-aztec-extent.tex`),
> threat model/definitions and taxonomy were rewritten for EuroS&P 2027. `\MISSING` #1 (abstract)
> and #21 (intro held-out bullet) are now `\TODO{S5}` placeholders; the S8a sections use `\TODO{lane}`.
> The ZKredential figure moved to `cases.tex`. `main.pdf` was **not** rebuilt in git (compiler output);
> the S8a build is under ignored `results/raw/S8a/build/`. Details and the placeholder list:
> [`reports/S8a/REPORT.md`](../../reports/S8a/REPORT.md). The rest of this file describes the S&P draft.

## 1. Deliverables and build

| File | Content |
|---|---|
| `main.tex`, `macros.tex` | IEEEtran `conference,compsoc`, US letter, anonymous |
| `sections/*.tex` | 12 section files + appendix |
| `figures/f1–f4*.tex` | TikZ/pgfplots; F3/F4 read `data/*.dat` |
| `refs.bib` | 31 entries; uncertain ones carry `note = {VERIFY…}` (§6) |
| `main.pdf` | 13 pages (main text ends on p. 11; references p. 12; appendices p. 12–13) |
| `scripts/` | 6 read-only scripts that produce every number not quoted from a lane report |
| `data/` | their outputs (JSON / `.dat`) |

Build: `sh paper/zk/scripts/regen.sh` from the repo root (regenerates `data/` and
runs `tectonic -X compile main.tex`). Tectonic 0.17.0. Last run: exit 0, no LaTeX
errors, no overfull boxes; only cosmetic underfull warnings. The rerun reproduced
`data/frozen-dev-stats.json` exactly.

Provenance convention: every number in the `.tex` sources has a `% src:` comment
naming the file and section/JSON key it came from.

## 2. CFP compliance (IEEE S&P 2027, fetched 2026-11-09)

Source: https://sp2027.ieee-security.org/cfpapers.html. Cycle 2: abstract registration
**10 Nov 2026**, paper **17 Nov 2026** (AoE).

| Rule | Draft |
|---|---|
| `\documentclass[conference,compsoc]{IEEEtran}`, 1.8b, US letter, no spacing hacks | done (tectonic bundle's IEEEtran; version not separately checked — **verify 1.8b**) |
| ≤13 pages main text, ≤5 pages refs + appendices, ≤18 total | 11 + 2 |
| Anonymous; no IEEE placeholder names | "Anonymous Submission"; no self-citation. The draft **names two undisclosed third-party projects** (§4g) |
| Manuscript must disclose and motivate generative-AI use (and HotCRP field) | §11 "Use of generative AI"; model/volume/hardware details `\MISSING` |
| Ethics field in HotCRP; ethics section required at camera-ready | §11 drafted; HotCRP text is for the authors |
| Disclosure done or detailed plan; required by rebuttal deadline; no full CVE IDs | §11 states drafts are unsent; plan `\MISSING` |
| Anonymized artifact, frozen at deadline | §11 open-science plan; URL `\MISSING` |

## 3. Target tables and figures

| Brief target | In paper | State |
|---|---|---|
| T1 taxonomy + examples + SoK mapping | Table 1 (`tab:taxonomy`) | done; zk_voting P5 and verifier-kind entries are AI opinion |
| F1 ZKredential flow | Fig. 1 (`fig:zkredential`) | done |
| F2 BindCheck pipeline | Fig. 2 (`fig:pipeline`) | done |
| T2 benchmark composition | Table 2 (`tab:benchmark`) | done; EVAL/gate rows `\MISSING` |
| T3 tool × pattern | Table 5 (`tab:toolpattern`) | synthetic set, **pre-freeze analyzer** (§4c) |
| F3 precision vs decided rate | Fig. 3 (`fig:scatter`) | synthetic screening only; EVAL version `\MISSING` |
| T4 unsafe certifications + pair discrimination | Table 6 (`tab:unsafe`) | partial; frozen synthetic and A/C DEV adjudication `\MISSING` |
| T5 circuit ablation | Table 8 (`tab:ablation`) | skeleton only |
| T6 held-out funnel + per-pattern | Table 9 (`tab:heldout`) | first three stages filled; rest `\MISSING` |
| T7 verifier census | Table 10 (`tab:census`) | done |
| T8 confirmed findings | Table 11 (`tab:findings`) | done; disclosure status `\MISSING` |
| F4 runtime distribution | Fig. 4 (`fig:runtime`) | DEV frozen run; EVAL `\MISSING` |
| (added) evidence per verdict | Table 3 (`tab:evidence`) | done |
| (added) unsafe-certification mechanisms | Table 4 (`tab:failures`) | done; row (vi) fix `\MISSING` |
| (added) frozen DEV outcomes | Table 7 (`tab:dev`) | done |

## 4. Findings from this lane that need a human decision

**(a) The frozen analyzer's P4 default-key check cannot fire (unsafe certifications).**
`bindcheck_zk/p4.py:16` sets the third coordinate of `BN254_G2` to
`4082367875863431332203403145435568316851327593401208105741076214120093531` (73 digits).
The EIP-197 value is `4082367875863433681332203403145435568316851327593401208105741076214120093531`
(76 digits; four digits `3681` missing). The encoded point is not on the BN254 twist;
the EIP-197 point is (`data/p4-g2-constant-check.json`: `frozen_on_twist=false`,
`eip197_on_twist=true`). The defect has been present since `9ffc8c9`.
Re-running only `p4.analyze_source` in memory with the EIP-197 constant changes the
outcome for **16 verifier files in 8 DEV repositories**. These are the same 16
default-key files found by `feasibility/v2/REPORT.md` §5, whose scanner uses the
correct constant. In the controlling frozen run, **3 of those files in 2 rows
(DEV-F09 zk-poll, DEV-F14 meridian-link)** received `VERIFIED_WITHIN_SCOPE /
VERIFICATION_KEY_CHECKS_PASS` (`data/p4-unsafe-certifications.json`).
`dataset/census_sourcify.py` and `feasibility/v2/scan_p4.py` use the correct
constant, so the census (43) and the 16-file source count are unaffected.
I did **not** fix it: this lane may not edit `bindcheck_zk/`, and FREEZE rule 1
requires a new freeze declaration. The paper reports it as mechanism (vi) and
footnotes the 17 P4 certifications in Table 7.
*Decision needed:* fix and re-freeze before any EVAL run. The fix is not motivated
by EVAL, gate or adversarial outcomes, so it does not by itself expose cases.

**(b) The brief's zk_voting premise is only half right.** "Real defect yet not
practically exploitable" holds for a hash-valued nullifier: an alias passes the
`q` check only if `n < q−r`, which is 127 bits against a 254-bit `r`, so the
probability is below 2^-126 (`data/zkvoting-alias.json`). In the pinned repository,
however:
- the circuit declares no public inputs (R1CS: 0 public inputs, 1 output);
- the verifier's only public signal is `isVoteValid`, a value in {0,1};
- `nullifierHash` is not in the R1CS (sym wire −1, checked by an `assert` on a `var`);
- the consumer reads `input[0]` as the nullifier;
- the key has γ = δ (`data/zkvoting-facts.json`).

So the alias is reachable here, and the application has worse problems: a P5
meaning mismatch, an underconstrained circuit, and a forgeable default key. §9.4
says this and labels it AI opinion from source reading at E1. *Decision needed:*
author review; optional E2–E4 attempt.

**(c) The synthetic comparison used the pre-freeze analyzer.** The red-team BindCheck
run executed at `011042e`, whose `bindcheck_zk` git tree equals `feb5c19`/`cd56c24`
(content `2741c40e`), not the frozen `8ea6d223`. All T3/F3 BindCheck cells are
labelled pre-freeze, and a rerun is `\MISSING`.

**(d) CLAIMS.md A26 wording.** The permitted wording says the 43 γ=δ deployments are
"on six of seven queried chains". Rows exist on six chains, but γ=δ deployments are on
**four**: Ethereum 13, Optimism 7, Polygon 1, Base 22
(`data/census-by-chain.json`). The paper uses "four of the seven".

**(e) Brief vs. evidence on "sound verdicts other tools cannot give".**
- `docs/FREEZE-2026-11-09.md` forbids comparative claims.
- (a) shows the frozen version is not sound for P4.
- `RELATED-WORK.md` §5.1 shows that every P1/P3 violation is reachable without the circuit.

The draft therefore claims scope/priority (hedged), fail-closed restraint on paired
cases, zkDrops pair discrimination (exposed), and the E4 findings. It does not claim
superiority or soundness.

**(f) Research contract scope.** §1 of the contract still names a Noir/ACIR producer.
This paper is Circom/Groth16 (also flagged in `reports/groundtruth/REPORT.md` §1,
item 7). A dated contract revision is needed before submission.

**(g) Naming undisclosed projects.** ZKredential and RacePass are named as the brief
asks, but both disclosures are unsent drafts. The authors should decide whether to
pseudonymize them until disclosure completes; the CFP requires disclosure by the
rebuttal deadline.

**(h) Numbers derived here, not in a lane report.** The following come from raw
controlling-run files via this lane's scripts and should be audited:
- frozen DEV runtimes: median 0.431605 s, max 53.799863 s (DEV-F09), sum 235.450396 s;
- decided/applicable per pattern;
- the 11 frozen violation rows;
- the pair-discrimination table;
- census by chain;
- the zk_voting facts;
- the P4 constant check.

**(i) PDF committed.** `AGENTS.md` says not to commit compiler output, but the brief
lists the PDF as a deliverable, so `main.pdf` is tracked. `main.log` is ignored.

## 5. Every `\MISSING`, and who fills it

| # | Location | Placeholder | Filled by |
|---:|---|---|---|
| 1 | main.tex:24 | abstract | human authors (locked at HotCRP registration) |
| 2 | appendix.tex:21 | UNKNOWN reason-code distribution, DEV + EVAL | lane EVAL |
| 3 | benchmark.tex:28 | signed human adjudication of 46 synthetic labels | lane redteam + human raters |
| 4 | benchmark.tex:63 | reviewed recall expectations, 16 gate pairs | human reviewers (`review/recall/`) |
| 5 | benchmark.tex:85 | human maturity review, 278 families | human reviewers (`review/maturity/`) |
| 6 | benchmark.tex:109 | Table 2 gate-pair status "run" | lane EVAL (recall) |
| 7 | benchmark.tex:110 | Table 2 EVAL status "run" | lane EVAL |
| 8 | benchmark.tex:116 | Table 2 footnote: frozen synthetic rerun | lane redteam |
| 9 | cases.tex:8 | advisor-reviewed policies, ZKredential/RacePass | lane impact + advisor |
| 10 | cases.tex:23 | Table 11 ZKredential disclosure status | advisor (disclosure) |
| 11 | cases.tex:24 | Table 11 RacePass disclosure status | advisor (disclosure) |
| 12 | cases.tex:27 | Table 11 zk_voting disclosure plan | advisor + lane impact |
| 13 | design.tex:151 | P4 constant fix, new freeze, DEV rerun | lane soundness (§4a) |
| 14 | design.tex:175 | Table 4 row (vi) "fix + refreeze" | lane soundness |
| 15 | discussion.tex:37 | held-out results | lane EVAL |
| 16 | ethics.tex:15 | misuse and release analysis | human authors |
| 17 | ethics.tex:23 | disclosure dates/channels/responses; plan for zk_voting and default-key verifiers | lane impact / advisor |
| 18 | ethics.tex:30 | naming decision for undisclosed projects | human authors (§4g) |
| 19 | ethics.tex:44 | AI models/versions, query volume, hardware, environmental rationale, inspection procedure | human authors |
| 20 | ethics.tex:55 | anonymized artifact URL | human authors / artifact lane |
| 21 | intro.tex:120 | held-out run (contribution bullet) | lane EVAL |
| 22 | methodology.tex:47 | zkFuzz, ELSA, CIVER, circuit-ablation runs | lane redteam / lane ablation |
| 23 | methodology.tex:88 | two-rater blind adjudication + κ (16 DEV groups, all EVAL warnings) | human raters |
| 24 | related.tex:50 | read SlowMist aliasing post | lane related / authors |
| 25 | results.tex:9 | synthetic rerun at 8ea6d223 | lane redteam |
| 26 | results.tex:94 | root cause of 3 synthetic false alarms at frozen revision | lane redteam |
| 27 | results.tex:129 | Table 6 arm A DEV unsafe certifications (adjudicated) | human raters + lane redteam |
| 28 | results.tex:131 | Table 6 arm C DEV unsafe certifications (adjudicated) | human raters + lane redteam |
| 29 | results.tex:133 | Table 6 frozen BindCheck synthetic M | lane redteam |
| 30–34 | results.tex:213–214 | Table 8 ablation cells (DEV no-circuit, diff; EVAL full, no-circuit, diff) | lane ablation (+ EVAL) |
| 35 | results.tex:217 | Table 8 fill note: ablation run at 8ea6d223 | lane ablation |
| 36 | results.tex:224 | held-out run, per-stratum decided rates, 95% family-resampled intervals | lane EVAL |
| 37 | results.tex:226 | gate-pair recall, exposed (5) / unexposed (11) | lane EVAL after human review |
| 38–43 | results.tex:242–248 | Table 9 funnel: acquired, builds, triples, verdicts, adjudication, E4 | lane EVAL (+ raters, impact for E4) |
| 44 | results.tex:274 | consumer linkage for 43 default-key verifiers | census lane |
| 45 | results.tex:309 | EVAL runtime distribution | lane EVAL |

Line numbers are from the committed sources. Regenerate this list with the
snippet in `scripts/` history or `grep -n '\\MISSING{' paper/zk/**/*.tex`.

## 6. Other open items

- **Bibliography.** These entries are marked `VERIFY` and have unconfirmed
  authors, titles or years: zkp-tools-study, elsa, zkfuzz, ccccheck, civer, zequal,
  zkcraft, coda, smartaxe, zkdrops-pr2, payy-ghsa, binding-design-2606, circuzz,
  lietome, rollup-formal, freever and slowmist. The authors must check each one
  against its primary source.
- **AI-opinion items in the text** (marked "AI opinion" or \aiop):
  - verifier-kind classes of warning groups;
  - zk_voting interpretation;
  - ZKredential/RacePass policies;
  - synthetic labels;
  - controls.
- **Not pooled:** the historical `bindcheck_d1` lineage (Appendix B) stays separate,
  per CLAIMS §B.
- **Not done here:** no analyzer, EVAL, recall or baseline run; no change outside
  `paper/zk/`; no transaction, maintainer contact, push or merge. `README.md` and
  `docs/project-status.md` were not edited, as the brief requires. The AGENTS.md
  checkpoint rule is therefore not applied.

## 7. Recommended next task

Fix §4a on a builder branch:
1. Commit a regression control with a real snarkjs default-key verifier
   (expected `UNKNOWN / DEFAULT_G2_GAMMA_DELTA_SOURCE_WARNING`) first.
2. Correct the constant.
3. Declare a new freeze.
4. Rerun the 56 DEV rows.

**Completion criterion:**
- DEV-F09 and DEV-F14 no longer report P4 `VERIFIED_WITHIN_SCOPE`;
- all 16 default-key files report the default-key reason;
- every other verdict change is explained;
- `data/` and Tables 4, 6 and 7 are regenerated from the new run.
