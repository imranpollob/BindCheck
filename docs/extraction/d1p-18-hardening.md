# D1P-18 — route-A Solidity-AST extractor hardening

## Decision and claim boundary

Route A remains the recommended consumer-extraction route for the supported
`WarpToadCore.mint` fragment. The hardened extractor recovers the same 22 path
families, the verifier argument vector, and committed/rolled-back effects, while
now rejecting unsupported semantics instead of emitting generic terms or
continuing past calls.

This is evidence of **extraction fidelity on the tested fragment**. It is not a
claim of automatic policy-to-obligation derivation. BindCheck must still state
the desired binding policy and derive/check its obligations separately. The
manual WarpToad relation is a frozen regression reference only; no equation or
case was added to it.

## Pinned subject and boundary

The run uses `WarpToadCore.sol` SHA-256
`323a1cf26c7449f67cf277ff0a46c31e12f725c555f9fa165d5a60011e122c39`,
the archived D1P-12R standard-JSON build, solc
`0.8.29+commit.ab55807c`, optimizer enabled with one run, and Cancun EVM.
All pin assertions pass in `results/raw/D1P-18/relation.json`.

The only relational external boundary is the resolved declaration
`project/contracts/core/WarpToadCore.sol::IVerifier::verify(bytes,bytes32[])`.
It is emitted as `R_verify(proof, word0, …, word10)` and is never assumed true.
The 11 words and their derivations remain source-recovered. Chain ID and the
configured Aztec address are consumer-constructed verifier arguments; their
connection to producer witnesses is a property of the joint binding relation,
not a producer constraint recovered by this consumer extractor.

## Fail-closed behavior

`UnsupportedConstruct` produces a named `UNSUPPORTED_<KIND>` code, source file
and line, and detail. The interpreter now rejects:

- unresolved identifiers, callees, events, assignment targets, missing returns,
  call arity errors, recursive/unimplemented calls, and unsupported AST nodes;
- every unmodeled external call, including statement-position calls;
- generic member and index access, symbolic memory indexing/allocation, and
  unsupported operators, conversions, loops, statements, or expressions;
- an OpenZeppelin call, storage write, or event whose exact resolved
  declaration has no supported versioned model; and
- malformed/unknown effect-model semantics or storage shapes.

There are no `call`, `member`, or `index` fallback operations in the extracted
IR. The regression suite also removes the exact `_mint` model and observes
`UNSUPPORTED_LIBRARY_CALL` rather than successful extraction. Synthetic
unsupported sites verify location-bearing rejections for unresolved calls,
external expression/statement calls, member/index access, and unresolved
events.

## Shared library effect models

`prototypes/d1p16/library_effect_models.v1.json` is version `1.0.0`, declares
`scope=shared_across_cases`, and has `case_specific_entries=false`. Keys are the
resolved source path, contract, signature, and pinned library version—not a
method name. For OpenZeppelin Contracts 5.6.1 it declares:

- ERC-20 `_mint`, `_burn`, `_transfer`, and `_update` call semantics;
- `_balances` functional-map and `_totalSupply` scalar writes; and
- the resolved IERC20 `Transfer(address,address,uint256)` event.

Bodies are still interpreted to recover ordered guards and storage effects; the
table authorizes and types the library boundary/effect. A WarpToad-specific or
expected-result-specific entry would be manual implementation input and is
forbidden by the table metadata. No such entry is present.

## Source-mutation controls

Each mutation changed one occurrence in the source, was compiled from the
complete archived compiler input with the isolated pinned solc package, and was
then processed by the same extractor SHA-256
`4a9dd7516d0b2291b0a3a1bf66f2bdb074d021356fff2fc506cd88e30e30af7b`
and the same model SHA-256
`236c4691c410ead94bdb500d904fe91243f66be8ce4e46b96b487fe0d325ac6d`.
No extractor or model edit occurs between cases.

| Mutation | Expected relation site | Observed result |
|---|---|---|
| `_mint(_recipient, amount-fee)` → `_mint(_relayer, amount-fee)` | second fee-branch mint beneficiary | Baseline beneficiaries were recipient/recipient; mutated beneficiaries resolve to `msg.sender` in the relayer-sentinel branch and `calldata._relayer` otherwise. The duplicated receiver check also removes two infeasible/redundant revert families (22 → 20). |
| remove fee-cap `require` | fee guard and its failure family | All 13 path occurrences of the cap guard disappear, the named fee-cap revert family disappears, and total paths change 22 → 21. |
| `nullifiers[_nullifier]` → `nullifiers[_localRoot]` | primary storage write key | Every successful nullifier write changes from `calldata._nullifier` to `calldata._localRoot`; guards and the 22-family count otherwise remain. |

