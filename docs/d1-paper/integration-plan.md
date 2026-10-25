# D1 paper integration plan

Date: **25 October 2026**. D1P-07 race-safe native-macOS Track A campaign:
**COMPLETE**. Complete 25-cell transformation eligibility remains **PASS**
from D1P-05; decomposition resolves no complete logical obligation under the
frozen D1P-07 budget. Research verdict: **UNKNOWN**. This plan records an
integration boundary and reviewed experiment protocol; it does not establish
a D1 security result, parent-query result, proof result, or paper claim.

## 1. Workspace and reviewed revisions

The integration worktree is
`/Users/imranpollob/Coding/bc/bindcheck-d1-paper`, branch `d1-paper`, currently
at `2ad4f699d527490149f3704e6f6f228494f2d4bd` plus uncommitted D1P-04–07
working changes. D1P-00 reattached the
already-existing branch at `cce1a966eb84e8e9819c6f658ca4ce07fd670036`, the
then-current `chatgpt-codex` tip, without creating, resetting, merging, or
rewriting it. The later tracked preparation/artifact commit is recorded in
D1P-02. D1P-03 through D1P-07 performed no Git commit, push, merge, or branch
change.

Reviewed sources:

| Role | Branch | Revision | Worktree |
| --- | --- | --- | --- |
| Integration base | `chatgpt-codex` | `cce1a966eb84e8e9819c6f658ca4ce07fd670036` | `/Users/imranpollob/Coding/bc/bindcheck-chatgpt-codex` |
| Selective-reuse source | `claude-code` | `9d90b93e00a8fe96d0fcd56261f9ee41d392cab5` | `/Users/imranpollob/Coding/bc/bindcheck-claude-code` |
| Common ancestor | — | `1b4d5683d87cd8f71b37e140d0b99c9fd21b856f` | — |
| Preservation checkout | `main` | `90f46a4e30c1b15ee94a357d244a54dbbabf2d2c` | `/Users/imranpollob/Coding/bc/BindCheck` |

There are three commits unique to `chatgpt-codex` after the common ancestor
and two commits unique to `claude-code`. A branch merge is not suitable:
`claude-code` deletes the typed-binding, consumer-execution, guard, proof
recovery, and associated evidence line while adding a synthetic-only joint
pipeline and closing report. Reuse must be path- and behavior-selective.

## 2. Integration constraints

The research contract, current README, and immutable reports remain the
evidence hierarchy. The following limits control this integration:

- Preserve the three verdicts and attach evidence grade, assumptions, bounds,
  non-vacuity, provenance, and reason codes separately.
- Treat the six historical N=8 outcomes as `UNKNOWN`; preparation does not
  reopen or spend their frozen execution slots.
- Do not use a case label, expected verdict, or manually asserted missing
  binding as analyzer input.
- Do not promote a satisfying ACIR model, `nargo execute`, an abstract
  verifier choice, or a component Foundry test to real-proof consumer replay.
- Keep the actual producer relation, decoder, successful consumer transition,
  occurrence-level policy, and replay evidence distinct.
- Do not run historical cleanup scripts against preserved evidence. New
  runners need fresh output roots and independent budgets.

## 3. Component inventory and decisions

“Tests” below are code-inspected or historical unless explicitly identified as
the D1P-00 local baseline. Historical success is not a fresh reproduction.

