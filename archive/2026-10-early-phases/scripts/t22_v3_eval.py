#!/usr/bin/env python3
"""T22 evaluation driver (Payy cases + declared mutants). Builds scratch N=8 instances (upstream untouched), compiles with the
pinned nargo, runs T22 (ACIR+spec+cvc5) and T21 (source rules) on the same sources.
usage: t22_eval.py SCRATCH_DIR OUT_JSON   env: NARGO, CVC5, T22_BACKEND, T22_ONLY_CASE"""
import json, os, re, shutil, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t22_v3_tailspec as T22
import t21_tailcheck as T21
S, OUT = sys.argv[1], sys.argv[2]
NARGO = os.environ["NARGO"]; HERE = os.path.dirname(os.path.abspath(__file__))
N = 8
def scale(src): return re.sub(r"\b1005\b", str(N + 5), re.sub(r"\b1000\b", str(N), src))
def src_of(rev, pkg): return open(f"{S}/{rev}/noir/{pkg}/src/main.nr").read()
TAIL_B = scale(src_of("B", "agg_agg"))
FLAG = '''fn assert_message_tail_zero(messages: [Field; 8], messages_index: u32) {
    let mut past = false;
    for i in 0..8 {
        if i == messages_index {
            past = true;
        }
        if past {
            assert(messages[i] == 0, "Message is not zero");
        }
    }
}'''
def sub(s, old, new):
    assert s.count(old) == 1, (old, s.count(old)); return s.replace(old, new)
FN = re.search(r"fn assert_message_tail_zero.*?\n}\n", TAIL_B, re.S).group(0)
U = scale(src_of("B", "agg_utxo"))
CASES = [  # name, pkg, source, spec, expected (declared before running; see results/raw/T22/05_expectations.md)
 ("A agg_agg (earlier)",            "agg_agg",  scale(src_of("A", "agg_agg")), "payy_agg_agg.json", "VIOLATION"),
 ("B agg_agg (check added)",        "agg_agg",  TAIL_B, "payy_agg_agg.json", "VERIFIED_WITHIN_SCOPE"),
 ("agg_utxo (A=B)",                 "agg_utxo", U, "payy_agg_utxo.json", "VERIFIED_WITHIN_SCOPE"),
 ("m1 B: guard > instead of >=",    "agg_agg",  sub(TAIL_B, "if i >= messages_index", "if i > messages_index"), "payy_agg_agg.json", "VIOLATION"),
 ("m2 B: loop skips last slot",     "agg_agg",  sub(TAIL_B, "for i in 0..messages.len() {", "for i in 0..7 {"), "payy_agg_agg.json", "VIOLATION"),
 ("m3 B: helper call deleted",      "agg_agg",  sub(TAIL_B, "    assert_message_tail_zero(messages, messages_index);\n", ""), "payy_agg_agg.json", "VIOLATION"),
 ("m4 B: different idiom (flag)",   "agg_agg",  sub(TAIL_B, FN, FLAG + "\n"), "payy_agg_agg.json", "VERIFIED_WITHIN_SCOPE"),
 ("m5 utxo: tail loop deleted",     "agg_utxo", re.sub(r"    // Verify all other messages are zero\n.*?\n    }\n", "", U, flags=re.S), "payy_agg_utxo.json", "VIOLATION"),
 ("m6 utxo: else-branch idiom",     "agg_utxo", sub(U, "        if i >= messages_index {\n            assert(messages[i] == 0, \"Message is not zero\");\n        }", "        if i < messages_index {\n        } else {\n            assert(messages[i] == 0, \"Message is not zero\");\n        }"), "payy_agg_utxo.json", "VERIFIED_WITHIN_SCOPE"),
]
ONLY_CASE = os.environ.get("T22_ONLY_CASE")
if ONLY_CASE:
    CASES = [case for case in CASES if case[0] == ONLY_CASE]
    if len(CASES) != 1:
        raise SystemExit(f"T22_ONLY_CASE did not match exactly one case: {ONLY_CASE!r}")
res = []
for name, pkg, src, specf, exp in CASES:
    d = f"{S}/work_{re.sub(r'[^a-z0-9]+', '_', name.lower())}"
    if not os.path.exists(d): shutil.copytree(f"{S}/B", d)
    open(f"{d}/noir/{pkg}/src/main.nr", "w").write(src)
    t0 = time.time()
    r = subprocess.run([NARGO, "compile", "--package", pkg, "--print-acir"], cwd=f"{d}/noir", capture_output=True, text=True)
    t_compile = time.time() - t0
    os.makedirs(f"{OUT}.artifacts", exist_ok=True)
    slug = re.sub(r'[^a-z0-9]+', '_', name.lower())
    base = f"{OUT}.artifacts/{slug}"
    open(base + ".compile.stdout", "w").write(r.stdout)
    open(base + ".compile.stderr", "w").write(r.stderr)
    open(base + ".source.nr", "w").write(src)
    if r.returncode != 0:
        res.append({"case": name, "expected": exp, "t22": "UNKNOWN", "queries": {},
                    "compile_exit_status": r.returncode, "notes": ["compile failed"]})
        json.dump(res, open(OUT, "w"), indent=1)
        print(f"{name}: UNKNOWN compile exit {r.returncode}", flush=True)
        continue
    acir_text = r.stdout
    abi = json.load(open(f"{d}/noir/target/{pkg}.json"))["abi"]
    json.dump(abi, open(base + ".abi.json", "w"), indent=2)
    spec = json.load(open(f"{HERE}/t22_specs/{specf}"))
    smt_dir = f"{OUT}.smt/{re.sub(r'[^a-z0-9]+', '_', name.lower())}"
    t0 = time.time(); rep = T22.run(spec, acir_text, abi, int(os.environ.get("TLIMIT", "300")), smt_dir); t_t22 = time.time() - t0
    r21 = T21.analyze(src, label=name)
    res.append({"case": name, "expected": exp, "t22": rep["verdict"], "t21": r21.verdict, "t21_first_reason": (r21.unknown[:1] or [""])[0][:140],
                "t22_seconds": round(t_t22, 1), "compile_seconds": round(t_compile, 1), "compile_exit_status": r.returncode, "queries": rep["queries"],
                "checked": rep["checked"], "assumed": rep["assumed"], "notes": rep["notes"]})
    json.dump(res, open(OUT, "w"), indent=1)
    print(f"{name:34} exp={exp:19} T22={rep['verdict']:19} T21={r21.verdict:14} ({t_t22:.0f}s)", flush=True)
json.dump(res, open(OUT, "w"), indent=1)
