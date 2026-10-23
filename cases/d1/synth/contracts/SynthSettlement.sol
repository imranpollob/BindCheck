// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title SynthSettlement — authored D1-04 baseline consumer
/// @notice Models the same N=9, 3-word record grammar as the synthetic producer.
///         NOT derived from any third-party contract.
///
/// Record format: [kind, a, b] where kind 0=pad/end, 2=mint, 3=burn.
/// Records are processed in order; the first pad record ends the active stream.
/// A burn transfers `a` tokens to address `b`. A mint registers asset `a`.
///
/// This contract does NOT verify a real proof. It accepts a mock "proof valid"
/// flag for baseline testing only. The actual proof/verification boundary is
/// assumption A6 in the research contract.
contract SynthSettlement {
    uint256 public constant N = 9;
    uint256 public constant STRIDE = 3;
    uint256 public constant PAD_KIND = 0;
    uint256 public constant MINT_KIND = 2;
    uint256 public constant BURN_KIND = 3;

    event BurnSettled(uint256 indexed slot, uint256 value, uint256 recipient);
    event MintSettled(uint256 indexed slot, uint256 id);

    struct SettlementResult {
        uint256 burnCount;
        uint256 mintCount;
        bool reverted_;
    }

    /// @notice Settle a batch of records from the public message array.
    /// @param messages The 9-word public output from the producer circuit.
    /// @return result The settlement outcome.
    function settle(uint256[N] calldata messages) external returns (SettlementResult memory result) {
        for (uint256 i = 0; i + STRIDE <= N; i += STRIDE) {
            uint256 kind = messages[i];
            if (kind == PAD_KIND) {
                break;
            } else if (kind == BURN_KIND) {
                uint256 value = messages[i + 1];
                uint256 recipient = messages[i + 2];
                emit BurnSettled(i, value, recipient);
                result.burnCount++;
            } else if (kind == MINT_KIND) {
                uint256 id = messages[i + 1];
                emit MintSettled(i, id);
                result.mintCount++;
            } else {
                result.reverted_ = true;
                return result;
            }
        }
    }
}
