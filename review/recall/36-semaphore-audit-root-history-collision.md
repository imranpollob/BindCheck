# Recall card 36 — semaphore-audit-root-history-collision

`semaphore-audit-root-history-collision`

| Field | Value |
|---|---|
| Repository | semaphore-protocol/semaphore |
| DSL (ledger) | Circom/Solidity or generated Groth16 verifier |
| Ledger pattern / impact | root state indexed without group context / proof-to-execution mismatch |
| Class v1 → v2 | `integration` → `integration` |
| Vulnerable → fixed | [fd3cc6f7db](https://github.com/semaphore-protocol/semaphore/tree/fd3cc6f7db46aec83c0f807a8155dcd66561a0db) → [c6667d98b8](https://github.com/semaphore-protocol/semaphore/tree/c6667d98b8c72a424afd118da6cbde03a4945690) |
| Exposure | **EXPOSED** — DEV row in source-corpus-v2 (semaphore-protocol/semaphore) |
| L4 proposal | **KEEP (v1 strict) - human to confirm severity** |

## 1. Source report (verbatim)

```text
[W1] Root history can be overridden by a different group
Location
https://github.com/semaphore-protocol/semaphore/blob/fd3cc6f7db46aec83c0f807a8155dcd66
561a0db/contracts/base/SemaphoreGroups.sol#L21
Description
The root history field variable in the SemaphoreGroups.sol contract is meant to store a mapping
of every root to its corresponding group id. Since it is possible that the same users (with the
same identity commitments) are added as members in the same order, the root history for the
first group will be overridden. Instead all of those roots will map to the new group. This can be
an issue for any applications that assume the root history for a group is unique and never
overridden.
Suggested Solution
Allow dApps to implement this feature themselves if needed and remove from contract.
```

<sub>Source: Semaphore 2.0.0 audit PDF, pdftotext -layout lines 230-246 of `results/raw/groundtruth/sources/semaphore-2.0.0-audit.txt` (sha256 975d9b029e18…)</sub>

## 2. Vulnerable vs fixed code

#### `contracts/base/SemaphoreGroups.sol`

<table><tr><th>Vulnerable @ <code>fd3cc6f7db</code>, lines 40–75</th><th>Fixed @ <code>c6667d98b8</code>, lines 35–68</th></tr>
<tr><td valign="top"><pre>  40    /// @dev Adds an identity commitment to an existing group.
  41    /// @param groupId: Id of the group.
  42    /// @param identityCommitment: New identity commitment.
  43    function _addMember(uint256 groupId, uint256 identityCommitment) internal virtual {
  44      require(getDepth(groupId) != 0, &quot;SemaphoreGroups: group does not exist&quot;);
  45  
  46      groups[groupId].insert(identityCommitment);
  47  
  48      uint256 root = getRoot(groupId);
  49      rootHistory[root] = groupId;
  50  
  51      emit MemberAdded(groupId, identityCommitment, root);
  52    }
  53  
  54    /// @dev Removes an identity commitment from an existing group. A proof of membership is
  55    /// needed to check if the node to be deleted is part of the tree.
  56    /// @param groupId: Id of the group.
  57    /// @param identityCommitment: Existing identity commitment to be deleted.
  58    /// @param proofSiblings: Array of the sibling nodes of the proof of membership.
  59    /// @param proofPathIndices: Path of the proof of membership.
  60    function _removeMember(
  61      uint256 groupId,
  62      uint256 identityCommitment,
  63      uint256[] calldata proofSiblings,
  64      uint8[] calldata proofPathIndices
  65    ) internal virtual {
  66      require(getDepth(groupId) != 0, &quot;SemaphoreGroups: group does not exist&quot;);
  67  
  68      groups[groupId].remove(identityCommitment, proofSiblings, proofPathIndices);
  69  
  70      uint256 root = getRoot(groupId);
  71      rootHistory[root] = groupId;
  72  
  73      emit MemberRemoved(groupId, identityCommitment, groups[groupId].root);
  74    }
  75  </pre></td><td valign="top"><pre>  35    /// @dev Adds an identity commitment to an existing group.
  36    /// @param groupId: Id of the group.
  37    /// @param identityCommitment: New identity commitment.
  38    function _addMember(uint256 groupId, uint256 identityCommitment) internal virtual {
  39      require(getDepth(groupId) != 0, &quot;SemaphoreGroups: group does not exist&quot;);
  40  
  41      groups[groupId].insert(identityCommitment);
  42  
  43      uint256 root = getRoot(groupId);
  44  
  45      emit MemberAdded(groupId, identityCommitment, root);
  46    }
  47  
  48    /// @dev Removes an identity commitment from an existing group. A proof of membership is
  49    /// needed to check if the node to be deleted is part of the tree.
  50    /// @param groupId: Id of the group.
  51    /// @param identityCommitment: Existing identity commitment to be deleted.
  52    /// @param proofSiblings: Array of the sibling nodes of the proof of membership.
  53    /// @param proofPathIndices: Path of the proof of membership.
  54    function _removeMember(
  55      uint256 groupId,
  56      uint256 identityCommitment,
  57      uint256[] calldata proofSiblings,
  58      uint8[] calldata proofPathIndices
  59    ) internal virtual {
  60      require(getDepth(groupId) != 0, &quot;SemaphoreGroups: group does not exist&quot;);
  61  
  62      groups[groupId].remove(identityCommitment, proofSiblings, proofPathIndices);
  63  
  64      uint256 root = getRoot(groupId);
  65  
  66      emit MemberRemoved(groupId, identityCommitment, root);
  67    }
  68  </pre></td></tr></table>


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** yes - Merkle root is a public input; rootHistory maps root -> groupId
- **Consumer consequence:** possible - a root may be attributed to the wrong group; audit severity 'Warning: does not pose an immediate security threat'
- **Fix locus:** consumer (rootHistory mapping removed)
- **P1–P5 mappable:** partial - P2 (execution-context/group binding of the root)
- **Research-contract scope:** in scope only for an application that trusts rootHistory for group membership
- **Relational class:** CONSUMER-ONLY — contract root->group mapping
- **Proposed expected pattern:** `P2`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^contracts/base/SemaphoreGroups\.sol(:\d+)?$`
- **Location basis:** rootHistory[root] = groupId at vulnerable SemaphoreGroups.sol:49 and :71
- **Concerns:**
  - SemaphoreGroups.sol at fd3cc6f7 contains no verifier call; a consumer-centred analyzer may not treat it as a proof consumer.
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
