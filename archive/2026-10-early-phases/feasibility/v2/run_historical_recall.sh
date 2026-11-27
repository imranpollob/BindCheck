#!/usr/bin/env bash
# Source-level recall controls at exact vulnerable/fixed revisions. Dynamic
# zkDrops E4 is a separate one-command run_zkdrops_alias_e4.sh reproduction.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HIST="$ROOT/feasibility/work/v2/historical"
ZKDROPS="$HIST/zkdrops"
SEMAPHORE="$HIST/semaphore"
ZK_VULN="4002962fb632578dd12477346d2e5c4159ffb2ef"
ZK_FIX="f6f58020911cd2a19e1639f0dc93ec9fca2a9e17"
SEM_VULN="8d703c124c663537966d6fc35cfec84146e236b2"
SEM_FIX="3dcf79f6a095397352f71384e3dc6889c640a50f"
RUN_ID="historical-recall-$(date -u +%Y%m%dT%H%M%SZ)-$$"
OUT="$ROOT/results/raw/feasibility-v2/$RUN_ID"
mkdir -p "$HIST" "$OUT/sources" "$OUT/screens"

if [[ ! -d "$ZKDROPS/.git" ]]; then
  git clone https://github.com/a16z/zkdrops.git "$ZKDROPS"
fi
if ! git -C "$ZKDROPS" cat-file -e "$ZK_FIX^{commit}" 2>/dev/null; then
  git -C "$ZKDROPS" fetch origin "$ZK_FIX"
fi
if [[ ! -d "$SEMAPHORE/.git" ]]; then
  git clone https://github.com/semaphore-protocol/semaphore.git "$SEMAPHORE"
fi

[[ "$(git -C "$ZKDROPS" rev-parse "$ZK_FIX^")" == "$ZK_VULN" ]]
[[ "$(git -C "$SEMAPHORE" rev-parse "$SEM_FIX^")" == "$SEM_VULN" ]]

for label_commit in \
  "zkdrops-vulnerable:$ZK_VULN" "zkdrops-fixed:$ZK_FIX"; do
  label="${label_commit%%:*}"
  commit="${label_commit#*:}"
  mkdir -p "$OUT/sources/$label"
  git -C "$ZKDROPS" archive "$commit" | tar -x -C "$OUT/sources/$label"
  python3 "$ROOT/feasibility/v2/screen_consumers.py" --repo "$OUT/sources/$label" \
    --output-json "$OUT/screens/$label.json" --output-csv "$OUT/screens/$label.csv" \
    > "$OUT/screens/$label.log"
done

for label_commit in \
  "semaphore-vulnerable:$SEM_VULN" "semaphore-fixed:$SEM_FIX"; do
  label="${label_commit%%:*}"
  commit="${label_commit#*:}"
  mkdir -p "$OUT/sources/$label"
  git -C "$SEMAPHORE" archive "$commit:semaphorejs" | tar -x -C "$OUT/sources/$label"
  python3 "$ROOT/feasibility/v2/screen_consumers.py" --repo "$OUT/sources/$label" \
    --output-json "$OUT/screens/$label.json" --output-csv "$OUT/screens/$label.csv" \
    > "$OUT/screens/$label.log"
done

python3 - "$OUT" "$ZK_VULN" "$ZK_FIX" "$SEM_VULN" "$SEM_FIX" <<'PY'
import hashlib
import json
import pathlib
import sys

out = pathlib.Path(sys.argv[1])
commits = {
    "zkdrops-vulnerable": sys.argv[2],
    "zkdrops-fixed": sys.argv[3],
    "semaphore-vulnerable": sys.argv[4],
    "semaphore-fixed": sys.argv[5],
}
cases = []
for label, commit in commits.items():
    screen = json.loads((out / "screens" / f"{label}.json").read_text())
    p3 = [
        {"path": record["path"], "function": record["function"], "warnings": record["warnings"]["P3"]}
        for record in screen["records"] if record["warnings"]["P3"]
    ]
    sources = sorted(path for path in (out / "sources" / label).rglob("*.sol") if path.is_file())
    cases.append({
        "label": label,
        "commit": commit,
        "p3_check_fired": bool(p3),
        "p3_records": p3,
        "solidity_files": len(sources),
        "source_set_sha256": hashlib.sha256("".join(
            hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.relative_to(out / "sources" / label).as_posix() + "\n"
            for path in sources
        ).encode()).hexdigest(),
    })

by_label = {case["label"]: case for case in cases}
assert by_label["zkdrops-vulnerable"]["p3_check_fired"]
assert not by_label["zkdrops-fixed"]["p3_check_fired"]
assert by_label["semaphore-vulnerable"]["p3_check_fired"]
payload = {
    "scope": "source-level historical recall; dynamic grades are reported separately",
    "cases": cases,
    "vulnerable_cases_detected": 2,
    "vulnerable_cases_total": 2,
    "fixed_zkdrops_negative_control_clear": True,
    "semaphore_fixed_note": "The fixed revision replaces the signal-tree insert with direct signal storage, so the current proof+effect prefilter does not emit a function record; its verifier-side <r fix is source-confirmed.",
}
(out / "summary.json").write_text(json.dumps(payload, indent=2) + "\n")
PY

{
  echo "run_id=$RUN_ID"
  echo "date_utc=$(date -u +%FT%TZ)"
  echo "workspace_git_head=$(git -C "$ROOT" rev-parse HEAD)"
  echo "zkdrops_vulnerable=$ZK_VULN"
  echo "zkdrops_fixed=$ZK_FIX"
  echo "semaphore_vulnerable=$SEM_VULN"
  echo "semaphore_fixed=$SEM_FIX"
} > "$OUT/environment.txt"

echo "RESULT: P3 check fired on both exact vulnerable revisions and cleared the zkDrops fixed control"
echo "EVIDENCE: $OUT"
