// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./Verifier.sol";

contract MockToken {
    mapping(address => uint256) public balances;
    function safeTransfer(address recipient, uint256 amount) external { balances[recipient] += amount; }
}

contract Consumer {
    IVerifier public immutable verifier;
    MockToken public immutable token;
    mapping(address => uint256) public balances;
    mapping(uint256 => bool) public used;
    mapping(address => mapping(uint256 => bool)) public usedByCaller;
    uint256 public observed;

    constructor(IVerifier verifier_) { verifier = verifier_; token = new MockToken(); }

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
        uint256[] memory verifierInputs = new uint256[](3);
        for (uint256 i = 0; i < 3; i++) { verifierInputs[i] = publicInputs[i]; }
        require(verifier.verifyProof(verifierInputs), "proof");
        address provedRecipient = address(uint160(publicInputs[0]));
        uint256 provedAmount = publicInputs[1];
        _mint(provedRecipient, provedAmount);
    }

    function commit2(uint256 first, uint256 second) public pure returns (uint256) {
        return first * 1000003 + second;
    }

    function _mint(address recipient, uint256 amount) internal { balances[recipient] += amount; }
    function _safeMint(address recipient, uint256 tokenId) internal { balances[recipient] += tokenId + 1; }
    function _burn(address owner, uint256 amount) internal { balances[owner] -= amount; }
}
