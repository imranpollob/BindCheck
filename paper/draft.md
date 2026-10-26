# [Title TBD]: Checking That Accepted Zero-Knowledge Proofs Justify Application Effects

**Draft status:** D1P-D01 evidence-based skeleton, 26 October 2026. Target
format is IEEE S&P. No new experiment was run for this draft. Every claim
below is tied to an existing report, the research contract, or a primary
source. Unsupported claims are marked **[TODO-EVIDENCE]**. Comparisons that
could not be checked against the cited paper's full text are marked
**[TODO-VERIFY]**.

**Controlling sources:** [research contract](../docs/research-contract.md)
(revision 1, 23 October 2026), [Payy case study](../docs/payy-case-study.md),
[T15](../reports/T15.md)–[T20](../reports/T20.md), [D1P-07](../reports/D1P-07.md),
[D1P-09](../reports/D1P-09.md), [D1P-10](../reports/D1P-10.md),
[D1P-11](../reports/D1P-11.md), and the
[D1 reference proposal](../docs/d1/reference-proposal.md). If this draft
disagrees with any of these, the source wins.

**Research verdict at drafting time:** `UNKNOWN`. No D1 method result exists.

---

## Contribution: UNDECIDED

The paper does not yet have a defensible contribution claim. Two framings
remain open, and the evidence currently supports neither:

| Candidate framing | Claim it would need | Current state |
| --- | --- | --- |
| **Efficiency.** Consumer-directed selection and refinement solve more obligations, or solve them at lower total cost, than equal-information monolithic and CIVER-style modular baselines (RQ2). | A measured advantage on frozen controls under equal bounds, information, and solver portfolio. | **Not established.** On the only real N=8 target, every combined producer obligation is still `UNKNOWN` (D1P-07, D1P-10). Consumer shapes remove only 4–8 of 620 selected-cone operations (D1P-09). Historical synthetic refinement was 3–9% *slower* than monolithic solving (historical, see §VI-D). |
| **Capability.** The joint producer/decoder/consumer analysis finds violations, or gives bounded guarantees, that direct contract tests with the same valid proofs and policy cannot (RQ4). | Confirmed findings or bounded guarantees that the baseline does not obtain, on held-out applications. | **Not established.** On Payy the hand-written checker and a direct Foundry assertion were functionally equivalent ([T14](../reports/T14.md) §4). No joint encoder exists for a real target. |

The contract's stop rule applies. A tie with a routine modular adapter,
hand-supplied correspondence, or infeasible independent proving paths would
undermine the contribution ([contract](../docs/research-contract.md) §11).
**Pick one framing only after the evidence in §V exists.**

---

## Abstract

> **[PLACEHOLDER — do not write until the contribution is decided.]**
>
> Fixed content: a valid proof establishes only the relation its circuit
> encodes; the consuming contract may perform effects that relation does not
> authorize. Motivating case: a publicly disclosed Payy defect, reproduced
> locally with real proofs. Method: **[TODO-EVIDENCE]**. Results:
> **[TODO-EVIDENCE]**. Transfer: **[TODO-EVIDENCE]**.

---

## I. Introduction

### A. A valid proof is not a valid effect

A zero-knowledge verifier accepts a proof when the public statement satisfies
the relation encoded by the circuit and the verification key. A blockchain
contract then decodes the public values and changes balances or state. The
security question crosses this boundary. Does every committed effect follow
from something the proof actually establishes? Correct cryptography does not
settle this. The SNARK SoK of Chaliasos et al. classifies such failures as
integration-layer vulnerabilities and reports that it found no defense
targeting that layer [1, §§6, 8].

### B. Motivating example: Payy's message tail

We use a publicly disclosed defect in Payy's Noir/Solidity rollup
(GHSA-fhxc-63vg-9gwr, CVE-2026-48100, published 10 June 2026) [2]. This is a
**known disclosure, not a new finding.** We rebuilt its mechanism locally,
with real proofs, from public source at pinned commits. The earlier commit is
`c4d2c902…` (no outer-tail assertion); the check-added commit is `dcd5d96e…`.
The consumer source is byte-identical at both commits
([case study](../docs/payy-case-study.md); [T15](../reports/T15.md) §1).

**Mechanism.** The `agg_agg` circuit merges inner proofs and exports a
1,000-word public `messages` array. A counter `messages_index` marks the end
of the active messages. At the earlier commit the circuit binds every word
below the counter to the inner proofs, but **no assertion reads words at or
above it** ([T15](../reports/T15.md) §1). `agg_final` copies these words
unchanged into its own public inputs ([T16](../reports/T16.md) §1). The
Solidity consumer `RollupV1.verifyAllMessages` scans every slot. It treats a
kind-3 record as a burn and pays the decoded recipient. Unlike mints, burns
have no registration or single-use check ([T17](../reports/T17.md) §§1, 3).

