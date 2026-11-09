# L2 relational builder report

## Objective and status

This lane implements a candidate Circom-to-Solidity relational mechanism for the property “consumer reliance must imply producer enforcement under compatible conditions.” It is available as a separate analyzer module and opt-in CLI envelope; the pre-existing analyzer logic was not changed.

The implementation status is complete for the bounded templates described below. The research status is **UNKNOWN**. Prospective synthetic controls pass, but the data-wall-safe DEV run found no applicable natural pair for any of the four central dimensions. The ROLE/IDENTITY stretch screen made only [three narrowly scoped decisions](dev-summary.json), which cannot validate the central mechanism or establish application safety.

The controlling authority was `docs/research-contract.md`, followed by `README.md` and the immutable reports. The pre-lane README and immutable reports disagree about the earlier frozen analyzer state ([README](../../README.md), [T25](../T25.md), [T26](../T26.md)); this lane therefore uses its own content hash and manifests rather than reconciling historical records. Per the lane instruction, neither `README.md` nor `docs/project-status.md` was edited.

## Property

For a producer public value or decoded field (x), let (E_x) be the recovered circuit enforcement condition, (L_x) the recovered consumer reliance region, and (A_x) the compatible activation mapping between the two sides. The supported check is:

\[
A_x \land L_x \Rightarrow E_x
\]

A `VIOLATION` requires a supported counter-region in which the consumer commits a guard, effect, or state write but the producer value is not enforced under the corresponding condition. `VERIFIED_WITHIN_SCOPE` means the two recovered conditions are compatible only within the exact bounded template. Missing compilation, ambiguous correspondence, unsupported extraction, or an unsupported implication is `UNKNOWN`.

| Dimension | Producer condition | Consumer reliance | Supported comparison |
|---|---|---|---|
| EXTENT | A selector-constrained array plus a monotone active prefix and public extent | An effect/state-write loop over the same array | Same extent is `VERIFIED_WITHIN_SCOPE`; a static full-width loop exposes the unenforced suffix as `VIOLATION` |
| MASK | Per-position selector times public/private equality | An effect/state-write loop over the selected values | The same equality-to-one guard is `VERIFIED_WITHIN_SCOPE`; unconditional reliance is `VIOLATION` |
| REPRESENTATION | A linear packed signal with recovered positional weights | An effect-bearing Solidity decode of the same public limbs | Exact weight-map equality is `VERIFIED_WITHIN_SCOPE`; a different map is `VIOLATION` |
| MULTIPLICITY/SCOPE | A recovered nullifier expression and compiled dependence | A two-level replay mapping keyed by entity and nullifier, with read and committed write | Direct inclusion of the entity in source and compiled constraint is `VERIFIED_WITHIN_SCOPE`; source absence plus R1CS disconnection is `VIOLATION`; mixed evidence is `UNKNOWN` |
| ROLE/IDENTITY | A scalar public wire that participates in R1CS and appears in an explicit source equality | A recognized scalar consumer role at the same public position whose identifier occurs beyond the verifier vector | Equal bounded annotations are `VERIFIED_WITHIN_SCOPE`; unequal annotations are a heuristic `VIOLATION`; insufficient evidence is `UNKNOWN` |

## Algorithm

The implementation is in [`bindcheck_zk/relational/`](../../bindcheck_zk/relational/):

- Discover Circom entry sources and Solidity functions containing exactly one verifier call. Explicit `--circuit` and `--consumer` paths remain supported.
- Compile or load each entry circuit’s R1CS and symbol table. Compilation failure, timeout, or missing artifacts cannot produce a safe verdict.
- Pair a consumer with a unique compiled circuit using public-vector width and name overlap. No positive score or a tied best score remains unresolved.
- Extract only bounded source templates from Circom and effect-bearing reliance from Solidity.
- Map source signal names to compiled wires and confirm direct constraint incidence. Graph connectivity is used only for the negative/disagreement branch of scope analysis and never by itself as proof of algebraic binding.
- Compare the recovered producer and consumer conditions with dimension-specific exact comparators, aggregate each dimension independently, and retain pair-level facts, hashes, limitations, and reason codes.

