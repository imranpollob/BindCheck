# BindCheck: Finding Proof-to-Execution Binding Failures at the Circuit–Consumer Boundary

*(Working title; frozen at abstract registration.)*

**Draft status:** D1P-P01 full-prose rewrite, 28 October 2026. Target format
is IEEE S&P (13 pages of text plus up to 5 pages of references and
appendices). No experiment was run for this draft. The prose is written in
full. Every cell or sentence whose content depends on an experiment not yet
run is marked **[PENDING D1P-30]**, **[PENDING D1P-31]**,
**[PENDING D1P-32]** or **[PENDING D1P-33]**. Comparisons that could not be
checked against the cited paper's full text stay **[TODO-VERIFY]**. The
previous skeleton (D1P-D01/D03) is preserved in Git history.

**Controlling sources, in order.** [Research contract](../docs/research-contract.md)
revision 2 (27 October 2026); [README](../README.md); the immutable reports
[T15](../reports/T15.md)–[T21](../reports/T21.md),
[D1P-12R](../reports/D1P-12R.md), [D1P-13](../reports/D1P-13.md),
[D1P-14A](../reports/D1P-14A.md)–[D1P-14D](../reports/D1P-14D.md),
[D1P-15](../reports/D1P-15.md),
[D1P-17](../reports/D1P-17-consumer-backends.md),
[D1P-19](../reports/D1P-19.md), [D1P-21A](../reports/D1P-21A.md); the
extraction records [D1P-16](../docs/extraction/d1p-16-feasibility.md),
[D1P-18](../docs/extraction/d1p-18-hardening.md),
[D1P-20](../docs/extraction/d1p-20-extracted-solver-model.md),
[D1P-21B](../docs/extraction/d1p-21b-variant-extraction.md); the
[B02 obligations](../docs/d1-paper/d1p-b02-discriminating.md); the
[taxonomy protocol v0.2.0](../docs/taxonomy/protocol.md); and the
[baseline preregistration](baselines.md). If this draft disagrees with any of
them, the source wins.

**Research verdict at drafting time:** `UNKNOWN`. No BindCheck rule has run
on any target. The capability gate (contract §11) has not passed.

### Pending-task map (provisional; set by this draft, to be confirmed by the planners)

| Tag | Scope | Paper locations |
| --- | --- | --- |
| **D1P-30** | Freeze and implement the rule engine (polarity classifier, R-BIND, R-ANCHOR, R-EFFECT) and the automatic validator; run them on the development cases and the development mutation benchmark | §V-F/H status lines, §VI, RQ1, RQ2 |
| **D1P-31** | Run every applicable baseline in both arms (generic/default and same-policy) under [baselines.md](baselines.md) | RQ3 |
| **D1P-32** | Held-out scan: reserved families, rules frozen before the first held-out artifact is opened | RQ4 |
| **D1P-33** | Taxonomy annotation round under protocol v0.2.0: retrieval, two human annotators, adjudication, agreement | §IV-D, RQ5 |

### Disagreements with controlling sources (for the authors)

1. **Contribution list.** Contract §3 lists capability, justified
   implementation, comparative evidence and efficiency. It does not list a
   taxonomy or "actionable warnings". This draft follows the user-requested
   thesis. The contract controls: before submission, either a dated
   change-control entry (contract §11) adds the taxonomy and the
   warning/diagnostic framing, or the paper demotes them. The capability gate
   is unchanged either way, and the evaluation below is laid out so that it
   can satisfy all four gate conditions.
2. **Rule names.** R-BIND, R-ANCHOR, R-EFFECT and the polarity classifier
   appear in no report, protocol or code in this repository. §V-E/F is this
   draft's proposed specification. D1P-30 must freeze it before any rule
   result is inspected.
3. **RQ numbering.** Paper RQ1–RQ5 differ from contract RQ1–RQ5. The mapping
   is in §VII-A. Contract RQ5 (efficiency) is not a paper RQ; its null
   results are reported in Appendix A, as the contract requires.

---

## Abstract

A zero-knowledge verifier establishes only the relation that its circuit
encodes. The contract that consumes an accepted proof then decodes the public
inputs and mints, transfers, records nullifiers or advances state. Whether
those effects are justified is a property of neither component alone. It
depends on whether every public value the consumer relies on is actually
constrained by the circuit, and whether every value the circuit trusts is
actually supplied by the consumer from trusted state. We call violations of
this agreement *proof-to-execution binding failures*. BindCheck analyzes the
circuit–consumer boundary of Noir/ACIR producers and Solidity/EVM consumers.
It extracts, from the compiled circuit and the consumer source, how each
public input is constrained and how it is used. It classifies each word by
its *polarity* across the boundary and applies three generic rules: R-BIND
(a word the consumer relies on is not bound by the circuit), R-ANCHOR (a word
the circuit treats as a trust anchor is not anchored by the consumer) and
R-EFFECT (a committed effect is not justified by bound words under the
reviewed policy). Each warning names the circuit locus, the consumer guard
and effect sites, and a repair locus. BindCheck then attempts to validate the
warning automatically with a real proof that is accepted by the unchanged
verifier and consumer and produces a committed effect on an owned local
chain. We ground the design in a taxonomy of binding failures and in three
case studies: a publicly disclosed Payy rollup defect (historical, reproduced
end to end with real proofs) and two injected WarpToad bridge variants, a
producer-side domain-binding removal (M-DOM) and a consumer-side root-guard
removal (M-SRC), each with real-proof differential ground truth. On these
development cases BindCheck [PENDING D1P-30]. Against circuit-only and
contract-only baselines in default and same-policy configurations,
[PENDING D1P-31]. On a held-out set of [PENDING D1P-32] families frozen
before analysis, [PENDING D1P-32]. In the taxonomy study, [PENDING D1P-33].

---

## I. Introduction

### A. A valid proof is not a valid effect

Zero-knowledge (ZK) applications split one security decision across two
programs written in different languages by different tools. A *producer*
circuit, here written in Noir and compiled to ACIR, defines a relation
`R_v(p, w)` over a public statement `p` and a private witness `w`. A
generated verifier accepts a proof exactly when `p` is in the relation's
language under the pinned verification key. A *consumer* contract, here in
Solidity, assembles `p` from calldata, storage and block context, calls the
verifier, and then performs protected effects: it mints tokens, pays
recipients, writes nullifiers and accepts new state roots.

Cryptographic soundness guarantees only that an accepted `p` satisfies
`R_v`. It does not guarantee that `R_v` constrains the values the consumer
acts on, nor that the consumer supplies from trusted state the values that
`R_v` silently trusts. The SNARK SoK classifies such failures as
integration-layer vulnerabilities and reports no defenses developed
specifically for that layer [1, §§6, 8]. Failures of this kind are invisible
to an analysis of either side in isolation unless someone first states the
cross-boundary property. A circuit analyzer sees a public input that nothing
constrains, but cannot tell whether any consumer relies on it. A contract
analyzer sees a verifier call that returns true, but cannot tell which
arguments the circuit actually binds.

### B. Three motivating cases

We study three concrete instances. They differ in which side is defective.

**Payy (historical, producer-side).** In a publicly disclosed defect in
Payy's Noir/Solidity rollup (advisory GHSA-fhxc-63vg-9gwr, 10 June 2026)
[2], the aggregation circuit exports a 1,000-word message array. It binds
only the words below a running counter. The consumer scans every word and
pays out any record that decodes as a burn. We reproduced the mechanism
locally from pinned public sources with real proofs: a forged burn record in
the unconstrained tail is accepted by both recursive circuits, settles on the
unmodified consumer, and moves tokens (T15–T18). The repaired revision
rejects the same witness (T19). This is a known disclosure, not a new
finding.

**WarpToad M-DOM (injected, producer-side).** WarpToad is a Noir/Solidity
privacy bridge. Its pinned withdrawal circuit binds the Aztec-origin note to
a configured contract address through public input word 5, which the
consumer fills from configuration. M-DOM is a mechanism-derived mutation:
the address that feeds the silo hash becomes a private, prover-chosen field,
and word 5 stays declared but unconstrained. The mutation follows an unused
in-tree hashing package and a developer warning; we make no claim that any
such artifact was released. With its own key and verifier, M-DOM accepts a
real proof for a note siloed under a foreign contract, and the unchanged
consumer mints from it (D1P-15).

**WarpToad M-SRC (injected, consumer-side).** M-SRC leaves the circuit
byte-identical and removes one consumer guard: the check that the
destination local root is in the consumer's root history. On the circuit's
same-root branch, that word is the root against which note membership is
proved, and the circuit's own comment states that it relies on it being
public. With the guard removed, a real proof over a private,
attacker-built tree mints through M-SRC. The same proof and calldata revert
at the guard on the pinned consumer (D1P-19).

The cases are complementary. In Payy and M-DOM, the circuit fails to bind a
word that the consumer relies on. In M-SRC, the consumer fails to anchor a
word that the circuit relies on. In M-SRC no circuit-only analysis can find
a defect, because the circuit is unchanged. In M-DOM, judging the circuit
requires knowing that the consumer treats word 5 as the binding domain
identity. These are our arguments for analyzing the pair, and they are
claims about what information a tool needs. Whether existing tools in fact
miss these cases is an empirical question that RQ3 answers
**[PENDING D1P-31]**; we do not assume it.

### C. BindCheck

BindCheck takes the pinned compiled circuit, its ABI, the verifier
configuration and the consumer source. It produces warnings that relate
specific public-input words to specific consumer guards and effects. It
works in four steps.

1. **Extraction** recovers implementation facts on both sides with
   provenance: the public-input layout and the constraints that read each
   word (from decoded ACIR), and the consumer's path families, verifier
   argument construction, guards and committed effects (from the Solidity
   AST). Unsupported constructs produce a named rejection, never a silent
   default.
2. **Polarity classification** assigns each public word a producer role
   (anchor, bound, chosen or free) and a consumer polarity (supplied,
   consumed or passed through) on each consumer path.
