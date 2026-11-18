#!/usr/bin/env bash
# BindCheck T0: install the pinned toolchains on Linux x86_64.
#
# Repeats T0 steps 2-5 from scratch:
#   circom v2.2.3 and v2.1.9 (source builds at pinned commits, cargo --locked),
#   snarkjs/circomlib/circomlibjs (npm ci from the committed lockfile),
#   nargo 1.0.0-beta.14, 1.0.0-beta.22, 1.0.0-rc.4 (official noir-lang releases),
#   bb 3.0.0-manual.20251030 (Payy pin), 5.0.0 and 6.0.0 (official Aztec releases),
#   @aztec/bb.js 5.0.0 (npm ci from the lockfile in reports/T0/bbjs-5.0.0/).
# Optional: circomspect (source build at its pinned commit).
#
# Every download is checked against a SHA-256 pinned below; a mismatch aborts.
# Linux checksums are new pins recorded by T0 (except bb 3.0.0-manual, whose
# Linux checksum is pinned by Payy itself); they are NOT the macOS checksums.
#
# usage: bash scripts/setup_linux_tools.sh [--skip-npm] [--skip-optional] [--smoke]
#   --smoke  also run T0 step 8 (circom+snarkjs toy Groth16 prove/verify on circuits/,
#            nargo execute + bb / bb.js UltraHonk prove/verify on a 1-constraint program,
#            each with a tampered-public-input control that must be rejected).
#            Work files go to build/T0/, logs to results/raw/T0/smoke/ (both ignored).
# env:   BINDCHECK_TOOLS  install directory (default: <repo>/../bindcheck-zk/tools
#                         if it exists, else <repo>/tools)
# No secrets are used. Network access is required on the first run.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -n "${BINDCHECK_TOOLS:-}" ]]; then
  TOOLS="$BINDCHECK_TOOLS"
elif [[ -d "$ROOT/../bindcheck-zk/tools" ]]; then
  TOOLS="$(cd "$ROOT/../bindcheck-zk/tools" && pwd)"
else
  TOOLS="$ROOT/tools"
fi
SKIP_NPM=0; SKIP_OPTIONAL=0; SMOKE=0
for a in "$@"; do
  case "$a" in
    --skip-npm) SKIP_NPM=1 ;;
    --skip-optional) SKIP_OPTIONAL=1 ;;
    --smoke) SMOKE=1 ;;
    *) echo "unknown argument: $a" >&2; exit 2 ;;
  esac
done

[[ "$(uname -s):$(uname -m)" == "Linux:x86_64" ]] || { echo "this script supports Linux x86_64 only" >&2; exit 2; }
for c in git cargo curl tar sha256sum node npm; do command -v "$c" >/dev/null || { echo "missing required command: $c" >&2; exit 2; }; done
mkdir -p "$TOOLS" "$TOOLS/.macos-archive"
echo "tools directory: $TOOLS"

is_elf() { [[ -f "$1" ]] && [[ "$(head -c 4 "$1" | od -An -c | tr -d ' ')" == '177ELF' ]]; }

# Move a directory that holds a non-Linux build of BIN aside (never delete it).
archive_foreign() { local dir="$1" bin="$2"
  if [[ -e "$dir/$bin" ]] && ! is_elf "$dir/$bin"; then
    local dest="$TOOLS/.macos-archive/$(basename "$dir")"
    [[ -e "$dest" ]] && dest="$dest.$(date -u +%Y%m%dT%H%M%SZ)"
    echo "archiving non-Linux $dir -> $dest"
    mv "$dir" "$dest"
  fi
}

sha_check() { local file="$1" want="$2" got
  got="$(sha256sum "$file" | awk '{print $1}')"
  if [[ "$got" != "$want" ]]; then
    echo "CHECKSUM MISMATCH: $file" >&2; echo "  expected $want" >&2; echo "  observed $got" >&2
    return 1
  fi
  echo "sha256 ok  $want  $(basename "$file")"
}

