# D1-03 protocol — minimal joint semantics (frozen before analyzer output)

Date: 23 October 2026. Authority: [research contract](../../docs/research-contract.md)
§4–§8 and [roadmap](../../docs/d1/roadmap.md) D1-03. Machine-readable twin:
[`d1-03-joint-semantics.json`](d1-03-joint-semantics.json). Both files are
hashed into `results/raw/D1-03/freeze/` before the first analyzer run on any
Payy case. Later changes require a new protocol version and a new run ID;
earlier outputs are preserved.

## 1 Completion criteria (from the roadmap, made measurable)

D1-03 is DONE only if all of the following hold:

1. **Schemas and IR.** `src/bindcheck_d1/` provides artifact identities, a
   policy schema, a result envelope (three verdicts plus evidence grade,
   scope, assumptions, provenance, non-vacuity and reason codes), and a
   boundary IR. The IR represents field words, consumer positions,
   occurrence records and state accesses separately.
2. **Extraction of one path.** The producer facts come from the compiled
   ACIR of the actual Payy `agg_agg` program. The consumer facts come from the
   solc AST of the actual `RollupV1` message path. Both are EXTRACTED with
   artifact locations. Any manual implementation fact is marked ASSUMED and
   counted.
3. **Faulty case.** Revision A (`c4d2c90`, real constraints) yields
   VIOLATION with a concrete model. The model then replays: the actual ACIR
   is executed by `nargo execute` with exit 0, the unchanged consumer runs in
   a local EVM with committed token effects, and an independent Python
   oracle confirms the policy violation from the observed effects.
4. **Repaired case.** Revision B (`dcd5d96`) yields a non-vacuous honest
   model that replays the same way, and VERIFIED_WITHIN_SCOPE under the
   declared scope.
5. **UNKNOWN discipline.** These conditions each produce UNKNOWN with a
   reason code:
   - an unsupported ACIR opcode or ACIR function call in the cone;
   - an unsupported Solidity construct on the path;
   - a missing declared assumption;
   - a solver timeout or resource failure;
   - an abstract SAT whose replay fails;
   - a reachable deferral (failed transfer).

   Each is shown by tests.
6. **Label isolation.** A test shows that expected verdicts or case labels
   cannot enter the analyzer input.
7. **Honest labeling.** Synthetic fixtures and synthetic seeds are labeled
   synthetic. No real-proof replay is claimed unless one is performed.

Failing any criterion leaves D1-03 incomplete. The reason must be reported;
it is not reinterpreted.

## 2 Cases (all Payy development data)

| ID | Producer | Decoder layer | Consumer | Scope modes |
|---|---|---|---|---|
| `payy-A-1000` | `noir/agg_agg` @ `c4d2c9021b8f…` (actual, N=1000) | `noir/agg_agg` → `agg_final` @ same revision | `eth/contracts/rollup3/RollupV1.sol` @ same revision | SEED-S1, SEED-S2 |
| `payy-B-1000` | `noir/agg_agg` @ `dcd5d96ee156…` (actual, N=1000) | same | same (byte-identical) | SEED-S1, SEED-S2 |
| `payy-A-8`, `payy-B-8`, `payy-m4-8` | T22's N=8 scaled sources (1000→8, 1005→13), identical scaling function; m4 = running-flag idiom | `agg_final` scaled the same way | RollupV1, `messages_length = 8` (admitted configuration) | FREE |
| `syn-*` | Synthetic printed-ACIR fixtures | n/a | Synthetic Solidity fixtures | Regression only; labeled SYNTHETIC |

The N=8 cases reuse the existing T22 controls. Their FREE-scope results do
not discharge the N=1000 claims, and vice versa.

## 3 Scope modes and admitted state (single transition)

All modes analyze one `verifyRollup` transition. Every mode quantifies over
all outer public inputs (roots, commit hash, all message words) and over all
ACIR witnesses that the declared constraints admit.

