# RacePass policy and attacker model

Pinned source: [`Servesh21/RacePass@abd54b5c541ac9d26f938a6bdbd78545526249e5`](https://github.com/Servesh21/RacePass/tree/abd54b5c541ac9d26f938a6bdbd78545526249e5). This is a DEV case. This agent derived the provisional policy interpretation below from source; independent human/advisor review and project-author confirmation are **MISSING**. AI analysis is not independent annotation.

## Intended authorization

The [README](https://github.com/Servesh21/RacePass/blob/abd54b5c541ac9d26f938a6bdbd78545526249e5/README.md) says a user verifies with a trusted issuer, then uses a proof across events; it says "Verify the holder's credentials at mint time." The [EventPass source](https://github.com/Servesh21/RacePass/blob/abd54b5c541ac9d26f938a6bdbd78545526249e5/contracts/passes/EventPass.sol) describes `credHash` as the credential hash linked to the pass for revocation tracking, and says production `countryCode` comes from the KYC public signals. The [KYC circuit](https://github.com/Servesh21/RacePass/blob/abd54b5c541ac9d26f938a6bdbd78545526249e5/circuits/kyc_proof/kyc_check.circom) exposes `credentialHash`; `mintPass` verifies its proof but stores a different caller-provided `credHash` without checking equality. The [age circuit](https://github.com/Servesh21/RacePass/blob/abd54b5c541ac9d26f938a6bdbd78545526249e5/circuits/age_proof/age_check.circom) has a separate public commitment.

Our **conditional** pass policy is: the stored/revocation-checked credential is the one established by the KYC proof, the pass recipient is the presenting holder, and one credential cannot create more than one pass for a particular event. The first relationship has direct support from the code comment and README. The latter two are plausible access-control choices, but the source does not unambiguously prohibit gifting or multiple passes. The prospective repair enforces this stricter policy as a design proposal.

## Attacker capabilities and observation

Any public caller can choose the proof bytes, witness inputs, `credHash`, `countryCode`, `recipient`, and transaction ordering. The caller can see proof/public signals and pass ownership, linked credential, and validity. The experiment uses synthetic identities and owned Anvil accounts. It passes valid real proofs to the committed `AgeVerifier` and `KYCVerifier`; no mock verifier, privileged issuer role, or live chain is involved.

The KYC circuit is explicitly marked a simplified demo. It asserts `kycStatus == 1` from a prover-supplied witness and has a placeholder revocation-root operation; it does not verify a trusted issuer signature. The age and KYC circuits also do not establish that their distinct commitments describe one credential or that either commitment belongs to `recipient`. The linked credential equality repair and local replay guard do not solve those gaps.

## Classification and limits

The unchanged local consumer accepts one genuine proof pair for distinct caller-selected stored credentials and recipients. That is a `VIOLATION` under the stated conditional holder/credential policy, with an observable committed NFT effect. Whether repeated use or gifting is prohibited by the authors is `UNKNOWN`; the stronger replay/recipient interpretation must not be asserted as a confirmed vulnerability. The mismatched stored credential is a direct integrity concern for revocation, but real issuer-backed eligibility and deployed exposure are also `UNKNOWN`.
