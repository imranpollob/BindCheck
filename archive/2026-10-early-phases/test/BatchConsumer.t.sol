// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {BatchConsumer, IGroth16Verifier} from "../contracts/BatchConsumer.sol";
import {Groth16Verifier} from "../contracts/generated/Groth16Verifier.sol";

/// Uses the real snarkjs-generated verifier and the T01 proof (build/T02/calldata.json,
/// written by `snarkjs zkey export soliditycalldata` from build/T01 proof.json/public.json).
/// setUp runs before every test, so each test starts from fresh deployments.
contract BatchConsumerTest is Test {
    // T01 example (reports/T01.md section 4).
    uint256 constant OLD_COMMITMENT = 4718284119804185511257508371982628095258483864365234338531443234707945892862;
    uint256 constant NEW_COMMITMENT = 1308650522590904424068291859776138677625716297266440279579353064214255920234;

    Groth16Verifier verifier;
    BatchConsumer consumer;

    uint256[2] pA;
    uint256[2][2] pB;
    uint256[2] pC;
    uint256[10] pub;

    event CommitmentUpdated(uint256 oldCommitment, uint256 newCommitment);

    function setUp() public {
        string memory j = vm.readFile("build/T02/calldata.json");
        uint256[] memory a = vm.parseJsonUintArray(j, "$[0]");
        uint256[] memory b0 = vm.parseJsonUintArray(j, "$[1][0]");
        uint256[] memory b1 = vm.parseJsonUintArray(j, "$[1][1]");
        uint256[] memory c = vm.parseJsonUintArray(j, "$[2]");
        uint256[] memory p = vm.parseJsonUintArray(j, "$[3]");
        assertEq(a.length, 2);
        assertEq(b0.length, 2);
        assertEq(b1.length, 2);
        assertEq(c.length, 2);
        assertEq(p.length, 10);
        pA = [a[0], a[1]];
        pB = [[b0[0], b0[1]], [b1[0], b1[1]]];
        pC = [c[0], c[1]];
        for (uint256 i = 0; i < 10; i++) pub[i] = p[i];

        // Fixture must be the T01 example in the T01 public-input order.
        uint256[10] memory expected = [
            uint256(100), 250, 0, 40, // amount[0..3]
            1, 1, 0, 1, // active[0..3]
            OLD_COMMITMENT, NEW_COMMITMENT
        ];
        for (uint256 i = 0; i < 10; i++) assertEq(pub[i], expected[i], "fixture differs from T01 example");

        verifier = new Groth16Verifier();
        consumer = new BatchConsumer(IGroth16Verifier(address(verifier)), OLD_COMMITMENT);
    }

    function test_honestProofAcceptedAndCommitmentUpdated() public {
        assertTrue(verifier.verifyProof(pA, pB, pC, pub), "verifier must accept T01 proof directly");
        assertEq(consumer.currentCommitment(), OLD_COMMITMENT);

        vm.expectEmit(address(consumer));
        emit CommitmentUpdated(OLD_COMMITMENT, NEW_COMMITMENT);
        consumer.submit(pA, pB, pC, pub);

        assertEq(consumer.currentCommitment(), NEW_COMMITMENT);
    }

    function test_alteredAmountWithOriginalProofRejectedByVerifier() public {
        pub[0] += 1; // amount[0]: 100 -> 101; commitments untouched
        // Precondition: the old-commitment check passes, so only the proof can reject.
        assertEq(pub[8], consumer.currentCommitment());
        assertFalse(verifier.verifyProof(pA, pB, pC, pub), "verifier must reject altered amount");

        // The consumer must actually call the verifier with all four arguments.
        vm.expectCall(address(verifier), abi.encodeCall(verifier.verifyProof, (pA, pB, pC, pub)));
        vm.expectRevert(BatchConsumer.InvalidProof.selector);
        consumer.submit(pA, pB, pC, pub);

        assertEq(consumer.currentCommitment(), OLD_COMMITMENT);
    }

    function test_invalidProofRejected_wrongCurvePoint() public {
        pA = pC; // on-curve G1 point, but not this proof's A
        assertFalse(verifier.verifyProof(pA, pB, pC, pub));

        vm.expectRevert(BatchConsumer.InvalidProof.selector);
        consumer.submit(pA, pB, pC, pub);

        assertEq(consumer.currentCommitment(), OLD_COMMITMENT);
    }

    function test_invalidProofRejected_pointNotOnCurve() public {
        pA[0] += 1; // (x+1, y) is (overwhelmingly) not on BN254 G1
        assertFalse(verifier.verifyProof(pA, pB, pC, pub));

        vm.expectRevert(BatchConsumer.InvalidProof.selector);
        consumer.submit(pA, pB, pC, pub);

        assertEq(consumer.currentCommitment(), OLD_COMMITMENT);
    }

    function test_validProofAgainstIncompatibleStoredCommitmentRejected() public {
        uint256 other = OLD_COMMITMENT + 1;
        BatchConsumer fresh = new BatchConsumer(IGroth16Verifier(address(verifier)), other);
        assertTrue(verifier.verifyProof(pA, pB, pC, pub), "proof itself is valid");

        vm.expectRevert(abi.encodeWithSelector(BatchConsumer.OldCommitmentMismatch.selector, other, OLD_COMMITMENT));
        fresh.submit(pA, pB, pC, pub);

        assertEq(fresh.currentCommitment(), other);
    }
}