The analyzer content hash reported by `freeze.sh` is [`3d5f37430a32a3f9f7b20bc72f272804d175d3afeb6a5322ec275a4578b164d1`](../../results/raw/relational/controls-20261109T032415Z-59275/manifest.json). Recursive package hashing was added so the relational subpackage is part of that value.

## Soundness and heuristic boundary

There is no general soundness or completeness theorem for this implementation.

Direct facts from R1CS/sym are compiler-backed wire presence, constraint incidence, and graph separation. They do not establish semantic equality, correct coefficient interpretation, range, field-to-integer meaning, or protocol policy. Once source facts and a unique correspondence have been recovered, the bounded equality/full-width/weight-map comparisons are deterministic, but the source extraction and circuit-consumer pairing remain syntactic heuristics.

ROLE/IDENTITY is deliberately isolated. Its labels come from bounded source-name tokens, and consumer reliance is only a repeat-identifier screen; the implementation does not prove that the second occurrence controls an effect. These facts are not compiler-semantic identities, independent annotations, or an authorization proof. All lane findings remain [E1 evidence](../../docs/research-contract.md); this lane performed no proof generation, local exploit transaction, or repair validation.

## CLI and ablation controls

`bindcheck-zk analyze <repo> --relational` enables every dimension. Each switch also enables relational analysis by itself and restricts the relational envelope to the selected set:

- `--relational-extent`
- `--relational-mask`
- `--relational-representation`
- `--relational-multiplicity-scope`
- `--relational-role-identity`

The main analyzer output is unchanged when none of these switches is present. The selector behavior is covered by the [CLI relational test](../../tests/test_bindcheck_zk_relational.py).

## Prospective controls

Expected outcomes were committed before the analyzer and fixtures. The frozen oracle contains [forty cases](../../tests/relational/expected.json), distributed as follows; every case compiles its Circom fixture and evaluates the paired Solidity path.

| Dimension | Expected vulnerable | Expected legitimate | Observed |
|---|---:|---:|---|
| EXTENT | [four](../../results/raw/relational/controls-20261109T032415Z-59275/manifest.json) | [four](../../results/raw/relational/controls-20261109T032415Z-59275/manifest.json) | all matched |
| MASK | [four](../../results/raw/relational/controls-20261109T032415Z-59275/manifest.json) | [four](../../results/raw/relational/controls-20261109T032415Z-59275/manifest.json) | all matched |
| REPRESENTATION | [four](../../results/raw/relational/controls-20261109T032415Z-59275/manifest.json) | [four](../../results/raw/relational/controls-20261109T032415Z-59275/manifest.json) | all matched |
| MULTIPLICITY/SCOPE | [four](../../results/raw/relational/controls-20261109T032415Z-59275/manifest.json) | [four](../../results/raw/relational/controls-20261109T032415Z-59275/manifest.json) | all matched |
| ROLE/IDENTITY | [four](../../results/raw/relational/controls-20261109T032415Z-59275/manifest.json) | [four](../../results/raw/relational/controls-20261109T032415Z-59275/manifest.json) | all matched |

The combined inherited, CLI, and relational suite ran [twelve test methods](../../results/raw/relational/controls-20261109T032415Z-59275/stderr.log) and exited [`0`](../../results/raw/relational/controls-20261109T032415Z-59275/manifest.json). The exact environment was Python [`3.14.7`](../../results/raw/relational/controls-20261109T032415Z-59275/manifest.json) with Circom [`2.2.3`](../../results/raw/relational/controls-20261109T032415Z-59275/manifest.json), whose binary SHA-256 is recorded in the same manifest.

## DEV run

The runner reconstructed the complete [fifty-six-row manifest](dev-summary.json) from DEV-only sources and supplied no hints to `bindcheck-zk analyze <checkout> --relational`. The historical manifest itself conflicts with the repository-level data wall: [six rows](dev-summary.json) name explicitly prohibited repositories. The corrected run did not acquire or analyze those rows; it records their artifacts as `MISSING`, assigns every dimension `UNKNOWN`, and identifies each policy block in the [raw acquisition ledger](../../results/raw/relational/dev-20261109T031624Z-47526/acquisition.json). The remaining [fifty rows](dev-summary.json) were analyzed unhinted.

