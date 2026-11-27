# Recall card 39 — zkemail-matterlabs-cross-chain-replay

`zkemail-matterlabs-cross-chain-replay`

| Field | Value |
|---|---|
| Repository | zkemail/clave-email-recovery |
| DSL (ledger) | Circom/Solidity or generated Groth16 verifier |
| Ledger pattern / impact | missing chain/domain binding permits recovery replay / proof-to-execution mismatch |
| Class v1 → v2 | `integration` → `integration` |
| Vulnerable → fixed | [c84a165605](https://github.com/zkemail/clave-email-recovery/tree/c84a165605fe4774c73d99c9a5ae9ff4cbc45c71) → MISSING (not-publicly-pinned) |
| Exposure | not exposed by C2; RELATED DEV repos in same org: zkemail/proof-of-twitter |
| L4 proposal | **ADVISORY: NEEDS-POLICY-DECISION (acknowledged as intended)** |

## 1. Source report (verbatim)

```text
8. There might be a scenario where Clave EmailRecoveryModule contracts are deployed on
  different chains, and both EmailRecoveryModule and the wallet account have the same
  addresses on both chains. In this case, the acceptance and recovery requests can be
  replayed due to the absence of cross-chain replay protection.
  Status: Acknowledged.
  Status details: The client has chosen not to implement cross-chain replay protection for
  account recovery because the same public key should or can be enabled and revoked across
  all chains in the context of recovery. However, this does not prevent other applications using
  ether-email-auth from implementing replay protection by including a chain ID in the
  command, should they choose to do so.
```

<sub>Source: Matter Labs zk-email review PDF (docs.zk.email), pdftotext -layout lines 1003-1012 of `results/raw/groundtruth/sources/matterlabs-zkemail.txt` (sha256 e6aeb75e9b2a…)</sub>

## 2. Vulnerable vs fixed code

#### `contracts/EmailRecoveryModule.sol`

<table><tr><th>Vulnerable @ <code>c84a165605</code>, lines 45–105</th><th>Fixed: MISSING</th></tr>
<tr><td valign="top"><pre>  45              _factoryAddr
  46          )
  47      {}
  48  
  49      function init(bytes calldata initData) external override {
  50          if (isInited(msg.sender)) {
  51              revert Errors.ALREADY_INITED();
  52          }
  53  
  54          if (!IClaveAccount(msg.sender).isModule(address(this))) {
  55              revert Errors.MODULE_NOT_ADDED_CORRECTLY();
  56          }
  57  
  58          (
  59              address[] memory guardians,
  60              uint256[] memory weights,
  61              uint256 threshold,
  62              uint256 delay,
  63              uint256 expiry
  64          ) = abi.decode(
  65                  initData,
  66                  (address[], uint256[], uint256, uint256, uint256)
  67              );
  68  
  69          inited[msg.sender] = true;
  70  
  71          configureRecovery(guardians, weights, threshold, delay, expiry);
  72  
  73          emit Inited(msg.sender);
  74      }
  75  
  76      function disable() external override {
  77          inited[msg.sender] = false;
  78  
  79          deInitRecoveryModule();
  80  
  81          emit Disabled(msg.sender);
  82      }
  83  
  84      function isInited(address account) public view override returns (bool) {
  85          return inited[account];
  86      }
  87  
  88      function canStartRecoveryRequest(
  89          address account
  90      ) external view returns (bool) {
  91          GuardianConfig memory guardianConfig = getGuardianConfig(account);
  92  
  93          return guardianConfig.acceptedWeight &gt;= guardianConfig.threshold;
  94      }
  95  
  96      function recover(
  97          address account,
  98          bytes calldata newOwner
  99      ) internal override {
 100          IClaveAccount(account).resetOwners(newOwner);
 101  
 102          emit RecoveryExecuted(account, newOwner);
 103      }
 104  
 105      /// @inheritdoc IERC165</pre></td><td valign="top"><pre>MISSING (no resolved fixed commit)</pre></td></tr></table>


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** yes - recovery command lacks chain id
- **Consumer consequence:** conditional - only when module and account share addresses across chains
- **Fix locus:** none - Acknowledged; client chose not to implement
- **P1–P5 mappable:** yes - P2 (missing chain/domain binding)
- **Research-contract scope:** in scope only if the stated policy requires chain binding; the client states the opposite policy
- **Relational class:** CONSUMER-ONLY — command lacks chain id
- **Proposed expected pattern:** `P2`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^contracts/EmailRecoveryModule\.sol(:\d+)?$`
- **Location basis:** recover at vulnerable EmailRecoveryModule.sol:96
- **Concerns:**
  - No fix will exist; scoring requires a policy decision that contradicts the maintainer's documented policy.

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
