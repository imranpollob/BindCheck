# `bindcheck-zk` development report

**Date:** 2026-11-03 (America/Detroit; the controlling run started 2026-11-04 UTC)

**Task:** T23

**Status:** `DONE` for unified-analyzer construction and DEV validation; held-out execution is `NEXT` and has not occurred

**Research verdict:** `UNKNOWN` beyond the per-pattern, per-input E1 results below

## 1. Objective and boundary

This task replaces the separate feasibility entry points
`feasibility/v2/screen_consumers.py`, `feasibility/v2/scan_p4.py`, and
`dataset/run_track_b.py` with one offline analyzer. The resulting command is:

```text
bindcheck-zk analyze <repo-dir> [--circuit <path>]... [--consumer <path>]...
bindcheck-zk analyze-bundle <verified-source-bundle>
bindcheck-zk baseline {slither,circomspect,picus,zkap} <repo-dir> ...
```

Every invocation emits one `bindcheck-zk.result/v1` JSON document. It contains
the tool identity and content hash, input paths and file hashes, repository
revision when available, discovered circuit/verifier/consumer triples and
matching confidence, P1--P5 results, source locations, evidence grades,
reasons, subprocess records, and explicit parsed/built/skipped/failed/timed-out
coverage.

The development data wall was preserved. Development used only:

- the 24 pre-existing Track B controls;
- 50 synthetic analyzer controls written for this task; and
- the three expressly named DEV applications at their pinned revisions.

No EVAL row was read, listed, or analyzed. Neither
`dataset/source-corpus.csv` nor `dataset/recall-set.csv` is opened by the DEV
runner. No held-out run, live RPC, proof submission, transaction, maintainer
contact, disclosure, or access to any of the 43 P4 deployment addresses took
place. Earlier E4 records remain earlier evidence; this tool's new DEV results
are E1 static/compiled-analysis evidence and do not inherit E4.

## 2. Frozen implementation identity

`freeze.sh` hashes the executable, Python analyzer modules, runtime
configuration, and pinned dependency declaration in a deterministic manifest.
It currently prints:

```text
BINDCHECK_ZK_CONTENT_SHA256=60211ab6e92d89c1361f56a89fe6f7769876702f1c3e0a0fbacdfb3ec0d2b54c
```

This is a content identifier, not a Git tag. No freeze tag was created. The
same value is embedded in all three controlling BindCheck DEV JSON results.
The runtime dependency declaration is deliberately standard-library-only;
optional external compilers and baselines are discovered and versioned at
runtime, and their absence or failure yields `UNKNOWN`.

The principal implementation files are:

- `bindcheck_zk/analyzer.py`: inventory, discovery, matching, P1/P2/P3/P5,
  aggregation, and result envelope;
- `bindcheck_zk/circuits.py`: Circom/Noir source parsing, R1CS/SYM parsing,
  bounded compilation, and named compiled-constraint paths;
- `bindcheck_zk/solidity.py`: bounded Solidity function, verifier call,
  public-vector, helper/copy, and protected-effect recovery;
- `bindcheck_zk/p4.py`: verification-key source and runtime-bytecode checks;
- `bindcheck_zk/baselines.py`: equal-envelope offline baseline adapters;
- `bindcheck_zk/subprocesses.py`: offline environment, time limits, and exact
  subprocess records; and
- `bindcheck_zk/config.json`: 2,500-file, 5 MB/file, 64-triple, 120-second
  repository, 30-second build, and two-circuit-build bounds.

## 3. Architecture

### 3.1 Input pinning and coverage

Repository mode resolves explicit paths inside the repository root, records
`git rev-parse HEAD` when available, inventories bounded non-generated files,
and hashes every retained input. Explicit `--circuit` and `--consumer` files
remain eligible even when the ordinary inventory limit would exclude their
lexicographic position. Bundle mode uses the same analyzer and additionally
extracts runtime bytecode from common Sourcify/artifact JSON fields and
`.bin-runtime`, `.runtime`, or `.runtime.hex` files. The analyzer makes no
network or RPC call.

