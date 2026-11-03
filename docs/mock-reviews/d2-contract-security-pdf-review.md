# PDF-only contract-security review: BindCheck D2 evidence status

## Artifact binding and review boundary

- Reviewed artifact: `/Users/imranpollob/Coding/bc/bindcheck-d1-paper/output/pdf/bindcheck-d2-evidence-status.pdf`
- SHA-256: `1697834e0c47de365ad04f8a1108dfd21555af5c7af9e697759d44e5b9f1e12d`
- Page-count check: `pdfinfo` reports 9 pages. I rendered and visually inspected all 9 pages; the sequence runs from Page 1 through Page 9 with no missing or duplicated page. The PDF is legible, and I found no clipping or table overlap that changes the security claims.
- Review scope: contract security and threat models only. I reviewed only the bound PDF. I did not inspect its source Markdown, repository, internal evidence-map targets, ledgers, reports, implementation, git history, or prior conversation.

This boundary is material. The PDF names internal hashes and records, but those references are assertions from the PDF for purposes of this review. I could not verify the referenced artifacts, recompute their hashes, replay an experiment, or determine whether a hash was externally timestamped or independently witnessed.

## Precise contribution

The proposed contribution is an end-to-end method for deciding whether a zero-knowledge proof authorizes a concrete contract effect by joining four kinds of information: producer constraints, decoded public-value identity, consumer reliance/effect identity, and a reviewed policy. The intended system would recover those facts automatically, derive a relational mismatch without embedding the expected verdict, and validate a candidate through a real proof to a committed policy-violating effect (pp. 1-2).

The PDF does not establish that proposed contribution. The contribution currently supported by the PDF is narrower and primarily methodological:

1. an exposed-development E1 diagnostic interface that associates bounded producer and consumer facts;
2. mechanical prototypes for opaque object/context identity, a shared authorization-boundary schema, and typed fact/provenance records; and
3. a fail-closed result showing that the corrected extractor derives neither an eligible producer authorization guarantee nor an eligible exact consumer-reliance fact, so both comparison arms remain effectively `UNKNOWN` (pp. 3-4, 8).

That is a useful clarification of where proof-to-execution reasoning can become unsound. It is not yet evidence that the system can discover a contract authorization defect, distinguish it fairly from existing approaches, or establish the absence of such a defect.

## Strongest evidence in the PDF

The strongest consequence evidence is the historical Payy reproduction: the PDF says a real-proof chain reproduced a publicly disclosed mechanism, reached a committed local effect, and included a repair contrast (p. 5). This is relevant evidence that this class of binding failure can have an execution consequence. It is explicitly post-disclosure, artifact-specific, and independent of the current warning set, so it does not support automated discovery, transfer, or validation of the current analyzer.

The strongest evidence about the current design is negative and fail-closed. The corrected typed-extraction run reports zero eligible `producer_guarantee` facts and zero eligible derived `consumer_used` facts; candidate relations remain annotated over-approximations, and both arms return `UNKNOWN` (pp. 3-4). The PDF also reports that an earlier sealed run was found to have incomplete operand replay, omitted serialized mapping-certificate replay, and an overstated caller-linked effect relation. Preserving that correction is valuable evidence that the authors are detecting unsound semantic promotion in their own pipeline. It is not evidence that all similar promotion errors have been eliminated.

The 30-mutant exposed benchmark and 7/7 versus 5/7 corrected ablation are weaker evidence. They show behavior on known, development-exposed targets and motivate a relational comparison, but the PDF correctly states that they do not estimate precision, recall, prevalence, transfer, or comparative advantage (pp. 4, 7).

## Security and threat-model concerns

### 1. The most important semantic step remains inside the trusted boundary

The threat model says the analysis may rely on "sound supported extraction" and correct artifact/key/configuration provenance (p. 2). Yet extraction soundness and provenance are among the central properties the proposed contribution must establish. The PDF later says the prototypes do not prove extraction soundness, arbitrary compiler or ABI identity, or a formal authorization theorem; the authoritative extraction run also executes no compiler or proof system (pp. 4, 6-7).

