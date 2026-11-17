# T0 — Linux toolchains at the pinned versions
Status: PARTIAL
Verdict/outcome: circom (both pins), snarkjs 0.7.6, nargo (beta.14, beta.22, rc.4), bb 5.0.0, bb 6.0.0 and bb.js 5.0.0 run on Linux and pass smoke tests. **Native bb 3.0.0-manual.20251030 (Payy pin) is BLOCKED**: its only official download location returns HTTP 404. A version-matched WASM substitute (`@aztec/bb.js@3.0.0-manual.20251030`) is installed and proves/verifies, but it is not the Payy artifact.

AI disclosure: this task was run by Claude Code (Anthropic), model Claude Opus 5.5 (`claude-opus-5-5`), on 2026-11-17, in worktree `$BC/wt-T0`, branch `sprint/T0`. The human author has not yet inspected the outputs.

## What was done

1. Recorded the host (`results/raw/T0/00_host.txt`): Linux Mint 22.3 (zena), kernel `7.0.0-42-generic` x86_64, 12 cores, 15 GiB RAM; gcc 13.3.0, rustc/cargo 1.99.0 (`b940084d7`, host `x86_64-unknown-linux-gnu`), rustup 1.29.2, node v24.19.0, npm 11.17.0, Python 3.12.12, forge/anvil 1.4.1-stable (`cf774604`), git 2.43.0, curl 8.5.0. rustc and cargo were already present, so rustup was not installed.
2. Mapped which circom each script uses (see the next section), then rebuilt `tools/circom-src` (v2.2.3) and `tools/circom-2.1.9` with `cargo build --release --locked` at their pinned commits. Also rebuilt the optional `tools/circomspect-src`.
3. Ran `npm ci` in the worktree root (lockfile pins snarkjs 0.7.6, circomlib 2.0.5, circomlibjs 0.1.7).
4. Downloaded the official Linux nargo releases for beta.14, beta.22 and rc.4. rc.4 is named by `scripts/fetch_noir_rc4.sh`, which already pinned a Linux checksum. The download matched that pin.
5. Downloaded the official Aztec bb releases v5.0.0 and v6.0.0. Tried the Payy bb 3.0.0-manual Linux tarball and got 404. Installed `@aztec/bb.js` 5.0.0 and 3.0.0-manual.20251030 into scratch folders under `tools/` from committed lockfiles.
6. Wrote `scripts/setup_linux_tools.sh`. It repeats steps 2–5 from scratch and runs step 8 with `--smoke`. Ran it three times. The final run (`--skip-optional --smoke`) ended with exit 3 (expected, because bb 3.0.0-manual is BLOCKED) and every smoke step as expected.
7. Ran the analyzer tests with the Linux circom: 9/9 pass. A control run with no working circom fails one test, which shows the suite really calls circom.

### Handling of the macOS binaries already in `tools/` (nothing deleted)

- `circom-src`, `circom-2.1.9`, `circomspect-src`: the Mach-O `target/` folders were renamed to `target.macos-arm64/` inside each source folder.
- `noir-1.0.0-beta.14`, `noir-rc4`, `bb-3.0.0-manual.20251030`: each folder was moved whole to `tools/.macos-archive/<name>/`. That includes the macOS tarballs, for example `bb.tar.gz` with SHA-256 `7f72eaf4…01ab2`, which matches the pin in `scripts/t09.sh`.
- `tools/bb-3.0.0-manual.20251030/` now exists but is **empty**, so scripts that use that path (`t09`–`t16`, `t19`, `t15_summarize.py`, `te06_wrap_batch2.sh`) fail fast.
- Not touched: `cvc5-1.4.2-gpl` (Mach-O, not needed now), `picus-*`, `oz-5.0.1`, `cases/`.

### Git hygiene

`.gitignore` does not cover the new tool folders, and T0 may not edit `.gitignore`. They were therefore added to the main checkout's **untracked** `.git/info/exclude` (`tools/noir-1.0.0-beta.22/`, `tools/bb-5.0.0/`, `tools/bb-6.0.0/`, `tools/bbjs-5.0.0/`, `tools/bbjs-3.0.0-manual.20251030/`, `tools/.macos-archive/`). After the run, `git status` in `$BC/BindCheck` is unchanged: the same three user changes as before, and no `tools/` entries. Nothing under `tools/` is committed, and no branch was switched in `$BC/BindCheck`.

## Which scripts expect which circom

