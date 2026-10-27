# D1P-B02 — WarpToad discriminating obligations

Date: **27 October 2026** (revision 2; change log in §7)<br>
Worktree: `/Users/imranpollob/Coding/bc/bindcheck-lane-b`, branch
`lane-b-design` (no commit, push or merge)<br>
Status: **CONDITIONAL ARGUMENT AND IMPLEMENTATION PLAN, with planner
decisions applied. Not authorization to build, mutate or run.**<br>
Research verdict: **UNKNOWN**

This document proposes two WarpToad obligations that could test the
consumer-direction hypothesis H-CD
([D1P-B01 §5](d1p-b01-design.md)). Every name used here (`Ω`, `R̂_v`,
`D_v`, `T_mint`, guarantees (a)/(a′)/(b), `NC`, route V-EXEC, arms, decision
rule) is defined in D1P-B01 revision 3. Facts come from the hash-verified
D1P-11 sources, D1P-12R and D1P-13 (read-only), and B01-RO reads recorded in
the ignored `results/raw/D1P-B01/rev{2,3}-readonly-reads.json`. Nothing was
built, compiled, mutated, solved or executed for this proposal.

**Nature of this document.** This is a **conditional argument and an
implementation plan**, not a result.
- The mechanical prerequisites **P1–P6 (§4) are all pending**: none is
  implemented, run or audited.
- The planner-approved cryptographic assumptions (§3) are premises of the
  argument. Approving them **does not make any mechanical check pass**, and
  does not substitute for one.
- Until every check a given claim depends on has passed and is recorded,
  no conditional `VERIFIED_WITHIN_SCOPE` or other result can be drawn from
  O1 or O2.

**Provenance.** O1 and O2 are **planner-written** (AI-assisted, with planner
decisions applied). They are **not automatically derived** by BindCheck. §6
records which parts come from reusable extraction, protocol policy, manual
implementation summaries, and defect-specific planner input.

## 0. Selection rules

An obligation qualifies only if all three conditions hold:

1. Its answer depends **non-trivially on producer constraints**. A
   consumer-only UNSAT does not qualify: AUTH-1's consumer-determined UNSAT
   is pipeline correctness, not a method advantage (B01 §6.2.2).
2. A consumer-derived fact (consumer-supplied `chain_id` or address, root or
   nullifier guard, fee branch) could plausibly simplify **producer**
   reasoning beyond goal-cone slicing, through a stated mechanism.
3. A **justified** faulty/repaired pair exists, with a stated justification
   class (§1.2, §2.2).

**Ablation rule.** Every ablation arm (CF-ABL, CD-NOPROP) keeps the **same
security property and the same admissible executions**: the same `Ω`,
including every consumer guard as a constraint. It withholds consumer
information **only from the selection strategy**. Semantic guards are never
deleted to compare a different problem. A faulty variant is a separate
system under test, not an ablation, and every arm analyzes it.

The nullifier guard and fee branch are not the lever in either proposal:
- Single use is consumer-checked per word (K3), and canonicality is resolved
  (D1P-12R §7). The remaining question is CR-only and has no justified
  faulty variant.
- The fee split is consumer-determined (AUTH-1).

Both remain constraints in every `Ω`.

## 1. O1 — DOM-AZ: Aztec-origin silo-address binding

### 1.1 Property and policy source

Every successful `mint` whose source is an Aztec note (`is_from_aztec`) must
be backed by an admitted note **siloed under the configured WarpToad Aztec
contract**. The policy source is documentation of intent, not implementation:
`main.nr:20-22` states that `aztec_warptoad_address` exists to stop
commitments from other Aztec contracts, which share the global note-hash
tree, from being accepted. This is DRAFT clause F7 (Aztec part) of B01 §4.3.

### 1.2 Faulty/repaired pair: a mechanism-derived mutation

| Variant | Mechanism | Evidence |
| --- | --- | --- |
| **Repaired** (pinned) | The silo address is the **public** word 5, which the consumer fixes to stored configuration | `main.nr:20`, `:71`; `nargo_hashing/src/lib.nr:56-62`, `:64-73`; `Core.sol:49`, `:67-73`, `:160`; D1P-13 MATCH artifact |
| **Faulty** (M-DOM, a **mechanism-derived mutation**) | The silo address is a **private**, prover-chosen field `aztec_merkle_data.contract_address`. Word 5 stays declared (11-word ABI and consumer unchanged) but feeds no constraint. All other bytes are pinned, including the current domain separators | The mechanism is supported by the unused in-tree `hashing` package (`hashing/src/lib.nr:7-12`, `:60-66`; SHA-256 `f3d0fc75…`) and the developer warning `main.nr:11-12` |

