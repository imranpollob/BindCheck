# Acquisition pass 2: progress

Date: 2026-11-23. Output: `acquisition.csv` (197 rows, same schema as pass 1).

| Part | Rows | PINNED-PAIR | PINNED | PARTIAL | NO-COMMIT | PRIVATE-OR-MISSING | FORBIDDEN |
|---|---|---|---|---|---|---|---|
| A: candidates not in pass 1 | 164 | 6 | 26 | 47 | 67 | 15 | 3 |
| B: retry of 33 KEEP rows (notes start `pass2-retry:`) | 33 | 10 | 10 | 5 | 7 | 1 | 0 |
| Total | 197 | 16 | 36 | 52 | 74 | 16 | 3 |

"none" in the closing message = NO-COMMIT 74 + PRIVATE-OR-MISSING 16 + FORBIDDEN 3 = 93.

Part B, before and after:
- Before (pass 1): 15 PARTIAL, 13 NO-COMMIT, 5 PINNED.
- Rows with a fix commit or candidate: 11 in pass 1, 17 in pass 2.
- Rows with a firm fix (named-in-report, message-cites-finding or file-and-message-match): 12 in pass 2.

Part A, by fix confidence: 1 named-in-report, 3 message-cites-finding, 8 file-and-message-match, 50 candidate (unconfirmed), 102 none-found.

Held-out guard: run as its own command before every repo. Three FORBIDDEN rows were recorded from report text only and not cloned: G0400 (`webb-tools/protocol-solidity`, which redirects to `tangle-network/protocol-solidity`), G0559 (`AztecProtocol/aztec-packages`) and G0603 (`tornadocash/tornado-core`).

Pairs are asserted only when the fix is a descendant of the vuln commit. Six rows have a fix commit that is not a descendant: G0373, G0374, G0375, G0535, G0342 and G0052. In each the fix is recorded and the row note says so. Only G0052 changed status (PINNED-PAIR to PINNED); the other five were never PINNED-PAIR.
