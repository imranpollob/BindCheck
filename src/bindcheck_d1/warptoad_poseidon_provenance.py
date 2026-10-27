"""Recover beta.22 WarpToad Poseidon2 construction provenance.

This module is deliberately narrower than the beta.22 ACIR decoder.  It joins
the decoded black-box calls to Noir's raw-deflate debug-symbol tree and then
checks the exact WarpToad withdraw construction shape.  It does not interpret
arbitrary Poseidon2 programs.
"""

from __future__ import annotations

import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import zlib

from .frontends.acir_binary_beta22 import decode


RATE = 3
WIDTH = 4
IV = RATE << 64
DOMAINS = {
    "siloed_note": 3_361_878_420,
    "unique_note": 226_850_429,
    "merkle_node": 2_982_624_097,
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _line_column(source: str, offset: int) -> tuple[int, int]:
    return source.count("\n", 0, offset) + 1, offset - source.rfind("\n", 0, offset)


def _debug_info(artifact: dict) -> dict:
    compressed = base64.b64decode(artifact["debug_symbols"], validate=True)
    decoded = zlib.decompress(compressed, -15)
    value = json.loads(decoded)
    infos = value.get("debug_infos")
    if not isinstance(infos, list) or len(infos) != 1:
        raise ValueError("expected one beta.22 debug-info entry")
    return infos[0]


def _call_stack(artifact: dict, debug: dict, opcode_index: int) -> list[dict]:
    location_id = debug["acir_locations"].get(str(opcode_index))
    locations = debug["location_tree"]["locations"]
    result: list[dict] = []
    while location_id is not None:
        entry = locations[location_id]
        value = entry["value"]
        file_id = str(value["file"])
        file_entry = artifact["file_map"].get(file_id)
        if file_entry is not None:
            span = value["span"]
            source = file_entry["source"]
            line, column = _line_column(source, span["start"])
            result.append({
                "location_id": location_id,
                "file_id": int(file_id),
                "path": file_entry["path"],
                "span": span,
                "line": line,
                "column": column,
                "snippet": source[span["start"]:span["end"]],
            })
        location_id = entry["parent"]
    return result


def _classify(stack: list[dict]) -> tuple[str, str | None]:
    snippets = [frame["snippet"] for frame in stack]
    joined = "\n".join(snippets)
    if "compute_siloed_note_hash(contract_address, leaf)" in joined:
        return "siloed_note", None
    if "compute_unique_note_hash(merkle_data.leaf_nonce, siloed_note_hash)" in joined:
        return "unique_note", None
    if "poseidon2::Poseidon2::hash([2982624097, leaves[0], leaves[1]], 3)" in joined:
        merkle_frames = [
            frame for frame in stack
            if frame["path"].endswith("/merkle-trees/src/merkle.nr")
            and "(self.hasher)([left, right])" in frame["snippet"]
        ]
        if len(merkle_frames) != 1:
            raise ValueError("ambiguous Merkle orientation call site")
        line = merkle_frames[0]["line"]
        if line == 84:
            return "merkle_node", "node_left"
        if line == 88:
            return "merkle_node", "node_right"
        raise ValueError(f"unexpected Merkle hasher source line {line}")
    raise ValueError("unclassified Poseidon2 debug call stack")


def trace_withdraw_poseidon2(artifact_path: str | Path) -> dict:
    """Return and strictly validate the pinned withdraw call-site inventory."""
    artifact_path = Path(artifact_path)
    artifact_bytes = artifact_path.read_bytes()
    artifact = json.loads(artifact_bytes)
    program = decode(artifact_path)
    circuit = program["functions"][0]
    debug = _debug_info(artifact)
    calls = [opcode for opcode in circuit["opcodes"] if opcode["kind"] == "Poseidon2Permutation"]
    if len(calls) != 86:
        raise ValueError(f"expected 86 Poseidon2 permutations, observed {len(calls)}")

    rows = []
    for ordinal, opcode in enumerate(calls):
        stack = _call_stack(artifact, debug, opcode["opcode_index"])
        construction, orientation = _classify(stack)
        expected_construction = (
            "siloed_note" if ordinal == 0 else
            "unique_note" if ordinal == 1 else
            "merkle_node"
        )
        if construction != expected_construction:
            raise ValueError(f"unexpected construction at ordinal {ordinal}: {construction}")
        level = None if ordinal < 2 else (ordinal - 2) // 2
        if level is not None:
            expected_orientation = "node_left" if ordinal % 2 == 0 else "node_right"
            if orientation != expected_orientation:
                raise ValueError(f"unexpected orientation at ordinal {ordinal}: {orientation}")
        inputs = opcode["inputs"]
        outputs = opcode["outputs"]
        if len(inputs) != WIDTH or len(outputs) != WIDTH:
            raise ValueError(f"unexpected width at opcode {opcode['opcode_index']}")
        if any(set(item) != {"witness"} for item in inputs):
            raise ValueError("pinned construction unexpectedly contains a constant ACIR input")
        input_witnesses = [item["witness"] for item in inputs]
        if construction == "siloed_note":
            absorption_roles = ["domain:siloed_note", "contract_address", "note_hash"]
        elif construction == "unique_note":
            absorption_roles = ["domain:unique_note", "leaf_nonce", "siloed_note_hash"]
        elif orientation == "node_left":
            absorption_roles = ["domain:merkle_node", "current_node", f"sibling[{level}]"]
        else:
            absorption_roles = ["domain:merkle_node", f"sibling[{level}]", "current_node"]
        if ordinal >= 2:
            sibling_witness = 16 + level
            if sibling_witness not in input_witnesses[1:3]:
                raise ValueError(f"level {level} does not absorb ABI sibling witness {sibling_witness}")
        rows.append({
            "ordinal": ordinal,
            "opcode_index": opcode["opcode_index"],
            "construction": construction,
            "merkle_level": level,
            "orientation_candidate": orientation,
            "boundary": {
                "width": WIDTH,
                "rate": RATE,
                "initial_state": [0, 0, 0, IV],
                "absorption": absorption_roles,
                "domain_separator": DOMAINS[construction],
                "permutation_count": 1,
                "final_permutation": False,
                "output_selection": "lane_0",
            },
            "input_witnesses": input_witnesses,
            "output_witnesses": outputs,
            "selected_output_witness": outputs[0],
            "other_output_witnesses": outputs[1:],
            "call_stack": stack,
        })

    counts = Counter(row["construction"] for row in rows)
    orientations = Counter(row["orientation_candidate"] for row in rows if row["orientation_candidate"])
    if counts != Counter({"merkle_node": 84, "siloed_note": 1, "unique_note": 1}):
        raise ValueError(f"unexpected construction counts: {counts}")
    if orientations != Counter({"node_left": 42, "node_right": 42}):
        raise ValueError(f"unexpected orientation counts: {orientations}")

    relevant_files = {}
    for file_id, entry in artifact["file_map"].items():
        if any(frame["file_id"] == int(file_id) for row in rows for frame in row["call_stack"]):
            relevant_files[file_id] = {
                "path": entry["path"],
                "source_sha256": _sha256(entry["source"].encode()),
                "source_bytes": len(entry["source"].encode()),
            }

    return {
        "schema": "bindcheck.d1p15.poseidon2-provenance/v1",
        "artifact": {
            "path": str(artifact_path.resolve()),
            "sha256": _sha256(artifact_bytes),
            "noir_version": artifact["noir_version"],
            "decoded_acir_sha256": program["serialization"]["decoded_sha256"],
        },
        "construction_model": {
            "initialization": "state=[0,0,0,3*2^64] because in_len=rate=3",
            "absorption": "add [domain,left,right] into lanes 0..2",
            "permutation": "one std::hash::poseidon2_permutation_internal width-4 call",
            "finalization": "no extra final permutation because in_len % rate == 0",
            "output_selection": "Poseidon2::hash_internal returns state[0]",
        },
        "count_resolution": {
            "source_level_logical_hashes": 44,
            "top_level_hashes": 2,
            "merkle_levels": 42,
            "source_merkle_hashes_per_selected_path": 42,
            "compiled_merkle_orientation_candidates_per_level": 2,
            "compiled_merkle_permutations": 84,
            "compiled_total_permutations": 86,
            "equation": "2 + (42 * 2) = 86",
            "reason": "beta.22 materializes both calculate_root if-branch hasher calls; constraints select the lane-0 candidate according to the index bit",
        },
        "counts": dict(sorted(counts.items())),
        "orientation_counts": dict(sorted(orientations.items())),
        "relevant_embedded_sources": relevant_files,
        "calls": rows,
    }