**Justification class: mechanism-derived mutation.** The unused package and
the warning show that the mechanism existed in the source tree and was
recognized by the developers. They do **not** show that a circuit using it
was ever built into a released artifact, deployed, or exploited, and no
such claim is made.

**Gates before any use**, each recorded with hashes. A failed or missing
gate removes O1 from the comparison; it is never treated as safe.

1. **Build gate.** M-DOM compiles with the pinned beta.22 `nargo` (D1P-13
   binary `37f7d55d…`). Its program, ABI and diff against the pinned source
   are hash-recorded. M-DOM then receives **its own** verification key and
   generated Solidity verifier, produced by the locked `@aztec/bb.js 5.0.0`
   `keccakZK` route, each hash-recorded. M-DOM never inherits the pinned VK
   `563a018c…` or verifier `d9a822a5…`; a changed relation needs a new key.
2. **Honest-control gate.** On M-DOM, an honest withdrawal of an admitted
   **WarpToad** note executes (`nargo execute`) and mints through the
   unchanged consumer (V-EXEC). For any real-proof run, the consumer is
   deployed with `withdrawVerifier` set to M-DOM's verifier, and the
   verifier's runtime-bytecode hash at that address is recorded. This shows the mutation does not break
   legitimate behavior.
3. **Attack-validation gate.** On M-DOM, a withdrawal of a note siloed under
   `A_X ≠ A_WT` passes V-EXEC (concrete-model grade), and the same input
   fails on the repaired build. This shows the mutation changes the target
   property.

### 1.3 Canonical obligation `Ω_DOM`

| Component | Definition |
| --- | --- |
| `R̂_v^var` | The full decoded ACIR of the variant. Repaired: the D1P-13 program `934c21fe…`. Faulty: the gated M-DOM build. Hash layer per §1.4 |
| `D_v`, `T_mint`, `Env` | As in B01 §6.2 (canonical words, unchanged consumer, chain 31337, symbolic base fee, named relayer) |
| Scope predicate | `is_from_aztec = true`. This is part of the obligation, identical for all arms, and not a witness fix |
| Admitted state `S_DOM` | **Synthetic, fixed pre-state** (§1.5) |
| Policy `Policy_DOM` (DRAFT) | Permissions are the admitted notes in `N_WT`. The source is derived (B01 §4.4 style) from the witness leaf index, nonce and admitted tree |
| Goal | A successful call whose derived source is `⊥` or not in `N_WT` |

### 1.4 Hash layer and guarantee requirements

- **Poseidon2.** The 86 unconditional permutation opcodes are modeled as one
  4→4 uninterpreted function, with ground instances from `S_DOM`. No-collision
  conditions apply only to applications that a mechanical check identifies
  as an instance of the actual three-input sponge construction (§3.4). Raw
  permutation outputs carry no no-collision condition.
  - Bijectivity of the full 4→4 permutation is a true functional fact, so it
    may be added under guarantee (a).
  - It implies nothing about collisions of the sponge output lane, and it
    is not used for binding.
- **BN254 Poseidon** (commitment, 5-level giga fold) needs a checked region
  extraction (locality and functionality, B01 §3.2; P1). Otherwise it is
  retained exactly, and the repaired query is expected to be unresolved.
- **Faulty variant.** The attack uses real hashes and needs **no
  collision**. It is resolvable under guarantee (a) plus V-EXEC.
- **Repaired variant.** Under plain uninterpreted functions it is SAT only
  through collision-dependent models. A resolved answer needs the §3.4
  construction-level conditions, which yield the logical class
  `A_PRIME_UNSAT`. It becomes a **conditional security result only when
  every §3 check passes**. Until then `A_PRIME_UNSAT` stays separate from
  any security verdict.

### 1.5 Synthetic Aztec admitted state

`S_DOM` is fixed-pre-state, synthetic, owned-local data:

