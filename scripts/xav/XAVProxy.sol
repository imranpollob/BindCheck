// SPDX-License-Identifier: MIT
// Minimal ERC1967-slot proxy for the X-AV Payy harness (test scaffolding only).
// The project's own stack deploys RollupV1 behind a proxy because the
// implementation disables initializers; this plays the same role under the
// pinned solc 0.8.20 (OZ's ERC1967Proxy requires ^0.8.22).
pragma solidity ^0.8.20;

contract XAVProxy {
    bytes32 private constant IMPL_SLOT =
        0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc;

    constructor(address impl, bytes memory initData) payable {
        bytes32 slot = IMPL_SLOT;
        assembly {
            sstore(slot, impl)
        }
        (bool ok, ) = impl.delegatecall(initData);
        require(ok, "XAVProxy: init failed");
    }

    fallback() external payable {
        bytes32 slot = IMPL_SLOT;
        address impl;
        assembly {
            impl := sload(slot)
        }
        assembly {
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), impl, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
                case 0 {
                    revert(0, returndatasize())
                }
                default {
                    return(0, returndatasize())
                }
        }
    }

    receive() external payable {}
}
