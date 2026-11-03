# IEEE S&P 2027 Cycle 2 readiness checklist

**Audit date:** 2 November 2026

**Current disposition:** **NOT SUBMISSION READY**

**Research status:** Gate A `INCONCLUSIVE`; research verdict `UNKNOWN`

This checklist records official venue requirements and project prerequisites.
It is not a submission plan, acceptance prediction, or authorization to
register a paper. The authoritative venue source is the
[IEEE S&P 2027 Call for Papers](https://sp2027.ieee-security.org/cfpapers.html).

## Deadline and registration lock

| Requirement | Official rule | Current state | Required action |
|---|---|---|---|
| Abstract registration | 10 November 2026, 23:59:59 AoE (UTC-12) | Not ready | Do not register until authors approve an accurate full abstract and stable contribution scope. |
| Paper submission | 17 November 2026, 23:59:59 AoE | Not ready | Final PDF, artifact link if used, disclosures, and metadata are absent. |
| Complete registration metadata | Full and complete abstract, complete author list with ORCIDs, and conflicts declared | Human-owned and incomplete | Authors must supply and verify names, ORCIDs, HotCRP email consistency, and COIs. |
| Locked fields | Title, abstract, and author list cannot change after abstract registration | Scope remains unresolved | Do not lock a final-results abstract while the central capability claim is unsupported. |
| Early upload | Authors are responsible for having a draft uploaded 24 hours before the deadline | No submission PDF exists | If submission later becomes authorized, schedule upload before the last 24-hour window. |

The current status draft deliberately says `UNKNOWN`, `INCONCLUSIVE`, and
not submission-ready. Registering it as a successful capability paper would
contradict the evidence ledger.

## Format and page budget

| Requirement | Official rule | Current state | Required action |
|---|---|---|---|
| Main text | Up to 13 pages of text | Unverified | The new Markdown status draft is not a formatted submission. Compile only after contribution scope and human review are stable. |
| References and appendices | Up to 5 pages; total at most 18; material after page 13 clearly marked appendix | Unverified | Keep central qualifications and Gate A outcome in the main text because reviewers need not read appendices. |
| Paper size | US letter, not A4 | No LaTeX package exists | Set only in a later authorized submission source. |
| Template | IEEEtran.cls 1.8b with `\documentclass[conference,compsoc]{IEEEtran}` | No LaTeX package exists | Do not claim format compliance until a rendered PDF is checked against the official template. |
| Space manipulation | No margin/font/line-spacing changes or egregious space scrunching | Not applicable yet | Preserve official formatting when a LaTeX version is authorized. |

Provisional 13-page allocation for a future reviewed version:

- 1.25 pages: abstract, problem, and explicit status;
- 1.5 pages: model, threat boundary, and evidence semantics;
- 2 pages: bounded current interface and mechanical prototypes;
- 3.5 pages: versioned evidence, negative results, and Gate A;
- 1.5 pages: closest related work and exact overlap;
- 1.5 pages: limitations, ethics, AI use, and artifact boundary;
- 0.5 page: conclusion; and
- 1.25 pages: figures, tables, and layout contingency.

The taxonomy should not receive a standalone contribution section because the
D2 human study has not started.

## Anonymous review and artifacts

| Requirement | Official rule | Current state | Required action |
|---|---|---|---|
| Paper anonymity | No author names, affiliations, identifying acknowledgments, or self-identifying first-person prior-work citations | Not audited | Run a human anonymity review over the final PDF and metadata. |
| Artifact anonymity | Repository/account names and artifact text must not identify authors or institutions | Current repository is not an anonymous artifact | Create a separately reviewed anonymous artifact only after release scope is decided. |
| Artifact freeze | An artifact repository supplied with the paper must not be updated after the paper deadline | No submission artifact exists | Freeze exact public bytes and preserve a manifest before linking an artifact. |
| Artifact encouragement | Paper artifact repositories are strongly encouraged | Not ready | Decide what can be released; do not expose private or reserved evidence. |
| Post-acceptance AE | Optional evaluation for availability, functionality, and reproduction; permanent public hosting required for an availability badge | Not applicable before acceptance | See the [official artifact call](https://sp2027.ieee-security.org/cfartifacts.html) only after release and paper decisions. |

Internal report paths, raw local paths, task identifiers, and developer
account names must not appear in a future anonymous submission. The claim map
is an internal traceability artifact, not reader-facing prose.

## Ethics, vulnerability disclosure, and competing interests

| Requirement | Official rule | Current state | Required action |
|---|---|---|---|
| HotCRP ethics field | Mandatory for every paper; “None” requires a short rationale | Not completed | Authors must write and approve the field. Current D2 used exposed local/synthetic material, no live third-party testing, and no maintainer contact. |
| Vulnerability disclosure | Submission must explain completed disclosure or the plan for any identified vulnerabilities; full CVE identifiers should not appear in an anonymous submission | No new D2 vulnerability claim | Reassess if later work produces a credible candidate. Do not contact maintainers without explicit authorization. |
| Live systems | Testing systems not owned by the authors requires a detailed harm/permission analysis | No such D2 testing occurred | Preserve owned-local scope unless separately authorized. |
| New tools/attacks | Discuss possible misuse, mitigation, and benefit/harm balance | Draft treatment incomplete | Human authors must decide release boundaries for proof/witness and validation tooling. |
| Human subjects | Disclose institutional review status where applicable | Taxonomy human study has not started | Do not imply IRB/ethics determination; authors must decide before any study. |
| Competing interests | Relevant financial and non-financial interests must be disclosed in the camera-ready paper | Not supplied | Human authors must provide and verify. |

## Generative-AI disclosure

The CFP permits generative-AI use but requires disclosure and motivation in
the HotCRP “Generative AI usage considerations” field. It makes authors
responsible for accuracy, originality, literature review, and all text and
figures. If AI was used editorially, the CFP supplies this statement:

> Generative AI was used for editorial purposes in this manuscript, and all
> outputs were inspected by the authors to ensure accuracy and originality.

That sentence must not be used until the inspection actually occurs. Current
project records show substantial AI-agent involvement in code, protocols,
reports, source screening, and manuscript drafting. A truthful disclosure must
therefore cover both editorial and methodological use, including:

- which work products were AI-assisted;
- model/service and reproducibility limits that can be disclosed;
- how generated ideas, code, citations, and claims were independently checked;
- limitations caused by agent generation and unavailable model internals;
- why AI use was needed;
- how query volume and model size were bounded where known; and
- the hardware/environment information and environmental rationale available
  from retained records.

The CFP says AI cannot be an author. No AI agent may be counted as a human
policy author, reviewer, scorer, adjudicator, annotator, or coauthor.

## Scientific readiness gates

- [x] Historical and current version counts are separated.
- [x] Gate A is reported as `INCONCLUSIVE` with zero score rows.
- [x] Construction/smoke and mechanical evidence are not scored.
- [x] Corrected Step 10 run-02 is bound; superseded run-01 is preserved.
- [x] ELSA is limited to its official abstract and DOI, with the access gap visible.
- [x] Public audits record Steps 11–14 not executed and Gate B not evaluated.
- [x] Public audits record Steps 15–17 not executed and Gate C not reached.
- [ ] A fair scored comparative result exists.
- [ ] A reviewed human policy author/adopter and distinct reviewer exist.
- [ ] A derived relational producer guarantee and exact effect-reliance relation exist on actual supported semantics.
- [ ] A supported independent/reserved evaluation exists.
- [ ] Independent human triage and adjudication exist.
- [ ] Gate B and Gate C have passed under frozen protocols.
- [ ] Every central claim, citation, code path, table, and disclosure has substantive human coauthor review.
- [ ] A final anonymized artifact and rendered IEEEtran PDF have been independently checked.

Until the unchecked scientific and human-review prerequisites are resolved or
the contribution is explicitly narrowed to a venue-appropriate negative/status
paper, the project remains **NOT SUBMISSION READY**.
