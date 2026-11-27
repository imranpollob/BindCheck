#!/usr/bin/env bash
# Fetch the pinned Noir 1.0.0-rc.4 release used by the T22 secondary case.
# The downloaded toolchain is generated input and stays under ignored tools/noir-rc4/.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/tools/noir-rc4"
VERSION="1.0.0-rc.4"
BASE="https://github.com/noir-lang/noir/releases/download/v$VERSION"

case "$(uname -s):$(uname -m)" in
  Darwin:arm64)
    ARCHIVE="noir-aarch64-apple-darwin.tar.gz"
    SHA256="a2ea54375afd4436677a35f5fd709ee97f30bb0c17fa99cad1d0ad7bee09d203"
    ;;
  Darwin:x86_64)
    ARCHIVE="noir-x86_64-apple-darwin.tar.gz"
    SHA256="a6fb30586a2d8aa7128a3ed3b49d1cfed070fb203ce106966cf782c2ee8d6b86"
    ;;
  Linux:aarch64|Linux:arm64)
    ARCHIVE="noir-aarch64-unknown-linux-gnu.tar.gz"
    SHA256="9ffe665bbdaeaf1d17a1799cd57db55106d35b50a17c03c085fcb7ddc1ede531"
    ;;
  Linux:x86_64)
    ARCHIVE="noir-x86_64-unknown-linux-gnu.tar.gz"
    SHA256="8b06351a89b6cef4b171e1e2e54fb5b1e0ccf1195142eb59b67841d3989b5c0e"
    ;;
  *)
    echo "unsupported host: $(uname -s) $(uname -m)" >&2
    exit 2
    ;;
esac

mkdir -p "$DEST"
TARBALL="$DEST/$ARCHIVE"

if [ ! -f "$TARBALL" ]; then
  curl -fsSL "$BASE/$ARCHIVE" -o "$TARBALL"
fi

OBSERVED="$(shasum -a 256 "$TARBALL" | awk '{print $1}')"
if [ "$OBSERVED" != "$SHA256" ]; then
  echo "checksum mismatch for $TARBALL" >&2
  echo "expected: $SHA256" >&2
  echo "observed: $OBSERVED" >&2
  exit 1
fi

tar -xzf "$TARBALL" -C "$DEST"
"$DEST/nargo" --version
