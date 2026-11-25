# DK-C02 (dark, P2, circuit-side)

| Field | Value |
|---|---|
| Operator | OP-C4 (see `OPERATORS.md`) |
| Pattern | P2 |
| Broken binding | the consumer passes its stored cap as a public input but the circuit no longer enforces a <= max_transfer |
| Unbound value | per-transfer policy cap `max_transfer` (stored `_caps.maxTransfer`) |
| GT consumer file | `DarkVault.sol` |
| GT function (where the unbound value enters the effect) | `transfer` |
| Edited file(s) | `baselines/dark/circuits/transfer/src/main.nr` |
| Related locations | DarkVault._transferInputs pi[20]; DarkVault.setCaps/tightenCaps |
| Attacker effect | confidential transfers above the configured cap are accepted (cap policy bypass) |
| Notes | Circuit-only edit. |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/dark/circuits/transfer/src/main.nr
-    assert(a <= as_u64(max_transfer), "a > max_transfer");
+++ edited
```
