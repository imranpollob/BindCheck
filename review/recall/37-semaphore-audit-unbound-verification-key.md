# Recall card 37 — semaphore-audit-unbound-verification-key

`semaphore-audit-unbound-verification-key`

| Field | Value |
|---|---|
| Repository | semaphore-protocol/semaphore |
| DSL (ledger) | Circom/Solidity or generated Groth16 verifier |
| Ledger pattern / impact | deployed verification key not checked against circuit / proof-to-execution mismatch |
| Class v1 → v2 | `integration` → `integration` |
| Vulnerable → fixed | [5186a940ff](https://github.com/semaphore-protocol/semaphore/tree/5186a940ff495ff163bd5779631a716d0bf96507) → MISSING (not-publicly-pinned) |
| Exposure | **EXPOSED** — DEV row in source-corpus-v2 (semaphore-protocol/semaphore) |
| L4 proposal | **ADVISORY: DROP-CANDIDATE (no defect, no fix)** |

## 1. Source report (verbatim)

```text
[W2] Users must trust the verification key stored in the Verifier
contracts
Location
N/A
Description
The verification key stored in the Verification contract can store a key that is meant for a much
less strict circuit. All it takes is one person to catch the incorrect verification keys, but that
requires good background knowledge on how to do that. Perhaps an easy to use script that
verifies that the verification key stored in the Verifier contracts matches the circuits will help
users to fully trust the application.
Suggested Solution
Add a simple script that any user can quickly run to verify that the verifying keys match the
circuits.
```

<sub>Source: Semaphore 2.0.0 audit PDF, pdftotext -layout lines 247-263 of `results/raw/groundtruth/sources/semaphore-2.0.0-audit.txt` (sha256 975d9b029e18…)</sub>

## 2. Vulnerable vs fixed code

#### `contracts/base/Verifier.sol`

<table><tr><th>Vulnerable @ <code>5186a940ff</code>, lines 290–300</th><th>Fixed: MISSING</th></tr>
<tr><td valign="top"><pre> 290        !Pairing.pairingProd4(Pairing.negate(proof.A), proof.B, vk.alfa1, vk.beta2, vk_x, vk.gamma2, proof.C, vk.delta2)
 291      ) return 1;
 292      return 0;
 293    }
 294  
 295    /// @return r  bool true if proof is valid
 296    function verifyProof(
 297      uint256[2] memory a,
 298      uint256[2][2] memory b,
 299      uint256[2] memory c,
 300      uint256[4] memory input</pre></td><td valign="top"><pre>MISSING (no resolved fixed commit)</pre></td></tr></table>


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** n/a (process/trust warning)
- **Consumer consequence:** none shown
- **Fix locus:** none - 'Not handled' in the Fix Log
- **P1–P5 mappable:** no code defect to map
- **Research-contract scope:** not a code defect
- **Relational class:** VERIFIER-ONLY — trust in deployed key
- **Proposed expected pattern:** `NONE`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `MISSING`
- **Location basis:** audit Location: N/A
- **Concerns:**
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
