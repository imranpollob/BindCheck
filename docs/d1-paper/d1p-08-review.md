# D1P-08 Track A interpretation and symbolic-consumer review

Date: **25 October 2026**. Review status: **READY FOR BOTH PLANNERS**.
Research verdict: **UNKNOWN**. This note adds a prospective interpretation and
component review; it does not rewrite D1P-07 or rerun Track A.

## 1. Frozen Track A evidence

`scripts/d1p_08_review.py` independently joined the D1P-04 artifact manifest,
the D1P-06 input manifest, the D1P-07 campaign ledger, and every on-disk
specialized query hash. It verified 150/150 rows before classifying the exact
specialized goal text.

| Goal syntax | D1P-07 result | Cells |
| --- | --- | ---: |
| Literal `false` | UNSAT | 58 |
| Literal `true` | timeout / UNKNOWN | 42 |
| Nontrivial expression | timeout / UNKNOWN | 50 |

The six goal-only diagnostics are SAT. The two producer-cone-only diagnostics
time out at 300.042378 and 300.028234 seconds. The selected producer cone is
therefore independently difficult under the frozen encoding and budget. A
literal-true goal removes only goal difficulty; it does **not** make the
remaining producer constraints syntactically or computationally trivial.

This observation does not imply that adding consumer constraints must preserve
the same timeout. Such constraints can make a conjunction easier, harder, or
inconsistent. Future reporting must keep literal-false, literal-true, and
nontrivial goals separate, and must not count a literal-true timeout as a
nontrivial goal timeout.

The raw audit is `results/raw/D1P-08/track-a-review.json`, SHA-256
`73fd90d57e39a711059519f5743650670835ea0767bb75b108cede022aad138d`.
Its three tracked inputs are:

| Input | SHA-256 |
| --- | --- |
| `metadata/d1/d1p-04-artifact-manifest.json` | `1a713bc5f464eda5e33218cd7985882405f06e5cccb8a3a79b7d5f1cb1e7e2ff` |
| `metadata/d1/d1p-06-input-manifest.json` | `67f588f4e1254b28cc17e226b31039574c6d2b26db4b16214c9d63a813b0fef5` |
| `metadata/d1/d1p-07-track-a-ledger.json` | `3c4d9b8293c91e88124b233c45e1fe46c0382377d823704f612f3d1c2a81e317` |

## 2. Minimal symbolic consumer

`src/bindcheck_d1/symbolic_consumer_v2.py` builds an inspectable,
solver-neutral expression DAG for a configurable number of message words. It
reuses the existing concrete `Token`, V2 admission, occurrence-key, policy,
and injective `Counter`-matching foundations. Evaluation is over a supplied
concrete assignment; the component does not launch a solver and is not a full
joint encoder.

The modeled successful transition follows pinned Payy B
`dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36`, whose
`eth/contracts/rollup3/RollupV1.sol` SHA-256 is
`7062065cc95f447fea8bb28242d51c836c3cf9e39f1625180ecf9c240a5ffd8f`:

- the registered verifier supplies the configurable message length, and the
  public-input vector must contain three header words plus exactly that length;
- kind 0 advances one word, kind 2 consumes four, kind 3 consumes five, and
  every other kind reverts; record reads use exact calldata bounds;
- mint registry checks and sequential spent writes are modeled, including the
  default all-zero mint entry and its protected zero-value spent write;
- burn recipients use the low 160 bits, ordinary token balances update in
  sequence, failed transfers are explicit, and successful committed transfers
  alone enter the protected-effect multiset;
- the supported V2 scope remains the funded ordinary OpenZeppelin 5.0.1 token
  with no substitutions; unsupported token targets, substitutions, unresolved
  boundaries, and out-of-fragment inputs produce `UNKNOWN`, never safety;
- validator-set writes made by the signature guard, mint writes, token state,
  the new root, and block height all roll back when any later outer condition
  reverts; and
- `P` (permissions), `O` (obligations), and committed `E` (effects) remain
  separate multisets. Authorization and coverage use exact semantic keys,
  occurrence multiplicity, and injective matching.

