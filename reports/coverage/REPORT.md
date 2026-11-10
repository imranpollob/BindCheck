# Lane C: bounded analyzer coverage revision

**Objective and status.** The bounded DEV coverage task is complete at the
new analyzer hash
[`a9ec7cb91a9a987ae9dc146142b5cf062114a1ec92551d05ab2eb05bf0e8f07b`](../../results/raw/coverage/verification.json).
The [new freeze declaration](../../docs/FREEZE-COVERAGE-2026-11-09.md)
records the reason for the revision and the historical results it supersedes
for current-code claims.
Across applicable pattern-row cells, decisions moved from
[`39/159` to `41/159`](dev-summary.json). This is a small, source-level
development gain, not a demonstrated precision, transfer, prevalence, or E4
result. The complete [unhinted DEV ledger](dev-ledger.csv) and
[changed-verdict ledger](changed-verdicts.csv) contain every row. The first two
coverage passes remain ignored raw exploratory evidence; only
[`after-20261109T150206Z-10301`](../../results/raw/coverage/after-20261109T150206Z-10301/manifest.json)
is the controlling after run.

The research contract controls verdict semantics. Its initial D1 scope still
names Noir/ACIR, whereas the current frozen `bindcheck_zk` tool and this
task analyze Circom/Groth16 plus Solidity. That scope discrepancy is not
silently resolved by this report. The current [freeze declaration](../../docs/FREEZE-2026-11-09.md)
controls the starting Circom analyzer identity; no older report was edited.

## Protocol and provenance

The [prospective plan](PLAN.md) and [synthetic control oracle](../../tests/coverage/test_rules.py)
were committed as `8a39ba0` before the first implementation. Addenda and
their control expectations were committed as `d245ad5` and `06daf92`
before the corresponding rule revisions. The analyzer receives none of those
expected outcomes. The before evidence is the soundness follow-up's
[`8ea6d2239cd94e2b4478bfae48fe8e764bf448a3b44c58224bbeeb6fa2f70542`](../soundness/REPORT-2.md)
run; [its raw manifest](</Users/imranpollob/Coding/bc/bindcheck-zk/results/raw/soundness/after-20261109T061325Z-77918/manifest.json>)
has SHA-256
[`21ecb42b7a45c0d37cac887b374377da038ace0caa2a6005f56a8769bd399db9`](dev-summary.json).
The after manifest has SHA-256
[`fddee05a6090b2e6b71c819937e1caa7b4516857a83726a00a4affba38fac177`](dev-summary.json).
The [runner manifest](../../results/raw/coverage/after-20261109T150206Z-10301/manifest.json)
records exact row commands, pinned checkout revisions, output hashes, exit
statuses, and timing. The [per-row ledger](dev-ledger.csv) records every source
revision and before/after reason. The DEV checkout root was reused read-only;
the runner used `--skip-fetch` and no path hints.

The controlling unhinted command was:

```sh
BINDCHECK_CIRCOM=/Users/imranpollob/Coding/bc/bindcheck-zk/tools/circom-src/target/release/circom /opt/homebrew/bin/python3 scripts/run_bindcheck_zk_full_dev.py --phase after --skip-fetch --raw-task coverage --checkout-root /Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev --analyze-jobs 3
```

The local environment used [Python `3.15.0`, Circom `2.2.3`, and Git `2.51.0`](../../results/raw/coverage/verification.json).
The Circom executable SHA-256 is
[`7d0bd3cc8d0c4942813f5060bd5f9c011f3469e46755a067926101ee74d4e202`](../../results/raw/coverage/verification.json).
The ignored local `circomlib` copy was checked against
[`vendor-lock.json`](../../bindcheck_zk/vendor-lock.json) before the controls;
it was not committed. No Picus run, local-chain transaction, RPC interaction,
live-chain transaction, or maintainer contact occurred.

## Diagnosis of every before UNKNOWN

The [before UNKNOWN inventory](before/unknown-inventory.csv) contains
[`241`](before/unknown-inventory.csv) row-pattern cells and a source-path,
function, verifier, circuit and per-triple blocker for every discovered triple.
For the [`10`](../soundness/full-dev-ledger-2.csv) no-triple rows, it records
the inspected dispatch/build shape and example pinned source location. The
[diagnostic script](scripts/diagnose.py) produces the
[ranked shape table](before/shape-counts.csv). Shape labels are AI-authored
source inspection aids, **not independent human annotations**. A row can
appear in several shapes and patterns; counts below overlap. In particular,
read-only utilities and missing triples are not applicable successes waiting
to be reclassified.

