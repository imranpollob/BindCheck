// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IPrefixVerifier {
    function verify(bytes calldata proof, bytes32[] calldata publicInputs) external returns (bool);
}

contract AmbiguousPrefix {
    IPrefixVerifier public verifier;
    bytes32 public committed;

    function consume(bytes calldata proof, bytes32[] calldata publicInputs) external {
        require(publicInputs.length == 3);
        committed = publicInputs[0];
        require(verifier.verify(proof, publicInputs));
    }
}