3. **Generic rules** evaluate the role–polarity pairs. R-BIND, R-ANCHOR and
   R-EFFECT are stated once, without case-specific content. The analyst
   supplies only policy roles (contract §6.2): which effects are protected
   and what each field means.
4. **Validation** turns each warning into a concrete candidate: a witness
   that satisfies the actual compiled relation, a real proof under the
   variant's own key, and a submission to the unchanged consumer on an owned
   local chain from an admitted pre-state. Effects are checked on state.
   Every failed step yields `UNKNOWN` with a reason, never a safety claim.

A warning is evidence level E1. A validated warning reaches E4, the
contract's *end-to-end validated mismatch* (§III-F). The absence of a
warning is not `VERIFIED_WITHIN_SCOPE`. It means only that no rule fired
within the supported fragment.

### D. Contributions

The following are the paper's contributions. Each item states the evidence
that exists now and the evidence still pending.

1. **A taxonomy of proof-to-execution binding failures** (§IV). It has three
   independent dimensions: cause, consequence and attacker role. It is tied
   to the authorization/coverage semantics of the research contract and
   comes with a preregistered annotation protocol that separates disclosure
   counts from tool support. *Exists:* codebook and protocol v0.2.0 with a
   frozen search plan. *Pending:* the annotation round and agreement
   statistics **[PENDING D1P-33]**.
2. **Cross-layer analysis by generic rules** (§V). Extracted circuit
   public-input facts are joined to consumer guards and effects, and three
   rules over a word-level polarity classification are applied. *Exists:*
   the extraction components, validated on the development fragment
   (ACIR decoding with source/artifact correspondence, D1P-13; checked hash
   region and construction provenance, D1P-15, D1P-19, D1P-21A;
   fail-closed consumer extraction that mechanically recovers the M-SRC
   guard removal, D1P-18, D1P-21B). *Pending:* the rule engine and its
   results **[PENDING D1P-30]**.
3. **Actionable diagnostics with automatic real-proof validation** (§V-G,
   §V-H). Each warning names its producer and consumer loci and a repair
   locus, and is taken automatically toward E4. *Exists:* the hand-built
   real-proof pipelines that the validator automates (T15–T18; D1P-12R,
   D1P-14A, D1P-15, D1P-19, D1P-21A). *Pending:* automation and warning
   quality **[PENDING D1P-30]**.
4. **Validated case studies** (§II, §VII). One historical case (Payy, with a
   locally reproduced end-to-end effect and a repair validated for one
   witness) and two injected cases (WarpToad M-DOM and M-SRC, each with a
   real-proof differential against the pinned build and exact-state honest
   controls). *Exists:* all of the listed ground truth. *Pending:* BindCheck's
   own detection and validation on them **[PENDING D1P-30]** and the
   baseline comparison **[PENDING D1P-31]**.

Consistent with contract §1, we do not claim as new: integration failures as
a category, the permission/obligation/effect terminology, rich semantic
specifications, or modular summaries. The specific advance over prior work
is the cross-layer rule set and its automatic validation, and it is
demonstrated only to the extent that RQ1–RQ4 show it.

### E. Scope of the evidence

We use three evidence classes throughout and never merge them.

- **Historical:** a real, publicly disclosed defect, reproduced locally from
  pinned artifacts (Payy). It is development data. The defect and its
  end-to-end artifact were known before BindCheck's rules were written, so
  Payy cannot show unbiased discovery.
- **Injected:** a mutation that we introduced into a pinned application
  (WarpToad M-DOM and M-SRC) or into the development mutation benchmark.
  An injected result shows that the tool detects the injected mechanism. It
  says nothing about a defect in the pinned application. All injected cases
  are development data.
- **Held-out:** families reserved by a private draw before development
  screening and analyzed only after the rules were frozen (RQ4). Only
  held-out results can support transfer or generality claims (contract §9).
  No held-out result exists yet.

All executions are owned-local. Synthetic admitted pre-states are labeled as
such and carry no cross-chain reachability claim.

---

## II. Background and Motivation

### A. The circuit–consumer boundary

**Producer.** A Noir program compiles to ACIR: a list of constrained opcodes
over a witness vector (arithmetic `AssertZero`, `RANGE`, black-box calls
such as `Poseidon2Permutation`) plus unconstrained Brillig functions that
compute witnesses but constrain nothing. Public parameters occupy a prefix
of the witness vector in ABI declaration order. For the pinned WarpToad
withdrawal circuit, the decoded program has 25,073 constrained opcodes:
24,860 `AssertZero`, 107 `RANGE`, 86 `Poseidon2Permutation`, plus 20 Brillig
calls. Its 11 public witnesses 0–10 map one-for-one to the consumer's
argument order (D1P-13 §§3, 5).

**Verifier.** The proving backend derives a verification key and a Solidity
verifier from the compiled artifact. The WarpToad route uses bb.js 5.0.0
UltraHonk with `keccakZK`. The generated verifier requires 11
caller-supplied words and rejects any word `≥ P` with `ValueGeFieldOrder()`
instead of reducing it (D1P-12R §§4, 7). A changed relation needs a new key:
a mutated circuit is analyzed only with its own key and verifier, and
artifacts are never mixed across revisions (T18 §1; D1P-15 §5).

**Consumer.** The consumer builds the public-input vector from calldata,
storage and block context, checks guards, calls the verifier and commits
effects. In `WarpToadCore.mint`, nine words come from calldata, `chain_id`
from `block.chainid`, and the Aztec contract address from deployer-set
configuration (D1P-12R §5). Guards check the giga root and local root
against stored histories and the nullifier against prior use. Effects are a
nullifier write and up to two ERC-20 mints, split between relayer and
recipient. The extracted relation has 22 terminal path families: 3 success
and 19 revert (D1P-18).

The boundary is the pair (verifier argument vector, public witness prefix).
The security question asks whether the constraints on that prefix and the
consumer's construction and use of the vector agree.

### B. Case study 1: Payy's message tail (historical)

**Mechanism.** At the earlier commit `c4d2c902…`, Payy's `agg_agg` circuit
merges inner proofs and exports a 1,000-word public `messages` array. A
counter `messages_index` marks the end of the active prefix. Every word
below the counter is bound to an inner proof, but no assertion reads words
at or above it (T15 §1). `agg_final` forwards these words unchanged into its
own public inputs (T16 §1). The consumer `RollupV1.verifyAllMessages` scans
every slot and pays out each kind-3 record as a burn. Unlike mints, burns
have no registration or single-use check (T17 §§1, 3). The validator
signature covers only `(newRoot, height, otherHash)` (T17 §3). The check-added
commit `dcd5d96e…` adds `assert_message_tail_zero`. The consumer source is
byte-identical at both commits (T15 §1).

**Local evidence chain.** Each stage used its own revision's program, key
and verifier.

| Stage | Observation | Evidence label | Source |
| --- | --- | --- | --- |
| Producer | Control and candidate (synthetic five-word burn at message indices 4–8) both satisfy earlier `agg_agg`; the candidate proof verifies natively; public inputs differ only at indices 4–8; a one-bit tamper fails | Locally reproduced | T15 §3 |
| Recursion | The unmodified candidate is accepted by `agg_final`; the record appears at final public-input indices 7–11 | Locally reproduced | T16 §2 |
| Consumer reading | Call path, burn dispatch, no burn registration, signature coverage | Source-confirmed | T17 §§1–3 |
| Committed effect | On a fresh earlier-revision consumer with its own verifier: rollup balance 100→93, `0x…dEaD` 0→7 (`balanceOf`); the mint-only control moves nothing; unregistered and replayed submissions revert; one signature settles both control and candidate | Locally reproduced, end to end | T18 §2 |
| Repair | The same witness fails at `agg_agg/src/main.nr:120` (`Message is not zero`, called from `:108`); a legitimate mint still settles | Repair-validated for this one witness | T19 §§1–3 |
| Advisory match | Root cause, rejecting assertion, signature coverage and dispatch match; our independently derived `agg_final` key hash `0x122d2ac7…` equals the advisory PoC's | Mechanically checked against the advisory API | T20 §1 |

**Limits.** The exercised capability was a registered prover with a
cooperating validator, both owned locally (T18 §3; contract §5.1). The burn
was 7 units, not the advisory's full-balance scenario. We tried one tail
position and one record shape. We make no claim about live deployments. The
T18 end-to-end artifact was built by hand after the advisory, so it is not a
tool's validation (baselines §4.2, rule 4).

### C. Case studies 2 and 3: WarpToad and two injected variants

WarpToad is pinned at `973e7d1e…` (Noir `1.0.0-beta.22`, bb.js 5.0.0,
solc 0.8.29). Its artifact chain is established end to end. An exact-compiler
rebuild matches the committed ACIR, ABI, VK and verifier (D1P-13 §2). A real
honest proof mints through the unchanged consumer with a nonzero relayer fee
and exact conservation. Replay is rejected (D1P-12R §6). The fee cap and the
zero-fee branch are exercised with real proofs (D1P-14A). The pinned
application has no known defect. It is an honest development fixture and
**not a proven negative control**.

**M-DOM (injected producer mutation).** Policy source: the circuit comment
at `main.nr:20–22` says the configured Aztec address prevents notes of other
Aztec contracts from being accepted (B02 §1.1). The mutation adds a private
`aztec_merkle_data.contract_address`, feeds it into the silo hash, and leaves
public word 5 declared but unused (D1P-15 §5). It has its own artifact,
VK and verifier (`db1a0a17…`, `3bc51af9…`, `d5ceca6e…`).

**M-SRC (injected consumer mutation).** Policy source: the documented
burn-to-mint intent and the circuit comment "destination_local_root is a
public input so its safe" on the same-root branch (B02 §2.1–2.2). The
mutation removes `require(isValidLocalRoot(_localRoot))` (K2) and changes
nothing else. It reuses the pinned producer, VK and verifier, which is the
correct pairing for a consumer-only change (D1P-19 §4).

