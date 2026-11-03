# D2-19 — partial development artifact and reproduction record

Date: 2 November 2026

Status: **PARTIAL_DEVELOPMENT_ARTIFACT / FINAL_ARTIFACT_BLOCKED**

Research verdict: **UNKNOWN**

Gate state: **Gate A `INCONCLUSIVE`; Gate B `NOT_EVALUATED`; Gate C
`NOT_REACHED`**

## 1. Outcome and boundary

This step provides a fail-closed, development-only artifact for inspecting the
versioned D2-00 through D2-10 record, the Steps 11–17 non-execution
dispositions, and the Step 18 status manuscript. It is not a frozen Gate B
release, reserved evaluation package, anonymous submission artifact, or final
paper artifact.

The artifact adds no analyzer result, baseline result, score, human judgment,
policy adoption, adjudication, proof, compiler result, reserved access, or
security verdict. It creates no `results/raw/D2-19` namespace. The retained raw
evidence and a complete reviewed sidecar are deliberately not copied into the
repository. Fresh mechanical runs write only to an unused direct child of
`artifact/work/`, which is ignored.

## 2. Package

The 85,890-byte checked-in package is rooted at `artifact/`. `SHA256SUMS`
binds every regular package file other than itself, excluding ignored
`artifact/work/` outputs and Python caches. The manifest separately binds 53
controlling tracked inputs at base commit
`544656abbfb535dcbe0f1157087240464f38cb0b` plus the individually hashed
worktree overlay. This is a content binding, not a clean-worktree or release-tag
claim.

| File | Purpose | SHA-256 | Bytes |
|---|---|---|---:|
| `artifact/.gitignore` | exclude fresh work and local sidecars | `b35a1dd0e22e99659e9765055021476e5b0625b2816b7b7f2f8887e31677dd8c` | 17 |
| `artifact/README.md` | evaluator commands and interpretation | `4847c92b149e87921683446d8f5caf586f9c6264928d75cdf93910c06c7caa41` | 5,761 |
| `artifact/STATUS.json` | exact artifact and gate status | `240186165c38cf7670e7d6d4387a7916f82bb712bfa1ac575ad76665dd3edb1c` | 1,080 |
| `artifact/THIRD_PARTY.md` | dependency and redistribution boundary | `52b2f6424e92cce6f325f6a28db34e4e57d6fd0ebdb83edeb71fc72dd9c09938` | 2,000 |
| `artifact/expected-results-v1.json` | selected categorical/count oracle and excluded fields | `c2e63a5a44bd05242a2c270c3f2737c94a2fd6a3e42fa245650ea7b5c67897b0` | 5,925 |
| `artifact/input-inventory-v1.json` | retained/sidecar byte contract and seal bindings | `bdff015329cdf27750f7329fb979062ae92b9132eb06e8ee5be35f9d63c9fda7` | 7,943 |
| `artifact/manifest-v1.json` | tracked source/report/protocol bindings | `b0ecbd8d90df73a008915cd2234fa9ebc12bb03bc85975af00ef2570efe34a02` | 9,748 |
| `artifact/platform-matrix-v1.json` | profile portability and blockers | `d6ee6834075f2c7d4e2db7c152fbfc599669c0529ad62e161c3a80cb0963c4c9` | 2,605 |
| `artifact/reproduce.py` | standard-library fail-closed driver | `1973a850466aee837fbd05c14bac216f424c95db3fa0eb6c0c1d3f3bbe9d6d91` | 44,651 |
| `artifact/test_reproduce.py` | path, sidecar, mismatch, overlay, and status tests | `d7947206721d1d88668d5d3bd694bd60ed1876785c4464c248af7abce0cf573b` | 5,241 |
| `artifact/SHA256SUMS` | package checksum list | `7d11a8d8f646f0f08c756ab58f193c9ce52e8c3b16efd9f53ce790847081dc38` | 919 |

The report is intentionally outside the self-bound package and is not included
in its own hash graph.

## 3. Profiles and observed results

The following commands were run from the repository root with
`PYTHONDONTWRITEBYTECODE=1`:

```sh
python3 artifact/reproduce.py metadata
python3 artifact/reproduce.py verify-retained --source current-workspace
python3 artifact/reproduce.py recompute --source current-workspace
python3 artifact/reproduce.py rerun-mechanical \
  --source current-workspace --run-id step19-validation-04
```

All four profiles returned `PASS`.

- `metadata` verified 10 package members, 53 tracked bindings, and Step 18's
  20 claims (13 supported, three contradicted, four unresolved), 17 claim-map
  entries, five closest works, and eleven primary-source records.
- `verify-retained` verified nine external D2-01 inputs and the authoritative
  D2-07, D2-08, D2-09, and corrected D2-10 seals at 623/623, 92/92, 40/40,
  and 9/9 respectively. Nine headline retained hashes also matched.
