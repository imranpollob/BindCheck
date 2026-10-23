# D1 workspace and preservation

Use `/home/pollmix/Coding/BindCheck-d1`, branch `research/d1`. It is a Git worktree of `/home/pollmix/Coding/BindCheck` at base commit `41093d1905e44af347e1d39cd6718728d4157c77`. Worktrees share object/history and administrative worktree metadata, but have separate indexes and working files. This is not a separate repository or an independent backup of Git history.

## Carried work

The source checkout had exactly three staged changes: `README.md`, `docs/research-and-work-summary.md`, and `scripts/t22_v5_audit.py`. Their binary staged patch was applied to the new worktree with `git apply --index`. The D1 documentation edits are deliberately unstaged. Consequently `README.md` is both staged and modified in the new worktree: the staged version is the user's baseline; the unstaged version adds D1. No commit, stash, push, or reset was performed.

The original checkout's HEAD, working files, index bytes, staged/unstaged patches, and status were checked against the captured baseline. Shared Git worktree metadata necessarily changed when the worktree was registered. Filesystem access times and administrative metadata are not preservation claims.

## Evidence locations

- [baseline.json](../../metadata/d1/baseline.json): source/worktree identity, index and patch hashes, inventory hash, counts.
- [historical-evidence.json](../../metadata/d1/historical-evidence.json): hashes for historical reports and raw artifacts.
- `results/raw/D1-00/source-inventory.json`: complete original file/symlink inventory excluding `.git` entries, including ignored tools and build artifacts.
- `results/raw/D1-00/baseline-results/`: independent copies of all 403 original raw-evidence files (123,791,761 regular-file bytes). Never use this as an experiment output directory.
- `results/raw/D1-00/{staged.patch,unstaged.patch,original.index}`: captured local state. Do not copy the saved index over a live index.
- [original contract](../history/research-contract-2026-10-20.md): exact pre-D1 contract, controlling interpretation of historical results.
- [literature-inputs.json](../../metadata/d1/literature-inputs.json): exact source hashes for the proposal, figures, and archival planning inputs.

Raw files are ignored, preserved locally, and not included by an ordinary Git clone or commit. Preserve the whole D1-00 raw directory when backing up this task. Toolchains and build caches remain in the original checkout and were inventoried but not copied. The new worktree is not yet a validated runnable experiment environment. Provision pinned dependencies into the new worktree before execution; do not modify the original tools or make new runs depend on mutable original caches.

## Continuing work

Read the [contract](../research-contract.md), [README](../../README.md), and [roadmap](roadmap.md). Keep historical scripts and reports frozen; place new logs in `results/raw/D1-xx/` and new reports in `reports/D1-xx.md`. Some legacy runners clear their output directory, so adapt output paths before any reuse. The D1-00 backup is archival input, never a rerun target.

To audit this preparation again while the baseline remains unchanged:

```sh
cd /home/pollmix/Coding/BindCheck-d1
python3 scripts/d1_verify_workspace.py
```

The verifier reads the original checkout without refreshing its Git index and emits JSON on stdout. It does not restore, stage, rewrite, or repair anything. It is a D1-00 checkpoint verifier, not a perpetual CI test: subsequent authorized source/index/code changes can legitimately make its baseline comparisons fail. Preserve this run's result instead of updating the baseline to hide such changes.
