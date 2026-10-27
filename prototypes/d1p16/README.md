# D1P-16 prototypes

`extract_relation.py` is a bounded symbolic interpreter over the archived solc
AST. It selects `WarpToadCore.mint`, follows declaration IDs into the formatter,
root predicates, OpenZeppelin `_mint`, and `_update`, and emits:

- ordered source and arithmetic guards;
- an uninterpreted `verify@target(proof, word0, ..., word10)` boundary;
- public-word expressions and source origins recovered by statically unrolling
  the formatter's fixed-size loops;
- ordered mint occurrences and functional-map storage updates; and
- one terminal record per success or revert family, with EVM transaction
  rollback applied to committed effects.

It does not contain the WarpToad fee equation or public-word list. Solidity
checked arithmetic, memory arrays, internal calls, mappings, `require`, `if`,
`revert`, and transaction rollback are interpreter semantics. The entry contract,
entry function, and immutable artifact pins are configuration for this bounded
experiment.

`compare_executions.py` concretizes the extracted IR against D1P-12R and D1P-14A
evidence. Actual verifier acceptance from each archived execution supplies the
truth value of the otherwise-uninterpreted producer boundary. D1P-14B supplies
only expected outcomes.

`probe_halmos.py` demonstrates that pinned Halmos retains path formulas and
storage-write records internally, then audits the stable CLI result schema and
unknown-call option. It is an interface probe, not a handwritten WarpToad model.

Run the regression suite with:

```sh
python3 -m unittest -v prototypes/d1p16/test_d1p16.py
```

The paths are intentionally pinned to the local read-only D1 paper worktree so
the test cannot silently switch consumer/compiler artifacts.