- **SEED-Sk.** The *certified inner vectors* are fixed to the synthetic seed
  Sk. These are the public-input arguments of each `RECURSIVE_AGGREGATION`
  call, together with each inner proof's `verification_key_hash`.
  Realizability of Sk by valid inner proofs is assumption A8; the seeds are
  SYNTHETIC. Fixing them is an explicit restriction: a SEED result says
  nothing about other inner proofs.
  - S1: proof 0 is non-padding (`old_root = 0x11`, `new_root = 0x12`,
    `commit_hash = 0x13`, `verification_key_hash = AGG_UTXO_VK_HASH`,
    messages `[2, 0x4b, 100, 0x4801, 0, …]`); proof 1 is padding
    (`old_root = 0`, messages all zero).
  - S2: proof 0 as in S1; proof 1 is non-padding (`old_root = 0x12`,
    `new_root = 0x14`, `commit_hash = 0x15`,
    `verification_key_hash = AGG_UTXO_VK_HASH`), messages
    `[3, 0x4b, 7, 0x4802, 0xdEaD, 0, …]`.
- **FREE.** The certified inner vectors are constrained only by the
  extracted `agg_agg` ACIR. Under A2 this is an over-approximation of the
  producer behaviors.

The admitted pre-state is the same for every mode:

- `rootHash` equals the outer `old_root`; it is owner-set at initialization,
  and that is admitted.
- One note kind `0x4b` maps to a standard OZ 5.0.1 ERC20 test token; other
  note kinds are unregistered.
- The mint registry is arbitrary: a symbolic `(amount, note_kind)` per hash,
  all initially unspent. In SEED mode the replay uses the model's registry.
- There are no burn substitutions. The prover and validators are owned
  (capability A7). The rollup's token balance is arbitrary; transfer success
  is modeled as a free boolean per attempt (`ok_j`). That over-approximates
  success for authorization; a failed attempt is a deferral and yields
  UNKNOWN for coverage.

This is a fixed-pre-state-family mode, not reachable-history exploration.
Results must say "single transition, admitted pre-state family".

## 4 Policy σ (analyst-supplied, independent of the expected verdict)

- **Certified vectors.** Each `RECURSIVE_AGGREGATION` call's public-input
  argument vector, as extracted from ACIR. Two certified vectors with equal
  content are one source (duplicate verification of the same proof grants
  nothing extra).
- **Permission records.** These are parsed from certified message words
  (vector offset 5 onward) starting at word 0, using the Payy compact message
  format documented in `pkg/zk-primitives`:
  - kind 2: mint, 4 words `[2, note_kind, value, hash]`;
  - kinds 3 and 4: 5 words; kind 3 is a burn
    `[3, note_kind, value, hash, recipient_word]`, and kind 4 (swap) grants no
    transfer permission;
  - any other word ends the parse.

  A permission's identity is (source, offset).
- **Protected effects.**
  - E-MINT: the state write `mints[hash].spent := true`.
  - E-BURN: a committed ERC20 transfer out of the rollup, of `value` units of
    `tokens[note_kind]`, to `address(uint160(recipient_word))`.

  Attempts whose transfer returns false are not committed effects.
- **Authorization.** Every committed E-MINT and E-BURN matches a distinct
  compatible permission of the same kind. Compatibility means equal
  `note_kind`, `value` and `hash`, plus, for burns, equal recipient. The
  analyzer uses *word equality* for the recipient. This under-approximates
  compatibility, so it may over-report violations (which then need replay)
  but cannot hide them. The oracle uses exact `uint160` semantics.
- **Coverage.** Every permission record is discharged by a distinct
  compatible committed effect. A compatible attempt whose transfer fails is
  a protocol deferral (substitution path). Deferral is unimplemented, so it
  yields UNKNOWN (`DEFERRAL_UNSUPPORTED`).
- **Violation goals** (each is a separate solver query; distinctness uses the
  sufficient conditions below):
  - G-AUTH-UNMATCHED: some committed effect has no compatible permission.
  - G-AUTH-SHARED: two committed effects at distinct positions are compatible
    with one permission.
  - G-COV-UNMATCHED: some permission has no compatible attempt.
  - G-COV-SHARED: two permissions are compatible with one attempt.
  - G-DEFER: some compatible attempt for a permission fails.
  - NONVAC: a successful transition with at least one committed effect
    (honest-path witness).
