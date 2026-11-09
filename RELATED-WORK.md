# Related work and defensible contribution claims (Lane D)

**Date:** 2026-11-09. **Branch:** `zk-related`, base `feb5c19`.
**Scope:** read-only literature and artifact research. No analyzer rule, case,
baseline run, or verdict was produced. Handoff, commands, and limitations are in
[`reports/related/REPORT.md`](reports/related/REPORT.md).

**Evidence rule used here.** A row says *detects* only when a primary source
(paper text, official slides, or the artifact) documents that input and
property. *No input for that layer* means the tool cannot see the artifact that
contains the defect, so it cannot detect the defect without being extended. A
tool that was not run is never counted as missing a defect. Search negatives are
bounded to the queries in the report and are not proof of absence.

Every number below links to the file that produced it. Most numbers are produced
by [`reports/related/scripts/collect_evidence.sh`](reports/related/scripts/collect_evidence.sh),
whose outputs are in [`reports/related/evidence/`](reports/related/evidence/).

---

## 1. Bottom line

1. **No published analyzer was found that takes a ZK circuit, its verifier, and
   the consuming contract as joint input.** This bounded search confirms the
   earlier gap findings, and it now covers ELSA, the item the earlier checks
   could not resolve.
   - ELSA (ISSTA 2026) is the only published tool that claims "ZKP-based smart
     contracts". It analyzes Solidity only. Its artifact has
     [4,086 `.sol` files and 0 circuit or constraint files](reports/related/evidence/elsa-artifact-inventory.txt).
   - Its "ZKP" benchmark consists of seven classic SWC weakness classes
     [injected into ZKP-project contracts](reports/related/evidence/primary-text-greps.txt).
     These are not integration-layer flaws.
2. **The gap is documented, but naming it is not our contribution.**
   - The SNARK SoK already defines the integration layer and taxonomizes
     [13 integration vulnerabilities out of 141](reports/related/evidence/primary-text-greps.txt).
   - It gives the zkDrops nullifier field-alias double spend as an example.
   - It proposes "combined testing of Circom and Solidity" as future work.
   - The July 2026 tools study evaluates
     [six circuit tools on 70 Circom bugs](reports/related/evidence/primary-text-greps.txt)
     and explicitly leaves integrations to future work.