**Local chain of evidence.** Each stage below uses its own revision's compiled
program, key, and verifier; artifacts are never mixed across revisions.

| Stage | What we observed | Evidence grade (contract §8; AGENTS) | Source |
| --- | --- | --- | --- |
| Producer, earlier commit | Mint-only control and a candidate with a synthetic five-word burn record at padding indices 4–8 both satisfy `agg_agg`. The candidate proof verifies natively under the commit's own key. Control and candidate public inputs differ only at indices 4–8. A one-bit tamper fails verification. | **Locally reproduced** (real proof, native verify) | [T15](../reports/T15.md) §3 |
| Recursive propagation | The unmodified candidate proof is accepted by `agg_final`. The resulting proof verifies independently, and the record appears at final public-input indices 7–11. Roots and commit hash match the control. | **Locally reproduced** | [T16](../reports/T16.md) §2 |
| Consumer interpretation | Call path, burn dispatch, missing burn registration, and validator signature coverage of only `(newRoot, height, otherHash)`. | **Source-confirmed** (reading, not execution) | [T17](../reports/T17.md) §§1–3 |
| Committed effect | The candidate settles on a freshly deployed earlier-revision consumer and its own verifier. `balanceOf` shows rollup 100→93 and `0x…dEaD` 0→7. The mint-only control moves nothing. Unregistered-mint and replay controls revert. One signature works interchangeably for control and candidate. | **Locally reproduced, end to end** (real proof, original consumer, owned prover/validator/minter) | [T18](../reports/T18.md) §2 |
| Repair | At the check-added commit, the same witness fails at witness generation (`Message is not zero`, `agg_agg/src/main.nr:120`, called from `:108`). A separate legitimate mint proof still settles, and the burn address stays at 0. | **Repair-validated** for this one witness only | [T19](../reports/T19.md) §§1–3 |
| Advisory correspondence | Root cause, rejecting assertion, signature coverage, and burn dispatch match the advisory. Our independently derived `agg_final` key hash `0x122d2ac7…` is byte-identical to the one in the advisory's PoC. The advisory's affected label (`zk-circuits-v1.1.12`) predates the Noir code. Its patched label (`payy v1.3.0`) maps to no tag in the mirror. | **Mechanically checked** against the GitHub advisory API; version mapping **unresolved** | [T20](../reports/T20.md) §§1–2 |

**Scope of this example.** The attacker capability we exercised was a
registered prover with a cooperating validator quorum, both owned locally
([T18](../reports/T18.md) §3). It is not an arbitrary external caller. The
burn was 7 units to `0x…dEaD`, not the advisory's full-balance scenario. We
tried one tail position and one record shape ([T15](../reports/T15.md) §4).
We make no claim about live deployment history, real financial impact, or an
independent clean-machine rerun ([case study](../docs/payy-case-study.md),
"Scope of the conclusion"; [T20](../reports/T20.md) §3).

### C. Why the example motivates joint analysis, and where it does not

The violated property spans both sides. The producer leaves words
unconstrained, and the consumer turns an unconstrained word into a token
transfer. In our own experiments, the producer stages (T15–T16) showed only
proof acceptance and the consumer reading (T17) showed only a possible path.
The committed effect was established only by the end-to-end replay (T18).

- Our earlier analysis argues that a checker which only inspects consumer
  traces would not flag this. The consumer dispatches whatever the public
  inputs contain, and the violated invariant concerns the producer's witness
  structure ([T20](../reports/T20.md) §4). This is our reasoning, **not a
  tested result**: we have not run any consumer-side tool on this case.
- A producer-only check can flag the missing tail constraint *if someone
  states the property*. A source-pattern prototype agreed with the known pair
  and its sibling `agg_utxo`. That agreement is in-sample: the patterns were
  written after reading the advisory and the fix ([T21](../reports/T21.md)).
  Whether an existing circuit analyzer such as CIVER or CCC-Check would
  report the tail without a hand-written property is **[TODO-VERIFY]**
  (§VII). We make no claim that circuit-only checkers miss it.

