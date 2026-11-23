# browser agent notes (PARTIAL)

## Totals
| Source | Enumerated | IN | KEEP | BORDERLINE | Status |
|---|---|---|---|---|---|
| Consensys Diligence | 148 (sitemap.xml + index) | 9 | 2 | 5 (after v1.2 re-check) | complete |
| Solodit | 16 queries | - | - | - | site on maintenance page twice; all 16 logged UNAVAILABLE |
| Sherlock 805, 618 | 2 | 0 (UNREADABLE) | 0 | 0 | private, no report visible |
| Cantina x5 | 5 | 5 | 0 | 0 | findings not public |
| Hacken | 1414 report pages in sitemap-audits.xml (2365 URLs incl. company pages) | 3 | 0 | 1 | all 1414 fetched, 44 keyword-hit pages itemized |
| CertiK | not run | | | | PARTIAL |
| Quantstamp (18 reports) | not read | | | | PARTIAL |

reports.csv has 199 rows, findings.csv 18 rows (2 KEEP, 6 BORDERLINE, 10 DROP).

## Findings of note
- KEEP: Linea contracts-update 5.1 (finalBlockNumber not in public input) and 5.4 (chainId not in public input). Audit repo commits 404 (PRIVATE-OR-MISSING).
- BORDERLINE: Linea message-service 4.4 (front-running finalizeBlocks, reward only hypothetical); Linea forced-transactions 4.4; Linea PLONK verifier 4.4, 4.5, 4.10 (verifier soundness, no consumer effect); Hacken Zilliqa ownership proof (unconstrained newAddr/domain, title only).
- Hacken: only 3 IN (DOP SmartLogic, Railgun, Zilliqa); DOP and Railgun have no proof-related findings. Hacken audits are mostly non-ZK.

## Deviations and limitations
- Hacken scan: the orchestrator's wrap-up message assumed ~798 pages; the scan had actually reached all 1414 by the time I screened (3 errors). Only the 44 pages with keyword hits (word-boundary regex over zk/snark/plonk/verifier etc.) have rows. The remaining ~1370 reports have no row, so the funnel count for Hacken must use "1414 enumerated, 44 itemized, 1370 no ZK keyword hit".  A first scan on the MacBook (~210 pages) was lost when the extension dropped; it was rerun from zero on POLLDELL.
- Hacken page text, Zilliqa quote: description bodies are behind "Details" links and were not captured; the Zilliqa quote is the finding title verbatim.
- Consensys page texts were not saved to disk (curl 403 Cloudflare). report_sha256 is the hash of a saved excerpt file containing the quoted passages; the in-browser full-text sha256 is in the notes column. Quotes were copied from get_page_text output into the excerpt files and checked ≤40 words.
- Consensys titles in reports.csv are slug-derived, not the page titles. report dates are YYYY-MM from the URL.
- Aligned Layer (Consensys 2024-08): screened IN under the orchestrator's assignment; v1.3 attested-verification clause now supports IN. Its findings were logged DROP (access control).
- Verifier-soundness rule v1.1: four Linea PLONK rows were downgraded from BORDERLINE to DROP after v1.2 (4.2, 4.3, 4.8, 4.9). The BORDERLINE verifier rows carry reason_code NO-EFFECT-DESCRIBED rather than BINDING; reason_code on those could be revisited.
- Browser rules: read-only, no logins, no forms except none used; a parallel-fetch speed-up was refused by the permission classifier and not pursued. Held-out guard was run alone before every repo request (Consensys/linea-*, LFDT-Lineth/lineth-monorepo, Zilliqa/zkp_recovery_app: all ALLOWED). Commit checks via github.com web URL with curl.
- Linea monorepo was renamed (Consensys/linea-monorepo -> LFDT-Lineth/lineth-monorepo); 8ccf2473, 4ddbeba8 and 70dde763 return 200 after redirect.
- No tabs left open beyond the two session tabs (MacBook tab group lost; POLLDELL tab 500925921 still open on hacken.io).

## Time
Roughly 6 hours of wall-clock across two browsers, most of it waiting on throttled background scans and the unreachable extension.
