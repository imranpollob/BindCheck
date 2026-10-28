// SPDX-License-Identifier: MIT
// Compile-only stub mirroring the @openzeppelin/contracts-upgradeable 5.0.1
// OwnableUpgradeable API used by RollupV1 (`__Ownable_init`, `onlyOwner`,
// `owner`). NOT the real implementation. Used only so `solc` can typecheck
// binding mutants offline. Never deploy.
pragma solidity ^0.8.20;

import {Initializable} from "../proxy/utils/Initializable.sol";

abstract contract OwnableUpgradeable is Initializable {
    address private _owner;

    error OwnableUnauthorizedAccount(address account);

    function __Ownable_init(address initialOwner) internal onlyInitializing {
        _owner = initialOwner;
    }

    function owner() public view returns (address) {
        return _owner;
    }

    modifier onlyOwner() {
        if (msg.sender != _owner) revert OwnableUnauthorizedAccount(msg.sender);
        _;
    }
}
