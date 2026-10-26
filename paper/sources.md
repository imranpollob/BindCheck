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
