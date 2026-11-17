# T0 — Linux toolchains at the pinned versions

**Goal:** S1, S2a and S4 need circom, snarkjs, nargo, bb and bb.js on this Linux
(Mint) machine. The binaries copied from the Mac are macOS builds, and they do
not run on Linux. T0 builds or downloads Linux versions at the **same pinned
versions** and records exact versions and checksums. The paper's artifact can
then state the toolchain.

**Branch:** `sprint/T0`.

**Start directory:** `$BC/BindCheck`, the main checkout. This is the one place
where the git-ignored `tools/` directory exists. All worktrees reach `tools/`
through the `$BC/bindcheck-zk` link.

**Owns:**

- `tools/` (git-ignored);
- `scripts/setup_linux_tools.sh`;
- `reports/T0/`.

**Must not edit:**

- tracked files outside the paths above;
- `results/raw/`, which is read-only.

## Steps

1. **Record the host.** Record `uname -a`, `lsb_release -a`, and the versions of
   gcc, rustc, cargo, node, npm, python3, forge and anvil. If rustc or cargo is
   missing, install rustup for the current user.
2. **circom.** Two versions are referenced: `scripts/t01.sh` pins v2.2.3
   (commit `ad44e915a12bb047b05745c2884aad9cc8326bc6`), and the handoff notes say
   2.1.9.
   1. Find the version each script really uses:

      ```bash
      rg -n "circom-src|circom-2.1.9|BINDCHECK_CIRCOM" -g '*.sh' -g '*.py'
      ```

   2. Build `tools/circom-src` at its pinned commit with
      `cargo build --release --locked`. This replaces the macOS binary in
      `target/`.
   3. If `tools/circom-2.1.9` is used anywhere, build it at tag `v2.1.9`.
   4. Run `--version` for each build.
3. **snarkjs and circomlib.** Run `npm ci` in the repository root.
   `package.json` and `package-lock.json` pin snarkjs 0.7.6, circomlib 2.0.5 and
   circomlibjs 0.1.7. Confirm `npx snarkjs --version`.
4. **nargo.** Download the Linux x86_64 release for each version the project
   uses:
   - 1.0.0-beta.14 (Payy, `scripts/t09.sh`);
   - 1.0.0-beta.22 (WarpToad);
   - any other version a script names; find them with
     `rg -n "nargo-|noir-1\.0" scripts docs/d1`.

   Get the files from the official `noir-lang/noir` GitHub releases. Record the
   SHA-256 of each tarball. The repository pins only macOS checksums, so record
   the new Linux checksums **as new pins**. Do not claim they match the macOS
   ones.
5. **bb (Barretenberg).** Download the Linux builds of:
   - bb **3.0.0-manual.20251030**, the Payy pin. `scripts/t09.sh` uses
     `.../barretenberg-arm64-darwin.tar.gz`; look for the `amd64-linux` file at
     the same location;
   - the official Aztec bb releases that match nargo beta.22 and the latest
     release. S1 needs these.

   Record the URLs and SHA-256 checksums. Also install `@aztec/bb.js@5.0.0` (the
   WarpToad pin) in a scratch folder under `tools/`.
6. **Optional tools.** Build circomspect and picus from `tools/*-src` if the
   sources are present. cvc5 is not needed now. If a build fails, record the
   error and continue.
7. **Write the setup script.** Write `scripts/setup_linux_tools.sh`. It must
   repeat steps 2–5 from scratch: pinned URLs and commits, checksum checks that
   fail closed, and no secrets.
8. **Smoke test.**
   - Compile `circuits/` (the T01 honest fixture) with the built circom.
   - Prove and verify one proof with snarkjs.
   - Run `nargo --version` and `bb --version` for each installed version.
   - Run the analyzer tests:

     ```bash
     BINDCHECK_CIRCOM=$PWD/tools/circom-src/target/release/circom python3 -m unittest discover -s tests -p 'test_bindcheck_zk*.py'
     ```

## Output

`reports/T0/REPORT.md`, in the handoff template of
`docs/orchestration/README.md`. It must contain a table with one row per tool:

| Column | Content |
|---|---|
| tool | Tool name |
| pinned version | The version the project pins |
| installed path | Where the Linux build is installed |
| source | URL or commit |
| sha256 | Checksum of the download or build |
| `--version` output | Exact text |
| smoke result | Pass or fail |

It must also say which scripts expect which circom version, and which tools are
still missing.

## Completion criteria

- All four required tools run on Linux: circom (the version used by
  `BINDCHECK_CIRCOM`), snarkjs 0.7.6, nargo (beta.14 and beta.22), and bb
  (3.0.0-manual and a release matching beta.22).
- The analyzer tests pass, or every failure is explained.
- Commit only the tracked files on branch `sprint/T0` and push them:
  `git push -u origin sprint/T0`. Do not commit anything under `tools/`.

## Time box

Half a day.
