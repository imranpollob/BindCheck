"""Collect build outcomes from $OUT into manifest.json.

Reads generation-record.json + per-mutant logs, writes manifest.json with
ground-truth summaries (from an embedded table) and observed build results.
Run after build.sh. Fails closed on missing logs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

GROUND_TRUTH = {
    "WT-C01": ("leave-public-unconstrained", "nullifier", "arbitrary-nullifier mint; real note unspent"),
    "WT-C02": ("leave-public-unconstrained", "max_fee", "fee-cap policy bypass at proof level"),
    "WT-C03": ("replace-public-with-private", "aztec_silo", "foreign-contract note verifies (O1 shape; M-DOM reuse)"),
    "WT-C04": ("remove-guard", "origin_root", "fabricated origin root verifies off-branch"),
    "WT-C05": ("swap-checks", "origin/destination roots", "destination proved, origin free; honest path intact"),
    "WT-C06": ("unbind-amount", "amount", "fixed commitment authorizes any amount (honest-breaking)"),
    "WT-C07": ("unbind-domain", "chain_id", "cross-chain replay shape (honest-breaking)"),
    "WT-C08": ("remove-guard", "recipient!=0", "zero-address mint verifies at circuit level"),
    "WT-C09": ("misorder-words", "amount/max_fee", "ABI/decoder misalignment"),
    "WT-S01": ("remove-guard", "K2 local root", "unadmitted-tree mint succeeds (O2 shape; M-SRC reuse)"),
    "WT-S02": ("remove-guard", "K1 giga root", "arbitrary giga root passes consumer"),
    "WT-S03": ("drop-accounting", "nullifier check+write", "unbounded replay, no spend recorded"),
    "WT-S04": ("remove-gate", "verifier call", "open mint without proof (positive control)"),
    "WT-S05": ("swap-checks", "giga/local histories", "honest mints revert; wrong-set bypass"),
    "WT-S06": ("unbind-fee", "maxFee cap", "relayer over-fee above stated maximum"),
    "WT-S07": ("misdirect-beneficiary", "recipient share", "principal paid to relayer"),
    "WT-S08": ("misorder-words", "amount/maxFee encoding", "verifier sees swapped value"),
    "WT-S09": ("drop-write", "nullifier write", "replay despite live check (cf S03)"),
    "PY-C01": ("remove-guard", "padding gaps", "sparse trailing records provable"),
    "PY-C02": ("leave-public-unconstrained", "messages[..]", "arbitrary public messages verify"),
    "PY-C03": ("remove-guard", "root chaining", "disjoint histories aggregate"),
    "PY-C04": ("unbind-commitment", "commit_hash", "aggregate floats free of inner commits"),
    "PY-C05": ("remove-config-check", "VK allowlist", "unlisted keys aggregate"),
    "PY-C06": ("leave-public-unconstrained", "new_root", "arbitrary claimed resulting state"),
    "PY-C07": ("misorder-words", "old/new root", "roots interpreted swapped downstream"),
    "PY-S01": ("remove-guard", "mint registration", "unregistered mints settle"),
    "PY-S02": ("drop-single-use", "mint spent flag", "registered mint settles twice"),
    "PY-S03": ("misbind-word", "burn recipient", "payout to note-kind-derived address"),
    "PY-S04": ("activate-dead-path", "kind 4", "swap records settle as burns, stride misaligned"),
    "PY-S05": ("offset", "header skip", "header words parsed as records"),
}

TOOLCHAIN = {
    "nargo_beta22": "1.0.0-beta.22+c57152f91260ecdb9faad4efc20abb14b6d2ece7",
    "nargo_beta14": "1.0.0-beta.14+60ccd48e18ad8ce50d5ecda9baf813b712145051",
    "solc_warptoad": "0.8.29+commit.ab55807c",
    "solc_payy": "0.8.20",
    "cvc5": "not run in this benchmark",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    out = args.out
    gen = json.loads((out / "generation-record.json").read_text())
    manifest = {
        "schema": "bindcheck.xbm.manifest/v1",
        "count": len(GROUND_TRUTH),
        "toolchain": TOOLCHAIN,
        "baselines": {
            "warptoad_app_revision": "973e7d1e4b60d0d8a8ca299b0cabd9193b147ef8",
            "payy_app_revision": "c4d2c902 (earlier, vulnerable)",
            "exposure": "both applications already exposed in-repo; development use only, never held-out",
        },
        "mutants": {},
    }
    summary = {}
    tsv = out / "build-summary.tsv"
    if tsv.exists():
        for line in tsv.read_text().splitlines():
            parts = line.split("\t")
            if len(parts) == 4:
                summary[parts[0]] = {"compile_exit": parts[1],
                                     "execute_exit": parts[2],
                                     "artifact_sha256": parts[3]}
    for mid, (operator, binding, effect) in GROUND_TRUTH.items():
        log = out / "logs" / f"{mid}-compile.log"
        if not log.exists():
            raise SystemExit(f"missing build log for {mid}")
        text = log.read_text(errors="replace")
        manifest["mutants"][mid] = {
            "operator": operator,
            "binding_broken": binding,
            "expected_effect": effect,
            "readme": f"mutants/{mid}.md",
            "files": gen["mutants"][mid]["files"],
            "observed": summary.get(mid, {"compile_exit": "unknown",
                                          "execute_exit": "unknown",
                                          "artifact_sha256": "unknown"}),
            "compile_log_tail": text[-1200:],
        }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"manifest for {len(manifest['mutants'])} mutants")


if __name__ == "__main__":
    main()
