#!/usr/bin/env python3
"""Prepare and audit the frozen D1P-06 Track A inputs.

This program only reads and serializes SMT text.  It has no subprocess or
solver interface.  Combined and specialized inputs are copied byte-for-byte;
goal-only and cone-only diagnostics are derived from the frozen parent layout.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
D1P04_SCRIPT = ROOT / "scripts/d1p_04_specialize.py"
D1P04_MANIFEST = ROOT / "metadata/d1/d1p-04-artifact-manifest.json"
D1P05_LEDGER = ROOT / "metadata/d1/d1p-05-equivalence-ledger.json"
EXPECTED_D1P04_MANIFEST = "1a713bc5f464eda5e33218cd7985882405f06e5cccb8a3a79b7d5f1cb1e7e2ff"
EXPECTED_D1P05_LEDGER = "fb29385f5dee51f69fd2a197ff93bab2ac897c49927beda2d083cd31e0272c5e"
FAMILIES = ("check_added", "running_flag")
QUERIES = ("nonvacuous", "prefix", "tail")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256(path):
    return sha256_bytes(Path(path).read_bytes())


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def load_specializer():
    spec = importlib.util.spec_from_file_location("d1p_04_specialize", D1P04_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_fresh(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"fresh output required: {path}")
    path.write_bytes(data)


def goal_only_text(parent):
    """Retain field/common walk definitions and the original goal, not C."""
    return (
        parent["header"]
        + parent["declarations"]
        + parent["walk"]
        + parent["goal_line"]
        + "(check-sat)\n"
        + parent["get_value"]
    ).encode("ascii")


def cone_only_text(parent):
    """Retain the complete selected-cone producer prefix, but no walk/goal."""
    return parent["producer_prefix"] + b"(check-sat)\n"


def assertion_count(data):
    return sum(line.startswith(b"(assert ") for line in data.splitlines())


def build(output_root, manifest_path):
    output_root = Path(output_root).resolve()
    manifest_path = Path(manifest_path).resolve()
    if output_root.exists():
        raise FileExistsError(f"fresh output namespace required: {output_root}")
    if manifest_path.exists():
        raise FileExistsError(f"fresh manifest required: {manifest_path}")
    if sha256(D1P04_MANIFEST) != EXPECTED_D1P04_MANIFEST:
        raise RuntimeError("D1P-04 artifact manifest identity mismatch")
    if sha256(D1P05_LEDGER) != EXPECTED_D1P05_LEDGER:
        raise RuntimeError("D1P-05 equivalence ledger identity mismatch")

    d1p04 = json.loads(D1P04_MANIFEST.read_text())
    d1p05 = json.loads(D1P05_LEDGER.read_text())
    if not d1p05.get("partition_eligible_for_primary_use"):
        raise RuntimeError("D1P-05 did not establish complete-partition eligibility")
    if d1p05.get("counts", {}).get("cells_unsat") != 150:
        raise RuntimeError("D1P-05 does not record 150 UNSAT equivalence cells")
    if d1p05.get("counts", {}).get("producer_prefix_audits_passed") != 150:
        raise RuntimeError("D1P-05 does not record 150 producer-prefix audits")

    specializer = load_specializer()
    if sha256(D1P04_SCRIPT) != d1p04["generator"]["sha256"]:
        raise RuntimeError("frozen D1P-04 specializer identity mismatch")
    parents = {
        (family, query): specializer.parse_parent(family, query)
        for family in FAMILIES for query in QUERIES
    }

    controls = []
    for item in d1p04["controls"]:
        source = ROOT / item["path"]
        data = source.read_bytes()
        if sha256_bytes(data) != item["sha256"]:
            raise RuntimeError(f"D1P-04 control hash mismatch: {item['name']}")
        destination = output_root / "controls" / source.name
        write_fresh(destination, data)
        controls.append({
            "name": item["name"], "expected": item["expected"],
            "path": relative(destination), "sha256": item["sha256"],
            "bytes": len(data), "source_path": item["path"],
            "source_bytes_identical": destination.read_bytes() == data,
        })

    combined = []
    goal_only = []
    for family in FAMILIES:
        for query in QUERIES:
            parent = parents[(family, query)]
            slot = f"{family}/{query}"
            combined_destination = output_root / "combined" / family / f"{query}.smt2"
            write_fresh(combined_destination, parent["raw"])
            combined.append({
                "slot": slot, "family": family, "query": query,
                "path": relative(combined_destination), "sha256": parent["hash"],
                "bytes": len(parent["raw"]),
                "source_path": relative(parent["path"]),
                "source_bytes_identical": combined_destination.read_bytes() == parent["raw"],
                "producer_prefix_sha256": parent["producer_prefix_hash"],
                "producer_assertions": parent["producer_assertions"],
                "anticipated_result_not_observation": (
                    "sat" if query == "nonvacuous" else "unsat"
                ),
            })

            data = goal_only_text(parent)
            destination = output_root / "goal-only" / family / f"{query}.smt2"
            write_fresh(destination, data)
            goal_only.append({
                "slot": slot, "family": family, "query": query,
                "path": relative(destination), "sha256": sha256_bytes(data),
                "bytes": len(data), "anticipated_result_not_observation": "sat",
                "derivation_audit": {
                    "parent_path": relative(parent["path"]),
                    "parent_sha256": parent["hash"],
                    "field_header_sha256": sha256_bytes(parent["header"].encode("ascii")),
                    "retained_declarations_sha256": sha256_bytes(
                        parent["declarations"].encode("ascii")
                    ),
                    "retained_declaration_count": len(
                        parent["declarations"].splitlines()
                    ),
                    "walk_sha256": parent["walk_hash"],
                    "walk_bytes_identical": parent["walk"].encode("ascii") in data,
                    "original_goal_sha256": parent["goal_hash"],
                    "original_goal_line_sha256": sha256_bytes(
                        parent["goal_line"].encode("ascii")
                    ),
                    "original_goal_line_bytes_identical": (
                        parent["goal_line"].encode("ascii") in data
                    ),
                    "producer_constraints_included": False,
                    "producer_assertions_removed": parent["producer_assertions"],
                    "output_assertions": assertion_count(data),
                    "new_auxiliary_symbols": [],
                },
            })

    cone_only = []
    for family in FAMILIES:
        family_parents = [parents[(family, query)] for query in QUERIES]
        prefix_hashes = {parent["producer_prefix_hash"] for parent in family_parents}
        if len(prefix_hashes) != 1:
            raise RuntimeError(f"producer prefix differs within {family}")
        parent = family_parents[0]
        data = cone_only_text(parent)
        destination = output_root / "cone-only" / f"{family}.smt2"
        write_fresh(destination, data)
        cone_only.append({
            "slot": family, "family": family, "path": relative(destination),
            "sha256": sha256_bytes(data), "bytes": len(data),
            "anticipated_result_not_observation": "sat",
            "derivation_audit": {
                "representative_parent_path": relative(parent["path"]),
                "representative_parent_sha256": parent["hash"],
                "all_family_parent_prefix_sha256": sorted(prefix_hashes),
                "parent_prefix_byte_range": [0, parent["producer_prefix_bytes"]],
                "output_prefix_byte_range": [0, parent["producer_prefix_bytes"]],
                "producer_prefix_sha256": parent["producer_prefix_hash"],
                "producer_prefix_bytes_identical": (
                    data[:parent["producer_prefix_bytes"]] == parent["producer_prefix"]
                ),
                "producer_assertions": parent["producer_assertions"],
                "walk_included": False, "goal_included": False,
                "only_appended_bytes_ascii": "(check-sat)\\n",
            },
        })

    partitioned_by_slot = {
        f"{family}/{query}": {
            "slot": f"{family}/{query}", "family": family, "query": query,
            "cells": [],
        }
        for family in FAMILIES for query in QUERIES
    }
    for artifact in d1p04["artifacts"]:
        source = ROOT / artifact["output"]["path"]
        data = source.read_bytes()
        if sha256_bytes(data) != artifact["output"]["sha256"]:
            raise RuntimeError(f"D1P-04 specialized hash mismatch: {artifact['slot']}")
        audit = artifact["producer_prefix_audit"]
        prefix_bytes = audit["bytes"]
        if not audit["ordered_bytes_identical"]:
            raise RuntimeError(f"failed recorded prefix audit: {artifact['slot']}")
        if sha256_bytes(data[:prefix_bytes]) != audit["parent_sha256"]:
            raise RuntimeError(f"independent prefix audit mismatch: {artifact['slot']}")
        destination = output_root / "partitioned" / artifact["family"] / artifact["query"] / source.name
        write_fresh(destination, data)
        partitioned_by_slot[f"{artifact['family']}/{artifact['query']}"]["cells"].append({
            "index": artifact["cell"]["index"], "id": artifact["cell"]["id"],
            "predicate": artifact["cell_predicate"], "path": relative(destination),
            "sha256": artifact["output"]["sha256"], "bytes": len(data),
            "source_path": artifact["output"]["path"],
            "source_bytes_identical": destination.read_bytes() == data,
            "producer_prefix_sha256": audit["parent_sha256"],
            "producer_prefix_bytes": prefix_bytes,
            "producer_prefix_bytes_identical": True,
        })
    partitioned = []
    for family in FAMILIES:
        for query in QUERIES:
            group = partitioned_by_slot[f"{family}/{query}"]
            group["cells"].sort(key=lambda item: item["index"])
            if [item["index"] for item in group["cells"]] != list(range(25)):
                raise RuntimeError(f"incomplete cell ordering: {group['slot']}")
            partitioned.append(group)

    manifest = {
        "task": "D1P-06",
        "status": "INPUTS_PREPARED_NOT_EXECUTED",
        "research_verdict": "UNKNOWN",
        "generator": {"path": relative(__file__), "sha256": sha256(__file__)},
        "dependencies": {
            "d1p04_specializer": {"path": relative(D1P04_SCRIPT), "sha256": sha256(D1P04_SCRIPT)},
            "d1p04_artifact_manifest": {"path": relative(D1P04_MANIFEST), "sha256": sha256(D1P04_MANIFEST)},
            "d1p05_equivalence_ledger": {"path": relative(D1P05_LEDGER), "sha256": sha256(D1P05_LEDGER)},
        },
        "output_root": relative(output_root),
        "counts": {
            "controls": len(controls), "goal_only": len(goal_only),
            "cone_only": len(cone_only), "combined": len(combined),
            "partitioned_slots": len(partitioned),
            "partitioned_cells": sum(len(item["cells"]) for item in partitioned),
            "primary_calls_max": len(goal_only) + len(cone_only) + len(combined)
            + sum(len(item["cells"]) for item in partitioned),
            "calls_with_controls_max": len(controls) + len(goal_only) + len(cone_only)
            + len(combined) + sum(len(item["cells"]) for item in partitioned),
        },
        "ordering": {
            "arms": ["controls", "goal_only", "cone_only", "combined", "partitioned"],
            "families": list(FAMILIES), "queries": list(QUERIES),
            "cells": [item["id"] for item in partitioned[0]["cells"]],
        },
        "controls": controls, "goal_only": goal_only,
        "cone_only": cone_only, "combined": combined,
        "partitioned": partitioned,
        "interpretation": {
            "C": "selected producer cone, not the full producer relation",
            "goal_only": "original v5 specification walk and goal without C",
            "cone_only": "C without the v5 specification walk or goal",
            "combined": "exact historical C and G query bytes",
            "partitioned": "D1P-05-validated cell-specialized combined queries",
            "limitations": [
                "diagnostics do not discharge combined obligations",
                "SAT is not validated full-ACIR, proof, replay, or consumer evidence",
                "this manifest records no solver observation",
            ],
        },
    }
    if manifest["counts"] != {
        "controls": 2, "goal_only": 6, "cone_only": 2, "combined": 6,
        "partitioned_slots": 6, "partitioned_cells": 150,
        "primary_calls_max": 164, "calls_with_controls_max": 166,
    }:
        raise RuntimeError(f"unexpected Track A counts: {manifest['counts']}")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": manifest["status"], **manifest["counts"],
                      "manifest": relative(manifest_path)}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    build(args.output_root, args.manifest)


if __name__ == "__main__":
    main()