- one L1 instance with `aztecWarptoadAddress = A_WT ≠ 0`;
- `gigaRootHistory ∋ g`, a 5-level BN254-Poseidon giga tree with leaf
  `ρ_Az`;
- `ρ_Az`, a 42-level Poseidon2 note tree (separator `2982624097`) over the
  unique note hashes of admitted notes `N_WT` (≥ 1, siloed under `A_WT`)
  and `N_X` (≥ 1, siloed under some `A_X ≠ A_WT`);
- L1 `localRootHistory` admitted and disjoint from `{ρ_Az}`; and
- empty nullifiers.

Ground values are computed with pinned reference hashes (LA-5).

This is **synthetic admitted-tree evidence only**. It assumes that the
giga-root provider delivered `g` and that `ρ_Az` is a valid note-tree root.
It does **not** show reachability through the real Aztec protocol: note
insertion by Aztec contracts, sequencing, the L2→L1 root bridge, adapter
behavior and `GigaBridge` aggregation are not executed or modeled. Any O1
result is scoped to "if such a pre-state is admitted".

### 1.6 Consumer-direction mechanism

1. **Address constant.** Word 5 is consumer configuration
   (`Core.sol:49`, `:160`). In the repaired circuit it is the silo
   sponge's second input (`lib.nr:56-62`, `:70`; `main.nr:71`).
   - Exact substitution makes the silo application
     `H^{P2}_3(3361878420, A_WT, c)`, symbolic **only** in `c`.
   - With ground instances and the §3.4 conditions, its output can equal an
     admitted silo value only if `c ∈ {c_k : k ∈ N_WT}`, a finite case split
     replacing a symbolic search.
   - In M-DOM, word 5 reaches no constraint, so the substitution has no
     lever. That is a built-in control.
2. **Root guards.** K1 makes `giga_root` range over a finite admitted set,
   and K2 does the same for `destination_local_root`, giving a per-root case
   split.
   - Because no admitted L1 local root equals `ρ_Az`, the same-root test
     (`main.nr:56`) is decided false per case.
   - The giga branch is therefore forced, and the giga fold and the 42-level
     Aztec fold are grounded from constant roots.

**Beyond goal-cone slicing.** GC's backward cone from the goal variables
already contains almost the whole circuit (both membership branches, both
arms per level, the silo, unique and commitment hashes). GC neither
substitutes word 5 nor splits on admitted roots. MONO has the same
equalities in `Ω` but no selection strategy. CF-ABL runs the CD machinery
on the same `Ω` without these consumer-derived selection facts.

### 1.7 Anticipated outcomes and falsification

Anticipated, not observed:
- M-DOM: `VALIDATED_VIOLATION` (concrete-model grade).
- Repaired: `A_PRIME_UNSAT`.

All comparisons follow B01 §5.4: same `Ω`, checked transformations, equal
budget, the repetition rule and validated outcomes.

**H-CD is falsified on O1** if any of the following holds:

- **F-1.** CD resolves no more variants than **CF-ABL**. On variants both
  resolve, the CD/CF-ABL charged-time ratio is `> 0.5`, or the ratio is
  `< 1` on fewer than two-thirds of them. The consumer facts then confer no
  advantage over identical machinery without them.
- **F-2.** The same holds against GC or MONO.
- **F-3 (soundness).** CD reports UNSAT or `A_PRIME_UNSAT` on M-DOM while
  M-DOM's attack validates. That is a preservation conflict: stop.

**Uninformative, declared in advance:**
- MONO resolves both variants within 10% of the slot budget (ceiling).
- No arm resolves either variant (floor).
- A §1.2 gate fails.

The runtime part of F-1/F-2 is evaluated **per obligation, descriptively**
(§4). It is not a pooled runtime claim.

## 2. O2 — SRC-EVM: same-root source authorization (no unbacked mint)

### 2.1 Property and policy source

Every successful EVM-origin, same-root mint (`¬is_from_aztec`,
`destination_local_root = origin_local_root`) must be backed by an admitted
burn leaf of **this** instance whose amount equals `w2`. This is DRAFT
clauses F1 and F2b with the B01 §4.4 derivation. Policy source: the
documented burn-to-mint intent, and "roots bind the source commitment"
(D1P-11 ledger; D1P-12R §8.1).

