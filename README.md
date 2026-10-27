# BindCheck

BindCheck investigates whether the guarantees of an accepted zero-knowledge proof justify the effects a blockchain application executes. Under D1 research contract revision 2, the prospective target is **automated discovery and end-to-end validation of proof-to-execution mismatches** from producer constraints, public-input decoding, and consumer effects. Consumer-directed selection and refinement remain a secondary efficiency question (RQ5), not an established advantage. The capability claim, comparative baselines, held-out transfer, and E4 validation have not been established.

The current integration checkout is the linked worktree
`/Users/imranpollob/Coding/bc/bindcheck-d1-paper` on `d1-paper`, currently at
`46dbfc3bf15dda805106254ab7572e3729428dcc` plus the uncommitted D1P-13 and
D1P-14A development-evidence records. It was established from
`chatgpt-codex` revision `cce1a966eb84e8e9819c6f658ca4ce07fd670036`.
[D1P-00](reports/D1P-00.md) records the branch/worktree baseline and the
source-inspected selective-reuse review of `claude-code`; the
[integration plan](docs/d1-paper/integration-plan.md) controls prospective
paper integration. The earlier independent Linux checkout description remains
historical context in the [workspace preservation guide](docs/d1/workspace.md).
Start with the [D1 brief](docs/d1/brief.md) and [development roadmap](docs/d1/roadmap.md).
[D1-00](reports/D1-00.md) records the original D1 preparation and preservation checks.

Start with the [research contract](docs/research-contract.md). It is authoritative for the research questions, threat model, scope, specification boundary, and evidence rules. The [living project checkpoint tree](docs/project-status.md) shows the path from current work to a possible paper submission without replacing the underlying evidence. The [Payy case study](docs/payy-case-study.md) gives the pinned versions, commands, expected outcomes, evidence locations, and limits for the independently built local reproduction of a publicly disclosed message-tail flaw.

[D1P-INT1](paper/contract-revision-proposal.md) applies the approved capability-framing revision prospectively on 27 October 2026. It adds automated-discovery and automated-validation research questions, the E0–E4 evidence ladder, generic/default plus same-policy baseline arms, and a four-part capability gate. [Revision 1](docs/history/research-contract-2026-10-23.md) is preserved byte-for-byte. No earlier result is relabeled or rerun; D1P-07, D1P-09, D1P-10, D1-01/T22 and the historical synthetic results remain evidence about the former efficiency hypothesis, now secondary RQ5, and do not count as capability evidence.

For a shareable introduction to the project and completed work, use the [research and work summary](docs/research-and-work-summary.md), dated 22 October 2026. It separates demonstrated results and open research claims at that historical checkpoint; the D1 roadmap now controls the next task.

The [research guide](BindCheck_Research_Guide.md) and [16 October progress update](2026-10-16-research-update.md) are historical planning and progress records. They remain useful context, but their evidence status and schedules may have been superseded.

The principal directories are `circuits/` and `contracts/` for the small fixture, `bindcheck/` for the checker and specification, `payy-harness/` and `payy-consumer/` for the Payy experiment, `scripts/` for task runners, and `reports/` for evidence reviews. Generated proof data and raw logs are under the ignored `results/raw/` tree and must be regenerated on a fresh checkout.

## Current status

- [D1P-INT1](paper/contract-revision-proposal.md) applies research contract
  revision 2 prospectively and archives revision 1 byte-for-byte under
  `docs/history/`. The target contribution is now automated discovery plus E4
  end-to-end validation, compared with generic/default and same-policy
  baselines and transferred to a frozen held-out family. Efficiency is
  retained as secondary RQ5. No historical report, evidence level or verdict
  changes, and no experiment is rerun.
- [D1P-00](reports/D1P-00.md) establishes the clean `d1-paper` linked
  worktree and an integration baseline without merging or porting code. The
  Codex V2/typed-consumer line remains the base; the Claude refinement loop is
  a selective reimplementation candidate, not a branch-merge candidate. The
  exact six-query N=8 input bundle is locally missing. An isolated Python
  baseline passes 27 tests but has four import errors because
  `pycryptodome==3.23.0` could not be installed through the sandboxed package
  index; this is not a 119-test pass. Research status remains UNKNOWN.
