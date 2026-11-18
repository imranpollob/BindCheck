# BindCheck reproducibility artifact

## EuroS&P paper tables (PP)

From the repository root, run the following with GNU Make and Python 3.12.

```sh
make paper-tables
python3 -B scripts/paper/check.py
```

The commands directly reaggregate tracked evidence and typically finish in
under a second per command on the PP Linux host. The build produces ten
booktabs tables and one macros file under [paper/generated](paper/generated/),
each with a companion JSON. The JSON identifies the input paths, their
SHA-256 digests, the parser used, and the values behind the table. The checker
regenerates the expected bytes in memory and fails for a missing, extra, or
stale generated TeX or JSON file. An absent S1 generator CSV produces a
visible TODO and an explicit missing-input record.

Load `booktabs`, input `paper/generated/numbers.tex` once, and input individual
table fragments from the manuscript. Each fragment provides its own
`tabular`. The manuscript supplies captions and any float wrappers. Adjust
paths relative to the TeX build directory. Select the prose macros by their
definitions in [numbers.json](paper/generated/numbers.json). The PP tables
cover R1, R2, AZ1, freeze-2 DEV, the spent-family S2a comparison, the S4 oracle
and the optional S1 census. The manuscript and its historical tables have their
own sources. See the [source inventory](reports/PP/INVENTORY.md) and
[discrepancy record](reports/PP/DISCREPANCIES.md).

### Linux toolchain and analyzer checks

The table commands require no network or proving tools. For execution checks,
use the Linux x86-64 setup on an artifact-review machine with the prerequisite
Git, Rust/Cargo, Node/npm, curl and archive tools. Provision the pinned tools
and per-checkout npm dependencies while online or from a prepared mirror.

```sh
export BINDCHECK_TOOLS="$PWD/tools"
bash scripts/setup_linux_tools.sh --skip-optional
```

Allow several minutes for a fresh Rust build and downloads. This is a planning
estimate. T0 documents the expected tool versions and the known partial
setup exit 3 for the missing Payy native Barretenberg pin. Inspect the report
and setup output before proceeding. The test paths below use Circom, Node and,
for execution, Foundry and solc. The Payy native binary is outside those test
paths. [T0 report](reports/T0/REPORT.md)

On the S2a revision 1 candidate, run from the repository root.

```sh
export BINDCHECK_CIRCOM="$BINDCHECK_TOOLS/circom-2.1.9/target/release/circom"
python3 -B -m unittest -v tests.test_bindcheck_zk_cli \
  tests.test_bindcheck_zk_controls tests.soundness.test_verdict_soundness \
  tests.soundness.test_followup tests.coverage.test_rules \
  tests.freeze2.test_p4_key tests.s2a.test_precision_fixes
```

