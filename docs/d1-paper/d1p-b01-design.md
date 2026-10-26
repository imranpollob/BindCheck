# D1P-B01 — WarpToad joint-model design

Date: **26 October 2026**<br>
Worktree: `/Users/imranpollob/Coding/bc/bindcheck-lane-b`, branch
`lane-b-design`, HEAD `9fabd08` (no commit, push, merge or branch change)<br>
Task status: **DESIGN REVISION 1 FOR REVIEW** (change log at the end)<br>
Fee-split policy (Section 4): **DRAFT — NOT APPROVED**<br>
Research verdict: **UNKNOWN**

This is a design document. No solver query, proof, build, compile,
consumer replay, live-chain call or tool tuning was run. Nothing here is a
vulnerability finding, a negative control, a held-out result or an
independent annotation. WarpToad is an exposed **development** family under
D1P-11.

It follows the [research contract](../research-contract.md) (Sections 4–8),
the [D1P-03 protocol](d1p-03-protocol.md) (Track B evidence grades; its
budgets are superseded), [D1P-04 protocol](d1p-04-protocol.md) §1 (current
method, budget, validation and freeze rules), [D1P-07
protocol](d1p-07-protocol.md) and its resource policy (sampled-RSS memory), [V2 joint semantics](../../protocols/d1/d1-03-joint-semantics-v2.md)
(exact occurrence matching), [D1P-08](d1p-08-feasibility.md) /
[D1P-08 review](d1p-08-review.md) (consumer-success trace intersection and
evidence categories), [D1P-09](d1p-09-feasibility.md) (conservative
propagation rules) and [D1P-11](../../reports/D1P-11.md) with its
[ledger](../../metadata/d1/d1p-11-screening-ledger.json).

### Labels used throughout

| Label | Meaning |
| --- | --- |
| **SRC** | Confirmed in a hash-verified pinned file at the cited line |
| **TS-ONLY** | Stated only by the TypeScript prover helper, not by the circuit or consumer |
| **UNRETRIEVED** | Depends on a pinned-revision file outside the D1P-11 hash record (Section 0.2) |
| **LANE-A** | Depends on the not-yet-built Lane A WarpToad fixture (artifact/key/verifier/proof and fork-free initialization; Section 6) |
| **ASSUMED** | An external or cryptographic assumption, never mechanically established here |
| **DRAFT** | An unapproved policy proposal |

## 0. Source retrieval and verification

### 0.1 Retrieved and verified