- [D1P-01](reports/D1P-01.md) installs the exact pinned Python dependency and
  completes the local baseline: 119 pre-change tests and 124 post-change tests
  pass with no failures or errors. A path-neutral, provenance-checked intake
  now rejects missing or mismatched inputs before generation and enforces a
  serialization-only no-solver boundary. Its five focused controls and the
  separate 65,536-vector compact-walk self-check pass. The exact two N=8
  ACIR/ABI pairs remain absent from recorded local evidence roots, so artifact
  recovery is BLOCKED, none of the six query hashes is newly reproduced, and
  research status remains UNKNOWN.
- [D1P-02](reports/D1P-02.md) resolves that local artifact blocker without
  rewriting D1P-01: four inputs imported from evidence commit `7d098cd3...`
  independently match the frozen D1-01 manifest, and the unchanged
  serialization-only adapter reproduces all six historical v5 query hashes in
  a fresh ignored namespace. No solver process or solver record exists. This
  is a byte-reproducibility result only; all six historical timeout outcomes
  and the D1 research verdict remain UNKNOWN.
- [D1P-03](reports/D1P-03.md) supplies the no-execution
  [experiment protocol](docs/d1-paper/d1p-03-protocol.md). It corrects the
  actual consumer scan to configurable length, kind-0 advance, four-word kind
  2, five-word kind 3, and revert for all other kinds, distinct from the frozen
  producer walk. A solver-free checker exhaustively validates 781,250 stream
  cases, all 25 cell pairs, and 12,825 goal cases, including overflow and
  truncated records. The check establishes only partition/rewrite equivalence.
  Track A execution and the unimplemented Track B joint solver remain pending
  both planners' decisions; research status is UNKNOWN.
- [D1P-04](reports/D1P-04.md) corrects the prospective comparison protocol and
  emits six parents × 25 cells as 150 specialized queries plus 150 producer-
  free two-direction equivalence queries. All 150 complete ordered producer
  prefixes are byte-identical to their parents, and six focused tests plus
  the complete 134-test D1 suite pass without solver calls. SMT equivalence is
  nevertheless **unestablished**: macOS rejected the frozen 4 GiB pre-exec
  address-space limit before the first control could launch cvc5. The no-retry
  rule left 0/150 cells validated and all 150 ineligible for primary use.
  Task reporting is complete, validation is incomplete, and the D1 research
  verdict remains UNKNOWN.
- [D1P-05](reports/D1P-05.md) preserves D1P-04 and executes the unchanged
  equivalence suite with a macOS libproc process-tree RSS monitor. Both
  controls pass and all 150 cell queries return UNSAT with exit zero; all 150
  producer-prefix audits remain true. The complete partition is now eligible
  for later primary use at the transformation-evidence level. The 50 ms RSS
  sampling can overshoot and is not a hard address-space cap; observed timing
  is non-primary macOS evidence. No parent satisfiability, consumer-direction,
  proof, consumer, or D1 verdict follows. The research verdict remains UNKNOWN.
- [D1P-06](reports/D1P-06.md) prepares and freezes the equal-budget Track A
  matrix on the planner-selected native Mac reference. The byte gate passes
  for all 166 inputs, all eight harmless-helper preflight checks pass, and the
  complete D1 suite passes 147/147. Both solver controls pass and one goal-only
  diagnostic returns usable SAT. The next goal-only call writes SAT text but
  hits a monitor/process-exit cleanup race before its exit/resource record is
  complete. The frozen infrastructure-stop rule leaves all six combined
  queries and all 150 cells unrun. Track A effectiveness is therefore
  unestablished and the D1 verdict remains UNKNOWN.
- [D1P-07](reports/D1P-07.md) repairs the process-exit race and completes a
  fresh frozen campaign from call 1. Focused tests pass 7/7, the complete D1
  suite passes 154/154, all 13 helper checks pass, and all 166 solver calls
  receive structured records. All six combined and all six partitioned
  logical obligations remain UNKNOWN: partitioning resolves 58/150 cells
  UNSAT but leaves 92 timeouts, improving zero complete obligations. Goal-only
  diagnostics are 6/6 SAT and both cone-only diagnostics time out. This is
  producer-side partial-progress evidence, not consumer-direction or D1
  security evidence; the D1 verdict remains UNKNOWN.