All subprocesses run with proxy variables removed and `NO_PROXY=*`. Command,
working directory, elapsed time, stdout, stderr, exit status, and timeout state
are retained. Missing tools, parse gaps, build failures, timeouts, inventory
caps, unsupported constructs, and ambiguous matches are coverage facts and
produce `UNKNOWN`, never a pass.

### 3.2 Front ends and discovery

The circuit front end recovers Circom public declarations and `main` public
lists, and Noir `pub` parameters. Where an existing `.r1cs`/`.sym` pair is
present, or a bounded Circom build succeeds, it parses the binary R1CS header,
constraint incidence graph, and symbol table. The compiled path is accepted
only when the named private signal reaches the named commitment through
constraints inside the expected component namespace.

The Solidity front end supports common Hardhat and Foundry layouts by
inventory rather than framework assumption. It recognizes implementation and
`IVerifier`-style declarations, Groth16 and PLONK-shaped entry points,
`uint[N]`, `uint[]`, `bytes32[N]`, and `bytes32[]` public inputs, internal
verification helpers, simple array-copy helpers, local aliases, exact dynamic
length guards, and common token/NFT effects. Consumer analysis continues when
a generated verifier or circuit artifact is missing, but the affected pattern
fails closed.

Each consumer is paired with plausible circuit/verifier combinations using
path/name overlap, directory proximity, public-input counts, verifier arity,
and test/mock penalties. Every triple records the score, reasons, and
`low`/`medium`/`high` confidence. Candidates near the best score are retained
rather than silently choosing one; incompatible candidates make affected
checks `UNKNOWN`. This deliberately favors visible ambiguity over an
unjustified match.

### 3.3 Verdict aggregation

Per-triple results use only `VIOLATION`, `VERIFIED_WITHIN_SCOPE`, and
`UNKNOWN`. Aggregation is conservative: any supported `VIOLATION` dominates;
otherwise any uncertainty dominates; `VERIFIED_WITHIN_SCOPE` is returned only
when all retained results for that pattern verify the narrow stated property.
The aggregate is not an application-wide safety verdict.

## 4. Per-pattern decision rules

### P1 -- effect binding

For every recovered protected transfer/mint/burn recipient or amount, P1
resolves local aliases and asks whether the value is:

1. a direct verifier public input;
2. the caller (`msg.sender`) for a recipient;
3. the consuming contract itself for a recipient; or
4. covered by a commitment that is public, locally recomputed and guarded,
   uses a recovered hash helper/order, and has a named path through compiled
   R1CS constraints from the effect signal to that commitment inside the hash
   component.

An independently caller-selectable supported effect role is `VIOLATION`. All
roles proven by the listed mechanisms are `VERIFIED_WITHIN_SCOPE`. Missing
artifacts, assembly/delegatecall/selfdestruct, an uncompiled commitment, an
unsupported helper, or an unresolved path is `UNKNOWN`. Source-level hash
syntax alone never proves commitment binding.

### P2 -- execution-context binding

P2 verifies the narrow property when a chain ID, consuming contract address,
or explicit domain/application identifier is in the public vector, or when a
supported local guard equates it to the proof-consuming path. Merely computing
context without a guard is `UNKNOWN`; total absence is also `UNKNOWN` because
the protocol policy or deployment may not require cross-context separation.
P2 therefore does not infer a violation from absence alone.

### P3 -- field aliases and replay barriers

P3 locates replay-state mappings whose names indicate nullifier/spent/used/
replay/claimed semantics. A supported accepted path must check the same key,
consume it, and use either a field-canonical raw value (verifier or local field
guard) or a supported domain-separated/canonicalized key such as a hash or
modular expression. Missing read or write is `VIOLATION`. An unguarded raw
integer used as a Solidity replay key when the verifier accepts field
representatives is `VIOLATION` (`FIELD_ALIAS_REPLAY_KEY`). Opaque helpers and
unrecognized expressions are `UNKNOWN`; no recovered replay policy is also
`UNKNOWN`, not a claim that replay is possible.

### P4 -- verifier-key invariants

Source mode parses named gamma/delta G2 coordinates, IC points, and canonical
public-input field guards. Equal gamma and delta at the default BN254 G2
generator, duplicate IC entries, or a missing canonicality guard are E1
warnings and remain `UNKNOWN`; they are not exploit or deployment claims.
Distinct parsed gamma/delta, no duplicate IC, and a supported guard verify only
those source invariants.

