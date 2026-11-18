# F2 — Oracle soundness fixes, then S4d obligations

## Research context and authorization (read first)

Authorized **defensive** security research for an academic paper (IEEE
EuroS&P 2027). The oracle is the project's **test harness**. It confirms
static findings on owned, synthetic, local Anvil deployments. Same scope as S4:
no fork (H1 not approved), no public-chain RPC, no broadcast, no forged proofs
or keys, no real addresses.

**Why.** The cross-model review `reports/XR/FINDINGS.md` found that the oracle
can grant `E4-CONFIRMED` on weaker evidence than research contract §8 requires.
Until this is fixed, the paper cites **no** oracle E4 number.

**Branch:** `sprint/F2`, created from `origin/main` in the existing worktree
`$BC/wt-S4` (`git fetch origin && git switch -c sprint/F2 origin/main`).
**Owns:** `oracle/`, `tests/oracle/`, `reports/F2/`, `results/raw/F2/`.
**Must not edit:** `bindcheck_zk/`, `findings/` (read-only), `paper/`.

## Part A — fixes (do these first)

1. **XR-01, effect evidence.** A protected effect counts only if it is
   corroborated by state. Use the before/after balance or ownership on a token
   contract that the policy names, or the prestate/diff trace. An event without
   matching state → the trial is `UNKNOWN` (reason `EFFECT_NOT_STATE_CORROBORATED`),
   never E4.
2. **XR-02, verifier on the mutated path.** E4 requires evidence, from the
   call trace of the **mutated** transaction, that the unchanged verifier was
   called with the mutated arguments and returned true. A standalone verifier
   check of the original proof stays only as an E3 preflight.
3. **XR-07, obligation quantity and multiplicity.** Match obligations by
   value and occurrence (a multiset), or mark quantitative obligations
   `UNKNOWN` if unsupported.
4. **XR-08, preparatory commands.** Either enforce an allowlist or a
   no-network sandbox for `prepare/proof/transform/build`, or narrow the
   safety claim in the reports to the driver path. State which you chose.
5. **XR-09, oracle tests.** Add Python unit tests in `tests/oracle/` for the E4
   gates, plus two owned-local negative controls:
   - a consumer that emits a fake `Transfer` with no state change, which must
     give `UNKNOWN` or `NOT_CONFIRMED`;
   - a consumer whose mutated branch skips verification, which must not give E4.
6. **Re-confirm** ZKredential and RacePass from their manifests with the
   stricter gates, plus the repaired variants and all synthetic controls.
   Report any result that changed, and why.

## Part B — S4d (only after Part A passes)

1. Obligation clauses for the two real cases, only where the source implies a
   required effect. Entitlement only, never a verdict.
2. A manifest for the **AZ1 testbed** (`prototypes/az1/`, faulty and fixed).
   The oracle alone should confirm the undischarged deposit obligation on the
   faulty consumer via `FREE_ARG` on the row count, and give `NOT_CONFIRMED`
   on the fixed one. Record the manifest-writing time in minutes.

## Completion criteria

- XR-01, 02, 07 and 08 addressed, each with a test that would have caught it.
- Both negative controls behave as specified.
- Operator × case matrix before and after the fixes, with reasons for every change.
- AZ1 testbed result from the oracle alone.
- `reports/F2/REPORT.md` in the handoff template with AI disclosure; update
  `docs/project-status.md`; commit and push `sprint/F2`.
- Final line: `F2 DONE` or `F2 BLOCKED: <reason>`.