**Ground truth, established by hand.**

| Variant | Real-proof differential | Honest control from exact frozen state | Source |
| --- | --- | --- | --- |
| M-DOM | A note siloed under `A_X ≠ A_WT` yields a real proof accepted by M-DOM's verifier. The unchanged consumer mints `5e18` and writes the nullifier. The same semantic input fails witness execution on the pinned circuit (`Cannot satisfy constraint`) | Honest `S_DOM` mint passes for both pinned and M-DOM | D1P-15 §6.2; D1P-21A §3 |
| M-SRC | A real proof for the pinned circuit over a private tree whose root is not admitted mints `3e18` through M-SRC. The identical proof and calldata revert at K2 (`_localRoot unknown`) on the pinned consumer with no state change | Honest `S_SRC` mint passes for both pinned and M-SRC | D1P-19 §4.2; D1P-21A §3 |

These differentials establish that each variant changes the target property
under its own correct artifact pairing. M-DOM's differential uses privileged
synthetic root admission, and M-SRC's uses an owned-local fixed pre-state.
Neither carries a cross-chain reachability claim. The obligations and
admitted-state designs behind them (O1/O2, `S_DOM`, `S_SRC`) were written by
the planners. They do not count as automatically derived (contract §2,
RQ2; B02 §6). We therefore do not count these differentials as E4 for any
tool. They are the ground truth against which tools are scored.

### D. What the cases ask of a tool

To flag Payy, a tool must know that the consumer decodes protected effects
from words that the circuit binds only below a data-dependent extent. To
flag M-DOM, it must know that the consumer supplies word 5 as a context
identity while the circuit no longer reads it. To flag M-SRC, it must know
that the circuit uses word 4 as a membership root while the consumer no
longer checks it. In each case the decisive fact sits on the other side of
the boundary from the defect. This motivates a joint, word-level analysis.
A source-pattern prototype written after reading the Payy advisory agreed
with the Payy pair (T21). That agreement was in-sample, and it shows why
detection on known cases cannot stand in for transfer.

---

## III. Threat Model and Definitions

This section restates contract §§4–6 and §8 and does not extend them.

### A. System model

For verification configuration `v`, `R_v(p, w)` is the compiled constraint
relation and `D_v(p, x)` is the actual decoding from public statement to
consumer values. `T(s, d, τ, s′)` is a successful supported consumer
execution from state `s` with calldata `d` and committed trace `τ`.
`Reach_L(h, s)` is an explicit bounded reachable-history relation. `σ` is the
reviewed policy. `P`, `O` and `E` are multisets of permissions, required
obligations and committed protected effects. Records carry kind, identity,
asset, quantity, beneficiary, domain and state version. A joint
counterexample requires a legal history, a satisfying producer witness,
actual decoding, a successful consumer execution and a policy violation
together. A fixed admitted pre-state is a narrower mode and is labeled as
such.

### B. Properties

**Authorization.** Every committed protected effect in `E` is justified by a
compatible permission in `P`. Matching preserves identity, asset,
beneficiary, domain and quantity. No permission is used beyond its
multiplicity. **Coverage.** Every required obligation in `O` is discharged,
validly cancelled, or turned into a protocol-permitted pending obligation.
Conservation is not a third property. Its components are matching
conditions inside both. Aggregation, splitting and deferral are policy
concepts. Where they occur, the result is `UNKNOWN` until they are modeled
(contract §5.5).

### C. Adversary

The adversary chooses witnesses, public inputs, proof bytes, calldata and
transaction ordering. It may deviate from the honest witness generator, call
public entry points with the roles the deployment model allows, reuse
available values unless the protocol prevents it, and select any reachable
supported pre-state. Case-specific capabilities are recorded: a registered
prover with a validator quorum for Payy, and an ordinary named relayer and
prover for WarpToad.

### D. Trust assumptions and scope

We assume proof-system soundness for the pinned relation and key; correct
correspondence among source, constraints, key and consumer configuration;
stated hash binding assumptions; correctness of `σ`; soundness of the
extractors on their supported fragments; and standard atomic ERC-20
behavior. Out of scope: breaking the verifier, trusted-setup failure,
consensus, sequencer, compiler or hardware compromise, unrelated privacy
leakage, liveness, non-standard tokens, unsupported proxies, inline
assembly, delegate calls, reentrancy, and live systems. Payy's separately
reported verifier failure is out of scope. Its message tail is in scope.

### E. Specification boundary

The tool establishes implementation facts: public-input schema, the
constraints that read each word, decoding, guards and effects. The analyst
supplies only semantic roles, the protected-effect set, permitted
transformations and admitted states. The specification must not state that a
value is constrained, that a binding holds, the expected verdict, or the
missing relation (contract §6.3). BindCheck's rules consume only extracted
facts and roles. Any manual implementation summary is marked `ASSUMED`,
counted and excluded from automatic-recovery claims.

### F. Verdicts and evidence ladder

Every analysis returns `VIOLATION`, `VERIFIED_WITHIN_SCOPE` or `UNKNOWN`,
with a separate evidence grade, bounds, assumptions, provenance and reason
codes. **E0**: no report. **E1**: a tool warning. **E2**: an assignment
satisfying the actual compiled producer relation, decoder and consumer
model. **E3**: a real proof of that assignment accepted by the pinned,
unchanged verifier. **E4**: that proof accepted by the unchanged consumer
from an admitted or reachable state, producing an unauthorized committed
effect or an undischarged obligation, checked on state. Only E4 is an
end-to-end validated mismatch. For a variant, "unchanged" means the frozen
variant with its own matching key and verifier. A timeout, crash,
unsupported feature or missing artifact is never evidence of safety.

---

## IV. A Taxonomy of Proof-to-Execution Binding Failures

### A. Unit and inclusion

The unit is one canonical finding with its pinned affected boundary. A
finding is a *binding failure* when evidence supports a disagreement between
what the accepted relation establishes and what the consumer treats as
authorized or required, with a possible committed incompatible effect or an
undischarged obligation (protocol §2). Pure circuit bugs and pure consumer
bugs are excluded unless the two sides disagree. Proof-system unsoundness is
excluded by premise. A reverted effect is not committed. Tool support never
decides inclusion: a Circom or Halo2 disclosure counts even if BindCheck
cannot ingest it.

### B. Three independent dimensions

**Cause** (what fails to bind):

| Code | Definition (protocol §4) | Boundary side | Development example (author-assigned, not annotation data) |
| --- | --- | --- | --- |
| `C_RELATION_GAP` | Accepted constraints omit a dependency needed by the consumer's interpretation | Producer | Payy tail; M-DOM word 5 |
| `C_FIELD_MAPPING` | Producer, verifier and consumer disagree on identity, order, slice or forwarded value | Boundary | — |
| `C_REPRESENTATION` | Field/integer/byte range, width, sign, canonicality or encoding differs | Boundary | Modeling obligation only: the verifier rejects non-canonical words, while Solidity `PoseidonT3` reduces them (D1P-12R §7; D1P-19 §7.3) |
| `C_ACTIVATION_EXTENT` | Count, prefix, padding, tag, length or activation differs | Producer or consumer | Payy: binding depends on `messages_index`, consumption does not |
| `C_CONTEXT_IDENTITY` | Domain, app, actor, asset, state or version not bound to the executing context | Either | M-DOM (domain identity); M-SRC (state root not anchored) |
| `C_VERIFICATION_CONFIG` | A sound relation, key or configuration interpreted as another | Configuration | — |
| `C_OCCURRENCE_ACCOUNTING` | Identity, multiplicity or single-use accounting lost | Consumer | Payy burns: no registration or single-use record |
| `C_DISCHARGE_TRANSFORMATION` | Selection, aggregation, split, cancellation or pending handling violates policy | Consumer | — |
| `C_OTHER_BINDING` | Other evidenced binding cause; requires human review | — | — |

**Consequence** (what the failure permits): `K_AUTHORIZATION`, `K_COVERAGE`,
`K_MISDIRECTED`, `K_QUANTITY`, `K_DUPLICATE_REPLAY`, `K_OMITTED_DISCHARGE`,
`K_STATE_INCONSISTENCY`, `K_OTHER_EFFECT`. Every complete included finding
carries `K_AUTHORIZATION`, `K_COVERAGE` or both. All three development cases
are authorization failures: an effect without a compatible permission.

**Attacker role** (minimum sufficient capability): `A_PUBLIC_CALLER`,
`A_WITNESS_PROVER`, `A_RELAYER`, `A_REGISTERED_PROVER`,
`A_OPERATOR_ORDERER`, `A_PRIVILEGED_CONFIGURATOR`, `A_OTHER_ROLE`. Payy
required `A_REGISTERED_PROVER` with a validator quorum. The WarpToad variants
require witness and proof construction by an ordinary submitter, given the
admitted pre-state.

The dimensions are multi-label and independent. Each label is recorded as
present, absent or uncertain, with a rationale and an evidence pinpoint.
Empty never means absent.

### C. From taxonomy to rules

The rules in §V target the causes that a word-level analysis of one
producer–consumer pair can observe. They do not cover the others, and the
taxonomy keeps those visible as tool limitations rather than dropping them.

| Cause | Rule coverage in the design |
| --- | --- |
| `C_RELATION_GAP` | R-BIND (word consumed or supplied but free in the producer) |
| `C_ACTIVATION_EXTENT` | R-BIND under the producer's extracted activation condition. If the condition cannot be related to the consumer's scan, the warning is emitted with reason `UNRESOLVED_CONDITION` |
| `C_CONTEXT_IDENTITY` | R-BIND (context word free in the producer) and R-ANCHOR (anchor word not anchored by the consumer) |
| `C_OCCURRENCE_ACCOUNTING` | R-EFFECT (single-use clause) |
| `C_FIELD_MAPPING` | Boundary join (§V-D): a mismatch between argument construction and the ABI yields `UNKNOWN`, not a rule warning |
| `C_REPRESENTATION` | Canonicality obligations in the boundary join, partial |
| `C_VERIFICATION_CONFIG`, `C_DISCHARGE_TRANSFORMATION` | Not covered; reported as unsupported in the tool funnel |

