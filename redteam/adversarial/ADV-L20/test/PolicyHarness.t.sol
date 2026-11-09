// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../Consumer.sol";
import "../Verifier.sol";

/// Generated from policy.json only. The mock verifier deliberately returns true.
contract PolicyHarness {
    function testPolicyAttempt() public {
        MockVerifier verifier = new MockVerifier();
        Consumer consumer = new Consumer(IVerifier(address(verifier)));
        uint256[] memory publicInputs = new uint256[](4);
        publicInputs[0] = uint256(uint160(address(0xBEEF)));
        publicInputs[1] = 7;
        publicInputs[2] = 11;
        publicInputs[3] = 2;
        uint256[] memory items = new uint256[](4);
        items[0] = 3;
        items[1] = 4;
        uint256[] memory maskA = new uint256[](4);
        uint256[] memory maskB = new uint256[](4);
        maskA[0] = 1;
        maskB[0] = 1;
        consumer.execute(publicInputs, address(this), 9, 13, items, 2, maskA, maskB);
        // Policy permits this caller/effect shape; the harness records execution only.
    }
}
