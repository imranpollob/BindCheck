# BindCheck: Finding Proof-to-Execution Binding Failures at the Circuit–Consumer Boundary

*(Working title; frozen at abstract registration.)*

**Draft status:** D1P-P05 revision, 29 October 2026, on repository base
`d981c64` (`main`). The base adds three things to everything in D1P-P04:
the D1P-33 held-out scan, the automatic-validation run on v1.1 warnings,
and TC02. Target format is IEEE S&P (13 pages of text plus up to 5 pages of
references and appendices). This revision:
- reports the held-out scan ([D1P-33](../reports/D1P-33.md));
- replaces the v1 validation results with the v1.1 run
  ([AUTO-VALIDATE](../docs/x-experiment/AUTO-VALIDATE.md);
  [TC02](../reports/TC02.md));
- records two threats: the unreachable R-ANCHOR rule and the placeholder
  behind the Payy control warning.

No experiment was run for this draft. Cells that depend on work not yet
done are marked **[PENDING D1P-35]** (version-only BindCheck v1.2) or
**[PENDING D1P-36]** (rescan of the reserved projects plus four unseen,
non-reserved projects). Claims about cited work that could not be checked
against a primary source stay **[TODO-VERIFY]**. Earlier drafts
(D1P-D01/D03, D1P-P01–P04) are in Git history.

**Controlling sources, in order.** [Research contract](../docs/research-contract.md)
revision 3 (28 October 2026; revision 2 archived as
[`research-contract-2026-10-27.md`](../docs/history/research-contract-2026-10-27.md),
and earlier experiments keep the revision under which they were run);
[README](../README.md); the immutable reports
[T15](../reports/T15.md)–[T22](../reports/T22.md),
[D1P-12R](../reports/D1P-12R.md), [D1P-13](../reports/D1P-13.md),
[D1P-14A](../reports/D1P-14A.md)–[D1P-14D](../reports/D1P-14D.md),
[D1P-15](../reports/D1P-15.md),
[D1P-17](../reports/D1P-17-consumer-backends.md),
[D1P-19](../reports/D1P-19.md), [D1P-21A](../reports/D1P-21A.md),
[D1P-30](../reports/D1P-30.md), [D1P-31](../reports/D1P-31.md),
[D1P-34](../reports/D1P-34.md), [D1P-33](../reports/D1P-33.md),
[TC02](../reports/TC02.md); the baseline records
[D1P-22](../docs/baselines/d1p-22-results.md) and
[D1P-32](../docs/baselines/d1p-32-benchmark.md); the extraction records
[D1P-16](../docs/extraction/d1p-16-feasibility.md),
[D1P-18](../docs/extraction/d1p-18-hardening.md),
[D1P-20](../docs/extraction/d1p-20-extracted-solver-model.md),
[D1P-21B](../docs/extraction/d1p-21b-variant-extraction.md); the
[mutation benchmark](../docs/x-experiment/BENCHMARK.md)
([package](../benchmarks/binding-mutants/)) and
[automatic-validation record](../docs/x-experiment/AUTO-VALIDATE.md); the
[B02 obligations](../docs/d1-paper/d1p-b02-discriminating.md); the
[taxonomy protocol v0.2.0](../docs/taxonomy/protocol.md), the
[v1 corpus](../docs/taxonomy/v1-corpus.md) and the
[reservation commitment](../docs/taxonomy/reservation-commitment-2026-10-28.json);
and the [baseline preregistration](baselines.md). If this draft disagrees with
any of them, the source wins.

**Research verdict at drafting time:** `UNKNOWN`. The capability gate
(contract §11) remains open. The held-out scan produced no supported
analysis (D1P-33), so there is no transfer result. No Payy warning has
reached E4. The same-policy baseline exists only for WarpToad, as a
handwritten harness with a stub verifier (D1P-32).

### Task map

| Tag | Scope | Status at `bda5265` | Paper locations |
| --- | --- | --- | --- |
| **D1P-30** | BindCheck v1 analyzer and validator; five development case runs; real-proof routes for the case mismatches | Done; v1 superseded as tool of record | §II-C, RQ2 case validation |
| **D1P-31** | v1 on the 30-mutant benchmark; contract revision 3; reservation commitment | Done; v1 numbers kept as history only | §VII-C (one line), §IV-D |
| **D1P-34** | BindCheck v1.1: application-neutral consumer lowering, corrected use accounting, full-size Payy; reruns the five targets and the 30 mutants | Done | §V, §VI, RQ1, RQ2 |
| **D1P-22** | Pinned baselines on the five case targets | Done | RQ3 case table |
| **D1P-32** | Baselines on the 30 mutants, including a Foundry same-policy harness for WarpToad and a sequential Mythril retry | Done | RQ3 benchmark table |
| **AUTO-VALIDATE** (Lane X) | Per-application validation harnesses run on all 53 v1.1 benchmark warnings (earlier on 20 v1 warnings) | Done | §V-H, RQ2 |
| **TC02** (Lane X) | Real Payy aggregation proof for PY-C02 (Rust stack) | Done | RQ2 |
| **D1P-33** | Frozen v1.1 scan of the four reserved projects | Done: 4/4 unsupported, 0 warnings | RQ4 |
| **D1P-35** | BindCheck v1.2: version-only producer-decoder change (no rule change) | Pending | RQ4 |
| **D1P-36** | v1.2 rescan of the four reserved projects plus four unseen, non-reserved projects | Pending | RQ4 |
| **Taxonomy v1 corpus** | Seed-only AI-assisted extraction (Lane X); blind labeling sheet prepared | Done as extraction; human labels pending | §IV-D, RQ5 |

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
circuit–consumer boundary of Noir/ACIR producers and Solidity consumers. It
decodes the compiled circuit and counts the proof-enforced uses of every
public input. It lowers the consumer's compiler AST, recognizes the verifier
call by its interface type rather than by any name, and follows each public
word to guards, storage writes and token effects. Four rules join the two
sides. R-BIND reports a public input that no proof-enforced constraint uses,
and R-EFFECT reports such an input that feeds a consumer effect. R-CONSUMER
reports an authenticated word that reaches no consumer guard, state or
effect. R-POLARITY reports replay accounting that lacks a *must-not-be-in*
check or the matching write on success. Each warning carries a location, an
explanation, evidence and a suggested fix. A separate validator reports the
highest evidence level reached with real proofs. We ground the design in a
taxonomy of binding failures and in three case studies: a publicly disclosed
Payy rollup defect (historical) and two injected WarpToad bridge variants,
M-DOM (producer side) and M-SRC (consumer side). On a 30-mutant development
benchmark over the same two applications, BindCheck v1.1 detects the named
mutation in 16 of 30 mutants. The other 14 fall outside its supported scope,
and there are no misses. A handwritten same-policy Foundry harness detects
more of the WarpToad consumer mutants (8/9 against 5/9). It needs a
per-application policy, however, reaches none of the 16 circuit mutants, and
misses one consumer mutant that BindCheck catches. Compiler and Solidity lint localizes some mutants without describing a
mismatch. Per-application validation harnesses took the 53 benchmark
warnings as far as they could with real proofs and local replays. Nine
reached E4, all on WarpToad and all but one without manual steps. Six
reached E3, six Payy warnings produced unauthorized effects under a mock
verifier, and 32 remain at E1. An AI-assisted seed
extraction for the taxonomy screened 27 public disclosures and included 19
from 15 families, with human labels pending. On the four projects reserved for a held-out test, the frozen tool
produced no analysis. Three use Noir versions it does not decode and one
uses recursive aggregation, so all four are unsupported and no warning was
emitted. Held-out transfer therefore remains untested, and all detection
results are development results on applications known before the rules
were written.

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
benchmark, a handwritten same-policy fuzz harness finds more WarpToad
consumer mutants than BindCheck does (D1P-32). Our claim is therefore
complementarity, not dominance.

### C. BindCheck

BindCheck v1.1 is a command-line tool with two commands (D1P-34; the CLI is
unchanged from v1):

```text
bindcheck analyze <producer artifact> <consumer source> --consumer-ir <checked relation>
bindcheck validate <warning>
```

`analyze` works in three steps.

1. **Producer facts.** It decodes the compiled Noir artifact (ACIR and ABI),
   flattens the ABI into scalar public inputs, and counts how often each
   public witness occurs in proof-enforced opcodes. Brillig calls, which
   only compute witnesses, are inventoried separately and never count.
2. **Consumer facts.** It reads a checked consumer relation whose recorded
   source hash must equal the consumer's. For Payy, an application-neutral
   frontend builds that relation from the solc compiler AST. It finds the
   verifier call by its declared type (proof bytes plus a public `bytes32[]`,
   returning `bool` or reverting), follows the public array through internal
   calls, and records which words reach guards, storage writes and standard
   token calls. For WarpToad, the relations are the earlier route-A
   extractions, now interpreted by the same structural identities. Without a
   checked relation the analysis stops with
   `UNSUPPORTED_CONSUMER_AST_REQUIRED`.
3. **Rules.** R-BIND, R-EFFECT, R-CONSUMER and R-POLARITY join the two
   sides and emit warnings. None of them names a contract, function, field
   or application (D1P-34 §2). Each warning carries a location, an
   explanation, evidence and a suggested fix.

`validate` looks up a registered validation route for the warning's exact
target identity (artifact hash, consumer hash, rule). It runs or audits that
route's staged evidence and reports the highest level reached. Separate
Lane X harnesses build attacker witnesses and drive them through
execution, proving and replay (§V-H). The validation harnesses are written
per application; the analyzer is not.

A warning is evidence level E1. A validated warning reaches E4, the
contract's *end-to-end validated mismatch* (§III-F). The absence of a
warning is not `VERIFIED_WITHIN_SCOPE`. It means only that no rule fired
within the supported scope.

### D. Contributions

The following are the paper's contributions, as listed in research contract
revision 3 (§3). Each item states the evidence that exists now and the
evidence still pending.

1. **A taxonomy of proof-to-execution binding failures** (§IV). It has three
   independent dimensions: cause, consequence and attacker role. It is tied
   to the authorization/coverage semantics of the research contract, and the
   annotation protocol separates disclosure counts from tool support.
   *Exists:* codebook and protocol v0.2.0, and a seed-only v1 corpus (one
   endpoint; 27 findings screened, 19 included from 15 families). Its cause
   labels are AI-suggested and its relevance decisions AI-made. *Pending:*
   human labels, consequence and role labels, agreement statistics, and the
   remaining endpoints.
2. **Actionable cross-layer diagnostics** (§V-F, §V-G). Proof-enforced uses
   of each public input in the compiled circuit are joined to a structural
   lowering of the consumer's guards, state writes and token effects. Four
   rules apply, each stated once without application identifiers. Each
   warning is a versioned JSON record with location, rule, explanation,
   evidence and a suggested fix. *Exists:* on five development targets,
   warnings at the expected word on 3/3 positives, no warning on pinned
   WarpToad, and one unadjudicated consumer-side warning on the repaired
   Payy control (D1P-34 §4). On the 30-mutant benchmark, 16/30 detected,
   14 unsupported, 0 missed, each detection at the named semantic boundary
   (D1P-34 §5). *Held-out:* the frozen tool supported none of the four
   reserved projects (D1P-33), so transfer is untested. *Pending:* a
   version-only rescan **[PENDING D1P-35, D1P-36]**.
3. **Real-proof validation** (§V-H). Warnings are taken toward E4 with real
   proofs and committed local effects, and every manual input is counted.
   *Exists:* the three case-study mismatches reached E4 in D1P-30 (two
   fresh, one preserved). The per-application harnesses produced the
   following on the 53 v1.1 benchmark warnings:
   - fresh E4 on 8 and preserved E4 on 1, all on WarpToad;
   - E3 on 6, including a real Payy aggregation proof (TC02);
   - a consumer effect under a mock verifier on 6 Payy warnings;
   - E1 on the other 32.

   *Pending:* E4 for any Payy warning, which needs a real-verifier
   replay.
4. **Validated case studies** (§II, §VII). One historical case (Payy, with a
   locally reproduced end-to-end effect and a repair validated for one
   witness) and two injected cases (WarpToad M-DOM and M-SRC, each with a
   real-proof differential against the pinned build and exact-state honest
   controls). *Exists:* this ground truth, BindCheck's detection on all
   three (D1P-34), real-proof validation of the v1 warnings on them
   (D1P-30), and baseline comparisons on the same targets (D1P-22, D1P-32).

Consistent with contract §1, we do not claim as new: integration failures as
a category, the permission/obligation/effect terminology, rich semantic
specifications, or modular summaries. The specific advance over prior work
is the cross-layer rule set and its validation. On current evidence it is
demonstrated only on development cases, and a handwritten same-policy
harness outperforms it on one subset (§VII-E). Transfer depends on RQ4,
whose first scan supported no reserved project.

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
  transfer or generality claims (contract §9). A reservation over a small
  frame of eight candidate groups was committed, and its four reserved
  projects were scanned (§IV-D). The scan produced no supported analysis
  (§VII-F).

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
validation routes for v1's warnings and generated fresh proofs (§V-H). That
E4 is credited to the validator only on the condition stated there: the
fixture's witness construction is pre-existing and counted as a manual
input.

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
counted and excluded from automatic-recovery claims. BindCheck v1.1 takes
no explicit `σ` and assigns no semantic roles. Its rules use structural
facts only: source class, guard, state and effect use, and replay pairs
(§V-D). The price is that a warning cannot say which role a word was meant
to play (§IX). Each checked consumer relation is counted as one manual
analysis input (§V-C).

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

The v1.1 rules (§V-F) target the causes that a word-level analysis of one
producer–consumer pair can observe. They do not cover the others, and the
taxonomy keeps those visible as tool limitations rather than dropping them.
Coverage below is by design. Measured coverage on the 30-mutant benchmark
(RQ1, Table 3) matches it. Mutants that remove a use, a guard or one half of
a replay pair are detected. Mutants that leave a binding present but wrong,
such as order, dependency strength or admitted-map identity, are
unsupported.

