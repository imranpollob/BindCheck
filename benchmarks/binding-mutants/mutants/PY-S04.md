# PY-S04 — dead kind-4 path activated as burn (Payy consumer)

- Family: Payy consumer. Operator: activate dead path.
- Change: message kind 4 (previously `revert("Invalid message kind")`)
  dispatches to `verifyBurn`.
- Ground truth: activation-extent break. Expected effect: kind-4 records
  (swaps per the circuit's own accounting) settle as burns with a
  5-word stride that misaligns subsequent records.
- Reachability (cheap): solc compile + diff audit.
