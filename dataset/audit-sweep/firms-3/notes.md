# firms-3 notes (protocol v1.1, v1.2 applied from mid-run)

Run date: 2026-11-22. Agent: firms-3. No subagents. Downloads in /tmp/claude-1000/audit-sweep/firms-3/.

## Totals (enumerated / IN / KEEP / BORDERLINE)

| Firm | Enumerated | IN | KEEP | BORDERLINE | Notes |
|---|---|---|---|---|---|
| Cyfrin | 232 | 6 | 0 | 0 | Repo holds abbreviated summaries only (no finding text). IN = Linea x4, Aztec x2. |
| Halborn (GitHub repo PublicReports) | 282 | 5 | 0 | 0 | IN = MatterLabs Verifier (x2 copies in two folders), zkSync Era Circuits, Sacred Finance, Portal Gate. 3 DROP rows. |
| Halborn (website halborn.com/audits, 278 audits) | 278 | 2 | 0 | 0 | IN = Rarimo passport ZK circuits (1 DROP row) and a website copy of the zkSync Era Circuits report (duplicate of a repo row). Soqucoin LatticeFold+ batch-verifier report (binding-shaped, UTXO chain) = NON-EVM. Overlap with the repo set was not computed; rows are per source. |
| Runtime Verification | 110 | 0 | 0 | 0 | zkVM folder = NON-EVM or not-a-security-audit. |
| MixBytes | 261 | 0 | 0 | 0 | 255 PDFs + 6 pre-2019 markdown reports (title-screened). |
| Ackee Blockchain | 97 | 1 | 0 | 0 | IN = ZK Email email-recovery (changed from OUT after advisor review; consumer-contracts side, verifier out of scope); 2 DROP rows (M5, H1). |
| Kudelski Security | 37 | 0 | 0 | 0 | 36 PDFs + Concordium entry (no PDF). |
| Dedaub | 60 | 0 | 0 | 0 | Public index lists 19 projects / 60 reports. |
| Quantstamp | 402 | 0 | 0 | 0 | 147 PDFs full-text scanned; 254 HTML reports not readable by curl (see below); 1 PDF 302. |
| Hacken | - | - | - | - | BLOCKED (Cloudflare challenge). |
| CertiK | - | - | - | - | BLOCKED/NO-INDEX (skynet captcha; www.certik.com has no public list). Keyword search not run. |

Total rows in reports.csv: 1759 (14 IN). findings.csv: 6 rows (all DROP: Halborn zkSync circuits HAL-01/02/04, Ackee ZK Email M5/H1, Rarimo HAL-01). There are no KEEP or BORDERLINE rows from this lane, so no artifact checks were needed (no repo requests beyond the report repos themselves).

## Items for the orchestrator

1. **Quantstamp HTML reports (254)**: client-rendered React SPA; report text is not in static assets. Screened by API metadata only (title+tags); 18 flagged ones are in `browser_queue.csv` (Hinkal x2 tagged Circom, Datachain LCP zk-dcap, Powerloom L2, Boba x2, Pheasant, Zircuit-tagged, light-client-tagged). The flag regex is deliberately broad (matches "Deployed on Zircuit" etc.). (An earlier hc message of mine said 246 remaining; that was wrong. The split is 18 queued and 236 OUT by metadata.) 1 PDF (cryptex-2) returned 302 and was not retrieved (UNREADABLE).
2. **Cyfrin**: git history (blobless clone, 18 commits) starts at bc9d7ca (2026-10-30) which already contains the abbreviated summaries, so no full-text revision exists in the repo. The 6 IN rows cannot be screen-2'd from this source. Each summary PDF says the complete report was delivered to the client, who retains it as the full record (quote: "was delivered to Consensys / Linea, who retain it as the full record of the engagement"). So full findings are client-only; no public location is named.
3. **Halborn MatterLabs Verifier (2023-07)**: 0 findings, but its manual-testing table lists as "Pass" that the verifier returns true for public input with dirty bits over the Fr mask, for EC points over modulo, and for Fr over modulo. That is non-canonical-input acceptance that the auditor did not report as a finding; candidate P3/P4 aliasing for rescreen. I did not log it as a finding row (no finding_id).
4. **Ackee ZK Email email-recovery (2024-08)**: marked IN under §3 (system with an EVM consumer of email-auth proofs; audited side = consumer contracts). The report text never discusses proof verification (verifier/EmailAuth is out of scope), so M5 and H1 were logged DROP (proof acceptance not described; value-not-fixed criterion fails: configuration logic). M3 (selector collisions) was not logged.
4b. **Halborn website vs repo**: the GitHub repo (282 PDFs, mostly 2021-2023) and halborn.com/audits (278 audits, newer) are different indexes. Both enumerated. Website pages embed full report text in Next.js flight data (extracted with `tools/hb_find.py`); findings whose description chunks were not resolved (reports with 0 extracted findings) were screened by keyword scan of the page text only.
4c. **Soqucoin (Halborn website, 2026-03/04)**: LatticeFold+ batch verifier for OP_CHECKFOLDPROOF reads batch_hash/t_coeffs/c from the proof blob and does not bind to the spent UTXO/script; proof replay across transactions/UTXOs. Binding-shaped but the consumer is a UTXO L1 (non-EVM), so excluded by §3 (NON-EVM). Row key `halborn-web-soqucoin-blockchain-architecture-assessment-added-days-...`.
5. **Duplicate**: Halborn MatterLabs Verifier exists in both `ZK Audits/` and `Solidity Smart Contract Audits/`; both enumerated (second key has `-2`).
6. **Dates**: Halborn, RV, Ackee dates are the first date found in the text (Halborn prefers "Date of Engagement"); may be approximate. 27 RV, 4 Ackee, 4 Halborn and 1 Kudelski rows are undated.