The five WarpToad files in the D1P-11 record were fetched at revision
`973e7d1e4b60d0d8a8ca299b0cabd9193b147ef8` into the ignored lane-local folder
`results/raw/D1P-B01/source/`, using
`curl -fsSL https://raw.githubusercontent.com/warptoad/warp-toad/<rev>/<path>`
(curl 8.7.1; five calls, each exit 0; `2026-10-26T13:46:00Z`). Each was
SHA-256-hashed and compared with
`/Users/imranpollob/Coding/bc/bindcheck-d1-paper/results/raw/D1P-11/retrieved-source-hashes.json`
(read-only; that record's own SHA-256 is `ac8c19ed…c090ce61b`).

| Path | SHA-256 | Match |
| --- | --- | --- |
| `backend/circuits/withdraw/src/main.nr` | `ce4bf56b…6e28de192f` | yes |
| `backend/contracts/core/WarpToadCore.sol` | `323a1cf2…a60011e122c39` | yes |
| `backend/test/testL1ToL1.ts` | `1c831d9e…6a4780ff349` | yes |
| `backend/lib/proving.ts` | `e1c7e4d2…0892f2c24d8323c` | yes |
| `backend/package.json` | `01f2bae4…3da8801b0aa57b` | yes |

All five match, so the stop condition did not trigger. Full hashes, the
command and tool versions are in the ignored
`results/raw/D1P-B01/retrieval.json`. Line citations below refer to these
exact bytes. Short names: `main.nr`, `Core.sol`, `proving.ts`, `test.ts`.

### 0.2 Deliberately not retrieved

The task requires verifying every retrieved file against the D1P-11 record,
and these files are not in it. They were therefore **not** fetched, and every
claim that depends on them is marked UNRETRIEVED:

- the `hashing` crate (`hash_commitment`, `evm_merkle_verify`,
  `aztec_merkle_verify`, the `*_merkle_data` structs) and the `constants`
  crate imported at `main.nr:2-9`;
- `README.md`, which D1P-11 cites for intended policy;
- the concrete `L1WarpToad` (`wrap`), `GigaBridge` and root-messenger
  contracts;
- `poseidon-solidity` `PoseidonT3`, `@zk-kit/lazy-imt.sol` and the resolved
  OpenZeppelin ERC-20 version; and
- the compiled `withdraw.json`, VK and generated Solidity verifier (D1-02
  found the compiled circuit but did not fetch it).

D1-02 also never fetched the hashing crate, so the project has no recorded
evidence of how the circuit composes its hashes. The integrator or Lane A
should add a hash-recorded fetch for it.

## 1. Public-input provenance

### 1.1 Classification

The consumer builds the eleven-word vector itself in
`_formatPublicInputs` (`Core.sol:114-140`) and calls the fixed verifier at
`Core.sol:161`. The vector's order matches the Noir signature
(`main.nr:15-34`) at source level (SRC). Whether the compiled ABI has the same
order is LANE-A.

Definitions:

- **Consumer-supplied:** the consumer produces the word from a block value,
  stored state or stored configuration, independently of the caller.
- **Calldata-supplied:** the word is a caller argument to `mint`. It may also
  be **state-guarded** if the consumer requires it to be a member of stored
  state before verification.
- **Proof-only:** the word exists in the proof's public statement with no
  consumer-side origin.

| # | Name (`main.nr` line) | Class | Consumer source | Prover source (`proving.ts`) | Constrained in circuit by | Consumer use after decode |
| ---: | --- | --- | --- | --- | --- | --- |
| 0 | `nullifier` (15) | Calldata, state-guarded (negative membership) | `_nullifier`, `Core.sol:144`; `require(!nullifiers[_nullifier])` `:157` | `hashNullifier(nullifierPreImage)` `:336` (TS-ONLY) | `_nullifier == nullifier` `:66`, from `hash_commitment` `:65` | Protected write `nullifiers[_nullifier]=true` `:158` |
| 1 | `chain_id` (16) | **Consumer-supplied: block value** | `block.chainid`, `Core.sol:160` | `publicClient.getChainId()` `:331` | Input to `hash_commitment` `:65` only | None beyond the vector |
| 2 | `amount` (17) | Calldata | `_amount`, `Core.sol:145` | caller argument `:318`, `:351` | `!amount.lt(max_fee)` `:47`; input to `hash_commitment` `:65` | Mint amounts `:172`, `:175` |
| 3 | `giga_root` (18) | Calldata, state-guarded | `_gigaRoot` `:146`; `gigaRootHistory` `:155` (written `:77`, `:189`) | `warpToadDestination.read.gigaRoot()` `:332` | Merkle root for `origin_local_root` only when `destination_local_root != origin_local_root` (`:56-62`) | Guard only |
| 4 | `destination_local_root` (19) | Calldata, state-guarded | `_localRoot` `:147`; `localRootHistory` `:156` (written `:110`) | `read.cachedLocalRoot()` `:333` | Only the branch test `:56` | Guard only |
| 5 | `aztec_warptoad_address` (20) | **Consumer-supplied: stored configuration** | `aztecWarptoadAddress` `Core.sol:49`, set once in `initialize` `:67-73`, used `:160` | origin contract's address `:240`, `:306` | Passed to `aztec_merkle_verify` `:71` on the `is_from_aztec` branch only; internal use UNRETRIEVED | None beyond the vector |
| 6 | `fee_factor` (30) | Calldata | `_feeFactor` `:148` | caller argument `:319` | `fee_factor != 1` `:50` | Branch `:164`; fee formula `:165` |
| 7 | `priority_fee` (31) | Calldata | `_priorityFee` `:149` | caller argument `:320` | `priority_fee != 0` `:53` | Fee formula `:165` |
| 8 | `max_fee` (32) | Calldata | `_maxFee` `:150` | caller argument `:321` | `!amount.lt(max_fee)` `:47` | `require(_relayerFee <= _maxFee)` `:166` |
| 9 | `relayer_address` (33) | Calldata | `_relayer` `:151`; encoded at `:137` | `BigInt(relayerAddress)` `:337` | `relayer_address != 0` `:51` | Mint beneficiary `:171`; replaced by `msg.sender` when equal to `address(1)` **after** verification (`:168-170`) |
| 10 | `recipient_address` (34) | Calldata | `_recipient` `:152`; encoded at `:137` | `BigInt(recipientAddress)` `:338` | `recipient_address != 0` `:52` | Mint beneficiary `:172`, `:175` |

Counts:

- **Consumer-supplied:** 2 (`chain_id` from a block value;
  `aztec_warptoad_address` from stored configuration).
- **Calldata-supplied:** 9, of which 3 are state-guarded (`nullifier`,
  `giga_root`, `destination_local_root`).
- **Proof-only:** 0. Every public word has a consumer origin. Proof-only
  values do exist, but they are the seven **private** inputs
  (`main.nr:37-43`): `origin_local_root`, `is_from_aztec`,
  `nullifier_preimage`, `secret` and the three Merkle-data structs.

### 1.2 Decoding facts for `D_v(p, x)`

- Every `uint256` word becomes `bytes32(uint256)` (`Core.sol:133`). Addresses
  become `uint256(uint160(bytes20(addr)))`, left-padded with zeros (`:137`),
  matching the circuit comments at `main.nr:33-34` (SRC). Every address is
  below `2^160 < p`.
- **Field canonicality (LANE-A).** Words 0, 2, 3, 4, 6, 7 and 8 are arbitrary
  calldata `uint256` values, while the circuit sees elements of the BN254
  scalar field `F_p`. Whether the generated keccakZK UltraHonk verifier
  **rejects** a word `>= p` or **reduces** it modulo `p` is unknown until
  Lane A pins the verifier. `D_v` must encode the verifier's actual map. If
  it reduces, the consumer's `uint256` keys (`nullifiers[...]`, mint amounts)
  and the circuit's field values can disagree. This is the
  range/canonicality obligation in contract Section 5.5. It is a modeling
  requirement, not a finding.
- **Vector length (LANE-A).** Whether the generated verifier expects exactly
  11 public inputs or appends proof-carried extra inputs internally must be
  checked against the compiled ABI and verifier.
- **Atomicity (SRC).** The nullifier write (`:158`) precedes verification
  (`:161`), and any later `require` or checked-arithmetic failure reverts the
  whole call. Effects count only when the outer call returns, following V2.

## 2. Binding dependencies

### 2.1 Proof-enforced and consumer-enforced relations

Relations enforced by the circuit relation `R_v`:

| Id | Relation | Source | Hash / Merkle |
| --- | --- | --- | --- |
| C1 | `max_fee <= amount`, compared as canonical integers through `Field.lt` | `main.nr:47` | — (range/limb constraints) |
| C2 | `fee_factor != 1` | `:50` | — |
| C3 | `relayer_address != 0` | `:51` | — |
| C4 | `recipient_address != 0` | `:52` | — |
| C5 | `priority_fee != 0` | `:53` | — |
| C6 | `destination_local_root == origin_local_root`, or `origin_local_root` is a leaf of `giga_root` | `:56-62` | **Merkle** (`evm_merkle_verify`, giga depth; UNRETRIEVED) |
| C7 | `(commitment, n') = hash_commitment(nullifier_preimage, secret, chain_id, amount)` | `:65` | **Hash** (composition UNRETRIEVED; TS-ONLY: `pre = H(np, s, chain)`, `commitment = H(pre, amount)`, `n = H(np)`, `proving.ts:334-336`) |
| C8 | `n' == nullifier` | `:66` | **Hash-mediated** (through C7) |
| C9 | `commitment` is a leaf of `origin_local_root`, in the Aztec tree (with `aztec_warptoad_address`) if `is_from_aztec`, else in the EVM tree | `:70-74` | **Merkle + hash** (Aztec siloing/unique-note hashing and the EVM node hash are UNRETRIEVED) |

Relations enforced by the consumer:

| Id | Relation | Source |
| --- | --- | --- |
| K1 | `gigaRootHistory[giga_root]`; the history is written at initialization (`:76-78`) and by the `onlyGigaRootProvider` role (`:188-191`) | `Core.sol:155` |
| K2 | `localRootHistory[destination_local_root]`; written by `storeLocalRootInHistory`, which is public, from the LazyIMT root over burn leaves (`:97-98`, `:107-111`) | `:156` |
| K3 | `!nullifiers[nullifier]`, then the write | `:157-158` |
| K4 | Vector construction with `block.chainid` and the configured address | `:160` |
| K5 | `verify(proof, vector)` against the fixed verifier set in the constructor (`:59`) | `:161` |
| K6 | If `fee_factor != 0`: `fee = fee_factor*(block.basefee+priority_fee)` with checked arithmetic, `fee <= max_fee`, the `address(1)` wildcard, `mint(relayer, fee)` and `mint(recipient, amount-fee)` with checked subtraction. Otherwise `mint(recipient, amount)` | `:164-176` |
| K7 | Source side: `_burn(sender, amount)`, then leaf `PoseidonT3(preCommitment, amount)` inserted into the LazyIMT | `:95-98` (**Hash + Merkle**, consumer side) |

Cryptographic and correspondence relations:

| Id | Relation | Status |
| --- | --- | --- |
| A-PS | **Knowledge** soundness of keccakZK UltraHonk for the pinned VK, which binds all 11 words | ASSUMED, key identity LANE-A. Soundness alone is not enough for Section 3.5. |
| A-CR | Collision resistance of each hash instance | Enters only guarantee (b), whose obligations B1–B6 are open (Section 3.5) |
| A-HC | Solidity `PoseidonT3` and the LazyIMT root equal the circuit's leaf/node hash and tree convention (depth, zero leaves) | ASSUMED, UNRETRIEVED + LANE-A |

### 2.2 Per-quantity dependency map

| Protected quantity | Depends on | Through hash/Merkle? | Notes |
| --- | --- | --- | --- |
| **Amount** | K4/K5 (word 2), C1, C7 → C9 → C6 → K1/K2 → K7, K6 arithmetic, A-PS, A-CR, A-HC | **Yes:** C7, C9, C6, K7 | Burn-to-mint conservation holds only if the minted `amount` equals the burned amount sealed in the leaf. That needs the leaf hash to bind `amount` (A-CR) and to equal the consumer's leaf hash (A-HC). |
| **Recipient** | K4/K5 (word 10, low 160 bits), C4, K6 beneficiary, A-PS | **No** | `recipient_address` enters no hash. It is bound to the proof transcript, not to the source commitment. Whoever holds the witness `(np, s)` chooses it. |
| **Relayer fee** (amount and beneficiary) | Words 6–9 via K4/K5, C1 (`max_fee <= amount`), C3, K6 (`block.basefee`, cap, wildcard), A-PS | **No** | The fee amount is **not** fixed by the proof. It depends on `block.basefee`, which the consumer supplies at execution, and is bounded only by `max_fee`. With `relayer_address == 1`, the beneficiary is `msg.sender` (`:168-170`). C2's source comment (`main.nr:49`) says it may only silence compiler warnings; C2 and C5 are not used as policy. |
| **Chain ID** | K4 (`block.chainid`), C7 → C9 → C6 → K2/K1, A-CR | **Yes** | Chain ID enters only the commitment preimage, which on the burn side (`:92-97`) is the user-chosen `preCommitment`. |
| **Nullifier** | K3, K4/K5 (word 0), C7/C8, A-CR, word canonicality (LANE-A) | **Yes** | K3 enforces single use per `uint256` word. Single use per **source commitment** also needs (a) commitment → `np` binding (A-CR on C7) and (b) a word → field map that is injective on accepted words (LANE-A). |
| **Domain** (instance and asset) | Local branch: K2 (own history). Giga branch: C6 + K1 (giga leaves chosen by the provider; UNRETRIEVED). Aztec: K4 address + C9 (UNRETRIEVED) | **Yes** | No circuit relation names the destination contract or token. Domain binding of an EVM-origin commitment rests on which local roots the giga tree admits, which is a deployment invariant, not part of `R_v`. |

`getFreeShit` (`Core.sol:199-201`) is an unrestricted public mint outside the
proof-consuming path. Following D1-02, the model infers no global supply
guarantee and observes only the effects of `mint` and `burn` calls.

## 3. Hash abstraction and preservation argument

### 3.1 Hash instances

| Instance | Where | Evidence |
| --- | --- | --- |
| `H_leaf^sol(pre, amt)` = `PoseidonT3.hash([pre, amt])` | `Core.sol:97` | SRC (library UNRETRIEVED) |
| `H_node^sol` (LazyIMT node hash) | `Core.sol:98`, `:180` | UNRETRIEVED |
| `H_pre`, `H_leaf`, `H_null` inside `hash_commitment` | `main.nr:65` | UNRETRIEVED; TS-ONLY shape at `proving.ts:334-336` |
| `H_node^evm` in `evm_merkle_verify` (local and giga trees) | `main.nr:61`, `:73` | UNRETRIEVED; TS uses `poseidon2` from `poseidon-lite` (`proving.ts:99`, `:152`) |
| Aztec siloing, unique-note and note-tree hashes | `main.nr:71` | UNRETRIEVED; TS-ONLY at `proving.ts:229-231` |

These are possibly distinct concrete functions. The Aztec tree uses
different hashing from the EVM tree (comment at `main.nr:68`). Whether pairs
of them are identical is an implementation fact, decided by A-HC and LANE-A
test vectors.

### 3.2 Abstraction `α`

For each concrete hash function `H_k` used by the query, `α` replaces every
occurrence of the region that computes `z = H_k(x⃗)` with `z = f_k(x⃗)`, where
`f_k` is a fresh uninterpreted function over the same sorts. All other
constraints are kept verbatim, including predicates and branch muxes around
the region, range constraints on `z`, and the consumer and policy
constraints.

Preconditions, each checked and recorded per query. Failure means the region
is not abstracted, or the result is UNKNOWN.

1. **Locality.** The region's internal witnesses, such as permutation-round
   intermediates, occur in no constraint outside the region. Otherwise those
   constraints are retained and the internals stay visible.
2. **Functionality.** The replaced constraints determine `z` uniquely from
   `x⃗`: `Ψ(x⃗,z₁,i₁) ∧ Ψ(x⃗,z₂,i₂) ⇒ z₁ = z₂`. For an ACIR black-box opcode
   this follows from ACVM semantics. For inlined arithmetic it is a proof
   obligation. Without it, functional consistency of `f_k` would exclude
   concrete models (under-approximation). The sound fallback is an
   uninterpreted **relation** `ρ_k(x⃗, z)` with no functionality axiom.
3. **One symbol per concrete function.** Using one symbol for two different
   concrete functions forces agreement that the concrete semantics lacks,
   which is unsound. Two sites share `f_k` only under an explicit identity
   fact, marked ASSUMED (A-HC) until Lane A validates it. Distinct symbols for
   the same function are always sound but lose precision.
4. **Domain coercion.** Where Solidity hashes `uint256` arguments, the
   abstraction applies the library's actual input map (for example
   `f(x mod p, y mod p)` if the library reduces). The map is LANE-A; until it
   is known, use a separate symbol.
