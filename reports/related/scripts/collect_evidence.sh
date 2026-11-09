#!/usr/bin/env bash
# Lane D (related work) evidence collector.
#
# Reproduces every number in RELATED-WORK.md that this lane computed itself.
# Raw downloads go to results/raw/related/ (git-ignored). Small derived
# summaries are written to reports/related/evidence/ (tracked).
#
# Usage: bash reports/related/scripts/collect_evidence.sh
# Needs: curl, gh (authenticated), git, pdftotext (poppler), python3.
# Network: read-only HTTPS GETs and one HTTPS POST (researchr download form)
# to public sites. No chain RPC, no transaction, no maintainer contact.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
RAW="$ROOT/results/raw/related"
EV="$ROOT/reports/related/evidence"
mkdir -p "$RAW/papers" "$RAW/elsa" "$EV"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

fetch() { # name url
  local out="$RAW/papers/$1"
  if [ ! -s "$out" ]; then curl -sSL -A "$UA" -o "$out" "$2"; fi
  pdftotext -layout "$out" "${out%.pdf}.txt" 2>/dev/null || true
  pdftotext -raw "$out" "${out%.pdf}.raw.txt" 2>/dev/null || true
}

# ---------------------------------------------------------------- 1. papers
fetch sok-2402.15293.pdf       https://arxiv.org/pdf/2402.15293
fetch tools-2607.23752.pdf     https://arxiv.org/pdf/2607.23752
fetch zkfuzz-2504.11961.pdf    https://arxiv.org/pdf/2504.11961
fetch zkcraft-2602.00667.pdf   https://arxiv.org/pdf/2602.00667
fetch liezz-2608.30648.pdf     https://arxiv.org/pdf/2608.30648
fetch ccccheck-sp26.pdf        https://vdb.space/papers/zkp2026.pdf
fetch zkap-usenix24.pdf        https://www.usenix.org/system/files/usenixsecurity24-wen_1.pdf
fetch smartaxe-2406.15999.pdf  https://arxiv.org/pdf/2406.15999

# ELSA (ISSTA 2026): ACM DL returns HTTP 403 to scripted clients; the
# official researchr page offers the authors' presentation slides.
if [ ! -s "$RAW/elsa/slides.pdf" ]; then
  curl -sSL -A "$UA" -o "$RAW/elsa/slides.pdf" -X POST "https://conf.researchr.org/details" \
    --data-urlencode "context=issta-2026" \
    --data-urlencode "track=issta-2026-research-papers" \
    --data-urlencode "urlKey=131" \
    --data-urlencode "decoTitle=Augmenting-Multi-Technique-Static-Analysis-with-Large-Language-Models-A-Neuro-Symbol" \
    --data-urlencode "3f48961a8c2344a59837f49e39d61a08action_1742650661072e03b7a79c526b5d946f0f4f3f278cc=1"
fi
pdftotext -layout "$RAW/elsa/slides.pdf" "$RAW/elsa/slides.txt" 2>/dev/null || true
curl -sSL -o "$RAW/elsa/doi-status.txt" -w "%{http_code}\n" -A "$UA" https://dl.acm.org/doi/pdf/10.1145/3832222 >"$RAW/elsa/acm-http-status.txt" || true