- **Verdict rule.**
  - VIOLATION: an AUTH-UNMATCHED or COV-UNMATCHED model is SAT, its replay
    succeeds, and the oracle confirms a violation.
  - VERIFIED_WITHIN_SCOPE: NONVAC is SAT and replays, and the AUTH-UNMATCHED,
    AUTH-SHARED, COV-UNMATCHED, COV-SHARED and DEFER goals are all UNSAT.
  - UNKNOWN: anything else. A SAT SHARED goal without an oracle-confirmed
    violation is UNKNOWN (`MATCHING_UNRESOLVED`). A SAT model whose replay
    fails is UNKNOWN (`CANDIDATE_NOT_CONCRETIZED`).

## 5 Assumptions recorded with every result

- A1: the pinned agg_final verifier accepts only proofs for the agg_final
  relation.
- A2: recursion soundness, i.e. each `RECURSIVE_AGGREGATION` call's public
  inputs belong to a valid proof under a key with the given key hash.
- A3: key correspondence. `AGG_AGG_VERIFICATION_KEY_HASH` identifies the
  compiled `agg_agg`; the consumer's registered verifier is that revision's
  agg_final verifier. This was established in T12/T15 on macOS and is not
  rechecked in D1-03, so it is ASSUMED.
- A4: verifier public inputs are canonical field elements, so a `bytes32`
  word equals the field value.
- A5: standard atomic OZ 5.0.1 ERC20 behavior.
- A6: correspondence between the solc 0.8.20 (viaIR) AST and bytecode
  semantics.
- A7: owned prover and validator capability.
- A8 (SEED only): the seed is realizable.
- A9: unmodeled black boxes (Poseidon2) have free outputs, an
  over-approximation; recursion black boxes are A2.

## 6 Method constraints

- **Producer.** Use the T22-v3 printed-ACIR parser through a hash-pinned
  adapter. Encode all live opcodes: ASSERT, RANGE, INIT/READ/WRITE memory,
  Brillig outputs free, recursion public-input bindings, and unmodeled black
  boxes with free outputs. Exact propagation may substitute a witness only
  where a constraint determines it uniquely (a linear unknown with a nonzero
  constant coefficient, or a ground check). Constraints are never dropped:
  each one is either kept, discharged by ground evaluation, or used for an
  equivalence-preserving substitution. A synthetic regression ports T22's
  implied-zero false positive.
- **Consumer.** Symbolic execution over the solc JSON AST of a documented
  subset. The scan loop `while (i < end) i = f(i)` is encoded by reachable
  positions when every case of `f` advances by a positive constant (checked
  from the extracted summary). Out-of-bounds calldata reads revert. External
  token calls use the A5 model. Anything else is UNKNOWN.
- **Joint link.** The agg_final ACIR must show each public message witness
  used, unchanged, as the matching recursion public input. The consumer AST
  must show `publicInputs` passed unchanged to `verifier.verify` and read for
  messages at `3 + j`. Both checks are EXTRACTED; if either fails, the result
  is UNKNOWN.
- **Solver.** cvc5 1.4.2 (GPL/CoCoA build already provisioned), QF_FF plus
  Bool, `--ff-solver=split`.

## 7 Frozen limits

- 300 s wall time and 4 GiB address space per solver query.
- At most 6 goals per (case, scope).
- N=1000 FREE scope is not run; it is reported as not attempted (size).
- No other solver attempts or configuration changes after a primary result;
  any change gets a new run ID.
- Replay: 600 s per `nargo execute`, 600 s per Foundry run.
- A real-proof replay (bb) is not part of this protocol. If attempted later,
  it is a separate protocol.

## 8 Pre-freeze exposure

The author knows the T15–T19 outcome: revision A accepts a forged tail burn
and revision B rejects it. Pre-freeze engineering compiled `agg_agg` @ A once
to profile the ACIR; that output was used only for opcode counts. No
analyzer, solver or replay ran on any Payy case before this freeze. Design
expectations: A SEED → VIOLATION; B SEED → VERIFIED_WITHIN_SCOPE; the FREE
N=8 outcomes are uncertain, and an UNKNOWN timeout is plausible given T22.
These expectations are recorded here only. They are never read by the
analyzer.