Constructing another length does not expand the V2 admission family: the
existing admission code continues to allow only its reviewed N=8/N=1000
scope and independently rejects unsupported funding, values, recipients,
substitutions, or deferral.

## 3. Verifier, forwarding, and attacker boundaries

The symbolic result records whether the verifier call is reached and accepted,
the exact requested verification-key word, expected relation-key word,
registered verifier address, complete ordered public-input vector and its
SHA-256, proof-byte SHA-256, relation identity, and whether the relation is the
full producer relation or only an abstraction.

The explicit external assumption is proof soundness: if the exact registered
verifier accepts a proof under the exact verification key and exact
public-input vector, then a satisfying witness exists for the producer relation
bound to that key and vector. A result establishes the component's
`sound_binding_established` flag only when the call is reached, acceptance is
true, the key identities match, the relation is labeled
`FULL_PRODUCER_RELATION`, and proof soundness is admitted. The historical T22
selected cone is explicitly `SELECTED_CONE_ABSTRACTION`; it can never satisfy
that flag by relabeling.

Pinned `agg_final` directly constructs the `agg_agg` public-input vector as
the two pinned key hashes, old root, new root, commit hash, and all 1,000
messages before recursively verifying it. D1P-08 records that source fact but
does not encode the recursive verifier, prove the forwarding correspondence,
or equate the N=8 T22 cone with that full relation. Those are remaining joint
integration obligations.

The `onlyProver` lookup and `verifyValidatorSignatures` result/state update are
explicit abstract boundary choices. A positive assignment must state its
evidentiary basis, the validator-set post-state, and the attacker capabilities
being admitted. The component does not silently assume an arbitrary user can
be a registered prover or supply a validator quorum. A later security query
must choose and justify one of, for example, an owned registered prover, a
compromised prover role, or a legitimately scheduled prover plus the required
signature capability.

The evidence categories are intentionally separate:

- **Extracted facts:** source-derived decoding, guards, registry/token effects,
  rollback, low-160 conversion, verifier-call arguments, and forwarding.
- **Analyst policy:** which certified producer occurrences form `P`, which are
  mandatory `O`, compatibility keys, and the funded/no-substitution research
  scope. Implementation behavior alone does not establish this policy.
- **External assumptions:** proof soundness, the exact deployed verifier/key
  correspondence, ordinary-token implementation correspondence, admitted
  caller/signature capabilities, and any reachability/pre-state premise.

No conclusion in this task extends beyond a fixed supplied pre-state or makes
a reachable-history claim. Unsupported kind-4 policy occurrences remain
`UNKNOWN`. A T22 result does not automatically become a D1 result.

## 4. Offline component validation

`scripts/d1p_08_symbolic_check.py` reads the exact pinned Solidity from Git,
loads the reviewed OpenZeppelin 5.0.1 sources, invokes pinned solc 0.8.20 only
to obtain the AST, revalidates the existing guard-frame certificate, and
compares symbolic-expression evaluation with the existing concrete AST
executor. It does not invoke cvc5, a proof tool, an EVM, or a live consumer.

All **12/12** cases match on outcome, protected state, validator-set state,
root/height, mint-spent state, sequential token balances, protected-effect
counts, and rollback where applicable:

- normal padding;
- a normal burn with high recipient bits, checking low-160 decoding;
- a zero-value default mint, checking the spent write remains protected;
- duplicate-mint rollback;
- a late truncated record after a transfer, checking outer rollback;
- invalid-kind revert;
- `onlyProver` rejection;
- signature-guard rejection;
- verifier rejection after message effects;
- height rejection after verifier acceptance;
- two sequential burns with a later failed transfer; and
- a self-transfer occurrence with sequential balance semantics.

The final raw result is
`results/raw/D1P-08/symbolic-validation-05/validation.json`, SHA-256
`281f5434570642155b172b758c7e7fa4d71d3cbc47cf8576d6f091720384fae9`.
The earlier `symbolic-validation-01` through `-04` attempts remain preserved;
they record fixture-label and boundary-hardening iterations and are not the
reported final validation.

This is component testing on selected concrete assignments, not universal
symbolic equivalence, accepted-proof evidence, a full consumer replay, or
proof-backed end-to-end behavior. The research verdict remains `UNKNOWN`.

