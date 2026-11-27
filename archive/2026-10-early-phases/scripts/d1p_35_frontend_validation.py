#!/usr/bin/env python3
"""Compile development-only Noir version fixtures and validate BindCheck v1.2.

No D1P-33 or D1P-36 project is an input to this program.  Downloads are exact
official release assets and are accepted only after their recorded SHA-256
matches.
"""

from __future__ import annotations

from datetime import datetime, timezone
import base64
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/D1P-35"
SOURCE = ROOT / "tests/d1/fixtures/noir_versions"
sys.path.insert(0, str(ROOT / "src"))

from bindcheck_d1.static_analyzer_v1 import load_producer  # noqa: E402


RELEASES = {
    3: "7506379c9e820ca7e1ed2bab6eb646f204cbfc89f62ae9c6e0b021bb96200e89",
    14: "2bb856a86e9e07ae94e052699ebd391426534d30fe43783bd6873f628a3a699b",
    15: "80414cb27eab37fd3f4fb21ac3c03b0ababa5eb4793d643db0bc42eb2c897488",
    16: "e21d6d09639831568850b365002e0c60456328155b143296ccf6fb3ca4cec794",
    17: "92a8703bb4f5b44f52afb3f91a487e1558ebc001b101441acc32054804b7b2b9",
    18: "ed67d9f3490a391f9ae2b454a7f6433df5abfe37e0bbdb0e4e28208da1ef9d41",
    19: "3d02143efcc06a5c991f69bb6bb770e639230549d64f35ed13defb44420b7a75",
    20: "10f58582f65c6e4c1036dc40be6109af581ced7f06b7845ebe1617c1dc01d304",
    21: "78cb9cbb4c9d173ef0b22a9eaf80a00fb43382c78868ae820e375424fd6f4e71",
    22: "445dac99258f867b016a05353eac7bf7c1cfee26b98b68cc851bb57ec569a91c",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(path: Path) -> dict:
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": sha256(path)}


def run(argv: list[str], cwd: Path | None = None) -> dict:
    started = time.monotonic()
    completed = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False)
    return {
        "argv": argv,
        "cwd": str((cwd or ROOT).resolve()),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "runtime_seconds": round(time.monotonic() - started, 6),
    }


def ensure_tool(version: int) -> tuple[Path, Path, dict]:
    archive = RAW / f"tools/nargo-1.0.0-beta.{version}-aarch64-apple-darwin.tar.gz"
    tool_dir = RAW / f"tools/noir-1.0.0-beta.{version}"
    nargo = tool_dir / "nargo"
    url = ("https://github.com/noir-lang/noir/releases/download/"
           f"v1.0.0-beta.{version}/nargo-aarch64-apple-darwin.tar.gz")
    fetch = None
    if not archive.is_file():
        archive.parent.mkdir(parents=True, exist_ok=True)
        fetch = run(["curl", "--fail", "--location", "--retry", "2",
                     "--output", str(archive), url])
        if fetch["returncode"]:
            raise RuntimeError(f"beta.{version} download failed: {fetch['stderr']}")
    if sha256(archive) != RELEASES[version]:
        raise RuntimeError(f"beta.{version} archive hash mismatch")
    if not nargo.is_file():
        tool_dir.mkdir(parents=True, exist_ok=True)
        extracted = run(["tar", "-xzf", str(archive), "-C", str(tool_dir)])
        if extracted["returncode"]:
            raise RuntimeError(f"beta.{version} extraction failed: {extracted['stderr']}")
    version_run = run([str(nargo), "--version"])
    if version_run["returncode"]:
        raise RuntimeError(f"beta.{version} version check failed")
    return archive, nargo, {"url": url, "fetch": fetch, "version_run": version_run}


def main() -> int:
    records = []
    for version in RELEASES:
        archive, nargo, retrieval = ensure_tool(version)
        workspace = RAW / f"version-fixtures/beta{version}"
        (workspace / "src").mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE / "Nargo.toml", workspace / "Nargo.toml")
        shutil.copy2(SOURCE / "src/main.nr", workspace / "src/main.nr")
        compile_run = run([str(nargo), "compile", "--program-dir", str(workspace)])
        if compile_run["returncode"]:
            raise RuntimeError(f"beta.{version} compile failed: {compile_run['stderr']}")
        artifact = workspace / "target/bindcheck_version_fixture.json"
        encoded = json.loads(artifact.read_text())
        compressed = base64.b64decode(encoded["bytecode"], validate=True)
        decoded = gzip.decompress(compressed)
        decoder = {"status": "UNSUPPORTED", "reason": None}
        try:
            producer = load_producer(artifact)
            decoder = {
                "status": "PASS",
                "decoder": producer["decoder"],
                "opcode_count": producer["opcode_count"],
                "opcode_counts": producer["opcode_counts"],
                "public_leaves": [
                    {key: item[key] for key in
                     ("path", "public_index", "witness", "occurrence_count")}
                    for item in producer["public_leaves"]
                ],
            }
        except Exception as exc:
            decoder["reason"] = f"{type(exc).__name__}:{exc}"
        records.append({
            "beta": version,
            "archive": record(archive),
            "nargo": record(nargo),
            "retrieval": retrieval,
            "compile": compile_run,
            "artifact": record(artifact),
            "noir_version": encoded["noir_version"],
            "compressed_sha256": hashlib.sha256(compressed).hexdigest(),
            "decoded_sha256": hashlib.sha256(decoded).hexdigest(),
            "decoded_bytes": len(decoded),
            "decoded_prefix_hex": decoded[:16].hex(),
            "decoder_result": decoder,
        })

    reference = records[1]["decoder_result"]
    supported = [item for item in records if 14 <= item["beta"] <= 22]
    match = all(
        item["decoder_result"]["status"] == "PASS"
        and item["decoder_result"]["opcode_counts"] == reference["opcode_counts"]
        and item["decoder_result"]["public_leaves"] == reference["public_leaves"]
        for item in supported
    )
    result = {
        "schema": "bindcheck.d1p35.frontend-validation/v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "development_only": True,
        "held_out_inputs_used": [],
        "source": [record(SOURCE / "Nargo.toml"), record(SOURCE / "src/main.nr")],
        "records": records,
        "beta14_through_beta22_public_leaves_and_occurrences_match": match,
        "beta3_supported": records[0]["decoder_result"]["status"] == "PASS",
    }
    output = RAW / "version-validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": record(output), "match": match,
                      "beta3_supported": result["beta3_supported"]}, indent=2))
    return 0 if match and not result["beta3_supported"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
