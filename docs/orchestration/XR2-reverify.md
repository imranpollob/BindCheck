# XR2 — Re-verify the F1 and F2 soundness fixes

## Research context and authorization (read first)

Authorized **defensive** security research for an academic paper (IEEE
EuroS&P 2027). You are an independent code reviewer, a different model from the
ones that wrote the fixes. This is **read-only review**. The oracle under
review is a local-only test harness (owned Anvil, synthetic assets, no fork, no
public RPC, no broadcast, no forged proofs).

**Why.** A first review (`reports/XR/FINDINGS.md`) found nine issues. Two lanes
then fixed them: F1 on the analyzer (`reports/F1/REPORT.md`), F2 on the oracle
(`reports/F2/REPORT.md`). This lane confirms the fixes actually close the holes
and open no new SAFE-verdict path. This is the gate before freeze 3.

**Branch / worktree:** `sprint/XR2`, `$BC/wt-XR2` (built from current `main`,
which includes F1 and F2). **Owns:** `reports/XR2/` only. **Edit no code.**

## What to check

For each original finding, decide: **CLOSED**, **PARTIAL** (narrowed but a gap
remains), or **OPEN**. Give file:line and a concrete reason.

1. **XR-01** (oracle): is an `E4-CONFIRMED` now impossible from a `Transfer`
   log alone, requiring a real balance/ownership state change? Look for a way a
   mint-shaped effect still reaches E4 without state corroboration.
2. **XR-02** (oracle): does E4 now require evidence that the unchanged verifier
   was called and returned true on the *mutated* path? Can a mutated branch
   that skips verification still reach E4?
3. **XR-03** (analyzer): does P1 (and a P4 result on its triple) now return
   UNKNOWN for a mismatched verifier?
4. **XR-04** (analyzer): is a base verifier's canonicality verdict no longer
   copied across an override or bypass?
5. **XR-05** (analyzer): does P5 now require a complete circuit interface before
   any safe verdict, including the dynamic-vector branch?
6. **XR-06** (analyzer): is the gnark loop recognizer now sound about the first
   and last words (init 0, unit step, exclusive bound)?
7. **XR-07, XR-08, XR-09** (oracle): quantity/multiplicity in obligations; the
   command denylist (can a `prepare` step still reach `--fork-url` or a
   non-loopback URL, e.g. via an env var, a wrapper script, or a redirect?);
   and whether the new oracle gate tests actually fail if the fix is reverted.

Then look for **new** problems the fixes may have introduced:

- Any new `VERIFIED_WITHIN_SCOPE` or `E4-CONFIRMED` path that is now reachable
  on unresolved facts.
- Any case-name or repository branching added to code logic (grep
  `oracle/*.cjs oracle/*.py bindcheck_zk/*.py` for case names; manifests and
  policies under `oracle/cases/` and `tests/oracle/` may name real cases — that
  is data, not logic).
- Tests whose expected value was copied from output.

You may run the suites to confirm a point:
`BINDCHECK_CIRCOM=$BC/BindCheck/tools/circom-2.1.9/target/release/circom
python3 -m unittest tests.f1.test_analyzer_soundness` and
`python3 -m pytest tests/oracle`. Local `anvil` is available; if a check needs a
full oracle run and it is blocked, say so and continue by reading. Change no code.

## Output

`reports/XR2/REVERIFY.md`:

- a table, one row per XR-01..09: status (CLOSED/PARTIAL/OPEN), file:line, reason;
- any new finding, with severity, file:line, failure scenario, confidence;
- a one-line **gate verdict**: `FREEZE-3 CLEAR` (all highs CLOSED, no new high)
  or `FREEZE-3 BLOCKED: <list>`.
- the AI disclosure (tool + model).

## Environment and reporting

No network. Do not `git commit` or push; leave `reports/XR2/` in the working
tree. Do **not** call `hc`. End your session by printing, as the final line in
this terminal, exactly: `FINAL: XR2 DONE` (or `FINAL: XR2 BLOCKED: <reason>`).
The orchestrator watches this terminal for that line.
