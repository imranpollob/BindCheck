"""Generate B2 binding mutants from vendored pinned baselines (fail-closed).

Each mutant is a list of exact-match (host-relative file, old, new, count)
edits applied to a pristine copy of baselines/<host>/. A replacement that does
not occur exactly `count` times aborts generation. Also renders
mutants/<ID>.md from the metadata below (ground truth for scoring).

Usage:
  python3 make_mutants.py --out DIR [--only ID,...] [--docs]
Writes DIR/<ID>/<host tree> for every mutant, plus DIR/generation-record.json.
With --docs it (re)writes mutants/<ID>.md next to this script.
No network, no proving.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / "baselines"

RP_OPEN_SIG = (
    "    function open(\n        uint256 id,\n        // zk proof:\n"
    "        uint256[] memory proof\n    ) public returns (uint256) {\n"
)
RP_INPUT = (
    "        uint256[2] memory input = [\n            p.passcodeHash,\n"
    "            uint256(uint160(msg.sender))\n        ];\n"
)
RPC = "contracts/RedPacket.sol"
PVC = "contracts/src/PrivacyVault.sol"
ORC = "src/OrcClaim.sol"

# id: dict(host, pattern, layer, edits, ...metadata)
M: dict[str, dict] = {}


def add(id_, host, pattern, layer, operator, broken, consumer, unbound, effect, honest, edits):
    M[id_] = dict(host=host, pattern=pattern, layer=layer, operator=operator, broken=broken,
                  consumer=consumer, unbound=unbound, effect=effect, honest=honest, edits=edits)


# ------------------------------------------------------------------ RedPacket
add("RP-S01", "redpacket", "P1", "consumer",
    "constant public input: caller replaced by `address(this)` in the proof statement",
    "caller identity (`msg.sender`) is no longer a public input of the proof; the proof binds only the passcode hash and a constant",
    "contracts/RedPacket.sol :: open", "msg.sender (claimer / payout recipient)",
    "Anyone who observes one claimer's proof (made for address(this)) replays it from any number of fresh addresses and drains the packet without knowing the passcode.",
    "Honest prover must use addr = contract address; honest claim still works (proof for that statement verifies).",
    [(RPC, RP_INPUT, RP_INPUT.replace("msg.sender", "address(this)"), 1)])

add("RP-S02", "redpacket", "P2", "consumer",
    "stored passcode hash replaced by a caller-supplied argument",
    "proof is not bound to the red packet's stored `passcodeHash`",
    "contracts/RedPacket.sol :: open", "passcodeHash (public input 0)",
    "Caller proves knowledge of a passcode for a hash of their own choosing and withdraws from any packet.",
    "Honest claim works when the caller passes the packet's real hash.",
    [(RPC, RP_OPEN_SIG, RP_OPEN_SIG.replace("uint256[] memory proof\n", "uint256[] memory proof,\n        uint256 passcodeHash_\n"), 1),
     (RPC, "            p.passcodeHash,\n            uint256(uint160(msg.sender))\n        ];",
      "            passcodeHash_,\n            uint256(uint160(msg.sender))\n        ];", 1)])

add("RP-S03", "redpacket", "P3", "consumer",
    "recipient taken from a caller argument `to` (proved) while the once-only key stays on `msg.sender`",
    "replay key (`withdrawedMap[id, msg.sender]`) is not bound to the proved recipient",
    "contracts/RedPacket.sol :: open", "msg.sender in the once-per-claimer key (proved identity is `to`)",
    "One proof for recipient `to` is replayed by many different senders; each call pays `to` again, draining the packet's slots into `to`.",
    "Honest claim works (sender == to).",
    [(RPC, RP_OPEN_SIG, RP_OPEN_SIG.replace("uint256[] memory proof\n", "uint256[] memory proof,\n        address to\n"), 1),
     (RPC, RP_INPUT, RP_INPUT.replace("msg.sender", "to"), 1),
     (RPC, "            (bool sent, bytes memory _data) = payable(msg.sender).call{",
      "            (bool sent, bytes memory _data) = payable(to).call{", 1),
     (RPC, "            (IERC20(p.token)).safeTransfer(msg.sender, bonus);",
      "            (IERC20(p.token)).safeTransfer(to, bonus);", 1)])

add("RP-S04", "redpacket", "P4", "consumer",
    "pairing result ignored: failing pairing returns success code",
    "verifier accepts proofs whose pairing check fails",
    "contracts/Verifier.sol :: verify (called from RedPacket.sol :: open)", "whole proof statement",
    "Every proof is accepted: anyone claims any packet with a garbage proof.",
    "Honest claim works (and so does every forgery).",
    [("contracts/Verifier.sol", "        )) return 1;\n        return 0;\n", "        )) return 0;\n        return 0;\n", 1)])

add("RP-S05", "redpacket", "P4", "consumer",
    "public-input range check removed",
    "public inputs are not required to be < the scalar field (aliasing x and x+r)",
    "contracts/Verifier.sol :: verify (called from RedPacket.sol :: open)", "public inputs (passcodeHash, sender) as field elements",
    "Public inputs become aliasable. Exploitability in this consumer is limited (sender is a 160-bit address; passcodeHash is creator-chosen): a weak mutant, scored as P4 by GUIDE shape.",
    "Honest claim works.",
    [("contracts/Verifier.sol", '            require(input[i] < snark_scalar_field,"verifier-gte-snark-scalar-field");\n', "", 1)])

add("RP-S06", "redpacket", "P5", "consumer",
    "sender re-encoded to its low 32 bits before it is used as the public input",
    "the proved identity is `uint32(msg.sender)`, not the 160-bit address (encoding mismatch with the circuit's `addr` field)",
    "contracts/RedPacket.sol :: open", "full address (only 32 bits are in the statement)",
    "Verifier accepts the proof for the truncated value; any sender whose address shares the low 32 bits (about 2^32 vanity grinding) reuses a victim's observed proof and takes a slot. The standard client (full address) would be rejected, so honest compatibility needs a client that uses the consumer's truncation.",
    "Honest claim works for a prover using the consumer's truncated encoding.",
    [(RPC, RP_INPUT, RP_INPUT.replace("uint256(uint160(msg.sender))", "uint256(uint32(uint160(msg.sender)))"), 1)])

add("RP-C01", "redpacket", "P2", "circuit",
    "constraint removed: `out <== hash.out` replaced by unconstrained assignment `<--`",
    "the public output (passcode hash) is not constrained to the MiMC of the secret",
    "contracts/RedPacket.sol :: open (consumer unchanged; verifier is the baseline one, see note)", "passcodeHash (public output)",
    "A prover can choose `out` freely, so a proof exists for any stored hash: anyone claims any packet. NOTE: the baseline Verifier.sol is not regenerated, so this is a circuit-layer target for circomspect/Picus; an end-to-end claim would need a regenerated verifier (not done).",
    "Circuit compiles; witness/proving not run (no node/snarkjs available).",
    [("circuits/passcode.circom", "    out <== hash.out;\n", "    out <-- hash.out;\n", 1)])

# ------------------------------------------------------------- Privacy Vaults
add("PV-S01", "privacyvaults", "P1", "consumer",
    "recipient public input replaced by constant 0 (circuit leaves the recipient word unconstrained)",
    "payout recipient `_recipient` is not fixed by the proof",
    "contracts/src/PrivacyVault.sol :: withdraw", "_recipient",
    "A front-runner copies a withdrawal proof from the mempool and calls withdraw with their own `_recipient`, taking the payout.",
    "Honest prover proves with recipient word 0; withdraw works.",
    [(PVC, "        publicInputs[3] = bytes32(uint256(uint160(_recipient)));\n", "        publicInputs[3] = bytes32(uint256(0));\n", 1)])

add("PV-S11", "privacyvaults", "P1", "consumer",
    "borrow recipient public input replaced by constant 0",
    "loan recipient `_recipient` is not fixed by the proof",
    "contracts/src/PrivacyVault.sol :: borrow", "_recipient",
    "A front-runner copies a borrow proof and receives the loan against someone else's collateral note.",
    "Honest prover proves with recipient word 0; borrow works.",
    [(PVC, "        publicInputs[2] = bytes32(uint256(uint160(_recipient)));\n", "        publicInputs[2] = bytes32(uint256(0));\n", 1)])

add("PV-S02", "privacyvaults", "P2", "consumer",
    "root-admission check removed in withdraw",
    "the proved Merkle root is not bound to the vault's own tree (`isKnownRoot`)",
    "contracts/src/PrivacyVault.sol :: withdraw", "_root",
    "Attacker builds their own tree with a self-made commitment and withdraws DENOMINATION from the vault.",
    "Honest withdraw works.",
    [(PVC, "            revert PrivacyVault__NoteAlreadySpent({nullifierHash: _nullifierHash});\n        }\n        if (!isKnownRoot(_root)) revert PrivacyVault__UnknownRoot({root: _root});\n",
      "            revert PrivacyVault__NoteAlreadySpent({nullifierHash: _nullifierHash});\n        }\n", 1)])

add("PV-S03", "privacyvaults", "P2", "consumer",
    "root-admission check removed in borrow",
    "the proved Merkle root is not bound to the vault's own tree",
    "contracts/src/PrivacyVault.sol :: borrow", "_root",
    "Attacker borrows up to 70% LTV against a fabricated collateral note.",
    "Honest borrow works.",
    [(PVC, "        // 3. Validate root is known\n        if (!isKnownRoot(_root)) revert PrivacyVault__UnknownRoot({root: _root});\n", "        // 3. (root validation removed)\n", 1)])

add("PV-C01", "privacyvaults", "P2", "circuit",
    "Merkle membership assertion removed from the borrow circuit",
    "borrow proof no longer shows the collateral commitment is in the tree under `root`",
    "contracts/src/PrivacyVault.sol :: borrow", "collateral commitment membership (root)",
    "Anyone proves any `collateral_nullifier_hash`/yield index for a commitment never deposited, and borrows. NOTE: the committed BorrowVerifier.sol is not regenerated; circuit-layer target.",
    "nargo compile only (no honest Prover.toml in the host).",
    [("circuits_borrow/src/main.nr", "    assert(computed_root == root);\n", "    // XBM PV-C01: membership assertion removed.\n", 1)])

add("PV-S04", "privacyvaults", "P3", "consumer",
    "nullifier write removed in withdraw",
    "no replay protection for the withdraw proof",
    "contracts/src/PrivacyVault.sol :: withdraw", "_nullifierHash",
    "The same withdrawal proof is submitted repeatedly; each call pays out again until the vault is drained.",
    "Honest first withdraw works.",
    [(PVC, "        s_nullifierHashes[_nullifierHash] = true;\n", "", 1)])

add("PV-C02", "privacyvaults", "P3", "circuit",
    "nullifier-hash binding removed from the withdraw circuit",
    "public `nullifier_hash` is no longer tied to the note's secret `nullifier`",
    "contracts/src/PrivacyVault.sol :: withdraw", "nullifier_hash",
    "One note is withdrawn many times under fresh nullifier hashes. NOTE: committed Verifier.sol not regenerated; circuit-layer target.",
    "nargo compile only.",
    [("circuits/src/main.nr", "    assert(computed_nullifier_hash == nullifier_hash);\n", "    // XBM PV-C02: nullifier binding removed.\n", 1)])

add("PV-C03", "privacyvaults", "P3", "circuit",
    "collateral-nullifier binding removed from the borrow circuit",
    "public `collateral_nullifier_hash` (loan key) is free",
    "contracts/src/PrivacyVault.sol :: borrow", "collateral_nullifier_hash",
    "One collateral note backs unlimited loans under fresh loan keys. NOTE: committed BorrowVerifier.sol not regenerated; circuit-layer target.",
    "nargo compile only.",
    [("circuits_borrow/src/main.nr", "    assert(poseidon2::Poseidon2::hash([nullifier, 1], 2) == collateral_nullifier_hash);\n",
      "    // XBM PV-C03: collateral nullifier binding removed.\n", 1)])

add("PV-S06", "privacyvaults", "P4", "consumer",
    "verifier return value ignored in withdraw",
    "a verifier that returns false (instead of reverting) is accepted",
    "contracts/src/PrivacyVault.sol :: withdraw", "whole proof statement",
    "Honk verifiers return false on a failed final pairing check; ignoring it lets forged proofs through where the failure is not a revert.",
    "Honest withdraw works.",
    [(PVC, "        if (!i_verifier.verify(_proof, publicInputs)) revert PrivacyVault__InvalidWithdrawProof();\n",
      "        i_verifier.verify(_proof, publicInputs);\n", 1)])

add("PV-S08", "privacyvaults", "P5", "consumer",
    "yield index narrowed to uint64 when computing the withdraw payout (verifier still gets the full word)",
    "the payout is computed from `uint64(_yieldIndex)`, not the 254-bit proved public input",
    "contracts/src/PrivacyVault.sol :: withdraw", "_yieldIndex (low 64 bits used for the effect)",
    "Verifier accepts the honest proof; the payout divides by the truncated value (about 1e27 truncates to an unrelated 64-bit number), so the effect is not what the proved statement entitles; a note's payout can be inflated far beyond DENOMINATION.",
    "Honest proof is accepted; the effect (payout amount) is wrong.",
    [(PVC, "        uint256 payout = (DENOMINATION * currentBlended) / _yieldIndex;\n",
      "        uint256 payout = (DENOMINATION * currentBlended) / uint64(_yieldIndex);\n", 1)])

add("PV-S09", "privacyvaults", "P5", "consumer",
    "yield index narrowed to uint64 when valuing borrow collateral",
    "collateral value is computed from `uint64(_yieldIndex)`, not the proved public input",
    "contracts/src/PrivacyVault.sol :: borrow", "_yieldIndex (low 64 bits used for the effect)",
    "Verifier accepts the honest proof; collateralValue and maxBorrow are computed from the truncated value, so the LTV bound is inflated and the borrower takes a loan far above 70% of the proved note value.",
    "Honest proof is accepted; the loan limit is wrong.",
    [(PVC, "        uint256 collateralValue = (DENOMINATION * currentBlended) / _yieldIndex;",
      "        uint256 collateralValue = (DENOMINATION * currentBlended) / uint64(_yieldIndex);", 1)])

# ------------------------------------------------------------------------ orc
add("OR-S01", "orc", "P1", "consumer",
    "sender check removed",
    "the claim is no longer bound to `msg.sender` (public value `ethAddress`)",
    "src/OrcClaim.sol :: claim", "msg.sender (whose account is credited)",
    "A front-runner submits a victim's observed (publicValues, proof); the claim and nullifier are recorded for the attacker (Claimed(account=msg.sender)), consuming the victim's one-per-account slot.",
    "Honest claim works.",
    [(ORC, "        if (pv.ethAddress != msg.sender) revert WrongSender(pv.ethAddress, msg.sender);\n", "", 1)])

add("OR-S02", "orc", "P2", "consumer",
    "campaign check removed",
    "proof is not bound to this deployment (campaignId = chain, address, salt)",
    "src/OrcClaim.sol :: claim", "campaignId",
    "Proofs and nullifiers made for another deployment on the same chain are accepted.",
    "Honest claim works.",
    [(ORC, "        if (pv.campaignId != campaignId) revert WrongCampaign(campaignId, pv.campaignId);\n", "", 1)])

add("OR-S03", "orc", "P2", "consumer",
    "snapshot check removed",
    "proof is not bound to this contract's configured snapshot (policy)",
    "src/OrcClaim.sol :: claim", "snapshot",
    "A proof computed for a later snapshot (more commits counted, new accounts) is accepted.",
    "Honest claim works.",
    [(ORC, "        if (pv.snapshot != snapshot) revert WrongSnapshot(snapshot, pv.snapshot);\n", "", 1)])

add("OR-S04", "orc", "P2", "consumer",
    "notary-key pin removed",
    "TLS attestation key is not pinned to the configured notary",
    "src/OrcClaim.sol :: claim", "notaryKeyHash",
    "Any notary key (attacker-run) can attest the GitHub session.",
    "Honest claim works.",
    [(ORC, "        if (pv.notaryKeyHash != notaryKeyHash) revert WrongNotary(notaryKeyHash, pv.notaryKeyHash);\n", "", 1)])

add("OR-S05", "orc", "P4", "consumer",
    "verifier call wrapped in try/catch that swallows failure",
    "failed proof verification no longer reverts",
    "src/OrcClaim.sol :: claim", "whole proof statement",
    "Any publicValues with an invalid proof pass the final check; claims need no proof.",
    "Honest claim works.",
    [(ORC, "        verifier.verifyProof(programVKey, publicValues, proofBytes);\n",
      "        try verifier.verifyProof(programVKey, publicValues, proofBytes) {} catch {}\n", 1)])

add("OR-S06", "orc", "P3", "consumer",
    "nullifier write removed",
    "no replay protection (nullifier never marked used)",
    "src/OrcClaim.sol :: claim", "nullifier",
    "The same account claims repeatedly in one campaign.",
    "Honest first claim works.",
    [(ORC, "        nullifierUsed[pv.nullifier] = true;\n", "", 1)])

add("OR-S08", "orc", "P5", "consumer",
    "threshold check reads the repoDatabaseId word instead of the threshold word",
    "the minimum-commit policy is checked against `pv.repoDatabaseId`, not the proved `threshold`",
    "src/OrcClaim.sol :: claim", "threshold (the proved commit count is never compared)",
    "Verifier and all other checks accept the honest proof; a proof attesting any threshold (e.g. 0 commits) passes because the large repo id is compared instead.",
    "Honest claim works (repo id is far above the configured threshold).",
    [(ORC, "        if (pv.threshold < threshold) revert ThresholdTooLow(threshold, pv.threshold);\n",
      "        if (pv.repoDatabaseId < threshold) revert ThresholdTooLow(threshold, pv.repoDatabaseId);\n", 1)])

add("OR-S09", "orc", "P5", "consumer",
    "nullifier truncated to 64 bits before the replay-set lookup and write",
    "the replay key is `uint64(nullifier)`, not the proved 256-bit nullifier word",
    "src/OrcClaim.sol :: claim", "nullifier (only 64 bits used)",
    "Verifier accepts the honest proof; two GitHub accounts whose nullifiers share the low 64 bits (about 2^32 accounts to find a pair) alias, so one account consumes another's one-claim slot.",
    "Honest claim call succeeds (no revert); host tests that read `nullifierUsed(fullNullifier)` fail by assertion, which only shows the key changed.",
    [(ORC, "        if (nullifierUsed[pv.nullifier]) revert NullifierUsed(pv.nullifier);\n",
      "        if (nullifierUsed[bytes32(uint256(uint64(uint256(pv.nullifier))))]) revert NullifierUsed(pv.nullifier);\n", 1),
     (ORC, "        nullifierUsed[pv.nullifier] = true;\n",
      "        nullifierUsed[bytes32(uint256(uint64(uint256(pv.nullifier))))] = true;\n", 1)])

add("OR-S10", "orc", "P4", "consumer",
    "program verification key made mutable with an unprotected setter",
    "the SP1 program vkey is not pinned: anyone can replace it",
    "src/OrcClaim.sol :: claim (setProgramVKey added)", "programVKey",
    "Anyone sets the vkey to a program they control and submits their own valid proof with arbitrary publicValues.",
    "Honest claim works.",
    [(ORC, "    bytes32 public immutable programVKey;\n", "    bytes32 public programVKey;\n", 1),
     (ORC, "    /// @notice Claims for `msg.sender` with an SP1 proof of the orc guest.\n",
      "    function setProgramVKey(bytes32 v) external {\n        programVKey = v;\n    }\n\n    /// @notice Claims for `msg.sender` with an SP1 proof of the orc guest.\n", 1)])


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def render_md(id_: str, m: dict) -> str:
    edits = "\n".join(f"- `{f}`: {c} exact replacement(s)" for f, _, _, c in m["edits"])
    return f"""# {id_}: {m['operator']}