| Need and candidate | Source revision | Dependencies | Semantic assumptions and inspected tests | Decision and required adaptation |
| --- | --- | --- | --- | --- |
| N=8 ACIR parser, cone builder, FF encoder, and solver wrapper: `scripts/t22_v3_tailspec.py` | Last changed `19fb42761ca8afbe1f600a9fd9544faac1eb67d4`; identical on both source branches; SHA-256 `81a1cd43cd3e6e735dc325535f05d9b2a88c6c9794b434ab53e834061ff700c8` | Python stdlib; printed beta.14 ACIR; cvc5 finite-field support | Cone omission assumes omitted components are satisfiable; recursive proof feasibility and parser/encoding soundness are not proved. `scripts/t22_v3_checks.py` contains seven historical soundness regressions. | **Reuse through a pinned adapter.** Keep the byte identity and regressions; add an explicit artifact/result interface and fail closed on unsupported ACIR. Do not make it the D1 architecture or edit it in place. |
| Six-query compact baseline: `scripts/t22_v5_compact.py`, `scripts/t22_v5_protocol.md`, and `scripts/t22_specs/payy_agg_agg.json` | `41093d1905e44af347e1d39cd6718728d4157c77`; encoder SHA-256 `39cb3731d6e2921ac0a59c21dbd5d18a7a91bec18628e0e6bb843382d766c792` | Previous parser; two printed ACIR/ABI pairs; GPL/CoCoA cvc5 1.4.2 | Exactly N=8, two streams, kinds 2→4 and 3/4→5. The compact walk self-checks 65,536 category vectors, but that is not an ACIR summary proof. All six historical full queries timed out at 300 seconds/4 GiB. | **Retain as the frozen comparison.** A new adapter may regenerate bytes in a fresh namespace, but may not rewrite the encoder, historical outputs, limits, or UNKNOWN outcomes. |
| D1-01 closure runner and manifests: `scripts/d1_01_closure.py`, `metadata/d1/d1-01-{query-matrix,execution-manifest}.json` | Runner last changed `30fb03ee78bb732169442047d8c9b5b16d2412e0` | Hard-coded historical Linux paths, local cvc5 tree, archived raw inputs | Runner targets old output locations and an already-consumed budget. Manifests contain the six query hashes and exact historical observations. | **Reuse manifests only. Reject the runner for execution.** Write a path-neutral, fresh-output importer/validator; never invoke `prepare`, `run`, or cleanup behavior from the old task. |
| Exact N=8 input/query bundle | Payy B source `dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36`; noirc `60ccd48e18ad8ce50d5ecda9baf813b712145051` | Check-added and running-flag printed ACIR/ABI; six SMT files; matching solver | D1P-02 validates the four inputs against evidence commit `7d098cd3...` and reproduces all six frozen query hashes through the unchanged no-solver adapter. | **Recovered and byte-gated.** Preserve D1P-01's historical blocker, use a fresh namespace for later diagnostics, and do not infer solver or semantic correctness from byte equality. |
| D1P-04 25-cell specializer and equivalence harness | Task-start HEAD `2ad4f699...`; generator SHA-256 `afb0d154...`; frozen parents above | Python stdlib; exact six D1P-02 parent bytes; compatible finite-field cvc5 only in the separate validator | The serializer copies the complete ordered producer prefix, emits only an explicit cell and specialized goal, and builds producer-free XOR equivalence queries over the original finite-field walk. Six focused tests and all 150 byte audits pass. The first solver control did not launch because native macOS rejected the frozen 4 GiB pre-exec limit. | **Retain generated bytes and manifest; validation incomplete.** No cell is eligible. A new-version portable runner may reuse the exact query bytes only after a fresh freeze and controls-first review; do not change expected results or parent hashes. |
| D1P-05 macOS equivalence runner | Task-start HEAD `2ad4f699...`; runner SHA-256 `16cc0ae3...`; D1P-04 inputs unchanged | Python stdlib; macOS libproc; exact arm64 cvc5 1.4.2 binary; D1P-04 manifest | Samples recursive process-tree RSS every 50 ms, kills the process group after observed RSS exceeds 4 GiB, and records launch/monitor failures. Helper launch/timeout/memory/cleanup controls pass; sampling can overshoot and is not a hard address-space cap. Both SMT controls pass and 150/150 cell XOR queries are UNSAT. | **Eligible transformation; retain with limitations.** The exact 25-cell transformation may be used in a later frozen primary plan. Native macOS timing/RSS is non-primary and does not establish parent satisfiability, method effectiveness, or a D1 verdict. |
| D1P-06 Track A preparation and runner | Task-start HEAD `2ad4f699...`; input manifest `67f588f...`; frozen runner `e472302e...` | Exact D1P-02 parents, D1P-05-eligible cells, arm64 cvc5, unchanged D1P-05 libproc monitor | Audits six goal-only and two cone-only derivations, copies six parents and 150 cells byte-for-byte, and freezes equal 300-second combined/partitioned slot budgets. Preflight passes, but call 4 hits a root-exit/cleanup race after SAT text and before a complete record. | **Retain preparation and stopped ledger; no effectiveness result.** Both controls and one goal-only SAT are usable; call 4 is UNKNOWN and calls 5–166 are unrun. Do not resume or repeat without a new planner-approved runner/freeze decision. |
| D1P-07 race-safe Track A runner | Task-start HEAD `2ad4f699...`; runner `cba540dc...`; D1P-06 inputs unchanged | Python stdlib; macOS libproc; exact arm64 cvc5; bounded wait/cleanup policy | Confirms a missing root with bounded reap, catches termination errors, falls back to bounded direct kill, always records calls/ledger, and uses null for unavailable memory. Seven focused, 154 full-suite and 13 helper checks pass. All 166 calls execute once; six combined and six partitions remain UNKNOWN, with 58 UNSAT and 92 timed-out cells. | **Retain as completed negative/partial Track A evidence.** Partitioning improves zero logical outcomes under the frozen budget. Do not treat lower partial elapsed time or cell UNSAT results as consumer-direction effectiveness or a D1 verdict. |
| V2 semantic domains, occurrence policy, token fragment, and admission: `model_v2.py`, `policy_v2.py`, `consumer_scope_v2.py` | `42bd0ebbf365469fe3147bb13d7359b129319aa2` and `cafe4dac50a24b36107ed9ef187abc2666156593` | Python stdlib | Separates field/EVM words, P/O, identities, committed traces, and unsupported deferral. Uses exact `Counter` multiplicity and funded standard-token admission. Twenty-three `test_v2_core.py` methods are defined; D1P-00 could not import that module without PyCryptodome. | **Retain as the semantic base.** Add symbolic forms without weakening canonicality, multiplicity, rollback, or UNKNOWN behavior. |
| Typed ACIR decoding and binding certificates: `acir_binary_v1.py`, `acir_bindings_v1.py`, `binding_certificate_check_v1.py` | `42bd0ebbf365469fe3147bb13d7359b129319aa2` | Python stdlib; pinned beta.14 serialization schema and tracked upstream excerpts | Checks typed recursive calls, ABI/frame mappings, polynomial certificates, canonical fields, caps, and unsupported tags. All 27 defined tests passed locally in D1P-00 without PyCryptodome. | **Reuse.** Make it the provenance/binding authority and adapt legacy printed-ACIR nodes into it; do not replace it with sequential-layout guesses. |
| Source-bound consumer inventory, guard frame, execution, rollback: `consumer_boundary_v1.py`, `guard_frame_v1.py`, `consumer_execution_v1.py` | Frame/boundary `42bd0ebbf365469fe3147bb13d7359b129319aa2`; execution `cafe4dac50a24b36107ed9ef187abc2666156593` | PyCryptodome 3.23.0; pinned solc 0.8.20 AST/source artifacts; ordinary OZ 5.0.1 token model | Keeps guard/verifier choices abstract, commits effects only on return, and fails closed on unsupported nodes. Nine boundary, 22 frame, and 38 execution tests are defined. All three modules failed D1P-00 discovery solely because `Crypto.Hash.keccak` was unavailable. | **Reuse after dependency and artifact provisioning.** Add a symbolic lowering that is checked against this concrete interpreter; do not import the weaker synthetic consumer walk as the real consumer. |
| Claude ACIR adapter and exact propagation: `frontends/acir.py`, `analysis/propagate.py` | `2009815848c7d67a12d812c3dbd6c07643b41afd` | Exact legacy parser hash; beta.14 printed ACIR/ABI; Python stdlib | Sequential ABI flattening; only one function; no returns; recursion proof slice may be accepted by length only. Propagation retains/substitutes polynomial constraints and resolves memory only with known indices. Covered as part of 15 synthetic tests. | **Selective logic reuse.** Port propagation/index concepts behind the typed decoder and new tests. Reject sequential-layout and length-only binding where the Codex certificate path can prove more. |
| Claude joint encoder, policy, result envelope: `analysis/joint.py`, `policy.py`, `result.py` | `2009815848c7d67a12d812c3dbd6c07643b41afd` | Legacy FF builder and cvc5 | Uniform three-word stride only; no real consumer execution; pad is treated as another valid fixed-stride record; matching permits the same permission to satisfy multiple effects; owned-role/token facts are assumptions. Fifteen synthetic tests use authored N=9 fixtures. | **Do not port as an implementation.** Retain as a design reference for query plumbing. Rebuild goals from V2 occurrence semantics and the source-bound consumer relation. |
| Claude consumer-directed refinement: `analysis/refinement.py` | `1b4d5683d87cd8f71b37e140d0b99c9fd21b856f` | Claude joint encoder; cvc5 | Authorization only. Starts with zero producer constraints, concretizes stream values against all residual ACIR constraints, then adds direct plus one-hop constraints. Sixteen historical tests cover the authored N=9 fixtures; every refinement selected all 26/35 constraints and was 3–9% slower than monolithic solving. | **Selectively reimplement, do not cherry-pick.** Preserve abstract-solve/concretize/refine control flow and logs, but operate on V2 observations, checked summaries, occurrence multiplicity, decoder/consumer state, cache identities, and explicit per-iteration budgets. |
| Claude Solidity frontend: `frontends/solidity.py` | `2009815848c7d67a12d812c3dbd6c07643b41afd` | solc JSON AST | Hand-supported subset with A4/A5/A7 assumptions. The Claude reports state it was not exercised in D1-03 and no consumer contract was part of the claimed synthetic result. | **Reject in favor of the Codex boundary/frame/execution line.** Useful only as a checklist of unsupported AST shapes. |
| Claude synthetic fixtures, runners, and closing reports | Core/refinement through `1b4d5683...`; closing tip `9d90b93e...` | nargo, cvc5, Forge; committed generated targets/output | Authored N=9, uniform stride, no recursion/hashing, no actual consumer replay. Reports label nargo executions `CONCRETE_MODEL_REPLAYED` and close D1 despite the real-consumer and N=8 gates remaining unmet. | **Preserve as historical negative/synthetic evidence only.** Do not port generated `target/`, `out-synth/`, closure status, or verdict promotion. Small source fixtures may later be recreated only under a new protocol. |
| Historical real-proof consumer harnesses: `payy-consumer/test/{MintSettlement,BurnPropagation,RepairedMintControl}.t.sol` and T13/T16/T18/T19 scripts/reports | Harness line last changed `51434d4410d2896060101f24676ca7cd0f57b219` | Forge 1.4.1; solc 0.8.20; forge-std; OZ 5.0.1; revision-matched RollupV1/verifier binaries; proof/public-input bundles | T18 uses revision A `c4d2c902...`, owned roles, real verifier, 1003 inputs, and checks committed balances. T19 uses repaired revision B controls. Historical shell runners delete output paths and must not be rerun against preserved evidence. | **Reuse harness logic and exact artifact hashes.** Import inputs into a fresh namespace and use a new non-cleaning runner. Keep revision/key/proof identities separate and treat N=1000 replay as a different evidence grade from N=8 solver work. |
| Proof capture/replay preparation: `d1_bb_recorder.py`, `d1_proof_recovery_{prove,replay}.py` | `cce1a966eb84e8e9819c6f658ca4ce07fd670036` | Pinned Rust 1.91/Linux bb for recovery; source checkout; Forge stack | Prepared for a new honest mint chain, 1003 inputs, and one successful captured proof. The historical two-build budget is exhausted and the second Linux link failed at 4 GiB. | **Reuse recorder and manifest patterns only.** Do not rerun the exhausted recovery task. Add a separate existing-bundle importer/replayer for T13/T16; make all paths configurable for macOS and fresh output roots. |

