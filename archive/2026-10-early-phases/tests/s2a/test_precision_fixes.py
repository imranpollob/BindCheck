"""Development-only regressions for the S2a false-positive root causes."""
from __future__ import annotations

# The minimized source shapes below were derived from these ALLOWED Set H
# packets, inspected at their pinned revisions (the assertions encode the
# research-contract semantics, not the cards' expected labels):
# W0007 0xSY3/polkadot-dust-protocol@7f0f532b; W0102
# wannabehero/ethglobal-lisbon@50efb8f2; W0220
# bunsenstraat/chainlink-workshop@9ded99d1; W0245
# Turupawn/zkBenchmark@ffef1b6d; W0294 Ambesh69/predacy@ff025ffb;
# W0461 Punith-KK/Kira@8a8ed58e; W0658 PhaseMirror/The-Foundry@c7187410;
# W0662 eugenioclrc/MercadoBarrani@86f646b5; W0672
# 0xbri3t/Privacy-Vaults@d3735bff; W0691 timimm/zk-writeups@f6e99f57;
# W0725 oguzutku1745/goodLane@24d1d767; W0765 JYugandhara/axiom@dae2e93d.

import pathlib
import tempfile
import unittest

from bindcheck_zk.analyzer import (
    Source,
    _contract_identity,
    _propagate_inherited_verifier_guards,
    _semantic_excluded,
    _self_balance_debit_bound,
    _state_derived,
    analyze,
    classify_verifier,
    load_config,
)
from bindcheck_zk.circuits import parse_circom, parse_noir
from bindcheck_zk.p4 import SCALAR_FIELD, canonical_guard
from bindcheck_zk.solidity import Call, effect_calls, effect_roles, public_vector, verifier_declarations


