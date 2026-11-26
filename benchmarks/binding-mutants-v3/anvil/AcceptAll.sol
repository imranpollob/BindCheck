// SPDX-License-Identifier: MIT
// Post-hoc Mythril arm only: a permissive dependency stub. Any call returns 32 bytes of 1, so
// bool-returning verifiers accept, void verifiers do not revert, and hash/oracle stubs return 1.
// Used identically for clean and mutant deployments; never used for an analysed target.
pragma solidity 0.8.28;
contract AcceptAll {
    fallback() external payable {
        assembly { mstore(0, 1) return(0, 32) }
    }
}
