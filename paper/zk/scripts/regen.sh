#!/bin/sh
# Regenerate every file under paper/zk/data/ and rebuild the PDF.
# Read-only over all inputs; run from the repository root.
set -eu
PY=/opt/homebrew/bin/python3
RAW_SOUND=/Users/imranpollob/Coding/bc/bindcheck-zk-soundness/results/raw/soundness/after-20261109T061325Z-77918
RAW_RT=/Users/imranpollob/Coding/bc/bindcheck-zk-redteam/results/raw/redteam/dev-20261109-final/cases
DEV=/Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev
D=paper/zk/data
export PYTHONDONTWRITEBYTECODE=1
$PY -I paper/zk/scripts/paper_stats.py "$RAW_SOUND"
$PY paper/zk/scripts/check_p4_g2_constant.py "$DEV" $D/p4-g2-constant-check.json
$PY -I paper/zk/scripts/crossref_p4_certifications.py $D/p4-g2-constant-check.json "$RAW_SOUND" $D/p4-unsafe-certifications.json
$PY -I paper/zk/scripts/pair_discrimination.py "$RAW_RT" "$RAW_SOUND" $D/pair-discrimination.json
$PY -I paper/zk/scripts/zkvoting_facts.py "$DEV/DEV-F34--avitenzer__zk_voting--18d3a277ccd8" $D/zkvoting-facts.json
$PY -I paper/zk/scripts/census_by_chain.py dataset/onchain-census.csv $D/census-by-chain.json
cd paper/zk && tectonic -X compile main.tex --keep-logs