- [D1P-08](reports/D1P-08.md) verifies the D1P-07 cell split without rerunning
  Track A: 58 literal-false goals are UNSAT, while 42 literal-true and 50
  nontrivial goals time out; all six goal-only diagnostics are SAT and both
  cone-only diagnostics time out. A minimal solver-neutral symbolic consumer
  now preserves exact decoding, guards, sequential effects, rollback, V2
  admission, and occurrence matching. Thirteen focused and all 167 D1 tests
  pass; 12 symbolic/concrete source-bound cases match. The proposed next gate
  is an offline forwarding/occurrence certificate plus 11 exact N=8 consumer
  trace predicates. No joint solver, proof, replay, or D1 verdict follows.
- [D1P-09](reports/D1P-09.md) inventories the exact N=8 producer, forwarding,
  and consumer boundary; generates all 11 successful consumer decoding shapes;
  and applies one conservative propagation implementation to the unspecialized
  620/540 check-added cone, all 11 consumer shapes, and all 25 producer cells.
  The shape partition is exhaustive/disjoint over 390,625 control-flow classes,
  12 focused and 179 complete D1 tests pass, and consumer kind facts discharge
  4–8 original cone operations without fixing payloads. The one authorized
  isolated N=8 `agg_final` compile fails before output when Nargo cannot lock
  its external cache, so exact N=8 forwarding/key correspondence and all
  full-relation claims remain blocked. No solver, proof, replay, joint encoder,
  AUTH/NONVAC result, or D1 verdict follows.
- [D1P-10](reports/D1P-10.md) completes a newly frozen, in-sample feasibility
  study of only the 620/540 check-added selected producer cone. Eight
  30-second profiling calls all time out; the predeclared RSS tie-break selects
  radix 4, not a measured solver advantage. Both controls and the T22
  lost-equality regression pass, but only 12/25 exact propagation XOR checks
  return UNSAT, 13 time out, and all four radix-4 boundary controls time out.
  Both transformed arms are therefore ineligible and remain unrun. The four
  eligible unchanged-baseline obligations each time out at 300 seconds.
  Total observed solver-call wall is 1,954.640027 seconds across 44 calls;
  there is no SAT model, solved obligation, validated encoding improvement,
  proof, replay, or D1 security result. The research verdict remains UNKNOWN.
- [D1P-11](reports/D1P-11.md) completes a prospective, bounded screening of
  the entire permitted development pool: four applications in four families,
  below the 12-application/six-family/four-hour ceilings. Semaphore-Noir and
  discovery-only leads remain protected and outside the denominator. The
  screen retains WarpToad as the first tractable candidate, 0xbow Privacy
  Pools as contingent on an explicit Circom/aggregation scope decision, and
  Payy only for calibration; it excludes the Aztec v6 epoch rollup as too
  broad for the current fragment. The ledger records both all-output and
  subset consumer use, concrete joint obligations, audit evidence separately
  from policy, artifacts and unresolved assumptions. No solver, build, proof,
  replay, vulnerability validation, live-chain test, or held-out evaluation
  ran. All four application verdicts and the D1 result remain UNKNOWN.
- [D1P-12](reports/D1P-12.md) completes the bounded WarpToad executable-
  fixture gate with an exact setup blocker. Five surviving D1P-11 source files
  match 5/5 recorded SHA-256 values in a fresh ignored workspace, but the full
  pinned checkout, lockfile, circuit dependencies, compiled artifact/ABI,
  matching VK/generated verifier and declared Noir beta.22/bb.js 5.0.0 route
  are unavailable. Direct Git retrieval cannot resolve GitHub under the
  environment policy and browser-origin access was not granted. The existing
  ACIR reader is version-locked to Noir beta.14, outside the declared beta.22
  Noir JS route; the absent artifact prevents an exact compatibility check.
  A setup-only checker, frozen two-attempt protocol, manifest and source-level
  eleven-input/hash-dependence analysis are preserved. Zero builds, proofs,
  consumer executions or solver calls ran; no effects or performance were
  measured, and the D1 verdict remains UNKNOWN.
