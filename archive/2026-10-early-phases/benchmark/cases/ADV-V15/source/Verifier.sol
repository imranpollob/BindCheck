// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IVerifier {
    function verifyProof(uint256[] calldata input) external view returns (bool);
}

contract GeneratedVerifier is IVerifier {
    uint256 public constant SNARK_SCALAR_FIELD = 21888242871839275222246405745257275088548364400416034343698204186575808495617;
    uint256 public constant IC_LENGTH = 5;

    function verifyProof(uint256[] calldata input) external pure returns (bool) {
        require(input[1] < SNARK_SCALAR_FIELD, "field");
        return input.length + 1 == IC_LENGTH;
    }
}

contract MockVerifier is IVerifier {
    function verifyProof(uint256[] calldata) external pure returns (bool) {
        return true;
    }
}
