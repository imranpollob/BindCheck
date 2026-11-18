# S8 — EuroS&P paper integration

Status: PARTIAL

Outcome: The revised manuscript builds on A4. Comparison with the venue-supplied template is open.

## What was written

- The design and methodology sections describe the circuit, generated verifier and consumer at the F1 candidate revision. They cover P1–P5, the supported prefix/neutral-tail extent rule, verifier correspondence, guarded dynamic vectors and the evidence needed for a local oracle confirmation. The oracle section distinguishes a successful preflight from acceptance on the changed path, token logs from state, and benefit delivery from discharge of required obligations. [F1](../F1/REPORT.md), [S2c](../S2c/REPORT.md), [F2](../F2/REPORT.md), [oracle contract](../../oracle/README.md)
- Taxonomy now includes a generator survey. Its compact table reads the behaviour column of the generated TeX during compilation. The text identifies the inspected interfaces and explains where the survey ends. The introduction and background use the same distinctions. [S1 evidence](../S1/REPORT.md), [generated table](../../paper/generated/T-generators.tex)
- Related work compares the circuit property checked by ZKAP, Circomspect and Picus with the contract question each leaves open. Railgun and Anon Aadhaar supply published audit examples. The comparison makes no performance claim for ZKAP. The ELSA bibliography entry uses the authors and full title published by the authors' group. [Comparison inventory](../../RELATED-WORK.md), [R2](../R2/REPORT.md), [ELSA authors](https://versys.ios.ac.cn/blog/ISSTA26/)
- Cases and ethics use Case A and Case B. The old case diagram and identifying case descriptions are outside the compiled manuscript. Historical manual validation is identified separately from oracle evaluation. Results distinguish the legacy funnel from v3. Previously recorded evaluation data and outstanding markers in untouched sections remain at their original scope.
- Changes are in `paper/zk/main.tex`, `refs.bib`, `STATUS.md`, `figures/generator-survey.tex` and the abstract, introduction, background, threat, taxonomy, design, methodology, results, cases, discussion, related-work and ethics section files. The project checkpoint links to this handoff. The parent commit preserves the previous sources.

## Template and page budget

