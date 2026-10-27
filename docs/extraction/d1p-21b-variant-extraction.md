# D1P-21B — campaign gate 2: variant-general extracted consumer model

Date: 27 October 2026  
Worktree base: `4897d6814ab1eb8adf1bae6526b5ac4436b8dd10`  
Application: WarpToad, revision `973e7d1e4b60d0d8a8ca299b0cabd9193b147ef8`  
Task status: **PASS for the bounded gate**  
D1 security verdict: **UNKNOWN**

## 1. Outcome and claim boundary

The route-A consumer adapter now accepts the actual shape of a newly extracted
relation, records the relation and serialized-path hashes, and emits every
terminal family. It no longer requires the pinned `22/19/3` shape. Running the
unchanged D1P-18 extractor on the D1P-19 M-SRC consumer recovered a `21/18/3`
relation and automatically removed precisely the K2 local-root family and its
positive guard from the remaining paths.

The extracted `aztecWarptoadAddress` storage read is now bound to
`fixed_pre_state_S0.aztec_warptoad_address`. The extracted `block.chainid`
read is bound to a separately required admitted environment input. Omitting
either input raises a named fail-closed rejection. The D1P-20 address and
chain-ID SMT constants are not used by the D1P-21B extracted route.

The five archived pinned executions, all eight D1P-14D controls, a nonzero
`S_DOM` configuration polarity, and the D1P-19 real-proof M-SRC/pinned
polarity all pass. Full producer-connected BASE encodings and producer-dropped
T-ARITH encodings for both relation shapes parse with cvc5 1.4.2. There were
zero primary solver calls.

This is extraction and serialization fidelity evidence on the tested
`WarpToadCore.mint` fragment. It is not automatic policy-to-obligation
derivation, a new proof campaign, a reachability result, a security verdict,
or a general Solidity/EVM claim.

## 2. State and environment binding

D1P-20 defined `config_aztec_address` from the manual module constant zero.
D1P-21B instead requires and serializes the value supplied in the admitted
pre-state. Its `S_DOM` control uses the frozen nonzero
`A_WT = 81985529216486895`:

| fixed check | result |
|---|---|
| verifier word 5 equals admitted `S_DOM.A_WT` | SAT |
| verifier word 5 is the old manual zero while the admitted value remains nonzero | UNSAT |

The same audit found one other source-derived configuration input previously
lowered from a module constant: `block.chainid`. It now comes from the required
`environment.chain_id` input. The complete configuration inventory is:

| source read | D1P-21B binding | status |
|---|---|---|
| `pre.aztecWarptoadAddress` | `fixed_pre_state_S0.aztec_warptoad_address` | source-extracted storage read; admitted-state value |
| `block.chainid` | `environment.chain_id` | source-extracted environment read; admitted-environment value |
| `pre.withdrawVerifier` | resolved verifier boundary declaration | manual relational-boundary target; no numeric SMT constant |

`block.basefee` remains symbolic. `msg.sender` remains the previously checked
owned-local named-relayer substitution, not deployment configuration.
`_totalSupply`, `_balances`, root histories and nullifiers were already read
from the admitted pre-state; they remain so. M-SRC correctly has no
`localRootHistory` read.

The machine-readable evidence is
[`s-dom-state-binding.json`](../../results/raw/D1P-21B/s-dom-state-binding.json)
and the configuration section of
[`manual-input-manifest.json`](../../results/raw/D1P-21B/manual-input-manifest.json).

## 3. Variant-general relation serialization

### 3.1 Input and extractor provenance

The extractor was not edited for the M-SRC run:

- extractor SHA-256:
  `4a9dd7516d0b2291b0a3a1bf66f2bdb074d021356fff2fc506cd88e30e30af7b`;
- M-SRC source SHA-256:
  `64ec0efd0df934afc46f06be76764b74b97b9ac554e1bd72add7ce0a630373e3`;
- solc build-info SHA-256:
  `93ebc781ccd3880d0965be0cb1c9df26731af559f2e56cee9ca5d8ceee9aaa14`;
- compiler-output SHA-256:
  `04fa7afbc535283117919968818838a6b9ffd63af40c490a35f4cd6d108cbe03`;
- solc `0.8.29+commit.ab55807c`, optimizer enabled with one run, EVM
  `cancun`; and
- all eight extractor pin assertions pass, with no case-specific effect model.

The resulting relation file SHA-256 is
`91929f0953313f05d67f3539edf8e7ef69cf51c423a83dfe941af1eb8cdce969`.
The pinned D1P-18 relation remains
`301ce67b6148bd889082f67b7c484cac55a52981d540917c21ac67f421293fd7`.