- [D1P-12R](reports/D1P-12R.md) preserves D1P-12 and completes the owned-local
  WarpToad development fixture at the exact pinned revision. The committed
  beta.22 artifact deterministically yields a saved 1,888-byte VK and a
  Solidity verifier byte-identical to the committed verifier; exact solc
  0.8.29 compiles it. One real 9,152-byte UltraHonk `keccakZK` proof is
  accepted by bb.js and the generated verifier, then the unchanged `mint`
  consumes the nullifier and splits 5e18 raw units between an ordinary named
  relayer and recipient with a nonzero fee. Identical proof/calldata replay is
  rejected. All 22 `P`/`P+1` public-word probes revert with
  `ValueGeFieldOrder()`, so this verifier rejects rather than reduces
  noncanonical words. The historical circuit artifact was behavior-validated,
  not independently rebuilt from source; no cross-chain, performance,
  protocol-policy, vulnerability or D1 verdict follows. D1 remains UNKNOWN.
- [D1P-13](reports/D1P-13.md) independently rebuilds the pinned WarpToad
  withdraw circuit with exact Noir beta.22. Rebuilt ACIR bytecode, decoded
  constraints, ABI, bb.js 5.0.0 VK and generated verifier all match the
  committed route; the only whole-JSON differences are seven nonsemantic
  diagnostic source paths. A separate fail-closed beta.22 MessagePack decoder
  classifies all 25,073 opcodes while the beta.14 decoder stays byte-unchanged.
  The D1P-12R honest inputs satisfy all 24,967 supported arithmetic/range
  constraints; 86 proof-enforced Poseidon2 permutations remain explicitly
  unsupported, separately from 20 Brillig witness-generation calls. Two
  predeclared mutation controls fail their named constraints, the focused
  set passes 58 tests/284 subtests and the complete D1 suite passes 197/312,
  and decoded witnesses 0–10 map
  exactly to the consumer order. No solver, joint encoder or new proof ran;
  this is correspondence/component evidence, not policy or security
  validation. D1 remains UNKNOWN.
- [D1P-14A](reports/D1P-14A.md) adds concrete fee-cap fixtures on the same
  exact-artifact, owned-local route. One new 9,152-byte proof with `max_fee`
  below amount succeeds at a frozen `0.1 gwei` base fee, consuming its
  nullifier and conserving `5e18` across an ordinary relayer
  (`194881000400000000`) and recipient (`4805118999600000000`). The unchanged
  proof and calldata are mined at `2 gwei` and revert at the pinned cap check
  because the computed fee is `2046250504200000000 > 1e18`; all consumer
  token/nullifier/root state rolls back. A second real proof with the
  proof-bound fee factor zero mints `4e18` to the recipient and zero to the
  relayer. Exactly two bounded proof attempts ran; no solver, encoder, fork,
  live-chain action, performance claim, policy validation or security verdict
  follows. D1 remains UNKNOWN.
- [D1P-14B](reports/D1P-14B.md) implements the first canonical WarpToad joint
  `AUTH-1`/`NONVAC-1` diagnostic encoder and occurrence-preserving `T_mint`
  lowering. The lowering matches the D1P-12R honest/replay cases and all
  D1P-14A fee controls; OpenZeppelin is resolved exactly to 5.6.1, and the
  D1P-12R real-proof anchor matches the modeled scope and DRAFT policy. The
  hash-complete manifest froze all three required queries, but each one-shot
  cvc5 process stopped on the same missing-parenthesis parse error before
  satisfiability checking. The no-refinement rule leaves Q1, Q2 and Q3
  `UNKNOWN`; no SAT validation, proof generation, consumer-direction result,
  policy validation or D1 verdict follows.
- [D1P-14C](reports/D1P-14C.md) preserves D1P-14B and repairs its SMT syntax,
  makes the consumer transition/effects independent of the unchanged policy,
  labels the summary `MANUAL / ASSUMED`, and derives G4/G5 from explicit mint
  occurrences and nullifier writes. All seven frozen queries pass both
  parenthesis and pinned-cvc5 parse preflights; 17 focused tests and 12
  subtests pass. C1 returns a model-validated conservation SAT in 24.335629
  seconds, but C2 times out at its single 60-second control slot. The required
  stop rule leaves C3, C4 and Q1–Q3 unrun. This is an exact sensitivity-control
  blocker, not Solidity equivalence, automatic discovery, a performance or
  vulnerability result; AUTH-1, NONVAC-1 and D1 remain `UNKNOWN`.
