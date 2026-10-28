# Lane-X experiment log

Exploratory development evidence only. Nothing here relabels any prior
report or verdict. Verdict vocabulary: VIOLATION / VERIFIED_WITHIN_SCOPE /
UNKNOWN; timeouts and unsupported features are UNKNOWN.

## 2026-10-27 — Orientation

Read (in AGENTS.md order): research contract rev.2, README, project-status,
paper/draft.md, paper/baselines.md, D1P-B02, D1P-19 campaign draft,
D1P-20/21B extraction records, D1P-21A, taxonomy protocol v0.2.0.
Verified against git: lane-x-muse at e64adfa, clean tree.

Confirmed state (not taken on trust):
- Consumer relation is extracted (D1P-18 AST -> D1P-20/21B SMT) for the
  WarpToad `mint` fragment; variant-general over path shape (21 vs 22).
- Producer is decoded ACIR with Poseidon2 havoc (L0); full-producer joint
  queries time out (D1P-14D Q1/Q2 300 s; D1P-17). Consumer-only resolves.
- O1/O2 obligations and G1-G5 policy are planner/manual. No automated
  discovery exists anywhere in the tree (grep: no O1/O2 in src/).
- Baselines preregistered, never run. No held-out family. Paper draft is
  a skeleton whose every claim cell is [TODO-EVIDENCE].

Decision: do not duplicate the main lanes' frozen O1/O2 campaign
(D1P-21C) or baselines (D1P-22). Attack two different weak points:
(X1) whether the cheapest generic baseline (Noir's own checks) already
sees these defect patterns — a novelty-critical question an S&P reviewer
will ask first; (X2) whether obligations can be derived from a generic
P/O/E template over extracted artifacts instead of planner text —
gate (a).

## 2026-10-27 — X1: Noir beta.22 default checks on synthetic patterns

Setup: pinned nargo 1.0.0-beta.22 (sha256 37f7d55d..., from D1P-13 tools),
three synthetic arithmetic-only Noir programs under results/raw/X-01/:
tail (public words >= count unconstrained), silo (public configured
address unused; private prover address bound instead), ok (honest
control), disc (sanity controls for check activation).
Commands: `nargo check` and `nargo compile` per program, nice -n 19.
Load average at start recorded in results/raw/X-01/logs/load.txt.

Observed:
- tail: exit 0, complete silence from both check and compile. The
  under-constrained check does not flag unconstrained public inputs.
- silo: exit 0, only a generic `unused variable configured` lint. No
  under-constrained finding. (In a real M-DOM source the same lint would
  fire; it localizes an unused public word but states no mismatch.)
- ok: exit 0, silent.
- disc control 3 (Brillig result returned unconstrained): the check IS
  active — "Brillig function call isn't properly covered by a manual
  constraint" (still exit 0; it is a diagnostic, not an error).

Conclusion: Noir's built-in checks, at the pinned version, do not detect
either defect pattern as a constrainedness problem. This supports (does
not prove) the novelty gap, and gives D1P-22 a cheap preregistered
expectation to confirm on the real artifacts. Limits: synthetic
arithmetic stand-ins for hash bindings; real WarpToad/Payy runs belong
to the main lanes' baseline task. Raw logs: results/raw/X-01/logs/.

## 2026-10-27 — X2: generic-template obligation derivation

Built prototypes/x2/derive_obligations.py: three IR-shape rules only
(R1 committed mint = protected effect; R2 select(storage, symbol) guard =
admission check; R3 candidate = success AND amount != 0 AND guarded word
outside admitted set). Word positions parsed from the relation's own
verifier-boundary expression. No application names, no planner text.

Observed (results/raw/X-02/derived-{pinned,msrc}.json):
- Pinned: admission inventory = {gigaRootHistory, localRootHistory,
  nullifiers}; M-SRC inventory lacks localRootHistory — the injected
  mutation is mechanically visible in derived output alone.
- 66 raw obligations dedupe to 9 unique (pinned) / 6 (M-SRC).

Solver (prototypes/x2/run_x2.py, run_x2_cross.py; cvc5 1.4.2 pinned,
producer dropped, S_SRC admitted roots from D1P-19 canonical states,
120 s cap, nice -n 19, load ~3.2 recorded):
- Pinned root-admission obligations: UNSAT in 0.013-0.162 s.
- Same derived obligations applied unchanged to M-SRC: SAT in
  5.0-17.1 s (local-root), UNSAT for giga-root. Exactly the D1P-19
  injected-mutation shape, rediscovered from the template.
- Flaw found in my own template: nullifier obligations SAT on both
  variants. Cause: polarity. Nullifier admission is must-not-be-in
  (single-use); my R3 assumed must-be-in. Single-call replay candidates
  need a two-transition scope. Excluded with reason recorded in
  cross-results.json; polarity-aware derivation is hand-off item H2.

Claim boundary: producer-dropped SAT is an abstract candidate. It is
not E2 (no producer relation) and not a verdict. Concretization for
this candidate shape already exists manually (D1P-19 attacker tree,
real proof, E4 on the injected mutant); automating that step is the
remaining gate-(b) work, not done here.

## 2026-10-28 — X-BM: 30-mutant binding benchmark

Goal: compiling, ground-truthed proof-to-execution binding mutants of
WarpToad (18) and Payy (12), circuit + consumer. Package
benchmarks/binding-mutants/; raw builds under results/raw/X-BM/.

Routes and fixes: pinned nargo beta.22/beta.14 compile in <1 s per
mutant (git dep cache at ~/nargo intact). WarpToad consumer compiles via
svm solc 0.8.29 with three vendored-equivalent dep packages copied at
build time (symlink + remap attempts failed on sandbox path rules).
Payy consumer needed solc 0.8.20 --via-ir --optimize-runs 200 (mirrors
pinned hardhat config) plus two thin upgradeable stubs (pinned API
subset, marked never-deploy); real OZ 5.x sources vendored at build
time. No third-party deps committed. A relative-OUT build.sh run failed
on log redirects; absolute OUT required (guard added).

Observed: 30/30 compile. Honest nargo execute passes for 6/9 WT-C
(C01, C02, C04, C05, C08, C09); C06/C07 fail as predicted
(honest-breaking by design); C03 skipped by design (reuses D1P-15
real-proof precedent). Compiler lint bonus: beta.22 names the freed
public word for C01/C02/C08. Full table in BENCHMARK.md §3 and
manifest.json observed fields. Build ran under load ~42 (parallel lane
heavy jobs; recorded in logs/load.txt).