# fetch DIR BIN URL SHA256 : download a release tarball into DIR, verify, extract.
fetch() { local dir="$TOOLS/$1" bin="$2" url="$3" want="$4"
  archive_foreign "$dir" "$bin"
  local tarball="$dir/$(basename "$url")"
  if is_elf "$dir/$bin" && [[ -f "$tarball" ]]; then
    sha_check "$tarball" "$want"; echo "already installed: $dir/$bin"; return 0
  fi
  mkdir -p "$dir"
  curl -fsSL --retry 3 -o "$tarball.part" "$url" || { echo "DOWNLOAD FAILED: $url" >&2; rm -f "$tarball.part"; return 1; }
  sha_check "$tarball.part" "$want" || { rm -f "$tarball.part"; return 1; }
  mv "$tarball.part" "$tarball"
  tar -xzf "$tarball" -C "$dir"
  is_elf "$dir/$bin" || { echo "no Linux $bin in $tarball" >&2; return 1; }
}

# build_rust DIR URL TAG COMMIT : clone (if absent), check out COMMIT, cargo build --locked.
# TAG may be empty when COMMIT is untagged (the default branch is cloned, then COMMIT checked out).
build_rust() { local dir="$TOOLS/$1" url="$2" tag="$3" commit="$4"
  if [[ ! -d "$dir/.git" ]]; then git clone --quiet --filter=blob:none ${tag:+--branch "$tag"} "$url" "$dir"; fi
  git -C "$dir" checkout --quiet --detach "$commit"
  [[ "$(git -C "$dir" rev-parse HEAD)" == "$commit" ]] || { echo "$dir is not at $commit" >&2; return 1; }
  # A target/ copied from macOS holds Mach-O binaries; keep it, but out of cargo's way.
  if [[ -d "$dir/target/release" ]] && [[ -n "$(find "$dir/target/release" -maxdepth 1 -type f -perm -u+x -print -quit)" ]] \
     && ! is_elf "$(find "$dir/target/release" -maxdepth 1 -type f -perm -u+x -print -quit)"; then
    mv "$dir/target" "$dir/target.macos-arm64.$(date -u +%Y%m%dT%H%M%SZ)"
  fi
  cargo build --release --locked --manifest-path "$dir/Cargo.toml"
}

# ---- step 2: circom ---------------------------------------------------------
# tools/circom-src (v2.2.3): BINDCHECK_CIRCOM default, scripts/t01.sh, feasibility/v2, findings/zkredential
build_rust circom-src   https://github.com/iden3/circom.git v2.2.3 ad44e915a12bb047b05745c2884aad9cc8326bc6
# tools/circom-2.1.9: findings/racepass/run.sh, feasibility/v2/run_racepass_e4.sh
build_rust circom-2.1.9 https://github.com/iden3/circom.git v2.1.9 2eaaa6dface934356972b34cab64b25d382e59de

# ---- step 3: snarkjs 0.7.6, circomlib 2.0.5, circomlibjs 0.1.7 --------------
if [[ "$SKIP_NPM" == 0 ]]; then
  (cd "$ROOT" && npm ci --no-audit --no-fund)
fi

# ---- step 4: nargo (official noir-lang/noir GitHub releases) ----------------
NOIR=https://github.com/noir-lang/noir/releases/download
fetch noir-1.0.0-beta.14 nargo "$NOIR/v1.0.0-beta.14/nargo-x86_64-unknown-linux-gnu.tar.gz" \
  7854a340b5ce39f471036031aa94087a7cc328d2029d1e3976eeade2fe4a9bb1
fetch noir-1.0.0-beta.22 nargo "$NOIR/v1.0.0-beta.22/nargo-x86_64-unknown-linux-gnu.tar.gz" \
  384c4fc800905b213e26aabd738a96a4a85b1a76ffc27fb19aeb6d33494a787b
# same pin as scripts/fetch_noir_rc4.sh (Linux:x86_64 branch)
fetch noir-rc4 nargo "$NOIR/v1.0.0-rc.4/noir-x86_64-unknown-linux-gnu.tar.gz" \
  8b06351a89b6cef4b171e1e2e54fb5b1e0ccf1195142eb59b67841d3989b5c0e