| Concrete blocked code shape | DEV rows affected | UNKNOWN cells | Why it blocked a decision |
| --- | ---: | ---: | --- |
| Indexed/member assignment with unresolved storage semantics | [20](before/shape-counts.csv) | [41](before/shape-counts.csv) | The verifier-calling body has an indexed or member assignment, but the extractor cannot establish storage, effect role, or committed path. |
| Read-only verifier utility | [18](before/shape-counts.csv) | [50](before/shape-counts.csv) | The recovered function is `view`/`pure` and commits no protected effect. |
| No live chain/contract/domain value in statement | [15](before/shape-counts.csv) | [15](before/shape-counts.csv) | P2 cannot infer whether the protocol requires replay-domain binding. |
| Scalar guard absent or unsupported in verifier | [15](before/shape-counts.csv) | [15](before/shape-counts.csv) | P4 cannot certify exact scalar canonicality; several pinned `checkField` helpers compare with base field `q`. |
| Multiple verifier shapes retained | [10](before/shape-counts.csv) | [10](before/shape-counts.csv) | P5 cannot select one arity/order, notably in multi-verifier repositories. |
| Effect delegated beyond verifier-call function | [9](before/shape-counts.csv) | [25](before/shape-counts.csv) | A helper or library call separates proof acceptance from the effect. |
| Fixed public array passed without named elements | [9](before/shape-counts.csv) | [9](before/shape-counts.csv) | A fixed count alone cannot establish semantic order. |
| Matched circuit/verifier implementation missing | [8](before/shape-counts.csv) | [21](before/shape-counts.csv) | Interface-only or absent compiled/source artifacts prevent a positive verdict. |
| Context computed without dominating statement binding | [8](before/shape-counts.csv) | [8](before/shape-counts.csv) | A chain/domain expression exists, but its path to the verified vector is not established. |
| Unsupported non-Groth16/PLONK verifier layout | [6](before/shape-counts.csv) | [6](before/shape-counts.csv) | The key invariant recognizer cannot parse that proof system's key. |

The no-triple records include selector-driven inherited verifier dispatch in
[`DEV-F13`](before/unknown-inventory.csv), a low-level ABI-encoded call in
[`DEV-F37`](before/unknown-inventory.csv), separate verifier/effect contracts
in [`DEV-F05`](before/unknown-inventory.csv), and a verifier-only source in
[`DEV-F17`](before/unknown-inventory.csv). These are discovery gaps, not safe
outcomes. The exact source examples and all other blocker shapes are in the
[inventory](before/unknown-inventory.csv).

## Rules added and controls

The added scope is in the [verdict rules](../../docs/verdict-rules.md), with
the [precommitted positive and adversarial cases](../../tests/coverage/test_rules.py):

- Direct `Pausable` `whenNotPaused`/`whenPaused` through exact bare or named
  OpenZeppelin imports; an exact imported base wins over an unrelated local
  name collision. Missing/wrong imports and local external-call modifiers
  remain UNKNOWN.
- A local lock modifier only for the exact unconditional status guard, set,
  single placeholder, and distinct reset form. Missing reset, conditional or
  duplicate placeholder, external call, and wrong reset remain UNKNOWN.
- An exact `ERC721Enumerable` import exposes its inherited `_mint` recipient
  role. A local override remains UNKNOWN.
- An unconditional fail-closed verifier blocks a non-vacuous P1 positive.
- A dynamic verifier wrapper can satisfy P4's guard subcondition only with an
  exact length check, position-preserving copy, and scalar guard on every
  fixed raw public-input position. Reordered, unguarded, and base-field
  variants remain UNKNOWN.

The full local validation record shows [`33` unittest methods passed](../../results/raw/coverage/verification.json),
including the [`122` existing controls](../../tests/controls/expected.json),
the retained [soundness controls](../../tests/soundness/expected.json), the
follow-up suite, and the new coverage suite. `compileall`, `git diff --check`,
and `./freeze.sh` each exited [`0`](../../results/raw/coverage/verification.json).
These are source-recognizer controls; they do not provide E2–E4 validation.

## Unhinted DEV before → after

These are **applicable rows only**; counts and denominators come from
[`dev-summary.json`](dev-summary.json). `NOT_APPLICABLE` and unknown
applicability are in that file and remain outside the decision denominator.

| Pattern | Applicable | Decided | VIOLATION | VERIFIED_WITHIN_SCOPE | UNKNOWN |
| --- | ---: | ---: | ---: | ---: | ---: |
| P1 | [17 → 17](dev-summary.json) | [5 → 6](dev-summary.json) | [5 → 6](dev-summary.json) | [0 → 0](dev-summary.json) | [12 → 11](dev-summary.json) |
| P2 | [27 → 27](dev-summary.json) | [0 → 0](dev-summary.json) | [0 → 0](dev-summary.json) | [0 → 0](dev-summary.json) | [27 → 27](dev-summary.json) |
| P3 | [23 → 23](dev-summary.json) | [13 → 13](dev-summary.json) | [6 → 6](dev-summary.json) | [7 → 7](dev-summary.json) | [10 → 10](dev-summary.json) |
| P4 | [46 → 46](dev-summary.json) | [17 → 18](dev-summary.json) | [0 → 0](dev-summary.json) | [17 → 18](dev-summary.json) | [29 → 28](dev-summary.json) |
| P5 | [46 → 46](dev-summary.json) | [4 → 4](dev-summary.json) | [0 → 0](dev-summary.json) | [4 → 4](dev-summary.json) | [42 → 42](dev-summary.json) |

Exactly [two row verdicts changed](changed-verdicts.csv):

