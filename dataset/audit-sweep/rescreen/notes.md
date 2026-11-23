# rescreen notes (protocol v1.1, re-read against v1.2 BORDERLINE discipline)

## Totals
- `findings.csv`: 206 new rows over 82 reports: 2 KEEP, 91 BORDERLINE, 113 DROP. Pattern of non-DROP rows: P4 44, P2 15, P1 12, P3 10, P5 8, OTHER 5.
- `disagreements.csv`: 25 existing DROP rows (other agents) that look like v1.1 verifier-soundness P4 cases (Fiat-Shamir, recursion/vk_root, curve checks, SP1/Pico verifier gaps). Not rewritten.
- `report_corrections.csv`: 4 rows, all for `zellic-nori-bridge-2026-07`.

## v1.2 reclassification (orchestrator request)
- At the orchestrator's message my first 143 rows were 126 BORDERLINE / 1 KEEP / 16 DROP. After re-reading each under v1.2 (liveness, gas/memory, circuit-internal, off-chain bugs -> DROP), the same families (Zellic, ToB, Veridise, OpenZeppelin: 149 rows incl. 6 added later) stand at 65 BORDERLINE / 1 KEEP / 83 DROP. My interim hc note said "~58 B"; the exact figure is 65. Reclassification is applied by `overrides` and is visible in each row's notes ("v1.2 BORDERLINE discipline: reclassified from BORDERLINE").
- Whole file after later families: 91 B / 2 K / 113 D.

## Screen-1 correction: Nori
Corrected NON-EVM -> IN, but the orchestrator's stated reason is not what the report shows. The SP1 PLONK proof is verified by o1js circuits on Mina. The Ethereum side that verifies a proof is `MinaStateSettlement.updateChain` (Mina state proof via Aligned Layer batch inclusion, records verifiedLedgerHashes). The two Critical SP1 findings (3.1, 3.2) and 3.3 therefore have a Mina consumer. They are logged BORDERLINE with that caveat; the author may prefer to treat them as NON-EVM-consumer.

## Method and honest coverage
- For each unique file (232 unique SHA-256 of 263) I extracted finding indexes by auditor format (Veridise IDs, Zellic `3.N`, ToB numbered list with Severity, OZ headings, zksecurity `#NN`, Nethermind/ChainSecurity TOC, Hexens IDs), diffed against logged rows by finding_id (alias-aware: SHA duplicates + content duplicates) and by title overlap, and judged unlogged titles. I read bodies only for candidates (via quote extraction), not every finding of every report. Expect residual misses.
- Quotes: most are auto-extracted from the first descriptive sentence after the finding header and asserted to be verbatim substrings (whitespace/ligature-folded). 7 had metadata noise and were replaced by hand. Quotes are mechanism-descriptive, not always the impact sentence.
- Calibration: SP1CC-004/-008, ToB Aztec #8, and Nori were all recovered. OZ Linea verifier "Missing Commitment in Challenge" was already logged.
- Severity fields are "see report" for auto-built rows (not parsed).
- Not covered / limits: Cantina contest HTMLs (5) contain only the contest page, no findings; sherlock-avail-2023-12 (README empty) and sherlock-pico-2025-08 (judging repo name guess 404) could not be fetched; sherlock-malda-2025-07 README was fetched from sherlock-audit/2025-07-malda-judging (guard ALLOWED) and had nothing new beyond logged M-4/M-8; summa-issue32 and GHSA/0xparc entries are single-finding and already logged; Taiko (OZ 2024, Sigma) is mostly SGX/optimistic-proof logic and was skimmed by title only; cantina-agglayer cryptography/zkevm-contracts, zisk, zksync OS, matterlabs v29, Scroll OZ phases skimmed by title.
- Hexens/Nethermind/zksecurity: `nethermind-nm0126` and `nm0122-world-final` repeat nm0122-final content; rows added once on `nethermind-nm0122-final-worldcoin-2023-05`.
- ToB/ezkl rows 4,13,14,15,34 were already logged (skipped by alias check).

## Artifact check
- Guard run first as its own command for every repo before any web request. HTTP checks via `github.com/<o>/<r>/commit/<sha>` only; 0 GitHub API calls. File presence (circuit/verifier/consumer) not checked (no tree listing), so acquirability for new rows is at most PARTIAL.
- 93 non-DROP rows: 13 reports resolved directly; sibling rows' artifact fields copied where the same report already had them; 32 rows `NO-COMMIT` (repo/commit not resolved quickly).
- Held-out incident: `webb-tools/protocol-solidity` commit URL redirected (HTTP 301) to `tangle-network/protocol-solidity`, which the guard reports FORBIDDEN (guard had said ALLOWED for the pre-redirect name). I only read the HTTP status code of the redirect chain, no repo content. The one non-DROP Webb row (V-WEB-VUL-005) is marked FORBIDDEN (DROP rows carry no artifact fields), commit left as text from the report. Orchestrator should confirm that is acceptable.
- Other redirects: risc0/kailua -> boundless-xyz/kailua (ALLOWED), cosmos/solidity-ibc-eureka -> lfdt-ibc/ibc-contracts (ALLOWED), succinctlabs/sp1-wip commit 404.

## Not done
- No project-status.md update (instructions confined me to this folder).
- No commits made.
