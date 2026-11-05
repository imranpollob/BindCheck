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
    elif name == "p1_erc721_mint":
        order = ["credential"]
        vsource = verifier(1)
        csource = """
contract Consumer is ERC721 {
  function submit(bytes memory proof, uint256 credential) public {
    verifier.verifyProof(proof, [credential]);
    uint256 tokenId = nextTokenId++;
    _mint(msg.sender, tokenId);
  }
}
"""
    elif name == "p1_storage_amount":
        order = ["recipient"]
        vsource = verifier(1)
        csource = """
contract Consumer {
  uint256 amountPerRedemption;
  function submit(bytes memory proof) public {
    verifier.verifyProof(proof, [uint256(uint160(msg.sender))]);
    token.transfer(msg.sender, amountPerRedemption);
  }
}
"""
    elif name == "p1_derived_amount":
        order = ["amount"]
        vsource = verifier(1)
        csource = """
contract Consumer {
  function submit(bytes memory proof, uint256 amount) public {
    verifier.verifyProof(proof, [amount]);
    uint256 fee = amount / 100;
    uint256 payout = amount - fee;
    token.transfer(msg.sender, payout);
  }
}
"""
    elif name == "p1_opaque_struct_input":
        order = ["amount"]
        vsource = """
contract CipherVerifier {
  function verifyProof(Proof calldata proof, bytes2 kind) public returns (bool) {
    proof; kind; return true;
  }
}
"""
        csource = """
contract Consumer {
  function submit(Proof calldata proof, bytes2 kind) public {
    PublicSignals calldata publicSignals = proof.publicSignals;
    verifier.verifyProof(proof, kind);
    token.transfer(msg.sender, publicSignals.amount);
  }
}
"""

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
        elif name == "p3_nested_index":
            before = "require(!spent[proof.publicSignals[0]]);"
            after = "spent[proof.publicSignals[0]] = true;"
            vector_expression = "proof.publicSignals"
            replay_params = "Proof calldata proof, address recipient, uint256 amount"
        elif name == "p3_nested_mapping":
            csource = """
contract Consumer {
  mapping(address => mapping(uint256 => bool)) usedNonces;
  function submit(bytes memory proof, uint256 proofNonce, address recipient, uint256 amount) public {
    require(!usedNonces[msg.sender][proofNonce]);
    usedNonces[msg.sender][proofNonce] = true;
    verifier.verifyProof(proof, [proofNonce, uint256(uint160(recipient)), amount]);
    token.transfer(recipient, amount);
  }
}
"""
        elif name == "p3_generic_helper":
            csource = """
contract Consumer {
  mapping(uint256 => bool) spent;
  function preflight(uint256 key) internal view { require(!spent[key]); }
  function submit(bytes memory proof, uint256 nullifier, address recipient, uint256 amount) public {
    preflight(nullifier);
    verifier.verifyProof(proof, [nullifier, uint256(uint160(recipient)), amount]);
    spent[nullifier] = true;
    token.transfer(recipient, amount);
  }
}
"""
        elif name == "p3_unbound_key":
            csource = """
contract Consumer {
  mapping(bytes32 => bool) spent;
  function submit(bytes memory proof, uint256 nullifier, bytes32 replayKey, address recipient, uint256 amount) public {
    require(!spent[replayKey]);
    verifier.verifyProof(proof, [nullifier, uint256(uint160(recipient)), amount]);
    spent[replayKey] = true;
    token.transfer(recipient, amount);
  }
}
"""
        elif name == "p3_member_vector_binding":
            csource = """
contract Consumer {
  mapping(uint256 => bool) spent;
  function submit(Proof calldata proof, uint256 nullifier, address recipient, uint256 amount) public {
    require(proof.input[0] == nullifier);
    require(!spent[nullifier]);
    verifier.verifyProof(proof.data, proof.input);
    spent[nullifier] = true;
    token.transfer(recipient, amount);
  }
}
"""
        elif name == "p3_aliased_vector_binding":
            csource = """
contract Consumer {
  mapping(bytes32 => bool) spent;
  function submit(bytes memory proof, Receipt calldata receipt, address recipient, uint256 amount) public {
    bytes32 replayKey = keccak256(abi.encode(receipt.sessionId, receipt.sequence));
    uint256 leaf = uint256(keccak256(abi.encode(receipt.sessionId, receipt.sequence)));
    require(!spent[replayKey]);
    verifier.verifyProof(proof, [leaf, uint256(uint160(recipient)), amount]);
    spent[replayKey] = true;
    token.transfer(recipient, amount);
  }
}
"""
        if name not in {"p3_nested_mapping", "p3_generic_helper", "p3_unbound_key", "p3_member_vector_binding", "p3_aliased_vector_binding"}:
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
        elif name == "p4_honk_unsupported":
            vsource = key_source(guard=False).replace("Groth16Verifier", "HonkVerifier")
        elif name == "p4_unknown_layout":
            vsource = key_source(guard=False).replace("Groth16Verifier", "CustomVerifier")
        elif name == "p4_direct_reject_guard":
            vsource = key_source(guard=False).replace(
                "input[0];", f"if (input[0] >= {R}) return false;"
            )
        elif name == "p4_alias_reject_guard":
            vsource = (
                key_source(guard=False)
                .replace(" memory input)", " memory inputs)")
                .replace("input[0];", f"uint256 publicInput = inputs[0]; if (publicInput >= {R}) revert();")
            )
        elif name == "p4_delegated_guard":
            vsource = """
contract Groth16Verifier {
  function verifyProof(bytes memory proof, uint256[2] memory input) public view returns (bool) {
    return Groth16.verifyProof(proof, input);
  }
}
"""
        elif name == "p4_fail_closed":
            vsource = """
contract Groth16Verifier {
  function verifyProof(bytes memory proof, uint256[2] memory input) public pure returns (bool) {
    proof; input; return false;
  }
}
"""

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
        elif name == "p5_main_template_scope":
            circuit_source = ("main.circom", """pragma circom 2.0.0;
template Helper() { signal input ignored; signal output helperOutput; helperOutput <== ignored; }
template Main() {
  signal input recipient;
  signal input amount;
  signal squared;
  squared <== recipient * amount;
}
component main {public [recipient, amount]} = Main();
""")
        elif name == "p5_receiver_type_match":
            vsource = ""
            (root / "contracts" / "ExpectedVerifier.sol").write_text(verifier(2).replace("Groth16Verifier", "ExpectedVerifier"))
            (root / "contracts" / "OtherVerifier.sol").write_text(verifier(3).replace("Groth16Verifier", "OtherVerifier"))
            csource = """
contract Consumer {
  ExpectedVerifier verifier;
  OtherVerifier other;
  function submit(bytes memory proof, address recipient, uint256 amount) public {
    verifier.verifyProof(proof, [uint256(uint160(recipient)), amount]);
    token.transfer(recipient, amount);
  }
}
"""
        elif name == "p5_dynamic_allocated":
            vsource = verifier(2, dynamic=True)
            csource = """
contract Consumer {
  function submit(bytes memory proof, address recipient, uint256 amount) public {
    uint256[] memory inputs = new uint256[](2);
    inputs[0] = uint256(uint160(recipient));
    inputs[1] = amount;
    verifier.verifyProof(proof, inputs);
    token.transfer(recipient, amount);
  }
}
"""
        elif name == "p5_count_guided_match":
            circuit_source = ("submit-two.nr", noir(["recipient", "amount"]))
            (root / "circuits" / "submit-three.nr").write_text(noir(["recipient", "amount", "domain"]))
            csource = """
contract Consumer {
  Groth16Verifier verifier;
  function submit(bytes memory proof, address recipient, uint256 amount) public {
    verifier.verifyProof(proof, [uint256(uint160(recipient)), amount]);
    token.transfer(recipient, amount);
  }
}
"""
        elif name == "p5_semantic_name_unresolved":
            csource = consumer(
                "[uint256(uint160(beneficiary)), amount]",
                "token.transfer(beneficiary, amount);",
                params="address beneficiary, uint256 amount",
            )
        elif name == "p5_incomplete_interface":
            vsource = verifier(3)
            csource = consumer(
                "[a, b, c]",
                "token.transfer(recipient, amount);",
                params="uint256 a, uint256 b, uint256 c, address recipient, uint256 amount",
            )
            circuit_source = ("main.circom", """pragma circom 2.0.0;
include "missing-template.circom";
component main {public [a, b]} = ImportedMain();
""")

    elif name == "discovery_merkle_only":
        csource = """
contract Consumer {
  function submit(bytes32[] calldata proof, address recipient, uint256 amount) public {
    require(MerkleProof.verify(proof, root, leaf));
    token.transfer(recipient, amount);
  }
}
"""
    elif name == "discovery_test_consumer":
        consumer_path = root / "contracts" / "test" / "TestConsumer.t.sol"
        consumer_path.parent.mkdir()
    elif name == "discovery_non_entry_circuit":
        (root / "circuits" / "constants.circom").write_text("pragma circom 2.0.0; var FIELD = 1;\n")
    elif name == "discovery_verify_only_consumer":
        csource = consumer(
            "[uint256(uint160(recipient)), amount]",
            "recipient; amount;",
        )
    elif name == "discovery_verifier_wrapper":
        (root / "contracts" / "AdapterVerifier.sol").write_text("""
contract AdapterVerifier {
  Groth16Verifier core;
  function verifyProof(bytes memory proof, uint256[2] memory input) public returns (bool) {
    return core.verifyProof(proof, input);
  }
}
""")
        csource = """
contract Consumer {
  Groth16Verifier verifier;
  function submit(bytes memory proof, address recipient, uint256 amount) public {
    verifier.verifyProof(proof, [uint256(uint160(recipient)), amount]);
    token.transfer(recipient, amount);
  }
}
"""
    elif name == "coverage_vendored_include":
        circuit_source = ("main.circom", """pragma circom 2.0.0;
include "circomlib/circuits/comparators.circom";
template Main() {
  signal input recipient;
  signal input amount;
  component isZero = IsZero();
  isZero.in <== amount;
  signal mixed;
  mixed <== recipient * amount;
}
component main {public [recipient, amount]} = Main();
""")
    elif name == "coverage_prioritized_cap":
        filler = root / "zz-filler"
        filler.mkdir()
        for index in range(2501):
            (filler / f"{index:04d}.txt").write_text("inventory filler\n")
    elif name == "coverage_no_generation_recipe":
        vsource = ""

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
                extra_failures = []
                if "expected_triples" in control and output["discovery"]["triples"] != control["expected_triples"]:
                    extra_failures.append(["triples", output["discovery"]["triples"]])
                if "expected_cap_skips" in control:
                    observed = sum(item.get("reason") == "MAX_FILES_EXCEEDED" for item in output["coverage"]["skipped"])
                    if observed < control["expected_cap_skips"]:
                        extra_failures.append(["cap_skips", observed])
                if "expected_build" in control:
                    kinds = [item.get("record", {}).get("kind") for item in output["coverage"]["builds"]]
                    if control["expected_build"] not in kinds:
                        extra_failures.append(["build_kinds", kinds])
                if "expected_include_source" in control:
                    sources = [
                        include.get("source")
                        for build in output["coverage"]["builds"]
                        for include in (build.get("record") or {}).get("include_resolution", [])
                    ]
                    if control["expected_include_source"] not in sources:
                        extra_failures.append(["include_sources", sources])
                if "expected_generation_reason" in control:
                    reasons = [item.get("reason") for item in output["coverage"]["generated_verifier"]]
                    if control["expected_generation_reason"] not in reasons:
                        extra_failures.append(["generation_reasons", reasons])
                if summary["verdict"] != control["verdict"] or control["reason"] not in summary["reasons"] or extra_failures:
                    failures.append({
                        "id": control["id"], "expected": [control["verdict"], control["reason"]],
                        "observed": [summary["verdict"], summary["reasons"]],
                        "extra_failures": extra_failures,
                        "coverage": output["coverage"],
                    })
        self.assertEqual(failures, [], json.dumps(failures, indent=2))


if __name__ == "__main__":
    unittest.main()