### D. Empirical method (protocol v0.2.0)

The sampling frame is public disclosures about proof-consuming ZK systems
from 1 January 2018 to 27 October 2026. Discovery starts from source indexes,
not application names. There are 17 frozen endpoints: two seed collections
(SNARK SoK dataset, 0xPARC zk-bug-tracker), 13 backbone indexes (audit-firm
listings, contest platforms, GitHub Security Advisories) and two
supplemental keyword endpoints. Their traversal order, pagination, stopping
rules and a 1,200-minute active budget are fixed in the search plan. If any
percentage from an audit report is reported, every finding in that report is
screened. Families are lineage components. Forks and ports stay in their
family.

A human custodian reserves half of the newly eligible, unexposed family
groups in each stratum by a private draw outside every agent session. Only a
salted commitment is stored in the repository. Reserved families feed the
held-out scan (RQ4) and are never screened during development. Payy,
WarpToad, 0xbow Privacy Pools and the Aztec epoch rollup are exposed
development families and are never eligible for reservation.

Two human annotators label 16 fresh packets independently after one unscored
calibration round of four packets. A third human adjudicates. AI systems are
never raters or tie-breakers. Agreement is reported per label (Cohen's kappa
or Krippendorff's alpha), with denominators, intervals and `null` where it
is undefined. The disclosure funnel (`candidate → screened →
include/exclude/unresolved`) and the tool funnel (`available → supported →
analyzed → validated`) are reported separately and never combined into one
attrition rate.

**Status.** The design and search plan are frozen. Reservation and
annotation have not been completed. All results are **[PENDING D1P-33]**.

**Claim limit.** The strongest permitted statement is that these mechanisms
recur across independent families in the sampled public disclosures. We
make no prevalence, incidence or audit-quality inference.

---

## V. Design

### A. Overview

```
 compiled ACIR + ABI ──► producer extraction ──► word facts (role, condition, provenance)
                                                        │
 VK / generated verifier ─► boundary join (D_v) ◄───────┤
                                                        │
 consumer source + solc ─► consumer extraction ─► path facts (polarity, guards, effects)
                                                        │
                       policy roles σ ───────────► rules R-BIND / R-ANCHOR / R-EFFECT
                                                        │
                                                   warnings (E1)
                                                        │
             admitted state ─► validator: witness ► proof ► consumer ► state check
                                                        │
                                      E2 / E3 / E4 or UNKNOWN(reason)
```

*Figure 1 (to be drawn).* Every arrow carries artifact hashes. A fact enters
a rule only if it is labeled `EXTRACTED` or `PROVED`. `ASSUMED` facts are
counted and reported, and a warning that depends on one says so.

### B. Producer extraction

**Decoding.** Versioned, fail-closed ACIR decoders exist for Noir
`1.0.0-beta.14` (Payy) and `1.0.0-beta.22` (WarpToad). The beta.22 decoder
parses all 25,073 constrained opcodes of the WarpToad artifact. Any unknown
opcode, black box, Brillig form or serialization form raises a named
`Unsupported` reason. Parsing is kept separate from semantic support:
arithmetic and range constraints are evaluated exactly over the BN254 field,
while black boxes are classified explicitly (D1P-13 §3). On the honest
witness, all 24,967 supported constraints hold. The 86 Poseidon2
permutations are listed as unsupported for whole-circuit satisfaction
(D1P-13 §4).

**Public-word dependency facts.** For each public witness `i`, the extractor
records the constrained opcodes that read `i`, directly or through
intermediate witnesses, and classifies the first constraint on each path.
The classes are: an equality with a value computed from private witnesses
(a digest or root), an input lane of a hash construction, a predicate (range,
nonzero, inequality), or none.

**Hash construction provenance.** Hash calls determine whether a word is an
anchor. BindCheck therefore identifies constructions, not just opcodes.
Every one of the 86 Poseidon2 opcodes in the pinned artifact is attributed
to a source-level construction (silo, unique note, or a Merkle node in one
of two orientations) with its initialization, absorption lanes, domain
separator and output lane (D1P-15 §3). The 77 compiler-lowered BN254
Poseidon regions are proposed from debug spans and then checked on the
decoded ACIR for straight-line locality and functionality (D1P-19 §3). On
M-DOM, the same extraction runs independently from the variant's own ABI. It
finds that the silo hash absorbs private witness 59 and that public word 5
is not its address input (D1P-21A §4). These region extractors are
artifact-specific: they accept only frozen artifact identities. §IX
discusses this limitation.

**Activation conditions.** Some constraints are active only under a
witness-dependent predicate, for example Payy's per-slot binding below
`messages_index` or WarpToad's same-root branch. The extractor records the
predicate when it can be recovered from the decoded program. Otherwise the
word's role is marked conditional with reason `UNRESOLVED_CONDITION`.

### C. Consumer extraction

The consumer extractor reads the pinned solc AST and symbolically follows
the actual function bodies and referenced declarations (route A; D1P-16). It
emits, for every terminal path family, the ordered guards, the terminal
status, the tentative and committed effects, and the rollback rule. The
verifier is the explicit relation `R_verify(proof, word0, …, word10)` and is
never assumed true. Each verifier argument carries its origin: a calldata
parameter, a storage read from the admitted pre-state, or an environment
read such as `block.chainid`. Library effects are typed by a shared,
versioned table keyed by resolved declaration. For OpenZeppelin 5.6.1, it
covers `_mint`, `_burn`, `_transfer`, `_update`, balances, total supply and
`Transfer`. The table declares `case_specific_entries=false` (D1P-18).
Unresolved calls, generic member or index access, unmodeled external calls
and unknown library declarations raise `UNSUPPORTED_<KIND>` with a source
location.

On the pinned `WarpToadCore.mint`, extraction recovers 22 path families
(3 success, 19 revert). The five archived real executions select one family
each with zero disagreements (D1P-18). Run unchanged on the M-SRC consumer,
the extractor recovers 21 families: exactly the K2 revert family and its
positive guard disappear (D1P-21B §3). Admitted-state values (the configured
Aztec address) and environment values (chain ID) are bound from required
inputs rather than module constants. Omitting either input raises a named
rejection (D1P-21B §2).

### D. Boundary join

The join equates each consumer verifier argument with the corresponding
public witness through `D_v`. Its preconditions are checked: equal arity,
the declared ABI order, and the documented casts (for example address →
`bytes20` → `uint160` → `uint256` → left-padded `bytes32`). Canonicality is
explicit. A word is admissible only if it is `< P`, because the verifier
rejects rather than reduces (D1P-12R §7). Any consumer-side hash library that
reduces modulo `P` is modeled as reducing (D1P-19 §7.3). A failed
precondition makes the case `UNKNOWN` (`BOUNDARY_MISMATCH`). It never makes
a rule silently skip a word.

### E. Polarity classification

Each public word `i` gets two labels, computed per producer activation
condition and per consumer path family.

**Producer role** (from §V-B):

- `ANCHOR`: the producer checks a value computed from private witnesses for
  equality against `i` (a Merkle root, a commitment). The circuit's
  guarantees are relative to `i`.
- `BOUND`: `i` is an input lane of a construction whose output reaches an
  `ANCHOR` equality, or `i` is equated to a function of private witnesses
  (for example a nullifier). The accepted relation fixes `i` relative to the
  witness and the anchors.
- `CHOSEN`: only predicate constraints read `i`. The proof commits to the
  value through the transcript, but the prover may pick any value that
  satisfies the predicates.
- `FREE`: no constrained opcode reads `i` under the given activation
  condition.

**Consumer polarity** (from §V-C), on a successful path family:

- `SUPPLIED`: the consumer fills `i` from configuration, environment or
  storage, or guards it by membership in or equality with trusted state
  before any protected effect. The consumer *asserts* this context.
- `CONSUMED`: `i`, or a value data-dependent on it, determines a field of a
  protected effect (amount, beneficiary, asset, storage key) or a dispatch
  decision that selects an effect.
- `PASSED`: `i` comes from calldata, reaches the verifier, and is neither
  guarded against trusted state nor consumed.

A word can be both `SUPPLIED` and `CONSUMED`. Polarity is an implementation
fact (contract §6.1). Policy roles in `σ` say only what a consumed field
*means*, for example "beneficiary", and whether prover choice of that field
is permitted.

### F. Generic rules

Rules are evaluated on each (word, producer condition, consumer path)
triple. Table 1 shows which role–polarity pairs raise which warning.

*Table 1: Role–polarity rule matrix.*

| Producer role \ Consumer polarity | `SUPPLIED` | `CONSUMED` | `PASSED` |
| --- | --- | --- | --- |
| `ANCHOR` | no warning (anchored) | **R-ANCHOR** unless also `SUPPLIED` on the path | **R-ANCHOR** |
| `BOUND` | no warning | R-EFFECT clauses apply | no warning (informational) |
| `CHOSEN` | no warning | **R-EFFECT** if `σ` forbids prover choice for that role | no warning |
| `FREE` | **R-BIND** (context not bound) | **R-BIND** (effect from free word) | informational |

**R-BIND.** *If a word is `FREE` under some producer activation condition and
is `SUPPLIED` or `CONSUMED` on some successful consumer path whose decoding
reaches it under that condition, warn.* Intuition: the consumer relies on the
proof for a value that the proof does not constrain. In Payy, words at or
above `messages_index` are free, and the consumer decodes protected burns
from them. In M-DOM, word 5 is free, and the consumer supplies it as the
domain identity, so the proof no longer depends on it. Repair locus:
producer (add the missing constraint or bind the context into the relation).

**R-ANCHOR.** *If a word is an `ANCHOR` under some producer activation
condition and is not `SUPPLIED` on some successful consumer path consistent
with that condition, warn.* Intuition: the circuit proves membership or
equality relative to a value that the consumer accepts from the caller. In
M-SRC, word 4 is the membership root on the same-root branch, and after K2
is removed it is `PASSED` on every success family. In pinned WarpToad, K2
guards it on all three success families, and the rule does not fire. Repair
locus: consumer (guard the word against trusted state before effects).

**R-EFFECT.** *For each committed protected effect occurrence on a successful
path, warn if (a) a policy-role field depends on a word that is `FREE`, or
`CHOSEN` where `σ` forbids prover choice, or depends on calldata outside the
verifier arguments; or (b) `σ` marks the authorizing permission single-use
and no single-use record keyed by a `BOUND` word is written on that path.*
Intuition: each effect must trace back to bound words and must not be
repeatable beyond its permission. Clause (a) overlaps R-BIND for free words;
both warnings are emitted and deduplicated by locus. In Payy, burn effects
fail (a) through free words and (b) through the missing registration.
Repair locus: consumer or policy.

The case illustrations above describe the facts each rule is designed to
observe. They are not results. Whether the implemented classifier recovers
those facts and the rules fire as described is RQ1 **[PENDING D1P-30]**.

**What the rules do not use.** No rule names a variable, index, application
or expected value. The only inputs are the extracted facts and the policy
roles of §III-E. The B02 obligations O1/O2 and the admitted-state designs
are not rule inputs. A warning on M-DOM or M-SRC therefore has to arise from
the generic matrix (contract §2, RQ2). Rule definitions, the matrix and the
extractor versions are hashed and frozen before any held-out artifact is
opened (RQ4).

*Status:* the matrix and rules above are a specification. Their
implementation and frozen hashes are **[PENDING D1P-30]**.

### G. Actionable diagnostics

A warning is a record with:

- rule identifier, public word index and ABI name, producer role (with the
  activation condition) and consumer polarity (with the path family);
- **producer locus:** the constrained opcodes that read the word, or their
  absence, mapped to Noir source spans through embedded debug symbols;
- **consumer locus:** the guard list of the path family, the verifier call,
  and each effect site (source line, effect kind, field roles);
- **repair locus:** producer, consumer or policy, as given by the rule;
- the policy roles used, every `ASSUMED` fact it depends on, and reason codes;
- the evidence level reached by validation, with the witness, proof, verifier
  and transaction hashes.

Warnings are deduplicated by (word, producer locus, consumer locus).
Overlapping R-BIND/R-EFFECT reports on the same locus are merged and keep
both rule identifiers.

### H. Automatic real-proof validation

Validation turns a warning into a concrete candidate without hand steps. It
uses concrete execution of the actual compiled circuit, not a whole-relation
SMT query. This choice follows the evidence: every whole-relation and
full-producer SMT query in our development history timed out or ended
without an answer (D1P-07, D1P-10, D1P-14D, D1P-17; Appendix A). By
contrast, every real-proof command for the 25,073-opcode WarpToad circuit
completed in roughly 8–11 seconds of observed wall time (D1P-14A §7; D1P-21A
§5). Those are operational observations, not benchmarks.

1. **Seed.** Start from an honest witness for the variant under test,
   obtained by executing the project's own witness generator from the
   admitted pre-state. Real-proof generation is one-shot per namespace and
   recorded.
2. **Rule-specific candidate synthesis (E2).** Each rule has one generic
   template.
   - *R-BIND (free word).* Hold the honest witness and change only the free
     words. Choose their values by solving the consumer path condition of an
     effect-bearing family over those words alone. This is a small
     consumer-side query: producer words outside the free set stay fixed. For
     a free context word, re-run the witness generator with the context value
     replaced by a distinct value that has data in the admitted state.
   - *R-ANCHOR (unanchored root).* Build a private structure (for example a
     Merkle tree) with the extracted construction and the reference hash
     implementations. Its leaf carries policy-violating content. Set the
     anchor word to its root.
   - *R-EFFECT.* Construct an occurrence whose field differs from every
     compatible permission, or resubmit an accepted occurrence where no
     single-use record is written.
   
   The candidate is accepted as E2 only if the compiled circuit executes on
   it (`nargo execute` succeeds). The rule's extracted fact is never trusted
   in place of execution.
3. **Proof (E3).** Prove with the variant's own key and check acceptance by
   the generated Solidity verifier deployed for that variant.
4. **Consumer and state (E4).** Deploy the unchanged consumer of the variant
   on a fresh owned-local chain in the admitted pre-state and submit. Read
   effects from state (balances, total supply, nullifier and root storage),
   not from events. Evaluate them against `σ`.
5. **Differential (when a paired variant exists).** Submit the same semantic
   input to the paired variant (for example the pinned build) and record
   where it is rejected: witness execution, verifier, or a named consumer
   guard.

Every step fails closed. The outcome is `UNKNOWN` with one of
`WITNESS_UNSAT`, `PROOF_FAILED`, `VERIFIER_REJECT`, `CONSUMER_REVERT@<guard>`,
`EFFECT_NOT_OBSERVED` or `STATE_NOT_ADMITTED`. A consumer revert at a named
guard is reported as *mitigated at that guard* with its location. It is not
reported as a false alarm and not as safety.

**Admitted state.** Some templates need state that contains data for another
context, such as a foreign-contract note. Admitted states are analyst inputs
(contract §6.2). They are counted, hashed and reported with every result,
and the result is labeled fixed-pre-state rather than reachable.

*Status:* each step above has been executed by hand-written fixtures on the
development cases (T15–T18; D1P-15; D1P-19; D1P-21A). Their automation as one
validator driven by warnings is **[PENDING D1P-30]**.

### I. What a result means

A warning is E1 and is not a vulnerability claim. A validated warning is E4
relative to `σ` and the admitted state, and is labeled with both. No rule
result is ever `VERIFIED_WITHIN_SCOPE`. The rules over-approximate within the
fragment: an unsupported construct stops the analysis with `UNKNOWN`, and
the absence of warnings on a supported input is reported as
"no warning (E0)". The bounded formal target of contract §7 concerns the
joint transition model. This paper proves no preservation theorem.

---

## VI. Implementation

BindCheck's D1 components are written in Python, with TypeScript fixtures
for proving and chain interaction. The table lists components that exist,
with the evidence that validates each one on the development fragment.

| Component | Location | Validation evidence |
| --- | --- | --- |
| ACIR decoder, Noir beta.14 (Payy) | `src/bindcheck_d1/frontends/acir_binary_v1.py`, `acir_bindings_v1.py` | Typed recursion/frame bindings (D1-03 typed bindings) |
| ACIR decoder and semantic checker, Noir beta.22 | `frontends/acir_binary_beta22.py`, `acir_semantics_beta22.py` | Exact rebuild match; 24,967/24,967 supported constraints on honest witness; two predeclared mutation controls (D1P-13) |
| Poseidon2 construction provenance | `warptoad_poseidon_provenance.py`, `warptoad_variant_provenance.py` | 86/86 opcodes attributed; 172 permutation tuples match references (D1P-15); independent M-DOM run (D1P-21A) |
| BN254 region extraction and function-identity audit | `warptoad_bn254_regions.py`, `warptoad_p6.py` | 77 regions, 24,448 core equations checked; identity and domains audited (D1P-19, D1P-21A) |
| Consumer extractor (route A) and shared library models | `prototypes/d1p16/extract_relation.py`, `library_effect_models.v1.json` | 22 families; 5/5 executions; three source-mutation and four edge-control classes (D1P-16, D1P-18) |
| Variant-general relation serializer | `prototypes/d1p20/`, `prototypes/d1p21b/` | Pinned 22/19/3 and M-SRC 21/18/3; 8/8 polarity controls; state/environment binding (D1P-20, D1P-21B) |
| Real-proof and chain fixtures | `scripts/d1p_12r_*`, `d1p_14a_*`, `d1p_15_*`, `d1p_19_*`, `d1p_21a_*` | One-shot proof ledgers; on-state effect checks |
| Polarity classifier, rule engine, warning emitter | — | **[PENDING D1P-30]** |
| Warning-driven validator | — | **[PENDING D1P-30]** |

**Toolchains (pinned).** Payy: Noir `1.0.0-beta.14+60ccd48e…`, bb 3.0.0,
solc 0.8.20, Forge 1.4.1. WarpToad: Noir `1.0.0-beta.22+c57152f9…`, bb.js
5.0.0 UltraHonk `keccakZK`, solc 0.8.29 (optimizer, 1 run, Cancun), Hardhat
3.3.0 EDR. Solver for validation-side consumer queries: cvc5 1.4.2. All
chains are fresh in-process instances with no fork.

**Tests.** The complete D1 suite passes 231 tests and 312 subtests (Python
3.13.9; D1P-21A §5). The artifact-specific tests need the ignored evidence
workspaces. Rule-engine tests: **[PENDING D1P-30]**.

**Generality limits of the current implementation.** The beta.22 region
extractors accept only frozen artifact identities. The consumer extractor
supports one entry point's reachable constructs and one versioned library.
Payy's `RollupV1` has not been processed by route A, and the forwarding
through `agg_final` is supported only through the beta.14 typed bindings.
Payy rows in RQ1 therefore depend on D1P-30 extending these components. If
they are not extended, the rows are reported as unsupported, not as misses.

---

## VII. Evaluation

### A. Research questions

| Paper RQ | Question | Contract RQ (rev. 2) | Task |
| --- | --- | --- | --- |
| **RQ1 Detection** | Do the generic rules warn at the correct loci on the development cases and the development mutation benchmark, without case-specific input? | RQ1 (fidelity), RQ2 (discovery) | D1P-30 |
| **RQ2 Warning quality** | Are warnings localized and actionable, and how many validate automatically to E4, at what cost and with how many manual steps? | RQ3 (validation) | D1P-30 |
| **RQ3 Baselines** | Which E1–E4 results do circuit-only, contract-only and joint baselines obtain under generic/default and same-policy arms? | RQ4 (comparative) | D1P-31 |
| **RQ4 Held-out** | With rules frozen, what does BindCheck report on reserved families, and do any reports validate? | RQ4 (transfer) | D1P-32 |
| **RQ5 Taxonomy** | Which causes, consequences and roles recur across independent families in sampled disclosures, and how reliably can humans label them? | — (descriptive; protocol v0.2.0) | D1P-33 |

### B. Subjects and protocol

**Development cases.** Payy earlier `c4d2c902…` (faulty, historical) and
check-added `dcd5d96e…` (repaired for one witness); WarpToad pinned
`973e7d1e…` (honest fixture, not a proven negative); WarpToad M-DOM and
M-SRC (injected).

**Development mutation benchmark.** The mutation operators are derived from
observed mechanisms and from the taxonomy causes in §IV-C, and are applied
only to development families (contract §9). Each mutant must compile, pass
an honest control (reachability), and change the target property, shown by a
real-proof differential or by a predeclared concrete differential. Mutants
that fail a gate are reported, not dropped. The operator list, sites and
gates are frozen in the D1P-30 protocol before any rule result is
inspected. The benchmark measures the rules' coverage of operator classes
across sites. It is not discovery evidence: the operators and the rules
share a source, and both are development data.

| Operator | Taxonomy cause | Side | Origin mechanism |
| --- | --- | --- | --- |
| OP-UNBIND | `C_RELATION_GAP` | Producer | M-DOM (public word replaced by private input in a constraint) |
| OP-EXTENT | `C_ACTIVATION_EXTENT` | Producer | Payy (extent or padding assertion removed) |
| OP-UNANCHOR | `C_CONTEXT_IDENTITY` | Consumer | M-SRC (trusted-state guard on an anchor word removed) |
| OP-REDIRECT | `K_MISDIRECTED` via `C_FIELD_MAPPING` | Consumer | D1P-18 control (effect beneficiary taken from another word) |
| OP-SINGLEUSE | `C_OCCURRENCE_ACCOUNTING` | Consumer | Nullifier write or check removed or rekeyed (D1P-18 control) |
| OP-CTXFREE | `C_CONTEXT_IDENTITY` | Consumer | Context word moved from configuration or environment to calldata |

*The operator list is this draft's proposal; D1P-30 freezes the final list.*

**Policy.** Each case receives the reviewed policy roles `σ`: protected
effects, field roles, and single-use permissions. The same `σ` is given to
every same-policy baseline arm. For WarpToad, `σ` is DRAFT where the
documentation leaves beneficiary policy open (D1P-12R §8.1). Warnings that
depend on that clause are adjudicated, not scored as detections or false
alarms.

**Scoring loci** (from [baselines.md](baselines.md) §4.3, extended to the
variants; used for scoring only and never as tool input):

- Payy producer: `agg_agg` outer `messages` words at indices ≥
  `messages_index`, or absence of a tail-zero constraint. Payy consumer:
  `verifyBurn`/`executeBurn` transfers from proof-derived words without
  registration.
- M-DOM: public word 5 (`aztec_warptoad_address`) unconstrained, or the silo
  hash's address input not bound to it.
- M-SRC: public word 4 (`destination_local_root`) unguarded on a successful
  `mint` path, or the missing `isValidLocalRoot` guard.

**Budgets and accounting.** BindCheck's per-case analysis budget, and the
never-below rule for baselines, are frozen before the first run. Setup,
proving and adjudication are timed separately. Manual inputs are counted by
category: policy roles, admitted states, `ASSUMED` facts and adapter code.

### C. RQ1 — Detection on development cases and benchmark

*Table 2: Detection on development cases.*

| Case | Class | Variant pins (artifact / VK / verifier / consumer) | Rule(s) fired | Word(s) | At scoring locus? | Highest level (E0–E4) | Fully automatic? | Manual inputs (count by category) | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Payy `c4d2c902` | Historical, faulty | `agg_agg`/`agg_final` beta.14; key `0x122d2ac7…`; `RollupV1` | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] |
| Payy `dcd5d96e` | Historical, repaired (one witness) | own key `0x0701c58c…`; same consumer source | [PENDING D1P-30] | [PENDING D1P-30] | n/a (adjudicate) | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] |
| WarpToad pinned | Honest fixture (not proven negative) | `7190813f…` / `563a018c…` / `d9a822a5…` / `323a1cf2…` | [PENDING D1P-30] | [PENDING D1P-30] | n/a (adjudicate) | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] |
| WarpToad M-DOM | Injected, producer | `db1a0a17…` / `3bc51af9…` / `d5ceca6e…` / `323a1cf2…` | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] |
| WarpToad M-SRC | Injected, consumer | `7190813f…` / `563a018c…` / `d9a822a5…` / `64ec0efd…` | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] |

