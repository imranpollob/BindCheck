# firms-2 notes (final)

## Totals (reports.csv: 2843 rows, all report_keys unique; findings.csv: 80 rows = 13 KEEP, 26 BORDERLINE, 41 DROP)
| Source | Enumerated | IN |
|---|---|---|
| zkSecurity | 68 | 20 |
| PSE (distributed) | 3 | 1 |
| Spearbit portfolio (+Cantina, merged) | 795 (766 ids + 29 README rows with no link) | 18 |
| Nethermind | 203 | 29 |
| ChainSecurity | 437 | 4 |
| OtterSec | 397 | 1 |
| Hexens | 183 | 9 |
| Sigma Prime | 149 | 1 |
| Least Authority | 71 | 1 |
| yAcademy | 1 (only zkemail/zk-email-verify/audits/yacademy-audit.pdf; site DOWN per orchestrator) | 1 |
| Oxorio | 0 (NO-INDEX, see blocked.md) | 0 |
| Zokyo | 316 | 3 |
| ABDK Consulting | 220 | 47 (IN decided from keyword scan/scope; findings read selectively) |
(rows in Spearbit/Cantina column counted from the sources column; Cantina IN=18, Spearbit-only README rows 29 UNREADABLE)

## Enumeration methods
- zkSecurity: reports.zksecurity.xyz index cards (68).
- PSE (distributed): github.com/privacy-scaling-explorations holds only `.github` (renamed to privacy-ethereum). Listed 139 repos of github.com/orgs/privacy-ethereum (HTML pages 1-5) plus 8 PSE-incubated repos (semaphore, anon-aadhaar, zk-kit, mopro, rln-circuits-v2, tlsn, maci, zk-email-verify); scanned each repo root HTML for audit/security dirs and pse.dev/en/blog. Found: Anon Aadhaar PSE audit (IN), P0TION assessment (OUT), Sonobe post (OUT). 4 GitHub API calls total.
- Spearbit+Cantina: spearbit/portfolio is README-only now and links Cantina; ids from cantina.xyz/portfolio SSR (509) + sitemap-0.xml (611) + README (134) = 766; 729 PDFs full-text scanned; 61 pages with counts only are UNREADABLE (incl. Polygon zkEVM Spearbit reviews, likely IN).
- Nethermind: NethermindEth/PublicAuditReports root tree (203 PDFs).
- ChainSecurity: 437 /security-audit/ pages from the reports list; PDFs scanned.
- OtterSec: osec.io/audits table (397 rows; /reports/<id> serves PDF).
- Hexens: hexens.io/audit-reports (145 pages) + Hexens/Smart-Contract-Review-Public-Reports (178 PDFs).
- Sigma Prime: sigp/public-audits/reports recursive web listing (149 PDFs).
- Least Authority: published-audits index -> 71 blog pages -> PDF via /static/publications or <slug>-report links (7 without link = UNREADABLE).
- Zokyo: zokyo-sec/audit-reports 242 dirs listed via web (316 files, 13 unreadable/scanned).
- ABDK: abdk-consulting/audits 120 dirs via web (220 PDFs). Includes Railgun Circom/Solidity (2021) with CVF-20 (inputs-hash omits commitments), CVF-59 (pairing check always true), CVF-61 (no curve checks), CVF-21/22/23/9.

## Method limits (be honest in the funnel)
- Keyword screening is on full extracted text; Nethermind/Least Authority/ABDK boilerplate hits were baseline-subtracted.
- For IN reports I did NOT read every finding. Circuit-only soundness findings in circuit-heavy reports (Self, Lighter, OpenVM, Intmax, many ABDK zk-rollup/mixer reports) are only sampled. ABDK IN reports beyond Railgun, Nebra, Morphose and ZeroPool were not read finding by finding (tornado, composable, mystiko, zksync/zkswap/zklink, edgeswap, nil, starkware, semaphore). A rescreen pass should cover them.
- IN/OUT where no EVM consumer is stated: libraries and zkVMs without a stated EVM verifier were OUT (NON-EVM); OpenVM and Plonky2-in-Intmax were IN because an EVM wrapper/L1 contract exists.
- v1.2 BORDERLINE discipline was applied after the fact: 5 rows downgraded to DROP (circuit-internal under-constraints).
- repo/commit data: audited commits named in reports were checked by web URL only; paths for circuit/verifier/consumer presence were checked for a few reports only (Aleph Zero, Anon Aadhaar, snark-wrapper, SP1 Blobstream, EncryptedERC, Railgun contract). Many rows are NO-COMMIT or PARTIAL.
- Date fields: Cantina/ChainSecurity/Least Authority use site dates; Nethermind uses first date in text; Sigma Prime/ABDK dates mostly UNKNOWN.
- No PDFs or raw logs are committed; all downloads under /tmp/claude-1000/audit-sweep/firms-2/.

## Protocol ambiguities
- §3 "IN if the system has an EVM consumer" vs §5 "confirm against scope": applied conservatively (see above).
- §2 definition of under-constraint-with-effect vs v1.2 BORDERLINE discipline: resolved by v1.2 (circuit-internal => DROP).
- v1.1 requires verifier-soundness (P4) findings to be logged even without effect: applied to ABDK Railgun, Nebra, RISC Zero checkField; NOT re-applied retroactively to earlier firms (rescreen lane).

## Guard slips
See blocked.md (retroactive guard run: 153/153 ALLOWED; later repos guarded first).

## Spot checks
All quotes were machine-verified as substrings of extracted report text (whitespace-normalised). No independent human spot check yet.