### 3.2 Shape and recovered difference

| relation | all paths | revert | success | rollback on every revert |
|---|---:|---:|---:|---|
| pinned | 22 | 19 | 3 | yes |
| M-SRC | 21 | 18 | 3 | yes |

The removed pinned family is `p01`, the revert at
`WarpToadCore.sol:156` with reason `_localRoot unknown` and guard
`not(select(pre.localRootHistory, calldata._localRoot))`. After removing the
positive K2 predicate from the other pinned paths, all 21 remaining families
match the M-SRC extraction. The successful-family renumbering is:

| pinned | M-SRC |
|---|---|
| `p14` | `p13` |
| `p18` | `p17` |
| `p21` | `p20` |

This comparison is mechanical and preserved in
[`variant-comparison.json`](../../results/raw/D1P-21B/variant-comparison.json).
It does not supply the implementation equation that changed.

### 3.3 Serialization checks

The loader now computes the observed shape and rejects a claimed/observed
mismatch, duplicate IDs, unknown statuses, failed pins, or a revert family
with committed effects. The serializer records:

| relation | canonical relation SHA-256 | serialized paths SHA-256 |
|---|---|---|
| pinned | `2370eef16a9c8100280aa5b2ab0c429ccf9692cd5c60dba07c2e19c97a15e059` | `350dea3eb0432f2338ea8d74490b075ffa9f8411cc3b3c596f2a846acd6239ac` |
| M-SRC | `68fbe438e98a7657c205345b05827ea5d861a17ed7ed7e4e4447e2c620a9a105` | `345552a20d880ad0c994c080afeb75258974be3429f9a8dad19a1375cf2b4b63` |

Every path ID is copied into the transformation certificate and checked
against the emitted `PATH` definitions. A new relation that stays inside the
supported D1P-18 IR/effect fragment may have any terminal-path count. A new
IR operator, effect shape, verifier boundary, or unsupported callsite still
raises the existing named `UNSUPPORTED_<kind>` rejection; shape generality is
not semantic-fragment generality.

## 4. Revalidation

### 4.1 Pinned concrete executions

The fixed archived inputs retain their D1P-18 path classifications and their
expected solver polarity:

| execution | pinned path | expected/observed |
|---|---|---|
| D1P-12R honest | `p18` | SAT / SAT |
| D1P-12R replay | `p02` | UNSAT / UNSAT |
| D1P-14A FC-POS | `p18` | SAT / SAT |
| D1P-14A FC-NEG | `p06` | UNSAT / UNSAT |
| D1P-14A zero-fee | `p21` | SAT / SAT |

Each run also checks that admitted `aztec_warptoad_address` equals public word
5. Full details and query hashes are in
[`pinned-concrete-executions.json`](../../results/raw/D1P-21B/pinned-concrete-executions.json).

### 4.2 D1P-14D controls

All four positive controls are SAT at their designated goals and all four
unchanged negative controls are UNSAT. The policy hash is identical across
all eight calls. See
[`pinned-d1p14d-controls.json`](../../results/raw/D1P-21B/pinned-d1p14d-controls.json).

### 4.3 D1P-19 real-proof polarity

The fixed input uses archived real proof
`d51ad19e73889b9eb9f1c53561415dd534faa1bba95738169bad2ae2367f534b`,
which the archived generated verifier accepted. The destination local root is
deliberately absent from the fixed consumer pre-state, while the giga root is
admitted. The source-level evaluator and fixed SMT checks agree:

| consumer relation | selected path | result |
|---|---|---|
| M-SRC | `p20`, success | SAT |
| pinned | `p01`, `_localRoot unknown` at K2 | UNSAT |

The producer-dropped boundary is used only because the archived real
proof already establishes accepted-proof feasibility; it remains explicitly
classified as that assumption and is never modeled as an always-successful
verifier in a full query. The base fee `130951701` is reconstructed from the
archived effective gas price minus public priority fee; fee factor is zero.
See
[`m-src-fixed-input-polarity.json`](../../results/raw/D1P-21B/m-src-fixed-input-polarity.json).

### 4.4 Full bridge and T-ARITH

For pinned and M-SRC, the full BASE query contains all eleven recovered
consumer-argument bridges and all eleven `D_v` producer-witness bridges and
passes cvc5 parse-only. T-ARITH for both relations declares exactly one fresh
`fee_amount`, removes the concrete fee definition, retains every variant path,
and passes parse-only. Thus path-shape generalization and admitted-state
binding do not introduce a consumer-model-specific T-ARITH transform.

