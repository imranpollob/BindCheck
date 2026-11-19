# S5H — Reserve-draw entry point for the held-out v3 run (code only; no network; do NOT run the evaluation)

## Research context and authorization (read first)

Authorized defensive research for an academic paper (IEEE EuroS&P 2027). This
task changes the evaluation harness so that the one-shot held-out v3 run uses
the approved reserve population. The run itself is NOT part of this task. Do not
clone, fetch, prebuild, analyze or open any repository. Work offline on code
and tests only.

**Read first:** `reports/S5/PREREG.md`, `reports/S5/README.md`,
`reports/S5/reserve-manifest.csv` (1,105 units), `docs/orchestration/S5-PROTOCOL-DRAFT.md`,
`eval/common.py` (`select_families`, `check_eval_gate`), `eval/run_heldout.py`,
`eval/prebuild_heldout.py`, `scripts/check_holdout.py`.

**Branch / worktree:** `sprint/S5H`, `$BC/wt-S5H` (already created from `origin/main`).
**Owns:** `eval/`, `scripts/check_holdout.py` (only the authorization hook below),
`tests/s5h/`, `reports/S5H/`.
**Must not edit:** `bindcheck_zk/` (frozen), `oracle/`, `dataset/`, `reports/heldout/`
(historical), `reports/S5/PREREG.md` and `reports/S5/reserve-manifest.csv` (pinned).

## Problem

The existing EVAL path (`select_families` by `v2_family_id`; `check_eval_gate`
requires `bindcheck-zk-frozen-*` tags and the original plan hash) cannot
correctly run the reserve. It would re-select spent families. Add a separate,
explicit reserve entry point and leave the historical path unchanged.

## Required changes

1. **`eval/reserve.py` (new):**
   - Load `reports/S5/reserve-manifest.csv`. Refuse unless its SHA-256 equals
     `b1752eede4ccabaf5dea45d827fbdd0c388346349a51129b2ace125322374278`.
   - Refuse unless it has exactly 1,105 rows, all (repository, commit) pairs
     distinct, and none of them in `reports/heldout/selected-families.csv`
     (compare by repository and commit). Refuse `warptoad/warp-toad`.
   - Produce a unit list with `unit_id`, stratum (`maturity`), and pinned commit.
     Emit the 390-stratum count and check it.
2. **Gate for the reserve (`eval/reserve.py`):** refuse unless
   (a) `git rev-parse` of the freeze-3 tag `freeze-3` equals `HEAD`, (b) the
   analyzer content hash from `python3 -m bindcheck_zk.freeze` equals
   `753c6e2a0f3f75255eb2fdc354402f3ef7aac1541206b0794a9d09cd7d485315`, and
   (c) `reports/S5/AUTHORIZATION.json` exists, its `manifest_sha256` matches the
   value above, and its `approved_by` and `approved_on` fields are non-empty.
   Do NOT reuse or weaken `check_eval_gate`; do not add a bypass to it.
3. **Authorized guard path:** `scripts/check_holdout.py` keeps refusing reserved
   families by default. Add a single, narrow exception: it allows a repository
   only when called from `eval/reserve.py` with a valid authorization record
   (as in step 2) and only for a repository on the reserve manifest. Every other
   call still refuses. Show by test that the default refusal is unchanged.
4. **Prebuild path:** `eval/prebuild_heldout.py` has a hard-coded macOS circom
   path and the spent sample. Add a `--sample` and `--circom` interface (no
   default macOS path) so that the reserve can use the Linux toolchain at
   `$BC/BindCheck/tools/circom-2.1.9/target/release/circom`. Leave the existing
   defaults intact for the historical record.
5. **Output:** the reserve writes to `results/raw/S5/` only, and its funnel uses
   the statuses in `PREREG.md` (ACQUISITION_FAILED, BUILD_FAILED,
   HARNESS_TIMEOUT, UNSUPPORTED, analyzable). Every one of the 1,105 units must
   appear in the output, with no unit silently dropped.

## Tests (`tests/s5h/`, offline)

- manifest hash mismatch refused; row count != 1105 refused;
- a unit that matches a spent (repository, commit) refused; WarpToad refused;
- missing or inconsistent `AUTHORIZATION.json` refused; wrong tag or hash refused;
- guard: default call for a reserved repository still FORBIDDEN; the reserve
  path allowed only for a manifest repository with a valid record; a non-manifest
  repository still refused even with a record;
- prebuild CLI refuses to run without an explicit `--circom`;
- every unit yields exactly one funnel status (no drops), using a fake runner.

Run: `python3 -m unittest discover -s tests/s5h -v` and the existing
`tests/` modules listed in `reports/F1/REPORT.md` (they must stay green).

## Do not

- Do not create `reports/S5/AUTHORIZATION.json`. Only the author can approve it.
- Do not open, clone or fetch any reserve repository.
- Do not commit. Leave changes in the working tree.

## Reporting

`reports/S5H/REPORT.md`: change list with file:line, test output, the revert
proof (show that each refusal test fails when its check is removed), and any
ambiguity you found in the protocol.
End your session by printing as the final line in this terminal exactly
`FINAL: S5H DONE` (or `FINAL: S5H BLOCKED: <reason>`). Do not call `hc`.
