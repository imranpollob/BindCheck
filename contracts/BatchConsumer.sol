// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

interface IGroth16Verifier {
    function verifyProof(
        uint256[2] calldata pA,
        uint256[2][2] calldata pB,
        uint256[2] calldata pC,
        uint256[10] calldata pubSignals
    ) external view returns (bool);
}

/// T02 minimal consumer for the T01 batch statement. Holds one balance commitment and
/// advances it only on a proof that verifies against the stored commitment.
/// No deposits, tokens, identities or access control: integration fixture only.
///
/// Public-signal order (T01, confirmed in reports/T01.md):
///   [0..3] amount[0..3]  [4..7] active[0..3]  [8] oldCommitment  [9] newCommitment
contract BatchConsumer {
    uint256 internal constant OLD_COMMITMENT_INDEX = 8;
    uint256 internal constant NEW_COMMITMENT_INDEX = 9;

    IGroth16Verifier public immutable verifier;
    uint256 public currentCommitment;

    error OldCommitmentMismatch(uint256 expected, uint256 provided);
    error InvalidProof();

    event CommitmentUpdated(uint256 oldCommitment, uint256 newCommitment);

    constructor(IGroth16Verifier verifier_, uint256 initialCommitment) {
        verifier = verifier_;
        currentCommitment = initialCommitment;
    }

    function submit(
        uint256[2] calldata pA,
        uint256[2][2] calldata pB,
        uint256[2] calldata pC,
        uint256[10] calldata pubSignals
    ) external {
        uint256 stored = currentCommitment;
        if (pubSignals[OLD_COMMITMENT_INDEX] != stored) {
            revert OldCommitmentMismatch(stored, pubSignals[OLD_COMMITMENT_INDEX]);
        }
        if (!verifier.verifyProof(pA, pB, pC, pubSignals)) revert InvalidProof();

        uint256 next = pubSignals[NEW_COMMITMENT_INDEX];
        currentCommitment = next;
        emit CommitmentUpdated(stored, next);
    }
}