## 4. Artifact and platform availability

The destination intentionally contains none of the ignored toolchains, build
outputs, or raw proof data. The local preservation checkout has useful inputs,
but the workspace guide forbids making new work depend silently on its mutable
caches. A later task must copy exact inputs into a fresh ignored namespace and
seal them in a manifest.

| Requirement | D1 worktree | Local preservation checkout / host | Consequence |
| --- | --- | --- | --- |
| Six exact v5 SMT queries and the two printed ACIR/ABI pairs | Available: four tracked inputs under `results/artifacts/d1-n8/`; six ignored byte-matching queries under `results/raw/D1P-02/generated/` | Evidence commit `7d098cd3...` and frozen manifest bind the input bytes | D1P-02 closes artifact intake. Any future query run must copy/audit into a fresh namespace and retain the six historical UNKNOWN outcomes. |
| cvc5 1.4.2 with finite-field split/CoCoA | Not copied into this worktree | GPL/CoCoA arm64 binary present under `BindCheck/tools`; SHA-256 `a083a7f5...`; PATH also has a different unrestricted build | D1P-07 completes the native-Mac within-campaign Track A comparison. Historical Linux remains background and no timing/resource parity claim is allowed. |
| nargo/noirc beta.14 | Missing | Correct pinned arm64 binary present under `BindCheck/tools/noir-1.0.0-beta.14` | Available for a later separately authorized rebuild; no compile ran in D1P-00. |
| T13 mint proof/input | Missing | Present: 10,560/32,096 bytes; SHA-256 `10eb689c...` / `2a0f2b2a...` | Eligible for a manifest-backed honest control after revision/key checks. |
| T16 control and candidate proof/input | Missing | Present; control `4e7f214f...` / `2a0f2b2a...`, candidate `cdf4b9de...` / `b6f92efa...` | Eligible for an existing-bundle real replay after copying and checking T16 summary/key/source identities. |
| Revision-matched verifier binaries and RollupV1 source | Missing | T12/T18 binaries and Payy revision worktrees present | Available, but must stay paired to the correct proof/key revision. |
| Forge stack | Forge on PATH | Forge 1.4.1; solc 0.8.20 exists under `~/.svm`; forge-std and OZ 5.0.1 exist only in preservation checkout | Build an isolated replay tree with explicit remappings. Default `solc` is 0.8.30 and must not be used accidentally. |
| bb | Missing local tool tree/PATH | arm64 `3.0.0-manual.20251030` present; differs from the historical Linux recovery package | Sufficient for a later native verification compatibility check only after pinning; no proof build is authorized here. |
| Codex Python dependency | `.venv-d1p-00` contains `pycryptodome==3.23.0` | Python 3.13.7; full D1P-07 pre-freeze discovery passes 154 tests | Use the isolated environment; D1P-00's incomplete result remains historical. D1P-05/D1P-07 tests launch harmless helpers but no solver. |
| Rust recovery toolchain | Host Rust/Cargo 1.99 | Historical recovery pinned Rust 1.91 and Linux-specific linker setup | Do not reuse the old build command on macOS or treat host availability as recovery readiness. |