### 2.2 Faulty/repaired pair: an injected consumer mutation

| Variant | Mechanism | Evidence |
| --- | --- | --- |
| **Repaired** (pinned) | The consumer checks `require(isValidLocalRoot(_localRoot))` (K2) | `Core.sol:156`, `:183-185` |
| **Faulty** (M-SRC, an **injected consumer mutation**) | K2 is removed; the producer is unchanged | Based on **documented reliance**: on the same-root branch the producer performs no root membership and comments "destination_local_root is a public input so its safe" (`main.nr:56-58`) |

**Justification class: injected mutation based on documented reliance.**
There is no evidence that any WarpToad version lacked K2. A result on O2
shows whether a method **detects this injected mutation**. It does **not**
indicate a defect in pinned WarpToad.

Gates, all required before use:
- **Build:** solc 0.8.29; M-SRC runtime bytecode hash-recorded.
- **Verifier pairing:** the producer is unchanged, so M-SRC is deployed with
  the **pinned** verifier (`d9a822a5…`, from VK `563a018c…`). The deployed
  `withdrawVerifier` address and its runtime-bytecode hash are recorded and
  checked against that identity. Any other pairing makes the variant
  undefined.
- **Honest control:** the D1P-12R-style honest mint succeeds on M-SRC.
- **Attack validation:** V-EXEC on M-SRC succeeds with an attacker-built
  tree, and the same input reverts at K2 on the pinned consumer.

M-SRC is a separate system under test. In the repaired variant every
ablation keeps K2.

### 2.3 Canonical obligation `Ω_SRC`

| Component | Definition |
| --- | --- |
| `R̂_v` | Pinned D1P-13 program (unchanged for both variants), hash layer per §2.4 |
| `T_mint^var` | Repaired: pinned consumer. Faulty: M-SRC |
| `D_v`, `Env` | As in B01 §6.2 |
| Scope predicate | `¬is_from_aztec ∧ destination_local_root = origin_local_root`, identical for all arms |
| Admitted state `S_SRC` | `S₀` (B01 §6.1) plus at least 2 admitted burns with distinct amounts and **canonical** `preCommitment`/`amount` inputs (synthetic, owned-local, fixed pre-state). Leaves and the LazyIMT root history are hash-recorded from execution |
| Policy (DRAFT) | Permissions are the admitted burn occurrences `(instance, ℓ)` with amount `a_ℓ`. The source id is derived by B01 §4.4 steps D1–D7 |
| Goal | A successful call with `id(g) = ⊥`, or `a(id(g)) ≠ w2` |

### 2.4 Hash layer and guarantee requirements

- **BN254 Poseidon** (C7 `hash_3`/`hash_2`; 32-level EVM fold with both arms
  per level) needs the checked region extraction (P1). Ground instances come
  from the admitted LazyIMT tree.
- Linking the circuit's `hash_2` to the consumer's `PoseidonT3` requires the
  §3.2 function-identity and domain checks. Until they pass, A-HC stays
  ASSUMED; D1P-12R observed one agreement point.
- **Poseidon2.** The 86 permutations are havoc'd (L0). The Aztec assertion
  is inactive in scope.
- **Faulty variant.** The attacker builds a private 32-level tree containing
  a commitment with an arbitrary amount, using **real hashes and no
  collision**. It is resolvable under guarantee (a) plus V-EXEC.
- **Repaired variant.** A resolved answer needs the §3.4 construction-level
  conditions, which yield `A_PRIME_UNSAT`. It is a conditional security
  result only when every §3 check passes.

### 2.5 Consumer-direction mechanism

1. **Root guard (K2).** `destination_local_root` ranges over the finite
   admitted history. With the scope equality, `origin_local_root` becomes an
   admitted constant **per case**. The EVM fold is grounded from a constant
   root, and under the §3.4 conditions the opened leaf at `ℓ'` must equal
   `c_{ℓ'}`, which through C7 fixes the amount.
   - In M-SRC this fact does not exist, so CD and CF-ABL have the same
     consumer information. That is a built-in control.
2. **Chain constant.** `chain_id := block.chainid`.
   - If BN254 Poseidon is retained exactly, the constant lane of
     `hash_3(np, s, chain)` allows exact substitution and discharge of
     first-round constraints (D1P-09 rules).
   - Under the uninterpreted-function layer it only yields a
     partially-ground term, which matches admitted pre-commitments only
     through ASSUMED ghost data.