- [D1P-14D](reports/D1P-14D.md) preserves D1P-14B/C and replaces the symbolic
  sensitivity gate with eight deterministic regressions derived from the
  D1P-14A FC-POS fixture. All four existing implementation mutants are SAT for
  their designated G1/G3/G4/G5 predicates; the BASE summary is UNSAT for each
  corresponding predicate at identical fixed inputs. Twenty-one tests and
  twelve subtests pass, and all eleven frozen inputs pass parser preflight.
  The unlocked, byte-identical D1P-14C diagnostics remain `UNKNOWN`: Q1 and Q2
  time out at 300 seconds, while Q3 ends in a root-process monitor error after
  229.747027 seconds with no SAT/UNSAT output. No primary candidate, proof or
  V-EXEC runs. These are fixed-input encoder regressions, not search,
  performance, automatic-extraction, semantic-equivalence or vulnerability
  evidence; AUTH-1, NONVAC-1 and D1 remain `UNKNOWN`.
- T15–T19 locally reproduce the public Payy message-tail mechanism with real proofs and committed token-balance effects, then validate the repair and an honest control.
- T20 maps those claims to pinned source and advisory evidence.
- T21 is an in-sample, source-pattern prototype; it does not establish generalization.
- T22-v2 passes the single-case feasibility gate: the bounded earlier Payy `agg_agg` case yields a cvc5 counterexample in 4.1 seconds after exact specialization reduces the probe from 587 opcodes/523 witnesses to 0/1. Its frozen nine-case primary evaluation then fails: 2/9 outcomes match, 6 are `UNKNOWN`, and the equivalent running-flag negative control produces a likely spurious `VIOLATION`. T22 remains incomplete and no general detector claim is supported.
- The T22-v2 failure diagnosis (report Section 3.2) explains all three failure classes against the same ACIR without changing any result:
  - **Running-flag `VIOLATION` (false positive):** confirmed as an analyzer false positive. Specialization discards the implied constraint `messages[k] = 0` for the goal witness, while subset certificates from the original ACIR are UNSAT for all eight slots.
  - **Timeouts:** traced to the default cvc5 finite-field mode on range-bit decompositions, missing re-componentization, and a slot schedule that skips the violating slot. The general queries remain an open scalability limit.
  - **`agg_utxo` contradictions:** genuine (the first proof can never be padding), but handled as unsupported, so no general query was issued.
