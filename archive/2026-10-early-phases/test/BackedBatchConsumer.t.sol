// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import {T01Fixture} from "./T01Fixture.sol";
import {BackedBatchConsumer} from "../contracts/BackedBatchConsumer.sol";
import {IGroth16Verifier} from "../contracts/BatchConsumer.sol";
import {Groth16Verifier} from "../contracts/generated/Groth16Verifier.sol";

/// TEST-ONLY: reaches a state production code cannot reach (stored commitment rewound to the
/// batch's old commitment after the batch was consumed), so the consumption guard can be
/// exercised without the old-commitment check rejecting first.
contract RewindableConsumer is BackedBatchConsumer {
    constructor(IGroth16Verifier v, uint256 c) BackedBatchConsumer(v, c) {}

    function testOnly_setCommitment(uint256 c) external {
        currentCommitment = c;
    }
}

/// Expected values are written from the T01 public batch (amount [100,250,0,40],
/// active [1,1,0,1]) and recomputed independently here, not read back from the contract.
contract BackedBatchConsumerTest is T01Fixture {
    Groth16Verifier verifier;
    BackedBatchConsumer consumer;

    // Independent oracle inputs (literals from reports/T01.md section 4).
    uint256[4] AMOUNT = [uint256(100), 250, 0, 40];
    bool[4] ACTIVE = [true, true, false, true];
    uint256 constant EXPECTED_CREDIT = 390; // 100 + 250 + 40
    bytes32 batchId;

    event Funded(bytes32 indexed batchId, uint256 indexed row, uint256 amount);
    event Consumed(bytes32 indexed batchId, uint256 indexed row, uint256 amount);
    event CommitmentUpdated(uint256 oldCommitment, uint256 newCommitment);

    function setUp() public {
        _loadFixture();
        verifier = new Groth16Verifier();
        consumer = new BackedBatchConsumer(IGroth16Verifier(address(verifier)), OLD_COMMITMENT);
        batchId = keccak256(abi.encode(
            uint256(100), uint256(250), uint256(0), uint256(40),
            uint256(1), uint256(1), uint256(0), uint256(1),
            OLD_COMMITMENT, NEW_COMMITMENT
        ));
        assertEq(consumer.batchIdOf(pub), batchId, "contract batchId differs from independent encoding");
        // Precondition for every test: the honest proof itself verifies.
        assertTrue(verifier.verifyProof(pA, pB, pC, pub));
    }

    // ---------- helpers ----------
    function _fund(uint256 row) internal {
        consumer.fund{value: AMOUNT[row]}(pub, row);
    }

    function _fundAllActive() internal {
        for (uint256 r = 0; r < 4; r++) if (ACTIVE[r]) _fund(r);
    }

    function _escrow(BackedBatchConsumer c, uint256 row) internal view returns (uint256 amt, bool funded, bool consumed) {
        return c.escrows(batchId, row);
    }

    /// Exact state of every row: funded[] and consumed[] expectations; also commitment, ETH and backing.
    function _assertState(
        BackedBatchConsumer c,
        uint256 commitment,
        bool[4] memory funded,
        bool[4] memory consumed,
        uint256 backing,
        uint256 ethHeld
    ) internal view {
        assertEq(c.currentCommitment(), commitment, "commitment");
        for (uint256 r = 0; r < 4; r++) {
            (uint256 amt, bool f, bool k) = _escrow(c, r);
            assertEq(f, funded[r], "funded flag");
            assertEq(k, consumed[r], "consumed flag");
            assertEq(amt, funded[r] ? AMOUNT[r] : 0, "escrow amount");
        }
        assertEq(c.consumedBacking(), backing, "consumedBacking");
        assertEq(address(c).balance, ethHeld, "ETH held");
    }

    // ---------- 1. honest path ----------
    function test_fundRows0_1_3_thenSettlementSucceeds() public {
        _fund(0);
        _fund(1);
        _fund(3);
        assertEq(address(consumer).balance, EXPECTED_CREDIT);
        _assertState(consumer, OLD_COMMITMENT, [true, true, false, true], [false, false, false, false], 0, 390);

        vm.expectEmit(address(consumer));
        emit Consumed(batchId, 0, 100);
        vm.expectEmit(address(consumer));
        emit Consumed(batchId, 1, 250);
        vm.expectEmit(address(consumer));
        emit Consumed(batchId, 3, 40);
        vm.expectEmit(address(consumer));
        emit CommitmentUpdated(OLD_COMMITMENT, NEW_COMMITMENT);
        consumer.submit(pA, pB, pC, pub);

        // credited units: sum(active*amount) from the public batch values, computed independently
        uint256 credited;
        for (uint256 r = 0; r < 4; r++) if (pub[4 + r] == 1) credited += pub[r];
        assertEq(credited, 390);
        // rows 0,1,3 consumed with their own amounts; row 2 never funded, never consumed
        _assertState(consumer, NEW_COMMITMENT, [true, true, false, true], [true, true, false, true], 390, 390);
        (uint256 a0,,) = _escrow(consumer, 0);
        (uint256 a1,,) = _escrow(consumer, 1);
        (uint256 a3,,) = _escrow(consumer, 3);
        assertEq(a0, 100);
        assertEq(a1, 250);
        assertEq(a3, 40);
    }

    // ---------- 2. omitted funding, one test per active row ----------
    function _omitAndSubmit(uint256 omitted) internal {
        for (uint256 r = 0; r < 4; r++) if (ACTIVE[r] && r != omitted) _fund(r);
        bool[4] memory funded = [true, true, false, true];
        funded[omitted] = false;
        // Precondition: old-commitment check passes and proof verifies (asserted in setUp), so only
        // the escrow check can reject. Rows before `omitted` are consumed in-flight and must roll back.
        vm.expectRevert(abi.encodeWithSelector(BackedBatchConsumer.MissingEscrow.selector, omitted));
        consumer.submit(pA, pB, pC, pub);
        uint256 held = EXPECTED_CREDIT - AMOUNT[omitted];
        _assertState(consumer, OLD_COMMITMENT, funded, [false, false, false, false], 0, held);
    }

    function test_omittedFundingRow0Rejected() public { _omitAndSubmit(0); }
    function test_omittedFundingRow1Rejected() public { _omitAndSubmit(1); }
    function test_omittedFundingRow3Rejected() public { _omitAndSubmit(3); }

    function test_escrowForDifferentBatchDoesNotBackThisBatch() public {
        // Fund an otherwise-identical batch whose amount[0] is 101 (different batchId).
        uint256[10] memory other = pub;
        other[0] = 101;
        consumer.fund{value: 101}(other, 0);
        _fund(1);
        _fund(3);
        vm.expectRevert(abi.encodeWithSelector(BackedBatchConsumer.MissingEscrow.selector, 0));
        consumer.submit(pA, pB, pC, pub);
        _assertState(consumer, OLD_COMMITMENT, [false, true, false, true], [false, false, false, false], 0, 101 + 250 + 40);
    }

    // ---------- 3. incorrect funding amount ----------
    function test_incorrectFundingAmountRejected() public {
        _fund(1);
        _fund(3);
        vm.expectRevert(abi.encodeWithSelector(BackedBatchConsumer.WrongFundingAmount.selector, 0, 100, 99));
        consumer.fund{value: 99}(pub, 0);
        vm.expectRevert(abi.encodeWithSelector(BackedBatchConsumer.WrongFundingAmount.selector, 0, 100, 101));
        consumer.fund{value: 101}(pub, 0);
        // nothing was recorded for row 0, and settlement is blocked by that missing entry
        _assertState(consumer, OLD_COMMITMENT, [false, true, false, true], [false, false, false, false], 0, 290);
        vm.expectRevert(abi.encodeWithSelector(BackedBatchConsumer.MissingEscrow.selector, 0));
        consumer.submit(pA, pB, pC, pub);
    }

    // ---------- 4. inactive row ----------
    function test_inactiveRowNeedsNoEscrowAndCannotBeFunded() public {
        vm.expectRevert(abi.encodeWithSelector(BackedBatchConsumer.InactiveRow.selector, 2));
        consumer.fund{value: 0}(pub, 2);
        vm.expectRevert(abi.encodeWithSelector(BackedBatchConsumer.InactiveRow.selector, 2));
        consumer.fund{value: 1}(pub, 2);
        vm.expectRevert(abi.encodeWithSelector(BackedBatchConsumer.InvalidRow.selector, 4));
        consumer.fund{value: 1}(pub, 4);

        _fundAllActive();
        consumer.submit(pA, pB, pC, pub); // succeeds with row 2 never funded
        _assertState(consumer, NEW_COMMITMENT, [true, true, false, true], [true, true, false, true], 390, 390);
    }

    // ---------- 5. duplicate funding ----------
    function test_duplicateFundingRejected() public {
        _fund(0);
        vm.expectRevert(abi.encodeWithSelector(BackedBatchConsumer.AlreadyFunded.selector, 0));
        consumer.fund{value: 100}(pub, 0);
        _assertState(consumer, OLD_COMMITMENT, [true, false, false, false], [false, false, false, false], 0, 100);

        _fund(1);
        _fund(3);
        consumer.submit(pA, pB, pC, pub);
        // exactly 390 consumed, not 490: the duplicate payment never entered the contract
        _assertState(consumer, NEW_COMMITMENT, [true, true, false, true], [true, true, false, true], 390, 390);
    }

    // ---------- 6. repeat of an accepted settlement ----------
    function test_repeatAcceptedSettlementRejected_byOldCommitmentCheck() public {
        _fundAllActive();
        consumer.submit(pA, pB, pC, pub);
        // The stored commitment is now NEW; the replay is rejected by the old-commitment check
        // BEFORE the consumption guard is reached. This test does not exercise AlreadyConsumed.
        vm.expectRevert(abi.encodeWithSelector(BackedBatchConsumer.OldCommitmentMismatch.selector, NEW_COMMITMENT, OLD_COMMITMENT));
        consumer.submit(pA, pB, pC, pub);
        _assertState(consumer, NEW_COMMITMENT, [true, true, false, true], [true, true, false, true], 390, 390);
    }

    function test_consumptionGuardRejectsAlreadyConsumedEntries_isolatedWithHarness() public {
        RewindableConsumer r = new RewindableConsumer(IGroth16Verifier(address(verifier)), OLD_COMMITMENT);
        for (uint256 i = 0; i < 4; i++) if (ACTIVE[i]) r.fund{value: AMOUNT[i]}(pub, i);
        r.submit(pA, pB, pC, pub);
        _assertState(r, NEW_COMMITMENT, [true, true, false, true], [true, true, false, true], 390, 390);

        // Test-only rewind makes the old-commitment check and the proof pass again; the only
        // remaining reason to reject is the consumed escrow (row 0 is checked first).
        r.testOnly_setCommitment(OLD_COMMITMENT);
        assertTrue(verifier.verifyProof(pA, pB, pC, pub));
        vm.expectRevert(abi.encodeWithSelector(BackedBatchConsumer.AlreadyConsumed.selector, 0));
        r.submit(pA, pB, pC, pub);
        // entries stay consumed exactly once; backing not double counted
        _assertState(r, OLD_COMMITMENT, [true, true, false, true], [true, true, false, true], 390, 390);
    }

    // ---------- 7. other failed settlements preserve everything (all rows funded) ----------
    function test_invalidProofWithFullEscrowLeavesStateUnchanged() public {
        _fundAllActive();
        uint256[10] memory altered = pub;
        altered[0] = 101; // original proof, altered public amount: batchId changes, verifier must reject
        assertFalse(verifier.verifyProof(pA, pB, pC, altered));
        vm.expectRevert(BackedBatchConsumer.InvalidProof.selector);
        consumer.submit(pA, pB, pC, altered);
        _assertState(consumer, OLD_COMMITMENT, [true, true, false, true], [false, false, false, false], 0, 390);
    }

    function test_oldCommitmentMismatchWithFullEscrowLeavesStateUnchanged() public {
        RewindableConsumer r = new RewindableConsumer(IGroth16Verifier(address(verifier)), OLD_COMMITMENT + 1);
        for (uint256 i = 0; i < 4; i++) if (ACTIVE[i]) r.fund{value: AMOUNT[i]}(pub, i);
        vm.expectRevert(abi.encodeWithSelector(BackedBatchConsumer.OldCommitmentMismatch.selector, OLD_COMMITMENT + 1, OLD_COMMITMENT));
        r.submit(pA, pB, pC, pub);
        // r is a different instance, so the shared helper is told its (different) starting commitment
        _assertState(r, OLD_COMMITMENT + 1, [true, true, false, true], [false, false, false, false], 0, 390);
    }
}
