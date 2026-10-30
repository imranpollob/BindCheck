# BindCheck: Finding Proof-to-Execution Binding Failures at the Circuit–Consumer Boundary

*(Working title; frozen at abstract registration.)*

**Draft status:** D1P-P07 revision, 30 October 2026, on repository base
`55d7da7` (`main`). Target format: IEEE S&P (13 pages of text plus up to 5
pages of references and appendices). The paper is organized around three
claims, *correctness*, *novelty* and *generality* (§I-D; §VII-C to §VII-E).
Each claim carries pending markers naming the lane whose work it awaits.
This revision adds the following.

- **Correctness audit ([D1P-40](../reports/D1P-40-correctness-audit.md)).**
  - *Repairs:* five confirmed extraction defects, repaired in prospective
    BindCheck v1.3.
  - *Benchmark:* the rerun changes 16 detected / 14 unsupported / 0 missed
    to **11 / 19 / 0**.
  - *Payy:* all 12 Payy mutants now stop at an unverified public-input
    mapping, and the real Payy message-tail bug is **`UNKNOWN` for the
    static analyzer**. Real-proof validation of that bug (T15–T19, TE04) is
    unaffected.
- **Novelty ablation ([D1P-41](../reports/D1P-41-ablation-preliminary.md)).**
  - The unjoined union of producer-only and consumer-only arms detects
    exactly what full BindCheck detects (6/8 each).
  - ZKAP already covers unused public inputs.
  - Novelty is therefore claimed only for the automated circuit-to-consumer
    join.
- **Evidence ledger ([EVIDENCE-LEDGER](../docs/x-experiment/EVIDENCE-LEDGER.md);
  [TE05](../reports/TE05.md)).**
  - Repair contrasts now support every WarpToad E4.
  - WT-S02's original run was a setup artifact. A corrected experiment
    isolates the defect.
  - PY-C02's own mutation reaches E3, and its effect warning is contained.
  - Mock-verifier rows are graded `E1+mock`.
- **Taxonomy human labels ([v1-agreement](../docs/taxonomy/v1-agreement.md)).**
  One human annotator labeled the corpus, with AI assistance for reading
  the sources (disclosed). Agreement *with the AI suggestions* is κ 0.83
  for inclusion and κ 0.35 for cause. A precedence rule in the labeling
  instructions is a threat to validity.
- **Milestone 2 is pending [PENDING AI 1, M2].** It covers path-conditional
  binding and role correspondence.
- **Protocol v2.** The
  [independent-evaluation protocol](../docs/evaluation/independent-protocol-v2.md)
  is finalized for approval. Its SHA-256 is `cd80f5f7…`, and the approval
  block is empty.

No experiment was run for this draft. Claims about cited work that could not
be checked against a primary source stay **[TODO-VERIFY]**. Earlier drafts
(D1P-D01/D03, D1P-P01–P06) are in Git history.

**Pending markers (lane key).** A marker means the claim is not supported
until that lane's work exists. The AI 2 assignment is an inference: D1P-41's
ablation is consistent with it, but the authors **must confirm** it.

| Marker | Lane | Work the marker waits for |
| --- | --- | --- |
| **[PENDING AI 1]** | Development and fact audit | A freeze of the corrected tool. Payy implementation-fact certificate (mapping and dynamic memory, D1P-40 §8). Rerun of the five case targets under v1.3. Development on the protocol-v2 pool |
| **[PENDING AI 1, M2]** | Development, Milestone 2 | Path-conditional binding and role correspondence. This is the "typed, policy-bearing boundary correspondence" of D1P-41 §1, needed for WT-S05, WT-C05 and Payy's conditional tail |
| **[PENDING AI 2]** | Novelty comparison (*assumed*) | Final ablation on the frozen corrected tool (D1P-41 §8). Held-out baseline arms. A Payy same-policy arm |
| **[PENDING AI 3]** | Independent evaluation | Executing protocol v2 after approval |
| **[PENDING AI 4]** | Validation | Any remaining same-transaction contrast. The TE04 on-chain repaired-stack contrast. Combined-mutant Payy E4, which is out of single-mutant scope |
| **[PENDING HUMAN]** | Authors and annotators | A second independent annotator and inter-annotator agreement. Adjudication. Protocol-v2 approval |

**Controlling sources, in order.** [Research contract](../docs/research-contract.md)
revision 3 (28 October 2026). Revision 2 is archived as
[`research-contract-2026-10-27.md`](../docs/history/research-contract-2026-10-27.md),
and earlier experiments keep the revision under which they were run. After the
contract come the following.

- **Project status:** [README](../README.md).
- **Immutable reports:** [T15](../reports/T15.md)–[T22](../reports/T22.md),
  [D1P-12R](../reports/D1P-12R.md), [D1P-13](../reports/D1P-13.md),
  [D1P-14A](../reports/D1P-14A.md)–[D1P-14D](../reports/D1P-14D.md),
  [D1P-15](../reports/D1P-15.md),
  [D1P-17](../reports/D1P-17-consumer-backends.md),
  [D1P-19](../reports/D1P-19.md), [D1P-21A](../reports/D1P-21A.md),
  [D1P-30](../reports/D1P-30.md), [D1P-31](../reports/D1P-31.md),
  [D1P-34](../reports/D1P-34.md), [D1P-33](../reports/D1P-33.md),
  [D1P-35](../reports/D1P-35.md), [D1P-36](../reports/D1P-36.md),
  [D1P-40](../reports/D1P-40-correctness-audit.md),
  [D1P-41](../reports/D1P-41-ablation-preliminary.md),
  [TC02](../reports/TC02.md), [TE04](../reports/TE04.md),
  [TE05](../reports/TE05.md). D1P-40 prospectively corrects D1P-34 and
  D1P-35 without rewriting them.
- **Baselines:** [D1P-22](../docs/baselines/d1p-22-results.md),
  [D1P-32](../docs/baselines/d1p-32-benchmark.md) and the
  [baseline preregistration](baselines.md).
- **Extraction:** [D1P-16](../docs/extraction/d1p-16-feasibility.md),
  [D1P-18](../docs/extraction/d1p-18-hardening.md),
  [D1P-20](../docs/extraction/d1p-20-extracted-solver-model.md),
  [D1P-21B](../docs/extraction/d1p-21b-variant-extraction.md).
- **Benchmark and validation:**
  [mutation benchmark](../docs/x-experiment/BENCHMARK.md)
  ([package](../benchmarks/binding-mutants/)),
  [automatic-validation record](../docs/x-experiment/AUTO-VALIDATE.md),
  [evidence ledger](../docs/x-experiment/EVIDENCE-LEDGER.md),
  [harness architecture](../docs/x-experiment/HARNESS.md) and
  [policy review](../docs/validation/policy-review-2026-10-30.md). The
  ledger's grades supersede the lane's earlier `results.json` grades, and
  the policy review's rules govern both.
- **Obligations:** [B02](../docs/d1-paper/d1p-b02-discriminating.md).
- **Taxonomy:** [protocol v0.2.0](../docs/taxonomy/protocol.md),
  [v1 corpus](../docs/taxonomy/v1-corpus.md),
  [v1 agreement](../docs/taxonomy/v1-agreement.md),
  [reservation commitment](../docs/taxonomy/reservation-commitment-2026-10-28.json).
- **Planned evaluation:**
  [independent protocol v2](../docs/evaluation/independent-protocol-v2.md).

If this draft disagrees with any of these sources, the source wins.

**Research verdict at drafting time:** `UNKNOWN`. The capability gate
(contract §11) remains open.
- *Held-out:* neither held-out run completed an analysis (D1P-33: 0/4;
  D1P-36: 0/8), so there is no transfer result.
- *Development:* the static analyzer now reports the one real (historical)
  bug, Payy's message tail, as `UNKNOWN`.
- *Validation:* E4 with a causation contrast exists for the three case
  mechanisms and for 9 of the 13 WarpToad benchmark warnings, all on
  development data.
- *Baselines:* the same-policy baseline exists only for WarpToad, as a
  handwritten harness with a stub verifier (D1P-32).

### Claims ledger

| Claim | What exists | What is not established | Pending |
| --- | --- | --- | --- |
| **Correctness:** extracted facts are right, warnings name a real broken binding, and validated warnings show that binding causing an unauthorized effect | D1P-40 audit: five extraction defects found on compiled controls and repaired (v1.3). Benchmark under v1.3: 11 detected, 19 unsupported, 0 missed, all on WarpToad. E4 with causation contrast for Payy's tail (T18/T19), M-DOM (D1P-15), M-SRC (D1P-19), and 9 WarpToad benchmark warnings (EVIDENCE-LEDGER §3) | Static detection of the real Payy bug (`UNKNOWN` under v1.3). A v1.3 rerun of the five case targets. Confirmation of WT-C02's "unbound" claim. Any Payy mutation at E4. A frozen v1.3. A precision estimate | AI 1; AI 1, M2; AI 4 |
| **Novelty:** the automated circuit-to-consumer join reports something that unjoined one-sided analyses and baselines do not | D1P-41: full BindCheck detects no more than the unjoined union (6/8 each). The join adds a named consumer effect on 1 example (WT-C08). No verified prior tool performs the join (bounded primary-source search). | Any detection advantage. **Noir lint matches every circuit-side detection**, ZKAP covers unused public inputs, and a same-policy harness beats BindCheck on WarpToad consumer mutants. No final ablation on a frozen tool, no held-out comparison | AI 2; AI 1, M2; AI 3 |
| **Generality:** the frozen tool transfers to independently developed Noir/EVM projects | Two frozen scans: D1P-33 completed 0/4 analyses, D1P-36 completed 0/8, and no rule ran on any project. Protocol v2 finalized for approval | Any completed held-out analysis, warning, triage or validation | AI 1; AI 3; HUMAN (approval) |
| **Taxonomy** (descriptive, contract §3 item 1) | One human annotator labeled the 27-entry seed corpus: 17 included, with cause labels. Agreement with the AI suggestions is κ 0.83 for inclusion and κ 0.35 for cause | Inter-annotator agreement. Consequence and role labels. A codebook with a fixed precedence rule. The remaining endpoints | HUMAN |

### Task map

| Tag | Scope | Status | Paper locations |
| --- | --- | --- | --- |
| **D1P-30** | BindCheck v1 analyzer and validator; five development case runs; real-proof routes for the case mismatches | Done; v1 superseded as tool of record | §II-C, §VII-C |
| **D1P-31** | v1 on the 30-mutant benchmark; contract revision 3; reservation commitment | Done; v1 numbers kept as history only | §VII-C (one line), §IV-D |
| **D1P-34** | BindCheck v1.1: application-neutral consumer lowering, corrected use accounting, full-size Payy; reruns the five targets and the 30 mutants | Done | §V, §VI, §VII-C |
| **D1P-35** | BindCheck v1.2: exact Noir beta.15–21 container decoding and reporting-only locations. The rerun of all 35 targets is identical apart from 20 locations | Done | §V-G, §VI, §VII-E |
| **D1P-22** | Pinned baselines on the five case targets | Done | §VII-D |
| **D1P-32** | Baselines on the 30 mutants, including a Foundry same-policy harness for WarpToad and a sequential Mythril retry | Done | §VII-D |
| **AUTO-VALIDATE** (Lane X) | Per-application validation harnesses on all 53 v1.1 benchmark warnings | Done; grades corrected by the policy review | §V-H, §VII-C |
| **TC02 / TE04** (Lane X) | Real Payy aggregation proof on the PY-C02 build (TC02). On-chain replay with a real verifier and the pinned consumer (TE04) | Done. TE04 is attributed to the inherited tail defect | §V-H, §VII-C |
| **Policy review** | Author review of the validated effects against each application's policy | Done (2026-10-30) | §VII-C, §VII-G |
| **D1P-33** | Frozen v1.1 scan of the four reserved projects | Done: 0/4 completed analyses; no rule ran | §VII-E |
| **D1P-36** | Frozen v1.2 scan: the four reserved projects (second attempt) and four unseen, non-reserved projects | Done: 0/8 completed analyses; no rule ran | §VII-E |
| **D1P-40** | Extraction-correctness audit on compiled controls. Five defects repaired in prospective v1.3. 30-mutant rerun | Done (Milestone 1). Milestone 2 pending | §V-J, §VII-C |
| **D1P-41** | Preliminary novelty ablation: producer-only, consumer-only, unjoined union and full, on 9 exposed examples; primary-source prior-work check | Done (preliminary). Final run waits for a frozen corrected tool | §VII-D, §VIII |
| **EVIDENCE-LEDGER / TE05** (Lane X) | Warning-to-experiment correspondence, repair contrasts, corrected WT-S02, PY-C02 active-prefix run | Done | §VII-C |
| **Protocol v2** | Independent held-out evaluation (about 30 candidates, about 10 reserved); fractional draw support in `reserve_families.py` | Final text for approval (SHA-256 `cd80f5f7…`); approvals empty; not executed **[PENDING AI 3]** | §VII-E |
| **Taxonomy v1** | Seed-only AI-assisted extraction (Lane X), then blind human labels by one annotator | Single-annotator labels done; inter-annotator round pending | §IV-D, §VII-F |

Discrepancies found while drafting are listed under *Open items for authors*
at the end.

---

## Abstract

A zero-knowledge verifier establishes only the relation its circuit encodes.
The contract that consumes an accepted proof then decodes the public inputs
and mints tokens, transfers them, records nullifiers or advances state.
Whether those effects are justified is a property of neither component alone.
It depends on two conditions:
- every public value the consumer relies on is constrained by the circuit;
  and
