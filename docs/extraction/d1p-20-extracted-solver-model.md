# D1P-20 — extracted consumer relation as the solver model

## Outcome and claim boundary

The D1P-18 Solidity-AST relation now replaces the manual WarpToad consumer
summary in a D1P-20 joint-encoder namespace for the tested
`WarpToadCore.mint` fragment. The full producer-plus-extracted-consumer SMT
query parses with pinned cvc5 1.4.2; five archived executions and all eight
D1P-14D deterministic controls pass.

This establishes an extracted implementation model for this fragment. It does
**not** derive authorization or coverage obligations automatically. G1–G5 and
the callsite-to-policy-role mapping remain separate policy inputs. No primary
solver campaign, proof generation, V-EXEC, performance claim, or D1 security
verdict is part of D1P-20.

## New namespace and default preservation

`prototypes/d1p20/joint_extracted.py` exposes
`consumer_model = {MANUAL, EXTRACTED}`:

- `MANUAL` is the default. It delegates to
  `src/bindcheck_d1/joint_warptoad.py` without changing that module. The wrapper
  produces byte-identical Omega, query, and transformation certificate values.
- `EXTRACTED` consumes the D1P-18 relation SHA-256
  `301ce67b6148bd889082f67b7c484cac55a52981d540917c21ac67f421293fd7`.
  It rejects a changed schema, failed artifact pin, changed 22/19/3 path shape,
  or unsupported IR operator using the existing located
  `UNSUPPORTED_<kind>` exception.

The canonical MANUAL implementation and all earlier query bytes remain
untouched.

## Extracted relation serialization

The D1P-20 IR retains all 22 path families rather than collapsing them to the
three successful terminals. For every family it records ordered guard IR,
terminal status/revert reason, tentative effects, committed effects, and the
rollback flag. The SMT serializer defines `path_p00` through `path_p21`, then:

- `consumer_success` is the disjunction of `p14`, `p18`, and `p21`;
- `consumer_revert` is the disjunction of the other 19 families;
- the existing joint scope excludes the sentinel-relayer `p14` case with
  `pi9 != 1`;
- committed mint/balance/nullifier effects are gated by extracted successful
  path predicates; and
- `rollback_holds` requires every committed effect predicate to be false on an
  extracted revert path.

The joint diagnostic still quantifies only successful consumer transitions:
it asserts `consumer_success` before policy evaluation. Revert order and
tentative effects remain available in `extracted-consumer-ir.json`; a fixed
archived revert therefore makes the successful-transition query UNSAT rather
than becoming a policy violation.

The three extracted source mint sites become occurrence-level solver effects:

| Source site | Extracted presence | Amount/beneficiary |
|---|---|---|
| line 171 fee mint | `p14 ∨ p18` | recovered fee expression; `msg.sender` on p14, relayer word on p18 |
| line 172 recipient mint | `p14 ∨ p18` | recovered `amount - fee`; recipient word |
| line 175 zero-fee mint | `p21` | amount word; recipient word |

The nullifier write is present exactly on `consumer_success` and keyed by the
recovered nullifier word. Zero-valued executed mints remain occurrences and
equal beneficiaries are not merged.

## Joint producer/verifier/consumer bridge

The extracted external call remains the explicit relational boundary
`IVerifier.verify(bytes,bytes32[])`; it is not modeled as an arbitrary external
call. The serializer reconstructs each consumer verifier argument and defines a
boundary predicate equating it to the corresponding joint public word:

| Word | Recovered consumer origin | Joint connection |
|---:|---|---|
| 0 | calldata nullifier | `consumer_verify_word_0 = pi0`, then `pi0 ↔ w0` through `D_v` |
| 1 | `block.chainid` | `pi1 = env_chain_id = 31337`, then `pi1 ↔ w1` |
| 2 | calldata amount | `pi2 ↔ w2` |
| 3 | calldata giga root | `pi3 ↔ w3` |
| 4 | calldata local root | `pi4 ↔ w4` |
| 5 | stored `aztecWarptoadAddress` | `pi5 = config_aztec_address = 0`, then `pi5 ↔ w5` |
| 6 | calldata fee factor | `pi6 ↔ w6` |
| 7 | calldata priority fee | `pi7 ↔ w7` |
| 8 | calldata maximum fee | `pi8 ↔ w8` |
| 9 | calldata relayer after Solidity casts | `pi9 ↔ w9` |
| 10 | calldata recipient after Solidity casts | `pi10 ↔ w10` |

In a full joint query, the same formula asserts the producer `R_hat` constraints
and `D_v`, so the recovered boundary is discharged by `R_hat ∧ D_v ∧` these 11
consumer argument bridges. Chain ID and configuration are therefore
consumer-constructed verifier arguments connected to producer witnesses by the
joint relation; they are not mislabeled as standalone producer constraints.
Dropped-producer execution/control queries explicitly classify accepted-proof
feasibility as a validation-only assumption.