All compiler runs returned zero with no compiler errors. Full compiler input and
output hashes, mutated sources, extracted relations, and assertions are under
`results/raw/D1P-18/mutations/`.

## Semantic edge controls and coverage

Checked arithmetic has concrete witnesses for base-fee addition overflow
(`p04`), fee multiplication overflow (`p05`), supply addition overflow (`p10`),
and amount subtraction underflow (`p15`). Structural guard/terminal inspection
covers all nine arithmetic-panic families. Aliasing controls execute sequential
stores to one balance key in both success fee branches. Zero-value controls
retain mint occurrences and `Transfer` events on all three success families.
Rollback checks all 19 revert families have empty committed writes, mints,
burns, transfers, and events, including paths with tentative effects.

| Family | Terminal | Applicable control(s) | Recorded execution(s) |
|---|---|---|---|
| p00 | revert: giga root | rollback | — |
| p01 | revert: local root | rollback | — |
| p02 | revert: replay/nullifier | rollback | D1P-12R replay |
| p03 | revert: verifier | rollback | — |
| p04 | revert: arithmetic panic | checked arithmetic; rollback | — |
| p05 | revert: arithmetic panic | checked arithmetic; rollback | — |
| p06 | revert: fee cap | rollback | D1P-14A FC-NEG |
| p07 | revert: invalid receiver | rollback | — |
| p08 | revert: arithmetic panic | checked arithmetic; rollback | — |
| p09 | revert: invalid receiver | rollback | — |
| p10 | revert: arithmetic panic | checked arithmetic; rollback | — |
| p11 | revert: arithmetic panic | checked arithmetic; rollback | — |
| p12 | revert: invalid receiver | rollback | — |
| p13 | revert: arithmetic panic | checked arithmetic; rollback | — |
| p14 | success: sentinel relayer | aliasing; zero value | — |
| p15 | revert: arithmetic panic | checked arithmetic; rollback | — |
| p16 | revert: invalid receiver | rollback | — |
| p17 | revert: arithmetic panic | checked arithmetic; rollback | — |
| p18 | success: explicit relayer | aliasing; zero value | D1P-12R honest; D1P-14A FC-POS |
| p19 | revert: invalid receiver | rollback | — |
| p20 | revert: arithmetic panic | checked arithmetic; rollback | — |
| p21 | success: zero-fee branch | zero value | D1P-14A zero-fee |

No family is uncovered by the combined edge controls and recorded executions.
The five executions alone select only `p02`, `p06`, `p18`, and `p21`; they do
not select 18 families. The machine-readable matrix and concrete witnesses are
in `results/raw/D1P-18/semantic-controls.json`.

## Regression comparisons and disagreements

The five archived executions select exactly one path each: honest `p18`, replay
`p02`, FC-POS `p18`, FC-NEG `p06`, and zero-fee `p21`. Their public words,
success/revert result, mint occurrences, relevant post-state, and rollback have
**zero disagreements** with the recorded executions.

Against the frozen manual summary, all previously identified agreements remain
and every disagreement is retained:

1. The manual summary checks chain ID/configuration beside a Boolean verifier
   result. The source constructs those verifier arguments and has no standalone
   guards; producer-witness linkage belongs to the joint binding relation.
2. On the synthetic witness with maxed pre-supply, fee one, and amount zero,
   source order first panics on the first ERC-20 supply addition after a
   tentative nullifier write and fee-mint occurrence. The manual summary instead
   reports the later subtraction underflow and exposes no tentative occurrence.
   Committed state agrees because both transactions roll back.

`results/raw/D1P-18/manual-regression-comparison.json` records both differences;
`results/raw/D1P-18/five-execution-comparison.json` records the zero-disagreement
concrete comparison.

## Validation and limits

Twelve unit regressions pass. The relation has 22 families (3 success, 19
revert), all artifact/model pins pass, and every revert commits nothing. The
source mutations and all four edge-control classes pass. Exact output hashes
are in `results/raw/D1P-18/validation.json`.

The supported fragment remains bounded: one pinned Solidity entry point, the
AST constructs reached from it, and the declared OpenZeppelin 5.6.1 models.
Fail-closed rejection prevents silent extrapolation to other constructs or
versions; it does not make those constructs supported. No Payy, O1, or solver
campaign was run.
