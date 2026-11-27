# Recall card 47 — the-registration-and-disclosure-circuits-lack-range-checks-f

`circom/selfxyz/self/zksecurity_the_registration_and_disclosure_circuits_lack_range_checks_for_the_input_indices`

| Field | Value |
|---|---|
| Repository | selfxyz/self |
| DSL (ledger) | Circom |
| Ledger pattern / impact | Wrong Translation of Logic into Constraints / Soundness |
| Class v1 → v2 | `integration-or-execution-semantics` → `integration` (**promoted**) |
| Vulnerable → fixed | [4f18c75041](https://github.com/selfxyz/self/tree/4f18c75041bb47c1862169eef82c22067642a83a) → [49de54966e](https://github.com/selfxyz/self/tree/49de54966e40709ac59d4070fd4bd0279b2a10c0) |
| Exposure | not exposed by C2; **SAMPLE-OVERLAP** with 278-family EVAL draw: rank 259 (unclassified) |
| L4 proposal | **DEMOTE** |

## 1. Source report (verbatim)

> There are actually two separate issues with this code. (1) The computation `dsc_pubKey_offset + dsc_pubKey_actual_size` could overflow or underflow the field, leading to a wrong check semantics. (2) The `LessEqThan` template checks that the first input is less than or equal to the second input, but it assumes that both of the inputs are between 0 and 2^{12} - 1. If this is not the case, the circuit will produce some unexpected behaviour, as for example `LessEqThan(12)` with input values p - 1 and 0 will return 1 instead of 0. In this context, the intended range of the indices is to be between 0 and 2^{12} - 1, so this check could pass even if the indices are outside this range, leading to unexpected behaviour in the circuit.
>
> zkbugs Location:
> - Path: circuits/circuits/register_id/register_id.circom
>   - Function: REGISTER_ID
>   - Line: 101-105

<sub>Source: zkbugs README @ ee4eb3ab (`results/raw/groundtruth/work/zkbugs/zksecurity_the_registration_and_disclosure_circuits_lack_range_checks_for_the_input_indices/README.md`, sha256 3c78260df0db…); report: https://github.com/zksecurity/zkbugs/blob/main/reports/documents/zksecurity-celo-self-audit-2.pdf</sub>

## 2. Vulnerable vs fixed code

#### `circuits/circuits/register_id/register_id.circom`

<table><tr><th>Vulnerable @ <code>4f18c75041</code>, lines 95–110</th><th>Fixed @ <code>49de54966e</code>, lines 96–128</th></tr>
<tr><td valign="top"><pre>  95      signal input secret;
  96  
  97      // assert only bytes are used in raw_dsc
  98      AssertBytes(MAX_DSC_LENGTH)(raw_dsc);
  99  
 100      // check offsets refer to valid ranges
 101      signal dsc_pubKey_offset_in_range &lt;== LessEqThan(12)([
 102          dsc_pubKey_offset + dsc_pubKey_actual_size,
 103          raw_dsc_actual_length
 104      ]); 
 105      dsc_pubKey_offset_in_range === 1;
 106  
 107      // generate DSC leaf as poseidon(dsc_hash, csca_tree_leaf)
 108      signal dsc_hash &lt;== PackBytesAndPoseidon(MAX_DSC_LENGTH)(raw_dsc);
 109      signal dsc_hash_with_actual_length &lt;== Poseidon(2)([dsc_hash, raw_dsc_actual_length]);
 110      signal dsc_tree_leaf &lt;== Poseidon(2)([dsc_hash_with_actual_length, csca_tree_leaf]);</pre></td><td valign="top"><pre>  96  
  97      signal input secret;
  98  
  99      // assert only bytes are used in raw_dsc
 100      AssertBytes(MAX_DSC_LENGTH)(raw_dsc);
 101  
 102      // Assert `dsc_pubKey_offset` fits in 2^12
 103      component is_dsc_pk_offset_valid = Num2Bits(12);
 104      is_dsc_pk_offset_valid.in &lt;== dsc_pubKey_offset;
 105  
 106      // Assert `dsc_pubKey_actual_size` fits in 2^12
 107      component is_dsc_pk_actual_size_valid = Num2Bits(12);
 108      is_dsc_pk_actual_size_valid.in &lt;== dsc_pubKey_actual_size;
 109  
 110      // Assert `dsc_pubKey_offset + dsc_pubKey_actual_size` fits in 2^12
 111      component is_dsc_pk_offset_plus_actual_size_valid = Num2Bits(12);
 112      is_dsc_pk_offset_plus_actual_size_valid.in &lt;== dsc_pubKey_offset + dsc_pubKey_actual_size;
 113  
 114      //Assert &#x27;raw_dsc_actual_length&#x27; fits in 2^12
 115      component is_raw_dsc_actual_length_valid = Num2Bits(12);
 116      is_raw_dsc_actual_length_valid.in &lt;== raw_dsc_actual_length;
 117  
 118      // check offsets refer to valid ranges
 119      signal dsc_pubKey_offset_in_range &lt;== LessEqThan(12)([
 120          dsc_pubKey_offset + dsc_pubKey_actual_size,
 121          raw_dsc_actual_length
 122      ]);
 123      dsc_pubKey_offset_in_range === 1;
 124  
 125      // generate DSC leaf as poseidon(dsc_hash, csca_tree_leaf)
 126      signal dsc_hash &lt;== PackBytesAndPoseidon(MAX_DSC_LENGTH)(raw_dsc);
 127      signal dsc_hash_with_actual_length &lt;== Poseidon(2)([dsc_hash, raw_dsc_actual_length]);
 128      signal dsc_tree_leaf &lt;== Poseidon(2)([dsc_hash_with_actual_length, csca_tree_leaf]);</pre></td></tr></table>


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** no - dsc_pubKey_offset / actual_size are private witness indices
- **Consumer consequence:** indirect - registration with a mis-extracted DSC key
- **Fix locus:** circuit-internal (Num2Bits(12) range checks before LessEqThan)
- **P1–P5 mappable:** no
- **Research-contract scope:** borderline under s5.3
- **Relational class:** CIRCUIT-ONLY — defect and fix inside REGISTER_ID
- **Proposed expected pattern:** `NONE`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^circuits/circuits/register_id/register_id\.circom(:\d+)?$`
- **Location basis:** zkbugs Location register_id.circom REGISTER_ID lines 101-105
- **Concerns:**
  - Ledger fixed commit 49de5496 is a 'merge dev to main (#657)' bulk merge touching app, CI and circuits.
  - SAMPLE-OVERLAP (selfxyz/self, EVAL rank 259).

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
