# WT-C03 — silo address made private (WarpToad circuit, M-DOM reuse)

- Family: WarpToad circuit (+ `nargo_hashing` lib). Operator:
  replace-public-with-private. Mechanism-derived: the unused `hashing`
  package and the developer warning (`main.nr:11-12`) show the mechanism
  existed in-tree. No claim it was ever deployed.
- Change: `aztec_merkle_verify` takes the silo address from the private
  `aztec_merkle_data.contract_address` instead of public word 5, which
  stays declared in the ABI but feeds no constraint.
- Ground truth: O1/DOM-AZ. Expected effect: a note siloed under a foreign
  contract verifies against the configured instance; the pinned circuit
  rejects the same semantic input ("Cannot satisfy constraint").
- Reachability: honest EVM-path `nargo execute` does NOT cover the Aztec
  branch; the stale honest Prover.toml lacks the new struct field, so
  plain execute is expected to fail at witness level. Reachability is
  established by the D1P-15 precedent (honest + foreign real proofs,
  E4 on the mutant with its own key). This mutant reuses that evidence;
  it does not re-prove.
- Non-equivalence: distinct artifact, VK, and verifier from pinned.
