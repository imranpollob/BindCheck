from __future__ import annotations

import importlib.util
import json
import pathlib
import struct
import tempfile
import unittest

from bindcheck_zk.analyzer import analyze
from bindcheck_zk.p4 import BN254_G2


ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPECTED = json.loads((ROOT / "tests" / "controls" / "expected.json").read_text())
R = 21888242871839275222246405745257275088548364400416034343698204186575808495617


def noir(order: list[str]) -> str:
    params = ", ".join(f"{name}: pub Field" for name in order)
    return f"fn main({params}) {{}}\n"


def verifier(count: int | None = 2, *, dynamic: bool = False, guard: bool = True, plonk: bool = False) -> str:
    array = "uint256[] memory input" if dynamic else f"uint256[{count}] memory input"
    guard_text = f"require(input[0] < {R});" if guard else "uint256 x = input[0] % FIELD; x;"
    family = "PlonkVerifier" if plonk else "Groth16Verifier"
    constant = f"uint256 constant NUMBER_OF_PUBLIC_INPUTS = {count};" if dynamic and count is not None else ""
    return f"""
contract {family} {{
  uint256 constant FIELD = {R};
  {constant}
  function verifyProof(bytes memory proof, {array}) public view returns (bool) {{
    proof; {guard_text} return true;
  }}
}}
"""


def consumer(vector: str, effect: str, *, params: str = "address recipient, uint256 amount", extra: str = "", function_name: str = "submit") -> str:
    return f"""
contract Consumer {{
  mapping(uint256 => bool) spent;
  function {function_name}(bytes memory proof, {params}) public {{
    {extra}
    verifier.verifyProof(proof, {vector});
    {effect}
  }}
}}
"""


def key_source(*, default: bool = False, duplicate: bool = False, guard: bool = True) -> str:
    gamma = BN254_G2 if default else tuple(value + 10 for value in BN254_G2)
    delta = BN254_G2 if default else tuple(value + 20 for value in BN254_G2)
    ic1 = (123456789012345678901, 223456789012345678901)
    ic2 = ic1 if duplicate else (323456789012345678901, 423456789012345678901)
    guard_text = f"require(input[0] < {R});" if guard else "input[0];"
    return f"""
contract Groth16Verifier {{
 uint256 constant gammaX1={gamma[0]}; uint256 constant gammaX2={gamma[1]};
 uint256 constant gammaY1={gamma[2]}; uint256 constant gammaY2={gamma[3]};
 uint256 constant deltaX1={delta[0]}; uint256 constant deltaX2={delta[1]};
 uint256 constant deltaY1={delta[2]}; uint256 constant deltaY2={delta[3]};
 uint256 constant ic0x={ic1[0]}; uint256 constant ic0y={ic1[1]};
 uint256 constant ic1x={ic2[0]}; uint256 constant ic1y={ic2[1]};
 function verifyProof(bytes memory proof, uint256[2] memory input) public view returns(bool) {{ proof; {guard_text} return true; }}
}}
"""


def p2_source() -> str:
    values = ",".join(str(value) for value in BN254_G2)
    return f"""
library Pairing {{
 struct G2Point {{ uint256[2] X; uint256[2] Y; }}
 function P2() internal pure returns (G2Point memory) {{ uint256[4] memory constants = [{values}]; constants; }}
}}
contract Groth16Verifier {{
 function verifyProof(bytes memory proof, uint256[2] memory input) public pure returns(bool) {{ proof; input; Pairing.P2(); return true; }}
}}
"""


def runtime_group(groups: int) -> str:
    raw = bytearray()
    for _ in range(groups):
        for value in BN254_G2:
            raw.append(0x7F)
            raw.extend(value.to_bytes(32, "big"))
            raw.append(0x50)
        raw.extend(b"\x00" * 8)
    raw.append(0)
    return raw.hex()


def write_minimal_r1cs(path: pathlib.Path, public_names: list[str]) -> None:
    field_size = 32
    header = (
        struct.pack("<I", field_size) + bytes(field_size)
        + struct.pack("<IIII", len(public_names) + 1, 0, len(public_names), 0)
        + struct.pack("<Q", len(public_names) + 1)
        + struct.pack("<I", 0)
    )
    payload = b"r1cs" + struct.pack("<II", 1, 2)
    payload += struct.pack("<IQ", 1, len(header)) + header
    payload += struct.pack("<IQ", 2, 0)
    path.write_bytes(payload)