PP observed 58 passing tests in about five seconds with Circom 2.1.9 and
the root lockfile dependencies available. The analyzer identity reproduced in
the PP output describes the historical candidate whose results were tabulated.
[S2a revision 1 report](reports/S2a/REPORT.md#revision-1--spent-family-rerun-and-semantic-exclusion-refactor)

### AZ1 synthetic testbed

Use the historical AZ1 checkout at `ec688bb41e5e9c9f5a4989bdff1cba0e6dde9a33`.
The test entry point, `bash prototypes/az1/run.sh`, checks the analyzer against
the freeze-2 hash and expects the root npm dependencies in that checkout.
Reusing the reviewer machine's installed tools is fine if the hashes match.
AZ1 requires the recorded Circom 2.2.3 binary, Foundry 1.4.1-stable, Slither
0.11.3 with crytic-compile 0.3.11, and the pinned Linux solc 0.8.11 at
`~/.solc-select/artifacts/solc-0.8.11/solc-0.8.11`. Keep `BINDCHECK_TOOLS`
pointing to the installed tool directory. Budget several minutes for setup
and proving with dependencies available. The report records 53 steps and
zero failures without a total wall time. Expected outputs are a fresh
`results/raw/AZ1/az1-*/` directory with `steps.tsv`, `environment.txt`, a
checksum manifest and the detector summary. The testbed uses an owned
synthetic fixture. The historical real-target comparison is available as
tracked report evidence for the table build. [AZ1 report](reports/AZ1/REPORT.md)

### Oracle control

Run the local bound control with Node/npm, Foundry 1.4.1-stable and the
fixture's solc 0.8.20 available. The driver caches ethers 6.13.4 under
`results/raw/S4/.driver/` and needs npm access on first use if that cache and
its dependencies are absent. From the repository root, choose a fresh output
directory each time.

```sh
python3 -B -m oracle run tests/oracle/bound.manifest.json \
  --out "results/raw/S4/artifact-bound-$(date -u +%Y%m%dT%H%M%SZ)"
```

Expect `result.json`, a variant result and per-step logs. The bound control
should complete with the honest reference successful and no confirmed
violation. Recorded full-run times for this control are about two to three
minutes, depending on the revision. The real-case matrix is regenerated
from the reviewed S4 reports. Re-execution of those cases depends on
release approval and on access to the reviewed case artifacts and toolchain.
[Oracle documentation](oracle/README.md) · [S4 report](reports/S4/REPORT.md) · [S4b report](reports/S4/REPORT-S4b.md)

### Public artifact data boundary

Exclude `dataset/onchain-census.csv`, deployment addresses drawn from it,
and nonpublic disclosure material from the public distribution. Any step
that needs row-level deployment data, including an independent regeneration
from that census, requires an approved private copy. The PP pipeline needs
only its listed evidence sources. Review real-case S4 report inputs and
generated rows for release approval when assembling the public package.
Keep the spent-family outputs labeled as DEV.

## Historical D1P-34 and X-AV artifact

This artifact reconstructs the ignored inputs needed by the frozen BindCheck
v1.1 tests, the D1P-34 30-mutant evaluation, and the X-AV validation driver.
It fetches only pinned public upstream revisions/tool releases, records every
command and hash in `results/raw/artifact-tools/input-materialization.json`,
and keeps all downloads and generated evidence under ignored `results/raw/`.
It does not modify `src/`.

## Requirements

The reviewed binary pins target an Apple-silicon Mac:

- macOS arm64 with Rosetta 2 (the official Solidity 0.8.20/0.8.29 macOS
  binaries are x86-64); 16 GiB RAM and about 8 GiB free disk;
- Python 3.10 or newer, Git, `curl`, Node.js 22 or newer, and npm;
- outbound HTTPS to GitHub releases/repos, the npm registry, and
  `crs.aztec-cdn.foundation` during setup; and
- no concurrent `bb` or `nargo` proving jobs for the validation command.

The tested artifact host was macOS arm64, Python 3.14.7, Node 26.12.0,
npm 11.20.0, and Git 2.51.0. Linux/Intel release hashes are not silently
substituted: the fetcher fails closed on an unsupported platform.

## Setup

From a fresh clone of commit `bda5265` or a descendant containing this
artifact patch:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-d1.txt
scripts/artifact/fetch_inputs.sh --profile all
```

The `tests` profile is the smaller setup for the focused v1.1 suite; `all`
also installs Foundry, the pinned X-AV npm closure and CRS, generates all 30
mutants, and extracts their consumer relations. Re-running the command is
idempotent. `--force` replaces only the fetcher's scoped ignored outputs.

Run the focused artifact tests with:

```sh
PYTHONPATH=src python3 -m unittest tests.test_bindcheck_v1 -v
```

Expected result: **11 tests, all passing**. The input manifest must end in
`"status": "PASS"`. Exact source/tool/archive hashes are checked directly.
Noir JSON is additionally checked by path-independent ABI/bytecode/version
hashes because Nargo embeds checkout paths. Consumer relations are freshly
extracted and checked by canonical semantic hash; the historical provenance
envelope is then restored and the exact frozen relation hash is checked for
the content-addressed consumer index.

## One command per paper table

Each command prepares any missing inputs and writes its reproduced table and
JSON evidence under `results/raw/artifact-reproduction/`.

### BindCheck benchmark table (D1P-34)

```sh
python3 scripts/artifact/reproduce.py benchmark-table
```

Expected: 30 targets; 16 detected, 14 unsupported, 0 misses; 20 related and
33 unrelated warning objects. The command derives compiler-AST relations,
runs the frozen analyzer, adjudicates only after analysis, and asserts those
totals before writing `benchmark-table.md`.

### Comparative baseline table (D1P-32)

```sh
python3 scripts/artifact/reproduce.py baseline-table
```

Expected for the reproducible Foundry rows: the generic G1/G2/G4/G5 arm
detects 3/9 WarpToad consumer mutants and the same-policy arm detects 8/9;
the remaining 21 benchmark inputs are unresolved for this harness. The
command verifies the two published harness hashes, stages the pinned consumer
and every WT-S variant, runs 256 invariant sequences of depth 100, and checks
the exact failing invariant per target before writing `baseline-table.md`.

The paper's full tool-by-operator table also contains frozen runs of Noir,
Slither, Mythril, Echidna, CCC-Check, Picus and SmartAxe. Their ignored D1P-32
logs were not committed and several rows are unavailable/unsupported by
design. They cannot honestly be regenerated by this command from public
inputs alone; see **Known manual or archival steps** below. The command does
not relabel those rows as misses or successes.

### Automatic-validation table (X-AV on D1P-34 warnings)

```sh
python3 scripts/artifact/reproduce.py validation-table
```

The command regenerates all 53 warnings, dispatches the tracked synthesis
plans, runs proofs serially at low priority, and attempts E2/E3/E4 replay.
It refuses to start if another `bb` or `nargo` process is active. On an idle
but unusually high-load host, rerun deliberately with `--ignore-load`; the
proofs remain serialized. Output is `validation-table.md` plus the per-warning
`xav-v11/results.json`.

The direct X-AV run is expected to report 8 fresh E4, 1 E4-preserved,
4 E3, 6 mock-verifier-scoped E2, and 34 E1 rows. The published final table
has 6 E3 and 32 E1 because two PY-C02 rows were subsequently promoted by the
separate TC02 Rust-stack real-proof experiment; that merge is not presented
as an automatic X-AV result.

### Corrected validation + repair table (evidence ledger)

```sh
python3 scripts/artifact/reproduce.py ledger
```

Expected: ledger grades 8 E4, 1 E4-preserved, 5 E3, 6 E1+mock, 33 E1
over the same 53 warnings (tracked core `src/bindcheck_d1/xav_core.py`).
The mock rows are relabeled E1+mock (a mock does not meet the contract's
E2); PY-C02 is corrected by the TE05 active-prefix experiment (W001 E3 on
its own mutation, W002 E1-contained; TE04 is E4 for the inherited
message-tail defect); WT-S02 is corrected by the honest-seeded
mock experiment. The command asserts the TE05 zero-state-change report
and every repair-check verdict without rerunning provers, then writes
`ledger-table.md`. Held-out transfer (RQ4) has no reproduce command: it
requires the custodian reservation (D1P-33/D1P-36 frozen runs).

## Expected runtime

Approximate wall times on an idle recent M-series Mac (not performance
claims):

| action | warm cache | fresh network/cache |
|---|---:|---:|
| `fetch_inputs.sh --profile tests` | 15–30 s | 1–3 min |
| `fetch_inputs.sh --profile all` | 2–4 min | 4–10 min |
| focused 11-test suite | 5–10 s | same |
| benchmark table | 2–5 min | plus setup |
| Foundry baseline rows | 2–5 min | plus setup |
| X-AV validation table | 8–25 min | plus setup |

Proof time varies with host load. These are operational estimates, not the
paper's timing measurements.

## Pins and generated inputs

The materializer includes:

- WarpToad `973e7d1e...`, Payy earlier `c4d2c902...` and repaired
  `dcd5d96e...`, and Noir Poseidon revisions `0880c371...`/`ba04f0a...`;
- Nargo beta.22 and beta.14, solc 0.8.29 and 0.8.20, Foundry 1.8.6, and
  Forge Std `77041d2c...`, all checked by revision or byte hash;
- a tracked npm lock for Hardhat 3.3.0, bb.js 5.0.0 and the exact X-AV
  dependency closure; and
- the exact 2^19 BN254 and 2^16 Grumpkin CRS ranges consumed by bb.js 5.0.0,
  checked by size and SHA-256 and isolated with `CRS_PATH`.

The generated tree covers D1P-13's pinned artifact, D1P-15's M-DOM artifact
and honest witness, D1P-18/D1P-21B consumer relations, both full-size Payy
artifacts and D1P-34 relations, D1P-31 variant relations, all X-BM mutants,
the X-AV npm/tool/CRS inputs, and the S_SRC burn records X-AV reads.

## Known manual or archival steps

- The full D1P-32 third-party baseline table needs the original ignored raw
  logs (or separate installations governed by `paper/baselines.md`). Only the
  newly tracked, publicly reconstructible Foundry generic/same-policy arms are
  rerun here. SmartAxe's Figshare artifact and previously unavailable tools
  remain archival limitations, not safety evidence.
- TC02's cold Rust-stack Payy proof run is separate from X-AV and is not
  rebuilt. Its two post-run E3 promotions therefore remain an archival merge.
- WT-C03's `E4-preserved` row includes the two already-disclosed manual
  associations to the D1P-15 proof/verifier/replay chain. Fresh E3 and exact
  artifact correspondence are automated; the historical chain is not
  recreated.
- X-AV reads only two `S_SRC.burns` records. The setup script reconstructs
  that minimal replay input and records the SHA-256 of the full historical
  D1P-19 state record. Transaction hashes and the one-shot owned-local chain
  ledger cannot be regenerated without the archived chain; no fresh-chain
  provenance is fabricated.
- Network access is setup-only except for ordinary package/repository fetches
  already named above. No live deployment, third-party target, transaction,
  disclosure, or maintainer contact is performed.

All results remain development evidence on exposed WarpToad and Payy cases.
Unsupported, unresolved, or missing archival evidence is `UNKNOWN`, never a
safety claim or an ecosystem-prevalence estimate.