- Evidence status: evidence is missing from the PDF; there is no direct contradictory result. The text consistently treats current results as `UNKNOWN`. The concern is that a future `VERIFIED_WITHIN_SCOPE` result would be circular if extraction soundness were assumed rather than established.
- Why it matters: an omitted, mistranslated, or misidentified producer/consumer fact can turn a real violation into apparent authorization. Fail-closed handling helps only if every unsupported semantic case is reliably recognized as unsupported.
- What would resolve it: define a formal source-to-fact relation and explicit soundness obligations for each supported instruction, compiler lowering, ABI decode, control-flow case, and effect. Supply translation validation or a mechanized proof for the supported fragment, plus adversarial differential tests against compiler/runtime traces. State separately which parts remain trusted.
- Verification limit: the PDF-only review cannot inspect extractor code, generated facts, compiler outputs, or the hashes listed on p. 4.

### 2. Policy and protected-effect ground truth are absent

The authorization judgment depends on permissions, obligations, protected effects, and an independently reviewed specification (pp. 1-2). The current fixtures use an `UNREVIEWED_DEVELOPMENT_FIXTURE`; Gate A lacked both a policy author/adopter and an independent reviewer; and the consumer relation does not establish that the supplied protected-effect identity denotes the exact AST effect occurrence (pp. 3-5).

- Evidence status: evidence is missing, not contradicted. The PDF explicitly reports the absence and does not claim a current policy verdict.
- Why it matters: exact identity matching cannot establish authorization if the policy is wrong, incomplete, or attached to the wrong effect. The same trace can be classified differently depending on asset semantics, allowed callers, replay rules, state version, and discharge conditions.
- What would resolve it: use a concrete application with a policy authored or adopted by a domain owner and independently reviewed before scoring. Bind every policy element to an exact deployed entry point, state variable or external effect, asset model, activation condition, and allowed trace. Include disagreement/adjudication records and negative controls in which only policy/effect identity changes.
- Verification limit: no policy packet, reviewer record, or exact effect mapping is present in the PDF, and the review boundary forbids following the p. 9 evidence map.

### 3. "Compiler-backed identity" is mechanically tested but not authenticated end to end

The identity prototype hashes semantic object/context fields and preserves provenance separately. Four bounded transformations and several mismatch controls pass, but the PDF says the logical slots are unreviewed fixture annotations and compiler provenance does not establish object authenticity or policy correctness (p. 3). It also does not identify a deployed bytecode hash, verifier key, circuit hash, compiler build, ABI, chain ID, or deployment address for a current end-to-end case.

- Evidence status: evidence for the narrow hash/reference mechanics is reported; evidence for authentic source-to-deployment identity is missing. No evidence in the PDF contradicts the narrow mechanical claim.
- Why it matters: artifact substitution, stale verifier keys, mismatched circuit/ABI versions, proxy upgrades, or a source-versus-bytecode mismatch can preserve local reference consistency while binding the analysis to the wrong program.
- What would resolve it: publish a signed manifest connecting source revision, compiler and flags, circuit/constraint hash, proving and verification keys, ABI, deployed runtime bytecode/code hash, address, chain ID/fork, and analysis inputs. Add deliberate substitution and downgrade tests that must become `UNKNOWN` or fail validation.
- Verification limit: the hashes printed in the PDF identify claimed records but do not, by themselves, prove origin, timing, immutability, or correspondence to deployed execution.

### 4. The decode relation is underspecified for contract-security failures

The paper introduces `D_v(p,x)` as the actual mapping from accepted public values to consumer values (p. 1), but the PDF gives no current evidence for endianness, field-modulus canonicalization, limb reconstruction, signedness, truncation, padding, range checks, calldata offsets, or duplicate/aliased public-input positions. These are precisely the representation boundaries at which a sound circuit statement can authorize the wrong contract value.

- Evidence status: missing evidence, not contradictory evidence. The PDF acknowledges that arbitrary ABI identity is not established and that matched reorder succeeds only through an explicit bijection.
- Why it matters: matching names or opaque identities above the decode layer does not rule out two encodings mapping to one consumer value, one field value mapping differently across runtimes, or an index/width mismatch.
- What would resolve it: specify `D_v` executable semantics for the supported ABI and field representation; prove or translation-validate the mapping; and test boundary values, non-canonical encodings, reordered/duplicated indices, width changes, zero/sign extension, and multi-limb values against actual verifier and EVM execution.
- Verification limit: no calldata, public-input vector, ABI trace, or runtime decode trace appears in the PDF.

