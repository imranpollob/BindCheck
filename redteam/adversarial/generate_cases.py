#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[2]
EXPECTED = ROOT / "redteam" / "adversarial" / "expected.json"
TEMPLATE = ROOT / "baselines" / "strong" / "foundry" / "PolicyHarness.t.sol.template"


def policy_for(case: dict) -> dict:
    family = case["family"]
    policy = {
        "schema": "bindcheck-redteam.policy/v1",
        "case_id": case["id"],
        "status": "AI_AUTHORED_DEVELOPMENT_POLICY_REQUIRES_HUMAN_REVIEW",
        "protected_effect": {"kind": "balance", "recipient_role": "recipient", "amount_role": "amount"},
        "public_schema": ["recipient", "amount", "nullifier", "activeLength"],
        "required_bindings": {
            "recipient": "public_input_or_declared_commitment",
            "amount": "public_input_or_declared_commitment"
        },
        "caller_policy": "proved_identity",
        "assumptions": [
            "The verifier is sound for the pinned synthetic relation in static arms.",
            "The Foundry consumer harness deliberately replaces it with an always-true mock and cannot establish a real-proof claim."
        ]
    }
    if family in {"prefix-vs-full-array", "array-length-signal"}:
        policy["protected_effect"] = {"kind": "state_accumulator", "amount_role": "items", "multiplicity": "active_prefix"}
        policy["arrays"] = {
            "active_length_role": "activeLength",
            "consumer_must_use_active_prefix": family == "prefix-vs-full-array",
            "require_length_equality": family == "array-length-signal"
        }
    if family == "overlapping-masks":
        policy["protected_effect"] = {"kind": "state_accumulator", "amount_role": "items", "multiplicity": "at_most_once"}
        policy["masks"] = {"roles": ["maskA", "maskB"], "require_pairwise_disjoint": True}
    if family == "decoding-order":
        policy["public_schema"] = ["recipient", "amount", "nullifier", "activeLength"]
    if family == "nullifier-chain-scope":
        policy["replay"] = {"key_role": "nullifier", "required_scope": ["chainId"], "require_scalar_canonicality": True}
        policy["public_schema"] = ["chainId", "nullifier"]
    if family == "nullifier-contract-scope":
        policy["replay"] = {"key_role": "nullifier", "required_scope": ["contractAddress"], "require_scalar_canonicality": True}
        policy["public_schema"] = ["contractAddress", "nullifier"]
    if family in {"commitment-order", "commitment-fields"}:
        policy["public_schema"] = ["commitment", "nullifier", "activeLength"]
        policy["commitment"] = {
            "role": "commitment",
            "algorithm": "linear-development-encoding",
            "fields": ["recipient", "amount"],
            "order_sensitive": True
        }
    if family == "caller-identity-policy" and case["label"] == "LEGITIMATE":
        policy["caller_policy"] = "arbitrary_verified_caller"
    return policy


def circuit_for(case: dict) -> str:
    family = case["family"]
    vulnerable = case["label"] == "VULNERABLE"
    header = "pragma circom 2.1.6;\n\n"
    if family in {"nullifier-chain-scope", "nullifier-contract-scope"}:
        scope = "chainId" if family == "nullifier-chain-scope" else "contractAddress"
        expression = "secret" if vulnerable else f"secret + {scope}"
        return header + f"""template App() {{
    signal input secret;
    signal input {scope};
    signal output nullifier;
    nullifier <== {expression};
}}

component main {{public [{scope}]}} = App();
"""
    if family in {"commitment-order", "commitment-fields"}:
        if family == "commitment-order":
            expression = "amount * 1000003 + recipient" if vulnerable else "recipient * 1000003 + amount"
        else:
            expression = "recipient" if vulnerable else "recipient * 1000003 + amount"
        return header + f"""template App() {{
    signal input recipient;
    signal input amount;
    signal output commitment;
    commitment <== {expression};
}}

component main = App();
"""
    if family == "prefix-vs-full-array" or family == "array-length-signal":
        return header + """template App() {
    signal input recipient;
    signal input amount;
    signal input nullifier;
    signal input activeLength;
    signal input items[4];
    signal input enabled[4];
    signal terms[4];
    signal output digest;
    var total = 0;
    var enabledTotal = 0;
    for (var i = 0; i < 4; i++) {
        enabled[i] * (enabled[i] - 1) === 0;
        terms[i] <== items[i] * enabled[i];
        total += terms[i];
        enabledTotal += enabled[i];
    }
    enabledTotal === activeLength;
    digest <== recipient + amount + nullifier + total;
}

component main {public [recipient, amount, nullifier, activeLength]} = App();
"""
    if family == "overlapping-masks":
        disjoint = "" if vulnerable else "        maskA[i] * maskB[i] === 0;\n"
        return header + f"""template App() {{
    signal input recipient;
    signal input amount;
    signal input nullifier;
    signal input activeLength;
    signal input items[4];
    signal input maskA[4];
    signal input maskB[4];
    signal terms[4];
    signal output digest;
    var total = 0;
    for (var i = 0; i < 4; i++) {{
        maskA[i] * (maskA[i] - 1) === 0;
        maskB[i] * (maskB[i] - 1) === 0;
{disjoint}        terms[i] <== items[i] * (maskA[i] + maskB[i]);
        total += terms[i];
    }}
    digest <== recipient + amount + nullifier + activeLength + total;
}}

component main {{public [recipient, amount, nullifier, activeLength]}} = App();
"""
    alias = "    signal output publicAlias;\n    publicAlias <== recipient;\n" if family == "alias-decoding" else ""
    digest_terms = "recipient + amount + nullifier + activeLength"
    return header + f"""template App() {{
    signal input recipient;
    signal input amount;
    signal input nullifier;
    signal input activeLength;
    signal output digest;
{alias}    digest <== {digest_terms};
}}

component main {{public [recipient, amount, nullifier, activeLength]}} = App();
"""


