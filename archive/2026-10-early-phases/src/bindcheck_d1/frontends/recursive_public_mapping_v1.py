"""Exact recursive-public-input mapping certificates.

The certificate connects an inner producer's public ABI to a bridge circuit's
public ABI and its decoded recursive-verifier argument.  Every equality is
checked against the bridge's serialized ACIR.  Width arithmetic and ABI shape
alone are never accepted as a mapping.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from . import acir_binary_v1
from .acir_bindings_v1 import certify_bindings
from .binding_certificate_check_v1 import verify, verify_tree


SCHEMA = "bindcheck.recursive-public-mapping.v1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _scalar_paths(abi: dict[str, Any]) -> list[dict[str, Any]]:
    leaves: list[dict[str, Any]] = []

    def visit(typ: dict[str, Any], path: str, visibility: str) -> None:
        kind = typ["kind"]
        if kind in {"field", "integer", "boolean"}:
            leaves.append({"path": path, "visibility": visibility})
        elif kind == "array":
            for index in range(typ["length"]):
                visit(typ["type"], f"{path}[{index}]", visibility)
        elif kind == "struct":
            for field in typ["fields"]:
                visit(field["type"], f"{path}.{field['name']}", visibility)
        else:
            raise ValueError(f"RECURSIVE_MAPPING_ABI_TYPE_UNSUPPORTED:{kind}")

    for parameter in abi["parameters"]:
        visit(parameter["type"], parameter["name"], parameter["visibility"])
    return [leaf for leaf in leaves if leaf["visibility"] == "public"]


def build(inner_artifact: Path, bridge_artifact: Path) -> dict[str, Any]:
    """Build and independently replay an exact bridge mapping certificate."""
    inner = acir_binary_v1.decode(inner_artifact)
    bridge = acir_binary_v1.decode(bridge_artifact)
    inner_leaves = _scalar_paths(inner["abi"])
    bridge_leaves = _scalar_paths(bridge["abi"])
    if len(inner_leaves) <= len(bridge_leaves):
        raise ValueError("RECURSIVE_MAPPING_HAS_NO_CONFIGURATION_PREFIX")
    prefix_width = len(inner_leaves) - len(bridge_leaves)
    if [item["path"] for item in inner_leaves[prefix_width:]] != [
            item["path"] for item in bridge_leaves]:
        raise ValueError("RECURSIVE_MAPPING_ABI_SUFFIX_MISMATCH")

    circuit = bridge["functions"][0]
    table = acir_binary_v1.abi_bindings(bridge["abi"], circuit)
    bindings = certify_bindings(bridge, table)
    checked = verify_tree(circuit, bindings)
    if len(bindings["bindings"]) != 1:
        raise ValueError("RECURSIVE_MAPPING_CALL_COUNT_UNSUPPORTED")
    binding = bindings["bindings"][0]
    if len(binding["allowed_key_constants"]) != prefix_width:
        raise ValueError("RECURSIVE_MAPPING_PREFIX_WIDTH_MISMATCH")
    equality_certificates = binding["public_inputs"]
    if len(equality_certificates) != len(bridge_leaves):
        raise ValueError("RECURSIVE_MAPPING_DIRECT_WIDTH_MISMATCH")

    certificate = {
        "schema": SCHEMA,
        "scope": "exact decoded recursive-call argument mapping; not key deployment or proof soundness",
        "inner_artifact": {"path": str(inner_artifact.resolve()), "sha256": _sha256(inner_artifact)},
        "bridge_artifact": {"path": str(bridge_artifact.resolve()), "sha256": _sha256(bridge_artifact)},
        "inner_public_count": len(inner_leaves),
        "consumer_public_count": len(bridge_leaves),
        "configuration_prefix": [
            {
                "producer_index": index,
                "producer_path": inner_leaves[index]["path"],
                "constant": binding["allowed_key_constants"][index]["value"],
                "certificate": binding["allowed_key_constants"][index]["certificate"],
            }
            for index in range(prefix_width)
        ],
        "mapping": [
            {
                "consumer_index": index,
                "consumer_path": bridge_leaf["path"],
                "producer_index": prefix_width + index,
                "producer_path": inner_leaves[prefix_width + index]["path"],
                "certificate": equality_certificates[index],
            }
            for index, bridge_leaf in enumerate(bridge_leaves)
        ],
        "checked_polynomial_identities": checked,
        "assumptions": [
            "correct pinned compiler/ABI decoder schema",
            "recursive proof-system soundness is external",
            "deployment selects the certified bridge artifact and its matching verification key",
        ],
    }
    verify_certificate(certificate, inner_artifact, bridge_artifact)
    return certificate


def verify_certificate(certificate: dict[str, Any], inner_artifact: Path,
                       bridge_artifact: Path) -> bool:
    """Fail closed unless every mapping row replays against the named bytes."""
    if certificate.get("schema") != SCHEMA:
        raise ValueError("RECURSIVE_MAPPING_CERTIFICATE_SCHEMA")
    if certificate.get("inner_artifact", {}).get("sha256") != _sha256(inner_artifact):
        raise ValueError("RECURSIVE_MAPPING_INNER_HASH_MISMATCH")
    if certificate.get("bridge_artifact", {}).get("sha256") != _sha256(bridge_artifact):
        raise ValueError("RECURSIVE_MAPPING_BRIDGE_HASH_MISMATCH")
    inner = acir_binary_v1.decode(inner_artifact)
    bridge = acir_binary_v1.decode(bridge_artifact)
    inner_paths = [item["path"] for item in _scalar_paths(inner["abi"])]
    bridge_paths = [item["path"] for item in _scalar_paths(bridge["abi"])]
    if certificate.get("inner_public_count") != len(inner_paths):
        raise ValueError("RECURSIVE_MAPPING_INNER_WIDTH_CHANGED")
    if certificate.get("consumer_public_count") != len(bridge_paths):
        raise ValueError("RECURSIVE_MAPPING_CONSUMER_WIDTH_CHANGED")

    prefix = certificate.get("configuration_prefix", [])
    mapping = certificate.get("mapping", [])
    if len(prefix) + len(mapping) != len(inner_paths) or len(mapping) != len(bridge_paths):
        raise ValueError("RECURSIVE_MAPPING_NOT_TOTAL")
    circuit = bridge["functions"][0]
    seen_consumer: set[int] = set()
    seen_producer: set[int] = set()
    for expected, row in enumerate(prefix):
        if row.get("producer_index") != expected or row.get("producer_path") != inner_paths[expected]:
            raise ValueError("RECURSIVE_MAPPING_PREFIX_IDENTITY_CHANGED")
        verify(circuit, row["certificate"])
        seen_producer.add(expected)
    for expected, row in enumerate(mapping):
        producer_index = row.get("producer_index")
        if row.get("consumer_index") != expected or row.get("consumer_path") != bridge_paths[expected]:
            raise ValueError("RECURSIVE_MAPPING_CONSUMER_IDENTITY_CHANGED")
        if not isinstance(producer_index, int) or not 0 <= producer_index < len(inner_paths):
            raise ValueError("RECURSIVE_MAPPING_PRODUCER_INDEX_INVALID")
        if row.get("producer_path") != inner_paths[producer_index]:
            raise ValueError("RECURSIVE_MAPPING_PRODUCER_IDENTITY_CHANGED")
        verify(circuit, row["certificate"])
        seen_consumer.add(expected)
        seen_producer.add(producer_index)
    if seen_consumer != set(range(len(bridge_paths))) or seen_producer != set(range(len(inner_paths))):
        raise ValueError("RECURSIVE_MAPPING_NOT_BIJECTIVE")
    return True