> **[TODO — novelty note]** If a circuit-only checker turns out to detect
> the Payy tail, that affects the *novelty* argument (what joint analysis
> adds over producer-side tools). It does **not** affect Payy's validity as
> a motivating example: the defect, its consumer effect (T18) and its repair
> (T19) stand regardless of which tool can find it. Rewrite §I-C and §VII
> accordingly once CIVER and CCC-Check full texts are read.
- The joint view could add value by deriving the property from what the
  consumer does: which padding words reach a protected effect. Whether that
  derivation is automatic, sound, and cheaper than the alternatives is the
  open question of this paper. **[TODO-EVIDENCE]**

### D. Contributions

**UNDECIDED** (see box above). The candidate contributions in the
[contract](../docs/research-contract.md) §3 are goals, not completed claims:
(1) a consumer-directed extraction and refinement method;
(2) a justified implementation with an abstraction-preservation argument;
(3) comparative evidence. **[TODO-EVIDENCE]** for all three.

---

## II. Background

**[TODO]** Brief background on Noir/ACIR, recursive aggregation, the
Solidity verifier interface (public-input vector layout), and EVM token
effects. Use only the pinned artifact facts in [T15](../reports/T15.md)–[T17](../reports/T17.md)
and [D1P-09](../reports/D1P-09.md) §§2, 4.

---

## III. Threat Model and Definitions

This section restates the [research contract](../docs/research-contract.md)
§§4–5. It does not extend them.

### A. System model

For verification configuration `v`:

- `R_v(p, w)` is the actual constraint relation for public statement `p` and
  witness `w`.
- `D_v(p, x)` is the actual decoding relation from public statement to
  consumer values.
- `T(s, d, τ, s')` is a successful supported consumer execution from state
  `s` to `s'` with calldata `d` and committed trace `τ`.
- `Reach_L(h, s)` is an explicit bounded reachable-history relation.
- `σ` is the reviewed protocol specification.
- `P` is the multiset of proof-backed or otherwise explicitly permitted
  authorizations; `O` is the multiset of required obligations created by the
  accepted transition; `E` is the multiset of committed protected effects;
  `q` records pending obligations when the protocol explicitly permits
  deferral.

Records may carry kind, identity, asset, quantity, beneficiary, domain, state
version, activation condition, and permitted discharge rule. A joint
counterexample needs all of these together: a legal history, a satisfying
producer witness, actual decoding, a successful consumer execution, and a
policy violation. A fixed admitted pre-state is a narrower mode and is
labeled as such (contract §4).

### B. Authorization

Every committed protected effect in `E` must be justified by a compatible
permission in `P` under `σ`. Matching must preserve identity, asset,
beneficiary, domain, and quantity. A permission cannot be reused beyond its
multiplicity or quantity. Authorization does not require every permission to
be exercised (contract §4.1).

*Payy instance.* The T18 burn effect has no matching inner burn occurrence,
so authorization fails ([T18](../reports/T18.md) §3; [D1P-11](../reports/D1P-11.md) §3.1).

### C. Coverage

Every required obligation in `O` must be discharged by a compatible committed
effect, validly cancelled, or turned into a protocol-permitted pending
obligation in `q`. Matching preserves identity, quantity, backing, and
single-use requirements. Coverage is a safety property; we do not prove that
pending actions eventually execute (contract §4.2).

### D. Conservation is not a third property

Identity, amount, asset, recipient, and multiplicity preservation are matching
conditions inside both authorization and coverage. Aggregation, splitting,
padding, and deferral are accepted only through explicit transformation rules
(contract §4.3). In the initial fragment, splitting, aggregation, and deferral
are policy concepts only; if they occur, the result is `UNKNOWN`
(contract §5.5).

### E. Adversary

The adversary may choose witnesses, public inputs, proof bytes, calldata, and
transaction ordering. It may deviate from the honest witness generator, call
public entry points and roles allowed by the deployment model, reuse
available proofs or values unless the protocol prevents it, and select any
reachable supported pre-state. Case-specific capabilities are recorded. For
Payy, that means a registered prover and a validator quorum
(contract §5.1; [T17](../reports/T17.md) §3).

### F. Trusted assumptions

The guarantee may rely on: soundness of the proof system for the pinned
relation and key; correspondence among source, compiled constraints, key, and
consumer configuration; stated hash binding and collision-resistance
assumptions; correctness of `σ`; soundness of producer and consumer summaries
for the supported subsets; and standard atomic ERC-20 behavior where it
applies. Every result lists these assumptions (contract §5.2).

### G. Out of scope

Out of scope: breaking the verifier or proof-system soundness; trusted-setup
failures; consensus, sequencer, compiler, or hardware compromise; privacy
leakage unrelated to execution consistency; liveness; malicious, rebasing, or
fee-on-transfer tokens; unsupported proxies, inline assembly, delegate calls,
reentrancy, or unbounded external calls; and live deployments
(contract §5.4). Payy's separately reported verifier failure is out of scope.
The `agg_agg` message tail is in scope.

