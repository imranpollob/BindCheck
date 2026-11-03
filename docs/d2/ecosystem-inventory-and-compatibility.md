# D2 exposed-development ecosystem inventory and compatibility triage

**Date:** 2 November 2026  
**Scope:** exposed development material only  
**Research verdict:** `UNKNOWN`

The authoritative machine-readable ledger is
[`protocols/d2/d2-02-ecosystem-inventory-v1.json`](../../protocols/d2/d2-02-ecosystem-inventory-v1.json).
This narrative explains its denominators and the bounded compatibility
recommendation. It does not authorize broader repository discovery or access
to reserved identities, source, labels, or evaluator outputs.

## 1. Population and counting units

The eligible population is deliberately narrow: the complete set of pinned
application revisions already named by the D2 development allowlist and backed
by tracked producer/consumer evidence. It contains three revision candidates
from two repositories and two code/architectural lineages.

| candidate revision | producer → consumer | current compatibility | architectural lineage |
|---|---|---|---|
| WarpToad `973e7d1e…` | `withdraw` artifact, 11 application words → `WarpToadCore.mint` | `ANALYZABLE` | WarpToad withdraw / UltraHonk / mint |
| Payy earlier `c4d2c902…` | recursive `agg_agg → agg_final`, exact 1,005-to-1,003 certificate → `RollupV1.verifyRollup` and message dispatch | `ANALYZABLE` | Payy recursive aggregation / RollupV1 |
| Payy check-added `dcd5d96e…` | tail-checked `agg_agg → agg_final`, its own exact certificate → byte-identical `RollupV1` consumer | `ANALYZABLE` | same Payy lineage |

These rows are revision candidates, not independent-family claims. The two
Payy revisions form a known before/after pair in one repository with the same
consumer architecture. The WT-C*/WT-S* and PY-C*/PY-S* authored mutants remain
variants of those two lineages. Repository-authored synthetic fixtures are
controls, not ecosystem projects or independent families.

The observed candidate status vector is therefore:

| status | candidates | interpretation |
|---|---:|---|
| `UNAVAILABLE` | 0 | No approved candidate lacked its pinned source/artifact evidence. |
| `INELIGIBLE` | 0 | Every approved candidate has the scoped Noir/ACIR-to-Solidity/EVM boundary. |
| `BUILD_FAILED` | 0 | Every approved candidate has a usable build/artifact route. |
| `UNSUPPORTED` | 0 | The exact pinned application pairs complete the requested current analysis. |
| `ANALYZABLE` | 3 | The interface reaches supported facts/warnings; this is not a safety verdict. |

Those zeros describe only the constructed exposed-development census. No
broader discovery was permitted, so they do not estimate ecosystem
availability, eligibility, or build success.

## 2. Pairing, verifier, and effect evidence

### WarpToad

The repository is `https://github.com/warptoad/warp-toad.git`, pinned at
`973e7d1e4b60d0d8a8ca299b0cabd9193b147ef8`. The saved artifact identifies
Noir `1.0.0-beta.22+c57152f91260ecdb9faad4efc20abb14b6d2ece7`;
the preserved proof route uses `@noir-lang/noir_js 1.0.0-beta.22` and
`@aztec/bb.js 5.0.0`, UltraHonk, with `keccakZK:true`.

The compiled ABI order and the 11-word vector built by
`WarpToadCore.mint` correspond exactly in the preserved evidence. A locally
generated verifier is byte-identical to the verifier at the pinned revision.
That is artifact/verifier correspondence, not historical deployment
provenance. Protected consumer effects include nullifier consumption,
principal mint amount/recipient, relayer-fee mint amount/beneficiary, and the
root-history, chain-domain, fee-cap, and recipient guards authorizing them.

### Payy

The repository is `https://github.com/polybase/payy.git`, with earlier pin
`c4d2c9021b8fb9988816eb6987a734b830bfce15` and check-added pin
`dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36`. Both use the beta.14 Noir line;
the exact compiler identity recorded by the artifacts is
`1.0.0-beta.14+60ccd48e18ad8ce50d5ecda9baf813b712145051`.
The preserved pipeline uses UltraHonk, a keccak-oracle `agg_final`, and its
generated ZK Honk Solidity verifier. Each revision uses its own circuit,
verification key, verifier, proof, and mapping evidence.

For each exact revision, the certificate accounts for 1,005 producer
positions: two recursive-verifier configuration words followed by the 1,003
Solidity-visible words `old_root`, `new_root`, `commit_hash`, and
`messages[1000]`. `RollupV1` checks and dispatches that array. Protected
effects include message-spent bookkeeping, burn token transfers, and final
`rootHash`/`blockHeight` commits, guarded by the prover/validator, root,
verifier-registry, message-grammar, and proof checks.