| circom | Path | Used by |
|---|---|---|
| **2.2.3** (`ad44e915…`) | `tools/circom-src/target/release/circom` | the `BINDCHECK_CIRCOM` default in `bindcheck_zk/circuits.py:332` and `bindcheck_zk/baselines.py`; `scripts/t01.sh`; `dataset/run_track_b.py`; `baselines/strong/arm_b.py`; `benchmark/*` (hard-coded macOS paths); `feasibility/v2/run_zkredential_e4.sh`, `run_public_input_experiment.sh`; `findings/zkredential/run.sh`; `reports/soundness/verify_followup.py`; `reports/coverage/scripts/verify.py` |
| **2.1.9** (`2eaaa6df…`) | `tools/circom-2.1.9/target/release/circom` | `findings/racepass/run.sh`; `feasibility/v2/run_racepass_e4.sh` (RacePass only) |

Both pins come from `feasibility/v2/setup_toolchain.sh`. The analyzer (`BINDCHECK_CIRCOM`) uses 2.2.3.

## Evidence (paths, hashes, commands, exit codes, tool versions)

Raw logs (ignored) are in `results/raw/T0/` of this worktree:

- `00_host.txt`: host
- `build_*.log`: first cargo builds, all `exit=0`
- `10_setup_run1.log`: first run, stopped at the bb 3.0.0 curl 404 (exit 22)
- `11_setup_run2.log`: after the bb 3.0.0 failure was made explicit, exit 3
- `12_setup_smoke.log` + `smoke/*.log` + `smoke/steps.tsv`: final run, exit 3, 29/29 smoke steps as expected
- `20_analyzer_tests.log` (exit 0) and `21_analyzer_tests_no_circom_control.log` (exit 1, control)
- `30_hashes.txt`: all binary and tarball checksums

Commands:

```bash
bash scripts/setup_linux_tools.sh                              # full install (run 1/2)
bash scripts/setup_linux_tools.sh --skip-optional --smoke      # final run: exit 3 (bb 3.0.0 BLOCKED), SMOKE: all steps as expected
BINDCHECK_CIRCOM=$BC/BindCheck/tools/circom-src/target/release/circom \
  python3 -m unittest discover -s tests -p 'test_bindcheck_zk*.py'   # Ran 9 tests, OK, exit 0
```

Install root: `$BC/BindCheck/tools/`. The script reaches it as `$BC/bindcheck-zk/tools` (a symlink).

### Tool table

