# Acquisition pass 3 (delta) notes

**Scope:** the 17 rows in `merged/delta_candidates.csv`: Quantstamp Hinkal 2023 (8), Quantstamp Hinkal 2026 (6), Quantstamp Datachain zkDCAP (2) and Hacken Zilliqa (1). The protocol is ACQUISITION.md v1 and the method follows `acquire2/notes.md`. **Date:** 2026-11-23.

## Method

- **Held-out guard.** Run once, as its own command, before any repository was touched: `python3 dataset/audit-sweep/tools/check_holdout.py Zilliqa/zkp_recovery_app Novelty-Today/Hinkal-Neo-Protocol Hinkal-Protocol/Hinkal-Contracts-Circuits datachainlab/zkdcap datachainlab/lcp-solidity`. All five were ALLOWED (exit 0).
- **Clones.** Blobless (`git clone --filter=blob:none --no-checkout`) into `/tmp/claude-1000/acquire3/clones/`: four repos cloned, and `Novelty-Today/Hinkal-Neo-Protocol` returned "not found".
- **Git commands used:**
  - `git log` for messages and dates, including `--grep` and `--all`;
  - `git diff-tree --name-only -r` and `git log --name-only` for file names;
  - `git ls-tree -r --name-only`, `git cat-file -t`, `git merge-base --is-ancestor`, `git ls-remote`;
  - one `git fetch <sha>` (refused with "not our ref").
- **Not done:** no checkout, no `git show` of file contents, no patch. No source or diff content was read.
- **Lazy fetch.** In a partial clone, `git cat-file -t <sha>` lazily fetches a missing commit object from GitHub. That is how `306b082` (Hinkal 2026) was resolved. Only commit and tree objects were fetched; no blobs were read.
- **GitHub API.** One call: `search/repositories?q=hinkal`, for the Hinkal 2023 mirror check. Plus one web request to `github.com/Novelty-Today` (404).
- **Report text.**
  - **Quantstamp:** extracted text in `/tmp/claude-1000/audit-sweep/quantstamp/`.
  - **Hacken Zilliqa:** the page returns 403 to curl. It was read in the browser (Claude in Chrome): the page text plus the "Details" panel of the newAddr finding (Description and Recommendation tabs). That panel gives the real ID, `F-2026-19026`, and the resolution "Fixed in commit 182ecaa".
- **`PINNED-PAIR` criteria** are as in acquire2: the vuln and fix commits resolve; the fix descends from the vuln commit; the fix is named-in-report or matches the finding by message; and the circuit, verifier and consumer files exist at the vuln commit.

## Per-candidate results

| Rows | Before → after | Why |
|---|---|---|
| Hinkal 2023 G0624, G0628, G0629, G0632, G0637, G0638, G0639, G0642 | PRIVATE-OR-MISSING → PRIVATE-OR-MISSING | See below. |
| Hinkal 2026 G0645, G0646, G0649, G0650, G0652, G0653 | PARTIAL → PARTIAL | See below. |
| zkDCAP G0658, G0659 | PINNED → PINNED-PAIR | See below. |
| Zilliqa G0360 | PARTIAL → PARTIAL | See below. |

**Hinkal 2023 (8 rows):**
- The repo is not public. The `Novelty-Today` org page returns 404.
- One mirror check: the search found only `Hinkal-Protocol/Hinkal-Contracts-Circuits` (created 2026-07-03), `Hinkal-Demo-App` and `hinkal-ios-sdk`, plus unrelated "hinkali" repos.
- The audited SHA `492ca006` and every report-named fix SHA are absent from `Hinkal-Contracts-Circuits`; a lazy fetch by SHA failed.
- Fix SHAs are kept as named-in-report but are not resolvable. G0639 and G0642 are acknowledged and unfixed (`none-found`).

