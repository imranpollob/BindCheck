"""Unit tests for the execution-oracle soundness gates (F2 / XR-01,02,07,08,09).

Two layers:

* Python tests over ``oracle.runner`` safety gates (the XR-08 local-only command
  gate, the verdict-free-policy gate, the fork rejection).
* Node tests over the pure verdict helpers exported by ``oracle/evm_runner.cjs``
  (XR-01 corroboration is EVM-backed and covered by the integration controls;
  here we cover XR-02 verifier-path detection and XR-07 obligation quantity /
  multiplicity, which are pure functions).

Each gate test is written so it fails if the corresponding fix is reverted.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from oracle import runner  # noqa: E402

DRIVER = ROOT / "oracle" / "evm_runner.cjs"


# ---------------------------------------------------------------------------
# XR-08 — local-only command gate
# ---------------------------------------------------------------------------

def test_local_command_allows_loopback_and_plain_tools():
    runner._assert_local_only_command("ok", ["node", "x.cjs"])
    runner._assert_local_only_command("ok", ["cast", "send", "--rpc-url", "http://127.0.0.1:8545"])
    runner._assert_local_only_command("ok", ["npm", "ci", "--no-audit"])


@pytest.mark.parametrize(
    "tokens",
    [
        ["anvil", "--fork-url", "https://mainnet.example/key"],
        ["cast", "send", "--rpc-url", "https://rpc.example.org", "--broadcast"],
        ["forge", "script", "--fork-url", "http://127.0.0.1:8545"],  # fork forbidden even if local
        ["curl", "https://evil.example.com/x"],
        ["tool", "--rpc-url", "wss://node.example.net"],
    ],
)
def test_local_command_rejects_network_and_fork(tokens):
    with pytest.raises(runner.OracleError):
        runner._assert_local_only_command("bad", tokens)


def test_local_command_rejects_network_in_env_value():
    # The driver scans manifest-provided env values too.
    with pytest.raises(runner.OracleError):
        runner._assert_local_only_command("bad", ["node", "x", "RPC=https://public.example/"])


# ---------------------------------------------------------------------------
# verdict-free-policy and fork gates (unchanged behaviour, guarded here)
# ---------------------------------------------------------------------------

def _write(tmp_path: Path, manifest: dict, policy: dict) -> Path:
    (tmp_path / "p.json").write_text(json.dumps(policy))
    m = dict(manifest)
    m["policy"] = "p.json"
    mp = tmp_path / "m.json"
    mp.write_text(json.dumps(m))
    return mp


BASE_MANIFEST = {
    "schema_version": 1,
    "safety": {"local_only": True, "fork_enabled": False},
    "variants": [{"id": "v", "scenario": {}}],
}
BASE_POLICY = {"policy_id": "x", "protected_effects": []}


def test_validate_rejects_fork_enabled(tmp_path):
    m = dict(BASE_MANIFEST)
    m["safety"] = {"local_only": True, "fork_enabled": True}
    mp = _write(tmp_path, m, BASE_POLICY)
    with pytest.raises(runner.OracleError):
        runner._validate_manifest(runner._json(mp), mp)


def test_validate_rejects_non_local(tmp_path):
    m = dict(BASE_MANIFEST)
    m["safety"] = {"local_only": False, "fork_enabled": False}
    mp = _write(tmp_path, m, BASE_POLICY)
    with pytest.raises(runner.OracleError):
        runner._validate_manifest(runner._json(mp), mp)


def test_validate_rejects_verdict_encoding_policy(tmp_path):
    bad = {"policy_id": "x", "protected_effects": [{"id": "e", "expected_verdict": "VIOLATION"}]}
    mp = _write(tmp_path, BASE_MANIFEST, bad)
    with pytest.raises(runner.OracleError):
        runner._validate_manifest(runner._json(mp), mp)


def test_validate_accepts_entitlement_only_policy(tmp_path):
    ok = {
        "policy_id": "x",
        "protected_effects": [{"id": "e", "match": {"type": "erc20_transfer"}, "entitlements": []}],
    }
    mp = _write(tmp_path, BASE_MANIFEST, ok)
    assert runner._validate_manifest(runner._json(mp), mp)["policy_id"] == "x"


def test_run_rejects_fork_url():
    with pytest.raises(runner.OracleError):
        runner.run(Path("/dev/null"), ROOT / "results" / "raw" / "S4" / "unused", fork_url="http://x")


# ---------------------------------------------------------------------------
# Node-backed tests of the pure verdict helpers (XR-02, XR-07)
# ---------------------------------------------------------------------------

def _node(expr: str):
    """Evaluate a snippet against the driver module; returns parsed JSON stdout."""
    try:
        deps = runner.ensure_driver_deps()
    except runner.OracleError:
        pytest.skip("driver deps (ethers) unavailable")
    script = (
        f"const m=require({json.dumps(str(DRIVER))});"
        f"const out=({expr});"
        "process.stdout.write(JSON.stringify(out));"
    )
    proc = subprocess.run(
        ["node", "-e", script],
        cwd=str(ROOT),
        env={
            "NODE_PATH": str(deps),
            # Pin ethers by path so a repo-root ethers 5.x cannot shadow it.
            "ORACLE_ETHERS_PATH": str(deps / "ethers"),
            "PATH": __import__("os").environ.get("PATH", ""),
        },
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


ID = "(x)=>x"  # identity resolver stand-in; matches use literal values below


def test_obligation_value_mismatch_does_not_discharge():
    # XR-07: a +1 fee does not discharge a required +50 fee.
    fee1 = {"kind": "erc20_transfer", "from": "0x0000000000000000000000000000000000000000",
            "contract_role": "fee", "to": "0xtreasury", "value": "1"}
    match = {"type": "erc20_transfer", "from": "0x0", "contract_role": "fee", "to": "0xtreasury", "value": "50"}
    assert _node(f"m.matchesObligation({json.dumps(fee1)},{json.dumps(match)},{{resolve:{ID}}})") is False


def test_obligation_value_match_discharges():
    fee50 = {"kind": "erc20_transfer", "from": "0x0000000000000000000000000000000000000000",
             "contract_role": "fee", "to": "0xtreasury", "value": "50"}
    match = {"type": "erc20_transfer", "from": "0x0", "contract_role": "fee", "to": "0xtreasury", "value": "50"}
    assert _node(f"m.matchesObligation({json.dumps(fee50)},{json.dumps(match)},{{resolve:{ID}}})") is True


def test_obligation_multiplicity_counts_each_occurrence():
    # XR-07: two required obligations of the same shape need two events.
    fee = {"kind": "erc20_transfer", "from": "0x0000000000000000000000000000000000000000",
           "contract_role": "fee", "to": "0xt", "value": "50"}
    match = {"type": "erc20_transfer", "from": "0x0", "contract_role": "fee", "to": "0xt", "value": "50"}
    assert _node(f"m.obligationCount([{json.dumps(fee)}],{json.dumps(match)},{{resolve:{ID}}})") == 1
    assert _node(f"m.obligationCount([{json.dumps(fee)},{json.dumps(fee)}],{json.dumps(match)},{{resolve:{ID}}})") == 2


def test_verifier_not_called_on_mutated_path():
    # XR-02: no verifier call in the trace -> not established.
    tree = {"to": "0xconsumer", "type": "CALL", "calls": [{"to": "0xtoken", "type": "CALL", "output": "0x"}]}
    res = _node(f"m.verifierOnMutatedPath({json.dumps(tree)},['0xVERIFIER'])")
    assert res["established"] is False


def test_verifier_called_but_false_not_established():
    tree = {"to": "0xconsumer", "type": "CALL",
            "calls": [{"to": "0xverifier", "type": "STATICCALL",
                       "output": "0x0000000000000000000000000000000000000000000000000000000000000000"}]}
    res = _node(f"m.verifierOnMutatedPath({json.dumps(tree)},['0xVERIFIER'])")
    assert res["established"] is False


def test_verifier_called_true_is_established():
    tree = {"to": "0xconsumer", "type": "CALL",
            "calls": [{"to": "0xverifier", "type": "STATICCALL",
                       "output": "0x0000000000000000000000000000000000000000000000000000000000000001"}]}
    res = _node(f"m.verifierOnMutatedPath({json.dumps(tree)},['0xVERIFIER'])")
    assert res["established"] is True


def test_verifier_reverted_not_established():
    tree = {"to": "0xconsumer", "type": "CALL",
            "calls": [{"to": "0xverifier", "type": "STATICCALL", "error": "execution reverted"}]}
    res = _node(f"m.verifierOnMutatedPath({json.dumps(tree)},['0xVERIFIER'])")
    assert res["established"] is False
