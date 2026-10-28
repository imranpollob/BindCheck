# BindCheck: Finding Proof-to-Execution Binding Failures at the Circuit–Consumer Boundary

*(Working title; frozen at abstract registration.)*

**Draft status:** D1P-P02 revision, 28 October 2026, on repository base
`ba571ff` (fast-forwarded from `d1-paper`; includes D1P-30, D1P-22 and the
Lane X mutation benchmark). Target format is IEEE S&P (13 pages of text plus
up to 5 pages of references and appendices). This revision rewrites §V to
describe the implemented BindCheck v1 rules, fills the development-case rows
from [D1P-30](../reports/D1P-30.md), and fills the case-study baseline rows
from [D1P-22](../docs/baselines/d1p-22-results.md). No experiment was run for
this draft. Cells that depend on work not yet done are marked
**[PENDING D1P-31]** (BindCheck on the mutation benchmark),
**[PENDING D1P-32]** (baselines on the benchmark), **[PENDING D1P-33]**
(held-out scan) or **[PENDING TAXONOMY-V1]** (taxonomy v1 corpus). Claims
about cited work that could not be checked against a primary source stay
**[TODO-VERIFY]**. Earlier drafts (D1P-D01/D03, D1P-P01) are in Git history.

**Controlling sources, in order.** [Research contract](../docs/research-contract.md)
revision 2 (revision 3, which adds the taxonomy and actionable diagnostics as
contributions, is being applied in D1P-31); [README](../README.md); the
immutable reports [T15](../reports/T15.md)–[T22](../reports/T22.md),
[D1P-12R](../reports/D1P-12R.md), [D1P-13](../reports/D1P-13.md),
[D1P-14A](../reports/D1P-14A.md)–[D1P-14D](../reports/D1P-14D.md),
[D1P-15](../reports/D1P-15.md),
[D1P-17](../reports/D1P-17-consumer-backends.md),
[D1P-19](../reports/D1P-19.md), [D1P-21A](../reports/D1P-21A.md),
[D1P-30](../reports/D1P-30.md); the baseline record
[D1P-22](../docs/baselines/d1p-22-results.md); the extraction records
[D1P-16](../docs/extraction/d1p-16-feasibility.md),
[D1P-18](../docs/extraction/d1p-18-hardening.md),
[D1P-20](../docs/extraction/d1p-20-extracted-solver-model.md),
[D1P-21B](../docs/extraction/d1p-21b-variant-extraction.md); the
[mutation benchmark](../docs/x-experiment/BENCHMARK.md)
([package](../benchmarks/binding-mutants/)); the
[B02 obligations](../docs/d1-paper/d1p-b02-discriminating.md); the
[taxonomy protocol v0.2.0](../docs/taxonomy/protocol.md); and the
[baseline preregistration](baselines.md). If this draft disagrees with any of
them, the source wins.

**Research verdict at drafting time:** `UNKNOWN`. D1P-30 ran BindCheck v1 on
five development targets. The capability gate (contract §11) remains open:
there is no held-out result, the same-policy baseline arms were not
instantiated, and the validator does not construct witnesses for an
arbitrary warning (D1P-30 §7; D1P-22).

### Task map

| Tag | Scope | Status at `ba571ff` | Paper locations |
| --- | --- | --- | --- |
| **D1P-30** | BindCheck v1 analyzer and validator; five development case runs | Done | §V, §VI, RQ1/RQ2 case rows |
| **D1P-31** | BindCheck v1 on the 30-mutant benchmark | Pending | RQ1/RQ2 benchmark rows |
| **D1P-22** | Pinned baselines on the five case targets | Done | RQ3 case table |
| **D1P-32** | Baselines on the 30-mutant benchmark | Pending | RQ3 benchmark table |
| **D1P-33** | Held-out scan | Pending | RQ4 |
| **TAXONOMY-V1** | Taxonomy v1 corpus, `docs/taxonomy/v1-corpus.md` (Lane X) | Pending; file not present at `ba571ff` | §IV-D, RQ5 |

Discrepancies found while drafting are listed under *Open items for authors*
at the end.

---

## Abstract

A zero-knowledge verifier establishes only the relation that its circuit
encodes. The contract that consumes an accepted proof then decodes the public
inputs and mints, transfers, records nullifiers or advances state. Whether
those effects are justified is a property of neither component alone. It
depends on whether every public value the consumer relies on is actually
constrained by the circuit, and whether every value the circuit trusts is
actually checked by the consumer against its own state. We call violations of
this agreement *proof-to-execution binding failures*. BindCheck analyzes the
circuit–consumer boundary of Noir/ACIR producers and Solidity consumers. Its
v1 analyzer decodes the compiled circuit, counts the proof-enforced uses of
every public input, joins them to a model of the consumer, and applies four
generic rules: R-BIND (a public input that no proof-enforced constraint
uses), R-EFFECT (such an input feeds a consumer effect), R-ANCHOR (a root the
circuit proves against lacks a *must-be-in* check against consumer state) and
R-POLARITY (a replay key lacks a *must-not-be-in* check or its write on
success). Each warning carries a location, an explanation, evidence and a
suggested fix. A separate validator replays registered real-proof routes and
reports the highest evidence level reached. We ground the design in a
taxonomy of binding failures and in three case studies: a publicly disclosed
Payy rollup defect (historical) and two injected WarpToad bridge variants, a
producer-side domain-binding removal (M-DOM) and a consumer-side root-guard
removal (M-SRC). On five development targets, v1 warns at the expected
public word on all three known-positive targets and on neither of two
honest or repaired controls. All three positive targets reach end-to-end
validation with real proofs and committed local effects: freshly for the
two injected variants, and from preserved evidence for Payy. Pinned
circuit-only and contract-only tools ran on the same five targets in their
default configurations. None described a mismatch. Two named a defect
location without explaining it. All of these are development results on cases
known before the rules were written. On a 30-mutant benchmark,
[PENDING D1P-31]; baselines on the benchmark, [PENDING D1P-32]; on held-out
families, [PENDING D1P-33]; in the taxonomy corpus, [PENDING TAXONOMY-V1].

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
acts on, nor that the consumer checks the values that `R_v` silently trusts.
The SNARK SoK classifies such failures as integration-layer vulnerabilities
and reports no defenses developed specifically for that layer [1, §§6, 8].
Failures of this kind are invisible to an analysis of either side in
isolation unless someone first states the cross-boundary property. A circuit
analyzer sees a public input that nothing constrains, but cannot tell whether
any consumer relies on it. A contract analyzer sees a verifier call that
returns true, but cannot tell which arguments the circuit actually binds.

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
word that the consumer relies on. In M-SRC, the consumer fails to check a
word that the circuit relies on. In M-SRC no circuit-only analysis can find
a defect, because the circuit is unchanged. In M-DOM, judging the circuit
requires knowing that the consumer treats word 5 as the binding domain
identity. These are our arguments for analyzing the pair, and they are
claims about what information a tool needs. Whether existing tools miss these
cases is measured, not assumed. On the five case targets, no pinned baseline
in its default configuration described the mismatch (D1P-22; §VII-E). On the
benchmark the comparison is **[PENDING D1P-32]**.

### C. BindCheck

BindCheck v1 is a command-line tool with two commands (D1P-30 §1):

```text
bindcheck analyze <producer artifact> <consumer source>
bindcheck validate <warning>
```

`analyze` works in three steps.

1. **Producer facts.** It decodes the compiled Noir artifact (ACIR and ABI),
   flattens the ABI into scalar public inputs, and counts how often each
   public witness occurs in proof-enforced opcodes.
2. **Consumer facts.** It obtains a consumer model in one of two ways. If the
   consumer source matches a hash-pinned entry, it uses a previously checked
   relation extracted from the Solidity AST. Otherwise it uses a
   conservative source profile. From the model it infers which public inputs
   are roots, replay keys and effect fields, and whether each root and
   replay key has the required *admission polarity*: must-be-in for roots,
   must-not-be-in plus a write on success for replay keys.
3. **Rules.** Four application-neutral rules, R-BIND, R-EFFECT, R-ANCHOR and
   R-POLARITY, join the two sides and emit warnings. Each warning carries a
   location, an explanation, evidence and a suggested fix.

`validate` looks up a registered validation route for the warning's exact
target identity (artifact hash, consumer hash, rule). It runs or audits that
route's staged evidence and reports the highest level reached. Witness
construction comes from the route's registered fixture. The validator does
not yet synthesize a witness from an arbitrary warning (§V-H).

A warning is evidence level E1. A validated warning reaches E4, the
contract's *end-to-end validated mismatch* (§III-F). The absence of a
warning is not `VERIFIED_WITHIN_SCOPE`. It means only that no rule fired
within the supported scope.

### D. Contributions

The following are the paper's contributions. Each item states the evidence
that exists now and the evidence still pending.

1. **A taxonomy of proof-to-execution binding failures** (§IV). It has three
   independent dimensions: cause, consequence and attacker role. It is tied
   to the authorization/coverage semantics of the research contract, and the
   annotation protocol separates disclosure counts from tool support.
   *Exists:* codebook and protocol v0.2.0 with a frozen search plan.
   *Pending:* the corpus and its label statistics **[PENDING TAXONOMY-V1]**.
2. **Cross-layer analysis by generic rules** (§V). Proof-enforced uses of
   each public input in the compiled circuit are joined to the consumer's
   guards, effects and replay accounting. Four rules apply, each stated once
   without application identifiers. *Exists:* the v1 implementation. On five
   development targets it warns at the expected public word on all three
   positives and on neither control (D1P-30 §§1, 4). *Pending:* the 30-mutant
   benchmark **[PENDING D1P-31]** and held-out transfer
   **[PENDING D1P-33]**.
