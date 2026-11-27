// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IEffectVerifier {
    function verify(bytes calldata proof, bytes32[] calldata publicInputs) external returns (bool);
}

interface IERC20D1P40 {
    function transfer(address recipient, uint256 amount) external returns (bool);
}

contract Effects {
    IEffectVerifier public verifier;
    IERC20D1P40 public token;
    bytes32 public committed;

    function helper(address, uint256) internal pure {}

    function consume(bytes calldata proof, bytes32[] calldata publicInputs, address recipient) external {
        require(publicInputs.length == 3);
        committed = publicInputs[0];
        token.transfer(recipient, uint256(publicInputs[1]));
        helper(recipient, uint256(publicInputs[2]));
        require(verifier.verify(proof, publicInputs));
    }
}