- every value the circuit trusts is checked by the consumer against its own
  state.

We call violations of this agreement *proof-to-execution binding failures*.

BindCheck analyzes the circuit–consumer boundary of Noir/ACIR producers and
Solidity consumers. It decodes the compiled circuit and counts the
proof-enforced uses of every public input. It lowers the consumer's compiler
AST, finds the verifier call by its interface type, and follows each public
word to guards, storage writes and token effects. Application-neutral rules
join the two sides, and each warning carries a location, an explanation and
a suggested fix.

We evaluate three claims.

**Correctness.** An audit on compiled controls found and repaired five
extraction defects:
- dynamic-memory uses were treated as unused;
- public-input mappings were guessed from array width;
- token effects were matched by signature alone;
- loop dependencies were over-widened; and
- an anchor rule could never fire.

On a 30-mutant development benchmark of two applications, the corrected
analyzer detects the named binding in 11 mutants, finds 19 outside its
supported scope, and misses none. All 12 mutants of the historical Payy
rollup now stop at an unverified public-input mapping. The real Payy
message-tail bug is therefore `UNKNOWN` to the static analyzer, although
real proofs still reproduce it end to end.

For three case mechanisms, real proofs show the defect causing an
unauthorized committed effect: the historical Payy tail and two injected
WarpToad bridge variants. A run on the original or repaired version shows
that the same input does not produce the effect. The same holds for 9 of the
13 benchmark warnings that survive the audit.

**Novelty.** In an ablation, BindCheck's joined analysis detects nothing that
the union of its producer-only and consumer-only halves misses. Compiler
lint and prior circuit tools already report unused public inputs, and a
handwritten same-policy harness beats BindCheck on consumer-side mutants. We
therefore claim novelty only for the automated join of circuit facts with
consumer guard, state and effect facts. On one example, that join names the
consumer effect at risk, which neither half reports alone.

**Generality.** Two frozen scans of independently developed Noir/EVM
projects completed no analysis: 0/4 and 0/8, so no rule ran. These are
limits of compiler-version, opcode, recursion and consumer-boundary support,
not misses and not evidence of safety. We give a preregistered protocol for
a larger independent evaluation.

A seed taxonomy corpus has been labeled by one human annotator. Inter-rater
agreement is not yet measured. Path-conditional binding and role
correspondence remain future work. All detection and validation results are
development results on applications known before the rules were written.

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
in its default configuration described the mismatch (D1P-22; §VII-D). On the
benchmark, two baselines match or beat BindCheck (D1P-32; §VII-D):
- the Noir compiler's unused-variable warning names every circuit-side
  mutant that BindCheck detects; and
- a handwritten same-policy fuzz harness finds more WarpToad consumer
  mutants than BindCheck.

Our claim is therefore complementarity, not dominance.

### C. BindCheck

BindCheck v1.1 is a command-line tool with two commands (D1P-34; the CLI is
unchanged from v1). §V describes v1.1. v1.2 changed only container decoding
and reporting (D1P-35). The prospective v1.3 repairs five extraction defects
found by the D1P-40 audit (§V-J); it is not yet frozen
**[PENDING AI 1]**.

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

### D. Claims and contributions

The paper makes three evaluated claims. Each item states the evidence that
exists now, what that evidence does not establish, and the lane whose work
it awaits (lane key in the header). The candidate contributions of research
contract revision 3 (§3) map onto these claims as shown in brackets.