## Protocol ambiguities met

- §5 "Check commits via the web URL ... Do not clone": the orchestrator explicitly allowed a blobless clone of the PDF-only Cyfrin reports repo (message from t3z). Used only for `git log`/`ls-tree`.
- §4 "enumerate every report": for Dedaub the public index shows only 19 projects (60 reports); Dedaub's own audits are far more numerous, so enumeration is limited to the public index.
- MixBytes enumerated from its README table (255 PDF links + 6 md); I did not cross-check against the folder tree.
- Halborn enumerated from folder listings via GitHub tree JSON (web, not API); .md/.sig/.html non-PDF files were not counted as reports.
- §5 "findings_total": for the 6 Cyfrin IN rows and the Sacred/Portal Gate rows only the count printed in the report was used; Cyfrin = UNKNOWN (summary-only).

## Method and spot checks

- Index sources: GitHub tree JSON via `github.com/<o>/<r>/tree/<ref>/<path>` with `Accept: application/json` (no API quota), `raw.githubusercontent.com` for PDFs, Quantstamp public `/api/certificates?offset=N` JSON (27 pages, 402 total), Dedaub and Kudelski HTML (Webflow pagination `?dd9f23d2_page=N`).
- All PDFs `pdftotext -layout`; **ligature normalization (ﬁ→fi etc.) applied after discovering `veriﬁer` was missed**; all sources rescanned. Keyword hits were reviewed in context for every flagged report.
- Quotes: the 3 findings quotes were checked programmatically against whitespace-normalized report text (assert passed). No KEEP rows to spot-check.
- One GitHub web 429 at ~22:0x UTC after ~290 requests in ~40 minutes (Cyfrin commits page); backed off, switched to non-GitHub sources; resolved without bypass.
- A tool-use denial by the harness occurred when I guessed Kudelski GitHub repo names; I did not retry it and used Kudelski's public site instead.

## Blocked

See `blocked.md`: Hacken (Cloudflare 403), CertiK skynet (captcha 403; no public list at www.certik.com).

## Deduplication (added 2026-11-23, at orchestrator request)

Duplicate rows carry `dup-of:<report_key>` in the `notes` column of reports.csv (9 rows):
- Halborn website vs GitHub repo (5): matched by shared 40-hex audited/fix commit IDs in the full text (zkSync Era assessment; Moonwell 2022-04 token-sale/comptroller, 2022-08 governance+timelock, 2022-09 dynamic quorum, 2023-07 contracts V2). Method limit: pairs without a shared commit ID (e.g. reports that name no commit) are not detected, so the true overlap may be higher; title+date matching was not reliable because website titles are generic ("Smart Contract Assessment Audit").
- Within-source identical files (3 by sha256): Halborn Yieldly Lottery (Algorand/Solidity folders), MixBytes governance cross-chain bridges (two versions with identical bytes), Ackee Axelar cross-chain DEX.
- Halborn MatterLabs Verifier second folder copy (1, same engagement and commits, bytes differ).

Deduplicated totals (enumerated -> unique): Cyfrin 232->232; Halborn repo 282->280; Halborn website 278->273; RV 110->110; MixBytes 261->260; Ackee 97->96; Kudelski 37->37; Dedaub 60->60; Quantstamp 402->402. Overall 1759 -> 1750 unique audits. IN: 14 rows -> 12 unique. KEEP 0, BORDERLINE 0.
(Quantstamp and Dedaub were not hash-deduplicated: HTML/SPA sources; Cyfrin/RV/Kudelski had no identical hashes.)
