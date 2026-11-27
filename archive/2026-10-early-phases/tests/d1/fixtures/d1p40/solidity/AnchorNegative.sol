// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IAnchorNegativeVerifier {
    function verify(bytes calldata proof, bytes32[] calldata publicInputs) external returns (bool);
}

contract AnchorNegative {
    IAnchorNegativeVerifier public verifier;
    mapping(bytes32 => bool) public admitted;
    bool public observed;

    function consume(bytes calldata proof, bytes32[] calldata publicInputs) external {
        require(publicInputs.length == 1);
        observed = admitted[publicInputs[0]];
        require(verifier.verify(proof, publicInputs));
    }
}
