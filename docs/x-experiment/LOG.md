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

## 2026-10-28 — X-CORPUS: taxonomy corpus v1 (seed endpoints only)

Cloned 0xPARC zk-bug-tracker at the pinned commit (remote HEAD equaled
56a99667...; README sha256 31a39587...); screened all 27 Bugs-in-the-Wild
entries against the protocol s2 inclusion boundary: 19 include, 8 exclude,
0 unresolved. SoK dataset has no standalone agent-reachable endpoint
under tonight's source constraint (corpus = paper + 107 audit reports,
both out of scope); recorded unresolved, custodian identification owed.
No audit-firm report or other source opened; linked issues/commits/papers
untouched. Schema needed 3 fix rounds (const-only access rules, in_window
rule for met-relevant rows, uncertainty array); ledger now validates with
0 errors. All 23 families logged as exposed (never held-out). Builder:
scripts/taxonomy_v1_corpus.py; ledger docs/taxonomy/v1-corpus-ledger.json;
table docs/taxonomy/v1-corpus.md. jsonschema 4.26.0 + rfc3339-validator
0.1.4 installed via pip (pinned public packages).

## 2026-10-28 — X-AV: automatic validation warning-to-E4

Built witness_synth_v1.py (rule-dispatched plans) + xav TS harness
(synth/prove/replay) + xav_run.py driver: 20/20 D1P-31 warnings run.
13/13 WarpToad detections reach E3+: 7 rows E4 with zero manual steps
(C01 double-mint, C04 fabricated-origin, S01 unadmitted-root, S02,
S03/S09 replays), C03 E4-preserved (fresh E3 + byte-identical M-DOM
correspondence, 2 counted manual steps), C02/C07/C08 E3-contained
(decoded consumer reverts: fee-cap, dataless verifier reject, OZ
ERC20InvalidReceiver). 7 Payy rows E1 (2-proof harness missing).
Debugging trail: stale mutant dir (pinned-circuit false runs) fixed by
regenerate+completeness gate; regex section-eater fixed; verifier/library
linking (0x-prefix + FQN artifacts + ZKTranscriptLib/RelationsLib);
balance reads moved to the consumer ERC20; S_SRC burn seeding reproduces
the honest root (T3==H2 confirmed); C07 attacker burn admits its tree.
Full run ~8 min proving total at nice-19, serial, under load 30-50.

## 2026-10-28 — X-AV v1.1: shape plans + Payy mock-verifier harness

FF-merged main (bda5265); v1.1 frozen files untouched. Reworked
witness_synth_v1.plan_for to dispatch purely by warning shape
(rule+location+evidence path spelling): R-CONSUMER local-root→anchor-tree,
giga_root→fabricated giga bind-word, nullifier→replay, max_fee→bind 0x0.
Built scripts/xav/payy_replay.ts + XAVProxy.sol + driver run_payy:
pinned solc 0.8.20 standard-json (content-embedded; OZ copied dereferenced
after symlinked-pnpm allow-paths failure), anvil :18549, ERC1967-style
proxy (impl disables initializers), ECDSA validator sigs over the raw
getSignatureMessageHash (no eth prefix). Debugging trail: truncated anvil
keys (derived exact via cast wallet private-key, test mnemonic);
bytes32 value/kind/recipient alignment; viem signMessage→sign({hash});
parseSignature for {r,s,v}; action-dict shape mismatch. Negative controls
on pinned consumer: unregistered mint→"Mint value invalid"; double
settle→2nd "Mint already spent". Mutant results: PY-S01 unregistered mint
settled; PY-S02 settled twice; PY-S03 burn paid noteKind-derived address
(1000) not recipient (0); PY-S04 dead kind-4 settled, recipient +1000 —
all E2 (mock-verifier-scoped), never E4. PY-C02 bounded circuit probe:
mutant needs valid inner proofs at verify_proof_with_type (type 7);
pinned Prover.toml is agg_final-shaped (no agg_agg vectors); bb-3.0.0
bundle lacks proof_as_fields/vk_as_fields; Rust xtask stack out of scope
for tonight → circuit rows stay E1 with documented manual step; C02
consumer-shape rows executed, contained by pinned consumer (reverts match
controls). Full 53-warning v1.1 run launched serial nice-19, no competing
lane provers, load ~8 at start.

