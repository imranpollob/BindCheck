#!/usr/bin/env python3
"""Per-chain counts from dataset/onchain-census.csv (read-only). usage: census_by_chain.py <csv> <out.json>"""
import csv, json, sys
from collections import Counter, defaultdict
rows = list(csv.DictReader(open(sys.argv[1])))
uniq = {}
for r in rows:
    uniq[(r["chain_id"], r["address"].lower())] = r
cols = list(rows[0].keys())
flag = "default_g2_twice_gamma_delta_signature"
by_chain = Counter(k[0] for k in uniq)
flag_by_chain = Counter(k[0] for k, r in uniq.items() if r[flag].strip().lower() in ("1", "true", "yes"))
out = {"source": sys.argv[1], "flag_column": flag, "rows": len(rows), "unique": len(uniq),
       "unique_by_chain": dict(sorted(by_chain.items())), "default_key_unique_by_chain": dict(sorted(flag_by_chain.items())),
       "default_key_unique_total": sum(flag_by_chain.values())}
json.dump(out, open(sys.argv[2], "w"), indent=2); print(json.dumps(out, indent=2))
