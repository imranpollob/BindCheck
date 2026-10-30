// SPDX-License-Identifier: MIT
pragma solidity 0.8.29;

interface IExtentVerifierLimited {
    function verify(bytes calldata proof, bytes32[] calldata publicInputs)
        external view returns (bool);
}

contract ConsumerLimited {
    IExtentVerifierLimited public immutable verifier;
    bytes32 public accumulator;

    constructor(IExtentVerifierLimited verifier_) { verifier = verifier_; }

    function consume(
        bytes calldata proof,
        bytes32[] calldata publicInputs
    ) external {
        require(publicInputs.length == 5, "width");
        uint32 activeCount = uint32(uint256(publicInputs[4]));
        require(activeCount <= 4, "extent");
        for (uint256 i = 0; i < activeCount; i++) {
            accumulator = accumulator ^ publicInputs[i];
        }
        require(verifier.verify(proof, publicInputs), "proof");
    }
}