def write_fixture(root: pathlib.Path, name: str) -> None:
    (root / "circuits").mkdir()
    (root / "contracts").mkdir()
    order = ["recipient", "amount"]
    circuit_source: tuple[str, str] | None = None
    consumer_path = root / "contracts" / "Consumer.sol"
    compiled_public_names: list[str] | None = None
    vsource = verifier()
    csource = consumer("[uint256(uint160(recipient)), amount]", "token.transfer(recipient, amount);")

    if name == "p1_fixed_direct":
        pass
    elif name == "p1_dynamic_direct":
        vsource = verifier(2, dynamic=True)
        csource = consumer("inputs", "token.transfer(address(uint160(inputs[0])), inputs[1]);", params="uint256[] calldata inputs")
    elif name == "p1_sender":
        order = ["amount"]
        vsource = verifier(1)
        csource = consumer("[amount]", "token.transfer(msg.sender, amount);")
    elif name == "p1_unbound_recipient":
        order = ["amount"]
        vsource = verifier(1)
        csource = consumer("[amount]", "token.transfer(recipient, amount);")
    elif name == "p1_unbound_amount":
        order = ["recipient"]
        vsource = verifier(1)
        csource = consumer("[uint256(uint160(recipient))]", "token.transfer(recipient, amount);")
    elif name == "p1_missing_verifier":
        order = ["amount"]
        vsource = ""
        csource = consumer("[amount]", "token.transfer(recipient, amount);")
    elif name == "p1_commitment_uncompiled":
        order = ["extDataHash"]
        vsource = verifier(1)
        csource = consumer("[extDataHash]", "token.transfer(recipient, amount);", params="address recipient, uint256 amount, uint256 extDataHash", extra="uint256 computed = Poseidon.compute(recipient, amount); require(computed == extDataHash);")
        circuit_source = ("main.circom", """pragma circom 2.0.0;
template HashBind() {
  signal input recipient;
  signal input amount;
  signal output out;
  component commitmentHash = Poseidon(2);
  commitmentHash.inputs[0] <== recipient;
  commitmentHash.inputs[1] <== amount;
  commitmentHash.out === extDataHash;
  out <== extDataHash;
}
component main {public [extDataHash]} = HashBind();
""")
    elif name == "p1_assembly":
        csource = consumer("[uint256(uint160(recipient)), amount]", "token.transfer(recipient, amount);", extra="assembly { let x := 1 }")
    elif name == "p1_internal_helper":
        order = ["recipient"]
        vsource = verifier(1)
        csource = """
contract Consumer {
  function _verifyProof(bytes memory proof, uint256[1] memory inputs) internal returns (bool) {
    return verifier.verifyProof(proof, inputs);
  }
  function submit(bytes memory proof, address recipient, uint256 amount) public {
    _verifyProof(proof, [uint256(uint160(recipient))]);
    token.mint(msg.sender, amount);
  }
}
"""
    elif name == "p1_erc721_safe_mint":
        order = ["credential"]
        vsource = verifier(1)
        csource = consumer("[credential]", "_safeMint(recipient, nextTokenId++);", params="uint256 credential, address recipient")
    elif name == "p1_internal_copy_helper":
        order = ["recipient"]
        vsource = verifier(1)
        csource = """
contract Consumer {
  function _verifyProof(bytes memory proof, uint256[] memory pubSignals) internal returns (bool) {
    uint256[1] memory signals;
    for (uint256 i = 0; i < 1; i++) signals[i] = pubSignals[i];
    return verifier.verifyProof(proof, signals);
  }
  function submit(bytes memory proof, uint256[] memory pubSignals, uint256 amount) public {
    _verifyProof(proof, pubSignals);
    token.mint(msg.sender, amount);
  }
}
"""
    elif name == "p1_explicit_over_cap":
        vsource = ""
        consumer_path = root / "zz" / "Consumer.sol"
        consumer_path.parent.mkdir()
        filler = root / "aa"
        filler.mkdir()
        for index in range(2501):
            (filler / f"{index:04d}.txt").write_text("inventory filler\n")
    elif name == "p1_contract_self":
        order = ["amount"]
        vsource = verifier(1)
        csource = consumer("[amount]", "token.transferFrom(msg.sender, address(this), amount);")

    elif name == "p2_chainid":
        order = ["chainId", "recipient", "amount"]
        vsource = verifier(3)
        csource = consumer("[block.chainid, uint256(uint160(recipient)), amount]", "token.transfer(recipient, amount);")
    elif name == "p2_contract":
        order = ["verifyingContract", "recipient", "amount"]
        vsource = verifier(3)
        csource = consumer("[uint256(uint160(address(this))), uint256(uint160(recipient)), amount]", "token.transfer(recipient, amount);")
    elif name == "p2_domain":
        order = ["domain", "recipient", "amount"]
        vsource = verifier(3)
        csource = consumer("[domain, uint256(uint160(recipient)), amount]", "token.transfer(recipient, amount);", params="uint256 domain, address recipient, uint256 amount")
    elif name == "p2_missing":
        pass
    elif name == "p2_comment":
        csource = "// block.chainid and domain are documented here\n" + csource
    elif name == "p2_unchecked":
        csource = consumer("[uint256(uint160(recipient)), amount]", "token.transfer(recipient, amount);", extra="uint256 chainId = block.chainid; chainId;")
    elif name == "p2_delegatecall":
        csource = consumer("[uint256(uint160(recipient)), amount]", "token.transfer(recipient, amount);", extra="address(this).delegatecall(proof);")
    elif name == "p2_chainid_guard":
        order = ["chainId", "recipient", "amount"]
        vsource = verifier(3, dynamic=True)
        csource = consumer("inputs", "token.transfer(recipient, amount);", params="uint256[] calldata inputs, address recipient, uint256 amount", extra="require(inputs[0] == block.chainid);")

    elif name.startswith("p3_"):
        order = ["nullifier", "recipient", "amount"]
        vsource = verifier(3, guard=name not in {"p3_alias", "p3_plonk_alias", "p3_hashed_alias"}, plonk=name == "p3_plonk_alias")
        key = "nullifier"
        before = "require(!spent[nullifier]);"
        after = "spent[nullifier] = true;"
        vector_expression = "[nullifier, uint256(uint160(recipient)), amount]"
        replay_params = "uint256 nullifier, address recipient, uint256 amount"
        if name == "p3_no_write":
            after = ""
        elif name == "p3_no_read":
            before = ""
        elif name == "p3_hashed":
            key = f"uint256(keccak256(abi.encode(nullifier % {R})))"
            before = f"require(!spent[{key}]);"
            after = f"spent[{key}] = true;"
        elif name == "p3_hashed_alias":
            before = "uint256 proofHash = uint256(keccak256(abi.encode(nullifier))); require(!spent[proofHash]);"
            after = "spent[proofHash] = true;"
        elif name == "p3_dynamic_key":
            key = "derive(nullifier)"
            before = "require(!spent[derive(nullifier)]);"
            after = "spent[derive(nullifier)] = true;"
        elif name == "p3_opaque_helper":
            before = "spent[nullifier]; checkNullifier(nullifier);"
            after = ""
        elif name == "p3_indexed_array":
            before = "uint256 i = 0; require(!spent[nullifiers[i]]);"
            after = "spent[nullifiers[i]] = true;"
            vector_expression = "[nullifiers[0], uint256(uint160(recipient)), amount]"
            replay_params = "uint256[1] memory nullifiers, address recipient, uint256 amount"
        csource = consumer(vector_expression, "token.transfer(recipient, amount);", params=replay_params, extra=before + after)

    elif name.startswith("p4_"):
        if name == "p4_distinct":
            vsource = key_source()
        elif name == "p4_default_key":
            vsource = key_source(default=True)
        elif name == "p4_library_p2":
            vsource = p2_source()
        elif name == "p4_duplicate_ic":
            vsource = key_source(duplicate=True)
        elif name == "p4_no_guard":
            vsource = key_source(guard=False)
        elif name == "p4_runtime_default":
            vsource = key_source()
            (root / "Verifier.bin-runtime").write_text(runtime_group(2))
        elif name == "p4_runtime_library":
            vsource = p2_source()
            (root / "Verifier.bin-runtime").write_text(runtime_group(1))
        elif name == "p4_runtime_truncated":
            vsource = key_source()
            (root / "Verifier.bin-runtime").write_text("7f12")
        elif name == "p4_interface_only":
            vsource = "interface IVerifier { function verifyProof(bytes memory proof, uint256[2] memory input) external view returns (bool); }"

    elif name.startswith("p5_"):
        if name == "p5_fixed_clean":
            pass
        elif name == "p5_count_bad":
            vsource = verifier(3)
        elif name == "p5_order_clean":
            pass
        elif name == "p5_order_bad":
            csource = consumer("[amount, uint256(uint160(recipient))]", "token.transfer(recipient, amount);")
        elif name == "p5_dynamic_clean":
            vsource = verifier(2, dynamic=True)
            csource = consumer("inputs", "token.transfer(address(uint160(inputs[0])), inputs[1]);", params="uint256[] calldata inputs", extra="require(inputs.length == 2);")
        elif name == "p5_dynamic_unknown":
            vsource = verifier(2, dynamic=True)
            csource = consumer("inputs", "token.transfer(address(uint160(inputs[0])), inputs[1]);", params="uint256[] calldata inputs")
        elif name == "p5_plonk_clean":
            vsource = verifier(2, dynamic=True, plonk=True)
            csource = consumer("inputs", "token.transfer(recipient, amount);", extra="uint256[] memory inputs = [uint256(uint160(recipient)), amount]; require(inputs.length == 2);")
        elif name == "p5_ambiguous":
            (root / "contracts" / "VerifierB.sol").write_text(verifier(3))
        elif name == "p5_compiled_symbolic":
            circuit_source = ("main.circom", """pragma circom 2.0.0;
function N() { return 1; }
template Main() { signal input recipient[N()]; signal input amount[N()]; }
component main {public [recipient, amount]} = Main();
""")
            compiled_public_names = ["recipient[0]", "amount[0]"]
        elif name == "p5_test_mock":
            mock_dir = root / "contracts" / "test"
            mock_dir.mkdir()
            (mock_dir / "MockVerifier.sol").write_text(verifier(3))

    if circuit_source is None:
        (root / "circuits" / "main.nr").write_text(noir(order))
    else:
        (root / "circuits" / circuit_source[0]).write_text(circuit_source[1])
    if compiled_public_names is not None:
        r1cs = root / "circuits" / "main.r1cs"
        write_minimal_r1cs(r1cs, compiled_public_names)
        (root / "circuits" / "main.sym").write_text("".join(
            f"{wire},{wire},0,main.{name}\n" for wire, name in enumerate(compiled_public_names, 1)
        ))
    if vsource:
        (root / "contracts" / "Verifier.sol").write_text(vsource)
    consumer_path.write_text(csource)


