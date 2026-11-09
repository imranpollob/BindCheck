from __future__ import annotations

import inspect
import json
import pathlib
import struct
import tempfile
import unittest

from bindcheck_zk.analyzer import analyze


ROOT = pathlib.Path(__file__).resolve().parents[2]
EXPECTED = json.loads((pathlib.Path(__file__).with_name("expected.json")).read_text())
R = 21888242871839275222246405745257275088548364400416034343698204186575808495617


def _noir(order: list[str]) -> str:
    parameters = ", ".join(f"{name}: pub Field" for name in order)
    return f"fn main({parameters}) {{}}\n"


def _verifier(count: int, guarded: str) -> str:
    if guarded == "all":
        guard = f"for (uint256 i = 0; i < input.length; i++) require(input[i] < {R});"
        array = "uint256[] memory input"
    else:
        guard = f"require(input[{int(guarded)}] < {R});"
        array = f"uint256[{count}] memory input"
    return f"""
contract Groth16Verifier {{
  function verifyProof(bytes memory proof, {array}) public view returns (bool) {{
    proof; {guard} return true;
  }}
}}
"""


def _write_base(root: pathlib.Path, circuit: str, verifier: str, consumer: str) -> None:
    (root / "circuits").mkdir()
    (root / "contracts").mkdir()
    (root / "circuits" / "main.nr").write_text(circuit)
    (root / "contracts" / "Verifier.sol").write_text(verifier)
    (root / "contracts" / "Consumer.sol").write_text(consumer)


def _guard_consumer(body: str, *, header_suffix: str = "", inheritance: str = "") -> str:
    return f"""
contract Consumer{inheritance} {{
  function submit(bytes memory proof, uint256[] calldata publicInputs, address recipient, bool choose){header_suffix} {{
    {body}
  }}
}}
"""


def _write_r1cs(path: pathlib.Path, constraints: list[list[list[tuple[int, int]]]]) -> None:
    field_size = 32
    prime = R.to_bytes(field_size, "little")
    n_wires = 7
    header = (
        struct.pack("<I", field_size)
        + prime
        + struct.pack("<IIII", n_wires, 1, 0, 2)
        + struct.pack("<Q", n_wires)
        + struct.pack("<I", len(constraints))
    )
    encoded = bytearray()
    for constraint in constraints:
        for linear_combination in constraint:
            encoded += struct.pack("<I", len(linear_combination))
            for wire, coefficient in linear_combination:
                encoded += struct.pack("<I", wire)
                encoded += (coefficient % R).to_bytes(field_size, "little")
    payload = bytearray(b"r1cs" + struct.pack("<II", 1, 2))
    payload += struct.pack("<IQ", 1, len(header)) + header
    payload += struct.pack("<IQ", 2, len(encoded)) + encoded
    path.write_bytes(payload)


def _write_commitment_fixture(root: pathlib.Path, fixture: str) -> None:
    (root / "circuits").mkdir()
    (root / "contracts").mkdir()
    (root / "circuits" / "main.circom").write_text("""pragma circom 2.0.0;
template Main() {
  signal input recipient;
  signal input amount;
  signal output extDataHash;
  component commitmentHash = Poseidon(2);
  commitmentHash.inputs[0] <== recipient;
  commitmentHash.inputs[1] <== amount;
  commitmentHash.out === extDataHash;
}
component main {public [extDataHash]} = Main();
""")
    coefficients = (1, -1)
    if fixture == "commitment_connected_nonbinding":
        coefficients = (0, -1)
    elif fixture == "commitment_altered_coefficients":
        coefficients = (7, -1)
    constraints = [
        [[(2, coefficients[0]), (4, coefficients[1])], [(0, 1)], []],
        [[(3, 1), (5, -1)], [(0, 1)], []],
        [[(4, 1), (5, 1)], [(0, 1)], [(6, 1)]],
        [[(6, 1), (1, -1)], [(0, 1)], []],
    ]
    _write_r1cs(root / "circuits" / "main.r1cs", constraints)
    (root / "circuits" / "main.sym").write_text(
        "1,1,0,main.extDataHash\n"
        "2,2,0,main.recipient\n"
        "3,3,0,main.amount\n"
        "4,4,0,main.commitmentHash.inputs[0]\n"
        "5,5,0,main.commitmentHash.inputs[1]\n"
        "6,6,0,main.commitmentHash.out\n"
    )
    (root / "contracts" / "Verifier.sol").write_text(_verifier(1, "0"))
    arguments = "amount, recipient" if fixture == "commitment_swapped_order" else "recipient, amount"
    (root / "contracts" / "Consumer.sol").write_text(f"""
contract Consumer {{
  function submit(bytes memory proof, address recipient, uint256 amount, uint256 extDataHash) public {{
    uint256 computed = Poseidon.compute({arguments});
    require(computed == extDataHash);
    verifier.verifyProof(proof, [extDataHash]);
    token.transfer(recipient, amount);
  }}
}}
""")