3. **Framing 1 (a better tool) is not defensible today.**
   - In the live analyzer, every P1 and P3 `VIOLATION` is decided from the
     consumer contract and the verifier's argument list alone.
   - The compiled circuit can only move a P1 role to `VERIFIED_WITHIN_SCOPE`
     (precision) or `UNKNOWN`. See [§5.1](#51-what-the-circuit-currently-contributes).
   - The strongest baseline is therefore a purpose-built contract-only rule, and
     it has not been built.
4. **Framing 2 (benchmark plus measurement) is defensible against the
   literature, but not yet on evidence.**
   - No existing ZK bug benchmark contains contract-layer integration cases.
     zkbugs has [140 entries, 0 located in a `.sol` file](reports/related/evidence/zkbugs-census.txt).
   - The benchmark, the measurement, and disclosed findings that the sentence
     would rest on do not exist yet in reviewed form.

---

## 2. Property legend

| Code | Defect class (BindCheck's [P1–P5 rules](TOOL-REPORT.md)) |
|---|---|
| **P1** | Unbound effect parameter: the consumer commits a transfer, mint, or burn whose recipient or amount the caller chooses, and the proof does not fix it. |
| **P2** | Missing context binding: chain ID, consumer address, or application domain is not bound to the proof. |
| **P3** | Replay-key aliasing or unbound replay key: the nullifier is not canonical modulo the field, is not checked or consumed, or is not bound to the proof. |
| **P4** | Verification-key defects: γ = δ = the default G2 generator, duplicate IC points, or a missing scalar-field guard. |
| **P5** | Public-input order or count mismatch among the consumer vector, verifier arity, and circuit public signals. |
| **R** | Relational mismatches: extent or prefix, mask, representation (field, integer, or bytes), or scope disagreements between what the circuit constrains and what the consumer relies on. Payy `agg_agg` is the historical example. |

Cell values: **D** = detects by documented design. **Part** = detects only a
one-layer precondition or a subset. **—** = no input for the layer that contains
the defect. **?** = unresolved from primary sources.

---

## 3. Matrix

### 3.1 Tools

| Tool (venue) | Inputs | Layer | Properties checked (primary source) | P1 | P2 | P3 | P4 | P5 | R | Artifact | Baseline? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **ELSA** (ISSTA 2026; PACMSE 3, ISSTA131; [DOI](https://doi.org/10.1145/3832222), [program page](https://conf.researchr.org/details/issta-2026/issta-2026-research-papers/131/Augmenting-Multi-Technique-Static-Analysis-with-Large-Language-Models-A-Neuro-Symbol)) | Solidity source. Mythril, Slither, and SmartCheck outputs. GPT-3.5-turbo prompts. A LoRA-tuned LLaMA-3.2-3B "translates" ZKP verification calls into semantic hints. | Contract only | 7 SWC classes: 101, 105, 107, 110, 121, 124, 128 ([slides B1](reports/related/evidence/primary-text-greps.txt)). The ZKP set is AST-injected SWC faults in 35 projects; 224 of 2,310 sampled. | ? (SWC-105 `isAuth(msg.sender)` is access control, not proof binding) | — | Part (SWC-121 is ECDSA signature replay, not nullifier aliasing) | — | — | — | [github.com/Anonymize-gitcode/ELSA](https://github.com/Anonymize-gitcode/ELSA) @`509c987`: Docker image; needs an OpenAI key. [Inventory](reports/related/evidence/elsa-artifact-inventory.txt): 0 circuit files; 2,311 `.sol` files under `datasets/ZKP_dataset`. | **Must cite and position.** Run in the generic arm if API access allows; recommended, not decisive. |
| **ZKAP** (USENIX Sec 2024; [paper](https://www.usenix.org/system/files/usenixsecurity24-wen_1.pdf)) | Circom source → circuit dependence graph | Circuit | 9 VDL detectors. Includes unconstrained signals and outputs, and explicitly the **unused public input** pattern ("UnusedPubInput"). | Part: flags a public input the circuit never constrains; cannot see a consumer effect missing from the vector | — | — | — | — | — | [whbjzzwjxq/ZKAP](https://github.com/whbjzzwjxq/ZKAP) @`fbd1ddd` | **Must**: circuit-only arm. It is unavailable in T23/T26 and must be installed. |
| **Circomspect** (Trail of Bits; [repo](https://github.com/trailofbits/circomspect)) | Circom source | Circuit | 14 lint passes, e.g. under-constrained signal, unused output, **non-strict binary conversion**, field comparison ([`doc/analysis_passes.md`](https://github.com/trailofbits/circomspect/blob/main/doc/analysis_passes.md)) | — | — | Part: in-circuit aliasing only (`Num2Bits` non-strict) | — | — | — | @`50010b6` | **Must**: circuit-only arm |
| **Picus / QED²** (PLDI 2023; [paper](https://eprint.iacr.org/2023/512.pdf)) | R1CS | Circuit | Uniqueness of outputs (under-constraint). Reports safe, unsafe, or unknown. | Part: a non-unique public output | — | — | — | — | — | [Veridise/Picus](https://github.com/Veridise/Picus) @`138b151`; last push 2024-03-13 | **Must**: circuit-only arm |
| **zkFuzz** (IEEE S&P 2026; [arXiv 2504.11961](https://arxiv.org/abs/2504.11961)) | Circom program | Circuit | TCCT under- and over-constraint, found by mutation fuzzing | Part | — | — | — | — | Part (circuit-internal only) | [Koukyosyumei/zkFuzz](https://github.com/Koukyosyumei/zkFuzz) @`c58639d` | **Must**: newest Circom tool at our target venue |
| **CCC-Check** (IEEE S&P 2026; [author PDF](https://vdb.space/papers/zkp2026.pdf), [ePrint 2025/2120](https://eprint.iacr.org/2025/2120)) | CirC IR (Circom, Noir, and ZoKrates frontends) | Circuit | Computation–constraint inconsistency via abstract interpretation. User preconditions express range checks. | Part | — | — | — | — | Part: circuit-side extent and range only | [ArmanKolozyan/CCC-Check](https://github.com/ArmanKolozyan/CCC-Check) @`7ed87b8` | **Should**, for the R class. A prior bounded build did not establish a runnable path ([D2 matrix](docs/d2/related-work-matrix-v2.json)). |
| **CIVER** (IEEE S&P 2024; [IEEE record](https://ieeexplore.ieee.org/document/10646792/)) | Circom | Circuit | Weak safety, tags, and pre/postconditions (artifact README; full text not retrieved) | Part (if a postcondition is written) | — | — | — | — | Part | [costa-group/circom_civer](https://github.com/costa-group/circom_civer) @`af7d4ed` | **Should**: same-policy circuit arm; charge specification effort |
| **Zequal** (CAV 2025; [ePrint 2025/916](https://eprint.iacr.org/2025/916)) | Circom and Gnark circuits | Circuit | Witness-generator versus constraint consistency (abstract) | Part | — | — | — | — | Part | No code link on the ePrint page; the PDF returned HTTP 403 to scripted fetch | Cite; record the baseline as not applicable (no located artifact) |
| **zkCraft** (arXiv [2602.00667](https://arxiv.org/abs/2602.00667), Jan 2026; no venue listed) | Circom R1CS plus LLM mutation templates | Circuit | Under- and over-constrained faults (TCCT) | Part | — | — | — | — | — | No repository link in the paper text | Cite only |
| **FreeVer** (USENIX Sec 2025; [page](https://www.usenix.org/conference/usenixsecurity25/presentation/peng-xinghao)) | Polygon zkEVM PIL and ROM free inputs | zkEVM | Free-input soundness and completeness against honest-prover semantics | — | — | — | — | — | — (zkEVM-internal) | — | Not applicable (no application consumer) |
| **SmartAxe** (FSE 2024; [arXiv 2406.15999](https://arxiv.org/abs/2406.15999)) | EVM bytecode of paired bridge contracts | Contract ↔ contract | Access-control incompleteness; cross-bridge semantic inconsistency over xCFG and xDFG | ? (access-control analog) | — | — | — | — | — | [InPlusLab/FSE24-SmartAxe](https://github.com/InPlusLab/FSE24-SmartAxe) @`7ca21f7` (tool on figshare) | Cite as the closest **cross-component** analog. Not applicable to non-bridge ZK apps. |
| **zkjac "Groth16 Setup Scanner"** ([Zeto issue #186](https://github.com/LFDT-Paladin/zeto/issues/186), opened 2026-04-05) | Committed Solidity verifier constants | Verifier | δ (and γ) equal to the BN254 G2 generator, i.e. no Phase-2 contribution. The issue reports all 20 Zeto verifiers. | — | — | — | **D** (γ = δ = G2 generator) | — | — | The linked `github.com/zk-audit/zk-audit` returned **HTTP 404** via the GitHub API on 2026-11-09 | **Must cite as P4 prior art.** It cannot be run; any comparison is a labeled reimplementation. |
| **snarkjs verifier template** ([iden3/snarkjs](https://github.com/iden3/snarkjs)) | — | Verifier | Current templates add `checkField` on public signals | — | — | Prevents the field-alias half on new verifiers | Part | — | — | — | Cite as the mitigation that bounds P3 prevalence |

### 3.2 Studies, benchmarks, and adjacent work

| Work | What it contributes | Relation to P1–P5 and R | Status |
|---|---|---|---|
| **SoK: What Don't We Know?** (USENIX Sec 2024; [arXiv 2402.15293](https://arxiv.org/abs/2402.15293)) | 141 vulnerabilities. Its integration layer has 13: 3 integration design errors and 10 missing input validation, of which 9 are "passing unchecked data" ([Table 5](reports/related/evidence/primary-text-greps.txt)). States "no specific defenses" for this layer and proposes "combined testing of Circom and Solidity". Appendix B.2 gives the zkDrops nullifier field-alias double spend. | V4 Passing Unchecked Data ≈ P3/P5 preconditions. V6 Proof Composition ≈ R. V7 Complementary Logic (nullifiers) ≈ P3. V10/V12 setup and unsafe verifier ≈ P4. **P1 and P2 are not named categories**, but they fall under integration design errors. | Full text read |
| **ZKP Security Tools and Verification** (arXiv [2607.23752](https://arxiv.org/abs/2607.23752), Jul 2026) | Six tools (Picus, Civer, Ecne, Circomspect, zkFuzz, ConsCS) on 70 Circom bugs: 45.7% detected on isolated circuits, 19.6% on whole projects. In its survey, 26% of practitioners rate system integration hard to detect and 5% rate it adequately covered ([greps](reports/related/evidence/primary-text-greps.txt)). Its only "integrations of ZKPs with smart contracts" citations, [87]–[89], are rollup papers. It leaves integration to future work. | Confirms that no evaluated tool targets P1–P5. It is a **template for a framing-2 paper**, by the same group. | Full text read |
| **zkbugs** ([zksecurity/zkbugs](https://github.com/zksecurity/zkbugs) @`212cc50`) | 140 reproducible entries: 70 Circom, 35 Halo2, and others. 123 are under-constrained. **0 entries are located in a `.sol` file** ([census](reports/related/evidence/zkbugs-census.txt)). | Circuit and backend only. It cannot serve as an integration benchmark. | Aggregate counts only (data wall) |
| **0xPARC zk-bug-tracker** ([repo](https://github.com/0xPARC/zk-bug-tracker) @`56a9966`; last push 2024-12-19) | A community list of bugs in ZK applications and circuits | Includes application-level cases. It is a narrative list, not an executable benchmark. | Not counted |
| **Tang et al.**, ZKP vulnerability analysis and security auditing ([ePrint 2024/514](https://eprint.iacr.org/2024/514)) | Audit methodology from the application layer down to infrastructure. A search snippet mentions a Semaphore "Missing Smart Contract Range Check". | P3/P4-adjacent manual guidance | Not read in full |
| **Fuzzing processing pipelines for ZK circuits** (CCS 2025; [DOI](https://doi.org/10.1145/3719027.3744791)) and **Lie to Me** (arXiv [2608.30648](https://arxiv.org/abs/2608.30648)) | Compiler, witness, and prover toolchain soundness | Out of scope (toolchain) | Abstract only |
| **Towards a formal foundation for blockchain ZK rollups** (CCS 2025; [DOI](https://doi.org/10.1145/3719027.3765115)) | Alloy model of L1 rollup contracts: governance, queues, upgrades | Contract-level rollup modelling. No circuit join. | Abstract only |
| **Source mapping for zkSolc** (ISSTA 2025 companion; [arXiv 2504.04322](https://arxiv.org/abs/2504.04322)) | Here "zero-knowledge smart contracts" means zkSync-compiled Solidity | A name collision only. Cite it to pre-empt confusion. | Abstract only |
| Protocol designs that add sender, `chainid`, or `address(this)` to public inputs (e.g. [arXiv 2606.20760](https://arxiv.org/abs/2606.20760)) | Design-time binding | Shows that P1 and P2 are **known design requirements** | From the earlier check |
| Veil Cash and FoomCash γ = δ incidents ([PoC](https://github.com/DK27ss/VeilCash-5K-PoC), [reproduction](https://crypto.training/hacks/2026-02-foomcash_groth16/)) | Exploited P4 in 2026 | P4 is a known, exploited class | From [feasibility/LITERATURE.md](feasibility/LITERATURE.md); not re-fetched |
| Coda (refinement types; [ePrint 2023/547](https://eprint.iacr.org/2023/547)) | Circuit specification and verification | Already listed by the research contract as prior work for semantic specifications | Not re-read |

**Fresh 2024–2026 search** (queries in the report): arXiv, IACR ePrint,
DBLP/venue pages via web index, audit-firm sites (Veridise, zkSecurity, Trail of
Bits, Zellic, OpenZeppelin), and LLM-audit benchmarks. **No additional joint
circuit+consumer analyzer was found.**
- [CyberChainBench (arXiv 2606.26216)](https://arxiv.org/abs/2606.26216) and
  other LLM smart-contract audit benchmarks are contract-only.
- An AuditAid vendor page was named by a search summary as cross-checking
  verifier public-input layouts. [The page itself](https://www.auditaid.io/zk-audit)
  contains no such statement, no tool, and no artifact.
- A SlowMist post on aliasing in Circom verifier contracts
  ([link](https://slowmist.medium.com/zkp-series-pseudonym-input-vulnerability-in-circoms-verification-contract-has-been-replicated-28fe3fb75ba8))
  returned HTTP 403. It is P3 prior art, unread, and must be read before
  submission.

---

## 4. Which P-classes are new, by the literature alone

| Class | Prior art | Novel as a *class*? | Novel as an *automated cross-layer check*? |
|---|---|---|---|
| P1 | Protocol designs bind recipients and senders (§3.2). The SoK's integration design errors. | No | No published tool found. **But the live check needs no circuit** (§5.1), so "cross-layer" is not what makes it work. |
| P2 | Protocol papers add `chainid` and `address(this)`. | No | No tool found. BindCheck decided 1 of 27 applicable DEV rows ([counts](reports/related/evidence/t25-dev-verdict-counts.txt)). |
| P3 | SoK Appendix B.2 (zkDrops alias), SoK V7, SlowMist post, snarkjs `checkField` | No | No tool found for the consumer half. It is a contract-plus-verifier fact. |
| P4 | Veil and FoomCash incidents, zkjac scanner, Zeto #186 | No | **No.** The zkjac scanner already automates γ = δ. |
| P5 | The SoK's "passing unchecked data" is adjacent | Partly (no named category) | Plausibly yes. It is the only live rule whose `VIOLATION` uses circuit facts. It has 0 DEV violations ([counts](reports/related/evidence/t25-dev-verdict-counts.txt)). |
| R | SoK V6 proof composition. CCC-Check and zkFuzz handle circuit-internal extent. | **Not found as a named class** | **Most novel by literature**, but the live analyzer does not implement it. The historical role mechanism now fails closed ([`role_binding.py:945`](../bindcheck-d1-paper/src/bindcheck_d1/role_binding.py)). |

---

## 5. Evidence that limits the claims

### 5.1 What the circuit currently contributes

The live analyzer was read at `feb5c19`:

- [`analyze_p1`](bindcheck_zk/analyzer.py) (lines 529–636) emits
  `UNBOUND_EFFECT_RECIPIENT` and `UNBOUND_EFFECT_AMOUNT` (lines 606–609). This
  happens only when the effect expression is caller-controlled and not among the
  verifier argument names. The circuit enters only through
  `_commitment_binding` (line 578), which can only add `compiled-commitment` to
  `bound_by` or add an `UNKNOWN` reason.
- [`analyze_p3`](bindcheck_zk/analyzer.py) (line 780) takes no circuit argument.
- Only [`analyze_p5`](bindcheck_zk/analyzer.py) (lines 881–895) can emit a
  `VIOLATION` from circuit facts: a count or order mismatch against
  `circuit.public_count` and `circuit.public_order`.

On the DEV ledger ([counts](reports/related/evidence/t25-dev-verdict-counts.txt)):

- There are 8 `VIOLATION` rows: 4 in P1 and 4 in P3. None of them can depend on
  circuit facts, by the code above.
- P5 has 0 violations.
- Circuit builds: 45 succeeded and 31 failed.

This matches the [claude-review](../reviews/claude-review.md) finding that the
joint reasoning made a difference once (SPSC, precision only).

### 5.2 Baselines are not yet a comparison

- [T26](reports/T26.md) (lines 115–116): Slither failed in native setup on all 5
  dry-run families. Circomspect, Picus, and ZKAP were unavailable. All 20
  baseline outcomes are `UNKNOWN`.
- The historical same-policy Foundry harness on the D1 WarpToad mutants
  ([`D1P-32/summary.json`](../bindcheck-d1-paper/results/raw/D1P-32/summary.json),
  `totals.foundry_same_policy`) scored detected 8, missed 1, and unresolved 21.
  That is a different analyzer line and authored mutants. It still shows that a
  property-test baseline is strong, not a strawman.

### 5.3 Measurement inputs exist only as candidates

- The deployed-verifier census
  ([`onchain-census-summary.json`](dataset/onchain-census-summary.json)) covers
  1,027 unique deployments.
  - 43 match the default-G2 γ = δ signature.
  - It has 0 source-confirmed consumer links and 0 funded vulnerable consumer
    instances.
- The consumer join
  ([`onchain-consumers-v2-summary.json`](dataset/onchain-consumers-v2-summary.json))
  covers 277 deployments from 86 GitHub repositories, with verdict `UNKNOWN`.
- The recall set and EVAL corpus were **not read** (data wall). Their sizes are
  reported only by the reviews and are not used here.

---

## 6. Answers

### (a) Defensible novelty sentences

**Framing 1: a tool that detects circuit–contract binding flaws better than
strong baselines.**

*Comparative sentence: **none defensible today**.* Reasons:

1. No baseline outcome has been adjudicated ([T26](reports/T26.md)).
2. The decisive comparator has not been built. That comparator is a
   purpose-built contract-only rule with the same role annotations.
3. By construction, every current DEV detection is reachable by that comparator
   (§5.1).
4. There is no held-out run.
5. A historical property-test baseline already outperformed static analysis on
   authored mutants (§5.2).

The scope sentence that *is* defensible today, with its hedges kept verbatim:

> "To our knowledge (bounded search as of November 2026), BindCheck is the first
> analyzer that takes a Circom circuit's compiled constraints, its generated
> Groth16 verifier, and the consuming Solidity contract as joint input, and
> reports for each protected effect whether the accepted proof fixes its
> recipient and amount, failing closed to UNKNOWN with a reason code
> otherwise."

This sentence claims scope and priority, not superiority. A reviewer will
immediately ask whether the circuit input changes any detection. Today it does
not (§5.1). The comparative sentence becomes writable only if a held-out
experiment shows detections, or precision at equal recall, that the
contract-only rule plus the circuit-tool union misses.

**Framing 2: a benchmark and measurement study of integration-layer flaws, with
a fail-closed checker and new findings.**

The literature supports this sentence, conditional on evidence:

> "We contribute the first executable benchmark of integration-layer flaws in
> Circom/Groth16 applications, where each case pins the circuit, the generated
> verifier, and the consuming contract with a vulnerable and repaired revision,
> and use it, together with a fail-closed checker, to measure how often
> proof-consuming contracts act on values the proof does not bind across N
> open-source applications, reporting K new, end-to-end validated and disclosed
> findings."

Why the literature supports it:
- zkbugs has [0 `.sol`-located entries](reports/related/evidence/zkbugs-census.txt).
- The tools study defers integration ([greps](reports/related/evidence/primary-text-greps.txt)).
- The SoK has 13 integration cases as a narrative taxonomy, not an executable
  benchmark.
- ELSA's ZKP set is injected SWC faults ([inventory](reports/related/evidence/elsa-artifact-inventory.txt)).

It is **not writable today**:
- N and K are MISSING. 0 held-out families have been analyzed, and 0 findings
  have been disclosed. Both E4 cases are in DEV hackathon code.
- The recall expectations are reported unreviewed.
- "Fail-closed" is methodology, not novelty. Picus already reports unknown.

**Recommendation.** Framing 2 is the stronger route. The novelty it needs is
backed by primary-source negatives, while framing 1's novelty hinges on a
capability that the current code does not exercise for detection. If framing 1
is kept, the relational class R (and P5) is the only place where joint reasoning
can matter for detection. That needs a live implementation.

### (b) Tools the paper must compare against

Each arm needs both a generic/default and a same-policy run, as the research
contract §9 requires. Not-run or unavailable outcomes are reported as such,
never as misses.

1. **A purpose-built contract-only detector** (Slither custom detector or
   equivalent). It flags any protected-effect argument that is not in the
   verifier argument list and not `msg.sender`, plus nullifier read, write, and
   `< r` checks. Every reviewer names it. Without it, framing 1 is dead on
   arrival.
2. **Slither** with default detectors, run on the consumer.
3. **Same-policy Foundry property or invariant tests** with valid-proof seeds,
   as the contract §9 requires and §5.2 shows to be strong.
4. **Circuit-only tools:** Circomspect, Picus, ZKAP, and zkFuzz. The first
   three were the SoK's named defenses; Picus, Circomspect, and zkFuzz were in
   the tools study, and zkFuzz is S&P 2026. Also run their **union with item 1**
   as the "unjoined union" ablation.
5. **BindCheck with circuit reasoning disabled.** This ablation isolates the
   joint contribution.

Strongly recommended:
- **ELSA**, generic arm. It is the only published tool claiming ZKP smart
  contracts, and its artifact is public.
- **CIVER**, same-policy, with postconditions charged as specification effort.
- **CCC-Check**, for the R class.

Cite, but record as not applicable with a reason:
- SmartAxe: bridge pairs only.
- FreeVer: zkEVM.
- Circuzz and Lie to Me: toolchains.
- Zequal and zkCraft: no artifact located.

For P4, cite the zkjac scanner. Its artifact returns 404, so any comparison is
a labeled reimplementation of its published check.

### (c) Strongest prior work a reviewer will cite, and our honest answer

1. **The SNARK SoK (Chaliasos et al., USENIX Sec 2024).** "The integration layer,
   its taxonomy, and the zkDrops alias are already known. Combined Circom and
   Solidity testing was proposed in 2024."
   *Answer:* Agreed on the problem. The SoK states there are "no specific
   defenses" for the layer. Our contribution must be the defense and/or the
   measurement, not the problem statement or a new taxonomy. P1–P5 should be
   presented as an operational refinement mapped onto SoK V4, V6, V7, V10, and
   V12, and P3 and P4 credited to the SoK and the 2026 incidents.
2. **A trivial contract-only rule.** This is not a paper, but every reviewer
   will raise it, and it is the strongest objection.
   "Your exploited bugs are missing-argument checks; Slither plus 20 lines finds
   them."
   *Answer:* Today this is correct for detection; see the code in §5.1. The
   circuit currently changes one DEV outcome, SPSC, and that is precision only.
   We either demonstrate held-out cases where only the circuit-aware analysis is
   right, especially commitment-bound effects, P5, and R, or we adopt framing 2,
   where the checker is an instrument and not the claim.
3. **ELSA (ISSTA 2026).** "A neuro-symbolic analyzer already handles ZKP-based
   smart contracts."
   *Answer:* ELSA reads Solidity only (0 circuit files in its artifact) and
   targets seven SWC classes injected into ZKP projects. It has no model of what
   a proof binds. Running it in the generic arm settles this empirically and is
   cheap.
4. **ZKAP's unused-public-input detector.** "Unbound proof values are already
   detected."
   *Answer:* ZKAP sees a public input the circuit ignores. P1 concerns an
   effect value that never enters the public vector, which the circuit cannot
   reveal. The two are complementary, which is why ZKAP belongs in the union
   ablation.
5. **The zkjac scanner, Veil, and FoomCash (2026).** "P4 is known and already
   automated."
   *Answer:* Agreed. P4 is a prerequisite check and must not be counted as a
   joint-analysis contribution.
6. **Kolozyan et al. 2026 (arXiv 2607.23752), and the same group's activity.**
   "This group will do integration next."
   *Answer:* Their paper explicitly defers integration. This is a priority risk,
   not prior art. It argues for submitting the framing-2 benchmark early,
   because a group with an established tools-evaluation template could publish
   it.
