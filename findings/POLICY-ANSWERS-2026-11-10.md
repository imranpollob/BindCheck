# Human policy answers (author, 2026-11-10)

Recorded verbatim from the human author; these replace the AI-drafted policy status for the abstract and Table 11.

- **Z1 (ZKredential recipient): Yes.** The mint recipient must match the proof's public walletAddress. The registry checks this ("Address mismatch"), but the gateway doesn't. Its replay key covers the proof and public signals but not the caller. So anyone who submits an unused proof first can receive the mint, provided the token allows that mint. This assumes proofs are meant to be tied to one wallet, which the registry's check strongly suggests.
- **Z2 (ZKredential amount): Unknown.** Nothing in the proof covers the amount, and the caller chooses it. The gateway enforces no quantity limit, and any limits in the token itself are unknown. The intended issuance rule isn't in the source, so this stays conditional.
- **R1 (RacePass credential): Yes.** The credential checked for revocation and stored with the pass must be the KYC proof's credentialHash. The circuit's revocation check does nothing (revocationRoot × 0), and the caller supplies credHash independently. So the code allows a revocation bypass, but no test has demonstrated it.
- **R2 (RacePass recipient): Unresolved.** The source supports checking the holder's eligibility at mint, but it doesn't settle whether minting to another recipient, or gifting, is allowed. This is true whether or not the pass is soulbound.
- **R3 (RacePass one pass per credential): Unknown.** The source states no per-credential, per-event limit. The circuit has no nullifier or event ID, maxSupply caps only the total number of passes, and usedPasses only stops one pass being used twice at the gate.

## Consequences for the paper
- Confirmed flaws (policy = yes, E4 reproduced, repair rejects / legitimate run passes): ZKredential recipient binding (Z1); RacePass credential-hash binding (R1).
- Conditional only: ZKredential amount (Z2); RacePass recipient (R2) and one-pass-per-credential (R3). Table 11 "observed effect" must lead with the Z1/R1 effect, not the caller-chosen amount or the second recipient.
- Revocation bypass is a consequence the code permits; it is not demonstrated (the circuit's revocation check is inert).