1. **Correctness** (contributions 2, 3 and 4 of contract §3). Three parts:
   - *Facts.* The extracted implementation facts are right.
   - *Warnings.* A warning names a binding that is really broken.
   - *Validation.* A validated warning shows that this binding causes an
     unauthorized committed effect.

   *Exists:*
   - D1P-40 audited the extracted facts on compiled synthetic controls. It
     confirmed and repaired five defects in prospective v1.3 (§V-J).
   - On the 30-mutant benchmark, v1.3 detects 11, finds 19 unsupported and
     misses 0. All 11 detections are WarpToad warnings with identities
     unchanged from v1.1.
   - The three case mechanisms (Payy's tail, M-DOM, M-SRC) have real-proof
     E4 evidence with a causation contrast. So do 9 of the 13 WarpToad
     benchmark warnings, each through a repair contrast in which the pinned
     version blocks the same attack while an honest control passes
     (EVIDENCE-LEDGER §3).

   *Not established:*
   - **Payy is `UNKNOWN` to the static analyzer.** v1.3 cannot establish
     the 1,005-to-1,003 public-input mapping, and the tail leaves have
     unresolved dynamic-memory dependencies. The real bug's E4 evidence is
     unaffected, because it comes from real proofs, not from the analyzer.
   - A v1.3 rerun of the five case targets **[PENDING AI 1]**.
   - Path-conditional binding and role correspondence
     **[PENDING AI 1, M2]**.
   - WT-C02's "unbound" claim, which is unconfirmed (EVIDENCE-LEDGER §4)
     **[PENDING AI 1]**.
   - Any Payy mutation at E4.
   - A precision estimate.
2. **Novelty** (contributions 2, 3 and 5 of contract §3). The *automated
   join* of circuit-side facts with consumer guard, state and effect facts.
   Detection is not claimed:
   - in D1P-41's preliminary ablation, full BindCheck and the unjoined union
     of its producer-only and consumer-only halves each match 6 of 8
     examples;
   - the pinned Noir compiler's unused-variable warning names every
     circuit-side mutant that BindCheck detects (D1P-32); and
   - ZKAP's paper describes the unused-public-input pattern for Circom
     circuits [15].

   *What the join adds:* naming the consumer effect at risk for a
   producer-unbound word. In the ablation it does so on one example
   (WT-C08), where it removes one of four manual confirmation checks. A
   bounded primary-source search found no verified prior tool that performs
   this join (D1P-41 §6). That is a gap in what we found, not a proof of
   absence.

   *Pending:* the final ablation on a frozen corrected tool, and held-out
   comparison **[PENDING AI 2, AI 3]**.
3. **Generality** (contributions 3 and 5 of contract §3). The frozen tool
   transfers to independently developed Noir/EVM projects.
   - *Exists:* D1P-33 completed **0/4** analyses and D1P-36 completed
     **0/8**; no rule ran on any of these projects. These are capability
     limits, not misses and not safety evidence.
   - *Planned:* a preregistered evaluation, finalized for approval, with
     about 30 candidates, about 10 reserved families and a separate
     development pool
     ([protocol v2](../docs/evaluation/independent-protocol-v2.md)).
   **[PENDING AI 1, AI 3]**
4. **Taxonomy** (contribution 1 of contract §3; descriptive). This is a
   taxonomy of proof-to-execution binding failures (§IV) with three
   independent dimensions: cause, consequence and attacker role. It is tied
   to the authorization/coverage semantics of the research contract.
   - *Exists:* codebook and protocol v0.2.0, and a seed-only v1 corpus of
     27 findings. One human annotator labeled them blind to the AI
     suggestions, including 17 with cause labels.
   - *Pending:* a second independent annotator, consequence and role
     labels, a codebook precedence rule, and the remaining endpoints
     **[PENDING HUMAN]**.

The validated case studies (§II) supply the ground truth for claim 1:
- one historical case, Payy;
- two injected cases, WarpToad M-DOM and M-SRC; and
- exact-state honest controls for the injected cases.

Consistent with contract §1, we do not claim as new:
- integration failures as a category;
- the permission/obligation/effect terminology;
- rich semantic specifications;
- modular summaries;
- unused-public-input detection (compiler lint, ZKAP [15]); or
- one-sided consumer dataflow.

The possible advance is the automated circuit-to-consumer join and its
real-proof validation. The evidence for it is limited:
- it is demonstrated only on development cases;
- it adds no detection over an unjoined union in a small ablation; and
- it is outperformed by a handwritten same-policy harness on one consumer
  subset (§VII-D).

Generality is untested, because no held-out analysis has completed.

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
  only after the rules were frozen. Only held-out results can support
  transfer or generality claims (contract §9). The first reservation was
  over a small frame of eight candidate groups (§IV-D). Two frozen scans
  followed (§VII-E), and neither completed an analysis:
  - D1P-33 completed 0/4 on the reserved projects; and
  - D1P-36 completed 0/8, consisting of a second attempt on the reserved
    projects plus four unseen, non-reserved projects.

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

**Policy scope.** The pinned development contract also exposes a public
minting faucet. Our WarpToad policy covers only the **proof-consuming
withdrawal path** (`mint` behind the verifier). Faucet mints are not
protected effects in this analysis, and no claim is made about them
(policy review, 2026-10-30).

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

**What exists: a seed-only extraction with single-annotator human labels.** The
[v1 corpus](../docs/taxonomy/v1-corpus.md) covers one of the two seed
endpoints, the 0xPARC zk-bug-tracker at commit `56a99667…`. An AI agent
screened all 27 listed in-the-wild entries. It included 19 and excluded 8,
with none unresolved, and suggested one cause label per included finding.
The machine-readable ledger is schema-valid, and its AI labels are recorded
as `ASSUMED`. One human annotator has since labeled all 27 entries blind
(§VII-F). Those labels are recorded in
[v1-agreement](../docs/taxonomy/v1-agreement.md) and the blind sheet, not
yet in the ledger. The protocol's two-annotator round has not run. The SoK
dataset was not reached: it has no standalone endpoint an agent could
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
So are, under protocol v2, all eight mini-draw candidates and the four
D1P-36 Set B projects.

**Successor design.** For tool transfer, protocol v2 replaces this
mini-draw (§VII-E). It uses a logged GitHub search frame of about 30
Noir+EVM candidates, a custodian metadata screen, and a one-third draw of
about 10 families. Its public record carries counts and hashes but no
membership. It is a tool-transfer frame, not a disclosure-taxonomy frame,
and it does not change the taxonomy protocol's sampling design.

**Claim limit.** The strongest permitted statement, once human labels exist,
is that these mechanisms recur across independent families in the sampled
public disclosures. We make no prevalence, incidence or audit-quality
inference. Before human labeling, the corpus supports no claim beyond its
own existence and its screening counts (§VII-F).

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

**R-ANCHOR.** *v1.3 update:* the D1P-40 audit confirmed that R-ANCHOR was
unreachable, and v1.3 repairs it (§V-J). The paragraph below describes v1.1
and v1.2.

v1's root-specific rule is still in the code and the result schema. Under v1.1, however, both loaders record an anchor only after
finding a guarded storage lookup on it. Every recorded anchor therefore
already satisfies must-be-in, and R-ANCHOR cannot fire. This is our reading
of the code; D1P-34 states only that the rule identity changed. A removed
root guard now surfaces as R-CONSUMER on that word, because the word then
reaches nothing (M-SRC; WT-S01, WT-S02). We defer the fix until after the
transfer test. v1.2 changed only container decoding and reporting
locations (D1P-35 §4), so R-ANCHOR stays unreachable in it. Changing a rule
between the first held-out attempt and the rescan would have mixed rule
tuning into the held-out result (contract §9).

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

**Localization weaknesses observed in the D1P-34 outputs.** v1.2 fixed the
first two by a reporting-only change (D1P-35 §3):
- it recovers a verifier-call line only when the recorded interface call has
  exactly one source occurrence; and
- it selects among effects that already carry the unbound word.

Emitted `:?` locations fell from six to zero, Payy R-EFFECT now points to
the payout at `RollupV1.sol:522`, and no warning identity or non-location
fact changed. The tables below keep the v1.1 locations as emitted.

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
[TC02](../reports/TC02.md); [TE04](../reports/TE04.md)). There are three
harnesses and one on-chain replay.

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
  invalid`) and a second settlement (`Mint already spent`). The lane first
  graded these rows "E2, mock-verifier-scoped". The evidence ledger relabels
  them **`E1+mock`**. They execute the real consumer but check no producer
  assignment, so they show a consumer effect under assumed proof acceptance.
  That is not the contract's E2, which requires an assignment that satisfies
  the compiled producer relation (§III-F).
- **Payy circuit harness (TC02).** A Rust harness modeled on T15 proves a
  real `utxo → agg_utxo → agg_agg` chain on the PY-C02 mutant. It then
  attempts an attacker mint record in the active message slots, which no
  inner proof stands behind. It is a bounded probe, run on one mutant.
- **Payy on-chain replay (TE04).** Using the PY-C02 build, TE04:
  - proves the TC02 *tail* candidate through a mutant-keyed `agg_final`;
  - generates the real bb Solidity verifier; and
  - settles the block on the pinned `RollupV1` on anvil, with no mock
    component on the proof path.

  A forged kind-3 burn pays 7 synthetic units to `0xdead`, and the rollup
  balance drops from 100 to 93.
- **Payy active-prefix run (TE05).** TE05 does the same for PY-C02's own
  active-slot candidate. The block reverts at the consumer's message gate
  before verification (§VII-C2).
- **Repair checks.** `repair_check.py` restores exactly the removed line,
  asserts that the result is byte-identical to the pinned source, and
  replays the attack and an honest control (EVIDENCE-LEDGER §3).

**Attribution and causation (policy review, 2026-10-30).**
- *TE04 attribution.* TC02 shows that the original `c4d2c902` circuit also
  accepts the tail candidate, so TE04 is an E4 for the **inherited Payy
  message-tail defect**. It is not an E4 for PY-C02's own mutation. TE04's
  "pinned contrast" verified the mutant's proof under the original key. That
  check fails for any proof, so it is not a same-transaction contrast.
- *General rule.* Every E4 must show that the warned binding, not the setup
  or an inherited defect, causes the effect. The same transaction is run on
  the original and the defective version, and on a repaired version where
  one exists, with matching keys and identical initial state. Rows without
  such a run are reported as **E4, causation pending [PENDING AI 4]**.

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
8.5. TC02 needed a 489 s cold build and an 88.4 s harness run. The TE04
replay took 10.0 s after `agg_final` proving. These times are operational
observations, not benchmarks.

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

### J. Correctness audit and v1.3 corrections (D1P-40)

D1P-40 audited whether v1.2's *extracted implementation facts* are right. It
used small compiled Noir and Solidity controls whose expected facts are
known independently, and it did not touch any held-out project. Five
defects were confirmed and repaired in prospective v1.3. Two other
behaviors were confirmed correct: constant-index reads, and write-only
values optimized away.

| # | Confirmed defect in v1.1/v1.2 | v1.3 repair | Effect on results |
| --- | --- | --- | --- |
| 1 | A public value placed in memory and read through a *dynamic* index counted as unused, although the read can select it and feed a constraint | Tracks memory blocks in opcode order. Constant reads propagate exact cells. A dynamic dependency on an otherwise unused public leaf fails closed (`UNSUPPORTED_DYNAMIC_MEMORY_DEPENDENCY`) | Payy `messages[1..999]` become `UNKNOWN`, neither used nor unused |
| 2 | A consumer array shorter than the producer ABI was mapped by *inventing* a selector prefix from width arithmetic | Identity mapping is accepted only when the supported path establishes full width. Otherwise `SOLIDITY_PUBLIC_INPUT_MAPPING_AMBIGUOUS`, and old relations give `CONSUMER_PUBLIC_INPUT_MAPPING_UNVERIFIED` | All 12 Payy mutants fail closed. Payy's 1,005-to-1,003 mapping is unclear, not wrong |
| 3 | Any function with an ERC-20-shaped signature was labeled a token effect | Requires the standard method name (`transfer`, `transferFrom`) *and* the signature | Removes a false effect on the synthetic control |
| 4 | Loop-index widening attached unreachable tail words to effects | Literal success-path intervals bound the words. Other loops keep the named widening limitation | Bounded literal loops only |
| 5 | R-ANCHOR candidates were created only after a positive guard, so a missing guard could never be reported | Boolean indexed-storage reads are recorded before guard matching | The unguarded control now emits R-ANCHOR |

The 30-mutant rerun under v1.3 changes **16 detected / 14 unsupported / 0
missed / 53 warning objects** to **11 / 19 / 0 / 13**. The five
reclassified detections are all Payy: PY-C02, C04, C06, S01 and S02. All 13
surviving warnings are WarpToad warnings with unchanged identities,
evidence and locations (D1P-40 §5). D1P-34 and D1P-35 remain immutable
history; D1P-40 is the prospective correction.

**Meaning for the Payy case.** The static analyzer can no longer say that
the tail words of the historical Payy artifact are unconstrained. Two
things are unresolved:
- the exact address and path conditions of the dynamic reads; and
- the producer-to-consumer mapping.

Whether each tail word is actually constrained is open pending an
address/path proof and an implementation-fact certificate
**[PENDING AI 1]**. This removes the v1.1 static warning as evidence. It
does not contradict the real-proof reproduction of the bug (T15–T19, TE04),
which never depended on the analyzer.

**Milestone 2 (pending).** Two classes of binding remain outside every rule:
- *Path-conditional binding:* a word constrained only under a
  witness-controlled condition or extent, as in Payy's tail.
- *Role correspondence:* a word bound, but to the wrong role, state map or
  domain, as in WT-S05, WT-C05 and the domain words of WT-C03/C07.

D1P-41 §1 frames the second as a typed, policy-bearing boundary
correspondence. Extracting the expected role without encoding the expected
verdict remains the central oracle problem. Both are planned as Milestone 2
**[PENDING AI 1, M2]**, and no result in this paper depends on them.

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
| Per-application validation harnesses (Lane X) | WarpToad: `witness_synth_v1.py`, `scripts/xav/`; Payy: `scripts/xav/payy_replay.ts`, `XAVProxy.sol`, `payy-harness/tc02_tail.rs`, `scripts/te04_part1.sh`, `te04_part2.py`, `scripts/xav/te04_replay.ts`, `scripts/te05_part1.sh`, `te05_part2.py`, `scripts/xav/te05_replay.ts`; repair checks `scripts/xav/repair_check.py`; grading core `xav_core.py`; driver `scripts/xav_run.py` | 53 v1.1 warnings, ledger grade 8 E4 + 1 preserved E4 (repair-contrasted), 5 E3, 6 E1+mock, 33 E1 (EVIDENCE-LEDGER; Table 5a) |
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

- v1.1 accepts exactly two Noir versions (beta.14 and beta.22). v1.2 adds
  exact beta.15–21 container dispatch, which was validated on one
  development-only, one-opcode circuit (D1P-35 §2). Opcode payloads absent
  from that fixture can still fail closed: two beta.21 held-out programs
  stopped on `BETA22_MEMORY_OPERATION_ENCODING` (D1P-36).
- Neither version decodes beta.3 or beta.25, `MultiScalarMul`, or
  `RecursiveAggregation`.
- The AST frontend has been run on one consumer family (Payy, seven
  sources) under one solc version, and supports a bounded statement and
  expression subset. It requires exactly one verifier boundary.
- WarpToad still uses route-A relations, and no AST relation was built for
  any WarpToad consumer.
- Validation needs a registered route for each target identity, or a
  validation harness written for the application.

No held-out project produced a completed analysis (§VII-E):
- In D1P-33, every project stopped at the producer frontend.
- In D1P-36, NullProof's beta.19 producer decoded. Its consumer then stopped
  at `UNSUPPORTED_CONSUMER_AST_REQUIRED`, and a separate diagnostic found two
  verifier boundaries.

The AST frontend has therefore still produced a relation for only one
application.

---

## VII. Evaluation

### A. Three evaluated claims and their research questions

The evaluation is organized by claim. The paper's RQ numbers are kept so
that earlier references stay valid.

| Claim | Paper RQ | Question | Contract RQ (rev. 3) | Evidence now | Pending |
| --- | --- | --- | --- | --- | --- |
| **Correctness** (§VII-C) | **RQ1 Detection** | Do the generic rules warn at the correct public word and consumer location, without case-specific input? | RQ1 (fidelity), RQ2 (discovery) | D1P-34; D1P-35 rerun; D1P-40 fact audit and v1.3 rerun (11/19/0) | Frozen v1.3; five-target rerun; Payy fact certificate [AI 1]; Milestone 2 [AI 1, M2] |
| | **RQ2 Validation** | Does a warned binding cause an unauthorized committed effect, shown by real proofs and an original-versus-defective run? At what cost, and with how many manual inputs? | RQ3 (validation) | D1P-30 routes; D1P-15/19; T18/T19; AUTO-VALIDATE; TC02; TE04; TE05; policy review; EVIDENCE-LEDGER | TE04 repaired-stack contrast; combined-mutant Payy E4 [AI 4] |
| **Novelty** (§VII-D) | **RQ3 Baselines** | What do circuit-only, contract-only and same-policy tools report on the same targets? | RQ4 (comparative) | D1P-22; D1P-32; D1P-41 ablation (preliminary) | Final ablation on frozen tool; held-out baseline arms; Payy same-policy arm [AI 2] |
| **Generality** (§VII-E) | **RQ4 Held-out transfer** | With the tool frozen, does BindCheck complete analyses on independently developed projects, and do its warnings survive triage and validation? | RQ4 (transfer) | D1P-33: 0/4 completed; D1P-36: 0/8 completed; no rule ran | Protocol v2 development and freeze [AI 1]; execution [AI 3] |
| (problem class, §VII-F) | **RQ5 Taxonomy** | Which causes, consequences and roles recur across independent families in sampled disclosures, and how reliably can people label them? | — (descriptive; contract §3 item 1) | v1 corpus; single-annotator human labels (v1-agreement) | Second annotator; inter-annotator agreement; precedence rule [HUMAN] |

Contract RQ5 (efficiency) is not a paper RQ. Its null results are in
Appendix A, as the contract requires.

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
   completion without a related warning. Only WT-S04 stopped (§VII-D
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
rollback, but not a maximum-fee ceiling. The WarpToad policy covers only the
proof-consuming withdrawal path, not the development contract's public
faucet (§II-C).

**Validation scoring (policy review, 2026-10-30).** An effect counts as
unauthorized only under the application's stated policy. The review's
per-case judgments are:
- *WarpToad repeated minting* (WT-C01, WT-S03, WT-S09): unauthorized if the
  same note is spent again.
- *WT-S06:* unauthorized if the payment exceeds the proof-authorized maximum
  fee.
- *Foreign or unadmitted source* (WT-C03, WT-C04, WT-S01): unauthorized. Its
  synthetic root setup limits the deployment claim.
- *WT-S02:* unresolved, because the mock provider may make the fabricated
  root acceptable to the original contract too.
- *WT-C02, WT-C07 and WT-C08:* no completed unauthorized effect. For WT-C08,
  an owner-chosen nonzero recipient may be permitted.
- *Payy S03:* Payy's legitimate substitute-recipient mechanism is excluded
  from the misdirection claim.

An E4 additionally needs a same-transaction original-versus-defective run
(§V-H).

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

### C. Correctness (RQ1, RQ2)

Correctness has two parts. A warning must name a binding that is really
broken (RQ1). A validated warning must show that the binding causes an
unauthorized committed effect, which requires a contrast with a version
without the defect (RQ2). Every result in this section is development
evidence on applications known before the rules were written.

#### C1. RQ1 — Extracted facts and detection at the broken binding

**Status after the correctness audit.** Tables 2–3a report v1.1 (D1P-34),
the tool of record when the case and benchmark runs were made. The D1P-40
audit then found five extraction defects, and its v1.3 rerun supersedes the
benchmark figures *prospectively*:

| Measure (30 mutants) | v1.1 (D1P-34) | v1.2 (D1P-35) | v1.3 (D1P-40) |
| --- | --- | --- | --- |
| Detected | 16 | 16 | **11** (WarpToad only) |
| Unsupported | 14 | 14 | **19** (all 12 Payy, 7 WarpToad) |
| Missed | 0 | 0 | 0 |
| Warning objects | 53 | 53 | **13** |

The five lost detections (PY-C02, C04, C06, S01, S02) are not misses. They
stop at the unverified Payy public-input mapping (§V-J). The five case
targets were not rerun under v1.3 **[PENDING AI 1]**. For the full-size
Payy earlier artifact, however, D1P-40 §3.1 reports the 999 tail leaves as
`UNKNOWN`. **The v1.1 Payy detection in Table 2 is therefore no longer
supported by the static analyzer.** The real-proof evidence for the bug
stands (§VII-C2). v1.3 is not yet frozen.


*Table 2: v1.1 detection on the five development targets (D1P-34 §4;
analysis outputs). Validation evidence comes from D1P-30 (v1 warnings) and
is discussed in §VII-C2.*

| Case | Class | Pins (artifact / consumer) | Consumer relation | Rule(s) fired | Public word(s) and evidence | At scoring locus? | Static runtime | Analysis manual inputs | Reported verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Payy earlier | Historical, faulty (full size) | `83b75a4a…` / `7062065c…` | AST (v1.1) | R-BIND, R-EFFECT, R-CONSUMER | R-BIND `messages[1]..messages[999]` (public 6–1004; no proof-enforced use, one memory definition each). R-EFFECT on the same words, effect kinds storage write, token transfer and transfer-from. R-CONSUMER on `commit_hash` (public 4) | Producer: yes. Consumer: the burn transfers appear only as effect kinds; the R-EFFECT location (`RollupV1.sol:850`) is not the payout. R-CONSUMER concerns another word (out of scope, data availability) | 2.06 s | 1 | `UNKNOWN` |
| Payy check-added | Historical, repaired (one witness; full size) | `866b1800…` / `7062065c…` | AST (v1.1) | R-CONSUMER | No unused public leaf. R-CONSUMER on `commit_hash` (public 4) at `RollupV1.sol:357` | Control, with one out-of-scope consumer-side warning | 2.16 s | 1 | `UNKNOWN` |
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
message tail and of the repair. The author policy review (2026-10-30)
labels it **out of scope (data availability)**: the missing on-chain
publication check is confirmed, but no unauthorized committed effect is
established. It counts neither as a detection of the Payy case nor as a
false alarm, and it is not a confirmed defect.

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

*v1.3 correction:* the Payy positive is withdrawn as a static detection,
because its tail words are `UNKNOWN` (D1P-40 §3.1). The two WarpToad
positives are unaffected by the repairs, but a fresh five-target run is
pending **[PENDING AI 1]**.

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

The headline figure is 16/30, over all targets. The v1.2 rerun leaves every
detection, unsupported outcome, warning identity and non-location fact
unchanged (D1P-35 §5). With no misses, a
within-scope ratio would be 16/16 by construction. We do not report it as a
capability estimate (D1P-34 §1). The 14 unsupported mutants are reported as
unsupported, never as misses or as safe.

*History.* Frozen v1 scored 13 detected, 16 unsupported and 1 miss (PY-S02)
on the same 30 mutants (D1P-31). v1.1 was developed after those results were
known (§VII-G).

**Answer to RQ1 (benchmark).** *Under v1.3 (prospective):* 11 detected, 19
unsupported and 0 missed. These are the WarpToad detections below. Every
Payy mutant stops at the mapping gate.

*Warning-quality flag.* For WT-C02, EVIDENCE-LEDGER §4 reports that the
restored pinned circuit also accepts the attack witness (`max_fee = 0`),
and suspects that the analyzer undercounts an integer-comparison use. Its
R-BIND "unbound" claim is therefore not confirmed: it is a possible false
warning, pending fact reconciliation **[PENDING AI 1]**. It is counted as a
detection below only under the frozen D1P-34 scoring.

*Under v1.1, as frozen:* across the 30 mutants, v1.1 detected the
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
figure is meaningless without this inheritance, so we do not report one. Under v1.3, none of the 40 Payy warning objects is emitted, because
analysis stops at the mapping gate (D1P-40 §5).

#### C2. RQ2 — Warning quality, validation and causation

*Table 4: Per-warning record for the development cases (v1.1 warnings,
D1P-34 §4; validation evidence from D1P-30 §5 for v1's warnings on the
same mismatches).*

| Warning | Case | Rule | Location (as emitted) | Evidence | Suggested fix (repair side) | Adjudication | Validation of the mismatch | Route mode, proofs, time | Manual steps (validation) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| W001 | Payy earlier | R-BIND | `agg_agg.json:abi.messages[1]..messages[999]` | public 6–1004; no proof-enforced use | Producer: constrain exposed arguments | Target | E4 on the preserved full-size chain, credited in D1P-30 to the v1 warning on the N=8 build; the v1.1 identity has no route | Preserved T15/T16/T18; no new proof | 2 (D1P-30) |
| W002 | Payy earlier | R-EFFECT | `RollupV1.sol:850` (first modeled effect, not the payout) | same words; effect kinds storage write, token transfer, transfer-from | Producer binding; consumer derives effects only from bound words | Target (same mismatch as W001) | As W001 | As W001 | — |
| W003 | Payy earlier | R-CONSUMER | `RollupV1.sol:357` (verifier call) | public 4 `commit_hash`; calldata; no guard, state or effect | Consumer: consume the word | Not the case target; structurally accurate; out of scope (data availability), per the policy review | E1 (no route) | — | — |
| W001 | Payy check-added | R-CONSUMER | `RollupV1.sol:357` | as above | as above | Control warning; structurally accurate; out of scope (data availability), per the policy review | E1 (no route) | — | — |
| W001 | M-DOM | R-BIND | `m-dom-withdraw.json:abi.aztec_warptoad_address` | public 5; no proof-enforced use | Producer: constrain exposed arguments | Target | E4 in D1P-30. The v1.1 warning has the same target identity, but the route was not rerun. The coinciding mutant WT-C03 reached fresh E3 and preserved E4 under the WarpToad harness | Fresh; 2 real proofs (honest, foreign note); 28.82 s; peak RSS 737 MB | 1 |
| W001 | M-SRC | R-CONSUMER | `WarpToadCore.sol:?` | public 4 `destination_local_root`; calldata; no guard, state or effect | Consumer: consume the word in a state admission, replay or effect (generic text; the role is not named) | Target | E4 in D1P-30 for the v1 R-ANCHOR warning on the same word. The coinciding mutant WT-S01 reached E4 with a repair contrast under the WarpToad harness (Table 5a) | Fresh; 1 real proof; 98.99 s; peak RSS 490 MB | 1 |

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

**Causation contrasts for the case mechanisms.** Each case-study E4 comes
with a run on a version without the defect, using matching keys:

| Mechanism | Unauthorized effect (E4) | Contrast without the defect | Source |
| --- | --- | --- | --- |
| Payy message tail (historical) | Forged tail burn settles on the earlier consumer: rollup 100→93, `0xdead` 0→7 | The check-added (repaired) circuit rejects the same witness at `main.nr:120`. A mint-only control moves nothing | T18 §2; T19 §§1–3 |
| Payy message tail, on-chain with real verifier | Forged kind-3 burn settles through a real bb Solidity verifier and the pinned consumer, with no mock on the proof path | **None valid.** TE04's contrast verified the mutant's proof under the original key, which fails for any proof. Repaired-circuit contrast **[PENDING AI 4]** | TE04; policy review |
| M-DOM (injected, producer) | Foreign-note mint of `5e18` with nullifier write | The pinned circuit rejects the same semantic witness at witness execution (`Cannot satisfy constraint`) | D1P-15 §6.2; D1P-30 §5.1 |
| M-SRC (injected, consumer) | Mint of `3e18` over an unadmitted local root | The identical proof and calldata revert at K2 on the pinned consumer with no state change | D1P-19 §4.2; D1P-30 §5.2 |

TE04 ran on the PY-C02 build, but its candidate exercises only the
inherited tail. TE04 is therefore an E4 for **the inherited Payy
message-tail defect**, and it adds a real verifier and the real consumer to
T18. It is not an E4 for PY-C02's own mutation (policy review).

**PY-C02's own mutation (TE05).** TE05 ran PY-C02's *active-prefix*
candidate through the mutant stack: an attacker mint record at messages
0–3, with no inner proof behind it. It used the same consumer and initial
state as TE04.
- *Mutant:* the mutant-keyed final proof verifies natively.
- *Original and repaired circuits:* both reject the same witness at witness
  execution.
- *Consumer:* on-chain, the block reverts at the consumer's message gate
  (`Mint value invalid`) *before* the verifier is called, under both keys.

PY-C02's R-BIND warning therefore reaches E3 on its own mutation, with a
producer contrast and on-chain containment. Its R-EFFECT warning is E1,
because there is no state change. The ledger notes that containment, not
E4, is the principled ceiling for PY-C02 alone. A combined circuit and
consumer gap is outside single-mutant scope **[PENDING AI 4]**.

*Table 5: Warning-quality and validation summary. Grades follow the
EVIDENCE-LEDGER, which applies the policy review. "E4 + contrast" requires
the same transaction on the original or repaired version, with matching keys
and identical initial state. `E1+mock` means a consumer effect under assumed
proof acceptance; it is not contract E2.*

| Scope | Warnings | Related / other | At semantic location | Warnings on controls | E4 + contrast | E3 | E1+mock | E1 | Manual validation steps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Development cases, v1.1 (D1P-34 §4) | 6 | 4 target / 2 `commit_hash` (out of scope, data availability) | 4/4 target warnings name the scoring word. In v1.1, M-SRC prints no line and Payy R-EFFECT points to an unrelated write; both are fixed in v1.2. The Payy static warnings are withdrawn under v1.3 | 1 of 2 (Payy check-added) | 3 mechanisms, via v1 warnings (D1P-30) and the contrasts above | — | — | 2 (`commit_hash`) | 1–2 per route (D1P-30) |
| Benchmark, v1.1 warnings, unchanged D1P-31 index (D1P-34 §5) | 53 | 20 / 33 inherited | 16/16 detections | n/a | 1 (WT-C03, preserved) | 0 | 0 | 52 | 2 (WT-C03) |
| Benchmark, v1.1 warnings, per-application harnesses and repair checks (EVIDENCE-LEDGER) | 53 | 20 / 33 inherited | — | n/a | **9** (8 fresh + WT-C03 preserved) | 5 | 6 | 33 | 0, except 2 on WT-C03 |
| Benchmark, the 13 warnings that survive v1.3 (all WarpToad) | 13 | 13 / 0 | 11/11 detections (WT-C02 flagged, §VII-C1) | n/a | 9 | 4 (WT-C02, C07, C08 ×2) | 0 | 0 | 0, except 2 on WT-C03 |

*Table 5a: Validation of the v1.1 benchmark warnings, warning by warning.
Sources: the EVIDENCE-LEDGER (§§2–4, 6–7), AUTO-VALIDATE, TC02, TE04 and
TE05. Raw evidence is in ignored `results/raw/X-AV/v11/`,
`results/raw/REPAIR/`, `results/raw/TC02/`, `results/raw/TE04/` and
`results/raw/TE05/`. "Lane grade" is AUTO-VALIDATE's original grade, and
"ledger grade" is the corrected grade that the paper uses.*

| Mutant | v1.1 warning | Lane grade | Ledger grade | Causation contrast (repair check) | Time | Manual steps | Outcome |
| --- | --- | --- | --- | --- | --- | --- | --- |
| WT-C01 | R-BIND `nullifier` | E4 | **E4 + contrast** | Repaired (= pinned) circuit: attacker witness BLOCKED (`nullifier doesn't match`); honest PASS | 26.2 s | 0 | Double mint from two proofs of one note |
| WT-C02 | R-BIND `max_fee` | E3 | E3 (contained) | Repaired circuit still accepts `max_fee = 0` (REPAIR-UNEXPECTED). The warning's "unbound" claim is unconfirmed **[PENDING AI 1]** | 18.0 s | 0 | Proof accepted; consumer reverts at the fee cap |
| WT-C03 | R-BIND `aztec_warptoad_address` | E4, preserved (E3 fresh) | **E4 + contrast**, preserved | Repaired circuit: attacker BLOCKED (aztec binding); honest PASS; also D1P-15 §6.2 | 11.7 s | 2 | Byte-identical to M-DOM; D1P-15 foreign-note chain associated |
| WT-C04 | R-BIND `giga_root`; R-BIND `destination_local_root` | E4; E4 | **E4 + contrast** (both; one repair) | Repaired circuit: attacker BLOCKED (giga membership); honest PASS | 17.3 s; 18.1 s | 0; 0 | Mint from a fabricated origin root; synthetic root setup limits the deployment claim |
| WT-C07 | R-BIND `chain_id` | E3 | E3 (contained) | Repaired circuit: attacker BLOCKED (commitment) | 18.7 s | 0 | Dataless verifier revert; contained on the same chain; cross-chain impact argued, not executed |
| WT-C08 | R-BIND `recipient_address`; R-EFFECT `:171` | E3; E3 | E3; E3 (contained) | Repaired circuit: attacker BLOCKED (`recipient_address cant be 0`) | 19.4 s; 20.7 s | 0; 0 | `ERC20InvalidReceiver` on mint to zero. An owner-chosen nonzero recipient may be permitted; no claim beyond the tested transaction |
| WT-S01 | R-CONSUMER `destination_local_root` | E4 | **E4 + contrast** | Recorded mutant proof on the pinned consumer: REVERT `_localRoot unknown`. Honest mint succeeds (D1P-12R) | 18.7 s | 0 | Mint over an unadmitted local root |
| WT-S02 | R-CONSUMER `giga_root` | E4 | **E4 + contrast**, corrected experiment | The original run was a **setup artifact**: the mock provider was seeded with the fabricated root, so the pinned consumer also accepted it, and that run is withdrawn. In the corrected run, the mock is seeded with the honest root and the same proof is used. Mutant: mint succeeds with `gigaRootAdmitted:false`. Pinned: REVERT `_gigaRoot unknown`, no state change | 19.1 s (original) | 0 | K1 admission defect isolated |
| WT-S03 | R-CONSUMER `nullifier` | E4 | **E4 + contrast** | Pinned consumer, same run: first mint succeeds, replay REVERT `nullifier already exists` | 19.4 s | 0 | Same note mints twice |
| WT-S06 | R-CONSUMER `max_fee` | E4 | **E4 + contrast** | Pinned consumer: REVERT `_relayerFee is larger than _maxFee`. Within-cap honest mint succeeds (D1P-14A) | 19.3 s | 0 | Relayer paid about `0.24e18` above a proof-authorized maximum of 0 |
| WT-S09 | R-POLARITY | E4 | **E4 + contrast** | Pinned consumer, same run: first mint succeeds, replay REVERT `nullifier already exists` | 19.9 s | 0 | Same note mints twice |
| PY-C02 | R-BIND `messages[0]..messages[999]` | E4 (via TE04) | **E3** on its own mutation | Original and repaired circuits reject the active-prefix witness (TC02; TE05). The TE04 effect belongs to the inherited tail | TE05 proving; replay | 0 | Active block contained at the consumer's message gate (TE05) |
| PY-C02 | R-EFFECT `:850` | E4 (via TE04) | **E1** (contained) | Same block under both keys reverts at `Mint value invalid` before verification; no state change | — | 0 | No committed effect |
| PY-S01 | R-EFFECT `:842`; R-POLARITY `:357` | E2, mock verifier (both) | E1+mock (both) | — | 1.5 s; 0.9 s replay | 0 | Unregistered mint settled |
| PY-S02 | R-EFFECT `:850`; R-POLARITY `:357` | E2, mock verifier (both) | E1+mock (both) | — | 1.1 s; 1.1 s replay | 0 | Registered mint settled twice |
| PY-S03 | R-EFFECT `:851` | E2, mock verifier | E1+mock | — | 1.0 s replay | 0 | Burn paid a `noteKind`-derived address and the recipient got 0. No substitute was registered, so Payy's legitimate substitute-recipient path was inactive |
| PY-S04 | R-EFFECT `:853` | E2, mock verifier | E1+mock | — | 1.0 s replay | 0 | Dead kind-4 record settled as a burn; recipient +1000 |
| PY-C01, C03–C07, PY-S01–S05 (other rows) | 31 R-BIND, R-EFFECT and R-CONSUMER warnings | E1 | E1 | — | — | — | No real inner-proof vector for these mutants |
| PY-C02 | R-CONSUMER `commit_hash` | E1 | E1 | — | — | — | Off-chain placeholder; out of scope (data availability) |