- The direct live D2-01 replay returned the required `EXPECTED_FAIL` with
  exactly one of 8,134 members different:
  `src/bindcheck_d1/role_binding.py`, sealed as
  `a516f0e339f6fec23fcd96efb52821e9933feb6837e740c99a6d5dbee7bd9028`
  (41,698 bytes) and currently
  `5bb3012b7d192e75e266cc3f5265e024046e8614c0cb63891c7acd5271eeaa71`
  (43,263 bytes). Step 8 deliberately quarantined the historical
  name-dependent behavior.
- The non-destructive wrapper then read the exact historical byte from Git
  object `544656abbfb535dcbe0f1157087240464f38cb0b` in memory and reproduced a
  D2-01 historical overlay `PASS` at 8,134/8,134 with one substitution and
  zero mismatches. This does not establish current-checkout equivalence or a
  current capability result. The separate D2-00 pre-report status-document
  byte remains `UNAVAILABLE_RETENTION_GAP_NOT_RECONSTRUCTED`.
- `recompute` reproduced all selected D2-00 through D2-10 counts and
  categorical states, both downstream non-execution dispositions, and the
  Step 18 counts. Research remained `UNKNOWN`.
- The fresh mechanical profile reproduced five Step 8 identity bundles and
  its name-influence `PASS`; Step 9's ten effective `UNKNOWN` rows with
  mechanical states 1 `ESTABLISHED`, 2 `MISMATCH_CANDIDATE`, and 7 `UNKNOWN`;
  and corrected Step 10's 16 fact-type rows, zero producer guarantees, zero
  eligible derived consumer-use facts, seven semantic controls, three
  adversarial controls, and five D1P-40 regressions. These are
  `UNREVIEWED_DEVELOPMENT_FIXTURE` results, unscored and not security
  findings.

Fresh equality deliberately excludes only the fields enumerated in
`expected-results-v1.json`: timestamps, elapsed/runtime/machine time, human
time, absolute and temporary paths, platform/Python strings, repository
branch/dirty/commit metadata, path- or timing-bearing stdout/stderr hashes,
and fresh transitive seal hashes. Retained sealed evidence remains byte-exact.

## 4. Explicit sidecar route

A fresh evaluator can run `metadata` with only a normal source checkout. An
evaluator with a separately reviewed, pre-extracted sidecar can run:

```sh
python3 artifact/reproduce.py verify-retained \
  --source sidecar --sidecar-root /absolute/path/to/sidecar
python3 artifact/reproduce.py recompute \
  --source sidecar --sidecar-root /absolute/path/to/sidecar
```

The driver never downloads or extracts the sidecar. It maps repository-relative
ignored evidence, sibling `BindCheck` inputs, the pinned absolute solc input,
and the 41,698-byte historical role-binding member through the explicit layout
in `input-inventory-v1.json`. It rejects a relative or symlinked sidecar root,
path escape, unknown absolute input, missing file, duplicate member, or hash or
size mismatch. The interface received known-answer coverage; an end-to-end
sidecar profile was not run because no second 314.22 MiB sidecar was copied for
this task.

The known retained D2 namespaces occupy 36,364,095 bytes (34.68 MiB). The
deduplicated complete known offline development set is 329,481,710 bytes
(314.22 MiB), before a source checkout and fresh work output. At least 1 GiB
of free disk is recommended. No defensible peak-memory bound was recorded.

## 5. Test and integrity checks

Focused validation:

```sh
PYTHONPATH=src python3 -m unittest \
  artifact/test_reproduce.py \
  tests/test_d2_d201_post_step8_replay.py \
  tests/test_d2_step8_identity.py \
  tests/test_d2_step9_authorization_boundary.py \
  tests/test_d2_step10_typed_extraction.py
```

Result: **46/46 PASS**.

Full repository validation:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test*.py'
```

Result: **151/151 PASS**. Artifact JSON parsing, manifest/hash replay, Python
AST parsing, and `git diff --check` also passed. No network command, compiler,
prover, analyzer, baseline, score, or reserved-data route ran during the
artifact profiles.

## 6. Portability and final-artifact blockers

The generic-container D2-01 and D2-06 rerun is intentionally not implemented.
Those records bind ignored inputs, sibling checkout paths, Darwin ARM binaries,
and absolute `/Users/...` compiler paths; no reviewed Linux-equivalent offline
image or toolchain digest exists. The historical `scripts/artifact` tree is a
networked D1 workflow and is not this reproduction route.

A final artifact remains blocked by, at minimum:

- missing Gate B execution and frozen release criteria;
- missing Gate C and reserved-transfer execution;
- absent human policy authorship/adoption, distinct review, taxonomy ratings,
  adjudication, coauthor review, and named custody/release approval;
- missing privacy, licensing, attribution, anonymity, disclosure, and binary
  redistribution review for any public sidecar;
- no portable generic D2-01/D2-06 build and run environment; and
- research verdict `UNKNOWN`, with no scored comparison or supported transfer
  result.

Nothing in this package converts `UNKNOWN`, unsupported, unexecuted, or
mechanical-only evidence into safety, detection performance, generality,
novelty, superiority, or submission readiness.