5. **Provenance.** Each replaced region records its ACIR opcode range or
   Solidity call site, the source line and the artifact hash.

### 3.3 Guarantee (a): plain-UF preservation (sound, unconditional)

Let `Φ[H]` be the concrete joint query (producer relation, decoding,
consumer transition, admitted history, policy violation goal) with the
concrete functions `H = (H_k)`, and let `Φ[f]` be its abstraction.

> **Claim (a).** If `σ ⊨ Φ[H]`, then `σ ∪ {f_k ↦ H_k} ⊨ Φ[f]`. Hence
> `Φ[f]` UNSAT ⇒ `Φ[H]` UNSAT.

*Argument.* Under preconditions 1–2, each removed region's constraints, for
any concrete satisfying assignment, are equivalent to `z = H_k(x⃗)`, and
`H_k` is a function. Interpreting `f_k` as `H_k` satisfies the replacement
equation. Under precondition 3, no two distinct concrete functions are forced
to agree. Under precondition 4, arguments match. All other constraints are
unchanged. So every concrete model extends to an abstract model with the
same observations (words, effects, state), which is exactly the inclusion
required by contract Section 7.

The argument uses only that each `H_k` is a total function. It uses no
injectivity, collision resistance, extraction or randomness property. An
abstract UNSAT is therefore a concrete UNSAT for the relation. It relies only
on the extraction-fidelity and compiler assumptions, and on the proof-system
soundness that links verifier acceptance to `R_v`.

**Sound refinement.** Adding a ground instance `f_k(c⃗) = H_k(c⃗)` for
concrete constants `c⃗`, with the right-hand side computed by the pinned
reference implementation, preserves Claim (a), because `H_k` satisfies it.
This is the only unconditional hash refinement.

**Corollary (a′), still purely logical.** Let `T` be the finite set of hash
applications in the query after Ackermannization. In fixed-pre-state mode,
`T` includes the ground instances of the admitted honest trees (LANE-A).
Define the **local no-collision** formula

`NC_k(T) := ⋀_{f_k(a⃗), f_k(b⃗) ∈ T} ( f_k(a⃗) = f_k(b⃗) ⇒ a⃗ = b⃗ )`,