The old snarkjs/ZoKrates `Pairing.P2()` generator is recognized separately.
Default-G2 constants inside that library helper do not count as key gamma or
delta. Runtime mode decodes EVM PUSH immediates, groups the four generator
coordinates by bounded bytecode proximity, and subtracts one group when a
corresponding source `Pairing.P2()` helper exists. Two remaining groups yield
the E1 `DEFAULT_G2_RUNTIME_SIGNATURE` warning; zero groups verifies only
signature absence. Ambiguous roles or incomplete bytecode are `UNKNOWN`.

### P5 -- public-input count and order

P5 compares the consumer vector, verifier arity, and circuit public signal
order. A definite count or semantic order mismatch is `VIOLATION`; compatible
fixed counts and names are `VERIFIED_WITHIN_SCOPE`. A dynamic array is verified
only for count when an exact length guard equals the verifier declaration;
unknown element meaning/order remains an explicit limitation. Missing
artifacts, multiple incompatible verifier candidates, unguarded dynamic
length, or unrecovered order is `UNKNOWN`.

## 5. Prospective development controls

`tests/controls/expected.json` contains 74 development controls: 24 inherited
Track B cases and 50 new analyzer controls. The 50 new cases cover P1 (13), P2
(8), P3 (10), P4 (9), and P5 (10), with 11 expected `VIOLATION`, 21
`VERIFIED_WITHIN_SCOPE`, and 18 `UNKNOWN` outcomes. They cover positive and
negative cases, missing artifacts, helper calls/copies, interfaces, arrays,
PLONK, runtime P4, ambiguity, unsupported constructs, inventory caps, and the
SPSC compiled-commitment regression.

Expected outcomes were committed before each corresponding implementation
rule. The oracle-only commit sequence is:

```text
81dcbbfdd14f94d36f2b080938066a4b1b00f54d  initial 40 analyzer controls + 24 Track B controls
8affad4e6b0dc0dd397deffb4b37b098f87bf72e  internal verification helper
85a3db66492904a58c7981fe952c58e7a06ecc1e  ERC-721 mint role
cbab43b2896b1c69153e1e50b5c47e409f2a56ed  helper copy and explicit over-cap paths
d0907f87c321da848375a4032b81c19d5c4148aa  replay alias and interface-only verifier
599aa2e9310b0f9533a25d4c91c9ab4e3c27498f  SPSC compiled-relation regressions
d7ad4d18257f1976b56404079ccf48c02726eb9d  test/mock verifier separation
```

The final control command passed all 74 expectations:

```text
python3 -m unittest tests.test_bindcheck_zk_controls tests.test_bindcheck_zk_cli -v
Ran 8 tests
OK
```

The eight test methods include table-driven execution of all 74 oracle rows,
CLI fail-closed behavior, bundle runtime extraction, and freeze/result hash
agreement.

## 6. DEV results

The controlling run is
`results/raw/T23/run-20261104T030439Z-3115/manifest.json`. It pins all commands,
three repository revisions, elapsed times, exit statuses, JSON hashes, and full
coverage. All three expected P1 outcomes match.

| DEV case and revision | Discovery and coverage | P1 result | Other pattern results |
| --- | --- | --- | --- |
| SPSC `6d07155ecf295e6d68936bf424557621d0c66456` | 128 files; 16 Solidity; 1 circuit, 1 verifier, 1 consumer, 1 medium-confidence triple; one R1CS built; 0 skips/failures/timeouts | `VERIFIED_WITHIN_SCOPE` E1, `EFFECT_VALUES_BOUND_BY_COMPILED_COMMITMENT` | P2 `UNKNOWN`; P3/P4/P5 `VERIFIED_WITHIN_SCOPE` |
| RacePass `abd54b5c541ac9d26f938a6bdbd78545526249e5` | 105 files; 15 Solidity; 2 circuits, 3 verifiers, 1 consumer, 6 low-confidence triples; 1 large file skipped; 2 circuit builds failed on missing relative includes; 0 timeouts | `VIOLATION` E1, `UNBOUND_EFFECT_RECIPIENT` | P2/P3/P4/P5 `UNKNOWN`; P4 includes one duplicate-IC warning and clean-key candidates |
| ZKredential parent `23917814522bac494150c7e99a123aa15a448155` | 2,500-file cap; 569 Solidity; 1 explicit circuit, 4 low-confidence verifier candidates, 1 consumer, 4 triples; 7,931 later files skipped; 1 missing-include build failure; 0 timeouts | `VIOLATION` E1, `UNBOUND_EFFECT_AMOUNT` | P2/P4/P5 `UNKNOWN`; P3 `VERIFIED_WITHIN_SCOPE` for the hashed, checked, consumed replay key |

