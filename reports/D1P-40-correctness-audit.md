# D1P-40 — BindCheck extraction-correctness audit

Date: 30 October 2026  
Task status: **DONE for Milestone 1 correctness audit and bounded repairs**  
Development scope: **WarpToad, Payy, benchmark mutants, and synthetic controls only**  
Result: **five confirmed extraction defects repaired; two bounded behaviors not bugs; Payy memory-tail identity remains UNKNOWN**  
D1 security verdict: **UNKNOWN**

## 1. Objective and outcome

This task audits whether BindCheck v1.2's extracted implementation facts are
correct. It does not audit compiler-version coverage, add opcode support, run a
solver or proof, validate a new vulnerability, or inspect any D1P-33/D1P-36
project checkout.

Five defects are confirmed and repaired in prospective BindCheck v1.3:

1. dynamic `MemoryInit`/`MemoryOp` dependencies were classified as unused even
   when a later memory read fed a constraint;
2. a shorter consumer verifier array was non-uniquely mapped to a producer ABI
   by inventing a selector prefix;
3. any function with an ERC-20-shaped signature could be mislabeled a token
   effect;
4. loop-index widening could attach unreachable tail words to an effect; and
5. R-ANCHOR candidates were created only after a positive guard was found, so
   the compiler-AST route could not emit the rule for a missing guard.

The repaired 30-mutant development rerun changes **16 detected / 14
unsupported / 0 misses / 53 warning objects** to **11 detected / 19
unsupported / 0 misses / 13 warning objects**. The five reclassified detections
are Payy `PY-C02`, `PY-C04`, `PY-C06`, `PY-S01`, and `PY-S02`. All 12 Payy
mutants now fail closed because the consumer's 1,003-word direct array does not
by itself establish its exact mapping into the 1,005-leaf producer ABI. All 13
remaining WarpToad warning identities are unchanged. Unsupported is not a miss
and is not safety evidence.

D1P-34 and D1P-35 remain immutable historical reports. Their Payy
selector-prefix and message-tail facts are not silently rewritten; this report
is the prospective correction.

## 2. Scope, versions, and evidence

The requested `git merge --ff-only main` was run. The sandboxed attempt could
not lock linked-worktree `ORIG_HEAD`; the approved retry returned zero and
reported `Already up to date.` Both `main` and task-start `HEAD` were
`83a4d8d2e4d8bb6ef8b3be6c3f91126d2c9cf580`.

Final tools:

- Python `3.13.9`;
- Nargo/noirc `1.0.0-beta.22+c57152f9...`, executable SHA-256
  `37f7d55d9795af0da3b471db2306e0296fa34c528386a828ce556fc3ebbf6e7b`;
- solc `0.8.29+commit.ab55807c.Darwin.appleclang`, executable SHA-256
  `66fabdd17c8c0091311997ec7d17b4d92e1b7b2c2d213dc14e4ff28c3de864d1`;
- Git `2.51.0`.

Final implementation identities (task-start revision plus uncommitted bytes):

- analyzer `src/bindcheck_d1/static_analyzer_v1.py`:
  `ae270377e537caf959159a060fb1a1247c7c666e2a315caee03461f9f6ea1dc5`;
- Solidity frontend `src/bindcheck_d1/frontends/solidity_ast_v1_1.py`:
  `97c377e371e3f5b54412908fe8677e10b979e51181aa1aa240ffd969df8d9faa`;
- v1.3 shared effect table:
  `87527166b31eaa39181d692dc398a38c47cf225600f0207d8cb82b01327c8091`;
- audit runner:
  `8f6b2f6a0bfb20651ba6d1a229b1226690d2d1d083e74608d6d20f7783c1201d`;
- focused regression file:
  `a77380062713886948b9f6ceebef2567505d3139c31d8ec927ac12504bf67719`.

Canonical ignored evidence is under `results/raw/D1P-40/final-04/`:

| record | SHA-256 |
|---|---|
| `synthetic-results.json` | `791fe845bd608a283451c0064f442a0d048e716bdd2718b319872104dd3eda8d` |
| `benchmark-rerun.json` | `ff53e2c7847c8ed514cf325a55c8959d666df7434ef75b09b6fcce2204daaf4f` |
| `run-ledger.json` | `97d44299d83133ea23566e23d81cb1cd6cbcdefbd56864358c86975811caf228` |

The ledger records every synthetic compiler argv, compiler hash, return code,
runtime, stdout and stderr hash. Exact pre-update copies of `README.md` and
`docs/project-status.md` are preserved under `prior-checkpoint/` with hashes
`b0c62f...` and `ab2c1f...`.

## 3. Audit findings

### 3.1 Memory dependencies

The positive dynamic control compiles:

```noir
fn main(left: pub Field, right: pub Field, index: pub u32, expected: pub Field) {
    let values = [left, right];
    assert(values[index] == expected);
}
```

The actual beta.22 ACIR is a two-witness `MemoryInit`, a dynamic-index
`MemoryOp(read)`, and an `AssertZero` on the read result and `expected`.
Pre-repair BindCheck reported `left` and `right` with zero proof-enforced
occurrences and one definition-only occurrence each. That is not enough to
claim either value unused: the read can select either cell. **Confirmed bug.**

