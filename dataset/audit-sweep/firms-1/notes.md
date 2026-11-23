# notes (firms-1, PROTOCOL v1)

## Coverage
| Source | Enumerated | IN | KEEP | BORDERLINE | DROP logged | Note |
|---|---|---|---|---|---|---|
| Zellic (Zellic/publications@bc479398) | 415 | 23 | 7 | 14 | 25 | full re-screen under v1; all 415 PDFs hashed |
| Trail of Bits (trailofbits/publications@e0894490, reviews/) | 463 | 17 | 5 | 11 | 11 | 3 research PDFs in reports/ not counted |
| Veridise (audit-report-sitemap.xml) | 167 | 36 | 2 | 10 | 3 | 167/167 pages and PDFs fetched; PDF sha256 recorded |
| OpenZeppelin (sitemap.xml /news/*audit*, *review*) | 419 | 29 | 2 | 7 | 1 | HTML reports; sha256 is of the saved page |
| Consensys Diligence | 0 | - | - | - | - | BLOCKED (Cloudflare challenge); orchestrator handles via browser |
Totals: 1464 reports enumerated, 105 IN, 16 KEEP, 42 BORDERLINE, 40 DROP logged.
Veridise: 61/167 report pages first returned HTTP 429 (4 parallel connections); after the orchestrator's instruction all remaining pages and all 167 PDFs were fetched serially (10 s gaps) with no further 429. Coverage 167/167.

## Depth caveats (important for QC)
- Screen 2 was NOT a line-by-line read of every finding. Method: finding titles for every IN report, then full reading of findings whose title/summary involved a proof, verifier, public input, nullifier, commitment, signature challenge or VK. Pure circuit under-constraints (e.g. Scroll zkEVM opcode gadgets) are represented by a few DROP rows only. `findings_logged` therefore under-counts DROP rows by design.
- Many Veridise/OZ IN reports (zkSync L1, Scroll L1, Linea rollup, RISC Zero, Boundless, Wormhole Boundless, Fluent, DendrETH, Semaphore, RLN, Hydra, Webb) had titles scanned only, nothing logged. These are the first place to look for misses.
- Veridise repo URLs are often not stated in the PDFs; those rows have repo=UNKNOWN, acquirability NO-COMMIT, and the audited short commit in notes.
- Veridise quotes are verbatim but mostly the first sentence(s) of the description (some are weak, e.g. V-ARIA-VUL-001). OZ quotes are first body paragraph sentences. All quotes were machine-checked as substrings of the extracted text.
- OZ `findings_total` comes from the "Total issues" line (includes none of the notes); OZ finding parsing is heuristic.
- ToB Scroll wave-1 report: finding ID 19 absent from the report text; total recorded as 27.

## Protocol ambiguities met
1. §3: "A report that audits only the circuits, or only the contracts, of such a system is still IN if the system has an EVM consumer." Applied to rollup/coprocessor systems. Library-only audits (Barretenberg bigfield, Axiom halo2-lib, Aztec bigfield, Circom bigint, ChainSafe BLS) were recorded OUT with `NON-EVM` and a note, because no verifier/consumer is in the audited scope; Axiom halo2 library upgrades (snark-verifier EVM loader) and zkemail.nr were kept IN. Reviewer may want a separate code.
2. §7 has no code for "audited side is neither circuits nor contracts" (Jovay relayer, Zellic). Recorded OUT / NO-ZK-COMPONENT with explanation.
3. §2 criterion 1 says SNARK or STARK: AZTEC 2019 (ToB) uses sigma-protocol range proofs; kept IN with a note.
4. Nori Bridge (Zellic): ZK proof verified in a Mina contract; recorded NON-EVM although the Platforms line lists EVM-compatible. 3.2 (vk_root not pinned) is binding-shaped.
5. Front-running rule applied: Nocturne 3.3 changed from pilot DROP to KEEP (P1, refund recipient); Veridise ARIA-001 KEEP.
6. §5 keyword scan: Zellic "About" boilerplate yields zk=1 and cairo=1 in nearly every report, and OZ pages carry nav text ("ZKsync", "Zero Knowledge Proof Audit"); both were filtered (OZ: body region only, baseline zk<=2/stark<=1 ignored).
7. §5 "report names no fix commit" (ToB gives only Fix Status): fix_commit=UNKNOWN; acquirability judged on the audited commit only.
8. DROP vs BORDERLINE for forgeable verifiers with no consumer effect (Linea PlonkVerifier 3.x, Nebra batching): I used BORDERLINE only when the auditor names a downstream effect or the artefact is a consumer-facing verifier; otherwise DROP / NOT-BINDING-CIRCUIT-ONLY.

## Guard and conduct
- Held-out guard slips (guard and fetch in one command; all ALLOWED) and pre-guard probes of AztecProtocol/aztec-v1 and succinctlabs/telepathy-circuits are listed in blocked.md. Later batches ran the guard as its own command first. Only HTTP status codes and directory listings were fetched; no code read, no clone, no API calls beyond one ToB tree call (1 of the ~10/hour budget).
- Commit existence checked via github.com web URLs only. Malda zk-coprocessor repo returns 404 under both name variants; succinctlabs/telepathy returns 404.

## Spot-check
All quotes machine-verified. No manual re-read of a random sample against the PDFs was done beyond reading the Zellic/ToB/Veridise/OZ findings that were logged KEEP/BORDERLINE; I would expect the orchestrator's 10% check to find errors mostly in pattern_guess and in circuit_present/verifier_present/consumer_present, which were judged from directory listings or report scope text.

## Time
Zellic+ToB ~ 2.5 h wall, Veridise/OZ fetching ~1 h (throttled), screening ~1.5 h. Approximate; the session clock was unreliable.