The ledger totals over the 53 v1.1 warnings are:

| Grade | Warnings |
| --- | --- |
| E4 | 8, all with a repair contrast |
| E4, preserved | 1, with a repair contrast (WT-C03) |
| E3 | 5: WT-C02, WT-C07, WT-C08 ×2, PY-C02 R-BIND |
| E1+mock | 6 |
| E1 | 33 |

The lane's original grading was 10 E4, 1 preserved E4, 4 E3, 6 mock-verifier
E2 and 32 E1. The ledger made five corrections:
- PY-C02's two warnings are reattributed: R-BIND drops to E3 and R-EFFECT
  to E1;
- the WT-S02 run is withdrawn as a setup artifact and replaced by a
  corrected experiment;
- the WarpToad E4 rows receive repair contrasts;
- WT-C02 is flagged; and
- the mock rows are relabeled `E1+mock`.

Under v1.3, the 40 Payy warnings are no longer emitted. The 13 WarpToad
warnings keep their identities, so their validation carries over.

**Harness timing and plan provenance.** The WarpToad synthesis plans were
written *after* the D1P-31 warnings and mutant ground truth were known, and
were revised after the first results (EVIDENCE-LEDGER §1). Dispatch is by
warning shape, never by mutant name. The plans show that the warnings can
be driven to proofs and effects. They do not show blind automatic discovery.

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

