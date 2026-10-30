# D1P-41 — preliminary novelty ablation

Date: 30 October 2026  
Task status: **DONE for the bounded preliminary ablation**  
Final-ablation status: **WAITING for AI 1's fact audit and a corrected frozen tool**  
D1 research verdict: **UNKNOWN**

## 1. Outcome

On nine pre-existing synthetic/development examples (eight positive examples
and one honest control), producer-only and consumer-only each match 3/8
positive expected outcomes. Their unjoined union matches 6/8. Full BindCheck
also matches 6/8. The current join therefore adds **no extra detected example**
over the unjoined union in this deliberately small set.

The join does add one narrower capability. On WT-C08, R-EFFECT relates the
producer-unbound `recipient_address` to the consumer's recipient mint. Relative
to the union, full BindCheck has one more related warning, names a consumer
effect on one more example (3/8 rather than 2/8), and reduces that example's
manual confirmation estimate from three substantive checks to two. The same
rule also adds one irrelevant Payy warning, so its aggregate delta is one
related and one irrelevant warning object.

This is E1 static-warning evidence. It is not a new `VIOLATION` result. In
particular, the WT-C08 zero-recipient execution is contained by the consumer
token implementation, and the current static join proves neither reachability
nor a committed effect. The clean control's silence is `UNKNOWN`, not
`VERIFIED_WITHIN_SCOPE`.

The highest-value deeper relationship suggested by these examples is a
**typed, policy-bearing boundary correspondence**:

```text
producer value/role and constraint relation
    ↔ decoded verifier word
    ↔ expected consumer state identity, domain, polarity, and effect authorization
```

Unlike direct occurrence or operand flow, that relationship could distinguish
the correct root map from a wrong one (WT-S05), the correct producer root
relationship from a swapped one (WT-C05), and a domain word that authorizes a
mint without being a direct mint operand (WT-C03/WT-C07). This is a candidate
next hypothesis, not a validated capability: extracting the expected role and
state identity without encoding the expected verdict remains the central
oracle problem.

## 2. Authority, merge, and preliminary boundary

The task followed, in order, `docs/research-contract.md`, `README.md`, the
immutable D1P reports (including D1P-34 through D1P-36), and the paper draft.
No material disagreement was found. D1P-35/36 supersede D1P-34's implementation
version with v1.2 format dispatch and source-location recovery while preserving
the non-location rule results; the research contract continues to require an
`UNKNOWN` D1 verdict.

`git merge --ff-only main` exited 0 and fast-forwarded the worktree from
`7915fd4` to `83a4d8d2e4d8bb6ef8b3be6c3f91126d2c9cf580`. No commit or push was
made by this task.

This ablation is explicitly preliminary:

- the fixtures and prior analyzer outputs were already exposed development
  material, not blind or held-out cases;
- AI 1 is auditing extracted facts in parallel;
- final conclusions require the same one-command run on the corrected, frozen
  tool; and
- the experiment changes no rule under `src/`.

The intended policies, reachable executions, and expected outcomes were frozen
before the first arm run in
[`docs/ablations/d1p-41-discriminating-examples.md`](../docs/ablations/d1p-41-discriminating-examples.md).
Exact paths and match predicates are in
[`protocols/d1/d1p-41-ablation-preliminary.json`](../protocols/d1/d1p-41-ablation-preliminary.json).
The protocol SHA-256 is
`aed5c82c286d265e215320d9a0f1f134e7ad2da2ec6f9754cd51fa6db31db151`.

## 3. Arms and scoring

[`scripts/d1p_41_ablation_preliminary.py`](../scripts/d1p_41_ablation_preliminary.py)
runs the unchanged current analyzer once per fixture and masks its fact/output
surface as follows:

| Arm | Available facts | Allowed current rules | Cross-layer synthesis |
|---|---|---|---|
| producer-only | public ABI/boundary and producer proof-enforced occurrence | R-BIND | none |
| consumer-only | public names as boundary metadata plus consumer guards, effects, state identities and replay facts; producer occurrences masked | R-CONSUMER, R-POLARITY, R-ANCHOR | none |
| unjoined union | set union of the preceding outputs | preceding rules | none |
| full BindCheck | both layers | all preceding rules plus R-EFFECT | R-EFFECT intersects producer-unused indices with consumer effect-word indices |

