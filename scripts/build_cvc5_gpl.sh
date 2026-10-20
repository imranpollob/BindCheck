#!/usr/bin/env bash
# Build the pinned cvc5 release with CoCoA, which is required for QF_FF.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$ROOT/tools/cases/cvc5-1.4.2"
PREFIX="$ROOT/tools/cvc5-1.4.2-gpl"
BUILD="$SOURCE/build-gpl"
COMMIT="282d5e0c84baf49c780704c532f87ba66d8b513d"
JOBS="${JOBS:-4}"

mkdir -p "$ROOT/tools/cases"
if [ ! -d "$SOURCE/.git" ]; then
  git clone --quiet --depth 1 --branch cvc5-1.4.2 \
    https://github.com/cvc5/cvc5.git "$SOURCE"
fi

ACTUAL="$(git -C "$SOURCE" rev-parse HEAD)"
if [ "$ACTUAL" != "$COMMIT" ]; then
  echo "unexpected cvc5 source commit: $ACTUAL" >&2
  echo "expected: $COMMIT" >&2
  exit 1
fi

if [ "$(uname -s)" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
  LLVM_PREFIX="$(brew --prefix llvm)"
  if [ -x "$LLVM_PREFIX/bin/clang" ] && [ -x "$LLVM_PREFIX/bin/clang++" ]; then
    export CC="$LLVM_PREFIX/bin/clang"
    export CXX="$LLVM_PREFIX/bin/clang++"
  fi
fi

cd "$SOURCE"
./configure.sh unrestricted \
  --name=build-gpl \
  --auto-download \
  --cocoa \
  --gpl \
  --prefix="$PREFIX"
cmake --build "$BUILD" --parallel "$JOBS"
cmake --install "$BUILD"

SMOKE='(set-logic QF_FF)
(define-sort F () (_ FiniteField 13))
(declare-const x F)
(assert (= (ff.mul x x) (as ff4 F)))
(check-sat)'
RESULT="$(printf '%s\n' "$SMOKE" | "$PREFIX/bin/cvc5" --lang=smt2)"
if [ "$RESULT" != "sat" ]; then
  echo "finite-field smoke test failed: $RESULT" >&2
  exit 1
fi

"$PREFIX/bin/cvc5" --version | head -1
echo "finite-field smoke test: sat"
