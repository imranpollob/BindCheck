#!/usr/bin/env python3
"""Offline D1P-07 goal/result classification audit; launches no processes."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_MANIFEST = ROOT / "metadata/d1/d1p-04-artifact-manifest.json"
INPUT_MANIFEST = ROOT / "metadata/d1/d1p-06-input-manifest.json"
LEDGER = ROOT / "metadata/d1/d1p-07-track-a-ledger.json"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative(path):
    path = Path(path)
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def classify(goal):
    if goal == "false":
        return "literal_false"
    if goal == "true":
        return "literal_true"
    return "nontrivial"


def audit():
    artifact_manifest = json.loads(ARTIFACT_MANIFEST.read_text())
    input_manifest = json.loads(INPUT_MANIFEST.read_text())
    ledger = json.loads(LEDGER.read_text())
    artifacts = {item["slot"]: item for item in artifact_manifest["artifacts"]}
    partition_inputs = {
        f"{slot['slot']}/{item['id']}": item
        for slot in input_manifest["partitioned"]
        for item in slot["cells"]
    }
    records = [item for item in ledger["records"] if item["arm"] == "partitioned"]
    if len(artifacts) != 150 or len(partition_inputs) != 150 or len(records) != 150:
        raise ValueError((len(artifacts), len(partition_inputs), len(records)))

    counts = Counter()
    by_slot = defaultdict(Counter)
    rows = []
    for record in records:
        query_hash = record["query_sha256"]
        artifact = artifacts.get(record["name"])
        source = partition_inputs.get(record["name"])
        if artifact is None or source is None:
            raise ValueError(f"unmanifested partition query: {record['name']}")
        if artifact["output"]["sha256"] != query_hash or source["sha256"] != query_hash:
            raise ValueError(f"manifest hash disagreement: {record['name']}")
        path = ROOT / record["query_path"]
        if digest(path) != query_hash:
            raise ValueError(f"query hash mismatch: {record['name']}")
        category = classify(artifact["specialized_goal"])
        observed = "timeout" if record["timed_out"] else record["result"].lower()
        counts[(category, observed)] += 1
        by_slot[record["logical_slot"]][(category, observed)] += 1
        rows.append({
            "index": record["index"],
            "name": record["name"],
            "logical_slot": record["logical_slot"],
            "query_sha256": query_hash,
            "goal_class": category,
            "specialized_goal": artifact["specialized_goal"],
            "result": record["result"],
            "status": record["status"],
            "timed_out": record["timed_out"],
        })

    expected = {
        ("literal_false", "unsat"): 58,
        ("literal_true", "timeout"): 42,
        ("nontrivial", "timeout"): 50,
    }
    if dict(counts) != expected:
        raise ValueError(f"classification mismatch: {dict(counts)}")

    goal_records = [item for item in ledger["records"] if item["arm"] == "goal_only"]
    cone_records = [item for item in ledger["records"] if item["arm"] == "cone_only"]
    if len(goal_records) != 6 or any(item["result"] != "SAT" for item in goal_records):
        raise ValueError("goal-only result mismatch")
    if len(cone_records) != 2 or any(
            item["result"] != "UNKNOWN" or not item["timed_out"] for item in cone_records):
        raise ValueError("cone-only result mismatch")

    return {
        "task": "D1P-08",
        "scope": "offline classification of frozen D1P-07 evidence",
        "inputs": {
            relative(ARTIFACT_MANIFEST): digest(ARTIFACT_MANIFEST),
            relative(INPUT_MANIFEST): digest(INPUT_MANIFEST),
            relative(LEDGER): digest(LEDGER),
        },
        "partition_queries_verified": len(rows),
        "classification": {
            "literal_false_unsat": counts[("literal_false", "unsat")],
            "literal_true_timeout": counts[("literal_true", "timeout")],
            "nontrivial_timeout": counts[("nontrivial", "timeout")],
        },
        "by_slot": {
            slot: {f"{category}_{observed}": value
                   for (category, observed), value in sorted(values.items())}
            for slot, values in sorted(by_slot.items())
        },
        "goal_only": [{"name": item["name"], "result": item["result"],
                       "elapsed_seconds": item["elapsed_seconds"]}
                      for item in goal_records],
        "cone_only": [{"name": item["name"], "result": item["result"],
                       "timed_out": item["timed_out"],
                       "elapsed_seconds": item["elapsed_seconds"]}
                      for item in cone_records],
        "interpretation": (
            "The selected producer cone is independently difficult under the frozen encoding "
            "and budget. Literal-true goals leave all producer constraints in place; this audit "
            "does not predict whether adding consumer constraints preserves or removes timeouts."
        ),
        "solver_calls": 0,
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in (
        "partition_queries_verified", "classification", "solver_calls")}, indent=2))


if __name__ == "__main__":
    main()