def verifier_for(case: dict) -> str:
    family = case["family"]
    vulnerable = case["label"] == "VULNERABLE"
    ic_length = 5
    guards = ""
    if family == "replay-position-canonicality":
        position = 1 if vulnerable else 2
        guards = f"        require(input[{position}] < SNARK_SCALAR_FIELD, \"field\");\n"
    elif family == "replay-key-binding":
        guards = "        require(input[2] < SNARK_SCALAR_FIELD, \"field\");\n"
    elif family in {"nullifier-chain-scope", "nullifier-contract-scope"}:
        guards = "        require(input[1] < SNARK_SCALAR_FIELD, \"field\");\n"
    return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IVerifier {{
    function verifyProof(uint256[] calldata input) external view returns (bool);
}}

contract GeneratedVerifier is IVerifier {{
    uint256 public constant SNARK_SCALAR_FIELD = {21888242871839275222246405745257275088548364400416034343698204186575808495617};
    uint256 public constant IC_LENGTH = {ic_length};

    function verifyProof(uint256[] calldata input) external pure returns (bool) {{
{guards}        return input.length + 1 == IC_LENGTH;
    }}
}}

contract MockVerifier is IVerifier {{
    function verifyProof(uint256[] calldata) external pure returns (bool) {{
        return true;
    }}
}}
"""


def consumer_body(case: dict) -> str:
    family = case["family"]
    vulnerable = case["label"] == "VULNERABLE"
    prelude = """        require(verifier.verifyProof(publicInputs), "proof");
        address provedRecipient = address(uint160(publicInputs[0]));
        uint256 provedAmount = publicInputs[1];
        uint256 provedNullifier = publicInputs[2];
"""
    if family == "effect-recipient":
        return prelude + ("        _mint(recipient, provedAmount);\n" if vulnerable else "        _mint(provedRecipient, provedAmount);\n")
    if family == "effect-amount":
        return prelude + ("        _mint(provedRecipient, amount);\n" if vulnerable else "        _mint(provedRecipient, provedAmount);\n")
    if family == "native-call-value":
        value = "amount" if vulnerable else "provedAmount"
        return prelude + f"        (bool ok,) = payable(provedRecipient).call{{value: {value}}}(\"\");\n        require(ok, \"call\");\n"
    if family == "burn-owner":
        owner = "recipient" if vulnerable else "provedRecipient"
        return prelude + f"        _burn({owner}, provedAmount);\n"
    if family == "state-write":
        value = "amount" if vulnerable else "provedAmount"
        return prelude + f"        balances[provedRecipient] += {value};\n"
    if family == "guard-dominance-irrelevant-branch":
        if vulnerable:
            return prelude + "        if (recipient == provedRecipient) { observed += 1; }\n        _mint(recipient, provedAmount);\n"
        return prelude + "        require(recipient == provedRecipient, \"recipient\");\n        _mint(recipient, provedAmount);\n"
    if family == "guard-dominance-after-effect":
        if vulnerable:
            return prelude + "        _mint(recipient, provedAmount);\n        require(recipient == provedRecipient, \"recipient\");\n"
        return prelude + "        require(recipient == provedRecipient, \"recipient\");\n        _mint(recipient, provedAmount);\n"
    if family == "replay-key-binding":
        key = "replayKey" if vulnerable else "provedNullifier"
        return prelude + f"        require(!used[{key}], \"used\");\n        used[{key}] = true;\n"
    if family == "replay-position-canonicality":
        return prelude + "        require(!used[provedNullifier], \"used\");\n        used[provedNullifier] = true;\n"
    if family == "verifier-arity":
        length = 3 if vulnerable else 4
        return f"""        uint256[] memory verifierInputs = new uint256[]({length});
        for (uint256 i = 0; i < {length}; i++) {{ verifierInputs[i] = publicInputs[i]; }}
        require(verifier.verifyProof(verifierInputs), "proof");
        address provedRecipient = address(uint160(publicInputs[0]));
        uint256 provedAmount = publicInputs[1];
        _mint(provedRecipient, provedAmount);
