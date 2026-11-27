#!/usr/bin/env python3
"""Reduce a saved v3 general SMT query to a source-linked assertion prefix.

The last assertion is the goal. Every other retained assertion is byte-for-byte
from the original query. Unused definitions/declarations are omitted by exact
symbol dependency; this changes no retained formula's meaning.
"""
import argparse
import hashlib
import json
import re
import resource
import subprocess
import time
from pathlib import Path

SYM = re.compile(r"\b(?:d|w|rb)\d+\b")
DEF = re.compile(r"^\(define-fun (d\d+) ")
DECL = re.compile(r"^\(declare-const ((?:w|rb)\d+) ")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def render(source, count):
    lines = source.splitlines()
    assertions = [(i, line) for i, line in enumerate(lines) if line.startswith("(assert ")]
    if len(assertions) < 2 or count < 0 or count >= len(assertions):
        raise ValueError("invalid assertion prefix")
    chosen = assertions[:count] + [assertions[-1]]
    definitions = {}
    declarations = {}
    for i, line in enumerate(lines):
        d, c = DEF.match(line), DECL.match(line)
        if d: definitions[d.group(1)] = (i, line)
        if c: declarations[c.group(1)] = (i, line)
    used = set()
    pending = set().union(*(set(SYM.findall(line)) for _, line in chosen))
    while pending:
        name = pending.pop()
        if name in used: continue
        used.add(name)
        if name in definitions:
            pending |= set(SYM.findall(definitions[name][1])) - {name} - used
    indices = {0, 1, 2} | {i for i, _ in chosen}
    indices |= {definitions[name][0] for name in used if name in definitions}
    indices |= {declarations[name][0] for name in used if name in declarations}
    output = "\n".join(lines[i] for i in sorted(indices)) + "\n(check-sat)\n"
    meta = {
        "original_assertions": len(assertions),
        "retained_assertions": len(chosen),
        "retained_original_assertion_indices_0_based": list(range(count)) + [len(assertions) - 1],
        "original_bytes": len(source.encode()),
        "reduced_bytes": len(output.encode()),
        "definitions": sum(1 for i in indices if lines[i].startswith("(define-fun ")),
        "declarations": sum(1 for i in indices if lines[i].startswith("(declare-const ")),
    }
    return output, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--count", type=int, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--cvc5", type=Path, required=True)
    ap.add_argument("--seconds", type=int, required=True)
    ap.add_argument("--memory-gib", type=int, default=4)
    args = ap.parse_args()
    src = args.source.read_text()
    query, meta = render(src, args.count)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(query)
    meta.update({"source": str(args.source), "source_sha256": sha(src.encode()),
                 "query_sha256": sha(query.encode()), "timeout_seconds": args.seconds,
                 "memory_gib": args.memory_gib})
    command = [str(args.cvc5), "--lang=smt2", "--ff-solver=split", str(args.output)]

    def limit():
        resource.setrlimit(resource.RLIMIT_AS, (args.memory_gib * 1024**3,) * 2)

    start = time.monotonic()
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=args.seconds, preexec_fn=limit)
        meta.update({"exit_status": result.returncode, "timed_out": False,
                     "stdout": result.stdout, "stderr": result.stderr})
    except subprocess.TimeoutExpired as ex:
        meta.update({"exit_status": None, "timed_out": True,
                     "stdout": (ex.stdout or b"").decode(errors="replace"),
                     "stderr": (ex.stderr or b"").decode(errors="replace")})
    meta["wall_seconds"] = round(time.monotonic() - start, 3)
    args.output.with_suffix(args.output.suffix + ".json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({k: meta[k] for k in ("retained_assertions", "reduced_bytes", "query_sha256", "exit_status", "timed_out", "wall_seconds", "stdout", "stderr")}, indent=2))


if __name__ == "__main__": main()