{
  echo "# SHA-256 of downloaded primary sources ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
  (cd "$RAW" && shasum -a 256 papers/*.pdf elsa/slides.pdf)
  echo "# ACM DL PDF HTTP status for 10.1145/3832222: $(cat "$RAW/elsa/acm-http-status.txt")"
} >"$EV/source-hashes.txt"

# ------------------------------------------------- 2. greps from primary text
{
  T="$RAW/papers/sok-2402.15293.txt"
  echo "## SoK 2402.15293: dataset size"
  grep -n -m3 "141" "$T" || true
  echo "## SoK Table 5 (integration vulnerabilities)"
  grep -n -E "Integration Design Error|Missing Validation Input|^ *.*Total +1 +2 +9 +1" "$T" | cut -c60- || true
  echo "## SoK Table 2/3 integration rows (layer total; impact: soundness/completeness/ZK)"
  grep -n -E "Integration +8 +1 +4 +13|Integration +11 +2 +0" "$T" | sed -E 's/^([0-9]+:).*(Integration +[0-9 ]+)$/\1 \2/' || true
  echo "## SoK: integration-layer defences"
  grep -n -E "no specific defenses|no defense detects bugs in that layer|combined testing|multi-layer testing" "$T" || true
  echo
  T="$RAW/papers/tools-2607.23752.txt"
  echo "## Tools study 2607.23752: scope and headline numbers"
  grep -n -E "six tools across|70 real-world vulnerabilities|45\.7%|19\.6%|System integration +26% +5%|integrations$|of ZKPs with smart contracts|We leave the systematic study" "$T" || true
  R="$RAW/papers/tools-2607.23752.raw.txt"
  echo "## Tools study: refs 87-89 (the only 'integrations of ZKPs with smart contracts' citations)"
  grep -n -A2 -E "^\[(87|88|89)\]" "$R" | tail -9 || true
  echo "## Tools study: evaluated tools (figure labels)"
  grep -n -m6 -E "^(Picus|Civer|Ecne|Circomspect|zkFuzz|ConsCS)$" "$R" || true
  echo
  echo "## Solidity / smart-contract mentions in circuit-tool papers (count of lines)"
  for f in ccccheck-sp26 zkfuzz-2504.11961 zkcraft-2602.00667 liezz-2608.30648 zkap-usenix24; do
    printf "%s: %s\n" "$f" "$(grep -c -i -E 'solidity|smart contract' "$RAW/papers/$f.txt" || true)"
  done
  echo "## ZKAP: unused public input discussion"
  grep -n -E "UnusedPubInput|public input is completely" "$RAW/papers/zkap-usenix24.raw.txt" || true
  echo
  T="$RAW/elsa/slides.txt"
  echo "## ELSA slides: scope lines"
  grep -n -E "github.com/Anonymize-gitcode/ELSA|2,310|224 +Complex|Detection range|107 reentrancy|ZKP model|Analyzers|signature replay|synthetic ZKP injection" "$T" || true
} >"$EV/primary-text-greps.txt"

# ------------------------------------------------ 3. ELSA artifact inventory
ELSA_SHA=509c987365502cee53764e552e14e42575cc7316
gh api "repos/Anonymize-gitcode/ELSA/git/trees/$ELSA_SHA?recursive=1" >"$RAW/elsa/tree.json"
python3 -I - "$RAW/elsa/tree.json" "$ELSA_SHA" >"$EV/elsa-artifact-inventory.txt" <<'EOF'
import json, sys, collections, re
d = json.load(open(sys.argv[1]))
paths = [t["path"] for t in d["tree"] if t["type"] == "blob"]
print("repository: https://github.com/Anonymize-gitcode/ELSA")
print("commit:", sys.argv[2], "| tree truncated:", d["truncated"])
print("blob paths:", len(paths))
print(".sol files:", sum(p.endswith(".sol") for p in paths))
circ = [p for p in paths if re.search(r"\.(circom|zok|nr|r1cs|zkey|sym)$", p)]
print("circuit/constraint files (.circom/.zok/.nr/.r1cs/.zkey/.sym):", len(circ))
cats = collections.Counter(p.split("/")[2] for p in paths
                           if p.startswith("datasets/ZKP_dataset/") and p.endswith(".sol"))
print("datasets/ZKP_dataset .sol files by category:")
for k, v in sorted(cats.items()):
    print(f"  {k}: {v}")
print("  total:", sum(cats.values()))
EOF

# ------------------------------------------------ 4. zkbugs aggregate census
ZKB_SHA=212cc500b7cf1a2221d3e42ff47baff453afd070
TMP="$(mktemp -d "${TMPDIR:-/tmp}/zkbugs.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
git clone -q --filter=blob:none --no-checkout https://github.com/zksecurity/zkbugs "$TMP/zkbugs"
git -C "$TMP/zkbugs" sparse-checkout set --no-cone '**/zkbugs_config.json'
git -C "$TMP/zkbugs" checkout -q "$ZKB_SHA"
python3 -I - "$TMP/zkbugs" "$ZKB_SHA" >"$EV/zkbugs-census.txt" <<'EOF'
# Aggregate only: no per-project rows are printed (lane data wall).
import json, sys, glob, os, collections
root, sha = sys.argv[1], sys.argv[2]
files = glob.glob(os.path.join(root, "**", "zkbugs_config.json"), recursive=True)
dsl, vul, rc, ext = (collections.Counter() for _ in range(4))
n = 0
for f in files:
    for _, b in json.load(open(f)).items():
        n += 1
        dsl[b.get("DSL")] += 1
        vul[b.get("Vulnerability")] += 1
        rc[b.get("Root Cause")] += 1
        loc = b.get("Location") or {}
        path = loc.get("Path", "") if isinstance(loc, dict) else ""
        ext[os.path.splitext(path)[1] or "(none)"] += 1
print("repository: https://github.com/zksecurity/zkbugs  commit:", sha)
print("bug entries:", n)
for name, c in (("DSL", dsl), ("Vulnerability", vul), ("Root Cause", rc), ("Location file extension", ext)):
    print(f"{name}:", dict(c.most_common()))
print("entries whose Location is a .sol file:", ext.get(".sol", 0))
EOF

# --------------------------------------- 5. BindCheck DEV facts (allowed rows)
python3 -I - "$ROOT/reports/T25-full-dev-ledger.csv" >"$EV/t25-dev-verdict-counts.txt" <<'EOF'
import csv, sys, collections, hashlib
path = sys.argv[1]
print("file:", "reports/T25-full-dev-ledger.csv",
      "sha256:", hashlib.sha256(open(path, "rb").read()).hexdigest())
rows = [r for r in csv.DictReader(open(path)) if r["phase"] == "after"]
print("phase=after repositories:", len(rows))
for p in ("P1", "P2", "P3", "P4", "P5"):
    v = collections.Counter(r[p + "_verdict"] for r in rows)
    a = collections.Counter(r[p + "_applicability"] for r in rows)
    print(p, "verdicts", dict(sorted(v.items())), "applicability", dict(sorted(a.items())))
viol = [(r["id"], p, r[p + "_reasons"]) for r in rows for p in ("P1", "P2", "P3", "P4", "P5")
        if r[p + "_verdict"] == "VIOLATION"]
print("VIOLATION rows:", len(viol))
for x in viol:
    print("  ", *x)
print("circuit builds ok:", sum(int(r["builds_ok"] or 0) for r in rows),
      "failed:", sum(int(r["builds_failed"] or 0) for r in rows))
EOF

echo "wrote: $EV/{source-hashes,primary-text-greps,elsa-artifact-inventory,zkbugs-census,t25-dev-verdict-counts}.txt"