### H. Verdicts and evidence grades

Each analysis returns `VIOLATION`, `VERIFIED_WITHIN_SCOPE`, or `UNKNOWN`. An
evidence grade, bounds, assumptions, provenance, non-vacuity result, and
reason codes are attached separately. Timeout, allocation failure, an
unsupported feature, or probe UNSAT never establishes
`VERIFIED_WITHIN_SCOPE`. An abstract SAT candidate stays unresolved until
checked against the concrete relation (contract §8).

### I. Specification boundary

The tool must establish implementation facts: public-input schema, constraints
on relevant public values, decoding, guards, and effects. The analyst
supplies only policy roles, protected effects, permitted transformations, and
environmental assumptions. The specification must not assert that a value is
constrained, that a binding holds, or what the expected verdict is. Manual
implementation summaries are marked `ASSUMED` and excluded from
automatic-recovery claims (contract §6).

---

## IV. Approach

**[TODO-EVIDENCE — no method result exists.]** The planned pipeline is
described in the [reference proposal](../docs/d1/reference-proposal.md) §§3–4:
artifact intake, boundary extraction, checked abstraction, query and
refinement, and evidence validation. Do not describe it here as implemented.
Existing components are listed in the
[integration plan](../docs/d1-paper/integration-plan.md) §3 with their
limits. Formal target: an abstraction-preservation result
(contract §7). **No preservation theorem has been proved.**

---

## V. Evaluation (results tables intentionally empty)

The rows follow the claim–evidence matrix requested for D1P-D01. A cell
stays empty (`—`) until a frozen, separately versioned experiment fills it.
Payy and authored fixtures are **development** cases and cannot fill a
held-out row (contract §9).

### A. Claim–evidence matrix

| Claim | Evidence required | Current evidence | Status |
| --- | --- | --- | --- |
| **C1. Problem recurs** | Pinned obligations of this class in independent application families, with primary provenance; no prevalence inference from a convenience sample (contract §2). | One known disclosed instance (Payy). D1P-11 screened four applications in four families and wrote one concrete joint obligation for each (Aztec excluded as intractable), but assigned no defect labels; all are `UNKNOWN`. | **[TODO-EVIDENCE]** |
| **C2. Analysis is trustworthy** | Extraction fidelity against independent traces; abstraction-preservation argument; non-vacuity; real-proof validation of the central result. | Typed binding certificates and 11 exhaustive consumer predicates on the N=8 selected cone (D1P-09). Full relation, recursion, Poseidon, and Brillig are unsupported. No exact N=8 `agg_final` artifact. | **[TODO-EVIDENCE]** |
| **C3. Consumer direction adds value** | Equal-information comparison against direct Foundry tests, a monolithic joint query, and a CIVER-style modular adaptation, with total cost charged. | No joint comparison exists. All producer-side N=8 obligations `UNKNOWN` (D1P-07, D1P-10). Consumer shapes remove 4–8 of 620 cone operations (D1P-09). | **[TODO-EVIDENCE]** |
| **C4. Transfer** | Frozen mechanism applied to an independent held-out family with no new defect-specific rule. | Candidate targets ranked (WarpToad first); no artifact/proof correspondence validated (D1P-11 §4). | **[TODO-EVIDENCE]** |
| **C5. Usability** | Specification size, authoring and correction time, adapter effort, analyst hours, false alarms. | Historical only: direct Payy mint property is about 90 lines of Solidity (87 non-comment), functionally equivalent to the checker's manual specification ([T14](../reports/T14.md) §4). | **[TODO-EVIDENCE]** |

### B. Table I — C1: Problem recurrence (development and held-out corpus)

| Application | Family | Split (dev / held-out) | Producer / consumer | Obligation | Verdict | Evidence grade | Root cause | Provenance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | — | — | — |

Notes: report every screened, built, failed, and excluded target
(contract §9). Never count `UNKNOWN` as safe.

### C. Table II — C2: Analysis trustworthiness

| Case | Control type (honest / repaired / faulty / harmless freedom / padding / duplicate) | Extracted facts (`EXTRACTED`/`PROVED`/`ASSUMED`) | Agreement with independent trace | Non-vacuity | Verdict | Concretization / real-proof replay | Unsupported features |
| --- | --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | — | — |

### D. Table III — C3: Consumer direction vs. equal-information baselines

