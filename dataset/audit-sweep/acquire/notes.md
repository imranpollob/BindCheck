# Acquisition notes

## Method
- Held-out guard (`tools/check_holdout.py`) run on all named repos first, as its own command: one FORBIDDEN, `tangle-network/protocol-solidity` (G0237). It was not touched. The old `vuln_commit_http=200` entry for it was written by an earlier agent before the guard was read, and I did not use it.
- 45 blobless clones (`git clone --filter=blob:none --no-checkout`) in `/tmp/claude-1000/acquire/clones/`. Used only `git log` (metadata), `git log --name-only --format=` (file names), `git ls-tree -r --name-only` and `git rev-parse`. No checkout, no `git show`, no patch. No source or diff content was read.
- GitHub API calls: 0. `git ls-remote` was run on 4 guessed darkpool mirror names (all absent).
- Fix search used commit messages after the vuln commit (`git log --grep`) and, for candidates, the names of the files they touch. Messages that only said "audit fixes" are `candidate (unconfirmed)`.
- Circuit, verifier and consumer paths are auto-detected by file-name heuristics. These are weak for Go and Rust circuits. Treat `PARTIAL` as "heuristics did not find all three", not as proof of absence. `circuit_paths` was forced empty for consumer-only repos where the heuristic matched unrelated prover/client code: G0088, G0145, G0147, G0151, G0152.
- `PINNED-PAIR` requires the vuln commit and fix commit to resolve in the clone, all three artifacts present at the vuln commit, and a fix confidence other than `candidate (unconfirmed)` or `none-found`.
- The `vuln_commit_http` and `fix_commit_http` columns say "resolved in blobless clone" or "not resolvable", not HTTP status codes. Git resolution replaced web checks.

## Per-candidate failures and open issues
- Named fix SHAs absent from public history (force-push, republication or another repo): G0004 (1800e7c8), G0007 (05e2b9f9), G0093-95 (privacy-boost, repo republished with squashed history), G0108, G0233, G0236, G0242/G0243, G0270/G0271, G0073/G0074, G0080/G0081. These stay `named-in-report` or `candidate` with no pair.
- Private or missing repos: portalgateme darkpool (G0029-G0045, 14 groups, no public mirror found), succinctlabs/telepathy (G0055, G0084; the SHA is also absent from telepathy-contracts), malda-zkcoprocessor (G0077; the renamed `malda-zk-coprocessor` exists but was not mapped), EYBlockchain/nightfall (G0211; `nightfall_3` exists, last commit 2024, not mapped), and DOP, Intmax, Worldcoin and other repos the report never names.
- Repos inferred by me (sp1-contract-call for G0078, Unirep for G0085): the report does not name them. Authors should check the attribution.
- Sherlock Morph (G0181): the vuln commit sits in the sherlock-audit fork and could not be fetched. The parent of the fix commit in `morph-l2/morph` is used instead.
- Unmapped or skipped for lack of a repo or SHA: G0098, G0102 (no audited SHA), G0111/G0112 (PR only), G0114, G0121, G0148-G0150, G0154-G0157, G0162, G0203-G0205, G0207, G0257, G0323-G0325 (advisories list versions only; tag lookup not done).
- Not done for lack of time: PR-merge lookups for vlayer PRs 1891/1950 and renegade/zkOS PRs; checking whether the later "audited publish" commits in privacy-boost correspond to the findings.
- Most `none-found` rows should be revisited by someone allowed to read diffs, once the reserved split is frozen.

## Time
About 1.5 hours wall-clock.
