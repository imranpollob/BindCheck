# Recall card 33 — zkemail-zellic-overlapping-masks

`zkemail-zellic-overlapping-masks`

| Field | Value |
|---|---|
| Repository | zkemail/ether-email-auth |
| DSL (ledger) | Circom/Solidity or generated Groth16 verifier |
| Ledger pattern / impact | overlapping circuit masks alter contract-visible subject semantics / proof-to-execution mismatch |
| Class v1 → v2 | `integration` → `integration` |
| Vulnerable → fixed | [b5694a9e0e](https://github.com/zkemail/ether-email-auth/tree/b5694a9e0e49d07a862232f665dc4d0886c5a15f) → [0096e59b9a](https://github.com/zkemail/ether-email-auth/tree/0096e59b9ac24c60d38a03a8f4c42f5d1be2c301) |
| Exposure | not exposed by C2; RELATED DEV repos in same org: zkemail/proof-of-twitter |
| L4 proposal | **ADVISORY: DROP-CANDIDATE (no code fix; no unauthorised effect)** |

## 1. Source report (verbatim)

```text
  3.10. Invitation code and email address may overlap, leading to unexpected be-
  havior
[…]
  To mask the subject bytes, one takes the full subject, matches InvitationCodeWithPrefixRegex,
  and matches EmailAddrRegex. Then, it subtracts the invitation code and email address from the
  subject bytes, then calls Bytes2Ints to make them field elements.
  signal masked_subject_bytes[max_subject_bytes];
  for(var i = 0; i < max_subject_bytes; i++) {
  masked_subject_bytes[i] <== subject_all[i] - removed_code[i] -
  removed_subject_email_addr[i];
  }
[…]
  Also, note that the Bytes2Ints circuit does not check that each input is a byte.
  One could even try to use this idea to craft a subject that has the following properties.
  •  The subject itself looks normal.
  •  Bytes2Ints(masked subject) = Bytes2Ints(dangerous masked subject).
  However, this does not work, as the masked subject is still composed of values within [-127, 127]
  (+- printable ASCII). As we are in base 256, and each Bytes2Ints only accumulates at most 31 bytes,
  it can be shown that even in Fp, no such “collisions'' occur. Note that this means that if we subtract
  out more things (not just two regex matches) a phishing-like idea could work, as the masked subject
[…]
  Impact
  The circuit does not work normally for email addresses with invitation code-like substrings.
```

<sub>Source: Zellic zk-email audit PDF (docs.zk.email), pdftotext -layout lines 1165-1168, 1178-1186, 1198-1209, 1216-1224 of `results/raw/groundtruth/sources/zkemail-zellic.txt` (sha256 ded98197ede9…)</sub>

## 2. Vulnerable vs fixed code

#### `packages/circuits/src/email_auth_template.circom`

<table><tr><th>Vulnerable @ <code>b5694a9e0e</code>, lines 108–125</th><th>Fixed @ <code>0096e59b9a</code>, lines 108–129</th></tr>
<tr><td valign="top"><pre> 108      signal raw_timestamp &lt;== Digit2Int(timestamp_len)(timestamp_str);
 109      timestamp &lt;== timestamp_regex_out * raw_timestamp;
 110      
 111      signal prefixed_code_regex_out, prefixed_code_regex_reveal[max_subject_bytes];
 112      (prefixed_code_regex_out, prefixed_code_regex_reveal) &lt;== InvitationCodeWithPrefixRegex(max_subject_bytes)(subject_all);
 113      is_code_exist &lt;== IsZero()(prefixed_code_regex_out-1);
 114      signal removed_code[max_subject_bytes];
 115      for(var i = 0; i &lt; max_subject_bytes; i++) {
 116          removed_code[i] &lt;== is_code_exist * prefixed_code_regex_reveal[i];
 117      }
 118      signal subject_email_addr_regex_out, subject_email_addr_regex_reveal[max_subject_bytes];
 119      (subject_email_addr_regex_out, subject_email_addr_regex_reveal) &lt;== EmailAddrRegex(max_subject_bytes)(subject_all);
 120      signal is_subject_email_addr_exist &lt;== IsZero()(subject_email_addr_regex_out-1);
 121      signal removed_subject_email_addr[max_subject_bytes];
 122      for(var i = 0; i &lt; max_subject_bytes; i++) {
 123          removed_subject_email_addr[i] &lt;== is_subject_email_addr_exist * subject_email_addr_regex_reveal[i];
 124      }
 125      signal masked_subject_bytes[max_subject_bytes];</pre></td><td valign="top"><pre> 108      signal raw_timestamp &lt;== Digit2Int(timestamp_len)(timestamp_str);
 109      timestamp &lt;== timestamp_regex_out * raw_timestamp;
 110      
 111      /// MASKED SUBJECT
 112      /// INVITATION CODE WITH PREFIX REGEX
 113      signal prefixed_code_regex_out, prefixed_code_regex_reveal[max_subject_bytes];
 114      (prefixed_code_regex_out, prefixed_code_regex_reveal) &lt;== InvitationCodeWithPrefixRegex(max_subject_bytes)(subject_all);
 115      is_code_exist &lt;== IsZero()(prefixed_code_regex_out-1);
 116      signal removed_code[max_subject_bytes];
 117      for(var i = 0; i &lt; max_subject_bytes; i++) {
 118          removed_code[i] &lt;== is_code_exist * prefixed_code_regex_reveal[i];
 119      }
 120      /// EMAIL ADDRESS REGEX
 121      /// Note: the email address in the subject should not overlap with the invitation code
 122      signal subject_email_addr_regex_out, subject_email_addr_regex_reveal[max_subject_bytes];
 123      (subject_email_addr_regex_out, subject_email_addr_regex_reveal) &lt;== EmailAddrRegex(max_subject_bytes)(subject_all);
 124      signal is_subject_email_addr_exist &lt;== IsZero()(subject_email_addr_regex_out-1);
 125      signal removed_subject_email_addr[max_subject_bytes];
 126      for(var i = 0; i &lt; max_subject_bytes; i++) {
 127          removed_subject_email_addr[i] &lt;== is_subject_email_addr_exist * subject_email_addr_regex_reveal[i];
 128      }
 129      signal masked_subject_bytes[max_subject_bytes];</pre></td></tr></table>


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** indirect - masked subject is public
- **Consumer consequence:** no demonstrated - Zellic shows no collision is possible; impact 'circuit does not work normally' (completeness)
- **Fix locus:** documentation only (comments added in 0096e59b); finding acknowledged, not fixed
- **P1–P5 mappable:** no
- **Research-contract scope:** out of the authorization model (completeness, no unauthorised effect shown)
- **Relational class:** CIRCUIT-ONLY — masking arithmetic inside the circuit
- **Proposed expected pattern:** `NONE`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^packages/circuits/src/email_auth_template\.circom(:\d+)?$`
- **Location basis:** masked_subject_bytes computation
- **Concerns:**
  - The fixed revision differs only by comments and an equivalent constraint rewrite; there is no fixed behaviour to score against.

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
