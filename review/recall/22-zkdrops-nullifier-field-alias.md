# Recall card 22 — zkdrops-nullifier-field-alias

`zkdrops-nullifier-field-alias`

| Field | Value |
|---|---|
| Repository | a16z/zkdrops |
| DSL (ledger) | Circom/Solidity or generated Groth16 verifier |
| Ledger pattern / impact | replay-key field alias / proof-to-execution mismatch |
| Class v1 → v2 | `integration` → `integration` |
| Vulnerable → fixed | [4002962fb6](https://github.com/a16z/zkdrops/tree/4002962fb632578dd12477346d2e5c4159ffb2ef) → [f6f5802091](https://github.com/a16z/zkdrops/tree/f6f58020911cd2a19e1639f0dc93ec9fca2a9e17) |
| Exposure | **EXPOSED** — DEV row in source-corpus-v2 (a16z/zkdrops); results/raw/feasibility-v2/zkdrops-alias-e4-* (E4); T25 DEV-H01/H02; lane brief (zkDrops) |
| L4 proposal | **KEEP (v1 strict; not subject to C1)** |

## 1. Source report (verbatim)

> Currently the nullifier is not checked to be within the SNARK field. This allows creating a nullifier which is still a valid bytes32/uint256 that has the same result modulo the field, but the spent nullifier dictionary treats them as different, allowing double-spending.﻿ […]

<sub>Source: https://github.com/a16z/zkdrops/pull/2 (API copy `results/raw/groundtruth/sources/zkdrops-pr-2.json`, sha256 2335dabaea44…, first 500 chars)</sub>

## 2. Vulnerable vs fixed code

#### `contracts/PrivateAirdrop.sol`

<table><tr><th>Vulnerable @ <code>4002962fb6</code>, lines 35–48</th><th>Fixed @ <code>f6f5802091</code>, lines 37–51</th></tr>
<tr><td valign="top"><pre>  35      /// @notice verifies the proof, collects the airdrop if valid, and prevents this proof from working again.
  36      function collectAirdrop(bytes calldata proof, bytes32 nullifierHash) public {
  37          require(!nullifierSpent[nullifierHash], &quot;Airdrop already redeemed&quot;);
  38  
  39          uint[] memory pubSignals = new uint[](3);
  40          pubSignals[0] = uint256(root);
  41          pubSignals[1] = uint256(nullifierHash);
  42          pubSignals[2] = uint256(uint160(msg.sender));
  43          require(verifier.verifyProof(proof, pubSignals), &quot;Proof verification failed&quot;);
  44  
  45          nullifierSpent[nullifierHash] = true;
  46          airdropToken.transfer(msg.sender, amountPerRedemption);
  47      }
  48  </pre></td><td valign="top"><pre>  37      /// @notice verifies the proof, collects the airdrop if valid, and prevents this proof from working again.
  38      function collectAirdrop(bytes calldata proof, bytes32 nullifierHash) public {
  39          require(uint256(nullifierHash) &lt; SNARK_FIELD ,&quot;Nullifier is not within the field&quot;);
  40          require(!nullifierSpent[nullifierHash], &quot;Airdrop already redeemed&quot;);
  41  
  42          uint[] memory pubSignals = new uint[](3);
  43          pubSignals[0] = uint256(root);
  44          pubSignals[1] = uint256(nullifierHash);
  45          pubSignals[2] = uint256(uint160(msg.sender));
  46          require(verifier.verifyProof(proof, pubSignals), &quot;Proof verification failed&quot;);
  47  
  48          nullifierSpent[nullifierHash] = true;
  49          airdropToken.transfer(msg.sender, amountPerRedemption);
  50      }
  51  </pre></td></tr></table>


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** yes - nullifierHash is public signal [1] and the replay key
- **Consumer consequence:** yes - repeated airdrop claim (locally reproduced E4: results/raw/feasibility-v2/zkdrops-alias-e4-20261103T183918Z-54527)
- **Fix locus:** consumer (require(uint256(nullifierHash) < SNARK_FIELD))
- **P1–P5 mappable:** yes - P3 FIELD_ALIAS_REPLAY_KEY
- **Research-contract scope:** in scope
- **Relational class:** VERIFIER-CONSUMER — consumer raw-integer replay key vs verifier field reduction; no circuit fact needed
- **Proposed expected pattern:** `P3`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^contracts/PrivateAirdrop\.sol(:\d+)?$`
- **Location basis:** collectAirdrop at vulnerable PrivateAirdrop.sol:36
- **Concerns:**
  - EXPOSED: DEV-H01/DEV-H02, feasibility-v2 E4, lane brief.
  - Auditor observation (not a decision): T25 retained output gives P3 VERIFIED_WITHIN_SCOPE on the vulnerable revision because p4.canonical_guard's checkField regex spans 19,084 characters of semicolon-free Yul (MerkVerifier.sol lines 183-743) and matches an unrelated 'calculatePl(pMem, pubSignals'. See reports/groundtruth/REPORT.md section 'Verdict defects observed in retained DEV output'.

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