| Case / obligation | Method (Foundry / monolithic / CIVER-style adaptation / consumer-directed) | Result (SAT / UNSAT / UNKNOWN) | Wall time | Peak memory | False candidates | Refinement iterations | Spec + adapter + proving + adjudication effort |
| --- | --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | — | — |

Ablations (consumer slicing, observation-directed refinement, occurrence
identity, reachable-state constraints):

| Case | Ablation | Semantic change | Result | Cost |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

### E. Table IV — C4: Transfer to a held-out family

| Held-out application | Frozen before inspection? | Prior exposure | Adapter effort | New rules added | Control accuracy | Findings / guarantees retained |
| --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | — |

### F. Table V — C5: Usability and cost

| Case | Policy spec size | Authoring time | Correction time | Manual `ASSUMED` facts | Analyst hours | Proving time | Solver time | Localization quality |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | — | — | — |

---

## VI. Limitations

### A. N=8 scalability: no producer obligation is resolved

The only real producer target with prepared solver queries is a scaled N=8
selected cone of Payy's check-added `agg_agg` (620 operations, 540 witnesses).
It is in-sample development data, and on it the producer-side analysis has
not resolved a single combined obligation.

- **D1P-07** (native macOS, cvc5 1.4.2 with `--ff-solver=split`, 300 s per
  slot, sampled 4 GiB process-tree RSS policy): all six exact combined
  queries timed out and are `UNKNOWN`. A 25-cell partition of each obligation
  returned 58 cell-level UNSAT and 92 cell timeouts across 150 cells. Every
  partition kept at least one unresolved cell, so **zero of six** obligations
  moved from `UNKNOWN` to SAT or UNSAT. The partitions used less elapsed time
  (1,116 s vs. 1,800 s). That is partial-progress evidence only, not a
  solved-result speedup ([D1P-07](../reports/D1P-07.md) §§1, 7).
- **D1P-10** (fresh, separately frozen in-sample study): the unchanged
  baseline timed out at 300 s on all four obligations (`C`, `C ∧ G_NV`,
  `C ∧ G_PRE`, `C ∧ G_TAIL`). Profiling found no radix encoding with any
  resolved result. Both transformed arms failed their pre-main validation
  gates and were never run in the primary comparison. This is a null
  feasibility result, not evidence that the encodings are wrong or slower
  ([D1P-10](../reports/D1P-10.md) §§1, 5, 8).
- Historical Linux runs of the same six queries also timed out at 300 s under
  a hard 4 GiB `RLIMIT_AS`. They are background only; we make no
  cross-platform comparison ([D1P-07](../reports/D1P-07.md) §9).
- The timeouts are not hard wall caps. Detection happens on the next 50 ms
  sample, so measured times exceed 300 s by up to about 0.08 s
  ([D1P-07](../reports/D1P-07.md) §5; [D1P-10](../reports/D1P-10.md) §6).

Implication: the selected cone does not establish full-ACIR satisfiability,
proof validity, consumer behavior, or any authorization/coverage verdict.
**A timeout is never evidence of safety.**

### B. Propagation gate: a small, real, unvalidated reduction

- **D1P-09.** Eleven exact consumer reached-kind predicates for N=8 cover
  exactly the 18,751 structurally valid of 390,625 equality/control-flow
  class vectors. Each valid vector matches exactly one predicate;
  invalid and truncated vectors match none. Applied to the 620-operation
  cone, these consumer facts remove only **4–8 operations** while every
  payload stays symbolic. Producer cells remove more (residual 499–620),
  but that is a diagnostic, not consumer-method evidence. Full-relation
  propagation is unsupported: recursion, Poseidon, Brillig hint boundaries,
  and printed/serialized ACIR correspondence are not implemented. The one
  authorized N=8 `agg_final` compile exited 101 on a dependency-cache lock
  and produced no artifact. Exact N=8 forwarding, the outer key, proof
  acceptance, and `messages_length = 8` registration therefore remain
  blockers ([D1P-09](../reports/D1P-09.md) §§3, 5–6, 8).
- **D1P-10 validation of the propagated arm.** 12 of 25 whole-cone XOR
  equivalence checks returned UNSAT and 13 timed out. The arm was ineligible
  under its frozen fail-closed rule ([D1P-10](../reports/D1P-10.md) §3.2).

### C. Scale mismatch between real proofs and solver queries

Every real proof and consumer replay uses Payy's original 1,000-message,
1,003-public-input configuration. The N=8 solver queries are a scaled
transformation and cannot be validated by those proofs. The two remain
separate evidence grades
([integration plan](../docs/d1-paper/integration-plan.md) §5, item 9).

