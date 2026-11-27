# Recall card 28 — zkemail-zellic-skipped-subject-prefix

`zkemail-zellic-skipped-subject-prefix`

| Field | Value |
|---|---|
| Repository | zkemail/ether-email-auth |
| DSL (ledger) | Circom/Solidity or generated Groth16 verifier |
| Ledger pattern / impact | unproven message tail changes authorized subject/effect / proof-to-execution mismatch |
| Class v1 → v2 | `integration` → `integration` |
| Vulnerable → fixed | [b5694a9e0e](https://github.com/zkemail/ether-email-auth/tree/b5694a9e0e49d07a862232f665dc4d0886c5a15f) → [1455cd221d](https://github.com/zkemail/ether-email-auth/tree/1455cd221dcb0849190879911688152669e4ed36) |
| Exposure | not exposed by C2; RELATED DEV repos in same org: zkemail/proof-of-twitter |
| L4 proposal | **KEEP (v1 strict; not subject to C1)** |

## 1. Source report (verbatim)

```text
3. Detailed Findings  3.1. Allowing bypass of proof verification via unrestricted skipedSubjectPrefix
  Target  EmailAuth.sol
  Category  Coding Mistakes  Severity  Critical
  Likelihood  High  Impact  Critical
  Description
  The vulnerability lies in the authEmail function of the EmailAuth contract, where an attacker can
  exploit the way certain parameters are processed. When a victim executes their transaction, cer-
  tain parameters such as expectedSubject, proof.maskedSubject, trimmedMaskedSubject, and
  proof.skipedSubjectPrefix are set.
  For example, the expectedSubject might be "A B C D", while proof.maskedSubject could be "A B C
  D", and the corresponding trimmedMaskedSubject remains "A B C D" (proof.skipedSubjectPrefix
  is zero in this case). Also, the Verifier contract’s verifyEmailProof function processes these values,
  packing the stringFields with "A B C D" and additional zero padding, resulting in a total length of
  605 bytes.
[…]
  vere risk, potentially leading to unauthorized transfers of valuable assets or control over contracts.
  Recommendations
  To prevent the described attack, the contract should enforce the following constraint.
  •  Constrain maskedSubject length: Ensure that the proof.maskedSubject is less than or
  equal to 605 bytes. This will prevent any excess data from being included in the proof.
```

<sub>Source: Zellic zk-email audit PDF (docs.zk.email), pdftotext -layout lines 460-482, 497-507 of `results/raw/groundtruth/sources/zkemail-zellic.txt` (sha256 ded98197ede9…)</sub>

## 2. Vulnerable vs fixed code

#### `packages/contracts/src/EmailAuth.sol`

Large file: showing the first 25 of 25 unified-diff lines between the pinned revisions.

```diff
--- vulnerable@b5694a9e
+++ fixed@1455cd22
@@ -222,4 +222,13 @@
             "invalid timestamp"
         );
+        require(
+            bytes(emailAuthMsg.proof.maskedSubject).length <=
+                verifier.SUBJECT_BYTES(),
+            "invalid masked subject length"
+        );
+        require(
+            emailAuthMsg.skipedSubjectPrefix < verifier.SUBJECT_BYTES(),
+            "invalid size of the skiped subject prefix"
+        );
 
         // Construct an expectedSubject from template and the values of emailAuthMsg.subjectParams.
@@ -242,5 +251,7 @@
 
         usedNullifiers[emailAuthMsg.proof.emailNullifier] = true;
-        lastTimestamp = emailAuthMsg.proof.timestamp;
+        if (timestampCheckEnabled) {
+            lastTimestamp = emailAuthMsg.proof.timestamp;
+        }
         emit EmailAuthed(
             emailAuthMsg.proof.emailNullifier,
```


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** yes - maskedSubject is a public input; skipedSubjectPrefix is caller-chosen calldata not in the proof
- **Consumer consequence:** yes - command/ownership change executed for a subject the proof did not authorise
- **Fix locus:** consumer (length bounds on maskedSubject and skipedSubjectPrefix)
- **P1–P5 mappable:** partial - P1 (effect parameters derived through a caller-chosen, unproven trim offset); P1 as implemented checks effect-argument dataflow, not string trimming
- **Research-contract scope:** in scope
- **Relational class:** RELATIONAL-CANDIDATE — consumer trims a public string by a caller-chosen offset; the correct bound is the circuit's SUBJECT_BYTES
- **Proposed expected pattern:** `P1`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^packages/contracts/src/EmailAuth\.sol(:\d+)?$`
- **Location basis:** authEmail at vulnerable EmailAuth.sol:200; removePrefix call :230-233
- **Concerns:**
  - Fixed commit 1455cd22 also fixes the lastTimestamp bug (row 31) in the same revision.

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
