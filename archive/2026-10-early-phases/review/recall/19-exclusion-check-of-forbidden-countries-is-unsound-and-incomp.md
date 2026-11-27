# Recall card 19 — exclusion-check-of-forbidden-countries-is-unsound-and-incomp

`circom/selfxyz/self/zksecurity_exclusion_check_of_forbidden_countries_is_unsound_and_incomplete_due_to_incorrect_indexing`

| Field | Value |
|---|---|
| Repository | selfxyz/self |
| DSL (ledger) | Circom |
| Ledger pattern / impact | Wrong Translation of Logic into Constraints / Soundness and Completeness |
| Class v1 → v2 | `integration-or-execution-semantics` → `integration` (**promoted**) |
| Vulnerable → fixed | [59c16d6e92](https://github.com/selfxyz/self/tree/59c16d6e924c946970665504d883ced46981e5c1) → MISSING (invalid-or-non-git-reference) |
| Exposure | not exposed by C2; **SAMPLE-OVERLAP** with 278-family EVAL draw: rank 259 (unclassified) |
| L4 proposal | **DEMOTE** |

## 1. Source report (verbatim)

> The `ProveCountryIsNotInList` check is performed by iterating over forbidden countries entry and comparing each letter individually for equality. However, the index `i` that is used to loop over the forbidden countries list is incorrect, as it should loop over `i * 3` instead.
>
> zkbugs Location:
> - Path: circuits/circuits/utils/passport/disclose/proveCountryIsNotInList.circom
>   - Function: ProveCountryIsNotInList
>   - Line: 12-18

<sub>Source: zkbugs README @ ee4eb3ab (`results/raw/groundtruth/work/zkbugs/zksecurity_exclusion_check_of_forbidden_countries_is_unsound_and_incomplete_due_to_incorrect_indexing/README.md`, sha256 0a223206e326…); report: https://github.com/zksecurity/zkbugs/blob/main/reports/documents/zksecurity-celo-self-audit.pdf</sub>

## 2. Vulnerable vs fixed code

#### `circuits/circuits/utils/passport/disclose/proveCountryIsNotInList.circom`

<table><tr><th>Vulnerable @ <code>59c16d6e92</code>, lines 8–22</th><th>Fixed: MISSING</th></tr>
<tr><td valign="top"><pre>   8      signal input forbidden_countries_list[forbiddenCountriesListLength * 3]; 
   9  
  10      signal equality_results[forbiddenCountriesListLength][4];
  11      
  12      for (var i = 0; i &lt; forbiddenCountriesListLength; i++) {
  13              equality_results[i][0] &lt;== IsEqual()([dg1[7], forbidden_countries_list[i ]]);
  14              equality_results[i][1] &lt;== IsEqual()([dg1[8], forbidden_countries_list[i + 1]]); 
  15              equality_results[i][2] &lt;== IsEqual()([dg1[9], forbidden_countries_list[i + 2]]);
  16              equality_results[i][3] &lt;==  equality_results[i][0] * equality_results[i][1];
  17              0 ===  equality_results[i][3] * equality_results[i][2];
  18      }
  19  
  20      signal output forbidden_countries_list_packed[2];
  21      forbidden_countries_list_packed  &lt;== PackBytes(forbiddenCountriesListLength * 3)(forbidden_countries_list);
  22  }</pre></td><td valign="top"><pre>MISSING (no resolved fixed commit)</pre></td></tr></table>


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** partly - as row 18 (forbidden-country list)
- **Consumer consequence:** yes in principle; impact is 'Soundness and Completeness'
- **Fix locus:** circuit-internal (index i -> i*3)
- **P1–P5 mappable:** no
- **Research-contract scope:** in scope under s5.3 only if a consumer relies on the exclusion result
- **Relational class:** CIRCUIT-ONLY — defect and fix inside ProveCountryIsNotInList
- **Proposed expected pattern:** `NONE`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^circuits/circuits/utils/passport/disclose/proveCountryIsNotInList\.circom(:\d+)?$`
- **Location basis:** zkbugs Location proveCountryIsNotInList.circom lines 12-18
- **Concerns:**
  - Fixed commit MISSING (zkbugs 'Fix Commit' empty).
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
