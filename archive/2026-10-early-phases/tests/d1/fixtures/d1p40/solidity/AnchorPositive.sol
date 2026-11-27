// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IAnchorPositiveVerifier {
    function verify(bytes calldata proof, bytes32[] calldata publicInputs) external returns (bool);
}

contract AnchorPositive {
    IAnchorPositiveVerifier public verifier;
    mapping(bytes32 => bool) public admitted;

    function consume(bytes calldata proof, bytes32[] calldata publicInputs) external {
        require(publicInputs.length == 1);
        require(admitted[publicInputs[0]]);
        require(verifier.verify(proof, publicInputs));
    }
}
