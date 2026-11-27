# Synthetic control scenario notes

Three owned, local-only Foundry contracts (`src/Synthetic.sol`), each isolating
one binding behaviour, with a trivial stand-in verifier. Synthetic controls test
the consumer's binding logic and the oracle's judgement — not a real proof
system — so a mocked verifier is appropriate here and carries no security claim
(research contract §8; `AGENTS.md`). The real findings (`oracle/cases/`) use real
snarkjs proofs and unchanged verifiers.

`fixtures/cred-proof.json` / `cred-public.json` are a hand-written groth16-shaped
fixture. `pub[0]` is a canonical nullifier (`7`); `pub[1]` is the holder address
(`0x7099…`, Anvil account #1) as a `uint160`. The stand-in verifiers ignore the
`a/b/c` components.

Expected operator × consumer matrix (the oracle must reproduce it from the
manifests alone):

| Consumer | CALLER | FREE_ARG(recipient) | ALIAS-0 | ALIAS-1 | REPLAY | DOMAIN |
|---|---|---|---|---|---|---|
| BoundConsumer   | NOT | NOT | NOT | NOT | NOT | NOT |
| AliasConsumer   | NOT | NOT | **E4** | NOT | NOT | NOT |
| ReplayConsumer  | NOT | NOT | NOT | NOT | **E4** | NOT |