The SPSC build used Circom 2.2.3 and produced 59,910 constraints and 13 public
inputs. P1 recovered an 85-wire named constraint path from `main.recipient` to
`main.extDataHash` within `main.extDataHasher`, plus the local consumer guard
and hash helper. The two failing RacePass builds and the ZKredential build
failure remain recorded coverage limitations; neither was converted into a
pass. RacePass P1 does not require the failed commitment path because the
caller-selected mint recipient is visibly absent from both recovered proof
vectors. ZKredential P1 similarly identifies the caller-selected mint amount,
while the recipient is locally constrained to `msg.sender`.

The ZKredential checkout is a large hackathon monorepo. Its four retained
verifier candidates are unrelated OpenZeppelin/mock files with low confidence;
the generated Groth16 implementations are absent. Consequently P4 and P5 stay
`UNKNOWN`. P1 is reported only as a supported consumer/vector dataflow result,
not as verifier correspondence. This is an important matching limitation, not
evidence that those four verifier files belong to ZKredential.

## 7. DEV baseline results

The adapters use the same input manifest and JSON envelope, retain native
stdout/stderr/exit semantics, and map every non-comparable integration result
to `UNKNOWN`. Baseline diagnostics are not automatically relabeled as P1--P5
annotations.

Installed versions were Slither 0.11.3, Circomspect at Git commit
`50010b623ed4f3bff9d1b0363cfe952385b47af3`, and Picus at Git commit
`138b151d3a388e5b6c040c163e0a1db04f2ceda6`. Picus used Racket 9.3, cvc5
1.4.2, and Z3 4.15.3. ZKAP was not installed: its documented Ubuntu/x86-64
Docker workflow and resource envelope were unavailable on this arm64 macOS
host, and Docker was absent. It is recorded as `BASELINE_TOOL_UNAVAILABLE`,
not silently omitted.

| Case | Slither | Circomspect | Picus | ZKAP | BindCheck P1 |
| --- | --- | --- | --- | --- | --- |
| SPSC | completed, exit 255, 2 native findings; P1--P5 `UNKNOWN` | completed, exit 1, CS0010; P1--P5 `UNKNOWN` | preprocess 0, exit 8 (native properly constrained); P1--P5 `UNKNOWN` pending adjudication | unavailable; `UNKNOWN` | `VERIFIED_WITHIN_SCOPE` |
| RacePass | completed, exit 255, 55 native findings; P1--P5 `UNKNOWN` | two exit-1 parse/include failures; `UNKNOWN` | two preprocess-0 / exit-8 results; P1--P5 `UNKNOWN` pending adjudication | unavailable; `UNKNOWN` | `VIOLATION` |
| ZKredential | completed, exit 255, 7 native findings; P1--P5 `UNKNOWN` | completed, exit 1, CS0006; P1--P5 `UNKNOWN` | preprocess 0, exit 0 (native cannot determine); P1--P5 `UNKNOWN` | unavailable; `UNKNOWN` | `VIOLATION` |

This table is a development comparison, not a scored benchmark. Slither and
Circomspect report within their native consumer-only and circuit-only scopes;
Picus reports circuit constraint status; none of these outputs alone adjudicates
cross-layer P1--P5. ZKAP remains unrun, and no performance or superiority claim
follows.

## 8. Known false-positive and false-negative sources

- The source front ends are balanced-token/regular-expression parsers, not
  complete Solidity, Circom, Noir, or EVM semantics. Macros, inheritance,
  modifiers, complex overloads, inline assembly, indirect storage, and deeper
  interprocedural paths can be missed or conservatively rejected.
