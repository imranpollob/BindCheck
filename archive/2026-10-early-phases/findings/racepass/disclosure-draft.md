# Private disclosure draft — RacePass

**Status: DRAFT; NOT SENT.** Advisor approval, policy adjudication, recipient selection, and any actual disclosure are outside this lane.

## Summary and impact

At `Servesh21/RacePass@abd54b5c541ac9d26f938a6bdbd78545526249e5`, `EventPass.mintPass` accepts genuine age and KYC proofs while taking the stored/revocation-checked credential hash and pass recipient from independent caller arguments. Our owned local run reuses the same proof pair to mint distinct passes with different stored credential hashes and recipients. The project describes a simplified demo circuit; whether gifting or multiple passes are intended is unresolved, and no live funded pass instance has been established.

## Reproduction

From the impact lane, run `./findings/racepass/run.sh`. The script archives the pinned project, installs pinned dependencies, rebuilds age/KYC circuits, verifies R1CS/zkey correspondence, generates real Groth16 proofs, checks the committed verifiers, and executes the unmodified consumer on local Anvil. The [report](../../reports/impact/REPORT.md) and ignored `results/raw/impact/` hold the exact commands, exits, hashes, proof bytes, and state assertions. No public chain is accessed.

## Proposed fix

Bind the pass's stored credential to the KYC proof's public commitment, reject recipient substitution under a holder-only policy, and prevent repeated minting from one commitment within an event. The prospective repair test checks both rejection and one legitimate mint. A production design still needs trusted issuer attestation, linkage between age and KYC credentials, and a confirmed per-event gifting/multiplicity policy.