- [T22-v3](reports/T22-v3.md) completes the separately frozen R1–R6 repair, nine-case rerun and SAT audit: 4/9 outcomes match, with 4 `VIOLATION`, 5 `UNKNOWN`, and no `VERIFIED_WITHIN_SCOPE`. It recovers the `>`-guard and skipped-final-slot mutants; the running-flag probe false positive is fixed (all eight slots UNSAT), while its full case remains `UNKNOWN`. Six general queries time out and nine fail allocation under the frozen 4 GiB cap. All four SAT probes replay successfully, all nine compiled cases match v2, and prior evidence is unchanged. This is development-case evidence, not generalization.
- [T22-v4](reports/T22-v4.md) completes the separately versioned check-added `agg_agg` general-query feasibility task with a minimized blocker. Exact fixed-stream specialization gives a conditional non-vacuity SAT in 79.9 seconds, but all three full Boolean-rank general queries still time out at 300 seconds. A byte-preserved goal-only reduction of the original non-vacuity SMT has one assertion, 18 free variables and no ACIR assertions, yet also times out at 300 seconds with 93,696 KiB peak RSS. The check-added case and overall T22 remain `UNKNOWN`/incomplete; no safe verdict follows from these timeouts.
- [D1-01](reports/D1-01.md) closes the T22-v5 reporting boundary: all six N=8 primary slots are accounted for by three validated historical check-added timeouts and three new running-flag timeouts, each at 300 seconds and 4 GiB. All six remain `UNKNOWN`; the original successful-solver milestone is unmet and overall T22 remains incomplete. The unchanged [v5 protocol](scripts/t22_v5_protocol.md), compact specification self-check, and saved ACIR-bearing blocker audit establish no whole-system safety result. The [query matrix](metadata/d1/d1-01-query-matrix.json) and [execution manifest](metadata/d1/d1-01-execution-manifest.json) record the evidence; no `reports/T22-v5.md` or earlier verdict is rewritten.
- [D1-02](reports/D1-02.md) completes a bounded availability screen of pinned WarpToad and 0xbow Privacy Pools sources (65 files). Neither meets the entire initial Noir/ACIR batched-settlement fragment: WarpToad supplies a single-claim Noir path; 0xbow supplies Circom/Groth16 and batched consumption with additional modeling needs. At that historical checkpoint no target was selected and D1-02 remained ACTIVE. The recovered continuation below supersedes that task state. No build, proof, replay or transfer evaluation ran in the screen.
- [D1-02 continuation](reports/D1-02-continuation-01.md), recovered and checked by the [reconciliation audit](reports/D1-02-reconciliation-01.md), selects Semaphore-Noir with qualifications. D1-02 availability selection is complete; no proving or transfer result follows. Inherited D1-03 setup and its hash-matching protocol are preserved; [D1-03 preflight](reports/D1-03-preflight-01.md) identifies a conflict between freely failing transfers and the required verified repaired control. The authorized [v2 design](reports/D1-03-v2-design.md) now supplies explicit funded-token conditions, separate P/O policy and exact occurrence matching; 10 component tests and 8,892 finite checks pass. The [extraction gate](reports/D1-03-v2-extraction-01.md) adds a domain/policy core and compiled-artifact inventories with 23 passing regressions, but typed recursion/frame bindings and transition semantics were unimplemented at that checkpoint. [Typed bindings](reports/D1-03-typed-bindings-01.md) now decode all four artifacts and certify six recursive-call/frame mappings, with 27 passing controls. [Consumer-boundary audit](reports/D1-03-consumer-boundary-01.md) follows 19 function/modifier bodies and exposes unresolved signature/validator-set loops; nine controls pass after a preserved fixture-error correction. [Guard-frame work](reports/D1-03-guard-frame-01.md) adds 22 passing controls; its single artifact check predates dispatch/cache hardening, so final artifact validation is incomplete. The subsequently authorized [codebase review](reports/D1-codebase-review-01.md) validates the final guard checker against the pinned artifact within 120 seconds/4 GiB; all 81 Python controls pass in an isolated source/test copy. The legacy JavaScript suite is blocked by the missing installed `js-sha3` dependency. The new [consumer execution task](reports/D1-03-consumer-execution-01.md) adds concrete AST execution, ordered registry/token effects, rollback and separate v2 admission: 119 Python tests, 29 actual-artifact controls and 13 unchanged-Solidity component tests pass. Guard/verifier acceptance remains abstract; symbolic composition and joint gates remain incomplete. Historical replay proof/public-input bundles are absent from the inspected local raw directories, while the protocol permits zero new proofs. The task stops for replay/resource review; D1-03 stays UNKNOWN and D1-04 is blocked.
- [Proof recovery 01](reports/D1-03-proof-recovery-01.md) uses a newly authorized, separately frozen recovery budget. Pinned Rust/Linux bb and an isolated source copy are ready. Build 1 fails on missing libclang; local pinned libraries fix that prerequisite, but build 2 fails at final linking with `Cannot allocate memory` under 4 GiB. Both build slots are consumed. All 119 Python checks pass; no proof or full replay ran. D1-03 remains UNKNOWN. Review the [one-build GNU BFD proposal](docs/d1/proof-recovery-02-proposal.md) before another attempt. The v2 seeds and 28 primary query slots are unchanged.
- No held-out application result or general research contribution has been established.

