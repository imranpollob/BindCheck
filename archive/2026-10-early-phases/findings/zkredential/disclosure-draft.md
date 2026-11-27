# Private disclosure draft — ZKredential

**Status: DRAFT; NOT SENT.** Advisor approval, policy adjudication, recipient selection, and any actual disclosure are outside this lane.

## Summary and impact

At `ethpanda-org/ETHShanghai-2025@23917814522bac494150c7e99a123aa15a448155`, `ComplianceGateway.verifyAndExecute` accepts a genuine PropertyFy proof whose public wallet differs from the caller, then mints a caller-supplied token quantity to the caller. In our owned local setup, the gateway had token mint authority and a synthetic proof led to a committed token balance increase. This can violate a wallet-specific, issuer-approved issuance policy. No deployed gateway/token pair or financial exposure has been established. The circuit also lacks issuer attestation for the supplied KYC attributes.

## Reproduction

From the impact lane, run `./findings/zkredential/run.sh`. The script archives the pinned project subtree, installs pinned dependencies, compiles the PropertyFy circuit, checks R1CS/zkey correspondence, generates and verifies a real Groth16 proof, and exercises the unmodified gateway and token on Hardhat's local EVM. The [report](../../reports/impact/REPORT.md) and ignored `results/raw/impact/zkredential-impact-20261109T053739Z-34171/` hold commands, exits, artifact hashes, proof, and pre/post-state assertions. No public chain is accessed.

## Proposed fix

Require the mint recipient to match the relevant proof public wallet and require a separately issuer-approved, consumed amount allowance. The included prospective repair tests reject the mismatched caller and an excessive amount while permitting an approved mint. A complete production fix additionally needs authenticated issuer data and policy-specific public-signal mappings across all supported platforms; this draft does not assert those are solved.