**Beyond goal-cone slicing.** GC's cone from `w2` and the source derivation
includes C7, both arms of the fold, the C6 branch test and the giga fold.
It performs no root case split and no constant substitution.

### 2.6 Anticipated outcomes and falsification

Anticipated:
- M-SRC: `VALIDATED_VIOLATION` (detection of the injected mutation;
  concrete-model grade).
- Repaired: `A_PRIME_UNSAT`.

F-1 to F-3 and the uninformative conditions are as in §1.7, applied to O2.
An additional falsifier is **F-4**: on the repaired variant, CD-NOPROP
matches CD under the §5.4 rule. Root grounding, not propagation, would then
carry any effect.

## 3. Conditional cryptographic argument (explicitly stated assumptions)

The planners have approved collision resistance and single-proof
extraction as **explicitly stated assumptions** (contract §5.2). They are
not established facts, and their approval does **not** discharge any
mechanical check. P1–P6 remain pending. A repaired-variant `A_PRIME_UNSAT` becomes a
**conditional** `VERIFIED_WITHIN_SCOPE` only when every check in §3.2 and
§3.4 passes and the assumptions of §3.1 are listed in the result. Otherwise
it stays separate from any security verdict (UNKNOWN, `CR_ARGUMENT_OPEN`).

### 3.1 Single-proof extraction assumption (A-KS1)

> **Per variant `V`.** Let `R_v^V` be the relation of `V`'s **own** compiled
> artifact, with real Poseidon2 semantics and all of its constrained
> opcodes. Let `VK_V` be the verification key and `Ver_V` the generated
> verifier derived from that artifact under UltraHonk `keccakZK`. Then there
> exists an efficient extractor `E_V`. Given any efficient adversary that
> outputs, with probability `ε`, one proof `π` and eleven canonical words
> `p` such that `Ver_V` accepts `(π, p)`, `E_V` outputs, with probability at
> least `ε' = poly(ε) − negl`, a full witness assignment `w` with
> `R_v^V(p, w)`. This is stated in the backend's model: Fiat–Shamir over
> Keccak in the random-oracle model, plus its commitment-scheme
> assumptions. These are taken from the backend and not independently
> verified.

A-KS1 is instantiated separately for each variant and **never transfers**
between keys:

| Variant | Circuit artifact (program) | VK | Verifier | Consumer pairing |
| --- | --- | --- | --- | --- |
| O1 repaired | D1P-13 program `934c21fe…` (25,073 constrained opcodes; honest witness size 25,384) | `563a018c…` | `d9a822a5…` | Pinned consumer with that verifier |
| O1 faulty (M-DOM) | M-DOM's own build. **Identity pending** the §1.2 build gate | M-DOM's own VK, **pending** | M-DOM's own verifier, **pending** | Pinned consumer with M-DOM's verifier; deployed pairing recorded |
| O2 repaired | D1P-13 program `934c21fe…` | `563a018c…` | `d9a822a5…` | Pinned consumer with that verifier |
| O2 faulty (M-SRC) | D1P-13 program `934c21fe…` (producer unchanged) | `563a018c…` | `d9a822a5…` | **M-SRC** consumer with the pinned verifier; deployed pairing **pending** the §2.2 gate |

Until a pending identity is recorded, A-KS1 for that variant has no
instance, and §3.3 cannot be applied to it. V-EXEC's stub verifier
(concrete-model grade) does not use A-KS1; real-proof grade and the §3.3
argument do.

**Multi-proof extraction (B2) is inapplicable to O1/O2 as scoped**, and only
because the scope excludes it:

- each obligation concerns **one** `mint` call from a fixed pre-state;
- that pre-state contains **no** previously accepted proof (nullifiers
  empty; ground trees, burns and the giga root are admitted data, not proof
  outputs); and
- the adversary receives **no** honest proofs (no mempool or front-running
  oracle).

Any scope that adds a prior accepted proof, a second mint (`Reach_L ≥ 2`),
or adversarial observation of honest proofs makes B2 applicable again. B2
would then need simulation-extractability or multi-instance extraction.

### 3.2 Mechanical checks, all required

