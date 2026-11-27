// SPDX-License-Identifier: MIT
pragma solidity 0.8.29;

/// @dev D1P-14B V-EXEC-only verifier stub. It accepts exactly one public-input
/// vector. It is never part of a primary query and is not a proof/verifier
/// soundness claim; amended section 6(b) explicitly requires this boundary.
contract D1P14BVectorVerifier {
    bytes32 public immutable expectedVectorHash;

    constructor(bytes32 _expectedVectorHash) {
        expectedVectorHash = _expectedVectorHash;
    }

    function verify(bytes calldata, bytes32[] calldata publicInputs)
        external view returns (bool)
    {
        return keccak256(abi.encode(publicInputs)) == expectedVectorHash;
    }
}