class BindCheckZKControlTests(unittest.TestCase):
    def test_frozen_oracle_has_required_coverage(self):
        self.assertEqual(len(EXPECTED["legacy_track_b"]), 24)
        self.assertGreaterEqual(len(EXPECTED["legacy_track_b"]) + len(EXPECTED["analyzer_controls"]), 60)
        self.assertEqual({item["pattern"] for item in EXPECTED["analyzer_controls"]}, {"P1", "P2", "P3", "P4", "P5"})

    def test_legacy_track_b_oracle_is_unchanged_and_decides_24_of_24(self):
        spec = importlib.util.spec_from_file_location("track_b", ROOT / "dataset" / "run_track_b.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        expected = {item["id"]: sorted(item["expected_p1_roles"]) for item in EXPECTED["legacy_track_b"]}
        observed = {case_id: module.decide(case)[0] for case_id, case in module.CONTROLS.items()}
        self.assertEqual(observed, expected)

    def test_all_new_pattern_controls(self):
        failures = []
        for control in EXPECTED["analyzer_controls"]:
            with self.subTest(control=control["id"]):
                with tempfile.TemporaryDirectory(prefix="bindcheck-zk-control-") as name:
                    root = pathlib.Path(name)
                    write_fixture(root, control["fixture"])
                    explicit = [control["explicit_consumer"]] if control.get("explicit_consumer") else None
                    output = analyze(root, explicit_consumers=explicit)
                summary = output["patterns"][control["pattern"]]
                if summary["verdict"] != control["verdict"] or control["reason"] not in summary["reasons"]:
                    failures.append({
                        "id": control["id"], "expected": [control["verdict"], control["reason"]],
                        "observed": [summary["verdict"], summary["reasons"]],
                        "coverage": output["coverage"],
                    })
        self.assertEqual(failures, [], json.dumps(failures, indent=2))


if __name__ == "__main__":
    unittest.main()
