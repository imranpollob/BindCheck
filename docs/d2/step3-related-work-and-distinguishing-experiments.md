# D2 Step 3 closest related work

**Version:** D2-03-v1, 2 November 2026

**Search boundary:** primary papers, publisher/conference pages, and author/tool
artifacts; no secondary-source scope claims

**Machine-readable matrix:**
[`related-work-matrix-v1.json`](related-work-matrix-v1.json)

This is a positioning and experiment-design record, not a literature-absence
claim. “The inspected source does not document X” does not mean that no tool,
extension, unpublished version, or later work can do X.

## ZKAP

[ZKAP's USENIX paper](https://www.usenix.org/system/files/usenixsecurity24-wen_1.pdf)
builds a Circuit Dependence Graph for Circom, expresses semantic vulnerability
patterns as queries, and implements nine detectors. Its unused-public-input
discussion directly overlaps R-BIND: it explains why a completely unused public
input may be changed at verification. The paper and
[public artifact](https://github.com/whbjzzwjxq/ZKAP) were accessible.

The inspected design analyzes circuits, not a checked Solidity consumer. That
supports a scoped input distinction, not a claim that ZKAP cannot be extended.
BindCheck cannot claim unused-input detection, dependence graphs, query-based
circuit patterns, or application-impact motivation as new.

**Smallest distinguishing experiment.** Hold a producer circuit and one
unbound public word fixed. Pair it with two checked consumers: one commits a
protected effect from the word and the other ignores it or uses it only in an
unprotected observation. Run ZKAP on an equivalent native Circom input, or label
and charge an adaptation. Give all arms the same mapping facts. A
consumer-specific predeclared effect/state association from the joined arm,
while the circuit-only report stays fixed, would establish added information on
that pair—not novelty by itself.

## CIVER

The [IEEE publisher record](https://ieeexplore.ieee.org/document/10646792/)
describes CIVER as a scalable modular technique using transformation and
deduction rules to verify properties over circuit signals. The
[public CIVER repository](https://github.com/costa-group/circom_civer) documents
weak-safety/determinism, tag specifications, explicit preconditions and
postconditions, `spec_fact` assumptions, and bottom-up modular verification.
The repository currently documents Circom 2.1.6 and lists R1CS, PLONK, and ACIR
as upcoming inputs. The publisher abstract and artifact were read; the full
publisher paper was not retrieved.

CIVER is a strong comparison for modular reasoning and rich circuit
specifications. Because users can state expressive properties, it is not enough
to say that the current artifact does not extract Solidity or accept the pinned
Noir version. Native frontend mismatch is unsupported, not an algorithmic loss.

**Smallest distinguishing experiment.** Freeze one language-neutral
state-identity or domain-identity obligation. Give CIVER the smallest equivalent
pre/postcondition on a native Circom version, and, if needed, run a clearly
labeled CIVER-style modular adaptation on the shared extracted relation. Give
BindCheck the same policy information and count every role. Compare property
lines, annotations, adapter lines, authoring/correction time, runtime, evidence
grade, and effect/state localization. The proposed contribution survives only
if BindCheck derives a useful association under materially less manual
information or produces a diagnosis unavailable under equal inputs.

## CCC-Check

The [author-hosted CCC-Check paper](https://vdb.space/papers/zkp2026.pdf)
defines a Domain Consistency Model that relates prover computation to verifier
constraints and implements abstract-interpretation value inference. It states
that its CirC IR frontends include ZoKrates, Noir, and Circom. The
[public artifact](https://github.com/ArmanKolozyan/CCC-Check) contains the
analysis, tests, evaluation data, and a documented Circom end-to-end script.
Both full text and artifact were accessible.

This is important overlap: CCC-Check can address producer semantic defects that
simple occurrence counting misses. Its “two sides” are computation and
constraints, whereas BindCheck's proposed relation is circuit and application
consumer. The inspected full text contains no Solidity consumer analysis, but
exact overlap on Payy and WarpToad remains an experiment. The repository's
Noir/ACIR version compatibility must not be assumed.

**Smallest distinguishing experiment.** Use two axes. In axis A, mutate prover
computation versus constraints while holding the consumer fixed. In axis B,
mutate only the consumer state/role relationship while keeping producer
computation and constraints byte-identical. Run CCC-Check natively or through a
predeclared charged adapter, and validate every candidate by the same process.
CCC-Check receives full credit for axis-A producer inconsistencies. A
predeclared axis-B diagnosis would isolate the extra consumer information only
if the producer is genuinely unchanged and transformation controls pass.

## SmartAxe

The [author-hosted SmartAxe paper](https://people.cs.umass.edu/~juanzhai/papers/fse24liao.pdf)
is a close structural analogue. It analyzes EVM bytecode on both sides of a
bridge, normalizes heterogeneous access controls, infers protected resources,
and builds cross-chain control-flow and data-flow graphs to find cross-bridge
semantic inconsistency. Its
[artifact index](https://github.com/InPlusLab/FSE24-SmartAxe) links datasets and
the downloadable tool. The full paper and artifact index were accessible; the
tool was not executed here.

SmartAxe does not consume a ZK producer relation in the inspected paper, but it
already performs cross-program semantic alignment. BindCheck therefore cannot
claim cross-component graphs, resource-to-check association, or semantic
inconsistency joining as new. The pinned same-chain WarpToad fixture may not
satisfy SmartAxe's deposit/withdraw pairing assumptions; such a native-scope
failure would be unsupported, not missed.

**Smallest distinguishing experiment.** If a real paired bridge enters the
permitted development pool, run SmartAxe natively. In parallel, implement a
strongest-simple-composition baseline over BindCheck's extracted graphs using
SmartAxe-like role/domain/state alignment. Freeze semantic swaps and no-op
renamings before output. Count bridge pairing, adapters, labels, warnings, and
transformation stability. If a simple graph composition matches the typed join,
the proposed contribution must narrow to circuit-specific proof semantics or
validation rather than joining itself.

## ELSA

The official [ISSTA 2026 ELSA page](https://conf.researchr.org/details/issta-2026/issta-2026-research-papers/131/Augmenting-Multi-Technique-Static-Analysis-with-Large-Language-Models-A-Neuro-Symbol)
describes an Ensemble LLM-assisted Static Analysis method with
constraint-guided semantic reasoning and conflict resolution across multiple
analyzers. Critically, the official abstract says the evaluation includes
self-constructed ZKP-based smart contracts as well as three open-source
datasets. The official page exposed presentation slides. A full paper and
artifact were not located in the bounded primary-source search.

ELSA is therefore an unresolved closest-work item. The accessible abstract is
not enough to say whether it consumes circuit constraints, joins them to
consumer effects, or analyzes only contract code. It is equally insufficient
to claim overlap proves or disproves BindCheck's novelty.

**Smallest distinguishing experiment.** First obtain and pin the paper,
artifact, analyzer versions, models, prompts, stochastic settings, ZKP
contracts, and labels. Then use the same exposed source bundle and paired
consumers with a byte-identical circuit. Count every prompt, label, model call,
token cost, and analyst correction. Score relationship localization,
irrelevant warnings, and E1-to-E4 validation identically. If the two tools
receive different circuit or policy information, the run is not a comparative
capability result.

## Cross-work decision rule

The Gate A comparison should not ask whether BindCheck can run where a foreign
frontend cannot. It should ask whether the proposed relation adds a predeclared,
transformation-stable diagnosis under equal facts and policy information. At a
minimum it needs:

1. the current full arm;
2. producer-only and consumer-only arms;
3. their strongest simple union/composition;
4. a transformation control that changes names without changing semantics;
5. a relationship mutation that changes semantics while preserving local use;
6. applicable native closest tools and honestly labeled adaptations;
7. generic/default and same-policy arms where the tool exposes them; and
8. identical candidate validation and evidence grading.

If a simple composition or closest tool matches the relationship diagnoses,
the contribution narrows. If no arm reaches E4 automatically, the capability
gate remains open regardless of E1 differences.