3. **Actionable diagnostics with real-proof validation** (§V-G, §V-H). Each
   warning is a versioned JSON record with location, rule, explanation,
   evidence and a suggested fix. A validator takes warnings to E4 through
   registered real-proof routes, counting every manual input. *Exists:*
   three positive mismatches reach E4: fresh real proofs for M-DOM and M-SRC,
   and an automatic audit of the preserved Payy chain (D1P-30 §5).
   *Pending:* automatic witness construction for warnings that have no
   registered route (not implemented), and validation on the benchmark
   **[PENDING D1P-31]**.
4. **Validated case studies** (§II, §VII). One historical case (Payy, with a
   locally reproduced end-to-end effect and a repair validated for one
   witness) and two injected cases (WarpToad M-DOM and M-SRC, each with a
   real-proof differential against the pinned build and exact-state honest
   controls). *Exists:* this ground truth, BindCheck's detection and
   validation on all three (D1P-30), and a pinned baseline comparison on the
   same targets (D1P-22).

Consistent with contract §1, we do not claim as new: integration failures as
a category, the permission/obligation/effect terminology, rich semantic
specifications, or modular summaries. The specific advance over prior work
is the cross-layer rule set and its validation. On current evidence it is
demonstrated only on development cases. Transfer depends on RQ4.

### E. Scope of the evidence

We use three evidence classes throughout and never merge them.

- **Historical:** a real, publicly disclosed defect, reproduced locally from
  pinned artifacts (Payy). It is development data. The defect and its
  end-to-end artifact were known before BindCheck's rules were written, so
  Payy cannot show unbiased discovery.
- **Injected:** a mutation that we introduced into a pinned application
  (WarpToad M-DOM and M-SRC) or into the 30-mutant development benchmark.
  An injected result shows that the tool detects the injected mechanism. It
  says nothing about a defect in the pinned application. All injected cases
  are development data.
- **Held-out:** families reserved before development screening and analyzed
  only after the rules were frozen (RQ4). Only held-out results can support
  transfer or generality claims (contract §9). No held-out result exists yet.

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
RQ2; B02 §6). The original hand-built differentials are therefore ground
truth, not tool results. D1P-30 later reran the same fixtures as BindCheck
validation routes and generated fresh proofs (§V-H). That E4 is credited to
the validator only on the condition stated there: the fixture's witness
construction is pre-existing and counted as a manual input.

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
counted and excluded from automatic-recovery claims. BindCheck v1 takes no
explicit `σ`. It infers root, replay-key and effect roles from consumer
origins, ABI names and committed-effect records (§V-D). This inference
stands in for analyst-supplied roles and is itself a limitation (§IX). The
checked consumer relations that v1 selects are prior extraction outputs, and
their use is counted as a manual input (§V-C).

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

The v1 rules (§V-F) target the causes that a word-level analysis of one
producer–consumer pair can observe. They do not cover the others, and the
taxonomy keeps those visible as tool limitations rather than dropping them.
Coverage below is by design. Measured coverage on the benchmark is RQ1
**[PENDING D1P-31]**.

| Cause | v1 rule coverage |
| --- | --- |
| `C_RELATION_GAP` | R-BIND when the needed public input has no proof-enforced occurrence; R-EFFECT when that input is also an effect word. A dependency that is present but wrong is not detected |
| `C_ACTIVATION_EXTENT` | Only when the extent leaves words with zero occurrences, as in the Payy N=8 builds. v1 has no activation-condition reasoning. A word constrained under some condition counts as used |
| `C_CONTEXT_IDENTITY` | R-BIND when the context word is unused (M-DOM); R-ANCHOR when a root lacks a must-be-in guard (M-SRC). A context word bound to the wrong value is not detected |
| `C_OCCURRENCE_ACCOUNTING` | R-POLARITY, for replay keys recognized by name or idiom. Missing accounting on another effect path is not detected (Payy burns) |
| `C_FIELD_MAPPING` | Partial: relation mode rejects a producer/consumer width mismatch with a named reason. Misorder at equal width is not detected |
| `C_REPRESENTATION`, `C_VERIFICATION_CONFIG`, `C_DISCHARGE_TRANSFORMATION` | Not covered; reported as unsupported in the tool funnel |

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

**Status.** The design and search plan are frozen. RQ5 results will come
from the taxonomy v1 corpus (`docs/taxonomy/v1-corpus.md`, Lane X), which is
not in the repository at `ba571ff`. When it lands, the corpus record must
state whether it completes the reservation and two-annotator procedure above
or uses a different method. This section will then follow that record. All
results are **[PENDING TAXONOMY-V1]**. Families reserved here feed the
held-out scan **[PENDING D1P-33]**.

**Claim limit.** The strongest permitted statement is that these mechanisms
recur across independent families in the sampled public disclosures. We
make no prevalence, incidence or audit-quality inference.

---

## V. Design

This section describes BindCheck v1 as implemented in
[`static_analyzer_v1.py`](../src/bindcheck_d1/static_analyzer_v1.py) and
[`validation_v1.py`](../src/bindcheck_d1/validation_v1.py) (D1P-30). Where
the implementation is narrower than the concept it serves, we say so.

### A. Overview

```
 Noir artifact (ABI + ACIR) ──► producer frontend ──► public inputs + proof-enforced occurrence counts
                                                                       │
 consumer source ──► relation index (SHA-256) ──hit──► checked relation (D1P-18 / D1P-21B) ──┐
                                             └─miss──► conservative source profile ──────────┤
                                                                       ▼
                                   role inference: roots, replay keys, effect words + admission polarity
                                                                       │
                                            rules R-BIND / R-EFFECT / R-ANCHOR / R-POLARITY
                                                                       │
                                                 warnings (E1; JSON and readable text)
                                                                       │
 validation index (artifact hash, consumer hash, rule) ──► registered route ──► staged evidence checks
                                                                       │
                              highest level E1–E4, or NO_VALIDATION_ROUTE / PREPARATION_FAILED
```

*Figure 1 (to be drawn).* Each target is analyzed alone. No result from a
reference version, revision diff or paired variant is an analyzer input
(D1P-30 §1). The relation index and the validation index are orchestration
data. The rule engine never sees them, and every use of either is counted
as a manual input.

### B. Producer frontend

**Version gate.** The frontend reads the artifact's `noir_version` and
selects the beta.14 bincode decoder (Payy) or the beta.22 MessagePack
decoder (WarpToad) by exact match. Any other version is rejected. Both
decoders are fail-closed: an unknown opcode, black box, Brillig form or
serialization form raises a named `Unsupported` reason (D1P-13 §3).

**Public inputs.** The ABI is flattened into scalar leaves in declaration
order. Arrays are indexed (`messages[3]`) and structs are dotted. Each public
leaf gets its public index and its witness index from the ABI bindings.
WarpToad's artifacts have 11 public leaves. The Payy artifacts analyzed in
D1P-30 have 13.

**Proof-enforced occurrence.** For each public witness, the frontend counts
its occurrences in the decoded opcodes of the main circuit and records up to
eight opcode locations. An occurrence is either a witness in a linear or
multiplication term of an `AssertZero` opcode, or a witness-valued input of
a black-box call (for example `RANGE`, `Poseidon2Permutation` or a recursive
verification). Brillig calls are not counted. They compute witnesses but
constrain nothing, so a Brillig input never discharges a binding. As
implemented, black-box *outputs* and memory-block operations are also not
counted, because the decoders represent those witnesses differently. A
public input used only through dynamic memory, or only as a black-box
output, therefore has occurrence count zero.

**What an occurrence means.** An occurrence shows syntactic use in a
proof-enforced constraint. It does not show injectivity, cryptographic
intent, full semantic dependence or policy correctness (D1P-30 §3). A word
that appears in a used hash is counted as used even if the construction is
weak. A word constrained only on one branch is counted as used on every
branch. A deliberately unconstrained metadata word would be warned about.

**Deeper producer facts (not rule inputs).** The project also has Poseidon2
construction provenance for all 86 permutation opcodes (D1P-15 §3), checked
extraction of 77 BN254 Poseidon regions (D1P-19 §3), and an independent
provenance run on M-DOM. That run shows that the silo hash absorbs private
witness 59 where the pinned circuit uses public word 5 (D1P-21A §4). These
extractors accept only frozen artifact identities, and v1 rules do not use
them. They explain the M-DOM warning after the fact. The warning itself is
derived from occurrence counts alone (D1P-30 §4.2).

### C. Consumer model

The CLI takes two positional arguments. It first hashes the consumer source
and looks it up in a hash-pinned
[consumer-relation index](../protocols/d1/d1p-30-consumer-relations.json).
A hit selects a checked relation. A miss selects the conservative source
profile.

**Checked relation (WarpToad).** The relation is the output of the
route-A solc-AST extractor: D1P-18 for the pinned consumer, and D1P-21B for
M-SRC. The extractor follows the actual function bodies and referenced
declarations and emits every terminal path family with its ordered guards,
terminal status, committed effects and storage writes (D1P-16, D1P-18). The
verifier is an explicit relation whose arguments carry their origins
(calldata parameter, storage read, environment read) and is never assumed
true. Library effects come from a shared, versioned OpenZeppelin 5.6.1 table
that declares `case_specific_entries=false` (D1P-18). On the pinned
`WarpToadCore.mint`, the relation has 22 path families (3 success, 19
revert). On M-SRC it has 21. Exactly the `isValidLocalRoot` revert family
and its positive guard disappear (D1P-21B §3). v1 requires the relation's
verifier-argument count to equal the producer's public-leaf count and
rejects the pair otherwise. The selected relation path is recorded as one
manual input.

