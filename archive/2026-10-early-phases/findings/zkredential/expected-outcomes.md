# ZKredential frozen expected outcomes

Frozen before authoring the prospective harness or repair. Source: `ethpanda-org/ETHShanghai-2025@23917814522bac494150c7e99a123aa15a448155`, `projects/ZKredential`.

| Trial | Expected local result | Required observation |
|---|---|---|
| Original gateway, proof whose public wallet is account A, transaction from account B | `VIOLATION` under the documented wallet-specific compliance interpretation | Real verifier accepts; unchanged gateway commits a mint to B, with an amount selected in calldata; A receives no mint. |
| Repaired gateway, same proof and transaction from B | Transaction reverts | No token balance or proof-use state change commits. |
| Repaired gateway, same proof and transaction from A | Transaction succeeds | Real verifier accepts; A receives the tested amount and proof is consumed. |

The proposed narrow repair checks the proof's public wallet against the caller. It cannot by itself authorize the mint amount: the circuit has no amount signal or issuance entitlement. Unless a separate amount policy and corresponding binding are established, the full mint-authorization repair remains `UNKNOWN`, even if these tests pass. The wallet policy is an interpretation of the README and source, not an independent author confirmation.