which is a finite formula over the query's own terms, not a universal axiom.
If `Φ[f] ∧ NC(T)` is UNSAT, then by Claim (a) every concrete model of `Φ[H]`
violates `NC(T)` under `f := H`. So every concrete violation within bounds
exhibits two terms of `T` with distinct arguments and equal concrete hash
values. This follows from (a) alone. **It is not a security guarantee**:
Poseidon collisions exist, so (a′) only says what a violation would have to
contain.

### 3.4 Why injectivity cannot be an axiom

The 2-to-1 Poseidon instances map `F_p²` (or `F_pⁿ`) to `F_p`, so by
pigeonhole they have collisions. The axiom `∀x⃗,y⃗. f(x⃗)=f(y⃗) ⇒ x⃗=y⃗` is
**false of `H_k`**: `H_k` is not a model of it, and Claim (a) fails. An
UNSAT obtained with that axiom says nothing about Poseidon. It is forbidden.

### 3.5 Guarantee (b): computational argument (OPEN, not discharged)

**Intended statement, not established.** If keccakZK UltraHonk is
knowledge-sound for the pinned VK (A-PS) and each `H_k` is collision
resistant (A-CR), then whenever (a′) holds, no efficient adversary produces
an accepted violating history except with negligible probability.
Existential soundness alone cannot give this: because collisions exist, a
satisfying witness for a violating statement may exist, so the argument
needs an extractor that turns an adversary into a collision finder.

Turning (a′) into (b) requires these obligations. **All are open.**

| Id | Obligation | Status |
| --- | --- | --- |
| B1 Extraction | Knowledge soundness of keccakZK UltraHonk for the pinned VK and compiled relation, in a stated model (Fiat–Shamir over Keccak in the random-oracle model; the commitment-scheme assumptions), with an extractor that outputs the **complete** ACIR witness, including every input of every hash region | Open; ASSUMED at most; key identity LANE-A |
| B2 Multi-proof extraction | Violations over `Reach_L` (for example, single use) involve two or more accepted proofs, possibly chosen adaptively after the adversary sees other parties' public proofs. This needs simulation-extractability or multi-instance extraction with bounded loss. | Open |
| B3 Term coverage | `T` must contain every hash application the violation depends on: each extracted witness's C7 applications (pre-commitment, leaf, nullifier) and every C9/C6 node; every consumer-side application (each burn leaf, K7, and every LazyIMT node of every admitted root, including zero subtrees); and the fixed-pre-state ground instances. It must also be shown that the collision exhibited by (a′) consists of values the reduction actually obtains from the extractor and the public history. | Open; the hashing crate and LazyIMT internals are UNRETRIEVED, so the term set cannot yet be enumerated |
| B4 Instance identity | A collision between two symbols (for example, the circuit leaf hash and Solidity `PoseidonT3`) is a collision of one concrete function only if A-HC holds. If distinct symbols are used for one function, the coverage argument must merge them under A-HC. | Open; LANE-A |
| B5 CR domain | CR is a statement over canonical field inputs. `uint256` inputs reduced modulo `p` give trivial non-canonical "collisions" (`x` versus `x+p`) that CR does not exclude. These are handled by `D_v` and canonicality (LANE-A), not by (b). | Open; LANE-A |
| B6 Reduction accounting | Advantage bound (extraction loss times the term-pair count), and the stated security level of each Poseidon instance and parameter set | Open |

Reporting rules:

- While B1–B6 are open, a query result `Φ[f] ∧ NC(T)` UNSAT is reported as
  **UNKNOWN** with reason `CR_ARGUMENT_OPEN`, together with the (a′)
  statement. It is never `VERIFIED_WITHIN_SCOPE` on its own.
- If the planners later accept some obligations as stated assumptions under
  contract Section 5.2, the result may be `VERIFIED_WITHIN_SCOPE`
  *conditional on that accepted list*. Unaccepted items keep it UNKNOWN.
- Any result obtained after an `NC` constraint was introduced, including as a
  refinement, carries the tag `CR_CONDITIONAL_OPEN`, even if a later step
  removes the constraint. `NC` is not a sound refinement in the sense of (a).

| Property | Hash on the path? | (a) can decide it alone? | Needs (b)? |
| --- | --- | --- | --- |
| Beneficiary match; fee cap; `x_R + x_F = amount` within one call | No | Yes (A-PS still links acceptance to `R_v`) | No |
| Minted amount equals the burned amount of the source leaf | Yes (C7, C9, K7) | Only if a violation is UNSAT without `NC` (anticipated not, as a hypothesis rather than an observation) | Yes |
| Destination chain equals the depositor's sealed chain | Yes (C7) | As above | Yes |
| Each source occurrence consumed at most once across `Reach_L` | Yes (C7/C8), plus canonicality | As above | Yes, plus B5 |
| Source occurrence derivable (§4.4 step D7) | Yes (Merkle) | As above | Yes |

### 3.6 Concrete validation of violation and non-vacuity candidates

Every abstract SAT model is an **abstract candidate**. Validation has two
separately accounted phases (D1P-04 Section 1.3).

**Method-internal concretization.** Charged to the method's analysis
budget. Every adaptive query is hashed and logged before it runs.

| Stage | Action | Failure outcome |
| --- | --- | --- |
| M1 Capture | Serialize the full model: all words, private leaves (`np`, `s`, paths, indices, `is_from_aztec`), history transactions, and every `f_k` application with its value | Missing data → UNKNOWN |
| M2 Collision audit | For each symbol, flag two applications with distinct arguments and equal values, including against ground tree instances | **Reject: `COLLISION_DEPENDENT`.** Never a VIOLATION. A method may refine with `NC` for that pair (`CR_CONDITIONAL_OPEN`) |
| M3 Hash concretization | Discard model hash values. Recompute every application bottom-up with the pinned reference implementations (LANE-A), replaying the candidate's `Reach_L` history (burn leaves, LazyIMT roots, root history) from its free leaves. Re-check every non-hash constraint, the consumer guards, the source-occurrence derivation (§4.4) and the goal | **`HASH_INCONSISTENT`** (spurious). Refine with sound ground instances (§3.3) within budget |
| M4 Optional ACIR check | `nargo execute` on the pinned ACIR, used only to steer refinement (LANE-A toolchain) | Rejection → refine within budget |

**Final validation.** Not analysis budget. Each method has an equal,
separate allowance. Results are reported separately. The allowance cannot be
transferred between methods or used to continue abstract search.

| Stage | Action | Failure outcome |
| --- | --- | --- |
| F1 Concrete model | `nargo execute` on the pinned compiled withdraw ACIR with the concretized witness and public words | `ACIR_REJECTED` → UNKNOWN; further refinement only within the remaining analysis budget |
| F2 Consumer replay | The unchanged consumer under fork-free owned initialization, with the concretized history, checking committed effects with an independent oracle. The verifier may be mocked only at this grade | `CONSUMER_MISMATCH` → UNKNOWN |
| F3 Real proof | A keccakZK UltraHonk proof accepted by the pinned generated verifier, then `mint` on the unchanged consumer. This is a **later, separately frozen gate** with equal method treatment; no budget is created here | Absent → grade remains concrete-model or consumer-state |

Rules:

- **Allowance template** (D1P-04 Section 1.3, to be restated in the WarpToad
  freeze): at most one candidate per AUTH, COVERAGE and NONVAC slot, per
  case/scope, per method. Each candidate gets one F1 and one F2 call of at
  most 600 seconds each.