**Conservative source profile (Payy).** Without a relation, v1 scans the
Solidity source for a small set of idioms and reports the limitation
`SOURCE_PROFILE_IS_NOT_FULL_SOLIDITY_SEMANTICS` in every result. It
recognizes:
- message-array public inputs (`messages[i]`), treated as effect-decoded
  when the source defines a `verifyMessages` function together with a
  `verifyMint` or `verifyBurn` function;
- an old-root membership check, matched by an equality between the root
  parameter and a `*Root*` identifier, or by a call `verifyRootHash(oldRoot)`;
- replay accounting, matched by `.spent == false` and `.spent = true`;
- the verifier call site, for locating warnings.

Each of these idioms occurs in Payy's `RollupV1.sol`, the only consumer the
profile has been run on. The rule engine names no application, but this
profile is fitted to the development consumer. It gives no evidence of
generality, and we treat it as development scaffolding rather than a
contribution (§IX).

### D. Role inference

v1 takes no explicit policy `σ`. It infers three roles from the consumer
model and the ABI. These inferences stand in for the analyst-supplied roles
of contract §6.2, and they are heuristics over names and idioms.

| Role | Checked-relation mode | Source-profile mode |
| --- | --- | --- |
| **Root (anchor)** | A verifier argument whose consumer origin contains `root` (WarpToad: `calldata._gigaRoot`, `calldata._localRoot`) | A public leaf whose ABI path contains `root` and one of `old`, `current` or `previous`. This excludes transition outputs such as `new_root` |
| **Replay key** | A verifier argument whose consumer origin contains `nullifier` | Present when the `.spent == false` idiom occurs |
| **Effect word** | A verifier argument whose origin symbol appears in a committed mint, burn or transfer on a success path (WarpToad: public indices 2, 6, 7, 9, 10) | Every `messages[i]` leaf, if the message-dispatch idiom is present (Payy: public indices 5–12) |

### E. Admission polarity

Roots and replay keys must be checked against consumer state in opposite
directions. We call this *admission polarity*. It is unrelated to the
positive and negative solver controls that earlier reports also call
"polarity" (D1P-14D).

- **Must-be-in (roots).** On every successful path, some guard checks that
  the root is present in consumer pre-state. In relation mode this is a
  guard that mentions the word's origin, reads pre-state storage (a
  `select(pre.…)` term) and is not negated. In source mode it is one of the
  matched old-root idioms.
- **Must-not-be-in plus write (replay keys).** On every successful path, a
  negated pre-state membership guard on the key (`== false` or
  `not(select(pre.…))`), *and* a committed storage write keyed by the same
  origin on success. This is a two-transaction obligation: the check stops a
  second use only because the first use wrote the key. v1 checks both
  halves syntactically in one transition and makes no claim about histories.

### F. Rules

*Table 1: BindCheck v1 rules (D1P-30 §3; `static_analyzer_v1.py`).*

| Rule | Producer fact | Consumer fact | Fires when | Reported location | Suggested fix (abridged from the tool) |
| --- | --- | --- | --- | --- | --- |
| **R-BIND** | Public leaf with occurrence count 0 | Every public leaf is taken to be a consumer-constructed verifier argument | Any public leaf is unused. Adjacent unused leaves of one array form one warning | `artifact:abi.<leaf>` or `<first>..<last>` | Constrain every exposed verifier argument in the producer, or remove it from the consumer-visible effect surface. Rebuild artifact, key and verifier together |
| **R-EFFECT** | Same as R-BIND | Effect words (§V-D) | Some unused leaf is an effect word. One warning lists all such leaves | First committed effect location, else the verifier call | Bind every effect-decoded public word in the producer. Derive consumer effects only from bound public inputs |
| **R-ANCHOR** | — | A root without must-be-in on every success path | Once per such root | Verifier call site | Require the root to be admitted by the appropriate on-chain history or current-state mapping before accepting the proof |
| **R-POLARITY** | — | A replay key without a must-not-be-in guard or without a write on success | Replay accounting is recognized and either half is missing | Verifier call site | Check that the replay key is absent before verification, and write the same key atomically on success |

**R-BIND** checks the producer half of the boundary: every word the consumer
passes to the verifier must constrain something. v1 does not consult the
consumer to decide whether a word is passed. In relation mode the width
check guarantees that every public leaf is a verifier argument. In source
mode this is assumed. **R-EFFECT** is the consumer-relevant subset of
R-BIND: it reports where an unbound word becomes an effect. On Payy, R-BIND
and R-EFFECT describe one mismatch, and we count it once (§VII-C).
**R-ANCHOR** checks the consumer half: a word the circuit proves against must
be one the consumer has admitted. **R-POLARITY** checks single-use
accounting for recognized replay keys.

**What the rules do not use.** No rule function contains a WarpToad, Payy,
mutation or contract identifier (D1P-30 §1). Role inference uses generic
name fragments (`root`, `nullifier`, `old`). The source profile uses the
idioms listed in §V-C. In relation mode, the verifier call line is found by a
pattern that matches WarpToad's `withdrawVerifier` call. That pattern only
sets the location string of R-ANCHOR and R-POLARITY warnings. The B02
obligations O1/O2, the admitted-state designs `S_DOM`/`S_SRC`, and any
comparison with the pinned or earlier revision are not inputs. The M-DOM
warning comes from M-DOM's artifact alone. The analyzer does not compare
M-DOM with pinned WarpToad (D1P-30 §4.2).

**What the rules cannot see.** A public input that is used but bound to the
wrong value (for example, hashed under the wrong domain). A word whose
binding depends on a witness-controlled extent but which occurs in some
constraint. A root that is checked against the wrong history. A misordered
argument vector of the correct width. An effect field that comes from
calldata outside the verifier arguments. Missing single-use accounting on an
effect path whose replay key the profile does not recognize. On Payy, the
burn path has no registration or single-use record (T17 §3). v1 does not
report this, because the mint path's `.spent` idiom satisfies the source
profile.

### G. Actionable diagnostics

`analyze` writes a versioned JSON result (`bindcheck.static-analysis.v1`) and
readable text. Each warning records:

- `id`, `rule`, `severity` (always `warning`) and `confidence` (always
  `high` in v1);
- `location`: the ABI leaf for R-BIND, the effect site for R-EFFECT, or the
  verifier call site for R-ANCHOR and R-POLARITY;
- `explanation`: a sentence naming the leaf, the consumer origin and the
  missing fact;
- `suggested_fix`: the repair text of Table 1;
- `evidence`: public indices, witness indices and occurrence counts, or the
  root's guard evidence and polarity, or the replay guard and write flags;
- `target_identity`: the artifact hash, consumer hash and rule. The
  validator keys on this identity.

The enclosing result also records the producer facts (decoder, opcode counts
by kind, every public leaf with its occurrence count and locations), the
consumer model kind and scope, inferred roots and replay keys with their
polarity evidence, manual inputs, limitations and runtime. For example, on
M-DOM:

```text
W001 R-BIND at m-dom-withdraw.json:abi.aztec_warptoad_address
  Consumer-constructed verifier argument(s) aztec_warptoad_address have no
  occurrence in the decoded proof-enforced ACIR. ...
  Fix: Constrain every exposed verifier argument in the producer, ...
```

v1 does not map producer locations back to Noir source spans, and it does
not cross-reference a producer-side warning with the consumer guard that
supplies the word. A developer reading the M-DOM warning learns *which* word
is free and that the consumer passes it. Learning *why* the domain binding
moved to a private witness requires the provenance facts of §V-B.

### H. Validation

`bindcheck validate <result>#<warning>` selects routes from a
[validation index](../protocols/d1/d1p-30-validation-index.json) whose
`match` equals the warning's target identity (artifact hash, consumer hash,
rule). More than one match is an error. No match returns status
`NO_VALIDATION_ROUTE` at E1.

A route has three parts.

- **Preparation (optional).** A command, working directory, environment and
  timeout that run the route's fixture in a clean namespace. A sentinel file
  makes the route audit existing evidence instead of generating another proof.
- **Failed-route record.** Earlier attempts, kept with their reasons. For
  example, the first fresh M-DOM run generated a proof and then failed with
  `ENOENT` because its output directory did not exist. A literal
  `nargo execute` route is marked not applicable where no complete
  `Prover.toml` exists.
- **Stages.** Each stage has an evidence level and a mode (`fresh`,
  `preserved`, or an alternative execution route). Each check verifies that a
  file exists, its SHA-256, or a JSON predicate.

The result is the highest level whose stage passed, together with the
route's classification, fresh-or-preserved mode, manual steps and manual
inputs. The three routes used in D1P-30 each have the same four stages:
concrete witness (E2), circuit execution (E2; NoirJS or the pinned Rust ACVM
harness), real proof (E3), and unchanged-consumer replay with state checks
(E4).

**What is and is not automatic.** The validator automates running a
registered route and auditing its evidence. Witness construction is the
route fixture's job. For the WarpToad routes, the fixtures are the
mechanism-derived foreign-note fixture (D1P-15) and the private-root
same-root fixture (D1P-19), both written by people before D1P-30. For Payy,
the route audits the preserved T15/T16/T18 chain, whose synthetic tail record
was authored historically. Associating a warning with its route is a counted
manual input (one step for each WarpToad route, two for Payy). BindCheck
does not yet turn an arbitrary warning into a witness. A warning without a
route stops at E1.

**Why concrete execution.** Validation executes the real compiled circuit,
produces real proofs, and replays them on an owned local chain. It does not
issue a whole-relation SMT query. Every whole-relation and full-producer
query in our development history timed out or ended without an answer
(D1P-07, D1P-10, D1P-14D, D1P-17; Appendix A). The fresh WarpToad routes
complete in 28.82 s (M-DOM, two proofs) and 98.99 s (M-SRC, one proof)
(D1P-30 §5). These times are operational observations, not benchmarks.

