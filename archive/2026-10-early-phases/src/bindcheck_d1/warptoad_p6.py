"""Mechanical D1P-19 P6 construction-identity and term-universe audit.

The audit is intentionally tied to the pinned WarpToad beta.22 artifact and
the locked dependency tree.  It does not run a solver and it does not create
the O1/O2 campaign queries.  A future freeze must still prove that its query
term set equals the inventory emitted here.
"""

from __future__ import annotations

import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from .model_v2 import FIELD_MODULUS


PINNED_ARTIFACT_SHA256 = "7190813f623967b79ba80a1635536fcc9c8524c1d1cb9f00696832f644b38327"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file(path: Path, root: Path) -> dict:
    return {
        "path": str(path.relative_to(root)),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }


def _hex_values(text: str) -> list[int]:
    return [int(value, 16) for value in re.findall(r"0x[0-9a-fA-F]+", text)]


def _noir_config_arguments(text: str, width: int) -> list[str]:
    start = text.index(f"pub fn x5_{width}_config")
    start = text.index("{", start)
    cursor = text.index("config(", start) + len("config(")
    depth = 0
    arguments: list[str] = []
    argument_start = cursor
    for index, character in enumerate(text[cursor:], cursor):
        if character in "[(":
            depth += 1
        elif character == ")":
            if depth == 0:
                arguments.append(text[argument_start:index].strip())
                break
            depth -= 1
        elif character == "]":
            depth -= 1
        elif character == "," and depth == 0:
            arguments.append(text[argument_start:index].strip())
            argument_start = index + 1
    if len(arguments) != 8:
        raise ValueError(f"x5_{width}: expected eight config arguments, got {len(arguments)}")
    return arguments


def _decode_poseidon_lite_constants(path: Path) -> tuple[list[int], list[int]]:
    text = path.read_text()
    c_text = text.split("C: [", 1)[1].split("],\n  M:", 1)[0]
    m_text = text.split("M: [", 1)[1].rsplit("]\n};", 1)[0]

    def decode(section: str) -> list[int]:
        return [
            int.from_bytes(base64.b64decode(value), "big")
            for value in re.findall(r"'([^']+)'", section)
        ]

    return decode(c_text), decode(m_text)