- A collision-dependent candidate cannot pass M3 unless a real Poseidon
  collision is exhibited. That would be a cryptographic event outside scope,
  reported separately and never as a WarpToad violation. **M3 is the
  definitive collision filter; M2 is an early classifier.**
- `VIOLATION` requires M3, F1 and F2. Its evidence grade states whether F3
  exists. Under contract Section 8, the central motivating result needs F3.
- **Non-vacuity.** `NONVAC` (a successful `mint` with at least one protected
  effect) is solved under the **same** abstraction and `NC` set as the
  property queries, and passes M3, F1 and F2. The Lane A honest proof is an
  independent anchor but does not replace this. If `NONVAC ∧ NC(T)` is UNSAT,
  every property result in that scope is UNKNOWN (`VACUOUS_NC`).
- Reason codes, all UNKNOWN unless validated: `COLLISION_DEPENDENT`,
  `HASH_INCONSISTENT`, `ACIR_REJECTED`, `CONSUMER_MISMATCH`, `VACUOUS_NC`,
  `CR_ARGUMENT_OPEN`, `HASH_UNRETRIEVED`, `CANONICALITY_UNRESOLVED`,
  `ORIGIN_UNSUPPORTED`, `SPECIFICATION_UNRESOLVED`, `SPLIT_UNSUPPORTED`.

## 4. Fee-split policy draft

> **DRAFT — NOT APPROVED.** This section requires independent human review.
> Planner inputs are recorded in §4.5 as open positions, not approvals.
> Until the policy is approved **and** split controls exist, contract
> Section 5.5 applies: splitting is a permitted policy concept, not an
> implemented capability, and **every fee-split occurrence yields UNKNOWN
> (`SPLIT_UNSUPPORTED`)**.

### 4.1 Policy sources

Policy is derived from protocol documentation and from the contract's
protocol-independent matching rules. The consumer's behavior is not a source.
In particular, the arithmetic at `Core.sol:164-176`, the wildcard branch at
`:168-170` and the honest test's assertion at `test.ts:105-108` are **not**
used as policy.

| Source | What it states | Status |
| --- | --- | --- |
| Research contract §4.1–4.3 | Identity/asset/beneficiary/domain/quantity matching, multiplicity, splitting only through explicit transformations | Authoritative, generic |
| V2 §3 | Exact keys, injective `E → P` and `O → E`, `Counter` argument | Authoritative for the base matching. Its Payy immediate-settlement choice does **not** carry over to WarpToad |
| `main.nr:24-28` (developer comment) | The relayer is paid `fee_factor × (baseFee + priorityFee)` | Documentation comment; the only formula source (used only by the separate FEE-FORMULA property) |
| `main.nr:50` (comment) | `fee_factor = 0` means no relayer payment | Documentation comment |
| `main.nr:20-22` (comment) | `aztec_warptoad_address` exists so that only WarpToad commitments, not other Aztec contracts', are accepted | Documentation comment (domain intent) |
| `main.nr:33-34` | Addresses are Ethereum addresses left-padded with zeros | Documentation comment (encoding) |
| D1P-11 ledger `documented_intended_policy` | README describes burn-to-mint, root membership, nullifier single use, destination chain binding and relayer compensation bounded by `max_fee` | Second-hand. README UNRETRIEVED; the status there is "no frozen, human-reviewed policy" |

No retrieved document states a wildcard relayer, a cross-asset rule, or
whether a consumed nullifier obliges a full payout. These remain open
decisions (§4.5) and are not filled from code.

### 4.2 Records