- Helper support is intentionally shallow. Multi-hop dispatch, verifier
  registries, factories, proxies, delegatecall, Yul, and generated-at-build
  implementations can leave correspondence `UNKNOWN`.
- Triple scoring is heuristic. Large monorepos can retain unrelated low-score
  verifier candidates, while unconventional names/layouts can hide a true
  match. The score and all alternatives are exposed for author review.
- Protected-effect recognition covers common transfer/mint/burn spellings and
  positional roles. Custom wrappers, non-token effects, overloaded semantics,
  authorization policies, and rollback through external calls are outside the
  current proof boundary.
- Compiled commitment validation checks named constraint connectivity and an
  expected namespace, not full algebraic equivalence of the circuit and
  Solidity hash implementation. Compiler-version drift, missing includes, or
  stripped symbols can cause false `UNKNOWN`; connectivity can still be too
  weak for adversarially unusual circuits.
- P2 recognizes a bounded vocabulary and cannot decide whether a protocol
  policy actually requires chain/contract/application separation.
- P3 is local to supported mapping reads/writes. Modifier- or helper-mediated
  replay barriers, state machines, bitmap schemes, and unusual canonicalization
  can be missed. A name-based candidate can also overapproximate replay intent.
- P4 source parsing assumes recognizable generated-verifier constant layouts.
  Runtime PUSH grouping is an E1 signature heuristic, sensitive to optimizer
  layout and inlining. Signature absence is not verifier correctness, and a
  source warning is not deployment or key/circuit correspondence.
- P5 semantic order comparison uses recovered names after cast normalization.
  Semantically equivalent renaming can become `UNKNOWN` or a false mismatch;
  dynamic arrays generally expose count but not element meaning.
- Repository bounds can omit relevant files. Explicit targets bypass the
  ordinary position cap, but discovery outside them does not. All cap effects
  are reported.

## 9. `UNKNOWN` by design

The analyzer intentionally returns `UNKNOWN` for missing circuit or verifier
artifacts, unresolved generated verifiers, ambiguous matches, failed/timed-out
builds, unsupported assembly/delegatecall/selfdestruct, opaque replay helpers,
dynamic arrays without exact guards, unrecovered public-input order, context
absence without a policy, incomplete P4 key/bytecode parsing, and all source or
runtime P4 warning signatures that lack higher-grade validation. Baseline
absence, native findings, failure, timeout, and non-comparable scopes are also
`UNKNOWN`.

`VERIFIED_WITHIN_SCOPE` never means application safety. It names only the
specific parsed property, artifacts, function, effect roles, and supported
execution/dataflow subset recorded in that result. `VIOLATION` is likewise an
E1 static finding here unless a separate immutable report records higher-grade
proof/replay/effect evidence.

## 10. Commands and observed results

```text
python3 -m unittest tests.test_bindcheck_zk_controls tests.test_bindcheck_zk_cli -v
# exit 0; 8 test methods; all 74 control outcomes exercised; OK

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
# exit 1; 146 run, 9 failures, 25 errors, 1 skip; 0 bindcheck-zk failures

python3 -m compileall -q bindcheck_zk tests
# exit 0

python3 scripts/run_bindcheck_zk_dev.py
# exit 0; 15 JSON results + manifest; three fixed DEV P1 expectations matched

./freeze.sh
# exit 0; BINDCHECK_ZK_CONTENT_SHA256=60211ab6e92d89c1361f56a89fe6f7769876702f1c3e0a0fbacdfb3ec0d2b54c

git diff --check
# exit 0
```

An attempted metadata/help check accidentally invoked
`python3 scripts/run_bindcheck_zk_dev.py --help`; the runner has no argument
parser, so it began a duplicate DEV run. It was stopped by exact PID during
ZKredential analysis. Its partial ignored namespace
`results/raw/T23/run-20261104T030035Z-1983/` is preserved, has no manifest, and
is not controlling evidence. No EVAL input was involved. An earlier toolchain
setup wrapper also stopped after successful builds because a `--help | head`
pipeline met `pipefail`; subsequent direct version and artifact checks
confirmed the required local tools. An initial full-suite invocation omitted
the documented `PYTHONPATH=src` and therefore produced import errors; the
corrected command above ran 146 tests. Its 9 failures and 25 errors arise from
unavailable ignored/generated Noir and historical D2 artifacts, external
preservation-checkout paths, tool binaries, and the already documented live
D2 replay mismatch; one owned-local WarpToad test skipped. All eight
`bindcheck-zk` test methods passed within that same corrected run. These
unrelated prerequisites were not reconstructed or rewritten. Circomspect's
RacePass include failures and all analyzer build failures remain in their JSON
records.