class S2aPrecisionFixes(unittest.TestCase):
    def test_interface_prefix_normalization_preserves_identity_names(self) -> None:
        self.assertEqual(_contract_identity("IIdentityVerifier"), _contract_identity("IdentityVerifier"))

    def test_comments_cannot_create_public_vector_assignments(self) -> None:
        body = """
uint256[2] memory input;
// input[0] = fake;
input[0] = real;
/* input[1] = fakeAgain; */
verifier.verifyProof(proof, input);
"""
        vector = public_vector(body, Call("verifyProof", "verifier", ["proof", "input"], 5, 100))
        self.assertEqual(vector.items, ["real", "<unresolved:input[1]>"])

    def test_proof_array_is_not_mistaken_for_public_inputs(self) -> None:
        body = "semaphore.verifyProof(groupId, root, signal, nullifier, externalNullifier, proof);"
        vector = public_vector(
            body,
            Call("verifyProof", "semaphore", ["groupId", "root", "signal", "nullifier", "externalNullifier", "proof"], 1, 0),
        )
        self.assertIsNone(vector.declared_count)
        self.assertIn("proof-argument-not-public-vector", vector.unresolved)

    def test_honk_layout_excludes_pairing_point_words(self) -> None:
        source = """
contract UltraHonkVerifier {
 uint256 constant NUMBER_OF_PUBLIC_INPUTS = 20;
 uint256 constant PAIRING_POINTS_SIZE = 16;
 function verify(bytes calldata proof, bytes32[] calldata publicInputs) external view returns (bool) {
   if (publicInputs.length != vk.publicInputsSize - PAIRING_POINTS_SIZE) revert();
   return true;
 }
}
"""
        declarations = verifier_declarations(source)
        layout = next(item for item in declarations if item["name"] == "constant")
        self.assertEqual((layout["arity"], layout["reserved_layout_words"]), (4, 16))

    def test_honk_layout_excludes_explicit_aggregation_words(self) -> None:
        source = """
uint256 constant NUMBER_OF_PUBLIC_INPUTS = 14;
uint256 constant PAIRING_POINTS_SIZE = 8;
uint256 constant AGGREGATION_OBJECT_SIZE = 4;
contract HonkVerifier {
 function verify(bytes calldata, bytes32[] calldata publicInputs) external view returns (bool) {
  if (publicInputs.length != NUMBER_OF_PUBLIC_INPUTS - PAIRING_POINTS_SIZE - AGGREGATION_OBJECT_SIZE) revert();
  return true;
 }
}
"""
        layout = next(item for item in verifier_declarations(source) if item["name"] == "constant")
        self.assertEqual((layout["arity"], layout["reserved_layout_words"]), (2, 12))

    def test_honk_wrapper_resolves_imported_arity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            (root / "keys").mkdir()
            (root / "keys" / "ExampleVerificationKey.sol").write_text(
                "uint256 constant NUMBER_OF_PUBLIC_INPUTS = 19;\n",
                encoding="utf-8",
            )
            (root / "ExampleHonkVerifier.sol").write_text("""
import "./keys/ExampleVerificationKey.sol";
contract ExampleHonkVerifier is BaseHonkVerifier(NUMBER_OF_PUBLIC_INPUTS) {}
""", encoding="utf-8")
            (root / "main.nr").write_text(
                "fn main(inputs: pub [Field; 19]) {}\n",
                encoding="utf-8",
            )
            (root / "Consumer.sol").write_text("""
interface IExampleHonkVerifier { function verify(bytes calldata, bytes32[] calldata) external returns (bool); }
contract Consumer { IExampleHonkVerifier verifier; IERC20 token;
 function submit(bytes calldata proof, bytes32[] calldata inputs) external {
  verifier.verify(proof, inputs); token.transfer(msg.sender, 1);
 }}
""", encoding="utf-8")
            output = analyze(root)
            self.assertTrue(any(
                item["verifier"]["path"] == "ExampleHonkVerifier.sol"
                for item in output["triples"]
            ))

    def test_circom_multidimensional_outputs_are_flattened_first(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            source = root / "main.circom"
            source.write_text("""
template Main() { signal input h[2]; signal output D[2][2][4]; }
component main {public [h]} = Main();
""", encoding="utf-8")
            circuit = parse_circom(source, root)
            self.assertEqual(circuit.public_count, 18)
            self.assertEqual(circuit.public_order[0], "D[0][0][0]")
            self.assertEqual(circuit.public_order[-1], "h[1]")

    def test_noir_composite_public_type_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            source = root / "main.nr"
            source.write_text("fn main(points: pub [Gaffine; 10]) {}\n", encoding="utf-8")
            circuit = parse_noir(source, root)
            self.assertIsNone(circuit.public_count)
            self.assertFalse(circuit.order_complete)

    def test_gnark_full_input_loop_is_a_canonical_guard(self) -> None:
        source = f"""
uint256 private constant R_MOD_MINUS_ONE = {SCALAR_FIELD - 1};
function Verify(bytes calldata proof, uint256[] calldata public_inputs) public view returns (bool) {{
 assembly {{
  check_inputs_size(public_inputs.length, public_inputs.offset)
  function check_inputs_size(s, p) {{
   for {{ let i }} lt(i, s) {{ i := add(i, 1) }} {{
    if gt(calldataload(p), R_MOD_MINUS_ONE) {{ error_inputs_size() }}
    p := add(p, 0x20)
   }}
  }}
 }}
 return true;
}}
"""
        self.assertTrue(canonical_guard(source, {0, 1, 2}))

    def test_non_asset_transfer_method_is_not_a_protected_effect(self) -> None:
        source = "contract C { TerritoryMap territoryMap; }"
        call = effect_calls("territoryMap.transfer(commitment, civId, 0);", source)[0]
        self.assertEqual(effect_roles(call, source), [])
        unknown = effect_calls("paymentContract.transfer(recipient, amount);", "")[0]
        self.assertEqual(effect_roles(unknown, ""), [("recipient", "recipient"), ("amount", "amount")])

    def test_state_selected_values_are_not_treated_as_caller_values(self) -> None:
        source = "contract C { mapping(uint256 => Batch) batches; }"
        self.assertTrue(_state_derived("(batches[batchId]).yesGap", source))

    def test_exact_self_balance_debit_is_locally_authorized(self) -> None:
        body = "require(amount <= balances[msg.sender]); balances[msg.sender] -= amount;"
        write = next(call for call in effect_calls(body, "mapping(address => uint256) balances;") if call.name == "__state_write__")
        self.assertTrue(_self_balance_debit_bound(write, "msg.sender", body))
        self.assertTrue(_self_balance_debit_bound(write, "amount", body))

    def test_ctf_and_writeup_sources_are_semantically_excluded(self) -> None:
        config = load_config()
        self.assertTrue(_semantic_excluded("docs/crypto/zkCTF/day2/Mixer/Verifier.sol", config))
        self.assertTrue(_semantic_excluded("writeups/example/Verifier.sol", config))

    def test_semantic_exclusion_is_config_driven_and_reported(self) -> None:
        config = load_config()
        self.assertIn("ctf", config["semantic_excluded_directories"])
        self.assertIn("writeup", config["semantic_excluded_directories"])
        self.assertIn("tutorial", config["semantic_excluded_directories"])
        self.assertIn("example", config["semantic_excluded_directories"])

    def test_semantically_excluded_file_never_produces_a_safe_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            (root / "main.nr").write_text("fn main(nullifier: pub Field) {}\n", encoding="utf-8")
            (root / "Verifier.sol").write_text(f"""
contract Groth16Verifier {{ function verifyProof(bytes memory, uint256[1] memory input) public returns(bool) {{
 require(input[0] < {SCALAR_FIELD}); return true;
}} }}
""", encoding="utf-8")
            consumer = """
contract Consumer { Groth16Verifier verifier; mapping(uint256 => bool) spent; IERC20 token;
 function submit(bytes memory proof, uint256 nullifier) public {
  require(!spent[nullifier]); verifier.verifyProof(proof, [nullifier]);
  spent[nullifier] = true; token.transfer(msg.sender, 1);
 }}
"""
            (root / "ctf").mkdir()
            (root / "ctf" / "Consumer.sol").write_text(consumer, encoding="utf-8")
            (root / "Application.sol").write_text(
                consumer.replace("contract Consumer", "contract Application"), encoding="utf-8"
            )
            output = analyze(root)
            consumer_paths = {item["consumer"]["path"] for item in output["triples"]}
            finding_paths = {
                (item.get("location") or {}).get("path", "")
                for triple in output["triples"]
                for item in triple["patterns"].values()
            }
            self.assertEqual(consumer_paths, {"Application.sol"})
            self.assertFalse(any(path.startswith("ctf/") for path in finding_paths))
            self.assertEqual(output["coverage"]["semantic_excluded_count"], 1)
            self.assertEqual(output["coverage"]["semantic_excluded_paths"], ["ctf/Consumer.sol"])
            self.assertFalse(any(
                finding["verdict"] == "VERIFIED_WITHIN_SCOPE"
                for triple in output["triples"]
                if triple["consumer"]["path"].startswith("ctf/")
                for finding in triple["patterns"].values()
            ))

    def test_inherited_verified_guard_propagates_to_wrapper(self) -> None:
        base_source = Source(
            pathlib.Path("Base.sol"), "Base.sol", f"""
contract BaseGroth16Verifier {{
    uint256 constant gammax1 = 1;
    uint256 constant gammax2 = 2;
    uint256 constant gammay1 = 3;
    uint256 constant gammay2 = 4;
    uint256 constant deltax1 = 5;
    uint256 constant deltax2 = 6;
    uint256 constant deltay1 = 7;
    uint256 constant deltay2 = 8;

    function verify(uint256[1] memory input) internal virtual returns (bool) {{
        require(input[0] < {SCALAR_FIELD});
        return true;
    }}
}}
""", "a" * 64,
        )
        wrapper_source = Source(
            pathlib.Path("Wrapper.sol"), "Wrapper.sol", """
import {BaseGroth16Verifier} from "./Base.sol";
contract WrapperGroth16Verifier is BaseGroth16Verifier {
    function verifyProof(uint256[1] memory input) public returns (bool) {
        return verify(input);
    }
}
""",
            "b" * 64,
        )
        base = classify_verifier(base_source)
        wrapper = classify_verifier(wrapper_source)
        self.assertEqual(base.p4["finding"]["verdict"], "VERIFIED_WITHIN_SCOPE")
        self.assertEqual(wrapper.p4["finding"]["verdict"], "UNKNOWN")
        _propagate_inherited_verifier_guards([base, wrapper])
        self.assertEqual(wrapper.p4["finding"]["verdict"], "VERIFIED_WITHIN_SCOPE")

    def test_checkfield_guard_preserves_p3_verified_case(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            (root / "main.nr").write_text("fn main(nullifier: pub Field) {}\n", encoding="utf-8")
            (root / "Verifier.sol").write_text(f"""
contract Groth16Verifier {{ function verifyProof(bytes memory, uint256[1] memory input) public returns(bool) {{
 require(input[0] < {SCALAR_FIELD}); return true;
}} }}
""", encoding="utf-8")
            (root / "Consumer.sol").write_text("""
contract Consumer { Groth16Verifier verifier; mapping(uint256 => bool) spent; IERC20 token;
 function submit(bytes memory proof, uint256 nullifier) public {
  require(!spent[nullifier]); verifier.verifyProof(proof, [nullifier]);
  spent[nullifier] = true; token.transfer(msg.sender, 1);
 }}
""", encoding="utf-8")
            output = analyze(root)
            p3 = next(item["patterns"]["P3"] for item in output["triples"])
            self.assertEqual(p3["verdict"], "VERIFIED_WITHIN_SCOPE")

    def test_multiple_verifier_calls_use_their_own_vectors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            (root / "two.nr").write_text("fn main(a: pub Field, b: pub Field) {}\n", encoding="utf-8")
            (root / "three.nr").write_text("fn main(a: pub Field, b: pub Field, c: pub Field) {}\n", encoding="utf-8")
            (root / "TwoVerifier.sol").write_text(
                "contract TwoVerifier { function verifyProof(bytes memory, uint256[2] memory) public returns(bool){return true;} }",
                encoding="utf-8",
            )
            (root / "ThreeVerifier.sol").write_text(
                "contract ThreeVerifier { function verifyProof(bytes memory, uint256[3] memory) public returns(bool){return true;} }",
                encoding="utf-8",
            )
            (root / "Consumer.sol").write_text("""
contract Consumer { TwoVerifier twoVerifier; ThreeVerifier threeVerifier; IERC20 token;
 function submit(bytes memory p, uint256 a, uint256 b, uint256 c) public {
  twoVerifier.verifyProof(p, [a,b]); threeVerifier.verifyProof(p, [a,b,c]);
  token.transfer(msg.sender, a);
 }}
""", encoding="utf-8")
            output = analyze(root)
            expected = {
                "TwoVerifier.sol": ["a", "b"],
                "ThreeVerifier.sol": ["a", "b", "c"],
            }
            self.assertEqual(len(output["triples"]), len(expected))
            self.assertEqual({item["verifier"]["path"] for item in output["triples"]}, set(expected))
            for item in output["triples"]:
                with self.subTest(verifier=item["verifier"]["path"]):
                    p5 = item["patterns"]["P5"]
                    facts = {fact["name"]: fact["value"] for fact in p5["facts"]}
                    self.assertEqual((p5["verdict"], p5["reason"]),
                                     ("VERIFIED_WITHIN_SCOPE", "PUBLIC_INPUT_COUNT_AND_ORDER_MATCH"))
                    self.assertEqual(facts["consumer_order"], expected[item["verifier"]["path"]])

    def test_specific_receiver_type_rejects_unrelated_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            (root / "main.nr").write_text(
                "fn main(amount: pub Field, root: pub Field, nonce: pub Field) {}\n",
                encoding="utf-8",
            )
            (root / "Wrong.sol").write_text(
                "contract TutorialVerifier { function verifyProof(bytes memory p, uint256[1] memory i) public returns(bool){return true;} }",
                encoding="utf-8",
            )
            (root / "Consumer.sol").write_text("""
interface ProductionVerifier { function verifyProof(bytes calldata, uint256[3] calldata) external returns(bool); }
contract Consumer { ProductionVerifier verifier; IERC20 token;
 function submit(bytes calldata proof, uint256 amount, uint256 root, uint256 nonce) external {
  verifier.verifyProof(proof, [amount, root, nonce]); token.transfer(msg.sender, amount);
 }}
""", encoding="utf-8")
            output = analyze(root)
            self.assertTrue(output["triples"])
            self.assertTrue(all(
                item["patterns"]["P5"]["reason"] == "VERIFIER_CALL_CORRESPONDENCE_UNRESOLVED"
                for item in output["triples"]
            ))

    def test_two_p5_true_mismatches_remain_violations(self) -> None:
        for supplied in (1, 3):
            with self.subTest(supplied=supplied), tempfile.TemporaryDirectory() as temporary:
                root = pathlib.Path(temporary)
                public = ", ".join(f"x{index}: pub Field" for index in range(2))
                values = ", ".join(f"x{index}" for index in range(supplied))
                params = ", ".join(f"uint256 x{index}" for index in range(supplied))
                (root / "main.nr").write_text(f"fn main({public}) {{}}\n", encoding="utf-8")
                (root / "Verifier.sol").write_text("""
contract Groth16Verifier { function verifyProof(bytes memory, uint256[2] memory input) public returns(bool) { return input[0] < 2; } }
""", encoding="utf-8")
                (root / "Consumer.sol").write_text(f"""
contract Consumer {{ Groth16Verifier verifier; IERC20 token;
 function submit(bytes memory proof, {params}) public {{
  verifier.verifyProof(proof, [{values}]); token.transfer(msg.sender, x0);
 }} }}
""", encoding="utf-8")
                output = analyze(root)
                p5 = next(item["patterns"]["P5"] for item in output["triples"])
                self.assertEqual((p5["verdict"], p5["reason"]), ("VIOLATION", "PUBLIC_INPUT_COUNT_MISMATCH"))


if __name__ == "__main__":
    unittest.main()