Each field is graded **consumer-recorded** (written by a committed consumer
effect), **proof-enforced** (fixed by `R_v` for the group's own witness), or
**ghost** (admitted-history data about an honest depositor's private intent,
ASSUMED and never consumer-checked).

- **Source permission `p`** (in `P`): one per committed source **occurrence**.
  On EVM origin this is one committed `burn` (`Core.sol:92-104`) at LazyIMT
  leaf index `ℓ`.
  - Consumer-recorded: `instance`, `asset`, `ℓ`, leaf `c_ℓ =
    PoseidonT3(preCommitment, a)` and amount `a` (`:95-98`, event `:102`).
  - Ghost, honest depositors only: `(np₀, s₀, ch₀)` with `preCommitment =
    H_pre(np₀, s₀, ch₀)`. An adversarial depositor's burn has no ghost
    fields; it authorizes whatever its own preimage authorizes.
  - Aztec and external giga origins: `ORIGIN_UNSUPPORTED` in the first
    fragment.
- **Withdrawal statement `w`**: the accepted public vector of one successful
  `mint`, with fields `(n, chain, a, roots, r, ρ, ff, pf, mf)`, plus the
  group's own witness `(np, s, origin root, is_from_aztec, ℓ', π)`, which is
  symbolic in the joint model.
- **Effect group `g`** (in `E`): the committed effects of one successful
  `mint`. These are the protected write `nullifiers[n] := true`, then
  `mint(r', x_R)` and optionally `mint(ρ', x_F)`, with token `t`, instance
  and `block.chainid`. A zero-valued mint is still an occurrence, following
  V2.

### 4.3 Clauses (extension of V2 exact matching)

Properties AUTH and COVERAGE use F1–F2 and F4–F9. **F3 is a separate
property, FEE-FORMULA**, and is excluded from AUTH until independently
justified (planner position D2).

| Id | Clause | Source |
| --- | --- | --- |
| F1 Identity / single use | Each `g` has a derived source id (§4.4) and matches exactly the permission with that id. Each id is matched by at most one `g` across `Reach_L`. Single use is per source occurrence, not per `uint256` nullifier word. | Contract §4.1; D1P-11 summary |
| F2 Conservation | `x_R + x_F = a(p)`, with `x_F = 0` when there is no fee mint. Nothing else is minted by the call. | Contract §4.3 |
| F3 Fee formula *(separate FEE-FORMULA property)* | If `ff ≠ 0`: `x_F = ff · (basefee(g) + pf)`, with `basefee` an admitted environment value. If `ff = 0`: `x_F = 0`. | `main.nr:24-28`, `:50` (comments only) |
| F4 Fee cap | `0 ≤ x_F ≤ mf ≤ a(p)` | D1P-11 summary ("bounded by max_fee") |
| F5 Beneficiaries | `r' = low160(r)` exactly; `ρ' = low160(ρ)` exactly. `ρ = 1` gives `SPECIFICATION_UNRESOLVED` (D1) | Contract §4.1; `main.nr:33-34` |
| F6 Chain | For an honest-depositor permission, `block.chainid(g) = ch₀(p)` (ghost comparison; its security reading needs (b)) | D1P-11 summary ("destination chain binding") |
| F7 Domain / asset | `g`'s instance and token equal `p`'s. For Aztec origin, `p` must come from the configured WarpToad Aztec contract. | `main.nr:20-22`; contract §4.1 |
| F8 Statement linkage | `w`'s amount equals `a(p)`; `w`'s `(r, ρ, mf)` are the parameters checked in F4–F5 | Contract §4.1 |
| F9 Immediate payout *(proposed for WarpToad, D3)* | Each committed nullifier write creates one obligation `o ∈ O` (a separate list, not `O := P`), discharged only by the payout effects of the same transition satisfying F2, F4, F5 and F7 | Contract §4.2; proposed explicitly here, not inherited from Payy V2 |

### 4.4 Source-occurrence identity and matching

The source id of a group `g` is computed by a fixed derivation function
`id(g)` from authenticated facts. **It is never chosen by the matcher or the
solver to make matching succeed.** Failure to derive does not fall back to
any other permission.

| Step | Fact used | Grade |
| --- | --- | --- |
| D1 | The group's witness `(np, s, origin_root, is_from_aztec, ℓ', π)` | In the joint model: variables of `R_v` (proof-enforced relation). For a real proof: available only through extraction, B1 (ASSUMED, open) |
| D2 | Local branch iff `destination_local_root == origin_root` and `¬is_from_aztec` | Proof-enforced (`main.nr:56`, `:70`). Giga or Aztec branch → `id = UNKNOWN (ORIGIN_UNSUPPORTED)`. Mapping a giga leaf to an origin instance would need `GigaBridge` provider indices (UNRETRIEVED, ASSUMED) |
| D3 | `c = H_leaf(H_pre(np, s, chain_id), amount)` and `n = H_null(np)` | Proof-enforced (C7, C8). The composition is UNRETRIEVED; the shape is TS-ONLY |
| D4 | `c` opens at position `ℓ'` along path `π` to `origin_root` | Proof-enforced (C9, EVM branch). That `ℓ'` is range-constrained to the tree depth's bits is UNRETRIEVED |
| D5 | `destination_local_root ∈ localRootHistory` of this instance | Consumer-checked (K2, `Core.sol:156`) |
| D6 | The leaf sequence `(c_0, c_1, …)` of this instance | Consumer-recorded: each committed `burn` computes and inserts `c_j` at index `j` (`:97-98`, `:102-103`). In `Reach_L` mode it comes from the history's committed burns. In fixed-pre-state mode it is admitted-state data, ASSUMED until Lane A replays the burns (LANE-A). Equality of LazyIMT's internal leaf count with `lastLeafIndex`, and the absence of other insertion paths in the concrete subclass, are LANE-A |
| D7 | `id(g) := (instance, ℓ')` iff `ℓ' < |leaves|` and `c = c_{ℓ'}`; otherwise `id(g) := ⊥` | Analysis check over D3–D6 |
| D8 | Uniqueness: the root at `ℓ'` commits to exactly `c_{ℓ'}`, so no other leaf could open there | **ASSUMED**: Merkle positional binding = A-CR on the node hash + A-HC (same hash, depth and zero-leaf conventions) + D4's range constraint. This is part of open obligation (b) (B3/B4) |

Consequences:

- Under plain UF (guarantee (a)), D7 is evaluated inside the model, and D8
  is **not** assumed. A model with `c ≠ c_{ℓ'}` yields `⊥`. A `⊥` group
  matches no permission and is therefore an AUTH candidate, which then goes
  through M2/M3. If it depends on a collision, M3 rejects it. So the
  derivation fails closed.
- The nullifier is **not** part of the identity. C8 ties `n` to the group's
  own `np` (proof-enforced). K3 ensures per-word single use
  (consumer-checked). F1 single use is per id, so two groups that derive the
  same id with different nullifier words (through an `np` collision, or
  non-canonical words, B5) violate F1.
- **Duplicate commitments (D5).** Two burns with an equal leaf at `ℓ₁ ≠ ℓ₂`
  are two permissions with distinct ids; occurrence identity is preserved.
  The prover's choice of `ℓ'` selects one of them. That choice is
  proof-determined, not matcher-determined. Both share `n`, so at most one
  can be withdrawn (K3).

**Matching.** Compatibility key `k = (instance, asset, kind=WITHDRAW, id,
a)`, with exact equality; a `⊥` or UNKNOWN id never matches. F2 and F4–F8
are **per-group predicates** evaluated after the key match. Each key holds at
most one permission (`count_P(k) ≤ 1`), so injective `E → P` reduces to
`count_E(k) ≤ count_P(k)` plus a per-group predicate check. V2's counting
argument survives only because the arithmetic sits outside the key. Moving
arithmetic into compatibility requires re-review (V2 §3).

Other unsupported or unresolved cases, each UNKNOWN: `ρ = address(1)` (D1);
non-canonical words (LANE-A); an ERC-20 hook or override in the concrete
token (LANE-A).

### 4.5 Open decisions, with planner input (recorded, NOT approved)

| Id | Question | Planner position (open) | Effect on this draft |
| --- | --- | --- | --- |
| D1 | Is `ρ = 1` a protocol-authorized "any relayer" permission with beneficiary `msg.sender`? | Unresolved. The first fixture uses a named relayer | `ρ = 1` → `SPECIFICATION_UNRESOLVED`. The first fixture exercises only named relayers |
| D2 | Fee property strength | Propose cap + conservation (F2, F4) as the property. Keep exact-formula correctness separate until independently justified | AUTH uses F2/F4. F3 is the separate FEE-FORMULA property; a FEE-FORMULA result never changes an AUTH verdict |
| D3 | Does a consumed nullifier oblige full payout in the same transition? | Propose explicitly for WarpToad. Payy's V2 policy does not establish it | F9 proposed. COVERAGE is defined only through F9 and remains unapproved |
| D4 | Can several instances or assets share a giga tree? | Requires deployment/protocol evidence. A one-instance fixture cannot establish cross-instance binding | A one-instance result reports F7 as **not established** for cross-instance or cross-asset binding, never as verified |
| D5 | Duplicate commitments | Preserve occurrence identity | Implemented in §4.4. **Separately open:** do both deposits create payout obligations? If yes, a coverage notion triggered by deposits, which F9 is not, would be needed |

Before any use, approve the controls: honest `ff = 0` and `ff ≠ 0`
withdrawals with a named relayer as legitimate controls; synthetic
matcher-level regressions for each clause (fee above cap, sum not equal to
`a`, wrong beneficiary, reused id, `⊥` id, duplicate-leaf occurrences,
wildcard). Matcher regressions are component tests, never primary evidence.

## 5. Consumer-direction hypothesis

### 5.1 Hypothesis

> **H-CD.** For WarpToad AUTH, COVERAGE and NONVAC, compare the
> consumer-directed method (CD) with each comparator under identical
> semantics (the same `Φ[f]`, `α`, `NC` set, ground instances, policy
> version, admitted state and bounds), the same partition treatment, and
> equal budgets. CD uses consumer-fixed facts for exact-substitution
> propagation (D1P-09 rules) and to direct checked-summary refinement.
> The hypothesis is that CD obtains strictly more **validated** resolved
> obligations, or, on obligations that both arms resolve with the same
> validated outcome, lower charged analysis time, with no validated-outcome
> disagreement.

Consumer-fixed facts, from Section 1 and the admitted state:

- `chain_id := block.chainid`, a constant in a single-chain fixture (LANE-A
  value).
- `aztec_warptoad_address := stored configuration`, a constant.
- `giga_root ∈ gigaRootHistory` and `destination_local_root ∈
  localRootHistory`: finite sets in fixed-pre-state mode, with their ground
  tree instances.
- `nullifier ∉ nullifiers`, from stored state.
- Success-path predicates: the `ff = 0` / `ff ≠ 0` branch (`Core.sol:164`),
  the named-relayer path (`:168`, per D1), no overflow in `ff·(basefee+pf)`,
  no underflow in `amount − fee`, `fee ≤ max_fee`, and non-zero mint
  receivers (the OpenZeppelin `_mint` guard; LANE-A version).

Propagation fixes **only** consumer-determined words and branch facts. It
never fixes private witnesses, payload amounts, beneficiaries or roots
outside the admitted set. Every propagated equality is kept as an auditable
reconstruction (D1P-09).

**Partitioning is a shared factor, not part of CD** (D1P-04 Section 1.1).
Root-set or success-path case splits, which must be exhaustive and checked
like the 11 Payy shapes, are applied identically to every arm in a
partitioned block, or to none in an unsplit block. The two blocks are
reported separately.

### 5.2 How this differs from goal-cone slicing

| | Goal-cone slicing | Consumer direction |
| --- | --- | --- |
| Direction | Backward from goal variables over the producer dependency graph | Forward from consumer-determined words, state and guard predicates into the producer |
| Information available | The same conjoined formula, including consumer constraints | The same formula; the difference is how consumer facts are used, not what is available |
| Effect on the relation | Removes constraints outside the cone; never adds facts | Adds equality and case facts from consumer-determined words and guards, discharges constraints by exact substitution, and uses them to select checked summaries and refinements |
| WarpToad specifics | `amount` and `nullifier` feed C7 → C9 → C6, so the cone is anticipated to retain essentially the whole circuit (anticipated, not measured) | Constant `chain_id` and Aztec address enter hash arguments; admitted roots ground the Merkle folds; path predicates decide which fee constraints matter |

### 5.3 Prospective six-arm design

> **This design is prospective. It is not authorization to implement or run
> any arm.** Running requires the Lane A fixture, approved policy, and planner
> approval of a hash-complete freeze manifest.

Arms 1–5 are D1P-04's five equal-information methods; arm 6 is a WarpToad
component ablation.

1. **MONO:** full monolithic joint analysis.
2. **MODULAR:** equal-information modular analysis.
3. **GC:** ordinary goal-cone analysis, without consumer-directed ordering
   or refinement.
4. **CF-ABL:** consumer-facts ablation. It uses CD's machinery with
   consumer-derived selection facts withheld, keeping enough schema to state
   the property.
5. **CD:** consumer-directed propagation and checked-summary refinement.
6. **CD-NOPROP:** CD refinement with exact-substitution propagation
   disabled.

A guard-removal variant changes the property, so it is not an arm. If run
later, it is a separately reported semantic diagnostic whose false candidates
are explained, and it never enters the decision rule (roadmap, ablations).

**Resource rules** (current rules; the D1P-03 budgets and upfront freezing
of every query hash are superseded):

- **Memory.** The D1P-07 policy
  (`metadata/d1/d1p-07-resource-policy.json`): libproc recursive process-tree
  RSS sampled every 50 ms. The process group is terminated with bounded
  cleanup when an observed aggregate RSS exceeds 4,294,967,296 bytes. The
  cutoff is sampled: it can overshoot, can miss short-lived allocations, and
  is **not** a hard address-space cap. Missing observations are null, never
  zero. A monitor or cleanup failure is an infrastructure failure that stops
  the campaign. A timeout, RSS cutoff, solver UNKNOWN, process error,
  malformed output or budget exhaustion is unresolved.
- **Platform.** The D1P-07 policy is native-macOS-specific. D1P-04 required
  primary timed comparisons on one frozen Linux environment. Which platform
  is primary for WarpToad is a planner decision recorded in the freeze. A
  Linux run needs an equivalent, separately validated memory policy.
- **Analysis budget** (template from D1P-04 Section 1.2, restated in the
  freeze): 300 analysis seconds per property slot per method. Fixed methods
  use one call. Modular and refinement methods use at most five internal
  calls of at most 60 seconds within the 300 seconds. Partitioned blocks
  share the slot allowance across cells.
- **Charged to the method:** extraction, selection, propagation, summary
  proof, method-internal concretization (M1–M4), rejected-candidate
  checking, refinement, every internal solver call and failed setup.
- **Final validation:** F1/F2 under the equal per-method allowance (§3.6),
  reported separately as analysis time, validation time and their sum. Never
  pooled or transferred.
- **Freeze and adaptive queries.** Before the first primary call, freeze and
  hash the generators, extraction/selection/propagation rules, policy
  version, **initial** queries, solver binary and configuration, budgets,
  validation rules, sources and artifacts. Adaptive queries (refinements,
  summary checks) are hashed and logged **before their individual
  execution**. No arm receives a post-result rule or fact. Stop on a
  preservation conflict (D1P-04 Section 1.4).

### 5.4 Decision rule (DRAFT; fixed before any measurement)

1. **Outcome classes** per (arm, obligation): `VALIDATED_VIOLATION` (M3, F1
   and F2 pass); `RESOLVED_UNSAT` (UNSAT under guarantee (a), with validated
   NONVAC in that scope); `UNSAT_CR_OPEN` (UNSAT only with `NC`, reported
   UNKNOWN per §3.5 and tallied separately, never merged); `UNRESOLVED`
   (everything else, including unvalidated abstract SAT).
2. **Identical semantics.** Arms are compared only on obligations whose
   formula, policy version, admitted state, bounds and partition treatment
   are byte-identical across arms.
3. **Consistency.** A validated disagreement (`VALIDATED_VIOLATION` against
   `RESOLVED_UNSAT`) stops the comparison as a preservation conflict.
   Unresolved against resolved is not a contradiction.
4. **Coverage comparison.** For CD against each comparator X (arms 1–4 and
   6), report the 2×2 table: resolved by both, CD only, X only, neither. CD
   has a coverage advantage over X iff `|CD only| > |X only|`. The claim is
   made per comparator, with the full table.
5. **Runtime comparison.** Only on `B(CD, X)`, the obligations resolved by
   both with the same validated outcome. Obligations unresolved by either
   arm are **excluded** from any speedup figure and reported as counts. The
   metric is charged analysis time; final-validation time is reported
   separately and never enters the speedup.
6. **Repetition** (fixed before measurement): `R = 5` measurement
   replicates per (arm, obligation) on identical frozen inputs, run in a
   pre-recorded randomized interleaving. Replicates are measurements, not
   retries: none is re-run after a failure. Final validation applies to
   replicate 1's candidate only. An obligation is resolved for an arm only if
   every replicate returns the same result class and replicate 1 validates.
   Otherwise it is unresolved and reported as unstable.
7. **Aggregation** (fixed before measurement): per obligation, the median of
   the `R` charged analysis times. Per comparator, the per-obligation ratio
   `CD/X` over `B`, summarized by geometric mean with `|B|`, minimum and
   maximum. A runtime advantage over X is claimed only if `|B| ≥ 3`, the
   geometric-mean ratio is `≤ 0.5`, and the ratio is `< 1` on at least
   two-thirds of `B`. Peak sampled RSS (median, null-aware) is reported but
   not used for the claim.
8. Anything else, including ties, `|B| < 3`, or advantage over only some
   comparators, is reported as **no demonstrated advantage** against the
   comparators concerned. Unsplit and partitioned blocks, and
   `UNSAT_CR_OPEN` tallies, are reported separately. Changing `R`, the
   thresholds or the aggregation after any primary result invalidates the
   comparison.

The numbers in items 6–7 (`R = 5`, `0.5`, two-thirds, `|B| ≥ 3`) are DRAFT
values for planner approval. They must be fixed in the freeze manifest
before measurement.

Declared risks:

- Under `α`, the residual WarpToad relation (limb comparison, non-zero
  checks, muxes, and on the order of 80 UF applications across both
  membership branches for the tree depths in the commented test at
  `main.nr:95-107`, UNRETRIEVED as constants) may be easy for every arm. This
  ceiling effect would leave `B` without discriminating power.
- WarpToad is single-claim, not batched (D1P-11 scope note).
- D1P-09 found only 4–8 of 620 operations removable, and D1P-10 was null.

A null result is a valid outcome, not a reason to retune.

## 6. Lane A dependency register

Every item below is an assumption of this design until the Lane A fixture
exists and is hash-recorded.

| Id | Dependency | Used by |
| --- | --- | --- |
| LA-1 | Pinned compiler choice (README beta.19 vs `noir_js` 1.0.0-beta.22 / `aztec-nargo`), compiled withdraw ACIR/ABI, and the 11-word ABI order | §1.1, §2, §3.2 provenance, M4/F1 |
| LA-2 | Hashing and constants crates (hash composition, tree depths, zero leaves, Aztec siloing) | §2.1 C6/C7/C9, §3.1, §3.2 precondition 3 |
| LA-3 | VK and generated keccakZK verifier: word canonicality (reject vs reduce) and expected public-input length | §1.2, §2.2 nullifier, §4.4 |
| LA-4 | Equality of Solidity `PoseidonT3`/LazyIMT with the circuit hash/tree (A-HC) via test vectors, labeled ASSUMED unless proved | §3.2, §3.5 (B4), §4.4 D8, M3 |
| LA-5 | Reference hash implementations for M3 concretization and ground tree instances | §3.3 refinement and (a′), M3 |
| LA-6 | Concrete `L1WarpToad` and token (resolved OpenZeppelin version, no `_update` override), `GigaBridge`/provider initialization, fork-free owned deployment, chain ID and base-fee model; LazyIMT leaf storage, its leaf count equal to `lastLeafIndex`, and no other insertion path | §2.1 K1/K6, §4.2, §4.4 D6, §5.1 |
| LA-7 | One accepted honest proof and vector, and one honest `mint` replay with a named relayer (`ff = 0` and `ff ≠ 0` if feasible) | §3.6 non-vacuity, §4.5 controls, F3 |
| LA-8 | A separately frozen, planner-approved real-proof gate (F3) with equal method treatment | §3.6 |

## 7. Assumptions, limitations and exposure

- **Scope.** All facts are source-level at one pinned revision. Nothing is
  established about deployment correspondence. Fixed-pre-state analysis is a
  narrower mode than `Reach_L` and must be labeled as such.
- **Trust assumptions.** ASSUMED: A-PS, A-HC, the giga-root provider role,
  standard atomic ERC-20 mint semantics, and the honest-depositor ghost data
  of §4.2. Knowledge soundness and A-CR enter only through guarantee (b),
  whose obligations B1–B6 are **open** (§3.5). No result in this design
  treats (b) as discharged.
- **Exposure.** The source warning at `main.nr:11-12` was read again. It is
  exposure, already recorded by D1-02/D1P-11, not investigated here. At this
  revision `aztec_warptoad_address` is a public input, but whether
  `aztec_merkle_verify` uses it is UNRETRIEVED.
- **Modeling obligations, not findings.** The canonicality class (§1.2) and
  the shared-giga-tree domain question (§2.2, D4) are obligations the model
  must be able to express. Neither is claimed reachable. Any later confirmed
  issue requires responsible disclosure before it supports a claim (contract
  §9).
- **Annotations.** These are AI-assisted design notes. Authors must inspect
  every line citation and policy clause. They are not independent
  annotations.

## 8. Handoff

- **Objective/status.** WarpToad joint-model design, revision 1, delivered
  for review. Policy DRAFT, not approved; planner positions D1–D5 are recorded
  as open. Guarantee (b) is open. The six-arm design is prospective and not
  authorization to run. Verdict UNKNOWN.
- **Files changed.** This document only. Ignored evidence from the original
  task: `results/raw/D1P-B01/source/**` (five verified files) and
  `results/raw/D1P-B01/retrieval.json`; the revision added no evidence.
  Not changed: `README.md`, `docs/project-status.md` (the integrator updates
  them, per the task instruction), any other worktree, and the D1P-11 record.
- **Commands.** Original task: five `curl -fsSL` fetches (exit 0) and one
  inline Python SHA-256 comparison, all five equal. Revision: reads of the
  D1P-04 and D1P-07 protocols and the D1P-07 resource policy, plus text
  edits. No build, solver, proof or test run in either.
- **Failed approaches / unexpected observations.** None failed. The hashing
  crate was never fetched by D1-02 or D1P-11, so B3 term coverage cannot be
  enumerated yet. D1P-04 requires Linux for primary timing, while D1P-07's
  memory policy is macOS-specific; this is recorded as a planner decision
  (§5.3).
- **Recommended next task.** Run the Lane A correspondence gate (D1P-11
  handoff), extended with a hash-recorded fetch of the hashing/constants
  crates. Completion criterion: (a) a pinned ACIR/ABI, VK and generated
  verifier linked to `main.nr` `ce4bf56b…`, with the verifier's canonicality
  behavior recorded, one accepted honest proof and vector with a named
  relayer, A-HC test vectors, and a confirmed LazyIMT leaf-index layout
  (D6); or (b) one reproducible blocker. Policy D1–D5 and the §5.4 draft
  numbers should be decided by human review before any query is frozen.

## 9. Change log

| Date | Revision | Changes |
| --- | --- | --- |
| 2026-10-26 | 0 | Initial design. |
| 2026-10-26 | 1 | (1) §4.4: source-occurrence identity is now derived by a fixed function `id(g)` from proof-enforced (C7–C9), consumer-checked (K2) and consumer-recorded (burn leaves) facts. Uniqueness (D8) is ASSUMED; a failed derivation fails closed as `⊥`. The nullifier was removed from the key, and depositor chain/nullifier intent became ASSUMED ghost data (§4.2). (2) §3.3–3.5: plain-UF preservation (a) and its logical corollary (a′) are separated from the computational argument (b), whose obligations B1–B6 (extraction, multi-proof extraction, term coverage, instance identity, CR domain, accounting) are listed as open; results relying on `NC` are UNKNOWN (`CR_ARGUMENT_OPEN`). (3) §3.6/§5.3: D1P-03 budgets and upfront hashing of every query were replaced with D1P-04 §1 rules and the D1P-07 sampled-RSS policy. Method-internal concretization (M1–M4) is charged to the method; final validation (F1–F2) has a separate, equal per-method allowance; adaptive queries are hashed before execution. Partitioning is a shared factor, and the arms were aligned with D1P-04's five methods plus CD-NOPROP. The guard-removal variant was moved out of the arms. (4) §5.4: a new decision rule over validated outcomes under identical semantics. Runtime is compared only on obligations both arms resolve, with unresolved obligations excluded, and repetition and aggregation are fixed before measurement. The design is stated as prospective. (5) §4.3/§4.5: planner inputs D1–D5 are recorded as open. F3 became the separate FEE-FORMULA property; F9 is proposed explicitly for WarpToad; the one-instance limit on F7 and the D5 occurrence rule are stated. |