The repair tracks memory blocks in opcode order. Exact constant-address reads
propagate only the selected current-cell dependencies. Dynamic reads or writes
mark possible initializer dependencies `unresolved-dynamic`; if an affected
public leaf has no independent proof-enforced occurrence, analysis fails closed
with `UNSUPPORTED_DYNAMIC_MEMORY_DEPENDENCY`.

Two negative/positive boundaries pass:

- a constant-index Noir assertion compiles to direct use of `right` and
  `expected` while `left` remains unused: **not a bug**;
- a write-only public `value` is optimized away and remains at zero
  occurrences: **not a bug**.

On the full Payy earlier artifact, `messages[1]..messages[999]` are initialized
and potentially selected by dynamic reads. Their exact address/path conditions
are not proved by this bounded repair, so all 999 are **UNKNOWN**, not “unused”
and not “used.” Whether each tail value is actually constrained remains
**unclear** pending an address/path proof. This removes the old static warning
as evidence but does not contradict the preserved real-proof Payy validation.

### 3.2 Public-input mapping

The nested-ABI positive control has the independently expected declaration
order:

1. `envelope.tag`;
2. `envelope.pair.values[0]`;
3. `envelope.pair.values[1]`;
4. `tail[0]`;
5. `tail[1]`.

The decoded witness allocation and verifier-array indices match exactly:
**not a bug** for nested structs/arrays in the supported beta.22 ABI.

The negative Solidity control supplies a three-word verifier array against
five producer leaves with a two-element selector-shaped prefix. Width arithmetic
alone cannot distinguish prefix, suffix, interleaving, verifier-supplied
constants, or a mismatched artifact. The old frontend chose the prefix and
marked the two invented leaves consumer-used. **Confirmed bug.**

The repair accepts identity mapping only when the supported path establishes
the full width, including an exact literal success-path length guard. Any
shorter direct array fails closed with
`SOLIDITY_PUBLIC_INPUT_MAPPING_AMBIGUOUS`; old relations carrying the inference
limitation fail with `CONSUMER_PUBLIC_INPUT_MAPPING_UNVERIFIED`.

For Payy, the old two-word selector-prefix mapping is therefore **unclear**.
It may be correct, but neither the producer ABI shape nor the consumer AST
proves it. Exact generated-verifier/configuration evidence is required.

### 3.3 Consumer effects and loop dependencies

The synthetic `Effects.sol` independently contains:

- `committed = publicInputs[0]` at line 21;
- `token.transfer(recipient, uint256(publicInputs[1]))` at line 22; and
- an unrelated `helper(address,uint256)` call using `publicInputs[2]`.

The storage write and ERC-20 transfer kinds, word identities and locations are
correct. The old signature-only table also matched `helper`, a false token
effect. **Confirmed bug.** The shared model now requires both the standard
method identity (`transfer` or `transferFrom`) and the parameter signature.
The repaired output contains exactly storage word 0 and token word 1; word 2
is not an effect dependency.

The `LoopBounds.sol` positive/negative pair uses a four-word array but a loop
whose exact success-path interval is `0 <= i < 2`. Pre-repair widening attached
all four words to the storage effect. **Confirmed bug.** The bounded interval
repair attaches only words 0 and 1. Non-literal or unsupported loop bounds
remain widened and are explicitly limited by
`AST_LOOP_INDEX_WIDENED_TO_PUBLIC_ARRAY_TAIL`; this is not general loop
equivalence.

The existing warning-location selector remains correct on its positive control:
when storage bookkeeping and an already-recognized external effect share a
vulnerable word, the external effect location is reported. No separate
location defect was found.

### 3.4 R-ANCHOR reachability

`AnchorPositive.sol` reads `admitted[publicInputs[0]]` in a positive `require`;
`AnchorNegative.sol` reads the same boolean storage membership into committed
state but never guards success on it. Before repair, the candidate was created
from the guard, so the negative path had no candidate and R-ANCHOR was
unreachable. **Confirmed bug.**

The frontend now records boolean indexed-storage reads independently, excludes
same-key replay records, and subsequently checks whether a positive guard with
the same declaration path and public-derived key exists. The positive control
emits no warning; the negative control emits exactly `R-ANCHOR`.

This is a bounded structural fact, not complete semantic role inference.
Non-boolean registries and anchors with no surviving storage read remain outside
R-ANCHOR and may still be covered only by R-CONSUMER or be unsupported.

## 4. Repairs and regression tests

| defect | repair | regression |
|---|---|---|
| dynamic memory falsely unused | exact constant-read propagation; dynamic dependencies fail closed | compiled dynamic/constant/write-only Noir controls plus two focused unit tests |
| non-unique selector prefix | require full-width identity evidence; reject old inferred relations | nested ABI positive and five-versus-three negative Solidity controls |
| signature-only token effect | require standard method identity and signature | real `transfer` positive plus same-signature `helper` negative |
| loop tail false dependencies | simple literal interval propagation | four-word array / two-iteration storage-effect control |
| R-ANCHOR dead path | record boolean storage candidates before guard matching | guarded and unguarded membership contracts |

