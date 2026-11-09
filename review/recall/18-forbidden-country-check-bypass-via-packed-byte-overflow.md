# Recall card 18 — forbidden-country-check-bypass-via-packed-byte-overflow

`circom/selfxyz/self/zksecurity_forbidden_country_check_bypass_via_packed_byte_overflow`

| Field | Value |
|---|---|
| Repository | selfxyz/self |
| DSL (ledger) | Circom |
| Ledger pattern / impact | Wrong Translation of Logic into Constraints / Soundness |
| Class v1 → v2 | `integration-or-execution-semantics` → `integration` (**promoted**) |
| Vulnerable → fixed | [3905a30aeb](https://github.com/selfxyz/self/tree/3905a30aeb19016d22c5493b8b34ade2d118da4e) → MISSING (invalid-or-non-git-reference) |
| Exposure | not exposed by C2; **SAMPLE-OVERLAP** with 278-family EVAL draw: rank 259 (unclassified) |
| L4 proposal | **DEMOTE** |

## 1. Source report (verbatim)

> The elements of `forbidden_countries_list` are not range‑checked to be bytes, which means PackBytes allows for aliasing.
>
> zkbugs Location:
> - Path: circuits/circuits/utils/aadhaar/disclose/country_not_in_list.circom
>   - Function: CountryNotInList
>   - Line: 12-29

<sub>Source: zkbugs README @ ee4eb3ab (`results/raw/groundtruth/work/zkbugs/zksecurity_forbidden_country_check_bypass_via_packed_byte_overflow/README.md`, sha256 0ea42b8abda5…); report: https://github.com/zksecurity/zkbugs/blob/main/reports/documents/zksecurity-self-aadhaar-circuits.pdf</sub>

## 2. Vulnerable vs fixed code

> **Candidate fixed commit (not a ledger pin):** Ledger marks the fixed commit 'invalid-or-non-git-reference' because the field holds a Python list string. Both listed SHAs are valid commits; 60501d17 ('fix: range check for country not in list') changes exactly this file (+3 lines AssertBytes). Shown below as a CANDIDATE, not a ledger pin.

#### `circuits/circuits/utils/aadhaar/disclose/country_not_in_list.circom`

<table><tr><th>Vulnerable @ <code>3905a30aeb</code>, lines 10–20</th><th>CANDIDATE fixed @ <code>60501d17ee</code>, lines 10–23</th></tr>
<tr><td valign="top"><pre>  10  /// @output forbidden_countries_list_packed Packed forbidden countries list — gas optimized
  11  
  12  template CountryNotInList(MAX_FORBIDDEN_COUNTRIES_LIST_LENGTH) {
  13      signal input country[3];
  14      signal input forbidden_countries_list[MAX_FORBIDDEN_COUNTRIES_LIST_LENGTH * 3];
  15  
  16      signal equality_result[MAX_FORBIDDEN_COUNTRIES_LIST_LENGTH][4];
  17      signal is_equal[MAX_FORBIDDEN_COUNTRIES_LIST_LENGTH][3];
  18      for (var i = 0; i &lt; MAX_FORBIDDEN_COUNTRIES_LIST_LENGTH; i++) {
  19          equality_result[i][0] &lt;== 1;
  20          for (var j = 1; j &lt; 3 + 1; j++) {</pre></td><td valign="top"><pre>  10  /// @output forbidden_countries_list_packed Packed forbidden countries list — gas optimized
  11  
  12  template CountryNotInList(MAX_FORBIDDEN_COUNTRIES_LIST_LENGTH) {
  13      signal input country[3];
  14      signal input forbidden_countries_list[MAX_FORBIDDEN_COUNTRIES_LIST_LENGTH * 3];
  15  
  16      //Range-check for forbidden_countries_list
  17      AssertBytes(MAX_FORBIDDEN_COUNTRIES_LIST_LENGTH * 3)(forbidden_countries_list);
  18  
  19      signal equality_result[MAX_FORBIDDEN_COUNTRIES_LIST_LENGTH][4];
  20      signal is_equal[MAX_FORBIDDEN_COUNTRIES_LIST_LENGTH][3];
  21      for (var i = 0; i &lt; MAX_FORBIDDEN_COUNTRIES_LIST_LENGTH; i++) {
  22          equality_result[i][0] &lt;== 1;
  23          for (var j = 1; j &lt; 3 + 1; j++) {</pre></td></tr></table>


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** partly - the packed forbidden-country list is a public output that a verifier/consumer compares against its configured list
- **Consumer consequence:** yes in principle - a disclosure proof can claim a forbidden-country check that a consumer accepts
- **Fix locus:** circuit-internal (AssertBytes on forbidden_countries_list)
- **P1–P5 mappable:** no
- **Research-contract scope:** in scope under s5.3 if a consumer compares the packed list; consumer behaviour not inspected here
- **Relational class:** CIRCUIT-ONLY — defect and fix inside CountryNotInList
- **Proposed expected pattern:** `NONE`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^circuits/circuits/utils/aadhaar/disclose/country_not_in_list\.circom(:\d+)?$`
- **Location basis:** zkbugs Location country_not_in_list.circom CountryNotInList lines 12-29
- **Concerns:**
  - Ledger fixed_commit is a list literal; candidate 60501d17ee9b339e36c3a2a0d63f24bda65110a8 resolves (human must accept before it enters any gate).
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