# ---- step 5: bb (Barretenberg) ----------------------------------------------
# Payy pin: pkg/xtask/src/setup/bb.rs @ polybase/payy dcd5d96 (Platform::LinuxX86_64).
# On 2026-11-17 the payy-public-fixtures bucket returned 404 for every bb asset (macOS too),
# so this step is expected to fail; the failure is reported and the script exits 3 at the end.
# No unverified substitute is ever placed at tools/bb-3.0.0-manual.20251030/bb.
BLOCKED=()
fetch bb-3.0.0-manual.20251030 bb \
  https://storage.googleapis.com/payy-public-fixtures/bb/v3.0.0-manual.20251030/barretenberg-amd64-linux.tar.gz \
  88586691621fdbf6105e064aca1b6e4f1f5345f2e75560d1d385693019480697 \
  || BLOCKED+=("bb 3.0.0-manual.20251030 native (Payy release URL unavailable)")
AZTEC=https://github.com/AztecProtocol/aztec-packages/releases/download
# v5.0.0: release paired with nargo beta.22 (ZKPassport, D1P-33) and bb.js 5.0.0 (WarpToad)
fetch bb-5.0.0 bb "$AZTEC/v5.0.0/barretenberg-amd64-linux.tar.gz" \
  4b42a64a0587e1e15089f7a20c87fa2d8a092acb4fc95465a798a73b98ba794d
# v6.0.0: latest aztec-packages GitHub release on 2026-11-17
fetch bb-6.0.0 bb "$AZTEC/v6.0.0/barretenberg-amd64-linux.tar.gz" \
  6a310ede6457cf47e6dcf11f8d6b59dd709328c272a70c03afb1417c5a798b67

# @aztec/bb.js from committed lockfiles (npm checks the sha512 integrity); install scripts disabled.
#   5.0.0                  WarpToad pin
#   3.0.0-manual.20251030  same version string as the Payy bb pin; WASM CLI only (no native bb
#                          inside the package). Substitute for experiments, NOT the Payy artifact.
install_bbjs() { local ver="$1" dir="$TOOLS/bbjs-$1"
  mkdir -p "$dir"
  cp "$ROOT/reports/T0/bbjs-$ver/package.json" "$ROOT/reports/T0/bbjs-$ver/package-lock.json" "$dir/"
  (cd "$dir" && npm ci --ignore-scripts --no-audit --no-fund)
  node -e 'const p=require(process.argv[1]); if(p.version!==process.argv[2]){console.error("bb.js version "+p.version);process.exit(1)}; console.log("@aztec/bb.js "+p.version)' \
    "$dir/node_modules/@aztec/bb.js/package.json" "$ver"
}
if [[ "$SKIP_NPM" == 0 ]]; then
  install_bbjs 5.0.0
  install_bbjs 3.0.0-manual.20251030
fi

# ---- step 6 (optional): circomspect -----------------------------------------
if [[ "$SKIP_OPTIONAL" == 0 ]]; then
  build_rust circomspect-src https://github.com/trailofbits/circomspect.git "" 50010b623ed4f3bff9d1b0363cfe952385b47af3 \
    || echo "WARNING: circomspect build failed (optional)" >&2
fi

# ---- versions ---------------------------------------------------------------
echo "---- installed versions ----"
for v in circom-src circom-2.1.9; do echo "$v: $("$TOOLS/$v/target/release/circom" --version)"; done
[[ "$SKIP_NPM" == 0 ]] && echo "snarkjs: $(cd "$ROOT" && node -p "require('./node_modules/snarkjs/package.json').version")"
for v in noir-1.0.0-beta.14 noir-1.0.0-beta.22 noir-rc4; do echo "$v: $("$TOOLS/$v/nargo" --version | tr '\n' ' ')"; done
for v in bb-3.0.0-manual.20251030 bb-5.0.0 bb-6.0.0; do
  if is_elf "$TOOLS/$v/bb"; then echo "$v: $("$TOOLS/$v/bb" --version)"; else echo "$v: MISSING"; fi
