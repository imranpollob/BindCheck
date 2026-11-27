# ZKredential policy and attacker model

Pinned source: [`ethpanda-org/ETHShanghai-2025@23917814522bac494150c7e99a123aa15a448155`](https://github.com/ethpanda-org/ETHShanghai-2025/tree/23917814522bac494150c7e99a123aa15a448155/projects/ZKredential). This is a DEV case. This agent derived the provisional policy interpretation below from source; independent human/advisor review and project-author confirmation are **MISSING**. AI analysis is not independent annotation.

## Intended authorization

The [project README](https://github.com/ethpanda-org/ETHShanghai-2025/blob/23917814522bac494150c7e99a123aa15a448155/projects/ZKredential/README.md) describes a whitelist model in which an address enters the chain whitelist after KYC ("用户通过 KYC 后，地址加入链上白名单"). The [PropertyFy circuit](https://github.com/ethpanda-org/ETHShanghai-2025/blob/23917814522bac494150c7e99a123aa15a448155/projects/ZKredential/packages/zk-proof-server/circuits/propertyfy_circuit.circom) declares `walletAddress` public and outputs `isCompliant`. The [gateway](https://github.com/ethpanda-org/ETHShanghai-2025/blob/23917814522bac494150c7e99a123aa15a448155/projects/ZKredential/packages/zk-contracts/contracts/core/ComplianceGateway.sol) says `verifyAndExecute` verifies a proof and executes an action. It verifies compliance and spends the proof hash, then `mint(msg.sender, amount)`.

Our **conditional** mint policy is: a compliant proof's public wallet must match the mint recipient, and the issued amount must be separately authorized by an issuer or equivalent policy. The source provides no quantity entitlement, issuance schedule, or proof signal for the amount. Therefore the exact authorized amount cannot be inferred from this code. The prospective repair supplies an explicit owner-approved, consumed allowance; that is a design proposal, not a claim about the original project's intended amount policy.

## Attacker capabilities and observation

Any caller of the public gateway can choose proof bytes, witnesses, public signals, `platform`, `targetAction`, and `amount`; the attacker can observe public calldata and minted token balances. The local experiment uses synthetic KYC/asset values and owned Hardhat accounts. It does not require a privileged gateway role. The local token owner is deliberately transferred to the gateway, matching the necessary deployment configuration for the mint path.

The test's public `walletAddress` is an independently chosen address. Calling it a credential owner would overstate the proof: the circuit's `commitment` includes the public wallet, but the reviewed circuit does not verify an issuer signature or on-chain credential ownership. The current source also lets the prover supply KYC and asset witness values without attestation. Thus even a wallet equality guard alone cannot establish real-world KYC authorization.

## Classification and limits

The observed original execution is a local, real-proof proof-to-effect mismatch. It is a `VIOLATION` of the stated conditional wallet/issuer-allowance policy. Whether the application authors intended this gateway to issue value-bearing tokens, and whether any deployed gateway/token pair uses it, are `UNKNOWN`. The source is a hackathon project with an explicit demo flow; no financial-loss claim follows. The amount-allowance repair tests a defensible proposed policy, not a proof that every missing authorization is fixed.