**Answer to RQ1/RQ2 for the cases (correctness).**

*Warnings.* Every v1.1 warning on the development cases names the public
word and the side to repair. In v1.1, the WarpToad consumer-side warnings
give no line, and the Payy R-EFFECT location is an unrelated write; v1.2
fixed both. Under v1.3, the Payy case warnings are withdrawn, because the
static analyzer now reports the tail as `UNKNOWN` (§V-J).

*Validation.* All three case mechanisms have real-proof E4 evidence *with* a
causation contrast. The contrast is at the producer for Payy (repaired
circuit) and M-DOM (pinned circuit), and at the consumer for M-SRC (pinned
consumer). TE04 adds an on-chain E4 for Payy's inherited tail with the real
verifier and consumer. Its own repaired-stack contrast is not recorded
**[PENDING AI 4]**. The real-proof evidence does not depend on the
analyzer, so v1.3's `UNKNOWN` leaves it intact.

*What the diagnostics do.* They are actionable in the narrow sense that the
suggested fix names the missing binding, guard or use. They do not explain
the mechanism.

**Answer to RQ2 (benchmark).** Of the 13 WarpToad warnings, all of which
survive v1.3:
- 9 reached E4 with a repair contrast: the pinned version blocks the same
  attack and an honest control passes. These are WT-C01, C03 (preserved),
  C04 ×2, S01, S02 (corrected), S03, S06 and S09.
- 4 reached E3 with the effect contained by an independent consumer check:
  WT-C02, C07, C08 ×2. WT-C02's repair check was unexpected, and its warning
  is flagged.

Every WarpToad E-level except WT-C03's was reached with no manual step at
run time.

No Payy mutation reached E4. PY-C02's circuit warning is E3 on its own
mutation, and containment is its ceiling as a single mutant. The six Payy
consumer rows are `E1+mock`. The remaining Payy rows are E1. Under v1.3 none
of the Payy warnings is emitted.

The harnesses are per application ([HARNESS](../docs/x-experiment/HARNESS.md))
and were written knowing the benchmark ground truth. They show that warnings
can be driven to causally contrasted effects. They do not show automatic
witness construction for an unseen application.

### D. Novelty (RQ3): comparison with circuit-only, contract-only and same-policy baselines

**Summary.** Novelty is claimed **only for the automated join** of
circuit-side facts with consumer guard, state and effect facts. Detection
is not claimed. Four results bound the claim.

1. **The join adds no detection over an unjoined union (D1P-41,
   preliminary).** The ablation uses nine exposed development examples:
   eight positives and one honest control. It masks the analyzer's fact
   surface into four arms.

   *Table 7a: D1P-41 ablation (preliminary, v1.2 analyzer, exposed
   examples). Detection counts only the predeclared rule at the predeclared
   boundary.*

   | Arm | Detection (of 8) | Names the effect at risk | Related / irrelevant warnings | Mean remaining manual checks (of 4) | Clean control |
   | --- | --- | --- | --- | --- | --- |
   | Producer-only (R-BIND) | 3 | 0 | 3 / 1 | 3.625 | silent |
   | Consumer-only (R-CONSUMER, R-POLARITY, R-ANCHOR) | 3 | 2 | 3 / 1 | 3.625 | silent |
   | Unjoined union | 6 | 2 | 6 / 2 | 3.250 | silent |
   | Full BindCheck (adds R-EFFECT) | 6 | 3 | 7 / 3 | 3.125 | silent |

   The join's only useful extra output is on WT-C08. There, R-EFFECT links
   the producer-unbound `recipient_address` to the consumer's recipient mint,
   which removes one manual check. It also adds one irrelevant inherited Payy
   warning. Neither arm covers the two relationship examples, the wrong
   state map (WT-S05) and the wrong root relationship (WT-C05); those are
   Milestone 2 **[PENDING AI 1, M2]**.

   The examples were chosen to discriminate, were already exposed, and ran
   on the uncorrected analyzer. A final run on the frozen corrected tool is
   pending **[PENDING AI 2]**. The clean control's silence is `UNKNOWN`.
2. **Unused public inputs are prior art.** Two sources already cover them:
   - the pinned Noir compiler's unused-variable warning names the locus of
     every circuit-side mutant that BindCheck detects (D1P-32; Table 8):
     9 of 9 under v1.1, and 6 of 6 under v1.3, which keeps only the
     WarpToad detections. Noir also names PY-C05, which BindCheck rates
     unsupported;
   - for Circom, ZKAP's paper explains that a completely unused public input
     verifies with an arbitrary value (D1P-41 §6; [15]).

   The one development case where v1.1 had a circuit-side detection that
   lint lacked was full-size Payy earlier. The beta.14 compiler emitted only
   an unrelated unused-import warning (D1P-22). Under v1.3, that detection
   is withdrawn: the tail words are `UNKNOWN` (§V-J). No circuit-side
   detection advantage over lint therefore remains.
3. **A handwritten same-policy harness beats BindCheck on consumer
   mutants.** It detects 8 of 9 WarpToad consumer mutants against
   BindCheck's 5 of 9. BindCheck needs no per-application policy and catches
   the one mutant the harness misses (WT-S06).
4. **No verified prior tool performs the join.** A bounded search of
   primary papers, official repositories and the SNARK SoK found no tool
   that extracts a ZK circuit relation and its application consumer, then
   reports the consumer effect or state at risk (D1P-41 §6). Joint manual
   audits exist. The absence is bounded by the search and is not proved.

What remains distinctive is therefore narrow:
- automated cross-layer *context* in each warning: that the word is a
  verifier argument, and which consumer effect it reaches; and
- consumer-side detection without a per-application policy.

Both are demonstrated only on two exposed development applications. A
held-out comparison of Noir compiler warnings, Slither and BindCheck on the
same reserved projects (protocol v2 §10.6) does not yet exist
**[PENDING AI 2, AI 3]**.

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
| **BindCheck v1.1** (D1P-34) | — | **D** | Warning (control; R-CONSUMER `commit_hash`, structurally accurate; out of scope (data availability)) | M (control) | **D** | **D** | Context row; not run by the baseline lanes |

**Answer to RQ3 (cases).** No default-arm baseline described the mismatch on
any case target. Two generic checks localized a known positive without
explaining it. Slither named Payy's `verifyBurn`, and the beta.22 Noir
compiler named M-DOM's unused `aztec_warptoad_address`. Slither's mention of
M-SRC's `_localRoot` also appears on the pinned control, so it does not
discriminate. The D1P-32 same-policy harness detects M-SRC as a
root-admission violation and passes M-DOM. M-DOM's defect lives in the
circuit, and the harness replaces the circuit with a stub that accepts the
expected public words. BindCheck is the only tool in the comparison whose
diagnostics state a cross-component reason on all three positives. That
reason is a description, not an extra detection. Lint also localizes M-DOM,
and only BindCheck localizes Payy's tail words (see the summary above).

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
| **BindCheck v1.3** (D1P-40; prospective, not frozen) | — | D 6 · U 3 | D 5 · U 4 | U 7 | U 5 | D 11 · U 19 | D 9 · U 19 |

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
- *Circuit-side coverage is matched by lint.* BindCheck detects 9 of the 16
  circuit mutants, and the Noir compiler's unused-variable warning names all
  9 of them, plus PY-C05. No Solidity baseline and no fuzzing arm reaches
  any circuit mutant: every cell is U or R. The policy harness cannot reach
  them by construction, because its stub replaces the circuit. Lint plus
  the WarpToad policy harness covers every BindCheck detection except
  three: WT-S06, and the two Payy consumer detections (PY-S01, PY-S02), for
  which no policy harness exists. Under v1.3 the Payy detections are gone,
  which leaves WT-S06 as the only one.
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
consumer effect (D1P-32). The difference from BindCheck's R-BIND is
therefore one of explanation, not of detection. Both name the same unused
value on the circuit side, and only R-BIND and R-EFFECT add that the value
is a verifier argument and which consumer effects it reaches. The generic Foundry invariants detect three
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

**Answer to RQ3 (novelty, benchmark).** No generic circuit-only or
contract-only tool *described* a proof-to-execution mismatch on any mutant.
Their signals are localized lint (Noir 10, Slither 13) or unresolved runs
(Mythril, Echidna).

As a detector, however, BindCheck is matched or beaten on both sides:
- *Circuit side:* Noir lint names every mutant that BindCheck detects (9/9
  under v1.1; 6/6 under v1.3).
- *Consumer side:* a handwritten same-policy fuzz harness detects more
  WarpToad consumer mutants (8/9 against 5/9). BindCheck catches the one
  mutant it misses.
- *The join itself:* in the ablation, the unjoined union of BindCheck's two
  halves detects as much as the full tool (6/8 each).

BindCheck's remaining distinctions are:
- the automated join's cross-layer context, which names the effect at risk
  on 1 of 8 ablation examples; and
- consumer-side detection with no per-application policy.

All of this is development evidence on exposed families. A held-out
comparison is **[PENDING AI 2, AI 3]**.

### E. Generality (RQ4): held-out transfer

**Headline.** Neither frozen scan completed an analysis:
- **D1P-33 completed 0/4 analyses** on the reserved projects; and
- **D1P-36 completed 0/8 analyses**: the same four projects as a second
  attempt, plus four unseen, non-reserved projects.

No rule ran on any of them. These counts are capability limits. They are
**not misses**, because no warning could have been emitted. They are **not
safety evidence**, because unsupported is `UNKNOWN`. They give no estimate
of false negatives, warning precision or validation transfer. Generality is
untested.

**Frame.** The reserved set comes from the mini-draw of §IV-D: eight
candidate Noir/EVM project groups listed from names and URLs only, of which
the custodian reserved four. This frame is smaller than the frozen v0.2.0
plan, which calls for full index traversal, and we disclose it as such.
Three gaps in the recorded procedure follow:
- no search query was recorded for the frame;
- D1P-33 records no check of the opening against the commitment; and
- D1P-36 does not record how its four unseen Set B projects were selected.

Protocol v2 addresses all three (below).

**Protocol (D1P-33, D1P-36).**
- *Freeze:* D1P-33 froze v1.1 at commit `4382ee6…`, tag `bindcheck-v1.1`.
  D1P-36 froze v1.2 by the D1P-35 manifest, with payload SHA-256
  `190cc96e…`.
- *Retrieval and build:* each project was pinned to a full commit with
  recursive submodules and built locally with its own toolchain pins where
  they exist. D1P-36 reused D1P-33's Set A trees and builds.
- *Single run:* each project got exactly one frozen `bindcheck analyze`
  invocation.
- *Byte identity:* after each run, the frozen files were byte-identical.
  D1P-33 checked 60 files under `src/` and `protocols/`, and D1P-36 checked
  the 17 files of the D1P-35 manifest.
- *No contact:* no maintainer was contacted, and no live-chain action took
  place.

Set B was opened only after the v1.2 freeze timestamp (D1P-35 §7).

**What v1.2 changed between the attempts (D1P-35).**
- *What changed:* exact compiler-identity dispatch for Noir beta.15–21,
  validated only on a synthetic development circuit, and reporting-only
  location fixes.
- *What did not change:* rules, thresholds, use counting, the effect table,
  and the beta.14, beta.22 and Solidity frontends.
- *Why it was made:* after D1P-33 failed at the version gate on three of
  the four reserved projects. The versions were chosen knowing which
  versions those projects use (D1P-35 §6).

Set A in D1P-36 is therefore a *second attempt after a change motivated by
the first attempt*, not a first held-out attempt. Only Set B is a first
attempt, and it is non-reserved. The two strata are never pooled.

*Table 9: Held-out results per project (D1P-33 §§1, 4; D1P-36 §§1, 4).
Project names are given because no finding exists. Whether to keep them in
the submission is Open item 11.*

