# DV-C01 (davinci, P1, circuit-side)

| Field | Value |
|---|---|
| Operator | OP-C1 (see `OPERATORS.md`) |
| Pattern | P1 |
| Broken binding | masked[i] no longer equals s_i + mask_i, so the stored shares are not tied to the Feldman-committed polynomial |
| Unbound value | masked share values (public masked[i]) stored for each recipient |
| GT consumer file | `CouncilManager.sol` |
| GT function (where the unbound value enters the effect) | `deal` |
| Edited file(s) | `baselines/davinci/circuits/deal.circom` |
| Related locations | circuits/deal.circom Deal (4); CouncilManager.deal pub[71+i], rec.masked |
| Attacker effect | CouncilManager.deal stores arbitrary masked shares in the recovery record while folding the dealer's commitments into the key; members recover wrong shares (decryption blocked or steered) |
| Notes | Circuit-only edit; DealVerifier unchanged. |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/davinci/circuits/deal.circom
-        masked[i] === u.out[i] * (s[i] + mask[i].out);
+++ edited
```
