# BindCheck D2 partial development artifact

Status: **PARTIAL_DEVELOPMENT_ARTIFACT / FINAL_ARTIFACT_BLOCKED**

This package verifies and recomputes the current D2 development record. It is
not a frozen Gate B release, a reserved evaluation package, an anonymous
submission artifact, or a final paper artifact. Gate A is `INCONCLUSIVE`, Gate
B is `NOT_EVALUATED`, Gate C is `NOT_REACHED`, and the research verdict is
`UNKNOWN`.

## Safety boundary

- No command performs network access.
- No command reads or reconstructs reserved/private inputs.
- The runner never writes under `results/raw/` and never overwrites an output.
- Fresh mechanical output is allowed only below `artifact/work/<run-id>/`.
- D2-01 and D2-06A/06B full reruns are intentionally not implemented because
  their frozen protocols bind Darwin binaries, absolute user paths and ignored
  inputs. Missing support is reported as blocked, not as a successful result.
- Human annotations, policy adoption/review, scoring and adjudication are
  retained dependencies, not reproducible computations.
- A fresh AI session is an engineering reproducer, not an independent human
  replication.

## Requirements

The metadata profile uses Python 3.10 or newer and the standard library. The
retained-verification and recomputation code has no third-party Python
dependency; the current-workspace route also needs local Git to read the pinned
historical object, while the explicit sidecar supplies that byte directly.
Mechanical reruns require the exact current source workspace, Git metadata and
the retained development inputs. They run the unscored Step 8–10 fixtures only.
The repository's broader Python suite uses `pycryptodome==3.23.0`; `pytest` is
not required.

## Profiles

From the repository root:

```sh
python3 artifact/reproduce.py metadata
python3 artifact/reproduce.py verify-retained --source current-workspace
python3 artifact/reproduce.py recompute --source current-workspace
python3 artifact/reproduce.py rerun-mechanical \
  --source current-workspace --run-id fresh-01
```

For an explicitly supplied, already reviewed and safely extracted sidecar:

```sh
python3 artifact/reproduce.py verify-retained \
  --source sidecar --sidecar-root /absolute/path/to/sidecar
python3 artifact/reproduce.py recompute \
  --source sidecar --sidecar-root /absolute/path/to/sidecar
```

The runner does not extract archives. The sidecar layout and required byte
classes are defined in `input-inventory-v1.json`. A missing file, hash or size
mismatch, unrecognized status, incomplete seal, forbidden output path, existing
run directory, or unsupported profile exits nonzero.

The explicit sidecar carries the 41,698-byte historical role-binding member at
the path declared in the inventory, so a shallow evaluator checkout need not
silently substitute a different Git object. The byte is verified before use
and is never written into the checkout.

## What each profile establishes

`metadata` verifies the artifact's own checksum list, schemas, exact status,
controlling tracked-file bindings, Step 18 counts and the absence of any final
artifact claim. It does not inspect raw evidence.

`verify-retained` additionally replays the D2-01 input seal, D2-01 external
input manifest, D2-07 authoritative seal, and D2-08–10 seals against either
the current development workspace or an explicit sidecar. The live D2-01
replay must produce exactly the one expected mismatch at
`src/bindcheck_d1/role_binding.py`: Step 8 deliberately quarantined the old
name-derived behavior. The profile then supplies the exact sealed byte from
Git object `544656abbfb535dcbe0f1157087240464f38cb0b` in memory and requires the
historical overlay replay to pass 8,134/8,134. The independent wrapper is:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/d2_d201_post_step8_replay.py
```

Its historical PASS is not current-checkout equivalence and does not rescore
or relabel D2-01. The unrelated unavailable pre-report D2-00 status-document
byte remains `UNAVAILABLE_RETENTION_GAP_NOT_RECONSTRUCTED` and is not overlaid.

`recompute` first performs retained verification, then recomputes the selected
categorical and count results in `expected-results-v1.json`. It does not rerun
compilers, analyzers, baselines, proofs or human judgments.

`rerun-mechanical` validates Gate A's blocked state and runs the Step 8, Step 9
and corrected Step 10 unscored fixtures into a new
`artifact/work/<run-id>/` directory. It compares only the declared categorical
fields. Timestamps, runtime, absolute paths, platform strings, Git dirty
metadata, compiler log bytes and fresh transitive seal hashes are deliberately
not compared. The original retained seals remain the exact historical record.

## Expected results and limits

`expected-results-v1.json` is the machine-readable source for every expected
count and categorical result. Headline expectations include D2-01's 49 rows
and 17/13/0/26 integrated result; zero Gate A scored arms; five Step 8 bundles;
ten Step 9 effective `UNKNOWN` rows; and corrected Step 10's zero relational
producer guarantees and zero eligible derived consumer-use facts.

The final Step 18 package remains an evidence-led status draft with 20 ledger
claims, 17 claim-map entries, five closest works and eleven primary-source
records. It is `NOT_SUBMISSION_READY`.

The complete known offline development byte set was measured at 314.22 MiB
before a source snapshot and fresh workspace outputs. It is deliberately not
copied here. Use at least 1 GiB of free disk for any locally assembled sidecar
and fresh workspaces. No defensible peak-memory bound was recorded.

See `THIRD_PARTY.md`, `platform-matrix-v1.json`, and
`reports/D2-19-artifact.md` for the release, portability and claim boundaries.