- Host: `{m['host']}`. Pattern: **{m['pattern']}**. Mutated layer: {m['layer']}.
- Operator: {m['operator']}.
- Binding broken: {m['broken']}.
- Consumer file and function: `{m['consumer']}`.
- Unbound value: {m['unbound']}.
- Expected effect (prediction, not an E4 result): {m['effect']}
- Honest path: {m['honest']}
- Edits (see `make_mutants.py`):
{edits}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--docs", action="store_true")
    a = ap.parse_args()
    only = set(filter(None, a.only.split(",")))
    out = Path(a.out)
    rec = {}
    for id_, m in M.items():
        if only and id_ not in only:
            continue
        host_dir = BASE / m["host"]
        dst = out / id_
        if dst.exists():
            print(f"refusing to overwrite {dst}; use a fresh --out", file=sys.stderr)
            return 2
        shutil.copytree(host_dir, dst)
        for f, old, new, cnt in m["edits"]:
            p = dst / f
            text = p.read_text()
            n = text.count(old)
            if n != cnt:
                print(f"FAIL {id_}: {f}: expected {cnt} occurrence(s), found {n}", file=sys.stderr)
                return 1
            p.write_text(text.replace(old, new))
        rec[id_] = {"host": m["host"], "pattern": m["pattern"], "layer": m["layer"],
                    "files": {f: sha((dst / f).read_bytes()) for f, *_ in m["edits"]}}
        if a.docs:
            (HERE / "mutants" / f"{id_}.md").write_text(render_md(id_, m))
    (out / "generation-record.json").write_text(json.dumps(rec, indent=1, sort_keys=True))
    print(f"generated {len(rec)} mutants")
    return 0


if __name__ == "__main__":
    sys.exit(main())