## 11. Evidence and next task

- Controlling raw evidence:
  `results/raw/T23/run-20261104T030439Z-3115/`
- Exact command/result/hash ledger:
  `results/raw/T23/run-20261104T030439Z-3115/manifest.json`
- Development oracle: `tests/controls/expected.json`
- Immutable task record: `reports/T23.md`

The recommended next task is an independent author review of all 50 new
control labels, the three DEV JSON results, and the stated P1--P5 boundaries.
Its measurable completion criterion is a signed review record with every
control and every non-`UNKNOWN` DEV result accepted, corrected prospectively,
or rejected without changing held-out data. Only after that review should this
exact content hash be frozen operationally and run once on the family-separated
held-out EVAL corpus. The held-out task is complete only when every scheduled
case has a schema-valid JSON result, all timeouts/failures remain `UNKNOWN`,
coverage is reported, and no rule or threshold is changed after EVAL access.

## 12. Full-DEV coverage and adjudication

**Update date:** 2026-11-04 (America/Los_Angeles; controlling evidence dated
2026-11-05 UTC)

**Task:** T24

This section supersedes the T23 hash, control count, and three-row-only DEV
coverage statements for freeze readiness. It does not alter or erase the T23
evidence above. The complete immutable account is [reports/T24.md](reports/T24.md),
the per-row table is
[reports/T24-full-dev-ledger.csv](reports/T24-full-dev-ledger.csv), and the
author warning review is
[reports/T24-warning-adjudication.csv](reports/T24-warning-adjudication.csv).

### 12.1 Unhinted full-DEV result

`scripts/run_bindcheck_zk_full_dev.py` analyzed every authorized DEV checkout
without `--circuit` or `--consumer`. It reconstructs the 56-row DEV set without
opening the mixed source-corpus ledger or recall set. The controlling before
and after directories are:

```text
results/raw/T24/before-20261105T020201Z-27822/
results/raw/T24/after-20261105T023639Z-38427/
```

| Coverage measure | Before | After |
| --- | ---: | ---: |
| completed / crashed | 56 / 0 | 56 / 0 |
| rows with at least one triple | 11/56 (19.6%) | 46/56 (82.1%) |
| triples | 105 | 489 |
| successful circuit builds | 19/88 (21.6%) | 45/76 (59.2%) |
| cap-affected rows / files | 1 / 4,061 | 1 / 3,503 |
| P1 `UNKNOWN` | 82.1% | 91.1% |
| P2 `UNKNOWN` | 100.0% | 98.2% |
| P3 `UNKNOWN` | 91.1% | 76.8% |
| P4 `UNKNOWN` | 91.1% | 58.9% |
| P5 `UNKNOWN` | 94.6% | 92.9% |

The P1 increase is not a safety regression: the analyzer now retains
verify-only and custom-effect consumers for visible `UNKNOWN` coverage rather
than silently dropping them. The final run's slowest row took 35.466 seconds,
within the 120-second repository bound. Remaining build failures are 20
missing includes/files, six parse/type failures, four other nonzero exits, and
one timeout. They remain `UNKNOWN`.

All three named DEV expectations hold without hints: RacePass and
ZKredential are P1 `VIOLATION`; SPSC is P1
`VERIFIED_WITHIN_SCOPE` through a compiled commitment path.

### 12.2 Coverage architecture changes

The inventory now excludes dependency/frontend/build/vendor/test-fixture
trees before counting and prioritizes Circom, Noir, Solidity, manifests, and
lockfiles. Every exclusion and cap effect appears in JSON and the tracked
ledger. The sole capped row is the F30 hackathon monorepo; its relevant
ZKredential files survive priority selection.

