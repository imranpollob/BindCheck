"""Pinned Noir beta.22 MessagePack-compact ACIR decoder.

This is deliberately separate from ``acir_binary_v1`` (the beta.14 legacy
bincode reader).  It decodes structure only.  Semantic support is declared by
the checker, not inferred from successful parsing.  Unknown opcode, black-box,
and Brillig variants fail closed with named reasons.
"""

from __future__ import annotations

import base64
from collections import Counter
import gzip
import hashlib
import io
import json
from pathlib import Path

from ..model_v2 import FIELD_MODULUS, Unsupported


REV = "c57152f91260ecdb9faad4efc20abb14b6d2ece7"
VERSION = "1.0.0-beta.22+" + REV
FORMAT_MSGPACK_COMPACT = 3
MAX_COMPRESSED_BYTES = 256 * 1024**2
MAX_DECODED_BYTES = 512 * 1024**2
MAX_ITEMS = 4_000_000
MAX_DEPTH = 256


class MessagePackReader:
    """Small strict reader for the MessagePack subset emitted by rmp-serde."""

    def __init__(self, data: bytes):
        if len(data) > MAX_DECODED_BYTES:
            raise Unsupported("BETA22_BINARY_SIZE_LIMIT", str(len(data)))
        self.data = data
        self.pos = 0

    def fail(self, reason: str, detail: str = "") -> None:
        raise Unsupported(reason, f"byte {self.pos}: {detail}")

    def take(self, count: int) -> bytes:
        if count < 0 or self.pos + count > len(self.data):
            self.fail("BETA22_TRUNCATED_MSGPACK", str(count))
        value = self.data[self.pos:self.pos + count]
        self.pos += count
        return value

    def uint(self, count: int) -> int:
        return int.from_bytes(self.take(count), "big", signed=False)

    def sint(self, count: int) -> int:
        return int.from_bytes(self.take(count), "big", signed=True)

    def checked_count(self, count: int) -> int:
        if count > MAX_ITEMS:
            self.fail("BETA22_COLLECTION_SIZE_LIMIT", str(count))
        return count

    def text(self, count: int) -> str:
        try:
            return self.take(self.checked_count(count)).decode("utf-8")
        except UnicodeDecodeError as exc:
            self.fail("BETA22_INVALID_UTF8", str(exc))

    def array(self, count: int, depth: int) -> list:
        return [self.value(depth + 1) for _ in range(self.checked_count(count))]

    def mapping(self, count: int, depth: int) -> dict:
        result = {}
        for _ in range(self.checked_count(count)):
            key = self.value(depth + 1)
            if not isinstance(key, (str, int, bool)):
                self.fail("BETA22_MAP_KEY_UNSUPPORTED", type(key).__name__)
            if key in result:
                self.fail("BETA22_DUPLICATE_MAP_KEY", repr(key))
            result[key] = self.value(depth + 1)
        return result

    def value(self, depth: int = 0):
        if depth > MAX_DEPTH:
            self.fail("BETA22_MSGPACK_DEPTH_LIMIT", str(depth))
        marker = self.uint(1)
        if marker <= 0x7f:
            return marker
        if 0x80 <= marker <= 0x8f:
            return self.mapping(marker & 0x0f, depth)
        if 0x90 <= marker <= 0x9f:
            return self.array(marker & 0x0f, depth)
        if 0xa0 <= marker <= 0xbf:
            return self.text(marker & 0x1f)
        if marker >= 0xe0:
            return marker - 256
        if marker == 0xc0:
            return None
        if marker == 0xc2:
            return False
        if marker == 0xc3:
            return True
        if marker in (0xc4, 0xc5, 0xc6):
            width = {0xc4: 1, 0xc5: 2, 0xc6: 4}[marker]
            return self.take(self.checked_count(self.uint(width)))
        if marker in (0xca, 0xcb):
            self.fail("BETA22_FLOAT_UNSUPPORTED", hex(marker))
        if marker in (0xcc, 0xcd, 0xce, 0xcf):
            return self.uint({0xcc: 1, 0xcd: 2, 0xce: 4, 0xcf: 8}[marker])
        if marker in (0xd0, 0xd1, 0xd2, 0xd3):
            return self.sint({0xd0: 1, 0xd1: 2, 0xd2: 4, 0xd3: 8}[marker])
        if marker in (0xd4, 0xd5, 0xd6, 0xd7, 0xd8, 0xc7, 0xc8, 0xc9):
            self.fail("BETA22_EXTENSION_UNSUPPORTED", hex(marker))
        if marker in (0xd9, 0xda, 0xdb):
            return self.text(self.uint({0xd9: 1, 0xda: 2, 0xdb: 4}[marker]))
        if marker in (0xdc, 0xdd):
            return self.array(self.uint({0xdc: 2, 0xdd: 4}[marker]), depth)
        if marker in (0xde, 0xdf):
            return self.mapping(self.uint({0xde: 2, 0xdf: 4}[marker]), depth)
        self.fail("BETA22_MSGPACK_MARKER_UNSUPPORTED", hex(marker))

    def one(self):
        value = self.value()
        if self.pos != len(self.data):
            self.fail("BETA22_TRAILING_MSGPACK_BYTES", str(len(self.data) - self.pos))
        return value


