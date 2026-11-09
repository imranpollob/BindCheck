#!/usr/bin/env python3
"""Record source facts for the zk_voting (DEV-F34) case study. Read-only.

usage: zkvoting_facts.py <DEV-F34 checkout> <out.json>
All values are read from pinned files; nothing is executed from the checkout.
"""
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
vk = json.loads((root / "circuit/verification_key.json").read_text())
r1cs = json.loads((root / "circuit/circuit.r1cs.json").read_text())
sym = {}
for line in (root / "circuit/circuit.sym").read_text().splitlines():
    idx, wire, comp, name = line.split(",", 3)
    sym[name] = int(wire)
consumer = (root / "contracts/VotingContract.sol").read_text()
circuit = (root / "circuit/circuit.circom").read_text()
out = {
    "source_root": str(root),
    "vk_nPublic": vk.get("nPublic"),
    "vk_IC_points": len(vk.get("IC", [])),
    "vk_gamma_equals_delta": vk["vk_gamma_2"] == vk["vk_delta_2"],
    "r1cs_nPubInputs": r1cs["nPubInputs"],
    "r1cs_nOutputs": r1cs["nOutputs"],
    "r1cs_nConstraints": r1cs["nConstraints"],
    "sym_wire_main.isVoteValid": sym.get("main.isVoteValid"),
    "sym_wire_main.nullifierHash": sym.get("main.nullifierHash"),
    "circuit_main_has_public_list": "public" in circuit.split("component main", 1)[1],
    "circuit_nullifier_check_is_assert_on_var": "var nullifierCheck" in circuit and "assert (nullifierCheck == 1)" in circuit,
    "consumer_reads_input0_as_nullifier": "uint256 nullifierHash = input[0];" in consumer,
    "consumer_checks_isVoteValid": "isVoteValid" in consumer,
}
pathlib.Path(sys.argv[2]).write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
