// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import {console2} from "forge-std/console2.sol";
import {T01Fixture} from "./T01Fixture.sol";
import {BackedBatchConsumer} from "../contracts/BackedBatchConsumer.sol";
import {ResearchMutantBackedBatchConsumer} from "../contracts/research/MutantBackedBatchConsumer.sol";
import {IGroth16Verifier} from "../contracts/BatchConsumer.sol";
import {Groth16Verifier} from "../contracts/generated/Groth16Verifier.sol";

/// T04 research-authored coverage failure (local Foundry EVM, synthetic accounts, test ETH).
/// Same real verifier and same T01 proof for the correct (T03) consumer, the mutant, and the control.
/// The invariant is measured from RAW STORAGE SLOTS and ETH balances against T01 literals, not from
/// the contract's own accounting. No vm.store / vm.mockCall / forged proof / circuit change is used.
contract MutantBackedBatchConsumerTest is T01Fixture {
    // Storage layout of both consumers (forge inspect): slot0 currentCommitment, slot1 consumedBacking,
    // slot2 escrows mapping. Escrow struct = slot a: amount; slot a+1: funded (byte 0), consumed (byte 1).
    uint256 constant SLOT_COMMITMENT = 0;
    uint256 constant SLOT_BACKING = 1;
    uint256 constant SLOT_ESCROWS = 2;

    // Independent oracle inputs (T01 example, reports/T01.md section 4).
    uint256[4] AMOUNT = [uint256(100), 250, 0, 40];
    bool[4] ACTIVE = [true, true, false, true];
    uint256 constant REQUIRED_CREDIT = 390; // sum(active[i]*amount[i]); 1000 -> 1390 balance transition

    Groth16Verifier verifier;
    bytes32 batchId;

    struct Measure {
        uint256 commitment;
        uint256 eth;
        uint256 rawBacking;
        uint256 matchingConsumed; // wei of consumed entries that match a required (active) row's amount
        uint256 missing;          // REQUIRED_CREDIT - matchingConsumed
        bool[4] consumed;
        bool[4] funded;
    }

    function setUp() public {
        _loadFixture();
        verifier = new Groth16Verifier();
        batchId = keccak256(abi.encode(
            uint256(100), uint256(250), uint256(0), uint256(40),
            uint256(1), uint256(1), uint256(0), uint256(1),
            OLD_COMMITMENT, NEW_COMMITMENT
        ));
        // Precondition for every test: the unmodified T01 proof verifies against the real verifier.
        assertTrue(verifier.verifyProof(pA, pB, pC, pub), "T01 proof must verify");
    }

    // ---------- deployment / funding helpers ----------
    function _correct() internal returns (BackedBatchConsumer) {
        return new BackedBatchConsumer(IGroth16Verifier(address(verifier)), OLD_COMMITMENT);
    }

    function _mutant() internal returns (ResearchMutantBackedBatchConsumer) {
        return new ResearchMutantBackedBatchConsumer(IGroth16Verifier(address(verifier)), OLD_COMMITMENT);
    }

    function _fundCorrect(BackedBatchConsumer c, uint256 row) internal {
        c.fund{value: AMOUNT[row]}(pub, row);
    }

    function _fundMutant(ResearchMutantBackedBatchConsumer c, uint256 row) internal {
        c.fund{value: AMOUNT[row]}(pub, row);
    }

    // ---------- raw-storage measurement (works for both: identical layout) ----------
    function _escrowBase(uint256 row) internal view returns (bytes32) {
        bytes32 inner = keccak256(abi.encode(batchId, SLOT_ESCROWS));
        return keccak256(abi.encode(row, inner));
    }

    function _rawEscrow(address c, uint256 row) internal view returns (uint256 amount, bool funded, bool consumed) {
        bytes32 base = _escrowBase(row);
        amount = uint256(vm.load(c, base));
        uint256 packed = uint256(vm.load(c, bytes32(uint256(base) + 1)));
        funded = (packed & 0xff) == 1;
        consumed = ((packed >> 8) & 0xff) == 1;
    }

    function _measure(address c) internal view returns (Measure memory m) {
        m.commitment = uint256(vm.load(c, bytes32(SLOT_COMMITMENT)));
        m.rawBacking = uint256(vm.load(c, bytes32(SLOT_BACKING)));
        m.eth = c.balance;
        for (uint256 r = 0; r < 4; r++) {
            (uint256 amt, bool f, bool k) = _rawEscrow(c, r);
            m.funded[r] = f;
            m.consumed[r] = k;
            if (ACTIVE[r] && f && k && amt == AMOUNT[r]) m.matchingConsumed += amt;
        }
        m.missing = REQUIRED_CREDIT - m.matchingConsumed;
    }

    function _crossCheckRawAgainstGetters(BackedBatchConsumer c) internal view {
        Measure memory m = _measure(address(c));
        assertEq(m.commitment, c.currentCommitment(), "raw slot0 != getter");
        assertEq(m.rawBacking, c.consumedBacking(), "raw slot1 != getter");
        for (uint256 r = 0; r < 4; r++) {
            (uint256 a, bool f, bool k) = c.escrows(batchId, r);
            (uint256 ra, bool rf, bool rk) = _rawEscrow(address(c), r);
            assertEq(a, ra);
            assertEq(f, rf);
            assertEq(k, rk);
        }
    }

    function _crossCheckRawAgainstGetters(ResearchMutantBackedBatchConsumer c) internal view {
        Measure memory m = _measure(address(c));
        assertEq(m.commitment, c.currentCommitment(), "raw slot0 != getter");
        assertEq(m.rawBacking, c.consumedBacking(), "raw slot1 != getter");
        for (uint256 r = 0; r < 4; r++) {
            (uint256 a, bool f, bool k) = c.escrows(batchId, r);
            (uint256 ra, bool rf, bool rk) = _rawEscrow(address(c), r);
            assertEq(a, ra);
            assertEq(f, rf);
            assertEq(k, rk);
        }
    }

    function _log(string memory label, Measure memory m) internal pure {
        console2.log(label);
        console2.log("  commitment      ", m.commitment);
        console2.log("  eth held        ", m.eth);
        console2.log("  rawBacking      ", m.rawBacking);
        console2.log("  matchingConsumed", m.matchingConsumed);
        console2.log("  missing backing ", m.missing);
        console2.log("  consumed r0,r1,r2,r3:", m.consumed[0], m.consumed[1]);
        console2.log("                      ", m.consumed[2], m.consumed[3]);
        console2.log("  funded   r0,r1,r2,r3:", m.funded[0], m.funded[1]);
        console2.log("                      ", m.funded[2], m.funded[3]);
    }

    function _callDataHash() internal view returns (bytes32) {
        return keccak256(abi.encode(pA, pB, pC, pub));
    }

    // ================= 1. correct T03 consumer =================
    function test_correctConsumer_rejectsPartiallyFundedBatch_missingEscrowRow3() public {
        BackedBatchConsumer c = _correct();
        _fundCorrect(c, 0);
        _fundCorrect(c, 1);
        _crossCheckRawAgainstGetters(c);
        Measure memory pre = _measure(address(c));
        assertEq(pre.eth, 350);
        assertEq(pre.commitment, OLD_COMMITMENT);

        console2.log("proof/public-input calldata hash (correct consumer):");
        console2.logBytes32(_callDataHash());
        vm.expectCall(address(verifier), abi.encodeCall(verifier.verifyProof, (pA, pB, pC, pub)));
        vm.expectRevert(abi.encodeWithSelector(BackedBatchConsumer.MissingEscrow.selector, 3));
        c.submit(pA, pB, pC, pub);

        Measure memory post = _measure(address(c));
        _log("correct consumer, post (reverted)", post);
        assertEq(post.commitment, pre.commitment, "commitment changed");
        assertEq(post.eth, pre.eth);
        assertEq(post.rawBacking, 0);
        for (uint256 r = 0; r < 4; r++) {
            assertEq(post.consumed[r], false, "an entry was consumed");
            assertEq(post.funded[r], pre.funded[r]);
        }
        assertEq(post.matchingConsumed, 0);
        assertEq(post.missing, REQUIRED_CREDIT);
        _crossCheckRawAgainstGetters(c);
    }

    // ================= 2. research mutant, numRealTxs = 3 =================
    function test_RESEARCH_MUTANT_numRealTxs3_acceptsVerifiedProofWithRow3Unbacked_confirmsInvariantViolation() public {
        ResearchMutantBackedBatchConsumer m = _mutant();
        _fundMutant(m, 0);
        _fundMutant(m, 1);
        _crossCheckRawAgainstGetters(m);
        Measure memory pre = _measure(address(m));
        _log("mutant, pre", pre);
        assertEq(pre.eth, 350);
        assertEq(pre.commitment, OLD_COMMITMENT);
        assertFalse(pre.funded[3], "row 3 must be unfunded");

        // Same proof + same ten public inputs as the correct consumer's call; real verifier accepts them.
        console2.log("proof/public-input calldata hash (mutant):");
        console2.logBytes32(_callDataHash());
        assertTrue(verifier.verifyProof(pA, pB, pC, pub), "real verifier accepts the proof");
        vm.expectCall(address(verifier), abi.encodeCall(verifier.verifyProof, (pA, pB, pC, pub)));
        m.submit(pA, pB, pC, pub, 3); // accepted: no revert

        Measure memory post = _measure(address(m));
        _log("mutant, post (ACCEPTED)", post);
        _crossCheckRawAgainstGetters(m);

        // State advanced on the strength of the verified proof...
        assertEq(post.commitment, NEW_COMMITMENT, "commitment advanced to the authenticated new commitment");
        // ...but backing is short. All figures below come from T01 literals + raw storage + ETH balance.
        assertEq(REQUIRED_CREDIT, 100 + 250 + 40, "required batch credit");
        assertEq(post.matchingConsumed, 350, "newly consumed matching backing");
        assertEq(post.eth, 350, "ETH held equals backing; nothing for row 3");
        assertEq(post.rawBacking, 350);
        assertEq(post.missing, 40, "missing required backing");
        assertEq(REQUIRED_CREDIT - post.matchingConsumed, AMOUNT[3], "deficit equals row 3's amount");

        // The omitted obligation is exactly this batch's row 3: active, amount 40, never funded, never consumed.
        for (uint256 r = 0; r < 4; r++) {
            bool requiredAndUnbacked = ACTIVE[r] && !(post.funded[r] && post.consumed[r]);
            assertEq(requiredAndUnbacked, r == 3, "only row 3 is required-but-unbacked");
        }
        (uint256 a3, bool f3, bool k3) = _rawEscrow(address(m), 3);
        assertEq(a3, 0);
        assertFalse(f3);
        assertFalse(k3);

        // Invariant (T03 section 4): every active row consumed an exact-amount entry whenever the commitment advances.
        bool invariantHolds = post.commitment == NEW_COMMITMENT && post.missing == 0;
        assertFalse(invariantHolds, "intended research mutation must make the invariant fail");
    }

    // ================= 3. control: fully funded, numRealTxs = 4 =================
    function test_control_mutantFullyFundedNumRealTxs4_consumesAllThreeActiveEntries() public {
        ResearchMutantBackedBatchConsumer m = _mutant();
        _fundMutant(m, 0);
        _fundMutant(m, 1);
        _fundMutant(m, 3);
        assertEq(address(m).balance, 390);

        console2.log("proof/public-input calldata hash (control):");
        console2.logBytes32(_callDataHash());
        vm.expectCall(address(verifier), abi.encodeCall(verifier.verifyProof, (pA, pB, pC, pub)));
        m.submit(pA, pB, pC, pub, 4);

        Measure memory post = _measure(address(m));
        _log("control (mutant, numRealTxs=4), post", post);
        _crossCheckRawAgainstGetters(m);
        assertEq(post.commitment, NEW_COMMITMENT);
        assertEq(post.matchingConsumed, 390);
        assertEq(post.rawBacking, 390);
        assertEq(post.eth, 390);
        assertEq(post.missing, 0);
        assertTrue(post.consumed[0] && post.consumed[1] && post.consumed[3]);
        assertFalse(post.consumed[2]);
        assertFalse(post.funded[2]);
    }

    // ================= mutant keeps every other check =================
    function test_mutant_retainsOldCommitmentProofAndBoundChecks() public {
        ResearchMutantBackedBatchConsumer m = _mutant();
        _fundMutant(m, 0);
        _fundMutant(m, 1);
        Measure memory pre = _measure(address(m));

        // bound 0..4
        vm.expectRevert(abi.encodeWithSelector(ResearchMutantBackedBatchConsumer.InvalidNumRealTxs.selector, 5));
        m.submit(pA, pB, pC, pub, 5);

        // altered public amount, original proof, even with a permissive prefix
        uint256[10] memory altered = pub;
        altered[0] = 101;
        assertFalse(verifier.verifyProof(pA, pB, pC, altered));
        vm.expectRevert(ResearchMutantBackedBatchConsumer.InvalidProof.selector);
        m.submit(pA, pB, pC, altered, 3);

        // stored commitment incompatible with the proof's old commitment
        ResearchMutantBackedBatchConsumer other =
            new ResearchMutantBackedBatchConsumer(IGroth16Verifier(address(verifier)), OLD_COMMITMENT + 1);
        vm.expectRevert(abi.encodeWithSelector(ResearchMutantBackedBatchConsumer.OldCommitmentMismatch.selector, OLD_COMMITMENT + 1, OLD_COMMITMENT));
        other.submit(pA, pB, pC, pub, 3);

        // funding rules are unchanged: wrong amount, duplicate, inactive row
        vm.expectRevert(abi.encodeWithSelector(ResearchMutantBackedBatchConsumer.WrongFundingAmount.selector, 3, 40, 39));
        m.fund{value: 39}(pub, 3);
        vm.expectRevert(abi.encodeWithSelector(ResearchMutantBackedBatchConsumer.AlreadyFunded.selector, 0));
        m.fund{value: 100}(pub, 0);
        vm.expectRevert(abi.encodeWithSelector(ResearchMutantBackedBatchConsumer.InactiveRow.selector, 2));
        m.fund{value: 0}(pub, 2);

        // inside the prefix the escrow checks still apply: numRealTxs=4 with row 3 unfunded rejects
        vm.expectRevert(abi.encodeWithSelector(ResearchMutantBackedBatchConsumer.MissingEscrow.selector, 3));
        m.submit(pA, pB, pC, pub, 4);

        Measure memory post = _measure(address(m));
        assertEq(post.commitment, pre.commitment);
        assertEq(post.eth, pre.eth);
        assertEq(post.rawBacking, 0);
        for (uint256 r = 0; r < 4; r++) assertFalse(post.consumed[r]);
    }
}