done

# ---- step 8 (--smoke) -------------------------------------------------------
if [[ "$SMOKE" == 1 ]]; then
  B="$ROOT/build/T0"; L="$ROOT/results/raw/T0/smoke"; rm -rf "$B" "$L"; mkdir -p "$B" "$L"
  : > "$L/steps.tsv"; SMOKE_FAIL=0
  # srun NAME EXPECT(0|nonzero) CMD... : log to $L/NAME.log, compare exit status with the expectation
  srun() { local n="$1" e="$2"; shift 2; local c=0
    { echo "\$ $*"; "$@"; } > "$L/$n.log" 2>&1 || c=$?
    echo "exit=$c" >> "$L/$n.log"; local v=ok
    if [[ "$e" == 0 && "$c" != 0 ]] || [[ "$e" == nonzero && "$c" == 0 ]]; then v=FAIL; SMOKE_FAIL=1; fi
    printf '%s\texpect=%s\tobserved=%s\t%s\n' "$n" "$e" "$c" "$v" | tee -a "$L/steps.tsv"; }
  SNARKJS="$ROOT/node_modules/.bin/snarkjs"
  for v in circom-src circom-2.1.9; do C="$TOOLS/$v/target/release/circom"; mkdir -p "$B/$v"
    srun "c10_compile_$v" 0 "$C" "$ROOT/circuits/batch_deposit.circom" --r1cs --wasm --sym -l "$ROOT/node_modules" -o "$B/$v"; done
  G="$B/circom-src"  # Groth16 smoke uses the BINDCHECK_CIRCOM default build (v2.2.3); toy, public entropy
  srun c20_input 0 node "$ROOT/scripts/make_input.js" "$G/input.json"
  srun c21_ptau_new 0 "$SNARKJS" powersoftau new bn128 12 "$G/pot0.ptau"
  srun c22_ptau_contrib 0 "$SNARKJS" powersoftau contribute "$G/pot0.ptau" "$G/pot1.ptau" --name=t0-toy -e="bindcheck T0 public toy entropy - not secret"
  srun c23_ptau_prepare 0 "$SNARKJS" powersoftau prepare phase2 "$G/pot1.ptau" "$G/pot.ptau"
  srun c24_setup 0 "$SNARKJS" groth16 setup "$G/batch_deposit.r1cs" "$G/pot.ptau" "$G/c.zkey"
  srun c25_vkey 0 "$SNARKJS" zkey export verificationkey "$G/c.zkey" "$G/vk.json"
  srun c26_witness 0 "$SNARKJS" wtns calculate "$G/batch_deposit_js/batch_deposit.wasm" "$G/input.json" "$G/w.wtns"
  srun c27_wtns_check 0 "$SNARKJS" wtns check "$G/batch_deposit.r1cs" "$G/w.wtns"
  srun c28_prove 0 "$SNARKJS" groth16 prove "$G/c.zkey" "$G/w.wtns" "$G/proof.json" "$G/public.json"
  srun c29_verify 0 "$SNARKJS" groth16 verify "$G/vk.json" "$G/public.json" "$G/proof.json"
  node -e 'const fs=require("fs");const p=JSON.parse(fs.readFileSync(process.argv[1]));p[0]=(BigInt(p[0])+1n).toString();fs.writeFileSync(process.argv[2],JSON.stringify(p))' "$G/public.json" "$G/public_bad.json"
  srun c30_verify_tampered nonzero "$SNARKJS" groth16 verify "$G/vk.json" "$G/public_bad.json" "$G/proof.json"

  # Noir/Barretenberg: x*x == y with y public, x=3, y=9.
  for v in noir-1.0.0-beta.14 noir-1.0.0-beta.22 noir-rc4; do P="$B/$v"; mkdir -p "$P/src"
    printf '[package]\nname = "t0_smoke"\ntype = "bin"\nauthors = [""]\n\n[dependencies]\n' > "$P/Nargo.toml"
    printf 'fn main(x: Field, y: pub Field) {\n    assert(x * x == y);\n}\n' > "$P/src/main.nr"
    printf 'x = "3"\ny = "9"\n' > "$P/Prover.toml"
    srun "n10_version_$v" 0 "$TOOLS/$v/nargo" --version
    srun "n11_execute_$v" 0 "$TOOLS/$v/nargo" execute --program-dir "$P"; done
  P="$B/noir-1.0.0-beta.22"
  for v in bb-5.0.0 bb-6.0.0; do BBX="$TOOLS/$v/bb"; O="$B/out-$v"
    srun "b10_version_$v" 0 "$BBX" --version
    srun "b11_prove_$v" 0 "$BBX" prove -b "$P/target/t0_smoke.json" -w "$P/target/t0_smoke.gz" -o "$O" --write_vk
    srun "b12_verify_$v" 0 "$BBX" verify -k "$O/vk" -p "$O/proof" -i "$O/public_inputs"
    python3 -I -c 'import sys;d=bytearray(open(sys.argv[1],"rb").read());d[-1]^=1;open(sys.argv[2],"wb").write(d)' "$O/public_inputs" "$O/public_inputs_bad"
    srun "b13_verify_tampered_$v" nonzero "$BBX" verify -k "$O/vk" -p "$O/proof" -i "$O/public_inputs_bad"; done
  cat > "$B/bbjs_smoke.mjs" <<'JS'