| Cause | v1.1 rule coverage |
| --- | --- |
| `C_RELATION_GAP` | R-BIND when the needed public input has no proof-enforced occurrence; R-EFFECT when that input also reaches an effect. A dependency that is present but wrong is not detected |
| `C_ACTIVATION_EXTENT` | Only when the extent leaves words with no proof-enforced occurrence, as in full-size Payy. v1.1 has no activation-condition reasoning. A word constrained under some condition counts as used |
| `C_CONTEXT_IDENTITY` | R-BIND when the context word is unused in the circuit (M-DOM); R-CONSUMER when an authenticated calldata word reaches no consumer guard, state or effect (M-SRC). A context word bound to the wrong value, or checked against the wrong map, is not detected |
| `C_OCCURRENCE_ACCOUNTING` | R-POLARITY when a replay record exists but its must-not-be-in guard or its write is missing; R-CONSUMER when the key reaches nothing. An effect path with no replay record at all is not reported |
| `C_FIELD_MAPPING` | Partial: a producer/consumer width mismatch stops with a named reason. Misorder at equal width is not detected |
| `C_REPRESENTATION`, `C_VERIFICATION_CONFIG`, `C_DISCHARGE_TRANSFORMATION` | Not covered; reported as unsupported in the tool funnel |

### D. Empirical method (protocol v0.2.0)

**Frozen design.** The sampling frame is public disclosures about
proof-consuming ZK systems from 1 January 2018 to 27 October 2026. Discovery
starts from source indexes, not application names. There are 17 frozen
endpoints: two seed collections (SNARK SoK dataset, 0xPARC zk-bug-tracker),
13 backbone indexes (audit-firm listings, contest platforms, GitHub Security
Advisories) and two supplemental keyword endpoints. Their traversal order,
pagination, stopping rules and a 1,200-minute active budget are fixed in the
search plan. Families are lineage components. Forks and ports stay in their
family. Two human annotators label 16 fresh packets independently after one
unscored calibration round of four packets, and a third human adjudicates. AI systems are
never raters or tie-breakers. Agreement is reported per label, with
denominators, intervals and `null` where it is undefined. The disclosure
funnel and the tool funnel are reported separately and never combined into
one attrition rate.

**What exists: a seed-only, AI-assisted extraction.** The
[v1 corpus](../docs/taxonomy/v1-corpus.md) covers one of the two seed
endpoints, the 0xPARC zk-bug-tracker at commit `56a99667…`. An AI agent
screened all 27 listed in-the-wild entries. It included 19 and excluded 8,
with none unresolved, and suggested one cause label per included finding.
The machine-readable ledger is schema-valid. Every label is recorded as
`ASSUMED` with an empty `human_label` field. No annotation round has run. The
SoK dataset was not reached: it has no standalone endpoint an agent could
use under the task's constraints, and a custodian still has to identify one.
The remaining 15 endpoints were not traversed.

**Deviation from the frozen plan.** The plan's access rule for agents is
metadata-only, with custodian sanitization. The corpus task instead read the
seed listing bodies (linked issues, commits, papers and reports were not
opened). All 23 families touched are logged as exposed in the ledger and can
never be held out. The metadata-only flow is still owed before any
annotation round.

**Held-out mini-draw (a disclosed smaller frame).** The frozen plan reserves
half of the newly eligible, unexposed family groups in each stratum, drawn
from the full index traversal. What exists is smaller. An AI planner
prepared a metadata-only list of eight candidate GitHub projects that pair a
Noir circuit with a Solidity/EVM consumer, from search-result names and URLs
only, without opening any repository. The custodian checked that none
appears in the 0xPARC tracker. The repository owner, acting as human
custodian, then performed the draw in a plain terminal outside every agent
session (stratum `noir-evm:eligible`, ceiling rounding per stratum). Only a
salted commitment is in the repository (SHA-256 `514ad719…`; definition
`SHA256(nonce ‖ canonical selection manifest)`). The opening was held
privately until the D1P-33 scan. The commitment file does not state how
many groups were reserved. D1P-33 scanned four reserved projects, which
matches the protocol's half-per-stratum rule with ceiling rounding. D1P-33
does not record a check of the opening against the commitment hash. The commitment shows only that a later opening is consistent
with it. It shows neither randomness nor timing. The custodian's attestation
is recorded as reported in the planner session, and the custodian's
signature has not yet been added. Payy, WarpToad, 0xbow Privacy Pools, the
Aztec epoch rollup and all 23 corpus families are exposed and ineligible.

**Claim limit.** The strongest permitted statement, once human labels exist,
is that these mechanisms recur across independent families in the sampled
public disclosures. We make no prevalence, incidence or audit-quality
inference. Before human labeling, the corpus supports no claim beyond its
own existence and its screening counts (§VII-G).

---

## V. Design

This section describes BindCheck v1.1 as implemented in
[`static_analyzer_v1.py`](../src/bindcheck_d1/static_analyzer_v1.py)
(result schema `bindcheck.static-analysis.v1.1`), the compiler-AST frontend
[`solidity_ast_v1_1.py`](../src/bindcheck_d1/frontends/solidity_ast_v1_1.py),
the shared effect table
[`bindcheck-v1.1-effect-models.json`](../protocols/d1/bindcheck-v1.1-effect-models.json)
and [`validation_v1.py`](../src/bindcheck_d1/validation_v1.py) (D1P-34). The
tool was frozen by file hash on base `9e9e71f`. The bytes committed at
`4382ee6` match the freeze manifest. Where the implementation is narrower
than the concept it serves, we say so. v1 (D1P-30) differed in three
places: a name- and regex-based Solidity profile, an occurrence count that
missed some proof-enforced uses, and a root-specific anchor rule. We note
the differences where they matter.

### A. Overview

```
 Noir artifact (ABI + ACIR) ──► producer frontend ──► public leaves; proof-enforced / witness-generation / definition-only counts
                                                                       │
 consumer source ──► solc AST ──► v1.1 AST lowering ───────────────┐
                 └─► route-A extraction (D1P-18 / D1P-21B / D1P-31) ┴─► checked relation (source hash must match)
                                                                       ▼
                 per word: source class, guard use, state or effect use, admitted lookups, replay records
                                                                       │
                              rules R-BIND / R-EFFECT / R-CONSUMER / R-POLARITY
                                                                       │
                                          warnings (E1; JSON and readable text)
                                                                       │
     validation index ──► registered route ──► staged checks;  Lane X harness ──► synthesized witness ──► E2 / E3 / E4
```

*Figure 1 (to be drawn).* Each target is analyzed alone. No result from a
reference version, revision diff or paired variant is an analyzer input. The
checked relation is one counted analysis input. The validation index and the
Lane X validation harnesses are orchestration outside the rule engine.

### B. Producer frontend

**Version gate.** The frontend reads the artifact's `noir_version` and
selects the beta.14 bincode decoder (Payy) or the beta.22 MessagePack
decoder (WarpToad) by exact match. Any other version is rejected. Both
decoders are fail-closed: an unknown opcode, black box, Brillig form or
serialization form raises a named `Unsupported` reason (D1P-13 §3).

**Public inputs.** The ABI is flattened into scalar leaves in declaration
order. Arrays are indexed (`messages[3]`) and structs are dotted. Each public
leaf gets its public index and its witness index from the ABI bindings.
WarpToad's artifacts have 11 public leaves. The full-size Payy artifacts have
1,005 (D1P-34 §4).

**Occurrence roles.** v1.1 sorts every witness occurrence into one of three
roles (D1P-34 §3).

| Role | What is counted | Discharges R-BIND? |
| --- | --- | --- |
| Proof-enforced use | Witnesses in linear or multiplication terms of `AssertZero`; black-box inputs *and outputs*; address and value expressions of memory operations; constrained calls | Yes |
| Witness generation | Brillig inputs, outputs and predicates | No. Inventoried separately |
| Definition only | `MemoryInit` cells | No. Initialization without a memory operation is not a use |

This corrects v1, which missed black-box outputs, Brillig outputs and
memory-operation expressions because its decoders stored those witnesses as
bare integers. On the full-size earlier Payy artifact, `messages[1]` through
`messages[999]` have no proof-enforced use, and each appears once as a memory
definition. The full-size check-added artifact has no unused public leaf.

**What an occurrence means.** An occurrence shows syntactic use in a
proof-enforced constraint. It does not show injectivity, cryptographic
intent, full semantic dependence or policy correctness (D1P-34 §7). A word
that appears in a used hash is counted as used even if the construction is
weak. A word constrained only on one branch is counted as used on every
branch. A deliberately unconstrained metadata word would be warned about.

**Deeper producer facts (not rule inputs).** The project also has Poseidon2
construction provenance for all 86 permutation opcodes (D1P-15 §3), checked
extraction of 77 BN254 Poseidon regions (D1P-19 §3), and an independent
provenance run on M-DOM. That run shows that the silo hash absorbs private
witness 59 where the pinned circuit uses public word 5 (D1P-21A §4). These
extractors accept only frozen artifact identities, and the rules do not use
them. They explain the M-DOM warning after the fact. The warning itself is
derived from occurrence counts alone.

### C. Consumer model

v1.1 accepts a consumer only through a checked relation whose recorded
source hash equals the hash of the consumer source. A mismatch stops with
`CONSUMER_RELATION_SOURCE_HASH_MISMATCH`, and a missing relation with
`UNSUPPORTED_CONSUMER_AST_REQUIRED`. v1's source profile, with its
Payy-derived idioms, is gone. Two relation forms exist.

**Compiler-AST relation (new in v1.1; all seven Payy consumers).** The
evaluation driver runs `solc --combined-json ast` (solc 0.8.20 for Payy) and
passes the AST to the frontend, which proceeds structurally (D1P-34 §2).

1. *Verifier boundary.* Exactly one call must resolve to a declaration with
   two parameters, `bytes` and `bytes32[]`, returning `bool` or nothing. Any
   other count stops with `SOLIDITY_VERIFIER_BOUNDARY_COUNT`. The public
   array argument must be a direct identifier.
2. *Propagation.* The array is followed through internal calls by
   declaration ID. A constant index maps to one word. A loop-carried index is
   widened to the tail of the array from its known lower bound.
3. *Source class.* Each word is classed as calldata, environment or
   consumer-supplied state or configuration.
4. *Guards.* `require` and `assert` arguments, and branch and loop
   conditions, become guard records. Each lists the words it depends on and
   the storage lookups it reads, identified by declaration-ID path and by the
   public words in the key.
5. *Effects.* An assignment to state becomes a storage-write effect. A call
   whose function type matches the shared table becomes a token effect with
   fixed amount and beneficiary positions: `function (address,uint256)` is a
   transfer, and `function (address,address,uint256)` a transfer-from. The
   match covers Payy's low-level `abi.encodeCall(IERC20.transfer, …)` burn
   payout.
6. *Replay records.* A write of boolean `true` is paired with any guard that
   compares a storage lookup with `false` when the declaration path and key
   words agree.
7. *Width mapping.* If the producer has more public leaves than the direct
   array, the difference is taken as a prefix outside the array. The direct
   width is derived from the largest public ABI array and the array-header
   lower bound seen in the AST. For Payy, 1,005 producer leaves face a
   1,003-word array, giving a two-word recursive-verifier selector prefix.
   Old state, new state, the commitment and the 1,000 message words then
   land at producer indices 2, 3, 4 and 5–1004 (D1P-34 §2).

Statement kinds outside the supported subset are named in the relation's
limitations (for example `AST_RECURSIVE_INTERNAL_CALL`) and evaluated
conservatively for dependencies. Every AST relation also carries three
standing limitations: loop-index widening, no Solidity semantic
equivalence, and the derived selector prefix.

**Route-A relation (WarpToad).** WarpToad targets still use relations from
the route-A solc-AST extractor: D1P-18 for the pinned consumer (shared by the
nine circuit mutants, pinned and M-DOM), D1P-21B for M-SRC, and D1P-31's
per-mutant extractions for the consumer mutants. WT-S04 has no relation,
because the extractor failed closed when the verifier call was removed. The
extractor follows actual function bodies and emits every terminal path
family with ordered guards, committed effects and storage writes, against a
shared OpenZeppelin 5.6.1 table with `case_specific_entries=false` (D1P-16,
D1P-18). v1.1 reads these relations with the same structural identities as
AST relations. The verifier relation is excluded as a consumer use, storage
selects are keyed by slot and key symbols, and replay is paired by those
keys. v1's name tests for `root` and `nullifier` and its verifier-line
pattern were removed. The extractor itself was developed on WarpToad's
`mint` fragment. v1.1 changes how its output is read, not how it was built.

### D. Word classification

v1.1 takes no explicit policy `σ` and assigns no semantic role (root,
nullifier, amount) to any word. For each verifier word it records structural
facts only.

| Fact | Meaning |
| --- | --- |
| Source class | Calldata, environment (`block.*`, `msg.*`, `tx.*`) or consumer-supplied state/configuration |
| Consumer use | The word reaches some guard or some effect, excluding the verifier call itself |
| Admitted | The word reaches a storage lookup inside a guard |
| Effect word | The word reaches a storage write or a token effect |
| Replay record | A `true` write paired, by declaration path and key, with a guard comparing the same lookup to `false` |

Only calldata words are required to have a consumer use. A
consumer-supplied configuration word, such as WarpToad's word 5 (the
configured Aztec address), or an environment word such as `block.chainid`,
is not required to appear anywhere beyond the verifier call.

### E. Admission polarity

Roots and replay keys must be checked against consumer state in opposite
directions. We call this *admission polarity*. It is unrelated to the
positive and negative solver controls that earlier reports also call
"polarity" (D1P-14D).

- **Must-be-in.** v1.1 records a word as admitted when it reaches a storage
  lookup inside a guard. It does not check the direction of that lookup, and
  it no longer singles out roots by name. A root that is checked against the
  wrong map, or with the wrong sign, is therefore still admitted (§V-F).
- **Must-not-be-in plus write (replay).** A replay record needs a guard that
  compares a storage lookup with `false` *and* a `true` write to the same
  declaration path and key on success. In route-A relations, replay applies
  if any such write or guard exists, and it is satisfied only if every one
  has both halves. In AST relations, replay applies only when a `true` write
  exists, so a guard left without its write does not make replay
  applicable. The check is still syntactic and within one transition. It
  makes no claim about histories.

### F. Rules

*Table 1: BindCheck v1.1 rules (D1P-34 §2; `static_analyzer_v1.py`).*

