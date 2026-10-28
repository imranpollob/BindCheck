# WT-C09 — public-word misorder (WarpToad circuit)

- Family: WarpToad circuit. Operator: misorder public words.
- Change: `amount` and `max_fee` swap positions in the `main` signature,
  so ABI word 2 is `max_fee` and word 8 is `amount`. Arity unchanged.
- Ground truth: field-mapping disagreement between producer ABI and the
  unchanged consumer's `_formatPublicInputs` order. Expected effect: the
  consumer's amount lands in the circuit's max_fee slot and vice versa;
  proofs built consumer-side fail, proofs built mutant-side mis-settle.
- Reachability (cheap): honest `nargo execute` is name-keyed, so it must
  still pass. Expected: pass. The break is at the ABI/decoder boundary,
  visible in the artifact ABI word order.
- Non-equivalence: artifact ABI differs from pinned.
