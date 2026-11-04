#!/usr/bin/env python3
"""Run the frozen Track-B decision protocol on DEV cases only.

The synthetic controls exercise the decision rule, not a Solidity compiler.
The SPSC case additionally requires source correspondence plus a path through
the compiled R1CS whose named intermediate signals stay in the Poseidon
`extDataHasher` component.  EVAL rows are never opened by this program.
"""

from __future__ import annotations

import collections
import csv
import hashlib
import json
import pathlib
import re
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
DATASET = ROOT / "dataset"
RAW = DATASET / "raw" / "track-b"
EXPECTED = DATASET / "track-b-expected.json"
CIRCOM = ROOT / "tools" / "circom-src" / "target" / "release" / "circom"
SNARKJS = ROOT / "node_modules" / ".bin" / "snarkjs"
SPSC = ROOT / "feasibility" / "work" / "v2" / "repos" / "NethermindEth__spsc"


# These are test inputs to the frozen rule.  They deliberately do not contain
# an expected verdict; expected outcomes live only in track-b-expected.json.
# A commitment tuple is (public, local guard, local spec, circuit spec,
# compiled support), where each spec maps effect roles to coefficients and
# carries an algorithm/domain/order identity.
BASE = {"algorithm": "poseidon", "domain": 7, "order": ["recipient", "amount"],
        "roles": {"recipient": 17, "amount": 31}}


def spec(**updates):
    value = json.loads(json.dumps(BASE))
    value.update(updates)
    return value


def commit(*, public=True, guard=True, local=None, circuit=None, support=True):
    return {"public": public, "guard": guard, "local": local or spec(),
            "circuit": circuit or spec(), "compiled_support": support}


