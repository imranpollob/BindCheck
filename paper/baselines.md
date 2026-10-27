# D1P-D02 — Baseline preregistration

**Status:** preregistration draft, 27 October 2026. **No tool was installed
or run.** Capabilities come from each tool's documentation or paper, as
cited. Anything not confirmed from such a source is marked
**[TODO-VERIFY]**. Fetched documentation, hashes and pins are in the
ignored `results/raw/D1P-D02/notes.json`.

**Framing used here.** The primary question is **capability**: can BindCheck
automatically discover *and validate* proof-to-execution mismatches that the
baselines below do not? **Efficiency** (solved obligations or cost under
equal information) is a secondary question and **untested**. Its only
current evidence is negative or null (D1P-07, D1P-10).

> **Revision D1P-D03 (27 October 2026)** applies planner corrections, listed
> in §8. [draft.md](draft.md) now uses the same capability framing. The
> research contract still controls until
> [contract-revision-proposal.md](contract-revision-proposal.md) is applied.

**Governing rules** (research contract §§8–9):

- Baselines get the same pinned artifacts, bounds, admitted states and
  policy roles as BindCheck in the equal-information comparison.
- An unsupported native frontend is **not** an algorithmic failure, and is
  reported separately.
- `UNKNOWN` is never counted as safe, and never as a semantic miss when the
  tool cannot accept the input.
- Payy and WarpToad are **development cases**. They can show capability on
  those cases, but not transfer, unbiased discovery or generality (§6).
