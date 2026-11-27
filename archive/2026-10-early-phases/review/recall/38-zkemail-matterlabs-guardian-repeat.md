# Recall card 38 — zkemail-matterlabs-guardian-repeat

`zkemail-matterlabs-guardian-repeat`

| Field | Value |
|---|---|
| Repository | zkemail/email-recovery |
| DSL (ledger) | Circom/Solidity or generated Groth16 verifier |
| Ledger pattern / impact | nullifier replay scope fails to enforce one guardian per recovery / proof-to-execution mismatch |
| Class v1 → v2 | `integration` → `integration` |
| Vulnerable → fixed | [041a882677](https://github.com/zkemail/email-recovery/tree/041a882677622b580693d2a4f08d6661bf77ea89) → [c866ecb3dd](https://github.com/zkemail/email-recovery/tree/c866ecb3dd326fe17850c61a9e38eb3db8a45695) |
| Exposure | not exposed by C2; RELATED DEV repos in same org: zkemail/proof-of-twitter |
| L4 proposal | **KEEP (v1 strict; not subject to C1)** |

## 1. Source report (verbatim)

```text
  5. Malicious guardians can recover an account by
  bypassing the threshold mechanism
Severity: High  Status: Resolved
Based on an email from a guardian address, a relayer can call the
EmailAccountRecovery.handleRecovery() external function, providing a ZK-proof and
other parameters inside the EmailAuthMsg struct to kick off the recovery process.
[…]
Currently, the EmailRecoveryManager doesn't prevent a scenario where the same guardian
sends multiple account recovery emails. Consequently, recoveryRequest.currentWeight
will be incremented multiple times by the same guardian in this case. Consider the following
attack scenario. A wallet owner has assigned multiple guardians with varying weights, and one
with the lowest weight is hacked. The attacker can send a few recovery emails from the
compromised email account to recover the wallet-account to an attacker-controlled public key,
bypassing the threshold mechanism with multiple guardians. The EmailRecoveryManager
contract includes protection against replay attacks for the same email using email nullifiers,
representing a Poseidon hash value of the message signature. However, this protection does
not address the scenario described above since the attacker can send the same command
within the body but a different subject, resulting in a different DKIM-signature and email nullifier.
Recommendation:
We recommend implementing a check to ensure that a specific guardian has already sent a
recovery email for the current recovery request. This will help avoid using multiple emails for the
same recovery request from a single guardian.
```

<sub>Source: Matter Labs zk-email review PDF (docs.zk.email), pdftotext -layout lines 540-545, 557-573 of `results/raw/groundtruth/sources/matterlabs-zkemail.txt` (sha256 e6aeb75e9b2a…)</sub>

## 2. Vulnerable vs fixed code

#### `src/EmailRecoveryManager.sol`

Large file: showing the first 42 of 415 unified-diff lines between the pinned revisions.

```diff
--- vulnerable@041a8826
+++ fixed@c866ecb3
@@ -4,4 +4,6 @@
 import { EmailAccountRecovery } from
     "@zk-email/ether-email-auth-contracts/src/EmailAccountRecovery.sol";
+import { EnumerableSet } from "@openzeppelin/contracts/utils/structs/EnumerableSet.sol";
+import { Ownable } from "@openzeppelin/contracts/access/Ownable.sol";
 import { IEmailRecoveryManager } from "./interfaces/IEmailRecoveryManager.sol";
 import { IEmailRecoveryCommandHandler } from "./interfaces/IEmailRecoveryCommandHandler.sol";
@@ -16,17 +18,18 @@
  *
  * This contract defines an implementation for email-based recovery. It is designed to
- * provide the core logic for email based account recovery that can be used across different modular
- * account implementations.
+ * provide the core logic for email-based account recovery that can be used across different
+ * account implementations. The core logic is agnostic to the account implementation and could be
+ * implemented as part of a smart account module, or on a smart account itself.
  *
- * EmailRecoveryManager relies on a dedicated recovery module to execute a recovery attempt. This
- * (EmailRecoveryManager) contract defines "what a valid recovery attempt is for an account", and
- * the recovery module defines "how that recovery attempt is executed on the account". A
- * specific email command handler is also accociated with a recovery manager. A command handler
- * defines and validates the recovery email commands. Developers can write their own command
- * handlers to make specifc commands for recovering modules
+ * EmailRecoveryManager defines "what a valid recovery attempt is for an account", and leaves
+ * defining "how that recovery attempt is executed on the account" to contracts implementing
+ * EmailRecoveryManager. A specific email command handler is also accociated with a recovery
+ * manager. A command handler defines and validates the recovery email commands. Developers can
+ * write their own command handlers to make specifc commands
  */
 abstract contract EmailRecoveryManager is
     EmailAccountRecovery,
     GuardianManager,
+    Ownable,
     IEmailRecoveryManager
 {
@@ -34,4 +37,5 @@
     /*                    CONSTANTS & STORAGE                     */
     /*.•°:°.´+˚.*°.˚:*.´•*.+°.•°:´*.´•*.•°.•°:°.´:•˚°.*°.˚:*.´+°.•*/
+    using EnumerableSet for EnumerableSet.AddressSet;
 
     /**
```


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** yes - email nullifier is a public input; guardian identity is derived from it
- **Consumer consequence:** yes - one guardian's weight counted multiple times, bypassing the threshold
- **Fix locus:** consumer (guardianVoted set + GuardianAlreadyVoted)
- **P1–P5 mappable:** partial - P3 (replay scope: key is per-email nullifier, policy requires per-guardian uniqueness)
- **Research-contract scope:** in scope
- **Relational class:** CONSUMER-ONLY — per-guardian uniqueness policy in the recovery manager
- **Proposed expected pattern:** `P3`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^src/EmailRecoveryManager\.sol(:\d+)?$`
- **Location basis:** processRecovery at vulnerable EmailRecoveryManager.sol:316; currentWeight += at :361
- **Concerns:**
  - Ledger fixed commit c866ecb3 is 'Downgrade modulekit (#62)' and does not itself touch recovery logic; the revision nevertheless contains hasGuardianVoted/GuardianAlreadyVoted (fixed EmailRecoveryManager.sol:184, :440-441, :473) absent at the vulnerable revision. Pair is usable; the fix commit itself is not identified.

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