def _array(value, length: int | None, reason: str) -> list:
    if not isinstance(value, list) or (length is not None and len(value) != length):
        raise Unsupported(reason, f"expected array length {length}, observed {type(value).__name__}/{getattr(value, '__len__', lambda: '?')()}")
    return value


def _enum(value, reason: str) -> tuple[str, object]:
    if not isinstance(value, dict) or len(value) != 1:
        raise Unsupported(reason, "expected one-entry enum map")
    return next(iter(value.items()))


def _field(value) -> int:
    if not isinstance(value, bytes) or len(value) != 32:
        raise Unsupported("BETA22_FIELD_ENCODING", f"expected 32-byte bin, observed {type(value).__name__}/{len(value) if hasattr(value, '__len__') else '?'}")
    result = int.from_bytes(value, "big")
    if result >= FIELD_MODULUS:
        raise Unsupported("BETA22_NONCANONICAL_FIELD_ENCODING", str(result))
    return result


def _witness(value) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 0xffffffff:
        raise Unsupported("BETA22_WITNESS_ENCODING", repr(value))
    return value


def _witness_set(value, reason: str) -> list[int]:
    values = [_witness(item) for item in _array(value, None, reason)]
    if values != sorted(set(values)):
        raise Unsupported("BETA22_NONCANONICAL_WITNESS_SET", reason)
    return values


def _expression(value) -> dict:
    mul, linear, constant = _array(value, 3, "BETA22_EXPRESSION_SHAPE")
    return {
        "mul": [[_field(c), _witness(lhs), _witness(rhs)]
                for c, lhs, rhs in (_array(term, 3, "BETA22_MUL_TERM_SHAPE") for term in _array(mul, None, "BETA22_MUL_TERMS_SHAPE"))],
        "linear": [[_field(c), _witness(witness)]
                   for c, witness in (_array(term, 2, "BETA22_LINEAR_TERM_SHAPE") for term in _array(linear, None, "BETA22_LINEAR_TERMS_SHAPE"))],
        "constant": _field(constant),
    }


def _function_input(value) -> dict:
    kind, payload = _enum(value, "BETA22_FUNCTION_INPUT_SHAPE")
    if kind == "Constant":
        return {"constant": _field(payload)}
    if kind == "Witness":
        return {"witness": _witness(payload)}
    raise Unsupported("BETA22_FUNCTION_INPUT_UNSUPPORTED", kind)


def _blackbox(value) -> dict:
    kind, payload = _enum(value, "BETA22_BLACKBOX_SHAPE")
    if kind == "RANGE":
        function_input, num_bits = _array(payload, 2, "BETA22_RANGE_SHAPE")
        if not isinstance(num_bits, int) or isinstance(num_bits, bool) or not 0 <= num_bits <= 0xffffffff:
            raise Unsupported("BETA22_RANGE_BITS_ENCODING", repr(num_bits))
        return {"kind": "RANGE", "input": _function_input(function_input), "num_bits": num_bits}
    if kind == "Poseidon2Permutation":
        inputs, outputs = _array(payload, 2, "BETA22_POSEIDON2_SHAPE")
        return {"kind": kind,
                "inputs": [_function_input(item) for item in _array(inputs, None, "BETA22_POSEIDON2_INPUTS_SHAPE")],
                "outputs": [_witness(item) for item in _array(outputs, None, "BETA22_POSEIDON2_OUTPUTS_SHAPE")]}
    raise Unsupported("BETA22_BLACKBOX_UNSUPPORTED", kind)


def _brillig_input(value) -> dict:
    kind, payload = _enum(value, "BETA22_BRILLIG_INPUT_SHAPE")
    if kind == "Single":
        return {"single": _expression(payload)}
    if kind == "Array":
        return {"array": [_expression(item) for item in _array(payload, None, "BETA22_BRILLIG_ARRAY_INPUT_SHAPE")]}
    if kind == "MemoryArray":
        return {"memory_array": _witness(payload)}
    raise Unsupported("BETA22_BRILLIG_INPUT_UNSUPPORTED", kind)


