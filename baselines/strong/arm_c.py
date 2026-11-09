from __future__ import annotations

import pathlib
import re
import time
from typing import Any

from .common import envelope, finding, load_policy, utc_now


def _texts(root: pathlib.Path, suffix: str) -> list[tuple[str, str]]:
    excluded = {".git", "node_modules", "vendor", "target", "build", "dist", "out", "artifacts", "cache"}
    output: list[tuple[str, str]] = []
    for path in sorted(root.rglob(f"*{suffix}")):
        if any(part in excluded for part in path.parts) or not path.is_file() or path.stat().st_size > 5_000_000:
            continue
        output.append((path.relative_to(root).as_posix(), path.read_text(encoding="utf-8", errors="replace")))
    return output


def _public_order(circuits: list[tuple[str, str]]) -> list[str] | None:
    for _, text in circuits:
        match = re.search(r"component\s+main\s*\{\s*public\s*\[([^\]]+)\]", text, re.S)
        if match:
            return [item.strip() for item in match.group(1).split(",") if item.strip()]
    return None


def _consumer_decoding(solidity: list[tuple[str, str]], roles: list[str]) -> dict[str, int]:
    decoded: dict[str, int] = {}
    for _, text in solidity:
        for role in roles:
            patterns = [
                rf"\b[A-Za-z_]*{re.escape(role)}[A-Za-z_]*\s*=\s*(?:address\s*\(\s*uint160\s*\(\s*)?(?:publicInputs?|input)\s*\[\s*(\d+)\s*\]",
                rf"\b{re.escape(role)}\s*=\s*(?:publicInputs?|input)\s*\[\s*(\d+)\s*\]",
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.I | re.S)
                if match:
                    decoded[role] = int(match.group(1))
                    break
    return decoded


def _commitment_orders(solidity: list[tuple[str, str]], circuits: list[tuple[str, str]]) -> tuple[list[str] | None, list[str] | None]:
    contract_order: list[str] | None = None
    circuit_order: list[str] | None = None
    for _, text in solidity:
        match = re.search(r"\bcommit2\s*\(\s*([^,]+)\s*,\s*([^)]+)\)", text, re.I)
        if match:
            contract_order = [_role_name(match.group(1)), _role_name(match.group(2))]
            break
        match = re.search(r"keccak256\s*\(\s*abi\.encode(?:Packed)?\s*\(([^)]+)\)\s*\)", text, re.I | re.S)
        if match:
            contract_order = [_role_name(item) for item in match.group(1).split(",")]
            break
    for _, text in circuits:
        match = re.search(r"\bcommitment\s*<==\s*([A-Za-z_]\w*)\s*\*\s*1000003\s*\+\s*([A-Za-z_]\w*)", text)
        if match:
            circuit_order = [_role_name(match.group(1)), _role_name(match.group(2))]
            break
        match = re.search(r"\bcommitment\s*<==\s*([A-Za-z_]\w*)\s*;", text)
        if match:
            circuit_order = [_role_name(match.group(1))]
            break
    return contract_order, circuit_order


def _role_name(expression: str) -> str:
    lowered = expression.lower()
    for role in ("recipient", "amount", "identity", "nullifier", "chainid", "contractaddress", "activelength"):
        if role in lowered:
            return role
    tokens = re.findall(r"[A-Za-z_]\w*", expression)
    return tokens[-1].lower() if tokens else expression.strip().lower()


def _nullifier_expression(circuits: list[tuple[str, str]]) -> str | None:
    for _, text in circuits:
        match = re.search(r"\bnullifier\s*<==\s*([^;]+);", text)
        if match:
            return match.group(1)
    return None


def _has_array_length_guard(solidity: list[tuple[str, str]], length_role: str) -> bool:
    for _, text in solidity:
        if re.search(rf"require\s*\(\s*items\.length\s*==\s*{re.escape(length_role)}\b", text):
            return True
        if re.search(rf"require\s*\(\s*{re.escape(length_role)}\s*==\s*items\.length\b", text):
            return True
    return False


def _consumer_loop_extents(solidity: list[tuple[str, str]]) -> list[str]:
    extents: list[str] = []
    for _, text in solidity:
        extents.extend(match.group(1).strip() for match in re.finditer(r"for\s*\([^;]*;\s*[^<]+<\s*([^;]+);", text))
    return extents


