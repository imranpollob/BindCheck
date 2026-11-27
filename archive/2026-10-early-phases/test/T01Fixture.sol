// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";

/// Loads the T01 proof (build/T02/calldata.json) and pins the T01 example values as literals.
abstract contract T01Fixture is Test {
    uint256 constant OLD_COMMITMENT = 4718284119804185511257508371982628095258483864365234338531443234707945892862;
    uint256 constant NEW_COMMITMENT = 1308650522590904424068291859776138677625716297266440279579353064214255920234;

    uint256[2] pA;
    uint256[2][2] pB;
    uint256[2] pC;
    uint256[10] pub;

    function _loadFixture() internal {
        string memory j = vm.readFile("build/T02/calldata.json");
        uint256[] memory a = vm.parseJsonUintArray(j, "$[0]");
        uint256[] memory b0 = vm.parseJsonUintArray(j, "$[1][0]");
        uint256[] memory b1 = vm.parseJsonUintArray(j, "$[1][1]");
        uint256[] memory c = vm.parseJsonUintArray(j, "$[2]");
        uint256[] memory p = vm.parseJsonUintArray(j, "$[3]");
        assertEq(p.length, 10);
        pA = [a[0], a[1]];
        pB = [[b0[0], b0[1]], [b1[0], b1[1]]];
        pC = [c[0], c[1]];
        for (uint256 i = 0; i < 10; i++) pub[i] = p[i];

        uint256[10] memory expected = [uint256(100), 250, 0, 40, 1, 1, 0, 1, OLD_COMMITMENT, NEW_COMMITMENT];
        for (uint256 i = 0; i < 10; i++) assertEq(pub[i], expected[i], "fixture differs from T01 example");
    }
}
