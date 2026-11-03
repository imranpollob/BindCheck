# D2 composition baselines and transformation controls

**Date:** 2 November 2026

**Status:** `CONSTRUCTION_SMOKE_ONLY`

**Research verdict:** `UNKNOWN`

**Machine protocol:** `protocols/d2/d2-06a-construction-v1.json`

**Final construction namespace:** `results/raw/D2-06A/construction-03/`

This document describes the Step 6a interfaces and construction evidence. It
does not score a Gate A target, define a detection, establish a safe control,
or authorize a final comparison. Step 7 still owns exact case selection,
reviewed policies, target fields, controls, resource enforcement, output
namespace, content seal, and any scored execution.

## 1. Shared interface and six arms

`src/bindcheck_d1/composition_baselines_v1.py` consumes one versioned
integrated-analysis record and an optional `bindcheck.composition-policy/v1`
object. Extraction is shared rather than rerun per arm. Every emitted object is
a candidate; the module never emits a violation or verified-safety verdict.

| arm | construction | interpretation |
|---|---|---|
| producer-only | masks existing `R-BIND` producer warnings | one-sided output, not a relationship diagnosis |
| consumer-only | masks existing `R-CONSUMER`, `R-POLARITY`, and `R-ANCHOR` warnings | one-sided output |
| unjoined-union | exact set union of the two one-sided masks | output-mask ablation, not an independent analyzer |
| basic structural composition | exact public-word mapping plus producer occurrence and consumer dataflow/effect checks | structural navigation candidates only |
| strong simple composition | the same extracted basic, exact extent, and available role facts plus direct policy obligations | straightforward joins and direct checks; all outputs remain candidates |
| full BindCheck | normalizes warnings from the frozen integrated record | current generic policy object is recorded but is not consumed by the integrated analyzer |

Candidates have a physical ID bound to the target inputs and a semantic ID
that replaces indices with declared logical word identities, applies explicit
term aliases, and removes unstable locations. Duplicate logical word
identities are rejected. Unsupported components remain `UNKNOWN`.

## 2. Baseline smoke construction

The final run constructed all six arms for 13 development case appearances:
two Payy tail rows, one WarpToad M-DOM row, one M-SRC row, and nine D1P-43
relationship rows. These 13 appearances and 78 case-arms are construction
counts, not deduplicated scored cases, independent families, or a sample-size
claim.

| construction outcome | case-arms |
|---|---:|
| `SUPPORTED` | 72 |
| `UNKNOWN` | 6 |
| total | 78 |

The six `UNKNOWN` rows are the six arms for D1P-43 E8; no arm coerces that
missing support into a miss, clean result, or safety claim. Scoring-readiness
states are 54 `DRAFT_UNSEALED`, 12
`UNRESOLVED_POLICY_NOT_HUMAN_REVIEWED`, and 12
`UNRESOLVED_EQUAL_POLICY_INTERFACE`. Candidate counts in the raw ledger are
smoke observations only.

The D1P-43 union audit passes for all nine rows: eight supported rows are exact
one-sided set unions and E8 remains `UNKNOWN`. This establishes only the set
operation implemented by the ablation.

## 3. Seeded transformations

Four transformations were authored over the D1P-42 bound-prefix producer and
`ConsumerAll` consumer because their public ABI, positional correspondence,
prefix condition, and XOR effect are small enough to state explicitly.

| transformation | build and focused controls | semantic-ID smoke result |
|---|---|---|
| identifier renaming | pass | stable for all six arms |
| single helper extraction | pass | stable for all six arms |
| equality-operand commutation | pass | stable for all six arms |
| matched public-input reordering | pass | stable for all six arms |

For each accepted construction, the ledger retains exact source and mapping
hashes, the compiled Noir artifact, Solidity AST, extracted relation,
integrated record, composition outputs, and commands. Focused controls are:

- logical ABI layouts match under the declared mapping;
- a tail-only change at `active_count = 2` executes successfully while an
  active-prefix change at `active_count = 4` fails, for original and variant;
- four exact 256-bit XOR vectors match under the consumer mapping; and
- semantic candidate identities match the original for every arm.

These checks support inclusion in the transformation-stability construction
denominator. They are not a formal or general semantic-equivalence proof. No
proof was generated.

Two application-level constructions were rejected before mutation and remain
in the denominator. A Payy reorder would require rebuilding both recursive
layers plus mapping certificate, revision-specific key/verifier, proof, and
consumer execution. A WarpToad helper refactor would likewise require a new
artifact correspondence, key/verifier, proof, and original-consumer execution
chain. Reusing the pinned artifacts would be unsound.

## 4. Preserved attempt history

No namespace was overwritten:

- `construction-01` completed but rejected the identifier-renaming control
  because the harness canonicalized renamed words as `payload[...]` and the
  original as `values[...]`. Three other transformations passed. This is a
  harness-control failure, not evidence that renaming changes the property.
- `construction-02` corrected the explicit alias and passed all four controls.
  It predates the final protocol's runner-hash binding. The exact 10,813-byte
  protocol used by both historical runs is preserved at
  `protocols/d2/history/d2-06a-construction-v1-f2627d.json` with SHA-256
  `f2627d4031ac1d320bcd1d3c6165e9535dfa3066527de9b90ec94f74555db6c6`.
- `construction-03` reran the same construction after the protocol began
  verifying the exact runner hash. It is the final Step 6a namespace.

The earlier runs are correction history, not repeated scientific trials and
not independent observations.

## 5. Information parity and current blocker

Strong simple composition and full BindCheck share the extracted implementation
facts. The strong arm has a generic direct-obligation interface, but no
human-authored/reviewed policy was supplied. The current full analyzer records
that same generic policy hash through the adapter but does not consume its
obligations. Therefore equal reviewed-policy consumption is false and the
matrix status is `UNRESOLVED_EQUAL_POLICY_INTERFACE`.

This blocks a scored strong-simple-versus-full comparison. It does not erase
the runnable construction or turn unrelated objective rows into unresolved
rows. Step 7 must either supply and equalize a primary-source human-reviewed
policy interface for both arms or declare the affected comparison
inconclusive. Step 6a makes no choice between those outcomes.

## 6. Cost and limits

The final runner used 22 compiler/version/execution subprocess calls under the
cap of 30, zero proof calls, zero network calls, and no scientific retries.
Elapsed runner time was 4.231065834 seconds; recorded subprocess time was
1.906229665 seconds and composition-only time was 0.069094751 seconds.
Extraction is shared and composition runtime is also retained per arm.

No hard memory cap was enforced, so no memory-enforcement claim is made.
Human minutes are `null`: the automated runner did not measure human activity,
and the missing value must not be imputed as zero or time saved.

## 7. Reproduction and validation

The runner refuses to overwrite an output directory and verifies the Step 5
draft, every bound input, both tool binaries, the composition module, and its
own runner hash before construction.

```sh
PYTHONPATH=src python3 scripts/d2_step6a_construct.py \
  --protocol protocols/d2/d2-06a-construction-v1.json \
  --output results/raw/D2-06A/<fresh-construction-id>

PYTHONPATH=src python3 -m unittest \
  tests.test_d2_step6a_composition \
  tests.test_d2_step6a_construction
```

The final raw summary is
`results/raw/D2-06A/construction-03/run-summary.json`. The run remains
`scored: false`; its research verdict is `UNKNOWN`.