## Policy separation and T-ARITH

Implementation serialization ends before `POLICY_EVALUATION begin`. The
unchanged policy serializer consumes only the already-emitted occurrence,
balance-change, supply-delta, and nullifier-write interface. The D1P-14D control
mutations affect implementation effects only, and the policy hash remains
`4d22ba313582676fb22c799446faddf7ccfba32b354a96e7485450cfd3d461e8` in
all eight controls.

T-ARITH has the same transformation for both consumer models: exactly one fresh
256-bit `fee_amount` replaces the concrete recovered fee product value, while
branch, overflow, cap, subtraction, receiver, supply, path, and effect
structure remain. Both models declare one fresh fee and contain no concrete
`define-fun fee_amount`; the extracted T-ARITH query retains all 22 paths and
passes cvc5 parse-only validation.

## Archived concrete executions

Fixed-input dropped-producer validation asserts no policy goal; it asks only
whether the extracted successful consumer relation admits the archived values.

| Execution | Extracted path | Expected | SMT result | Disagreement |
|---|---:|---:|---:|---:|
| D1P-12R honest | p18 | success | SAT | none |
| D1P-12R replay | p02 | revert | UNSAT | none |
| D1P-14A FC-POS | p18 | success | SAT | none |
| D1P-14A FC-NEG | p06 | revert | UNSAT | none |
| D1P-14A zero-fee | p21 | success | SAT | none |

These are fixed archived execution checks, not producer search or new primary
diagnostics.

## Eight D1P-14D controls

The validation-only control layer applies the same four D1P-14D implementation
mutations after extracted effect serialization, never to policy:

| Control | Positive mutation | Positive | Extracted BASE negative |
|---|---|---:|---:|
| C1 / G1 | recipient receives full amount in addition to fee mint | SAT | UNSAT |
| C2 / G3 | fee mint benefits recipient | SAT | UNSAT |
| C3 / G4 | extra executed zero-value recipient occurrence | SAT | UNSAT |
| C4 / G5 | extra write at `nullifier + 1` | SAT | UNSAT |

All 8/8 results match the frozen D1P-14D polarity. They are deterministic
encoder controls, not evidence of general search capability or runtime.

## Preserved manual-summary differences

D1P-20 deliberately does not normalize the extracted relation to the frozen
manual summary:

1. **Revert ordering and tentative effects.** With pre-supply `2^256-1`, fee
   one, and amount zero, the source first panics in the first ERC-20 supply
   addition after a tentative nullifier write and fee-mint occurrence. The
   manual summary checks later aggregate conditions and reports the line-172
   subtraction underflow with no tentative occurrence. Both roll back, but the
   extracted source ordering is retained because it is more faithful.
2. **Boundary placement.** The manual summary checks chain ID and configuration
   beside a Boolean verifier result. The extracted consumer constructs those
   verifier arguments. Their producer-witness connection is encoded only in the
   joint relation described above.

The five archived executions show no concrete disagreement; these two modeling
differences remain explicit in `manual-differences.json`.

## Remaining manual inputs

`manual-input-manifest.json` records every remaining manual boundary:

- shared effect-model table version 1.0.0, SHA-256
  `236c4691c410ead94bdb500d904fe91243f66be8ce4e46b96b487fe0d325ac6d`;
- seven declaration entries covering OpenZeppelin 5.6.1 mint, burn, transfer,
  update, balances, total supply, and `Transfer` event semantics;
- the exact resolved `IVerifier.verify(bytes,bytes32[])` relational boundary,
  with `assumed_true=false`;
- owned-local chain ID 31337 and configured Aztec address zero; and
- the separate manual policy interpretation mapping source mint sites to FEE
  or RECIPIENT roles.

The model table is shared and declares `case_specific_entries=false`. Adding a
WarpToad-result-specific entry remains manual implementation input. D1P-14D
mutations are separately labeled validation transforms and are not base-model
inputs.

## Validation and solver accounting

- focused tests: 6/6 pass;
- full extracted joint query: 22 paths, 11 consumer argument bridges, 11
  producer-witness bridges, cvc5 parse-only exit 0;
- extracted T-ARITH query: parse-only exit 0;
- archived execution validation: 5/5 pass;
- deterministic controls: 4 positive SAT and 4 negative UNSAT;
- primary solver calls: **0**;
- validation-only solver calls: 13 fixed queries plus 2 parse-only calls.

The primary evidence is under `results/raw/D1P-20/`, with summary hash and
accounting in `validation.json`. Extraction replaces the manual consumer
summary only for the tested WarpToad mint fragment. Automatic obligation
derivation remains open.