Unsupported cases are reported as unsupported, never as misses.
`UNKNOWN` is never counted as safe.

*Table 3: Detection on the development mutation benchmark.*

| Operator | Family | Built | Compile | Honest control passes | Property-changing (gate) | Detected E1 | E2 | E3 | E4 | Missed | Unsupported | Unresolved |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OP-UNBIND | WarpToad | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] |
| OP-EXTENT | Payy | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] |
| OP-UNANCHOR | WarpToad | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] |
| OP-REDIRECT | WarpToad | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] |
| OP-SINGLEUSE | WarpToad | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] |
| OP-CTXFREE | WarpToad | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] |
| **Total** | — | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] |

A mutant counts toward "Detected" only if it passed all three gates.
Columns E1–E4 record the highest level reached and sum to "Detected".

**Answer to RQ1.** [PENDING D1P-30]

### D. RQ2 — Warning quality and automatic validation

*Table 4: Per-warning record (development cases; benchmark warnings in the
artifact).*

| Warning | Case | Rule | Word | Producer locus (span) | Consumer locus (path / guard / effect line) | Repair locus | Adjudication (target / false alarm / real out-of-scope / new candidate / policy-dependent) | Validation outcome (E-level or `UNKNOWN` reason) | Validation wall time | Proofs used | Manual steps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] |

