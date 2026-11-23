# Source coverage statement

One row per source. It states how completely each source was swept, so the funnel is not read as more complete than it is. Date: 2026-11-23.

| Source | Coverage | How enumerated | Gaps |
|---|---|---|---|
| Zellic | Complete | GitHub publications repo, pinned commit; full-text scan | — |
| Trail of Bits | Complete | GitHub publications repo; full-text scan | — |
| Veridise | Complete | Website archive (167 pages; slow retry after a 429) | — |
| OpenZeppelin | Complete | Website audit index (419) | — |
| Consensys Diligence | Complete | In-browser (Cloudflare); sitemap, 148 audits | Page text saved only as quoted excerpts |
| zkSecurity | Complete | reports.zksecurity.xyz (68) | — |
| PSE | Complete as distributed | No central index. Audits found in 139 org/incubated repositories and on pse.dev (3 found) | A distributed source can miss items |
| Spearbit / Cantina portfolio | Mostly | GitHub portfolio (795 rows) | 61 Cantina pages without a PDF marked UNREADABLE |
| Nethermind, ChainSecurity, OtterSec, Hexens, Sigma Prime, Least Authority, Zokyo, ABDK | Complete | Public indexes or repositories. ABDK re-scanned with `pdftohtml` because of garbled `pdftotext` output | — |
| Halborn | Complete | GitHub repository and website index; 9 duplicate rows marked `dup-of` | Website/repo overlap detected through commit IDs only |
| Quantstamp | Complete for PDFs; metadata for web reports | Public API (402). 236 client-rendered reports screened by API metadata only; 18 flagged ones read from the JS-embedded report text | Metadata-only screening for 236 |
| Cyfrin | Screen 1 only | GitHub repository holds summary-only PDFs (the full reports are retained by clients, and no full-text revision exists in history) | Findings of 6 IN reports not public |
| Runtime Verification, MixBytes, Kudelski, Dedaub, Ackee | Complete | Public indexes or repositories | — |
| Hacken | Complete at screen 1 | In-browser fetch of all 1,414 sitemap report pages and keyword scan; 44 itemized, 1,370 OUT with no ZK hit | Finding bodies behind "Details" links were not captured |
| Code4rena | Complete | Sitemap (412) | — |
| Sherlock | Mostly | Public API (301) | 64 UNREADABLE (empty API text; judging repositories missing). ZKP2P V2 and Covalent LC findings not public |
| Cantina competitions | Screen 1 only | Sitemap (116) | Findings not public for the 5 IN competitions |
| 0xPARC zk-bug-tracker, zkbugs | Complete | Pinned repositories; every config row logged | — |
| GitHub Security Advisories | Complete for the fixed terms | 16 terms on reviewed and unreviewed advisories, slow pass | Term-based search only |
| **CertiK** | **Not covered** | Skynet search matches project names only, not audit text. There is no public enumerable audit list and no report repository on GitHub. The 16 terms were run (see `certik/queries.csv`); ZK-named hits show "CertiK Audit: No" | Whole source |
| **Solodit** | **Not covered** | Site on a maintenance page during the sweep (retried) | Aggregator mostly mirrors the firms above |
| **yAcademy** | **Not covered except 1 report** | Site down (connection timeout). The one known report (in the zk-email repository) was screened | Whole source |
| **Oxorio** | **Not covered** | No public index (JS-rendered; GitHub repository 404) | Whole source |

**Independent check.** Recall against the R2 census, compiled separately and hidden from the sweep agents, is 49/50 in-scope findings (`RECALL-R2.md`).