def write_fixture(root: pathlib.Path, fixture: str) -> tuple[str, str]:
    if fixture.startswith("commitment_"):
        _write_commitment_fixture(root, fixture)
        return "circuits/main.circom", "contracts/Consumer.sol"

    if fixture.startswith("guard_"):
        circuit = _noir(["provenRecipient", "amount"])
        verifier = _verifier(2, "0")
        require = "require(publicInputs[0] == uint256(uint160(recipient)));"
        effect = "token.transfer(recipient, publicInputs[1]);"
        if fixture == "guard_irrelevant_branch":
            body = f"if (choose) {{ {require} }} verifier.verifyProof(proof, publicInputs); {effect}"
        elif fixture == "guard_after_effect":
            body = f"verifier.verifyProof(proof, publicInputs); {effect} {require}"
        elif fixture == "guard_require_before":
            body = f"{require} verifier.verifyProof(proof, publicInputs); {effect}"
        elif fixture == "guard_conditional_effect":
            body = f"verifier.verifyProof(proof, publicInputs); if (publicInputs[0] == uint256(uint160(recipient))) {{ {effect} }}"
        elif fixture == "guard_modifier":
            body = f"{require} verifier.verifyProof(proof, publicInputs); {effect}"
            _write_base(root, circuit, verifier, _guard_consumer(body, header_suffix=" public onlyAuthorized"))
            return "circuits/main.nr", "contracts/Consumer.sol"
        elif fixture == "guard_inheritance":
            body = f"{require} verifier.verifyProof(proof, publicInputs); {effect}"
            _write_base(root, circuit, verifier, _guard_consumer(body, header_suffix=" public", inheritance=" is GuardBase"))
            return "circuits/main.nr", "contracts/Consumer.sol"
        else:
            body = "address(target).delegatecall(proof); verifier.verifyProof(proof, publicInputs); " + effect
        _write_base(root, circuit, verifier, _guard_consumer(body, header_suffix=" public"))
        return "circuits/main.nr", "contracts/Consumer.sol"

    if fixture.startswith("identity_"):
        verifier = _verifier(2 if fixture != "identity_any_caller" else 1, "0")
        if fixture == "identity_unproven_caller":
            circuit = _noir(["provenIdentity", "amount"])
            consumer = """
contract Consumer {
  function submit(bytes memory proof, uint256 provenIdentity, uint256 amount) public {
    verifier.verifyProof(proof, [provenIdentity, amount]);
    token.transfer(msg.sender, amount);
  }
}
"""
        elif fixture == "identity_proven_caller":
            circuit = _noir(["provenIdentity", "amount"])
            consumer = """
contract Consumer {
  function submit(bytes memory proof, uint256[] calldata publicInputs) public {
    require(publicInputs[0] == uint256(uint160(msg.sender)));
    verifier.verifyProof(proof, publicInputs);
    token.transfer(msg.sender, publicInputs[1]);
  }
}
"""
        else:
            circuit = _noir(["amount"])
            consumer = """
contract Consumer {
  function submit(bytes memory proof, uint256 amount) public {
    verifier.verifyProof(proof, [amount]);
    token.transfer(msg.sender, amount);
  }
}
"""
        _write_base(root, circuit, verifier, consumer)
        return "circuits/main.nr", "contracts/Consumer.sol"

    if fixture.startswith("canonical_"):
        guard = "0" if fixture == "canonical_wrong_position" else "1"
        if fixture == "canonical_all_positions":
            guard = "all"
        consumer = """
contract Consumer {
  mapping(uint256 => bool) spent;
  function submit(bytes memory proof, uint256 amount, uint256 nullifier, address recipient) public {
    require(!spent[nullifier]);
    verifier.verifyProof(proof, [amount, nullifier, uint256(uint160(recipient))]);
    spent[nullifier] = true;
    token.transfer(recipient, amount);
  }
}
"""
        _write_base(root, _noir(["amount", "nullifier", "recipient"]), _verifier(3, guard), consumer)
        return "circuits/main.nr", "contracts/Consumer.sol"

    if fixture == "direct_public_positive":
        consumer = """
contract Consumer {
  function submit(bytes memory proof, address recipient, uint256 amount) public {
    verifier.verifyProof(proof, [uint256(uint160(recipient)), amount]);
    token.transfer(recipient, amount);
  }
}
"""
        _write_base(root, _noir(["recipient", "amount"]), _verifier(2, "0"), consumer)
        return "circuits/main.nr", "contracts/Consumer.sol"
    raise AssertionError(f"unknown fixture {fixture}")


class VerdictSoundnessTests(unittest.TestCase):
    def test_expectations_cover_all_four_review_concerns(self) -> None:
        self.assertEqual(
            {case["concern"] for case in EXPECTED["cases"]},
            {"guard-dominance", "proof-authorized-identity", "replay-key-canonicality", "commitment-screen"},
        )
        self.assertEqual(EXPECTED["commitment_policy"], "SCREEN_ONLY_NEVER_VERIFIED")

    def test_declared_soundness_outcomes(self) -> None:
        failures: list[dict[str, object]] = []
        analyze_parameters = inspect.signature(analyze).parameters
        for case in EXPECTED["cases"]:
            with self.subTest(case=case["id"]):
                with tempfile.TemporaryDirectory(prefix="bindcheck-zk-soundness-") as name:
                    root = pathlib.Path(name)
                    circuit, consumer = write_fixture(root, case["fixture"])
                    kwargs: dict[str, object] = {
                        "explicit_circuits": [circuit],
                        "explicit_consumers": [consumer],
                    }
                    if "policy" in analyze_parameters:
                        kwargs["policy"] = case.get("policy", {})
                    output = analyze(root, **kwargs)
                summary = output["patterns"][case["pattern"]]
                if summary["verdict"] != case["verdict"] or case["reason"] not in summary["reasons"]:
                    failures.append({
                        "id": case["id"],
                        "expected": [case["verdict"], case["reason"]],
                        "observed": [summary["verdict"], summary["reasons"]],
                    })
        self.assertEqual(failures, [], json.dumps(failures, indent=2))


if __name__ == "__main__":
    unittest.main()