### D. Historical synthetic results (claude-code branch) — historical, not current-line evidence

The `claude-code` branch (common ancestor `1b4d5683…`; preserved copies in
[docs/history/synthetic-branch-1b4d568](../docs/history/synthetic-branch-1b4d568/README.md))
reported results on **authored N=9 fixtures** with a uniform three-word
record stride, no recursion, no hashing, and no real consumer replay. It
reported `VIOLATION` on the faulty fixture and `VERIFIED_WITHIN_SCOPE` on the
repaired one. Its own D1-04 found no clear advantage over Foundry tests. Its
D1-05 refinement loop ended up selecting all 26/35 producer constraints and
was 3–9% slower than monolithic solving. The integration review rejected its
D1 closure: the fixture's walk matches neither Payy's producer nor its
consumer, permissions could be reused, and nargo executions were labeled as
replayed concrete models ([integration plan](../docs/d1-paper/integration-plan.md)
§3 and §5, items 3–4 and 10). **These results are historical and are not
evidence for the current line.**

### E. Other limitations

- The motivating case is known, public, and development data. Nothing here
  shows BindCheck would have found it before disclosure
  ([case study](../docs/payy-case-study.md); [T20](../reports/T20.md) §4).
- An earlier ACIR/SMT evaluation produced a confirmed analyzer false positive
  from unsound probe specialization ([T22](../reports/T22.md)).
- The D1P-11 screen has four applications. Its labels are AI-assisted
  development notes, not independent annotations or prevalence evidence
  ([D1P-11](../reports/D1P-11.md) §1).
- AI agents implemented code and drafted reports and this text. Authors must
  inspect all claims and citations before submission (contract §10). The
  venue requires the HotCRP "Generative AI usage considerations" field
  and disclosure of AI use in the submission, with use that is integral to
  the methodology described explicitly [8, "Generative AI Policy"]. See
  §VIII-B.

---

## VII. Related Work

Each row states one precise difference. Each was checked against the cited
paper's text where noted. These papers are prior art for integration
failures, rich specifications, modular summaries, and selective unfolding
(contract §1); we claim none of those as new.

| Work | What it does (from the paper) | One precise difference from D1 | Verification status |
| --- | --- | --- | --- |
| **SNARK SoK** [1] | Taxonomy of 141 SNARK vulnerabilities across circuit, frontend, backend, and integration layers. Integration-layer bugs "stem from improper interactions between the application/system and the prover or verifier" (§6). It states that "there are currently no specific defenses developed for vulnerabilities in the integration layer" and suggests "multi-layer testing and verification techniques targeting both these components simultaneously" (§8). | The SoK names the gap and proposes the direction. It does not provide an analysis. D1 would be one concrete instance of that multi-layer analysis, and its value over the SoK depends on C3/C4 results. | Verified against arXiv 2402.15293 text (§§6, 8). Section numbering against the USENIX version: **[TODO-VERIFY]**. |
| **CIVER** [3] | Modular verification of Circom circuits using transformation and deduction rules. Checks weak safety, tag specifications, and pre/postconditions over circuit signals, analyzing components bottom-up through the circuit hierarchy. | CIVER's modules come from the producer's own component hierarchy, and its specifications are about circuit signals. D1 would choose and refine summaries from **consumer** observations, and its specification relates circuit outputs to contract effects. Whether that improves on a CIVER-style adaptation given the same facts is exactly C3. | Verified against the IEEE abstract (via search result), the SoK's description [1, §8], and the tool README [3b]. Full text not obtained. Detailed claims (e.g., component recovery from flattened constraints, §3.5 cited in the proposal) are **[TODO-VERIFY]**. |
| **Coda** [4] | A new statically typed language in which developers re-implement circuits and state properties as refinement types. Proof obligations become Coq lemmas proven interactively with a tactic library. Evaluated on 77 re-implemented Circom circuits, revealing 6 previously unknown vulnerabilities. | Coda verifies a circuit the developer **re-writes in Coda**, with interactive proofs. D1 targets the **existing compiled** producer artifact and the deployed consumer, and returns `UNKNOWN` rather than requiring proofs. We found no model of a consuming contract in the text we read (the phrase "smart contract" does not occur). | Verified against the full text (author-hosted version: abstract, §§1–3; whole-text search). The arXiv/ePrint abstracts say 79 circuits; reconcile against the S&P version: **[TODO-VERIFY]**. |
| **CCC-Check** [5] | A language-agnostic Domain Consistency Model for computation–constraint relationships, a taxonomy of mismatch vulnerabilities, and an IR-based abstract-interpretation detector reported to run about two orders of magnitude faster than CIVER with comparable precision; 15 previously unknown vulnerabilities in six projects. | CCC-Check compares a circuit's **computation against its own constraints**. D1 compares what a circuit's constraints admit against what a **consuming contract does** with the public outputs. Whether CCC-Check analyzes consumers, supports Noir/ACIR, or would flag Payy's tail (where the out-of-circuit Rust witness builder compacts with trailing zeros) is unconfirmed. | Abstract only (ePrint 2025/2120). Full text not obtained. Scope, supported languages, and Payy applicability: **[TODO-VERIFY]**. |
| **SmartAxe** [6] | Static analysis of cross-chain bridge contracts at the **EVM bytecode** level. Builds cross-chain control-flow and data-flow graphs (xCFG/xDFG). Its semantic-integrity check reports a function as vulnerable when withdrawal state variables have **no data-flow dependency** on deposit state variables (§4.3). | SmartAxe's semantic-integrity check, as described in §4.3, reports an **absent** dependency. In Payy, the burn amount and recipient do flow from proof-verified public inputs; the defect is that the producer constraints admit arbitrary values there. So that one check, as described, would not report this pattern. D1 instead reasons over the constraint relation [7, §3B]. SmartAxe analyzes smart-contract bytecode (§2.3), not circuits. Whether its other checks (e.g., access-control incompleteness, §4.2) would flag `RollupV1`'s burn path is untested: **[TODO-VERIFY]**. | Verified against arXiv 2406.15999 v1 (§§2.3, 4.3). Version counts differ between arXiv and FSE versions; cite FSE for numbers: **[TODO-VERIFY]**. |