## 5. Semantic conflicts requiring planner decisions

1. **Experiment target.** The six T22 queries are producer-side
   non-vacuity/prefix/tail obligations. D1's primary properties are
   occurrence-level authorization and coverage across producer, decoder, and
   consumer. Decide whether D1P's first N=8 result is a frozen T22 comparison,
   a new D1 joint query, or both reported separately.
2. **Permissions and obligations.** The Claude fixture supplies a private
   `authorized` array. Payy supplies recursive proof inputs and messages, not
   that authored abstraction. Freeze how P and O are derived without asserting
   the implementation binding under test.
3. **Producer walk versus consumer decoding.** The N=8 producer specification
   uses active-frame lengths 2→4 and 3/4→5 and stops export at the first other
   kind. The actual consumer instead uses a verifier-configured length, advances
   one word for kind 0, consumes four for kind 2 and five for kind 3, and reverts
   on kind 4 or any other kind; truncated record reads also revert. The Claude
   joint encoder's uniform length-three walk matches neither relation. Track B
   must encode both relations and their forwarding link separately.
4. **Multiplicity.** The Claude goals allow reuse of one matching permission;
   V2 requires occurrence identity and exact multiset discharge. The integrated
   method must use the V2 rule.
5. **Concretization evidence.** Full-ACIR SAT is a concrete model check, not a
   proof, reachable consumer execution, or committed effect. Freeze evidence
   grades before importing the CEGAR loop.