*Table 5: Warning-quality summary.*

| Scope | Warnings (dedup.) | At scoring locus | Producer locus correct | Consumer locus correct | Non-target: false alarm | Non-target: real out-of-scope | Non-target: new candidate | Policy-dependent | Reached E4 | Mitigated at named guard | `UNKNOWN` (by reason) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Development cases | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] |
| Benchmark | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] |

We report counts, not precision. The honest fixtures are not proven
negatives, so a "false alarm" rate over them would be ill-defined (contract
§9). A new candidate goes through the same validation and, if confirmed,
through responsible disclosure before it supports any claim.

*Table 6: Analyst effort and manual inputs (BindCheck vs. a hand-written
same-policy Foundry property, per [baselines.md](baselines.md) §5).*

| Case | Policy roles (lines) | `ASSUMED` facts (lines; target 0) | Admitted-state inputs | Adapter/harness lines | Authoring time | Corrections (count, time) | Proof seeds | Adjudication time | Total analyst time | Foundry property (same measures) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-31] |

Historical reference point: the hand-written Payy mint property was about 90
lines of Solidity (87 non-comment) and functionally equivalent to the earlier
checker's manual specification (T14 §4).

**Answer to RQ2.** [PENDING D1P-30]

### E. RQ3 — Comparison with circuit-only, contract-only and joint baselines

Baselines, versions, arms, budgets and setup are preregistered in
[baselines.md](baselines.md). Every baseline candidate at E1 or E2 enters the
same validation pipeline, with the same budget and adjudicator as BindCheck's.
An unsupported native frontend is reported as unsupported, not as an
algorithmic miss.

*Table 7: Baseline outcomes. Class ∈ {detected (level), missed, unsupported,
unresolved}; G = generic/default arm, S = same-policy arm; n/a = no property
interface (reason in artifact).*

| Baseline | Arm | Payy `c4d2c902` | Payy `dcd5d96e` | WarpToad pinned | M-DOM | M-SRC | Non-target reports (adjudicated) | Analysis time | Setup effort |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Noir compiler checks | G | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| Noir compiler checks | S | n/a | n/a | n/a | n/a | n/a | — | — | — |
| CCC-Check | G | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| CCC-Check | S | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| Circomspect | G | unsupported (Noir) | unsupported | unsupported | unsupported | unsupported | — | — | — |
| Picus (adapted, if predeclared) | G | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| CIVER (adapted, if predeclared) | G / S | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| Slither | G | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| Slither (custom detector) | S | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| Mythril | G | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| Mythril (`σ` as assertions) | S | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| Foundry invariants (G1–G5 where justified) | G | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| Foundry invariants (`σ` property) | S | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| Echidna | G | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| Echidna (`σ` property) | S | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| SmartAxe | G | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| Joint: monolithic query | S | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| Joint: goal-cone query | S | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| Ablation: BindCheck without consumer facts (producer-only rules) | — | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| Ablation: BindCheck without producer facts (consumer-only rules) | — | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| **BindCheck** | S | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] | [PENDING D1P-30] |

The two ablation rows test the cross-layer claim directly. Each withholds
one side's facts from the rule matrix while keeping the same cases and
policy. If either ablation matches full BindCheck on all five cases, the
cross-layer join adds nothing on these cases, and we will say so. The
M-DOM and M-SRC baseline rows extend [baselines.md](baselines.md), which
predates the variants. The extension must be preregistered before D1P-31.

**Answer to RQ3.** [PENDING D1P-31]

### F. RQ4 — Held-out scan

**Protocol.** Rules, the polarity matrix, the extractor versions and the
validator are hashed and frozen before the first held-out artifact is
opened. Held-out families come from the private reservation (§IV-D) or from
an equivalent frozen inventory. Every attempted build and every exclusion is
reported. No rule changes after the scan begins. A post-hoc correction is
reported as such, and the affected family stops counting as held out
(contract §§9, 11). Any confirmed finding is disclosed to its maintainers
before it supports a claim, and is anonymized in the submission.

*Table 8: Held-out funnel and results.*

