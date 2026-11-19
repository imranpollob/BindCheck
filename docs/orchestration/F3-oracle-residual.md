# F3 — Close the residual oracle false-E4 paths

## Research context and authorization (read first)

Authorized **defensive** security research for an academic paper (IEEE
EuroS&P 2027). The oracle is the project's local-only **test harness** that
confirms static findings on owned, synthetic Anvil deployments. Scope as in S4
and F2: no fork (H1 not approved), no public-chain RPC, no broadcast, no forged
proofs or keys, no real addresses.

**Why.** The re-review `reports/XR2/REVERIFY.md` found that three paths can
still yield a false `E4-CONFIRMED`. The held-out run (S5) will use the oracle
to confirm every VIOLATION, so these must close first.

**Branch / worktree:** `sprint/F3`, `$BC/wt-F3`.
**Owns:** `oracle/`, `tests/oracle/`, `reports/F3/`, `results/raw/F3/`.
**Must not edit:** `bindcheck_zk/` (the analyzer is being frozen in parallel),
`findings/`, `paper/`.

## Fixes

1. **XR-01 (ERC-721).** Require a pre/post ownership change: the token is not
   owned by the recipient before the transaction and is owned after it (and a
   burn/mint direction consistent with the log). Ownership only after the
   transaction is not enough. Otherwise `UNKNOWN / EFFECT_NOT_STATE_CORROBORATED`.
2. **XR-02 (verifier binding).** E4 requires that the verifier call on the
   mutated path is the one the consumer uses for this check, and that its
   **input** carries the mutated values the operator changed (for example the
   altered public input for `ALIAS`, the same proof bytes). Accepting any
   declared verifier that returned true is not enough. If several checks are
   required, each must be shown. Otherwise `UNKNOWN / VERIFIER_PATH_NOT_ESTABLISHED`.
3. **XR2-01 (view baselines).** A view read that fails (reverts or errors)
   before or after the transaction must make that effect or obligation
   `UNKNOWN / VIEW_READ_FAILED`. Never substitute `0`.
4. **XR-07/08/09 residuals.** Read the PARTIAL notes in `REVERIFY.md`. Close
   what you can in the same style. Where a full fix is out of scope (e.g. a
   network sandbox for `prepare`), narrow the stated claim in `oracle/README.md`
   and say so in the report.

## Tests

For each of XR-01, XR-02 and XR2-01, add an owned-local negative control that
reproduces the XR2 scenario and **fails on the current code** (gives E4), then
passes after the fix (UNKNOWN or NOT_CONFIRMED). Record both runs. Add unit
tests in `tests/oracle/test_oracle_gates.py` that would fail if the fix were
reverted.

Then re-run every existing case with the stricter gates: ZKredential, RacePass
(original and repaired), the synthetic controls, the AZ1 testbed. Report any
verdict that changed, with the reason. `python3 -m pytest tests/oracle` must be
green; if a helper needs a package that is absent, report it instead of
installing over the network.

## Output and reporting

`reports/F3/REPORT.md` in the handoff template with AI disclosure, the
before/after control table, and the re-confirmation matrix. Do not `git
commit` or push (the sandbox cannot); leave changes in the working tree. Do
**not** call `hc`. End by printing as the final line in this terminal exactly:
`FINAL: F3 DONE` (or `FINAL: F3 BLOCKED: <reason>`). The orchestrator watches
this terminal for that line.
