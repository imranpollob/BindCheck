"""Generate proof-to-execution binding mutants from vendored pinned baselines.

Each mutant is a list of exact-match (file, old, new) replacements applied
to a pristine copy of the baseline tree. Every replacement must occur exactly
`count` times or generation fails closed. No network, no proving.

Usage:
  python3 make_mutants.py --baseline DIR --out DIR [--only ID,...]
Writes one build tree per mutant under OUT/<ID>/ plus a generation record.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent

# (mutant_id, target_file, old_text, new_text, expected_count)
MUTANTS: dict[str, list[tuple[str, str, str, int]]] = {
    # ---- WarpToad circuit (Noir beta.22) ----
    "WT-C01": [("warptoad-withdraw-main.nr",
        '    assert(_nullifier == nullifier, "nullifier doesn\'t match inputs");\n',
        '    // XBM WT-C01: nullifier binding removed; public nullifier is free.\n', 1)],
    "WT-C02": [("warptoad-withdraw-main.nr",
        '    assert(!amount.lt(max_fee), "max_fee higher than amount");\n',
        '    // XBM WT-C02: max_fee bound removed; max_fee word is free.\n', 1)],
    "WT-C03": [  # M-DOM reuse: mechanism-derived, developer warning main.nr:11-12
        ("warptoad-withdraw-main.nr",
         '        aztec_merkle_verify(origin_local_root, commitment, aztec_merkle_data, aztec_warptoad_address);\n',
         '        // XBM WT-C03 (M-DOM reuse): public word 5 stays in the ABI but feeds no constraint.\n        aztec_merkle_verify(origin_local_root, commitment, aztec_merkle_data);\n', 1),
        ("warptoad-nargo-hashing-lib.nr",
         'pub struct Aztec_merkle_data<let D: u32> {\n    pub leaf_index: Field,\n    pub hash_path: [Field; D],\n    pub leaf_nonce: Field,\n}',
         'pub struct Aztec_merkle_data<let D: u32> {\n    pub leaf_index: Field,\n    pub hash_path: [Field; D],\n    pub leaf_nonce: Field,\n    // XBM WT-C03: prover-chosen silo address.\n    pub contract_address: Field,\n}', 1),
        ("warptoad-nargo-hashing-lib.nr",
         '    merkle_data: Aztec_merkle_data<D>,\n    contract_address: Field\n',
         '    merkle_data: Aztec_merkle_data<D>\n', 1),
        ("warptoad-nargo-hashing-lib.nr",
         '    let siloed_note_hash = compute_siloed_note_hash(contract_address, leaf);\n',
         '    let siloed_note_hash = compute_siloed_note_hash(merkle_data.contract_address, leaf);\n', 1),
    ],
    "WT-C04": [("warptoad-withdraw-main.nr",
        '        evm_merkle_verify(giga_root, origin_local_root, giga_merkle_data);\n',
        '        // XBM WT-C04: origin membership against the giga root NOT verified.\n', 1)],
    "WT-C05": [("warptoad-withdraw-main.nr",
        '        evm_merkle_verify(giga_root, origin_local_root, giga_merkle_data);\n',
        '        // XBM WT-C05: membership checks destination instead of origin.\n        evm_merkle_verify(giga_root, destination_local_root, giga_merkle_data);\n', 1)],
    "WT-C06": [("warptoad-withdraw-main.nr",
        '    let (commitment, _nullifier) = hash_commitment(nullifier_preimage, secret, chain_id, amount);\n',
        '    // XBM WT-C06: amount unbound from the commitment (honest witness breaks by design).\n    let (commitment, _nullifier) = hash_commitment(nullifier_preimage, secret, chain_id, 0);\n', 1)],
    "WT-C07": [("warptoad-withdraw-main.nr",
        '    let (commitment, _nullifier) = hash_commitment(nullifier_preimage, secret, chain_id, amount);\n',
        '    // XBM WT-C07: chain_id unbound from the commitment (cross-chain replay shape).\n    let (commitment, _nullifier) = hash_commitment(nullifier_preimage, secret, 0, amount);\n', 1)],
    "WT-C08": [("warptoad-withdraw-main.nr",
        '    assert(recipient_address != 0, "recipient_address cant be 0");\n',
        '    // XBM WT-C08: zero-recipient guard removed.\n', 1)],
    "WT-C09": [("warptoad-withdraw-main.nr",
        '    nullifier: pub Field,\n    chain_id: pub Field,\n    amount: pub Field,\n    giga_root: pub Field,\n',
        '    // XBM WT-C09: public-word order mutated (amount/max_fee swapped).\n    nullifier: pub Field,\n    chain_id: pub Field,\n    max_fee: pub Field,\n    giga_root: pub Field,\n', 1),
        ("warptoad-withdraw-main.nr",
        '    fee_factor: pub Field, \n    priority_fee: pub Field,\n    max_fee: pub Field,\n',
        '    fee_factor: pub Field, \n    priority_fee: pub Field,\n    amount: pub Field,\n', 1)],
    # ---- WarpToad consumer (Solidity 0.8.29) ----
    "WT-S01": [("WarpToadCore.sol",  # M-SRC reuse
        '        require(isValidLocalRoot(_localRoot), "_localRoot unknown"); \n',
        '        // XBM WT-S01 (M-SRC reuse): K2 local-root admission removed.\n', 1)],
    "WT-S02": [("WarpToadCore.sol",
        '        require(isValidGigaRoot(_gigaRoot), "_gigaRoot unknown");\n',
        '        // XBM WT-S02: K1 giga-root admission removed.\n', 1)],
    "WT-S03": [("WarpToadCore.sol",
        '        require(nullifiers[_nullifier] == false, "nullifier already exists");\n        nullifiers[_nullifier] = true;\n',
        '        // XBM WT-S03: nullifier check and write both removed (replay).\n', 1)],
    "WT-S04": [("WarpToadCore.sol",
        '        require(IVerifier(withdrawVerifier).verify(_poof, _publicInputs), "invalid proof"); \n',
        '        // XBM WT-S04: proof verification removed (open mint).\n', 1)],
    "WT-S05": [("WarpToadCore.sol",
        '        require(isValidGigaRoot(_gigaRoot), "_gigaRoot unknown");\n        require(isValidLocalRoot(_localRoot), "_localRoot unknown"); \n',
        '        // XBM WT-S05: root/anchor checks swapped.\n        require(isValidGigaRoot(_localRoot), "_gigaRoot unknown");\n        require(isValidLocalRoot(_gigaRoot), "_localRoot unknown"); \n', 1)],
    "WT-S06": [("WarpToadCore.sol",
        '            require(_relayerFee <= _maxFee, "_relayerFee is larger than _maxFee");\n',
        '            // XBM WT-S06: fee-cap admission removed.\n', 1)],
    "WT-S07": [("WarpToadCore.sol",
        '            _mint(_recipient, _amount - _relayerFee);\n',
        '            // XBM WT-S07: recipient share misdirected to the relayer.\n            _mint(_relayer, _amount - _relayerFee);\n', 1)],
    "WT-S08": [("WarpToadCore.sol",
        '[_nullifier,_chainId,_amount,_gigaRoot,_localRoot,_aztecWarptoadAddress,_feeFactor,_priorityFee,_maxFee]',
        '[_nullifier,_chainId,_maxFee,_gigaRoot,_localRoot,_aztecWarptoadAddress,_feeFactor,_priorityFee,_amount]', 1)],
    "WT-S09": [("WarpToadCore.sol",
        '        nullifiers[_nullifier] = true;\n',
        '        // XBM WT-S09: nullifier write dropped (check kept; replay).\n', 1)],
    # ---- Payy circuit (Noir beta.14, agg_agg) ----
    "PY-C01": [("payy-agg-agg-main.nr",
        '                assert(proof_message == 0, "messages cannot have gaps");\n',
        '                // XBM PY-C01: padding-gap check removed.\n', 1)],
    "PY-C02": [("payy-agg-agg-main.nr",
        '                assert(proof_message == messages[messages_index], "proof message must be exported");\n',
        '                // XBM PY-C02: export binding removed; public messages free.\n', 1)],
    "PY-C03": [("payy-agg-agg-main.nr",
        '            assert(proof.old_root == root, "proof old_root must match previous root");\n',
        '            // XBM PY-C03: root chaining removed.\n', 1)],
    "PY-C04": [("payy-agg-agg-main.nr",
        '    assert(\n        commit_hash\n            == poseidon2::Poseidon2::hash(\n                [proofs[0].commit_hash, proofs[1].commit_hash],\n                2,\n            ),\n    );\n',
        '    // XBM PY-C04: commit-hash binding removed.\n', 1)],
    "PY-C05": [("payy-agg-agg-main.nr",
        '        assert(is_valid_proof, "proof must be one of the valid proofs");\n',
        '        // XBM PY-C05: verification-key allowlist removed.\n', 1)],
    "PY-C06": [("payy-agg-agg-main.nr",
        '    assert(new_root == root, "Roots must match");\n',
        '    // XBM PY-C06: final root match removed; new_root free.\n', 1)],
    "PY-C07": [("payy-agg-agg-main.nr",
        '    old_root: pub Field,\n    new_root: pub Field,\n',
        '    new_root: pub Field,\n    old_root: pub Field,\n', 1)],
    # ---- Payy consumer (Solidity 0.8.20) ----
    "PY-S01": [("RollupV1.sol",
        '        require(\n            mints[hash].amount == uint256(value),\n            "RollupV1: Mint value invalid"\n        );\n        require(\n            mints[hash].note_kind == note_kind,\n            "RollupV1: Mint note kind invalid"\n        );\n        require(mints[hash].spent == false, "RollupV1: Mint already spent");\n',
        '        // XBM PY-S01: mint registration/value/kind admission removed.\n', 1)],
    "PY-S02": [("RollupV1.sol",
        '        require(mints[hash].spent == false, "RollupV1: Mint already spent");\n',
        '        // XBM PY-S02: mint single-use removed (replay).\n', 1)],
    "PY-S03": [("RollupV1.sol",
        '        address burn_addr = bytes32ToAddress(messages[i + 4]);\n',
        '        // XBM PY-S03: burn recipient misbound to the note-kind word.\n        address burn_addr = bytes32ToAddress(messages[i + 1]);\n', 1)],
    "PY-S04": [("RollupV1.sol",
        '        } else if (kind == 3) {\n            // Burn\n            return verifyBurn(index, publicInputs);\n',
        '        } else if (kind == 3) {\n            // Burn\n            return verifyBurn(index, publicInputs);\n        } else if (kind == 4) {\n            // XBM PY-S04: dead kind-4 path activated as burn.\n            return verifyBurn(index, publicInputs);\n', 1)],
    "PY-S05": [("RollupV1.sol",
        '        // Skip the first 4 (as they are processed separately)\n        uint i = skipCount;\n',
        '        // XBM PY-S05: header skip removed; header words read as messages.\n        uint i = 0;\n', 1)],
}

# Baseline file set copied per mutant family.
FAMILY_FILES = {
    "WT-C": ["warptoad-withdraw-main.nr", "warptoad-withdraw-Nargo.toml",
             "warptoad-nargo-hashing-lib.nr"],
    "WT-S": ["WarpToadCore.sol"],
    "PY-C": ["payy-agg-agg-main.nr", "payy-agg-agg-Nargo.toml"],
    "PY-S": ["RollupV1.sol", "payy-IVerifier.sol", "payy-IUSDC.sol"],
}


def family(mutant_id: str) -> str:
    return mutant_id.rsplit("-", 1)[0] if mutant_id.rsplit("-", 1)[0] in FAMILY_FILES else mutant_id[:4]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def apply(baseline: Path, out: Path, only: set[str] | None) -> dict:
    record: dict = {"mutants": {}}
    for mid, edits in MUTANTS.items():
        if only and mid not in only:
            continue
        fam = family(mid)
        dest = out / mid
        if dest.exists():
            raise SystemExit(f"refusing to overwrite {dest}")
        dest.mkdir(parents=True)
        for name in FAMILY_FILES[fam]:
            shutil.copy(baseline / name, dest / name)
        applied = []
        for fname, old, new, count in edits:
            target = dest / fname
            text = target.read_text()
            found = text.count(old)
            if found != count:
                raise SystemExit(f"{mid}/{fname}: expected {count}, found {found}")
            target.write_text(text.replace(old, new))
            applied.append({"file": fname, "replaced_spans": found,
                            "old_sha256": hashlib.sha256(old.encode()).hexdigest(),
                            "new_sha256": hashlib.sha256(new.encode()).hexdigest()})
        record["mutants"][mid] = {
            "family": fam, "edits": applied,
            "files": {n: sha256(dest / n) for n in FAMILY_FILES[fam]},
        }
    return record


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--record", type=Path, required=True)
    args = ap.parse_args()
    only = set(args.only.split(",")) if args.only else None
    args.out.mkdir(parents=True, exist_ok=True)
    record = apply(args.baseline, args.out, only)
    record["schema"] = "bindcheck.xbm.generation/v1"
    args.record.write_text(json.dumps(record, indent=1) + "\n")
    print(f"generated {len(record['mutants'])} mutants -> {args.out}")


if __name__ == "__main__":
    main()