There are [seven fatal rows](dev-summary.json): the [six policy blocks](dev-summary.json) and [one analyzer timeout](dev-ledger.csv). A timeout and a policy block are not wins. Among the permitted executions, the analyzer compiled [fifty-seven circuit relations across thirty-one rows](dev-summary.json) and recovered [thirty paired paths across twelve rows](dev-summary.json).

| Dimension | Pair results | Applicable | Decided | Violations | Row-level result |
|---|---:|---:|---:|---:|---|
| EXTENT | [thirty](dev-summary.json) | [zero](dev-summary.json) | [zero](dev-summary.json) | [zero](dev-summary.json) | all [fifty-six](dev-summary.json) `UNKNOWN` |
| MASK | [thirty](dev-summary.json) | [zero](dev-summary.json) | [zero](dev-summary.json) | [zero](dev-summary.json) | all [fifty-six](dev-summary.json) `UNKNOWN` |
| REPRESENTATION | [thirty](dev-summary.json) | [zero](dev-summary.json) | [zero](dev-summary.json) | [zero](dev-summary.json) | all [fifty-six](dev-summary.json) `UNKNOWN` |
| MULTIPLICITY/SCOPE | [thirty](dev-summary.json) | [zero](dev-summary.json) | [zero](dev-summary.json) | [zero](dev-summary.json) | all [fifty-six](dev-summary.json) `UNKNOWN` |
| ROLE/IDENTITY | [thirty](dev-summary.json) | [thirty](dev-summary.json) | [three](dev-summary.json) | [zero](dev-summary.json) | [three](dev-summary.json) `VERIFIED_WITHIN_SCOPE`; [fifty-three](dev-summary.json) `UNKNOWN` |

The [three decided ROLE/IDENTITY pairs](dev-decisions.csv) were inspected as builder opinion. The [review ledger](dev-builder-review.csv) agrees only with the local source-role annotation and explicitly rejects any whole-function or application-safety interpretation. It is not independent annotation. There were [zero flags](dev-summary.json), so the [flag-adjudication ledger](dev-flag-adjudication.csv) contains only its header. Zero flags do not validate the analyzer; the absence of central-dimension applicability leaves the candidate mechanism `UNKNOWN` on natural DEV data.

The controlling raw manifest is [`2ee6ced34165c0a916d3c8a4e40845c5356dae0538a3374bdf5aa255bba5b788`](../../results/raw/relational/dev-20261109T031624Z-47526/manifest.json), the raw ledger is [`a043151ae7325a8deb73c90b7e2d3f3c551e6c955a8e59e7e19ec07d53686967`](../../results/raw/relational/dev-20261109T031624Z-47526/per-row-ledger.json), and the tracked summary is [`4ea36711e0ceca194af7f7b5c9c9741f9fa91f9a1007f8efd3c385e470e70c3c`](dev-summary.json). The DEV analyzer revision and exact compiler/tool environment are recorded in the [raw manifest](../../results/raw/relational/dev-20261109T031624Z-47526/manifest.json).

## Commands and observed results

Prospective expectations were committed before the implementation. The exact source sequence is visible in branch history: `893930c` contains only the frozen expectations and `879d9c7` introduces the analyzer and fixtures.

The recorded control command and its exit status are in the [control manifest](../../results/raw/relational/controls-20261109T032415Z-59275/manifest.json):

```sh
BINDCHECK_CIRCOM=/Users/imranpollob/Coding/bc/bindcheck-zk/tools/circom-src/target/release/circom \
PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_bindcheck_zk_relational_controls.py
```

The DEV execution and renderer were:

```sh
BINDCHECK_CIRCOM=/Users/imranpollob/Coding/bc/bindcheck-zk/tools/circom-src/target/release/circom \
PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_bindcheck_zk_relational_dev.py --fetch-jobs 6 --analyze-jobs 3

PYTHONDONTWRITEBYTECODE=1 python3 scripts/render_bindcheck_zk_relational_dev.py \
results/raw/relational/dev-20261109T031624Z-47526
```

