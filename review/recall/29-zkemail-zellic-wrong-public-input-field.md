# Recall card 29 — zkemail-zellic-wrong-public-input-field

`zkemail-zellic-wrong-public-input-field`

| Field | Value |
|---|---|
| Repository | zkemail/ether-email-auth |
| DSL (ledger) | Circom/Solidity or generated Groth16 verifier |
| Ledger pattern / impact | replay-key alias from q-vs-r public-input guard / proof-to-execution mismatch |
| Class v1 → v2 | `integration` → `integration` |
| Vulnerable → fixed | [b5694a9e0e](https://github.com/zkemail/ether-email-auth/tree/b5694a9e0e49d07a862232f665dc4d0886c5a15f) → [e84065db4f](https://github.com/zkemail/ether-email-auth/tree/e84065db4fa087b8d6152bb9682de71f6676e3ff) |
| Exposure | not exposed by C2; RELATED DEV repos in same org: zkemail/proof-of-twitter |
| L4 proposal | **KEEP (v1 strict; not subject to C1)** |

## 1. Source report (verbatim)

```text
  3.3.  Incorrect public input range check
  Target  Groth16Verifier.sol
  Category  Coding Mistakes  Severity  High
  Likelihood  High  Impact  High
[…]
  // ....
  usedNullifiers[emailAuthMsg.proof.emailNullifier] = true;
  lastTimestamp = emailAuthMsg.proof.timestamp;
  }
  In the Groth16Verifier, an automatically generated verifier contract, the check is performed but im-
  plemented incorrectly.
  // Scalar field size
  uint256 constant r = 21888242871839275 ... 575808495617;
  // Base field size
  uint256 constant q = 21888242871839275 ... 645226208583;
  // ...
  function checkField(v) {
  if iszero(lt(v, q)) {
[…]
  }
  }
  Here, the field check is done against q, which is the base field of BN254. The correct check is against
  r, the scalar field of BN254. As q is larger than r, this allows an attacker to carry out an attack — for
  example, a nullifier can be used twice.
```

<sub>Source: Zellic zk-email audit PDF (docs.zk.email), pdftotext -layout lines 581-591, 606-626, 636-646 of `results/raw/groundtruth/sources/zkemail-zellic.txt` (sha256 ded98197ede9…)</sub>

## 2. Vulnerable vs fixed code

#### `packages/contracts/src/utils/Groth16Verifier.sol`

<table><tr><th>Vulnerable @ <code>b5694a9e0e</code>, lines 176–186</th><th>Fixed @ <code>e84065db4f</code>, lines 159–166</th></tr>
<tr><td valign="top"><pre> 176          }
 177  
 178          assembly {
 179  
 180              function checkField(v) {
 181                  if iszero(lt(v, q)) {
 182                      mstore(0, 0)
 183                      return(0, 0x20)
 184                  }
 185              }
 186              </pre></td><td valign="top"><pre> 159          assembly {
 160              function checkField(v) {
 161                  if iszero(lt(v, r)) {
 162                      mstore(0, 0)
 163                      return(0, 0x20)
 164                  }
 165              }
 166              </pre></td></tr></table>

#### `packages/contracts/src/EmailAuth.sol`

<table><tr><th>Vulnerable @ <code>b5694a9e0e</code>, lines 205–215</th><th>Fixed @ <code>e84065db4f</code>, lines 205–215 — <b>identical to vulnerable excerpt</b></th></tr>
<tr><td valign="top"><pre> 205                  emailAuthMsg.proof.domainName,
 206                  emailAuthMsg.proof.publicKeyHash
 207              ) == true,
 208              &quot;invalid dkim public key hash&quot;
 209          );
 210          require(
 211              usedNullifiers[emailAuthMsg.proof.emailNullifier] == false,
 212              &quot;email nullifier already used&quot;
 213          );
 214          require(
 215              accountSalt == emailAuthMsg.proof.accountSalt,</pre></td><td valign="top"><pre> 205                  emailAuthMsg.proof.domainName,
 206                  emailAuthMsg.proof.publicKeyHash
 207              ) == true,
 208              &quot;invalid dkim public key hash&quot;
 209          );
 210          require(
 211              usedNullifiers[emailAuthMsg.proof.emailNullifier] == false,
 212              &quot;email nullifier already used&quot;
 213          );
 214          require(
 215              accountSalt == emailAuthMsg.proof.accountSalt,</pre></td></tr></table>


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** yes - emailNullifier and timestamp are public inputs used as replay/freshness keys
- **Consumer consequence:** yes - nullifier reuse (x and x+r both < q)
- **Fix locus:** generated verifier (checkField compares against q at vulnerable, r at fixed)
- **P1–P5 mappable:** yes - P3 FIELD_ALIAS_REPLAY_KEY (guard uses the wrong modulus)
- **Research-contract scope:** in scope
- **Relational class:** VERIFIER-CONSUMER — verifier compares against q instead of r; consumer keys replay state by raw integer
- **Proposed expected pattern:** `P3`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^packages/contracts/src/EmailAuth\.sol(:\d+)?$`
- **Location basis:** replay key usedNullifiers at EmailAuth.sol:211/243 inside authEmail (:200); the wrong modulus is at Groth16Verifier.sol:181
- **Concerns:**
  - The ledger fixed commit e84065db itself only bumps snarkjs in package.json/yarn.lock; the regenerated Groth16Verifier.sol (lt(v, r)) is present at e84065db but was committed earlier. The pair is valid for scoring.
  - Auditor note: the only Solidity difference between the pair is the modulus constant inside checkField; a guard recogniser that does not check which modulus is compared cannot distinguish the pair.

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