| tool | pinned version | installed path (under `$BC/BindCheck/`) | source | sha256 (download → binary) | `--version` output | smoke result |
|---|---|---|---|---|---|---|
| circom | 2.2.3 | `tools/circom-src/target/release/circom` | `https://github.com/iden3/circom` @ `ad44e915a12bb047b05745c2884aad9cc8326bc6` (tag v2.2.3), `cargo build --release --locked`, rustc 1.99.0 | build: `599552d8027722ee9de3cf21a5a78f3f36bad07d0e0f40a627d6c3a35dff6cb7` | `circom compiler 2.2.3` | pass (compiles `circuits/batch_deposit.circom`; Groth16 prove/verify; analyzer tests 9/9) |
| circom | 2.1.9 | `tools/circom-2.1.9/target/release/circom` | same repo @ `2eaaa6dface934356972b34cab64b25d382e59de` (tag v2.1.9), `--locked` | build: `1bacd5583e2cc79dc1e2deaefc9c7438f21957968651c5f93dc71073c58435e3` | `circom compiler 2.1.9` | pass (compiles `batch_deposit.circom`) |
| snarkjs (+ circomlib 2.0.5, circomlibjs 0.1.7) | 0.7.6 | `<worktree>/node_modules/` | npm registry via `package-lock.json` (sha256 `63679f1e…0006`, integrity checked by `npm ci`) | lockfile: `63679f1efedd00cc480f9b78e4a04009341913610af82c9b0cf205ebd4740006` | `snarkjs@0.7.6` | pass (toy ptau 2^12, groth16 setup/prove/verify OK; tampered public signal rejected, exit 1) |
| nargo | 1.0.0-beta.14 | `tools/noir-1.0.0-beta.14/nargo` | `https://github.com/noir-lang/noir/releases/download/v1.0.0-beta.14/nargo-x86_64-unknown-linux-gnu.tar.gz` | tar: `7854a340b5ce39f471036031aa94087a7cc328d2029d1e3976eeade2fe4a9bb1` → bin: `6774e1f93c4ae5e05781bc7687a5c8225ac88d9343d2d05cde52379402c112d2` | `nargo version = 1.0.0-beta.14` / `noirc version = 1.0.0-beta.14+60ccd48e18ad8ce50d5ecda9baf813b712145051` (is dirty: false) | pass (`nargo execute`) |
| nargo | 1.0.0-beta.22 | `tools/noir-1.0.0-beta.22/nargo` | `…/v1.0.0-beta.22/nargo-x86_64-unknown-linux-gnu.tar.gz` | tar: `384c4fc800905b213e26aabd738a96a4a85b1a76ffc27fb19aeb6d33494a787b` → bin: `d57714db2a94f26409b6ff56555438227ecf0b9d185d220fd072b42465dcd686` | `nargo version = 1.0.0-beta.22` / `noirc version = 1.0.0-beta.22+c57152f91260ecdb9faad4efc20abb14b6d2ece7` (is dirty: false) | pass (`nargo execute`; bb 5/6 and bb.js 5 prove/verify) |
| nargo | 1.0.0-rc.4 | `tools/noir-rc4/nargo` | `…/v1.0.0-rc.4/noir-x86_64-unknown-linux-gnu.tar.gz` | tar: `8b06351a89b6cef4b171e1e2e54fb5b1e0ccf1195142eb59b67841d3989b5c0e` (equals the existing pin in `scripts/fetch_noir_rc4.sh`) → bin: `4cf503b44c53438b64cd64f23e3e2ad77869388bb1047c818c4c916b61827c05` | `nargo version = 1.0.0-rc.4` / `noirc version = 1.0.0-rc.4+9cdc6086c58086e35cd2ff3ff3f18d42112277f3` | pass (`nargo execute`) |
| bb (native) | 3.0.0-manual.20251030 (Payy) | **not installed** (`tools/bb-3.0.0-manual.20251030/` is empty) | `https://storage.googleapis.com/payy-public-fixtures/bb/v3.0.0-manual.20251030/barretenberg-amd64-linux.tar.gz` → **HTTP 404**; the bucket itself returns "bucket does not exist" | Payy's own Linux pin (`pkg/xtask/src/setup/bb.rs` @ payy `dcd5d96`): `88586691621fdbf6105e064aca1b6e4f1f5345f2e75560d1d385693019480697`, not obtainable | — | **BLOCKED** |
| bb.js (WASM substitute for the above) | 3.0.0-manual.20251030 | `tools/bbjs-3.0.0-manual.20251030/` | npm `@aztec/bb.js@3.0.0-manual.20251030` (gitHead `c8ef7827ac03a059fe3febb2f7552af49cabeeae`), lockfile `reports/T0/bbjs-3.0.0-manual.20251030/` | npm integrity `sha512-YPOZSvfm6b8MAxEWxKLt6qgnyJYg+x6IInjJARRGY/ZErgfKUSLhWQz7gTclyowpG7wJh8NraEC1Qf/G5tn94w==`; lockfile sha256 `bc9275dc…1924` | no CLI (the package's `bin` points to a missing `dest/node/main.js`); `package.json` version `3.0.0-manual.20251030` | pass (JS API UltraHonk prove/verify of a beta.14 program; tampered public input rejected) |
| bb (native) | 5.0.0 (matches beta.22) | `tools/bb-5.0.0/bb` | `https://github.com/AztecProtocol/aztec-packages/releases/download/v5.0.0/barretenberg-amd64-linux.tar.gz` | tar: `4b42a64a0587e1e15089f7a20c87fa2d8a092acb4fc95465a798a73b98ba794d` (equals GitHub's published asset digest) → bin: `07e14e5aef7dd374e0b557892f5f9044be3a8dbc6b522596535cbefda0943cb2` | `5.0.0` | pass (prove `--write_vk`, verify OK; flipped public input rejected, exit 1) |
| bb (native) | 6.0.0 (latest Aztec release, 2026-10-22) | `tools/bb-6.0.0/bb` | `…/v6.0.0/barretenberg-amd64-linux.tar.gz` | tar: `6a310ede6457cf47e6dcf11f8d6b59dd709328c272a70c03afb1417c5a798b67` (equals the GitHub digest) → bin: `97242cb29cab39f22f001dfd9d7fa5937d414fd0ae326b000759ffb7a4544f31` | `6.0.0` | pass (same as 5.0.0, on the beta.22 artifact) |
| bb.js | 5.0.0 (WarpToad) | `tools/bbjs-5.0.0/` | npm `@aztec/bb.js@5.0.0`, lockfile `reports/T0/bbjs-5.0.0/` | npm integrity `sha512-O4HDjzrjXMvM44+VbgDG1GaDUztWGEVujbBmwZAEVJh6BHpmJfMxBB2/69h1oi4kX2adgaowlJNFhpzcz1MHSA==`; lockfile sha256 `b3bf50d9…8f23` | CLI `dest/node/bin/index.js --version` → `5.0.0-nightly.20260710` | pass (JS API UltraHonk prove/verify of a beta.22 program; tampered public input rejected) |
| circomspect (optional) | commit `50010b62…` (crate 0.9.0) | `tools/circomspect-src/target/release/circomspect` | `https://github.com/trailofbits/circomspect` @ `50010b623ed4f3bff9d1b0363cfe952385b47af3` (untagged), `--locked` | build: `1512174c25d8fc08de38a799b92d6d81d2935320768f12df43f1033fa38ae133` | no `--version` flag (rejected by its CLI) | built only, not exercised |
| picus (optional) | `138b151d…` | not built | `tools/picus-src` | — | — | not attempted: Racket is not installed (`racket`/`raco` missing), and its cvc5 in `tools/` is a Mach-O binary |

All Linux checksums except bb 3.0.0-manual are **new T0 pins**, observed on 2026-11-17. They are not the macOS pins. Two independent checks back them:

- For nargo beta.14, nargo beta.22, bb 5.0.0 and bb 6.0.0, the tarball checksum equals the `digest` that the GitHub Releases API publishes for that asset.
- For nargo rc.4, it equals the Linux pin already in `scripts/fetch_noir_rc4.sh`. The circom/circomspect build checksums are for this host's toolchain (rustc 1.99.0, unpinned); they are not expected to be reproducible across rustc versions.

### Why bb 5.0.0 is the release that matches beta.22

Repository evidence: `reports/D1P-33.md` records that ZKPassport's release script enforces nargo beta.22 with bb `5.0.0`, and WarpToad pairs beta.22 with `@aztec/bb.js` 5.0.0 (`reports/D1P-13.md`). Locally, bb 5.0.0 and bb.js 5.0.0 both prove and verify a beta.22 program. bb 6.0.0 does too, at least for this one-constraint program; that does not establish general compatibility.

## Results (tables; exact counts)

- Smoke steps: 29 run, 29 as expected (`results/raw/T0/smoke/steps.tsv`). That is 2 circom compiles, 11 snarkjs steps (including 1 negative control), 6 nargo version/execute steps, 8 bb steps (2 negative controls) and 2 bb.js runs (each with an internal negative control).
- Analyzer tests: 9 run, 9 pass. In the control run with `BINDCHECK_CIRCOM=/nonexistent/circom`, 9 run and 1 fails (`test_all_new_pattern_controls`).
- Completion criteria:

| criterion | met? |
|---|---|
| circom used by `BINDCHECK_CIRCOM` (2.2.3) runs | yes |
| snarkjs 0.7.6 | yes |
| nargo beta.14 and beta.22 | yes |
| bb 3.0.0-manual | **no**: native binary unobtainable (WASM bb.js of the same version works) |
| bb release matching beta.22 | yes (5.0.0; 6.0.0 also installed) |
| analyzer tests pass | yes, 9/9 |

### Tools still missing

1. **Native bb 3.0.0-manual.20251030**, needed by the Payy scripts `t09`, `t10`, `t12`–`t16`, `t19`, `te04_part*`, `te06_wrap_batch2.sh` and `t15_summarize.py`.
2. picus (optional), which needs Racket and a Linux cvc5.
3. cvc5 1.4.2 Linux (not needed now).
4. nargo beta.19 and beta.21 appear only in `reports/D1P-33.md`, not in any script, so they were not installed.

## Assumptions and limitations

- "Release matching beta.22" is taken to be Aztec v5.0.0, based on the evidence above. "Latest release" means the GitHub `releases/latest` of `AztecProtocol/aztec-packages`, which was v6.0.0 (2026-10-22). The npm `latest` tag for bb.js is 5.3.0, which differs.
- The bb.js 3.0.0-manual substitute uses the WASM backend and has the same version string as Payy's bb. **It is not shown to be the same code as Payy's native tarball.** Payy's own comment says its build came from a `3.0.0-nightly.20251016` and that `bb --version` printed `00000000.00000000.00000000`. Any Payy result reproduced with it must be labelled a substitute run.
- The bb.js transitive dependencies (pako, msgpackr, and others) were resolved on 2026-11-17 and frozen in the committed lockfiles. Install scripts are disabled (`--ignore-scripts`).
- The root `npm ci` runs **in the repository that holds the script** (this worktree), not in `$BC/BindCheck`. Each worktree needs its own `npm ci` (`node_modules/` is ignored). `npm ci` reported that `blake-hash@2.0.0` has an install script not yet covered by `allowScripts`; snarkjs and circomlibjs did not need it in the smoke test.
- bb downloaded the public Aztec CRS into `~/.bb-crs/` on first use (`bn254_g1.dat`, `bn254_g1_compressed.dat`). This is outside `tools/`.
- The Rust toolchain is not pinned (rustc 1.99.0 from rustup stable). `--locked` pins the dependencies but not the compiler.
- Hard-coded `/Users/imranpollob/...` paths in `benchmark/*.py`, `scripts/te0*` and other scripts still point to macOS. Per `docs/orchestration/README.md`, that fix belongs in a separate commit and is out of T0 scope.
- `AGENTS.md` asks for a `docs/project-status.md` checkpoint after tasks that change research state. T0 changes only infrastructure, and the T0 ownership table forbids editing tracked files outside `scripts/setup_linux_tools.sh` and `reports/T0/`. The main checkout also has uncommitted user edits to that file. **No checkpoint row was added.** The reviewer should decide whether one is needed at merge time.

## Failed approaches / surprises

- **Payy bb bucket is gone.** Both `…/barretenberg-amd64-linux.tar.gz` and the macOS asset already pinned in `t09.sh` return 404, and the GCS JSON API reports that bucket `payy-public-fixtures` does not exist. The latest Payy `bb.rs` in the local clone (`bf27238`, 2026-03-25; `main` = `2f95947`, 2026-06-24) still points there. The clone was not fetched, because `tools/cases/` must not be edited.
- No official GitHub release exists for `v3.0.0-manual.20251030` or for the nearby `v3.0.0-nightly.202510{16,29,30,31}` tags (API 404; Aztec prunes nightlies).
- `@aztec/bb.js@3.0.0-manual.20251030` ships no native `bb` and no working CLI. bb.js 5.0.0 does ship a native `build/amd64-linux/bb` (sha256 `c3a4a112…97d5`, `--version` `5.0.0-nightly.20260710`). That binary differs from the GitHub v5.0.0 `bb` (`07e14e5a…`) and reports a nightly version string.
- A source build of bb at `c8ef7827` (the bb.js 3.0.0-manual gitHead) was not attempted. Barretenberg needs clang ≥ 18 and ninja, and neither is installed; installing them needs `sudo apt` or a large LLVM download, which is outside the agreed scope. Even if it worked, the result could not be checked against Payy's tarball checksum.
- bb.js ≥ 4 changed the `UltraHonkBackend` constructor (it needs an explicit `Barretenberg` instance). The smoke script handles both APIs.
- circomspect commit `50010b62` is not tagged (the first script draft assumed `v0.8.2`; fixed). Its CLI has no `--version`.
- The first `setup_linux_tools.sh` run aborted at the 404 under `set -e` (exit 22). It now records the failure, finishes the other installs, and exits 3. It never puts a substitute at the pinned path.

## Held-out hygiene statement (which families were read; confirm no unused EVAL family was opened)

The only third-party code read was the existing local Payy clone `tools/cases/payy-history` (`polybase/payy`): `pkg/xtask/src/setup/bb.rs` at `dcd5d96`, plus `git log` metadata. `python3 scripts/check_holdout.py polybase/payy` returned `ALLOWED`. Toolchain repositories and release metadata were also read: iden3/circom, trailofbits/circomspect, noir-lang/noir, AztecProtocol/aztec-packages, and the npm `@aztec/bb.js` registry. These are tools, not dataset families. No family in the dataset v2 EVAL pool was opened, cloned, built or analyzed. No transaction was sent, no deployment was contacted, and no maintainer was contacted.

## Recommended next task (one, with a measurable completion criterion)

**T0b — obtain a Linux `bb` for the Payy pin.** The human decides between two routes:

- (a) Approve installing clang-20 and ninja (`sudo apt install clang-20 ninja-build`), then build `barretenberg/cpp` target `bb` at aztec-packages `c8ef7827ac03a059fe3febb2f7552af49cabeeae`.
- (b) Accept the bb.js 3.0.0-manual WASM substitute for Payy work.

Completion criterion: `scripts/t09.sh` (with `BB` pointing at the result) reaches its `00_toolchain.txt` step, and the Payy `agg_final` VK it regenerates at `dcd5d96` has the same SHA-256 as the committed fixture `fixtures/circuits/agg_final/key`. If the hashes differ, the run is recorded as `UNKNOWN`, not as a reproduction.