The derivation is valid for the current rules because the consumer-only rules
do not inspect producer occurrence counts and R-BIND does not inspect consumer
guard/effect facts. The runner asserts the exact masks and synthesizes no rule.

Detection requires a warning matching the predeclared rule and boundary, not
merely any warning on the target. “Effect named” requires a related R-EFFECT or
R-POLARITY warning. R-POLARITY names the protected replay-state write, but does
not name the downstream duplicate mint. Every other warning is counted as
irrelevant to the seeded example, even when it may describe a real inherited
issue.

The manual-confirmation estimate counts four substantive checks: producer
binding, consumer relation, intended policy, and reachable committed/contained
outcome. R-BIND credits the first; a related consumer-only rule credits the
second; R-EFFECT credits both. No current warning credits policy or execution.

## 4. Results

### 4.1 Aggregate

| Arm | Detection | Examples naming effect at risk | Related W | Irrelevant W | Mean remaining human checks | Clean control |
|---|---:|---:|---:|---:|---:|---:|
| producer-only | 3/8 | 0/8 | 3 | 1 | 3.625 | 1/1 matched |
| consumer-only | 3/8 | 2/8 | 3 | 1 | 3.625 | 1/1 matched |
| unjoined union | 6/8 | 2/8 | 6 | 2 | 3.250 | 1/1 matched |
| full BindCheck | 6/8 | 3/8 | 7 | 3 | 3.125 | 1/1 matched |

These denominators are the eight positive examples only. Warning counts also
exclude the clean control, which emits none in every arm.

### 4.2 Per example

`Y` means that the arm matches the outcome frozen before execution; `N` means
it does not. Parentheses give `effect named / irrelevant warnings / remaining
human checks`.

| ID | Frozen discriminator | Producer | Consumer | Union | Full |
|---|---|---:|---:|---:|---:|
| E1 WT-C08 | producer gap, word directly consumed by mint | Y (N/0/3) | N (N/0/4) | Y (N/0/3) | **Y (Y/0/2)** |
| E2 WT-C03 | producer domain gap, no direct effect operand | Y (N/0/3) | N (N/0/4) | Y (N/0/3) | Y (N/0/3) |
| E3 WT-S03 | consumer ignores replay word | N (N/0/4) | Y (N/0/3) | Y (N/0/3) | Y (N/0/3) |
| E4 WT-S09 | correct absence check, missing write | N (N/0/4) | Y (Y/0/3) | Y (Y/0/3) | Y (Y/0/3) |
| E5 WT-S05 | consumer checks wrong state maps | N (N/0/4) | N (N/0/4) | N (N/0/4) | N (N/0/4) |
| E6 WT-C05 | producer uses wrong root relationship | N (N/0/4) | N (N/0/4) | N (N/0/4) | N (N/0/4) |
| E7 WT-C07 | producer domain gap, indirect mint risk | Y (N/0/3) | N (N/0/4) | Y (N/0/3) | Y (N/0/3) |
| E8 PY-S01 | missing admission check plus inherited findings | N (N/1/4) | Y (Y/1/3) | Y (Y/2/3) | Y (Y/3/3) |
| E9 pinned control | no target diagnostic expected | Y (N/0/4) | Y (N/0/4) | Y (N/0/4) | Y (N/0/4) |

The union's 6/8 is additive: E1/E2/E7 come from R-BIND and E3/E4/E8 from
consumer rules. Full BindCheck does not cover the two relationship examples
(E5/E6). Its exclusive useful output is E1's direct producer-gap-to-effect
link. Its exclusive irrelevant output is Payy's inherited message-tail
R-EFFECT on E8.

## 5. External baseline, not an arm

Noir compiler lint and Slither classifications are imported from the frozen
D1P-32 benchmark and remain external baselines. Neither receives producer or
consumer facts from BindCheck, so neither is placed in the arm table.

