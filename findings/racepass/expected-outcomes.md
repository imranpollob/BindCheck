# RacePass frozen expected outcomes

Frozen before authoring the prospective harness or repair. Source: `Servesh21/RacePass@abd54b5c541ac9d26f938a6bdbd78545526249e5`.

| Trial | Expected local result | Required observation |
|---|---|---|
| Original EventPass, one real age/KYC proof pair reused with caller-chosen credential hashes and recipients | `VIOLATION` under the documented holder/credential interpretation | Both real verifiers accept; unchanged consumer commits two distinct pass mints and linked credential values. |
| Repaired EventPass, proof pair with a `credHash` different from the KYC public commitment | Transaction reverts | No pass mint or state change commits. |
| Repaired EventPass, same proof pair with its KYC public commitment as `credHash`, then replay | First transaction succeeds; replay reverts | Genuine eligible mint remains possible; only one pass is minted for the commitment. |

The proposed narrow repair checks the linked credential against the KYC public commitment and records its use. This does not establish recipient ownership, issuer approval, age/KYC linkage, or real revocation semantics. Those parts of the broader credential policy remain `UNKNOWN` absent a stronger producer/registry design. The demo's intent is ambiguous and no author confirmation is assumed.