def _brillig_output(value) -> dict:
    kind, payload = _enum(value, "BETA22_BRILLIG_OUTPUT_SHAPE")
    if kind == "Simple":
        return {"simple": _witness(payload)}
    if kind == "Array":
        return {"array": [_witness(item) for item in _array(payload, None, "BETA22_BRILLIG_ARRAY_OUTPUT_SHAPE")]}
    raise Unsupported("BETA22_BRILLIG_OUTPUT_UNSUPPORTED", kind)


def _opcode(value, index: int) -> dict:
    kind, payload = _enum(value, "BETA22_OPCODE_SHAPE")
    if kind == "AssertZero":
        result = {"kind": kind, "expression": _expression(payload)}
    elif kind == "BlackBoxFuncCall":
        result = _blackbox(payload)
    elif kind == "MemoryOp":
        block_id, operation = _array(payload, 2, "BETA22_MEMORY_OP_SHAPE")
        read, memory_index, memory_value = _array(operation, 3, "BETA22_MEMOP_SHAPE")
        if not isinstance(read, bool):
            raise Unsupported("BETA22_MEMORY_OPERATION_ENCODING", repr(read))
        result = {"kind": kind, "block_id": _witness(block_id),
                  "operation": "write" if read else "read",
                  "index": _witness(memory_index), "value": _witness(memory_value)}
    elif kind == "MemoryInit":
        block_id, init, block_type = _array(payload, 3, "BETA22_MEMORY_INIT_SHAPE")
        if isinstance(block_type, str):
            parsed_type = {"kind": block_type}
        else:
            type_kind, type_payload = _enum(block_type, "BETA22_MEMORY_BLOCK_TYPE_SHAPE")
            parsed_type = {"kind": type_kind, "id": _witness(type_payload)}
        if parsed_type["kind"] not in ("Memory", "CallData", "ReturnData"):
            raise Unsupported("BETA22_MEMORY_BLOCK_TYPE_UNSUPPORTED", parsed_type["kind"])
        result = {"kind": kind, "block_id": _witness(block_id),
                  "init": [_witness(item) for item in _array(init, None, "BETA22_MEMORY_INIT_VALUES_SHAPE")],
                  "block_type": parsed_type}
    elif kind == "BrilligCall":
        function_id, inputs, outputs, predicate = _array(payload, 4, "BETA22_BRILLIG_CALL_SHAPE")
        result = {"kind": kind, "id": _witness(function_id),
                  "inputs": [_brillig_input(item) for item in _array(inputs, None, "BETA22_BRILLIG_INPUTS_SHAPE")],
                  "outputs": [_brillig_output(item) for item in _array(outputs, None, "BETA22_BRILLIG_OUTPUTS_SHAPE")],
                  "predicate": _expression(predicate)}
    elif kind == "Call":
        function_id, inputs, outputs, predicate = _array(payload, 4, "BETA22_CALL_SHAPE")
        result = {"kind": kind, "id": _witness(function_id),
                  "inputs": [_witness(item) for item in _array(inputs, None, "BETA22_CALL_INPUTS_SHAPE")],
                  "outputs": [_witness(item) for item in _array(outputs, None, "BETA22_CALL_OUTPUTS_SHAPE")],
                  "predicate": _expression(predicate)}
    else:
        raise Unsupported("BETA22_OPCODE_UNSUPPORTED", kind)
    result["opcode_index"] = index
    return result


BRILLIG_OPCODE_NAMES = {
    "BinaryFieldOp", "BinaryIntOp", "Cast", "JumpIf", "Jump", "CalldataCopy",
    "Call", "Const", "Return", "Mov", "Store", "Stop",
}


def _brillig_address(value) -> dict:
    kind, payload = _enum(value, "BETA22_BRILLIG_ADDRESS_SHAPE")
    if kind not in ("Direct", "Relative"):
        raise Unsupported("BETA22_BRILLIG_ADDRESS_UNSUPPORTED", kind)
    return {kind.lower(): _witness(payload)}


def _integer_bitsize(value) -> str:
    allowed = {"U1", "U8", "U16", "U32", "U64", "U128"}
    if not isinstance(value, str) or value not in allowed:
        raise Unsupported("BETA22_BRILLIG_INTEGER_BITSIZE_UNSUPPORTED", repr(value))
    return value


def _bitsize(value) -> str:
    if value == "Field":
        return value
    kind, payload = _enum(value, "BETA22_BRILLIG_BITSIZE_SHAPE")
    if kind != "Integer":
        raise Unsupported("BETA22_BRILLIG_BITSIZE_UNSUPPORTED", kind)
    return _integer_bitsize(payload)