The earlier exact pair emits the expected `R-EXTENT` warning; the check-added
pair does not. Both remain development evidence. The absence of `R-EXTENT` on
the repair control is not a safety claim, and the preserved T15–T19 E4 chain
applies only to the known earlier message-tail mechanism.

## 3. Target variants and controls are separate denominators

The current 30-target mutant collection is a target-variant dataset, not a
population of 30 systems:

| lineage | variants | analyzable/detected | unsupported | first-stop reason |
|---|---:|---:|---:|---|
| WarpToad | 18 | 17 | 1 (`WT-S04`) | `UNSUPPORTED_CONSUMER_AST_REQUIRED` |
| Payy | 12 | 0 | 12 | `UNSUPPORTED_CONSUMER_AST_REQUIRED` |
| **Total** | **30** | **17** | **13** | 13 named first stops |

All 13 unsupported variants remain `UNKNOWN`, not misses or safe targets. The
exact two-row Payy earlier/check-added analysis is separately analyzable
because it has exact artifact-specific mapping certificates. Those
certificates cannot be transferred to mutated artifact bytes.

The bounded D1P-42 synthetic extent set contributes three analyzable relation
pairs and six execution controls. These are nine control observations, not
nine applications or families. This inventory does not invent a comprehensive
count for every historical repository-authored fixture.

## 4. Historical attempts: attempts, projects, and families

The tracked D1P-33 and D1P-36 reports are used only in aggregate. Together
they contain 12 analysis attempts over eight unique projects, including four
reattempts, with zero supported analyses and 12 fail-closed unsupported
results. There is no adjudicated independent-family count.

All 12 attempt rows have usable build evidence, although some use an
evidence-derived or scoped route and D1P-36 reuses four D1P-33 builds. A failed
default build followed by a successful scoped consumer/verifier build is not
classified `BUILD_FAILED`.

Across attempt occurrences, including repeats, the first-stop categories are:

| category | D1P-33 attempts | D1P-36 attempts | combined attempt occurrences |
|---|---:|---:|---:|
| compiler or schema | 3 | 2 | 5 |
| semantic opcode | 1 | 3 | 4 |
| memory semantics/encoding | 0 | 2 | 2 |
| verifier mapping | 0 | 0 | 0 |
| consumer extraction | 0 | 1 | 1 |
| **Total** | **4** | **8** | **12** |

For the latest scan of the eight unique projects, the distribution is three
semantic-opcode stops, two compiler/schema stops, two beta.21 MemoryOp stops,
and one consumer-extraction stop. These are affected-project counts. Without
lineage adjudication they cannot be converted to affected-family counts or
combined with the exposed-development family ranking.

## 5. Current blocker ranking

The family-ranked development view has two rows:

| rank | barrier | affected lineages | affected variants | implementation risk |
|---:|---|---:|---:|---|
| 1 | current consumer-AST relation route, named `UNSUPPORTED_CONSUMER_AST_REQUIRED` | 2 | 13 | medium-high |
| 2 | artifact-specific recursive mapping for Payy mutant bytes | 1 | 12 | high |

The second row is a nested contributor to the same 12 Payy variants, not an
additional set of 12 failures. Supporting them requires deriving and
certifying a mapping for each mutated artifact, with certificate/artifact hash
mismatch rejected. Reusing either exact pinned certificate would be unsound.

The historical rows remain useful implementation-risk context but are not in
this family ranking. MultiScalarMul and RecursiveAggregation require sound
semantic support; beta.3 and beta.25 are distinct version/schema tasks;
beta.21 MemoryOp requires semantics-preserving decoding; and multiple consumer
boundaries require explicit selection or multi-boundary modeling. None of the
published project counts establishes how many independent families a new
frontend would unlock.

## 6. Bounded recommendation

Preserve every current fail-closed gate. If development proceeds on exposed
coverage, first specify and test the exact consumer-AST relation shapes that
currently stop. For the Payy mutant subset, require artifact-bound recursive
mapping derivation before calling the consumer relation analyzable. This may
increase depth within the one Payy lineage, but it does not add ecosystem
breadth.

Do not prioritize a beta.3, beta.25, MemoryOp, MultiScalarMul, or
RecursiveAggregation extension from the historical project counts alone. A
custodian would need to supply permitted redacted lineage metadata before
those rows can support family-ranked prioritization. Revisit the ranking after
Gate A or an approved lineage-aware population expansion. No universal family
threshold and no claim that a new frontend automatically yields successful
analyses are supported.

## 7. Reproduction

Run the read-only consistency check from the repository root:

```sh
python3 scripts/d2_step2_inventory.py
python3 -m unittest tests.test_d2_step2_inventory
```

The validator checks the 13 evidence hashes, population and lineage counts,
the preserved 30-target outcome/reason vector, the exact Payy pair, the nine
bounded synthetic-control observations, historical attempt arithmetic, and
the current family-ranked blocker counts. It performs no discovery and runs no
analyzer.