**Future route synthesis (not implemented).** The natural next step is one
generic witness template per rule. For R-BIND, vary only the unused words
and solve the consumer path condition over them alone. For R-ANCHOR, build a
private structure under the extracted construction and set the root to its
root. For R-POLARITY, resubmit an accepted occurrence. We describe these
templates only to state the gap. No result in this paper uses them.

### I. What a result means

A warning is E1 and is not a vulnerability claim. A validated warning is E4
relative to the route's admitted state and the effect it checks, and is
labeled with both. No rule result is ever `VERIFIED_WITHIN_SCOPE`. Silence
on a supported input is reported as "no warning in the supported static
scope", which is E0. It is not evidence of safety. An unsupported compiler
version, decoder form or consumer-width mismatch stops the analysis with a
named reason. The bounded formal target of contract §7 concerns the joint
transition model. This paper proves no preservation theorem.

---

## VI. Implementation

BindCheck v1 is written in Python. The proving and chain fixtures that the
validation routes run are written in TypeScript and Rust. The table lists
the components and the evidence that validates each one on the development
fragment.

| Component | Location | Validation evidence |
| --- | --- | --- |
| CLI (`analyze`, `validate`) | [`bin/bindcheck`](../bin/bindcheck) | Five-target runner, all expected rule sets (D1P-30 §6) |
| Static analyzer and rules | [`static_analyzer_v1.py`](../src/bindcheck_d1/static_analyzer_v1.py) | 7/7 focused tests; 3/3 positives warned, 0/2 controls warned (D1P-30 §§4, 6) |
| Validator | [`validation_v1.py`](../src/bindcheck_d1/validation_v1.py); [validation index](../protocols/d1/d1p-30-validation-index.json) | Four warning objects audited to E4: two fresh (WarpToad), two views of one preserved Payy chain (D1P-30 §5) |
| Consumer-relation index | [`d1p-30-consumer-relations.json`](../protocols/d1/d1p-30-consumer-relations.json) | Hash-pinned; selects D1P-18/D1P-21B relations |
| ACIR decoder, Noir beta.14 (Payy) | `src/bindcheck_d1/frontends/acir_binary_v1.py`, `acir_bindings_v1.py` | Typed recursion/frame bindings (D1-03) |
| ACIR decoder and semantic checker, Noir beta.22 | `frontends/acir_binary_beta22.py`, `acir_semantics_beta22.py` | Exact rebuild match; 24,967/24,967 supported constraints on the honest witness; two predeclared mutation controls (D1P-13) |
| Consumer extractor (route A) and shared library models | `prototypes/d1p16/extract_relation.py`, `library_effect_models.v1.json` | 22 families; 5/5 executions; three source-mutation and four edge-control classes (D1P-16, D1P-18); 18 preserved extraction tests rerun in D1P-30 |
| Variant-general relation serializer | `prototypes/d1p20/`, `prototypes/d1p21b/` | Pinned 22/19/3 and M-SRC 21/18/3; 8/8 polarity controls; state/environment binding (D1P-20, D1P-21B) |
| Poseidon2 provenance and BN254 regions (not rule inputs) | `warptoad_poseidon_provenance.py`, `warptoad_variant_provenance.py`, `warptoad_bn254_regions.py`, `warptoad_p6.py` | 86/86 opcodes attributed (D1P-15); 77 regions, 24,448 core equations (D1P-19); independent M-DOM run (D1P-21A) |
| Real-proof and chain fixtures used by routes | D1P-15 Hardhat fixture; D1P-19 fixture; T15/T16/T18 harnesses | One-shot proof ledgers; on-state effect checks |

**Toolchains (pinned).** Payy: Noir `1.0.0-beta.14+60ccd48e…`, bb 3.0.0,
solc 0.8.20, Forge 1.4.1. WarpToad: Noir `1.0.0-beta.22+c57152f9…`, bb.js
5.0.0 UltraHonk `keccakZK`, solc 0.8.29 (optimizer, 1 run, Cancun), Hardhat
3.3.0 EDR. All chains are fresh in-process instances with no fork.

**Tests and runs.** The focused v1 suite passes 7/7 tests, and 18 preserved
D1P-16/18/21B extraction tests also pass (D1P-30 §6). Once proof evidence
exists, the five-target runner completes all five analyses and four warning
audits in 4.661 s. Static analysis takes 1.476–1.565 s per WarpToad target
and 0.031–0.035 s per Payy target. These are native-Mac development
observations, not performance results (D1P-30 §1). The complete earlier D1
suite passes 231 tests and 312 subtests (Python 3.13.9; D1P-21A §5). The
artifact-specific tests need the ignored evidence workspaces.

**Generality limits of the current implementation.** v1 accepts exactly two
Noir versions. Checked relations exist for two consumer sources (pinned
WarpToad and M-SRC), and the source profile is fitted to `RollupV1.sol`
(§V-C). Any other consumer falls back to the source profile, which will
recognize few or none of its idioms. Validation needs a registered route for
each target identity. These limits govern D1P-31: consumer mutants have new
hashes and no checked relations, and the Payy mutants are full-size
1,000-message artifacts that v1 has not yet analyzed (§VII-B).

---

## VII. Evaluation

### A. Research questions

| Paper RQ | Question | Contract RQ (rev. 2) | Case studies | Mutation benchmark |
| --- | --- | --- | --- | --- |
| **RQ1 Detection** | Do the generic rules warn at the correct public word and consumer location, without case-specific input? | RQ1 (fidelity), RQ2 (discovery) | D1P-30 (done) | D1P-31 |
| **RQ2 Warning quality and validation** | Are warnings localized and actionable? How many reach E4, at what cost, and with how many manual inputs? | RQ3 (validation) | D1P-30 (done) | D1P-31 |
| **RQ3 Baselines** | What do circuit-only and contract-only tools report on the same targets, in default and same-policy arms? | RQ4 (comparative) | D1P-22 (done) | D1P-32 |
| **RQ4 Held-out** | With rules frozen, what does BindCheck report on reserved families, and do any reports validate? | RQ4 (transfer) | — | D1P-33 |
| **RQ5 Taxonomy** | Which causes, consequences and roles recur across independent families in sampled disclosures, and how reliably can people label them? | — (descriptive) | — | TAXONOMY-V1 |

Contract RQ5 (efficiency) is not a paper RQ. Its null results are in
Appendix A, as the contract requires. Contract revision 3 (D1P-31) may
renumber the contract RQs. This table will be re-checked against it.

### B. Subjects and protocol

**Development cases (five targets).**

- Payy earlier `c4d2c902…` (historical, faulty) and check-added `dcd5d96e…`
  (repaired for one witness). D1P-30 analyzed bounded **N=8** `agg_agg`
  builds derived from the pinned sources (T22 scratch instances, artifact
  hashes `f50f6bb8…` and `e7b5731c…`) against the unchanged consumer
  `RollupV1.sol` (`7062065c…`). The preserved E4 chain (T15/T16/T18) uses
  the original 1,000-message configuration. The validation route links the
  N=8 warning to that full-size chain, and the link is a counted manual
  input. v1 has not been run on the full-size Payy artifacts.
- WarpToad pinned `973e7d1e…`: an honest development fixture, not a proven
  negative.
- WarpToad M-DOM and M-SRC (injected), each paired with its own artifact,
  key, verifier and consumer (§II-C).

**Mutation benchmark (30 mutants).** The Lane X benchmark
([`benchmarks/binding-mutants/`](../benchmarks/binding-mutants/);
[BENCHMARK.md](../docs/x-experiment/BENCHMARK.md)) applies exact-match edits
to vendored pinned sources of the two development applications: WarpToad
(18 mutants: 9 circuit, 9 consumer) and Payy (12 mutants: 7 circuit, 5
consumer). All 30 compile under the pinned toolchains. Each mutant has a
ground-truth record giving the operator, the binding it breaks, and the
predicted effect (`manifest.json`, `mutants/<ID>.md`). Predicted effects are
**unexecuted**, except for the two mutants that reuse frozen evidence:
WT-C03 reuses M-DOM (D1P-15) and WT-S01 reuses M-SRC (D1P-19). Cheap
reachability was checked only for WarpToad circuit mutants, by running
`nargo execute` on the honest path. WT-C01, C02, C04, C05, C08 and C09 pass.
WT-C06 and C07 fail with `Cannot satisfy constraint`, as designed, because
those mutants break the honest path. WT-C03 was skipped by design. Payy
circuit mutants and all consumer mutants were checked by compilation and
diff audit only. Four candidate classes were excluded with reasons
(BENCHMARK.md §6): a private-recipient circuit that breaks the 11-word
interface, two policy-neutral assertion removals, Brillig mutants (no
Brillig on either binding path), and `agg_final` forwarder mutants
(deferred, since misorder is already covered at both ends).

The benchmark is development data. Both families are exposed and can never
be held out. Its operators were chosen with knowledge of the case
mechanisms, so it measures coverage of operator classes, not discovery.

**Benchmark scoring rules (to be frozen in the D1P-31 protocol before any
benchmark result is inspected).**

1. A mutant counts as detected only if a warning names the mutant's own
   broken binding (word, guard or effect). Any other warning on that target
   does not count.
2. The Payy baseline is the *earlier, faulty* revision. Every Payy mutant
   therefore inherits the message-tail defect. Warnings at the tail words
   are inherited and are not detections of a Payy mutant.
3. WT-C03 and WT-S01 overlap M-DOM and M-SRC. Totals are reported with and
   without them.
4. Consumer mutants have new source hashes and no checked relation. D1P-31
   must either extract a relation for each one (counted per mutant) or
   report source-profile results labeled as such. The Payy mutants are
   full-size artifacts that v1 has not yet analyzed.