| Family (anonymized) | Reserved before development? | Prior exposure (log) | Producer / consumer stack | Artifacts available | Supported | Analyzed | Warnings (R-BIND / R-ANCHOR / R-EFFECT) | Adjudication | Highest level | New rules added (must be 0) | Disclosure status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] |

*Table 9: Held-out funnel totals.*

| Stage | Families | Applications | Notes |
| --- | --- | --- | --- |
| Reserved / frozen inventory | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] |
| Artifacts available | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] |
| Supported (Noir/ACIR + Solidity fragment) | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] |
| Analyzed to completion | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] |
| With ≥1 warning | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] |
| Validated (E4) | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] |

Stages are monotone. An unsupported family explains attrition and is never
counted as a miss or as safe.

**Answer to RQ4.** [PENDING D1P-32]

### G. RQ5 — Taxonomy

*Table 10: Disclosure funnel (human annotation only).*

| Stage | Count | Unit |
| --- | --- | --- |
| Raw retrieval hits | [PENDING D1P-33] | hits |
| Unique source documents | [PENDING D1P-33] | documents |
| Candidate findings (before deduplication) | [PENDING D1P-33] | findings |
| Canonical findings | [PENDING D1P-33] | findings |
| Included / excluded / unresolved | [PENDING D1P-33] | findings |
| Families represented (included) | [PENDING D1P-33] | families |
| Unresolved duplicate matches | [PENDING D1P-33] | pairs |

*Table 11: Label frequencies over included canonical findings, by family.*

| Label | Present (findings) | Present (families) | Uncertain | Absent | Example family (anonymized) |
| --- | --- | --- | --- | --- | --- |
| `C_RELATION_GAP` … `C_OTHER_BINDING` | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] |
| `K_AUTHORIZATION` … `K_OTHER_EFFECT` | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] |
| `A_PUBLIC_CALLER` … `A_OTHER_ROLE` | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] |

(One row per label in the final table.)

*Table 12: Inter-annotator agreement (16 fresh packets, two annotators).*

| Field / label | Comparable n | Positives / negatives | Raw agreement | Coefficient (κ or α) | 95% interval | Missing / null |
| --- | --- | --- | --- | --- | --- | --- |
| Relevance (include / exclude / unresolved) | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] |
| Each cause, consequence and role label | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] |

*Table 13: Tool funnel for included findings (separate denominator).*

| Stage | Findings | Families | Main attrition reasons |
| --- | --- | --- | --- |
| Artifacts available | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] |
| Supported by BindCheck | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] |
| Cause covered by a rule (§IV-C) | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] |

**Answer to RQ5.** [PENDING D1P-33]

### H. Threats to validity

**Development bias.** The rules were designed after the three case studies
were known. Payy's defect, advisory and end-to-end artifact predate the
rules. WarpToad was screened and inspected in D1-02, D1P-11 and later tasks.
RQ1 and RQ2 therefore show capability *on these cases* only (contract §9).
Transfer rests on RQ4 alone.

**Injected cases.** M-DOM and M-SRC are injected. M-DOM is grounded in an
unused in-tree package and a developer warning, M-SRC in documented
reliance. Neither indicates a defect in pinned WarpToad. Benchmark operators
share mechanisms with the rules (§VII-B).

**Admitted state.** The M-DOM differential uses privileged synthetic root
admission (`S_DOM`). Neither variant demonstrates cross-chain reachability.

**Policy.** `σ` for WarpToad is DRAFT for beneficiary selection.
Policy-dependent warnings are reported separately.

**Negatives.** No fixture is a proven negative control. We report adjudicated
counts, not false-positive rates.

**AI involvement.** AI agents implemented code, drafted reports, wrote the
B02 obligations and drafted this text (§X-B). AI output is not independent
annotation (contract §10). Taxonomy labels come only from human annotators.

---

## VIII. Related Work

We group prior work by which side of the boundary it analyzes. Each
difference stated below is derived from the cited text where marked, and is
otherwise **[TODO-VERIFY]**. Empirical overlap with BindCheck on our cases is
measured in RQ3, not asserted here.

### A. Integration-layer framing

The **SNARK SoK** [1] classifies 141 SNARK vulnerabilities across circuit,
frontend, backend and integration layers. It defines integration-layer bugs
as stemming "from improper interactions between the application/system and
the prover or verifier" (§6). It reports that "there are currently no
specific defenses developed for vulnerabilities in the integration layer"
and suggests "multi-layer testing and verification techniques targeting
both these components simultaneously" (§8). BindCheck is one concrete
instance of that direction for the Noir/Solidity boundary. Our taxonomy
refines the SoK's integration layer at the level of individual public words,
with authorization/coverage consequences, and differs from it in
sampling frame and annotation protocol. *Verified against arXiv 2402.15293
(§§6, 8).*

### B. Circuit-only analysis

These tools reason about a circuit relation in isolation.

- **Noir compiler checks** flag values disconnected from both inputs and
  outputs, and unconstrained-call results not used by a later constraint.
  Whether they flag an unused *public input* such as M-DOM's word 5 at the
  pinned beta.22 compiler is **[TODO-VERIFY]**, then measured in RQ3.
- **Circomspect** (Circom linting passes) and **Picus** (QED²
  under-constrained-signal detection [9]) target Circom or R1CS. Neither
  accepts Noir ACIR natively. Picus's uniqueness property concerns outputs
  given inputs. Whether it can express "public input word `i` is
  unconstrained" is **[TODO-VERIFY]**.
- **CIVER** [3] verifies Circom circuits modularly against weak safety, tag
  specifications and pre/postconditions over circuit signals. Its
  specifications describe circuit signals, not contract effects.
  *Abstract, SoK description and README only; full text
  **[TODO-VERIFY]**.*
- **Coda** [4] re-implements circuits in a refinement-typed language and
  discharges obligations in Coq. In the text we read, it does not model a
  consuming contract: the phrase "smart contract" does not occur. *Verified
  against the author-hosted full text.*
- **CCC-Check** [5] detects computation–constraint inconsistencies by
  value inference over an IR, and compares a circuit's witness computation
  with its own constraints. Payy's tail is a case where the out-of-circuit
  witness builder writes trailing zeros that the circuit does not enforce,
  so CCC-Check's applicability to Payy is a genuine open question,
  **[TODO-VERIFY]**, measured in RQ3. *Abstract only.*

The common limitation, as we understand these designs, is informational. A
circuit-only tool cannot know that a consumer decodes effects from a word
(Payy), supplies a word as context (M-DOM), or fails to anchor a word
(M-SRC). In M-SRC the circuit is unchanged, so no circuit-only report can be
specific to the defect.

### C. Contract-only analysis

These tools treat the verifier as an opaque call.

- **Slither** [10] runs static detectors over Solidity.
- **Mythril** symbolically executes EVM bytecode [11].
- **Echidna** [12] and **Foundry invariants** [13] fuzz properties over call
  sequences.

None of them models the circuit relation, so none can tell which verifier
arguments are bound. In the same-policy arm a fuzzer can check `σ`, but it
needs a valid proof for every input it explores. Seeded only with honest
proofs (baselines §3.1), it cannot produce a proof of a forged statement. In
our own Payy work, the consumer-side test exercised the forged effect only
because we supplied a hand-built forged proof (T18). RQ3 tests whether this
reasoning holds for the baselines.
**SmartAxe** [6] analyzes cross-chain bridge bytecode. Its semantic-integrity
check reports withdrawal state with *no* data-flow dependency on deposit
state (§4.3). In Payy and M-DOM, the effect fields *do* flow from verified
public inputs. The defect lies in what the circuit constrains, which
SmartAxe does not analyze. *Verified against arXiv 2406.15999v1 (§§2.3,
4.3).*

### D. Joint analysis

Our earlier exploratory work encoded producer, decoder, consumer and policy
as one SMT query. Those queries did not resolve at the sizes we tried
(Appendix A). BindCheck therefore uses joint *facts* and generic rules, with
validation by concrete execution and real proofs, rather than a monolithic
joint query. The monolithic and goal-cone joint queries remain RQ3 baselines.

---

## IX. Limitations

**Fragment.** The supported fragment is a Noir/ACIR producer and one
Solidity entry point per consumer, with OpenZeppelin 5.6.1 effects, standard
atomic ERC-20 behavior, and no proxies, delegate calls, inline assembly or
reentrancy. The beta.22 hash-region extractors are artifact-specific.
Unsupported constructs stop the analysis with `UNKNOWN`. That keeps results
honest but bounds applicability, and RQ4's funnel measures how much.

**Hash semantics.** Poseidon2 is modeled at most as a functional
uninterpreted tuple function (equal inputs give equal outputs), with no
injectivity or collision resistance (D1P-19 §2.2). Role classification uses
construction provenance, not hash semantics. Validation uses real hashes.
Any conditional no-collision argument (B02 §3) is outside this paper's
results.

**Conditional binding.** Payy's binding depends on a witness-dependent
extent. If the extractor cannot relate the producer's activation condition
to the consumer's scan, R-BIND reports `UNRESOLVED_CONDITION`. Earlier ACIR
and SMT work on exactly this pattern produced an analyzer false positive
from unsound probe specialization (later repaired), and general queries that
did not finish (T22, T22-v3, T22-v4). It also showed that consumer-shape
facts remove only 4–8 of 620 cone operations at a scaled size (D1P-09).

**Scale.** Payy's real proofs and consumer replays use the original
1,000-message, 1,003-public-input configuration. Earlier solver queries used
a scaled N=8 transformation. These evidence grades are kept separate.

**Single-call scope.** Validation covers one consumer call from a fixed
admitted pre-state. Multi-transaction histories (`Reach_L ≥ 2`), front-running
and observation of honest proofs are out of scope. They would require
stronger extraction assumptions (B02 §3.1).

**No safety claims.** BindCheck never returns `VERIFIED_WITHIN_SCOPE` from
rule silence. Absence of warnings is E0 within the fragment.

