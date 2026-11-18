"""Manifest-driven, local-only execution oracle.

The runner deliberately has no network-fetch or public-RPC mode for *chain*
access: contracts run only on a private Anvil node this process starts and
stops. Source inputs must already exist locally at their pinned revision. The
fork CLI shape is reserved for a future authorized implementation but is
fail-closed while H1 is not approved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BC = ROOT.parent
TOOLS = BC / "BindCheck" / "tools"
ANVIL = Path.home() / ".foundry" / "bin" / "anvil"
# Pinned ethers for the generic driver, installed into an ignored cache.
ETHERS_VERSION = "6.13.4"
DRIVER_DEPS = ROOT / "results" / "raw" / "S4" / ".driver"

ALLOWED_OWNED_PREFIXES = (
    ROOT / "oracle",
    ROOT / "tests" / "oracle",
    ROOT / "reports" / "S4",
    ROOT / "results" / "raw" / "S4",
)

# Keys/phrases that would encode the expected verdict into a policy file. The
# policy must state entitlement only (research contract §6); the oracle decides
# the verdict. These are matched against JSON object *keys* and against
# verdict-bearing phrases, not arbitrary prose, so a policy may still describe
# itself without tripping the gate.
FORBIDDEN_POLICY_KEYS = (
    "expected_verdict",
    "expected_result",
    "expected_outcome",
    "should_be_violation",
    "is_violation",
    "expected_classification",
)
FORBIDDEN_POLICY_PHRASES = (
    '"violation"',
    '"verified_within_scope"',
    "this is a violation",
    "should be flagged",
    "expected to be unsafe",
)


class OracleError(RuntimeError):
    """A fail-closed oracle error."""


@dataclass
class CommandRecord:
    name: str
    argv: list[str]
    cwd: str
    exit_code: int
    wall_seconds: float
    log: str


def _json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise OracleError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _owned_output(path: Path) -> Path:
    resolved = path.resolve()
    if not any(
        resolved == prefix or prefix in resolved.parents
        for prefix in ALLOWED_OWNED_PREFIXES
    ):
        raise OracleError(f"output path is not S4-owned: {resolved}")
    return resolved


def _render(value: str, context: dict[str, str]) -> str:
    for key, replacement in context.items():
        value = value.replace("{" + key + "}", replacement)
    if "{" in value or "}" in value:
        raise OracleError(f"unresolved template token in {value!r}")
    return value


def _command(
    spec: dict[str, Any],
    context: dict[str, str],
    logs: Path,
    records: list[CommandRecord],
    extra_env: dict[str, str] | None = None,
) -> None:
    name = str(spec["name"])
    argv = [_render(str(item), context) for item in spec["argv"]]
    cwd = Path(_render(str(spec.get("cwd", "{work}")), context)).resolve()
    expected = int(spec.get("expected_exit", 0))
    env = os.environ.copy()
    env.update(
        {key: _render(str(value), context) for key, value in spec.get("env", {}).items()}
    )
    if extra_env:
        env.update(extra_env)
    log = logs / f"{len(records):02d}-{name}.log"
    start = time.monotonic()
    with log.open("w", encoding="utf-8") as handle:
        handle.write(f"cwd={cwd}\nargv={json.dumps(argv)}\n")
        handle.flush()
        completed = subprocess.run(
            argv, cwd=cwd, env=env, stdout=handle, stderr=subprocess.STDOUT, check=False
        )
    elapsed = time.monotonic() - start
    records.append(
        CommandRecord(name, argv, str(cwd), completed.returncode, elapsed, str(log))
    )
    if completed.returncode != expected:
        raise OracleError(
            f"command {name!r} exited {completed.returncode}, expected {expected}; see {log}"
        )


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_local_rpc(port: int, process: subprocess.Popen, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise OracleError(f"anvil exited early with {process.returncode}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    raise OracleError("local Anvil RPC did not become ready")


def _validate_manifest(manifest: dict[str, Any], path: Path) -> dict[str, Any]:
    if manifest.get("schema_version") != 1:
        raise OracleError("unsupported manifest schema_version")
    safety = manifest.get("safety", {})
    if safety.get("local_only") is not True:
        raise OracleError("manifest must assert safety.local_only=true")
    if safety.get("fork_enabled") is not False:
        raise OracleError("fork mode must remain disabled because H1 is not approved")
    if not manifest.get("variants"):
        raise OracleError("manifest has no variants")
    policy_path = (path.parent / manifest["policy"]).resolve()
    policy = _json(policy_path)

    def check_keys(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key.lower() in FORBIDDEN_POLICY_KEYS:
                    raise OracleError(
                        f"policy encodes a verdict (forbidden key {key!r}); policy must state entitlement only"
                    )
                check_keys(value)
        elif isinstance(node, list):
            for item in node:
                check_keys(item)

    check_keys(policy)
    serialized = json.dumps(policy).lower()
    for phrase in FORBIDDEN_POLICY_PHRASES:
        if phrase in serialized:
            raise OracleError(
                f"policy encodes a verdict (forbidden phrase {phrase!r}); policy must state entitlement only"
            )
    return policy


def ensure_driver_deps() -> Path:
    """Install the pinned ethers used by the generic driver, into an ignored cache."""
    marker = DRIVER_DEPS / "node_modules" / "ethers" / "package.json"
    if marker.exists():
        return DRIVER_DEPS / "node_modules"
    DRIVER_DEPS.mkdir(parents=True, exist_ok=True)
    (DRIVER_DEPS / "package.json").write_text(
        json.dumps({"name": "s4-oracle-driver-deps", "private": True}) + "\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        ["npm", "install", "--no-audit", "--no-fund", "--save-exact", f"ethers@{ETHERS_VERSION}"],
        cwd=DRIVER_DEPS,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode != 0 or not marker.exists():
        raise OracleError(f"failed to install ethers@{ETHERS_VERSION}: {completed.stdout.decode(errors='replace')[-800:]}")
    return DRIVER_DEPS / "node_modules"


def _stage_source(manifest: dict[str, Any], work: Path, context: dict[str, str]) -> Path:
    source = manifest["source"]
    kind = source.get("kind")
    staged = work / "source"
    if kind == "git_archive":
        repo = Path(_render(source["repo"], context)).resolve()
        revision = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if revision.returncode != 0 or revision.stdout.strip() != source["commit"]:
            raise OracleError(
                f"source revision mismatch for {repo}: {revision.stdout.strip()!r} != {source['commit']}"
            )
        archive = work / "source.tar"
        tree = source["commit"]
        if source.get("subtree"):
            tree += ":" + source["subtree"]
        with archive.open("wb") as handle:
            completed = subprocess.run(
                ["git", "-C", str(repo), "archive", "--format=tar", tree],
                stdout=handle,
                stderr=subprocess.PIPE,
                check=False,
            )
        if completed.returncode != 0:
            raise OracleError(f"git archive failed: {completed.stderr.decode(errors='replace')}")
        staged.mkdir()
        completed = subprocess.run(["tar", "-xf", str(archive), "-C", str(staged)], check=False)
        if completed.returncode != 0:
            raise OracleError("source archive extraction failed")
    elif kind == "local_copy":
        local = (ROOT / source["path"]).resolve()
        if ROOT not in local.parents and local != ROOT:
            raise OracleError("local_copy source must be within this worktree")
        shutil.copytree(local, staged)
    else:
        raise OracleError(f"unsupported source kind: {kind}")
    return staged


def run(manifest_path: Path, out: Path, fork_url: str | None = None) -> dict[str, Any]:
    if fork_url is not None:
        raise OracleError("fork mode is built but disabled: H1 authorization is not approved")
    manifest_path = manifest_path.resolve()
    manifest = _json(manifest_path)
    policy = _validate_manifest(manifest, manifest_path)
    out = _owned_output(out)
    if out.exists() and any(out.iterdir()):
        raise OracleError(f"output directory already exists and is non-empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    logs = out / "logs"
    logs.mkdir()
    work = out / "work"
    work.mkdir()
    started = time.time()
    records: list[CommandRecord] = []

    base_context = {
        "ROOT": str(ROOT),
        "BC": str(BC),
        "TOOLS": str(TOOLS),
        "out": str(out),
        "work": str(work),
    }
    source = _stage_source(manifest, work, base_context)
    policy_path = (manifest_path.parent / manifest["policy"]).resolve()
    policy_snapshot = out / "policy.json"
    shutil.copy2(policy_path, policy_snapshot)
    manifest_snapshot = out / "manifest.json"
    shutil.copy2(manifest_path, manifest_snapshot)

    context = dict(base_context)
    context["source"] = str(source)
    context["policy"] = str(policy_snapshot)
    context["manifest"] = str(manifest_snapshot)

    driver_node_modules = ensure_driver_deps()

    outcome = "DONE"
    failure: str | None = None
    variant_results: list[dict[str, Any]] = []
    try:
        for spec in manifest.get("prepare", []):
            _command(spec, context, logs, records)
        for spec in manifest.get("proof", []):
            _command(spec, context, logs, records)
        for variant in manifest["variants"]:
            variant_id = variant["id"]
            for spec in variant.get("transform", []):
                _command(spec, context, logs, records)
            for spec in variant.get("build", []):
                _command(spec, context, logs, records)

            scenario = variant["scenario"]
            scenario["proofs"] = {
                name: {
                    "proof": _render(entry["proof"], context),
                    "public": _render(entry["public"], context),
                }
                for name, entry in scenario.get("proofs", {}).items()
            }
            artifacts_dirs = [_render(p, context) for p in variant["artifacts"]]

            port = _free_port()
            rpc_url = f"http://127.0.0.1:{port}"
            anvil_log = logs / f"anvil-{variant_id}.log"
            with anvil_log.open("wb") as handle:
                anvil = subprocess.Popen(
                    [str(ANVIL), "--silent", "--port", str(port), "--chain-id", "31337"],
                    stdout=handle,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            try:
                _wait_local_rpc(port, anvil)
                result_path = out / f"result-{variant_id}.json"
                driver_spec = {
                    "case_id": manifest["case_id"],
                    "variant": {"id": variant_id, "label": variant.get("label", variant_id)},
                    "scenario": scenario,
                    "artifacts_dirs": artifacts_dirs,
                    "policy": policy,
                    "result_path": str(result_path),
                    "output_dir": str(out),
                    "manifest_path": str(manifest_snapshot),
                    "policy_path": str(policy_snapshot),
                }
                driver_spec_path = out / f"driver-{variant_id}.json"
                driver_spec_path.write_text(json.dumps(driver_spec, indent=2) + "\n", encoding="utf-8")
                env = {
                    "ORACLE_DRIVER_SPEC": str(driver_spec_path),
                    "ORACLE_RPC_URL": rpc_url,
                    "NODE_PATH": str(driver_node_modules),
                }
                driver_command = {
                    "name": f"execute-{variant_id}",
                    "cwd": "{out}",
                    "argv": ["node", "{ROOT}/oracle/evm_runner.cjs"],
                }
                _command(driver_command, context, logs, records, env)
                variant_results.append(_json(result_path))
            finally:
                if anvil.poll() is None:
                    os.killpg(anvil.pid, signal.SIGTERM)
                    try:
                        anvil.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(anvil.pid, signal.SIGKILL)
                        anvil.wait(timeout=5)
    except Exception as error:  # preserve UNKNOWN instead of pretending safety
        outcome = "UNKNOWN"
        failure = str(error)

    summary = {
        "schema_version": 1,
        "case_id": manifest.get("case_id"),
        "status": outcome,
        "failure": failure,
        "local_only": True,
        "fork_enabled": False,
        "anvil": str(ANVIL),
        "ethers_version": ETHERS_VERSION,
        "manifest_sha256": _sha256(manifest_snapshot),
        "policy_sha256": _sha256(policy_snapshot),
        "wall_seconds": time.time() - started,
        "commands": [record.__dict__ for record in records],
        "variants": variant_results,
    }
    (out / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if failure:
        raise OracleError(failure)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 -m oracle")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run", help="run a local case manifest")
    run_parser.add_argument("manifest", type=Path)
    run_parser.add_argument("--out", type=Path, required=True)
    run_parser.add_argument(
        "--fork-url",
        help="reserved fork option; always rejected until written H1 authorization is recorded",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    try:
        if args.command == "run":
            summary = run(args.manifest, args.out, args.fork_url)
            print(json.dumps({"status": summary["status"], "result": str(args.out / "result.json")}))
    except OracleError as error:
        print(f"oracle: {error}", file=sys.stderr)
        raise SystemExit(2) from error