1. **Term coverage.** An independent auditor recomputes `T` from the decoded
   program (all 86 Poseidon2 opcode ids and all extracted BN254 regions, by
   opcode or region id) and from the admitted-state record (every ground
   instance). For O2, `T` also includes the consumer-side burn leaf hashes
   and the LazyIMT nodes of every admitted root. The query's `T` must equal
   this set exactly. Any omitted application must be mechanically shown
   outside the dependency cone of the goal; it is never assumed irrelevant.
2. **Function identity.** Each uninterpreted symbol must correspond to
   exactly one concrete construction, and each application must instantiate
   that construction exactly. Identity is established by comparing what the
   construction is made of: permutation width, round counts, round constants,
   MDS matrix, S-box exponent, state initialization, absorption positions
   and output lane. The comparison runs across the decoded program
   (opcode/region structure), the reference implementation used for ground
   instances, and, for O2, Solidity `PoseidonT3` sources. Test vectors are
   supporting evidence, not identity. A symbol shared by two implementations
   without a passing identity check is not allowed: the symbols are split,
   and the obligation is expected to be unresolved.
3. **Canonical input domains.**
   - Every hash input in `T` must be a canonical field element `< P`.
   - Circuit-side inputs are field elements by construction. Public words
     are canonical by `D_v` (D1P-12R §7).
   - Ground-instance inputs are canonical by builder check.
   - For Solidity `PoseidonT3` (O2), the library's treatment of `uint256`
     inputs `≥ P` must be mechanically determined. If it reduces, then
     `x` and `x+P` are a **non-cryptographic** equality outside CR. The
     admitted state must contain only canonical inputs, and any modeled
     burn must restrict or reduce its inputs explicitly.

### 3.3 Conditional argument: violation to extractable collision

Suppose all of the following hold:
- the §3.2 checks pass;
- `Φ[f] ∧ NC_constr(T)` is UNSAT, with `NC_constr` from §3.4; and
- an efficient adversary `A`, given `S`, produces with probability `ε` an
  accepted call whose committed effects meet the goal.

Then:

1. By **A-KS1** for the variant `V` under analysis (its own `VK_V` and `Ver_V`), `E_V` yields `w` with `R_v^V(p, w)`.
2. The tuple `(w, S, call)` is then a concrete execution of `Φ[H]`. It uses
   real hashes on canonical inputs, under the checked identity and domains.
3. By Claim (a), that execution satisfies `Φ[f]` with `f := H`.
4. Because `Φ[f] ∧ NC_constr(T)` is UNSAT, the execution violates
   `NC_constr(T)`. So there are two applications in `T` of the **same
   construction** `K`, with distinct admissible inputs and equal outputs.
5. All inputs of applications in `T` are read from `w` (circuit-side) or
   from `S` (ground instances). Scanning the at most `|T|²` pairs is
   therefore polynomial, and outputs a `K`-collision with probability at
   least `ε' − negl`.

Under **CR(K)** for each construction `K` used, `ε'`, and hence `ε`, is
negligible.

This argument introduces no new theorem. It composes Claim (a), A-KS1 and
CR(K), with a loss of extraction loss plus a polynomial scan. The concrete
security level of each `K` is taken from its specification, not
re-derived.

### 3.4 No-collision conditions on the actual constructions

`NC_constr(T) := ⋀_K ⋀_{u ≠ u' admissible, K(u), K(u') ∈ T} K(u) ≠ K(u')`.
The conjunction ranges over each **construction** `K` below, and `u`, `u'`
range over that construction's admissible input domain. There is no
condition across constructions, and none on raw permutation outputs.

