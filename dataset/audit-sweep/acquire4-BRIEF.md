# Lane pin4: pin code for LIGHT items

Goal: grow the FULL evaluation pool. For every item in `dataset/labels-v1/LABELS-v1.csv` with `tier = LIGHT`, `binding` Y or N, no `dup_of`, and `holdout_flag` not FORBIDDEN, try to pin the audited code.

Priority order:
1. binding Y items;
2. binding N items (they become hard negatives).

## Procedure
Follow `dataset/audit-sweep/ACQUISITION.md`. It is **metadata only**: blobless clones, `git log`/`ls-tree`, and the report's stated commit/tag/scope. No reading of source or diffs. Run `tools/check_holdout.py` before touching any repo.

Find the repo, the audited (vuln) commit, and the fix commit or PR where the report or the repo history names one. Record the acquirability value and confidence exactly as in earlier passes.

## Output
`dataset/audit-sweep/acquire4/acquisition.csv` in the same schema as `acquire3`, plus the column `item_id`, and `acquire4/notes.md`. Write nothing else. No git commits (the orchestrator commits).

## Rules
- Network for git metadata and report pages only. No logins and no contacting projects.
- No `rm`, `nohup` or background jobs. The GitHub API allows only 60 requests per hour without a token, so use web commit URLs for existence checks.
- Use `/home/pollmix/.local/bin/hc`. When done: `hc send t3z "pin4 DONE <n pinned>/<n tried>"`; send blockers early.
