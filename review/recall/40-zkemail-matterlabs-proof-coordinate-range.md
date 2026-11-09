# Recall card 40 — zkemail-matterlabs-proof-coordinate-range

`zkemail-matterlabs-proof-coordinate-range`

| Field | Value |
|---|---|
| Repository | zkemail/ether-email-auth |
| DSL (ledger) | Circom/Solidity or generated Groth16 verifier |
| Ledger pattern / impact | generated verifier omits proof-coordinate base-field validation / proof-to-execution mismatch |
| Class v1 → v2 | `integration` → `integration` |
| Vulnerable → fixed | [8a62db1e67](https://github.com/zkemail/ether-email-auth/tree/8a62db1e676aedbb20a403be95fffebef12b97e4) → [984b5919a9](https://github.com/zkemail/ether-email-auth/tree/984b5919a9be715b743b08863ab6471c2b5356a6) |
| Exposure | not exposed by C2; RELATED DEV repos in same org: zkemail/proof-of-twitter |
| L4 proposal | **ADVISORY: NEEDS-PAIR-REPAIR** |

## 1. Source report (verbatim)

```text
9. The Groth16Verifier contract doesn't validate that coordinates of each elliptic curve
  point _pA, _pB, _pC, representing a ZK-proof, are within the base field (i.e., less than q). This
  causes an arithmetic underflow when computing negative _pA points during pairing
  operations since the YUL language lacks the underflow protection that Solidity provides.
```

<sub>Source: Matter Labs zk-email review PDF (docs.zk.email), pdftotext -layout lines 1014-1017 of `results/raw/groundtruth/sources/matterlabs-zkemail.txt` (sha256 e6aeb75e9b2a…)</sub>

## 2. Vulnerable vs fixed code

#### `packages/contracts/src/utils/Groth16Verifier.sol`

<table><tr><th>Vulnerable @ <code>8a62db1e67</code>, lines 484–492</th><th>Fixed @ <code>984b5919a9</code>, lines 271–276</th></tr>
<tr><td valign="top"><pre> 484                  // -A
 485                  mstore(_pPairing, calldataload(pA))
 486                  mstore(
 487                      add(_pPairing, 32),
 488                      mod(sub(q, calldataload(add(pA, 32))), q)
 489                  )
 490  
 491                  // B
 492                  mstore(add(_pPairing, 64), calldataload(pB))</pre></td><td valign="top"><pre> 271                  // -A
 272                  mstore(_pPairing, calldataload(pA))
 273                  mstore(add(_pPairing, 32), mod(sub(q, calldataload(add(pA, 32))), q))
 274  
 275                  // B
 276                  mstore(add(_pPairing, 64), calldataload(pB))</pre></td></tr></table>


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** n/a (proof encoding)
- **Consumer consequence:** unclear - underflow when negating pA
- **Fix locus:** claimed 'Resolved'; ledger fixed revision does not add coordinate checks
- **P1–P5 mappable:** partial - P4 (verifier invariant)
- **Research-contract scope:** borderline: proof-encoding validation sits next to the 'proof-system soundness' trusted assumption
- **Relational class:** VERIFIER-ONLY — proof-encoding validation in the verifier
- **Proposed expected pattern:** `P4`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^packages/contracts/src/utils/Groth16Verifier\.sol(:\d+)?$`
- **Location basis:** mod(sub(q, calldataload(add(pA, 32))), q) at vulnerable Groth16Verifier.sol:488
- **Concerns:**
  - Ledger fixed commit 984b5919 adds updateGroth16Verifier() to Verifier.sol; the fixed Groth16Verifier.sol still has no _pA/_pB/_pC < q check (fixed :273 'mod(sub(q, calldataload(add(pA, 32))), q)'). The pinned fixed revision does not remove the defect as described.

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