### 5. The contract adversary and state model exclude many consequential attack paths

The attacker can choose witnesses, public inputs, proof bytes, calldata, transaction ordering, and accessible entry points (p. 2). The implemented boundary, however, is a finite one-transition, one-to-one fragment. The PDF expressly excludes or leaves unsupported aggregation, splitting, deferral, unbounded history, proxies, delegate calls, inline assembly, reentrancy, general external-call semantics, and arbitrary token behavior (pp. 3, 7).

- Evidence status: this is a declared scope limitation, not contradictory evidence. Evidence for security beyond that scope is absent.
- Why it matters: authorization failures frequently depend on replay/nullifier state, multi-call sequences, callbacks, upgrade state, token hooks, cross-domain ordering, or inconsistent state snapshots. A one-transition trace can be locally authorized while the multi-transition execution violates conservation, uniqueness, freshness, or atomicity.
- What would resolve it: define the exact chain/runtime semantics and attacker-controlled environmental inputs, then add multi-transaction traces for replay, front-running/order changes, state-version races, callback/reentrancy, proxy upgrades, external-call failure/reentry, and token-behavior variation. Each unsupported feature should have a demonstrated fail-closed path.
- Verification limit: the PDF provides no executable state-machine definition, deployment trace, or coverage argument over accessible entry points.

### 6. The historical E4 classification is not independently checkable from the PDF

The PDF calls the historical Payy reproduction E4 because it used a real proof, reached a committed local effect, and included a repair contrast (p. 5). Under the PDF's own evidence discipline, E4 also requires the necessary policy and causal evidence (p. 2). The PDF does not show the exact policy, pre-state, proof/public inputs, transaction receipt, state delta, effect identity, or causal isolation for that chain.

- Evidence status: the supporting evidence is missing from the PDF. This is an internal evidentiary tension, but not a direct contradiction: the required records may exist outside the PDF, and the PDF does not say that the historical case used the same unreviewed policy fixture as the later prototypes.
- Why it matters: a committed effect alone does not show that the effect was unauthorized, caused by the binding defect rather than another condition, or reachable under the declared attacker model.
- What would resolve it: include a self-contained case packet or independently verifiable archive with pinned artifacts, attacker capabilities, policy source/review status, pre-state, malicious witness, proof and public values, transaction/receipt, exact post-state effect, causal explanation, and a repair-only negative control.
- Verification limit: I cannot validate the E4 label from the PDF alone and did not inspect the historical artifacts.

### 7. The benchmark cannot support practical miss, safety, or transfer claims

The 30 targets are authored or known variants from two exposed lineages. Thirteen are classified unsupported, including all 12 Payy mutants; "zero misses" counts only supported, predeclared targets that lacked a frozen association (p. 4). Earlier independent scans completed zero supported analyses (pp. 5-6).

- Evidence status: evidence needed for recall, precision, independent transfer, and practical coverage is missing. The zero supported independent analyses are affirmative evidence against claiming demonstrated transfer. They do not contradict the PDF, which explicitly refuses that claim.
- Why it matters: excluding unsupported cases from the miss denominator is defensible for a component metric but does not measure how often the tool helps on contracts presented by users. For end-to-end security, an unsupported known-positive is still an unresolved case.
- What would resolve it: preregister a supported-fragment inclusion rule before seeing outcomes; evaluate a reserved independently developed family; report both conditional accuracy and unconditional coverage; and require human adjudication of warnings, unsupported cases, and safe controls.
- Verification limit: the PDF contains aggregate counts, not per-case outputs or a sampling frame, so label correctness and denominator construction cannot be audited here.

### 8. Equal hashes do not establish equal effective information or a fair comparison

The two arms receive identical input, policy, and fact hashes, and the proposed future comparison would count adapters, annotations, prompts, setup corrections, and human time (pp. 4, 7). Gate A had no eligible equal-information row, and no applicable closest-work experiment ran (p. 5).

