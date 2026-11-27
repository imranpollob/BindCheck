# Recall card 14 — data-are-not-fully-verified-during-state-update

`circom/privacy-scaling-explorations/maci/hashcloak_data_are_not_fully_verified_during_state_update`

| Field | Value |
|---|---|
| Repository | privacy-scaling-explorations/maci |
| DSL (ledger) | Circom |
| Ledger pattern / impact | Misimplementation of a Specification / Soundness |
| Class v1 → v2 | `integration-or-execution-semantics` → `integration` (**promoted**) |
| Vulnerable → fixed | [2db5f625b6](https://github.com/privacy-scaling-explorations/maci/tree/2db5f625b67a6b810bd851950d7a42c26189088b) → [6df6a4054d](https://github.com/privacy-scaling-explorations/maci/tree/6df6a4054da926b07f35c5befab4f1f8af33dcc6) |
| Exposure | **EXPOSED** — DEV row in source-corpus-v2 (privacy-scaling-explorations/maci) |
| L4 proposal | **DEMOTE** |

## 1. Source report (verbatim)

> In `ResultCommitmentVerifier` (tallyVotes.circom), the initial tally commitment is not verified for the first batch. The circuit computes `hz <== iz.out * currentTallyCommitmentHasher.hash` where `iz.out` is 0 when `isFirstBatch == 1`, making `hz = 0`. The constraint `hz === currentTallyCommitment` then only forces `currentTallyCommitment` to be zero without verifying it against the actual computed tally hash. A malicious coordinator can start with an arbitrary tally state for the first batch, compromising all subsequent tally results.
>
> zkbugs Location:
> - Path: circuits/circom/tallyVotes.circom
>   - Function: ResultCommitmentVerifier
>   - Line: 258-273

<sub>Source: zkbugs README @ ee4eb3ab (`results/raw/groundtruth/work/zkbugs/hashcloak_data_are_not_fully_verified_during_state_update/README.md`, sha256 57753917e11f…); report: https://github.com/zksecurity/zkbugs/blob/main/reports/documents/hashcloak-maci.pdf</sub>

```text
Initial Conditions Are Not Properly Enforced
Type: Critical
Files affected: tallyVotes.circom
In ResultCommitmentVerifier, the verification of currentTallyCommitment is
skipped when processing the first batch, so as to allow accepting the value zero.
Hence, there should be other checks confirming that the current tally is actually the
initial tally in such a case, but this is absent from the current implementation.
Otherwise, a malicious coordinator could actually start with an arbitrary tally and thus
affect the tally result.
Impact: A malicious coordinator can affect the tally result, violating correct execution.
Suggestion: Add constraints to the current tally in case of the first batch. Another
option is to avoid skipping verification, and to initialize the tally commitment in Poll.sol
with a valid and expected commitment.
[…]
Status: This issue is has been partially resolved as of commit
e61c684e2b61350a8adf44686184a3fe1cd9d05a,
4bc217db24f573c1da5e24ad0caca596637c3dc8 and
4892ada0dc7bcc2f7710aea917e309f1553317c5 as only constraints have been added
to the tallyVotes circuit but not hasn’t been enforced in Poll.sol. Due to the contract
bytecode size limit, the development team has decided against also initializing the tally
commit in Poll.sol. As such, an issue has been opened to keep track of this for future
iterations of MACI.
```

<sub>Source: HashCloak MACI audit PDF (via zkbugs pinned copy), pdftotext -layout lines 94-108, 110-120 of `results/raw/groundtruth/sources/hashcloak-maci.txt` (sha256 bc1df660c54c…)</sub>

## 2. Vulnerable vs fixed code

#### `circuits/circom/tallyVotes.circom`

<table><tr><th>Vulnerable @ <code>2db5f625b6</code>, lines 255–273</th><th>Fixed @ <code>6df6a4054d</code>, lines 259–277 — <b>identical to vulnerable excerpt</b></th></tr>
<tr><td valign="top"><pre> 255  
 256      /*currentTallyCommitmentHasher.hash === currentTallyCommitment;*/
 257       // Check if the current tally commitment is correct only if this is not the first batch
 258       component iz = IsZero();
 259       iz.in &lt;== isFirstBatch;
 260       // iz.out is 1 if this is not the first batch
 261       // iz.out is 0 if this is the first batch
 262   
 263       // hz is 0 if this is the first batch
 264       // currentTallyCommitment should be 0 if this is the first batch
 265   
 266       // hz is 1 if this is not the first batch
 267       // currentTallyCommitment should not be 0 if this is the first batch
 268       signal hz;
 269       hz &lt;== iz.out * currentTallyCommitmentHasher.hash;
 270   
 271       hz === currentTallyCommitment;
 272  
 273      // Compute the root of the new results</pre></td><td valign="top"><pre> 259  
 260      /*currentTallyCommitmentHasher.hash === currentTallyCommitment;*/
 261       // Check if the current tally commitment is correct only if this is not the first batch
 262       component iz = IsZero();
 263       iz.in &lt;== isFirstBatch;
 264       // iz.out is 1 if this is not the first batch
 265       // iz.out is 0 if this is the first batch
 266   
 267       // hz is 0 if this is the first batch
 268       // currentTallyCommitment should be 0 if this is the first batch
 269   
 270       // hz is 1 if this is not the first batch
 271       // currentTallyCommitment should not be 0 if this is the first batch
 272       signal hz;
 273       hz &lt;== iz.out * currentTallyCommitmentHasher.hash;
 274   
 275       hz === currentTallyCommitment;
 276  
 277      // Compute the root of the new results</pre></td></tr></table>

#### `circuits/circom/processMessages.circom`

<table><tr><th>Vulnerable @ <code>2db5f625b6</code>, lines 30–36</th><th>Fixed @ <code>6df6a4054d</code>, lines 32–38</th></tr>
<tr><td valign="top"><pre>  30      var batchSize = TREE_ARITY ** msgBatchDepth;
  31  
  32      var MSG_LENGTH = 10;
  33      var PACKED_CMD_LENGTH = 4;
  34  
  35      var STATE_LEAF_LENGTH = 4;
  36      var BALLOT_LENGTH = 2;</pre></td><td valign="top"><pre>  32      var batchSize = TREE_ARITY ** msgBatchDepth;
  33  
  34      var MSG_LENGTH = 11;
  35      var PACKED_CMD_LENGTH = 4;
  36  
  37      var STATE_LEAF_LENGTH = 4;
  38      var BALLOT_LENGTH = 2;</pre></td></tr></table>


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** yes - currentTallyCommitment is one of the values hashed into the single public inputHash (tallyVotes.circom comment at vulnerable lines 35-40)
- **Consumer consequence:** yes - Poll/Tally contract accepts the coordinator's tally commitment; attacker is the privileged coordinator
- **Fix locus:** circuit-internal (tallyVotes ResultCommitmentVerifier); the contract-side option (initialise in Poll.sol) was explicitly not taken
- **P1–P5 mappable:** no - the defect is a missing in-circuit constraint on a hashed public value; no P1-P5 predicate expresses it
- **Research-contract scope:** in scope under contract s5.3 (underconstrained circuit with consumer consequence); attacker is a privileged coordinator
- **Relational class:** RELATIONAL-CANDIDATE — circuit skips the first-batch check on a value whose correct initial value lives in contract state; HashCloak offers a fix on either layer
- **Proposed expected pattern:** `NONE`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^circuits/circom/tallyVotes\.circom(:\d+)?$`
- **Location basis:** zkbugs Location: circuits/circom/tallyVotes.circom ResultCommitmentVerifier lines 258-273
- **Concerns:**
  - Case identity is ambiguous: zkbugs id/title 'Data are not fully verified during state update' and the ledger fixed commit 6df6a40 ('fix(processmessages.circom): data are not fully verified during state update', touches processMessages.circom + MaciState.ts only) describe a processMessages issue, while the zkbugs description, Location and the HashCloak PDF finding ('Initial Conditions Are Not Properly Enforced', tallyVotes.circom) describe the first-batch tally commitment.
  - The hz/isFirstBatch logic described by the source is still present at the ledger fixed commit (fixed tallyVotes.circom lines 263-273), so the pinned pair does not isolate the described defect.
  - HashCloak status: 'partially resolved' by e61c684e, 4bc217db, 4892ada0 (not the ledger fixed commit); Poll.sol initialisation deliberately not done.
  - Repository is a DEV repository (DEV-F03, privacy-scaling-explorations/maci) - EXPOSED.

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
