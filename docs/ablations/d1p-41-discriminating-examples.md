# D1P-41 preliminary discriminating examples

Date frozen before the arm run: **30 October 2026**  
Status: **PRELIMINARY, exposed development examples**  
Machine-readable protocol: [`protocols/d1/d1p-41-ablation-preliminary.json`](../../protocols/d1/d1p-41-ablation-preliminary.json)

This file preregisters the intended policy, reachable execution, and expected
outcome for the nine examples used by D1P-41. It was written before executing
the D1P-41 arm runner. The examples and earlier BindCheck results were already
public development material, so this ordering prevents post-run relabeling but
does not make the experiment blind or held out.

“Expected outcome” below is a fixture ground-truth expectation. It is not a new
result category. A related static warning earns E1 detection credit; it does
not by itself establish `VIOLATION`. Silence never establishes
`VERIFIED_WITHIN_SCOPE`. AI 1 is auditing the extracted facts in parallel, and
the final interpretation requires a one-command rerun on the corrected frozen
tool.

## Frozen arms

- **Producer-only:** producer public-leaf and proof-enforced occurrence facts;
  output only R-BIND.
- **Consumer-only:** consumer guard/effect/state/replay facts with producer
  occurrence facts masked; output R-CONSUMER, R-POLARITY, and R-ANCHOR.
- **Unjoined union:** the set union of the first two outputs, with no new
  cross-layer relation.
- **Full BindCheck:** all current warnings, including R-EFFECT. R-EFFECT is the
  only current rule whose predicate intersects producer-unused indices with
  consumer effect-word indices.

No rule in `src/` may change for this preliminary run.

## Frozen scoring

Detection requires a warning at the predeclared semantic boundary, not merely
some warning on the target. For the clean control, the expected diagnostic
outcome is no warning. A warning “names the effect at risk” only if it names a
concrete token/state effect or the missing replay write. R-POLARITY therefore
earns that credit for the protected replay-state write, while its failure to
name the downstream duplicate mint is reported separately.

Human confirmation uses four substantive checks:

1. establish the relevant producer binding or gap;
2. establish the relevant consumer guard/effect/state relationship;
3. confirm that the reviewed policy requires that relationship; and
4. confirm a reachable execution and committed or contained outcome.

R-BIND discharges check 1. R-EFFECT discharges checks 1–2. R-CONSUMER,
R-POLARITY, and R-ANCHOR discharge check 2. Current warnings never discharge
checks 3–4. Noir lint and Slither may help navigation but discharge none of
these cross-layer checks. Irrelevant warnings are every emitted warning that
does not match the example's predeclared boundary.

## Examples frozen before execution

| ID | Synthetic target and hypothesis | Intended policy | Reachable execution | Expected outcome before any arm |
| --- | --- | --- | --- | --- |
| E1 | **WT-C08**, producer gap with a directly consumed word | A withdrawal proof excludes the zero recipient before the recipient mint. | Honest execution remains reachable. A zero-recipient proof is expected to verify at circuit level; the consumer ERC-20 rejects the zero receiver. | Producer defect at `recipient_address` (public 10); the attempted mint is contained, so no E4 committed mint is expected. |
| E2 | **WT-C03 / M-DOM**, producer context gap while the consumer does not directly consume the context word in an effect | The note silo domain equals the consumer-configured WarpToad address. | The preserved M-DOM route proves a foreign-domain note with the mutant key and commits the mint from the admitted synthetic state. | End-to-end mismatch at `aztec_warptoad_address` (public 5); the mint is context-authorized incorrectly even though the word is not an effect operand. |
| E3 | **WT-S03**, consumer ignores an authenticated replay key | Each proof-bound nullifier authorizes at most one mint. | The same proof/calldata is submitted twice; both the absence check and write are removed. | Replay mismatch at `nullifier` (public 0); duplicate mint is the downstream effect. |
| E4 | **WT-S09**, retained absence check but missing success write | A nullifier is absent before acceptance and atomically marked spent after success. | The first call passes but writes nothing; the identical proof passes the unchanged check again. | Replay mismatch localized to the missing nullifier write; duplicate mint is the downstream effect. |
| E5 | **WT-S05**, consumer checks roots against the wrong state maps | The giga root is admitted by `gigaRootHistory`; the local root by `localRootHistory`. | Honest distinct roots are predicted to revert when checks are crossed; a value admitted to the wrong set supplies the bypass shape. No new execution is claimed here. | Wrong state/domain relation even though both words reach guarded lookups; research evidence remains `UNKNOWN` beyond frozen development ground truth. |
| E6 | **WT-C05**, producer uses a word but in the wrong root relationship | The private origin root, not the public destination root, is the membership root on the cross-root branch. | Honest same-root execution still passes because origin equals destination; an adversarial cross-root witness distinguishes the swap. No new execution is claimed here. | Wrong producer relationship with all involved words still occurring in constraints; research evidence remains `UNKNOWN` beyond frozen development ground truth. |
| E7 | **WT-C07**, unused domain word whose risk is not direct operand flow | The commitment and withdrawal authorization are bound to the executing chain ID. | The frozen honest witness fails by design; an adversarial cross-chain construction is the target route. Existing evidence reaches E3, not a cross-chain committed effect. | Gap at `chain_id` (public 1); the at-risk mint is not a direct operand and the end-to-end verdict remains `UNKNOWN`. |
| E8 | **PY-S01**, missing admission guard with inherited unrelated findings | A mint record matches a registered unspent mint before it is marked spent and settled. | An unregistered mint reaches settlement after the `verifyMint` requirements are removed while the spent write remains. No unchanged-real-verifier E4 is claimed for this warning. | Missing admission/must-not-be-in guard. The inherited Payy tail and `commit_hash` warnings are irrelevant to this mutation. |
| E9 | **Pinned WarpToad**, honest development control | All eleven words are bound; roots use their matching histories; nullifier check/write and mint effects agree. | The preserved honest proof mints once; identical replay rejects. | No target warning in supported static scope. The formal result remains `UNKNOWN`, not `VERIFIED_WITHIN_SCOPE`. |

The exact artifact, source, relation paths, expected public indices/rules, and
the pre-existing Noir/Slither classifications are frozen in the machine-readable
protocol.
