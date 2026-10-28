# Binding-mutant benchmark (lane-x exploratory)

30 proof-to-execution binding mutants over two already-exposed development
applications: WarpToad (`973e7d1e…`, 18 mutants) and Payy (`c4d2c90…`,
12 mutants). Circuit and consumer sides both covered. Development use
only — these families can never be held out.

## Layout

- `baselines/` — vendored pinned sources + provenance hashes. Application
  sources only; no third-party dependencies are committed.
- `make_mutants.py` — applies exact-match edits (fail-closed) to baseline
  copies; `mutants/<ID>/` holds the generated build inputs.
- `mutants/<ID>.md` — per-mutant ground truth: operator, binding broken,
  expected effect, cheap reachability check.
- `_stubs/payy/` — compile-only stubs for the two OZ upgradeable
  contracts (pinned API subset). Clearly marked, never deploy. Real OZ
  `contracts` sources are copied from the read-only reference backend at
  build time, never committed.
- `build.sh` — compiles every mutant and runs cheap honest-execution
  checks; writes only under `$OUT` (default `results/raw/X-BM/`).
- `collect_results.py` — folds build logs into `manifest.json`.
- `manifest.json` — generated after a build (not hand-edited).

## Toolchain pins

- WarpToad circuit: nargo `1.0.0-beta.22+c57152f9…` (D1P-13 tool).
- Payy circuit: nargo `1.0.0-beta.14+60ccd48e…` (pinned case tool).
- WarpToad consumer: solc `0.8.29`, vendored OZ 5.x + zk-kit + poseidon-solidity.
- Payy consumer: solc `0.8.20` with `--via-ir --optimize --optimize-runs 200`
  (mirrors the pinned hardhat config), vendored OZ 5.0.1-era `contracts`
  sources + upgradeable stubs.
- All compiler runs at idle priority (`nice -n 19`).

## Reproduce

```sh
OUT=results/raw/X-BM sh benchmarks/binding-mutants/build.sh
python3 benchmarks/binding-mutants/collect_results.py --out results/raw/X-BM
```

Reference dependency paths are absolute (see `build.sh` header); builds
require the read-only reference checkouts on this machine.

## Claim boundary

- A compiling mutant is a detection target, not a validated finding.
  Ground-truth "expected effects" are predictions, mostly unexecuted.
- Cheap reachability = honest-path `nargo execute` (WarpToad circuit
  only) or compile + diff audit. Two mutants (WT-C06, WT-C07) are
  honest-breaking by design and recorded as such.
- WT-C03/WT-S01 reuse the M-DOM/M-SRC evidence (D1P-15/D1P-19), including
  their real-proof E4 results on the injected variants.
- Excluded with reason: see `docs/x-experiment/BENCHMARK.md` §6
  (private-recipient arity break, neutral-guard removals, Brillig scope).
