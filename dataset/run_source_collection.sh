#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$ROOT/dataset/collect_source_corpus.py"
python3 "$ROOT/dataset/label_dev_maturity.py"
