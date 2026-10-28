# PY-S05 — header skip removed (Payy consumer)

- Family: Payy consumer. Operator: offset/misorder.
- Change: `verifyAllMessages` starts at word 0 instead of `skipCount`,
  reading the 4 header words as message records.
- Ground truth: decoder offset disagreement. Expected effect: the first
  record is parsed from header material (VK hash / roots), shifting every
  subsequent dispatch.
- Reachability (cheap): solc compile + diff audit.