| ID | Noir lint | Slither |
|---|---|---|
| E1 WT-C08 | E1-lint | unsupported |
| E2 WT-C03 | E1-lint | unsupported |
| E3 WT-S03 | unsupported | E1-lint |
| E4 WT-S09 | unsupported | E1-lint |
| E5 WT-S05 | unsupported | E1-lint |
| E6 WT-C05 | miss | unsupported |
| E7 WT-C07 | E1-lint | unsupported |
| E8 PY-S01 | unsupported | miss |
| E9 control | no target lint | no target lint |

Each tool localizes 3/8 positive targets, misses one supported-side target, and
cannot inspect the other four. Under this task's stricter semantic-mismatch
criterion, neither names a circuit-to-consumer relationship or consumer effect
at risk (0/8), and each leaves all four substantive confirmation checks. The
D1P-32 per-target table does not preserve warning-object counts for this
subset, so irrelevant-warning object counts are **unverified and not
reconstructed**.

## 6. Prior-work comparison from primary sources

`PRIMARY-VERIFIED` below means the positive scope/property was checked in the
linked paper or official repository. A statement that the source does not
model the consumer is limited to that inspected source and is not an exhaustive
claim about every derivative or unpublished system.

| Work | Primary-verified capability | Precise relationship to this result |
|---|---|---|
| [Picus / QED²](https://www.cs.utexas.edu/~isil/qed.pdf) | Semantic finite-field reasoning plus uniqueness inference/SMT to prove output signals uniquely determined by inputs or find non-uniqueness. | Circuit relation only in the paper. Whether current Picus reports these exact unused-public-input fixtures was not run and is **unverified**. It does not supply the consumer-effect link measured here. |
| [Circomspect](https://github.com/trailofbits/circomspect) | Static analyzer/linter with analysis passes for Circom source. | Producer-source diagnostics; no inspected consumer-contract IR or circuit-to-effect join. Exact fixture coverage is **unverified**. |
| [ZKAP](https://www.usenix.org/system/files/usenixsecurity24-wen_1.pdf) | Circom circuit-dependence graph and nine query-based detectors. The paper explicitly explains that a completely unused public input can verify with an arbitrary value. | Strongest direct overlap with R-BIND and therefore not novelty for producer-gap detection. The inspected paper contains no Solidity/consumer analysis; it discusses possible application impact but does not automatically name the consuming state/effect. |
| [Ecne](https://github.com/franklynwang/EcneProject) | Verifies that de-optimized R1CS equations uniquely determine outputs from inputs; `false` means unable to prove, not unsound. | Circuit-only uniqueness property. No consumer state/effect relation in the inspected tool description. Exact fixture results are **unverified**. |
| [CIVER](https://github.com/costa-group/circom_civer) | Modular Circom weak-safety/determinism checking plus tag and pre/postcondition verification. The official repository describes R1CS/PLONK/ACIR support as future work. | Rich circuit policy specifications can express more than occurrence, but the inspected modes do not extract a Solidity consumer or join a circuit word to consumer state/effects. |
| [CCC-Check](https://vdb.space/papers/zkp2026.pdf) | Domain Consistency Model for computation–constraint mismatch; abstract interpretation over CirC IR, whose frontends include Noir, Circom and ZoKrates. | Its “cross-side” relation is witness computation versus circuit constraints, not circuit versus application consumer. It may cover producer defects missed by occurrence, but no result on these fixtures was run; coverage is **unverified**. |
| [Slither](https://agroce.github.io/wetseb19.pdf) | Solidity-to-SlithIR static framework using SSA, dataflow and taint analysis. | Consumer-side only; the D1P-32 run is reported separately above. It has no circuit relation with which to determine whether a verifier word was proof-bound. |
| [SmartAxe](https://people.cs.umass.edu/~juanzhai/papers/fse24-2.pdf) | Cross-chain bridge bytecode analysis with cross-chain CFG/DFG, access-control inference and cross-bridge semantic inconsistency checks. | Closest structural analogue to a semantic join, but its two sides are bridge smart contracts/bytecode. The inspected paper contains no zero-knowledge circuit analysis. Its state/domain alignment ideas are relevant to the proposed deeper relationship. |

### Circuit-to-contract work

The [2024 SNARK security SoK](https://www.usenix.org/system/files/usenixsecurity24-chaliasos.pdf)
models an integration layer, states that it found no specific defenses for
integration-layer vulnerabilities, and identifies combined Circom/Solidity
testing or verification as future work. That is motivation/taxonomy, not an
implemented comparator.

Joint circuit/contract systems and reviews do exist. For example, the
[Railgun Circom and Solidity audit](https://assets.railgun.ch/docs/audits/2021-04-01%20ABDK.pdf)
reviews both and explicitly describes its methodology as a project-tuned
collection of audit tactics rather than a strict formal procedure. Recent
construction work such as
[token-guided flow tracing](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/ise2/1765419)
implements a Rust/arkworks circuit with a Solidity layer, but presents a
protocol construction and evaluation, not an automated consistency analyzer.

A bounded search of primary papers, official repositories, and the SoK found
no verified automated tool that extracts a ZK circuit relation and its
application consumer, then reports the consumer effect/state relationship at
risk. **Exhaustive absence remains unverified.** BindCheck's defensible novelty
hypothesis is therefore the automated circuit-to-consumer discovery/join, not
unused-input detection, contract dataflow, integration framing, or manually
specified policy.

## 7. Reproduction and evidence

One command reruns all examples and arms on the current checkout:

```sh
PYTHONPATH=src python3 scripts/d1p_41_ablation_preliminary.py
```

The final command exited 0 in 9.3 seconds on macOS 27.0.1 arm64 with Python
3.13.9. Its machine-readable result is
`results/raw/D1P-41/ablation-results.json`, SHA-256
`e30aedee7b627b3f42c0b6aa099f8a65d21bed8aa6bf0241080db0dea14e43fc`.
Per-example full analyzer outputs are in the same ignored directory. The
analyzer source hash is
`92e3970e4b3cd06b40196d60b12003c060a5bb71a2ab0e31b0d94f15f61c4d4e`;
the final runner hash is
`f1c9bf7dd4a34c13abc4900674b3145e385a2d162bceacbce506cd9989333ab0`.

Commands/checks:

```text
git merge --ff-only main                                      exit 0
python3 -m json.tool protocols/d1/d1p-41-ablation-preliminary.json
custom duplicate-key/protocol-identity check                 9 examples, 0 duplicate keys
python3 -m py_compile scripts/d1p_41_ablation_preliminary.py exit 0
PYTHONPATH=src python3 scripts/d1p_41_ablation_preliminary.py exit 0 (attempt 1)
PYTHONPATH=src python3 scripts/d1p_41_ablation_preliminary.py exit 0 (final)
git diff --check                                              exit 0 before report/checkpoint edits
```

The first arm execution revealed a scorer defect: R-POLARITY has no
`public_index`, so WT-S09 was incorrectly rejected after its rule matched. No
analyzer or protocol rule changed. The failed scorer output is preserved as
`results/raw/D1P-41/attempt-01-scoring-bug.json`, SHA-256
`aedc5acecda5e08bbdb8208c1d10a9795545521d43f3a482bbae0d4a2b58d8c7`.
The scorer now uses the predeclared rule/replay relation for R-POLARITY; the
final run is the table above.

## 8. Limitations and next task

- The examples are small, selected to discriminate known capabilities, and
  already exposed. Aggregate rates are descriptive, not effectiveness
  estimates.
- Five matches are one-sided diagnoses; only WT-C08 exercises the current
  R-EFFECT join, and that execution is contained rather than an E4 committed
  effect.
- R-ANCHOR contributes no warning because current extracted anchor facts do
  not produce a negative `must_be_in` fact. This arm definition is preserved
  as requested but its current implementation has no discriminating example.
- Wrong order, value relation, state identity, domain correspondence, and
  indirect authorization remain unsupported. Silence is not safety.
- Prior tools were source-verified, not locally adapted or run on these Noir
  artifacts. Comparative fixture coverage beyond D1P-32 is unverified.

Recommended next task: after AI 1 completes the fact audit, freeze the corrected
analyzer and all nine input hashes, run the single command once, and require
(1) byte-recorded arm masks, (2) exact per-example warning associations, and
(3) no post-output label changes. Completion is a final report whose result
JSON hash and all tool/input revisions are fixed before interpretation. A
subsequent bounded design task should test one explicit typed state/domain
correspondence on WT-S05 and WT-C05 without encoding their expected verdicts.
