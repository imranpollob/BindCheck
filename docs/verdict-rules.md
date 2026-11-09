# BindCheck `VERIFIED_WITHIN_SCOPE` rules

**Scope:** `bindcheck_zk` after the L1 soundness revision. These rules establish
only the named, recovered source property for the matched artifacts. They do
not establish whole-application security, E2 model validity, E3 proof
acceptance, or E4 committed effects.

The analyzer uses the research contract's three verdicts. A missing artifact,
ambiguous match, unsupported call path, unresolved modifier/inheritance/proxy,
or screen-only commitment observation is `UNKNOWN`, never a pass. Aggregate
`VERIFIED_WITHIN_SCOPE` requires every applicable retained triple for that
pattern to be verified.

## P1 — protected-effect binding

### `EFFECT_VALUES_DIRECT_PUBLIC_INPUTS`

Property: every recovered recipient, amount, or protected state identity is
either the same normalized expression as a verifier public-vector member, or
is equated to a member by an enforcing guard that dominates that effect in the
supported structured function body.

Justification: direct expression equality needs no inferred circuit
relationship. Guard evidence is limited to `require`/`assert` equality,
rejecting inequality branches, or an effect nested in the equality branch.
The guard must occur in the same enclosing block before the effect, or the
effect must be inside the equality branch. A guard in a sibling branch does
not count. A post-effect guard is `UNKNOWN` because this frontend does not
model the required post-dominance/rollback argument.

Adversarial negatives: `SND-G01`, `SND-G02` in
[`tests/soundness/expected.json`](../tests/soundness/expected.json), plus
`P1-04`, `P1-05`, `P1-19`, `P1-21`, and `P1-23` in
[`tests/controls/expected.json`](../tests/controls/expected.json).

Legitimate positives: `SND-G03`, `SND-G04`, `SND-I02`, `SND-M05`, plus
`P1-01`, `P1-02`, `P1-18`, `P1-20`, `P1-22`, and `P1-25`.

### `RECIPIENT_ALLOWED_BY_ANY_CALLER_POLICY`

Property: the recovered recipient is `msg.sender`, and the caller supplied the
explicit policy flag `any_caller_may_receive=true`. All other recovered effect
roles must independently satisfy a P1 binding rule.

Justification: `msg.sender` is execution context, not proof authorization. It
is accepted only as policy, recorded in the result inputs, rather than inferred
from Solidity syntax. Without the flag it must be directly supplied/equated to
a public input or it is unbound.

Adversarial negative: `SND-I01`. Legitimate positives: `SND-I03`, `P1-03`,
and `P1-26`. `P1-16` and `P1-17` use the flag only to isolate their independent
amount/vector uncertainty and therefore remain `UNKNOWN`.

### `RECIPIENT_BOUND_TO_CONTRACT_SELF`

Property: the recovered recipient normalizes to `address(this)`/`this`, so the
recipient is fixed by the executing consumer rather than caller calldata.
Every other recovered role must independently be bound.

Justification: this is a local identity fact for the analyzed call frame; it
does not infer proxy/delegatecall behavior. Delegatecall is unsupported and
produces `UNKNOWN`.

Adversarial negative: `SND-G07`. Legitimate positive: `P1-13`.

### Commitment observations (never verified)

`COMMITMENT_BINDING_SCREEN_ONLY` and
`COMMITMENT_PREIMAGE_ORDER_UNRESOLVED` are `UNKNOWN`. The analyzer records the
Circom component, ordered source inputs, local recomputation/guard, compiled
R1CS path when present, hashes, and coefficients parsed from each linear
combination. It does not claim that graph connectivity proves algebraic or
cryptographic binding, that the compiled relation implements Poseidon/MiMC,
or that Solidity and Circom use the same domain/encoding.

This is the selected implementation policy instead of a coefficient-aware
recognizer for a restricted hash construction. Adversarial screens are
`SND-M01` (zero-coefficient/nonbinding connectivity), `SND-M02` (altered
coefficients), and `SND-M03` (swapped preimage order). `SND-M04` is the
legitimate construction that is deliberately still `UNKNOWN`; `SND-M05`
shows the unaffected direct-public-input positive.

## P2 — execution-context binding

### `CONTEXT_BOUND_IN_PUBLIC_INPUTS`

Property: a supported chain ID, consumer address, or explicit application
domain expression occurs directly in the recovered verifier public vector.

Justification: the consumer constructs the verified statement from the live
context. The rule does not infer that a particular context is required by
protocol policy; absence remains `UNKNOWN`.

Adversarial negatives: `P2-04`, `P2-05`, and `P2-06`. Legitimate positives:
`P2-01`, `P2-02`, and `P2-03`.

### `CONTEXT_BOUND_IN_PUBLIC_COMMITMENT`

Property: the live chain/contract context occurs inside a supported hash
expression that is itself passed as a public verifier input.