| Construction `K` | Exact definition (source) | Admissible inputs | Uses |
| --- | --- | --- | --- |
| `H^{P2}_3(x0, x1, x2)` | Poseidon2 sponge of width 4, rate 3. State initialized to `(0, 0, 0, IV)` with `IV = 3·2⁶⁴` (length tag); absorb `x0..x2` into lanes 0–2; one permutation; output lane 0. There is no final permutation, since `in_len % 3 = 0` (poseidon v0.3.0 `poseidon2.nr:14-17`, `:58-115`) | `(x0, x1, x2) ∈ F_P³` | Silo `x0 = 3361878420`; unique `x0 = 226850429`; node `x0 = 2982624097` (`nargo_hashing/src/lib.nr:16-22`, `:49-62`). Domain separation is the fixed `x0`, so silo, unique and node applications are distinct inputs of one construction |
| `H^{BN}_1(x)` | Poseidon `x5_2`: state `(0, x)`, permutation, output lane 0 (`bn254.nr:14-23`, `:27-30`; Circom-compatible) | `x ∈ F_P` | Nullifier |
| `H^{BN}_2(x, y)` | Poseidon `x5_3`: state `(0, x, y)`, permutation, output lane 0 (`bn254.nr:32-35`) | `F_P²` | Commitment `(pre, amount)`; EVM and giga nodes `(l, r)`; for O2, Solidity `PoseidonT3` only if §3.2 identity holds |
| `H^{BN}_3(x, y, z)` | Poseidon `x5_4`: state `(0, x, y, z)`, permutation, output lane 0 (`bn254.nr:37-40`) | `F_P³` | Pre-commitment `(np, s, chain)` |

Mechanical applicability check: a Poseidon2 opcode application gets an
`NC_constr` term **only if** its decoded input vector is
`(x0, x1, x2, 3·2⁶⁴)` with lanes 0–2 absorbed from zero state and only
output lane 0 consumed. A BN254 region qualifies only if region extraction
shows the zero capacity lane, input lanes `1..n` and output lane 0. Any
application that does not match, including any permutation used outside
these constructions, gets **no** no-collision condition.

Collision resistance of the sponge construction does **not** justify
injectivity of an arbitrary truncated permutation output, for example one
with a non-standard capacity value. Both arms of each Merkle level are real
applications of the same construction on admissible inputs, so their
inclusion in `T` is legitimate.

## 4. Shared conditions, runtime reporting and prerequisites

- **Experimental rules.** B01 §5.3 and §5.4 apply: the reference Mac; the
  D1P-07 sampled-RSS policy; D1P-04 analysis budgets with method-internal
  concretization charged; V-EXEC final validation with an equal per-method
  allowance; the repetition rule; identical `T`, ground instances and
  `NC_constr` inside `Ω`; adaptive queries hashed before execution.
- **Runtime reporting.**
  - Each of the four variant-obligations (O1 and O2, each faulty and
    repaired) is reported **individually**, with its own outcome classes
    and descriptive timing.
  - A pooled summary may be shown **only descriptively and always alongside
    the individual results**.
  - The four variant-obligations belong to **one application family**
    (WarpToad), so pooling does **not** count toward B01 §5.4's
    three-obligation threshold.
  - **B02 alone cannot support a runtime-advantage claim.** It can support
    per-obligation coverage comparisons and descriptive timing.
- **`A_PRIME_UNSAT`** comparisons are comparisons of query outcomes. They
  become conditional security results only under §3.
- **Blocking prerequisites:**
  - **P1.** Checked BN254 Poseidon region extraction (debug-symbol
    provenance; B01 §3.2 locality and functionality).
  - **P2.** Reference hash implementations and a ground-tree builder (LA-5).
  - **P3.** M-DOM and M-SRC builds plus their gates (§1.2, §2.2).
  - **P4.** Hash-recorded synthetic admitted states `S_DOM`/`S_SRC`.
  - **P5.** Per-opcode provenance for the 86 Poseidon2 permutations.
  - **P6.** The §3.2 term-coverage, function-identity and domain checks,
    implemented and independently audited.

## 5. Exposure and claim limits

- **Exposure.** WarpToad is an exposed development family. O1's mechanism
  is the developer-documented warning, already recorded as exposure by
  D1-02/D1P-11, and O2 is an injected mutation.
- **What results can show.** They are method-evaluation evidence on a
  mechanism-derived mutation (O1) and an injected mutation (O2). They are
  not discoveries, held-out results, deployment claims, or evidence of a
  defect in pinned WarpToad.
- **Labels.** The anticipated outcomes are hypotheses, not encoded
  expectations: no `Ω` contains the expected verdict or the missing
  constraint.
- **Annotations.** These are AI-assisted design notes. Authors must inspect
  every citation and clause.

## 6. Provenance of O1 and O2

Contract §6.3 forbids presenting manual summaries as automatic recovery.
O1 and O2 are **planner-written**; an automation claim would require
BindCheck to re-derive the "reusable extraction" rows, with every other row
marked ASSUMED or policy.