| Project (pinned commit) | Stratum | Producer / consumer stack | Local build | v1.1 result (D1P-33) | v1.2 result (D1P-36) | Analysis-time facts | Warnings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NullProof (`79156bc9…`) | A: reserved | Noir beta.19 / Solidity 0.8.33 (`ComplianceGate`) | Circuit and contracts compile | Unsupported: compiler identity (beta.19) | Unsupported: `UNSUPPORTED_CONSUMER_AST_REQUIRED`. The producer decodes (300 opcodes, 2 public leaves) | A separate diagnostic found 2 verifier boundaries (`SOLIDITY_VERIFIER_BOUNDARY_COUNT:2`) | 0 / 0 |
| privacy-preserving-IP-NFT (`6ed03661…`) | A: reserved | Noir beta.3, a fallback evidenced by adjacent Noir JS dependencies (the project declares only `>=0.31.0`) / Solidity 0.8.30 (no project pin) | Circuit compiles with the beta.3 fallback; contracts compile with tests and scripts skipped | Unsupported: compiler identity (beta.3) | Unsupported: compiler identity (beta.3 schema not added) | Declared version does not determine the building compiler | 0 / 0 |
| zkt-research (`166b3c30…`) | A: reserved | Noir beta.21 / Solidity 0.8.31 (`ZKTCore`) | Circuit and contracts compile | Unsupported: compiler identity (beta.21) | Unsupported: `MultiScalarMul` | The checked-in `HonkVerifier.sol` is a stub that returns false, and the rebuilt artifact differs from the committed one | 0 / 0 |
| ZKPassport circuits (`818e7a7e…`, `outer_count_4`) | A: reserved | Noir beta.22 / Solidity 0.8.30 (`SubVerifier`) | Circuit and contracts compile | Unsupported: `RecursiveAggregation` | Unsupported: `RecursiveAggregation` | Recursive outer verifier | 0 / 0 |
| zk-panagram (`162443fa…`) | B: unseen, non-reserved | Noir beta.21 / Solidity | Circuit and contracts compile | — | Unsupported: `BETA22_MEMORY_OPERATION_ENCODING` | MemoryOp payload absent from the D1P-35 fixture | — / 0 |
| nachweis-app (`83d47410…`) | B: unseen, non-reserved | Noir beta.21 / Solidity | Circuit and contracts compile; compiler warns of an unconstrained dependency Brillig call | — | Unsupported: `BETA22_MEMORY_OPERATION_ENCODING` | As above | — / 0 |
| confidential-agent-policy-verdicts (`212ff1f5…`) | B: unseen, non-reserved | Noir beta.25 (three circuits) / Solidity | All three circuits and the contracts compile | — | Unsupported: compiler identity (beta.25) | 40-word public-input vector built by an adapter | — / 0 |
| e-votinng-diploma (`e2670a9e…`) | B: unseen, non-reserved | Noir beta.21 / Solidity | Full Foundry route fails (stack too deep); scoped consumer and verifier routes compile | — | Unsupported: `MultiScalarMul` | — | — / 0 |

The source facts in the last two columns are preserved for auditing target
selection and stopping position. They are not BindCheck warnings, and they
are not promoted to findings.

*Table 10: Held-out funnel (D1P-33; D1P-36). Stages are monotone.*

| Stage | D1P-33 (v1.1), Set A | D1P-36 (v1.2), Set A (second attempt) | D1P-36 (v1.2), Set B (first attempt, non-reserved) |
| --- | --- | --- | --- |
| Candidate frame | 8 groups (names and URLs only; AI-prepared; no query recorded) | same | Selection not recorded |
| Reserved / selected | 4 (commitment `514ad719…`; no opening check recorded) | same 4 | 4 |
| Retrieved, pinned, built locally | 4 | 4 (D1P-33 builds reused) | 4 (one through scoped routes) |
| **Completed analyses (rules ran)** | **0/4** | **0/4** | **0/4** |
| Unsupported, with named reason | 4 | 4 | 4 |
| Warnings | 0 | 0 | 0 |
| Triaged | 0 | 0 | 0 |
| Validated | 0 | 0 | 0 |
| Confirmed defects | 0 | 0 | 0 |

**Answer to RQ4 (generality).** Neither frozen scan completed an analysis on
any independently developed project:
- 0/4 for v1.1 (D1P-33);
- 0/4 for v1.2 on the reserved second attempt (D1P-36 Set A); and
- 0/4 for v1.2 on unseen, non-reserved projects (D1P-36 Set B).

No rule ran. Every stop is a named fail-closed reason:
- an unsupported compiler identity (beta.3, beta.25);
- an unsupported opcode or encoding (`MultiScalarMul`, the beta.21 MemoryOp
  payload);
- recursion (`RecursiveAggregation`); or
- a consumer boundary the frontend does not lower (two verifier calls).

The results locate where the tool's generality ends. They say nothing about
whether its rules transfer. They are not misses, and they are not evidence
that any project is safe. Transfer remains untested.

**Next: an independent evaluation (protocol v2) [PENDING AI 1, AI 3].** The
[protocol](../docs/evaluation/independent-protocol-v2.md) replaces the
mini-draw.
- *Status:* its text is final for approval, with SHA-256 `cd80f5f7…`
  computed over everything above its approval block. The approval block is
  empty, so the protocol is not yet frozen **[PENDING HUMAN]**.
- *Draw support:* `reserve_families.py --fraction 1/3` implements the
  one-third draw. The fraction is recorded in the private manifest, the
  default half rule is unchanged, and the tests cover 30→10 and 8→3.
- *Tool:* the frozen tool for that evaluation will be whatever AI 1 freezes
  after the v1.3 audit, and possibly after Milestone 2. The order is fixed:
  freeze first, then open the reserved set.

Its main points:
- *Frame:* about 30 Noir+EVM candidates and about 10 reserved families.
  These are targets, not acceptance requirements. The search sources and
  exact query strings are frozen and logged before retrieval.
- *Screen:* a metadata screen by the human custodian, covering the
  `Nargo.toml` package and `compiler_version` fields and the presence of
  non-vendored Solidity. The screen only admits candidates. Metadata cannot
  establish:
  - verifier pairing;
  - verifier correspondence;
  - the number of verifier boundaries;
  - the absence of recursion; or
  - the compiler that actually builds the project.

  These facts are determined at analysis time and reported for every
  project. The compiler version is recorded, not filtered on, so the frame
  is not fitted to current tool support.
- *Draw:* family grouping, then a custodian draw of one third per stratum,
  rounded up, with a salted commitment. The public record carries counts
  and hashes but no membership, and the opening must be checked before any
  retrieval.
- *Development pool:* the non-reserved eligible pool is AI 1's development
  set. AI 1 freezes the tool by tag and hash manifest before the reserved
  set is opened.
- *Single run:* one frozen run per target pair. Every reserved project
  stays in the results, including failed retrievals, failed builds, missing
  pairings, unsupported analyses and timeouts.
- *Counts:* completed analyses, warnings and confirmed defects are reported
  separately. Human triage has two steps (is the structural fact true; then
  false warning, intended design, plausible issue or unclear), and is sealed
  before validation. A confirmed defect requires an E4 with a causation
  contrast.

Until protocol v2 is executed, the paper makes no generality claim.

### F. Generality of the problem class (RQ5): taxonomy

**Status: single-annotator human labels.** The repository author labeled all
27 seed entries blind on
[`v1-blind-labels.md`](../docs/taxonomy/v1-blind-labels.md), which had the
AI labels and include tags removed
([v1-agreement](../docs/taxonomy/v1-agreement.md)). The author made every
include decision and every cause label.
- *Disclosed assistance:* an AI assistant helped the annotator understand
  the source bug descriptions. It did not see the AI-suggested labels and
  did not choose labels.
- *Anchoring residue:* the sheet still carried AI-written one-line
  summaries, and the annotator corrected one of them (CF-01).
- *What this is not:* this is human annotation by **one** annotator, not
  the protocol's two-annotator round. AI output is not an independent
  annotation (contract §10), so the agreement figures below compare the
  human with an *AI suggester*. They are not inter-annotator reliability.

*Table 11: Disclosure funnel (v1 corpus; one seed endpoint). The human
decision governs. The AI screening is shown for comparison.*

| Stage | Count | Unit |
| --- | --- | --- |
| Endpoints traversed | 1 of 17 (0xPARC zk-bug-tracker, commit `56a99667…`) | endpoints |
| Raw retrieval hits | 27 | entries |
| Unique source records | 1 | documents |
| Candidate findings (before deduplication) | 27 | findings |
| Canonical findings (duplicates) | 27 (0) | findings |
| Included / excluded / unresolved (**human**) | **17 / 10 / 0** | findings |
| Included / excluded / unresolved (AI screening) | 19 / 8 / 0 | findings |
| Families touched (all logged as exposed) | 23 | families |
| Families represented among included findings (human; AI) | 13; 15 | families (ledger family IDs) |

Every human-included entry was also AI-included. The human additionally
excluded two:
- CF-04: unusable groups, an availability break with no wrong effect; and
- CF-05: a failed leaf removal, not an accepted unauthorized proof.

The AI's eight exclusions and their recorded reasons are: a pure circuit-library
gap with no evidenced consumer; a verifier soundness break and a
trusted-setup compromise (both out of scope by contract §5.4); two
proof-protocol or proof-system soundness flaws; a privacy leak with no
execution effect; a library availability bug; and a consumer concurrency bug
with no proof/consumer disagreement.

*Table 12: Cause labels over the 17 findings that both the human and the AI
included (one primary label per finding).*

| Cause | Human | AI suggestion (same 17) | Example (corpus ID) |
| --- | --- | --- | --- |
| `C_REPRESENTATION` | **10** | 5 | CF-01, out-of-range moves accepted (Dark Forest) |
| `C_RELATION_GAP` | **6** | 5 | CF-10, message-to-leaf binding missing (MACI; AI said `C_ACTIVATION_EXTENT`) |
| `C_FIELD_MAPPING` | **1** | 1 | CF-22, context zero aliases slots (Polygon zkEVM; AI said `C_CONTEXT_IDENTITY`) |
| `C_ACTIVATION_EXTENT` | 0 | 3 | — |
| `C_OCCURRENCE_ACCOUNTING` | 0 | 2 | — |
| `C_CONTEXT_IDENTITY` | 0 | 1 | — |
| `C_VERIFICATION_CONFIG`, `C_DISCHARGE_TRANSFORMATION`, `C_OTHER_BINDING` | 0 | 0 | — |
| Consequence (`K_*`) and attacker-role (`A_*`) labels | not labeled | not extracted | — |

The protocol records each label as present, absent or uncertain, and allows
several per finding. Both label sets here are a single primary cause per
finding, with no consequence or role labels. Table 12 is therefore not the
protocol's label-frequency table.

*Table 13: Agreement between the single human annotator and the AI
suggestions (v1-agreement). This is not inter-annotator agreement.*

| Field | Comparable n | Raw agreement | Cohen's κ (human vs AI) | Interval | Notes |
| --- | --- | --- | --- | --- | --- |
| Include / exclude | 27 | 25/27 (92.6%) | 0.83 | not computed | Both disagreements are human exclusions of AI includes (CF-04, CF-05) |
| Cause label (both included) | 17 | 9/17 (52.9%) | 0.35 | not computed | 6 of the 8 disagreements move to `C_REPRESENTATION` or `C_RELATION_GAP` |
| Inter-annotator (two humans) | — | — | — | — | No second annotator; pending **[PENDING HUMAN]** |

**Interpretation and threats (v1-agreement).**
- *Systematic, not random.* The human labeled the root mechanism, such as
  a missing range check or a missing constraint. The AI often labeled the
  downstream manifestation, such as duplicate nullifiers or branch
  activation.
- *Instruction-induced precedence.* The labeling guide given to the
  annotator in a planner session listed the causes as an ordered decision
  list, with `C_REPRESENTATION` first and `C_RELATION_GAP` second, and said
  "stop at the first clear match". The protocol codebook defines no
  precedence. The human notes cite this priority on CF-08, 10, 20, 23 and
  27, and the AI never saw the guide. Part of the cause disagreement, and
  the human distribution's concentration in the first two labels, may
  therefore be produced by the instructions. A future round must fix one
  precedence rule in the protocol and give it to every annotator.
- *Codebook overlap.* Range defects often also create occurrence or
  activation effects, so the causes are not mutually exclusive as written.
- *Include-rule ambiguity.* CF-04 and CF-05 were excluded under a "no wrong
  effect / availability-only" reading from the sheet. Protocol §2 does not
  explicitly exclude availability.
- *Scope.* One annotator, one source (the zk-bug-tracker seed), 27
  entries.

*Table 14: Tool funnel for included findings (separate denominator).*

| Stage | Findings | Families | Main attrition reasons |
| --- | --- | --- | --- |
| Artifacts available | 0 (not attempted) | 0 | Tool funnel not run for the v1 corpus |
| Supported by BindCheck v1.1 | 0 (not attempted) | 0 | No corpus application lists a Noir producer (10 of 23 list Circom). None would pass v1.1's Noir beta.14/beta.22 gate |
| Cause covered by a v1.1 rule (§IV-C) | not assessed | — | — |

The second row's attrition reason comes from the ledger's `producer_stack`
fields. It is an expectation, not a measurement. The same observation is why
the held-out frame (§VII-E) was drawn from Noir/EVM projects rather than
from the corpus.

**Answer to RQ5.** Only a descriptive single-annotator result is supported.
In one seed source, the human annotator included 17 of 27 disclosures from
13 families. The annotator labeled 10 of them representation failures, 6
relation gaps and 1 a field-mapping failure. No `C_OTHER_BINDING` label was
needed.

That concentration cannot yet be separated from the instruction-induced
precedence threat. No reliability claim is possible without a second
independent human annotator. Relation gaps are what R-BIND targets, but none
of the corpus systems is analyzable by BindCheck.

Whether these mechanisms *recur across independent families* in the
protocol's sense awaits the two-annotator round with a fixed precedence
rule, and the remaining endpoints **[PENDING HUMAN]**.

### G. Threats to validity

**Development bias.** The rules were designed after the three case studies
were known. Payy's defect, advisory and end-to-end artifact predate the
rules. WarpToad was screened and inspected in D1-02, D1P-11 and later tasks.
The benchmark mutates the same two applications. RQ1 and RQ2 therefore show
capability *on these applications* only (contract §9). Transfer rests on
RQ4 (generality) alone, which has no completed analysis yet.

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
on an unseen consumer is untested. No held-out consumer has yet been
lowered (§VII-E).

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

