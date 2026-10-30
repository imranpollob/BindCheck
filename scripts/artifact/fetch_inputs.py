#!/usr/bin/env python3
"""Materialize the ignored inputs used by the BindCheck paper artifact.

The default ``tests`` profile is intentionally small.  ``evaluation`` also
builds every binding mutant and the D1P-31/D1P-34 consumer relations.
``xav`` adds the Node/Foundry runtime used by the automatic validator, and
``all`` selects both.  Downloads and clones are pinned before use; generated
objects are checked by path-independent semantic hashes where Noir embeds
absolute debug paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "results/raw"
TOOLS = RAW / "artifact-tools"
BIN = TOOLS / "bin"
DOWNLOADS = TOOLS / "downloads"
UPSTREAM = TOOLS / "upstream"
NPM_ROOT = TOOLS / "npm"
CRS_ROOT = TOOLS / "crs"
NPM_LOCK = ROOT / "scripts/artifact/npm-package-lock.json"

WARP_URL = "https://github.com/warptoad/warp-toad.git"
WARP_REV = "973e7d1e4b60d0d8a8ca299b0cabd9193b147ef8"
PAYY_URL = "https://github.com/polybase/payy.git"
PAYY_EARLIER_REV = "c4d2c9021b8fb9988816eb6987a734b830bfce15"
PAYY_REPAIRED_REV = "dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36"
POSEIDON_URL = "https://github.com/noir-lang/poseidon.git"
POSEIDON_03_REV = "0880c371e88e583d39515fd3f877538657ac41eb"
POSEIDON_011_REV = "ba04f0a3b53b2a2037debe41d55c1595b1bde507"
FORGE_STD_URL = "https://github.com/foundry-rs/forge-std.git"
FORGE_STD_REV = "77041d2ce690e692d6e03cc812b57d1ddaa4d505"

# The paper run was Darwin/arm64.  The two solc release binaries are the
# official Darwin x86_64 builds and run under Rosetta on Apple silicon.  Their
# compiler long versions are identical to the native binaries used originally.
DOWNLOAD_SPECS = {
    "nargo-beta22": {
        "url": "https://github.com/noir-lang/noir/releases/download/v1.0.0-beta.22/nargo-aarch64-apple-darwin.tar.gz",
        "archive_sha256": "445dac99258f867b016a05353eac7bf7c1cfee26b98b68cc851bb57ec569a91c",
        "member": "nargo",
        "binary_sha256": "37f7d55d9795af0da3b471db2306e0296fa34c528386a828ce556fc3ebbf6e7b",
    },
    "nargo-beta14": {
        "url": "https://github.com/noir-lang/noir/releases/download/v1.0.0-beta.14/nargo-aarch64-apple-darwin.tar.gz",
        "archive_sha256": "2bb856a86e9e07ae94e052699ebd391426534d30fe43783bd6873f628a3a699b",
        "member": "nargo",
        "binary_sha256": "a0528f1c7a070f51addcefc707f889f2f9cbd85b17261e43f4b8dcf3d1d81eb8",
    },
    "solc-0.8.20": {
        "url": "https://github.com/ethereum/solidity/releases/download/v0.8.20/solc-macos",
        "archive_sha256": "fc329945e0068e4e955d0a7b583776dc8d25e72ab657a044618a7ce7dd0519aa",
        "binary_sha256": "fc329945e0068e4e955d0a7b583776dc8d25e72ab657a044618a7ce7dd0519aa",
    },
    "solc-0.8.29": {
        "url": "https://github.com/ethereum/solidity/releases/download/v0.8.29/solc-macos",
        "archive_sha256": "66fabdd17c8c0091311997ec7d17b4d92e1b7b2c2d213dc14e4ff28c3de864d1",
        "binary_sha256": "66fabdd17c8c0091311997ec7d17b4d92e1b7b2c2d213dc14e4ff28c3de864d1",
    },
    "foundry-1.8.6": {
        "url": "https://github.com/foundry-rs/foundry/releases/download/v1.8.6/foundry_v1.8.6_darwin_arm64.tar.gz",
        "archive_sha256": "d6bc05ee937b4308bded496068728c8ba140abe49dd7527f37e025bc335b91ec",
        "members": {
            "forge": "f63f468bdeb5ea66b0379722657ddfacdd0141f1fab80fe542da345eb2961f07",
            "anvil": "04edadf755498160912c6ee799ada3ccef3af338a201b1d03b424a5d45969f45",
        },
    },
}

# @aztec/bb.js 5.0.0 requests these exact ranges with its default node SRS.
CRS_SPECS = {
    "bn254_g1_compressed.dat": {
        "url": "https://crs.aztec-cdn.foundation/g1_compressed.dat",
        "range": "bytes=0-16777215", "bytes": 16777216,
        "sha256": "1d03ebeb73e1a6d426e44a2ccc88b04125ca185ab9d1679817380502a723fa80",
    },
    "bn254_g2.dat": {
        "url": "https://crs.aztec-cdn.foundation/g2.dat", "bytes": 128,
        "sha256": "01797bfc4de5a96f0e516a9ea4537d18786dc30cb991aca4274c95822b69c32f",
    },
    "grumpkin_g1_v2.flat.dat": {
        "url": "https://crs.aztec-cdn.foundation/grumpkin_g1_v2.dat",
        "range": "bytes=0-4194303", "bytes": 4194304,
        "sha256": "64236c9455e75aeea77a94587ea607eed2e978d2609a421d66bf10bb9698b8fd",
    },
}

SOURCE_HASHES = {
    "warptoad": "323a1cf26c7449f67cf277ff0a46c31e12f725c555f9fa165d5a60011e122c39",
    "warptoad_msrc": "64ec0efd0df934afc46f06be76764b74b97b9ac554e1bd72add7ce0a630373e3",
    "payy_rollup": "7062065cc95f447fea8bb28242d51c836c3cf9e39f1625180ecf9c240a5ffd8f",
}

NOIR_COMPONENT_HASHES = {
    "warptoad-pinned": {
        "noir_version": "5626f05628893445b7f53c7dc0df7984c02a4f482b13ec6ad3c4d2bc07ab656b",
        "bytecode": "61c782664fb70b7ed76ec1da63775383f3b6923ce67230e6e2b6a569a112d8bc",
        "abi": "9d1778b43162df9acb7e845b91291369c72af15c1040a194f3316cf3be82edbf",
        "archived_file_sha256": "7190813f623967b79ba80a1635536fcc9c8524c1d1cb9f00696832f644b38327",
    },
    "warptoad-m-dom": {
        "noir_version": "5626f05628893445b7f53c7dc0df7984c02a4f482b13ec6ad3c4d2bc07ab656b",
        "bytecode": "20c874ae63e1c1af82f6323a1fde15fb95ea22f10b0d8d7f7960de27d809765e",
        "abi": "c26a875d6217ee4c754cf6cdc6c4c21534a7cf30b3a633d8ea67bdaf428845c2",
        "archived_file_sha256": "db1a0a17b2717cce2fe9a9a01e114632634fcf43f0f813d062dfa9c660aa7f2f",
    },
    "payy-earlier": {
        "noir_version": "0c6f5113ff62be59ea448d158c5857d6db39a1cdb114f2e7dabfd6588552a8c7",
        "bytecode": "294ac544456be546cfab2944e62bf2f8d8dd30fbfbcd06d046bbf4a0e26d4a73",
        "abi": "eceebb221048e3c6cba1de65d55058c0d3bf80f14c7a1eb1bbbd5186377b87dd",
        "archived_file_sha256": "83b75a4af7434c9c722f19f7638404bd45ddbbd2ec0ff85b779bf89ca31d3b2c",
    },
    "payy-check-added": {
        "noir_version": "0c6f5113ff62be59ea448d158c5857d6db39a1cdb114f2e7dabfd6588552a8c7",
        "bytecode": "c19af2e47da4a45dd6636dbcd9d2b791e90f0f431e189f96cc74a839308e6c89",
        "abi": "fa212fa8c40e0765d45fb4fd7171b3c2eaacc360c05919a6553bdffd29c8e47c",
        "archived_file_sha256": "866b1800f8ad9a95623cb720a408acd234a7466e13242461b934249724c71f42",
    },
}

RELATION_SEMANTIC_HASHES = {
    "pinned": "b3da6a440f0395b20f8fdb818d6456666d8f89e0b37de6e95e412d057f4541a6",
    "m-src": "9b3763cf1dd8efee12d76a2596c3fcef1136157f52fece25fe7ba690209b4a52",
    "payy-baseline": "3e999a2ac5f804e534c3da49895fdc04293bb02dae8aa5a0dd00f9681e196a12",
    "payy-check-added": "3e999a2ac5f804e534c3da49895fdc04293bb02dae8aa5a0dd00f9681e196a12",
}

# These fields are non-semantic provenance embedded in the archived relation
# JSON.  The extractor is first run against the fresh build and its semantic
# hash is checked.  We then restore the historical provenance envelope so the
# resulting bytes also satisfy the frozen content-addressed consumer index.
# The fresh build paths and hashes remain in input-materialization.json.
ARCHIVED_RELATION_PROVENANCE = {
    "pinned": {
        "build_info": "/Users/imranpollob/Coding/bc/bindcheck-d1-paper/results/raw/D1P-12R/workspace/source/backend/artifacts/build-info/solc-0_8_29-a52609323fd0bce65aec2ea493681a10c5c96cfa.json",
        "build_info_sha256": "ee1cc02abcaf96af8c8349cd02fa4bdc09db41e6ac8f7bc5b74434eb31a9068e",
        "compiler_output": "/Users/imranpollob/Coding/bc/bindcheck-d1-paper/results/raw/D1P-12R/workspace/source/backend/artifacts/build-info/solc-0_8_29-a52609323fd0bce65aec2ea493681a10c5c96cfa.output.json",
        "compiler_output_sha256": "708c3dc4dc1cc61a689936d77aaaa48ad3ee752fe83352014239f0ebedb8c07e",
        "library_effect_models": "/Users/imranpollob/Coding/bc/bindcheck-lane-c/prototypes/d1p16/library_effect_models.v1.json",
        "source": "/Users/imranpollob/Coding/bc/bindcheck-d1-paper/results/raw/D1P-12R/workspace/source/backend/contracts/core/WarpToadCore.sol",
    },
    "m-src": {
        "build_info": "/Users/imranpollob/Coding/bc/bindcheck-d1-paper/results/raw/D1P-19/workspace/source/backend/artifacts/build-info/solc-0_8_29-aec81eab73589a53b8dc9a27808995da0b1e3bbb.json",
        "build_info_sha256": "93ebc781ccd3880d0965be0cb1c9df26731af559f2e56cee9ca5d8ceee9aaa14",
        "compiler_output": "/Users/imranpollob/Coding/bc/bindcheck-d1-paper/results/raw/D1P-19/workspace/source/backend/artifacts/build-info/solc-0_8_29-aec81eab73589a53b8dc9a27808995da0b1e3bbb.output.json",
        "compiler_output_sha256": "04fa7afbc535283117919968818838a6b9ffd63af40c490a35f4cd6d108cbe03",
        "library_effect_models": "/Users/imranpollob/Coding/bc/bindcheck-lane-c/prototypes/d1p16/library_effect_models.v1.json",
        "source": "/Users/imranpollob/Coding/bc/bindcheck-d1-paper/results/raw/D1P-19/workspace/source/backend/contracts/core/WarpToadCore.sol",
    },
}

ARCHIVED_PAYY_SOURCE = {
    "payy-baseline": "/Users/imranpollob/Coding/bc/bindcheck-d1-paper/benchmarks/binding-mutants/baselines/RollupV1.sol",
    "payy-check-added": "/Users/imranpollob/Coding/bc/BindCheck/tools/cases/payy-history/eth/contracts/rollup3/RollupV1.sol",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


class Materializer:
    def __init__(self, profile: str, force: bool, verify_only: bool):
        self.profile = profile
        self.force = force
        self.verify_only = verify_only
        self.started = time.time()
        self.records: list[dict[str, Any]] = []
        self.commands: list[dict[str, Any]] = []

    def run(self, argv: list[str | Path], *, cwd: Path | None = None,
            env: dict[str, str] | None = None, timeout: int = 1800,
            stdin: str | None = None) -> subprocess.CompletedProcess[str]:
        cmd = [str(item) for item in argv]
        started = time.monotonic()
        complete = subprocess.run(
            cmd, cwd=cwd or ROOT, env={**os.environ, **(env or {})},
            input=stdin, text=True, capture_output=True, timeout=timeout,
            check=False,
        )
        self.commands.append({
            "argv": cmd, "cwd": str(cwd or ROOT), "returncode": complete.returncode,
            "runtime_seconds": round(time.monotonic() - started, 3),
            "stdout_tail": complete.stdout[-2000:], "stderr_tail": complete.stderr[-2000:],
        })
        if complete.returncode:
            raise RuntimeError(f"command failed ({complete.returncode}): {' '.join(cmd)}\n{complete.stderr[-2000:]}")
        return complete

    def require_darwin_arm(self) -> None:
        if platform.system() != "Darwin" or platform.machine() not in {"arm64", "aarch64"}:
            raise SystemExit(
                "the recorded binary checksums are for Darwin arm64; use the documented "
                "macOS artifact environment or extend DOWNLOAD_SPECS with a reviewed platform pin"
            )

    def download(self, name: str, spec: dict[str, Any]) -> Path:
        DOWNLOADS.mkdir(parents=True, exist_ok=True)
        suffix = ".tar.gz" if spec["url"].endswith(".tar.gz") else ".bin"
        destination = DOWNLOADS / f"{name}{suffix}"
        if not destination.is_file() or sha256(destination) != spec["archive_sha256"]:
            if self.verify_only:
                raise FileNotFoundError(destination)
            temporary = destination.with_suffix(destination.suffix + ".part")
            # Use the system curl trust store.  The python.org CPython build on
            # macOS may not be linked to the managed CA bundle even when curl
            # and git use it correctly; TLS verification remains enabled.
            self.run(["curl", "--fail", "--location", "--retry", "2",
                      "--output", temporary, spec["url"]], timeout=600)
            got = sha256(temporary)
            if got != spec["archive_sha256"]:
                temporary.unlink(missing_ok=True)
                raise ValueError(f"{name}: archive sha256 {got} != {spec['archive_sha256']}")
            temporary.replace(destination)
        return destination

    @staticmethod
    def extract_member(archive: Path, member: str, destination: Path) -> None:
        with tarfile.open(archive, "r:gz") as tar:
            candidate = next((item for item in tar.getmembers()
                              if Path(item.name).name == member and item.isfile()), None)
            if candidate is None:
                raise ValueError(f"{archive}: missing {member}")
            source = tar.extractfile(candidate)
            if source is None:
                raise ValueError(f"{archive}: cannot extract {member}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("wb") as output:
                shutil.copyfileobj(source, output)
        destination.chmod(destination.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def install_tools(self, include_foundry: bool) -> None:
        self.require_darwin_arm()
        BIN.mkdir(parents=True, exist_ok=True)
        names = ["nargo-beta22", "nargo-beta14", "solc-0.8.20", "solc-0.8.29"]
        if include_foundry:
            names.append("foundry-1.8.6")
        for name in names:
            spec = DOWNLOAD_SPECS[name]
            archive = self.download(name, spec)
            if "members" in spec:
                for member, expected in spec["members"].items():
                    target = BIN / member
                    if not target.is_file() or sha256(target) != expected:
                        self.extract_member(archive, member, target)
                    if sha256(target) != expected:
                        raise ValueError(f"{member}: binary checksum mismatch")
            else:
                target = BIN / name
                if not target.is_file() or sha256(target) != spec["binary_sha256"]:
                    if "member" in spec:
                        self.extract_member(archive, spec["member"], target)
                    else:
                        shutil.copyfile(archive, target)
                        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                if sha256(target) != spec["binary_sha256"]:
                    raise ValueError(f"{name}: binary checksum mismatch")
            binary_hashes = (spec["members"] if "members" in spec
                             else {name: spec["binary_sha256"]})
            self.records.append({"kind": "tool", "name": name, "url": spec["url"],
                                 "archive_sha256": spec["archive_sha256"],
                                 "binary_sha256": binary_hashes})

        version_commands = {
            "nargo-beta22": [BIN / "nargo-beta22", "--version"],
            "nargo-beta14": [BIN / "nargo-beta14", "--version"],
            "solc-0.8.20": [BIN / "solc-0.8.20", "--version"],
            "solc-0.8.29": [BIN / "solc-0.8.29", "--version"],
        }
        if include_foundry:
            version_commands["foundry-1.8.6"] = [BIN / "forge", "--version"]
        for name, command in version_commands.items():
            completed = self.run(command)
            record = next(item for item in reversed(self.records)
                          if item.get("kind") == "tool" and item.get("name") == name)
            record["reported_version"] = (completed.stdout or completed.stderr).strip()
        if include_foundry:
            # anvil has an independently checked member hash; retain its own
            # version text as well as forge's release identity.
            completed = self.run([BIN / "anvil", "--version"])
            record = next(item for item in reversed(self.records)
                          if item.get("kind") == "tool"
                          and item.get("name") == "foundry-1.8.6")
            record["anvil_reported_version"] = (completed.stdout or completed.stderr).strip()

    def install_crs(self) -> None:
        CRS_ROOT.mkdir(parents=True, exist_ok=True)
        for name, spec in CRS_SPECS.items():
            destination = CRS_ROOT / name
            valid = (destination.is_file() and destination.stat().st_size == spec["bytes"]
                     and sha256(destination) == spec["sha256"])
            if not valid:
                if self.verify_only:
                    raise FileNotFoundError(destination)
                temporary = destination.with_suffix(destination.suffix + ".part")
                command = ["curl", "--fail", "--location", "--retry", "2"]
                if "range" in spec:
                    command += ["--header", f"Range: {spec['range']}"]
                command += ["--output", temporary, spec["url"]]
                self.run(command, timeout=900)
                if temporary.stat().st_size != spec["bytes"] or sha256(temporary) != spec["sha256"]:
                    temporary.unlink(missing_ok=True)
                    raise ValueError(f"{name}: CRS size/hash mismatch")
                temporary.replace(destination)
            self.records.append({"kind": "crs", "name": name, "url": spec["url"],
                                 "bytes": spec["bytes"], "sha256": spec["sha256"]})

    def clone_at(self, name: str, url: str, revision: str) -> Path:
        destination = UPSTREAM / name
        if not destination.exists():
            if self.verify_only:
                raise FileNotFoundError(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            self.run(["git", "clone", "--filter=blob:none", "--no-checkout", url, destination])
        if not (destination / ".git").exists():
            raise ValueError(f"{destination} is not a git checkout")
        if not self.verify_only:
            self.run(["git", "fetch", "--depth", "1", "origin", revision], cwd=destination)
            self.run(["git", "checkout", "--detach", revision], cwd=destination)
        got = self.run(["git", "rev-parse", "HEAD"], cwd=destination).stdout.strip()
        if got != revision:
            raise ValueError(f"{name}: revision {got} != {revision}")
        dirty = self.run(["git", "status", "--porcelain"], cwd=destination).stdout.strip()
        if dirty:
            raise ValueError(f"{name}: upstream cache is dirty: {dirty}")
        self.records.append({"kind": "upstream", "name": name, "url": url, "revision": got})
        return destination

    def replace_tree(self, source: Path, destination: Path,
                     ignore: Any | None = None) -> None:
        if destination.exists() or destination.is_symlink():
            if not self.force:
                return
            if destination.is_symlink() or destination.is_file():
                destination.unlink()
            else:
                shutil.rmtree(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination, symlinks=False, ignore=ignore)

    @staticmethod
    def patch_poseidon_manifest(manifest: Path, relative_vendor: str) -> None:
        text = manifest.read_text()
        updated, count = re.subn(
            r'poseidon\s*=\s*\{\s*tag\s*=\s*"v(?:0\.3\.0|0\.1\.1)",\s*git\s*=\s*"https://github\.com/noir-lang/poseidon"\s*\}',
            f'poseidon = {{ path = "{relative_vendor}" }}', text,
        )
        if count:
            manifest.write_text(updated)

    def stage_sources(self) -> tuple[Path, Path, Path, Path]:
        warp = self.clone_at("warptoad", WARP_URL, WARP_REV)
        poseidon03 = self.clone_at("poseidon-v0.3.0", POSEIDON_URL, POSEIDON_03_REV)
        payy_a_cache = self.clone_at("payy-earlier", PAYY_URL, PAYY_EARLIER_REV)
        payy_b_cache = self.clone_at("payy-check-added", PAYY_URL, PAYY_REPAIRED_REV)
        poseidon011 = self.clone_at("poseidon-v0.1.1", POSEIDON_URL, POSEIDON_011_REV)

        ignore = shutil.ignore_patterns(".git", "node_modules", "target", "artifacts", "cache", "dist")
        d13_source = RAW / "D1P-13/workspace/source"
        pinned = RAW / "D1P-19/workspace/pinned-source"
        msrc = RAW / "D1P-19/workspace/source"
        self.replace_tree(warp, d13_source, ignore)
        self.replace_tree(warp, pinned, ignore)
        self.replace_tree(warp, msrc, ignore)

        for root in (d13_source, pinned, msrc):
            vendor = root / "backend/circuits/vendor/poseidon-v0.3.0"
            self.replace_tree(poseidon03, vendor, shutil.ignore_patterns(".git"))
            for manifest in (root / "backend/circuits").glob("*/Nargo.toml"):
                self.patch_poseidon_manifest(manifest, "../vendor/poseidon-v0.3.0")

        pinned_source = pinned / "backend/contracts/core/WarpToadCore.sol"
        if sha256(pinned_source) != SOURCE_HASHES["warptoad"]:
            raise ValueError("pinned WarpToadCore.sol disagrees with the recorded D1P-19 hash")
        msrc_source = msrc / "backend/contracts/core/WarpToadCore.sol"
        if sha256(msrc_source) != SOURCE_HASHES["warptoad_msrc"]:
            original = msrc_source.read_text()
            old = '        require(isValidLocalRoot(_localRoot), "_localRoot unknown"); \n'
            new = "        // D1P-19 INJECTED M-SRC: remove K2 only; producer/verifier are unchanged.\n"
            if original.count(old) != 1:
                raise ValueError("M-SRC mutation site count is not one")
            mutated = original.replace(old, new)
            if not mutated.endswith("\n"):
                mutated += "\n"
            msrc_source.write_text(mutated)
        if sha256(msrc_source) != SOURCE_HASHES["warptoad_msrc"]:
            raise ValueError("M-SRC source disagrees with the recorded D1P-19 hash")

        payy_a = ROOT / "tools/cases/payy-c4d2c90"
        payy_b = ROOT / "tools/cases/payy-history"
        self.replace_tree(payy_a_cache, payy_a, shutil.ignore_patterns(".git", "target", "node_modules"))
        self.replace_tree(payy_b_cache, payy_b, shutil.ignore_patterns(".git", "target", "node_modules"))
        for checkout in (payy_a, payy_b):
            vendor = checkout / "noir/vendor/poseidon-v0.1.1"
            self.replace_tree(poseidon011, vendor, shutil.ignore_patterns(".git"))
            self.patch_poseidon_manifest(checkout / "noir/agg_agg/Nargo.toml", "../vendor/poseidon-v0.1.1")
            rollup = checkout / "eth/contracts/rollup3/RollupV1.sol"
            if sha256(rollup) != SOURCE_HASHES["payy_rollup"]:
                raise ValueError(f"{checkout.name}: RollupV1.sol hash mismatch")
        return d13_source, pinned, msrc, payy_a

    def install_npm_inputs(self, include_xav: bool) -> Path:
        packages = [
            "@openzeppelin/contracts@5.6.1",
            "@zk-kit/lazy-imt.sol@2.0.0-beta.12",
            "poseidon-solidity@0.0.5",
        ]
        if include_xav:
            packages += [
                "@aztec/bb.js@5.0.0", "hardhat@3.3.0",
                "@nomicfoundation/hardhat-toolbox-viem@5.0.3",
                "@nomicfoundation/hardhat-viem@3.0.4",
                "@nomicfoundation/hardhat-verify@3.0.7",
                "@nomicfoundation/hardhat-ignition@3.0.7",
                "@nomicfoundation/hardhat-ignition-viem@3.0.7",
                "@nomicfoundation/ignition-core@3.0.7",
                "@nomicfoundation/hardhat-keystore@3.0.5",
                "@nomicfoundation/hardhat-network-helpers@3.0.4",
                "@nomicfoundation/hardhat-viem-assertions@3.0.5",
                "@nomicfoundation/hardhat-node-test-runner@3.0.5",
                "tsx@4.21.0", "viem@2.47.10", "poseidon-lite@0.3.0",
                "@zkpassport/poseidon2@0.6.2",
            ]
        package_json = {"name": "bindcheck-artifact-runtime", "private": True,
                        "version": "1.0.0", "dependencies": {
                            item.rsplit("@", 1)[0]: item.rsplit("@", 1)[1] for item in packages
                        }}
        NPM_ROOT.mkdir(parents=True, exist_ok=True)
        write_json(NPM_ROOT / "package.json", package_json)
        if not self.verify_only:
            if include_xav and NPM_LOCK.is_file():
                shutil.copyfile(NPM_LOCK, NPM_ROOT / "package-lock.json")
                self.run(["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"],
                         cwd=NPM_ROOT, timeout=1800)
            else:
                self.run(["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund", "--save-exact"],
                         cwd=NPM_ROOT, timeout=1800)
        node_modules = NPM_ROOT / "node_modules"
        for package, version in package_json["dependencies"].items():
            metadata = json.loads((node_modules / package / "package.json").read_text())
            if metadata["version"] != version:
                raise ValueError(f"{package}: {metadata['version']} != {version}")
        for backend in (
            RAW / "D1P-19/workspace/pinned-source/backend",
            RAW / "D1P-19/workspace/source/backend",
        ):
            link = backend / "node_modules"
            if link.exists() or link.is_symlink():
                if link.is_symlink() and link.resolve() == node_modules.resolve():
                    continue
                if not self.force:
                    continue
                if link.is_symlink() or link.is_file():
                    link.unlink()
                else:
                    shutil.rmtree(link)
            link.symlink_to(node_modules, target_is_directory=True)
        self.records.append({"kind": "npm", "packages": package_json["dependencies"],
                             "package_lock_sha256": sha256(NPM_ROOT / "package-lock.json")})
        return node_modules

    @staticmethod
    def noir_component_hashes(path: Path) -> dict[str, str]:
        value = json.loads(path.read_text())
        output = {}
        for key in ("noir_version", "bytecode", "abi"):
            item = value[key]
            payload = item.encode() if isinstance(item, str) else canonical(item)
            output[key] = sha256_bytes(payload)
        return output

    def check_noir_artifact(self, label: str, path: Path) -> None:
        expected = NOIR_COMPONENT_HASHES[label]
        observed = self.noir_component_hashes(path)
        failures = {key: (observed[key], expected[key]) for key in observed
                    if observed[key] != expected[key]}
        if failures:
            raise ValueError(f"{label}: semantic component mismatch: {failures}")
        self.records.append({
            "kind": "noir-artifact", "label": label, "path": str(path.relative_to(ROOT)),
            "sha256": sha256(path), "archived_file_sha256": expected["archived_file_sha256"],
            "exact_archived_match": sha256(path) == expected["archived_file_sha256"],
            "path_independent_component_hashes": observed,
            "component_hashes_match_archived_record": True,
        })

    def build_noir_inputs(self, d13_source: Path, payy_a: Path) -> None:
        pinned_dir = d13_source / "backend/circuits/withdraw"
        self.run([BIN / "nargo-beta22", "compile"], cwd=pinned_dir, timeout=600)
        pinned_artifact = pinned_dir / "target/withdraw.json"
        self.check_noir_artifact("warptoad-pinned", pinned_artifact)

        d15_backend = RAW / "D1P-15/workspace/source/backend"
        self.replace_tree(d13_source / "backend", d15_backend,
                          shutil.ignore_patterns("target", "node_modules", "artifacts", "cache"))
        mutants = TOOLS / "generated/d1p15-mutants"
        if mutants.exists() and self.force:
            shutil.rmtree(mutants)
        if not mutants.exists():
            self.run([
                sys.executable, ROOT / "benchmarks/binding-mutants/make_mutants.py",
                "--baseline", ROOT / "benchmarks/binding-mutants/baselines",
                "--out", mutants, "--only", "WT-C03",
                "--record", TOOLS / "generated/d1p15-generation.json",
            ])
        shutil.copyfile(mutants / "WT-C03/warptoad-withdraw-main.nr",
                        d15_backend / "circuits/withdraw/src/main.nr")
        shutil.copyfile(mutants / "WT-C03/warptoad-nargo-hashing-lib.nr",
                        d15_backend / "circuits/nargo_hashing/src/lib.nr")
        self.run([BIN / "nargo-beta22", "compile"], cwd=d15_backend / "circuits/withdraw", timeout=600)
        mdom = d15_backend / "circuits/withdraw/target/withdraw.json"
        artifact_destination = RAW / "D1P-15/artifacts/m-dom-withdraw.json"
        artifact_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(mdom, artifact_destination)
        self.check_noir_artifact("warptoad-m-dom", artifact_destination)
        honest = d15_backend / "circuits/withdraw/D1P15_12R.toml"
        honest.write_text(honest_witness_toml())
        expected_honest = "fd6830cbaec59466497c41fc178fd7aac7983a49c5289608736dd6ce720530b2"
        if sha256(honest) != expected_honest:
            raise ValueError("generated D1P15_12R.toml hash mismatch")
        self.records.append({"kind": "fixture", "path": str(honest.relative_to(ROOT)),
                             "sha256": expected_honest})

        for checkout, label in ((payy_a, "payy-earlier"),
                                (ROOT / "tools/cases/payy-history", "payy-check-added")):
            self.run([BIN / "nargo-beta14", "compile", "--package", "agg_agg"],
                     cwd=checkout / "noir", timeout=900)
            self.check_noir_artifact(label, checkout / "noir/target/agg_agg.json")

    @staticmethod
    def solidity_input(backend: Path, node_modules: Path, source_override: str | None = None) -> dict[str, Any]:
        sources: dict[str, dict[str, str]] = {}
        for path in sorted((backend / "contracts").rglob("*.sol")):
            key = "project/contracts/" + path.relative_to(backend / "contracts").as_posix()
            content = path.read_text()
            if key == "project/contracts/core/WarpToadCore.sol" and source_override is not None:
                content = source_override
            sources[key] = {"content": content}
        packages = (
            ("npm/@openzeppelin/contracts@5.6.1", node_modules / "@openzeppelin/contracts"),
            ("npm/@zk-kit/lazy-imt.sol@2.0.0-beta.12", node_modules / "@zk-kit/lazy-imt.sol"),
            ("npm/poseidon-solidity@0.0.5", node_modules / "poseidon-solidity"),
        )
        for prefix, directory in packages:
            for path in sorted(directory.rglob("*.sol")):
                sources[prefix + "/" + path.relative_to(directory).as_posix()] = {"content": path.read_text()}
        return {
            "language": "Solidity", "sources": sources,
            "settings": {
                "evmVersion": "cancun", "optimizer": {"enabled": True, "runs": 1},
                "remappings": [
                    "project/:@openzeppelin/contracts/=npm/@openzeppelin/contracts@5.6.1/",
                    "project/:@zk-kit/lazy-imt.sol/=npm/@zk-kit/lazy-imt.sol@2.0.0-beta.12/",
                    "project/:poseidon-solidity/=npm/poseidon-solidity@0.0.5/",
                    "npm/@zk-kit/lazy-imt.sol@2.0.0-beta.12/:poseidon-solidity/=npm/poseidon-solidity@0.0.5/",
                ],
                "outputSelection": {"*": {
                    "": ["ast"],
                    "*": ["abi", "evm.bytecode.object", "evm.bytecode.linkReferences"],
                }},
            },
        }

    def extract_warptoad_relation(self, label: str, backend: Path, source: Path,
                                  destination: Path, node_modules: Path) -> None:
        build_dir = TOOLS / "solidity-builds" / label
        build_dir.mkdir(parents=True, exist_ok=True)
        build_input = self.solidity_input(backend, node_modules, source.read_text())
        standard_input = build_dir / "standard-input.json"
        standard_output = build_dir / "standard-output.json"
        write_json(standard_input, build_input)
        complete = self.run([BIN / "solc-0.8.29", "--standard-json"],
                            cwd=build_dir, stdin=standard_input.read_text(), timeout=900)
        standard_output.write_text(complete.stdout)
        output = json.loads(complete.stdout)
        errors = [item for item in output.get("errors", []) if item.get("severity") == "error"]
        if errors:
            raise RuntimeError(f"{label}: solc errors: {errors[:2]}")
        build_id = "bindcheck-artifact-" + label
        metadata = build_dir / "build-info.json"
        compiler_output = build_dir / "build-info.output.json"
        write_json(metadata, {"_format": "hh-sol-build-info-1", "id": build_id,
                              "solcVersion": "0.8.29",
                              "solcLongVersion": "0.8.29+commit.ab55807c",
                              "input": build_input})
        write_json(compiler_output, {"_format": "hh-sol-build-info-1", "id": build_id,
                                     "output": output})
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.run([
            sys.executable, ROOT / "prototypes/d1p16/extract_relation.py",
            "--build-info", metadata, "--compiler-output", compiler_output,
            "--source", source, "--expected-source-sha256", sha256(source),
            "--output", destination,
        ], timeout=900)

    @staticmethod
    def relation_semantic_hash(path: Path, payy: bool = False) -> str:
        value = json.loads(path.read_text())
        if payy:
            value["source"] = "$SOURCE"
        else:
            value.pop("pins", None)
            value.pop("provenance", None)
        return sha256_bytes(canonical(value))

    def check_relation(self, label: str, path: Path, payy: bool = False) -> None:
        observed = self.relation_semantic_hash(path, payy)
        expected = RELATION_SEMANTIC_HASHES[label]
        if observed != expected:
            raise ValueError(f"{label}: semantic relation hash {observed} != {expected}")
        archived = {
            "pinned": "301ce67b6148bd889082f67b7c484cac55a52981d540917c21ac67f421293fd7",
            "m-src": "91929f0953313f05d67f3539edf8e7ef69cf51c423a83dfe941af1eb8cdce969",
            "payy-baseline": "f99293b4d71923bc82cb8eb1a3ce129db020b5c38dd166a448994e51aa2ac4f3",
            "payy-check-added": "ef6650312e1c9245b8b1cf5b3a22f194461f9f02cd214ae66c6a11ee7c7ae8e5",
        }[label]
        rebuilt_sha256 = sha256(path)
        relation = json.loads(path.read_text())
        if payy:
            relation["source"] = ARCHIVED_PAYY_SOURCE[label]
        else:
            relation["pins"].update(ARCHIVED_RELATION_PROVENANCE[label])
        write_json(path, relation)
        exact_sha256 = sha256(path)
        if exact_sha256 != archived:
            raise ValueError(f"{label}: archived serialization hash {exact_sha256} != {archived}")
        self.records.append({"kind": "consumer-relation", "label": label,
                             "path": str(path.relative_to(ROOT)), "sha256": sha256(path),
                             "archived_file_sha256": archived,
                             "fresh_provenance_sha256": rebuilt_sha256,
                             "semantic_sha256": observed, "semantic_hash_matches_archived": True})

    def build_warptoad_relations(self, pinned: Path, msrc: Path, node_modules: Path,
                                  evaluation: bool) -> None:
        pinned_source = pinned / "backend/contracts/core/WarpToadCore.sol"
        pinned_relation = RAW / "D1P-18/relation.json"
        self.extract_warptoad_relation("pinned", pinned / "backend", pinned_source,
                                      pinned_relation, node_modules)
        self.check_relation("pinned", pinned_relation)
        msrc_source = msrc / "backend/contracts/core/WarpToadCore.sol"
        msrc_relation = RAW / "D1P-21B/m-src-relation.json"
        self.extract_warptoad_relation("m-src", msrc / "backend", msrc_source,
                                      msrc_relation, node_modules)
        self.check_relation("m-src", msrc_relation)
        if not evaluation:
            return
        mutants = TOOLS / "generated/consumer-mutants"
        if mutants.exists() and self.force:
            shutil.rmtree(mutants)
        if not mutants.exists():
            self.run([
                sys.executable, ROOT / "benchmarks/binding-mutants/make_mutants.py",
                "--baseline", ROOT / "benchmarks/binding-mutants/baselines",
                "--out", mutants, "--only", "WT-S01,WT-S02,WT-S03,WT-S04,WT-S05,WT-S06,WT-S07,WT-S08,WT-S09",
                "--record", TOOLS / "generated/consumer-generation.json",
            ])
        for label in ("WT-S01", "WT-S02", "WT-S03", "WT-S05", "WT-S06", "WT-S07", "WT-S08", "WT-S09"):
            source = mutants / label / "WarpToadCore.sol"
            destination = RAW / f"D1P-31/consumer-relations/{label}/relation.json"
            self.extract_warptoad_relation(label, pinned / "backend", source, destination, node_modules)
            relation = json.loads(destination.read_text())
            self.records.append({"kind": "variant-relation", "label": label,
                                 "source_sha256": sha256(source), "relation_sha256": sha256(destination),
                                 "shape": relation["summary"]})

    def build_payy_relation(self, label: str, source: Path, artifact: Path,
                            node_modules: Path, destination: Path) -> None:
        sys.path.insert(0, str(ROOT / "src"))
        from bindcheck_d1.frontends.solidity_ast_v1_1 import extract  # type: ignore
        from bindcheck_d1.static_analyzer_v1 import load_producer  # type: ignore

        workspace = TOOLS / "payy-ast" / label
        # Compiler scratch is always disposable and scoped below artifact-tools.
        if workspace.exists():
            shutil.rmtree(workspace)
        (workspace / "contracts/rollup3").mkdir(parents=True, exist_ok=True)
        (workspace / "contracts/noir").mkdir(parents=True, exist_ok=True)
        (workspace / "stubs/proxy/utils").mkdir(parents=True, exist_ok=True)
        (workspace / "stubs/access").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, workspace / "contracts/rollup3/RollupV1.sol")
        shutil.copyfile(ROOT / "benchmarks/binding-mutants/baselines/payy-IVerifier.sol",
                        workspace / "contracts/noir/IVerifier.sol")
        shutil.copyfile(ROOT / "benchmarks/binding-mutants/baselines/payy-IUSDC.sol",
                        workspace / "contracts/IUSDC.sol")
        shutil.copyfile(ROOT / "benchmarks/binding-mutants/_stubs/payy/proxy/utils/Initializable.sol",
                        workspace / "stubs/proxy/utils/Initializable.sol")
        shutil.copyfile(ROOT / "benchmarks/binding-mutants/_stubs/payy/access/OwnableUpgradeable.sol",
                        workspace / "stubs/access/OwnableUpgradeable.sol")
        oz_link = workspace / "node_modules/@openzeppelin/contracts"
        oz_link.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(node_modules / "@openzeppelin/contracts", oz_link, symlinks=False)
        combined = workspace / "combined.json"
        complete = self.run([
            BIN / "solc-0.8.20", "--base-path", ".", "--include-path", "node_modules",
            "@openzeppelin/contracts-upgradeable/=stubs/", "--combined-json", "ast",
            "contracts/rollup3/RollupV1.sol",
        ], cwd=workspace, timeout=900)
        combined.write_text(complete.stdout)
        public_leaves = load_producer(artifact)["public_leaves"]
        relation = extract(combined, "contracts/rollup3/RollupV1.sol", source, public_leaves)
        write_json(destination, relation)
        self.check_relation(label, destination, payy=True)

    def build_payy_relations(self, payy_a: Path, node_modules: Path) -> None:
        self.build_payy_relation(
            "payy-baseline", ROOT / "benchmarks/binding-mutants/baselines/RollupV1.sol",
            payy_a / "noir/target/agg_agg.json", node_modules,
            RAW / "D1P-34/consumer-relations/payy-baseline.json",
        )
        payy_b = ROOT / "tools/cases/payy-history"
        self.build_payy_relation(
            "payy-check-added", payy_b / "eth/contracts/rollup3/RollupV1.sol",
            payy_b / "noir/target/agg_agg.json", node_modules,
            RAW / "D1P-34/consumer-relations/payy-check-added.json",
        )

    def write_canonical_state_subset(self) -> None:
        # X-AV reads only S_SRC.burns.  These values are the hash-checked output
        # of the two owned-local D1P-19 burn executions, retained here as the
        # minimum replay input rather than pretending to regenerate tx hashes.
        state = {
            "schema": "bindcheck.d1p19.canonical-states/v1-artifact-subset",
            "source_full_record_sha256": "a8030d0c03112d457942c235a99ab9b57702301e49fb137507ef1e1032848b65",
            "S_SRC": {"burns": [
                {"amount": "5000000000000000000", "secret": "1234", "nullifierPreimage": "4321",
                 "preCommitment": "6623066489464621701802254125941223588827815953538474237249022404516174581199",
                 "commitment": "18657061007963497385873439993474320070394536285434801550476755170557711333402",
                 "root": "20419743986860794548232381865258329306313806197552198584473571389746156968437",
                 "leafIndex": 0},
                {"amount": "4000000000000000000", "secret": "12341111111", "nullifierPreimage": "432111111",
                 "preCommitment": "21659646677758266371225015768806895816705151884358407013845216249551404098882",
                 "commitment": "12857004527284668767542651087524200021739373867315891590958957555169489329792",
                 "root": "16394615154364444302767658388832134810776939818926555987100142738213167520957",
                 "leafIndex": 1},
            ]},
        }
        path = RAW / "D1P-19/canonical-states.json"
        write_json(path, state)
        self.records.append({"kind": "archived-replay-subset", "path": str(path.relative_to(ROOT)),
                             "sha256": sha256(path),
                             "source_full_record_sha256": state["source_full_record_sha256"]})

    def build_mutants(self, node_modules: Path) -> None:
        output_root = RAW / "X-BM"
        summary = output_root / "build-summary.tsv"
        if summary.is_file():
            rows = [line.split("\t") for line in summary.read_text().splitlines() if line]
            mutant_dirs = [path for path in (output_root / "mutants").glob("*") if path.is_dir()]
            complete = (len(rows) == 30 and all(len(row) > 1 and row[1] == "0" for row in rows)
                        and len(mutant_dirs) == 30 and all(any(path.iterdir()) for path in mutant_dirs))
            if complete and not self.force:
                self.records.append({"kind": "binding-mutants", "count": 30,
                                     "build_summary_sha256": sha256(summary), "reused": True})
                return
        if output_root.exists():
            if not self.force:
                raise ValueError("partial X-BM output exists; rerun with --force to replace this scoped output")
            shutil.rmtree(output_root)
        env = {
            "BINDCHECK_ROOT": str(ROOT),
            "BINDCHECK_WARPTOAD_NODE_MODULES": str(node_modules),
            "BINDCHECK_NARGO_22": str(BIN / "nargo-beta22"),
            "BINDCHECK_NARGO_14": str(BIN / "nargo-beta14"),
            "BINDCHECK_SOLC_0_8_20": str(BIN / "solc-0.8.20"),
            "BINDCHECK_SOLC_0_8_29": str(BIN / "solc-0.8.29"),
            "OUT": str(output_root),
        }
        self.run(["sh", ROOT / "benchmarks/binding-mutants/build.sh"], env=env, timeout=3600)
        summary = output_root / "build-summary.tsv"
        rows = [line.split("\t") for line in summary.read_text().splitlines() if line]
        if len(rows) != 30 or any(row[1] != "0" for row in rows):
            raise ValueError("binding-mutant build did not compile all 30 targets")
        self.records.append({"kind": "binding-mutants", "count": 30,
                             "build_summary_sha256": sha256(summary)})

    def write_environment(self) -> None:
        env = TOOLS / "artifact-env.sh"
        env.parent.mkdir(parents=True, exist_ok=True)
        env.write_text(
            "# Generated by scripts/artifact/fetch_inputs.py\n"
            f"export BINDCHECK_ROOT={shell_quote(str(ROOT))}\n"
            f"export BINDCHECK_PAYY_ROOT={shell_quote(str(ROOT))}\n"
            f"export BINDCHECK_NARGO_22={shell_quote(str(BIN / 'nargo-beta22'))}\n"
            f"export BINDCHECK_NARGO_14={shell_quote(str(BIN / 'nargo-beta14'))}\n"
            f"export BINDCHECK_SOLC_0_8_20={shell_quote(str(BIN / 'solc-0.8.20'))}\n"
            f"export BINDCHECK_SOLC_0_8_29={shell_quote(str(BIN / 'solc-0.8.29'))}\n"
            f"export BINDCHECK_WARPTOAD_NODE_MODULES={shell_quote(str(NPM_ROOT / 'node_modules'))}\n"
            f"export BINDCHECK_WARPTOAD_BUILDINFO={shell_quote(str(TOOLS / 'solidity-builds/pinned'))}\n"
            f"export BINDCHECK_FORGE_STD={shell_quote(str(UPSTREAM / 'forge-std'))}\n"
            f"export CRS_PATH={shell_quote(str(CRS_ROOT))}\n"
            f"export PATH={shell_quote(str(BIN))}:$PATH\n"
        )

    def execute(self) -> None:
        evaluation = self.profile in {"evaluation", "xav", "all"}
        xav = self.profile in {"xav", "all"}
        self.install_tools(include_foundry=xav)
        if xav:
            self.clone_at("forge-std", FORGE_STD_URL, FORGE_STD_REV)
            self.install_crs()
        d13_source, pinned, msrc, payy_a = self.stage_sources()
        node_modules = self.install_npm_inputs(include_xav=xav)
        self.build_noir_inputs(d13_source, payy_a)
        self.build_warptoad_relations(pinned, msrc, node_modules, evaluation)
        self.build_payy_relations(payy_a, node_modules)
        self.write_canonical_state_subset()
        if evaluation:
            self.build_mutants(node_modules)
        self.write_environment()
        report = {
            "schema": "bindcheck.reproducibility-inputs/v1",
            "profile": self.profile, "root": str(ROOT),
            "platform": {"system": platform.system(), "machine": platform.machine(),
                         "python": platform.python_version()},
            "runtime_seconds": round(time.time() - self.started, 3),
            "records": self.records, "commands": self.commands,
            "status": "PASS",
            "hash_policy": (
                "exact hashes for source and tool bytes; canonical component hashes for Noir "
                "artifacts; canonical semantic hashes are checked for freshly extracted relations, "
                "then their historical provenance envelopes are restored and exact archived JSON "
                "hashes are checked for the frozen content-addressed index"
            ),
        }
        write_json(TOOLS / "input-materialization.json", report)
        print(json.dumps({"status": "PASS", "profile": self.profile,
                          "records": len(self.records),
                          "runtime_seconds": report["runtime_seconds"],
                          "manifest": str((TOOLS / 'input-materialization.json').relative_to(ROOT))},
                         indent=2))


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def honest_witness_toml() -> str:
    zeros42 = ", ".join('"0x0"' for _ in range(42))
    evm = [
        "0x0", "0x2098f5fb9e239eab3ceac3f27b81e481dc3124d55ffed523a839ee8446b64864",
        "0x1069673dcdb12263df301a6ff584a7ec261a44cb9dc68df067a4774460b1f1e1",
        "0x18f43331537ee2af2e3d758d50f72106467c6eea50371dd528d57eb2b856d238",
        "0x7f9d837cb17b0d36320ffe93ba52345f1b728571a568265caac97559dbc952a",
        "0x2b94cf5e8746b3f5c9631f4c5df32907a699c58c94b2ad4d7b5cec1639183f55",
        "0x2dee93c5a666459646ea7d22cca9e1bcfed71e6951b953611d11dda32ea09d78",
        "0x78295e5a22b84e982cf601eb639597b8b0515a88cb5ac7fa8a4aabe3c87349d",
        "0x2fa5e5f18f6027a6501bec864564472a616b2e274a41211a444cbe3a99f3cc61",
        "0xe884376d0d8fd21ecb780389e941f66e45e7acce3e228ab3e2156a614fcd747",
        "0x1b7201da72494f1e28717ad1a52eb469f95892f957713533de6175e5da190af2",
        "0x1f8d8822725e36385200c0b201249819a6e6e1e4650808b5bebc6bface7d7636",
        "0x2c5d82f66c914bafb9701589ba8cfcfb6162b0a12acf88a8d0879a0471b5f85a",
        "0x14c54148a0940bb820957f5adf3fa1134ef5c4aaa113f4646458f270e0bfbfd0",
        "0x190d33b12f986f961e10c0ee44d8b9af11be25588cad89d416118e4bf4ebe80c",
        "0x22f98aa9ce704152ac17354914ad73ed1167ae6596af510aa5b3649325e06c92",
        "0x2a7c7c9b6ce5880b9f6f228d72bf6a575a526f29c66ecceef8b753d38bba7323",
        "0x2e8186e558698ec1c67af9c14d463ffc470043c9c2988b954d75dd643f36b992",
        "0xf57c5571e9a4eab49e2c8cf050dae948aef6ead647392273546249d1c1ff10f",
        "0x1830ee67b5fb554ad5f63d4388800e1cfe78e310697d46e43c9ce36134f72cca",
        "0x2134e76ac5d21aab186c2be1dd8f84ee880a1e46eaf712f9d371b6df22191f3e",
        "0x19df90ec844ebc4ffeebd866f33859b0c051d8c958ee3aa88f8f8df3db91a5b1",
        "0x18cca2a66b5c0787981e69aefd84852d74af0e93ef4912b4648c05f722efe52b",
        "0x2388909415230d1b4d1304d2d54f473a628338f2efad83fadf05644549d2538d",
        "0x27171fb4a97b6cc0e9e8f543b5294de866a2af2c9c8d0b1d96e673e4529ed540",
        "0x2ff6650540f629fd5711a0bc74fc0d28dcb230b9392583e5f8d59696dde6ae21",
        "0x120c58f143d491e95902f7f5277778a2e0ad5168f6add75669932630ce611518",
        "0x1f21feb70d3f21b07bf853d5e5db03071ec495a0a565a21da2d665d279483795",
        "0x24be905fa71335e14c638cc0f66a8623a826e768068a9e968bb1a1dde18a72d2",
        "0xf8666b62ed17491c50ceadead57d4cd597ef3821d65c328744c74e553dac26d",
        "0x918d46bf52d98b034413f4a1a1c41594e7a7a3f6ae08cb43d1a2a230e1959ef",
        "0x1bbeb01b4c479ecde76917645e404dfa2e26f90d0afc5a65128513ad375c5ff2",
    ]
    qevm = ", ".join(f'"{item}"' for item in evm)
    return f'''# Generated from an existing frozen fixture by scripts/d1p15_prepare.py.
nullifier = "0x187ba16490abbc9983dd173e0d491aa5cb45d3aa1c2976716dec69a8680828b8"
chain_id = "0x7a69"
amount = "0x4563918244f40000"
giga_root = "0x2b94cf5e8746b3f5c9631f4c5df32907a699c58c94b2ad4d7b5cec1639183f55"
destination_local_root = "0x2d252a5fea4ed67e85d8e446324eb9d0153e997a7b75e04c95e5d6b48ac099f5"
aztec_warptoad_address = "0x0"
fee_factor = "0x3a143d8a"
priority_fee = "0x5f5e100"
max_fee = "0x4563918244f40000"
relayer_address = "0x70997970c51812dc3a010c7d01b50e0d17dc79c8"
recipient_address = "0x90f79bf6eb2c4f870365e785982e1f101e93b906"
origin_local_root = "0x2d252a5fea4ed67e85d8e446324eb9d0153e997a7b75e04c95e5d6b48ac099f5"
is_from_aztec = false
nullifier_preimage = "0x10e1"
secret = "0x4d2"

[aztec_merkle_data]
leaf_index = "0x0"
hash_path = [{zeros42}]
leaf_nonce = "0x0"

[evm_merkle_data]
leaf_index = "0x0"
hash_path = [{qevm}]

[giga_merkle_data]
leaf_index = "0x0"
hash_path = ["0x0", "0x0", "0x0", "0x0", "0x0"]
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("tests", "evaluation", "xav", "all"),
                        default="tests")
    parser.add_argument("--force", action="store_true",
                        help="replace only this script's scoped ignored output directories")
    parser.add_argument("--verify-only", action="store_true",
                        help="do not download or fetch; rebuild from cached sources and verify")
    args = parser.parse_args()
    Materializer(args.profile, args.force, args.verify_only).execute()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
