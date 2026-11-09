# Recall card 24 — payy-message-tail

`payy-message-tail`

| Field | Value |
|---|---|
| Repository | polybase/payy |
| DSL (ledger) | Circom/Solidity or generated Groth16 verifier — **WRONG: Noir/Solidity (UltraHonk); see card** |
| Ledger pattern / impact | public message extent mismatch / proof-to-execution mismatch |
| Class v1 → v2 | `integration` → `integration` |
| Vulnerable → fixed | [c4d2c9021b](https://github.com/polybase/payy/tree/c4d2c9021b8fb9988816eb6987a734b830bfce15) → [dcd5d96ee1](https://github.com/polybase/payy/tree/dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36) |
| Exposure | **EXPOSED** — DEV row in source-corpus-v2 (polybase/payy); T15-T19 (BindCheck/results/raw), T25 DEV-H05/H06, D1P/D2 reports; lane brief (Payy) |
| L4 proposal | **KEEP (v1 strict) but DSL label must be corrected** |

## 1. Source report (verbatim)

> ## Summary
> 
> `agg_agg` forwards the compacted message stream from its inner proofs into a public `messages: [Field; 1000]` array, but it never checks that the unused tail of the outer array is zero. A registered prover can build a valid `agg_final` proof for an approved rollup block while inserting an extra burn message after the real messages. `RollupV1.verifyRollup()` then parses that public input as a normal burn and transfers USDC from the rollup contract to the attacker.
> 
> This is a severe circuit soundness failure: the proof system accepts a public statement whose `messages` array is not fully derived from the verified inner proofs. On the current deployment, `verifyRollup()` is restricted to the existing allowlisted prover, so a fresh public caller cannot submit the invalid proof directly. That gate limits who can reach L1 today; it does not make the circuit statement sound.
> 
> The issue becomes permissionless under the prover model described in the [Payy whitepaper](https://polybase.github.io/zk-rollup/whitepaper.pdf). Section 3.3.2 states: "To join as a prover, the prover […]

<sub>Source: https://github.com/polybase/payy/security/advisories/GHSA-fhxc-63vg-9gwr (API copy `results/raw/groundtruth/sources/payy-ghsa.json`, sha256 fcec8f7bd2b8…, first 1100 chars)</sub>

## 2. Vulnerable vs fixed code

#### `noir/agg_agg/src/main.nr`

<table><tr><th>Vulnerable @ <code>c4d2c9021b</code>, lines 95–115</th><th>Fixed @ <code>dcd5d96ee1</code>, lines 96–115</th></tr>
<tr><td valign="top"><pre>  95                  first_public_inputs
  96              },
  97              proof.verification_key_hash,
  98              7,
  99          );
 100  
 101          if proof.old_root != 0 {
 102              assert(proof.old_root == root, &quot;proof old_root must match previous root&quot;);
 103              root = proof.new_root;
 104          }
 105      }
 106  
 107      assert(
 108          commit_hash
 109              == poseidon2::Poseidon2::hash(
 110                  [proofs[0].commit_hash, proofs[1].commit_hash],
 111                  2,
 112              ),
 113      );
 114      assert(new_root == root, &quot;Roots must match&quot;);
 115  }</pre></td><td valign="top"><pre>  96                  first_public_inputs
  97              },
  98              proof.verification_key_hash,
  99              7,
 100          );
 101  
 102          if proof.old_root != 0 {
 103              assert(proof.old_root == root, &quot;proof old_root must match previous root&quot;);
 104              root = proof.new_root;
 105          }
 106      }
 107  
 108      assert_message_tail_zero(messages, messages_index);
 109  
 110      assert(
 111          commit_hash
 112              == poseidon2::Poseidon2::hash([proofs[0].commit_hash, proofs[1].commit_hash], 2),
 113      );
 114      assert(new_root == root, &quot;Roots must match&quot;);
 115  }</pre></td></tr></table>

#### `eth/contracts/rollup3/RollupV1.sol`

<table><tr><th>Vulnerable @ <code>c4d2c9021b</code>, lines 400–415</th><th>Fixed @ <code>dcd5d96ee1</code>, lines 400–415 — <b>identical to vulnerable excerpt</b></th></tr>
<tr><td valign="top"><pre> 400      ) internal returns (uint) {
 401          // Get the kind from public input at index
 402          uint256 kind = uint256(publicInputs[index]);
 403  
 404          if (kind == 0) {
 405              return index + 1;
 406          } else if (kind == 2) {
 407              // Mint
 408              return verifyMint(index, publicInputs);
 409          } else if (kind == 3) {
 410              // Burn
 411              return verifyBurn(index, publicInputs);
 412          } else {
 413              // Not allowed
 414              revert(&quot;RollupV1: Invalid message kind&quot;);
 415          }</pre></td><td valign="top"><pre> 400      ) internal returns (uint) {
 401          // Get the kind from public input at index
 402          uint256 kind = uint256(publicInputs[index]);
 403  
 404          if (kind == 0) {
 405              return index + 1;
 406          } else if (kind == 2) {
 407              // Mint
 408              return verifyMint(index, publicInputs);
 409          } else if (kind == 3) {
 410              // Burn
 411              return verifyBurn(index, publicInputs);
 412          } else {
 413              // Not allowed
 414              revert(&quot;RollupV1: Invalid message kind&quot;);
 415          }</pre></td></tr></table>


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** yes - messages[1000] is a public output parsed by RollupV1.verifyRollup
- **Consumer consequence:** yes - forged burn transfers USDC (locally reproduced E4 in T15-T19 with locally controlled prover identity)
- **Fix locus:** circuit (assert_message_tail_zero in agg_agg); consumer RollupV1.sol is byte-identical across the pair
- **P1–P5 mappable:** no as currently defined - burn values ARE direct public inputs, so P1's 'direct public input' rule is satisfied; the defect is that the circuit leaves the tail unconstrained (prefix/extent relation, historical bindcheck_d1 R-EXTENT)
- **Research-contract scope:** in scope (contract s5.4 names agg_agg message tail in scope)
- **Relational class:** RELATIONAL — producer constrains the active prefix; consumer parses the whole 1000-word array (prefix vs extent)
- **Proposed expected pattern:** `NONE (closest P1; see mappability)`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^noir/agg_agg/src/main\.nr(:\d+)?$|^eth/contracts/rollup3/RollupV1\.sol(:\d+)?$`
- **Location basis:** defect: agg_agg/src/main.nr (no tail assertion before line 107 at vulnerable); consumer: RollupV1.sol verifyRollup:314, kind==3 burn at :409
- **Concerns:**
  - DSL label 'Circom/Solidity or generated Groth16 verifier' is wrong: the pinned tree has 25 .nr files, 0 .circom files, noir/agg_agg/Nargo.toml and an UltraHonk verifier (eth/contracts/noir/agg_agg_HonkVerifier.bin, eth/noir/agg_agg.sol). Proposed label: 'Noir/Solidity (Barretenberg UltraHonk verifier)'.
  - Ledger fixed commit dcd5d96 is a 105-file 'Sync ...' commit; docs/payy-case-study.md documents that it adds assert_message_tail_zero.
  - EXPOSED: DEV-H05/DEV-H06, T15-T19, lane brief. Research contract s9: 'Payy and authored fixtures are development cases, not held-out evidence.'
  - Attacker capability: registered (allowlisted) prover on the current deployment (GHSA text).

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