def _label(value) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise Unsupported("BETA22_BRILLIG_LABEL_ENCODING", repr(value))
    return value


def _validate_brillig_opcode(kind: str, payload) -> None:
    if kind == "BlackBox":
        inner = next(iter(payload)) if isinstance(payload, dict) and payload else type(payload).__name__
        raise Unsupported("BETA22_BRILLIG_BLACKBOX_UNSUPPORTED", str(inner))
    if kind not in BRILLIG_OPCODE_NAMES:
        raise Unsupported("BETA22_BRILLIG_OPCODE_UNSUPPORTED", kind)
    if kind == "Return":
        if payload is not None:
            raise Unsupported("BETA22_BRILLIG_RETURN_SHAPE", repr(payload))
        return
    values = _array(payload, {
        "BinaryFieldOp": 4, "BinaryIntOp": 5, "Cast": 3, "JumpIf": 2,
        "Jump": 1, "CalldataCopy": 3, "Call": 1, "Const": 3, "Mov": 2,
        "Store": 2, "Stop": 1,
    }[kind], f"BETA22_BRILLIG_{kind.upper()}_SHAPE")
    if kind == "BinaryFieldOp":
        _brillig_address(values[0])
        if values[1] not in {"Add", "Sub", "Mul", "Div", "IntegerDiv", "Equals", "LessThan", "LessThanEquals"}:
            raise Unsupported("BETA22_BRILLIG_FIELD_OP_UNSUPPORTED", repr(values[1]))
        _brillig_address(values[2]); _brillig_address(values[3])
    elif kind == "BinaryIntOp":
        _brillig_address(values[0])
        if values[1] not in {"Add", "Sub", "Mul", "Div", "Equals", "LessThan", "LessThanEquals", "And", "Or", "Xor", "Shl", "Shr"}:
            raise Unsupported("BETA22_BRILLIG_INTEGER_OP_UNSUPPORTED", repr(values[1]))
        _integer_bitsize(values[2]); _brillig_address(values[3]); _brillig_address(values[4])
    elif kind == "Cast":
        _brillig_address(values[0]); _brillig_address(values[1]); _bitsize(values[2])
    elif kind == "JumpIf":
        _brillig_address(values[0]); _label(values[1])
    elif kind in ("Jump", "Call"):
        _label(values[0])
    elif kind == "CalldataCopy":
        for value in values:
            _brillig_address(value)
    elif kind == "Const":
        _brillig_address(values[0]); _bitsize(values[1]); _field(values[2])
    elif kind in ("Mov", "Store"):
        _brillig_address(values[0]); _brillig_address(values[1])
    elif kind == "Stop":
        pointer, size = _array(values[0], 2, "BETA22_BRILLIG_HEAP_VECTOR_SHAPE")
        _brillig_address(pointer); _brillig_address(size)


def _brillig_function(value, index: int) -> dict:
    function_name, bytecode = _array(value, 2, "BETA22_BRILLIG_FUNCTION_SHAPE")
    if not isinstance(function_name, str):
        raise Unsupported("BETA22_BRILLIG_FUNCTION_NAME_ENCODING", repr(function_name))
    kinds = []
    for opcode in _array(bytecode, None, "BETA22_BRILLIG_BYTECODE_SHAPE"):
        if isinstance(opcode, str):
            kind = opcode
        else:
            kind, _payload = _enum(opcode, "BETA22_BRILLIG_OPCODE_SHAPE")
        _validate_brillig_opcode(kind, _payload if not isinstance(opcode, str) else None)
        kinds.append(kind)
    return {"id": index, "function_name": function_name, "opcode_count": len(kinds),
            "opcode_kind_counts": dict(sorted(Counter(kinds).items()))}


def _circuit(value, index: int) -> dict:
    function_name, opcodes, private, public, returns, assert_messages = _array(
        value, 6, "BETA22_CIRCUIT_SHAPE",
    )
    if not isinstance(function_name, str):
        raise Unsupported("BETA22_FUNCTION_NAME_ENCODING", repr(function_name))
    if not isinstance(assert_messages, list):
        raise Unsupported("BETA22_ASSERT_MESSAGES_SHAPE", type(assert_messages).__name__)
    return {
        "function_index": index,
        "function_name": function_name,
        "opcodes": [_opcode(opcode, opcode_index) for opcode_index, opcode in enumerate(opcodes)],
        "private_parameters": _witness_set(private, "private_parameters"),
        "public_parameters": _witness_set(public, "public_parameters"),
        "return_values": _witness_set(returns, "return_values"),
        "assert_message_count": len(assert_messages),
    }


