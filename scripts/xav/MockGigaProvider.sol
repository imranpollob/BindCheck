// SPDX-License-Identifier: MIT
// Minimal IGigaRootProvider stand-in for automatic validation replays.
// Returns a fixed root; no access control. Local EDR use only.
pragma solidity 0.8.29;

contract MockGigaProvider {
    uint256 private _gigaRoot;

    constructor(uint256 root) {
        _gigaRoot = root;
    }

    function gigaRoot() external view returns (uint256) {
        return _gigaRoot;
    }
}