Justification: this is consumer-side statement construction, not the P1
private-opening commitment rule. The exact hash expression is public and
directly supplied to the verifier. It makes no collision-resistance theorem
or circuit-policy claim.

Adversarial negatives: `P2-05` and `P2-06`. Legitimate positives: `P2-09` and
`P2-10`.

### `CONTEXT_BOUND_BY_LOCAL_GUARD`

Property: a supported equality guard between live context and the verifier
vector dominates every recovered protected effect in the supported body.

Justification: P2 uses the same path-sensitive prefix-dominance recognizer as
P1. No effect, an unresolved replay-only path, or a non-dominating context
comparison cannot yield this verdict.

Adversarial negatives: `P2-05`, `P2-06`, and `P2-07`. Legitimate positive:
`P2-08`.

## P3 — replay-key canonicality and consumption

### `REPLAY_KEY_CANONICAL_AND_CONSUMED`

Property: each recovered replay mapping key is proof-bound, checked, consumed,
and either domain-separated/canonicalized locally or protected by a scalar
range guard for the exact public-input position from which that key derives.

Justification: the consumer-vector analysis returns exact numeric positions.
The verifier guard extractor returns exact guarded indices or an all-position
loop. A guard on position `i` cannot discharge a replay key at position `j`.
If proof relationship exists but position recovery fails, the result is
`UNKNOWN`.

Adversarial negatives: `SND-C01`, `P3-02`, `P3-03`, `P3-04`, `P3-07`, and
`P3-15`. Legitimate positives: `SND-C02`, `SND-C03`, `P3-01`, `P3-05`,
`P3-09`, `P3-10`, `P3-11`, `P3-16`, and `P3-17`.

The guarantee remains local to the recovered mapping/body subset. Opaque
helpers, nested mapping semantics outside that subset, modifiers, and unusual
state machines remain `UNKNOWN`.

## P4 — bounded verifier invariants

### `VERIFICATION_KEY_CHECKS_PASS`

Property: parsed gamma/delta differ from the known default-equal G2 pattern,
no duplicate parsed IC point exists, and every fixed public-input position (or
all positions of a dynamic vector) has a recognized rejecting scalar guard.

Justification: source constants and guard positions are extracted directly.
The result says nothing about key ceremony, circuit/key correspondence,
deployment correspondence, or exploitability.

Adversarial negatives: `P4-02`, `P4-04`, and `P4-05`. Legitimate positives:
`P4-01`, `P4-12`, and `P4-13`.

### `PAIRING_LIBRARY_GENERATOR_EXCLUDED`

Property: the only default G2 constants recognized in source/runtime form the
standard pairing-library generator helper, not parsed gamma/delta key
assignments.

Justification: this is a narrow false-positive exclusion for the default-G2
signature. It does not verify the rest of the key.

Adversarial negatives: `P4-02` and `P4-06`. Legitimate positives: `P4-03` and
`P4-07`.

### `RUNTIME_DEFAULT_G2_SIGNATURE_ABSENT`

Property: complete runtime-bytecode parsing finds fewer than two unexplained
groups containing all four default BN254 G2 coordinates.

Justification: this verifies only absence of the named bytecode signature
within completely parsed runtime bytes. Truncated bytecode is `UNKNOWN`.

Adversarial negative: `P4-06`. Legitimate positive: the runtime-absence branch
covered by the P4 runtime controls; `P4-08` is the truncated `UNKNOWN` control.

## P5 — public-input interface agreement

### `PUBLIC_INPUT_COUNT_AND_ORDER_MATCH`

Property: recovered consumer count, verifier arity, and complete circuit public
count agree, and complete recovered consumer/circuit semantic names occur in
the same order.

Justification: the rule compares explicit fixed vectors or complete compiled
metadata. Equal counts with unresolved/renamed meaning are `UNKNOWN`, not a
pass.

Adversarial negatives: `P5-02` and `P5-04`; unresolved negatives include
`P5-08`, `P5-15`, and `P5-16`. Legitimate positives: `P5-01`, `P5-03`,
`P5-07`, and `P5-09` through `P5-14`, subject to each control's recorded
shape.

### `DYNAMIC_PUBLIC_INPUT_LENGTH_GUARDED`

Property: a dynamic consumer vector has an exact local length guard equal to
the matched verifier declaration. Only the count subproperty is verified.

Justification: the result explicitly records that element meaning/order was
not independently named. An unguarded dynamic vector is `UNKNOWN`.

Adversarial negative: `P5-06`. Legitimate positive: `P5-05`.

## Aggregation and non-vacuity boundary

Per-pattern aggregation returns `VERIFIED_WITHIN_SCOPE` only when at least one
applicable result exists and every applicable retained result is verified.
Any applicable `UNKNOWN` prevents aggregate verification; any applicable
`VIOLATION` dominates. Applicability is separate and cannot turn missing or
unsupported evidence into a pass.
