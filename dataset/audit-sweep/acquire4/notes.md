# acquire4 (pin4): pin code for LIGHT items

Date: 2026-11-24. Scope: 146 items in `dataset/labels-v1/LABELS-v1.csv` with `tier = LIGHT`, `binding` Y or N, no `dup_of`, and `holdout_flag` not FORBIDDEN (54 Y, 92 N). Output: `acquisition.csv` (acquire3 schema plus `item_id`). Every item has a row.

## Result

| acquirability | before | after |
|---|---|---|
| PINNED-PAIR | 0 | 4 |
| PINNED | 0 | 20 |
| PARTIAL | 54 | 47 |
| NO-COMMIT | 59 | 39 |
| PRIVATE-OR-MISSING | 31 | 34 |
| N/A (DROP) | 2 | 2 |

24 pinned of 146 tried: 12 Y and 12 N. 35 rows changed status or gained evidence.

- **PINNED-PAIR (4):** L055, L168, L172, L196.
- **PINNED (20):**
  - binding Y: L057, L076, L089, L119, L149, L166, L169, L179, L180, L193.
  - binding N: L096, L107, L108, L144, L152, L155, L165, L170, L190, L200.

## Method

- Guard: `dataset/audit-sweep/tools/check_holdout.py` was run on every repo before cloning (all ALLOWED).
- Blobless clones with `--no-checkout` in the session scratchpad. Only `git log`, `ls-tree`, `merge-base`, `diff-tree --name-only` and `rev-parse` were used. No diffs, no checkout and no source reads. Clones were not deleted (the brief forbids `rm`).
- New audited commits came from the report text's stated scope/commit: Veridise PDFs (Steel, Kailua V2, Fluent), Nethermind PDFs (Worldcoin, Privado), the Hexens PDF, and OpenZeppelin pages. Existence checks for unclonable SHAs used web commit URLs (HTTP status only).
- PINNED means that the audited commit resolves in a clone and that circuit, verifier and consumer file names all exist in its tree.
- PINNED-PAIR also needs a fix that resolves, descends from the audited commit, and has confidence named-in-report, message-cites-finding or file-and-message-match.
- The script checked every listed path against `ls-tree` and checked fix ancestry. It reported no mismatches.

## Judgement calls (review these)

1. **Submodule or vendored verifiers.** Counted as visible where `.gitmodules` or a vendored flattened import exists at the audited commit (acquire3 precedent). The verifier source itself was not file-checked. This applies to boundless, kailua, blobstreamx, r0vm-helios and sp1-helios.
2. **Generated verifiers.** Rows whose verifier is only an interface or a generator template are PARTIAL (e.g. Unirep L198, zkopru L101, ezkl L123/L173).
3. **Derived pins** (the scope names no SHA):
   - r0vm-helios (L149, L172): scope is PR #2; the pin is merge commit `87796bb`, the parent of the first audit-fix commit `667f6d5`. `7f56d8b` carries the same title on main.
   - EncryptedERC (L055, L190): scope is branch `circom2-circuits`; the pin is `495b497`, the parent of the first ETRP fix.
4. **Hinkal 2026 (6 rows).** The audited commit `306b082` is only an unreferenced object. Public main is a squashed re-upload. The report-named fix SHAs return 404, so there is no pair. These rows are fragile.
5. **Semaphore `27320f1` (L165).** Reachable only through `refs/pull/*/head`.
6. **Kailua fix commits.** L089 and L119 stay candidate (unconfirmed); the only evidence is a release commit.
7. **Fix candidates.** L152's candidate is `7b70488` (message match only, not diff-confirmed). The SP1 Helios candidate `07096e1` was rejected because it is not a descendant of the audited commit.

## Not pinned, with reasons

- **PRIVATE-OR-MISSING with a named commit:** zkSync L162 (`zksync-2-dev` 404), Linea L086 (`linea-contracts-audit` 404), Axiom L059 (working repo 404; the public repo has no commit with prefix `41fab5`), plus the earlier private rows (Hinkal-Neo, Singularity/portalgate, DOP, Nightfall, ...).
- **PARTIAL, new commits found but an artifact is missing (contract-only or cross-repo):** L130, L118, L192, L065, L134, L139, L074, L185. L139 and L074 were not cloned, so their trees were not checked.
- **Unresolvable audited SHAs:**
  - lighter-prover (L054, L081, L115): the report SHAs are not on github.com or in the clone, and public history starts 2025-12-25, after the reports.
  - telepathy (L070, L077, L156), panther (L071, L105) and malda-zk-coprocessor (L072, L182): the report SHAs return 404 and are absent from the clone.
- **tornado-anonymity-mining (L163):** ABDK says the audited files were private. The `Fix CVF-*` commits exist, but no audited baseline is named.
- **No repo or commit in the report, not re-read this pass:** about 35 rows (ABDK private repos, zkLink, matterlabs, edgeswap, nebra, Intmax2 ChainSecurity, Silent, ...). `InternetMaximalism/intmax2-zkp` is public and guard-ALLOWED, and was cloned, but the ChainSecurity reports were not read for a commit. This is the best candidate for a follow-up pass.
- **Hexens/others:** L190 has no ETRP-18 fix located.

## Unexpected observations

- `git fetch origin <sha>` fails with "not our ref" for the unreferenced report SHAs. Only SHAs that happen to be in the clone resolve.
- Sibling findings in one report share one audited commit but can have different fix confidence, so per-finding fix evidence is thin for the "Assorted audit fixes" commits.
- Nothing was committed, per the brief.
