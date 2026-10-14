// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import {VmSafe} from "forge-std/Vm.sol";
import {T01Fixture} from "./T01Fixture.sol";
import {BackedBatchConsumer} from "../contracts/BackedBatchConsumer.sol";
import {ResearchMutantBackedBatchConsumer} from "../contracts/research/MutantBackedBatchConsumer.sol";
import {RepairedPrefixBatchConsumer} from "../contracts/research/RepairedPrefixBatchConsumer.sol";
import {IGroth16Verifier} from "../contracts/BatchConsumer.sol";
import {Groth16Verifier} from "../contracts/generated/Groth16Verifier.sol";

interface IObservable {
    function currentCommitment() external view returns (uint256);
    function consumedBacking() external view returns (uint256);
    function escrows(bytes32 batchId, uint256 row) external view returns (uint256 amount, bool funded, bool consumed);
}

/// T06 EXPORTER (observation layer) + ORACLE (independent Foundry assertions).
///
/// Records (results/raw/T06/records/exec-NN.json) contain only observations: public inputs, ids,
/// call status, state before/after (via public getters), the consumer's actual verifier call (from
/// vm.startStateDiffRecording) and a direct verifier re-check. They contain NO expected verdicts,
/// no contract-variant names and no scenario labels. Expected outcomes live only in
/// results/raw/T06/oracle/exec-NN.json, written AFTER hand-written raw-storage assertions pass.
/// The checker never reads the oracle directory.
contract T06ExportTest is T01Fixture {
    uint256 constant PADDED_NEW_COMMITMENT = 13087091886095216173338600835649502128422847627890228330606202401392478644873;

    uint256[2] qA;
    uint256[2][2] qB;
    uint256[2] qC;
    uint256[10] qpub;

    Groth16Verifier verifier;
    bytes32 idO;
    bytes32 idP;

    struct Snap {
        uint256 commitment;
        uint256 backing;
        uint256 eth;
        uint256[4] amount;
        bool[4] funded;
        bool[4] consumed;
    }

    function setUp() public {
        _loadFixture();
        string memory j = vm.readFile("build/T05/calldata.json");
        uint256[] memory a = vm.parseJsonUintArray(j, "$[0]");
        uint256[] memory b0 = vm.parseJsonUintArray(j, "$[1][0]");
        uint256[] memory b1 = vm.parseJsonUintArray(j, "$[1][1]");
        uint256[] memory c = vm.parseJsonUintArray(j, "$[2]");
        uint256[] memory p = vm.parseJsonUintArray(j, "$[3]");
        qA = [a[0], a[1]];
        qB = [[b0[0], b0[1]], [b1[0], b1[1]]];
        qC = [c[0], c[1]];
        for (uint256 i = 0; i < 10; i++) qpub[i] = p[i];
        uint256[10] memory expectedP = [uint256(100), 250, 0, 0, 1, 1, 0, 0, OLD_COMMITMENT, PADDED_NEW_COMMITMENT];
        for (uint256 i = 0; i < 10; i++) assertEq(qpub[i], expectedP[i], "padded fixture differs");

        verifier = new Groth16Verifier();
        // Oracle batch ids from literals (independent of the exporter's own derivation).
        idO = keccak256(abi.encode(
            uint256(100), uint256(250), uint256(0), uint256(40), uint256(1), uint256(1), uint256(0), uint256(1),
            OLD_COMMITMENT, NEW_COMMITMENT
        ));
        idP = keccak256(abi.encode(
            uint256(100), uint256(250), uint256(0), uint256(0), uint256(1), uint256(1), uint256(0), uint256(0),
            OLD_COMMITMENT, PADDED_NEW_COMMITMENT
        ));
        vm.createDir("results/raw/T06/records", true);
        vm.createDir("results/raw/T06/oracle", true);
    }

    // =====================================================================
    // Observation layer
    // =====================================================================
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

    /// Finds the consumer's own call to the verifier in the recorded account accesses.
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
        // Direct re-check of the same statement against the same verifier AFTER the call (not the consumer's own result).
        r.recheck = verifier.verifyProof(pr.a, pr.b, pr.c, pr.p);
        r.verifierCallJson = _verifierCallJson(acc, consumer);
        vm.writeFile(string.concat("results/raw/T06/records/", execId, ".json"), _recJson(r, pr.p));
        return r.ok;
    }

    function _origProof() internal view returns (Proof memory) {
        return Proof(pA, pB, pC, pub);
    }

    function _paddedProof() internal view returns (Proof memory) {
        return Proof(qA, qB, qC, qpub);
    }

    // =====================================================================
    // Oracle (separate from observation): raw-storage assertions, then the expected label
    // =====================================================================
    function _rawAssert(
        address c,
        bytes32 id,
        uint256 commitment,
        uint256 backing,
        uint256 eth,
        uint256[4] memory amounts,
        bool[4] memory funded,
        bool[4] memory consumed
    ) internal view {
        assertEq(uint256(vm.load(c, bytes32(uint256(0)))), commitment, "oracle: commitment");
        assertEq(uint256(vm.load(c, bytes32(uint256(1)))), backing, "oracle: consumedBacking");
        assertEq(c.balance, eth, "oracle: ETH");
        for (uint256 r = 0; r < 4; r++) {
            bytes32 base = keccak256(abi.encode(r, keccak256(abi.encode(id, uint256(2)))));
            uint256 packed = uint256(vm.load(c, bytes32(uint256(base) + 1)));
            assertEq((packed & 0xff) == 1, funded[r], "oracle: funded");
            assertEq(((packed >> 8) & 0xff) == 1, consumed[r], "oracle: consumed");
            assertEq(uint256(vm.load(c, base)), funded[r] ? amounts[r] : 0, "oracle: amount");
        }
    }

    function _writeOracle(string memory execId, string memory verdict, string memory missingJson, uint256 deficit) internal {
        vm.writeFile(
            string.concat("results/raw/T06/oracle/", execId, ".json"),
            string.concat(
                '{"executionId":"', execId, '","expectedVerdict":"', verdict, '","expectedMissing":', missingJson,
                ',"expectedDeficit":', _u(deficit), "}"
            )
        );
    }

    // helpers to build consumers / funding
    function _correct() internal returns (BackedBatchConsumer) {
        return new BackedBatchConsumer(IGroth16Verifier(address(verifier)), OLD_COMMITMENT);
    }

    function _mutant() internal returns (ResearchMutantBackedBatchConsumer) {
        return new ResearchMutantBackedBatchConsumer(IGroth16Verifier(address(verifier)), OLD_COMMITMENT);
    }

    function _repaired() internal returns (RepairedPrefixBatchConsumer) {
        return new RepairedPrefixBatchConsumer(IGroth16Verifier(address(verifier)), OLD_COMMITMENT);
    }

    uint256[4] AMT_O = [uint256(100), 250, 0, 40];
    uint256[4] AMT_P = [uint256(100), 250, 0, 0];

    function _fundO(address c, uint256 row) internal {
        (bool ok,) = c.call{value: AMT_O[row]}(abi.encodeWithSignature("fund(uint256[10],uint256)", pub, row));
        require(ok, "fund failed");
    }

    function _fundP(address c, uint256 row) internal {
        (bool ok,) = c.call{value: AMT_P[row]}(abi.encodeWithSignature("fund(uint256[10],uint256)", qpub, row));
        require(ok, "fund failed");
    }

    // =====================================================================
    // Executions (real contracts, real verifier, real proofs)
    // =====================================================================

    // exec-01: correct consumer, original batch fully funded
    function test_export_exec01() public {
        BackedBatchConsumer c = _correct();
        _fundO(address(c), 0);
        _fundO(address(c), 1);
        _fundO(address(c), 3);
        bool ok = _execute("exec-01", address(c), _origProof(), abi.encodeCall(BackedBatchConsumer.submit, (pA, pB, pC, pub)));
        assertTrue(ok);
        _rawAssert(address(c), idO, NEW_COMMITMENT, 390, 390, AMT_O, [true, true, false, true], [true, true, false, true]);
        _writeOracle("exec-01", "NO_VIOLATION", "[]", 0);
    }

    // exec-02: mutant, rows 0 and 1 funded, limit 3 (row 3 unfunded)
    function test_export_exec02() public {
        ResearchMutantBackedBatchConsumer c = _mutant();
        _fundO(address(c), 0);
        _fundO(address(c), 1);
        bool ok = _execute("exec-02", address(c), _origProof(), abi.encodeCall(ResearchMutantBackedBatchConsumer.submit, (pA, pB, pC, pub, 3)));
        assertTrue(ok);
        _rawAssert(address(c), idO, NEW_COMMITMENT, 350, 350, AMT_O, [true, true, false, false], [true, true, false, false]);
        _writeOracle("exec-02", "VIOLATION", '[{"row":3,"amount":"40","fundedButUnconsumed":false}]', 40);
    }

    // exec-03: mutant, fully funded, limit 4
    function test_export_exec03() public {
        ResearchMutantBackedBatchConsumer c = _mutant();
        _fundO(address(c), 0);
        _fundO(address(c), 1);
        _fundO(address(c), 3);
        bool ok = _execute("exec-03", address(c), _origProof(), abi.encodeCall(ResearchMutantBackedBatchConsumer.submit, (pA, pB, pC, pub, 4)));
        assertTrue(ok);
        _rawAssert(address(c), idO, NEW_COMMITMENT, 390, 390, AMT_O, [true, true, false, true], [true, true, false, true]);
        _writeOracle("exec-03", "NO_VIOLATION", "[]", 0);
    }

    // exec-04: repaired consumer, original batch, rows 0 and 1 funded, limit 3 -> revert
    function test_export_exec04() public {
        RepairedPrefixBatchConsumer c = _repaired();
        _fundO(address(c), 0);
        _fundO(address(c), 1);
        bool ok = _execute("exec-04", address(c), _origProof(), abi.encodeCall(RepairedPrefixBatchConsumer.submit, (pA, pB, pC, pub, 3)));
        assertFalse(ok);
        _rawAssert(address(c), idO, OLD_COMMITMENT, 0, 350, AMT_O, [true, true, false, false], [false, false, false, false]);
        _writeOracle("exec-04", "REVERTED_UNCHANGED", "[]", 0);
    }

    // exec-05: repaired consumer accepts padded batch, limit 2
    function test_export_exec05() public {
        RepairedPrefixBatchConsumer c = _repaired();
        _fundP(address(c), 0);
        _fundP(address(c), 1);
        bool ok = _execute("exec-05", address(c), _paddedProof(), abi.encodeCall(RepairedPrefixBatchConsumer.submit, (qA, qB, qC, qpub, 2)));
        assertTrue(ok);
        _rawAssert(address(c), idP, PADDED_NEW_COMMITMENT, 350, 350, AMT_P, [true, true, false, false], [true, true, false, false]);
        _writeOracle("exec-05", "NO_VIOLATION", "[]", 0);
    }

    // exec-06: repaired consumer rejects padded batch, limit 1
    function test_export_exec06() public {
        RepairedPrefixBatchConsumer c = _repaired();
        _fundP(address(c), 0);
        _fundP(address(c), 1);
        bool ok = _execute("exec-06", address(c), _paddedProof(), abi.encodeCall(RepairedPrefixBatchConsumer.submit, (qA, qB, qC, qpub, 1)));
        assertFalse(ok);
        _rawAssert(address(c), idP, OLD_COMMITMENT, 0, 350, AMT_P, [true, true, false, false], [false, false, false, false]);
        _writeOracle("exec-06", "REVERTED_UNCHANGED", "[]", 0);
    }

    // exec-07: mutant, ALL active rows funded (390 wei held), limit 3 -> row 3 funded but never consumed
    function test_export_exec07() public {
        ResearchMutantBackedBatchConsumer c = _mutant();
        _fundO(address(c), 0);
        _fundO(address(c), 1);
        _fundO(address(c), 3);
        bool ok = _execute("exec-07", address(c), _origProof(), abi.encodeCall(ResearchMutantBackedBatchConsumer.submit, (pA, pB, pC, pub, 3)));
        assertTrue(ok);
        // 390 wei physically held, but only 350 reclassified as backing; row 3's escrow stays unconsumed.
        _rawAssert(address(c), idO, NEW_COMMITMENT, 350, 390, AMT_O, [true, true, false, true], [true, true, false, false]);
        _writeOracle("exec-07", "VIOLATION", '[{"row":3,"amount":"40","fundedButUnconsumed":true}]', 40);
    }
}
