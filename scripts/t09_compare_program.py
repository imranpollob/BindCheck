#!/usr/bin/env python3
"""T09: compare two Noir program JSONs on the fields that define the circuit (ACIR bytecode, ABI, expression width,
compiler version). file_map / debug_symbols / hash depend on build paths and are reported but not required equal.
usage: python3 -I t09_compare_program.py <committed.json> <compiled.json>"""
import json, sys
a, b = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
core = ["bytecode", "abi", "expression_width", "noir_version"]
ok = True
for k in core:
    eq = a.get(k) == b.get(k); ok &= eq
    print(f"{k:18} equal={eq}")
for k in ["file_map", "debug_symbols", "hash"]:
    print(f"{k:18} equal={a.get(k) == b.get(k)}  (path/build dependent, informational)")
print("CIRCUIT-DEFINING FIELDS IDENTICAL" if ok else "CIRCUIT-DEFINING FIELDS DIFFER")
sys.exit(0 if ok else 1)