**Hinkal 2026 (6 rows):**
- The audited commit `306b082` (2026-07-19, "update-contracts", parent `29dd546`) is in GitHub's object store but on **no public ref**. Public `main` is a 6-commit re-upload dated 2026-08-31 (HEAD `61b6839`), so the vuln commit could disappear.
- None of the report-named fix SHAs can be fetched ("not our ref").
- At `306b082` the circuits (`circom/*.circom`, 15 files) and the consumers (`Hinkal.sol`, `HinkalBase.sol`, `EmporiumUpgradeable.sol`, …) are present. On the verifier side there is only `VerifierFacade.sol` plus a `Verifier.sol.mustache` template and `generateVerifier.ts`. The generated Groth16 verifiers (`contracts/verifiers/*.sol`) exist only on main `61b6839`.
- These rows stay PARTIAL: the fix is unresolvable, the vuln commit is unreachable from refs, and the generated verifier is absent.

**zkDCAP (2 rows):**
- The vuln commit is `a0f3800` (zkdcap). The report also names `lcp-solidity@293fac8` as audited repo [1].
- Fixes:
  - DCAP-3: `80cc77a`, whose message matches the title.
  - DCAP-4: `309d1e48d8`, a 10-char report prefix that resolves uniquely to `309d1e48d8e4…`; its message matches the title.
- Both fixes are named in the report, descend from `a0f3800`, and were merged via PR #22 (branch `audit-202503`, merge `d5408a5`).
- Artifacts:
  - circuit: `zkvm/risc0/guest/src/bin/main.rs` and `crates/quote-verifier/src/*.rs`;
  - verifier: `lcp-solidity@293fac8:contracts/DCAPValidator.sol` plus the `lib/risc0-ethereum` submodule;
  - consumer: `lcp-solidity@293fac8:contracts/LCPClientZKDCAPBase.sol`.
- **Judgement call:** the verifier and consumer are in a second repo, and pass 2 has no cross-repo PINNED-PAIR precedent. I counted them because the report names both repos at these commits. Without that, both rows would be PINNED.

**Zilliqa G0360:**
- The real finding ID is `F-2026-19026`; the candidates file has the truncated "F-2026-190x".
- The fix `182ecaa` is named in the report (Hacken: "Fixed in commit 182ecaa"). Its message cites F-2026-19026, it descends from `d52b921`, it was merged via PR #7, and it touches `groth16-prover-min/circuit.circom`, `verifier.sol`, `vk.json` and `circuit.wasm`.
- Circuit and verifier are present at `d52b921`. The consumer `escrow_v1.sol` is in the report scope but **not in this repo** at `d52b921`. It was vendored in later, at `claim-relayer/e2e/src/escrow_v1.sol` by `24dc30e` (2026-09-08, "real zq2 escrow_v1.sol"), so the row stays PARTIAL.
- The upstream zq2 repo was neither guard-checked nor cloned.

## Totals

Of 17 rows: **PINNED-PAIR 2, PINNED 0, PARTIAL 7, none 8** (PRIVATE-OR-MISSING 8; there are no NO-COMMIT or FORBIDDEN rows).

## Things that looked odd

- `git log --name-only` on `182ecaa` in the blobless clone printed no file names, but `git diff-tree --name-only -r` did. Use the latter.
- Hinkal 2026's audited commit exists only as an unreferenced object. If GitHub garbage-collects it, the row drops to NO-COMMIT.
- Zilliqa commit history also has messages citing other Hacken IDs (F-2026-19024, -19085, -19094, -19095, …). I did not open page 2 of the Hacken findings or read those bodies, so they are not judged here. Two look circuit-side and may merit a screen: 19085 (branch `feature/hardened-index-binding`) and 19094 (patches circom-ecdsa `get_dummy_point` and regenerates the verifier).

## Time and hygiene

- About 45 minutes wall-clock.
- At the end, the clones folder `/tmp/claude-1000/acquire3/clones` was deleted with `rm -rf` on that exact path.
- `docs/project-status.md` was not updated: edits were limited to `acquire3/`, `triage/triage_delta.csv` and `triage/SAMPLE_delta.md`.
