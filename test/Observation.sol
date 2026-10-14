// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import {VmSafe} from "forge-std/Vm.sol";
import {Test} from "forge-std/Test.sol";
import {Groth16Verifier} from "../contracts/generated/Groth16Verifier.sol";

interface IObservable {
    function currentCommitment() external view returns (uint256);
    function consumedBacking() external view returns (uint256);
    function escrows(bytes32 batchId, uint256 row) external view returns (uint256 amount, bool funded, bool consumed);
}

/// Observation layer for T07: the same record format and capture method as test/T06Export.t.sol
/// (copied, not shared; T06's test file is left untouched). Records contain observations only:
/// no verdicts, no consumer/variant names, no scenario labels. Writes under RECORD_DIR.
abstract contract Observation is Test {
    string internal constant RECORD_DIR = "results/raw/T07/records/";

    Groth16Verifier internal verifier;

    struct Snap {
        uint256 commitment;
        uint256 backing;
        uint256 eth;
        uint256[4] amount;
        bool[4] funded;
        bool[4] consumed;
    }

    struct Proof {
        uint256[2] a;
        uint256[2][2] b;
        uint256[2] c;
        uint256[10] p;
    }

    struct Rec {
        string execId;
        address consumer;
        bytes32 id;
        bool ok;
        bytes ret;
        bool recheck;
        string verifierCallJson;
        Snap pre;
        Snap post;
    }

    function _snap(address c, bytes32 id) internal view returns (Snap memory s) {
        s.commitment = IObservable(c).currentCommitment();
        s.backing = IObservable(c).consumedBacking();
        s.eth = c.balance;
        for (uint256 r = 0; r < 4; r++) {
            (s.amount[r], s.funded[r], s.consumed[r]) = IObservable(c).escrows(id, r);
        }
    }

    function _u(uint256 v) internal pure returns (string memory) {
        return string.concat('"', vm.toString(v), '"');
    }

    function _bool(bool b) internal pure returns (string memory) {
        return b ? "true" : "false";
    }

    function _snapJson(Snap memory s) internal pure returns (string memory) {
        string memory rows = "[";
        for (uint256 r = 0; r < 4; r++) {
            rows = string.concat(
                rows, r == 0 ? "" : ",",
                '{"funded":', _bool(s.funded[r]), ',"amount":', _u(s.amount[r]), ',"consumed":', _bool(s.consumed[r]), "}"
            );
        }
        rows = string.concat(rows, "]");
        return string.concat(
            '{"commitment":', _u(s.commitment), ',"consumedBacking":', _u(s.backing),
            ',"ethBalance":', _u(s.eth), ',"rows":', rows, "}"
        );
    }

    function _pubJson(uint256[10] memory p) internal pure returns (string memory out) {
        out = "[";
        for (uint256 i = 0; i < 10; i++) out = string.concat(out, i == 0 ? "" : ",", _u(p[i]));
        out = string.concat(out, "]");
    }

    function _verifierCallJson(VmSafe.AccountAccess[] memory acc, address consumer) internal view returns (string memory) {
        for (uint256 i = 0; i < acc.length; i++) {
            VmSafe.AccountAccess memory a = acc[i];
            bool isCall = a.kind == VmSafe.AccountAccessKind.Call || a.kind == VmSafe.AccountAccessKind.StaticCall;
            if (isCall && a.account == address(verifier) && a.accessor == consumer) {
                return string.concat(
                    '{"observed":true,"source":"vm.startStateDiffRecording","target":"', vm.toString(a.account),
                    '","kind":"', a.kind == VmSafe.AccountAccessKind.StaticCall ? "StaticCall" : "Call",
                    '","calldata":"', vm.toString(a.data), '","revertedInScope":', _bool(a.reverted), "}"
                );
            }
        }
        return '{"observed":false}';
    }

    function _recJson(Rec memory r, uint256[10] memory p) internal view returns (string memory) {
        string memory head = string.concat(
            '{"schema":"bindcheck.execution-record/v1","executionId":"', r.execId,
            '","chain":{"chainId":', _u(block.chainid), ',"blockNumber":', _u(block.number),
            ',"timestamp":', _u(block.timestamp), "},"
        );
        string memory ids = string.concat(
            '"consumer":"', vm.toString(r.consumer), '","verifier":"', vm.toString(address(verifier)),
            '","batchId":"', vm.toString(r.id), '",'
        );
        string memory inputs = string.concat(
            '"publicInputs":', _pubJson(p),
            ',"publicInputLayout":{"amount":[0,1,2,3],"active":[4,5,6,7],"oldCommitment":8,"newCommitment":9},'
        );
        string memory sub = string.concat(
            '"submission":{"status":"', r.ok ? "success" : "reverted", '","revertData":',
            r.ok ? "null" : string.concat('"', vm.toString(r.ret), '"'), "},"
        );
        string memory ver = string.concat(
            '"verifierCall":', r.verifierCallJson, ',"verifierRecheck":{"result":', _bool(r.recheck),
            ',"note":"direct call after submission with the recorded arguments; not the consumer call result"},'
        );
        string memory state = string.concat('"pre":', _snapJson(r.pre), ',"post":', _snapJson(r.post), "}");
        return string.concat(head, ids, inputs, sub, ver, state);
    }

    /// Runs one submission against `consumer` and writes its execution record. Returns call success.
    function _execute(string memory execId, address consumer, Proof memory pr, bytes memory callData)
        internal
        returns (bool)
    {
        Rec memory r;
        r.execId = execId;
        r.consumer = consumer;
        r.id = keccak256(abi.encode(pr.p));
        r.pre = _snap(consumer, r.id);

        vm.startStateDiffRecording();
        (r.ok, r.ret) = consumer.call(callData);
        VmSafe.AccountAccess[] memory acc = vm.stopAndReturnStateDiff();

        r.post = _snap(consumer, r.id);
        r.recheck = verifier.verifyProof(pr.a, pr.b, pr.c, pr.p);
        r.verifierCallJson = _verifierCallJson(acc, consumer);
        vm.writeFile(string.concat(RECORD_DIR, execId, ".json"), _recJson(r, pr.p));
        return r.ok;
    }
}
