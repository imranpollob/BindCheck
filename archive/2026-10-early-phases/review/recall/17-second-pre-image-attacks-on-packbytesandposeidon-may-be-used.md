# Recall card 17 — second-pre-image-attacks-on-packbytesandposeidon-may-be-used

`circom/selfxyz/self/zksecurity_second_pre_image_attacks_on_packbytesandposeidon_may_be_used_to_register_arbitrary_passports_and_dsc_certificates`

| Field | Value |
|---|---|
| Repository | selfxyz/self |
| DSL (ledger) | Circom |
| Ledger pattern / impact | Missing Input Constraints / Soundness |
| Class v1 → v2 | `integration-or-execution-semantics` → `integration` (**promoted**) |
| Vulnerable → fixed | [629dfdad1a](https://github.com/selfxyz/self/tree/629dfdad1a867eb82ccba6857a545f3ef838e123) → MISSING (invalid-or-non-git-reference) |
| Exposure | not exposed by C2; **SAMPLE-OVERLAP** with 278-family EVAL draw: rank 259 (unclassified) |
| L4 proposal | **DEMOTE** |

## 1. Source report (verbatim)

> The function `PackBytesAndPoseidon(k)` in CustomHashers.circom is susceptible to a second pre-image attack: given an input x, an input y can be found such that `PackBytesAndPoseidon(k)(x) == PackBytesAndPoseidon(k)(y)` where y is not an array of bytes, but an array of arbitrary field elements. For example consider [0, 1, 0] and [256, 0, 0] they both compute [256] as an intermediate value (output of PackBytes bytes.circom). This intermediate value is later passed to the `CustomHasher` function: because the intermediate value is identical, both inputs will yield the same hash.
>
> zkbugs Location:
> - Path: circuits/circuits/utils/passport/customHashers.circom
>   - Function: PackBytesAndPoseidon
>   - Line: 54-60

<sub>Source: zkbugs README @ ee4eb3ab (`results/raw/groundtruth/work/zkbugs/zksecurity_second_pre_image_attacks_on_packbytesandposeidon_may_be_used_to_register_arbitrary_passports_and_dsc_certificates/README.md`, sha256 f5edab36db90…); report: https://github.com/zksecurity/zkbugs/blob/main/reports/documents/zksecurity-self-aadhaar-circuits.pdf</sub>

## 2. Vulnerable vs fixed code

#### `circuits/circuits/utils/passport/customHashers.circom`

<table><tr><th>Vulnerable @ <code>629dfdad1a</code>, lines 50–60</th><th>Fixed: MISSING</th></tr>
<tr><td valign="top"><pre>  50  /// @notice PackBytesAndPoseidon circuit — used to pack a byte array and hash it
  51  /// @param k Size of the array to pack
  52  /// @param in Input array
  53  /// @param out Output hash
  54  template PackBytesAndPoseidon(k) {
  55      var packed_length = computeIntChunkLength(k);
  56  
  57      signal input in[k];
  58      signal packed[packed_length] &lt;== PackBytes(k)(in);
  59      signal output out &lt;== CustomHasher(packed_length)(packed);
  60  }</pre></td><td valign="top"><pre>MISSING (no resolved fixed commit)</pre></td></tr></table>


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** no - the packed bytes are hashed inside the circuit; the hash output, not the byte array, is public
- **Consumer consequence:** indirect - registration of arbitrary passports/DSC certificates via a valid proof
- **Fix locus:** circuit-internal (byte range checks inside PackBytesAndPoseidon)
- **P1–P5 mappable:** no
- **Research-contract scope:** borderline under s5.3
- **Relational class:** CIRCUIT-ONLY — defect and fix inside PackBytesAndPoseidon
- **Proposed expected pattern:** `NONE`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^circuits/circuits/utils/passport/customHashers\.circom(:\d+)?$`
- **Location basis:** zkbugs Location customHashers.circom PackBytesAndPoseidon lines 54-60
- **Concerns:**
  - Fixed commit MISSING (zkbugs 'Fix Commit' is empty; ledger stores the literal '* DSL: Circom').
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
