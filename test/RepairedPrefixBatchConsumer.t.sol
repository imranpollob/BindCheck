// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import {T01Fixture} from "./T01Fixture.sol";
import {RepairedPrefixBatchConsumer} from "../contracts/research/RepairedPrefixBatchConsumer.sol";
import {IGroth16Verifier} from "../contracts/BatchConsumer.sol";
import {Groth16Verifier} from "../contracts/generated/Groth16Verifier.sol";

/// T05: repaired prefix consumer vs the original T01 proof (batch O) and a second, padded proof
/// from the same circuit/zkey (batch P: [100,250,0,0], flags [1,1,0,0], 1000 -> 1350).
/// State is measured from RAW STORAGE (slot0 commitment, slot1 backing, slot2 escrow mapping) and
/// ETH balance, against literals, with getters cross-checked. Each rejection names its causing check.
contract RepairedPrefixBatchConsumerTest is T01Fixture {
    uint256 constant PADDED_NEW_COMMITMENT = 13087091886095216173338600835649502128422847627890228330606202401392478644873;

    // Batch O (original T01 proof, fixture from T01Fixture): amounts [100,250,0,40], flags [1,1,0,1].
    uint256[4] AMT_O = [uint256(100), 250, 0, 40];
    // Batch P (padded proof): amounts [100,250,0,0], flags [1,1,0,0].
    uint256[4] AMT_P = [uint256(100), 250, 0, 0];

    // Padded fixture (build/T05/calldata.json).
    uint256[2] qA;
    uint256[2][2] qB;
    uint256[2] qC;
    uint256[10] qpub;

    Groth16Verifier verifier;
    bytes32 idO;
    bytes32 idP;

    struct S {
        uint256 commitment;
        uint256 eth;
        uint256 backing;
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
        assertEq(p.length, 10);
        qA = [a[0], a[1]];
        qB = [[b0[0], b0[1]], [b1[0], b1[1]]];
        qC = [c[0], c[1]];
        for (uint256 i = 0; i < 10; i++) qpub[i] = p[i];
        uint256[10] memory expectedP =
            [uint256(100), 250, 0, 0, 1, 1, 0, 0, OLD_COMMITMENT, PADDED_NEW_COMMITMENT];
        for (uint256 i = 0; i < 10; i++) assertEq(qpub[i], expectedP[i], "padded fixture differs from expected");

        verifier = new Groth16Verifier();
        idO = keccak256(abi.encode(
            uint256(100), uint256(250), uint256(0), uint256(40), uint256(1), uint256(1), uint256(0), uint256(1),
            OLD_COMMITMENT, NEW_COMMITMENT
        ));
        idP = keccak256(abi.encode(
            uint256(100), uint256(250), uint256(0), uint256(0), uint256(1), uint256(1), uint256(0), uint256(0),
            OLD_COMMITMENT, PADDED_NEW_COMMITMENT
        ));
        // Both proofs are ordinary valid proofs for the real verifier.
        assertTrue(verifier.verifyProof(pA, pB, pC, pub), "original proof verifies");
        assertTrue(verifier.verifyProof(qA, qB, qC, qpub), "padded proof verifies");
    }

    // ---------- helpers ----------
    function _deploy() internal returns (RepairedPrefixBatchConsumer) {
        return new RepairedPrefixBatchConsumer(IGroth16Verifier(address(verifier)), OLD_COMMITMENT);
    }

    function _fundO(RepairedPrefixBatchConsumer c, uint256 row) internal {
        c.fund{value: AMT_O[row]}(pub, row);
    }

    function _fundP(RepairedPrefixBatchConsumer c, uint256 row) internal {
        c.fund{value: AMT_P[row]}(qpub, row);
    }

    function _base(bytes32 id, uint256 row) internal pure returns (bytes32) {
        return keccak256(abi.encode(row, keccak256(abi.encode(id, uint256(2)))));
    }

    function _raw(address c, bytes32 id, uint256 row) internal view returns (uint256 amount, bool funded, bool consumed) {
        bytes32 base = _base(id, row);
        amount = uint256(vm.load(c, base));
        uint256 packed = uint256(vm.load(c, bytes32(uint256(base) + 1)));
        funded = (packed & 0xff) == 1;
        consumed = ((packed >> 8) & 0xff) == 1;
    }

    /// Exact expected state: commitment, ETH, backing, and per-row funded/consumed (+ stored amount).
    function _assertState(
        RepairedPrefixBatchConsumer c,
        bytes32 id,
        uint256[4] memory amounts,
        uint256 commitment,
        uint256 eth,
        uint256 backing,
        bool[4] memory funded,
        bool[4] memory consumed
    ) internal view {
        assertEq(uint256(vm.load(address(c), bytes32(uint256(0)))), commitment, "raw commitment");
        assertEq(c.currentCommitment(), commitment, "getter commitment");
        assertEq(uint256(vm.load(address(c), bytes32(uint256(1)))), backing, "raw backing");
        assertEq(c.consumedBacking(), backing, "getter backing");
        assertEq(address(c).balance, eth, "ETH held");
        for (uint256 r = 0; r < 4; r++) {
            (uint256 a, bool f, bool k) = _raw(address(c), id, r);
            assertEq(f, funded[r], "funded");
            assertEq(k, consumed[r], "consumed");
            assertEq(a, funded[r] ? amounts[r] : 0, "stored amount");
            (uint256 ga, bool gf, bool gk) = c.escrows(id, r);
            assertEq(ga, a);
            assertEq(gf, f);
            assertEq(gk, k);
        }
    }

    // ---------- 1. original T04 scenario, limit 3 ----------
    function test_1_originalScenario_rows0and1Funded_limit3_rejectedByActiveRowOutsidePrefix3() public {
        RepairedPrefixBatchConsumer c = _deploy();
        _fundO(c, 0);
        _fundO(c, 1);
        // Preconditions: old-commitment check passes and the proof verifies, so only the repair can reject.
        assertEq(pub[8], c.currentCommitment());
        assertTrue(verifier.verifyProof(pA, pB, pC, pub));
        vm.expectCall(address(verifier), abi.encodeCall(verifier.verifyProof, (pA, pB, pC, pub)));
        // Cause: ActiveRowOutsidePrefix(3) -- NOT MissingEscrow (T04 mutant accepted this exact call).
        vm.expectRevert(abi.encodeWithSelector(RepairedPrefixBatchConsumer.ActiveRowOutsidePrefix.selector, 3));
        c.submit(pA, pB, pC, pub, 3);
        _assertState(c, idO, AMT_O, OLD_COMMITMENT, 350, 0, [true, true, false, false], [false, false, false, false]);
    }

    // ---------- 2. fully funded but limit 3: funding alone is not consumption ----------
    function test_2_allActiveRowsFunded_limit3_stillRejectedByActiveRowOutsidePrefix3() public {
        RepairedPrefixBatchConsumer c = _deploy();
        _fundO(c, 0);
        _fundO(c, 1);
        _fundO(c, 3);
        // Escrow for row 3 exists and would pass its escrow check; only the prefix rule rejects.
        vm.expectRevert(abi.encodeWithSelector(RepairedPrefixBatchConsumer.ActiveRowOutsidePrefix.selector, 3));
        c.submit(pA, pB, pC, pub, 3);
        _assertState(c, idO, AMT_O, OLD_COMMITMENT, 390, 0, [true, true, false, true], [false, false, false, false]);
    }

    // ---------- 3. original proof, all funded, limit 4 ----------
    function test_3_originalProof_allActiveRowsFunded_limit4_succeeds() public {
        RepairedPrefixBatchConsumer c = _deploy();
        _fundO(c, 0);
        _fundO(c, 1);
        _fundO(c, 3);
        c.submit(pA, pB, pC, pub, 4);
        // 1000 -> 1390: credit 390 = 100+250+40, all three entries consumed with their own amounts
        _assertState(c, idO, AMT_O, NEW_COMMITMENT, 390, 390, [true, true, false, true], [true, true, false, true]);
    }

    // ---------- 4. padded proof, limit 2 accepted ----------
    function test_4_paddedProof_rows0and1Funded_limit2_acceptedAndConsumesExactly350() public {
        RepairedPrefixBatchConsumer c = _deploy();
        _fundP(c, 0);
        _fundP(c, 1);
        _assertState(c, idP, AMT_P, OLD_COMMITMENT, 350, 0, [true, true, false, false], [false, false, false, false]);
        vm.expectCall(address(verifier), abi.encodeCall(verifier.verifyProof, (qA, qB, qC, qpub)));
        c.submit(qA, qB, qC, qpub, 2); // rows 2,3 are outside the prefix with authenticated flag 0
        // 1000 -> 1350: credit 350 = 100+250; exactly entries 0 and 1 consumed; rows 2,3 never funded
        _assertState(c, idP, AMT_P, PADDED_NEW_COMMITMENT, 350, 350, [true, true, false, false], [true, true, false, false]);
    }

    function test_4b_paddedProof_limit4_alsoAccepted() public {
        RepairedPrefixBatchConsumer c = _deploy();
        _fundP(c, 0);
        _fundP(c, 1);
        c.submit(qA, qB, qC, qpub, 4);
        _assertState(c, idP, AMT_P, PADDED_NEW_COMMITMENT, 350, 350, [true, true, false, false], [true, true, false, false]);
    }

    // ---------- 5. padded proof, limit 1: active row 1 omitted ----------
    function test_5_paddedProof_limit1_rejectedByActiveRowOutsidePrefix1() public {
        RepairedPrefixBatchConsumer c = _deploy();
        _fundP(c, 0);
        _fundP(c, 1);
        vm.expectRevert(abi.encodeWithSelector(RepairedPrefixBatchConsumer.ActiveRowOutsidePrefix.selector, 1));
        c.submit(qA, qB, qC, qpub, 1);
        // row 0 (inside the prefix, funded) must not have been consumed: atomic rollback
        _assertState(c, idP, AMT_P, OLD_COMMITMENT, 350, 0, [true, true, false, false], [false, false, false, false]);
    }

    // ---------- 6. limit above 4 ----------
    function test_6_limitAbove4_rejectedByInvalidNumRealTxs() public {
        RepairedPrefixBatchConsumer c = _deploy();
        _fundO(c, 0);
        _fundO(c, 1);
        _fundO(c, 3);
        vm.expectRevert(abi.encodeWithSelector(RepairedPrefixBatchConsumer.InvalidNumRealTxs.selector, 5));
        c.submit(pA, pB, pC, pub, 5);
        vm.expectRevert(abi.encodeWithSelector(RepairedPrefixBatchConsumer.InvalidNumRealTxs.selector, type(uint256).max));
        c.submit(pA, pB, pC, pub, type(uint256).max);
        _assertState(c, idO, AMT_O, OLD_COMMITMENT, 390, 0, [true, true, false, true], [false, false, false, false]);
    }

    // ---------- retained checks ----------
    function test_repairRetainsEscrowProofAndOldCommitmentChecks() public {
        RepairedPrefixBatchConsumer c = _deploy();
        _fundO(c, 0);
        _fundO(c, 1);
        bool[4] memory none = [false, false, false, false];
        bool[4] memory f = [true, true, false, false];

        // limit 4 covers row 3, so the escrow check (not the prefix rule) rejects the missing funding
        vm.expectRevert(abi.encodeWithSelector(RepairedPrefixBatchConsumer.MissingEscrow.selector, 3));
        c.submit(pA, pB, pC, pub, 4);
        _assertState(c, idO, AMT_O, OLD_COMMITMENT, 350, 0, f, none);

        // altered public amount with the original proof: verifier rejects (before the prefix rule is reached)
        uint256[10] memory altered = pub;
        altered[0] = 101;
        assertFalse(verifier.verifyProof(pA, pB, pC, altered));
        vm.expectRevert(RepairedPrefixBatchConsumer.InvalidProof.selector);
        c.submit(pA, pB, pC, altered, 4);
        _assertState(c, idO, AMT_O, OLD_COMMITMENT, 350, 0, f, none);

        // stored commitment incompatible with the proof's old commitment
        RepairedPrefixBatchConsumer other =
            new RepairedPrefixBatchConsumer(IGroth16Verifier(address(verifier)), OLD_COMMITMENT + 1);
        vm.expectRevert(abi.encodeWithSelector(
            RepairedPrefixBatchConsumer.OldCommitmentMismatch.selector, OLD_COMMITMENT + 1, OLD_COMMITMENT));
        other.submit(pA, pB, pC, pub, 4);

        // after a legitimate settlement, replay is stopped by the old-commitment check
        _fundO(c, 3);
        c.submit(pA, pB, pC, pub, 4);
        vm.expectRevert(abi.encodeWithSelector(
            RepairedPrefixBatchConsumer.OldCommitmentMismatch.selector, NEW_COMMITMENT, OLD_COMMITMENT));
        c.submit(pA, pB, pC, pub, 4);
        _assertState(c, idO, AMT_O, NEW_COMMITMENT, 390, 390, [true, true, false, true], [true, true, false, true]);
    }
}
