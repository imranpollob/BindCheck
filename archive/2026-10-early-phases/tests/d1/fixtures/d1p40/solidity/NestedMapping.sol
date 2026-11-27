// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface INestedVerifier {
    function verify(bytes calldata proof, bytes32[] calldata publicInputs) external returns (bool);
}

contract NestedMapping {
    INestedVerifier public verifier;
    bytes32 public committed;

    function consume(bytes calldata proof, bytes32[] calldata publicInputs) external {
        require(publicInputs.length == 5);
        require(publicInputs[0] != bytes32(0));
        committed = publicInputs[4];
        require(verifier.verify(proof, publicInputs));
    }
}
