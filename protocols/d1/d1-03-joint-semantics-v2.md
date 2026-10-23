# D1-03 joint semantics v2 — immediate settlement fragment

Date: 23 October 2026. This is a prospective replacement for v1, authorized
by the user's “do the recommended tasks” follow-up to the preflight review.
The [research contract](../../docs/research-contract.md) remains authoritative.
V1, its freeze, and all historical results remain unchanged. This document
is a policy/design artifact, not an implemented analyzer or verification result.
The bounded design task is [separately frozen](d1-03-v2-design.json).

## 1. Completion and evidence gates

D1-03 still requires v1 §1's schemas, actual ACIR/consumer extraction, faithful
decoder link, faulty and repaired cases, replay, non-vacuity, label isolation,
and explicit UNKNOWN tests. None is discharged by the component tests below.
The repaired case is a **gate to be tested**, not an assumed result. A failed
gate leaves D1-03 incomplete and D1-04 blocked. Real inner proofs remain an
explicit assumption for synthetic seeds; ACIR execution is not a real proof.

Before primary execution, freeze a new manifest containing the exact analyzer,
policy, sources, compiled artifacts, adapters, tool executables, commands and
query hashes. Missing extraction/binding or artifact identity gives UNKNOWN;
do not replace it with a handwritten producer summary. This protocol contains
no expected case verdicts, missing-tail constraint, or asserted producer/output
equality. Historical T22 formulas and results are not rewritten.

## 2. Admitted states and transfer semantics

One successful, atomic `verifyRollup` transition; same revisions, message
capacities and owned prover/validator capability as v1. The root is initialized
to the outer old root. There are no substitutions. Kind `0x4b` maps to the
exact pinned OpenZeppelin 5.0.1 ERC20 implementation, with no overridden
transfer behavior, fees, callbacks or reentrancy. Other token registrations,
unmodeled token code, and empty-code targets are outside the supported family.
The test-only mint function initializes balances; it is not a settlement rule.

The immediate-transfer subfamily has these **explicit restrictions**:

- N is 8 or 1000. Each consumed burn amount is in `[0, 2^64-1]`.
- Each consumed burn's decoded recipient is nonzero. Decode exactly as
  `uint160(uint256(word))`; a nonzero field word alone is insufficient.
- Initial rollup token balance is `F = N * (2^64-1)`, initialized by minting
  that amount. All other token balances start at zero; total supply is F.
- The mint registry is symbolic, with initially unspent entries. Committed
  mint effects must satisfy the actual registry checks; incompatible or
  repeated consumption reverts the entire transition. Registry entries are
  not assumed to be reachable from a full deposit history.

The amount and funding restrictions apply to consumed effects without asking
whether they are authorized. They do not require P/O correspondence and cannot
silently constrain the implementation to have the missing binding. The report
must expose their cost: this excludes large amounts, zero-address recipients,
insufficient liquidity, other token behaviors and general reachable histories.
Excluded inputs are reported as outside scope/UNKNOWN, never as safe cases.

Derive each call result from the token state. A transfer to a nonzero recipient
succeeds iff the current sender balance covers the amount. On success, deduct
from the sender and add to the recipient, in that order. A self-transfer has
zero net balance change but is a successful transfer occurrence; amount zero
also has an occurrence. On failure, preserve balances and set the deferred
attempt flag. If the outer transition reverts, discard **all** its effects.
Conservation and `F < 2^256` exclude overflow for this initialization.

For an accepted scan there are at most N burn calls (in fact no more than
floor(N/5) when all records fit). Each costs at most `2^64-1` and a self-transfer
costs no net balance. Induction therefore gives enough balance before every
burn. This is a sufficient-condition argument, not an ACIR UNSAT certificate.
The analyzer must still encode and check the actual scan and state updates;
it must not set a free `ok_j` to true. It must model Solidity reads against
actual calldata bounds, not silently assume records fit a logical subarray.
An unhandled overread or boundary condition yields UNKNOWN.

Keep separate regression controls with insufficient funds, zero decoded
recipient, and unmodeled token behavior. A reachable failed transfer remains
`UNKNOWN / DEFERRAL_UNSUPPORTED` for joint coverage. The empty-account control
shows why low-level call success alone cannot be counted as a token effect.

## 3. Independent permissions and obligations

### Source provenance and policy decisions

Pinned evidence is captured at A `c4d2c9021b8fb9988816eb6987a734b830bfce15`
and B `dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36` under
`results/raw/D1-03/v2-design/sources/`, with hashes and exact `git show`
commands in `source-capture.json`.

| Evidence | What it supports | What it does not establish |
|---|---|---|
| `docs/whitepaper/05_utxo.md`, Mint/Burn discussion | Deposits create notes; burning destroys a note and releases bridge funds when proved on Ethereum | A complete policy specification or implementation correctness |
| `pkg/zk-primitives/src/agg_agg.rs`, `burn.rs` | Ordered message concatenation and burn record layout/address type | Missing producer constraints or a security verdict |
| `noir/agg_agg/src/main.nr` | Padding activation and substituted recursive verification arguments | That equal vector contents represent one authorization |
| `RollupV1.sol`, `verifyMint`, `verifyBurn`, `executeBurnToAddress`, `mint` | Registry consumption, address truncation, token call/failure behavior | That every permission is necessarily an obligation |

