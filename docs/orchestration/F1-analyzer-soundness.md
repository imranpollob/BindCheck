# F1 — Analyzer soundness fixes from the cross-model review (DEV only)

## Research context (read first)

Authorized **defensive** research for an academic paper (IEEE EuroS&P 2027).
Static-analyzer engineering. No network, no live systems.

**Why.** The cross-model review `reports/XR/FINDINGS.md` found paths where
BindCheck can return `VERIFIED_WITHIN_SCOPE` (a SAFE verdict) on an unresolved
fact. The research contract forbids this, and freeze 3 is blocked until they
are fixed. Fix **XR-03, XR-04, XR-05, XR-06** and the P5 half of **XR-09**.

**Branch / worktree:** `sprint/F1`, `$BC/wt-F1`.
**Owns:** `bindcheck_zk/`, `tests/f1/`, `reports/F1/`, `results/raw/F1/`.
**Must not edit:** `oracle/`, `findings/`, `tests/oracle/`, `paper/`.

## Steps

For each finding:

1. **Write the failing negative test first** in `tests/f1/`, reproducing the
   XR counterexample (XR describes each scenario). Confirm it fails on the
   current code, i.e. it shows the wrong SAFE verdict. Record that output.
2. Fix the general cause. The default is fail closed: `UNKNOWN` with a reason
   code. Specifically:
   - **XR-03:** apply the exact-correspondence gate used by P3/P5 to P1 and to
     any P4 result attached to a P1 triple.
   - **XR-04:** propagate a base verifier's guard only when the called method
     resolves to the guarded implementation and no override or bypass exists.
     Fix the existing S2a test that expects unconditional copying.
   - **XR-05:** require `order_complete` and an established circuit public
     count before any P5 safe verdict, including the dynamic-vector branch.
   - **XR-06:** verify the loop's initialisation (0), condition, step (1) and
     pointer progression together. Add negative controls for a loop starting
     at 1 and for a skipped pointer step.
   - **XR-09 (P5 part):** make the multi-verifier test assert the exact
     intended verdict and matched vector.
3. Confirm the positive controls still hold: AZ1 faulty → P1-EXTENT
   VIOLATION; the S2a/S2a2 regressions; the freeze-2 tests.
4. **Check the PP oddity:** `reports/PP/DISCREPANCIES.md` notes that 5
   canonicality-P4 TP warning cards are retained, but 0 have a new verdict of
   VIOLATION. Determine from `reports/S2a/revision1/*` and the analyzer whether
   this is a field-meaning issue in the analysis script or a real regression.
   Report it; fix it only if it is an analyzer bug.
5. Rerun the original 56 DEV rows (as in `reports/S2a2/REPORT.md`,
   `--skip-fetch`). Every changed cell needs a reason. Report any
   VERIFIED→UNKNOWN movement explicitly. Those are the cost of soundness.
6. Full suite (all modules in `reports/S2a2/REPORT.md` plus `tests.s2c.test_extent`
   and `tests.f1`) with
   `BINDCHECK_CIRCOM=$BC/BindCheck/tools/circom-2.1.9/target/release/circom`.
   Then `python3 -m bindcheck_zk.freeze` for the candidate hash. Do not declare a freeze.

No repository, file or card names in analyzer logic.

## Environment limits

No network. Do not `git commit` or push; leave changes in the working tree.

## Completion criteria

- Each of XR-03..06 has a negative test that failed before the fix and passes after.
- Full suite green; DEV delta with reasons; PP P4 question answered.
- `reports/F1/REPORT.md` in the handoff template, with AI disclosure and candidate hash.
- Final line: `F1 DONE` or `F1 BLOCKED: <reason>`.
