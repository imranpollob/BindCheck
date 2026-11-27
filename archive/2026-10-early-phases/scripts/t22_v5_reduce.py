#!/usr/bin/env python3
"""Byte-preserving subset reduction of a saved T22-v5 SMT query.

Retained assertions and their transitive definitions/declarations are copied
verbatim. A reduction is a relaxation, not an equivalent circuit query.
"""
import argparse
import hashlib
import json
import re
import resource
import subprocess
import time
from pathlib import Path

SYM = re.compile(r"\b(?:d|b|w|rb)\d+\b")
DEF = re.compile(r"^\(define-fun ((?:d|b)\d+) ")
DECL = re.compile(r"^\(declare-const ((?:w|rb)\d+) ")


def digest(data): return hashlib.sha256(data).hexdigest()


def render(source, indices):
    lines = source.splitlines()
    assertions = [(i, line) for i, line in enumerate(lines) if line.startswith("(assert ")]
    if len(assertions) < 2 or any(k < 0 or k >= len(assertions) - 1 for k in indices):
        raise ValueError("invalid ACIR assertion index")
    chosen = [assertions[k] for k in sorted(set(indices))] + [assertions[-1]]
    defs, decls = {}, {}
    for i, line in enumerate(lines):
        d, c = DEF.match(line), DECL.match(line)
        if d: defs[d.group(1)] = (i, line)
        if c: decls[c.group(1)] = (i, line)

    def closure(selected):
        used, pending = set(), set().union(*(set(SYM.findall(line)) for _, line in selected))
        while pending:
            name = pending.pop()
            if name in used: continue
            used.add(name)
            if name in defs: pending |= set(SYM.findall(defs[name][1])) - {name} - used
        return used

    used = closure(chosen)
    goal_witnesses = {n for n in closure([assertions[-1]]) if n.startswith("w")}
    line_indices = {0, 1, 2} | {i for i, _ in chosen}
    line_indices |= {defs[name][0] for name in used if name in defs}
    line_indices |= {decls[name][0] for name in used if name in decls}
    output = "\n".join(lines[i] for i in sorted(line_indices)) + "\n(check-sat)\n"
    meta = {
        "source_sha256": digest(source.encode()),
        "reduced_sha256": digest(output.encode()),
        "source_assertions": len(assertions),
        "retained_acir_assertion_indices_0_based": sorted(set(indices)),
        "retained_acir_assertions": [assertions[k][1] for k in sorted(set(indices))],
        "shared_goal_witnesses_through_definitions": {
            str(k): sorted({n for n in closure([assertions[k]]) if n.startswith("w")}
                           & goal_witnesses)
            for k in sorted(set(indices))},
        "reduced_bytes": len(output.encode()),
        "retained_definitions": sum(lines[i].startswith("(define-fun ") for i in line_indices),
        "retained_declarations": sum(lines[i].startswith("(declare-const ") for i in line_indices),
    }
    return output, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--count", type=int)
    group.add_argument("--index", type=int)
    ap.add_argument("--cvc5", type=Path, required=True)
    ap.add_argument("--seconds", type=int, required=True)
    args = ap.parse_args()
    source = args.source.read_text()
    indices = list(range(args.count)) if args.count is not None else [args.index]
    query, meta = render(source, indices)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(query)
    meta.update({"source": str(args.source), "output": str(args.output),
                 "time_limit_seconds": args.seconds, "memory_limit_bytes": 4 * 1024**3})
    command = [str(args.cvc5), "--lang=smt2", "--ff-solver=split", str(args.output)]

    def limit(): resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3,) * 2)

    start = time.monotonic()
    try:
        r = subprocess.run(command, capture_output=True, text=True,
                           timeout=args.seconds, preexec_fn=limit)
        meta.update({"exit_status": r.returncode, "timed_out": False,
                     "stdout": r.stdout, "stderr": r.stderr})
    except subprocess.TimeoutExpired as e:
        meta.update({"exit_status": None, "timed_out": True,
                     "stdout": (e.stdout or b"").decode(errors="replace"),
                     "stderr": (e.stderr or b"").decode(errors="replace")})
    meta["wall_seconds"] = round(time.monotonic() - start, 3)
    args.output.with_suffix(args.output.suffix + ".json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({k: meta[k] for k in ("retained_acir_assertion_indices_0_based",
                   "shared_goal_witnesses_through_definitions", "reduced_bytes", "timed_out",
                   "exit_status", "wall_seconds", "stdout", "stderr")}, indent=2))


if __name__ == "__main__": main()
