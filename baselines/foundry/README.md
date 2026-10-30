# D1P-32 Foundry baselines

This directory tracks the exact shared WarpToad invariant harness used for
both D1P-32 Foundry arms. The generic arm scores only the G1/G2/G4/G5
invariants (verifier gating, single-use/rollback, and supply accounting); the
same-policy arm scores all seven invariants, adding the BindCheck policy for
amount/beneficiary and admitted-root binding. The relational verifier stub
checks the proof hash and all eleven public words and can reject; it is not an
always-successful verifier.

Frozen source hashes, as recorded in
[`docs/baselines/d1p-32-benchmark.md`](../../docs/baselines/d1p-32-benchmark.md):

- `test/WarpToadPolicy.t.sol` —
  `a33732d2262e8115bd4a1ef66cc5f075f5d015cfbe686df14c2fc58862670370`
- `foundry.toml` —
  `0a7b8b389511a9508a444d9eca7c106e13f1bae419f082b659d0b63b8e28363d`

The tracked `foundry.toml` is retained byte-for-byte, including the original
machine paths, because its published hash is evidence. Do not run it directly
on another checkout. The artifact driver writes a portable runtime copy with
the same semantic settings (`solc 0.8.29`, optimizer 200, 256 runs × 100
calls) and pinned Forge Std revision `77041d2c...`:

```sh
python3 scripts/artifact/reproduce.py baseline-table
```

The command stages the pinned WarpToad source and each WT-S consumer mutant,
runs the unchanged harness, checks each failing invariant against the frozen
D1P-32 classification, and writes ignored evidence under
`results/raw/artifact-reproduction/`.
