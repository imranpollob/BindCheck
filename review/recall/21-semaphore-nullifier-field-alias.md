# Recall card 21 — semaphore-nullifier-field-alias

`semaphore-nullifier-field-alias`

| Field | Value |
|---|---|
| Repository | semaphore-protocol/semaphore |
| DSL (ledger) | Circom/Solidity or generated Groth16 verifier |
| Ledger pattern / impact | replay-key field alias / proof-to-execution mismatch |
| Class v1 → v2 | `integration` → `integration` |
| Vulnerable → fixed | [8d703c124c](https://github.com/semaphore-protocol/semaphore/tree/8d703c124c663537966d6fc35cfec84146e236b2) → [3dcf79f6a0](https://github.com/semaphore-protocol/semaphore/tree/3dcf79f6a095397352f71384e3dc6889c640a50f) |
| Exposure | **EXPOSED** — DEV row in source-corpus-v2 (semaphore-protocol/semaphore); T25 DEV-H03/H04; lane brief (Semaphore field alias) |
| L4 proposal | **KEEP (v1 strict; not subject to C1)** |

## 1. Source report (verbatim)

> Looks like in [Semaphore.sol#L83](https://github.com/kobigurk/semaphore/blob/602dd57abb43e48f490e92d7091695d717a63915/semaphorejs/contracts/Semaphore.sol#L83) we don't check that nullifier length is less than field modulus. So `nullifier_hash + 21888242871839275222246405745257275088548364400416034343698204186575808495617` will also pass snark proof verification if it fits into uint256, allowing double spend.
> 
> Example of 2 transactions:
> 
> https://kovan.etherscan.io/tx/0x5e8bf35ad76a086b98698f9d20bd7b6397ccc90aa6f85c1c5debc0262be5458a
> https://kovan.etherscan.io/tx/0x9a47cc8daec9d0a5e9a860ada77730190124f9864a5917dcb8f41773d94cfc1a […]

<sub>Source: https://github.com/semaphore-protocol/semaphore/issues/16 (API copy `results/raw/groundtruth/sources/semaphore-issue-16.json`, sha256 3949d2d58a09…, first 700 chars)</sub>

## 2. Vulnerable vs fixed code

#### `semaphorejs/contracts/Semaphore.sol`

<table><tr><th>Vulnerable @ <code>8d703c124c</code>, lines 70–98</th><th>Fixed @ <code>3dcf79f6a0</code>, lines 63–82</th></tr>
<tr><td valign="top"><pre>  70      function broadcastSignal(
  71          bytes memory signal,
  72          uint[2] a,
  73          uint[2][2] b,
  74          uint[2] c,
  75          uint[5] input // (root, nullifiers_hash, signal_hash, external_nullifier, broadcaster_address)
  76      ) public {
  77          uint256 start_gas = gasleft();
  78  
  79          uint256 signal_hash = uint256(sha256(signal)) &gt;&gt; 8;
  80          require(signal_hash == input[2]);
  81          require(external_nullifier == input[3]);
  82          require(verifyProof(a, b, c, input));
  83          require(nullifiers_set[input[1]] == false);
  84          address broadcaster = address(input[4]);
  85          require(broadcaster == msg.sender);
  86  
  87          bool found_root = false;
  88          for (uint8 i = 0; i &lt; root_history_size; i++) {
  89              if (root_history[i] == input[0]) {
  90                  found_root = true;
  91                  break;
  92              }
  93          }
  94          require(found_root);
  95  
  96          insert(signal_tree_index, signal_hash);
  97          nullifiers_set[input[1]] = true;
  98          emit SignalBroadcast(signal, input[1], external_nullifier);</pre></td><td valign="top"><pre>  63      function broadcastSignal(
  64          bytes memory signal,
  65          uint[2] memory a,
  66          uint[2][2] memory b,
  67          uint[2] memory c,
  68          uint[5] memory input // (root, nullifiers_hash, signal_hash, external_nullifier, broadcaster_address)
  69      ) public {
  70          uint256 signal_hash = uint256(sha256(signal)) &gt;&gt; 8;
  71          require(signal_hash == input[2]);
  72          require(external_nullifier == input[3]);
  73          require(verifyProof(a, b, c, input));
  74          require(nullifiers_set[input[1]] == false);
  75          address broadcaster = address(input[4]);
  76          require(broadcaster == msg.sender);
  77  
  78          require(root_history[input[0]]);
  79  
  80          signals[current_signal_index++] = signal;
  81          nullifiers_set[input[1]] = true;
  82          emit SignalBroadcast(signal, input[1], external_nullifier);</pre></td></tr></table>


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** yes - nullifier hash is public input[1] and the replay-mapping key
- **Consumer consequence:** yes - double signal/spend
- **Fix locus:** build dependency: snarkjs pinned to f8ba7cbf whose generated verifier checks input < r; tracked Solidity unchanged at the replay check
- **P1–P5 mappable:** yes - P3 FIELD_ALIAS_REPLAY_KEY
- **Research-contract scope:** in scope
- **Relational class:** VERIFIER-CONSUMER — consumer raw-integer replay key vs verifier field reduction; no circuit fact needed
- **Proposed expected pattern:** `P3`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^semaphorejs/contracts/Semaphore\.sol(:\d+)?$`
- **Location basis:** broadcastSignal at vulnerable Semaphore.sol:70; replay read :83, write :97
- **Concerns:**
  - The fix is not visible in tracked Solidity: semaphorejs/contracts/verifier.sol is a symlink to ../build/verifier.sol (untracked build output). Vulnerable and fixed revisions are indistinguishable without generating the verifier with each revision's pinned snarkjs.
  - EXPOSED: DEV-H03/DEV-H04 and the lane brief. T25 retained output already shows P3 VERIFIED_WITHIN_SCOPE on both revisions with VERIFIER_ARTIFACT_MISSING (results/raw/T25/after-20261106T155532Z-23564/DEV-H03--result.json).

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
