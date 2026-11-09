#!/usr/bin/env python3
"""Check the frozen P4 analyzer's BN254 G2 generator constant (lane P audit).

Read-only. Imports bindcheck_zk from the repository root (frozen content
hash 8ea6d223...), compares p4.BN254_G2 with the EIP-197 G2 generator,
checks both against the BN254 twist equation, then re-runs p4.analyze_source
on every Solidity file in the read-only DEV checkouts twice: once with the
frozen constant and once with the EIP-197 constant patched in memory. Writes
JSON to the path given as argv[2]. No file under bindcheck_zk/ is modified.

usage: check_p4_g2_constant.py <full-dev-checkout-root> <out.json>
"""
import hashlib
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from bindcheck_zk import p4  # noqa: E402

# EIP-197 G2 generator, in the (x_im, x_re, y_im, y_re) order snarkjs verifiers
# use for gammax1/gammax2/gammay1/gammay2 and that p4.BN254_G2 also uses.
EIP197_G2 = (
    11559732032986387107991004021392285783925812861821192530917403151452391805634,
    10857046999023057135944570762232829481370756359578518086990519993285655852781,
    4082367875863433681332203403145435568316851327593401208105741076214120093531,
    8495653923123431417604973247489272438418190587263600148770280649306958101930,
)
Q = 21888242871839275222246405745257275088696311157297823662689037894645226208583


def fp2_mul(a, b):
    return ((a[0] * b[0] - a[1] * b[1]) % Q, (a[0] * b[1] + a[1] * b[0]) % Q)


def on_twist(pt):
    # pt = (x_im, x_re, y_im, y_re); Fp2 elements as (re, im)
    x = (pt[1], pt[0])
    y = (pt[3], pt[2])
    # b' = 3 / (9 + i)
    nine_i = (9, 1)
    inv_den = pow((81 + 1) % Q, Q - 2, Q)
    conj = (9, (-1) % Q)
    b2 = ((3 * conj[0] * inv_den) % Q, (3 * conj[1] * inv_den) % Q)
    lhs = fp2_mul(y, y)
    x3 = fp2_mul(fp2_mul(x, x), x)
    rhs = ((x3[0] + b2[0]) % Q, (x3[1] + b2[1]) % Q)
    assert fp2_mul(nine_i, b2) == (3, 0)
    return lhs == rhs


def main():
    root = pathlib.Path(sys.argv[1])
    out = pathlib.Path(sys.argv[2])
    frozen = tuple(p4.BN254_G2)
    report = {
        "p4_source_sha256": hashlib.sha256((REPO / "bindcheck_zk/p4.py").read_bytes()).hexdigest(),
        "frozen_constant": [str(v) for v in frozen],
        "eip197_constant": [str(v) for v in EIP197_G2],
        "differing_coordinates": [i for i in range(4) if frozen[i] != EIP197_G2[i]],
        "frozen_digit_lengths": [len(str(v)) for v in frozen],
        "eip197_digit_lengths": [len(str(v)) for v in EIP197_G2],
        "frozen_on_twist": on_twist(frozen),
        "eip197_on_twist": on_twist(EIP197_G2),
        "files": [],
    }
    for path in sorted(root.rglob("*.sol")):
        if "node_modules" in path.parts or not path.is_file():
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        if "gamma" not in text.lower() or "delta" not in text.lower():
            continue
        rel = str(path.relative_to(root))
        p4.BN254_G2 = frozen
        a = p4.analyze_source(text, rel)
        p4.BN254_G2 = EIP197_G2
        b = p4.analyze_source(text, rel)
        p4.BN254_G2 = frozen
        report["files"].append({
            "path": rel,
            "row": rel.split("--", 1)[0],
            "frozen": [a["finding"]["verdict"], a["finding"]["reason"]],
            "eip197": [b["finding"]["verdict"], b["finding"]["reason"]],
            "gamma_eq_delta": a["gamma"] is not None and a["gamma"] == a["delta"],
        })
    changed = [f for f in report["files"] if f["frozen"] != f["eip197"]]
    report["summary"] = {
        "files_examined": len(report["files"]),
        "files_gamma_eq_delta": sum(f["gamma_eq_delta"] for f in report["files"]),
        "files_outcome_changed": len(changed),
        "files_frozen_verified_eip197_default_warning": sum(
            f["frozen"][0] == "VERIFIED_WITHIN_SCOPE" for f in changed),
        "rows_outcome_changed": sorted({f["row"] for f in changed}),
    }
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
