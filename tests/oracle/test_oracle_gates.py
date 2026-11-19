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
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from oracle import runner  # noqa: E402

DRIVER = Path(os.environ.get("ORACLE_TEST_DRIVER", ROOT / "oracle" / "evm_runner.cjs"))


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
        "Promise.resolve(typeof out==='function'?out():out)"
        ".then(v=>process.stdout.write(JSON.stringify(v)))"
        ".catch(e=>{console.error(e);process.exitCode=1});"
    )
    proc = subprocess.run(
        ["node", "-e", script],
        cwd=str(ROOT),
        env={
            "NODE_PATH": str(deps),
            # Pin ethers by path so a repo-root ethers 5.x cannot shadow it.
            "ORACLE_ETHERS_PATH": str(deps / "ethers"),
            "PATH": os.environ.get("PATH", ""),
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
    res = _node(f"m.verifierOnMutatedPath({json.dumps(tree)},[{{address:'0xverifier',input:'0x1234'}}],'0xconsumer')")
    assert res["established"] is False


def test_verifier_called_but_false_not_established():
    tree = {"to": "0xconsumer", "type": "CALL",
            "calls": [{"to": "0xverifier", "type": "STATICCALL",
                       "input": "0x1234", "output": "0x0000000000000000000000000000000000000000000000000000000000000000"}]}
    res = _node(f"m.verifierOnMutatedPath({json.dumps(tree)},[{{address:'0xverifier',input:'0x1234'}}],'0xconsumer')")
    assert res["established"] is False


def test_verifier_called_true_is_established():
    tree = {"to": "0xconsumer", "type": "CALL",
            "calls": [{"to": "0xverifier", "type": "STATICCALL",
                       "input": "0x1234", "output": "0x0000000000000000000000000000000000000000000000000000000000000001"}]}
    res = _node(f"m.verifierOnMutatedPath({json.dumps(tree)},[{{address:'0xverifier',input:'0x1234'}}],'0xconsumer')")
    assert res["established"] is True


def test_verifier_reverted_not_established():
    tree = {"to": "0xconsumer", "type": "CALL",
            "calls": [{"to": "0xverifier", "type": "STATICCALL", "input": "0x1234", "error": "execution reverted"}]}
    res = _node(f"m.verifierOnMutatedPath({json.dumps(tree)},[{{address:'0xverifier',input:'0x1234'}}],'0xconsumer')")
    assert res["established"] is False


def test_xr02_requires_every_check_and_exact_mutated_input():
    tree = {"to": "0xconsumer", "type": "CALL", "calls": [
        {"to": "0xv1", "input": "0xaaaa", "output": "0x01"},
        {"to": "0xv2", "input": "0xbbbb", "output": "0x01"},
    ]}
    checks = [{"address": "0xv1", "input": "0xaaaa"}, {"address": "0xv2", "input": "0xbbbb"}]
    assert _node(f"m.verifierOnMutatedPath({json.dumps(tree)},{json.dumps(checks)},'0xconsumer')")["established"] is True
    assert _node(f"m.verifierOnMutatedPath({json.dumps({**tree, 'calls': tree['calls'][:1]})},{json.dumps(checks)},'0xconsumer')")["established"] is False
    changed = [{"address": "0xv1", "input": "0xaaab"}, checks[1]]
    assert _node(f"m.verifierOnMutatedPath({json.dumps(tree)},{json.dumps(changed)},'0xconsumer')")["established"] is False
    nested = {"to": "0xconsumer", "calls": [{"to": "0xhelper", "calls": tree["calls"]}]}
    assert _node(f"m.verifierOnMutatedPath({json.dumps(nested)},{json.dumps(checks)},'0xconsumer')")["established"] is False


def test_xr01_existing_erc721_owner_is_not_corroborated():
    code = """async()=>{const addr='0x0000000000000000000000000000000000000001';
      const contract={balanceOf:async()=>1n,ownerOf:async()=>addr};
      return await m.corroborateEffect(contract,{kind:'erc721_transfer',from:'0x0000000000000000000000000000000000000000',to:addr,token_id:'1'},2)}"""
    # The node helper accepts a Promise and serializes its resolved value.
    assert _node(code)["corroborated"] is False


def test_xr01_new_erc721_owner_is_corroborated():
    code = """async()=>{const addr='0x0000000000000000000000000000000000000001';
      const contract={balanceOf:async(_a,o)=>o.blockTag===1?0n:1n,
        ownerOf:async(_id,o)=>{if(o.blockTag===1)throw Error('nonexistent');return addr}};
      return await m.corroborateEffect(contract,{kind:'erc721_transfer',from:'0x0000000000000000000000000000000000000000',to:addr,token_id:'1'},2)}"""
    assert _node(code)["corroborated"] is True


def test_xr02_alias_expected_verifier_input_carries_mutation():
    code = """()=>{const scenario={alias:{arg:'pub',proof:'p'},
      verifier_checks:[{contract:'v',function:'verifyProof',args:[{$proofPart:{proof:'p',part:'a'}},{$pubArray:{proof:'p'}}]}]};
      const deployments={v:{target:'0xv',contract:{interface:{encodeFunctionData:(_f,args)=>JSON.stringify(args)}}}};
      const resolver={resolve:x=>x.$lit??(x.$pubArray?['7']:['proof'])};
      return m.expectedVerifierCalls(scenario,deployments,resolver,{operator:'ALIAS'},
        {arg:'pub',position:0},{pub:{$lit:['8']}})[0].input}"""
    assert _node(code) == '[["proof"],["8"]]'


def test_xr2_01_missing_view_baseline_fails_closed():
    code = """()=>{try{m.diffViews({credit:{error:'reverted'}},{credit:150n},[{name:'credit'}]);
      return 'accepted'}catch(e){return e.message}}"""
    assert "credit" in _node(code)


def test_xr07_same_event_cannot_discharge_two_clauses():
    event = {"kind": "erc20_transfer", "from": "0x0000000000000000000000000000000000000000",
             "contract_role": "fee", "to": "0xt", "value": "50"}
    match = {"type": "erc20_transfer", "from": "0x0", "contract_role": "fee", "to": "0xt", "value": "50"}
    clauses = [{"id": "a", "match": match}, {"id": "b", "match": match}]
    assert sorted(_node(f"Object.values(m.obligationCounts([{json.dumps(event)}],{json.dumps(clauses)},{{resolve:{ID}}}))")) == [0, 1]
    assert sorted(_node(f"Object.values(m.obligationCounts([{json.dumps(event)},{json.dumps(event)}],{json.dumps(clauses)},{{resolve:{ID}}}))")) == [1, 1]


# F4: test the exported final verdict with recorded trial observations. These
# assertions exercise the last E4 decision, not only its individual helpers.
def _verdict(**changes):
    observation = {
        "honest_succeeded": True,
        "tx_succeeded": True,
        "tx_error": None,
        "effects": [{"contract_role": "token", "state_corroboration": {"corroborated": True}}],
        "matched_effects": [{"contract_role": "token", "state_corroboration": {"corroborated": True}}],
        "view_committed": False,
        "violations": [{"rule": "r", "type": "entitlement_mismatch"}],
        "verifier_path": {"established": True},
        "view_read_failure": None,
        "rule_error": None,
    }
    observation.update(changes)
    return _node(f"m.decideTrial({json.dumps(observation)})")


def test_f4_xr01_fake_mint_cannot_reach_final_e4():
    effect = {"contract_role": "token", "state_corroboration": {"corroborated": False, "reason": "balance_delta_mismatch"}}
    decision = _verdict(effects=[effect], matched_effects=[effect])
    assert decision["result"] == "UNKNOWN"
    assert decision["reason"].startswith("EFFECT_NOT_STATE_CORROBORATED")


def test_f4_xr02_missing_or_mismatched_verifier_call_cannot_reach_final_e4():
    for path in ({"established": False, "reason": "call_missing"},
                 {"established": False, "reason": "calldata_mismatch"}):
        decision = _verdict(verifier_path=path)
        assert decision["result"] == "UNKNOWN"
        assert decision["reason"].startswith("VERIFIER_PATH_NOT_ESTABLISHED")


def test_f4_xr07_underpayment_reaches_final_e4():
    policy = {"protected_effects": [], "required_obligations": [{"id": "fee", "match": {"type": "erc20_transfer", "value": "50", "contract_role": "fee"}}]}
    fee = {"kind": "erc20_transfer", "contract_role": "fee", "value": "1"}
    benefit = {"kind": "erc20_transfer", "contract_role": "reward", "state_corroboration": {"corroborated": True}}
    code = f"""async()=>{{const p={json.dumps(policy)},f={json.dumps(fee)},b={json.dumps(benefit)};
      const v=await m.evaluatePolicy(p,[b,f],{{honest_obligations:{{fee:1}},benefit_committed:true}},{{resolve:x=>x}},{{}});
      return {{violations:v,decision:m.decideTrial({{honest_succeeded:true,tx_succeeded:true,
        effects:[b,f],matched_effects:[b],view_committed:false,violations:v,verifier_path:{{established:true}}}})}}}}"""
    result = _node(code)
    assert [v["type"] for v in result["violations"]] == ["undischarged_obligation"]
    assert result["decision"]["result"] == "E4-CONFIRMED"


def test_f4_xr07_one_effect_cannot_discharge_two_clauses_at_final_gate():
    match = {"type": "erc20_transfer", "value": "50", "contract_role": "fee"}
    policy = {"protected_effects": [], "required_obligations": [{"id": "a", "match": match}, {"id": "b", "match": match}]}
    fee = {"kind": "erc20_transfer", "contract_role": "fee", "value": "50"}
    benefit = {"kind": "erc20_transfer", "contract_role": "reward", "state_corroboration": {"corroborated": True}}
    code = f"""async()=>{{const p={json.dumps(policy)},f={json.dumps(fee)},b={json.dumps(benefit)};
      const v=await m.evaluatePolicy(p,[b,f],{{honest_obligations:{{a:1,b:1}},benefit_committed:true}},{{resolve:x=>x}},{{}});
      return {{violations:v,decision:m.decideTrial({{honest_succeeded:true,tx_succeeded:true,
        effects:[b,f],matched_effects:[b],view_committed:false,violations:v,verifier_path:{{established:true}}}})}}}}"""
    result = _node(code)
    assert len(result["violations"]) == 1
    assert result["violations"][0]["type"] == "undischarged_obligation"
    assert result["decision"]["result"] == "E4-CONFIRMED"


def test_f4_xr2_01_failed_view_read_is_unknown_at_final_gate():
    decision = _verdict(view_read_failure="credit: before=object, after=150")
    assert decision["result"] == "UNKNOWN"
    assert decision["reason"].startswith("VIEW_READ_FAILED")


def test_f4_xr3_01_repeatable_b_replay_is_not_e4_but_a_replay_is():
    policy = {"protected_effects": [
        {"id": "single_A", "match": {"type": "erc20_transfer", "from": "0x0", "contract_role": "a"},
         "single_use": {"key_pub": {"proof": "cred", "index": 0}}},
        {"id": "repeatable_B", "match": {"type": "erc20_transfer", "from": "0x0", "contract_role": "b"}},
    ]}
    code = f"""async()=>{{const p={json.dumps(policy)},z='0x0000000000000000000000000000000000000000';
      const out={{}};for(const role of ['a','b']){{const e={{kind:'erc20_transfer',from:z,contract_role:role,
        state_corroboration:{{corroborated:true}}}};
        const replay=m.singleUseReplays(p,[e],[e],{{cred:['7']}});
        const v=await m.evaluatePolicy(p,[e],{{single_use_replays:replay.replays}},{{resolve:x=>x}},{{}});
        out[role]={{replay,violations:v,decision:m.decideTrial({{honest_succeeded:true,tx_succeeded:true,
          effects:[e],matched_effects:[e],view_committed:false,violations:v,verifier_path:{{established:true}},rule_error:replay.error}})}};
      }}return out}}"""
    result = _node(code)
    assert result["b"]["replay"]["replays"] == []
    assert result["b"]["decision"]["result"] == "NOT_CONFIRMED"
    assert result["a"]["violations"][0]["authorization_key"] == "7"
    assert result["a"]["decision"]["result"] == "E4-CONFIRMED"


def test_f4_ambiguous_rule_match_is_unknown():
    policy = {"protected_effects": [{"id": "a", "match": {"type": "erc20_transfer", "from": "0x0"}},
                                     {"id": "b", "match": {"type": "erc20_transfer", "from": "0x0"}}]}
    effect = {"kind": "erc20_transfer", "from": "0x0000000000000000000000000000000000000000"}
    code = f"""()=>{{const attribution=m.singleUseReplays({json.dumps(policy)},[],[{json.dumps(effect)}],{{}});
      return m.decideTrial({{honest_succeeded:true,tx_succeeded:true,effects:[{json.dumps(effect)}],
        matched_effects:[{json.dumps(effect)}],view_committed:false,violations:[{{type:'entitlement_mismatch'}}],verifier_path:{{established:true}},
        rule_error:attribution.error}})}}"""
    assert _node(code) == {"result": "UNKNOWN", "reason": "EFFECT_RULE_AMBIGUOUS"}


def test_f4_each_single_use_rule_uses_its_own_canonical_key():
    policy = {"protected_effects": [
        {"id": "a", "match": {"type": "erc20_transfer", "from": "0x0", "contract_role": "a"},
         "single_use": {"key_pub": {"proof": "cred", "index": 0}}},
        {"id": "c", "match": {"type": "erc20_transfer", "from": "0x0", "contract_role": "c"},
         "single_use": {"key_pub": {"proof": "cred", "index": 1}}},
    ]}
    effect = {"kind": "erc20_transfer", "from": "0x0000000000000000000000000000000000000000", "contract_role": "c"}
    code = f"m.singleUseReplays({json.dumps(policy)},[{json.dumps(effect)}],[{json.dumps(effect)}],{{cred:['7',(m.FIELD_R+9n).toString()]}})"
    result = _node(code)
    assert result["error"] is None
    assert result["replays"] == [{"rule": "c", "authorization_key": "9"}]


def test_f4_failed_honest_transaction_is_unknown_at_final_gate():
    assert _verdict(honest_succeeded=False)["result"] == "UNKNOWN"


def test_f4_mixed_rules_manifest_validates():
    path = ROOT / "tests/oracle/f4_mixed_rules.manifest.json"
    policy = runner._validate_manifest(runner._json(path), path)
    assert len(policy["protected_effects"]) == 2
    assert policy["protected_effects"][0]["single_use"]["key_pub"]["index"] == 0


def test_f4_output_namespace_is_owned():
    path = ROOT / "results/raw/F4/reviewer-mixed-rules"
    assert runner._owned_output(path) == path.resolve()
