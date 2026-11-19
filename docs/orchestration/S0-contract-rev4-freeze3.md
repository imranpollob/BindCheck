# S0 — Research contract revision 4 and freeze-3 preparation

## Context (read first)

Academic paper (IEEE EuroS&P 2027) on BindCheck. Before the held-out v3 run,
the analyzer is frozen and the research contract states exactly what the
frozen tool claims. This is documentation and bookkeeping. **Do not change any
code under `bindcheck_zk/`.**

The analyzer passed independent re-review (`reports/XR2/REVERIFY.md`: XR-03..06
CLOSED, no new SAFE path). Its content hash on `main` is
`753c6e2a0f3f75255eb2fdc354402f3ef7aac1541206b0794a9d09cd7d485315`.

**Branch / worktree:** `sprint/S0`, `$BC/wt-S0`.
**Owns:** `docs/research-contract.md`, `docs/FREEZE-3.md`, `reports/S0/`.
**Must not edit:** code, other reports, `paper/`.

## Steps

1. **Verify the hash.** Run `python3 -m bindcheck_zk.freeze` and confirm it
   prints the hash above. If it differs, stop and report `BLOCKED`.
2. **Full test suite** with
   `BINDCHECK_CIRCOM=$BC/BindCheck/tools/circom-2.1.9/target/release/circom`:
   the modules listed in `reports/F1/REPORT.md` (freeze-2 modules, s2a, s2a2,
   s2c, f1). Record the count and exit code. It must be green.
3. **Contract revision 4** (`docs/research-contract.md`). Keep revision 3 text
   intact where unchanged and add a dated revision-4 section and changelog.
   It must state, in contract language:
   - **Semantic exclusion rule**: the configured directory/file classes
     (test, script, ctf, writeup, tutorial, example, `.t.sol`, `.s.sol`;
     exact list from `bindcheck_zk/config.json`) are out of scope; excluded
     files are counted in coverage and never yield `VERIFIED_WITHIN_SCOPE`.
   - **P1-EXTENT** (extent binding, direction b): what it checks, its fail-closed
     reasons, and that it was designed on the AZ1 development fixture.
   - **Verifier correspondence**: a safe verdict requires exact
     receiver/implementation correspondence (F1, XR-03/04).
   - **Circuit interface completeness**: P5 safe verdicts require a complete
     flattened public order (XR-05); user-defined Noir composites stay UNKNOWN.
   - **Honk/UltraHonk layout**: arity recovery including pairing-point and
     aggregation reservations (S2a). State that a Honk canonicality rule is
     **not** in this freeze (S2b deferred).
   - **Scope of the held-out v3 run**: the 1,106 reserved families, run once
     with the frozen tool, with no tuning on held-out results.
   - **Oracle**: E4 confirmation is a separate tool, not part of the frozen
     analyzer. Oracle results count only after the oracle passes its own
     re-review (F3/XR3).
4. **`docs/FREEZE-3.md`** mirroring `docs/FREEZE-2.md`: the hash block, what it
   supersedes, a contents list citing the controlling reports (S2a, S2a2, S2c,
   F1, XR, XR2), the DEV numbers labelled "development data, not held-out",
   the test command and count, and the toolchain pins.
5. `reports/S0/REPORT.md` in the handoff template with AI disclosure.

**Do not create the git tag.** The reviewer creates and pushes
`freeze-3` after reading this lane's output.

## Reporting

Do not `git commit` or push; leave changes in the working tree. Do **not** call
`hc`. End by printing as the final line in this terminal exactly:
`FINAL: S0 DONE` (or `FINAL: S0 BLOCKED: <reason>`). The orchestrator watches
this terminal for that line.