| Rule | Producer fact | Consumer fact | Fires when | Reported location | Suggested fix (abridged from the tool) |
| --- | --- | --- | --- | --- | --- |
| **R-BIND** | Public leaf with no proof-enforced occurrence | Every public leaf is a verifier argument (width check) | Any such leaf. Adjacent unused leaves of one array form one warning | `artifact:abi.<leaf>` or `<first>..<last>` | Constrain every exposed verifier argument in the producer, or remove it from the consumer-visible effect surface. Rebuild artifact, key and verifier together |
| **R-EFFECT** | Same as R-BIND | Effect words (§V-D) | Some unused leaf is an effect word. One warning lists all such leaves and the effect kinds | First modeled effect in the relation, else the verifier boundary | Bind every effect-decoded public word in the producer. Derive consumer effects only from bound public inputs |
| **R-CONSUMER** | — | A calldata word with no guard, state or modeled-effect dependency | Once per such word | Verifier boundary | Consume the authenticated word in the corresponding state admission, replay or effect operation, and regenerate the checked relation |
| **R-POLARITY** | — | An applicable replay record whose must-not-be-in guard or `true` write is missing | Once per target | Verifier boundary | Check that the replay key is absent before verification, and write the same key atomically on success |

**R-BIND** and **R-EFFECT** check the producer half: every word the consumer
passes to the verifier must constrain something, and R-EFFECT reports where
an unbound word becomes an effect. On Payy, R-BIND and R-EFFECT describe one
mismatch, and we count it once. **R-CONSUMER** checks the consumer half from
the other direction: an authenticated calldata word that the consumer uses
for nothing beyond the verifier call. It does not infer which guard, state
update or effect was intended (D1P-34 §7). **R-POLARITY** checks single-use
accounting where a replay record exists.

**R-ANCHOR.** v1's root-specific rule is still in the code and the result
schema. Under v1.1, however, both loaders record an anchor only after
finding a guarded storage lookup on it. Every recorded anchor therefore
already satisfies must-be-in, and R-ANCHOR cannot fire. This is our reading
of the code; D1P-34 states only that the rule identity changed. A removed
root guard now surfaces as R-CONSUMER on that word, because the word then
reaches nothing (M-SRC; WT-S01, WT-S02). We defer the fix until after the
transfer test. The planned v1.2 is a version-only change, and R-ANCHOR stays
unreachable in it. Changing a rule between the first held-out attempt and
the rescan would mix rule tuning into the held-out result (contract §9).

**What the rules do not use.** No analyzer or frontend function names a
contract, application, verifier function, guard function or storage field.
A regression test scans both files for the identifiers that v1 used and
passes (D1P-34 §2). The effect table matches function types, not names. The
B02 obligations O1/O2, the admitted-state designs `S_DOM`/`S_SRC`, and any
comparison with the pinned or earlier revision are not inputs. The M-DOM
warning comes from M-DOM's artifact alone.

**What the rules cannot see.**

- A public input that is used but bound to the wrong value, for example
  hashed under the wrong domain.
- A word whose binding depends on a witness-controlled extent but which
  occurs in some constraint.
- A word checked against the wrong map or in the wrong direction.
- A misordered argument vector of the correct width.
- A fee cap, amount or beneficiary that reaches an effect but obeys the
  wrong policy.
- Missing single-use accounting on an effect path that writes no replay
  record at all. On Payy, v1.1 now recovers the burn transfers as effects
  and links them to the unbound tail words through R-EFFECT. No rule states
  separately that burns lack registration.

These gaps account for the 14 unsupported benchmark mutants (§VII-C).

### G. Actionable diagnostics

`analyze` writes a versioned JSON result (`bindcheck.static-analysis.v1.1`)
and readable text. Each warning records:

- `id`, `rule`, `severity` (always `warning`) and `confidence` (always
  `high`);
- `location`, given per rule as in Table 1;
- `explanation`: a sentence naming the leaf, its consumer origin and the
  missing fact;
- `suggested_fix`: the repair text of Table 1;
- `evidence`: public indices, witness indices and occurrence counts; or the
  word's consumer origin and source classes (R-CONSUMER); or the replay guard
  and write flags (R-POLARITY);
- `target_identity`: the artifact hash, consumer hash and rule. The
  validator keys on this identity.

The enclosing result also records the producer facts and the occurrence
policy. These include the opcode counts by kind, and every public leaf with
its proof-enforced, witness-generation and memory-definition counts and
locations. It also records the consumer relation's kind, scope and
limitations, admitted words, replay records, manual inputs and runtime. Two
examples:

```text
W001 R-BIND at m-dom-withdraw.json:abi.aztec_warptoad_address
  Consumer-constructed verifier argument(s) aztec_warptoad_address have no
  occurrence in the decoded proof-enforced ACIR. ...
W003 R-CONSUMER at RollupV1.sol:357            (Payy earlier, full size)
  Verifier public word 4 (commit_hash) is constructed at the boundary but has
  no guard, committed-state, or modeled effect dependency ...
```

**Localization weaknesses observed in the D1P-34 outputs.**

- WarpToad route-A relations carry no source line for the verifier call, and
  v1.1 removed v1's pattern that found it. WarpToad R-CONSUMER and
  R-POLARITY warnings therefore print `WarpToadCore.sol:?`. They name the
  word, for example `destination_local_root`, but not a line.
- R-EFFECT reports the first modeled effect in relation order, which need
  not depend on the unbound word. On full-size Payy earlier this is
  `RollupV1.sol:850`, a validator-set index write with no public-word
  dependency. The burn transfers that consume the tail words, at lines 511
  and 521–522, appear only as effect kinds in the evidence.
- v1.1 maps no producer location back to a Noir source span. It does not
  cross-reference a producer-side warning with the consumer code that
  supplies the word.

### H. Validation

**Registered routes.** `bindcheck validate <result>#<warning>` selects routes
from a validation index whose `match` equals the warning's target identity.
More than one match is an error. No match returns `NO_VALIDATION_ROUTE` at
E1. A route has an optional preparation command that runs the route's
fixture in a clean namespace (a sentinel file makes it audit existing
evidence instead), a record of failed earlier attempts with reasons, and
staged checks. Each stage has an evidence level, a mode (`fresh` or
`preserved`) and file-existence, SHA-256 or JSON-predicate checks. The
result is the highest level whose stage passed, together with manual steps
and inputs. The D1P-30 routes for M-DOM, M-SRC and Payy each have four
stages: concrete witness, circuit execution, real proof, and
unchanged-consumer replay with state checks. Their witnesses come from
fixtures written before D1P-30 (D1P-15, D1P-19, T15/T16/T18), and each
route association is a counted manual input.

Routes are keyed by rule. v1.1's rule identities therefore matter. The
M-DOM warning keeps the identity of its D1P-30 route. The M-SRC and WT-S01
warnings changed from R-ANCHOR to R-CONSUMER, and the full-size Payy
artifacts differ from the N=8 builds the D1P-30 route was keyed to. Under
the unchanged D1P-31 index, only WT-C03's preserved route still matches
(D1P-34 §5.1). No association was added after the run.

**Per-application validation harnesses (Lane X).** *Validation is written
per application. The analyzer is not.* The analyzer applies the same rules
to any supported pair. The harnesses that turn its warnings into evidence
are built for each application
([AUTO-VALIDATE](../docs/x-experiment/AUTO-VALIDATE.md);
[TC02](../reports/TC02.md)). There are three.

- **WarpToad harness.** It maps a warning's shape (rule, location and the
  word named in its evidence) to a synthesis plan in a data table
  ([`witness_synth_v1.py`](../src/bindcheck_d1/witness_synth_v1.py)). The
  plans are:
  - single-word surgery, for R-BIND, R-EFFECT and an R-CONSUMER fee word;
  - a fresh attacker Merkle tree on the same-root branch, for an
    unadmitted local root;
  - a fabricated giga root;
  - an Aztec-branch note, for the domain word;
  - an honest double submission, for a replay key.

  From the frozen honest witness it builds an attacker `Prover.toml`, then
  runs three stages. E2 is `nargo execute` on the mutant. E3 is bb.js
  UltraHonk (`keccakZK`) proving and verification with the mutant's own
  key. E4 deploys the mutant's verifier and consumer on Hardhat EDR,
  replays, and checks the effect on state. A self-test first recomputes
  the honest commitment, nullifier and root from the frozen witness. For
  v1.1, the v1 table's branches keyed to specific mutants were replaced by
  shape dispatch. The word names it matches (`giga_root`,
  `destination_local_root`, `nullifier`, `max_fee`) and its hash code are
  still WarpToad's.
- **Payy consumer harness.** It deploys the pinned or mutant `RollupV1`
  behind an ERC1967-style proxy on anvil (solc 0.8.20), signs blocks with
  ECDSA validator keys, and replays them. A mock verifier stands in for
  proof acceptance, following the project's own test pattern. On the pinned
  consumer, negative controls reject an unregistered mint (`Mint value
  invalid`) and a second settlement (`Mint already spent`). The lane grades
  these rows "E2, mock-verifier-scoped" and never E4. They execute the real
  consumer but check no producer assignment. They therefore show a consumer
  effect, not the contract's E2, which requires an assignment that
  satisfies the compiled producer relation (§III-F).
- **Payy circuit harness (TC02).** A Rust harness modeled on T15 proves a
  real `utxo → agg_utxo → agg_agg` chain on the PY-C02 mutant. It then
  attempts an attacker mint record in the active message slots, which no
  inner proof stands behind. It is a bounded probe, run on one mutant.

The harnesses were written by the AI-assisted lane that built the
benchmark, with the ground truth available. The v1.1 plans were revised
after the v1.1 warnings were known. Two incidents are preserved:
- In the v1 run, a stale mutant directory caused pinned circuits to be
  "validated". Every run now regenerates the mutant and checks it for
  completeness first.
- In the v1.1 run, shape dispatch first sent two Payy R-POLARITY warnings
  down the WarpToad replay path and graded them E3 on WarpToad artifacts.
  An audit caught this before reporting. The Payy rows were rerouted and
  regraded as E2, and the bogus E3 results were never committed.

**Why concrete execution.** Validation executes the real compiled circuit,
produces real proofs, and replays them on an owned local chain. It does not
issue a whole-relation SMT query. Every whole-relation and full-producer
query in our development history timed out or ended without an answer
(D1P-07, D1P-10, D1P-14D, D1P-17; Appendix A). The fresh D1P-30 routes
complete in 28.82 s (M-DOM, two proofs) and 98.99 s (M-SRC, one proof). The
v1.1 WarpToad harness rows take 17–26 s each, at a machine load of about
8.5. TC02 needed a 489 s cold build and an 88.4 s harness run. These times
are operational observations, not benchmarks.

### I. What a result means

A warning is E1 and is not a vulnerability claim. A validated warning is E4
relative to the route's admitted state and the effect it checks, and is
labeled with both. No rule result is ever `VERIFIED_WITHIN_SCOPE`. Silence
on a supported input is reported as "no warning in the supported static
scope", which is E0. It is not evidence of safety. An unsupported compiler
version or decoder form, a missing or mismatched consumer relation, an
unrecovered verifier boundary or a width mismatch stops the analysis with a
named reason. The bounded formal target of contract §7 concerns the joint
transition model. This paper proves no preservation theorem.

---

## VI. Implementation

BindCheck v1.1 is written in Python. The validation fixtures and the Lane X
harnesses use TypeScript, JavaScript and Rust. The table lists the
components and the evidence that validates each one on the development
fragment.

| Component | Location | Validation evidence |
| --- | --- | --- |
| CLI (`analyze`, `validate`) | [`bin/bindcheck`](../bin/bindcheck), `cli.py` | Five-target and 30-mutant evaluation driver (`scripts/d1p_34_evaluate.py`; D1P-34 §6) |
| Static analyzer and rules | [`static_analyzer_v1.py`](../src/bindcheck_d1/static_analyzer_v1.py) (SHA-256 `7f367dfb…`) | 11/11 focused v1.1 tests; scoped suite of 242 tests and 312 subtests passes (D1P-34 §6) |
| Compiler-AST consumer frontend | [`solidity_ast_v1_1.py`](../src/bindcheck_d1/frontends/solidity_ast_v1_1.py) (`e74076f3…`) | Seven Payy relations (baseline, check-added, PY-S01–S05); identifier-absence regression test |
| Shared effect table | [`bindcheck-v1.1-effect-models.json`](../protocols/d1/bindcheck-v1.1-effect-models.json) | Two function-type entries; recovers Payy's burn transfers (D1P-34 §2) |
| Validator | [`validation_v1.py`](../src/bindcheck_d1/validation_v1.py); D1P-30 and D1P-31 validation indices | Case mismatches to E4 in D1P-30; 1 preserved E4 among 53 v1.1 benchmark warnings (D1P-34 §5.1) |
| Per-application validation harnesses (Lane X) | WarpToad: `witness_synth_v1.py`, `scripts/xav/`; Payy: `scripts/xav/payy_replay.ts`, `XAVProxy.sol`, `payy-harness/tc02_tail.rs`; driver `scripts/xav_run.py` | 53 v1.1 warnings: 8 E4, 1 preserved E4, 6 E3, 6 mock-verifier E2, 32 E1 (AUTO-VALIDATE; TC02) |
| ACIR decoder, Noir beta.14 (Payy) | `frontends/acir_binary_v1.py`, `acir_bindings_v1.py` | Typed recursion/frame bindings (D1-03) |
| ACIR decoder and semantic checker, Noir beta.22 | `frontends/acir_binary_beta22.py`, `acir_semantics_beta22.py` | Exact rebuild match; 24,967/24,967 supported constraints on the honest witness; two predeclared mutation controls (D1P-13) |
| Route-A consumer extractor and library models | `prototypes/d1p16/extract_relation.py`, `library_effect_models.v1.json` | 22 families; 5/5 executions; three source-mutation and four edge-control classes (D1P-16, D1P-18) |
| Variant-general relation serializer | `prototypes/d1p20/`, `prototypes/d1p21b/` | Pinned 22/19/3 and M-SRC 21/18/3; 8/8 polarity controls (D1P-20, D1P-21B) |
| Poseidon2 provenance and BN254 regions (not rule inputs) | `warptoad_poseidon_provenance.py`, `warptoad_variant_provenance.py`, `warptoad_bn254_regions.py`, `warptoad_p6.py` | 86/86 opcodes attributed (D1P-15); 77 regions (D1P-19); independent M-DOM run (D1P-21A) |
| Real-proof and chain fixtures used by routes | D1P-15 Hardhat fixture; D1P-19 fixture; T15/T16/T18 harnesses | One-shot proof ledgers; on-state effect checks |

