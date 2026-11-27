"""Checked BN254 Poseidon region extraction for beta.22 WarpToad artifacts.

The default is the frozen pinned artifact; callers may provide a separately
frozen variant identity and debug-line layout.  This is a deliberately
artifact-specific P1 checker.  It uses beta.22 debug
locations to propose regions and then checks the proposal against decoded ACIR:

* every equation in a permutation core has one fresh, linearly-defined target;
* the target definitions are a straight-line DAG over the boundary inputs;
* internal definitions do not escape the region except through the recorded
  output link; and
* the compiler-fused hash3 -> hash2 boundary is named and checked explicitly.

It does not replace BN254 arithmetic with an abstraction and it is not a
general Noir region extractor.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from .frontends.acir_binary_beta22 import decode
from .model_v2 import FIELD_MODULUS
from .warptoad_poseidon_provenance import _call_stack, _debug_info


EXPECTED_PINNED_ARTIFACT_SHA256 = (
    "7190813f623967b79ba80a1635536fcc9c8524c1d1cb9f00696832f644b38327"
)


def _witnesses(expression: dict) -> set[int]:
    result = {w for _coefficient, left, right in expression["mul"] for w in (left, right)}
    result.update(w for _coefficient, w in expression["linear"])
    return result


def _target(expression: dict) -> int:
    """Return the unique fresh-target-shaped witness or fail closed."""
    multiplied = {
        witness
        for _coefficient, left, right in expression["mul"]
        for witness in (left, right)
    }
    candidates = [
        witness
        for coefficient, witness in expression["linear"]
        if coefficient == FIELD_MODULUS - 1 and witness not in multiplied
    ]
    if len(candidates) != 1:
        raise ValueError(f"expected one -target term, observed {candidates}")
    return candidates[0]


def _debug_region_key(
    artifact: dict, debug: dict, opcode_index: int,
    direct_lines: tuple[int, int, int] = (43, 44, 45),
    merkle_withdraw_lines: tuple[int, int] = (61, 73),
):
    stack = _call_stack(artifact, debug, opcode_index)
    if not any("/poseidon/bn254/" in frame["path"] for frame in stack):
        return None
    merkle = [
        frame for frame in stack
        if frame["path"].endswith("/merkle-trees/src/merkle.nr")
        and "(self.hasher)([left, right])" in frame["snippet"]
    ]
    if merkle:
        withdraw = [
            frame for frame in stack
            if frame["path"].endswith("/withdraw/src/main.nr")
        ]
        if len(merkle) != 1 or len(withdraw) != 1:
            raise ValueError("ambiguous BN254 Merkle debug stack")
        if merkle[0]["line"] not in (84, 88) or withdraw[0]["line"] not in merkle_withdraw_lines:
            raise ValueError("unexpected BN254 Merkle debug location")
        return ("merkle", merkle[0]["line"], withdraw[0]["line"])
    direct = [
        frame for frame in stack
        if frame["path"].endswith("/nargo_hashing/src/lib.nr")
        and "poseidon::bn254::hash_" in frame["snippet"]
    ]
    if len(direct) != 1 or direct[0]["line"] not in direct_lines:
        raise ValueError("unexpected direct BN254 debug location")
    return ("direct", direct[0]["line"])


def _contiguous_debug_regions(
    artifact: dict, debug: dict, opcodes: list[dict],
    direct_lines: tuple[int, int, int] = (43, 44, 45),
    merkle_withdraw_lines: tuple[int, int] = (61, 73),
) -> list[dict]:
    result: list[dict] = []
    start = None
    active_key = None
    for index in range(len(opcodes) + 1):
        key = _debug_region_key(
            artifact, debug, index, direct_lines, merkle_withdraw_lines,
        ) if index < len(opcodes) else None
        if key != active_key:
            if active_key is not None:
                result.append({"debug_start": start, "debug_end": index - 1, "debug_key": active_key})
            start = index if key is not None else None
            active_key = key
    return result


def _expression_record(expression: dict) -> dict:
    return {
        "mul": expression["mul"],
        "linear": expression["linear"],
        "constant": expression["constant"],
    }


def extract_bn254_regions(
    artifact_path: str | Path,
    *,
    expected_artifact_sha256: str = EXPECTED_PINNED_ARTIFACT_SHA256,
    region_id_prefix: str = "BN254-R",
    variant: str = "pinned",
    direct_lines: tuple[int, int, int] = (43, 44, 45),
    merkle_withdraw_lines: tuple[int, int] = (61, 73),
) -> dict:
    """Extract and check all 77 BN254 Poseidon regions in a beta.22 variant.

    The default remains the frozen pinned-artifact check used by D1P-19.  A
    caller may supply a separately frozen artifact identity for a variant;
    all witness definitions and boundaries are then recovered from that
    artifact's own decoded opcodes rather than copied from pinned evidence.
    """
    artifact_path = Path(artifact_path)
    artifact_bytes = artifact_path.read_bytes()
    artifact_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
    if artifact_sha256 != expected_artifact_sha256:
        raise ValueError(
            f"unexpected {variant} artifact hash {artifact_sha256}; "
            f"expected {expected_artifact_sha256}"
        )
    artifact = json.loads(artifact_bytes)
    decoded = decode(artifact_path)
    opcodes = decoded["functions"][0]["opcodes"]
    debug = _debug_info(artifact)
    proposed = _contiguous_debug_regions(
        artifact, debug, opcodes, direct_lines, merkle_withdraw_lines,
    )
    if len(proposed) != 77:
        raise ValueError(f"expected 77 debug regions, observed {len(proposed)}")

    expected_keys = (
        [("merkle", side, merkle_withdraw_lines[0]) for _level in range(5) for side in (84, 88)]
        + [("direct", direct_lines[0]), ("direct", direct_lines[1]), ("direct", direct_lines[2])]
        + [("merkle", side, merkle_withdraw_lines[1]) for _level in range(32) for side in (84, 88)]
    )
    if [row["debug_key"] for row in proposed] != expected_keys:
        raise ValueError(f"BN254 debug-region order differs from the expected {variant} construction")

    all_references: dict[int, set[int]] = defaultdict(set)
    for opcode in opcodes:
        if opcode["kind"] == "AssertZero":
            for witness in _witnesses(opcode["expression"]):
                all_references[witness].add(opcode["opcode_index"])

    # The compiler emits both Merkle orientations, then four equations that
    # materialize the two predicate/output products.  The candidate lane-0
    # output links are the second and fourth equations in that glue block.
    merkle_pairs: dict[tuple[int, int], tuple[dict, dict]] = {}
    for left, right in zip(proposed, proposed[1:]):
        if left["debug_key"][0] == "merkle" and left["debug_key"][1] == 84:
            if right["debug_key"] != ("merkle", 88, left["debug_key"][2]):
                raise ValueError("left BN254 candidate lacks its right candidate")
            merkle_pairs[(left["debug_start"], right["debug_start"])] = (left, right)

    regions = []
    shared_preludes = []
    direct_by_line = {row["debug_key"][1]: row for row in proposed if row["debug_key"][0] == "direct"}
    for ordinal, row in enumerate(proposed):
        kind = row["debug_key"][0]
        core_start = row["debug_start"]
        debug_count = row["debug_end"] - row["debug_start"] + 1
        if debug_count == 319:
            prelude = [core_start, core_start + 1]
            prelude_targets = [_target(opcodes[index]["expression"]) for index in prelude]
            shared_preludes.append({
                "opcode_indices": prelude,
                "defined_witnesses": prelude_targets,
                "classification": "compiler-shared input materialization; not permutation arithmetic",
            })
            core_start += 2
        core_indices = list(range(core_start, row["debug_end"] + 1))
        if kind == "merkle" and len(core_indices) != 317:
            raise ValueError("BN254 hash2 core does not contain 317 equations")
        if row["debug_key"] == ("direct", direct_lines[0]) and len(core_indices) != 329:
            raise ValueError("BN254 hash1 core does not contain 329 equations")
        if row["debug_key"] == ("direct", direct_lines[1]) and len(core_indices) != 344:
            raise ValueError("BN254 hash3 core does not contain 344 equations")
        if row["debug_key"] == ("direct", direct_lines[2]) and len(core_indices) != 317:
            raise ValueError("BN254 commitment hash2 core does not contain 317 equations")

        output_link = None
        virtual_output = None
        if kind == "merkle":
            if row["debug_key"][1] == 84:
                right = next(
                    item for item in proposed
                    if item["debug_key"] == ("merkle", 88, row["debug_key"][2])
                    and item["debug_start"] == row["debug_end"] + 1
                )
                output_link = right["debug_end"] + 2
            else:
                output_link = row["debug_end"] + 4
        elif row["debug_key"] == ("direct", direct_lines[0]):
            output_link = 4294
        elif row["debug_key"] == ("direct", direct_lines[1]):
            consumer = opcodes[direct_by_line[direct_lines[2]]["debug_start"]]
            if consumer["opcode_index"] != 3977:
                raise ValueError("hash3 output is no longer fused into hash2 opcode 3977")
            virtual_output = {
                "kind": "polynomial boundary expression",
                "consumer_opcode_index": 3977,
                "expression_without_consumer_target_or_round_constant": {
                    "mul": consumer["expression"]["mul"],
                    "linear": [],
                    "constant": 0,
                },
                "normalization": (
                    "introduce z_hash3 equal to this polynomial, then replace the polynomial "
                    "occurrence in opcode 3977 by z_hash3; no field equation is dropped"
                ),
            }
        else:
            output_link = 4296

        region_indices = list(core_indices)
        if output_link is not None:
            if opcodes[output_link]["kind"] != "AssertZero":
                raise ValueError("BN254 output link is not AssertZero")
            region_indices.append(output_link)

        definitions = []
        known_inputs = set()
        for index in core_indices:
            expression = opcodes[index]["expression"]
            target = _target(expression)
            definitions.append(target)
        defined = set(definitions)
        for index in core_indices:
            known_inputs.update(_witnesses(opcodes[index]["expression"]) - defined)
        known = set(known_inputs)
        for index, target in zip(core_indices, definitions):
            dependencies = _witnesses(opcodes[index]["expression"]) - {target}
            if not dependencies <= known:
                raise ValueError(f"non-DAG BN254 definition at opcode {index}")
            known.add(target)

        if output_link is not None:
            link_expression = opcodes[output_link]["expression"]
            output_witness = _target(link_expression)
            dependencies = _witnesses(link_expression) - {output_witness}
            if not dependencies <= known:
                raise ValueError(f"BN254 output link {output_link} has an unknown dependency")
            boundary_outputs = {output_witness}
            output = {
                "kind": "materialized witness",
                "witness": output_witness,
                "link_opcode_index": output_link,
                "link_expression": _expression_record(link_expression),
            }
        else:
            expression = virtual_output["expression_without_consumer_target_or_round_constant"]
            boundary_operands = _witnesses(expression)
            if not boundary_operands <= defined:
                raise ValueError("hash3 virtual output depends outside its permutation core")
            boundary_outputs = boundary_operands
            output = virtual_output

        internal = defined - boundary_outputs
        allowed = set(region_indices)
        if virtual_output is not None:
            allowed.add(virtual_output["consumer_opcode_index"])
        escapes = {
            witness: sorted(all_references[witness] - allowed)
            for witness in sorted(internal)
            if all_references[witness] - allowed
        }
        if escapes:
            raise ValueError(f"BN254 internal witnesses escape region: {escapes}")

        construction = (
            "giga_merkle_hash2" if kind == "merkle" and row["debug_key"][2] == merkle_withdraw_lines[0] else
            "evm_merkle_hash2" if kind == "merkle" else
            "nullifier_hash1" if row["debug_key"] == ("direct", direct_lines[0]) else
            "precommitment_hash3" if row["debug_key"] == ("direct", direct_lines[1]) else
            "commitment_hash2"
        )
        orientation = None if kind != "merkle" else ("left" if row["debug_key"][1] == 84 else "right")
        level = None
        if kind == "merkle":
            earlier = [item for item in regions if item["construction"] == construction]
            level = len(earlier) // 2
        regions.append({
            "region_id": f"{region_id_prefix}{ordinal:02d}",
            "construction": construction,
            "merkle_level": level,
            "orientation_candidate": orientation,
            "debug_opcode_range": [row["debug_start"], row["debug_end"]],
            "core_opcode_range": [core_indices[0], core_indices[-1]],
            "core_constraint_count": len(core_indices),
            "region_opcode_indices": region_indices,
            "boundary_input_witnesses": sorted(known_inputs),
            "output": output,
            "definition_count": len(definitions),
            "functionality_check": "PASS: one fresh linear target per equation and topological dependency order",
            "locality_check": "PASS: internal definitions have no references outside the checked region/output normalization",
        })

    debug_counts = Counter(row["debug_end"] - row["debug_start"] + 1 for row in proposed)
    core_counts = Counter(row["core_constraint_count"] for row in regions)
    construction_counts = Counter(row["construction"] for row in regions)
    if debug_counts != Counter({317: 40, 319: 35, 329: 1, 344: 1}):
        raise ValueError(f"unexpected debug-region size distribution {debug_counts}")
    if core_counts != Counter({317: 75, 329: 1, 344: 1}):
        raise ValueError(f"unexpected BN254 core size distribution {core_counts}")
    if len(shared_preludes) != 35:
        raise ValueError("expected 35 two-equation shared input preludes")

    return {
        "schema": "bindcheck.d1p19.bn254-region-extraction/v1",
        "classification": "checked artifact-specific extraction; no BN254 abstraction applied",
        **({} if variant == "pinned" else {"variant": variant}),
        "artifact": {
            "path": str(artifact_path.resolve()),
            "sha256": artifact_sha256,
            "decoded_acir_sha256": decoded["serialization"]["decoded_sha256"],
            "noir_version": artifact["noir_version"],
        },
        "counts": {
            "regions": len(regions),
            "construction_counts": dict(sorted(construction_counts.items())),
            "debug_region_size_distribution": {str(k): v for k, v in sorted(debug_counts.items())},
            "core_size_distribution": {str(k): v for k, v in sorted(core_counts.items())},
            "core_constraints": sum(row["core_constraint_count"] for row in regions),
            "shared_input_prelude_constraints": sum(len(row["opcode_indices"]) for row in shared_preludes),
            "materialized_output_links": sum(row["output"]["kind"] == "materialized witness" for row in regions),
            "fused_virtual_output_boundaries": sum(row["output"]["kind"] != "materialized witness" for row in regions),
        },
        "count_resolution": {
            "source_level_bn254_calls_on_selected_paths": 40,
            "compiled_regions": 77,
            "equation": "5*2 giga candidates + hash1 + hash3 + commitment hash2 + 32*2 EVM candidates = 77",
            "reason": "both Merkle orientation candidates are materialized at every level",
        },
        "checks": {
            "debug_region_locality": "PASS",
            "straight_line_functionality": "PASS",
            "exact_bn254_arithmetic_retained": True,
            "general_extractor_claim": False,
        },
        "shared_input_preludes": shared_preludes,
        "regions": regions,
    }