def audit_p6(root: str | Path) -> dict:
    root = Path(root).resolve()
    artifact = root / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json"
    p2_provenance_path = root / "results/raw/D1P-15/poseidon2-provenance.json"
    regions_path = root / "results/raw/D1P-19/bn254-region-extraction.json"
    states_path = root / "results/raw/D1P-19/canonical-states.json"
    solidity_domain_path = root / "results/raw/D1P-19/p6-solidity-domain.json"

    node_modules = root / "results/raw/D1P-19/workspace/source/backend/node_modules"
    p2_js_constants = node_modules / "@zkpassport/poseidon2/dist/esm/bn254/constants.js"
    p2_js_permutation = node_modules / "@zkpassport/poseidon2/dist/esm/core/poseidon2.js"
    poseidon_lite = node_modules / "poseidon-lite"
    poseidon_solidity = node_modules / "poseidon-solidity/PoseidonT3.sol"

    noir_root = root / "results/raw/D1P-19/upstream/poseidon-v0.3.0"
    noir_constants = noir_root / "src/poseidon/bn254/consts.nr"
    noir_permutation = noir_root / "src/poseidon/mod.nr"
    noir_framing = noir_root / "src/poseidon/bn254.nr"
    bb_root = root / "results/raw/D1P-19/upstream/aztec-packages-v5.0.0"
    bb_params = bb_root / "barretenberg/cpp/src/barretenberg/crypto/poseidon2/poseidon2_params.hpp"
    bb_permutation = bb_root / "barretenberg/cpp/src/barretenberg/crypto/poseidon2/poseidon2_permutation.hpp"
    circom_root = root / "results/raw/D1P-19/upstream/circomlibjs-reference"
    circom_raw = circom_root / "src/poseidon_constants.json"
    circom_opt = circom_root / "src/poseidon_constants_opt.json"
    circom_transform = circom_root / "tools/poseidon_optimize_constants.js"
    solidity_source_root = root / "results/raw/D1P-19/upstream/poseidon-solidity-source"
    solidity_generator = solidity_source_root / "src/buildPoseidonSimple.mjs"
    solidity_generator_constants = solidity_source_root / "src/poseidon_constants.json"
    solidity_generated = solidity_source_root / "contracts/PoseidonT3.sol"

    if _sha256(artifact) != PINNED_ARTIFACT_SHA256:
        raise ValueError("pinned artifact identity mismatch")

    p2_provenance = json.loads(p2_provenance_path.read_text())
    p2_calls = p2_provenance["calls"]
    p2_opcode_ids = [call["opcode_index"] for call in p2_calls]
    if len(p2_calls) != 86 or len(set(p2_opcode_ids)) != 86:
        raise ValueError("Poseidon2 term inventory is not 86 unique opcodes")
    expected_boundary = {
        "width": 4,
        "rate": 3,
        "initial_state": [0, 0, 0, 3 * 2**64],
        "permutation_count": 1,
        "final_permutation": False,
        "output_selection": "lane_0",
    }
    boundary_pass = all(
        all(call["boundary"][key] == value for key, value in expected_boundary.items())
        and call["boundary"]["domain_separator"]
        in {3361878420, 226850429, 2982624097}
        for call in p2_calls
    )

    js_p2_numbers = [
        int(value, 16)
        for value in re.findall(r'BigInt\("(0x[0-9a-fA-F]+)"\)', p2_js_constants.read_text())
    ]
    cpp_p2_numbers = [
        int(value, 16)
        for value in re.findall(
            r'FF\(std::string\("(0x[0-9a-fA-F]+)"\)\)', bb_params.read_text()
        )
    ]
    p2_parameter_match = len(js_p2_numbers) == 276 and js_p2_numbers == cpp_p2_numbers[:276]
    p2_cpp_tail = len(cpp_p2_numbers) - len(js_p2_numbers)
    p2_algorithm_markers = all(
        marker in p2_js_permutation.read_text()
        for marker in ("matmulExternal", "matmulInternal", "sboxP", "rounds_f_beginning")
    )
    # C++ uses the longer function names, so check its exact operations too.
    p2_cpp_algorithm = all(
        marker in bb_permutation.read_text()
        for marker in (
            "matrix_multiplication_external",
            "matrix_multiplication_internal",
            "apply_single_sbox",
            "rounds_f / 2",
        )
    )
    p2_shape = all(
        marker in bb_params.read_text()
        for marker in (
            "static constexpr size_t t = 4;",
            "static constexpr size_t d = 5;",
            "static constexpr size_t rounds_f = 8;",
            "static constexpr size_t rounds_p = 56;",
        )
    )

    raw = json.loads(circom_raw.read_text())
    optimized = json.loads(circom_opt.read_text())
    noir_text = noir_constants.read_text()
    bn_widths = []
    for width in (2, 3, 4):
        arguments = _noir_config_arguments(noir_text, width)
        noir_tables = [_hex_values(argument) for argument in arguments[4:]]
        opt_tables: list[list[int]] = []
        for name in ("C", "M", "P", "S"):
            table = optimized[name][width - 2]
            if name in ("M", "P"):
                table = [entry for row in table for entry in row]
            opt_tables.append([int(value, 16) for value in table])
        lite_c, lite_m = _decode_poseidon_lite_constants(
            poseidon_lite / f"constants/{width - 1}.js"
        )
        raw_c = [int(value, 16) for value in raw["C"][width - 2]]
        raw_m = [
            int(value, 16)
            for row in raw["M"][width - 2]
            for value in row
        ]
        bn_widths.append({
            "width": width,
            "input_arity": width - 1,
            "full_rounds": int(arguments[1]),
            "partial_rounds": int(arguments[2]),
            "sbox_exponent": 5,
            "noir_optimized_table_lengths": [len(table) for table in noir_tables],
            "noir_equals_circomlibjs_optimized_tables": noir_tables == opt_tables,
            "locked_reference_equals_circomlibjs_raw_constants": lite_c == raw_c,
            "locked_reference_equals_circomlibjs_raw_mds": lite_m == raw_m,
            "state_initialization": f"[0, input_0..input_{width - 2}]",
            "output_lane": 0,
        })

    bn_algorithm_markers = all(
        marker in noir_permutation.read_text()
        for marker in ("pow_32(alpha)", "apply_matrix(presparse_mds", "sparse_mds")
    )
    bn_framing_markers = all(
        marker in noir_framing.read_text()
        for marker in (
            "let mut state = [0; STATE_SIZE]",
            "state[i + 1] = input[i]",
            "perm_fn(state)[0]",
            "hash_internal(input, perm::x5_2)",
            "hash_internal(input, perm::x5_3)",
            "hash_internal(input, perm::x5_4)",
        )
    )
    lite_algorithm = (poseidon_lite / "poseidon/index.js").read_text()
    lite_markers = all(
        marker in lite_algorithm
        for marker in ("const N_ROUNDS_F = 8", "const pow5", "let state = [0n, ...inputs]", "return state[0]")
    )

    # The installed Solidity source is byte-identical to the independently
    # retrieved generator output, whose raw constants are byte-identical to
    # circomlibjs.  The generator itself supplies the exact round schedule,
    # x^5 S-box, matrix orientation, initialization and lane-0 selection.
    solidity_generator_identity = (
        poseidon_solidity.read_bytes() == solidity_generated.read_bytes()
        and solidity_generator_constants.read_bytes() == circom_raw.read_bytes()
        and all(
            marker in solidity_generator.read_text()
            for marker in (
                "const ROUNDS_F = 8",
                "const _ROUNDS_P",
                "BigInt(C[0]) ** BigInt(5)",
                "mload(${mem})",
                "mstore(0x0",
            )
        )
    )

    regions = json.loads(regions_path.read_text())
    bn_region_ids = [region["region_id"] for region in regions["regions"]]
    if len(bn_region_ids) != 77 or len(set(bn_region_ids)) != 77:
        raise ValueError("BN254 term inventory is not 77 unique regions")
    states = json.loads(states_path.read_text())
    ground = states["groundHashInstances"]
    ground_ids = [term["id"] for term in ground]
    if len(ground_ids) != len(set(ground_ids)):
        raise ValueError("duplicate admitted-state ground term id")
    ground_counts = Counter(term["function"] for term in ground)
    ground_canonical = all(
        all(0 <= int(value) < FIELD_MODULUS for value in term["inputs"])
        and 0 <= int(term["output"]) < FIELD_MODULUS
        for term in ground
    )
    s_src_ground_ids = [term["id"] for term in ground if term["id"].startswith("s-src-")]
    s_src_has_burns_and_nodes = (
        any("commitment" in term_id for term_id in s_src_ground_ids)
        and any("node" in term_id for term_id in s_src_ground_ids)
    )

    solidity_domain = json.loads(solidity_domain_path.read_text())
    domain_pass = (
        states["checks"]["allValuesCanonical"]
        and ground_canonical
        and solidity_domain["allPassed"]
        and all(
            case["behavior"] == "reduced modulo P"
            for case in solidity_domain["noncanonicalCases"]
        )
    )
    public_domain = json.loads(
        (root / "results/raw/D1P-12R/canonicality-summary.json").read_text()
    )
    public_domain_pass = (
        public_domain["honest_proof_accepted"]
        and public_domain["all_rejected_by_revert"]
        and len(public_domain["cases"]) == 22
    )

    identity_pass = (
        boundary_pass
        and p2_parameter_match
        and p2_algorithm_markers
        and p2_cpp_algorithm
        and p2_shape
        and all(
            row["noir_equals_circomlibjs_optimized_tables"]
            and row["locked_reference_equals_circomlibjs_raw_constants"]
            and row["locked_reference_equals_circomlibjs_raw_mds"]
            for row in bn_widths
        )
        and bn_algorithm_markers
        and bn_framing_markers
        and lite_markers
        and solidity_generator_identity
    )

    return {
        "schema": "bindcheck.d1p19.p6-audit/v1",
        "classification": "artifact-specific mechanical prerequisite audit; no solver query",
        "termCoverage": {
            "programPoseidon2OpcodeIds": p2_opcode_ids,
            "programPoseidon2Count": len(p2_opcode_ids),
            "programBn254RegionIds": bn_region_ids,
            "programBn254RegionCount": len(bn_region_ids),
            "admittedStateGroundTermIds": ground_ids,
            "admittedStateGroundTermCount": len(ground_ids),
            "admittedStateGroundFunctionCounts": dict(sorted(ground_counts.items())),
            "sSrcGroundTermIds": s_src_ground_ids,
            "sSrcIncludesBurnLeavesAndLazyImtNodes": s_src_has_burns_and_nodes,
            "inventoryStatus": "PASS",
            "futureQueryEqualityGate": (
                "MANDATORY AT FREEZE: recompute T independently and require exact set equality "
                "with this inventory; D1P-19 intentionally emits no campaign query"
            ),
        },
        "functionIdentity": {
            "poseidon2": {
                "width": 4,
                "fullRounds": 8,
                "partialRounds": 56,
                "sboxExponent": 5,
                "lockedJsNumericParameterCount": len(js_p2_numbers),
                "barretenbergNumericParameterCount": len(cpp_p2_numbers),
                "barretenbergNonparameterTailValues": p2_cpp_tail,
                "allLockedParametersEqualBarretenbergV5Tag": p2_parameter_match,
                "permutationAlgorithmStructureEqual": p2_algorithm_markers and p2_cpp_algorithm,
                "all86BoundariesAreH3": boundary_pass,
                "domainSeparators": [3361878420, 226850429, 2982624097],
                "initialization": [0, 0, 0, 3 * 2**64],
                "outputLane": 0,
            },
            "bn254Poseidon": {
                "widths": bn_widths,
                "noirOptimizedTablesExactlyEqualCircomlibjsTransformOutput": all(
                    row["noir_equals_circomlibjs_optimized_tables"] for row in bn_widths
                ),
                "lockedReferenceRawTablesExactlyEqualCircomlibjs": all(
                    row["locked_reference_equals_circomlibjs_raw_constants"]
                    and row["locked_reference_equals_circomlibjs_raw_mds"]
                    for row in bn_widths
                ),
                "noirAndReferenceAlgorithmFramingChecked": (
                    bn_algorithm_markers and bn_framing_markers and lite_markers
                ),
                "soliditySourceRegeneratedFromSameRawTables": solidity_generator_identity,
                "solidityTermCompleteGroundChecks": {
                    "count": len(solidity_domain["groundChecks"]),
                    "allPassed": all(case["pass"] for case in solidity_domain["groundChecks"]),
                    "role": "supporting application checks; generator/table comparison establishes identity",
                },
            },
            "status": "PASS" if identity_pass else "FAIL",
        },
        "canonicalDomains": {
            "circuitInputsAreFieldElements": True,
            "publicWordsCanonicalAtVerifierBoundary": public_domain_pass,
            "allGroundInputsAndOutputsBelowFieldModulus": ground_canonical,
            "solidityPoseidonT3NoncanonicalBehavior": "reduces modulo P; does not reject",
            "modeledBurnRule": "restrict every preCommitment and amount operand to < P",
            "status": "PASS" if domain_pass and public_domain_pass else "FAIL",
        },
        "sources": {
            "pinnedArtifact": _file(artifact, root),
            "poseidon2Provenance": _file(p2_provenance_path, root),
            "bn254Regions": _file(regions_path, root),
            "canonicalStates": _file(states_path, root),
            "solidityDomainExecution": _file(solidity_domain_path, root),
            "lockedPoseidon2Constants": _file(p2_js_constants, root),
            "lockedPoseidon2Permutation": _file(p2_js_permutation, root),
            "barretenbergPoseidon2Params": _file(bb_params, root),
            "barretenbergPoseidon2Permutation": _file(bb_permutation, root),
            "noirPoseidonConstants": _file(noir_constants, root),
            "noirPoseidonPermutation": _file(noir_permutation, root),
            "noirPoseidonFraming": _file(noir_framing, root),
            "circomlibjsRawTables": _file(circom_raw, root),
            "circomlibjsOptimizedTables": _file(circom_opt, root),
            "circomlibjsOptimizationTransform": _file(circom_transform, root),
            "lockedPoseidonLiteAlgorithm": _file(poseidon_lite / "poseidon/index.js", root),
            "lockedSolidityPoseidonT3": _file(poseidon_solidity, root),
            "solidityGenerator": _file(solidity_generator, root),
        },
        "overall": "PASS" if identity_pass and domain_pass and public_domain_pass else "FAIL",
        "claimLimits": [
            "The audit checks construction identity and domains; it does not prove collision resistance.",
            "The future campaign must perform exact query-term equality at freeze.",
            "No no-collision condition was asserted and no solver query was run.",
        ],
    }
