# Recall card 35 — semaphore-audit-group-id-field

`semaphore-audit-group-id-field`

| Field | Value |
|---|---|
| Repository | semaphore-protocol/semaphore |
| DSL (ledger) | Circom/Solidity or generated Groth16 verifier |
| Ledger pattern / impact | contract state permits external nullifier rejected by verifier field guard / proof-to-execution mismatch |
| Class v1 → v2 | `integration` → `integration` |
| Vulnerable → fixed | [5186a940ff](https://github.com/semaphore-protocol/semaphore/tree/5186a940ff495ff163bd5779631a716d0bf96507) → MISSING (not-publicly-pinned) |
| Exposure | **EXPOSED** — DEV row in source-corpus-v2 (semaphore-protocol/semaphore) |
| L4 proposal | **ADVISORY: DROP-CANDIDATE (liveness, not authorization)** |

## 1. Source report (verbatim)

```text
[M2] Missing checks to ensure zk proof inputs are less than
SNARK_SCALAR_FIELD
Location
https://github.com/semaphore-protocol/semaphore/blob/5186a940ff495ff163bd5779631a716d0b
f96507/contracts/base/SemaphoreGroups.sol#L27
Description
The SemaphoreGroup.sol contract uses the "groupId" as the external nullifier. Therefore, the
groupId will be provided as a public input when calling Verifier.verifyProof. When a user creates
a new poll via SemaphoreVoting.createPoll, the user can enter any uint256 value as the poll id,
which will then be the group Id. The issue arises when the user inputs a value for pollId that is
greater than the SNARK_SCALAR_FIELD constant. Then, the call to verify any proofs for this
poll will fail because the Verifier checks that input[i] < snark_scalar_field for each public input.
Since both the SemaphoreVoting.sol and SemaphoreWhistleblowing.sol contracts use the
groupId as external nullifiers, this issue is present in both.
Suggested Solution
Add a constraint in the SemaphoreGroup.sol contract to check that the groupId is less than the
SNARK_SCALAR_FIELD. This will protect any extensions that use the group id as an external
nullifier.
```

<sub>Source: Semaphore 2.0.0 audit PDF, pdftotext -layout lines 206-226 of `results/raw/groundtruth/sources/semaphore-2.0.0-audit.txt` (sha256 975d9b029e18…)</sub>

## 2. Vulnerable vs fixed code

> **Candidate fixed commit (not a ledger pin):** Fix Log names semaphore issue #90 (closed 2022-03-09T23:02:11Z). Commit 2ffaf28a ('fix: add check to ensure group id is valid zk value', 2022-03-09T17:43:06Z) adds exactly the recommended require. CANDIDATE only.

#### `contracts/base/SemaphoreGroups.sol`

<table><tr><th>Vulnerable @ <code>5186a940ff</code>, lines 25–40</th><th>CANDIDATE fixed @ <code>2ffaf28a12</code>, lines 25–41</th></tr>
<tr><td valign="top"><pre>  25    /// @param depth: Depth of the tree.
  26    /// @param zeroValue: Zero value of the tree.
  27    function _createGroup(
  28      uint256 groupId,
  29      uint8 depth,
  30      uint256 zeroValue
  31    ) internal virtual {
  32      require(getDepth(groupId) == 0, &quot;SemaphoreGroups: group already exists&quot;);
  33  
  34      groups[groupId].init(depth, zeroValue);
  35  
  36      emit GroupCreated(groupId, depth, zeroValue);
  37    }
  38  
  39    /// @dev Adds an identity commitment to an existing group.
  40    /// @param groupId: Id of the group.</pre></td><td valign="top"><pre>  25    /// @param depth: Depth of the tree.
  26    /// @param zeroValue: Zero value of the tree.
  27    function _createGroup(
  28      uint256 groupId,
  29      uint8 depth,
  30      uint256 zeroValue
  31    ) internal virtual {
  32      require(groupId &lt; SNARK_SCALAR_FIELD, &quot;SemaphoreGroups: group id must be &lt; SNARK_SCALAR_FIELD&quot;);
  33      require(getDepth(groupId) == 0, &quot;SemaphoreGroups: group already exists&quot;);
  34  
  35      groups[groupId].init(depth, zeroValue);
  36  
  37      emit GroupCreated(groupId, depth, zeroValue);
  38    }
  39  
  40    /// @dev Adds an identity commitment to an existing group.
  41    /// @param groupId: Id of the group.</pre></td></tr></table>


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** yes - groupId is used as the external nullifier public input
- **Consumer consequence:** denial of service only - proofs for that poll always fail
- **Fix locus:** consumer (require(groupId < SNARK_SCALAR_FIELD))
- **P1–P5 mappable:** no - P3 canonicality concerns aliasing that enables replay; here the verifier rejects (liveness)
- **Research-contract scope:** liveness: initially out of scope (s5.4)
- **Relational class:** VERIFIER-CONSUMER — contract accepts a group id that the verifier's public-input range check rejects
- **Proposed expected pattern:** `NONE`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^contracts/base/SemaphoreGroups\.sol(:\d+)?$`
- **Location basis:** _createGroup at vulnerable SemaphoreGroups.sol:27 (audit link #L27)
- **Concerns:**
  - Fixed pin MISSING in ledger; candidate 2ffaf28a12ac92d7683cfd4b507defdc0bf51300.
  - Semaphore repository is DEV (DEV-F02) - EXPOSED.

## 4. Reviewer decision

| Field | Fill in |
|---|---|
| Decision | ☐ ACCEPT  ☐ EDIT  ☐ DROP |
| Strict scope (keep / demote) | |
| expected_pattern (P1–P5 or NONE) | |
| expected_location_regex | |
| Accept candidate commit? (if shown) | ☐ yes ☐ no ☐ n/a |
| Reviewer | |
| Date | |
| Notes | |
