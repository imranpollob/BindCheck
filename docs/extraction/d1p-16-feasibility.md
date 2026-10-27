# D1P-16 — consumer-extraction feasibility

## Decision

**Yes: the supported `WarpToadCore.mint` consumer relation can be recovered
without manually supplying its implementation equations. Recommend route A, a
bounded extension of the Solidity frontend.**

The route-A prototype reads the pinned solc AST, symbolically follows the actual
function bodies and referenced declarations, and emits guards, the verifier
boundary, public-word provenance, storage/token effects, events, and rollback.
It recovered 22 terminal path families (3 success, 19 revert). Concretization
against D1P-12R honest/replay and D1P-14A FC-POS/FC-NEG/zero-fee selected one
path per case and produced no disagreements.

Halmos was selected for route B because its Python implementation exposes path
conditions (`Path.conditions`, `Path.to_smt2`) and trace records for storage and
logs (`StorageWrite`, `EventLog`). Pinned Halmos installs and those internal APIs
work, but its supported CLI JSON exports test results rather than a reusable
path/post-state relation, and its former uninterpreted-unknown-call option is a
deprecated no-op. A route-B result would therefore require a custom driver or
Halmos patch plus a new verifier-boundary adapter and serializer. That is more
invasive than route A and was not needed after route A met the success criterion.

This decision is about extracting implementation relation `T_mint` only. It does
**not** derive AUTH/NONVAC or any other policy obligation. A separate,
reviewed policy-to-obligation step must consume the extracted relation.

## Scope and pins

The experiment used the read-only D1P-12R workspace, without recompilation:

| Item | Pin |
|---|---|
| WarpToad revision | `973e7d1e4b60d0d8a8ca299b0cabd9193b147ef8` |
| `WarpToadCore.sol` | SHA-256 `323a1cf26c7449f67cf277ff0a46c31e12f725c555f9fa165d5a60011e122c39` |
| solc | `0.8.29+commit.ab55807c` |
| settings | optimizer enabled, runs `1`; EVM `cancun` |
| archived build input | SHA-256 `ee1cc02abcaf96af8c8349cd02fa4bdc09db41e6ac8f7bc5b74434eb31a9068e` |
| archived compiler output | SHA-256 `708c3dc4dc1cc61a689936d77aaaa48ad3ee752fe83352014239f0ebedb8c07e` |

The extractor verifies all of these pins and the matching build-info/output ID
before interpreting the AST. It resolves calls by solc declaration ID across
`WarpToadCore.sol` and OpenZeppelin ERC20 5.6.1. No Payy or O1 target, live chain,
or solver campaign was used.

## Route A — AST symbolic extraction

### What is automatic

The prototype in `prototypes/d1p16/extract_relation.py` implements bounded
semantics for the constructs exercised by this entry point: identifiers and
state reads, fixed memory arrays, statically bounded loops, casts, checked and
unchecked arithmetic, mappings as functional arrays, `require`, branching,
internal calls, external-call boundaries, reverts, events, and transaction
rollback.

The prototype is configured with the pinned source/contract/entry function, but
does not contain WarpToad's fee equation or the public-input list. Specifically:

- the fee expression comes from the AST for the declaration of `_relayerFee`;
- the 11 words come from executing `_formatPublicInputs`, including unrolling
  its length-9 and length-2 loops;
- the nullifier write comes from the mapping assignment at line 158;
- mint and balance/supply effects come from following `_mint` into OpenZeppelin
  `_update`; and
- rollback is the EVM/Solidity transaction rule applied uniformly to every
  terminal revert, not a WarpToad-specific equation.

The only semantic label keyed to a function name is the high-level “mint
occurrence” record at calls to `_mint`; its underlying storage changes are still
derived by inlining the referenced implementation.

### Recovered verifier boundary

The verifier is represented as the uninterpreted relation
`R_verify(proof, word0, …, word10)`. It is a success guard and is never replaced
by `true`. The recovered words are:

| Word | Extracted expression | Origin |
|---:|---|---|
| 0 | `bytes32(_nullifier)` | calldata |
| 1 | `bytes32(block.chainid)` | environment |
| 2 | `bytes32(_amount)` | calldata |
| 3 | `bytes32(_gigaRoot)` | calldata |
| 4 | `bytes32(_localRoot)` | calldata |
| 5 | `bytes32(aztecWarptoadAddress)` | pre-state |
| 6 | `bytes32(_feeFactor)` | calldata |
| 7 | `bytes32(_priorityFee)` | calldata |
| 8 | `bytes32(_maxFee)` | calldata |
| 9 | `bytes32(uint256(uint160(bytes20(_relayer))))` | calldata address |
| 10 | `bytes32(uint256(uint160(bytes20(_recipient))))` | calldata address |