**Toolchains (pinned).** Payy: Noir `1.0.0-beta.14+60ccd48e…`, bb 3.0.0,
solc 0.8.20 (also used for the AST relations), Forge 1.4.1. WarpToad: Noir
`1.0.0-beta.22+c57152f9…`, bb.js 5.0.0 UltraHonk `keccakZK`, solc 0.8.29
(optimizer, 1 run, Cancun), Hardhat 3.3.0 EDR. All chains are fresh
in-process instances with no fork.

**Tests and runs.** The focused v1.1 suite passes 11/11 tests. The scoped
repository suite (`pytest -q tests`) passes 242 tests and 312 subtests in
224.50 s. An unscoped `pytest -q` failed during collection with 83 errors in
preserved third-party CirC scripts under `results/raw/D1P-22`. No BindCheck
test failed (D1P-34 §6). Static analysis takes a median 2.12 s per target
(range 1.65–2.91 s over the 34 completed analyses in the ignored run
ledger). The 30 mutants take 62.405 s in total: 38.552 s for WarpToad and
23.853 s for Payy. These are native-Mac development observations, not
performance results.

**Generality limits of the current implementation.**

- v1.1 accepts exactly two Noir versions.
- The AST frontend has been run on one consumer family (Payy, seven
  sources) under one solc version, and supports a bounded statement and
  expression subset.
- WarpToad still uses route-A relations, and no AST relation was built for
  any WarpToad consumer.
- Validation needs a registered route for each target identity, or a
  validation harness written for the application.

D1P-33 never reached the AST frontend, because all four reserved projects
stopped at the producer frontend (§VII-F). A held-out consumer will go
through the AST frontend, which has so far seen
one application.

---

## VII. Evaluation

### A. Research questions

| Paper RQ | Question | Contract RQ (rev. 3) | Case studies | Mutation benchmark |
| --- | --- | --- | --- | --- |
| **RQ1 Detection** | Do the generic rules warn at the correct public word and consumer location, without case-specific input? | RQ1 (fidelity), RQ2 (discovery) | D1P-34 (v1.1 rerun of the D1P-30 targets) | D1P-34 |
| **RQ2 Warning quality and validation** | Are warnings localized and actionable? How many reach E4, at what cost, and with how many manual inputs? | RQ3 (validation) | D1P-30 routes; D1P-34 | D1P-34 index audit; AUTO-VALIDATE (v1.1); TC02 |
| **RQ3 Baselines** | What do circuit-only and contract-only tools report on the same targets, in default and same-policy arms? | RQ4 (comparative) | D1P-22; D1P-32 harness on WarpToad targets | D1P-32 |
| **RQ4 Held-out** | With the tool frozen, what does BindCheck report on reserved families, and do any reports validate? | RQ4 (transfer) | — | D1P-33 (done: 4/4 unsupported); D1P-35/36 pending |
| **RQ5 Taxonomy** | Which causes, consequences and roles recur across independent families in sampled disclosures, and how reliably can people label them? | — (descriptive; contract §3 item 1) | — | v1 corpus (AI-assisted; human labels pending) |

Contract RQ5 (efficiency) is not a paper RQ. Its null results are in
Appendix A, as the contract requires. Revision 3 added the taxonomy and
actionable diagnostics as candidate contributions without renumbering the
RQs.

### B. Subjects and protocol

**Development cases (five targets).**

- Payy earlier `c4d2c902…` (historical, faulty) and check-added `dcd5d96e…`
  (repaired for one witness). v1.1 analyzes the full-size 1,000-message
  `agg_agg` artifacts: `83b75a4a…` (1,624,682 bytes) and `866b1800…`
  (1,702,898 bytes), each with 1,005 public leaves. The consumer
  `RollupV1.sol` (`7062065c…`) is byte-identical at both commits, and each
  revision gets its own AST relation (D1P-34 §4). The preserved E4 chain
  (T15/T16/T18) also uses the 1,000-message configuration. T15 does not
  record whether its artifact is byte-identical to `83b75a4a…`. D1P-30's
  v1 rows used N=8 builds and are not relabeled.
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
predicted effect (`manifest.json`, `mutants/<ID>.md`). Cheap reachability
was checked only for WarpToad circuit mutants, by running `nargo execute` on
the honest path. WT-C01, C02, C04, C05, C08 and C09 pass. WT-C06 and C07
fail with `Cannot satisfy constraint`, as designed, and WT-C03 was skipped
by design. Payy circuit mutants and all consumer mutants were checked by
compilation and diff audit only. Four candidate classes were excluded with
reasons (BENCHMARK.md §6). The Payy mutants are full-size 1,000-message
builds of the *earlier, faulty* revision. The benchmark is development data,
and both families are exposed and can never be held out. Its operators were
chosen with knowledge of the case mechanisms, so it measures coverage of
operator classes, not discovery.

**Benchmark protocol (D1P-34 §§5–6).** The mutants and ground truth are
unchanged from D1P-31. The v1.1 tool files were hashed into a freeze
manifest before the evaluation, and no rule or loader changed afterwards.
Ground-truth records were not given to BindCheck. They were read only by the
post-run adjudication script. Consumer relations:
- the nine WarpToad circuit mutants share the pinned D1P-18 relation;
- the WarpToad consumer mutants use D1P-31's per-mutant route-A
  extractions, except WT-S04, which has none and is unsupported;
- the Payy mutants use v1.1 AST relations, one baseline relation for the
  seven circuit mutants and one per consumer mutant.

Each analyzed mutant has one counted relation input (29 of 30). Scoring
followed these rules.

1. A mutant is **detected** only if a warning names its own broken binding
   (word, guard, effect or replay obligation). The benchmark records do not
   give literal line numbers, so location is scored at that semantic
   boundary, not as recovery of the edited line.