5. Because predicted effects are unexecuted, a warning on a mutant is E1
   against predicted ground truth. Higher levels require a validation route.

**Policy.** v1 takes no explicit `σ` (§V-D). Its roles are inferred. Any
same-policy baseline receives the reviewed `σ` of
[baselines.md](baselines.md). For WarpToad, `σ` is DRAFT where the
documentation leaves beneficiary policy open (D1P-12R §8.1).

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

**Accounting.** Manual inputs are counted separately for analysis (relation
selection) and validation (route association, historical witness content).
Static runtime, proof time and peak memory are reported separately.

### C. RQ1 — Detection

*Table 2: Detection on the five development targets (D1P-30 §§1, 4, 5).*

| Case | Class | Pins (artifact / consumer) | Consumer model | Rule(s) fired | Public word(s) | At scoring locus? | Highest level | Static runtime | Manual inputs (analysis + validation) | Reported verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Payy earlier | Historical, faulty (N=8 build) | `f50f6bb8…` / `7062065c…` | Source profile | R-BIND, R-EFFECT | `messages[1]..messages[7]` (public 6–12); `messages[0]` occurs twice | Producer: yes. Consumer: R-EFFECT at the dispatch function (`RollupV1.sol:397`), not at `verifyBurn`. Missing burn registration not reported | E4, preserved (T15/T16/T18, full-size chain) | 0.035 s | 0 + 2 | `UNKNOWN` |
| Payy check-added | Historical, repaired (one witness; N=8 build) | `e7b5731c…` / `7062065c…` | Source profile | none | all eight message words used (`messages[0]` three times, others once) | n/a (control) | — | 0.031 s | 0 + 0 | `UNKNOWN` |
| WarpToad pinned | Honest fixture (not proven negative) | `7190813f…` / `323a1cf2…` | Checked relation (D1P-18) | none | all 11 words used; both roots must-be-in; nullifier must-not-be-in and written | n/a (control) | — | 1.534 s | 1 + 0 | `UNKNOWN` |
| WarpToad M-DOM | Injected, producer | `db1a0a17…` / `323a1cf2…` | Checked relation (D1P-18) | R-BIND | word 5 `aztec_warptoad_address` (occurrence 0) | Yes | E4, fresh (injected variant) | 1.565 s | 1 + 1 | `UNKNOWN` |
| WarpToad M-SRC | Injected, consumer | `7190813f…` / `64ec0efd…` | Checked relation (D1P-21B) | R-ANCHOR | word 4 `destination_local_root` (origin `calldata._localRoot`; no must-be-in guard) | Yes | E4, fresh (injected variant) | 1.476 s | 1 + 1 | `UNKNOWN` |

The reported verdict is the D1 verdict recorded by D1P-30. E4 on an injected
variant is evidence about that variant, not about pinned WarpToad.

**Answer to RQ1 (cases).** On the five development targets, v1 warned on all
three known-positive targets at the scoring words and on neither control
(0/2 controls with a warning). Each target was analyzed alone, with no
revision diff. The producer-side defects (Payy, M-DOM) are found by R-BIND,
and the consumer-side defect (M-SRC) by R-ANCHOR. No single-sided rule
covers all three. These results are in-sample. The rules were written after
all three mechanisms were known. Two controls do not support a precision
estimate (D1P-30 §1). The Payy rows come from N=8 builds. On Payy's consumer
side, v1 points to the message dispatch but does not report the missing burn
registration that makes the tail exploitable.

*Table 3: Detection on the mutation benchmark, by operator. The first four
data columns come from the Lane X build (BENCHMARK.md §3–4); the rest are
pending.*

| Operator | Mutants | Side | Compiles | Reachability check (Lane X) | Warning at mutant locus (rule) | Highest level | Missed | Unsupported | Unresolved |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| leave-public-unconstrained | WT-C01, WT-C02, PY-C02, PY-C06 | Circuit | 4/4 | WT honest path passes (2/2); PY compile + diff | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| replace-public-with-private | WT-C03 (M-DOM shape) | Circuit | 1/1 | Skipped; reuses D1P-15 E4 | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| remove-guard (circuit) | WT-C04, WT-C08, PY-C01, PY-C03 | Circuit | 4/4 | WT honest path passes (2/2); PY compile + diff | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| swap-checks | WT-C05; WT-S05 | Circuit; consumer | 2/2 | C05 honest path passes; S05 compile + diff | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| unbind-amount | WT-C06 | Circuit | 1/1 | Honest path fails (by design) | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| unbind-domain | WT-C07 | Circuit | 1/1 | Honest path fails (by design) | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| misorder-words | WT-C09, PY-C07; WT-S08 | Circuit; consumer | 3/3 | C09 honest path passes; others compile + diff | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| unbind-commitment | PY-C04 | Circuit | 1/1 | Compile + diff | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| remove-config-check | PY-C05 | Circuit | 1/1 | Compile + diff | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| remove-guard (consumer) | WT-S01 (M-SRC), WT-S02, PY-S01 | Consumer | 3/3 | Compile + diff; WT-S01 reuses D1P-19 E4 | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| drop-accounting | WT-S03 | Consumer | 1/1 | Compile + diff | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| drop-write | WT-S09 | Consumer | 1/1 | Compile + diff | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| drop-single-use | PY-S02 | Consumer | 1/1 | Compile + diff | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| remove-gate (verifier call) | WT-S04 | Consumer | 1/1 | Compile + diff | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| unbind-fee | WT-S06 | Consumer | 1/1 | Compile + diff | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| misdirect-beneficiary | WT-S07 | Consumer | 1/1 | Compile + diff | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| misbind-word | PY-S03 | Consumer | 1/1 | Compile + diff | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| activate-dead-path | PY-S04 | Consumer | 1/1 | Compile + diff | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| offset | PY-S05 | Consumer | 1/1 | Compile + diff | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| **Total** | 30 (16 circuit, 14 consumer) | — | 30/30 | 6 pass, 2 fail by design, 1 skipped, 21 compile + diff only | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |
| **Total excluding WT-C03, WT-S01** | 28 | — | 28/28 | — | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |

Unsupported mutants are reported as unsupported, never as misses. An
honest-breaking mutant (WT-C06, WT-C07) is reported, not dropped.

**Answer to RQ1 (benchmark).** [PENDING D1P-31]

### D. RQ2 — Warning quality and validation

*Table 4: Per-warning record for the development cases (D1P-30 §§4–5;
validation index).*

| Warning | Case | Rule | Location (as emitted) | Evidence | Suggested fix (repair side) | Adjudication | Validation outcome | Route mode, proofs, time | Manual steps (validation) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| W001 | Payy earlier | R-BIND | `agg_agg.json:abi.messages[1]..messages[7]` | public 6–12; witnesses' occurrence count 0 | Producer: constrain exposed arguments | Target | E4 | Preserved T15/T16/T18; no new proof | 2 |
| W002 | Payy earlier | R-EFFECT | `RollupV1.sol:397` (message dispatch) | same words; effect kind: message-dispatched mint/burn | Producer binding; consumer derives effects only from bound words | Target (same mismatch as W001) | E4 (same chain, not counted separately) | Preserved; no new proof | 2 |
| W001 | M-DOM | R-BIND | `m-dom-withdraw.json:abi.aztec_warptoad_address` | public 5; witness occurrence count 0 | Producer: constrain exposed arguments | Target | E4 | Fresh; 2 real proofs (honest, foreign note); 28.82 s; peak RSS 737 MB | 1 |
| W001 | M-SRC | R-ANCHOR | `WarpToadCore.sol:161` (verifier call) | public 4; polarity must-be-in; no matching guard | Consumer: admit the root before accepting the proof | Target | E4 | Fresh; 1 real proof; 98.99 s; peak RSS 490 MB | 1 |

The fresh M-DOM route generated a note siloed under a contract distinct from
the configured address. NoirJS executed the M-DOM artifact, and bb.js and
the generated Solidity verifier accepted the proof. The unchanged consumer
wrote the nullifier and minted `5e18` to the recipient, with no relayer
mint. The pinned producer rejected the same semantic witness. The fresh
M-SRC route admitted the giga root but not the private local root. The
pinned artifact and verifier accepted the proof, and M-SRC committed a
nullifier write and `3e18` recipient and supply deltas. The Payy route
checked the preserved sequence: T15 satisfies the earlier circuit and is
rejected by the check-added one, T16 carries the record through `agg_final`
under the committed key, and T18 records the `100 → 93` and `0 → 7` balance
changes and a reverting second submission (D1P-30 §5). A first M-DOM launch
failed with `ENOENT` after generating a proof. The failure is preserved in
the route record.

*Table 5: Warning-quality summary.*

| Scope | Warnings | Distinct mismatches | At scoring locus | Warnings on controls | Reached E4 (mismatches) | Fresh / preserved | `NO_VALIDATION_ROUTE` | Non-target warnings (false alarm / real out-of-scope / new candidate) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Development cases | 4 | 3 | 4/4 | 0 (0/2 controls) | 3/3 | 2 / 1 | 0 | 0 / 0 / 0 |
| Benchmark | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | n/a (no controls in benchmark) | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |

We report counts, not precision. The two controls are not proven
negatives, so a false-alarm rate over them would be ill-defined (contract
§9). A new candidate would go through the same validation and, if confirmed,
through responsible disclosure before it supports any claim.

*Table 6: Manual inputs and analyst effort on the development cases.*