**Also relevant, not compared here:** formal rollup models and cross-rollup
atomicity [7, refs 6–7]. **[TODO-VERIFY]** before adding.

---

## VIII. Ethics Considerations and Disclosures

Venue requirements below are from the IEEE S&P 2027 call for papers [8],
retrieved 26 October 2026.

### A. Ethics considerations

The venue requires an "Ethics Considerations" field on HotCRP at
registration. Accepted papers add an "Ethics Considerations" section at
camera-ready, and it does not count toward the page limit [8, "Research
Ethics Considerations"]. Draft content, mapped to the CFP's subsections:

- **Working with live systems.** None. All experiments were local, with
  synthetic notes and assets and owned prover, validator, and minter
  identities. We sent no transactions to live systems, made no maintainer
  contact, and broadcast nothing ([case study](../docs/payy-case-study.md);
  [T18](../reports/T18.md)).
- **Vulnerability disclosure.** The Payy defect was already publicly
  disclosed by others [2]; we reproduce it, we did not discover it. The CFP
  strongly recommends disclosing any vulnerability before the original
  submission and requires disclosure no later than the rebuttal deadline,
  with the submitted paper discussing the steps taken or planned
  [8, "Ethical Considerations for Vulnerability Disclosure"]. Any new
  finding needs this before it supports a claim (contract §9).
  **[TODO-EVIDENCE]** if new findings arise.
- **New tools.** If the paper presents a tool, the CFP asks how it could be
  misused, how to limit that, and how benefits were weighed against harms
  [8, "Ethics Considerations for Developing New Tools or Technologies"].
  **[TODO]** write once the contribution is decided.
- **Human subjects.** None planned. **[TODO]** revisit if the usability
  study (C5) involves participants; the CFP then requires IRB approval or
  waiver details [8, "Ethical Considerations for Human Subjects Research"].

### B. Generative-AI disclosure

The venue requires disclosure and motivation of generative-AI use, the
HotCRP "Generative AI usage considerations" field, explicit detail where AI
was integral to the methodology, and independent author validation of any
AI-generated idea. Authors remain responsible for all content and for the
thoroughness of the literature review. Non-compliance is grounds for desk
rejection [8, "Generative AI Policy"]. In this project AI agents wrote code,
reports, screening labels (D1P-11) and draft text (contract §10), so AI use
is integral to the methodology and must be described, not covered only by
the CFP's editorial-use sentence. **[TODO]** write the disclosure from the
preserved task prompts and reports.

### C. Competing interests

The camera-ready must disclose relevant financial and non-financial
competing interests [8, "Financial and Non-financial Competing Interests"].
**[TODO]** authors to supply.

### D. Submission-format constraints

From [8, "Page Limit and Formatting", "Anonymous Submission", "Submission
Deadlines & Decisions"]:

- Up to **13 pages of text plus up to 5 pages** of references and
  appendices, at most 18 pages in total. Text and figures after page 13 must
  be marked as appendix. Reviewers need not read appendices. Over-length
  papers are rejected without review.
- US letter, IEEE `compsoc` template, `\documentclass[conference,compsoc]{IEEEtran}`,
  IEEEtran.cls v1.8b; no margin, font or spacing changes.
- Anonymous review: no author names or identifying acknowledgments, own
  prior work cited in the third person, and anonymized artifact
  repositories. The internal repository links in this draft (`../reports/…`)
  must be replaced by an anonymized artifact before submission.
- **"Submitted papers should not include full CVE identifiers"** to preserve
  anonymity. This draft names the Payy CVE and GHSA identifiers; the
  submitted version must drop the full CVE identifier. **[TODO]** confirm
  with the PC chairs whether the GHSA link to a third-party advisory is
  acceptable.
- Deadlines are 23:59:59 AoE. The second cycle has abstract registration on
  10 November 2026 and paper submission on 17 November 2026. Title, abstract
  and author list are frozen at registration. A rejected paper waits one
  year before resubmission.

---

## IX. Conclusion

**[PLACEHOLDER — depends on the contribution decision and §V results.]**

---

## Open items for authors

1. Decide efficiency vs. capability only after Table III and Table IV have
   data. If neither shows an advantage, report the failed gate
   (contract §11).
2. A human author will supply full texts of CIVER (IEEE S&P 2024) and
   CCC-Check (IEEE S&P 2026); their rows stay **[TODO-VERIFY]** until then.
   Then apply the novelty note in §I-C.
3. Venue rules are resolved from the CFP [8] in §VIII. Remaining items:
   remove the full CVE identifier, anonymize repository links, and write
   the AI and competing-interest disclosures.
4. Have a human author independently inspect every citation and claim
   (contract §10). Retrieved texts and hashes are listed in
   [sources.md](sources.md).

---

## References

Primary sources only. Section numbers refer to the version actually read.

[1] S. Chaliasos, J. Ernstberger, D. Theodore, D. Wong, M. Jahanara,
B. Livshits. "SoK: What Don't We Know? Understanding Security Vulnerabilities
in SNARKs." USENIX Security 2024. Read: arXiv:2402.15293.
<https://www.usenix.org/conference/usenixsecurity24/presentation/chaliasos>

[2] Payy (polybase/payy). Security advisory GHSA-fhxc-63vg-9gwr /
CVE-2026-48100, published 10 June 2026.
<https://github.com/polybase/payy/security/advisories/GHSA-fhxc-63vg-9gwr>
(retrieved via GitHub API in [T20](../reports/T20.md)).

[3] M. Isabel, C. Rodríguez-Núñez, A. Rubio. "Scalable Verification of
Zero-Knowledge Protocols." IEEE S&P 2024, pp. 1794–1812.
<https://doi.org/10.1109/SP54263.2024.00133>
[3b] CIVER tool repository. <https://github.com/costa-group/circom_civer>

[4] J. Liu, I. Kretz, H. Liu, B. Tan, J. Wang, Y. Sun, L. Pearson,
A. Miltner, I. Dillig, Y. Feng. "Certifying Zero-Knowledge Circuits with
Refinement Types." IEEE S&P 2024. <https://doi.org/10.1109/SP54263.2024.00078>
Read: author-hosted copy <https://www.cs.utexas.edu/~isil/coda.pdf>.

[5] A. Kolozyan, B. Vandenbogaerde, J. Swalens, L. Hoste, S. Chaliasos,
C. De Roover. "Language-Agnostic Detection of Computation-Constraint
Inconsistencies in ZKP Programs via Value Inference." IEEE S&P 2026.
Read: abstract only, IACR ePrint 2025/2120. <https://eprint.iacr.org/2025/2120>

[6] Z. Liao, Y. Nan, H. Liang, S. Hao, J. Zhai, J. Wu, Z. Zheng. "SmartAxe:
Detecting Cross-Chain Vulnerabilities in Bridge Smart Contracts via
Fine-Grained Static Analysis." Proc. ACM Softw. Eng. 1(FSE), 2024.
<https://doi.org/10.1145/3643738> Read: arXiv:2406.15999v1.

[7] BindCheck D1 reference proposal (internal, not a citable primary
source; used only for cross-checking).
[../docs/d1/reference-proposal.md](../docs/d1/reference-proposal.md)

[8] IEEE S&P 2027 Call for Papers.
<https://sp2027.ieee-security.org/cfpapers.html>, retrieved 26 October 2026
(page states Cycle 2 updates to the Research Ethics Considerations section).
