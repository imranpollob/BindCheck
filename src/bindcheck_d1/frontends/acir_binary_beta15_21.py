"""Validated ACIR container support for Noir beta.15 through beta.21.

This module is a format adapter, not a new semantic checker.  The beta.15--18
development fixtures use the same legacy-bincode program encoding as beta.14.
The beta.19--21 fixtures use MessagePack compact format 3, with the
``current_witness_index`` circuit field that beta.22 removed.  Opcode decoding
and ABI allocation delegate to the already fail-closed beta.14/beta.22
readers; unknown variants remain unsupported with a named reason.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
from pathlib import Path

from ..model_v2 import Unsupported
from . import acir_binary_beta22 as beta22
from . import acir_binary_v1 as beta14


VERSIONS = {
    "1.0.0-beta.15+83245db91dcf63420ef4bcbbd85b98f397fee663": "legacy-bincode",
    "1.0.0-beta.16+2d46fca7203545cbbfb31a0d0328de6c10a8db95": "legacy-bincode",
    "1.0.0-beta.17+0d6984c7c643b690e6559351f0cb36ce62b44b26": "legacy-bincode",
    "1.0.0-beta.18+99bb8b5cf33d7669adbdef096b12d80f30b4c0c9": "legacy-bincode",
    "1.0.0-beta.19+74d6be658e1ad252f87943292ba09bdd4da80bd4": "msgpack-compact-v3-with-witness-index",
    "1.0.0-beta.20+b4236c1957d0c26cb65d82adc9e5447b6ff1d629": "msgpack-compact-v3-with-witness-index",
    "1.0.0-beta.21+89a0f0faf3a5f1273c8ac4843b7877882437e277": "msgpack-compact-v3-with-witness-index",
}


def _decompress(compressed: bytes, *, reason_prefix: str) -> bytes:
    if len(compressed) > beta22.MAX_COMPRESSED_BYTES:
        raise Unsupported(f"{reason_prefix}_COMPRESSED_SIZE_LIMIT", str(len(compressed)))
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
            decoded = stream.read(beta22.MAX_DECODED_BYTES + 1)
    except (OSError, EOFError) as exc:
        raise Unsupported(f"{reason_prefix}_GZIP_INVALID", str(exc)) from exc
    if len(decoded) > beta22.MAX_DECODED_BYTES:
        raise Unsupported(f"{reason_prefix}_BINARY_SIZE_LIMIT", str(len(decoded)))
    if not decoded:
        raise Unsupported(f"{reason_prefix}_EMPTY_BINARY", "")
    return decoded


def _msgpack_circuit(value, index: int) -> dict:
    (function_name, current_witness_index, opcodes, private, public, returns,
     assert_messages) = beta22._array(value, 7, "BETA19_21_CIRCUIT_SHAPE")
    if not isinstance(function_name, str):
        raise Unsupported("BETA19_21_FUNCTION_NAME_ENCODING", repr(function_name))
    if (not isinstance(current_witness_index, int)
            or isinstance(current_witness_index, bool)
            or not 0 <= current_witness_index <= 0xffffffff):
        raise Unsupported("BETA19_21_CURRENT_WITNESS_INDEX_ENCODING",
                          repr(current_witness_index))
    if not isinstance(assert_messages, list):
        raise Unsupported("BETA19_21_ASSERT_MESSAGES_SHAPE", type(assert_messages).__name__)
    return {
        "function_index": index,
        "function_name": function_name,
        "current_witness_index": current_witness_index,
        "opcodes": [beta22._opcode(opcode, opcode_index)
                    for opcode_index, opcode in enumerate(opcodes)],
        "private_parameters": beta22._witness_set(private, "private_parameters"),
        "public_parameters": beta22._witness_set(public, "public_parameters"),
        "return_values": beta22._witness_set(returns, "return_values"),
        "assert_message_count": len(assert_messages),
    }


def _decode_msgpack(compressed: bytes) -> dict:
    decoded = _decompress(compressed, reason_prefix="BETA19_21")
    if decoded[0] != beta22.FORMAT_MSGPACK_COMPACT:
        raise Unsupported("BETA19_21_SERIALIZATION_FORMAT_UNSUPPORTED", str(decoded[0]))
    raw = beta22.MessagePackReader(decoded[1:]).one()
    functions, unconstrained = beta22._array(raw, 2, "BETA19_21_PROGRAM_SHAPE")
    result = {
        "functions": [
            _msgpack_circuit(item, index)
            for index, item in enumerate(
                beta22._array(functions, None, "BETA19_21_FUNCTIONS_SHAPE")
            )
        ],
        "unconstrained_functions": [
            beta22._brillig_function(item, index)
            for index, item in enumerate(
                beta22._array(unconstrained, None, "BETA19_21_UNCONSTRAINED_FUNCTIONS_SHAPE")
            )
        ],
        "serialization": {
            "format_byte": decoded[0],
            "format": "msgpack-compact-v3-with-witness-index",
            "decoded_sha256": hashlib.sha256(decoded).hexdigest(),
            "decoded_bytes": len(decoded),
        },
    }
    if len(result["functions"]) != 1:
        raise Unsupported("BETA19_21_CONSTRAINED_FUNCTION_COUNT_UNSUPPORTED",
                          str(len(result["functions"])))
    return result


def _decode_legacy(compressed: bytes) -> dict:
    decoded = _decompress(compressed, reason_prefix="BETA15_18")
    result = beta14.Reader(decoded).program()
    result["serialization"] = {
        "format": "legacy-bincode",
        "decoded_sha256": hashlib.sha256(decoded).hexdigest(),
        "decoded_bytes": len(decoded),
    }
    return result


def decode(path) -> dict:
    artifact_path = Path(path)
    artifact = json.loads(artifact_path.read_text())
    version = artifact.get("noir_version")
    encoding = VERSIONS.get(version)
    if encoding is None:
        raise Unsupported("BETA15_21_COMPILER_VERSION_UNSUPPORTED", str(version))
    try:
        compressed = base64.b64decode(artifact["bytecode"], validate=True)
    except (KeyError, ValueError) as exc:
        raise Unsupported("BETA15_21_BASE64_INVALID", str(exc)) from exc
    result = (_decode_legacy(compressed) if encoding == "legacy-bincode"
              else _decode_msgpack(compressed))
    result["identity"] = {
        "path": str(artifact_path),
        "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        "compressed_sha256": hashlib.sha256(compressed).hexdigest(),
        "compressed_bytes": len(compressed),
        "decoder_version": version,
        "encoding": encoding,
    }
    result["abi"] = artifact["abi"]
    return result


def abi_bindings(abi: dict, circuit: dict) -> dict[str, list[int]]:
    """Use the checked declaration-order ABI allocation shared by the fixtures."""
    return beta22.abi_bindings(abi, circuit)
