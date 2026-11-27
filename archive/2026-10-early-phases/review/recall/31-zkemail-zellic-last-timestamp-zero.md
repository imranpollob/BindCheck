# Recall card 31 — zkemail-zellic-last-timestamp-zero

`zkemail-zellic-last-timestamp-zero`

| Field | Value |
|---|---|
| Repository | zkemail/ether-email-auth |
| DSL (ledger) | Circom/Solidity or generated Groth16 verifier |
| Ledger pattern / impact | replay/freshness state overwritten on accepted zero timestamp / proof-to-execution mismatch |
| Class v1 → v2 | `integration` → `integration` |
| Vulnerable → fixed | [b5694a9e0e](https://github.com/zkemail/ether-email-auth/tree/b5694a9e0e49d07a862232f665dc4d0886c5a15f) → [4e2f119a42](https://github.com/zkemail/ether-email-auth/tree/4e2f119a428b694c1115e59dc52cfbe278c0e494) |
| Exposure | not exposed by C2; RELATED DEV repos in same org: zkemail/proof-of-twitter |
| L4 proposal | **KEEP (v1 strict; not subject to C1)** |

## 1. Source report (verbatim)

```text
  3.7. The lasttimestamp update mechanism flaw in EmailAuth
  Target  EmailAuth.sol
  Category  Coding Mistakes  Severity  Low
  Likelihood  Low  Impact  Low
  Description
  Based on the below code, if emailAuthMsg.proof.timestamp is zero, the lastTimestamp is
  overwritten with zero. This could potentially disrupt the logic that relies on the emailAu-
  thMsg.proof.timestamp value, as the condition checking the timestamp may be affected by this
  overwrite.
[…]
  Impact
  The code intended to prevent the use of outdated proofs using lastTimestamp may not function
  correctly.
[…]
  Recommendations
  To  resolve this issue, lastTimestamp  should  only  be  updated  when  emailAu-
  thMsg.proof.timestamp is not zero.
```

<sub>Source: Zellic zk-email audit PDF (docs.zk.email), pdftotext -layout lines 917-933, 958-961, 971-974 of `results/raw/groundtruth/sources/zkemail-zellic.txt` (sha256 ded98197ede9…)</sub>

## 2. Vulnerable vs fixed code

#### `packages/contracts/src/EmailAuth.sol`

Large file: showing the first 42 of 62 unified-diff lines between the pinned revisions.

```diff
--- vulnerable@b5694a9e
+++ fixed@4e2f119a
@@ -222,18 +222,42 @@
             "invalid timestamp"
         );
+        require(
+            bytes(emailAuthMsg.proof.maskedSubject).length <=
+                verifier.SUBJECT_BYTES(),
+            "invalid masked subject length"
+        );
+        require(
+            emailAuthMsg.skipedSubjectPrefix < verifier.SUBJECT_BYTES(),
+            "invalid size of the skipped subject prefix"
+        );
 
         // Construct an expectedSubject from template and the values of emailAuthMsg.subjectParams.
-        string memory expectedSubject = SubjectUtils.computeExpectedSubject(
-            emailAuthMsg.subjectParams,
-            template
-        );
+        // string memory expectedSubject = SubjectUtils.computeExpectedSubject(
+        //     emailAuthMsg.subjectParams,
+        //     template
+        // );
         string memory trimmedMaskedSubject = removePrefix(
             emailAuthMsg.proof.maskedSubject,
             emailAuthMsg.skipedSubjectPrefix
         );
-        require(
-            Strings.equal(expectedSubject, trimmedMaskedSubject),
-            "invalid subject"
-        );
+        // require(
+        //     Strings.equal(expectedSubject, trimmedMaskedSubject),
+        //     "invalid subject"
+        // );
+        string memory expectedSubject = "";
+        for (uint stringCase = 0; stringCase < 3; stringCase++) {
+            expectedSubject = SubjectUtils.computeExpectedSubject(
+                emailAuthMsg.subjectParams,
+                template,
+                stringCase
```


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** yes - timestamp is a public input
- **Consumer consequence:** yes - lastTimestamp freshness state reset to 0; Zellic severity Low
- **Fix locus:** consumer (update lastTimestamp only when enabled / non-zero)
- **P1–P5 mappable:** partial - P3 (replay/freshness state), but P3 as implemented models mapping-keyed replay, not monotone timestamps
- **Research-contract scope:** in scope
- **Relational class:** CONSUMER-ONLY — contract freshness-state update
- **Proposed expected pattern:** `P3`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^packages/contracts/src/EmailAuth\.sol(:\d+)?$`
- **Location basis:** lastTimestamp = emailAuthMsg.proof.timestamp at vulnerable EmailAuth.sol:244 in authEmail (:200)
- **Concerns:**
  - The same fix already ships in row 28's fixed commit 1455cd22.

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
