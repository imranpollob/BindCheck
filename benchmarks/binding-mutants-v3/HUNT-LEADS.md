# Leads seen while building B3 (unverified; not part of B3)

These are unverified baseline observations from source read-throughs while screening hosts on 2026-11-25. No proof or exploit was built, no live system was touched, and nobody was contacted. Disclosure scope is the author's decision.

| Repo @ commit | Observation | Status |
|---|---|---|
| `fiit-ba/A-Resumable-Zero-Knowledge-Cross-Chain-Transfer-Protocol-with-Stateless-Coordination` @ `643cee8` | **KB-1.** None of the six RISC Zero guests (`zk-proofs/risc_zero/*/methods/guest/src/main.rs`) commits a Steel block commitment. No contract validates one: `Connector` recomputes only the event-field digest. The queried connector address is a private guest input. The README's trust model assumes chain consensus is enforced. | B3 host (excluded from the hunt pool); pre-registered KB-1 |
| `Zellic/zkerc20` @ `ff7b101` | **KB-2.** `MerkleTree._insert(uint256)` is `public` and inherited by `ZKERC20`. Anyone appears able to insert a commitment with no proof or deposit, then unlock against it. The README says it is unaudited and a proof of concept. | B3 host (excluded from the hunt pool); pre-registered KB-2 |
| `Laundry-Protocol/ethlaundry.xyz` @ `0fd30c0` | `contracts/crypto/verifiers/WithdrawalVerifier.sol` has γ = δ and IC1 = IC4 (a forgeable Groth16 key). `HomomorphicPoolV2` takes the Merkle root from the first 32 proof bytes. | rejected host |
| `usdsv/usd.sv` @ `3637a93` | `DualChainIntent.finalizeOnOrigin` takes `programVKey` from the caller | rejected host (BSL licence) |
| `masaun/ZK-energy-trading-platform-in-RISC0` @ `5a6745d` | `createSellOrder` records `msg.sender` as the seller, but the seller is not in the journal, so a copied seal plus journal can be front-run. The replay key is `(seal, nullifier)`. | rejected host |
