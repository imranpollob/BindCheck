# Recall card 20 — incorrect-initialization-in-membership-circuits

`circom/tangle-network/protocol-solidity/veridise_incorrect_initialization_in_membership_circuits`

| Field | Value |
|---|---|
| Repository | tangle-network/protocol-solidity |
| DSL (ledger) | Circom |
| Ledger pattern / impact | Wrong Translation of Logic into Constraints / Soundness |
| Class v1 → v2 | `integration-or-execution-semantics` → `integration` (**promoted**) |
| Vulnerable → fixed | [848d073bb1](https://github.com/tangle-network/protocol-solidity/tree/848d073bb17f0aaffc6d39f594cc59efedeaec89) → [eeb4fc7a48](https://github.com/tangle-network/protocol-solidity/tree/eeb4fc7a4883d513e3fe3adbe2c447133ccd39f2) |
| Exposure | not exposed by C2 |
| L4 proposal | **DEMOTE** |

## 1. Source report (verbatim)

> The templates `SetMembership` try to check if an element e is in a set S by generating a constraint of the form: for all  s in S, product of (s - e) = 0. They do does this by iterating over elements s of the set S and building the product. The issue is that `product[0]` is initialized to `element` which makes the constarint to be trivailly satisfied when `element` is 0.
>
> zkbugs Location:
> - Path: circuits/set/membership.circom
>   - Function: SetMembership
>   - Line: 20

<sub>Source: zkbugs README @ ee4eb3ab (`results/raw/groundtruth/work/zkbugs/veridise_incorrect_initialization_in_membership_circuits/README.md`, sha256 869a8ab2f477…); report: https://github.com/zksecurity/zkbugs/blob/main/reports/documents/veridise-tangle-network-protocol-solidity.pdf</sub>

## 2. Vulnerable vs fixed code

#### `circuits/set/membership.circom`

<table><tr><th>Vulnerable @ <code>848d073bb1</code>, lines 14–26</th><th>Fixed @ <code>eeb4fc7a48</code>, lines 14–26</th></tr>
<tr><td valign="top"><pre>  14  template SetMembership(length) {
  15    signal input element;
  16    signal input set[length];
  17    
  18    signal diffs[length];
  19    signal product[length + 1];
  20    product[0] &lt;== element;
  21  
  22    for (var i = 0; i &lt; length; i++) {
  23      diffs[i] &lt;== set[i] - element;
  24      product[i + 1] &lt;== product[i] * diffs[i];
  25    }
  26  </pre></td><td valign="top"><pre>  14  template SetMembership(length) {
  15    signal input element;
  16    signal input set[length];
  17    
  18    signal diffs[length];
  19    signal product[length + 1];
  20    product[0] &lt;== 1;
  21  
  22    for (var i = 0; i &lt; length; i++) {
  23      diffs[i] &lt;== set[i] - element;
  24      product[i + 1] &lt;== product[i] * diffs[i];
  25    }
  26  </pre></td></tr></table>


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** partly - the set (Merkle roots) is a public input supplied by the anchor contract; element is the computed root
- **Consumer consequence:** yes in principle (membership check trivially satisfied when element = 0)
- **Fix locus:** circuit-internal (product[0] <== 1)
- **P1–P5 mappable:** no
- **Research-contract scope:** borderline: exploitation needs a computed root equal to 0
- **Relational class:** CIRCUIT-ONLY — defect and fix inside SetMembership
- **Proposed expected pattern:** `NONE`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^circuits/set/membership\.circom(:\d+)?$`
- **Location basis:** zkbugs Location membership.circom SetMembership line 20
- **Concerns:**
  - Ledger fixed commit eeb4fc7a is a bulk 'Veridise audit fixes (#350)' commit; other fixes ship in the same revision.
  - Repository is an EVAL in-scope family (v2-family:6edc8a55e55ee119f15c) but not in the 278 sample.

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