**Analyst policy choice:** in the explicitly funded, immediate-settlement
family, an active certified mint authorizes and obliges one registry-consumption
occurrence; an active certified burn authorizes and obliges one token-transfer
occurrence. This is motivated by the deposit/burn lifecycle above, but is not
an independently human-annotated fact or an extraction from the implementation.
Pending settlement, partial discharge, aggregation and substitution are not
implemented policies. They require a new reviewed protocol.

Represent permissions P and obligations O as separate lists with separate
provenance and classification fields. The policy resolver may create one of
each for this family; no generic rule sets `O := P`. A synthetic optional
permission with no obligation and no effect must pass both properties; a
mandatory obligation with no effect must fail coverage. This prevents the
schema from silently equating authorization and mandatory settlement.

### Logical activation and occurrence identity

Use logical producer frame identity and message offset: `(frame_id, offset)`.
Extract activation from the actual producer constraints/witness mapping. The
padding frame with old_root zero contributes no P or O, even if recursion
verifies the first proof again. Do not use a recursive-call index alone and
do not deduplicate vectors by value. Two active frames with equal messages
retain two occurrences. Active/certified correspondence must be checked:
pre-substitution vectors, activation predicates and actual recursive public
input arguments must be linked. If that link cannot be recovered, UNKNOWN.

Parse kind 2 as four words and kind 3 as five words. Padding zero emits no
record; a zero tail must be checked if relied on. Kind 4 or an unrecognized
format is unsupported for policy extraction, not evidence of no obligations.
Do not impose the desired outer-tail property as part of this parsing policy.

### Compatibility and effects

Each effect has its own consumer occurrence identity. A mint effect is the
committed `spent := true` write; a burn effect is the successful token transfer
occurrence with observed state and transfer event, including zero/self cases.
An attempt log is not a committed effect. Record the enclosing transaction's
commit status. The compatibility key is `(domain, kind, token/note_kind,
amount, note_hash, decoded_recipient)` with recipient absent for mint; domain
fixes this rollup/token mapping. Addresses use exact low-160 semantics in both
analyzer and replay oracle. Do not compare full recipient words.

Authorization requires an injective matching from E to P. Coverage independently
requires an injective matching from O to E. With the exact-equality compatibility
keys above, these are precisely `count_E(k) <= count_P(k)` and
`count_O(k) <= count_E(k)` for every key k. Preserve multiplicity, not merely
membership. Do not reject two effects sharing a compatible key when two
permissions exist. If compatibility is generalized beyond equality, this
counting argument no longer applies and the extension needs review.

## 4. Prospective queries, budgets and verdicts

Machine-readable matrix: [v2 JSON](d1-03-joint-semantics-v2.json). Retain the
seven v1 case/scope rows: A/B at N=1000 with S1/S2; A/B/m4 at N=8 FREE.
S1/S2 describe **logical pre-substitution frames**, not two independent
recursive-call inputs; preserve v1 numeric seed values. S2 is not run at N=8.
FREE at N=1000 is not attempted. Family status remains development-only.

For each row allocate exactly four primary slots:

1. AUTH: some compatibility class has more effects than permissions.
2. COVERAGE: some class has more obligations than effects.
3. DEFER: a compatible burn attempt fails in an otherwise accepted transition.
4. NONVAC: a successful transition with at least one protected effect.

At most 28 primary attempts total, each 300 seconds and 4 GiB; at most 8,400
solver wall-seconds. No retry or changed solver configuration after a result.
This is below v1's 42-slot ceiling; unused slots are **not** a tuning budget.
Do not preserve v1's pair-sharing goals: they are insufficient for general
injective matching and unnecessarily flag legitimate equal-key multiplicity.
The change is prospective and all prior results retain their original meaning.

At most one model/replay candidate from each AUTH, COVERAGE and NONVAC slot:
21 candidates, each at most one `nargo execute` (600 seconds) and one Foundry
invocation (600 seconds). No new real-proof generation. Missing or failing
replay is UNKNOWN. Synthetic unit/component tests are separately named and
never counted as primary verification. Log all attempts, including setup errors.

VIOLATION requires an AUTH or COVERAGE SAT candidate, actual-ACIR execution,
unchanged-consumer committed effects and independent trace-oracle confirmation.
VERIFIED_WITHIN_SCOPE requires AUTH, COVERAGE and DEFER UNSAT, plus NONVAC SAT
with successful replay and all extraction/assumption gates. Otherwise UNKNOWN.
Unsupported features, missing assumptions, timeout, allocation/build failures,
abstract-only SAT and unresolved replay are never verification. Report each
property separately when one is unresolved; a failed repair gate blocks D1-04.

Retain v1 A1–A9 as explicit assumptions with A8 only for SEED. A3's historical
key correspondence is not newly re-established. Exact token implementation,
initialization, numeric bound and immediate obligation policy are additional
scope conditions, not hidden implementation assertions. Token semantics and
canonical word/address translation must be validated before primary queries.

## 5. Design validation and remaining implementation

The design task permits one offline Foundry invocation and one finite Python
enumeration (at most 10,000 cases), zero primary queries, proof generation or
full rollup replay. Freeze their input hashes before execution and report
failure honestly. These checks test helper behavior, finite occurrence matching
and the sufficient funding condition; they cannot establish analyzer soundness.

Next implement extraction, the explicit P/O schema, exact matching and token
state semantics, unsupported/label-isolation regressions, and a hash-complete
execution manifest. Do not start D1-04 unless all D1-03 completion gates pass.
The existing mandated review stops after D1-04 and D1-06 and before held-out
evaluation remain in force. No independent target is evaluated here.