| Case | Analysis manual inputs | Validation manual inputs | Explicit `σ` | Witness construction | Analyst time | Same-policy Foundry property (D1P-22) |
| --- | --- | --- | --- | --- | --- | --- |
| Payy earlier | 0 | 2 (route association; historically authored tail record) | None (roles inferred) | Preserved T15 harness | Not recorded in D1P-30 | No earlier-revision honest-only harness (R) |
| Payy check-added | 0 | 0 (no warning) | None | — | Not recorded | Existing honest property wrapper: 7/7 tests pass (control) |
| WarpToad pinned | 1 (checked relation) | 0 (no warning) | None | — | Not recorded | No harness (R) |
| M-DOM | 1 (checked relation) | 1 (route association) | None | D1P-15 fixture (pre-existing) | Not recorded | No harness (R) |
| M-SRC | 1 (checked relation) | 1 (route association) | None | D1P-19 fixture (pre-existing) | Not recorded | No harness (R) |

Historical reference point: the hand-written Payy mint property was about 90
lines of Solidity (87 non-comment) and functionally equivalent to the earlier
checker's manual specification (T14 §4). Analyst time was not instrumented
in D1P-30. D1P-31 should record it.

**Answer to RQ2 (cases).** Every warning on the development cases names the
public word and the side to repair. R-EFFECT and R-ANCHOR also name a
consumer source line. All three positive mismatches reached E4. Two reached
it with fresh real proofs and committed local effects on the injected
variants. Payy reached it through an automatic audit of the preserved
historical chain. Each validation needed one or two manual route inputs, and
each witness came from a fixture written before D1P-30. The diagnostics
are actionable in the narrow sense that the suggested fix names the missing
binding or guard. They do not explain the mechanism. For example, the M-DOM
warning does not mention the private witness that replaced word 5 (§V-G).

**Answer to RQ2 (benchmark).** [PENDING D1P-31]

### E. RQ3 — Comparison with circuit-only and contract-only baselines

Versions, arms, budgets and setup are preregistered in
[baselines.md](baselines.md). D1P-22 froze run limits and scoring in a plan
file before analyzing any target. It ran the pinned tools on the five case
targets and scored each cell as follows: **D**, the report describes the
proof-to-execution mismatch; **E1**, a warning names the defect locus or
variable but does not describe the mismatch; **M**, an applicable completed
run gave no such warning; **U**, unsupported (the tool cannot accept the
target or has no policy interface); **R**, unresolved (the run could not
complete, or a required harness or property was absent). On a control,
`M (control)` means no binding signal and `E1 (control)` means
nondiscriminating lint (D1P-22, "Scoring").

*Table 7: Baseline outcomes on the case targets (D1P-22). G = generic or
default arm; S = same-policy arm.*

| Baseline | Arm | Payy earlier (+) | Payy check-added (control) | WarpToad pinned (control) | M-DOM (+) | M-SRC (+) | Note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Pinned Noir checks | G | M | M (control) | M (control) | **E1** | M | beta.22 named M-DOM's unused public variable (`src/main.nr:20`); beta.14 emitted only an unrelated unused-import warning |
| Pinned Noir checks | S | U | U | U | U | U | No user-policy interface |
| CCC-Check | G / S | U | U | U | U | U | Pinned build timed out; consumes CirC IR, and no Noir/ACIR route exists |
| Picus | G / S | U | U | U | U | U | Installed; native inputs are `.circom`, iden3 `.r1cs`, gnark `.sr1cs`, not ACIR |
| Slither | G | **E1** | **E1 (control)** | M (control) | M | **E1** | `reentrancy-no-eth` names `verifyBurn`; naming lint names `_localRoot`, and the same style warning appears on the pinned control |
| Slither | S | U | U | U | U | U | No custom policy detector existed |
| Mythril | G / S | R | R (control) | R (control) | R | R | Three runs hit the 1,800 s cap; one startup race; one exit `-11`. No frozen assertion wrapper |
| Foundry | G | R | R (control) | R (control) | R | R | No G1–G5 harness exists for either application |
| Foundry | S | R | M (control) | R (control) | R | R | Existing honest Payy property wrapper: 7/7 pass on the repaired revision only |
| Echidna | G / S | R | R (control) | R (control) | R | R | No G1–G5 harness; the Payy wrapper failed on an unsupported cheatcode |
| SmartAxe | G | U | U | R (control) | R | R | Payy is not a bridge pair. The official artifact was blocked by a WAF challenge |
| SmartAxe | S | U | U | U | U | U | No user-property interface |
| Circomspect, CIVER | — | not run | not run | not run | not run | not run | Circom-only natively (READMEs); not in D1P-22 |
| Joint SMT (monolithic, goal-cone) | — | not run | not run | not run | not run | not run | Not in D1P-22; earlier attempts in Appendix A |
| **BindCheck v1** (archived D1P-30) | — | **D** | M (control) | M (control) | **D** | **D** | Context row, not rerun in D1P-22 |

**Answer to RQ3 (cases).** No baseline emitted a warning that described a
proof-to-execution mismatch on any case target. Two generic checks localized
a known positive without explaining it. Slither named Payy's `verifyBurn`.
The beta.22 Noir compiler named M-DOM's unused `aztec_warptoad_address`.
Slither's mention of M-SRC's `_localRoot` also appears on the pinned control,
so it does not discriminate. BindCheck is the only tool in the comparison
whose diagnostics state the cross-component reason on all three positives
(D1P-22).

We state the limits plainly. Most same-policy cells are U or R because no
policy wrapper, custom detector or G1–G5 harness existed. None was written
after seeing the outcomes, which keeps the comparison clean but leaves it
incomplete. This table therefore does not show that a same-policy
contract-only baseline would miss these cases. It shows that none was
instantiated, so capability-gate part (c) remains open. Mythril's cells are
unresolved, not misses. Circuit-only tools other than the Noir compiler
could not ingest ACIR. That is a frontend limitation, not an algorithmic
miss. The Noir compiler's E1 on M-DOM agrees with the Lane X probe on
synthetic stand-ins: the unused-variable lint is the only built-in signal,
and it states no mismatch ([Lane X report §2, X1](../docs/x-experiment/REPORT.md)).

*Table 8: Baseline outcomes on the mutation benchmark (counts of D / E1 / M
/ U / R).*

| Baseline | Arm | WarpToad circuit (9) | WarpToad consumer (9) | Payy circuit (7) | Payy consumer (5) | Total (30) | Excluding WT-C03, WT-S01 (28) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Pinned Noir checks | G | [PENDING D1P-32] | n/a | [PENDING D1P-32] | n/a | [PENDING D1P-32] | [PENDING D1P-32] |
| Slither | G | n/a | [PENDING D1P-32] | n/a | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] |
| Mythril | G | n/a | [PENDING D1P-32] | n/a | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] |
| Foundry / Echidna | G / S | n/a | [PENDING D1P-32] | n/a | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] |
| Other preregistered tools | G / S | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] | [PENDING D1P-32] |
| **BindCheck v1** | — | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] | [PENDING D1P-31] |

One observation constrains how D1P-32 must score the Noir compiler. The
build logs (`manifest.json`, `compile_log_tail`) already contain
unused-variable warnings on WT-C01, C02, C03, C04, C07 and C08, and on
PY-C02, C04, C05 and C06. Some name the freed public input (for example
`nullifier`, `max_fee`, `aztec_warptoad_address`, `new_root`). PY-C05's
warning names a local variable, not an input. Under the D1P-22 scale, such
warnings are E1 unless they describe the mismatch.

**Answer to RQ3 (benchmark).** [PENDING D1P-32]

### F. RQ4 — Held-out scan

**Protocol.** The rules, role inference, decoders, consumer extractors and
validator are hashed and frozen before the first held-out artifact is
opened. v1's source profile is fitted to a development consumer (§V-C).
Freezing it as is will likely make many held-out consumers fall back to an
empty profile, and the funnel will report that. Held-out families come from
the private reservation (§IV-D) or from an equivalent frozen inventory. Every
attempted build and every exclusion is reported. No rule changes after the
scan begins. A post-hoc correction is reported as such, and the affected
family stops counting as held out (contract §§9, 11). Any confirmed finding
is disclosed to its maintainers before it supports a claim, and is
anonymized in the submission.

*Table 9: Held-out funnel and results.*

| Family (anonymized) | Reserved before development? | Prior exposure (log) | Producer / consumer stack | Artifacts available | Supported | Consumer model (relation / profile) | Warnings (R-BIND / R-EFFECT / R-ANCHOR / R-POLARITY) | Adjudication | Highest level | Rule changes (must be 0) | Disclosure status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] |

*Table 10: Held-out funnel totals.*

| Stage | Families | Applications | Notes |
| --- | --- | --- | --- |
| Reserved / frozen inventory | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] |
| Artifacts available | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] |
| Supported (Noir beta.14/beta.22 + Solidity) | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] |
| Analyzed to completion | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] |
| With ≥1 warning | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] |
| Validated (E4) | [PENDING D1P-33] | [PENDING D1P-33] | [PENDING D1P-33] |

Stages are monotone. An unsupported family explains attrition and is never
counted as a miss or as safe.

**Answer to RQ4.** [PENDING D1P-33]

### G. RQ5 — Taxonomy

The corpus for RQ5 is the taxonomy v1 corpus
(`docs/taxonomy/v1-corpus.md`, Lane X). That file is not in the repository at
`ba571ff`. The tables below follow protocol v0.2.0. If the corpus uses a
different procedure, the tables will follow the corpus record and the
difference will be stated.

*Table 11: Disclosure funnel (human annotation only).*

| Stage | Count | Unit |
| --- | --- | --- |
| Raw retrieval hits | [PENDING TAXONOMY-V1] | hits |
| Unique source documents | [PENDING TAXONOMY-V1] | documents |
| Candidate findings (before deduplication) | [PENDING TAXONOMY-V1] | findings |
| Canonical findings | [PENDING TAXONOMY-V1] | findings |
| Included / excluded / unresolved | [PENDING TAXONOMY-V1] | findings |
| Families represented (included) | [PENDING TAXONOMY-V1] | families |
| Unresolved duplicate matches | [PENDING TAXONOMY-V1] | pairs |