**Not novel by itself.** Integration-layer failures [1], rich circuit
specifications [3, 4] and computation–constraint consistency [5] are prior
work. Our claim is limited to the cross-layer rule set and its automatic
validation, to the extent that RQ1–RQ4 support it.

---

## X. Ethics Considerations and Disclosures

Venue requirements are from the IEEE S&P 2027 call for papers [8], retrieved
26 October 2026.

### A. Ethics considerations

- **Live systems.** None. All experiments used fresh in-process chains,
  synthetic notes and assets, and owned prover, validator, relayer and
  deployer identities. Nothing was broadcast, and no maintainer was
  contacted (T18; D1P-12R; D1P-15; D1P-19; D1P-21A).
- **Vulnerability disclosure.** Payy's defect was disclosed publicly by
  others [2]; we reproduced it and did not discover it. M-DOM and M-SRC are
  our own injected variants and imply no defect in WarpToad. Any new
  candidate from RQ2 or RQ4 is disclosed to its maintainers before the
  original submission where possible, and no later than the rebuttal
  deadline, as the CFP requires [8]. The paper will describe the steps taken
  **[PENDING D1P-32]**.
- **New tool.** BindCheck's validator produces working forged proofs against
  local deployments. Misuse risk: an attacker could use validated warnings
  against live systems. Mitigations: validation runs only on owned-local
  chains with fresh deployments. The planned artifact omits automation for
  live-network submission **[TODO: authors confirm]**. Held-out findings are
  released only after disclosure. The benefit is that developers can find and fix
  binding failures before deployment, the same capability attackers already
  apply by hand.
- **Human subjects.** The taxonomy study uses public disclosures, and its
  annotators are research staff labeling documents. Whether this requires
  IRB review is **[TODO]** for the authors' institution.

### B. Generative-AI disclosure

AI agents wrote code, task reports, the B02 obligations, screening notes and
draft text. AI use is therefore integral to the methodology and is
described explicitly, as the CFP requires [8]. AI systems are excluded from
taxonomy annotation and adjudication. Authors inspect every claim, citation,
label and result. **[TODO]** Write the disclosure from the preserved task
prompts and reports.

### C. Competing interests

**[TODO]** Authors to supply.

### D. Submission constraints

13 pages of text plus up to 5 pages of references and appendices (18 total);
IEEEtran `compsoc` v1.8b; anonymous review. Internal repository links must be
replaced with an anonymized artifact. Submissions must not include full CVE
identifiers, so only the GHSA identifier appears; whether linking a
third-party advisory is acceptable is **[TODO]** for the PC chairs. Cycle 2:
abstract registration 10 November 2026, submission 17 November 2026
(AoE) [8].

---

## XI. Conclusion

Proof-to-execution binding failures arise when the words a consumer relies
on and the words a circuit constrains disagree. They are properties of the
pair, not of either component. BindCheck makes this agreement checkable. It
extracts word-level facts from both sides, classifies each word's role and
polarity, applies three generic rules, and attempts to turn each warning into
a real proof that moves state on an unchanged consumer. The case studies show
that such failures occur on both sides of the boundary: a historical
producer-side defect in Payy, and injected producer-side and consumer-side
variants of WarpToad, each with real-proof ground truth. On these cases
BindCheck [PENDING D1P-30]. Against baselines, [PENDING D1P-31]. On held-out
families, [PENDING D1P-32]. In public disclosures, [PENDING D1P-33].

---

## Appendix A. Exploratory solver results (contract RQ5; not capability evidence)

These results were gathered under the revision-1 efficiency hypothesis. They
are reported unchanged and are not evidence for any paper RQ (contract §11
change log).

- **D1P-07.** The scaled N=8 selected cone of Payy's check-added `agg_agg`
  has 620 operations and 540 witnesses. All six exact combined queries timed
  out at 300 s (cvc5 1.4.2, `--ff-solver=split`). A 25-cell partition
  resolved 58 of 150 cells and zero of six obligations.
- **D1P-09.** Eleven exact consumer reached-kind predicates partition the
  18,751 valid of 390,625 control-flow classes. They remove only 4–8 of 620
  cone operations.
- **D1P-10.** The unchanged baseline timed out on all four obligations. Both
  transformed arms failed their validation gates.
- **D1P-14B–D.** The first WarpToad joint encoder failed on a parse error
  (14B). After repair, a symbolic sensitivity control timed out (14C). Eight
  fixed-input polarity regressions passed, while the three diagnostics timed
  out or ended in a monitor error (14D).
- **D1P-17.** Abstracting the fee product resolved only the producer-dropped
  diagnostic (UNSAT in 8.2 s). The full-producer queries remained `UNKNOWN`.
- **Historical synthetic branch.** Refinement selected all constraints and
  was 3–9% slower than monolithic solving on authored N=9 fixtures. The
  integration review rejected its closure.

None of these timeouts is evidence of safety.

## Appendix B. Evidence map

| Claim in this paper | Evidence | Label |
| --- | --- | --- |
| Payy tail accepted by both recursive circuits | T15 §3; T16 §2 | Locally reproduced |
| Payy committed effect | T18 §2 | Locally reproduced, end to end (hand-built) |
| Payy repair rejects the witness | T19 §1 | Repair-validated (one witness) |
| WarpToad source/artifact correspondence | D1P-13 §2 | Mechanically checked |
| WarpToad honest mint, replay, canonicality | D1P-12R §§6–7 | Locally reproduced |
| Fee-cap and zero-fee behavior | D1P-14A | Locally reproduced |
| M-DOM own key; foreign-note mint; pinned rejects | D1P-15 §§5–6 | Locally reproduced (injected) |
| M-SRC mint over unadmitted root; pinned reverts at K2 | D1P-19 §4 | Locally reproduced (injected) |
| Exact-state honest controls, four pairings | D1P-21A §3 | Locally reproduced |
| M-DOM independent producer provenance | D1P-21A §4 | Mechanically checked |
| Consumer extraction, 22 families, fail-closed | D1P-16; D1P-18 | Mechanically checked on fragment |
| M-SRC extraction removes exactly K2 | D1P-21B §3 | Mechanically checked |
| Taxonomy design and search plan frozen | protocol v0.2.0; search plan | Design only |
| Rule results, validation, baselines, held-out, annotation | — | [PENDING D1P-30/31/32/33] |

---

## Open items for authors

1. Resolve the three disagreements listed at the top (contract change
   control for the contribution list; freeze the rule specification in
   D1P-30; confirm the RQ mapping).
2. Preregister the M-DOM/M-SRC baseline rows and the two BindCheck ablations
   as an addendum to [baselines.md](baselines.md) before D1P-31.
3. Supply full texts of CIVER and CCC-Check and resolve each
   **[TODO-VERIFY]**. Verify bibliographic details of [9]–[13].
4. Draw Figure 1. Replace repository links with an anonymized artifact.
5. Have a human author inspect every claim and citation (contract §10).

---

## References

Primary sources only. Section numbers refer to the version actually read.
Retrieval provenance is in [sources.md](sources.md).

[1] S. Chaliasos, J. Ernstberger, D. Theodore, D. Wong, M. Jahanara,
B. Livshits. "SoK: What Don't We Know? Understanding Security Vulnerabilities
in SNARKs." USENIX Security 2024. Read: arXiv:2402.15293.

[2] Payy (polybase/payy). Security advisory GHSA-fhxc-63vg-9gwr, published
10 June 2026. (Full CVE identifier omitted per the venue's anonymity rule
[8]; recorded in T20.)

[3] M. Isabel, C. Rodríguez-Núñez, A. Rubio. "Scalable Verification of
Zero-Knowledge Protocols." IEEE S&P 2024, pp. 1794–1812.
doi:10.1109/SP54263.2024.00133. Tool: github.com/costa-group/circom_civer.

[4] J. Liu, I. Kretz, H. Liu, B. Tan, J. Wang, Y. Sun, L. Pearson,
A. Miltner, I. Dillig, Y. Feng. "Certifying Zero-Knowledge Circuits with
Refinement Types." IEEE S&P 2024. doi:10.1109/SP54263.2024.00078.

[5] A. Kolozyan, B. Vandenbogaerde, J. Swalens, L. Hoste, S. Chaliasos,
C. De Roover. "Language-Agnostic Detection of Computation-Constraint
Inconsistencies in ZKP Programs via Value Inference." IEEE S&P 2026. Read:
abstract only, IACR ePrint 2025/2120.

[6] Z. Liao, Y. Nan, H. Liang, S. Hao, J. Zhai, J. Wu, Z. Zheng. "SmartAxe:
Detecting Cross-Chain Vulnerabilities in Bridge Smart Contracts via
Fine-Grained Static Analysis." Proc. ACM Softw. Eng. 1(FSE), 2024.
doi:10.1145/3643738. Read: arXiv:2406.15999v1.

[7] (Removed: the internal D1 reference proposal is not a citable source.)

[8] IEEE S&P 2027 Call for Papers. sp2027.ieee-security.org/cfpapers.html,
retrieved 26 October 2026.

[9] S. Pailoor et al. "Automated Detection of Under-Constrained Circuits in
Zero-Knowledge Proofs." PLDI 2023. Tool: Picus. **[TODO-VERIFY: not
retrieved]**

[10] J. Feist, G. Grieco, A. Groce. "Slither: A Static Analysis Framework
for Smart Contracts." WETSEB 2019. **[TODO-VERIFY: not retrieved]**

[11] Mythril, ConsenSys Diligence. github.com/Consensys/mythril (v0.24.8,
pinned in baselines.md). **[TODO-VERIFY: citation form]**

[12] G. Grieco, W. Song, A. Cygan, J. Feist, A. Groce. "Echidna: Effective,
Usable, and Fast Fuzzing for Smart Contracts." ISSTA 2020 (tool demo).
**[TODO-VERIFY: not retrieved]**

[13] Foundry. github.com/foundry-rs/foundry (v1.8.6, pinned in
baselines.md). **[TODO-VERIFY: citation form]**
