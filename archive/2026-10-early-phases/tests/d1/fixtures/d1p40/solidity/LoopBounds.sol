// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface ILoopVerifier {
    function verify(bytes calldata proof, bytes32[] calldata publicInputs) external returns (bool);
}

contract LoopBounds {
    ILoopVerifier public verifier;
    mapping(uint256 => bytes32) public committed;

    function consume(bytes calldata proof, bytes32[] calldata publicInputs) external {
        require(publicInputs.length == 4);
        uint256 i = 0;
        while (i < 2) {
            committed[i] = publicInputs[i];
            i += 1;
        }
        require(verifier.verify(proof, publicInputs));
    }
}
