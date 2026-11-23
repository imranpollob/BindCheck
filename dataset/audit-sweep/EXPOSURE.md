# Audit sweep: held-out exposure log

This file records every time a sweep agent touched a repository that the held-out guard (`tools/check_holdout.py`) marks FORBIDDEN, i.e. a family reserved for the held-out v3 evaluation. The orchestrator maintains it, and a future paper's exposure ledger must include it.

| Date (UTC) | Agent | Repository | What was fetched | Code read? | Disposition |
|---|---|---|---|---|---|
| 2026-11-22 ~20:5x | curated | tangle-network/protocol-solidity | Web commit-existence check `/commit/848d073` (HTTP 200 only), sent in the same shell command as the guard and before its output was read | No | Metadata-only touch. The family stays reserved, but this touch is disclosed. |
| 2026-11-22 ~21:0x | curated | summa-dev/summa-solvency | `issues/32` page fetched in a batch after the guard returned FORBIDDEN. Only the title and meta description were printed; the HTML was deleted unread. | No | Metadata-only touch. Disclosed. |
| 2026-11-22 ~21:0x | curated | 0xPolygonHermez/zisk | `security/advisories/GHSA-qjgg-fcj3-p9x3` fetched in the same batch. Only the title and meta description were printed; deleted unread. | No | Metadata-only touch. Disclosed. |

**Procedural slips with no exposure:**

- **firms-2, 2026-11-22.** Commit and root pages for about 153 repositories were fetched before the guard ran: renegade-fi ×3, zkOS-circuits, openpassport, anon-aadhaar, and ~147 PSE org repository root pages. The guard was run retroactively on all 153, and all returned ALLOWED (0 FORBIDDEN). No reserved family was touched.
- **firms-1, 2026-11-22.**
  - For 15 repositories, the guard and the fetch were issued in the same command. All 15 were ALLOWED.
  - AztecProtocol/aztec-v1 and succinctlabs/telepathy-circuits were probed before the guard ran. Both were ALLOWED.
  - Only HTTP codes and directory listings were fetched. No reserved family was touched.
- **contests, 2026-11-22.** One HTTP-status request (`code-423n4/code423n4.com`, 200) was sent before the guard ran. The guard then returned ALLOWED. No reserved family was touched.

- **rescreen, 2026-11-22.** `webb-tools/protocol-solidity` redirects to the FORBIDDEN `tangle-network/protocol-solidity` (already listed above). Only an HTTP status was read. No new reserved family was touched.

**Assessment.** No source code, circuit or contract from a reserved family was read. All three touches are issue, advisory or commit metadata that a curated public bug list (zkbugs) already summarizes. The orchestrator judges the contamination risk as negligible, but the families must be listed as "metadata-touched" when the held-out v3 sample is drawn. The author decides whether to exclude them.

**Corrective rule issued 2026-11-22.** Run the guard as its own command and read its result before issuing any other request for that repository. Never batch-download URLs for repositories that have not yet been guarded.

## Audit-report text about reserved families (semantic exposure)

The protocol allowed reading audit-report text for FORBIDDEN families (only their repositories were off-limits). Reading a reserved family's audit findings is nonetheless **semantic exposure**: it reveals known bugs in a family reserved for held-out v3. Known cases:

- **Tornado Cash** (reserved family `v2-family:288524d1ec6a14d95809`). The ABDK reports `Tornado_circuit_audit.pdf`, `Tornado_solidity_audit.pdf`, `Tornado_cryptographic_review.pdf` and `TornadoCash_anonymity_mining_first_audit_ABDK.pdf` were screened at report level by firms-2 (2026-11-22).
- **tangle-network/protocol-solidity, summa-solvency, zisk**: see the touches above. zkbugs config text was read.

**Rule for the benchmark.** A candidate whose repository is FORBIDDEN must not enter the study or reserved audit sets while its family stays in the held-out v3 pool. The author decides one of two options:

- (a) keep these families held-out and exclude their audit candidates from the benchmark; or
- (b) move the families out of the held-out pool and allow their audit candidates.

`merged/candidates.csv` carries `holdout_flag`; filter on it at split time.
