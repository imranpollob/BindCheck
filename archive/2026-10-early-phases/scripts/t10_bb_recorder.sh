#!/usr/bin/env bash
# Pass-through recorder named `bb` for PATH. It executes the REAL pinned bb with the identical arguments and returns
# its exit status and output unchanged; it only copies the files bb is given or writes (key, program, proof, public
# inputs, prove output dir) and per-call timing/peak-RSS into $T10_CAPTURE_DIR. It is not a mock.
set -u
REAL="${T10_REAL_BB:?}"; CAP="${T10_CAPTURE_DIR:?}"; mkdir -p "$CAP"
seq=$(( $(ls "$CAP" | grep -c '^[0-9]') + 1 )); sub="${1:-none}"
d="$CAP/$(printf %03d "$seq")-$sub"; mkdir -p "$d"
printf '%q ' "$@" > "$d/args.txt"
arg_of() { local f="$1"; shift; while [ $# -gt 1 ]; do [ "$1" = "$f" ] && { echo "$2"; return; }; shift; done; }
K=$(arg_of -k "$@"); P=$(arg_of -p "$@"); I=$(arg_of -i "$@"); O=$(arg_of -o "$@"); B=$(arg_of -b "$@"); W=$(arg_of -w "$@")
/usr/bin/time -l -o "$d/rusage.txt" "$REAL" "$@" > "$d/stdout.txt" 2> "$d/stderr.txt"; code=$?
cat "$d/stdout.txt"; cat "$d/stderr.txt" >&2
echo "$code" > "$d/exit.txt"
[ -n "$K" ] && [ -f "$K" ] && cp "$K" "$d/key"
[ -n "$B" ] && [ -f "$B" ] && cp "$B" "$d/program.json"
[ -n "$P" ] && [ -f "$P" ] && cp "$P" "$d/proof_in"
[ -n "$I" ] && [ -f "$I" ] && cp "$I" "$d/public_inputs_in"
[ -n "$W" ] && [ -f "$W" ] && { shasum -a 256 "$W" | cut -d' ' -f1 > "$d/witness.sha256"; wc -c < "$W" > "$d/witness.bytes"; }
[ -n "$O" ] && [ -d "$O" ] && { mkdir -p "$d/out"; cp -R "$O"/. "$d/out/" 2>/dev/null; }
exit "$code"
