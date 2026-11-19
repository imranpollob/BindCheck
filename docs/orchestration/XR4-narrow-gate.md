# XR4 — Narrow review of F4 before the held-out run

## Research context and authorization (read first)

Authorized **defensive** security research for an academic paper (IEEE
EuroS&P 2027). You are an independent reviewer. **Read-only review** of the
oracle, a local-only test harness (owned Anvil, synthetic assets, no fork, no
public RPC, no broadcast, no forged proofs).

**Why.** XR3 (`reports/XR3/GATE.md`) blocked the held-out run (S5) on XR3-01.
F4 (`reports/F4/REPORT.md`) fixed it and moved the final verdict into a pure
`decideTrial` function with revert-proof tests. The F4 report ends with
reviewer-run EVM evidence (your sandbox cannot start Anvil; treat it as
recorded evidence and check it against the code).

## Scope (strict)

Review **only the F4 diff**: `git diff 726938f -- oracle/ tests/oracle/`
(726938f is F4's base). Earlier findings XR-01, XR-02, XR-07, XR2-01 were
CLOSED by XR3; XR-08 is an accepted, documented safety boundary and is **out of
scope**.

Answer only these questions:

1. Is **XR3-01** closed: can a `single_use` violation be raised for a rule whose
   own effect did not fire in both the prelude and the mutated transaction?
   Is the authorization key per rule?
2. Did moving the logic into `decideTrial` change any gate's meaning or
   **order**, or drop a gate, such that a trial that was `UNKNOWN` or
   `NOT_CONFIRMED` before could now be `E4-CONFIRMED`?
3. Does `runTrial` pass every observation `decideTrial` needs, so no gate sees a
   missing value treated as "pass"?
4. Do the new tests fail when their fix is reverted (the report says yes, via
   scratch copies; spot-check two of them)?
5. Any **new** path, introduced by F4, to a false `E4-CONFIRMED` in a held-out
   run where the project writes the manifest from a held-out VIOLATION.

Report a finding only if it can produce a false `E4-CONFIRMED`. Note anything
else in one line under "Out of scope / minor".

Run `python3 -m pytest tests/oracle -q` (the pinned ethers driver is copied
under `results/raw/F3/.driver/`; no network).

## Output and reporting

`reports/XR4/GATE.md`: answers 1–5 with file:line, any finding (severity,
failure scenario, confidence), one gate line `ORACLE CLEAR FOR S5` or
`ORACLE BLOCKED: <list>`, and the AI disclosure.

Do not `git commit` or push. Do **not** call `hc`. End by printing as the final
line in this terminal exactly: `FINAL: XR4 DONE` (or `FINAL: XR4 BLOCKED:
<reason>`).
