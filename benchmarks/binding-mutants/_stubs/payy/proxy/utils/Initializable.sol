// SPDX-License-Identifier: MIT
// Compile-only stub mirroring the @openzeppelin/contracts-upgradeable 5.0.1
// `initializer` modifier API used by RollupV1. NOT the real implementation:
// no version tracking, no reinitializer guard. Used only so `solc` can
// typecheck binding mutants offline. Never deploy.
pragma solidity ^0.8.20;

abstract contract Initializable {
    bool private _initialized;

    error InvalidInitialization();

    modifier initializer() {
        if (_initialized) revert InvalidInitialization();
        _initialized = true;
        _;
    }

    modifier onlyInitializing() {
        _;
    }

    function _disableInitializers() internal {
        _initialized = true;
    }
}