Concrete comparison supplies `R_verify=true` only because the archived evidence
records a real verifier acceptance for that exact proof/word vector. This does
not weaken the symbolic relation.

### Guards, success paths, and effects

Every successful path shares these guards, in source order:

1. `gigaRootHistory[_gigaRoot]`;
2. `localRootHistory[_localRoot]`;
3. `nullifiers[_nullifier] == false`;
4. `R_verify(_poof, recovered_words)`.

The nonzero-fee paths add checked `basefee + priorityFee`, checked multiplication
by `feeFactor`, `fee <= maxFee`, relayer selection (`address(1)` becomes
`msg.sender`), a nonzero fee beneficiary, checked `amount - fee`, a nonzero
recipient, and the two sequential OpenZeppelin total-supply overflow checks.
They commit, in order:

1. `nullifiers[_nullifier] = true`;
2. `_mint(selected_relayer, feeFactor * (block.basefee + priorityFee))`;
3. `_mint(_recipient, _amount - fee)`.

The zero-fee path adds `_recipient != address(0)` and the OpenZeppelin supply
overflow check, then commits the nullifier write and
`_mint(_recipient, _amount)`.

Inlining `_update` recovers sequential functional-map stores to `_balances`,
checked additions to `_totalSupply`, and `Transfer(address(0), beneficiary,
amount)` events. Functional-map stores preserve the case where fee beneficiary
and recipient alias; the two mint occurrences remain distinct.

The revert catalogue contains the three initial source guards, verifier failure,
the two fee-arithmetic panics, fee-cap failure, amount-underflow panic, invalid
ERC20 receivers, and per-mint total-supply overflow. Writes before a failing
guard remain visible as tentative trace effects, while every revert has empty
committed writes, mints, and events and restores the pre-state.

### Comparison with the manual summary

The extracted relation agrees with the manual summary on public-word order,
root/nullifier guards, fee formula and cap, relayer alias, the three source mint
callsites, primary nullifier key, balances/supply on success, and rollback.

Two disagreements were found and are recorded in
`results/raw/D1P-16/manual-comparison.json`:

1. **Boundary placement.** `build_consumer_transition` directly checks
   `chain_id == 31337` and `aztec_address == 0` beside a Boolean
   `verifier_accepts`. The Solidity consumer has no such standalone guards; it
   passes both words to the verifier. Route A therefore keeps those producer
   constraints inside `R_verify`, as required by this task. This distinction is
   not observable in the five pinned valid-proof executions.
2. **Exceptional-path precedence and tentative effects.** The manual model
   validates amount subtraction and both receivers, builds both occurrences,
   and only then checks one aggregate total-supply addition. The source performs
   `_mint(relayer, fee)` before evaluating the second mint's subtraction and
   receiver. With `pre.totalSupply = 2^256-1`, `fee = 1`, and `amount = 0`, the
   extracted source relation first panics at `ERC20.sol:179`, after a tentative
   nullifier write and attempted fee mint. The manual model instead reports the
   later subtraction underflow at `WarpToadCore.sol:172` and exposes no tentative
   occurrence. Both commit nothing, so ordinary committed-state comparisons did
   not reveal this difference.

The second disagreement refines the manual summary; it does not invalidate the
five earlier execution results. There is also a representation-only difference:
the manual model uses OpenZeppelin source ranges and expanded diagnostic strings,
whereas the extractor records the exact AST line and normalizes custom errors or
arithmetic panics by name. The path guards retain the failing operands, but exact
custom-error arguments are not serialized.

### Five concrete executions

| Execution | Selected extracted path | Result | Extracted effects | Disagreements |
|---|---:|---|---|---:|
| D1P-12R honest | `p18` | success | fee `260069110130330852`; recipient `4739930889869669148`; nullifier committed | 0 |
| D1P-12R replay | `p02` | revert at `WarpToadCore.sol:157` | no committed effect | 0 |
| D1P-14A FC-POS | `p18` | success | fee `194881000400000000`; recipient `4805118999600000000`; nullifier committed | 0 |
| D1P-14A FC-NEG | `p06` | revert at `WarpToadCore.sol:166` | tentative nullifier rolled back; no committed effect | 0 |
| D1P-14A zero-fee | `p21` | success | recipient `4000000000000000000`; nullifier committed | 0 |