Circom include resolution now recursively follows circuit-relative,
dependency-relative, package/lockfile, repository `node_modules`, and common
monorepo layouts. An absent circomlib dependency may fall back only to the
locally vendored `circomlib@2.0.5` whose package and 144-file tree hashes are
pinned in `bindcheck_zk/vendor-lock.json`. The final run records 155 vendored
resolutions across 27 rows. Other unavailable libraries remain explicit
unresolved includes.

Generated-verifier recovery is offline and allowlisted. It requires both a
repository-defined complete fresh setup/export recipe and a compiled R1CS;
arbitrary repository scripts are never executed. Three final rows had no
recipe and one had no compiled R1CS, so no verifier was regenerated and those
paths remain `UNKNOWN`.

Matching now uses uncapped internal scores for pruning and capped scores only
for JSON display. Entry circuits, main-template scope, receiver types,
verifier wrappers, test/mock sources, exact dynamic allocations, and generated
artifacts are handled explicitly. Temporary build artifacts are cleaned after
each run.

### 12.3 Revised pattern decisions

- P1 distinguishes ERC-721 token IDs, storage/configured values, opaque
  structs, and derived effects from independently caller-selected transfer
  roles. Unsupported transformations are `UNKNOWN`, not violations.
- P3 parses nested mapping keys, recognizes helper barriers and read-only
  verifier utilities, and follows bounded alias/equality flow from replay keys
  to verifier inputs. A consumed caller key with no recovered verifier binding
  is `REPLAY_KEY_NOT_BOUND_TO_PROOF`; unsupported helper/expression flow stays
  `UNKNOWN`.
- P4 accepts direct and alias-based rejecting scalar guards, distinguishes
  delegated helpers and fail-closed placeholders, and returns unsupported-key
  layout `UNKNOWN` for Honk/custom/STARK families instead of applying a
  Groth16-specific warning.
- P5 reports count mismatch only from a complete source interface or compiled
  relation. An equal-name permutation is a violation; semantic renaming is
  `UNKNOWN`. Candidate-score saturation no longer retains materially worse
  circuit matches.

### 12.4 Controls, warnings, and baselines

The prospective oracle now has 105 rows: the unchanged 24 Track B controls
and 81 analyzer controls covering all five patterns. Oracle-only commits
precede every new rule. Both plain unittest forms pass, including on this host
where a site-packages package named `tests` previously shadowed the repository:

```text
python3 -m unittest tests.test_bindcheck_zk_controls tests.test_bindcheck_zk_cli -v
# Ran 8 tests; OK

python3 -m unittest discover -s tests -p 'test_bindcheck_zk*.py' -v
# Ran 8 tests; OK
```

The final warning inventory contains 15 grouped rows / 49 triple instances:
13 groups are true positives for the stated source property, two F38
field-alias groups are unclear because verifier correspondence is ambiguous,
and none is a retained false positive. The adjudication does not promote E1
source evidence to an exploit or deployment claim. Every false-positive class
encountered during DEV review was repaired generally with a prospective
control; the exact classes and source reasons are recorded in T24.

The T23 equal-envelope Slither/Circomspect/Picus comparison remains the
baseline evidence; no full-DEV baseline campaign was rerun in T24. ZKAP remains
unavailable. These consumer-only/circuit-only baselines cannot independently
decide cross-layer P1–P5 and no superiority claim is made.

### 12.5 Remaining `UNKNOWN` and freeze identity

Fifteen percent of rows still have no triple, only 59.2% of attempted circuit
builds succeed, P2 policy is usually absent, P5 semantic order is usually
unrecoverable, custom effects/helpers are bounded, and verifier/key/circuit
correspondence is often ambiguous. These conditions are `UNKNOWN` by design;
timeouts, build failures, missing artifacts, unsupported layouts, and caps
never become passes.

The final content identity includes the analyzer, configuration, pinned
dependency declaration, and vendor lock:

```text
BINDCHECK_ZK_CONTENT_SHA256=d8510859b918a5166d0f1629cf0d883e965fa0acb1be92a34987c24f1967ae13
```

No tag was created. Any subsequent change to the hashed files requires a new
hash and a new freeze review before the one-shot held-out run.
