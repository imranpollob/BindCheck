# D1 paper integration plan

Date: **25 October 2026**. Preparation task: **D1P-00 DONE**. Research
verdict: **UNKNOWN**. This plan records an integration boundary; it does not
establish a D1 security result, solver result, proof result, or paper claim.

## 1. Workspace and reviewed revisions

The integration worktree is
`/Users/imranpollob/Coding/bc/bindcheck-d1-paper`, branch `d1-paper`, at
`cce1a966eb84e8e9819c6f658ca4ce07fd670036`. The branch already existed at
the `chatgpt-codex` tip; its previous registered worktree directory was
missing and marked prunable. `git worktree add --force ... d1-paper`
reattached that branch without creating, resetting, merging, or rewriting it.
At intake, `d1-paper` and `chatgpt-codex` had identical trees and revisions.

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
| Exact N=8 input/query bundle | Payy B source `dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36`; noirc `60ccd48e18ad8ce50d5ecda9baf813b712145051` | Check-added and running-flag printed ACIR/ABI; six SMT files; matching solver | Tracked metadata records their hashes, but the exact printed artifacts and six v5 SMT files are absent from all three linked worktrees and the local preservation checkout. Older T22 SMT files are not substitutes. | **Missing prerequisite.** Restore exact hash-matching copies from an archive, or authorize a separately versioned rebuild. Until then the N=8 experiment is not runnable. |
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
| Six exact v5 SMT queries and the two printed ACIR/ABI pairs | Missing | Missing; only older T22 SMT files found | Blocks byte-reproduction and all six N=8 executions. Tracked expected hashes remain available. |
| cvc5 1.4.2 with finite-field split/CoCoA | Missing local tool tree | GPL/CoCoA arm64 binary present under `BindCheck/tools`; PATH also has a different unrestricted build | Copy and hash-pin the intended binary; do not compare timing across the historical Linux binary without disclosing platform change. |
| nargo/noirc beta.14 | Missing | Correct pinned arm64 binary present under `BindCheck/tools/noir-1.0.0-beta.14` | Available for a later separately authorized rebuild; no compile ran in D1P-00. |
| T13 mint proof/input | Missing | Present: 10,560/32,096 bytes; SHA-256 `10eb689c...` / `2a0f2b2a...` | Eligible for a manifest-backed honest control after revision/key checks. |
| T16 control and candidate proof/input | Missing | Present; control `4e7f214f...` / `2a0f2b2a...`, candidate `cdf4b9de...` / `b6f92efa...` | Eligible for an existing-bundle real replay after copying and checking T16 summary/key/source identities. |
| Revision-matched verifier binaries and RollupV1 source | Missing | T12/T18 binaries and Payy revision worktrees present | Available, but must stay paired to the correct proof/key revision. |
| Forge stack | Forge on PATH | Forge 1.4.1; solc 0.8.20 exists under `~/.svm`; forge-std and OZ 5.0.1 exist only in preservation checkout | Build an isolated replay tree with explicit remappings. Default `solc` is 0.8.30 and must not be used accidentally. |
| bb | Missing local tool tree/PATH | arm64 `3.0.0-manual.20251030` present; differs from the historical Linux recovery package | Sufficient for a later native verification compatibility check only after pinning; no proof build is authorized here. |
| Codex Python dependency | `pycryptodome==3.23.0` not installed | No local wheel or installed copy found; PyPI unavailable from sandbox | Current unit baseline is incomplete for four modules. Provision a pinned wheel before claiming a clean suite. |
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
3. **Record grammar and termination.** Real Payy uses variable lengths
   2→4 and 3/4→5 and stops at the first invalid kind. The Claude joint encoder
   assumes uniform length three and does not model pad/end as termination.
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

## 8. Minimal next implementation task

**D1P-02 — Archive-backed N=8 restore and byte gate.** Supply the precise
archive requested by D1P-01, copy its four inputs into a fresh ignored D1P
namespace, and run the completed adapter without invoking cvc5. It must:

- match all four ACIR/ABI SHA-256 identities before query generation;
- preserve any incompatible archive or reconstruction under distinct
  provenance rather than substituting it;
- serialize all six queries and match their SHA-256 values recorded in
  `metadata/d1/d1-01-execution-manifest.json`;
- emit the adapter's fresh manifest in the new D1P namespace; and
- launch no solver and preserve all historical outputs.

Completion is 4/4 exact input matches plus 6/6 exact query matches, or one
precise incompatible-artifact report. This is the smallest remaining gate
before a separately authorized N=8 solver experiment; it does not port the
refinement engine or establish a security verdict.
