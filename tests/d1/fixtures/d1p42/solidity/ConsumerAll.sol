// SPDX-License-Identifier: MIT
pragma solidity 0.8.29;

interface IExtentVerifierAll {
    function verify(bytes calldata proof, bytes32[] calldata publicInputs)
        external view returns (bool);
}

contract ConsumerAll {
    IExtentVerifierAll public immutable verifier;
    bytes32 public accumulator;

    constructor(IExtentVerifierAll verifier_) { verifier = verifier_; }

    function consume(bytes calldata proof, bytes32[] calldata publicInputs) external {
        require(publicInputs.length == 5, "width");
        for (uint256 i = 0; i < 4; i++) {
            accumulator = accumulator ^ publicInputs[i];
        }
        require(verifier.verify(proof, publicInputs), "proof");
    }
}