**Validation causation.** An unauthorized effect does not by itself show
that the warned binding caused it. The setup can cause it, as may be the
case for WT-S02, whose mock giga provider may admit the fabricated root on
the original contract too. So can an inherited defect: TE04's effect comes
from the Payy tail, which the original circuit also accepts. The policy
review therefore requires a same-transaction run on the original and the
defective version, with matching keys and identical initial state.

The repair checks now give such a run for every WarpToad benchmark E4
(EVIDENCE-LEDGER §3). WT-S02's original run was confirmed to be a setup
artifact: the mock provider trusted the fabricated root on the pinned
contract too. It was replaced by a corrected experiment that isolates the
defect. Three gaps remain:
- the honest controls for WT-S01, WT-S02 and WT-S06 come from earlier runs
  (D1P-12R, D1P-14A), not from the same run as the attack;
- TE04 has no repaired-stack on-chain contrast **[PENDING AI 4]**; and
- TE05 shows that a revert at a consumer gate placed *before* the verifier
  call says nothing about proof acceptance.

The policy review itself replayed no experiment.

**Static facts can be wrong.** The D1P-40 audit found five extraction
defects in the analyzer that produced the benchmark results. After repair,
the historical Payy detection and all Payy benchmark detections became
`UNSUPPORTED` or `UNKNOWN` (§V-J). Further defects may exist in fact classes
the audit did not test. WT-C02's warning is already flagged as a possible
undercount (EVIDENCE-LEDGER §4), and v1.3 is not frozen **[PENDING AI 1]**.

**Plan timing.** The validation plans were written after the warnings and
ground truth were known, and revised after first results (EVIDENCE-LEDGER
§1). The validation results show drivability, not blind discovery.

**R-ANCHOR was unreachable.** v1.3 repairs this on synthetic controls
(D1P-40 §3.4), but v1.3 has not been run on any held-out project. In v1.1,
and in v1.2, which changed only decoding and reporting,
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
check. The author policy review labels it **out of scope (data
availability)**. The missing on-chain publication check is confirmed, but
no unauthorized committed effect is established. It is not a false
positive, and not a confirmed defect. We therefore report one of two
controls as carrying a structurally accurate warning outside the threat
model. It shows that R-CONSUMER reports a missing use without knowing the
application's policy.

**Injected cases and benchmark.** M-DOM and M-SRC are injected. M-DOM is
grounded in an unused in-tree package and a developer warning, M-SRC in
documented reliance. Neither indicates a defect in pinned WarpToad. The
benchmark was built in parallel with D1P-30 by an AI-assisted lane. Its
operators share mechanisms with the cases. Its predicted effects are mostly
unexecuted outside the harness rows. Its Payy mutants sit on the
faulty revision.

**Admitted state.** The M-DOM differential uses privileged synthetic root
admission (`S_DOM`). WarpToad's giga-root admission comes from a mock
provider. The original WT-S02 run seeded that provider with the fabricated
root and is withdrawn. The corrected run seeds it with the honest root. Neither variant demonstrates cross-chain reachability. The
WarpToad policy covers only the proof-consuming withdrawal path. The
development contract's public faucet is outside the protected-effect model.

**Baselines.** The only same-policy harness covers WarpToad. It was
AI-authored, with no human inspection recorded, and uses a stub verifier.
No Payy or circuit-mutant harness was written after the results were seen,
so those cells stay unresolved (D1P-32). BindCheck's own scale and the
baselines' scale differ, so Table 8 shows BindCheck under both.

**Held-out frame and rescans.** The reserved frame has eight candidates
from one AI-prepared search with no recorded query, of which four were
reserved. Its commitment shows consistency, not randomness or timing. No
check of the opening is recorded, and the custodian's signature is not yet
added (§IV-D).

The D1P-36 rescan followed a version change made because of D1P-33's
failure, after the analysis lane had built the reserved projects. It is
therefore labeled a second attempt.

Set B's selection is not recorded, and Set B is non-reserved. Both scans
completed 0 analyses, so neither tests rule transfer (§VII-E). Protocol v2
is designed to remove these weaknesses, but it is not executed.

**Novelty is bounded by simple baselines.** Three results bound it:
- compiler lint matches every circuit-side benchmark detection;
- a same-policy harness beats BindCheck on WarpToad consumer mutants; and
- the D1P-41 ablation finds no detection gain from the join over an
  unjoined union.

The ablation is small, its examples were selected to discriminate and were
already exposed, and it ran on the uncorrected analyzer. The prior-work
search is bounded and found no verified joint tool, which does not prove
absence. No final ablation or held-out comparison exists
**[PENDING AI 2]**.

**Taxonomy.** The corpus covers one seed endpoint, and its extraction
deviated from the metadata-only access rule (§IV-D). The human labels come
from a single annotator, the repository author. That annotator used AI help
to understand source descriptions, and the sheet still carried AI-written
summaries. The labeling instructions imposed a cause precedence that the
codebook does not define, which may explain the concentration in the first
two causes (§VII-F). κ is reported only against AI suggestions, and no
inter-annotator reliability exists.

**Negatives.** No fixture is a proven negative control. We report adjudicated
counts, not false-positive rates.

**AI involvement.** AI agents did all of the following:
- implemented the code;
- ran D1P-22, D1P-30, D1P-31, D1P-32, D1P-34, D1P-35, and the D1P-33 and
  D1P-36 held-out scans;
- built the benchmark, the validation harnesses (including TC02 and TE04)
  and the Foundry policy harness;
- drafted the independent-evaluation protocol v2;
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
  the mutant locus on 10 of 30 mutants, as E1 lint (D1P-32). These 10 include
  all 9 circuit-side mutants that BindCheck detects. Lane X's
  synthetic probe found the same
  pattern. The under-constrained Brillig check fires on its own control,
  but public inputs are outside its scope ([Lane X report §2, X1](../docs/x-experiment/REPORT.md)). *Measured, not cited.*
- **Circomspect** [14] is a static analyzer and linter for Circom. It does
  not accept Noir. *Verified against the repository description; not run.*
- **ZKAP** [15] builds a circuit-dependence graph for Circom and runs nine
  query-based detectors. Its paper explicitly explains that a completely
  unused public input verifies with an arbitrary value. This is the
  strongest direct overlap with R-BIND, which is therefore not a novelty
  claim. The inspected paper contains no Solidity or consumer analysis. It
  discusses possible application impact but does not automatically name the
  consuming state or effect. *Verified against the USENIX Security 2024 PDF
  in D1P-41 §6. Not run; Circom only.*
- **Ecne** [16] checks whether de-optimized R1CS equations uniquely
  determine outputs from inputs. A `false` result means "unable to prove",
  not "unsound". This is a circuit-only uniqueness property. *Verified
  against the official repository (D1P-41 §6); not run.*
- **Picus** [9] checks the uniqueness property of ZKP circuits to find
  under-constrained signals. Its documented inputs are Circom source, iden3
  R1CS and gnark `.sr1cs`. Its README illustrates a counterexample as one
  input assignment with two different output assignments. A public input
  that no constraint reads is an input, so it falls outside that property
  as the README states it. Whether the paper's formulation covers it is
  **[TODO-VERIFY: full text]**. D1P-41 checked the related QED² paper. It
  confirms semantic finite-field reasoning with uniqueness inference over
  the circuit relation only. D1P-22 installed Picus and parsed its bundled
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
  and the pinned build timed out. D1P-41 read the paper, which describes
  CirC frontends that include Noir. Its "cross-side" relation is witness
  computation against circuit constraints, not circuit against consumer. Payy's tail is a case where the
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
E1 rather than real-proof executions (§VII-D).

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

Joint circuit-and-contract *reviews* exist. For example, a published Railgun
Circom-and-Solidity audit describes its method as project-tuned audit
tactics, not a formal procedure. D1P-41's bounded search of primary papers,
official repositories and the SNARK SoK found no verified automated tool
that extracts a ZK circuit relation and its application consumer, then
reports the consumer effect or state at risk (D1P-41 §6). Exhaustive absence
is not verified. **[TODO-VERIFY: cite the audit as a primary source if it is
kept.]**

---

## IX. Limitations

**Fragment.** v1.1 accepts Noir `1.0.0-beta.14` and `1.0.0-beta.22`
artifacts only. v1.2 adds exact beta.15–21 container dispatch, but opcode
payloads outside its one-opcode validation fixture can still fail closed
(D1P-35 §2; D1P-36). Consumer facts come from a checked relation: a v1.1 AST
relation, or a route-A relation for WarpToad. The AST frontend supports a
bounded statement and expression subset, one verifier boundary per
consumer, and standard token calls matched by function type. The route-A
extractor supports one entry point's reachable constructs with OpenZeppelin
5.6.1 effects. Neither handles proxies, delegate calls, inline assembly or
reentrancy, and both assume standard atomic ERC-20 behavior. Unsupported
inputs stop with a named reason. That keeps results honest but bounds
applicability. On the benchmark, 14 of 30 mutants were unsupported
(§VII-C). On independently developed projects, D1P-33 completed 0/4
analyses and D1P-36 completed 0/8, so no rule ran on any of them (§VII-E).
The stopping reasons were:
- compiler identity (beta.3, beta.19, beta.21 and beta.25 across the two
  versions);
- `MultiScalarMul`;
- `RecursiveAggregation`;
- the beta.21 MemoryOp encoding; and
- a consumer with two verifier boundaries.

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
v1.3 bounds literal success-path intervals exactly and keeps the named
widening limitation for every other loop (D1P-40 §3.3).

**Selector-prefix inference (removed in v1.3).** When the producer has more
public leaves than the verifier's direct array, v1.1 and v1.2 inferred a
prefix width from array widths. For Payy this gave a two-word selector
prefix (D1P-34 §2). D1P-40 confirmed that width arithmetic alone cannot
tell a prefix from a suffix, an interleaving or verifier-supplied
constants. v1.3 therefore fails closed unless the full-width identity is
established. Payy's mapping may well be correct, but it is unproved, and an
implementation-fact certificate for it is pending **[PENDING AI 1]**.

**Localization.** In v1.1, WarpToad consumer-side warnings carry no source
line (`WarpToadCore.sol:?`), and R-EFFECT reports the first modeled effect,
which on Payy is an unrelated write. v1.2 fixed both by reporting-only
changes (D1P-35 §3; §V-G). A verifier call with more than one source
occurrence still prints `:?`. Producer warnings are not mapped to Noir
source spans.

**Hash semantics.** Poseidon2 is modeled at most as a functional
uninterpreted tuple function (equal inputs give equal outputs), with no
injectivity or collision resistance (D1P-19 §2.2). v1.1 does not reason
about hash semantics at all. Validation uses real hashes. Any conditional
no-collision argument (B02 §3) is outside this paper's results.

**Conditional binding and dynamic memory.** No version has
activation-condition reasoning. v1.1 caught Payy's tail because it counted
memory-initialized tail words as unused. D1P-40 showed that dynamic reads
can select them, so v1.3 reports them as `UNKNOWN`. A word constrained
under a witness-controlled predicate, or reachable only through a dynamic
memory read, cannot be classified as bound or unbound. Path-conditional
binding is Milestone 2 **[PENDING AI 1, M2]**. Earlier ACIR and SMT
work on this pattern produced an analyzer false positive from unsound probe
specialization (later repaired) and general queries that did not finish
(T22, T22-v3, T22-v4).

**Validation coverage and causation.**
- *Witnesses.* D1P-30's E4 results replay witness constructions designed
  before D1P-30.
- *Harnesses.* The Lane X harnesses run without manual steps but are
  written per application. A new application needs its own harness before
  any of its warnings can be validated.
- *Causation contrasts.* All 9 WarpToad benchmark E4 grades rest on repair
  checks (EVIDENCE-LEDGER §3), and WT-S02 on a corrected experiment. Some
  honest controls come from earlier runs, and TE04 lacks a repaired-stack
  contrast **[PENDING AI 4]**.
- *Payy.* TE04 reaches E4 on-chain only for the inherited message-tail
  defect. No Payy benchmark mutation has its own E4. PY-C02 stops at E3 with
  its effect contained, and the six consumer rows are `E1+mock`.
- *Open warnings.* Of the 53 v1.1 benchmark warnings, 33 remain at E1.
- *Transaction scope.* Validation covers one consumer call from a fixed
  admitted pre-state, or a replay in a second call. Multi-transaction
  histories, front-running and observation of honest proofs are out of
  scope (B02 §3.1).

**Same-policy arm for WarpToad only.** D1P-32's same-policy Foundry harness
covers WarpToad's consumer and case targets. It is handwritten,
AI-authored, uses a stub verifier, and yields E1 counterexamples. No
same-policy harness exists for Payy or for circuit mutants. Those cells are
unresolved, so the comparison cannot show how a same-policy baseline would
do there.

**Held-out coverage; AI-assisted taxonomy.** The reserved frame has four
projects from one AI-prepared search, which is smaller than the frozen
plan. Neither frozen scan completed an analysis on them or on four unseen,
non-reserved projects (0/4 and 0/8). The binding constraints are
producer-frontend coverage (compiler identities, opcode payloads,
recursion) and consumer-boundary support. The taxonomy corpus covers one
seed endpoint, and its labels come from a single human annotator. No
inter-annotator agreement exists (§VII-F).

**No safety claims.** BindCheck never returns `VERIFIED_WITHIN_SCOPE` from
rule silence. Absence of warnings is E0 within the supported scope.