*Table 12: Label frequencies over included canonical findings, by family.*

| Label | Present (findings) | Present (families) | Uncertain | Absent | Example family (anonymized) |
| --- | --- | --- | --- | --- | --- |
| `C_RELATION_GAP` … `C_OTHER_BINDING` | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] |
| `K_AUTHORIZATION` … `K_OTHER_EFFECT` | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] |
| `A_PUBLIC_CALLER` … `A_OTHER_ROLE` | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] |

(One row per label in the final table.)

*Table 13: Inter-annotator agreement (two human annotators).*

| Field / label | Comparable n | Positives / negatives | Raw agreement | Coefficient (κ or α) | 95% interval | Missing / null |
| --- | --- | --- | --- | --- | --- | --- |
| Relevance (include / exclude / unresolved) | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] |
| Each cause, consequence and role label | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] |

*Table 14: Tool funnel for included findings (separate denominator).*

| Stage | Findings | Families | Main attrition reasons |
| --- | --- | --- | --- |
| Artifacts available | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] |
| Supported by BindCheck v1 | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] |
| Cause covered by a v1 rule (§IV-C) | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] | [PENDING TAXONOMY-V1] |

**Answer to RQ5.** [PENDING TAXONOMY-V1]

### H. Threats to validity

**Development bias.** The rules were designed after the three case studies
were known. Payy's defect, advisory and end-to-end artifact predate the
rules. WarpToad was screened and inspected in D1-02, D1P-11 and later tasks.
RQ1 and RQ2 therefore show capability *on these cases* only (contract §9).
Transfer rests on RQ4 alone.

**Fitted heuristics.** Role inference relies on name fragments, and the
source profile matches identifiers that occur in Payy's consumer (§V-C,
§V-D). The Payy result shows that the profile works on the consumer it was
written for, and nothing more.

**Artifact scale.** The Payy static rows use N=8 builds, while the Payy E4
chain uses the full-size configuration. The validation route links them by
a counted manual association, not by re-analysis.

**Validation provenance.** Every E4 in this paper reuses a witness
construction that people designed before D1P-30. The validator automates
execution and auditing, not discovery of the witness.

**Injected cases and benchmark.** M-DOM and M-SRC are injected. M-DOM is
grounded in an unused in-tree package and a developer warning, M-SRC in
documented reliance. Neither indicates a defect in pinned WarpToad. The
benchmark was built in parallel with D1P-30 by an AI-assisted lane. Its
operators share mechanisms with the cases. Its predicted effects are mostly
unexecuted. Its Payy mutants sit on the faulty revision.

**Admitted state.** The M-DOM differential uses privileged synthetic root
admission (`S_DOM`). Neither variant demonstrates cross-chain reachability.

**Baselines.** The same-policy arms were not instantiated (§VII-E). The
comparison is between BindCheck and default tool configurations.

**Negatives.** No fixture is a proven negative control. We report adjudicated
counts, not false-positive rates.

**AI involvement.** AI agents implemented code, ran D1P-22 and D1P-30,
built the benchmark, wrote the B02 obligations and drafted this text
(§X-B). AI output is not independent annotation (contract §10). Taxonomy
labels come only from human annotators.

---

## VIII. Related Work

We group prior work by which side of the boundary it analyzes. Each
difference stated below is derived from the cited source where marked, and
is otherwise **[TODO-VERIFY]**. Empirical overlap with BindCheck on our case
targets is measured in RQ3 (D1P-22), not asserted here.

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

- **Noir compiler checks.** At the pinned beta.22 compiler, the only signal
  on M-DOM was a generic unused-variable warning on
  `aztec_warptoad_address`. The compiler was silent on pinned WarpToad and
  M-SRC. At beta.14 it emitted only an unrelated unused-import warning on
  both Payy revisions (D1P-22). Lane X's synthetic probe found the same
  pattern. The under-constrained Brillig check fires on its own control,
  but public inputs are outside its scope ([Lane X report §2, X1](../docs/x-experiment/REPORT.md)). *Measured, not cited.*
- **Circomspect** [14] is a static analyzer and linter for Circom. It does
  not accept Noir. *Verified against the repository description; not run.*
- **Picus** [9] checks the uniqueness property of ZKP circuits to find
  under-constrained signals. Its documented inputs are Circom source, iden3
  R1CS and gnark `.sr1cs`. Its README illustrates a counterexample as one
  input assignment with two different output assignments. A public input
  that no constraint reads is an input, so it falls outside that property
  as the README states it. Whether the paper's formulation covers it is
  **[TODO-VERIFY: full text]**. D1P-22 installed Picus and parsed its bundled
  R1CS example. The case targets were unsupported. *Bibliographic data
  verified via the DOI registry; property and inputs verified against the
  README.*
- **CIVER** [3] verifies Circom circuits for weak safety (determinism), tag
  specifications, and pre/postconditions over circuit signals. Its README
  lists R1CS, PLONK and ACIR inputs as planned, not supported. Its
  specifications describe circuit signals, not contract effects. *README
  verified; full text **[TODO-VERIFY: not retrieved]**.*
- **Coda** [4] re-implements circuits in a refinement-typed language and
  discharges obligations in Coq. In the text we read, it does not model a
  consuming contract: the phrase "smart contract" does not occur. *Verified
  against the author-hosted full text.*
- **CCC-Check** [5] detects computation–constraint inconsistencies by
  abstract-interpretation value inference. Its artifact README describes
  analysis "via the CirC intermediate representation" and gives Circom as
  its end-to-end example. D1P-22 found no admitted Noir/ACIR-to-CirC route,
  and the pinned build timed out. Payy's tail is a case where the
  out-of-circuit witness builder writes trailing zeros that the circuit does
  not enforce. Whether CCC-Check's model would capture it given an ACIR
  frontend remains **[TODO-VERIFY: full text]**. *Abstract and README
  verified. The ePrint PDF refused automated retrieval (HTTP 403) on
  28 October 2026.*

The common limitation, as we understand these designs, is informational. A
circuit-only tool cannot know that a consumer decodes effects from a word
(Payy), supplies a word as context (M-DOM), or fails to check a word
(M-SRC). In M-SRC the circuit is unchanged, so no circuit-only report can be
specific to the defect. D1P-22 is consistent with this on the case targets.

### C. Contract-only analysis

These tools treat the verifier as an opaque call.

- **Slither** [10] is a static analysis framework that runs detectors over
  Solidity.
- **Mythril** [11] symbolically executes EVM bytecode.
- **Echidna** [12] is a property-based fuzzer for smart contracts.
  **Foundry** [13] provides fuzz and invariant testing.

None of them models the circuit relation, so none can tell which verifier
arguments are bound. On the case targets, Slither's only relevant output
was lint at a defect location, and Mythril did not complete (D1P-22). In a
same-policy arm, a fuzzer could check `σ`, but it needs a valid proof for
every input it explores. Seeded only with honest proofs (baselines §3.1), it
cannot produce a proof of a forged statement. In our own Payy work, the
consumer-side test exercised the forged effect only because we supplied a
hand-built forged proof (T18). The same-policy arms were not instantiated in
D1P-22, so this reasoning remains untested.

**SmartAxe** [6] analyzes cross-chain bridge bytecode. Its semantic-integrity
check reports withdrawal state with *no* data-flow dependency on deposit
state (§4.3). In Payy and M-DOM, the effect fields *do* flow from verified
public inputs. The defect lies in what the circuit constrains, which
SmartAxe does not analyze. *Verified against arXiv 2406.15999v1 (§§2.3,
4.3).* D1P-22 could not obtain the official artifact.

### D. Joint analysis

Our earlier exploratory work encoded producer, decoder, consumer and policy
as one SMT query. Those queries did not resolve at the sizes we tried
(Appendix A). BindCheck therefore uses joint *facts* and generic rules, with
validation by concrete execution and real proofs, rather than a monolithic
joint query. A Lane X prototype derived admission obligations from the
D1P-18 relation by IR-shape rules and solved them with the producer
dropped. It recovered the M-SRC root-admission gap as an abstract candidate,
below E2 ([Lane X report §2, X2](../docs/x-experiment/REPORT.md)). The monolithic and goal-cone joint queries were not scored
baselines in D1P-22.

---

## IX. Limitations

**Fragment.** v1 accepts Noir `1.0.0-beta.14` and `1.0.0-beta.22` artifacts
only. Consumer facts come from a checked relation for two WarpToad consumer
sources, or from a source profile fitted to Payy's `RollupV1.sol`. The
route-A extractor supports one entry point's reachable constructs with
OpenZeppelin 5.6.1 effects, standard atomic ERC-20 behavior, and no proxies,
delegate calls, inline assembly or reentrancy. Unsupported inputs stop with
a named reason. That keeps results honest but bounds applicability. RQ4's
funnel measures how much.

**Occurrence is not binding.** R-BIND treats one proof-enforced occurrence as
sufficient. It misses a public input that is used but bound to the wrong
value, used only on an inactive branch, or absorbed by a weak construction.
It can warn on deliberately unconstrained metadata. As implemented, it also
misses uses through dynamic memory and through black-box outputs (§V-B), so
a word used only that way would draw a spurious warning.

**Name-based roles.** Roots, replay keys and effect words are inferred from
name fragments and idioms (§V-D). A root named otherwise is not checked by
R-ANCHOR. A transition-output root named `old_*` would be wrongly required to
be must-be-in. Replay accounting on one path can satisfy R-POLARITY while
another effect path has none, as on Payy's burn path.

