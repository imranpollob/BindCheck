// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import {IGroth16Verifier} from "../BatchConsumer.sol";

/// RESEARCH-AUTHORED MUTANT (T04). DO NOT DEPLOY OR REUSE. Self-authored coverage failure for
/// local defensive research, not a vulnerability in any real-world system.
/// Identical to BackedBatchConsumer (T03) except: submit() takes a caller-supplied `numRealTxs`
/// (0..4) and only processes/consumes active rows with index < numRealTxs; nothing enforces that
/// rows outside the prefix are neutral. numRealTxs is NOT part of the verified statement.
///
/// T03: T02's consumer extended with per-row ETH escrow backing. TEST ARCHITECTURE ONLY.
///
/// Demonstration identity (the T01 circuit has no deposit IDs):
///   batchId   = keccak256(abi.encode(all ten public inputs))
///   deposit   = (batchId, rowIndex)
/// Because batchId commits to every public input, an escrow entry is bound to one exact
/// batch (amounts, flags, old and new commitment) and one row. This is not a general
/// deposit protocol: there are no depositor identities, nullifiers, refunds, withdrawals
/// or cancellation. ETH stays in this contract; "consumption" reclassifies an escrow entry
/// as backing for the credited balance (1 unit == 1 wei by convention here).
///
/// Public-signal order (T01): [0..3] amount, [4..7] active, [8] oldCommitment, [9] newCommitment.
contract ResearchMutantBackedBatchConsumer {
    uint256 internal constant ROWS = 4;
    uint256 internal constant ACTIVE_OFFSET = 4;
    uint256 internal constant OLD_COMMITMENT_INDEX = 8;
    uint256 internal constant NEW_COMMITMENT_INDEX = 9;

    struct Escrow {
        uint256 amount; // wei received for this (batchId, row)
        bool funded;
        bool consumed;
    }

    IGroth16Verifier public immutable verifier;
    uint256 public currentCommitment;
    /// Total wei reclassified from escrow to backing by accepted settlements.
    uint256 public consumedBacking;

    mapping(bytes32 batchId => mapping(uint256 row => Escrow)) public escrows;

    error InvalidRow(uint256 row);
    error InactiveRow(uint256 row);
    error WrongFundingAmount(uint256 row, uint256 expected, uint256 provided);
    error AlreadyFunded(uint256 row);
    error OldCommitmentMismatch(uint256 expected, uint256 provided);
    error InvalidProof();
    error MissingEscrow(uint256 row);
    error AlreadyConsumed(uint256 row);
    error EscrowAmountMismatch(uint256 row, uint256 expected, uint256 stored);
    error InvalidNumRealTxs(uint256 numRealTxs);

    event Funded(bytes32 indexed batchId, uint256 indexed row, uint256 amount);
    event Consumed(bytes32 indexed batchId, uint256 indexed row, uint256 amount);
    event CommitmentUpdated(uint256 oldCommitment, uint256 newCommitment);

    constructor(IGroth16Verifier verifier_, uint256 initialCommitment) {
        verifier = verifier_;
        currentCommitment = initialCommitment;
    }

    function batchIdOf(uint256[10] calldata pubSignals) public pure returns (bytes32) {
        return keccak256(abi.encode(pubSignals));
    }

    /// Escrow exactly `pubSignals[row]` wei for an active row of the claimed batch.
    /// The batch is not proof-checked here; an escrow for a batch that is never proven just
    /// stays locked (no withdrawals exist in this demonstration).
    function fund(uint256[10] calldata pubSignals, uint256 row) external payable {
        if (row >= ROWS) revert InvalidRow(row);
        if (pubSignals[ACTIVE_OFFSET + row] != 1) revert InactiveRow(row);
        uint256 amount = pubSignals[row];
        if (msg.value != amount) revert WrongFundingAmount(row, amount, msg.value);

        Escrow storage e = escrows[batchIdOf(pubSignals)][row];
        if (e.funded) revert AlreadyFunded(row);
        e.amount = amount;
        e.funded = true;
        emit Funded(batchIdOf(pubSignals), row, amount);
    }

    function submit(
        uint256[2] calldata pA,
        uint256[2][2] calldata pB,
        uint256[2] calldata pC,
        uint256[10] calldata pubSignals,
        uint256 numRealTxs
    ) external {
        if (numRealTxs > ROWS) revert InvalidNumRealTxs(numRealTxs);
        uint256 stored = currentCommitment;
        if (pubSignals[OLD_COMMITMENT_INDEX] != stored) {
            revert OldCommitmentMismatch(stored, pubSignals[OLD_COMMITMENT_INDEX]);
        }
        if (!verifier.verifyProof(pA, pB, pC, pubSignals)) revert InvalidProof();

        // Every active row (flag == 1; the proof forces flags to be Boolean) needs a funded,
        // unconsumed entry of exactly its public amount. Any failure reverts the whole call.
        bytes32 batchId = batchIdOf(pubSignals);
        uint256 backed;
        for (uint256 row = 0; row < numRealTxs; row++) {
            if (pubSignals[ACTIVE_OFFSET + row] != 1) continue;
            Escrow storage e = escrows[batchId][row];
            if (!e.funded) revert MissingEscrow(row);
            if (e.consumed) revert AlreadyConsumed(row);
            if (e.amount != pubSignals[row]) revert EscrowAmountMismatch(row, pubSignals[row], e.amount);
            e.consumed = true;
            backed += e.amount;
            emit Consumed(batchId, row, e.amount);
        }
        consumedBacking += backed;

        uint256 next = pubSignals[NEW_COMMITMENT_INDEX];
        currentCommitment = next;
        emit CommitmentUpdated(stored, next);
    }
}
