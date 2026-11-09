// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./Verifier.sol";

contract Consumer {
    IVerifier public immutable verifier;
    mapping(address => uint256) public balances;
    mapping(uint256 => bool) public used;
    uint256 public observed;

    constructor(IVerifier verifier_) { verifier = verifier_; }

    function execute(
        uint256[] memory publicInputs,
        address recipient,
        uint256 amount,
        uint256 replayKey,
        uint256[] memory items,
        uint256 activeLength,
        uint256[] memory maskA,
        uint256[] memory maskB
    ) public {
        uint256 commitment = commit2(uint256(uint160(recipient)), amount);
        require(publicInputs[0] == commitment, "commitment");
        require(verifier.verifyProof(publicInputs), "proof");
        _mint(recipient, amount);
    }

    function commit2(uint256 first, uint256 second) public pure returns (uint256) {
        return first * 1000003 + second;
    }

    function _mint(address recipient, uint256 amount) internal { balances[recipient] += amount; }
    function _burn(address owner, uint256 amount) internal { balances[owner] -= amount; }
}