6. **Consumer success family.** Decide whether the initial theorem retains the
   V2 funded standard-token restriction. Failed transfers and unimplemented
   deferral must remain UNKNOWN if that restriction is relaxed.
7. **Field/EVM crossings.** Freeze canonicality, integer ranges, bytes32
   decoding, address truncation, token amount bounds, and state/caller
   assumptions before a new joint query.
8. **N=8 versus replay scale.** Available real proofs use the original
   1,000-message/1,003-public-input consumer. They cannot validate a scaled N=8
   query. Report N=8 solver evidence and N=1000 real replay as separate grades
   unless a new revision-matched N=8 proving/consumer path is explicitly built.
9. **Branch conclusions.** `claude-code` closes D1 on synthetic evidence;
   `chatgpt-codex` keeps D1-03 incomplete. Under the research contract and real
   consumer requirements, the integration baseline retains UNKNOWN. Planners
   must decide whether the paper studies the negative result, reopens a bounded
   method experiment, or narrows the claim.

## 6. Baseline tests

The documented Codex command is:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-d1.txt
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests/d1 -v
```

D1P-00 used isolated `.venv-d1p-00` with Python 3.13.7 and pip 25.2.
Installation of `pycryptodome==3.23.0` failed after five connection retries
because PyPI was unreachable; no alternate or unpinned dependency was used.
Running the suite anyway returned exit 1: unittest reported 31 entries in
0.007 seconds, with 27 passing test methods and four import errors
(`test_consumer_boundary`, `test_consumer_execution`, `test_guard_frame`, and
`test_v2_core`), all `ModuleNotFoundError: Crypto`. Those four modules contain
92 additional test methods, so the source-defined total is 119. There were no
assertion failures among tests that loaded.

## 7. D1P-01 implementation checkpoint

On 25 October 2026, [D1P-01](../../reports/D1P-01.md) completed the exact
Python dependency baseline and the path-neutral, provenance-checked intake
implementation. The pre-change documented suite passes 119/119; the
post-change suite passes 124/124. Five focused intake controls and the separate
65,536-vector compact-walk self-check pass. The adapter validates the frozen
manifest, parser, encoder, protocol, specification, and both ACIR/ABI pairs
before output; its serialization-only sink cannot return a solver status and
its process-launch boundary fails closed.

Artifact recovery is **BLOCKED**: bounded searches of only the recorded local
evidence locations found none of the four exact input files, so D1P-01 did not
generate or claim a match for any of the six historical v5 queries. The report
contains the exact archive request and a reviewed, unexecuted reconstruction
recipe pinned to the Payy B revision, beta.14/noirc revision, historical
scaling, and running-flag transformation. Research verdict remains UNKNOWN.

## 8. D1P-02 archive byte-gate checkpoint

On 25 October 2026, [D1P-02](../../reports/D1P-02.md) validated all four
recovered inputs as byte-identical to evidence commit
`7d098cd393c5cc8609765b663d393fcaebf24aeb` and as exact matches for the
frozen D1-01 manifest. The unchanged D1P-01 adapter then serialized all six v5
queries into `results/raw/D1P-02/generated/`; every SHA-256 matched the frozen
historical identity. The adapter and independent audit record zero solver
processes and no solver record. The D1P-01 artifact blocker is resolved, but
the research verdict remains UNKNOWN.

This establishes same-implementation query-byte reproducibility, not parser,
cone, encoding, specification, solver, proof, or consumer correctness. The six
historical primary outcomes remain timeouts/UNKNOWN, the goal-only v3-derived
timeout remains separate from v5 specification-only SAT diagnostics, and N=8
producer queries remain a different evidence grade from N=1000 real-proof
consumer replay.

## 9. D1P-03 protocol and offline-check checkpoint

On 25 October 2026, [D1P-03](../../reports/D1P-03.md) produced the
[review protocol](d1p-03-protocol.md) without executing a solver. It separates
Track A's exact six selected-cone producer queries from an unimplemented Track
B joint producer/decoder/consumer experiment; `C` is explicitly the selected
cone, not the full producer relation. The protocol defines goal-only,
cone-only, combined, and 25-cell diagnostics, labels SAT/UNSAT directions only
as expectations, retains V2 P/O/E and funded/no-substitution scope, separates
concrete-model from real-proof evidence, and freezes numeric fair-budget and
stopping rules for review.

The independent offline checker exhaustively covers 781,250 activation/word-
class stream cases, all 25 cell pairs, and 12,825 goal cases. Coverage,
exclusion, and specialized walk/goal equivalence pass, including inactive,
overflow, and truncated-record cases. This is finite specification-rewrite
evidence only: no ACIR, SMT, solver, proof, consumer, or security claim follows.

## 10. D1P-04 transformation checkpoint

On 25 October 2026, [D1P-04](../../reports/D1P-04.md) added the corrected
[prospective protocol](d1p-04-protocol.md), a serialization-only specializer,
and a frozen equivalence plan. The corrected Track B design has five methods
and 140 method-slots, treats partitioning as a shared factor, gives each method
its own candidate/final-validation allowance, charges refinement internally,
and preserves the V2 policy/evidence limits. Track B remains unimplemented.

The specializer generated 150 cell queries and 150 producer-free XOR
equivalence queries from the six exact D1P-02 parents. The manifest records
parent, predicate, generator, output and equivalence hashes, rank/offset
mapping, and 150/150 passing byte audits of the complete ordered producer
prefix. Six focused tests and the complete 134-test D1 suite pass without
solver calls.

SMT validation is **INCOMPLETE**. The frozen validator accepted every identity
but macOS rejected its 4 GiB `RLIMIT_AS` child pre-exec assignment before the
known-equivalence control could execute cvc5. The one-attempt/no-retry rule
stopped the plan: zero solver processes/calls, 0/2 controls, and 0/150 cells
executed. The ledger explicitly marks all 152 records unrun. No cell and no
complete partition is eligible for primary use. No solver answer or D1 claim
follows.

## 11. D1P-05 equivalence-execution checkpoint

On 25 October 2026, [D1P-05](../../reports/D1P-05.md) preserved D1P-04 and
introduced a separately frozen macOS validation runner and
[resource policy](../../metadata/d1/d1p-05-resource-policy.json). The final
pre-freeze helper gate passes launch, timeout, descendant cleanup, sampled
tree-memory cutoff, monitoring-failure cleanup, and structured launch-error
checks without invoking a solver.

The runner independently matches all 152 query hashes, passes the expected
UNSAT and SAT controls, and obtains UNSAT with exit zero for all 150 cell XOR
queries. There are no timeouts, solver UNKNOWNs, cell SAT results, memory
cutoffs, execution errors, or unrun calls. All 150 producer-prefix audits pass.
The complete 25-cell specialization is eligible for later primary use at the
transformation-evidence level.

The 50 ms libproc policy monitors aggregate observed process-tree RSS and
kills the process group after an observed value above 4 GiB. It can overshoot
and is not a hard address-space cap. The 8.704804 seconds of solver-process
wall time and 9,322,496-byte maximum observed RSS are non-primary native-macOS
observations. They do not alter historical parent-query UNKNOWN results or
support timing parity, consumer effectiveness, proof, replay, or D1 claims.

## 12. D1P-06 Track A checkpoint

On 25 October 2026, [D1P-06](../../reports/D1P-06.md) prospectively changes
only the Track A reference platform to native macOS. Its input manifest
validates 166/166 hashes: two controls, six goal-only diagnostics, two
cone-only diagnostics, six unchanged combined parents, and 150 unchanged
specialized cells. The derivation audit removes producer constraints from
goal-only inputs and retains the complete producer prefix in cone-only inputs.
Seven focused and all 147 D1 tests pass.

The final harmless-helper preflight passes and the protocol, environment,
solver, resource policy, schedule, budgets and inputs are frozen before the
first solver call. The 50 ms recursive RSS cutoff is sampled, can overshoot,
and is not a hard address-space cap. Both controls pass and the first goal-only
diagnostic returns usable SAT. Call 4 writes SAT/witness text but encounters a
monitor-root exit race followed by an uncaught cleanup `PermissionError`, so
it is unusable/UNKNOWN. The infrastructure-stop rule leaves 162 calls unrun,
including every combined query and partitioned cell. Decomposition
effectiveness and the D1 verdict remain UNKNOWN.

## 13. D1P-07 race-safe Track A checkpoint

On 25 October 2026, [D1P-07](../../reports/D1P-07.md) preserves D1P-06 and
uses the planner's explicit authority for a new campaign beginning at call 1.
The repaired runner confirms missing-root exits with bounded reap, catches and
records cleanup errors, uses bounded group/direct termination, always writes
call and campaign ledgers, and represents missing memory observations as null.
Seven focused regressions, all 154 D1 tests and 13 harmless-helper checks pass.

The freeze binds the same 166 inputs, solver, order and budgets. Every call is
attempted exactly once in a fresh namespace. Six goal-only diagnostics return
SAT; both cone-only diagnostics and all six combined queries time out. Across
150 cells, 58 return UNSAT and 92 time out. Every partition therefore remains
UNKNOWN, as does every unsplit combined query. Partitioning improves zero
complete logical outcomes under the frozen budget. Its lower partial elapsed
time and cell-level UNSAT results are not a solved-result speedup and provide
no consumer-direction evidence. The D1 verdict remains UNKNOWN.

## 14. Next review gate

**Two-planner interpretation and Track B readiness review.** Decide whether
the paper retains this negative/partial producer-decomposition result and
whether the 50 ms timeout-enforcement granularity needs a separate hard-wall
validation. Do not retune or extend these Track A queries. Any continuation to
Track B must satisfy its existing joint producer/decoder/consumer,
equal-information baseline, policy and real-proof prerequisites. Research
verdict remains UNKNOWN.
