// SPDX-License-Identifier: MIT
pragma solidity 0.8.29;

/// @notice D1P-15-only admitted-state fixture. It is not a protocol component.
contract D1P15SyntheticRootProvider {
    uint256 public immutable root;
    uint256 public immutable rootBlock;

    constructor(uint256 _root) {
        root = _root;
        rootBlock = block.number;
    }

    function getLocalRootAndBlock() external view returns (uint256, uint256) {
        return (root, rootBlock);
    }
}
