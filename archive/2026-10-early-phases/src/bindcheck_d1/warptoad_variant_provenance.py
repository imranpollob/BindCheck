"""Independent beta.22 provenance extraction for the injected M-DOM artifact.

Unlike :mod:`warptoad_poseidon_provenance`, this extractor does not consume
the pinned call rows or assume the pinned private-witness layout.  It flattens
the selected artifact's ABI, checks that layout against its decoded parameter
sets, and classifies every Poseidon2 opcode from that artifact's debug stacks.
"""

from __future__ import annotations

import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import zlib

from .frontends.acir_binary_beta22 import decode
from .model_v2 import FIELD_MODULUS


WIDTH = 4
RATE = 3
IV = RATE << 64
DOMAINS = {
    "siloed_note": 3_361_878_420,
    "unique_note": 226_850_429,
    "merkle_node": 2_982_624_097,
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _debug_info(artifact: dict) -> dict:
    compressed = base64.b64decode(artifact["debug_symbols"], validate=True)
    decoded = zlib.decompress(compressed, -15)
    value = json.loads(decoded)
    infos = value.get("debug_infos")
    if not isinstance(infos, list) or len(infos) != 1:
        raise ValueError("expected one beta.22 debug-info entry")
    return infos[0]


def _line_column(source: str, offset: int) -> tuple[int, int]:
    return source.count("\n", 0, offset) + 1, offset - source.rfind("\n", 0, offset)


def _call_stack(artifact: dict, debug: dict, opcode_index: int) -> list[dict]:
    location_id = debug["acir_locations"].get(str(opcode_index))
    locations = debug["location_tree"]["locations"]
    result = []
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


def _flatten_type(type_spec: dict, prefix: str) -> list[str]:
    kind = type_spec["kind"]
    if kind in {"field", "boolean", "integer", "string"}:
        return [prefix]
    if kind == "array":
        result = []
        for index in range(type_spec["length"]):
            result.extend(_flatten_type(type_spec["type"], f"{prefix}[{index}]"))
        return result
    if kind == "tuple":
        result = []
        for index, field in enumerate(type_spec["fields"]):
            result.extend(_flatten_type(field, f"{prefix}[{index}]"))
        return result
    if kind == "struct":
        result = []
        for field in type_spec["fields"]:
            result.extend(_flatten_type(field["type"], f"{prefix}.{field['name']}"))
        return result
    raise ValueError(f"unsupported ABI kind {kind!r}")


def _abi_witness_layout(artifact: dict, circuit: dict) -> dict:
    public_names = []
    private_names = []
    for parameter in artifact["abi"]["parameters"]:
        target = public_names if parameter["visibility"] == "public" else private_names
        target.extend(_flatten_type(parameter["type"], parameter["name"]))
    public_witnesses = circuit["public_parameters"]
    private_witnesses = circuit["private_parameters"]
    if len(public_names) != len(public_witnesses):
        raise ValueError("flattened public ABI does not match decoded parameter count")
    if len(private_names) != len(private_witnesses):
        raise ValueError("flattened private ABI does not match decoded parameter count")
    if public_witnesses + private_witnesses != list(range(len(public_names) + len(private_names))):
        raise ValueError("beta.22 artifact parameters are not the expected contiguous ABI prefix")
    rows = [
        {"visibility": "public", "name": name, "witness": witness}
        for name, witness in zip(public_names, public_witnesses)
    ] + [
        {"visibility": "private", "name": name, "witness": witness}
        for name, witness in zip(private_names, private_witnesses)
    ]
    return {
        "public": public_names,
        "private": private_names,
        "rows": rows,
        "by_name": {row["name"]: row["witness"] for row in rows},
    }


def _classify(stack: list[dict]) -> tuple[str, str | None]:
    snippets = [frame["snippet"] for frame in stack]
    joined = "\n".join(snippets)
    if "GENERATOR_INDEX__SILOED_NOTE_HASH" in joined and "contract_address" in joined:
        return "siloed_note", None
    if "GENERATOR_INDEX__UNIQUE_NOTE_HASH" in joined and "leaf_nonce" in joined:
        return "unique_note", None
    if "poseidon2::Poseidon2::hash([2982624097, leaves[0], leaves[1]], 3)" in joined:
        frames = [
            frame for frame in stack
            if frame["path"].endswith("/merkle-trees/src/merkle.nr")
            and "(self.hasher)([left, right])" in frame["snippet"]
        ]
        if len(frames) != 1:
            raise ValueError("ambiguous M-DOM Merkle call site")
        return "merkle_node", {84: "node_left", 88: "node_right"}.get(frames[0]["line"])
    raise ValueError("unclassified M-DOM Poseidon2 debug call stack")


def _constant_definition(opcodes: list[dict], before: int, witness: int) -> dict:
    matches = []
    for opcode in opcodes[:before]:
        if opcode["kind"] != "AssertZero":
            continue
        expression = opcode["expression"]
        if expression["mul"]:
            continue
        terms = expression["linear"]
        if terms == [[FIELD_MODULUS - 1, witness]]:
            matches.append({
                "opcode_index": opcode["opcode_index"],
                "witness": witness,
                "value": expression["constant"],
            })
    if len(matches) != 1:
        raise ValueError(f"expected one constant definition for witness {witness}, got {matches}")
    return matches[0]


def extract_mdom_poseidon2(
    artifact_path: str | Path,
    *,
    expected_artifact_sha256: str,
) -> dict:
    """Recover M-DOM's own ABI layout and all 86 Poseidon2 call boundaries."""
    artifact_path = Path(artifact_path)
    artifact_bytes = artifact_path.read_bytes()
    artifact_sha256 = _sha256(artifact_bytes)
    if artifact_sha256 != expected_artifact_sha256:
        raise ValueError(f"unexpected M-DOM artifact hash {artifact_sha256}")
    artifact = json.loads(artifact_bytes)
    decoded = decode(artifact_path)
    circuit = decoded["functions"][0]
    opcodes = circuit["opcodes"]
    debug = _debug_info(artifact)
    layout = _abi_witness_layout(artifact, circuit)
    by_name = layout["by_name"]
    required = {
        "public_contract": by_name["aztec_warptoad_address"],
        "private_contract": by_name["aztec_merkle_data.contract_address"],
        "leaf_nonce": by_name["aztec_merkle_data.leaf_nonce"],
    }
    calls = [opcode for opcode in opcodes if opcode["kind"] == "Poseidon2Permutation"]
    if len(calls) != 86:
        raise ValueError(f"expected 86 M-DOM Poseidon2 permutations, observed {len(calls)}")

    rows = []
    for ordinal, opcode in enumerate(calls):
        stack = _call_stack(artifact, debug, opcode["opcode_index"])
        construction, orientation = _classify(stack)
        expected = "siloed_note" if ordinal == 0 else "unique_note" if ordinal == 1 else "merkle_node"
        if construction != expected:
            raise ValueError(f"unexpected M-DOM call {ordinal} classification {construction}")
        level = None if ordinal < 2 else (ordinal - 2) // 2
        if level is not None:
            expected_orientation = "node_left" if ordinal % 2 == 0 else "node_right"
            if orientation != expected_orientation:
                raise ValueError(f"unexpected orientation at M-DOM call {ordinal}")
        inputs = opcode["inputs"]
        outputs = opcode["outputs"]
        if len(inputs) != WIDTH or len(outputs) != WIDTH or any(set(item) != {"witness"} for item in inputs):
            raise ValueError(f"unexpected M-DOM permutation boundary at opcode {opcode['opcode_index']}")
        input_witnesses = [item["witness"] for item in inputs]
        domain_definition = _constant_definition(opcodes, opcode["opcode_index"], input_witnesses[0])
        iv_definition = _constant_definition(opcodes, opcode["opcode_index"], input_witnesses[3])
        if domain_definition["value"] != DOMAINS[construction] or iv_definition["value"] != IV:
            raise ValueError(f"M-DOM constants differ at call {ordinal}")
        if construction == "siloed_note":
            roles = ["domain:siloed_note", "private:aztec_merkle_data.contract_address", "note_hash", "iv"]
            if input_witnesses[1] != required["private_contract"]:
                raise ValueError("M-DOM silo hash does not absorb its derived private contract witness")
            if input_witnesses[1] == required["public_contract"]:
                raise ValueError("M-DOM silo hash unexpectedly reuses the pinned public contract witness")
        elif construction == "unique_note":
            roles = ["domain:unique_note", "private:aztec_merkle_data.leaf_nonce", "siloed_note_hash", "iv"]
            if input_witnesses[1] != required["leaf_nonce"]:
                raise ValueError("M-DOM unique hash does not absorb its derived nonce witness")
        else:
            sibling_name = f"aztec_merkle_data.hash_path[{level}]"
            sibling_witness = by_name[sibling_name]
            if sibling_witness not in input_witnesses[1:3]:
                raise ValueError(f"M-DOM level {level} lacks its own ABI sibling witness")
            roles = (
                ["domain:merkle_node", "current_node", f"private:{sibling_name}", "iv"]
                if orientation == "node_left" else
                ["domain:merkle_node", f"private:{sibling_name}", "current_node", "iv"]
            )
        rows.append({
            "term_id": f"M-DOM-P2-{ordinal:03d}",
            "ordinal": ordinal,
            "opcode_index": opcode["opcode_index"],
            "construction": construction,
            "merkle_level": level,
            "orientation_candidate": orientation,
            "boundary": {
                "initial_state": [0, 0, 0, IV],
                "absorption": roles,
                "domain_separator": DOMAINS[construction],
                "domain_definition": domain_definition,
                "iv_definition": iv_definition,
                "permutation_count": 1,
                "final_permutation": False,
                "output_selection": "lane_0",
            },
            "l1_application": {
                "function": "P2_WIDTH4_SHARED",
                "ordered_input_witnesses": input_witnesses,
                "ordered_output_witnesses": outputs,
                "equation": "P2_WIDTH4_SHARED(inputs[0],inputs[1],inputs[2],inputs[3]) = (outputs[0],outputs[1],outputs[2],outputs[3])",
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
        raise ValueError(f"unexpected M-DOM construction counts {counts}")
    if orientations != Counter({"node_left": 42, "node_right": 42}):
        raise ValueError(f"unexpected M-DOM orientation counts {orientations}")

    relevant_files = {}
    used_file_ids = {str(frame["file_id"]) for row in rows for frame in row["call_stack"]}
    for file_id in sorted(used_file_ids, key=int):
        entry = artifact["file_map"][file_id]
        relevant_files[file_id] = {
            "path": entry["path"],
            "source_sha256": _sha256(entry["source"].encode()),
            "source_bytes": len(entry["source"].encode()),
        }
    return {
        "schema": "bindcheck.d1p21a.m-dom-poseidon2-provenance/v1",
        "classification": "independent M-DOM artifact decode; no pinned witness IDs or pinned call rows consumed",
        "artifact": {
            "path": str(artifact_path.resolve()),
            "sha256": artifact_sha256,
            "decoded_acir_sha256": decoded["serialization"]["decoded_sha256"],
            "noir_version": artifact["noir_version"],
            "opcode_count": len(opcodes),
        },
        "abi_witness_layout": {
            "public": layout["public"],
            "private": layout["private"],
            "rows": layout["rows"],
            "derived_key_witnesses": required,
        },
        "l1_semantics": {
            "layer": "functional uninterpreted width-four tuple function",
            "same_function_for_all_calls": True,
            "equal_ordered_inputs_imply_equal_ordered_outputs": True,
            "injectivity": False,
            "collision_resistance": False,
            "preimage_resistance": False,
            "bn254_poseidon_treatment": "unchanged exact arithmetic",
        },
        "construction_model": {
            "initialization": "state=[0,0,0,3*2^64] because in_len=rate=3",
            "absorption": "add [domain,left,right] into lanes 0..2",
            "permutation": "one shared width-four tuple-function application in L1",
            "finalization": "no extra final permutation because in_len % rate == 0",
            "output_selection": "hash_internal returns lane 0",
        },
        "count_resolution": {
            "source_level_logical_hashes": 44,
            "top_level_hashes": 2,
            "merkle_levels": 42,
            "compiled_orientation_candidates_per_level": 2,
            "compiled_total_permutations": 86,
            "equation": "2 + (42 * 2) = 86",
        },
        "counts": dict(sorted(counts.items())),
        "orientation_counts": dict(sorted(orientations.items())),
        "relevant_embedded_sources": relevant_files,
        "calls": rows,
    }