## 2026-10-28 — X-AV v1.1 run complete (53/53)

Driver exit 0. WarpToad 13/15 E3+ with zero manual steps (C03 association
excepted, 2 counted steps): 8 E4 (incl. new WT-S06 max_fee bind-word),
4 E3, 1 E4-preserved; shape dispatch handles renamed R-CONSUMER rows and
WT-S06 generically. Payy: 6 rows E2 (mock-verifier-scoped) — S01
unregistered settle, S02 double settle, S03 burn misdirection (recipient
0, noteKind-addr 1000), S04 kind-4 activation; 2 C02 rows
executed-and-contained (pinned consumer reverts match controls); 32 rows
E1 (Rust-stack inner proofs owed). Incident: first pass graded PY-S01/S02
W004 as E3 via the WarpToad replay path (shape plan looked compatible;
artifacts were WarpToad's). Caught in audit, fixed by routing all PY-*
to run_payy first, re-ran S01/S02 (`v11-fix/`), spliced 8 corrected rows
into `v11/results.json` with identity checks. Bogus E3s never committed.
Per-mutant compile cache added (14 compiles for ~40 Payy rows).
AUTO-VALIDATE.md carries the v1.1 table; v1 table preserved as history.

## 2026-10-28 — TC02: PY-C02 real-proof vector (E3)

Reused the lane's T15 apparatus. Mutant checkout (c4d2c90 + PY-C02
one-assert removal) compiled with pinned nargo, VK via pinned bb (local
CRS), cold cargo build 489 s exit 0. New tracked harness
payy-harness/tc02_tail.rs adds an active-slot candidate (attacker mint
@0-3) beside T15's control + tail-burn@4-8. Mutant: all three prove +
natively verify; active public inputs carry the attacker hash exactly;
independent bb verify exit 0; 1-bit tamper exits 1. Pristine pinned
contrast (second cold build 590 s): control/tail verify, active rejected
at witness generation (`proof message must be exported`, main.nr:74:24 —
the removed line). PY-C02 W001/W002 re-graded E1→E3 (zero manual steps);
W003 stays E1 (by-design offchain). Incidents: field-modulus overflow of
first attacker hash (diagnosed, fixed, re-ran); disk-full from two cargo
targets (deleted regenerable dirs, rebuilt with 9.1 G free). Evidence
reports/TC02.md; raw under results/raw/TC02/ (ignored).

## 2026-10-29 — TE04: E4 for PY-C02 W002, zero mock components

Mutant-keyed agg_final (constant = mutant agg_agg VK hash, keccak oracle
per repo generator) proves the TC02 tail-candidate inputs; native verify
exit 0. bb Solidity verifiers for mutant + pinned keys (solc 0.8.29
runs=1 legacy — runs=200 exceeds EIP-170; consumer stays on pinned
0.8.20; HonkVerifier already implements IVerifier; ZKTranscriptLib
deployed via cast and linked by patching linkReferences). Anvil replay
(replay wall 10.0 s, load ~5.6, serial; priority oversight recorded in
AUTO-VALIDATE, nice re-prove confirms): MockUSDC, both verifiers, pinned
RollupV1 behind XAVProxy, synthetic validator key at initialize, honest
mint registered (100). Mutant block settles: height 1, mint spent,
forged burn pays 7 to 0xdead (0→7), rollup 100→93. Same block under the
pinned verifier reverts as `SumcheckFailed()` (0x9fc3a218). W001/W002 →
E4, zero manual steps. Debugging trail: quote TOML hex; bb prove needs
-k; witness is target/agg_final.gz; proof→fields is 32B chunking; use
the proof's note-kind as consumer kind. Evidence results/raw/TE04/
(ignored); scripts te04_part1.sh, te04_part2.py, xav/te04_replay.ts
tracked. Disk stayed ≥8 GB free throughout.
