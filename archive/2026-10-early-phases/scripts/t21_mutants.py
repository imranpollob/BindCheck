#!/usr/bin/env python3
"""T21 sanity mutants: textual edits of the real sources, expected verdicts fixed in 00_preregistration.md.
Usage: t21_mutants.py SRC_DIR   (SRC_DIR has A_c4d2c90/ B_dcd5d96/ each with agg_agg/main.nr, agg_utxo/main.nr)"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from t21_tailcheck import analyze

d = sys.argv[1]
rd = lambda r, f: open(os.path.join(d, r, f, "main.nr")).read()
A, B, U = rd("A_c4d2c90", "agg_agg"), rd("B_dcd5d96", "agg_agg"), rd("B_dcd5d96", "agg_utxo")
CALL = "    assert_message_tail_zero(messages, messages_index);\n"
LOOP = re.search(r"    // Verify all other messages are zero\n.*?\n    }\n", U, re.S).group(0)

def sub(s, old, new, count=1):
    assert s.count(old) == count, (old, s.count(old)); return s.replace(old, new)
def rename(s): return re.sub(r"\bmessages_index\b", "out_n", re.sub(r"\bmessages\b", "out_words", s))

M = [
 ("m1 B: guard >= -> >",              sub(B, "if i >= messages_index", "if i > messages_index"), "UNKNOWN"),
 ("m2 B: assert == 0 -> != 0",        sub(B, "assert(messages[i] == 0,", "assert(messages[i] != 0,"), "UNKNOWN"),
 ("m3 B: delete helper call",         sub(B, CALL, ""), "UNCONSTRAINED"),
 ("m4 B: call before proofs loop",    sub(sub(B, CALL, ""), "    for i in 0..2 {", CALL + "    for i in 0..2 {"), "UNKNOWN"),
 ("m5 utxo: delete tail loop",        sub(U, LOOP, ""), "UNCONSTRAINED"),
 ("m6 utxo: tail loop under if",      sub(U, LOOP, "    if root != 0 {\n" + LOOP + "    }\n"), "UNKNOWN"),
 ("m7 B: loop bound 0..999",          sub(B, "for i in 0..messages.len() {", "for i in 0..999 {"), "UNKNOWN"),
 ("m8 A: hash(messages) added",       sub(A, "    assert(new_root == root", "    let h = poseidon2::Poseidon2::hash(messages, 1000);\n    assert(new_root == root"), "UNKNOWN"),
 ("m9 A renamed identifiers",         rename(A), "UNCONSTRAINED"),
 ("m10 B renamed identifiers",        rename(B), "SATISFIED"),
]
bad = 0
print(f"{'mutant':34} {'expected':14} {'got':14} ok  first reason")
for name, src, exp in M:
    R = analyze(src, label=name)
    ok = R.verdict == exp; bad += not ok
    print(f"{name:34} {exp:14} {R.verdict:14} {'Y' if ok else 'N'}   {(R.unknown[0] if R.unknown else '')[:100]}")
sys.exit(1 if bad else 0)