- **Two comparison arms** for every applicable baseline: a
  **generic/default** arm (the tool's defaults, or the generic suite G1–G5)
  and a **same-policy** arm (the reviewed policy `σ` expressed through the
  tool's own property interface). If a tool has no property interface, its
  same-policy arm is recorded as *not applicable*.

---

## 1. Targets

| Target | Producer | Consumer | Known defect? | Role |
| --- | --- | --- | --- | --- |
| **Payy** earlier `c4d2c902…` / check-added `dcd5d96e…` | Noir `1.0.0-beta.14+60ccd48e…` ACIR (`agg_agg`, `agg_final`), bb 3.0.0 UltraHonk | `RollupV1.sol`, solc 0.8.20, Forge 1.4.1 ([integration plan](../docs/d1-paper/integration-plan.md) §4) | Yes: public advisory, locally reproduced (T15–T19) | Faulty/repaired development pair |
| **WarpToad** `973e7d1e…` | Noir `1.0.0-beta.22+c57152f9…` ACIR (`withdraw`), bb.js 5.0.0 UltraHonk `keccakZK` | `WarpToadCore.sol`, solc 0.8.29, Hardhat 3.3.0 EDR ([D1P-12R](../reports/D1P-12R.md) §4) | None known | Honest development fixture. **Not a proven negative control**: no defect is known, but absence is not established. |

The Noir tag `v1.0.0-beta.14` resolves to `60ccd48e…`, and `v1.0.0-beta.22`
to `c57152f9…`. These match the compiler identities recorded in the
artifacts.

---

## 2. Candidate baselines

### 2.1 Circuit / ZK baselines

| Baseline | What it analyzes (source) | Input languages / IR (source) | Accepts Payy? | Accepts WarpToad? |
| --- | --- | --- | --- | --- |
| **Noir compiler checks** | Two default compiler passes. The *under-constrained values* check flags values disconnected from both inputs and outputs. The *Brillig constraints* check flags unconstrained-call results not involved in a later constraint (Noir docs; disable flags `--skip-underconstrained-check`, `--skip-brillig-constraints-check`). | Noir source, inside `nargo` | **Yes, native** with the pinned beta.14 `nargo`. Flag names and behavior at beta.14: **[TODO-VERIFY]** (docs read were v1.0.0-rc.5/dev; versioned pages returned 404). | **Yes, native** with beta.22 `nargo`; same **[TODO-VERIFY]**. D1P-12R did not compile from source. |
| **CCC-Check** [draft ref 5] (public artifact [github.com/ArmanKolozyan/CCC-Check](https://github.com/ArmanKolozyan/CCC-Check), HEAD `7ed87b8c…` on 27 October 2026) | Computation–constraint inconsistencies via abstract-interpretation value inference (ePrint 2025/2120 abstract; artifact README). | The artifact README says analysis runs over the CirC intermediate representation. Which source frontends feed it natively: **[TODO-VERIFY]**, pending D1P-C02. | **[TODO-VERIFY]** pending D1P-C02 | **[TODO-VERIFY]** pending D1P-C02 |
| **Circomspect** v0.9.0 (`82e63df7…`) | Static analyzer and linter: named analysis passes, e.g. side-effect-free assignments and shadowing (README; `doc/analysis_passes.md`). | Circom only (README) | **Unsupported** (Noir) | **Unsupported** |
| **Picus** (`138b151d…`, no tags) | QED² uniqueness check for under-constrained signals; optional `--strong` safety and `--precondition` JSON (README). | Three documented input paths (README): Circom ≥ 2.0.6 source; **R1CS** binary in the iden3 `r1csfile` format; gnark `.sr1cs` | **Not as compiled.** The R1CS path is documented, but Payy's artifact is Noir ACIR, not iden3 R1CS. An ACIR→R1CS conversion would be our adapter, reported as *adapted* with its effort charged. Whether a faithful conversion exists: **[TODO-VERIFY]** | **Not as compiled** (same) |
| **CIVER** (`af7d4ed0…`, no tags) [draft ref 3] | Modular weak-safety (determinism), tag-specification and pre/postcondition verification (`--check_safety`, `--check_tags`, `--check_postconditions`) (README). | Circom. The README says R1CS/PLONK/ACIR inputs will be supported "soon". | **Unsupported natively** at the pinned commit. ACIR support: **[TODO-VERIFY]** | **Unsupported natively**; same |

**Scope caution, stated as reasoning, not a prediction.** Payy's outer
`messages` array and WarpToad's eleven fields are public **inputs** of the
proved relation. Determinism and uniqueness properties, as the CIVER and
Picus READMEs define them, concern **outputs** given inputs. Whether these
tools can express "public input word *i* is unconstrained" is
**[TODO-VERIFY]** from the papers. We do not assume they miss it.

### 2.2 Contract baselines

| Baseline | What it analyzes (source) | Languages (source) | Accepts Payy `RollupV1`? | Accepts `WarpToadCore`? |
| --- | --- | --- | --- | --- |
| **Slither** 0.11.6 (`050cc0a0…`) | Static analysis with a detector suite and printers (README). | Solidity ≥ 0.4 and Vyper (README) | **Yes** (solc 0.8.20). Behavior behind the OZ proxy: **[TODO-VERIFY]** | **Yes** (solc 0.8.29, via crytic-compile/Hardhat). Hardhat 3 support: **[TODO-VERIFY]** |
| **Mythril** v0.24.8 (`9e9ee39a…`) | Symbolic execution of EVM bytecode for security issues (README). The docs call symbolic executors generally unsound. | EVM bytecode / Solidity (README) | **Likely yes**; handling of the verifier's pairing precompile and the 1,003-word input: **[TODO-VERIFY]** | **Likely yes**; same precompile **[TODO-VERIFY]** |
| **Foundry invariants** v1.8.6 (`6bad0a66…`) | Stateful fuzzing of `invariant_*` functions over handler-targeted call sequences, configured by `runs`, `depth` and `fail_on_revert` (Foundry docs). | Solidity tests | **Yes** (existing Forge harness) | **Yes, with a port**: the D1P-12R fixture is a Hardhat/TypeScript harness |
| **Echidna** v2.3.3 (`4454f3a3…`) | Grammar-based property fuzzing; `property`, `assertion` and `foundry` test modes (README). | Solidity via crytic-compile: Foundry and Hardhat (README) | **Yes** | **Yes**; Hardhat 3: **[TODO-VERIFY]** |
| **SmartAxe** (artifact `InPlusLab/FSE24-SmartAxe@7ca21f72…`; tool on figshare) | Cross-chain bridge contracts: access-control incompleteness and deposit/withdraw semantic inconsistency over xCFG/xDFG (paper §§4.2–4.3). | EVM **bytecode** (paper §2.3) | **Applicability doubtful.** Payy is a rollup, not a source/destination bridge pair. Its xCFG needs deposit/withdraw event pairing. **[TODO-VERIFY]** | **Plausible.** WarpToad is a burn-to-mint bridge, but this fixture is same-chain. Tool runnability from figshare: **[TODO-VERIFY]** |

### 2.3 Joint baselines (all over the same extracted relation)

These are ablations or adaptations inside our own infrastructure. A
manual-summary joint encoder exists; its main diagnostic queries remain
unexecuted, and automatic consumer extraction is not established. **None of
the four baselines below has been run on a real target** (D1P-07/D1P-10
cover producer-only queries).

| Baseline | Definition | Current status |
| --- | --- | --- |
| **Monolithic joint** | One query over the complete supported producer relation, actual decoder, admitted consumer transition and policy. No summaries. | Not run as a joint query. The producer-only N=8 monolithic queries all time out (D1P-07, D1P-10). |
| **Goal-cone** | Monolithic query restricted to the dependency cone of the policy goal: the T22 selected cone, 620 ops / 540 witnesses at N=8. Dropping constraints is an **over-approximation**: the cone admits every assignment of the full relation and possibly more. An UNSAT result transfers to the full relation only if the encoding is faithful; a SAT result is only a candidate until checked against the full relation (E2). Fixing omitted witnesses is different: it under-approximates (contract §7). | Producer-only cone exists; all obligations `UNKNOWN` (D1P-07, D1P-10). |
| **Modular adaptation (CIVER-style)** | Producer-hierarchy summaries proved from retained constraints, with selective unfolding, over the same extracted facts. Labeled an **adaptation**, not CIVER (contract §9). | Not built |
| **Consumer-facts ablation** | The BindCheck method with consumer-derived facts **withheld from summary and constraint selection only**, e.g. the 11 reached-kind shapes and consumer-directed refinement choice. **All semantic guards stay in the query**: decoder, consumer guards, state, policy and goal. The ablation therefore changes what the method chooses to look at, not what the query means. | Not built. Shapes exist and remove 4–8 of 620 ops (D1P-09). |

---

## 3. Exact setup (frozen before any run)

### 3.1 Common rules

- **Pins.** Use the revisions in §2. Record binary SHA-256, `--version`
  output, solver and solc identities, and host before the first call.
- **No bug-specific assertions in either arm.** No assertion may name the
  Payy tail, the burn path, a specific index, a specific value or the fix.
  No WarpToad property may encode a suspected defect. The same-policy arm
  uses only the reviewed policy `σ` that BindCheck receives.
- **No candidate seeds.** Fuzzers may be seeded **only with honest proofs**:
  the T13 mint and T16 control for Payy, and the D1P-12R honest proof for
  WarpToad. The T15/T16 candidate tail proof is the defect itself and is
  never a seed.
- **Budgets (development caps).**
  - Mythril: 1,800 s per case.
  - Each fuzzer (Foundry invariants, Echidna): 3,600 s per case.
  - These are development caps. A baseline's effective cap is **never below
    BindCheck's per-case analysis budget**: if BindCheck receives more, the
    baseline gets the same.
  - **Setup and proving are declared separately**: compilation, deployment,
    honest-proof generation and harness construction are timed and
    reported, but not charged against the analysis cap.
  - Other tools (Slither, Noir checks, Circomspect, Picus, CIVER,
    CCC-Check, SmartAxe) run to completion under the same never-below rule,
    with a hard stop **[TODO]** frozen before the first run.
- **Default configurations.** The generic arm runs each tool at its
  documented defaults, plus at most one predeclared non-default
  configuration, listed below. No tuning after results are seen.

### 3.2 Per-tool setup (both arms)

| Baseline | Generic/default arm | Same-policy arm (`σ`) |
| --- | --- | --- |
| Noir checks | `nargo compile` and `nargo check` at the pinned version with default checks on; plus once with `--enable-brillig-constraints-check-lookback` if the flag exists. Payy: both revisions. WarpToad: a compile from source is a **new rebuild**, reported separately from D1P-12R's validated artifact. | *Not applicable*: no user-property interface |
| CCC-Check | Artifact defaults | Through the artifact's annotation/tag mechanism, if `σ` is expressible: **[TODO-VERIFY]** pending D1P-C02 |
| Circomspect | *Unsupported* natively (Noir) | *Not applicable*: lint passes only |
| Picus | *Not as compiled*. Optional *adapted* run through the documented R1CS path, only if a conversion is predeclared and charged: `run-picus --solver cvc5`, default timeout, plus one `--strong` run. | *Not applicable*: uniqueness only; `--precondition` constrains assumptions, not properties **[TODO-VERIFY]** |
| CIVER | *Unsupported* natively; optional *adapted* `--check_safety` | Adapted `--check_postconditions` with `σ`-derived pre/postconditions, if an adaptation exists |
| Slither | `slither <target> --json out.json`, all default detectors | A custom detector encoding `σ`'s provenance checks through the detector API, effort charged. Run if built; otherwise *not run*, with the reason. |
| Mythril | `myth analyze` on consumer bytecode, default modules | `σ` as Solidity `assert` in a wrapper, so assertion-violation reports apply |
| Foundry invariants | G1–G5 (§3.3) where justified; `[invariant] runs=256, depth=100, fail_on_revert=false` | `σ` property in the T14 `MintProperty` style, as an invariant over the same handlers |
| Echidna | Same justified G1–G5 in `foundry` test mode; default `testLimit`/`seqLen` | Same `σ` property |
| SmartAxe | Figshare artifact defaults on consumer bytecode; *unsupported* if no deposit/withdraw pairing is accepted | *Not applicable*: no user-property interface |
| Joint baselines | *Not applicable*: they use `σ` by construction | Same extracted relation, `σ`, bounds, solver (cvc5 1.4.2 `--ff-solver=split`) and limits as BindCheck: monolithic / goal-cone / modular adaptation / consumer-facts ablation |

### 3.3 Generic invariant suite (G1–G5) with protocol justification

The templates are application-agnostic and instantiated only with role
names. They do **not** use `σ`. **An invariant runs on a target only if the
protocol's own source or documentation justifies it there.** An unjustified
invariant would turn into an unfounded false alarm or a vacuous pass.

| ID | Invariant | Payy justification | WarpToad justification |
| --- | --- | --- | --- |
| **G1 Replay** | Resubmitting identical accepted calldata reverts or changes no protected state. | `verifyRootHash` requires `oldRoot == rootHash`, and `verifyMint` marks `mints[hash]` spent ([T17](../reports/T17.md) §§1, 3) | The nullifier is intended single-use; `mint` checks and records it ([D1P-12R](../reports/D1P-12R.md) §§8.1–8.2) |
| **G2 Revert atomicity** | A reverted call changes no protected state. | The consumer writes state before later checks and relies on revert rollback (T17 §1 call order) | The early nullifier write relies on rollback (D1P-12R §8.2) |
| **G3 Solvency** | Cumulative asset outflow from the consumer ≤ cumulative inflow. | `mint()` escrows tokens into the consumer, and burns pay out from that balance (T17 §3; T18 §1) | **Not justified yet.** A burn-to-mint bridge may mint on a destination without local backing by design. Not run until the intended backing policy is documented. **[TODO-VERIFY]** |
| **G4 Supply accounting** | Total supply changes exactly by net mint/burn transfer events. | **Not applicable**: the consumer mints no token; the asset is an external ERC20 | ERC-20 transfer-event convention for the wrapped token that `WarpToadCore` mints (D1P-12R §6). Same-chain fixture only. |
| **G5 Verifier gating** | Every successful entry-point call invoked the verifier, and the verifier returned true. | `verifyRollup` calls the registered verifier before state update (T17 §1) | `mint` calls the fixed verifier before minting (D1P-12R §8.2) |

---

## 4. Outcome classes and the warning/effect rule

### 4.1 Classes (one per tool × target × revision)

| Class | Definition |
| --- | --- |
| **detected** | The tool emits a relevant **E1** warning or **E2** model that meets the predeclared localization criterion (§4.3) for a known defect, or a candidate later validated to **E4** (§4.2). The highest level reached is recorded with the class. |
| **missed** | The tool accepted the input, ran to completion within budget, and emitted no report meeting the criterion. |
| **unsupported** | The tool cannot ingest the target natively (language, IR, version, frontend), or its documented scope excludes the target (e.g. no bridge pairing). This is never counted as a miss. |
| **unresolved** | Timeout, crash, memory stop, `UNKNOWN`, or a report that cannot be adjudicated within the adjudication budget. This is never counted as safe. |

Every other report is a **non-target report**. It is **not** automatically
a false alarm. Each one is adjudicated separately into one of three
outcomes: false alarm, real but out-of-scope issue, or new candidate. A new
candidate goes through the same validation process (§4.2) and, if
confirmed, through disclosure (contract §9). It is reported separately.
Adjudication time is recorded (§5).

### 4.2 Evidence ladder: a warning is not an unauthorized effect

| Level | Meaning |
| --- | --- |
| **E0** | No report |
| **E1 Warning** | A tool report (lint, under-constrained flag, detector hit, abstract SAT) |
| **E2 Concrete relation model** | An assignment satisfying the *actual* compiled producer relation, decoder and consumer model (contract §8, conditional violation) |
| **E3 Accepted proof** | A real proof of that assignment accepted by the pinned, unchanged verifier |
| **E4 End-to-end validated mismatch** | That proof submitted to the unchanged consumer from a reachable or admitted state, producing a committed protected effect with no compatible permission in `P` under `σ` (authorization), or leaving a required obligation in `O` undischarged (coverage). Effects are checked on state, e.g. `balanceOf`, not on events. |

**"Unchanged" for mutants.** For a seeded or historical variant,
"unchanged" means the **frozen variant under test with its own matching
verification key and verifier**, never another revision's key. This follows
the T18/T19 rule of never mixing artifacts across revisions.

**Rules.**

1. **Only E4 is an "end-to-end validated mismatch".** An E1 warning or E2
   model is never reported as an unauthorized effect.
2. **Detection credit at E1/E2.** A relevant E1 warning or E2 model that
   meets §4.3 still earns detection credit, recorded at its level. This
   holds for BindCheck and for every baseline.
3. **Same validation process for everyone.** Every baseline candidate that
   reaches E1 or E2 is taken through the same E2→E3→E4 validation pipeline,
   budget and adjudicator as BindCheck's candidates. The pipeline is
   charged separately from the tool's analysis cap. A baseline candidate
   that validates to E4 counts as end-to-end validated for that baseline.
4. **Automated vs. manual.** The capability claim needs BindCheck to
   *discover* and *validate* automatically. Hand-performed steps are charged
   as analyst effort and disclosed. On Payy, the E4 artifact from T18 was
   built by hand after the advisory, so it does not count as a tool's
   validation.

### 4.3 Localization criteria (scoring only, never tool input)

- **Payy producer locus:** a report that identifies the `agg_agg` outer
  `messages` words at indices ≥ `messages_index` as unconstrained, or the
  absence of a tail-zero constraint.
- **Payy consumer locus:** a report that identifies the `verifyBurn` /
  `executeBurn` path as executing a transfer from proof-derived words
  without provenance or registration.
- **Payy repair:** at `dcd5d96e…`, a report on either locus is adjudicated
  like any non-target report. It is not presumed false: the repair was
  validated for one witness only (T19).
- **WarpToad:** no known defect, and not a proven negative control. Any
  report is adjudicated. Only a validated candidate counts as a finding.

A report on another location, e.g. Slither's unchecked low-level call on
`executeBurn`, is a non-target report. It is not target detection, and it
is adjudicated separately.

---

## 5. Specification-effort measures

These compare BindCheck with a **hand-written Foundry property** built from
the same reviewed policy `σ`. This is the equal-information contract
baseline in the style of [T14](../reports/T14.md) `MintProperty`, and is
separate from the generic G1–G5 suite.

| Measure | BindCheck | Hand-written Foundry property |
| --- | --- | --- |
| Policy specification size | Non-blank, non-comment lines of `σ` | Non-blank, non-comment lines of the property function |
| Re-implemented semantics | Lines of manual implementation summaries marked `ASSUMED` (should be 0) | Lines re-implementing decoder/grammar/helpers (T14: about 87 non-comment lines in total for Payy mint) |
| Semantic role annotations | Count of roles assigned (amount, recipient, identity, …) | Count of fields the property names |
| Adapter/harness code | Lines of case-specific adapter code | Lines of setup, deployment and handler code |
| Authoring time | Wall-clock, logged start and stop per artifact | Same |
| Correction count and time | Edits after the first run, with reason | Same |
| Proof seeds required | Number of real proofs and their proving time | Same |
| Adjudication time | Minutes per report to reach a class | Same |
| Total analyst time | Sum of the above | Sum |
| Transfer cost | Same measures on the second target, with reused-vs-new lines split | Same |

**Integrity rules.** Authorship is recorded for every artifact. AI-authored
specifications are labeled, and human inspection time is logged separately
(contract §10). The BindCheck policy and the Foundry property must not share
an author's reading of the defect. Either author them independently, or
disclose the shared reading as in T14. All effort measures are descriptive
and are not compared statistically.

---

## 6. What these results can and cannot show

- **Development cases (Payy, WarpToad).** They **can** show capability
  *on those cases*: whether BindCheck and each baseline discover and
  validate the mismatch there, and at what effort. They **cannot** show:
  - **transfer**, because the method may be shaped by these cases;
  - **unbiased discovery**, because the Payy defect and its E4 artifact
    were known before the method existed, and WarpToad was inspected in
    D1-02, D1P-11 and D1P-12R; or
  - **generality** beyond these applications.
- **WarpToad reports** are adjudicated, not counted as false alarms by
  default. The fixture is honest but not a proven negative control.
- **Held-out families** must be inventoried and frozen before BindCheck
  runs on them (contract §9). None exists yet. Transfer, unbiased discovery
  and generality claims all need one.
- Efficiency comparisons (§2.3) are secondary and untested. A tie with the
  modular adaptation would undermine any efficiency claim (contract §11).

## 7. Open items

1. Read the CIVER and CCC-Check full texts and resolve every
   **[TODO-VERIFY]** on public-input expressiveness and on frontend
   support.
2. Confirm the Noir check flags at beta.14 and beta.22 with
   `nargo --help`. This is a documentation step, not an analysis run.
3. Freeze hard stops for the non-fuzzer, non-Mythril tools (§3.1).
   Mythril (1,800 s) and the fuzzers (3,600 s) are set.
4. Decide whether to build an ACIR→R1CS adapter for Picus or CIVER, or to
   record them as *unsupported / not as compiled* only.
5. Check that the SmartAxe figshare artifact runs, and whether it accepts a
   single-chain target.
6. Resolve CCC-Check native input support in D1P-C02.
7. Document WarpToad's intended backing policy before deciding G3 there.
8. Decide whether the Slither same-policy custom detector is built.

## 8. D1P-D03 revision log

Planner corrections applied 27 October 2026:

- **Goal-cone.** Dropping constraints is an over-approximation (it was
  wrongly called an under-approximation).
- **Consumer-facts ablation.** Withholds information from selection only;
  all semantic guards stay.
- **Non-target reports.** Adjudicated separately; never automatically false
  alarms.
- **WarpToad.** Not a proven negative control.
- **CCC-Check.** Public artifact recorded; native input support stays
  [TODO-VERIFY] pending D1P-C02.
- **Picus.** Its documented R1CS input path is recorded.
- **Budgets.** Mythril 1,800 s and fuzzers 3,600 s, as development caps
  never below BindCheck's per-case budget; setup and proving declared
  separately.
- **Two arms.** Generic/default and same-policy arms for every applicable
  baseline.
- **Fuzzer invariants.** Each must be justified by the protocol per target.
- **E0–E4 credit.** Only E4 is an end-to-end validated mismatch; E1/E2 earn
  detection credit; one validation process for all candidates; mutant
  "unchanged" means the frozen variant with its matching key.
- **Development cases.** Can show capability on those cases, but not
  transfer, unbiased discovery or generality.
