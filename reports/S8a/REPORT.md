# S8a — Paper draft: framing sections for EuroS&P 2027
Status: DONE
Verdict/outcome: Framing sections drafted and building (tectonic exit 0, no LaTeX warnings, no overfull boxes). Held-out (S5), generator (S1), disclosure/naming (S7) and oracle (F2) content are explicit `\TODO{lane}` placeholders.

AI disclosure: Claude Code (Anthropic), model Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-18, worktree `$BC/wt-S8a`, branch `sprint/S8a`. The model wrote all prose, the TikZ figure, the bib additions and this report. The human author has not reviewed the text yet. The class labels it relies on (R1, R2) are AI-proposed and also await author review (R1b).

## What was done

Read `AGENTS.md`, `docs/orchestration/README.md`, the S8a prompt, `docs/sprint-eurosp-2027.md`, `docs/orchestration/DECISIONS.md`, `docs/research-contract.md`, `paper/zk/STATUS.md`, the S&P-era `main.tex`/`intro`/`threat`/`taxonomy`/`background`, `reports/AZ1/REPORT.md`, `reports/S2c/REPORT.md`, `reports/PP/DISCREPANCIES.md`, `reports/R1/REPORT.md` + `incidents.csv`, `reports/R2/REPORT.md` + `findings.csv`, `reports/S4/REPORT.md` (design only) and `reports/impact/REPORT.md`. Then wrote or rewrote these deliverables:

| # | Deliverable | File(s) |
|---|---|---|
| 1 | Three title options; title 1 chosen | `reports/S8a/titles.md`, `paper/zk/main.tex` |
| 1 | Abstract: 174 words plus one S5 sentence of at most 26 words (≤ 200 total) | `paper/zk/sections/abstract.tex`; HotCRP plain text in `reports/S8a/abstract.txt` |
| 2 | Introduction: hook, Aztec example, signature lens, why single-layer tools miss, property, six contributions each tied to a section, four lessons | `paper/zk/sections/intro.tex` (rewritten) |
| 3 | Motivating example: Aztec Connect in 139 words of prose, plus a TikZ figure of proved rows vs. settled prefix | `paper/zk/sections/motivating.tex`, `paper/zk/figures/f0-aztec-extent.tex` (new) |
| 4 | Taxonomy: P1–P5 with signature analogues, extent binding P1(a)/P1(b) as a named refinement, Table 1 (instances and "checker must know"), Table 2 (`\input` of generated `T-incidents` + `T-audits`), Table 3 (`\input` of placeholder `T-generators`) | `paper/zk/sections/taxonomy.tex` (rewritten) |
| 5 | Threat model and definitions: system, adversary, trust, effects/permissions/obligations, authorization, coverage, binding flaw, proof coverage and extent, the 3 verdicts, the E0–E4 ladder | `paper/zk/sections/threat.tex` (rewritten) |
| 6 | This report | `reports/S8a/REPORT.md` |