// usage: node bbjs_smoke.mjs <bb.js package dir> <program.json> <witness.gz>
import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
const [pkg, prog, wit] = process.argv.slice(2);
const version = JSON.parse(readFileSync(pkg + '/package.json', 'utf8')).version;
const bb = await import(pathToFileURL(pkg + '/dest/node/index.js').href);
const program = JSON.parse(readFileSync(prog, 'utf8'));
const witness = readFileSync(wit);
// bb.js >= 4 takes an explicit Barretenberg instance; 3.x creates its own.
const api = Number(version.split('.')[0]) >= 4 ? await bb.Barretenberg.new() : undefined;
const backend = api ? new bb.UltraHonkBackend(program.bytecode, api) : new bb.UltraHonkBackend(program.bytecode);
const proof = await backend.generateProof(witness);
const ok = await backend.verifyProof(proof);
const bad = { ...proof, publicInputs: proof.publicInputs.map(() => '0x' + '0'.repeat(63) + 'a') };
let badOk; try { badOk = await backend.verifyProof(bad); } catch (e) { badOk = 'threw: ' + String(e.message).slice(0, 80); }
console.log('bb.js', version, 'publicInputs', JSON.stringify(proof.publicInputs), 'verify', ok, 'tampered_verify', badOk);
await backend.destroy?.(); await api?.destroy?.();
process.exit(ok === true && badOk !== true ? 0 : 1);
JS
  if [[ "$SKIP_NPM" == 0 ]]; then
    srun j10_bbjs-5.0.0_beta22 0 node "$B/bbjs_smoke.mjs" "$TOOLS/bbjs-5.0.0/node_modules/@aztec/bb.js" \
      "$P/target/t0_smoke.json" "$P/target/t0_smoke.gz"
    P14="$B/noir-1.0.0-beta.14"
    srun j11_bbjs-3.0.0-manual_beta14 0 node "$B/bbjs_smoke.mjs" "$TOOLS/bbjs-3.0.0-manual.20251030/node_modules/@aztec/bb.js" \
      "$P14/target/t0_smoke.json" "$P14/target/t0_smoke.gz"
  fi
  if [[ "$SMOKE_FAIL" == 1 ]]; then echo "SMOKE: at least one step differed from its expectation (see $L/steps.tsv)"; exit 1; fi
  echo "SMOKE: all steps as expected"
fi
if (( ${#BLOCKED[@]} )); then
  echo "---- BLOCKED (not installed) ----"; printf '  %s\n' "${BLOCKED[@]}"; exit 3
fi