## 5. Remaining manual inputs

The updated manifest is variant-aware and keeps implementation facts separate
from policy:

- seven shared OpenZeppelin 5.6.1 effect-model entries, table version 1.0.0,
  SHA-256
  `236c4691c410ead94bdb500d904fe91243f66be8ce4e46b96b487fe0d325ac6d`;
- one exact `IVerifier.verify(bytes,bytes32[])` relational boundary
  declaration, with `assumed_true=false`;
- admitted state and environment values, including the address and chain ID
  bindings above;
- the named-relayer owned-local environment assumption; and
- a separate three-callsite policy-role map (`FEE`, `RECIPIENT`,
  `RECIPIENT`), which is not part of the implementation relation.

The effect table and boundary declaration are identical across pinned and
M-SRC. The source-read inventory is intentionally variant-specific because
M-SRC has no `localRootHistory` read. No case-specific library entry or manual
M-SRC implementation equation was added.

## 6. Commands and accounting

The M-SRC relation was generated with:

```sh
python3 prototypes/d1p16/extract_relation.py \
  --build-info /Users/imranpollob/Coding/bc/bindcheck-d1-paper/results/raw/D1P-19/workspace/source/backend/artifacts/build-info/solc-0_8_29-aec81eab73589a53b8dc9a27808995da0b1e3bbb.json \
  --compiler-output /Users/imranpollob/Coding/bc/bindcheck-d1-paper/results/raw/D1P-19/workspace/source/backend/artifacts/build-info/solc-0_8_29-aec81eab73589a53b8dc9a27808995da0b1e3bbb.output.json \
  --source /Users/imranpollob/Coding/bc/bindcheck-d1-paper/results/raw/D1P-19/workspace/source/backend/contracts/core/WarpToadCore.sol \
  --expected-source-sha256 64ec0efd0df934afc46f06be76764b74b97b9ac554e1bd72add7ce0a630373e3 \
  --output results/raw/D1P-21B/m-src-relation.json
```

Validation and focused tests used:

```sh
PYTHONPATH=src:prototypes/d1p21b python3 prototypes/d1p21b/validate_d1p21b.py \
  --paper-root /Users/imranpollob/Coding/bc/bindcheck-d1-paper \
  --artifact /Users/imranpollob/Coding/bc/bindcheck-d1-paper/results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json \
  --pinned-relation results/raw/D1P-18/relation.json \
  --m-src-relation results/raw/D1P-21B/m-src-relation.json \
  --solver /Users/imranpollob/Coding/bc/BindCheck/tools/cvc5-1.4.2-gpl/bin/cvc5 \
  --output-dir results/raw/D1P-21B

PYTHONPATH=src:prototypes/d1p21b \
  python3 -m unittest prototypes/d1p21b/test_d1p21b.py -v

PYTHONPATH=src:prototypes/d1p20 \
  python3 -m unittest prototypes/d1p20/test_d1p20.py -v
```

Observed results: D1P-21B `6/6` and preserved D1P-20 `6/6` tests pass under
Python 3.14.7. cvc5 is 1.4.2, git `282d5e0`. Solver accounting is:

- primary solver calls: **0**;
- fixed archived-execution validation: 5;
- deterministic D1P-14D controls: 8;
- fixed M-SRC/pinned polarity: 2;
- fixed `S_DOM` configuration polarity: 2; and
- parse-only calls: 4.

The aggregate machine-readable result is
[`validation.json`](../../results/raw/D1P-21B/validation.json). D1P-20 source,
report, and raw outputs were not modified. Exact argv arrays and exit statuses
are in
[`command-records.json`](../../results/raw/D1P-21B/command-records.json).

## 7. Limitations and next gate

The admitted `S_DOM` configuration check is synthetic fixed-state evidence,
not cross-chain reachability. The M-SRC polarity reuses an archived real proof
and execution; this task generated no proof and made no new E4 claim. The
producer-dropped fixed checks do not replace full joint queries, and the two
full queries were parsed but not solved.

The serializer remains bounded by the D1P-18 supported IR and the versioned
OpenZeppelin models. The policy adapter still maps extracted occurrences to
semantic roles manually. Therefore automatic obligation derivation remains
open. A measurable next gate is to derive at least one G1–G5-style obligation
from versioned policy input and extracted occurrences without a manual
callsite-role map, while retaining the pinned/M-SRC polarity and all current
fail-closed controls.