Supporting changes in `paper/zk/`:
- `macros.tex`: added `\TODO{lane}`, `\input{../generated/numbers}`, `xfp` with `\usdM{}` (USD in millions from a generated macro), anonymised `\CaseA`/`\CaseB`, and the TikZ libraries `decorations.pathreplacing,patterns`.
- `main.tex`: new title, abstract `\input`, and the motivating section placed after the introduction. Header comment updated.
- `refs.bib`: 8 entries added (Aztec Labs, BlockSec, Rekt, Zellic Singularity, ABDK Railgun, zkSecurity Self, PSE Anon Aadhaar, Semaphore #16). URLs come from the R1/R2 CSVs and AZ1. Each carries `note = {… VERIFY …}`.
- `cases.tex`: the ZKredential figure float was moved here from the old introduction, because `cases.tex` is its only remaining reference. No other text changed.
- `STATUS.md`: a dated S8a note at the top. The S&P-era content is preserved.
- `docs/project-status.md`: one new S8a node and one checkpoint row, as `AGENTS.md` requires.

The S&P-era intro, threat and taxonomy sections are preserved at commit `96a8c7c` (and at base `6c73566`).

## Evidence (paths, hashes, commands, exit codes, tool versions)

- Base revision: `6c73566a88f2f974eddead90f3ed364570f8992d` (`origin/main`).
- Build: no `latexmk`, `pdflatex` or `xelatex` is installed. I used the system binary `/usr/lib/chatgpt/resources/tectonic/tectonic` (Tectonic 0.17.0, sha256 `a98aa59a…6da`); it fetched TeX bundle files over the network.
  ```sh
  cd paper/zk && tectonic -X compile --keep-logs --outdir ../../results/raw/S8a/build main.tex
  ```
  Exit 0 (`results/raw/S8a/build/exit.txt`). `main.log`: 0 `LaTeX Warning`, 0 `Overfull`; only underfull warnings in older sections. BibTeX warns about empty authors in `elsa` and `smartaxe` (pre-existing entries). Output: 15 pages, `results/raw/S8a/build/main.pdf`, sha256 `b0784436…02f1` (ignored; not committed).
- Generated inputs used, unchanged: `paper/generated/numbers.tex` sha256 `540d9732…829`, `T-incidents.tex` `4338db99…296`, `T-audits.tex` `b235319c…d2d`, `T-generators.tex` (TODO stub).
- Word counts (prose, comments excluded): abstract 174 + S5 sentence; motivating example 139; introduction about 1,220 words of source including LaTeX.

## Results

### Numbers used and their source

Every number in the S8a sections expands from `paper/generated/numbers.tex` or a generated table, or sits inside a `\TODO`:

| Claim | Macro / table |
|---|---|
| Aztec loss "about $2.1M" | `\usdM{\AztecLossUSD}` (R1-005 confirmed figure) |
| Slither: 167 reports on real V3, none on the fault | `\AztecSlitherReports` |
| Testbed unbacked credit: 1000 units | `\AztecTestbedUnbackedGap` |
| 50 incident records; 15 in P1–P5 | `\RoneCases`, `\RoneInClassCases` |
| 68 audits; 18 with a binding finding (26.5%); 34 binding findings; 17 High/Critical in 7 audits of 7 protocols; 38.2% need the circuit | `\RtwoAudits`, `\RtwoBindingAudits`, `\RtwoBindingAuditShare`, `\RtwoBindingFindings`, `\RtwoHighCriticalBinding`, `\RtwoHighCriticalBindingAudits`, `\RtwoHighCriticalBindingProtocols`, `\RtwoBindingNeedsCircuitShare` |
| Per-class incident and audit counts | `\input{../generated/T-incidents}`, `\input{../generated/T-audits}` |

The text uses the corrected count of 7 audits with High/Critical binding findings (`reports/PP/DISCREPANCIES.md`), not 16. No oracle E4 number and no DEV precision number appears in the S8a sections. Contract addresses do not appear.

### Placeholders and the lane that fills each

| Location | Placeholder | Filled by |
|---|---|---|
| `abstract.tex` | one sentence (≤ 26 words) on the held-out v3 result and S1 root cause | S5 (+ S1) |
| `intro.tex` contribution 4 | number of held-out families; headline numbers | S5 |
| `intro.tex` lesson 3 | held-out confirmed flaws in audited/deployed apps | S5 |
| `intro.tex` contribution 5 | generator canonicality result and template lineage | S1 |
| `taxonomy.tex` Table 3 | generator census (driven by `paper/generated/T-generators`, currently a TODO stub awaiting `reports/S1/generators.csv`) | S1 → PP (`make paper-tables`) |
| `intro.tex` contribution 6 | naming of Case A / Case B and disclosure status | S7 (advisor) |
| `intro.tex` contribution 3 | oracle results cited only after the XR-01/XR-02 fixes | F2, then XR re-review |
| `intro.tex` "This paper" | fail-closed claim confirmed after the XR-03/XR-04 fixes | F1 |
| `intro.tex`, `taxonomy.tex` §5.2 | largest single-protocol share of High/Critical binding findings (Singularity) | PP (new macro) |
| `intro.tex`, `taxonomy.tex` Table 2 caption | author review of R1/R2 labels, especially R1-005 Aztec P5 vs. P1 | R1b (author) |
| `threat.tex` System | contract revision 4: Circom/Groth16 scope and Noir/Honk generator survey | S0 (reviewer) |

The rest of the paper still carries 43 S&P-era `\MISSING{}` placeholders (abstract #1 and intro #21 are gone). Those belong to S8.

### Page budget (current US-letter build; A4 will shift slightly)

| Section | Target | Current estimate |
|---|---:|---:|
| Title + abstract | 0.4 | 0.4 |
| 1 Introduction | 1.25 | ≈ 1.35 |
| 2 Motivating example (with Fig. 1) | 0.35 | ≈ 0.35 |
| 3 Background (unchanged S&P text) | 0.5 | ≈ 0.6 |
| 4 Threat model and definitions | 0.9 | ≈ 1.0 |
| 5 Taxonomy (Tables 1–3) | 1.5 | ≈ 1.8 |
| **Framing subtotal** | **4.9** | **≈ 5.5** |
| Remaining for design, evaluation, findings, root causes, ethics, related work, limitations | 8.1 | ≈ 7.5 |

About 0.6 page can be saved without losing content. Candidate cuts:
- Move Table 2 (census by class) to an appendix and keep its two summary sentences.
- Fold the P1–P5 paragraphs into Table 1.
- Trim the "single-layer tools" paragraph of the introduction.

## Assumptions and limitations

- **Template.** The build still uses the S&P `IEEEtran conference,compsoc` US-letter setup. The switch to EuroS&P A4 belongs to S8.
- **Undisclosed findings.** The S8a sections refer to ZKredential and RacePass only as `\CaseA`/`\CaseB` and do not describe their mechanisms. The S&P-era sections that remain (`cases.tex`, `results.tex`, `ethics.tex`, `design.tex`, the ZKredential figure) still **name and describe them**, and they also describe zk_voting. The compiled PDF therefore still contains them. S7/S8 must anonymise or remove them before submission.
- **Case A/B E4.** These rest on the hand-run local reproductions in `reports/impact/REPORT.md`, not on the S4 oracle. Their policies are agent-drafted and provisional (human and advisor review MISSING).
- **"Checker must know" column.** This is the author-facing reading of AZ1 and the R2 labelling rules, cross-checked against the per-class "needs circuit" shares in T-audits. P1 and P3 are mostly decidable in the contract; P2 and P5 mostly need the circuit. The column is not an independent measurement.
- **Signature analogues.** These are explanatory. The P1(a) analogue ("accepting trailing unsigned bytes") and the P1(b) analogue ("a signed batch executed in part") are mine; neither has a citation.
- **One-sentence property.** The intro states "the same proof and public inputs, applied to the same state, must produce the same protected effects, and only as often as the policy permits". §4 presents it as intuition and gives the contract's authorization + coverage definitions as the formal property. It also notes the exceptions: policy-permitted variation (e.g. any-caller faucets) and coverage, which the sentence leaves implicit.
- **`main.pdf`.** The tracked `paper/zk/main.pdf` (S&P draft) was not rebuilt, because `AGENTS.md` forbids committing compiler output. It is now stale relative to the sources.

## Failed approaches / surprises

- No TeX engine was on `PATH`. I found a tectonic binary under `/usr/lib/chatgpt/resources/` and used it. It is not part of this project's pinned toolchain.
- The first figure render was too small to read, and resizing the two census sub-tables to `\textwidth` gave them mismatched font sizes. I fixed both: wider cells in the figure, and one `\footnotesize` with no resizing for the tables.
- I first wrote that P4 needs "neither circuit nor consumer". T-audits shows 55% of P4 audit findings needing the circuit, because R2 counts in-circuit recursive verifiers as P4. I corrected the text and the table.

## Disagreements between sources (reported, not resolved)

1. **Research contract §1 vs. the paper scope.** Contract revision 3 names a Noir/ACIR producer, while the paper is Circom/Groth16 with a Noir/Honk generator survey. Revision 4 (S0) has not been written. I marked this `\TODO{S0}` in §4.
2. **Aztec Connect class.** R1's CSV (and therefore the generated T-incidents) records R1-005 as P5, with P1 as the alternative. The S8a prompt and DECISIONS treat it as P1 extent (b). The taxonomy text classifies it as P1(b). The generated table keeps the CSV class, with a caption note pending R1b. If R1b relabels it, `make paper-tables` will move it to P1, and the §5.2 sentence "every exploited in-class case falls in P4, except Aztec Connect" stays true.
3. **Contract §5.4 vs. P4.** The contract puts trusted-setup failures out of scope, yet P4 includes γ = δ. §4 keeps the S&P draft's resolution: P4 is reported as a verifier-configuration class and a root cause, never as evidence for joint analysis.

## Open questions for the author

1. Title: is option 1 acceptable, or option 2 if you want the lens up front?
2. Should the paper name Aztec Connect, a public incident with a public post-mortem, in the abstract? The current abstract says only "a zk-rollup contract".
3. R1b: confirm P1(b) for Aztec Connect so that Table 2 and the text agree.
4. The abstract says BindCheck "fails closed, and checks candidates by replaying real proofs". Keep this only if F1 and F2 land; otherwise change it to "is designed to".
5. Page budget: approve moving Table 2 to an appendix if space is short.
6. Case A/B: should the intro mention them at all before S7 decides, or should the contribution bullet be dropped until disclosure?

## Held-out hygiene statement

I read only tracked reports, CSVs and paper sources in this repository. I did not open, clone or analyze any third-party repository, so `scripts/check_holdout.py` was not needed. No EVAL family was opened. No transaction, RPC call, maintainer contact or disclosure took place. The only network activity was tectonic downloading TeX bundle files.

## Recommended next task

**S8b — anonymise and integrate.** Replace every remaining name and mechanism description of ZKredential, RacePass and zk_voting in `cases.tex`, `results.tex`, `design.tex`, `ethics.tex` and the ZKredential figure with `\CaseA`/`\CaseB`/`\CaseC` stubs gated on S7. Switch `main.tex` to the EuroS&P A4 template.

Completion criterion: `pdftotext main.pdf - | grep -ciE 'zkredential|racepass|zk_voting|propertyfy|eventpass'` returns 0; the build exits 0 with no overfull boxes; and the page count of the body is reported.
