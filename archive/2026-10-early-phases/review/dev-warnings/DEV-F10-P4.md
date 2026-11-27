# DEV-F10 / P4 — 0xFable

**Frozen result:** `VIOLATION / GAMMA_EQUALS_DELTA_SOURCE_KEY` ([ledger](../../reports/freeze2/dev-ledger.csv); [raw](</Users/imranpollob/Coding/bc/bindcheck-zk/results/raw/coverage/after-20261109T165844Z-58315/DEV-F10--result.json>)). **Revision:** `f4aece4c513161e78d3dd78579687133cfd4f22a`. Source root: `/Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev/DEV-F10--0xFableOrg__0xFable--f4aece4c5131/`.

- **Verifier reality:** `packages/contracts/src/verifiers/DrawVerifier.sol:36-43,80`, `DrawHandVerifier.sol:36-43,77`, and `PlayVerifier.sol:36-43,74` are generated pairing verifiers with gamma = delta. The raw triple list includes cross-matched circuits; use each verifier's actual arity and call site, not those circuit pairings.
- **Consumer wiring:** `packages/contracts/src/Game.sol:10-12,214-227` imports/stores all three. `src/deploy/Deploy.s.sol:9-11,51-56` constructs them and passes them to `Game`. Actual calls are `Game.sol:499-503` (DrawHand), `649-653` (Draw), and `709-713` (Play). `checkProofs` can be disabled; the deploy script defaults it to `true` at line 54.
- **Policy:** The `Game.sol` branches explicitly revert on `InvalidProof` when `checkProofs` is true (`:499-503,649-653,709-713`). Accepting arbitrary proof points conflicts with that branch's intent; the configurable bypass is a separate policy choice.
- **P4 setup:** `packages/circuits/Makefile:201-203` runs `snarkjs groth16 setup` straight to `out/%.zkey`; `:211-213` exports that same key as Solidity. No `zkey contribute` rule appears in the inspected Makefile. Thus its own generation path would produce an uncontributed key.

**AI opinion:** `TRUE` for the three correctly wired source verifiers, conditional on `checkProofs=true`; E3/E4 and any live deployment remain MISSING. **Human label:** ____  **Human reviewer/date:** ____  **Reason or correction:** ____