The venue requires its own LaTeX package, A4 and a maximum of 13 body pages. The shell could not resolve the venue host (curl exit 6). The web reader reached the official ZIP but cannot extract ZIP content. The local build uses IEEEtran conference/compsoc with the A4 class option. Its verified page size is 595.28 × 841.89 PDF points. This verifies paper size and pagination. Equivalence to the official class and preamble is outstanding. [Venue formatting rules](https://eurosp2027.ieee-security.org/cfp.html), [official archive](https://eurosp2027.ieee-security.org/eurosp2027-template.zip)

| Build | Paper | Last body page | First reference page | Total pages |
|---|---|---:|---:|---:|
| Starting branch sources | US letter | 14 | 14 | 15 |
| S8 manuscript | A4 | 12 | 12 | 12 |

The following locations come from the final PDF text boxes and auxiliary file. Spans include floats; sections share boundary pages. L and R denote the first and second columns.

| Material | Starts | Page span |
|---|---|---|
| Title and abstract | 1, top | 1 |
| Introduction | 1 L | 1–2 |
| Motivating example | 2 L | 2 |
| Background | 2 R | 2–3 |
| Threat model and definitions | 3 L | 3 |
| Taxonomy and generator survey | 3 R | 3–5, census float on 6 |
| Benchmark design | 5 L | 5–6 |
| Analyzer and execution oracle | 6 R | 6–8 |
| Evaluation methodology | 8 L | 8 |
| Results | 8 R | 8–10, runtime float on 11 |
| Development cases | 10 R | 10 |
| Discussion and limitations | 10 R | 10–11 |
| Related work | 11 L | 11 |
| Ethics, disclosure, AI use and open science | 11 R | 11–12 |
| References and appendices A/B | 12 L / 12 R | 12 |

## Results and open evidence

The generated survey contains **25 data rows**. Its six behaviour strings comprise 17 reject, four source-read split, one native reduce, one older native Keccak rejection whose mechanism is unresolved, one split package-marker row and one reject package-marker row. Some rows cover multiple configurations. The manuscript reports the source-read gnark entries as unexecuted. The four generated split templates rejected the changed encodings with the original proof. Acceptance under a different proof remains unconfirmed. The known reduction result is native bb.js only.

| Remaining marker | Occurrences | Owner and location |
|---|---:|---|
| `\TODO{S5}` | 4 | Held-out headline in abstract and introduction, v3 funnel in results, transfer in discussion |
| `\TODO{XR2/S5}` | 2 | Oracle evaluation in methodology and results |
| `\TODO{S7}` | 3 | Case naming, disclosure and harms in introduction, cases and ethics |
| `\TODO{S0}` | 1 | Threat-model scope under the proposed contract revision |
| `\TODO{R1b}` | 2 | Author review of census labels in introduction and census caption, including the Aztec P1/P5 difference |
| `\TODO{PP}` | 2 | Largest single-protocol share of High/Critical binding findings in introduction and taxonomy |

## Evidence and reproduction

Base commit `aac072f1bdfd4845d0912c9548ebaa5f9d6f5f21`. Analyzer content SHA-256 `753c6e2a0f3f75255eb2fdc354402f3ef7aac1541206b0794a9d09cd7d485315`. The prompt calls this the frozen candidate. The controlling F1 report and decision log record a candidate pending XR2 and a new freeze declaration. Historical tables retain their original analyzer revision. Contract revision 3 remains authoritative. [Decision log](../../docs/orchestration/DECISIONS.md), [research contract](../../docs/research-contract.md)

Tools were Tectonic 0.17.0 (SHA-256 `a98aa59ad5c1df39a6c9e56cbfc5088f2b11d6c179c0130b97998e4bd46a46da`), Poppler 24.02.0, Python 3.12.12 and Git 2.43.0. Both builds used the same locally cached TeX bundle. The output directory in the compile command was `before` at the base revision and `after` for the final sources.

```sh
export BC=/home/pollmix/Coding/bc
cd "$BC/wt-S8"
mkdir -p results/raw/S8/{before,after,cache,render}
cp -r ~/.cache/tectonic results/raw/S8/cache/
cd paper/zk
XDG_CACHE_HOME="$PWD/../../results/raw/S8/cache" /usr/lib/chatgpt/resources/tectonic/tectonic -X compile --only-cached --keep-logs --keep-intermediates --outdir ../../results/raw/S8/after main.tex
cd ../..
pdfinfo results/raw/S8/after/main.pdf
pdftotext -layout results/raw/S8/after/main.pdf results/raw/S8/after/main.txt
pdftotext -bbox-layout results/raw/S8/after/main.pdf results/raw/S8/after/bbox.xhtml
pdftoppm -scale-to 780 -png results/raw/S8/after/main.pdf results/raw/S8/render/page
python3 -B scripts/paper/check.py
python3 -m bindcheck_zk.freeze
python3 results/raw/S8/verify.py
git diff --check
```

Both builds and final checks exited 0. The generated-file check matched all 22 outputs. The final build had zero overfull boxes, LaTeX warnings, missing glyphs or BibTeX warnings. Underfull box messages remain. The rendered text scan found zero undisclosed names from the S8a check and zero literal contract addresses. All pages were rendered for visual review. The checks cover paper sources and generated inputs; no analyzer or oracle experiment was rerun.

| SHA-256 | Artifact |
|---|---|
| `ce948277669c626e508ab7696932e3ac87133fc39caa4bb2df6b082d81dd0e70` | `results/raw/S8/before/main.pdf` |
| `06d96cfde5632272f35cc4d353a8e3bb9110f73a03e9cf53641651221ef2cbbc` | `results/raw/S8/after/main.pdf` |
| `b69c16820caadc031280fa25b814bcd8b1261a9f52e30a33859ba8daf1843e6a` | `paper/generated/T-generators.tex` |
| `6d5720f13b60801abde0dc3be4654c3f06aae99c9fbe61d2b8572c87bd860a34` | `reports/S1/generators.csv` |

Raw logs, PDF text, page images, the before-edit checkpoint, and verification script are under ignored `results/raw/S8/`. The tracked legacy PDF is stale and contains historical case details. Use the ignored A4 build for this review.

## Failed approaches and limitations

The old full generator table produced a 2,252.65-point overflow. The first A4 render exposed blank row counts because the TeX delimiter matched an alignment token rather than literal text. The corrected reader splits textual columns, and the final check compares the printed numbers with an independent count. Two other tables were resized to fit A4. A local staging attempt exited 128 because the linked worktree's shared Git index directory is read-only.

AI disclosure: OpenAI Codex, GPT-6 family, drafted and edited these sections, the table, bibliography correction and handoff, and ran the build and layout checks. Human authors have yet to review this lane's prose, interpretations and labels.

## Held-out hygiene

Inputs were tracked paper sources, lane reports, local generated evidence and publication metadata. No third-party case source or unused EVAL family was opened. There were no blockchain calls, maintainer contacts or disclosures.

## Recommended next task

Compare the class, options, preamble and bibliography style with the official EuroS&P 2027 archive. Record the archive SHA-256, apply any differences, rebuild, and verify A4, a body ending on or before page 13, and zero overfull boxes.
