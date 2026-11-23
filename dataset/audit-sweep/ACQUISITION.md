# Acquisition protocol: pinning vulnerable and fixed commits for audit candidates

**Version:** v1. **Date:** 2026-11-22. **Owner:** the orchestrator. **Author approval:** "is 3 can be done after this then do it" (2026-11-22).

## Purpose

For each candidate in `merged/candidates.csv` (KEEP and BORDERLINE), establish what the benchmark needs:

- the **vulnerable commit**;
- the **fix commit**;
- the **paths of the circuit, verifier and consumer** at the vulnerable commit;
- **build hints**.

Goal: upgrade acquirability (`PARTIAL`/`NO-COMMIT` → `PINNED`) wherever the public record allows. This is still pre-labeling metadata work.

## The contamination boundary (important)

Some of these candidates will later be put in the **reserved** set. Nobody may study their code before the tool is frozen, so the work stays at the **metadata** level:

**Allowed:**
- commit metadata: SHA, date, message, author;
- PR and issue titles and descriptions;
- the **list of file names** a commit changes;
- the file tree at a commit;
- the repository README and build files, for build hints only.

**Not allowed:**
- reading diff contents;
- reading circuit or contract source;
- running anything.

If confirming a fix would require reading the diff, record the fix as `candidate (unconfirmed)` with the evidence you have, e.g. "commit message cites finding 3.5; touches `Darkpool.sol`".

**Allowed tools:**
- `git clone --filter=blob:none --no-checkout` (history only, no file contents), followed by `git log`, `git log --name-only` and `git ls-tree`. Never `git checkout`, `git show <file>`, or `git diff -p`. Clones go to `/tmp/claude-1000/acquire/clones/` and are deleted at the end with `rm -rf` on that exact path.
- `curl` against commit, PR and issue web pages and `raw.githubusercontent.com` for README and build manifests (`package.json`, `foundry.toml`, `hardhat.config.*`, `Nargo.toml`, `Cargo.toml`, circom version files) only.
- Run the held-out guard (`tools/check_holdout.py`) as its own command and read its result before touching any repository.
- No more than ~10 GitHub API calls per hour; the blobless clone makes most API calls unnecessary.

## How to find the fix

In order of preference:

1. The report names the fix commit or PR.
2. A PR or commit message references the finding ID or title.
3. A commit after the audited commit that changes the file the report names, with a message matching the issue.
4. The project's "audit fixes" branch or tag.

Record which method you used.

## How to find the vulnerable commit

1. The report's audited commit.
2. Otherwise, the parent of the fix commit.

## Output: `acquire/acquisition.csv`

```
group_id,finding_key,decision,repo,vuln_commit,vuln_commit_source,vuln_commit_http,fix_commit,fix_commit_source,fix_confidence,fix_commit_http,circuit_paths,verifier_paths,consumer_paths,circuit_lang,proof_system,build_system,build_hints,holdout_flag,acquirability_before,acquirability_after,notes
```

| Field | Values |
|---|---|
| `fix_confidence` | `named-in-report`, `message-cites-finding`, `file-and-message-match`, `candidate (unconfirmed)`, or `none-found` |
| `acquirability_after` | The protocol §7 vocabulary, plus `PINNED-PAIR` when both the vulnerable and fixed commits exist and all three artifacts are present at the vulnerable commit |

Also write:
- `acquire/progress.md`;
- `acquire/notes.md`, with method notes, per-candidate failures, and the time taken.

Process `PARTIAL`, `NO-COMMIT` and `PRIVATE-OR-MISSING` candidates first, then confirm the `PINNED` ones with a fix commit. For `PRIVATE` repositories, do one quick check for a public mirror or a later open-sourcing, then record the result and move on.