**Hash semantics.** Poseidon2 is modeled at most as a functional
uninterpreted tuple function (equal inputs give equal outputs), with no
injectivity or collision resistance (D1P-19 §2.2). v1 does not reason about
hash semantics at all. Validation uses real hashes. Any conditional
no-collision argument (B02 §3) is outside this paper's results.

**Conditional binding.** v1 has no activation-condition reasoning. Payy's
tail is caught in the N=8 builds because the tail words have no occurrences
there. A variant that constrains tail words under a witness-controlled
predicate would be counted as used. Earlier ACIR and SMT work on this
pattern produced an analyzer false positive from unsound probe
specialization (later repaired) and general queries that did not finish
(T22, T22-v3, T22-v4).

**Scale.** The Payy static rows use N=8 builds. Payy's real proofs and
consumer replays use the original 1,000-message configuration. These
evidence grades are kept separate.

**Validation is route-bound.** E4 requires a registered route whose fixture
constructs the witness. Every route used here reuses a construction designed
before D1P-30. Validation covers one consumer call from a fixed admitted
pre-state (or, for Payy, a replay rejection in a second call).
Multi-transaction histories, front-running and observation of honest proofs
are out of scope (B02 §3.1).

**No safety claims.** BindCheck never returns `VERIFIED_WITHIN_SCOPE` from
rule silence. Absence of warnings is E0 within the supported scope.

**Not novel by itself.** Integration-layer failures [1], rich circuit
specifications [3, 4] and computation–constraint consistency [5] are prior
work. Unused-variable lint already flags some unused public inputs
(D1P-22). Our claim is limited to joining both sides into rules that state
the cross-component reason, and validating them, to the extent that RQ1–RQ4
support it.

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
  **[PENDING D1P-33]**.
- **New tool.** BindCheck's validation routes produce working forged proofs
  against local deployments. Misuse risk: an attacker could use validated
  warnings against live systems. Mitigations: validation runs only on
  owned-local chains with fresh deployments. v1 replays only registered
  routes and does not synthesize attack witnesses. The planned artifact omits automation for
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
pair, not of either component. BindCheck v1 makes part of this agreement
checkable. It counts proof-enforced uses of each public input, infers roots,
replay keys and effect words on the consumer side with their admission
polarity, and applies four generic rules. A validator replays registered
real-proof routes. On five development targets, v1 warned on the
producer-side defects in historical Payy and injected M-DOM, and on the
consumer-side defect in injected M-SRC, at the expected public words. It
emitted no warning on the two controls. All three positive mismatches
reached end-to-end validation. On the same targets, pinned circuit-only and
contract-only tools in default configurations described no mismatch. These
are development results. On the mutation benchmark, [PENDING D1P-31] and
[PENDING D1P-32]. On held-out families, [PENDING D1P-33]. In public
disclosures, [PENDING TAXONOMY-V1].

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
| v1 rules and warnings on five development targets | D1P-30 §§3–4; `results/raw/D1P-30/analyses/` (ignored) | Tool output (E1), development |
| Fresh E4 on M-DOM and M-SRC through registered routes | D1P-30 §§5.1–5.2; validation index | Locally reproduced (injected), tool-driven route |
| Preserved E4 audit for Payy | D1P-30 §5.3 | Automatic audit of preserved evidence |
| Payy static rows use N=8 builds | D1P-30 §2 hashes; T22 §§2–3; analysis paths | Checked against the D1P-30 analysis outputs |
| Baselines on the case targets | D1P-22 record; `results/raw/D1P-22/` (ignored) | Tool output, scored under the preregistered plan |
| 30 mutants compile; reachability checks | BENCHMARK.md §§3–4; `manifest.json` | Build observation (development) |
| Taxonomy design and search plan frozen | protocol v0.2.0; search plan | Design only |
| Benchmark detection, benchmark baselines, held-out, taxonomy corpus | — | [PENDING D1P-31/32/33, TAXONOMY-V1] |

---

## Open items for authors

1. **Payy artifact scale.** D1P-30's Payy static rows analyze the N=8
   `agg_agg` builds from T22 (`build/T22/scratch/…`), while the E4 chain they
   are linked to uses the full-size 1,000-message artifacts. The D1P-30 report
   gives the hashes but not this fact. Either run v1 on the full-size
   artifacts (D1P-31 needs that for the Payy mutants anyway) or keep the
   caveat as written in §VII-B.
2. **Fitted identifiers.** D1P-30 §1 says the rule engine contains no Payy or
   WarpToad identifier. That holds for the rule functions. The source
   profile's idioms (`verifyMessages`, `verifyMint`/`verifyBurn`,
   `verifyRootHash(oldRoot)`, `.spent`) match `RollupV1.sol`, and the
   relation-mode location pattern matches WarpToad's `withdrawVerifier`.
   The paper says this in §V-C/F and §IX. Decide whether to generalize the
   profile before D1P-33 freezes the rules.
3. **Occurrence counting.** D1P-30 §3 says Poseidon and recursive black boxes
   contribute "checked input/output occurrences". The code counts
   witness-valued black-box *inputs* only. Outputs, memory-block operations
   and Brillig calls are not counted. The paper describes the code (§V-B).
   Either fix the code or append a correction note. Do not edit the
   immutable report.
4. **Taxonomy v1 corpus.** `docs/taxonomy/v1-corpus.md` does not exist at
   `ba571ff`. §IV-D and RQ5 assume the protocol v0.2.0 procedure until the
   corpus states its own.
5. **D1P-31 protocol.** Freeze the scoring rules of §VII-B, which cover
   inherited Payy tail warnings, the WT-C03/WT-S01 overlap, relations for
   consumer mutants, and analyst-time recording, before inspecting any
   benchmark result.
6. **Contract revision 3.** When D1P-31 lands, re-check §I-D and the RQ
   mapping against it.
7. **Citations.** CIVER and CCC-Check full texts remain unread. The CCC-Check
   ePrint PDF refused automated retrieval. Supply copies and resolve each
   **[TODO-VERIFY]**. Mythril and Foundry are cited as software, because we
   found no canonical paper for either.
8. Draw Figure 1. Replace repository links with an anonymized artifact.
9. Have a human author inspect every claim and citation (contract §10).

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
doi:10.1109/SP54263.2024.00133. Tool: github.com/costa-group/circom_civer
(README read 28 October 2026; full text not retrieved).

[4] J. Liu, I. Kretz, H. Liu, B. Tan, J. Wang, Y. Sun, L. Pearson,
A. Miltner, I. Dillig, Y. Feng. "Certifying Zero-Knowledge Circuits with
Refinement Types." IEEE S&P 2024. doi:10.1109/SP54263.2024.00078.

[5] A. Kolozyan, B. Vandenbogaerde, J. Swalens, L. Hoste, S. Chaliasos,
C. De Roover. "Language-Agnostic Detection of Computation-Constraint
Inconsistencies in ZKP Programs via Value Inference." IEEE S&P 2026. Read:
abstract (IACR ePrint 2025/2120) and artifact README
(github.com/ArmanKolozyan/CCC-Check, which gives the S&P 2026 citation).

[6] Z. Liao, Y. Nan, H. Liang, S. Hao, J. Zhai, J. Wu, Z. Zheng. "SmartAxe:
Detecting Cross-Chain Vulnerabilities in Bridge Smart Contracts via
Fine-Grained Static Analysis." Proc. ACM Softw. Eng. 1(FSE), 2024.
doi:10.1145/3643738. Read: arXiv:2406.15999v1.

[7] (Removed: the internal D1 reference proposal is not a citable source.)

[8] IEEE S&P 2027 Call for Papers. sp2027.ieee-security.org/cfpapers.html,
retrieved 26 October 2026.

[9] S. Pailoor, Y. Chen, F. Wang, C. Rodríguez, J. Van Geffen, J. Morton,
M. Chu, B. Gu, Y. Feng, I. Dillig. "Automated Detection of Under-Constrained
Circuits in Zero-Knowledge Proofs." Proc. ACM Program. Lang. 7(PLDI),
pp. 1510–1532, 2023. doi:10.1145/3591282. Tool: github.com/Veridise/Picus.
(Metadata verified via doi.org, 28 October 2026; full text not read.)

[10] J. Feist, G. Grieco, A. Groce. "Slither: A Static Analysis Framework
for Smart Contracts." In Proc. 2nd IEEE/ACM Int. Workshop on Emerging Trends
in Software Engineering for Blockchain (WETSEB), pp. 8–15, 2019.
doi:10.1109/WETSEB.2019.00008. (Metadata verified via doi.org, 28 October
2026.)

[11] ConsenSys Diligence. Mythril, release v0.24.8 (27 March 2024).
github.com/ConsenSysDiligence/mythril (formerly Consensys/mythril). Software
citation. (Release verified via the GitHub API, 28 October 2026.)

[12] G. Grieco, W. Song, A. Cygan, J. Feist, A. Groce. "Echidna: Effective,
Usable, and Fast Fuzzing for Smart Contracts." In Proc. 29th ACM SIGSOFT
Int. Symp. on Software Testing and Analysis (ISSTA), pp. 557–560, 2020.
doi:10.1145/3395363.3404366. (Metadata verified via doi.org, 28 October
2026.)

[13] Foundry contributors. Foundry, release v1.8.6 (21 October 2026).
github.com/foundry-rs/foundry. Software citation. (Release verified via the
GitHub API, 28 October 2026.)

[14] Trail of Bits. Circomspect: a static analyzer and linter for the Circom
zero-knowledge DSL. github.com/trailofbits/circomspect. Software citation.
(Repository description verified via the GitHub API, 28 October 2026;
version not pinned, tool not run.)

