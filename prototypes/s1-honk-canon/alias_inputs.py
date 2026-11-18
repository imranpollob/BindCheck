#!/usr/bin/env python3
"""Write aliased encodings of public input 0 next to a bb `public_inputs` file.

Outputs public_inputs_honest, public_inputs_plus_r and public_inputs_max_k
(x + k*r for the largest k with x + k*r < 2**256). Other inputs are unchanged.
Prints JSON with the three values as 0x-prefixed 32-byte hex.
"""
import json
import sys
from pathlib import Path

R = 21888242871839275222246405745257275088548364400416034343698204186575808495617


def main() -> None:
    path = Path(sys.argv[1])
    data = path.read_bytes()
    assert data and len(data) % 32 == 0, f"bad public_inputs length {len(data)}"
    words = [data[i:i + 32] for i in range(0, len(data), 32)]
    x = int.from_bytes(words[0], "big")
    assert x < R, "honest input is already non-canonical"
    k = (2**256 - 1 - x) // R
    out = {"n": x, "max_k": k}
    for name, value in [("honest", x), ("plus_r", x + R), ("max_k", x + k * R)]:
        assert value < 2**256
        enc = value.to_bytes(32, "big")
        (path.parent / f"public_inputs_{name}").write_bytes(enc + b"".join(words[1:]))
        out[name] = "0x" + enc.hex()
    print(json.dumps(out))


if __name__ == "__main__":
    main()