"""
    if family == "prefix-vs-full-array":
        extent = "items.length" if vulnerable else "activeLength"
        return prelude + f"        for (uint256 i = 0; i < {extent}; i++) {{ observed += items[i]; }}\n"
    if family == "overlapping-masks":
        return prelude + "        for (uint256 i = 0; i < items.length; i++) { observed += items[i] * (maskA[i] + maskB[i]); }\n"
    if family == "decoding-order":
        recipient_index, amount_index = ((1, 0) if vulnerable else (0, 1))
        return f"""        require(verifier.verifyProof(publicInputs), "proof");
        address decodedRecipient = address(uint160(publicInputs[{recipient_index}]));
        uint256 decodedAmount = publicInputs[{amount_index}];
        _mint(decodedRecipient, decodedAmount);
"""
    if family in {"nullifier-chain-scope", "nullifier-contract-scope"}:
        return """        require(verifier.verifyProof(publicInputs), "proof");
        uint256 provedNullifier = publicInputs[1];
        require(!used[provedNullifier], "used");
        used[provedNullifier] = true;
"""
    if family in {"commitment-order", "commitment-fields"}:
        return """        uint256 commitment = commit2(uint256(uint160(recipient)), amount);
        require(publicInputs[0] == commitment, "commitment");
        require(verifier.verifyProof(publicInputs), "proof");
        _mint(recipient, amount);
"""
    if family == "array-length-signal":
        guard = "" if vulnerable else "        require(items.length == activeLength, \"length\");\n"
        return prelude + guard + "        for (uint256 i = 0; i < items.length; i++) { observed += items[i]; }\n"
    if family == "alias-decoding":
        if vulnerable:
            return prelude + "        address decodedAlias = recipient;\n        _mint(decodedAlias, provedAmount);\n"
        return prelude + "        address decodedAlias = recipient;\n        require(decodedAlias == provedRecipient, \"alias\");\n        _mint(decodedAlias, provedAmount);\n"
    if family == "caller-identity-policy":
        return prelude + "        _mint(msg.sender, provedAmount);\n"
    raise ValueError(f"unhandled family {family}")


def consumer_for(case: dict) -> str:
    body = consumer_body(case)
    return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./Verifier.sol";

contract Consumer {{
    IVerifier public immutable verifier;
    mapping(address => uint256) public balances;
    mapping(uint256 => bool) public used;
    uint256 public observed;

    constructor(IVerifier verifier_) {{ verifier = verifier_; }}

    function execute(
        uint256[] memory publicInputs,
        address recipient,
        uint256 amount,
        uint256 replayKey,
        uint256[] memory items,
        uint256 activeLength,
        uint256[] memory maskA,
        uint256[] memory maskB
    ) public {{
{body}    }}

    function commit2(uint256 first, uint256 second) public pure returns (uint256) {{
        return first * 1000003 + second;
    }}

    function _mint(address recipient, uint256 amount) internal {{ balances[recipient] += amount; }}
    function _burn(address owner, uint256 amount) internal {{ balances[owner] -= amount; }}
}}
"""


def assertion_for(policy: dict) -> str:
    caller_policy = policy.get("caller_policy")
    kind = policy.get("protected_effect", {}).get("kind")
    if caller_policy == "proved_identity" and kind == "balance":
        return 'require(consumer.balances(address(this)) == 0, "unauthorized caller effect");'
    if kind == "state_accumulator":
        return 'require(consumer.observed() <= 7, "unauthorized multiplicity or extent");'
    return "// Policy permits this caller/effect shape; the harness records execution only."


def main() -> int:
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    harness_template = TEMPLATE.read_text(encoding="utf-8")
    for case in expected["cases"]:
        directory = ROOT / "redteam" / "adversarial" / case["id"]
        (directory / "test").mkdir(parents=True, exist_ok=True)
        policy = policy_for(case)
        (directory / "policy.json").write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (directory / "circuit.circom").write_text(circuit_for(case), encoding="utf-8")
        (directory / "Verifier.sol").write_text(verifier_for(case), encoding="utf-8")
        (directory / "Consumer.sol").write_text(consumer_for(case), encoding="utf-8")
        harness = harness_template.replace("__POLICY_ASSERTION__", assertion_for(policy))
        (directory / "test" / "PolicyHarness.t.sol").write_text(harness, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
