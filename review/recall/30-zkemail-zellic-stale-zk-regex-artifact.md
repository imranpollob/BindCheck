# Recall card 30 — zkemail-zellic-stale-zk-regex-artifact

`zkemail-zellic-stale-zk-regex-artifact`

| Field | Value |
|---|---|
| Repository | zkemail/ether-email-auth |
| DSL (ledger) | Circom/Solidity or generated Groth16 verifier |
| Ledger pattern / impact | stale circuit generation omitted audited dependency fixes / proof-to-execution mismatch |
| Class v1 → v2 | `integration` → `integration` |
| Vulnerable → fixed | [b5694a9e0e](https://github.com/zkemail/ether-email-auth/tree/b5694a9e0e49d07a862232f665dc4d0886c5a15f) → [9deaf80435](https://github.com/zkemail/ether-email-auth/tree/9deaf80435502c4d9c1a77465a0e8195f749e63d) |
| Exposure | not exposed by C2; RELATED DEV repos in same org: zkemail/proof-of-twitter |
| L4 proposal | **ADVISORY: DEMOTE-CANDIDATE (circuit-internal, no P1-P5 mapping)** |

## 1. Source report (verbatim)

```text
  3.4.  The zk-regex audit fixes are not incorporated
  Target  invitation_code_regex.circom
  Category  Coding Mistakes  Severity  High
  Likelihood  High  Impact  High
  Description
  The regex circuits in ether-email-auth are derived from the ZK Regex library, which automatically
  generates a corresponding circom circuit. The regex library was previously audited by a different
  audit firm, and this audit assumes that the ZK Regex library is correct.
  However, we note that the version of ZK Regex library used to generate the circom circuits in ether-
  email-auth is not up to date, especially with the previous audit fixes.
  For example, in ether-email-auth, the is_consecutive signal is initialized to 1.
  signal is_consecutive[msg_bytes+1][3];
  is_consecutive[msg_bytes][2] <== 1;
  However, this is incorrect, and this was fixed in the ZK Regex audit, as shown in this commit ↗.
  signal is_consecutive[msg_bytes+1][3];
```

<sub>Source: Zellic zk-email audit PDF (docs.zk.email), pdftotext -layout lines 676-703 of `results/raw/groundtruth/sources/zkemail-zellic.txt` (sha256 ded98197ede9…)</sub>

## 2. Vulnerable vs fixed code

#### `packages/circuits/src/regexes/invitation_code_with_prefix_regex.circom`

Large file: showing the first 42 of 43 unified-diff lines between the pinned revisions.

```diff
--- vulnerable@b5694a9e
+++ fixed@9deaf804
@@ -161,11 +161,11 @@
 	}
 
-	component final_state_result = MultiOR(num_bytes+1);
+	component is_accepted = MultiOR(num_bytes+1);
 	for (var i = 0; i <= num_bytes; i++) {
-		final_state_result.in[i] <== states[i][7];
+		is_accepted.in[i] <== states[i][7];
 	}
-	out <== final_state_result.out;
+	out <== is_accepted.out;
 	signal is_consecutive[msg_bytes+1][3];
-	is_consecutive[msg_bytes][2] <== 1;
+	is_consecutive[msg_bytes][2] <== 0;
 	for (var i = 0; i < msg_bytes; i++) {
 		is_consecutive[msg_bytes-1-i][0] <== states[num_bytes-i][7] * (1 - is_consecutive[msg_bytes-i][2]) + is_consecutive[msg_bytes-i][2];
@@ -174,4 +174,5 @@
 	}
 	// substrings calculated: [{(0, 1), (0, 2), (1, 3), (2, 1), (3, 4), (4, 5), (5, 6), (5, 7), (6, 7), (7, 7)}]
+	signal prev_states0[10][msg_bytes];
 	signal is_substr0[msg_bytes];
 	signal is_reveal0[msg_bytes];
@@ -179,6 +180,16 @@
 	for (var i = 0; i < msg_bytes; i++) {
 		 // the 0-th substring transitions: [(0, 1), (0, 2), (1, 3), (2, 1), (3, 4), (4, 5), (5, 6), (5, 7), (6, 7), (7, 7)]
-		is_substr0[i] <== MultiOR(10)([states[i+1][0] * states[i+2][1], states[i+1][0] * states[i+2][2], states[i+1][1] * states[i+2][3], states[i+1][2] * states[i+2][1], states[i+1][3] * states[i+2][4], states[i+1][4] * states[i+2][5], states[i+1][5] * states[i+2][6], states[i+1][5] * states[i+2][7], states[i+1][6] * states[i+2][7], states[i+1][7] * states[i+2][7]]);
-		is_reveal0[i] <== is_substr0[i] * is_consecutive[i][2];
+		prev_states0[0][i] <== from_zero_enabled[i+1] * states[i+1][0];
+		prev_states0[1][i] <== from_zero_enabled[i+1] * states[i+1][0];
+		prev_states0[2][i] <== (1 - from_zero_enabled[i+1]) * states[i+1][1];
+		prev_states0[3][i] <== (1 - from_zero_enabled[i+1]) * states[i+1][2];
+		prev_states0[4][i] <== (1 - from_zero_enabled[i+1]) * states[i+1][3];
+		prev_states0[5][i] <== (1 - from_zero_enabled[i+1]) * states[i+1][4];
+		prev_states0[6][i] <== (1 - from_zero_enabled[i+1]) * states[i+1][5];
+		prev_states0[7][i] <== (1 - from_zero_enabled[i+1]) * states[i+1][5];
+		prev_states0[8][i] <== (1 - from_zero_enabled[i+1]) * states[i+1][6];
+		prev_states0[9][i] <== (1 - from_zero_enabled[i+1]) * states[i+1][7];
+		is_substr0[i] <== MultiOR(10)([prev_states0[0][i] * states[i+2][1], prev_states0[1][i] * states[i+2][2], prev_states0[2][i] * states[i+2][3], prev_states0[3][i] * states[i+2][1], prev_states0[4][i] * states[i+2][4], prev_states0[5][i] * states[i+2][5], prev_states0[6][i] * states[i+2][6], prev_states0[7][i] * states[i+2][7], prev_states0[8][i] * states[i+2][7], prev_states0[9][i] * states[i+2][7]]);
+		is_reveal0[i] <== MultiAND(3)([out, is_substr0[i], is_consecutive[i][2]]);
 		reveal0[i] <== in[i+1] * is_reveal0[i];
```

#### `packages/circuits/src/regexes/invitation_code_regex.circom`

<table><tr><th>Vulnerable @ <code>b5694a9e0e</code>, lines 1–40</th><th>Fixed @ <code>9deaf80435</code>, lines 1–40 — <b>identical to vulnerable excerpt</b></th></tr>
<tr><td valign="top"><pre>   1  pragma circom 2.1.5;
   2  
   3  include &quot;@zk-email/zk-regex-circom/circuits/regex_helpers.circom&quot;;
   4  
   5  // regex: ( )?(c|C)ode( )?(0|1|2|3|4|5|6|7|8|9|a|b|c|d|e|f)+
   6  template InvitationCodeRegex(msg_bytes) {
   7  	signal input msg[msg_bytes];
   8  	signal output out;
   9  
  10  	var num_bytes = msg_bytes+1;
  11  	signal in[num_bytes];
  12  	in[0]&lt;==255;
  13  	for (var i = 0; i &lt; msg_bytes; i++) {
  14  		in[i+1] &lt;== msg[i];
  15  	}
  16  
  17  	component eq[19][num_bytes];
  18  	component and[10][num_bytes];
  19  	component multi_or[3][num_bytes];
  20  	signal states[num_bytes+1][8];
  21  	signal states_tmp[num_bytes+1][8];
  22  	signal from_zero_enabled[num_bytes+1];
  23  	from_zero_enabled[num_bytes] &lt;== 0;
  24  	component state_changed[num_bytes];
  25  
  26  	for (var i = 1; i &lt; 8; i++) {
  27  		states[0][i] &lt;== 0;
  28  	}
  29  
  30  	for (var i = 0; i &lt; num_bytes; i++) {
  31  		state_changed[i] = MultiOR(7);
  32  		states[i][0] &lt;== 1;
  33  		eq[0][i] = IsEqual();
  34  		eq[0][i].in[0] &lt;== in[i];
  35  		eq[0][i].in[1] &lt;== 67;
  36  		eq[1][i] = IsEqual();
  37  		eq[1][i].in[0] &lt;== in[i];
  38  		eq[1][i].in[1] &lt;== 99;
  39  		and[0][i] = AND();
  40  		and[0][i].a &lt;== states[i][0];</pre></td><td valign="top"><pre>   1  pragma circom 2.1.5;
   2  
   3  include &quot;@zk-email/zk-regex-circom/circuits/regex_helpers.circom&quot;;
   4  
   5  // regex: ( )?(c|C)ode( )?(0|1|2|3|4|5|6|7|8|9|a|b|c|d|e|f)+
   6  template InvitationCodeRegex(msg_bytes) {
   7  	signal input msg[msg_bytes];
   8  	signal output out;
   9  
  10  	var num_bytes = msg_bytes+1;
  11  	signal in[num_bytes];
  12  	in[0]&lt;==255;
  13  	for (var i = 0; i &lt; msg_bytes; i++) {
  14  		in[i+1] &lt;== msg[i];
  15  	}
  16  
  17  	component eq[19][num_bytes];
  18  	component and[10][num_bytes];
  19  	component multi_or[3][num_bytes];
  20  	signal states[num_bytes+1][8];
  21  	signal states_tmp[num_bytes+1][8];
  22  	signal from_zero_enabled[num_bytes+1];
  23  	from_zero_enabled[num_bytes] &lt;== 0;
  24  	component state_changed[num_bytes];
  25  
  26  	for (var i = 1; i &lt; 8; i++) {
  27  		states[0][i] &lt;== 0;
  28  	}
  29  
  30  	for (var i = 0; i &lt; num_bytes; i++) {
  31  		state_changed[i] = MultiOR(7);
  32  		states[i][0] &lt;== 1;
  33  		eq[0][i] = IsEqual();
  34  		eq[0][i].in[0] &lt;== in[i];
  35  		eq[0][i].in[1] &lt;== 67;
  36  		eq[1][i] = IsEqual();
  37  		eq[1][i].in[0] &lt;== in[i];
  38  		eq[1][i].in[1] &lt;== 99;
  39  		and[0][i] = AND();
  40  		and[0][i].a &lt;== states[i][0];</pre></td></tr></table>


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** indirect - regex reveal determines the masked subject (public)
- **Consumer consequence:** possible - incorrect masking of the subject
- **Fix locus:** circuit-internal (regenerated regex circuits)
- **P1–P5 mappable:** no
- **Research-contract scope:** in scope under s5.3 only if an incorrect mask changes an authorised command
- **Relational class:** CIRCUIT-ONLY — stale generated regex circuit
- **Proposed expected pattern:** `NONE`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^packages/circuits/src/regexes/invitation_code(_with_prefix)?_regex\.circom(:\d+)?$`
- **Location basis:** is_consecutive initialisation in invitation_code_with_prefix_regex.circom
- **Concerns:**
  - v1 classified this as strict integration; by the C1 criteria it would be demoted. C1 was pre-registered for the 7 promoted rows only, so this is advisory.

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