2. A mutant is **unsupported** when its intended semantic role, ordering,
   hash dependency, beneficiary policy or record format is not available
   from the target-alone IR. A **miss** is a supported mutant without a
   correct warning. Unsupported mutants are never counted as misses or
   successes. Thirteen of the 14 unsupported mutants were analyzed to
   completion without a related warning. Only WT-S04 stopped (§VII-E
   rescores them on the baselines' scale).
3. Warnings that do not concern the mutant's named binding are
   **unrelated**. All are on Payy and are inherited from its faulty baseline
   (§VII-C).
4. WT-C03 and WT-S01 coincide with M-DOM and M-SRC. Totals are given with
   and without them.
5. All 53 warnings were passed once through the unchanged D1P-31 validation
   index. No association was added after the run.

**Policy.** v1.1 takes no explicit `σ` (§V-D). Any same-policy baseline
receives the reviewed `σ` of [baselines.md](baselines.md). For WarpToad,
`σ` is DRAFT where the documentation leaves beneficiary policy open
(D1P-12R §8.1). D1P-32's Foundry property covers mint amount and
beneficiary, admitted roots, verifier gating, single-use nullifiers and
rollback, but not a maximum-fee ceiling.

**Scoring loci for the case targets** (from [baselines.md](baselines.md)
§4.3, extended to the variants; used for scoring only and never as tool
input):

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
BindCheck analyst time was not instrumented in D1P-30, D1P-31 or D1P-34.
D1P-32 records the effort for the Foundry harness.

### C. RQ1 — Detection

*Table 2: v1.1 detection on the five development targets (D1P-34 §4;
analysis outputs). Validation evidence comes from D1P-30 (v1 warnings) and
is discussed in §VII-D.*

| Case | Class | Pins (artifact / consumer) | Consumer relation | Rule(s) fired | Public word(s) and evidence | At scoring locus? | Static runtime | Analysis manual inputs | Reported verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Payy earlier | Historical, faulty (full size) | `83b75a4a…` / `7062065c…` | AST (v1.1) | R-BIND, R-EFFECT, R-CONSUMER | R-BIND `messages[1]..messages[999]` (public 6–1004; no proof-enforced use, one memory definition each). R-EFFECT on the same words, effect kinds storage write, token transfer and transfer-from. R-CONSUMER on `commit_hash` (public 4) | Producer: yes. Consumer: the burn transfers appear only as effect kinds; the R-EFFECT location (`RollupV1.sol:850`) is not the payout. R-CONSUMER concerns another word (unadjudicated) | 2.06 s | 1 | `UNKNOWN` |
| Payy check-added | Historical, repaired (one witness; full size) | `866b1800…` / `7062065c…` | AST (v1.1) | R-CONSUMER | No unused public leaf. R-CONSUMER on `commit_hash` (public 4) at `RollupV1.sol:357` | Control, with one unadjudicated consumer-side warning | 2.16 s | 1 | `UNKNOWN` |
| WarpToad pinned | Honest fixture (not proven negative) | `7190813f…` / `323a1cf2…` | Route A (D1P-18) | none | All 11 words used; every calldata word reaches a guard or effect; replay record complete | n/a (control) | 2.13 s | 1 | `UNKNOWN` |
| WarpToad M-DOM | Injected, producer | `db1a0a17…` / `323a1cf2…` | Route A (D1P-18) | R-BIND | Word 5 `aztec_warptoad_address` (no proof-enforced use) | Yes | 2.46 s | 1 | `UNKNOWN` |
| WarpToad M-SRC | Injected, consumer | `7190813f…` / `64ec0efd…` | Route A (D1P-21B) | R-CONSUMER | Word 4 `destination_local_root` (calldata; no guard, state or effect dependency). Printed location `WarpToadCore.sol:?` | Word: yes. Line: not given | 2.25 s | 1 | `UNKNOWN` |

The reported verdict is the D1 verdict. Detection on an injected variant is
evidence about that variant, not about pinned WarpToad.

**The `commit_hash` warning.** On both Payy revisions, public word 4
reaches only the verifier call. Its consumer check, `verifyCommitHash`, has
an empty body, and the source comments it as a "Placeholder for asserting
the commit hash is stored on Celestia" (`RollupV1.sol:381–382`). The warning
is therefore a true structural observation: the authenticated word reaches
no on-chain guard, state or effect. Whether that is a defect depends on the
off-chain data-availability check that the placeholder anticipates. TC02
treats it as off-chain by design, and D1P-34 §4 labels it neither a
vulnerability nor a false positive. The warning is independent of the
message tail and of the repair. We report it as a true structural
observation pending adjudication. It counts neither as a detection of the
Payy case nor as a false alarm.

**Answer to RQ1 (cases).** On the five development targets, v1.1 warned at
the scoring word on all three known positives: Payy through R-BIND and
R-EFFECT, M-DOM through R-BIND, and M-SRC through R-CONSUMER. It emitted no
warning on pinned WarpToad. On the repaired Payy control, it emitted only
the `commit_hash` R-CONSUMER warning described above, so one of two controls
carries a warning. Each target was analyzed alone, with no revision diff.
No single-sided rule covers all three positives: the producer-side defects
need R-BIND and the consumer-side one needs R-CONSUMER. These results are
in-sample, because the rules were written after all three mechanisms were
known. Two controls do not support a precision estimate. v1 (D1P-30) gave
the same outcome on the three positives, with R-ANCHOR on M-SRC and N=8
Payy builds.

*Table 3: v1.1 detection on the mutation benchmark, by operator (D1P-34
§§5.3–5.4; compile and reachability from BENCHMARK.md §§3–4). D = detected,
M = missed, U = unsupported. Related and unrelated count warning objects.
Validation is the unchanged D1P-31 index.*

| Operator | Mutants | Side | Reachability check (Lane X) | Result | Warnings at the broken binding | Related / unrelated W | Index validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| leave-public-unconstrained | WT-C01, WT-C02, PY-C02, PY-C06 | Circuit | WT honest path passes; PY compile + diff | 4 D | R-BIND `nullifier`; R-BIND `max_fee`; R-BIND `messages[0]..messages[999]` + R-EFFECT; R-BIND `new_root` + R-EFFECT | 6 / 3 | E1 |
| replace-public-with-private | WT-C03 (= M-DOM) | Circuit | Skipped; reuses D1P-15 | 1 D | R-BIND `aztec_warptoad_address` | 1 / 0 | E4, preserved |
| remove-guard (circuit) | WT-C04, WT-C08, PY-C01, PY-C03 | Circuit | WT honest path passes; PY compile + diff | 2 D, 2 U | WT-C04: R-BIND `giga_root`, `destination_local_root`; WT-C08: R-BIND `recipient_address` + R-EFFECT `WarpToadCore.sol:171` | 4 / 6 | E1 |
| swap-checks | WT-C05; WT-S05 | Circuit; consumer | C05 passes; S05 compile + diff | 2 U | — | 0 / 0 | — |
| unbind-amount | WT-C06 | Circuit | Fails by design | 1 U | — | 0 / 0 | — |
| unbind-domain | WT-C07 | Circuit | Fails by design | 1 D | R-BIND `chain_id` | 1 / 0 | E1 |
| misorder-words | WT-C09, PY-C07; WT-S08 | Circuit; consumer | C09 passes; others compile + diff | 3 U | — | 0 / 3 | — |
| unbind-commitment | PY-C04 | Circuit | Compile + diff | 1 D | R-BIND `commit_hash` | 1 / 3 | E1 |
| remove-config-check | PY-C05 | Circuit | Compile + diff | 1 U | — | 0 / 3 | — |
| remove-guard (consumer) | WT-S01 (= M-SRC), WT-S02, PY-S01 | Consumer | Compile + diff; WT-S01 reuses D1P-19 | 3 D | R-CONSUMER `destination_local_root`; R-CONSUMER `giga_root`; R-POLARITY at `RollupV1.sol:357` (guard missing, write present) | 3 / 3 | E1 (WT-S01's preserved route is keyed to R-ANCHOR) |
| drop-accounting | WT-S03 | Consumer | Compile + diff | 1 D | R-CONSUMER `nullifier` | 1 / 0 | E1 |
| drop-write | WT-S09 | Consumer | Compile + diff | 1 D | R-POLARITY (guard present, write missing) | 1 / 0 | E1 |
| drop-single-use | PY-S02 | Consumer | Compile + diff | 1 D | R-POLARITY at `RollupV1.sol:357` (guard missing, write present) | 1 / 3 | E1 |
| remove-gate (verifier call) | WT-S04 | Consumer | Compile + diff | 1 U (route-A extractor finds no verifier boundary) | — | 0 / 0 | — |
| unbind-fee | WT-S06 | Consumer | Compile + diff | 1 D | R-CONSUMER `max_fee` | 1 / 0 | E1 |
| misdirect-beneficiary | WT-S07 | Consumer | Compile + diff | 1 U | — | 0 / 0 | — |
| misbind-word | PY-S03 | Consumer | Compile + diff | 1 U | — | 0 / 3 | — |
| activate-dead-path | PY-S04 | Consumer | Compile + diff | 1 U | — | 0 / 3 | — |
| offset | PY-S05 | Consumer | Compile + diff | 1 U | — | 0 / 3 | — |
| **Total** | 30 (16 circuit, 14 consumer) | — | 6 pass, 2 fail by design, 1 skipped, 21 compile + diff only | **16 D, 0 M, 14 U** | 16/16 at the semantic boundary | **20 / 33** | 1 E4 (preserved), 52 E1 |
| **Excluding WT-C03, WT-S01** | 28 | — | — | 14 D, 0 M, 14 U | 14/14 | 18 / 33 | 51 E1 |

*Table 3a: Benchmark summary by application (D1P-34 §5.2).*

| Application | Mutants | Detected | Missed | Unsupported | Detected / all | Related / unrelated W | Static wall sum |
| --- | --- | --- | --- | --- | --- | --- | --- |
| WarpToad | 18 | 11 | 0 | 7 | 11/18 | 13 / 0 | 38.552 s |
| Payy | 12 | 5 | 0 | 7 | 5/12 | 7 / 33 | 23.853 s |
| **Total** | **30** | **16** | **0** | **14** | **16/30 (53.3%)** | **20 / 33** | **62.405 s** |

The headline figure is 16/30, over all targets. With no misses, a
within-scope ratio would be 16/16 by construction. We do not report it as a
capability estimate (D1P-34 §1). The 14 unsupported mutants are reported as
unsupported, never as misses or as safe.

*History.* Frozen v1 scored 13 detected, 16 unsupported and 1 miss (PY-S02)
on the same 30 mutants (D1P-31). v1.1 was developed after those results were
known (§VII-H).

**Answer to RQ1 (benchmark).** Across the 30 mutants, v1.1 detected the
named mutation in 16, found 14 outside its supported scope, and missed none.
Every detection named the broken word, guard, effect or replay obligation.
Coverage follows the rules' design:
- unused public inputs (WT-C01, C02, C03, C04, C07, C08; PY-C02, C04,
  C06) → R-BIND, with R-EFFECT where the word reaches an effect;
- calldata words left with no consumer use (removed root guards WT-S01 and
  S02, dropped nullifier accounting WT-S03, unbound fee WT-S06) →
  R-CONSUMER;
- broken replay pairs (dropped write WT-S09; removed guard PY-S01 and
  PY-S02) → R-POLARITY.

The unsupported set is not homogeneous (D1P-34 §5.4). It covers:
- how strongly a hash or Merkle construction depends on its inputs (WT-C05,
  C06);
- word role and order identity (WT-C09, WT-S08, PY-C07);
- which admitted map a root is checked against (WT-S05);
- beneficiary policy (WT-S07);
- an absent verifier boundary (WT-S04);
- recursive padding, root and key semantics (PY-C01, C03, C05);
- Payy record format, offset and activation (PY-S03, S04, S05).

Almost all of these are bindings that exist but are wrong, which neither
occurrence counting nor "some consumer use" can see (§V-F). WT-S06 is
detected only because the mutant leaves `max_fee` with no use at all. A fee
check against the wrong cap would not be detected. These are development
results on exposed applications. They are not held-out transfer.

**Unrelated warnings.** All 33 unrelated warnings are on Payy, and they are
not false positives. The Payy mutants are built on the earlier, faulty
revision, which intentionally keeps the message-tail defect. Its consumer
also leaves `commit_hash` without a guard, state write or modeled effect.
Each Payy mutant therefore inherits up to three baseline warnings: R-BIND on
the tail, R-EFFECT, and R-CONSUMER on `commit_hash`. These are unrelated
unless the mutant's own binding coincides with them, which happens in
PY-C02 (the tail and R-EFFECT) and PY-C06 (R-EFFECT). Ten mutants carry
three unrelated warnings each, PY-C06 carries two and PY-C02 one. No warning was
adjudicated a confirmed semantic false warning. A warning-object precision
figure is meaningless without this inheritance, so we do not report one.

### D. RQ2 — Warning quality and validation

*Table 4: Per-warning record for the development cases (v1.1 warnings,
D1P-34 §4; validation evidence from D1P-30 §5 for v1's warnings on the
same mismatches).*

| Warning | Case | Rule | Location (as emitted) | Evidence | Suggested fix (repair side) | Adjudication | Validation of the mismatch | Route mode, proofs, time | Manual steps (validation) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| W001 | Payy earlier | R-BIND | `agg_agg.json:abi.messages[1]..messages[999]` | public 6–1004; no proof-enforced use | Producer: constrain exposed arguments | Target | E4 on the preserved full-size chain, credited in D1P-30 to the v1 warning on the N=8 build; the v1.1 identity has no route | Preserved T15/T16/T18; no new proof | 2 (D1P-30) |
| W002 | Payy earlier | R-EFFECT | `RollupV1.sol:850` (first modeled effect, not the payout) | same words; effect kinds storage write, token transfer, transfer-from | Producer binding; consumer derives effects only from bound words | Target (same mismatch as W001) | As W001 | As W001 | — |
| W003 | Payy earlier | R-CONSUMER | `RollupV1.sol:357` (verifier call) | public 4 `commit_hash`; calldata; no guard, state or effect | Consumer: consume the word | Not the case target; true structural observation, pending adjudication | E1 (no route) | — | — |
| W001 | Payy check-added | R-CONSUMER | `RollupV1.sol:357` | as above | as above | Control warning; true structural observation, pending adjudication | E1 (no route) | — | — |
| W001 | M-DOM | R-BIND | `m-dom-withdraw.json:abi.aztec_warptoad_address` | public 5; no proof-enforced use | Producer: constrain exposed arguments | Target | E4 in D1P-30. The v1.1 warning has the same target identity, but the route was not rerun. The coinciding mutant WT-C03 reached fresh E3 and preserved E4 under the WarpToad harness | Fresh; 2 real proofs (honest, foreign note); 28.82 s; peak RSS 737 MB | 1 |
| W001 | M-SRC | R-CONSUMER | `WarpToadCore.sol:?` | public 4 `destination_local_root`; calldata; no guard, state or effect | Consumer: consume the word in a state admission, replay or effect (generic text; the role is not named) | Target | E4 in D1P-30 for the v1 R-ANCHOR warning on the same word. The coinciding mutant WT-S01 reached fresh E4 with the v1.1 R-CONSUMER warning under the WarpToad harness | Fresh; 1 real proof; 98.99 s; peak RSS 490 MB | 1 |

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

*Table 5: Warning-quality and validation summary.*

| Scope | Warnings | Related / other | At semantic location | Warnings on controls | E4 fresh / preserved | E3 | E2 (mock verifier) | E1 | Manual validation steps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Development cases, v1.1 (D1P-34 §4) | 6 | 4 target / 2 `commit_hash` (pending adjudication) | 4/4 target warnings name the scoring word; M-SRC prints no line; Payy R-EFFECT points to an unrelated write | 1 of 2 (Payy check-added) | Mismatches: 2 / 1, via v1 warnings (D1P-30) | — | — | — | 1–2 per route (D1P-30) |
| Benchmark, v1.1, unchanged D1P-31 index (D1P-34 §5) | 53 | 20 / 33 inherited | 16/16 detections | n/a | 0 / 1 (WT-C03) | 0 | 0 | 52 | 2 (WT-C03) |
| Benchmark, v1.1, per-application harnesses (AUTO-VALIDATE; TC02) | 53 | 20 / 33 inherited | — | n/a | 8 / 1 | 6 | 6 | 32 | 0, except 2 on WT-C03 |

*Table 5a: Validation of the v1.1 benchmark warnings by the per-application
harnesses (AUTO-VALIDATE v1.1 table; TC02; results ledgers in ignored
`results/raw/X-AV/v11/` and `results/raw/TC02/`). WarpToad times were
observed at a machine load of about 8.5 and are cost observations.*

| Mutant | v1.1 warning | Level | Time | Manual steps | Outcome |
| --- | --- | --- | --- | --- | --- |
| WT-C01 | R-BIND `nullifier` | E4 | 26.2 s | 0 | Second mint from an honest second proof |
| WT-C02 | R-BIND `max_fee` | E3 | 18.0 s | 0 | Proof accepted; consumer reverts at the fee cap (contained) |
| WT-C03 | R-BIND `aztec_warptoad_address` | E4, preserved (E3 fresh) | 11.7 s | 2 | Byte-identical to the M-DOM artifact; D1P-15 foreign-note chain associated |
| WT-C04 | R-BIND `giga_root`; R-BIND `destination_local_root` | E4; E4 | 17.3 s; 18.1 s | 0; 0 | Mint from a fabricated origin root |
| WT-C07 | R-BIND `chain_id` | E3 | 18.7 s | 0 | Dataless verifier revert with all prior gates passing; contained on the same chain; cross-chain impact argued, not executed; out-of-gas not excluded |
| WT-C08 | R-BIND `recipient_address`; R-EFFECT `:171` | E3; E3 | 19.4 s; 20.7 s | 0; 0 | OpenZeppelin `ERC20InvalidReceiver` on mint to zero (contained) |
| WT-S01 | R-CONSUMER `destination_local_root` | E4 | 18.7 s | 0 | Mint over an unadmitted local root |
| WT-S02 | R-CONSUMER `giga_root` | E4 | 19.1 s | 0 | Mock giga provider admits the fabricated root by construction; shows that K1 is absent, not a real-bridge bypass |
| WT-S03 | R-CONSUMER `nullifier` | E4 | 19.4 s | 0 | Replay of an honest proof |
| WT-S06 | R-CONSUMER `max_fee` | E4 | 19.3 s | 0 | Proof with `max_fee = 0` mints and pays the relayer about `0.24e18`, above the stated maximum (new in v1.1) |
| WT-S09 | R-POLARITY | E4 | 19.9 s | 0 | Replay of an honest proof |
| PY-C02 | R-BIND `messages[0]..messages[999]` | E3 | 17.3 s prove and verify (88.4 s harness) | 0 | Attacker mint record in slots 0–3 proves and verifies under the mutant's key; independent `bb verify` exits 0; a 1-bit tamper fails; the pristine circuit rejects it at the removed `main.nr:74` assertion (TC02) |
| PY-C02 | R-EFFECT `:850` | E3 | same proof | 0 | Same proof. The pinned consumer contained the effect in the mock-verifier replay; real-verifier E4 is owed |
| PY-S01 | R-EFFECT `:842`; R-POLARITY `:357` | E2, mock verifier; E2, mock verifier | 1.5 s; 0.9 s replay | 0 | Unregistered mint settled |
| PY-S02 | R-EFFECT `:850`; R-POLARITY `:357` | E2, mock verifier; E2, mock verifier | 1.1 s; 1.1 s replay | 0 | Registered mint settled twice |
| PY-S03 | R-EFFECT `:851` | E2, mock verifier | 1.0 s replay | 0 | Burn paid a `noteKind`-derived address; the recipient received nothing |
| PY-S04 | R-EFFECT `:853` | E2, mock verifier | 1.0 s replay | 0 | Dead kind-4 record settled as a burn; recipient +1000 |
| PY-C01, C03–C07, PY-S01–S05 (other rows) | 31 R-BIND, R-EFFECT and R-CONSUMER warnings | E1 | — | — | No real inner-proof vector for these mutants |
| PY-C02 | R-CONSUMER `commit_hash` | E1 | — | — | Off-chain placeholder check; no experiment |

The counts are 8 E4, 1 preserved E4, 6 E3, 6 mock-verifier E2 and 32 E1,
over all 53 warnings. Of the 32 E1 warnings, 31 are Payy rows waiting for
real inner-proof vectors, and one is the `commit_hash` warning on PY-C02.
The other Payy R-EFFECT locations (`:842`–`:853`) are again first-effect
positions in each mutant's relation (§V-G). The earlier run on the 20 v1
warnings (7 fresh E4, 1 preserved, 4 E3, 8 E1) is history.

*Table 6: Manual inputs and analyst effort on the development cases.*

| Case | Analysis manual inputs (v1.1) | Validation manual inputs (D1P-30) | Explicit `σ` | Witness construction | Same-policy Foundry property (D1P-22; D1P-32) |
| --- | --- | --- | --- | --- | --- |
| Payy earlier | 1 (AST relation) | 2 (route association; historically authored tail record) | None | Preserved T15 harness | No earlier-revision harness (R) |
| Payy check-added | 1 (AST relation) | 0 (no target warning) | None | — | Honest wrapper: 7/7 tests pass (control) |
| WarpToad pinned | 1 (route-A relation) | 0 (no warning) | None | — | D1P-32 harness: all seven invariants pass (control) |
| M-DOM | 1 (route-A relation) | 1 (route association) | None | D1P-15 fixture (pre-existing) | D1P-32 harness: all invariants pass (M) |
| M-SRC | 1 (route-A relation) | 1 (route association) | None | D1P-19 fixture (pre-existing) | D1P-32 harness: `invariant_roots_are_admitted` fails (D, E1 under a stub verifier) |

Historical reference point: the hand-written Payy mint property was about 90
lines of Solidity (87 non-comment) and functionally equivalent to the earlier
checker's manual specification (T14 §4). The D1P-32 WarpToad harness is 156
nonblank, non-comment lines plus 18 lines of configuration.

**Answer to RQ2 (cases).** Every v1.1 warning on the development cases names
the public word and the side to repair. The producer-side warnings name the
ABI leaf. The consumer-side warnings name the word, but on WarpToad they
give no source line, and on Payy the R-EFFECT location is an unrelated write
(§V-G). All three positive mismatches reached E4 in D1P-30, through v1
warnings, with fresh real proofs on the injected variants and an automatic
audit of the preserved Payy chain. The M-DOM v1.1 warning has the same
target identity as its validated v1 warning. The M-SRC and Payy identities
changed. The benchmark mutants that coincide with M-DOM and M-SRC (WT-C03,
WT-S01) were validated with their v1.1 warnings by the WarpToad harness. The
v1.1 Payy case warnings have not been revalidated. Each D1P-30
validation needed one or two manual route inputs, and each witness came from
a fixture written before D1P-30. The diagnostics are actionable in the
narrow sense that the suggested fix names the missing binding, guard or
use. They do not explain the mechanism.

**Answer to RQ2 (benchmark).** Under the unchanged D1P-31 index, 1 of the 53
v1.1 warnings reached E4: WT-C03, preserved, with two manual inputs. The
drop from v1's two is a routing effect, because WT-S01's route is keyed to
the old R-ANCHOR identity (D1P-34 §5.1). With the per-application harnesses,
the picture changes:
- **WarpToad: every one of the 13 warnings reached at least E3.** Eight
  reached fresh E4 with no manual steps, including the new WT-S06 fee
  detection. One reached preserved E4. Four stopped at E3: the forged proof
  verifies, but an independent consumer check (the fee cap, the ERC-20
  receiver check, or a verifier revert under `block.chainid`) contains the
  effect. These are informative negatives: the circuit-side binding is
  broken, yet the consumer blocks the effect.
- **Payy: no warning reached E4.** TC02 took PY-C02's circuit warning to E3
  with a real aggregation proof. Six consumer-mutant warnings produced
  unauthorized effects on state under a mock verifier: an unregistered
  mint, a double settlement, a misdirected burn and a dead record kind.
  These are consumer executions, not contract-level E2 (§V-H). The other 31
  Payy rows and the `commit_hash` warning stay at E1.

All E-levels except WT-C03's were reached without manual steps at run time.
The harnesses, however, are per application and were written with the
benchmark's ground truth available. They show that these warnings can be
driven to real proofs and effects. They do not show witness construction
for an application without a harness.

### E. RQ3 — Comparison with circuit-only and contract-only baselines

Versions, arms, budgets and setup are preregistered in
[baselines.md](baselines.md). D1P-22 (case targets) and D1P-32 (benchmark)
froze run limits and scoring before analyzing any target. Each cell is
scored as follows:
- **D**: the report describes the seeded defect or the proof-to-execution
  mismatch;
- **E1**: a warning names the defect locus or variable but does not
  describe the mismatch (D1P-32 calls this "detected-E1-lint");
- **M**: an applicable completed run gave no such warning;
- **U**: unsupported (the tool cannot accept the input or has no policy
  interface);
- **R**: unresolved (timeout, failure before analysis, or a missing
  required harness), never treated as safe.

On a control, `M (control)` means no binding signal and `E1 (control)` means
nondiscriminating lint.

*Table 7: Baseline outcomes on the case targets (D1P-22; D1P-32 for the
WarpToad same-policy harness and the sequential Mythril retry). G = generic
or default arm; S = same-policy arm.*

| Baseline | Arm | Payy earlier (+) | Payy check-added (control) | WarpToad pinned (control) | M-DOM (+) | M-SRC (+) | Note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Pinned Noir checks | G | M | M (control) | M (control) | **E1** | M | beta.22 named M-DOM's unused public variable (`src/main.nr:20`); beta.14 emitted only an unrelated unused-import warning |
| Pinned Noir checks | S | U | U | U | U | U | No user-policy interface |
| CCC-Check | G / S | U | U | U | U | U | Pinned build timed out; consumes CirC IR, and no Noir/ACIR route exists |
| Picus | G / S | U | U | U | U | U | Installed; native inputs are `.circom`, iden3 `.r1cs`, gnark `.sr1cs`, not ACIR |
| Slither | G | **E1** | **E1 (control)** | M (control) | M | **E1** | `reentrancy-no-eth` names `verifyBurn`; naming lint names `_localRoot`, and the same style warning appears on the pinned control |
| Slither | S | U | U | U | U | U | No custom policy detector existed |
| Mythril | G / S | R | R (control) | R (control) | R | R | Sequential retry with isolated state: Payy earlier killed at 1,810 s; WarpToad pinned `SIGSEGV` at 30 s; the others hit the 1,800 s cap with generic warnings only |
| Foundry | G | R | R (control) | R (control) | R | R | No G1–G5 harness for the case targets in D1P-22 |
| Foundry | S | R | M (control) | M (control) | M | **D** | Payy: honest wrapper, 7/7 pass on the repaired revision only. WarpToad: D1P-32 harness with a relational stub verifier; M-SRC fails root admission (E1 counterexample, not E4) |
| Echidna | G / S | R | R (control) | R (control) | R | R | Payy wrapper failed on an unsupported cheatcode; WarpToad runs stopped before fuzzing on an unlinked library (D1P-32) |
| SmartAxe | G | U | U | R (control) | R | R | Payy is not a bridge pair. The official artifact was blocked by a WAF challenge |
| SmartAxe | S | U | U | U | U | U | No user-property interface |
| Circomspect, CIVER | — | not run | not run | not run | not run | not run | Circom-only natively (READMEs) |
| Joint SMT (monolithic, goal-cone) | — | not run | not run | not run | not run | not run | Earlier attempts in Appendix A |
| **BindCheck v1.1** (D1P-34) | — | **D** | Warning (control; R-CONSUMER `commit_hash`, true structural observation pending adjudication) | M (control) | **D** | **D** | Context row; not run by the baseline lanes |

**Answer to RQ3 (cases).** No default-arm baseline described the mismatch on
any case target. Two generic checks localized a known positive without
explaining it. Slither named Payy's `verifyBurn`, and the beta.22 Noir
compiler named M-DOM's unused `aztec_warptoad_address`. Slither's mention of
M-SRC's `_localRoot` also appears on the pinned control, so it does not
discriminate. The D1P-32 same-policy harness detects M-SRC as a
root-admission violation and passes M-DOM. M-DOM's defect lives in the
circuit, and the harness replaces the circuit with a stub that accepts the
expected public words. BindCheck is the only tool in the comparison whose
diagnostics state a cross-component reason on all three positives.

*Table 8: Baseline outcomes on the mutation benchmark (D1P-32 per-mutant
classifications, grouped by application and side; counts per outcome).*

| Baseline | Arm | WarpToad circuit (9) | WarpToad consumer (9) | Payy circuit (7) | Payy consumer (5) | Total (30) | Excluding WT-C03, WT-S01 (28) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Pinned Noir checks | G | E1 6 · M 3 | U 9 | E1 4 · M 3 | U 5 | E1 10 · M 6 · U 14 | E1 9 · M 6 · U 13 |
| Pinned Noir checks | S | U 9 | U 9 | U 7 | U 5 | U 30 | U 28 |
| Slither 0.11.6 | G | U 9 | E1 9 | U 7 | E1 4 · M 1 | E1 13 · M 1 · U 16 | E1 12 · M 1 · U 15 |
| Slither 0.11.6 | S | U 9 | U 9 | U 7 | U 5 | U 30 | U 28 |
| Mythril 0.24.8 | G / S | U 9 | R 9 | U 7 | R 5 | U 16 · R 14 | U 15 · R 13 |
| Foundry 1.8.6, G1/G2/G4/G5 | G | R 9 | D 3 · M 6 | R 7 | R 5 | D 3 · M 6 · R 21 | D 3 · M 5 · R 20 |
| Foundry 1.8.6, handwritten policy | S | R 9 | **D 8 · M 1** | R 7 | R 5 | D 8 · M 1 · R 21 | D 7 · M 1 · R 20 |
| Echidna 2.3.3 | G / S | R 9 | R 9 | R 7 | R 5 | R 30 | R 28 |
| CCC-Check; Picus | G | U 9 | U 9 | U 7 | U 5 | U 30 | U 28 |
| SmartAxe | G | U 9 | R 9 | U 7 | U 5 | U 21 · R 9 | U 20 · R 8 |
| **BindCheck v1.1**, own adjudication (D1P-34) | — | D 6 · U 3 | **D 5 · U 4** | D 3 · U 4 | D 2 · U 3 | **D 16 · U 14** | D 14 · U 14 |
| **BindCheck v1.1**, rescored on the baseline scale | — | D 6 · M 3 | D 5 · M 3 · U 1 | D 3 · M 4 | D 2 · M 3 | D 16 · M 13 · U 1 | D 14 · M 13 · U 1 |

The two scales differ on purpose, so we show both. On the baselines' scale,
U means the tool cannot accept the input, and a completed applicable run
without a detection is M. BindCheck's own adjudication marks a completed run
as unsupported when the mutant's broken binding lies outside its model. The
last row applies the baselines' scale to BindCheck. Its 13 completed runs
without a related warning become M, and only WT-S04, where no verifier
boundary was found, stays U. No per-mutant outcome changes between the two
rows.

**The policy harness is stronger on WarpToad consumer mutants.** On the nine
WarpToad consumer mutants, the handwritten Foundry same-policy harness
detects eight (S01, S02, S03, S04, S05, S07, S08, S09). BindCheck detects
five (S01, S02, S03, S06, S09). The harness finds the swapped checks, the
misordered words and the misdirected beneficiary, which BindCheck cannot
model. It also finds the removed verifier gate, on which BindCheck's
extractor fails closed. The harness misses WT-S06, the unbound fee, because
its frozen property has no maximum-fee ceiling. Its cost and limits:
- 156 nonblank lines of shared Solidity, 18 lines of configuration, and
  about 0.16 h of authoring;
- WarpToad's policy encoded by hand, AI-authored, with no human inspection
  recorded;
- a relational stub verifier that checks the eleven expected public words,
  so its counterexamples are E1 property violations, not real-proof
  executions;
- no harness for Payy or for any circuit mutant, so those 21 cells are
  unresolved.

**BindCheck is complementary, not dominant.**
- *No per-application policy.* The same rules and loaders run on both
  applications.
- *Circuit-side coverage.* BindCheck detects 9 of the 16 circuit mutants.
  No Solidity baseline and no fuzzing arm reaches any of them: every cell
  is U or R. The policy harness cannot reach them by construction, because
  its stub replaces the circuit.
- *WT-S06.* BindCheck catches the fee mutant that the policy harness
  misses.

Where someone has written the policy, a same-policy harness is the better
tool for consumer-side mutants of this kind.

**Lint is localized E1, never a mismatch description.** Noir earned 10 E1
cells by naming an unused value at the mutant locus (WT-C01, C02, C03, C04,
C07, C08; PY-C02, C04, C05, C06). Slither earned 13 through naming, boolean,
reentrancy or uninitialized-state reports that name the seeded variable or
function (every WarpToad consumer mutant and PY-S02–S05). Some of these
warnings do not discriminate. None relates producer enforcement to a
consumer effect (D1P-32). The generic Foundry invariants detect three
mutants: the two nullifier-accounting mutants and the removed gate. The G4
supply invariant never fired.

**Failures are reported as failures.** Every Mythril run on the 14 consumer
mutants is unresolved at the 1,800 s cap. The sequential, isolated retry on
the case targets ended in an outer kill (Payy earlier), a `SIGSEGV` at
30.22 s (WarpToad pinned), or the internal cap with only generic warnings.
No Mythril output localized a seeded binding. All nine Echidna 2.3.3
attempts stopped before fuzzing. Its combined-JSON loader rejected the
unlinked `LazyIMT` library, and the first full-source attempt rejected
`GigaBridge`. These runs are unresolved, not misses. CCC-Check, Picus and
SmartAxe keep their D1P-22 dispositions, and no adapter was introduced.

**Answer to RQ3 (benchmark).** No generic circuit-only or contract-only tool
described a proof-to-execution mismatch on any mutant. Their signals are
localized lint (Noir 10, Slither 13) or unresolved runs (Mythril, Echidna).
A handwritten same-policy fuzz harness detects more WarpToad consumer
mutants than BindCheck (8/9 against 5/9), and BindCheck catches the one it
misses. BindCheck alone covers circuit-side mutants (9/16) and needs no
per-application policy. All of this is development evidence on exposed
families.

### F. RQ4 — Held-out scan

**Frame.** RQ4 uses the mini-draw of §IV-D: eight candidate Noir/EVM project
groups listed from names and URLs only. The custodian reserved four of them.
This is a disclosed, smaller frame than the frozen v0.2.0 plan, which calls
for full index traversal, and we report it as such. Any transfer claim from
RQ4 is bounded by four projects drawn from one search, not a sample of the
ecosystem.

**Protocol (D1P-33).** The tool was frozen at exact commit `4382ee6…`, tag
`bindcheck-v1.1`. Each reserved project was handled as follows:
- it was pinned to a full commit, with recursive submodules recorded;
- it was built locally with the project's own toolchain pins where they
  exist;
- it was analyzed with exactly one frozen `bindcheck analyze` invocation.

After the run, all 60 tracked files under `src/` and `protocols/`,
including the effect table, were byte-identical to the tag. The focused
suite passed 11/11, after a preserved first attempt that failed to import
because `PYTHONPATH` was unset. No rule, decoder, frontend, protocol or
effect model changed. No maintainer was contacted, and no live-chain action
took place (D1P-33 §§1–3).

*Table 9: Held-out results with frozen v1.1 (D1P-33 §§1, 4). Project names
are given because no finding exists; whether to keep them in the submission
is Open item 11.*

| Project (pinned commit) | Reserved | Prior exposure | Producer / consumer stack | Local build | Supported by v1.1 | Consumer relation | Warnings | Adjudication | Highest level | Rule changes | Disclosure status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NullProof (`79156bc9…`) | Yes | Name and URL only | Noir `1.0.0-beta.19` / Solidity 0.8.33 (`ComplianceGate`) | Circuit and contracts compile | No: `unsupported Noir compiler` (beta.19) | Not reached | 0 | n/a | — | 0 | Nothing to disclose |
| privacy-preserving-IP-NFT (`6ed03661…`) | Yes | Name and URL only | Noir `1.0.0-beta.3`, a fallback evidenced by adjacent Noir JS dependencies (the project declares only `>=0.31.0`) / Solidity 0.8.30 (no project pin) | Circuit compiles with the beta.3 fallback; contracts compile with tests and scripts skipped | No: `unsupported Noir compiler` (beta.3) | Not reached | 0 | n/a | — | 0 | Nothing to disclose |
| zkt-research (`166b3c30…`) | Yes | Name and URL only | Noir `1.0.0-beta.21` / Solidity 0.8.31 (`ZKTCore`) | Circuit and contracts compile. The rebuilt artifact differs from the committed one, and the checked-in `HonkVerifier.sol` is a stub that returns false | No: `unsupported Noir compiler` (beta.21) | Not reached | 0 | n/a | — | 0 | Nothing to disclose |
| ZKPassport circuits (`818e7a7e…`, `outer_count_4`) | Yes | Name and URL only | Noir `1.0.0-beta.22` / Solidity 0.8.30 (`SubVerifier`) | Circuit and contracts compile | No: `RecursiveAggregation` | Not reached | 0 | n/a | — | 0 | Nothing to disclose |

*Table 10: Held-out funnel totals (D1P-33).*

| Stage | Projects | Notes |
| --- | --- | --- |
| Candidate frame (names and URLs only) | 8 | Stratum `noir-evm:eligible`; AI-prepared list; none in the 0xPARC tracker |
| Reserved (custodian draw) | 4 | Commitment `514ad719…`; D1P-33 records no check of the opening against it |
| Retrieved and pinned | 4 | Full commits and recursive submodules |
| Built locally | 4 | IP-NFT only through an evidenced compiler fallback and a contracts-only route; zkt-research without a complete generated verifier pairing in the checkout |
| Supported by v1.1 | 0 | 3 stopped at the exact Noir version gate (beta.19, beta.3, beta.21); 1 at `RecursiveAggregation` (beta.22) |
| Analyzed to completion | 0 | — |
| With ≥1 warning | 0 | — |
| Validated | 0 | No warning to validate; no `bindcheck validate` run |

Stages are monotone. An unsupported project explains attrition and is never
counted as a miss or as safe.

**Answer to RQ4.** With the tool frozen, BindCheck v1.1 supported none of
the four reserved projects: 0 supported, 4 unsupported, 0 warnings and 0
validations. Three stopped at the exact compiler-version gate of the
producer frontend (Noir beta.19, beta.3 and beta.21). The fourth uses a
supported version (beta.22) but contains recursive verification, which the
decoder rejects by name. The result is a capability limitation. v1.1's two
version-keyed decoders do not reach the compiler versions these projects
use, and no held-out consumer reached the AST frontend. The scan measures
neither false negatives nor warning precision nor validation transfer,
because no analysis completed. Transfer of the rules remains untested.

**Pending: a version-only change and a rescan.**
- **D1P-35 [PENDING D1P-35].** BindCheck v1.2 changes only compiler-version
  support in the producer frontend. No rule, consumer-lowering step, effect
  model or validation route changes. In particular, R-ANCHOR stays
  unreachable and the location defects of §V-G stay unfixed (§V-F;
  §VII-H).
- **D1P-36 [PENDING D1P-36].** v1.2 rescans the four reserved projects and
  scans four unseen, non-reserved projects once each.

A version-only change cannot help the ZKPassport route, which fails on
recursive aggregation, not on its version. It also cannot supply
zkt-research's missing verifier pairing. Tables 9 and 10 will gain v1.2
rows, and the v1.1 rows above stay unchanged.

**Disclosure for the rescan (pre-written for D1P-36).** The D1P-36 rescan of
the reserved projects is not a first, blind held-out attempt. It follows a
tool change made *after* the first attempt (D1P-33) failed at the compiler
version gate on three of the four reserved projects. The change was
motivated by that failure, and the versions it adds
**[PENDING D1P-35: list]** were chosen knowing which versions the reserved
projects use. The change is confined to version support. No rule, consumer
lowering, effect model or validation route changed, and v1.2 was frozen by
hash before the rescan. The analysis lane had also already retrieved and
built the reserved projects, and the D1P-33 report describes their consumer
boundaries. It had seen no warning on them, because none was emitted. We
therefore report two strata and never pool them:
1. the four reserved projects, labeled *held out, second attempt after a
   version-only change made in response to the first attempt*;
2. the four unseen, non-reserved projects, which are first attempts, with
   their selection procedure frozen before any of them was inspected
   **[PENDING D1P-36: procedure]**.

Only the second stratum is a first-attempt transfer result. Any change
beyond version support would end the reserved projects' held-out status.

### G. RQ5 — Taxonomy

**Status: AI-assisted extraction, pending human labels.** A blind labeling
sheet with the AI labels and include tags removed has been prepared for the
human annotators ([`v1-blind-labels.md`](../docs/taxonomy/v1-blind-labels.md));
its one-line summaries are still AI-written. Every number below
comes from the seed-only v1 corpus (§IV-D). Relevance decisions were made by
an AI agent, and every cause label is AI-suggested, recorded as `ASSUMED`,
with the `human_label` field empty. These are not annotation data. Under
contract §10 they cannot support a frequency or recurrence claim until human
annotators label the findings and agreement is measured.

*Table 11: Disclosure funnel (v1 corpus; AI screening, one seed endpoint).*

| Stage | Count | Unit |
| --- | --- | --- |
| Endpoints traversed | 1 of 17 (0xPARC zk-bug-tracker, commit `56a99667…`) | endpoints |
| Raw retrieval hits | 27 | entries |
| Unique source records | 1 | documents |
| Candidate findings (before deduplication) | 27 | findings |
| Canonical findings (duplicates) | 27 (0) | findings |
| Included / excluded / unresolved (AI screening) | 19 / 8 / 0 | findings |
| Families touched (all logged as exposed) | 23 | families |
| Families represented among included findings | 15 | families |

The eight exclusions and their recorded reasons are: a pure circuit-library
gap with no evidenced consumer; a verifier soundness break and a
trusted-setup compromise (both out of scope by contract §5.4); two
proof-protocol or proof-system soundness flaws; a privacy leak with no
execution effect; a library availability bug; and a consumer concurrency bug
with no proof/consumer disagreement.

*Table 12: AI-suggested cause labels over the 19 included findings (one
label per finding; human labels pending).*

| Cause | Findings | Families | Example (corpus ID) | Human label |
| --- | --- | --- | --- | --- |
| `C_REPRESENTATION` | 7 | 7 | CF-01, out-of-range moves accepted (Dark Forest) | pending |
| `C_RELATION_GAP` | 5 | 5 | CF-03, range-check outputs never constrained (circom-pairing) | pending |
| `C_ACTIVATION_EXTENT` | 3 | 3 | CF-10, votes applied to wrong keys (MACI) | pending |
| `C_OCCURRENCE_ACCOUNTING` | 2 | 2 | CF-06, one note yields many nullifiers (Aztec 2.0) | pending |
| `C_CONTEXT_IDENTITY` | 1 | 1 | CF-22, context aliasing (Polygon zkEVM) | pending |
| `C_FIELD_MAPPING` | 1 | 1 | CF-21, unconstrained path bit (Polygon zkEVM) | pending |
| `C_VERIFICATION_CONFIG`, `C_DISCHARGE_TRANSFORMATION`, `C_OTHER_BINDING` | 0 | 0 | — | pending |
| Consequence (`K_*`) and attacker-role (`A_*`) labels | not extracted | — | — | pending |

The protocol records each label as present, absent or uncertain, and
findings may carry several. The corpus has one suggested primary cause per
finding and no consequence or role labels. Table 12 is therefore not the
protocol's label-frequency table. Some inclusions need human review against
the inclusion rule of §IV-A, which excludes pure circuit bugs unless the two
sides disagree. Examples are zkEVM opcode-circuit gaps (CF-15, CF-16, CF-20)
and a circuit-library range check (CF-03).

*Table 13: Inter-annotator agreement.*

| Field / label | Comparable n | Positives / negatives | Raw agreement | Coefficient (κ or α) | 95% interval | Missing / null |
| --- | --- | --- | --- | --- | --- | --- |
| All fields | — | — | — | — | — | No annotation round has run (ledger `annotation_rounds` empty); pending human labels |

*Table 14: Tool funnel for included findings (separate denominator).*

| Stage | Findings | Families | Main attrition reasons |
| --- | --- | --- | --- |
| Artifacts available | 0 (not attempted) | 0 | Tool funnel not run for the v1 corpus |
| Supported by BindCheck v1.1 | 0 (not attempted) | 0 | No corpus application lists a Noir producer (10 of 23 list Circom). None would pass v1.1's Noir beta.14/beta.22 gate |
| Cause covered by a v1.1 rule (§IV-C) | not assessed | — | — |

The second row's attrition reason comes from the ledger's `producer_stack`
fields. It is an expectation, not a measurement. The same observation is why
the held-out frame (§VII-F) was drawn from Noir/EVM projects rather than
from the corpus.

**Answer to RQ5.** No answer is supported yet. In the seed extraction the
AI suggestions used no `C_OTHER_BINDING` label and were dominated by
representation and relation-gap mechanisms. Relation gaps are the cause that
R-BIND targets, but none of the corpus systems is analyzable by v1.1. These
are observations about AI suggestions, not findings. Whether these
mechanisms *recur across independent families*, and how reliably people
label them, awaits human labels, the remaining endpoints, and the agreement
study.

### H. Threats to validity

**Development bias.** The rules were designed after the three case studies
were known. Payy's defect, advisory and end-to-end artifact predate the
rules. WarpToad was screened and inspected in D1-02, D1P-11 and later tasks.
The benchmark mutates the same two applications. RQ1 and RQ2 therefore show
capability *on these applications* only (contract §9). Transfer rests on
RQ4 alone.

**v1.1 was revised after seeing the benchmark.** D1P-34 kept the 30 mutants
and their ground truth unchanged and froze the tool by hash before
rerunning them. However, it was developed after D1P-31's per-mutant results
were known, including the PY-S02 miss and the unsupported Payy mutants. The
improvement from 13 to 16 detections is therefore in-sample. It shows that
the revised design covers those mutants, not that it would have found them
blind.

**Structural loaders, narrow exposure.** v1.1 removes the name- and
regex-based consumer profile. Its AST frontend, however, has been run on one
consumer family (Payy). The WarpToad relations come from a route-A
extractor developed on WarpToad's `mint` fragment. How the frontend behaves
on an unseen consumer is untested until RQ4.

**Occurrence is not correct binding.** R-BIND treats one proof-enforced
occurrence as sufficient, and R-CONSUMER treats one guard, state or effect
use as sufficient. A detection shows that a word has no such use. A
non-detection may hide a weak or wrong binding, which is the main reason for
the 14 unsupported mutants.

**Validation provenance.** Every D1P-30 E4 replays a witness construction
that people designed before D1P-30. The Lane X harnesses need no manual
steps at run time. They are written per application, however, and their
WarpToad plans match WarpToad word names. They were written by the same
AI-assisted lane as the benchmark, with the ground truth available, and the
v1.1 plans were revised after the v1.1 warnings were known. The Payy
consumer rows use a mock verifier and check no producer assignment.

**R-ANCHOR is unreachable.** In v1.1, and in the planned version-only v1.2,
both consumer loaders record an anchor only after finding a guarded storage
lookup. The root-specific R-ANCHOR rule therefore cannot fire (§V-F).
Removed root guards are still reported, through R-CONSUMER, but a root
whose guard is present with the wrong direction or the wrong map is not.
We defer the fix until after the transfer test. Changing a rule between the
first held-out attempt and the rescan would be held-out tuning (contract
§9).

**The repaired-control warning.** The only warning on the repaired Payy
control is R-CONSUMER on `commit_hash`, whose consumer check
`verifyCommitHash` is an empty placeholder (`RollupV1.sol:381–382`). The
structural observation is true: the authenticated word reaches no on-chain
check. Whether it is a defect depends on the intended off-chain
data-availability check, and adjudication is pending. Until then, we report
one of two controls as carrying a warning, and we count that warning
neither as a detection nor as a false alarm.

**Injected cases and benchmark.** M-DOM and M-SRC are injected. M-DOM is
grounded in an unused in-tree package and a developer warning, M-SRC in
documented reliance. Neither indicates a defect in pinned WarpToad. The
benchmark was built in parallel with D1P-30 by an AI-assisted lane. Its
operators share mechanisms with the cases. Its predicted effects are mostly
unexecuted outside the harness rows. Its Payy mutants sit on the
faulty revision.

**Admitted state.** The M-DOM differential uses privileged synthetic root
admission (`S_DOM`). The WarpToad
harness's WT-S02 run uses a mock provider that
admits the plan's giga root by construction. Neither variant demonstrates
cross-chain reachability.

**Baselines.** The only same-policy harness covers WarpToad. It was
AI-authored, with no human inspection recorded, and uses a stub verifier.
No Payy or circuit-mutant harness was written after the results were seen,
so those cells stay unresolved (D1P-32). BindCheck's own scale and the
baselines' scale differ, so Table 8 shows BindCheck under both.

**Held-out frame and rescan.** The reserved frame has eight candidates
from one AI-prepared search, of which four were reserved. Its commitment
shows consistency, not randomness or timing, and the custodian's signature
is not yet added (§IV-D). The first scan supported none of the four. The
planned rescan follows a version-only change that was made because of
that failure, after the analysis lane had built the projects. Its results
on the reserved projects will be labeled as second attempts (§VII-F).

**Taxonomy.** The corpus covers one seed endpoint. Its relevance decisions
and labels are AI-made, and its extraction deviated from the metadata-only
access rule (§IV-D).

**Negatives.** No fixture is a proven negative control. We report adjudicated
counts, not false-positive rates.

**AI involvement.** AI agents did all of the following:
- implemented the code;
- ran D1P-22, D1P-30, D1P-31, D1P-32, D1P-34 and the D1P-33 held-out scan;
- built the benchmark, the validation harnesses (including TC02) and the
  Foundry policy harness;
- extracted the taxonomy seed corpus and prepared the held-out candidate
  list;
- wrote the B02 obligations and drafted this text (§X-B).

AI output is not independent annotation (contract §10). Final taxonomy
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
  both Payy revisions (D1P-22). On the benchmark it named an unused value at
  the mutant locus on 10 of 30 mutants, as E1 lint (D1P-32). Lane X's
  synthetic probe found the same
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
was lint at a defect location, and Mythril did not complete (D1P-22, D1P-32).
In a same-policy arm, a fuzzer could check `σ`, but it needs a valid proof
for every input it explores. Seeded only with honest proofs (baselines
§3.1), it cannot produce a proof of a forged statement. In our own Payy
work, the consumer-side test exercised the forged effect only because we
supplied a hand-built forged proof (T18). D1P-32's WarpToad harness avoids
this obstacle by replacing the verifier with a relational stub that accepts
any call carrying the expected public words. With that stub it detected 8 of
9 consumer mutants. The same stub removes the circuit from the analysis, so
the harness cannot reach circuit-side mutants, and its counterexamples are
E1 rather than real-proof executions (§VII-E).

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

**Fragment.** v1.1 accepts Noir `1.0.0-beta.14` and `1.0.0-beta.22`
artifacts only. Consumer facts come from a checked relation: a v1.1 AST
relation, or a route-A relation for WarpToad. The AST frontend supports a
bounded statement and expression subset, one verifier boundary per
consumer, and standard token calls matched by function type. The route-A
extractor supports one entry point's reachable constructs with OpenZeppelin
5.6.1 effects. Neither handles proxies, delegate calls, inline assembly or
reentrancy, and both assume standard atomic ERC-20 behavior. Unsupported
inputs stop with a named reason. That keeps results honest but bounds
applicability. On the benchmark, 14 of 30 mutants were unsupported
(§VII-C). On the four reserved held-out projects, all four were
unsupported: three at the compiler-version gate and one at recursive
aggregation (§VII-F).

**Occurrence is not correct binding.** R-BIND treats one proof-enforced
occurrence as sufficient. It misses a public input that is used but bound
to the wrong value, used only on an inactive branch, or absorbed by a weak
construction. It can warn on deliberately unconstrained metadata.
Similarly, R-CONSUMER is satisfied by any guard, state or effect use, and
admission is recorded without checking the direction of the storage lookup
(§V-E). A root checked against the wrong map or with the wrong sign is
therefore not reported.

**R-CONSUMER does not infer intended role.** R-CONSUMER reports that an
authenticated calldata word reaches no guard, state or modeled effect. It
does not say whether the word should have been a root to admit, a key to
spend or an amount to transfer, and its suggested fix is generic (D1P-34
§7). Consumer-supplied configuration and environment words are exempt, so a
missing use of such a word is not reported. v1's root-specific R-ANCHOR
remains in the code but cannot fire under v1.1's loaders, and its fix is
deferred until after the transfer test (§V-F).

**Loop widening.** The AST frontend widens a loop-carried index to the whole
tail of the public array from its known lower bound. This is a conservative
dependency slice, not exact Solidity path equivalence (D1P-34 §2). On Payy,
every message word is treated as reaching every effect inside the message
loop. That over-approximation can mask an unused word in such a loop, since
the word counts as used, and it blurs which effect depends on which word.

**Selector-prefix inference.** When the producer has more public leaves
than the verifier's direct array, the frontend infers a prefix width from
the largest public ABI array and the array-header bound seen in the AST. For
Payy, this gives the two-word recursive-verifier selector prefix and places
every word correctly (D1P-34 §2). The inference is a width check. It is not
a proof of the recursive verifier's semantics, and it assumes that the
direct array consists of a header followed by the largest public array.

**Localization.** WarpToad consumer-side warnings carry no source line
(`WarpToadCore.sol:?`), because route-A relations do not record the
verifier call's line. R-EFFECT reports the first modeled effect, which on
Payy is an unrelated write (§V-G). Producer warnings are not mapped to Noir
source spans.

**Hash semantics.** Poseidon2 is modeled at most as a functional
uninterpreted tuple function (equal inputs give equal outputs), with no
injectivity or collision resistance (D1P-19 §2.2). v1.1 does not reason
about hash semantics at all. Validation uses real hashes. Any conditional
no-collision argument (B02 §3) is outside this paper's results.

**Conditional binding.** v1.1 has no activation-condition reasoning. Payy's
tail is caught because the tail words have no proof-enforced occurrence in
the full-size earlier artifact. A variant that constrains tail words under a
witness-controlled predicate would be counted as used. Earlier ACIR and SMT
work on this pattern produced an analyzer false positive from unsound probe
specialization (later repaired) and general queries that did not finish
(T22, T22-v3, T22-v4).

**Validation coverage.** D1P-30's E4 results replay witness constructions
designed before D1P-30. The Lane X harnesses run without manual steps but
are written per application. Only WarpToad has a full warning-to-E4 path.
Payy has a mock-verifier consumer harness and a one-mutant real-proof
circuit harness (TC02), and no Payy warning has reached E4. Of the 53 v1.1
benchmark warnings, 32 remain at E1. A new application needs its own
harness before any of its warnings can be validated. Validation covers one
consumer call from a fixed admitted pre-state, or a replay in a second
call. Multi-transaction histories, front-running and observation of honest
proofs are out of scope (B02 §3.1).

**Same-policy arm for WarpToad only.** D1P-32's same-policy Foundry harness
covers WarpToad's consumer and case targets. It is handwritten,
AI-authored, uses a stub verifier, and yields E1 counterexamples. No
same-policy harness exists for Payy or for circuit mutants. Those cells are
unresolved, so the comparison cannot show how a same-policy baseline would
do there.

**Held-out coverage; AI-assisted taxonomy.** The reserved frame has four
projects from one AI-prepared search, smaller than the frozen plan, and the
frozen tool supported none of them. The binding constraint is the
producer frontend's exact compiler-version gate. The
taxonomy corpus covers one seed endpoint, and its relevance decisions and
labels are AI-made, pending human labels (§IV-D).

**No safety claims.** BindCheck never returns `VERIFIED_WITHIN_SCOPE` from
rule silence. Absence of warnings is E0 within the supported scope.

**Not novel by itself.** Integration-layer failures [1], rich circuit
specifications [3, 4] and computation–constraint consistency [5] are prior
work. Unused-variable lint already flags some unused public inputs (D1P-22,
D1P-32). A handwritten policy harness catches more consumer-side mutants on
WarpToad (D1P-32). Our claim is limited to joining both sides into rules
that state the cross-component reason without a per-application policy,
and validating them, to the extent that RQ1–RQ4 support it.

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
  deadline, as the CFP requires [8]. D1P-33 emitted no warning, so there
  was nothing to disclose and no maintainer was contacted. Any candidate
  from D1P-36 follows the same procedure **[PENDING D1P-36]**.
- **New tool.** BindCheck's validation routes produce working forged proofs
  against local deployments. Misuse risk: an attacker could use validated
  warnings against live systems. Mitigations: validation runs only on
  owned-local chains with fresh deployments. The Lane X harnesses
  do synthesize attack witnesses and forged proofs. They do so only for our
  two development applications (WarpToad, and one Payy mutant in TC02) and
  only against fresh local deployments. The Payy consumer harness uses a
  mock verifier. The planned artifact omits automation for
  live-network submission **[TODO: authors confirm]**, and whether to
  release the harnesses at all is **[TODO: authors decide]**. Held-out
  findings are released only after disclosure. The benefit is that developers can find and fix
  binding failures before deployment, the same capability attackers already
  apply by hand.
- **Human subjects.** The taxonomy study uses public disclosures, and its
  annotators are research staff labeling documents. Whether this requires
  IRB review is **[TODO]** for the authors' institution.

### B. Generative-AI disclosure

AI agents wrote code, task reports, the B02 obligations, screening notes and
draft text. AI use is therefore integral to the methodology and is
described explicitly, as the CFP requires [8]. An AI agent screened the
taxonomy seed corpus and suggested its cause labels. Those suggestions are
recorded as `ASSUMED` and are not annotation. AI systems are excluded from
final taxonomy labeling and adjudication. An AI planner also prepared the
held-out candidate list from names and URLs only. A human custodian
performed the draw outside every agent session. AI agents also wrote
BindCheck v1.1 (D1P-34), the validation harnesses (including TC02) and the
D1P-32 Foundry policy harness, and they ran the D1P-33 held-out scan. D1P-32 records no human inspection of that harness.
Authors inspect every claim, citation, label and result. **[TODO]** Write the disclosure from the preserved task
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
pair, not of either component. BindCheck v1.1 makes part of this agreement
checkable without application identifiers. It counts proof-enforced uses of
each public input. It lowers the consumer's compiler AST from the verifier's
interface type to guards, state writes and token effects. It then applies
four generic rules. On five development targets, v1.1 warned at the
expected public word on the producer-side defects in historical Payy and
injected M-DOM, and on the consumer-side defect in injected M-SRC. It
emitted no warning on pinned WarpToad and one open consumer-side warning on
the repaired Payy control. All three mismatches reached end-to-end
validation in D1P-30. On 30 mutants of the same two applications, v1.1
detected 16, with 14 outside its supported scope and no misses. Each
detection named the broken binding. A handwritten same-policy harness does
better on WarpToad consumer mutants (8/9 against 5/9). BindCheck covers the
circuit-side mutants that no Solidity baseline reaches, needs no
per-application policy, and catches the one consumer mutant the harness
misses. Per-application validation harnesses took every WarpToad warning to at
least E3 and nine to E4. No Payy warning has reached E4. These are
development results. On the four reserved held-out projects, the frozen
tool supported none: three stopped at its compiler-version gate and one at
recursive aggregation, so transfer is untested. Still to come are a
version-only v1.2, a rescan that adds four unseen projects
[PENDING D1P-35, D1P-36], and human taxonomy labels.

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
| Route-A consumer extraction, 22 families, fail-closed | D1P-16; D1P-18 | Mechanically checked on fragment |
| M-SRC extraction removes exactly K2 | D1P-21B §3 | Mechanically checked |
| v1.1 design: AST lowering, structural identities, no application identifiers | D1P-34 §2; `solidity_ast_v1_1.py`; identifier-absence test | Implementation, frozen by hash; committed bytes match the manifest |
| Corrected occurrence roles; full-size Payy leaves | D1P-34 §3 | Tool output |
| v1.1 warnings on the five development targets | D1P-34 §4; ignored analysis outputs | Tool output (E1), development |
| Fresh E4 on M-DOM and M-SRC through registered routes (v1 warnings) | D1P-30 §§5.1–5.2; validation index | Locally reproduced (injected), tool-driven route |
| Preserved E4 audit for Payy (v1 warning, N=8 build) | D1P-30 §5.3 | Automatic audit of preserved evidence |
| Benchmark: 16/30 detected, 14 unsupported, 0 missed; 53 warnings (20 related, 33 inherited) | D1P-34 §§1, 5 | Tool output (E1) with post-run adjudication, development |
| Benchmark index validation: 1 preserved E4, 52 E1 | D1P-34 §5.1 | Automatic audit of preserved evidence; no new proof |
| Validation of 53 v1.1 warnings: 8 E4, 1 preserved E4, 6 E3, 6 mock-verifier E2, 32 E1 | AUTO-VALIDATE (v1.1 table); ignored `results/raw/X-AV/v11/` | Locally reproduced (injected), per-application harnesses; E4 on WarpToad only |
| PY-C02 real aggregation proof accepted by the mutant, rejected by the pristine circuit | TC02; ignored `results/raw/TC02/` | Locally reproduced (injected), E3 |
| Held-out scan: 4 reserved projects, 0 supported, 0 warnings; frozen files unchanged | D1P-33; ignored `results/raw/D1P-33/manifest.json` | Tool output under freeze; capability limitation |
| Benchmark baselines, including the Foundry same-policy harness and the Mythril retry | D1P-32; ignored `results/raw/D1P-32/` | Tool output, scored under the frozen plan |
| Baselines on the case targets | D1P-22 record; ignored `results/raw/D1P-22/` | Tool output, scored under the preregistered plan |
| v1 history: 13/30, 16 unsupported, 1 miss | D1P-31 §§1, 4 | Tool output, superseded |
| 30 mutants compile; reachability checks | BENCHMARK.md §§3–4; `manifest.json` | Build observation (development) |
| Contract revision 3 | D1P-31 §2; contract change log | Controlling document |
| Taxonomy seed corpus (27 screened, 19 included, 15 families) | v1-corpus.md; v1-corpus-ledger.json | AI-assisted extraction; human labels pending |
| Held-out mini-draw commitment (8 candidates) | reservation-commitment-2026-10-28.json | Custodian-reported; signature pending |
| Version-only v1.2, rescan plus four unseen projects, human labels | — | [PENDING D1P-35, D1P-36] |

---

## Open items for authors

1. **R-ANCHOR is unreachable** in v1.1 and v1.2 (§V-F). The fix is deferred
   until after D1P-36. Then decide whether to remove the rule or make
   admission direction-sensitive, and rerun the development evaluation.
2. **Lost source lines.** WarpToad R-CONSUMER and R-POLARITY warnings print
   `WarpToadCore.sol:?`, and Payy R-EFFECT points to a first-effect position
   such as `RollupV1.sol:850` (§V-G). These are also deferred, because the
   fix is a tool change. Note that any held-out warning in D1P-36 will carry
   the same defects.
3. **Payy E4.** No Payy warning has reached E4. TC02's recommended next
   step deploys the real mutant verifier and the pinned consumer, then
   submits the verified block with validator signatures.
4. **Reservation.** Record a check that the four D1P-33 projects match the
   commitment opening (`514ad719…`), and add the custodian's signature.
5. **D1P-35/36 records.** Record the exact versions v1.2 adds and freeze it
   by hash before the rescan. Freeze the selection procedure for the four
   unseen, non-reserved projects before inspecting any of them. Report the
   two strata separately, as pre-written in §VII-F.
6. **The `commit_hash` warning.** Adjudicate R-CONSUMER on Payy's
   `commit_hash` (empty `verifyCommitHash` placeholder).
7. **Mock-verifier grade.** The lane's "E2, mock-verifier-scoped" label does
   not meet the contract's E2 wording, because no producer assignment is
   checked (§V-H). Decide on a separate label before submission.
8. **Taxonomy.**
   - The metadata-only access rule was not followed for the seed endpoint.
     The custodian-sanitized flow is owed before any annotation round.
   - A blind labeling sheet now hides the AI labels, but its one-line
     summaries are AI-written. Decide whether that is acceptable.
   - Several AI inclusions need checking against the pure-circuit exclusion
     (§VII-G).
9. **Policy harness review.** The Foundry same-policy harness has no recorded
   human inspection. A human should review it before the comparison is
   published.
10. **Citations.** CIVER and CCC-Check full texts remain unread. Supply
    copies and resolve each **[TODO-VERIFY]**.
11. Draw Figure 1. Replace repository links with an anonymized artifact.
    Decide whether the held-out project names stay in Table 9.
12. Have a human author inspect every claim and citation (contract §10).

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

