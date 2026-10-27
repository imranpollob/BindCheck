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

## D1P-18 hardening

The same route-A prototype now fails closed. An unresolved declaration,
unmodeled external call, unsupported member/index operation, unmodeled library
call or storage/event effect, and every unsupported AST/operator form raises a
located `UNSUPPORTED_<kind>` rejection. Only the exact verifier declaration in
the model table may remain relational.

`library_effect_models.v1.json` is the shared, versioned declaration model. Its
keys combine source path, contract, signature, and pinned library version for
ERC-20 mint, burn, transfer/update, balance/supply writes, and `Transfer`
events. `case_specific_entries` is false; adding a WarpToad-specific entry would
be manual input and is outside the automatic route.

`source_mutation_tests.py` recompiles three changed `WarpToadCore.sol` sources
with the archived standard-JSON compiler input and the pinned solc 0.8.29
package, then runs the unchanged extractor. `semantic_controls.py` concretely
checks checked arithmetic, sequential aliased storage stores, zero-value effect
retention, and rollback, and emits the path-family/execution coverage matrix.
The compiler transport helper `compile_standard_json.js` only avoids truncated
CLI stdout; it invokes the same pinned compiler package and settings.

Run both regression suites with:

```sh
python3 -m unittest -v prototypes/d1p16/test_d1p16.py prototypes/d1p16/test_d1p18.py
```
