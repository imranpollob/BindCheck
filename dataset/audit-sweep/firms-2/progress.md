# progress firms-2
started 2026-11-22. Source order: zkSecurity, PSE, Spearbit, Cantina, Nethermind, ChainSecurity, OtterSec, Hexens, Sigma Prime, Least Authority, yAcademy, Oxorio, Zokyo.
## zkSecurity
- 68 reports listed on index; HTML downloaded to /tmp/.../zks/. Screening in progress (no rows written yet).
- zkSecurity done rows: hinkal, intmax, renegade x3. Next IN: aleph-zero-shielder, celo-self x2, self-aadhaar, silent x2, risc0-helios, zklighter x6, openvm, zkemail; then write OUT rows for the rest (scripts in /tmp/.../tools/e_zks*.py; csvh/mk helpers)
- done also: aleph, helios, celo-self x2, self-aadhaar. Remaining IN: silent, silent2, zklighter x6, openvm, zkemail; then OUT rows. TODO later: add zks OUT rows script e_zks_out.py
- done: silent x2, lighter x6. Remaining IN: openvm, zkemail; then OUT rows
- **zkSecurity DONE** (2026-11-22): 68 enumerated / 20 IN / 5 KEEP / 12 BORDERLINE. No blocks. Findings logged only where proof/verifier/binding related (see findings_logged per report); circuit-only soundness findings mostly logged as DROP samples, not exhaustively.
## Next: PSE audits (github.com/privacy-scaling-explorations audits page)
- PSE: no public index (see blocked.md), 0 enumerated. Next: Spearbit
- **PSE (distributed) DONE**: method = privacy-ethereum org repo list (HTML pages 1-5, 139 repos, 0 API calls beyond 3 API calls that showed old org privacy-scaling-explorations has only .github) + 8 PSE-incubated repos; each repo root scanned for audit/security dirs; pse.dev/en/blog scanned. Found: Anon Aadhaar PSE audit (IN), P0TION assessment (OUT), Sonobe blog post (OUT). zkemail/zk-email-verify/audits holds yacademy-audit.pdf + zksecurity-audit.pdf (note for yAcademy). API calls used: 3 (+1 earlier org check). 
- Next: Cantina portfolio (509 ids in cantina.xyz/portfolio SSR index; pages SSR with full text and pdf link cdn.cantina.xyz/reports/*.pdf); Spearbit README (164 rows, 134 cantina links) overlaps.
- **Spearbit portfolio + Cantina portfolio DONE** (merged, because spearbit/portfolio README now links Cantina): 766 portfolio ids (509 from cantina.xyz/portfolio SSR index + 257 more from sitemap-0.xml and Spearbit README) + 29 README rows with no link = 795 rows. 729 PDFs downloaded and full-text keyword-scanned (pdftotext). IN=18, KEEP=0, BORDERLINE=1 (snark-wrapper 5.1.1). 61 UNREADABLE (pages with finding counts only, no PDF). Findings of IN reports only logged where proof-related title (5 logged); remaining IN findings not exhaustively read.
- Next: Nethermind, ChainSecurity, OtterSec, Hexens, Sigma Prime, Least Authority, yAcademy, Oxorio, Zokyo
- **Nethermind DONE**: NethermindEth/PublicAuditReports root listing (HTML embedded tree, 203 PDFs, 0 API calls). 203 enumerated / 29 IN / 5 KEEP / 4 BORDERLINE. Boilerplate keywords (About Nethermind mentions zk, cairo, stark) excluded from screening; Starknet reports = NON-EVM. Next: ChainSecurity
- **ChainSecurity DONE**: 437 report pages on /smart-contract-audit-reports/ (security-audit slugs), 437 PDFs scanned. 437 enumerated / 4 IN / 0 KEEP / 2 BORDERLINE. Next: OtterSec
- **OtterSec DONE**: osec.io/audits table (397 rows, 395 PDFs via osec.io/reports/<id>). 397 enumerated / 1 IN / 1 KEEP / 0 BORDERLINE. Next: Hexens
- **Hexens DONE** (hexens.io/audit-reports 145 pages + Hexens/Smart-Contract-Review-Public-Reports 178 PDFs): rows written; 9 IN, 1 KEEP (ETRP-12), 1 BORDERLINE.
- **STOPPED: usage limit reached 2026-11-22.** Remaining sources NOT started: Sigma Prime (github.com/sigp/public-audits), Least Authority, yAcademy, Oxorio, Zokyo. notes.md NOT yet written. Helper scripts live in /tmp/claude-1000/audit-sweep/firms-2/tools (not committed). Note for yAcademy: zkemail/zk-email-verify/audits/yacademy-audit.pdf exists.
- **Sigma Prime DONE**: sigp/public-audits (recursive web listing, 149 PDFs). 149/1 IN/0 KEEP/0 BORDERLINE. Next: Least Authority
- notes.md written (partial). Least Authority fetch denied by permission classifier; yAcademy/Oxorio/Zokyo pending.
- **Least Authority DONE**: published-audits index (71 blog pages, 64 PDFs via static/publications or <slug>-report links; 7 no link=UNREADABLE). 71/1 IN/0/0. Rule changes noted: no rm, no bg jobs; v1.2 BORDERLINE discipline applied, 5 rows downgraded. yAcademy single report logged. Next: Zokyo (listing in progress, foreground), ABDK.
- **Zokyo DONE**: zokyo-sec/audit-reports (242 dirs listed via web, 316 files, 13 unreadable). 316/3 IN/0 KEEP/1 BORDERLINE. Next: ABDK
- **ALL SOURCES DONE** (Oxorio NO-INDEX, yAcademy single report). notes.md final. DONE message sent.