The DEV command template, environment, source revision, artifact hashes, per-row exit state, and results are in the [DEV manifest](../../results/raw/relational/dev-20261109T031624Z-47526/manifest.json) and [ledger](../../results/raw/relational/dev-20261109T031624Z-47526/per-row-ledger.json). `./freeze.sh` produced the content hash reported above. `python3 -m py_compile` for the evidence scripts and `git diff --check` both completed without output or error before this report.

## Files changed

- Analyzer: [`bindcheck_zk/relational/`](../../bindcheck_zk/relational/), [`bindcheck_zk/cli.py`](../../bindcheck_zk/cli.py), and recursive package coverage in [`bindcheck_zk/freeze.py`](../../bindcheck_zk/freeze.py).
- Prospective controls: [`tests/relational/expected.json`](../../tests/relational/expected.json), [`tests/relational/fixtures.py`](../../tests/relational/fixtures.py), and [`tests/test_bindcheck_zk_relational.py`](../../tests/test_bindcheck_zk_relational.py).
- Evidence tooling: [`scripts/run_bindcheck_zk_relational_controls.py`](../../scripts/run_bindcheck_zk_relational_controls.py), [`scripts/run_bindcheck_zk_relational_dev.py`](../../scripts/run_bindcheck_zk_relational_dev.py), and [`scripts/render_bindcheck_zk_relational_dev.py`](../../scripts/render_bindcheck_zk_relational_dev.py).
- Tracked evidence summaries: [`reports/relational/`](./).

## Failed approaches and unexpected observations

- The first control-runner invocation failed before creating raw evidence because script-mode imports could not find the package. The runner now inserts the repository root before importing the freeze helper.
- The inherited coverage control initially failed because the ignored pinned Circom library dependency was absent in this checkout. The exact preservation copy was verified against [`vendor-lock.json`](../../bindcheck_zk/vendor-lock.json); the final control suite passed, and the ignored dependency copy was removed afterward. This setup failure was not counted as a win.
- A first DEV runner version acquired and analyzed repositories later recognized as explicitly blocked by the lane data wall. That raw run is preserved but excluded from every result; the exact affected rows, original manifest hash, and remediation are in [`dev-run-quarantine.json`](dev-run-quarantine.json). Temporary checkouts were removed, and the corrected runner blocks those repositories before acquisition. This is a process failure, not evidence about BindCheck.
- The core dimensions achieved synthetic control separation but no natural DEV applicability. That is the principal negative observation and prevents a central-mechanism claim.

## Assumptions and limitations

- The Circom compiler, R1CS parser, and symbol-table mapping are assumed correct; compiler-backed here does not mean formally verified.
- Positional public-input correspondence is considered only after a unique width/name pairing. ABI transformations, wrapper contracts, libraries, assembly, proxy indirection, and dynamically constructed vectors are outside the supported relation.
- The source matchers cover exact atomic templates, not arbitrary arithmetic, non-linear encodings, bit/range gadgets, field reduction, transitive scope derivations, or nested control flow.
- A direct shared R1CS constraint proves incidence only. It does not prove coefficient semantics or equality.
- ROLE/IDENTITY depends on source names and is a stretch screening heuristic.
- The prohibited rows remain `MISSING`/`UNKNOWN`; this report does not satisfy the literal “analyze every manifest row” request because doing so would violate the higher-priority repository data wall.
- No EVAL ledger, recall ledger, recall expectations, decision-gate repository source, live chain, deployed contract, or maintainer channel was intentionally used in the corrected run.

## Recommended next task

Prospectively add one new non-template producer-extraction family for each central dimension using only new synthetic cases and permitted DEV material. Commit vulnerable and legitimate expected outcomes before changing extraction, then rerun the unchanged frozen controls and the same data-wall-safe DEV manifest. Completion requires each central dimension to obtain at least one applicable permitted DEV pair, preserve every existing control outcome, and keep any unsupported or ambiguous pair `UNKNOWN`; do not tune on held-out data or reinterpret zero flags as success.