def decode_bytes(compressed: bytes) -> dict:
    if len(compressed) > MAX_COMPRESSED_BYTES:
        raise Unsupported("BETA22_COMPRESSED_SIZE_LIMIT", str(len(compressed)))
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
            decoded = stream.read(MAX_DECODED_BYTES + 1)
    except (OSError, EOFError) as exc:
        raise Unsupported("BETA22_GZIP_INVALID", str(exc)) from exc
    if len(decoded) > MAX_DECODED_BYTES:
        raise Unsupported("BETA22_BINARY_SIZE_LIMIT", str(len(decoded)))
    if not decoded:
        raise Unsupported("BETA22_EMPTY_BINARY", "")
    if decoded[0] != FORMAT_MSGPACK_COMPACT:
        raise Unsupported("BETA22_SERIALIZATION_FORMAT_UNSUPPORTED", str(decoded[0]))
    raw = MessagePackReader(decoded[1:]).one()
    functions, unconstrained = _array(raw, 2, "BETA22_PROGRAM_SHAPE")
    result = {
        "functions": [_circuit(item, index) for index, item in enumerate(_array(functions, None, "BETA22_FUNCTIONS_SHAPE"))],
        "unconstrained_functions": [_brillig_function(item, index) for index, item in enumerate(_array(unconstrained, None, "BETA22_UNCONSTRAINED_FUNCTIONS_SHAPE"))],
        "serialization": {"format_byte": decoded[0], "format": "msgpack-compact",
                          "decoded_sha256": hashlib.sha256(decoded).hexdigest(),
                          "decoded_bytes": len(decoded)},
    }
    if len(result["functions"]) != 1:
        raise Unsupported("BETA22_CONSTRAINED_FUNCTION_COUNT_UNSUPPORTED", str(len(result["functions"])))
    return result


def decode(path) -> dict:
    artifact_path = Path(path)
    artifact = json.loads(artifact_path.read_text())
    if artifact.get("noir_version") != VERSION:
        raise Unsupported("BETA22_COMPILER_VERSION_UNSUPPORTED", str(artifact.get("noir_version")))
    try:
        compressed = base64.b64decode(artifact["bytecode"], validate=True)
    except (KeyError, ValueError) as exc:
        raise Unsupported("BETA22_BASE64_INVALID", str(exc)) from exc
    result = decode_bytes(compressed)
    result["identity"] = {
        "path": str(artifact_path),
        "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        "compressed_sha256": hashlib.sha256(compressed).hexdigest(),
        "compressed_bytes": len(compressed),
        "decoder_version": VERSION,
    }
    result["abi"] = artifact["abi"]
    return result


def abi_bindings(abi: dict, circuit: dict) -> dict[str, list[int]]:
    """Mirror beta.22 noirc_abi's flat, declaration-order witness allocation."""
    cursor = 0
    table: dict[str, list[int]] = {}
    public: list[int] = []
    private: list[int] = []

    def visit(typ: dict, name: str) -> list[int]:
        nonlocal cursor
        start = cursor
        kind = typ["kind"]
        if kind in ("field", "integer", "boolean"):
            cursor += 1
        elif kind == "array":
            length = typ["length"]
            if not isinstance(length, int) or not 0 <= length <= MAX_ITEMS:
                raise Unsupported("BETA22_ABI_SIZE_LIMIT", name)
            for item in range(length):
                visit(typ["type"], f"{name}[{item}]")
        elif kind == "struct":
            for field in typ["fields"]:
                visit(field["type"], name + "." + field["name"])
        else:
            raise Unsupported("BETA22_ABI_TYPE_UNSUPPORTED", kind)
        if name in table:
            raise Unsupported("BETA22_DUPLICATE_ABI_PATH", name)
        table[name] = list(range(start, cursor))
        return table[name]

    for parameter in abi["parameters"]:
        ids = visit(parameter["type"], parameter["name"])
        if parameter["visibility"] == "public":
            public.extend(ids)
        elif parameter["visibility"] == "private":
            private.extend(ids)
        else:
            raise Unsupported("BETA22_ABI_VISIBILITY_UNSUPPORTED", parameter["visibility"])
    if public != circuit["public_parameters"] or private != circuit["private_parameters"]:
        raise Unsupported("BETA22_ABI_DECLARATION_IDENTITY_MISMATCH",
                          "typed declaration differs from beta.22 ABI allocation")
    if abi.get("return_type") is not None or circuit["return_values"]:
        raise Unsupported("BETA22_ABI_RETURN_MAPPING_UNSUPPORTED", "")
    return table
