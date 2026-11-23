# contests agent notes (protocol v1)

Date: 2026-11-22. Sources: Code4rena, Sherlock, Cantina competitions.

## Funnel
| Source | Enumerated | IN | NON-EVM | UNREADABLE | Findings logged | KEEP | BORDERLINE |
|---|---|---|---|---|---|---|---|
| Code4rena | 412 sitemap reports (415 rows: 2 spurious/404 slugs + 1 alias) | 5 | 1 | 2 | 14 | 0 | 1 (succinct M-01) |
| Sherlock | 301 | 6 | 2 | 64 | 18 | 2 (morphl2 H-2, symbiotic-relay Z-1) | 0 |
| Cantina | 116 | 5 | 2 | 0 | 0 | 0 | 0 |

## Method and limits
- C4: enumerated from code4rena.com/sitemap.xml; full-text keyword scan on each downloaded report HTML. Only 5 IN (zkSync x4, Succinct SP1).
- Sherlock: enumerated via the public JSON `audits.sherlock.xyz/api/contests` (31 pages) and `/api/contests/<id>` (scope + final report text). Keyword scan covered description, scope, context and report text. 64 contests UNREADABLE: report text empty in the API; judging repos were 404 (50) or had an empty README (15) (recovery pass done, all guarded ALLOWED). ZKP2P V2 (805) and Covalent EWM Light Client (618) are ZK-likely and still UNRESOLVED. Avail (146) is IN from its contest README (VectorX proofs) but 0 labelled High/Medium issues were found via 2 API calls (label-based, unverified).
- Cantina: enumerated from sitemap-0.xml (116 competition UUIDs). The competition pages only expose description/scope, not findings. 5 IN contests (Aligned, Space and Time, SP1, OpenVM, Succinct network) have findings_total UNKNOWN; their findings may be in spearbit/portfolio (firms-2). Citrea/Clementine are Bitcoin consumers (NON-EVM).
- The 109 OUT Cantina and the NO-ZK Sherlock rows were screened by description/scope (and report text for Sherlock), not by reading findings.
- Pico (Sherlock 873): only the 10 Highs were logged; M-1..M-5 were not logged (circuit-only/privacy). Re-screen if needed.

## Protocol ambiguities
- §3 "A report that audits only the circuits ... is still IN if the system has an EVM consumer": applied to SP1, Pico, OpenVM (circuit-side scopes). has_evm_consumer says 'no (scope Rust only)' for Succinct/Pico.
- §2 criterion 2 for circuit under-constraints with a described consumer effect (Symbiotic Z-1 forged proof sets valSetHeader): logged KEEP; reviewer should confirm vs NOT-BINDING-CIRCUIT-ONLY.
- Taiko 2024-03 (C4) marked NO-ZK-COMPONENT: verifiers audited were SGX; "zk" only branding.
- C4 `report_date` is blank for older reports (page lacks a parseable date).
- §9 "~10 API calls per hour": used 9 API calls total over the run (org counts x2, 5 org repo pages, 2 Avail issue lists).

## Guard slips
One unguarded status-only curl to github.com/code-423n4/code423n4.com at the start (logged in blocked.md). No block/CAPTCHA/login encountered; `hc` was initially not on PATH (path /home/pollmix/.local/bin/hc).

## Spot checks
- C4 quotes and Sherlock quotes were asserted against the source text by script (C4 case-insensitive match then original case copied; Sherlock whitespace-normalised). 
- Not independently re-read by a second pass; the orchestrator's 10% QC applies.
