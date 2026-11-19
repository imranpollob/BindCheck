# XR3 — Final oracle gate before the held-out run

## Research context and authorization (read first)

Authorized **defensive** security research for an academic paper (IEEE
EuroS&P 2027). You are an independent code reviewer. This is **read-only
review** of the oracle, a local-only test harness (owned Anvil, synthetic
assets, no fork, no public RPC, no broadcast, no forged proofs).

**Why.** The held-out v3 run (S5) will use the oracle to confirm every analyzer
VIOLATION, and the paper will cite those confirmations. Two reviews found
false-E4 paths (`reports/XR/FINDINGS.md`, `reports/XR2/REVERIFY.md`). F2 and
F3 fixed them (`reports/F2/REPORT.md`, `reports/F3/REPORT.md`). F3's report
ends with a reviewer-run EVM section: each XR2 control gives a false E4 on the
base oracle and `UNKNOWN` on F3, and no real or synthetic E4 changed. Your
sandbox cannot start Anvil, so treat that section as recorded evidence and
check it against the code.

The analyzer is frozen (`docs/FREEZE-3.md`) and out of scope here.

**Branch / worktree:** `sprint/XR3`, `$BC/wt-XR3`. **Owns:** `reports/XR3/`
only. **Edit no code.**

## Check

1. For XR-01, XR-02, XR-07, XR-08, XR-09 and XR2-01: **CLOSED**, **PARTIAL**
   or **OPEN**, with file:line and reason. For anything still PARTIAL, say
   whether it can produce a false `E4-CONFIRMED` in a held-out run (where the
   manifest is written by the project from a held-out VIOLATION), or only
   affects a stated safety boundary.
2. Any **new** path to a false `E4-CONFIRMED`: effects without state, verifier
   acceptance not tied to the mutated call, obligations miscounted, failed reads
   treated as values, honest-transaction failure ignored, trial state leaking
   between operators.
3. Whether the gate tests in `tests/oracle/test_oracle_gates.py` would fail if
   each fix were reverted. Run `python3 -m pytest tests/oracle -q` (no network).
4. Case-name or repository branching in `oracle/*.cjs` and `oracle/*.py`
   (manifests and policies may name cases; that is data).

## Output and reporting

`reports/XR3/GATE.md`: the status table, new findings (severity, file:line,
failure scenario, confidence), and one gate line:
`ORACLE CLEAR FOR S5` or `ORACLE BLOCKED: <list>`. Include the AI disclosure.

Do not `git commit` or push. Do **not** call `hc`. End by printing as the final
line in this terminal exactly: `FINAL: XR3 DONE` (or `FINAL: XR3 BLOCKED:
<reason>`). The orchestrator watches this terminal for that line.
