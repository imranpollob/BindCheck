# Recall card 15 — an-attacker-can-craft-a-fake-non-inclusion-proof-for-a-given

`circom/selfxyz/self/zksecurity_an_attacker_can_craft_a_fake_non_inclusion_proof_for_a_given_key_due_to_an_aliasing_bug_in_the_smt_verifier`

| Field | Value |
|---|---|
| Repository | selfxyz/self |
| DSL (ledger) | Circom |
| Ledger pattern / impact | Wrong Translation of Logic into Constraints / Soundness |
| Class v1 → v2 | `integration-or-execution-semantics` → `integration` (**promoted**) |
| Vulnerable → fixed | [4f18c75041](https://github.com/selfxyz/self/tree/4f18c75041bb47c1862169eef82c22067642a83a) → [99e8eece5e](https://github.com/selfxyz/self/tree/99e8eece5e0867017ca076731fba63ed96ae4711) |
| Exposure | not exposed by C2; **SAMPLE-OVERLAP** with 278-family EVAL draw: rank 259 (unclassified) |
| L4 proposal | **DEMOTE** |

## 1. Source report (verbatim)

> The `Num2Bits(254)` component presents an aliasing issue. The Num2Bits circuit in circomlib, witnesses the binary representation in the `out` array, and then checks that the recomposed value matches the input `in`. This computation is done modulo the field size, which is smaller than 2^254. Therefore, for approximately a quarter of the possible keys, an attacker can witness a different binary representation of the key.
>
> zkbugs Location:
> - Path: circuits/circuits/utils/crypto/merkle-trees/smt.circom
>   - Function: SMTVerify
>   - Line: 18-67

<sub>Source: zkbugs README @ ee4eb3ab (`results/raw/groundtruth/work/zkbugs/zksecurity_an_attacker_can_craft_a_fake_non_inclusion_proof_for_a_given_key_due_to_an_aliasing_bug_in_the_smt_verifier/README.md`, sha256 ebda862a6cfd…); report: https://github.com/zksecurity/zkbugs/blob/main/reports/documents/zksecurity-celo-self-audit-2.pdf</sub>

## 2. Vulnerable vs fixed code

#### `circuits/circuits/utils/crypto/merkle-trees/smt.circom`

<table><tr><th>Vulnerable @ <code>4f18c75041</code>, lines 22–32</th><th>Fixed @ <code>99e8eece5e</code>, lines 22–32</th></tr>
<tr><td valign="top"><pre>  22      signal input siblings[nLength];
  23      signal input mode;
  24      signal depth &lt;-- getSiblingsLength(siblings, nLength);
  25  
  26      // Convert the full key to bits and take only nLength bits
  27      component num2Bits = Num2Bits(254);  // Using 254 bits for poseidon output
  28      num2Bits.in &lt;== virtualKey;
  29      
  30      // Convert back to a field element using only nLength bits
  31      component bits2Num = Bits2Num(nLength);
  32      for (var i = 0; i &lt; nLength; i++) {</pre></td><td valign="top"><pre>  22      signal input siblings[nLength];
  23      signal input mode;
  24      signal depth &lt;-- getSiblingsLength(siblings, nLength);
  25  
  26      // Convert the full key to bits and take only nLength bits
  27      component num2Bits = Num2Bits_strict();  
  28      num2Bits.in &lt;== virtualKey;
  29  
  30      // Convert back to a field element using only nLength bits
  31      component bits2Num = Bits2Num(nLength);
  32      for (var i = 0; i &lt; nLength; i++) {</pre></td></tr></table>


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** no - virtualKey is an internal signal of SMTVerify (OFAC non-inclusion); it is not a public value read by a contract
- **Consumer consequence:** indirect - a forged non-inclusion proof lets a sanctioned identity register/disclose; the contract only sees the resulting proof
- **Fix locus:** circuit-internal (Num2Bits(254) -> Num2Bits_strict)
- **P1–P5 mappable:** no
- **Research-contract scope:** borderline under s5.3: consequence is a consumer-accepted proof, but no proof-to-execution interpretation mismatch
- **Relational class:** CIRCUIT-ONLY — defect and fix inside SMTVerify
- **Proposed expected pattern:** `NONE`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^circuits/circuits/utils/crypto/merkle-trees/smt\.circom(:\d+)?$`
- **Location basis:** zkbugs Location smt.circom SMTVerify lines 18-67
- **Concerns:**
  - selfxyz/self is also sampled EVAL family rank 259 (v2-family:b856f5604c150e532d44) - SAMPLE-OVERLAP between the recall gate and the held-out prevalence sample.

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