def _mask_disjoint(circuits: list[tuple[str, str]]) -> bool:
    return any(re.search(r"maskA\s*\[.*?\]\s*\*\s*maskB\s*\[.*?\]\s*===\s*0", text, re.S) for _, text in circuits)


def _policy_joins(
    policy: dict[str, Any],
    solidity: list[tuple[str, str]],
    circuits: list[tuple[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, Any], set[str]]:
    findings: list[dict[str, Any]] = []
    suppress_a: set[str] = set()
    facts: dict[str, Any] = {}
    public_schema = policy.get("public_schema", [])
    circuit_order = _public_order(circuits)
    decoding = _consumer_decoding(solidity, public_schema)
    facts["policy_public_schema"] = public_schema
    facts["circuit_public_order"] = circuit_order
    facts["consumer_decoding"] = decoding
    if public_schema and circuit_order:
        for role, index in decoding.items():
            if role in circuit_order and circuit_order.index(role) != index:
                findings.append(finding(
                    "C_PUBLIC_INPUT_DECODING_MISMATCH",
                    "The consumer decodes a semantic role from a different position than the circuit public order.",
                    facts={"role": role, "consumer_index": index, "circuit_index": circuit_order.index(role)},
                    source="composition-join",
                ))
                break
    arrays = policy.get("arrays") or {}
    if arrays:
        role = arrays.get("active_length_role", "activeLength")
        extents = _consumer_loop_extents(solidity)
        facts["consumer_loop_extents"] = extents
        if arrays.get("consumer_must_use_active_prefix") and any(".length" in extent for extent in extents):
            findings.append(finding(
                "C_ARRAY_EXTENT_MISMATCH",
                "The consumer iterates a full array although policy requires the proof-bound active prefix.",
                facts={"required_extent": role, "observed_extents": extents}, source="composition-join",
            ))
        if arrays.get("require_length_equality") and not _has_array_length_guard(solidity, role):
            findings.append(finding(
                "C_ARRAY_LENGTH_UNBOUND",
                "The consumer array length lacks a dominating equality to the proof length role.",
                facts={"length_role": role}, source="composition-join",
            ))
    masks = policy.get("masks") or {}
    if masks.get("require_pairwise_disjoint") and not _mask_disjoint(circuits):
        findings.append(finding(
            "C_MASKS_OVERLAP",
            "The producer lacks the policy-required pairwise-disjoint mask constraint.",
            facts={"mask_roles": masks.get("roles", ["maskA", "maskB"])}, source="composition-join",
        ))
    replay = policy.get("replay") or {}
    nullifier_expression = _nullifier_expression(circuits)
    facts["nullifier_expression"] = nullifier_expression
    if nullifier_expression:
        for scope in replay.get("required_scope", []):
            normalized = scope.replace("_", "").lower()
            if normalized not in nullifier_expression.replace("_", "").lower():
                code = "C_NULLIFIER_SCOPE_MISSING_CHAIN" if "chain" in normalized else "C_NULLIFIER_SCOPE_MISSING_CONTRACT"
                findings.append(finding(
                    code,
                    "The proof-bound nullifier omits a policy-required replay domain.",
                    facts={"required_scope": scope, "expression": nullifier_expression}, source="composition-join",
                ))
    commitment = policy.get("commitment") or {}
    if commitment:
        contract_order, producer_order = _commitment_orders(solidity, circuits)
        expected_order = [item.lower() for item in commitment.get("fields", [])]
        facts["commitment"] = {
            "expected_order": expected_order,
            "contract_order": contract_order,
            "producer_order": producer_order,
        }
        if producer_order is not None and any(field not in producer_order for field in expected_order):
            findings.append(finding(
                "C_COMMITMENT_FIELD_MISSING",
                "The producer commitment omits a policy-required protected-effect field.",
                facts=facts["commitment"], source="composition-join",
            ))
        elif contract_order != expected_order or producer_order != expected_order:
            findings.append(finding(
                "C_COMMITMENT_ENCODING_MISMATCH",
                "Consumer and producer commitment preimage order disagree with the declared encoding.",
                facts=facts["commitment"], source="composition-join",
            ))
        else:
            if "recipient" in expected_order:
                suppress_a.update({"A_EFFECT_RECIPIENT_UNBOUND", "A_EFFECT_IDENTITY_UNBOUND"})
            if "amount" in expected_order:
                suppress_a.update({"A_EFFECT_AMOUNT_UNBOUND", "A_STATE_WRITE_VALUE_UNBOUND", "A_CALL_VALUE_UNBOUND"})
    if policy.get("caller_policy") == "arbitrary_verified_caller":
        suppress_a.update({"A_CALLER_NOT_PROVED_IDENTITY", "A_EFFECT_RECIPIENT_UNBOUND"})
    return findings, facts, suppress_a


def _name_heuristic_joins(
    solidity: list[tuple[str, str]],
    circuits: list[tuple[str, str]],
    a_findings: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], set[str], dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    suppress: set[str] = set()
    solidity_text = "\n".join(text for _, text in solidity)
    circuit_text = "\n".join(text for _, text in circuits)
    facts: dict[str, Any] = {}
    if "activeLength" in circuit_text:
        extents = _consumer_loop_extents(solidity)
        facts["consumer_loop_extents"] = extents
        if any(".length" in extent for extent in extents):
            findings.append(finding(
                "C_ARRAY_EXTENT_MISMATCH",
                "A circuit active-length role coexists with a consumer full-array loop.",
                facts={"observed_extents": extents}, source="name-composition-heuristic",
            ))
    for item in a_findings:
        role = item.get("facts", {}).get("role")
        expression = item.get("facts", {}).get("expression", "")
        token = _role_name(expression)
        if role in {"recipient", "amount", "state_value", "call_value"} and token and token in circuit_text.lower():
            contract_commitment = bool(re.search(rf"(?:keccak256|commit2)\s*\([^;)]*\b{re.escape(token)}\b", solidity_text, re.I))
            circuit_commitment = bool(re.search(rf"\bcommitment\b[^;]*\b{re.escape(token)}\b", circuit_text, re.I))
            if contract_commitment and circuit_commitment:
                suppress.add(item["code"])
                facts.setdefault("commitment_name_matches", []).append(token)
    return findings, suppress, facts


def analyze_arm_c(
    root: pathlib.Path,
    output_dir: pathlib.Path,
    arm_a: dict[str, Any],
    arm_b: dict[str, Any],
) -> dict[str, Any]:
    del output_dir
    started_utc = utc_now()
    started = time.monotonic()
    root = root.resolve()
    policy = load_policy(root)
    solidity = _texts(root, ".sol")
    circuits = _texts(root, ".circom")
    a_findings = list(arm_a.get("result", {}).get("findings", []))
    if policy:
        join_findings, join_facts, suppress = _policy_joins(policy, solidity, circuits)
        policy_status = "loaded"
    else:
        join_findings, suppress, join_facts = _name_heuristic_joins(solidity, circuits, a_findings)
        policy_status = "absent-name-heuristics-only"
    retained_a = [item for item in a_findings if item.get("code") not in suppress]
    findings = [*retained_a, *join_findings]
    a_verdict = arm_a.get("result", {}).get("verdict", "UNKNOWN")
    if findings:
        verdict = "VIOLATION"
    elif policy and solidity and circuits:
        verdict = "VERIFIED_WITHIN_SCOPE"
    elif a_verdict == "VERIFIED_WITHIN_SCOPE":
        verdict = "VERIFIED_WITHIN_SCOPE"
    else:
        verdict = "UNKNOWN"
    run_status = "completed" if solidity else "UNKNOWN"
    return envelope(
        "C", root,
        started_utc=started_utc,
        elapsed_seconds=time.monotonic() - started,
        run_status=run_status,
        findings=findings,
        verdict=verdict,
        coverage={
            "arm_a_status": arm_a.get("run", {}).get("status"),
            "arm_b_status": arm_b.get("run", {}).get("status"),
            "policy_status": policy_status,
            "solidity_files": len(solidity),
            "circuit_files": len(circuits),
            "suppressed_arm_a_codes": sorted(suppress),
            "join_facts": join_facts,
        },
        native={
            "arm_a_finding_codes": [item.get("code") for item in a_findings],
            "arm_b_native_signal_codes": [item.get("code") for item in arm_b.get("native", {}).get("signals", [])],
        },
        limitations=[
            "Arm C is a union plus name, position, length, mask, scope, and declared-commitment joins; it does not solve circuit constraints.",
            "Policy files state authorization roles and transformations but are not implementation facts or expected verdicts.",
            "Without a policy, commitment suppression is a name-occurrence heuristic and can be unsound.",
            "A VERIFIED_WITHIN_SCOPE result is limited to the recovered policy roles and supported syntactic forms.",
        ],
        fatal_reason=None if solidity else "NO_SOLIDITY_INPUT",
    )