**D1-01 reporting closure and D1-02 availability selection are complete;
research results remain UNKNOWN. D1-03 is incomplete:** D1P-09 validates the
11-trace predicates and a small selected-cone propagation opportunity. D1P-10
does not turn that opportunity into a validated solver comparison: both
transformed arms fail their frozen pre-main gates and all four eligible
baseline obligations time out. D1P-11 consequently screens the four permitted
development applications instead of extending that tuning line. D1P-12
records the first WarpToad setup blocker; D1P-12R preserves it and completes a
real owned-local proof-to-mint chain from the exact committed artifact through
a regenerated VK/verifier, nonzero-fee effects, replay rejection and strict
public-field canonicality. D1P-13 then establishes exact pinned
source-to-bytecode/ABI/VK/verifier correspondence and checks every supported
arithmetic/range constraint on the honest witness, while leaving 86 Poseidon2
constraints uninterpreted. D1P-14A concretely exercises the nonzero fee cap,
an unchanged-proof over-cap revert, and the zero-fee branch with real proofs
and receipts. D1P-14B then freezes the first joint AUTH-1/NONVAC-1 encoding,
but a common SMT-LIB parenthesis defect makes all three one-shot processes
parser errors. D1P-14C repairs and preflights a fresh freeze, then stops at the
required sensitivity gate when C1 validates as SAT but C2 times out; C3, C4
and all three primary queries remain unrun. D1P-14D replaces that gate with
eight deterministic fixed-input polarity regressions, all of which pass, then
runs the unchanged primaries: Q1/Q2 time out and Q3 has a monitor error, so all
three diagnostics remain UNKNOWN.
These are development artifact/component results, not general
policy validation, cross-chain evidence or a security result. The exact N=8 forwarding artifact/key,
full-producer propagation, joint query, proof, and accepted full settlement
replay remain absent. Offline component checks are not joint verification.
The two principal properties remain authorization and coverage.

Prospective work is governed by contract revision 2's capability gate:
automated artifact-derived discovery with manual inputs counted, automated E4
validation on a development case, both baseline arms, and transfer to a frozen
held-out family without a new defect-specific rule. None of those four gate
conditions is currently complete.

D1-00 ran preservation and documentation checks only. D1-01 validated the saved check-added records and ran only the three missing running-flag slots. No D1 method-feasibility or novelty claim follows from preparation or reporting closure.

## Evidence hierarchy

1. `docs/research-contract.md` — current research decisions.
2. This README — current task status.
3. `reports/Txx.md` and `reports/D1-xx.md` — tracked evidence summaries.
4. `results/raw/Txx/` and `results/raw/D1-xx/` — ignored, regenerable raw logs.
5. The research guide and dated updates — historical context.

## Repository layout

The principal directories are `circuits/` and `contracts/` for the small fixture, `bindcheck/` for the checker and specification, `payy-harness/` and `payy-consumer/` for the Payy experiment, `scripts/` for task runners, `reports/` for tracked evidence summaries, and `docs/` for current and historical-facing documentation. Generated proof data, downloaded dependencies, compiler output, and raw logs are ignored and must be regenerated on a fresh checkout.

## Checking this checkout

The latest D1 Python controls were checked with Python 3.13.7 and PyCryptodome
3.23.0 (189/189 passing in D1P-10). The small upstream Noir test-source
excerpts, provenance and MIT notice
are included under `tests/d1/fixtures/`; unit controls need no compiler download,
proof, solver, generated artifact or historical raw log. To set up and run them:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-d1.txt
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests/d1 -v
```

The legacy checker tests use `node --test bindcheck/test/checker.test.js`,
installed dependencies from `package-lock.json`, and the seven preserved T06
records under ignored `results/raw/T06/records/`. They cannot run on a fresh
clone without those inputs. The codebase review records a dependency setup
failure, not a passing JavaScript suite. No dependency installation occurred
during that frozen review.

Task-specific D1 experiment runners are frozen historical entrypoints,
not general test commands: they may refuse completed attempts or exhausted
budgets. The reusable `scripts/d1_guard_frame_check.py --output <fresh-path>`
needs the separately pinned solc/source artifacts and only checks a local
storage frame. Obtain any required experiment budget approval and freeze
inputs before using it. Its success is not a complete transition or security
verdict.

The [codebase review](reports/D1-codebase-review-01.md) explains the independent
checkout's inherited history. Exact synthetic-branch reports and protocol
versions are preserved under `docs/history/synthetic-branch-1b4d568/`; their
original full implementation remains in Git history. Their synthetic claims
do not complete this checkout's D1 gates.