For every case, all 11 recovered public words equal the proof's archived public
inputs. Balances, total supply, nullifier state, mint multiplicity, beneficiaries,
amounts, revert reason/location, and rollback agree with the archived expected
outcomes. The comparison report contains `all_checks_pass=true` and an empty
`disagreements` array.

## Route B — Halmos

### Selection and pin

Halmos was chosen over hevm for this bounded comparison because its implementation
offers directly inspectable Python data structures for the two needed export
dimensions: [path constraints in `Path`](https://github.com/a16z/halmos/blob/ba94bdc232c746b61f12eeacef6136eace81c7c2/src/halmos/sevm.py)
and storage/log trace records in the same module. Its official CLI remains a
Foundry symbolic-test interface. This was a better starting point for an export
adapter than hevm's documented symbolic-test/debugging interface.

The isolated environment installed Halmos `v0.3.3` at commit
`ba94bdc232c746b61f12eeacef6136eace81c7c2`. The executable SHA-256 is
`1f9b13c9b1d634bd2e406550d2f93ccf7670c9e18997b985d014b111bbe93a44`.
Installation and the API probe succeeded; no network request was blocked.

### Probe result and stopping decision

The probe confirmed:

- `Path` retains conditions and produces an `SMTQuery` containing SMT-LIB;
- `StorageWrite(address, slot, value, transient)` and
  `EventLog(address, topics, data)` retain the required internal effects; but
- CLI `TestResult` JSON contains only name, exit code, counterexample/model data,
  path counts, time, and bounded-loop count—not path formulas, post-storage, or
  events.

The CLI also labels `--uninterpreted-unknown-calls` as “Deprecated; no-op”. Thus
there is no supported option that turns the verifier call into the required
`R_verify(proof, words)` boundary. Running the consumer with a verifier that
always returns true would violate the task rule, so no such harness was used.

A custom Halmos route remains plausible: intercept the verifier `CALL`, create a
named relational Boolean tied to its calldata, retain final `Exec.path` and
storage/log trace objects, distinguish reverted from committed traces, and write
a stable serializer. That work depends on internal APIs and duplicates much of
the adapter/extractor engineering already demonstrated by route A. Accordingly,
route B is **not demonstrated for the pinned consumer**, and it produced no
relation to compare against the manual summary or five executions. This absence
is the route-B comparison result—not evidence that EVM-level extraction is
impossible.

Consequently, every requested route-B comparison is `NOT_RUN_NO_RECOVERED_RELATION`:
there are no exported guards, verifier arguments, committed effects, or rollback
relation to compare with the manual summary or any of the five executions. These
are missing results, not observed semantic disagreements.

## Limitations and recommendation

Route A is a feasibility prototype, not a general Solidity verifier. Its present
support is intentionally bounded to the constructs reached from this pinned
`mint`; dynamic loop bounds, assembly/Yul, proxy/delegatecall semantics, and
arbitrary external reentrancy are outside scope. It relies on solc's typed AST and
standard Solidity/EVM semantics, and has not been mechanically proved sound.

Within the requested scope, route A is the only route with an exported relation
and complete five-execution differential evidence. Adopt route A as the consumer
extraction path, retain the source/compiler pin checks and regression fixtures,
and keep the producer relation and policy compiler as explicit downstream
boundaries. Do not describe this result as automatic obligation derivation.

## Evidence map

- `results/raw/D1P-16/experiment-plan.md` — prospective plan and stopping rules.
- `results/raw/D1P-16/route-a-relation.json` — compact extracted relation.
- `results/raw/D1P-16/concrete-comparison.json` — five-case comparison and input
  hashes.
- `results/raw/D1P-16/manual-comparison.json` — manual-summary agreements and all
  observed disagreements.
- `results/raw/D1P-16/route-b-install.json` — Halmos pin, version, hashes, and
  network record.
- `results/raw/D1P-16/route-b-halmos-probe.json` — internal/CLI export probe.
- `results/raw/D1P-16/route-b-assessment.json` — explicit missing-result status
  for the manual and five concrete comparisons.
- `results/raw/D1P-16/commands.md` — replay commands.
- `prototypes/d1p16/` — extractor, comparisons, probe, and regression tests.
