# Lane-X report — what blocks S&P, and two routes tested

Date: 2026-10-27. Exploratory development evidence. No prior report,
protocol, or verdict is changed. Raw outputs: `results/raw/X-01/`,
`results/raw/X-02/` (ignored). Log: [LOG.md](LOG.md).

## 1. Acceptance blockers, ranked

1. **No automated discovery (gate a).** Every obligation in the project
   (O1/O2, G1–G5) is planner-written. Contract §11(a) fails outright.
   This is the top blocker: without it there is no capability claim.
2. **Producer-side scalability (gates a/b).** Full-producer joint queries
   time out at 300 s (D1P-14D, D1P-17); only consumer-only or
   producer-dropped queries resolve. Any discovery pipeline dies at
   concretization unless it routes around monolithic ACIR solving.
3. **No baselines run (gate c).** Preregistered (paper/baselines.md),
   never executed. An S&P reviewer cannot price the contribution.
4. **No held-out family (gate d).** None reserved; taxonomy design is
   frozen but the custodian draw has not happened. Transfer is
   untestable until a human does the private draw (protocol §3).
5. **Novelty exposure.** CIVER/CCC-Check/Coda comparisons are still
   [TODO-VERIFY]. If a circuit-only tool expresses "public word
   unconstrained", the joint-analysis novelty shrinks to validation.

## 2. What I tried

### X1 — Does Noir's own checker already see these patterns? (blocker 5)

Pinned nargo 1.0.0-beta.22 (sha256 `37f7d55d…`) on three synthetic
arithmetic-only Noir programs (`results/raw/X-01/`): a Payy-like tail
(public words ≥ count unconstrained), an M-DOM-like silo (public
configured address unused, private prover address bound), an honest
control, plus Brillig sanity controls. Commands and logs in LOG.md.

Result: tail — complete silence, exit 0. Silo — only a generic
`unused variable` lint. Brillig control — the under-constrained check
does fire ("Brillig function call isn't properly covered"), proving the
check was active. So at the pinned version, neither defect pattern is
detected as a constrainedness problem: public inputs sit outside the
check's scope, and a fully-used private substitute is invisible to it.
This supports the novelty gap; it does not prove it (synthetic stand-ins,
not the real artifacts — that run belongs to the main lanes' D1P-22).

### X2 — Generic P/O/E-template obligation derivation (blocker 1)

`prototypes/x2/derive_obligations.py` derives obligations from the
D1P-18 extracted relation using three IR-shape rules only (committed
mint = effect; `select(storage, symbol)` guard = admission check;
candidate = success ∧ amount≠0 ∧ guarded word ∉ admitted set). Word
positions are parsed from the relation's own verifier-boundary
expression. Zero case-specific input.

Result: the derivation mechanically recovers the admission inventory
per variant — pinned {giga, local, nullifier}, M-SRC missing local —
so the injected mutation is visible in derived output alone. Solving
the derived obligations (cvc5 1.4.2, producer dropped, S_SRC admitted
state): pinned root obligations UNSAT in 0.013–0.162 s; the identical
obligations applied unchanged to M-SRC return SAT in 5.0–17.1 s for
the local root, UNSAT for giga. The template rediscovers the D1P-19
injected-mutation shape with no planner text.

Two honest limits. (i) My template initially mishandled nullifiers:
single-use is must-not-be-in, replay needs two transitions; excluded
with reason, polarity handling is still owed. (ii) Producer-dropped
SAT is an abstract candidate — not E2, not a verdict. Concretization
exists manually for this shape (D1P-19: attacker tree → real proof →
E4 on the mutant); automating it is not done here.

## 3. Gate state after this lane

| Gate | State | Evidence level |
|---|---|---|
| (a) automated discovery | Partial candidate route shown | abstract candidate (below E2) |
| (b) automated E4 validation | Done on development mutants (X-AV v1+v1.1, below) | E4 fresh, zero manual steps (WarpToad); E2 mock-scoped (Payy) |
| (c) baselines | Not run; X1 gives one preregistered expectation | E1-scope probe, synthetic |
| (d) held-out transfer | Blocked on human custodian draw | — |

Follow-up lane work after X1/X2 (own docs, same worktree/rules):
deliverables are [BENCHMARK](BENCHMARK.md) (30 compiling mutants),
[AUTO-VALIDATE](AUTO-VALIDATE.md) v1 (20/20 D1P-31: 7 fresh E4 zero
manual steps, 1 E4-preserved, 5 E3-contained, 7 Payy E1) and v1.1
(53/53 D1P-34: 8 E4 + 1 E4-preserved + 4 E3 on WarpToad incl. new WT-S06;
6 E2 mock-verifier-scoped on Payy S01–S04 with unauthorized effects on
state; 2 executed-and-contained; 32 E1 owing Rust-stack inner proofs).
Gate (b) is met on exposed development mutants only — no held-out claim,
D1 verdict stays UNKNOWN. A cross-contamination misgrade (Payy rows run
down the WarpToad path, bogus E3s) was caught in audit and corrected
before reporting; see AUTO-VALIDATE Limits.

Manual inputs in X2, counted: admitted-state values, environment chain
id, the shared effect-model table inside the extracted relation. No
role map, no defect-specific rule, no expected verdict encoded.

## 4. Hand-off items for the main lanes

- **H1 (freeze):** adopt the X2 derivation as the D1P-21C candidate
  generator for O2-class obligations; freeze its three rules and rerun
  under campaign accounting. Files: `prototypes/x2/derive_obligations.py`,
  `prototypes/x2/run_x2.py`, `prototypes/x2/run_x2_cross.py`.
- **H2 (protocol change):** derivation must be polarity-aware
  (must-be-in vs must-not-be-in admission). Single-use obligations need
  a declared two-transition scope or must be emitted as UNKNOWN-scope.
- **H3 (concretization):** wire derived candidates to the existing
  D1P-19 concretization route (witness/tree construction → `nargo
  execute` → real proof → consumer replay) with per-candidate budgets.
  That wire, not more solver tuning, is the shortest path to (b).
- **H4 (baselines):** add X1's expectation to D1P-22: pinned nargo
  checks are predicted silent on the Payy tail and lint-only on M-DOM.
  Confirm on real artifacts; a contradiction revises blocker 5.

## 5. What only humans can do

- Custodian private family draw + attestation (taxonomy protocol §3)
  before any held-out claim; no agent may substitute.
- Staff two annotators + one adjudicator for the taxonomy pilot.
- Advisor decision: narrow the paper to capability-on-development-cases
  if the held-out draw cannot complete before submission.

## 6. Disagreements with the current plan

- The frozen O1/O2 campaign spends its budget on planner-written
  obligations. Even a perfect campaign result cannot satisfy gate (a).
  Derivation (X2-class) should be frozen first; the campaign should
  consume derived obligations, with planner obligations kept only as a
  same-policy baseline arm.
- Producer monolithic solving has three consecutive null results
  (D1P-07/10/14D lineage). Further encoding tuning has poor expected
  value versus candidate-first concretization (H3), where the expensive
  relation is only ever checked on concrete witnesses.
