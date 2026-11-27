#!/usr/bin/env bash
# S1 step 5: date the canonical-input guards in published @aztec/bb.js packages.
# Downloads a version's npm tarball, checks it against the registry sha512
# integrity, and counts three marker strings in the packaged files
# (Solidity template guard, old reducing fromBytes32, native error message).
# Usage: bbjs_markers.sh <registry.json> <workdir> <version>...
set -euo pipefail
REG="$1"; WORK="$2"; shift 2
mkdir -p "$WORK"
for v in "$@"; do
  read -r url integrity < <(python3 -I -c 'import json,sys; d=json.load(open(sys.argv[1]))["versions"][sys.argv[2]]["dist"]; print(d["tarball"], d["integrity"])' "$REG" "$v")
  tgz="$WORK/bbjs-$v.tgz"; dir="$WORK/bbjs-$v"
  [[ -f "$tgz" ]] || curl -sS -m 600 -o "$tgz" "$url"
  got="sha512-$(openssl dgst -sha512 -binary "$tgz" | base64 -w0)"
  [[ "$got" == "$integrity" ]] || { echo "$v integrity MISMATCH" >&2; exit 3; }
  rm -rf "$dir"; mkdir -p "$dir"; tar -xzf "$tgz" -C "$dir"
  # Expand any gzipped wasm so its strings are searchable.
  find "$dir" -name '*.wasm.gz' -exec sh -c 'gzip -dc "$1" > "${1%.gz}"' _ {} \;
  count() { grep -r -a -o -F "$1" "$dir" 2>/dev/null | wc -l; }
  printf '%s\t%s\tsolidity_guard=%s\told_reducing_fromBytes32=%s\tnative_noncanonical_error=%s\tsha512_ok\n' \
    "$v" "$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["time"][sys.argv[2]][:10])' "$REG" "$v")" \
    "$(count 'require(uint256(publicInputs[i]) < P')" "$(count 'uint256(value) % MODULUS')" "$(count 'Non-canonical public input')"
  rm -rf "$dir"
done
