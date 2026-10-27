# D1P-20 extracted consumer model

This namespace adapts the D1P-18 Solidity-AST relation to the existing joint
WarpToad solver interface without modifying the canonical D1P-14C/D1P-17
encoder.

- `joint_extracted.py` provides `consumer_model={MANUAL,EXTRACTED}`. `MANUAL`
  is the default and delegates byte-for-byte to the existing encoder.
- `EXTRACTED` serializes all 22 terminal paths, the 11 recovered verifier
  arguments, successful effects, nullifier writes, and rollback. Unsupported IR
  uses D1P-18's located `UnsupportedConstruct` rejections.
- `validate_d1p20.py` generates the raw evidence, performs two parse-only
  checks, validates five archived executions, and replays eight deterministic
  D1P-14D controls. It launches no primary solver query.
- `test_d1p20.py` checks default preservation, fail-closed translation,
  implementation/policy ordering, verifier bridges, rollback, T-ARITH, and the
  generated validation results.

Run from the lane root:

```sh
PYTHONPATH=src python3 prototypes/d1p20/validate_d1p20.py \
  --paper-root /Users/imranpollob/Coding/bc/bindcheck-d1-paper \
  --artifact /Users/imranpollob/Coding/bc/bindcheck-d1-paper/results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json \
  --relation results/raw/D1P-18/relation.json \
  --solver /Users/imranpollob/Coding/bc/BindCheck/tools/cvc5-1.4.2-gpl/bin/cvc5 \
  --output-dir results/raw/D1P-20

PYTHONPATH=src:prototypes/d1p20 python3 -m unittest \
  prototypes/d1p20/test_d1p20.py -v
```

The extracted implementation relation does not derive G1–G5 or any other
policy obligation. The callsite-to-role adapter remains a separately manifested
manual policy interpretation.

