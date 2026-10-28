# D1P-D01 retrieved sources

Hashes and provenance for every primary text used in [draft.md](draft.md).
The bytes live only in the ignored folder `results/raw/D1P-D01/` (manifest:
`results/raw/D1P-D01/manifest.json`). PDFs and full texts are never
committed. All retrievals happened on **26 October 2026**.

## Retrieved

| Draft ref | Work | URL | Local file | SHA-256 |
| --- | --- | --- | --- | --- |
| [1] | SNARK SoK (arXiv version of USENIX Security 2024) | <https://arxiv.org/pdf/2402.15293> | `papers/sok.pdf` | `32652ce1debd0dfb4abb694dafc926d69f7498364ac99b0384060fac9dc2fac7` |
| [4] | Coda, author-hosted copy (IEEE S&P 2024) | <https://www.cs.utexas.edu/~isil/coda.pdf> | `papers/coda.pdf` | `6fbbb71243feba46c2d3bb5f1e8551ba4beef7e534dfb40109b1fec0d4212f2c` |
| [6] | SmartAxe, arXiv v1 (FSE 2024) | <https://arxiv.org/pdf/2406.15999> | `papers/smartaxe.pdf` | `9d08ae1ffffea775de2b6d58f1c9a438b2ed92081c8a7058329103ee284b1020` |
| [8] | IEEE S&P 2027 call for papers | <https://sp2027.ieee-security.org/cfpapers.html> | `cfp/sp2027-cfpapers.html` | `33d271f690f352819006ac375cbab8748223c0dd0b18e42a26981fa139fba0ef` |

## Derived plain text

| File | Derived from | Tool | SHA-256 |
| --- | --- | --- | --- |
| `papers/sok.txt` | `papers/sok.pdf` | `pdftotext -layout` (poppler 25.10.0) | `4f4ff7fbb91bd1808580f2c338fb35ae929f80f058719242569ae1e5d20792c4` |
| `papers/coda.txt` | `papers/coda.pdf` | same | `741e1aab91782e3e3a1f6c5df73fdce51f8ffb3273e5966d36aa88d5d7e7cc29` |
| `papers/smartaxe.txt` | `papers/smartaxe.pdf` | same | `5295b387b2c0812b5ae346c9105d41cc58a640f0f70d626c6ff0a979b165c42c` |
| `cfp/sp2027-cfpapers.txt` | `cfp/sp2027-cfpapers.html` | Python tag strip + `html.unescape` | `f31a61424763828cea1dfecf677e26388f438eb84cada1bbfdc011ff89bd7f36` |

## Not retrieved (comparisons remain [TODO-VERIFY])

| Draft ref | Work | Attempt and result |
| --- | --- | --- |
| [3] | CIVER (IEEE S&P 2024) | Web search found no open full text. Only the abstract, the SoK's description and the tool README were used. A human author will supply the full text. |
| [5] | CCC-Check (IEEE S&P 2026) | `https://eprint.iacr.org/2025/2120.pdf` returned HTTP 403 (curl and WebFetch). Abstract only, from the ePrint landing page. A human author will supply the full text. |
| [4] alt. | Coda arXiv/ePrint copies | `https://eprint.iacr.org/2023/547.pdf` returned HTTP 403; `https://arxiv.org/pdf/2304.07648` returned HTTP 404. The author-hosted copy above was used instead. |

## D1P-P01 additions (28 October 2026)

The full-prose rewrite of [draft.md](draft.md) adds references [9]–[13] for
the preregistered baseline tools in [baselines.md](baselines.md). **None was
retrieved**; bibliographic details come from author knowledge and the tool
pins in baselines.md, and stay **[TODO-VERIFY]** until a human author checks
them against the primary source.

| Draft ref | Work | Status |
| --- | --- | --- |
| [9] | Picus / QED², PLDI 2023 | Not retrieved; authors, venue and title to verify |
| [10] | Slither, WETSEB 2019 | Not retrieved; to verify |
| [11] | Mythril v0.24.8 repository | Citation form to verify |
| [12] | Echidna, ISSTA 2020 tool demo | Not retrieved; to verify |
| [13] | Foundry v1.8.6 repository | Citation form to verify |

Former ref [7] (the internal D1 reference proposal) has been removed from the
reference list because it is not a citable primary source.

## D1P-P02 verification (28 October 2026)

References [9]–[13] were checked against primary registries, and [14] was
added. Bibliographic metadata came from DOI content negotiation
(`curl -L -H "Accept: application/vnd.citationstyles.csl+json"
https://doi.org/<doi>`), which returns the publisher's Crossref record.
Software releases came from the GitHub REST API (`gh api
repos/<owner>/<repo>/releases/tags/<tag>`). Tool behavior claims came from
the repository READMEs (WebFetch). dblp returned HTTP 429 and an Anubis
block, so it was not used. The ACM DL returned HTTP 403.

| Draft ref | Work | Source checked | Result |
| --- | --- | --- | --- |
| [9] | Picus, PLDI 2023 | doi.org → 10.1145/3591282; github.com/Veridise/Picus README | Verified: 10 authors (Pailoor … Dillig), PACMPL 7(PLDI), pp. 1510–1532, 2023. README: uniqueness property, inputs `.circom`/`.r1cs`/`.sr1cs`. Full text not read. Whether its property covers unread public inputs stays **[TODO-VERIFY]** |
| [10] | Slither, WETSEB 2019 | doi.org → 10.1109/WETSEB.2019.00008 | Verified: Feist, Grieco, Groce; pp. 8–15; May 2019 |
| [11] | Mythril v0.24.8 | GitHub API | Verified: tag v0.24.8 published 2024-03-27; repository now `ConsenSysDiligence/mythril`. Cited as software; no canonical paper found |
| [12] | Echidna, ISSTA 2020 | doi.org → 10.1145/3395363.3404366 | Verified: Grieco, Song, Cygan, Feist, Groce; pp. 557–560 |
| [13] | Foundry v1.8.6 | GitHub API | Verified: tag v1.8.6 published 2026-10-21. Cited as software |
| [14] | Circomspect | GitHub API | Verified: `trailofbits/circomspect`, "A static analyzer and linter for the Circom zero-knowledge DSL". Version not pinned; tool not run |
| [3] | CIVER README | github.com/costa-group/circom_civer | Verified: weak safety, tags, pre/postconditions; Circom only; R1CS/PLONK/ACIR listed as forthcoming. Full text still not retrieved |
| [5] | CCC-Check README | github.com/ArmanKolozyan/CCC-Check | Verified: analysis via CirC IR; Circom end-to-end script; README cites IEEE S&P 2026. ePrint PDF again returned HTTP 403 (curl with a browser user agent). Full text still not retrieved |

The Noir-compiler claim in the related-work section is now a measured
result (D1P-22), not a citation.
