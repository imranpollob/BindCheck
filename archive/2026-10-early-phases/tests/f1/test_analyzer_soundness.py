"""Synthetic development controls for the analyzer review."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from bindcheck_zk.analyzer import analyze
from bindcheck_zk.p4 import SCALAR_FIELD, analyze_source, canonical_guard_positions


DISTINCT_SOURCE_KEY = """
    uint256 constant gammax1 = 1;
    uint256 constant gammax2 = 2;
    uint256 constant gammay1 = 3;
    uint256 constant gammay2 = 4;
    uint256 constant deltax1 = 5;
    uint256 constant deltax2 = 6;
    uint256 constant deltay1 = 7;
    uint256 constant deltay2 = 8;
"""


def analyze_sources(sources: dict[str, str]) -> dict:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for name, content in sources.items():
            (root / name).write_text(content, encoding="utf-8")
        output = analyze(root)
        if output["run"]["status"] != "completed":
            raise AssertionError(output["coverage"])
        return output


def guarded_verifier(name: str, method: str, size: int, visibility: str) -> str:
    return f"""
contract {name} {{
    {DISTINCT_SOURCE_KEY}
    function {method}(uint256[{size}] memory input) {visibility} returns (bool) {{
        require(input[0] < {SCALAR_FIELD});
        {'require(input[1] < ' + str(SCALAR_FIELD) + ');' if size == 2 else ''}
        return true;
    }}
}}
"""


class F1AnalyzerSoundness(unittest.TestCase):
    def test_p1_and_triple_p4_require_verifier_correspondence(self) -> None:
        output = analyze_sources({
            "main.nr": "fn main(recipient: pub Field, amount: pub Field) {}",
            "Other.sol": guarded_verifier("OtherGroth16Verifier", "verifyProof", 2, "public"),
            "Consumer.sol": """
                interface ProductionVerifier {
                    function verifyProof(bytes calldata proof, uint256[2] calldata input)
                        external returns (bool);
                }
                contract Consumer {
                    ProductionVerifier verifier; IERC20 token;
                    function submit(bytes calldata proof, uint256 recipient, uint256 amount) external {
                        require(verifier.verifyProof(proof, [recipient, amount]));
                        token.transfer(address(uint160(recipient)), amount);
                    }
                }
            """,
        })
        self.assertEqual(len(output["triples"]), 1)
        patterns = output["triples"][0]["patterns"]
        for pattern in ("P1", "P4"):
            with self.subTest(pattern=pattern):
                self.assertEqual((patterns[pattern]["verdict"], patterns[pattern]["reason"]),
                                 ("UNKNOWN", "VERIFIER_CALL_CORRESPONDENCE_UNRESOLVED"))

    def test_p4_guard_does_not_follow_an_override_or_a_bypass(self) -> None:
        for body in (
            """
            function verifyProof(uint256[1] memory input) public returns (bool) {
                return verify(input);
            }
            function verify(uint256[1] memory input) internal override returns (bool) {
                return true;
            }
            """,
            """
            function verifyProof(uint256[1] memory input) public returns (bool) {
                if (input[0] == 0) { return verify(input); }
                return true;
            }
            """,
        ):
            with self.subTest(body=body):
                output = analyze_sources({
                    "main.nr": "fn main(amount: pub Field) {}",
                    "Base.sol": guarded_verifier("BaseGroth16Verifier", "verify", 1, "internal virtual"),
                    "Wrapper.sol": 'import {BaseGroth16Verifier} from "./Base.sol";\n'
                                   "contract WrapperGroth16Verifier is BaseGroth16Verifier {" + body + "}",
                    "Consumer.sol": """
                        contract Consumer {
                            WrapperGroth16Verifier verifier; IERC20 token;
                            function submit(uint256 amount) external {
                                require(verifier.verifyProof([amount]));
                                token.transfer(msg.sender, amount);
                            }
                        }
                    """,
                })
                self.assertEqual(len(output["triples"]), 1)
                finding = output["triples"][0]["patterns"]["P4"]
                self.assertEqual((finding["verdict"], finding["reason"]),
                                 ("UNKNOWN", "INHERITED_VERIFIER_GUARD_UNRESOLVED"))

    def test_p5_guarded_dynamic_vector_requires_complete_circuit_interface(self) -> None:
        output = analyze_sources({
            "main.nr": "fn main(point: pub Gaffine) {}",
            "Verifier.sol": """
                contract Groth16Verifier {
                    uint256 constant NUMBER_OF_PUBLIC_INPUTS = 1;
                    function verifyProof(bytes calldata proof, uint256[] calldata inputs)
                        external returns (bool) { return true; }
                }
            """,
            "Consumer.sol": """
                contract Consumer {
                    Groth16Verifier verifier; IERC20 token;
                    function submit(bytes calldata proof, uint256[] calldata inputs) external {
                        require(inputs.length == 1);
                        require(verifier.verifyProof(proof, inputs));
                        token.transfer(msg.sender, inputs[0]);
                    }
                }
            """,
        })
        self.assertEqual(len(output["triples"]), 1)
        finding = output["triples"][0]["patterns"]["P5"]
        self.assertEqual((finding["verdict"], finding["reason"]),
                         ("UNKNOWN", "CIRCUIT_INTERFACE_INCOMPLETE"))

    def test_p4_yul_guard_must_visit_every_word(self) -> None:
        for start, stride in ((":= 1", "single"), ("", "double")):
            with self.subTest(start=start, stride=stride):
                # A second, individually valid increment skips every other word.
                advance = "p := add(p, 0x20)"
                if stride == "double":
                    advance += "\n p := add(p, 0x20)"
                source = f"""
                  contract GnarkPlonkVerifier {{
                    {DISTINCT_SOURCE_KEY}
                    uint256 private constant R_MOD_MINUS_ONE = {SCALAR_FIELD - 1};
                    function Verify(bytes calldata proof, uint256[] calldata public_inputs)
                        public view returns (bool) {{
                        assembly {{
                            check_inputs_size(public_inputs.length, public_inputs.offset)
                            function check_inputs_size(s, p) {{
                                for {{ let i {start} }} lt(i, s) {{ i := add(i, 1) }} {{
                                    if gt(calldataload(p), R_MOD_MINUS_ONE) {{ error_inputs_size() }}
                                    {advance}
                                }}
                            }}
                            function error_inputs_size() {{ revert(0, 0) }}
                        }}
                        return true;
                    }}
                  }}
                """
                finding = analyze_source(source, "Verifier.sol")["finding"]
                self.assertEqual((finding["verdict"], finding["reason"]),
                                 ("UNKNOWN", "PUBLIC_INPUT_CANONICALITY_GUARD_NOT_FOUND"))
                self.assertFalse(canonical_guard_positions(source)["all_positions"])