- Evidence status: fair-comparison evidence is absent; no contradictory comparative result exists because no eligible comparison occurred.
- Why it matters: byte-identical inputs do not show that adapters expose the same semantics, that an arm does not embed target-specific knowledge, or that unsupported cases and setup labor are treated symmetrically.
- What would resolve it: freeze a common semantic input contract and adapter outputs; preregister target labels, applicability, prompts/configurations, and scoring; blind the implementation/scoring roles where possible; account for all setup and human effort; and run producer-only, consumer-only, unjoined, strongest-simple, full, same-policy, and applicable prior-work arms through the same E1-to-E4 route.
- Verification limit: no arm implementation, information-flow audit, or scored row is available in the PDF.

### 9. `VERIFIED_WITHIN_SCOPE` needs a stronger completeness obligation than the PDF currently supplies

The outcome means no violation exists within a declared supported model, bounds, and assumptions (p. 2). That negative claim requires more than sound warning generation: it requires complete enumeration of relevant entry points, protected effects, traces within the bound, and policy obligations, plus sound extraction and solving. The PDF supplies no such completeness argument and reports no current verified result.

- Evidence status: evidence is missing; there is no contradiction because the current verdict is `UNKNOWN` and the PDF warns against promoting mechanical `ESTABLISHED` to `VERIFIED_WITHIN_SCOPE`.
- Why it matters: an apparently supported analysis can be unsoundly reassuring if it overlooks one entry point, effect, decode path, or state transition.
- What would resolve it: state a theorem or auditable assurance case defining soundness and completeness for the supported fragment, including whole-program entry-point/effect enumeration and solver bounds. Add seeded safe and unsafe controls and demonstrate that any incomplete enumeration becomes `UNKNOWN`, never verified.
- Verification limit: no formal model, solver certificate, whole-program inventory, or negative-verdict replay is embedded in the PDF.

## Unsupported inferences to avoid

The PDF itself rejects most tempting overclaims. Based on its evidence, none of the following inferences is supportable:

- A current E1 warning denotes an exploitable or even reachable contract violation. The PDF contains contrary evidence: exact effect reliance and producer authorization are not derived.
- The 7/7 full-arm result establishes a relational advantage. Evidence is missing because the cases were exposed and no fair comparator or E1-to-E4 replay ran.
- The historical Payy E4 case validates the current warning set. The PDF directly separates the historical, injected, and current strata and says the historical chain was constructed after disclosure.
- "Zero misses" indicates security or recall. The PDF's denominator excludes unsupported targets, including all Payy mutants.
- Passing identity transformations establishes semantic equivalence or source-to-bytecode authenticity. Only bounded mechanical checks are reported.
- Identical hashes establish equal semantic information, external provenance, or immutability. They establish byte identity only if the referenced objects are available and recomputed; that was not possible in this review.
- `UNKNOWN` is a safe result. It is an explicit statement of insufficient evidence.

I found no direct evidence in the PDF that contradicts its narrow bottom-line claim: current capability remains unresolved. The dominant review issue is missing evidence, not an overstated final security verdict.

## Most consequential limitations

Ranked by effect on the security contribution:

1. There is no current end-to-end chain from automatically recovered facts to a real proof and exact unauthorized committed effect.
2. There is no reviewed policy or exact protected-effect grounding for the current prototypes.
3. Extraction soundness, source/compiler/ABI identity, and artifact provenance are not established, while some are placed in the trusted boundary.
4. The one-transition, one-to-one model excludes common contract behaviors that create authorization failures.
5. There is no eligible fair comparison or supported independent-family run, so advantage and transfer remain unmeasured.

The most probative next result would be one preregistered, hash-bound, independently reviewed application case in which the system derives a `MUST/EXACT/DERIVED/SUPPORTED` producer fact and an exact runtime-grounded effect-reliance fact, survives a paired semantic negative control, and carries the same candidate through a real proof to a policy-adjudicated committed effect. A matching safe/repair control and an unsupported-feature fail-closed control should accompany it. That would not by itself establish generality, but it would address the current missing center of the contribution.

## Verification limits of this review

This review verifies the wording, internal relationships, page count, and rendered presentation of the bound PDF only. It does not verify implementation behavior, experiment execution, the correctness of aggregate counts, the existence or contents of referenced records, the provenance or timestamp of internal hashes, external related-work characterizations, or any deployed-contract claim. Page references above refer to the PDF's printed page numbers.
