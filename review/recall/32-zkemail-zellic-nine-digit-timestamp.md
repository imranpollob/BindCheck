# Recall card 32 — zkemail-zellic-nine-digit-timestamp

`zkemail-zellic-nine-digit-timestamp`

| Field | Value |
|---|---|
| Repository | zkemail/ether-email-auth |
| DSL (ledger) | Circom/Solidity or generated Groth16 verifier |
| Ledger pattern / impact | circuit-decoded timestamp violates contract freshness semantics / proof-to-execution mismatch |
| Class v1 → v2 | `integration` → `integration` |
| Vulnerable → fixed | [b5694a9e0e](https://github.com/zkemail/ether-email-auth/tree/b5694a9e0e49d07a862232f665dc4d0886c5a15f) → [b7fc2f6fc2](https://github.com/zkemail/ether-email-auth/tree/b7fc2f6fc27084bc9662403deb699c8d7aab7948) |
| Exposure | not exposed by C2; RELATED DEV repos in same org: zkemail/proof-of-twitter |
| L4 proposal | **ADVISORY: DEMOTE-CANDIDATE (circuit-internal, no P1-P5 mapping)** |

## 1. Source report (verbatim)

```text
  3.9. DKIM signatures before 2001 may break the timestamp logic
  Target  email_auth_template.circom
[…]
  Likelihood  Low  Impact  Low
  Description
[…]
  signal output out;
  signal sums[n+1];
  sums[0] <== 0;
  for(var i = 0; i < n; i++) {
  sums[i + 1] <== 10 * sums[i] + (in[i] - 48);
  }
  out <== sums[n];
  }
```

<sub>Source: Zellic zk-email audit PDF (docs.zk.email), pdftotext -layout lines 1064-1068, 1070-1075, 1100-1120 of `results/raw/groundtruth/sources/zkemail-zellic.txt` (sha256 ded98197ede9…)</sub>

## 2. Vulnerable vs fixed code

#### `packages/circuits/src/utils/digit2int.circom`

<table><tr><th>Vulnerable @ <code>b5694a9e0e</code>, lines 1–16</th><th>Fixed @ <code>b7fc2f6fc2</code>, lines 1–23</th></tr>
<tr><td valign="top"><pre>   1  pragma circom 2.1.6;
   2  
   3  include &quot;circomlib/circuits/bitify.circom&quot;;
   4  include &quot;circomlib/circuits/comparators.circom&quot;;
   5  include &quot;circomlib/circuits/poseidon.circom&quot;;
   6  include &quot;./constants.circom&quot;;
   7  
   8  
   9  // `in` is a big-endtian digit string of `out`.
  10  template Digit2Int(n) {
  11      signal input in[n];
  12      signal output out;
  13  
  14      out &lt;== DigitBytesToInt(n)(in);
  15  }
  16  </pre></td><td valign="top"><pre>   1  pragma circom 2.1.6;
   2  
   3  include &quot;circomlib/circuits/bitify.circom&quot;;
   4  include &quot;circomlib/circuits/comparators.circom&quot;;
   5  include &quot;circomlib/circuits/poseidon.circom&quot;;
   6  include &quot;./constants.circom&quot;;
   7  
   8  
   9  // `in` is a big-endtian digit string of `out`.
  10  template Digit2Int(n) {
  11      signal input in[n];
  12      signal output out;
  13  
  14      signal is_g[n];
  15      signal is_l[n];
  16      for(var i=0; i&lt;n; i++) {
  17          is_g[i] &lt;== GreaterEqThan(8)([in[i], 48]);
  18          is_l[i] &lt;== LessEqThan(8)([in[i], 57]);
  19          is_g[i] * is_l[i] === 1;
  20      }
  21      out &lt;== DigitBytesToInt(n)(in);
  22  }
  23  </pre></td></tr></table>


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** yes - timestamp is a public output used by the contract freshness check
- **Consumer consequence:** yes - stale (pre-2001) signature treated as fresh, or lastTimestamp pushed to year 2286; Zellic severity Low
- **Fix locus:** circuit-internal (digit range check in Digit2Int)
- **P1–P5 mappable:** no
- **Research-contract scope:** in scope under s5.3
- **Relational class:** RELATIONAL-CANDIDATE — circuit decoding yields a timestamp that violates the contract's freshness semantics; fix is in the circuit
- **Proposed expected pattern:** `NONE`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^packages/circuits/src/utils/digit2int\.circom(:\d+)?$`
- **Location basis:** Digit2Int template, vulnerable digit2int.circom
- **Concerns:**
  - Requires a DKIM signature generated before September 2001 (Zellic).

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