**Role correspondence.** No rule checks that a bound word plays the
*right* role, state map or domain. Examples are a root checked against the
wrong map (WT-S05), a swapped root relationship (WT-C05), and a domain word
that authorizes a mint without being its operand (WT-C03, WT-C07). This is
Milestone 2 **[PENDING AI 1, M2]**.

**Not novel by itself.** Several ingredients are prior work:
- integration-layer failures [1];
- rich circuit specifications [3, 4];
- computation–constraint consistency [5]; and
- unused-public-input detection [15].

Unused-variable lint already names every circuit-side mutant that BindCheck
detects on our benchmark (D1P-32; §VII-D). A handwritten policy harness
catches more consumer-side mutants on WarpToad (D1P-32). The unjoined union
of BindCheck's own two halves detects as much as the full tool (D1P-41).

Our claim is limited to the *automated* join of both sides, which names the
consumer effect at risk without a per-application policy, together with its
real-proof validation, to the extent that RQ1–RQ4 support it.

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
  deadline, as the CFP requires [8]. D1P-33 and D1P-36 emitted no warning,
  so there was nothing to disclose and no maintainer was contacted.
  Protocol v2 requires a confirmed defect to be disclosed before any
  submission claim, and contacting a maintainer requires explicit
  authorization **[PENDING AI 3]**.
- **New tool.** BindCheck's validation routes produce working forged proofs
  against local deployments. Misuse risk: an attacker could use validated
  warnings against live systems. Mitigations: validation runs only on
  owned-local chains with fresh deployments. The Lane X harnesses
  do synthesize attack witnesses and forged proofs. They do so only for our
  two development applications (WarpToad, and the PY-C02 build in TC02 and
  TE04) and
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

AI use is integral to the methodology and is described explicitly, as the
CFP requires [8].

- **Code, reports and text.** AI agents wrote code, task reports, the B02
  obligations, screening notes and draft text.
- **Tools and harnesses.** They wrote BindCheck v1.1 to v1.3 (D1P-34,
  D1P-35, D1P-40), the validation harnesses and repair checks (TC02, TE04,
  TE05, EVIDENCE-LEDGER), and the D1P-32 Foundry policy harness. D1P-32
  records no human inspection of that policy harness.
- **Runs.** They ran the D1P-33 and D1P-36 held-out scans and the D1P-41
  ablation, and drafted the independent-evaluation protocol v2.
- **Taxonomy screening.** An AI agent screened the taxonomy seed corpus and
  suggested cause labels. Those suggestions are `ASSUMED` and are not
  annotation.
- **Taxonomy labels.** The human labels were made by one author. An AI
  assistant helped that author understand source bug descriptions. It saw
  no AI-suggested labels and chose no labels (v1-agreement). AI systems are
  excluded from final labeling and adjudication.
- **Held-out list and draw.** An AI planner prepared the held-out candidate
  list from names and URLs only. A human custodian performed the draw
  outside every agent session.
- **Policy review.** The author policy review of validated effects was
  assisted by an external AI advisor and replayed no experiment.

Authors inspect every claim, citation, label and result. **[TODO]** Write
the disclosure from the preserved task prompts and reports.

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
pair, not of either component. BindCheck makes part of this agreement
checkable without application identifiers. It counts proof-enforced uses of
each public input, lowers the consumer's compiler AST from the verifier's
interface type to guards, state writes and token effects, and applies
generic rules.

**Correctness (development evidence).**
- *Facts:* an audit on compiled controls found five extraction defects in
  the analyzer behind our benchmark results. After repair, 11 of 30 mutants
  are detected, 19 are unsupported and none is missed, and all detections
  are WarpToad. The historical Payy bug is `UNKNOWN` to the static analyzer.
- *Causation:* real proofs still show the Payy tail, M-DOM and M-SRC
  causing unauthorized committed effects, each with a contrast on a version
  without the defect. The same holds for 9 of the 13 surviving WarpToad
  warnings through repair contrasts. No Payy mutation has its own E4.
- *Open:* a frozen corrected tool, a Payy fact certificate and Milestone 2
  (path-conditional binding, role correspondence) **[PENDING AI 1; AI 1,
  M2]**.

**Novelty (narrow).** The join detects nothing that BindCheck's unjoined
halves miss. Compiler lint and ZKAP cover unused public inputs, and a
same-policy harness beats BindCheck on consumer-side mutants. What remains
is the automated circuit-to-consumer join, which names the effect at risk
without a per-application policy. No verified prior tool does that, within
a bounded search. Final ablation and held-out comparison are pending
**[PENDING AI 2]**.

**Generality (untested).** Two frozen scans of independently developed
Noir/EVM projects completed no analysis: 0/4 and 0/8, so no rule ran. They
show where the tool's language and opcode support ends. They are not misses
or safety evidence. A preregistered independent evaluation is the next
step. It has about 30 candidates, about 10 reserved families and a separate
development pool, and it is awaiting approval **[PENDING AI 1, AI 3,
HUMAN]**.

**Taxonomy.** One human annotator has labeled the seed corpus. A second
annotator and a fixed precedence rule are needed before any recurrence
claim.

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
| Benchmark: 16/30 detected, 14 unsupported, 0 missed; 53 warnings (20 related, 33 inherited) | D1P-34 §§1, 5 | Tool output (E1) with post-run adjudication, development; superseded prospectively by D1P-40 |
| Five extraction defects confirmed and repaired; benchmark 11/19/0, 13 warnings; Payy tail and mapping `UNKNOWN` | D1P-40 §§1, 3, 5; `tests/test_bindcheck_d1p40.py`; ignored `results/raw/D1P-40/final-04/` | Source- and model-confirmed on compiled controls; development; v1.3 not frozen |
| Benchmark index validation: 1 preserved E4, 52 E1 | D1P-34 §5.1 | Automatic audit of preserved evidence; no new proof |
| Validation of 53 v1.1 warnings, ledger grade: 8 E4 + 1 preserved E4 (all with repair contrasts), 5 E3, 6 E1+mock, 33 E1 | EVIDENCE-LEDGER §§2–3; AUTO-VALIDATE (lane grade 10 + 1 + 4 + 6 + 32); ignored `results/raw/X-AV/v11/`, `results/raw/REPAIR/` | Locally reproduced (injected), per-application harnesses with repair checks; development |
| WT-S02 original run is a setup artifact; corrected run isolates the K1 defect | EVIDENCE-LEDGER §7; ignored `results/raw/REPAIR/s02-corrected/` | Locally reproduced (injected) |
| PY-C02 own mutation: real proofs at both levels, original and repaired reject, on-chain containment | TC02; TE05; EVIDENCE-LEDGER §6 | Locally reproduced (injected), E3 |
| Inherited Payy tail defect on-chain: real verifier, pinned consumer, forged burn 7 units | TE04; ignored `results/raw/TE04/`; policy review | Locally reproduced, E4 for the inherited historical defect; repaired-stack contrast not recorded |
| Case-mechanism causation contrasts | T19 §§1–3 (Payy repaired); D1P-15 §6.2 (M-DOM pinned circuit); D1P-19 §4.2 (M-SRC pinned consumer) | Locally reproduced |
| Held-out scan v1.1: 0/4 completed analyses (no rule ran), 0 warnings; frozen files unchanged | D1P-33; ignored `results/raw/D1P-33/manifest.json` | Tool output under freeze; capability limitation |
| v1.2: beta.15–21 container dispatch and reporting-only locations; 35-target rerun unchanged except 20 locations | D1P-35; ignored `results/raw/D1P-35/` | Development tool change, frozen by manifest |
| Held-out scan v1.2: 0/8 completed analyses (no rule ran; Set A second attempt, Set B unseen non-reserved), 0 warnings | D1P-36; ignored `results/raw/D1P-36/manifest.json` | Tool output under freeze; capability limitation |
| Noir lint names all 9 circuit-side BindCheck detections (6/6 under v1.3) | D1P-32 per-mutant table; D1P-34 §5; D1P-40 §5 | Tool outputs compared under frozen scoring |
| Join adds no detection over the unjoined union (6/8 each); one extra effect-naming example | D1P-41 §4; `protocols/d1/d1p-41-ablation-preliminary.json`; ignored `results/raw/D1P-41/` | Preliminary ablation on exposed examples; uncorrected analyzer |
| No verified automated circuit-to-consumer joint tool found; ZKAP covers unused public inputs | D1P-41 §6 | Bounded primary-source search; absence not proved |
| Benchmark baselines, including the Foundry same-policy harness and the Mythril retry | D1P-32; ignored `results/raw/D1P-32/` | Tool output, scored under the frozen plan |
| Baselines on the case targets | D1P-22 record; ignored `results/raw/D1P-22/` | Tool output, scored under the preregistered plan |
| v1 history: 13/30, 16 unsupported, 1 miss | D1P-31 §§1, 4 | Tool output, superseded |
| 30 mutants compile; reachability checks | BENCHMARK.md §§3–4; `manifest.json` | Build observation (development) |
| Contract revision 3 | D1P-31 §2; contract change log | Controlling document |
| Taxonomy seed corpus (27 screened; AI 19 included, 15 families) | v1-corpus.md; v1-corpus-ledger.json | AI-assisted extraction |
| Human labels: 17 included (13 families); κ vs AI 0.83 for inclusion, 0.35 for cause | v1-agreement.md; v1-blind-labels.md | Single human annotator, AI help with understanding disclosed; not inter-annotator |
| Held-out mini-draw commitment (8 candidates) | reservation-commitment-2026-10-28.json | Custodian-reported; signature pending |
| Independent held-out evaluation (about 30 candidates, about 10 reserved); one-third draw support | [protocol v2](../docs/evaluation/independent-protocol-v2.md) (SHA-256 `cd80f5f7…`); `scripts/taxonomy/reserve_families.py --fraction`; `scripts/taxonomy/test_reserve_families.py` (9/9) | Final text for approval, approvals empty; not executed [PENDING AI 1, AI 3, HUMAN] |
| Frozen v1.3; five-target rerun; Payy fact certificate; WT-C02 reconciliation | — | [PENDING AI 1] |
| Milestone 2: path-conditional binding and role correspondence | D1P-40 §8; D1P-41 §1 (motivation only) | [PENDING AI 1, M2] |
| TE04 repaired-stack contrast; combined-mutant Payy E4 | — | [PENDING AI 4] |
| Final ablation on frozen tool; held-out baseline arms | — | [PENDING AI 2] |
| Second annotator and inter-annotator agreement | — | [PENDING HUMAN] |

---

## Open items for authors

1. **Lane key.** Confirm the AI 2 assignment (assumed here to be the novelty
   and baseline comparison, consistent with D1P-41).
2. **Tool of record [AI 1].** Freeze v1.3, or its successor after Milestone
   2, by tag and hash manifest. Rerun the five case targets and reconcile
   WT-C02's occurrence count. Decide which version the development tables
   report. Do all of this before protocol v2's reserved set is opened.
3. **Payy implementation-fact certificate [AI 1].** Establish a unique
   1,005-leaf mapping, or a per-leaf `UNKNOWN` blocker, and address/path
   evidence for `messages[1..999]` (D1P-40 §8). Until then the Payy static
   result stays `UNKNOWN`.
4. **Milestone 2 [AI 1, M2].** Path-conditional binding and role
   correspondence. Its scope and success criterion are not yet written down
   in the repository.
5. **Remaining validation [AI 4].** Add the TE04 repaired-stack on-chain
   contrast. Optionally rerun the honest controls for WT-S01, S02 and S06 in
   the same run as the attack. Combined-mutant Payy E4 is out of
   single-mutant scope.
6. **Reservation (2026-10-28).** Record a check that the four D1P-33 projects
   match the commitment opening (`514ad719…`), and add the custodian's
   signature. Record how D1P-36 Set B was selected, or state that it was not
   recorded.
7. **Protocol v2 [HUMAN, AI 3].** Fill the approval block against SHA-256
   `cd80f5f7…` with two planner approvals and the custodian's agreement.
   Commit the `--fraction` change (P1) before the draw.
8. **Final ablation [AI 2].** Rerun D1P-41 once on the frozen corrected tool
   with fixed input hashes (D1P-41 §8). Decide whether the WT-C08
   effect-naming result is worth a claim or only a mention.
9. **Taxonomy [HUMAN].**
   - Run a two-annotator round with a precedence rule fixed in the protocol.
   - Settle the availability-only inclusion question (CF-04, CF-05).
   - Record the human labels in the ledger.
   - The metadata-only access rule was not followed for the seed endpoint,
     so the custodian-sanitized flow is owed before the next round.
10. **Prior work.** Verify ZKAP's full bibliographic data. Decide whether to
    cite the Railgun audit and the token-guided flow-tracing paper (D1P-41
    §6).
11. **Policy harness review.** The Foundry same-policy harness has no
    recorded human inspection. A human should review it before the
    comparison is published.
12. **Citations.** CIVER and CCC-Check full texts remain unread. Supply
    copies and resolve each **[TODO-VERIFY]**.
13. **Presentation.** Draw Figure 1. Replace repository links with an
    anonymized artifact. Decide whether the held-out project names stay in
    Table 9.
14. **Human review.** Have a human author inspect every claim and citation
    (contract §10).

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

[15] H. Wen et al. "Practical Security Analysis of Zero-Knowledge Proof
Circuits" (ZKAP). USENIX Security 2024.
usenix.org/system/files/usenixsecurity24-wen_1.pdf. (Scope verified against
the PDF in D1P-41 §6. **[TODO-VERIFY: full author list, title and pages.]**)

[16] F. Wang. Ecne: automated verification of ZK circuits.
github.com/franklynwang/EcneProject. Software citation. (Property verified
against the repository in D1P-41 §6; version not pinned, tool not run.)

