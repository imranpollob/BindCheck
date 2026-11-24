# Pass 2 (code-checked) to-do: 16 newly pinned TEST items

For each item, write a row in `labeling-a/code-review-rater-A.csv` following the same procedure as before (PROTOCOL.md two-pass). Pass 1 is already final. Do not share these with the build lane.

| item | Pass 1 binding | family | finding | repo | vuln | fix |
|---|---|---|---|---|---|---|
| L057 | Y | Hinkal | Missing Domain Separation Enables Conditional Cross-Fork Pro | Hinkal-Protocol/Hinkal-Contracts-Circuits | 306b08253d | 7b8696f86c |
| L089 | Y | RISC Zero / Boundless | On-chain conversion to field elements is incorrect | boundless-xyz/kailua | 6e2ce8f35b | c1aa054e8f |
| L096 | N | RISC Zero / Boundless | Commitment Should Include REVM Version | risc0/risc0-ethereum | 649289a20b |  |
| L107 | N | Hinkal | Emporium Wallet-Mode Signature Authorizes the Operations but | Hinkal-Protocol/Hinkal-Contracts-Circuits | 306b08253d | 2985a07432 |
| L108 | N | Hinkal | EdDSA Verification Does Not Validate Spending Key and Signat | Hinkal-Protocol/Hinkal-Contracts-Circuits | 306b08253d | 62339e220f |
| L119 | Y | RISC Zero / Boundless | Not all fields included in rollup hash | boundless-xyz/kailua | 6e2ce8f35b | c1aa054e8f |
| L144 | N | Hinkal | A Zero `signerAddress` Skips Both the Signature Check and th | Hinkal-Protocol/Hinkal-Contracts-Circuits | 306b08253d | 33810266db |
| L149 | Y | RISC Zero / Boundless | Next Sync Committee Might Be Arbitrarily Set | risc0/r0vm-helios | 87796bbdcc |  |
| L152 | N | RISC Zero / Boundless | Commitment Should Include Execution Environment | risc0/risc0-ethereum | 649289a20b | 7b704888ce |
| L168 | N | RISC Zero / Boundless | No domain separation between client and prover | boundless-xyz/boundless | f0e5fc49c9 | 740adfbc01 |
| L170 | N | Hinkal | Admin Can Configure Security-Critical Changes without Timelo | Hinkal-Protocol/Hinkal-Contracts-Circuits | 306b08253d | ef86e0b3df |
| L172 | Y | RISC Zero / Boundless | Lack of Assurance on Verified Chain Identity | risc0/r0vm-helios | 87796bbdcc | 667f6d5c3a |
| L179 | Y | RISC Zero / Boundless | Incomplete L1 config hash preimage may lead to incorrect | boundless-xyz/kailua | 2414297a5f |  |
| L180 | Y | RISC Zero / Boundless | BoundlessMarket allows delivery of bogus fulfillments | boundless-xyz/boundless | f0e5fc49c9 | fd501d0120 |
| L193 | Y | RISC Zero / Boundless | The BoundlessMarket does not validate RequestIds during | boundless-xyz/boundless | f0e5fc49c9 | fd501d0120 |
| L200 | N | Hinkal | Arbitrary Emporium Calls Allow Theft of Untracked Assets | Hinkal-Protocol/Hinkal-Contracts-Circuits | 306b08253d |  |