| Element | O1 | O2 | Category |
| --- | --- | --- | --- |
| Decoded producer constraints, public-word map, opcode counts | D1P-13 decoder on the pinned program (repaired); on M-DOM's own build (faulty, pending) | D1P-13 decoder on the pinned program (both variants) | **Reusable extraction** |
| Circuit artifact, VK and verifier identity, plus consumer/verifier deployment pairing | Repaired: `934c21fe…` / `563a018c…` / `d9a822a5…` (D1P-13). Faulty: M-DOM's own artifact, VK and verifier (pending build gate) | Pinned artifact/VK/verifier for both. Faulty: M-SRC consumer paired with the pinned verifier (pending deployment record) | **Reusable extraction** (artifact/VK derivation) plus a **recorded deployment fact** |
| Consumer transition, guards K1/K2/K3, occurrence roles, `D_v` | Consumer lowering (to be built; B01 §6.3) and D1P-12R verifier facts | Same | **Reusable extraction** (pending implementation) |
| Hash construction definitions (§3.4), domain separators, tree depths, both-arms lowering | Read manually from `nargo_hashing`, poseidon v0.3.0 and `merkle-trees` sources | Same, plus `PoseidonT3` (not yet read) | **Manual implementation summary**; to be mechanically checked by §3.2 |
| `86 = 2 + 2·42` attribution | Inference | — | **Manual summary**; open (P5) |
| Policy: F7 (Aztec silo) / F1 + F2b (backed mint) | `main.nr:20-22` documentation | D1P-11 / D1P-12R documentation | **Protocol policy** (DRAFT) |
| Choice of obligation, scope predicates, admitted-state design (`S_DOM` synthetic Aztec trees; `S_SRC` burns) | Planner | Planner | **Defect-specific planner input** |
| Faulty variant | M-DOM: mechanism-derived from the `hashing` package and warning | M-SRC: injected, from documented reliance | **Defect-specific planner input** |
| Consumer-direction mechanisms (§1.6, §2.5) | Planner hypothesis | Planner hypothesis | **Defect-specific planner input** (to be implemented generically by CD, never hard-coded per defect) |
| Cryptographic assumptions A-KS1, CR(K) | Planner-approved stated assumptions | Same | **Stated assumption** |

## 7. Change log

| Date | Revision | Changes |
| --- | --- | --- |
| 2026-10-27 | 0 | Initial proposal (O1 DOM-AZ, O2 SRC-EVM). |
| 2026-10-27 | 1 | Applied planner decisions. (1) O1's faulty variant is now a mechanism-derived mutation supported by the unused `hashing` package and `main.nr:11-12`, with no claim of historical deployment; build, honest-control and attack-validation gates are required. (2) O2 is labeled an injected consumer mutation based on documented reliance; results show detection on that mutation, not a pinned-WarpToad defect. (3) New §3: the single-proof extraction assumption A-KS1, with multi-proof extraction inapplicable only because the scope excludes it; required mechanical checks of term coverage, function identity and canonical domains; a concise conditional violation-to-collision argument; and no-collision conditions on the actual constructions (sponge initialization, absorption, domain separation, output lane) instead of over raw lane-0 terms. `A_PRIME_UNSAT` stays separate from security verdicts until §3 holds. (4) The synthetic Aztec state is fixed-pre-state, synthetic admitted-tree evidence only, with no reachability through the real Aztec protocol (§1.5). (5) Runtime pooling is descriptive only, always alongside individual results; the four variant-obligations are one family and never meet the three-obligation threshold, so B02 alone cannot support a runtime claim. (6) New §6 provenance table; O1 and O2 are planner-written, not automatically derived. |
| 2026-10-27 | 2 | (1) A-KS1 (§3.1) is now instantiated per variant, with an identity table. O1's M-DOM gets its own compiled artifact, VK and generated verifier (pending the build gate) and never inherits the pinned key. O2's M-SRC consumer must be deployed with, and recorded against, the pinned verifier. The §1.2/§2.2 gates and the §6 provenance table were updated, and §3.3 uses the variant's own key. (2) The document is stated to be a conditional argument and implementation plan: P1–P6 are all pending, and the planner-approved assumptions neither make nor substitute for any mechanical check. |
