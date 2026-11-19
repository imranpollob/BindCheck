# F4 — Bind single-use checks to their rule; test the final verdict wiring

## Research context and authorization (read first)

Authorized **defensive** security research for an academic paper (IEEE
EuroS&P 2027). The oracle is the project's local-only **test harness** (owned
Anvil, synthetic assets, no fork, no public RPC, no broadcast, no forged proofs,
no real addresses).

**Why.** `reports/XR3/GATE.md` blocked the held-out run on **XR3-01**: one
global double-spend flag marks every `single_use` rule violated when a replay
emits any protected mint, even if that rule's own effect never fired. XR3 also
found (XR-09) that the tests cover helper functions but not the final step that
turns a trial's observations into a verdict, so a reverted fix could pass the
suite.

**Branch / worktree:** `sprint/F4`, `$BC/wt-F4`.
**Owns:** `oracle/`, `tests/oracle/`, `reports/F4/`, `results/raw/F4/`.
**Must not edit:** `bindcheck_zk/` (frozen, freeze 3), `findings/`, `paper/`.

## Part A — XR3-01

1. A `single_use_exceeded` violation may be raised for a rule only when **that
   rule's own** matched effects (or its declared authorization key) were
   committed in the honest prelude **and** again in the mutated transaction.
   An effect that matches a different, repeatable rule never triggers it.
2. Derive the authorization key per rule from the effect that rule matched, not
   from the first `single_use` rule in the policy.
3. If an effect cannot be attributed to exactly one rule (ambiguous match), the
   trial is `UNKNOWN / EFFECT_RULE_AMBIGUOUS`. Never resolve ambiguity toward E4.

## Part B — make the final verdict testable (XR-09)

1. Move the decision that maps a trial's recorded observations (tx success,
   verifier-path evidence, state corroboration, view reads, matched effects and
   obligations, policy evaluation, prelude data) to `E4-CONFIRMED` /
   `NOT_CONFIRMED` / `UNKNOWN` into **one pure, exported function** in
   `oracle/evm_runner.cjs`. `runTrial` gathers observations and calls it. Do
   not change any gate's meaning.
2. Add Node-level tests (run from pytest, like the existing helper tests, or as
   a `node --test` file invoked by pytest) that feed that function recorded
   observation objects, with no chain. Include, at minimum, one test per fix that
   **fails if the fix is reverted**:
   - XR-01 fake mint log without state change → not E4;
   - XR-02 missing or mismatched verifier call on the mutated path → not E4;
   - XR-07 underpaid obligation → E4; one effect discharging two obligations → not discharged twice;
   - XR2-01 failed view read → `UNKNOWN`;
   - XR3-01 repeatable effect B replayed with single-use rule A unfired → not E4;
     A itself replayed → E4;
   - honest transaction failed → `UNKNOWN`, never E4.
   For each, show in the report that it fails against the pre-F4 logic (for
   example by temporarily reverting that line in a scratch copy under
   `results/raw/F4/`, never in the tracked file).
3. Add an owned-local manifest `tests/oracle/f4_mixed_rules.manifest.json` with
   a policy that has one `single_use` rule A and one repeatable rule B, where
   `REPLAY` commits only B. Expected after F4: not E4. Your sandbox cannot start
   Anvil (`Operation not permitted`); the reviewer will run the EVM controls
   outside it. Validate the manifest with `_validate_manifest`.

## Checks

- `python3 -m pytest tests/oracle -q` green (the pinned ethers driver is
  copied under `results/raw/F3/.driver/`; do not install over the network).
- `node --check oracle/evm_runner.cjs`; `git diff --check`.

## Output and reporting

`reports/F4/REPORT.md` in the handoff template with AI disclosure: the change,
the revert-proof table for each test, and what the reviewer must run on Anvil.
Do not `git commit` or push. Do **not** call `hc`. End by printing as the final
line in this terminal exactly: `FINAL: F4 DONE` (or `FINAL: F4 BLOCKED:
<reason>`). The orchestrator watches this terminal for that line.
