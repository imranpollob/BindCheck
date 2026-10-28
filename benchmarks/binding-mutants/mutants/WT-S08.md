# WT-S08 — public-word misorder (WarpToad consumer)

- Family: WarpToad consumer. Operator: misorder public words.
- Change: `_amount` and `_maxFee` swap slots in the `_formatPublicInputs`
  `uintInputs` array (words 2 and 8). Circuit and ABI unchanged.
- Ground truth: encoder/decoder field-mapping disagreement. Expected
  effect: the verifier sees max_fee where the circuit proved amount and
  vice versa; honest proofs fail and crafted calldata shifts value.
- Reachability (cheap): solc compile + diff audit.
