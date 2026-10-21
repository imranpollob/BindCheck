#!/usr/bin/env python3
"""Audit the saved concrete-branch model and replay the frozen walk policy."""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t22_v3_tailspec as T


def walk(words, records):
    emitted, end, remaining = [], False, 0
    for word in words:
        length = records.get(str(word), 0)
        take = not end and (remaining != 0 or length != 0)
        if take: emitted.append(word)
        if not end:
            if remaining != 0: remaining -= 1
            elif length != 0: remaining = length - 1
            else: end = True
    return emitted


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", type=Path, required=True)
    ap.add_argument("--acir", type=Path, required=True)
    ap.add_argument("--abi", type=Path, required=True)
    ap.add_argument("--spec", type=Path, required=True)
    args = ap.parse_args()
    record = json.loads(args.record.read_text())
    assert record["status"] == "sat"
    assert record["solver_record"]["exit_status"] == 0
    assert not record["solver_record"]["timed_out"]
    raw = record["solver_record"]["stdout"]
    assert raw.startswith("sat\n")
    # The frozen v4c display parser also matches the value in the first
    # constant term. Parse only right-hand values from the get-value pairs.
    vals = [int(x) for x in re.findall(r"\([^\s()]+ #f(\d+)m\d+\)", raw)]
    acir = T.Acir(args.acir.read_text())
    spec = json.loads(args.spec.read_text())
    abi = json.loads(args.abi.read_text())
    if "abi" in abi: abi = abi["abi"]
    M, streams = T.build(spec, acir, abi)
    assert len(vals) == len(M) == 8
    assert vals == [2] + [0] * 7
    fixed = {int(k): v for k, v in record["fixed_witness_values"].items()}
    words0 = [fixed[next(iter(T.expr_wits(e)))] for e in streams[0][0]]
    words1 = [fixed[next(iter(T.expr_wits(e)))] for e in streams[1][0]]
    act0 = fixed[next(iter(T.expr_wits(streams[0][1])))]
    act1 = fixed[next(iter(T.expr_wits(streams[1][1])))]
    assert (act0, act1) == (1, 0)
    emitted = walk(words0, spec["derivation"]["records"])
    assert words0 == words1 == [2] + [0] * 7
    assert emitted == [2, 0, 0, 0]
    seeds = set()
    for e in M: seeds |= T.expr_wits(e)
    for words, act in streams:
        for e in words: seeds |= T.expr_wits(e)
        seeds |= T.expr_wits(act)
    selected, wits = T.cone(acir, seeds)
    free = [name for name, outs in acir.unmodeled if set(outs) & wits]
    assert not free
    result = {"status": "PASS", "raw_model_message_values": vals,
              "display_parser_extra_first_value": len(record["messages"]) == 9,
              "emitted_words": emitted, "nonempty_prefix_length": len(emitted),
              "original_cone_opcodes": len(selected), "unmodeled_blackboxes": free,
              "conditional_on_outside_cone_satisfiable": True}
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
