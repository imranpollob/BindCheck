#!/usr/bin/env python3
"""T11: compare the creation code Foundry compiled for HonkVerifier with Payy's committed eth/contracts/noir/agg_final_HonkVerifier.bin,
ignoring (a) the 20-byte library-address slot named in the committed linkrefs.json and (b) the trailing solc metadata (CBOR).
usage: python3 -I t11_compare_bytecode.py <upstream.bin> <linkrefs.json> <foundry_artifact.json>"""
import json, re, sys
up = open(sys.argv[1]).read().strip(); refs = json.load(open(sys.argv[2]))
start = refs["agg_final.sol"]["ZKTranscriptLib"][0]["start"]; length = refs["agg_final.sol"]["ZKTranscriptLib"][0]["length"]
mine = json.load(open(sys.argv[3]))["bytecode"]["object"][2:]
strip = lambda x: x[:-(int(x[-4:], 16) + 2) * 2]
u = up[:start * 2] + "0" * (length * 2) + up[(start + length) * 2:]
m = re.sub(r"__\$[0-9a-f]{34}\$__", "0" * 40, mine)
us, ms = strip(u), strip(m)
print(f"upstream creation code: {len(up)//2} bytes; compiled here: {len(mine)//2} bytes; after removing metadata: {len(us)//2} vs {len(ms)//2}")
print(f"library slot: upstream linkrefs start={start} length={length}; compiled placeholder offset={re.search(r'__[$]', mine).start()//2}")
same = us == ms
print("IDENTICAL (excluding the library-address slot and metadata):", same)
sys.exit(0 if same else 1)