The regression set is `tests/test_bindcheck_d1p40.py`; the complete compiler
controls and benchmark runner are `scripts/d1p_40_correctness_audit.py`. The
new tests exercise conditions that the pre-repair implementations either
misclassified or could not represent.

## 5. Benchmark rerun and every change

| metric | D1P-34 | D1P-40 | explanation |
|---|---:|---:|---|
| detected targets | 16 | 11 | five Payy detections become unsupported |
| unsupported targets | 14 | 19 | all 12 Payy targets now fail closed; seven were already unsupported |
| misses | 0 | 0 | no unsupported result is counted as a miss |
| warning objects | 53 | 13 | 40 Payy objects are suppressed after mapping failure: 7 related + 33 inherited/unrelated |

The five identity changes are:

- `PY-C02`: R-BIND/R-EFFECT detection → mapping unsupported; its message-tail
  memory dependency is independently unresolved;
- `PY-C04`: R-BIND detection → mapping unsupported;
- `PY-C06`: R-BIND/R-EFFECT detection → mapping unsupported;
- `PY-S01`: R-POLARITY detection → mapping unsupported;
- `PY-S02`: R-POLARITY detection → mapping unsupported.

The other seven Payy mutants remain unsupported, now at the earlier exact
mapping gate. WarpToad remains 11 detected / 7 unsupported / 0 misses. Its 13
warnings retain the same target, rule, semantic word/polarity evidence and
locations. No warning was validated in this milestone.

## 6. Commands and observed results

Primary commands:

```sh
git merge --ff-only main
PYTHONPATH=src python3 scripts/d1p_40_correctness_audit.py
PYTHONPATH=src python3 tests/test_bindcheck_d1p40.py -v
PYTHONPATH=src python3 tests/test_bindcheck_v1.py -v
PYTHONPATH=src python3 tests/test_bindcheck_v12.py -v
PYTHONPATH=src python3 -m pytest -q tests
python3 -m py_compile src/bindcheck_d1/static_analyzer_v1.py \
  src/bindcheck_d1/frontends/solidity_ast_v1_1.py \
  scripts/d1p_40_correctness_audit.py
git diff --check
```

Observed results:

- merge: exit 0 on approved retry, already up to date;
- final audit runner: exit 0, nine synthetic checks, 30 benchmark targets;
- D1P-40 focused tests: 7/7 pass;
- existing v1 tests: 11/11 pass;
- existing v1.2 tests: 5/5 pass;
- complete scoped suite: **254 tests and 323 subtests pass in 104.21 s**;
- bytecode compilation and `git diff --check`: pass.

All five Nargo and six solc final compiler calls returned zero. Their exact
argv and individual runtimes are in `run-ledger.json`.

## 7. Assumptions, limitations, and failed approaches

- This is source-/model-confirmed and locally reproduced extraction evidence,
  not a proof-system, Solidity-equivalence, policy, security, or E4 result.
- Dynamic memory addresses are deliberately `UNKNOWN` unless exact; no solver
  proves Payy's path-sensitive address range in this task.
- Exact Payy selector/public-array correspondence is not established. The
  consumer and producer artifacts are not declared mismatched; analysis stops.
- Token recognition identifies a standard ABI method, not successful transfer,
  standard token behavior, or transaction commitment.
- Loop intervals cover the tested literal comparison only. Other loops retain
  the named widening limitation.
- R-ANCHOR candidate extraction is limited to boolean indexed storage reads.
- No D1P-33/D1P-36 project checkout, held-out source, live chain, third-party
  system, maintainer, or disclosure channel was opened.
- The first sandboxed Nargo calls failed on the global dependency-cache lock;
  approved local-cache access resolved it. Initial fixture manifests used an
  invalid prerelease `compiler_version` requirement and were corrected before
  the final run.
- A preliminary `results/raw/D1P-40/final/` run attached the generic mapping
  reason to pre-existing WT-S04 consumer-AST absence. `final-02/` corrected the
  runner reason; final review then added a fail-closed dynamic-write/constant-
  read edge case in `final-03/`. Final schema review then versioned the repaired
  consumer relation and effect table while restoring the historical v1.1 table.
  All three earlier namespaces are preserved but non-canonical; `final-04/`
  binds the final code and is canonical.
- No commit, push, history rewrite, prior-report edit, or evidence deletion
  occurred.

## 8. Recommended next task

Build a Payy-specific **implementation-fact certificate**, without changing
rules: establish a unique mapping for all 1,005 producer leaves to the
recursive verifier configuration plus the 1,003-word consumer array, and prove
or conservatively classify every dynamic memory read address affecting
`messages[1..999]`. Completion requires (1) a mechanically checked bijection or
an explicit `UNKNOWN` blocker for every leaf, (2) exact address/path evidence
for all 999 tail leaves, and (3) a fresh rerun of the 12 Payy mutants and the
earlier/check-added controls with every count and warning identity reconciled.