| Row and pattern | Before → after | Source-grounded reason and evidence limit |
| --- | --- | --- |
| [DEV-F29 P4](changed-verdicts.csv) | `UNKNOWN / PUBLIC_INPUT_CANONICALITY_GUARD_NOT_FOUND` → `VERIFIED_WITHIN_SCOPE / VERIFICATION_KEY_CHECKS_PASS` | The pinned [Groth16 wrapper](</Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev/DEV-F29--Veilpayapp__VEILPAY-APP--955cc7511f4f/packages/contracts-evm/src/Groth16Verifier.sol:209>) checks exact length and copies public words position for position into its raw verifier. The [after result](../../results/raw/coverage/after-20261109T150206Z-10301/DEV-F29--result.json) records exact scalar-guard indices and parsed distinct gamma/delta. This verifies the named source invariants only; key ceremony, circuit/key correspondence, accepted proofs, and deployment are unresolved. |
| [DEV-F44 P1](changed-verdicts.csv) | `UNKNOWN / UNRESOLVED_CONSUMER_INHERITANCE` → `VIOLATION / UNBOUND_EFFECT_RECIPIENT` | The pinned [consumer](</Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev/DEV-F44--zkemail__proof-of-twitter--b6d9c2d6a8c9/packages/contracts/src/ProofOfTwitter.sol:109>) calls inherited `_mint(msg.sender, tokenId)`, while its [proof-address equality](</Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev/DEV-F44--zkemail__proof-of-twitter--b6d9c2d6a8c9/packages/contracts/src/ProofOfTwitter.sol:69>) is commented out. The matched [verifier](</Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev/DEV-F44--zkemail__proof-of-twitter--b6d9c2d6a8c9/packages/contracts/src/Verifier.sol:245>) has a pairing-based success path. This is a source-confirmed E1 role warning; a real proof, accepted mint, protocol policy and human label are MISSING. |

The [complete ledger](dev-ledger.csv) also records reason-only transitions.
Notably [DEV-F12](dev-ledger.csv) now stops at unresolved commitment preimage
order; [DEV-F29](dev-ledger.csv) verifies the deposit triple's P1 roles but
the withdraw triple retains state-derived fee/amount uncertainty, so aggregate
P1 stays UNKNOWN. [DEV-F38](dev-ledger.csv) no longer exposes a false positive
path through fail-closed placeholders. [DEV-F39](dev-ledger.csv) retains its
aggregate P1 warning from another triple, while its fail-closed triple is
UNKNOWN. Neither a timeout nor a reason-only change is scored as a decision.

The run analyzed [56 DEV rows, with 46 rows having a triple and zero crashes](dev-summary.json).
Circuit builds were [45 successful and 31 failed/timed out before versus 43
successful and 33 failed/timed out after](dev-summary.json), with
[one versus three timeouts](dev-summary.json). The additional timeouts were
[`DEV-F09`](../../results/raw/coverage/after-20261109T150206Z-10301/DEV-F09--result.json)
and [`DEV-F45`](../../results/raw/coverage/after-20261109T150206Z-10301/DEV-F45--result.json),
whose corresponding before builds had succeeded. They remain UNKNOWN setup
outcomes, not misses or coverage gains. The retained final run has
[`239` UNKNOWN cells](after/unknown-inventory.csv), including nonapplicable
and unknown-applicability cells.

## Remaining shapes and next task

The [after ranking](after/shape-counts.csv) still has indexed/member
assignments with unresolved storage semantics ([20 rows](after/shape-counts.csv)),
read-only utilities ([18 rows](after/shape-counts.csv)), missing live-context
binding ([15 rows](after/shape-counts.csv)), unsupported/absent scalar guards
([14 rows](after/shape-counts.csv)), verifier ambiguity
([11 rows](after/shape-counts.csv)), and delegated effects
([9 rows](after/shape-counts.csv)) at the top. These counts overlap and include
nonapplicable paths. The [after inventory](after/unknown-inventory.csv)
preserves the exact source functions and reason codes for all remaining
UNKNOWN cells.

**Recommended next bounded task:** add storage-qualified member/mapping-write
and one-hop internal-helper effect extraction with explicit call-path and
storage-location evidence. Precommit positive, adversarial and legitimate
controls before implementing it. Completion means every newly decided DEV
row has a source-path adjudication, no new positive on a fail-closed or
unmatched verifier, all existing controls pass, and a fresh unhinted DEV
ledger shows at least one additional applicable decision without relabeling a
timeout or nonapplicable path.

**Limitations and failed approaches.** The initial coverage pass admitted a
P1 positive on a fail-closed placeholder; the precommitted regression and
final code restored UNKNOWN. A later pass mixed source revisions while the
resolver was being corrected; it is retained as exploratory raw evidence and
excluded from the table. The final run was launched after the resolver change
and has one analyzer hash throughout. The checkout's vendored OpenZeppelin
names initially overrode exact imports; the final resolver uses the exact
import and leaves wrong or absent imports unresolved. Source-shape labels and
the new warning are AI judgments pending author inspection and, for security
claims, independent human policy review. No real proof or committed effect was
newly validated here.