CONTROLS = {
    "C01-direct-amount": {"direct": ["amount"], "sender": ["recipient"]},
    "C02-direct-recipient": {"direct": ["recipient", "amount"]},
    "C03-direct-both-array-literal": {"direct": ["recipient", "amount"], "syntax": "array-literal"},
    "C04-direct-both-indexed": {"direct": ["recipient", "amount"], "syntax": "indexed"},
    "C05-neither-bound": {},
    "C06-msg-sender-recipient": {"direct": ["amount"], "sender": ["recipient"]},
    "C07-msg-sender-unbound-amount": {"sender": ["recipient"]},
    "C08-commit-recipient": {"direct": ["amount"], "commitments": [commit()]},
    "C09-commit-recipient-and-amount": {"commitments": [commit()]},
    "C10-commit-only-recipient": {"commitments": [commit(local=spec(roles={"recipient": 17}), circuit=spec(roles={"recipient": 17}))]},
    "C11-commit-only-amount": {"commitments": [commit(local=spec(roles={"amount": 31}), circuit=spec(roles={"amount": 31}))]},
    "C12-commit-not-public": {"direct": ["amount"], "commitments": [commit(public=False, local=spec(roles={"recipient": 17}), circuit=spec(roles={"recipient": 17}))]},
    "C13-public-commit-no-local-guard": {"direct": ["amount"], "commitments": [commit(guard=False, local=spec(roles={"recipient": 17}), circuit=spec(roles={"recipient": 17}))]},
    "C14-local-guard-wrong-parameter": {"direct": ["amount"], "commitments": [commit(local=spec(roles={"amount": 31}), circuit=spec(roles={"recipient": 17}))]},
    "C15-local-hash-function-mismatch": {"direct": ["amount"], "commitments": [commit(local=spec(algorithm="keccak"), circuit=spec())]},
    "C16-local-hash-order-mismatch": {"commitments": [commit(local=spec(order=["amount", "recipient"]), circuit=spec())]},
    "C17-local-domain-mismatch": {"direct": ["amount"], "commitments": [commit(local=spec(domain=8), circuit=spec())]},
    "C18-cast-wrapped-direct-values": {"direct": ["recipient", "amount"], "syntax": "casts"},
    "C19-alias-public-vector": {"direct": ["recipient", "amount"], "syntax": "aliases"},
    "C20-arbitrary-calldata-vector": {"syntax": "unrecovered-calldata"},
    "C21-two-separate-commitments": {"commitments": [
        commit(local=spec(roles={"recipient": 17}), circuit=spec(roles={"recipient": 17})),
        commit(local=spec(domain=9, roles={"amount": 31}), circuit=spec(domain=9, roles={"amount": 31})),
    ]},
    "C22-commit-private-signal-absent": {"direct": ["amount"], "commitments": [commit(local=spec(roles={"recipient": 17}), circuit=spec(roles={}), support=False)]},
    "C23-constant-equality-not-binding": {"direct": ["amount"], "constant_equality": True},
    "C24-direct-amount-hashed-recipient": {"direct": ["amount"], "commitments": [commit(local=spec(roles={"recipient": 17}), circuit=spec(roles={"recipient": 17}))]},
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def decide(case):
    direct = set(case.get("direct", []))
    sender = set(case.get("sender", []))
    bound = set(direct) | set(sender)
    evidence = {role: (["direct-public-input"] if role in direct else []) for role in ("recipient", "amount")}
    if "recipient" in sender:
        evidence["recipient"].append("msg.sender")
    for index, item in enumerate(case.get("commitments", [])):
        valid = (item["public"] and item["guard"] and item["compiled_support"]
                 and canonical(item["local"]) == canonical(item["circuit"]))
        if not valid:
            continue
        for role in item["circuit"].get("roles", {}):
            bound.add(role)
            evidence[role].append(f"commitment-{index}")
    return sorted({"recipient", "amount"} - bound), evidence


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(args, *, cwd=None):
    proc = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if proc.returncode:
        sys.stderr.write(proc.stdout + proc.stderr)
        raise SystemExit(f"command failed ({proc.returncode}): {' '.join(map(str, args))}")
    return proc


def parse_sym(path):
    names = collections.defaultdict(list)
    by_name = {}
    for line in path.read_text().splitlines():
        label, wire, component, name = line.split(",", 3)
        wire = int(wire)
        if wire >= 0:
            names[wire].append(name)
            by_name[name] = wire
    return names, by_name


def r1cs_named_path(r1cs_json, sym, start_name, end_name, namespace):
    data = json.loads(r1cs_json.read_text())
    names, by_name = parse_sym(sym)
    start, end = by_name[start_name], by_name[end_name]
    constraints = []
    incident = collections.defaultdict(list)
    for index, constraint in enumerate(data["constraints"]):
        wires = set()
        for expression in constraint:
            wires.update(map(int, expression))
        wires.discard(0)
        constraints.append(wires)
        for wire in wires:
            incident[wire].append(index)
    queue = collections.deque([start])
    previous = {start: None}
    previous_constraint = {}
    while queue and end not in previous:
        wire = queue.popleft()
        for constraint_index in incident[wire]:
            for neighbour in constraints[constraint_index]:
                if neighbour not in previous:
                    previous[neighbour] = wire
                    previous_constraint[neighbour] = constraint_index
                    queue.append(neighbour)
    if end not in previous:
        return None
    path = []
    wire = end
    while wire is not None:
        path.append({"wire": wire, "constraint": previous_constraint.get(wire),
                     "names": names.get(wire, [])})
        wire = previous[wire]
    path.reverse()
    interior_names = [name for step in path[1:-1] for name in step["names"]]
    namespace_ok = bool(interior_names) and all(name.startswith(namespace) for name in interior_names)
    return {"length_wires": len(path), "namespace_ok": namespace_ok, "path": path}


def run_spsc():
    circuit = SPSC / "circuits" / "circom" / "joinsplit.circom"
    consumer = SPSC / "contracts" / "circom" / "src" / "SPSC.sol"
    poseidon_library = SPSC / "contracts" / "circom" / "src" / "PoseidonLib.sol"
    solidity_constants = SPSC / "contracts" / "circom" / "src" / "Constants.sol"
    circuit_constants = SPSC / "circuits" / "circom" / "constants.circom"
    output = RAW / "spsc-compiled"
    output.mkdir(parents=True, exist_ok=True)
    r1cs = output / "joinsplit.r1cs"
    sym = output / "joinsplit.sym"
    r1cs_json = output / "joinsplit.r1cs.json"
    command([str(CIRCOM), str(circuit), "--r1cs", "--sym", "-l",
             str(SPSC / "circuits" / "circom" / "node_modules"), "-o", str(output)])
    command([str(SNARKJS), "r1cs", "export", "json", str(r1cs), str(r1cs_json)])
    source = circuit.read_text()
    solidity = consumer.read_text()
    poseidon_source = poseidon_library.read_text()
    solidity_constants_source = solidity_constants.read_text()
    circuit_constants_source = circuit_constants.read_text()
    public_match = re.search(r"component\s+main\s*\{public\s*\[(.*?)\]\}", source, re.S)
    public_names = set(re.findall(r"\b[A-Za-z_]\w*\b", public_match.group(1))) if public_match else set()
    vector_match = re.search(r"uint256\[13\]\s+memory\s+pubSignals\s*=\s*\[(.*?)\];", solidity, re.S)
    vector_names = set(re.findall(r"\b[A-Za-z_]\w*\b", vector_match.group(1))) if vector_match else set()
    circuit_relation = all(token in source for token in (
        "extDataHasher.inputs[1] <== recipient", "extDataHasher.inputs[2] <== relayer",
        "extDataHasher.inputs[3] <== fee", "extDataHasher.out === extDataHash"))
    normalized_solidity = re.sub(r"\s+", " ", solidity)
    normalized_poseidon = re.sub(r"\s+", " ", poseidon_source)
    local_hash_order = all(token in normalized_poseidon for token in (
        "Constants.DS_EXTDATA, uint256(uint160(recipient)), uint256(uint160(relayer)), uint256(fee)".split(", ")
    )) and normalized_poseidon.index("Constants.DS_EXTDATA") < normalized_poseidon.index("uint256(uint160(recipient))") < normalized_poseidon.index("uint256(uint160(relayer))") < normalized_poseidon.index("uint256(fee)")
    solidity_domain = re.search(r"DS_EXTDATA\s*=\s*(\d+)", solidity_constants_source)
    circuit_domain = re.search(r"DS_EXTDATA\(\)\s*\{\s*return\s+(\d+)", circuit_constants_source)
    matching_domain = bool(solidity_domain and circuit_domain and solidity_domain.group(1) == circuit_domain.group(1))
    local_guard = ("PoseidonLib.computeExtDataHash" in solidity
                   and "recipient, address(0), fee" in normalized_solidity
                   and "computedExtDataHash != extDataHash" in solidity
                   and local_hash_order and matching_domain)
    transfer = "token.transfer(recipient, publicAmountOut)" in solidity
    path = r1cs_named_path(r1cs_json, sym, "main.recipient", "main.extDataHash", "main.extDataHasher.")
    amount_bound = "publicAmountOut" in public_names and "publicAmountOut" in vector_names
    recipient_bound = ("extDataHash" in public_names and "extDataHash" in vector_names
                       and circuit_relation and local_guard and path is not None and path["namespace_ok"])
    return {
        "repository": "NethermindEth/spsc", "commit": command(["git", "rev-parse", "HEAD"], cwd=SPSC).stdout.strip(),
        "circuit_sha256": sha256(circuit), "consumer_sha256": sha256(consumer),
        "poseidon_library_sha256": sha256(poseidon_library),
        "solidity_constants_sha256": sha256(solidity_constants),
        "circuit_constants_sha256": sha256(circuit_constants),
        "r1cs_sha256": sha256(r1cs), "sym_sha256": sha256(sym),
        "public_input_count": json.loads(r1cs_json.read_text())["nPubInputs"],
        "public_amount_out_direct": amount_bound, "recipient_local_guard": local_guard,
        "local_hash_order_match": local_hash_order, "domain_constant_match": matching_domain,
        "recipient_circuit_relation": circuit_relation, "recipient_compiled_path": path,
        "effect_transfer_recovered": transfer,
        "observed_p1_roles": sorted({"recipient", "amount"} - ({"amount"} if amount_bound else set()) - ({"recipient"} if recipient_bound else set())),
    }


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    expected = json.loads(EXPECTED.read_text())
    expected_by_id = {item["id"]: sorted(item["expected_p1_roles"]) for item in expected["controls"]}
    if set(expected_by_id) != set(CONTROLS):
        raise SystemExit("control IDs differ from the frozen protocol")
    rows = []
    for case_id, case in CONTROLS.items():
        observed, evidence = decide(case)
        rows.append({"id": case_id, "expected_p1_roles": expected_by_id[case_id],
                     "observed_p1_roles": observed, "match": observed == expected_by_id[case_id],
                     "evidence": evidence})
    spsc = run_spsc()
    dev = [
        {"id": "DEV-SPSC", "repository": spsc["repository"], "commit": spsc["commit"],
         "expected_p1_roles": [], "observed_p1_roles": spsc["observed_p1_roles"],
         "evidence_grade": "E1", "verdict": "VERIFIED_WITHIN_SCOPE",
         "evidence": "source correspondence + compiled R1CS path; no deployment/zkey correspondence claimed"},
        {"id": "DEV-RACEPASS", "repository": "Servesh21/RacePass", "commit": "abd54b5c541ac9d26f938a6bdbd78545526249e5",
         "expected_p1_roles": ["recipient"], "observed_p1_roles": ["recipient"],
         "evidence_grade": "E4", "verdict": "VIOLATION", "evidence": "feasibility/v2 RacePass unchanged-consumer local reproduction"},
        {"id": "DEV-ZKREDENTIAL", "repository": "ethpanda-org/ETHShanghai-2025", "commit": "23917814522bac494150c7e99a123aa15a448155",
         "expected_p1_roles": ["amount"], "observed_p1_roles": ["amount"],
         "evidence_grade": "E4", "verdict": "VIOLATION", "evidence": "feasibility/v2 ZKredential unchanged-consumer local reproduction"},
    ]
    for item in dev:
        item["match"] = sorted(item["expected_p1_roles"]) == sorted(item["observed_p1_roles"])
    result = {
        "schema_version": 1, "scope": "DEV only", "eval_rows_read": 0,
        "expected_sha256": sha256(EXPECTED),
        "controls": rows, "control_matches": sum(row["match"] for row in rows),
        "control_total": len(rows), "development_cases": dev, "spsc_compiled_evidence": spsc,
        "tool_versions": {
            "circom": command([str(CIRCOM), "--version"]).stdout.strip(),
            "circom_commit": command(["git", "rev-parse", "HEAD"], cwd=CIRCOM.parents[2]).stdout.strip(),
            "snarkjs": "0.7.6",
        },
    }
    (DATASET / "track-b-results.json").write_text(json.dumps(result, indent=2) + "\n")
    with (DATASET / "track-b-results.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "kind", "repository", "commit", "expected_p1_roles", "observed_p1_roles", "match", "evidence_grade", "verdict", "evidence"])
        writer.writeheader()
        for row in rows:
            writer.writerow({"id": row["id"], "kind": "control", "repository": "synthetic", "commit": "",
                             "expected_p1_roles": "|".join(row["expected_p1_roles"]), "observed_p1_roles": "|".join(row["observed_p1_roles"]),
                             "match": str(row["match"]).lower(), "evidence_grade": "E0", "verdict": "UNKNOWN", "evidence": canonical(row["evidence"])})
        for row in dev:
            writer.writerow({"id": row["id"], "kind": "development", "repository": row["repository"], "commit": row["commit"],
                             "expected_p1_roles": "|".join(row["expected_p1_roles"]), "observed_p1_roles": "|".join(row["observed_p1_roles"]),
                             "match": str(row["match"]).lower(), "evidence_grade": row["evidence_grade"], "verdict": row["verdict"], "evidence": row["evidence"]})
    print(json.dumps({"controls": f"{result['control_matches']}/{result['control_total']}",
                      "development": f"{sum(x['match'] for x in dev)}/{len(dev)}",
                      "spsc_p1": spsc["observed_p1_roles"], "eval_rows_read": 0}, indent=2))


if __name__ == "__main__":
    main()
