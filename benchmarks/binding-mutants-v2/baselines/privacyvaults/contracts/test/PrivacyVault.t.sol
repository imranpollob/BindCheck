// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {TestBase} from "./TestBase.t.sol";
import {IPrivacyVault} from "../src/interfaces/IPrivacyVault.sol";

contract PrivacyVaultTest is TestBase {
    function setUp() public override {
        super.setUp();
    }

    function testGetCommitment() public {
        (bytes32 commitment, bytes32 nullifier, bytes32 secret) = _getCommitment();
        assertTrue(commitment != 0);
        assertTrue(nullifier != 0);
        assertTrue(secret != 0);
    }

    function testMakeDeposit() public {
        // create a commitment
        // make a DepositWithAuthorization
        (bytes32 _commitment, bytes32 _nullifier, bytes32 _secret) = _getCommitment();
        bytes memory signature = _getSignature(depositor);
        uint256 yieldIndex = privacyVault.getCurrentBucketedYieldIndex();
        bytes32 finalCommitment = privacyVault.hashLeftRight(_commitment, bytes32(yieldIndex));
        vm.expectEmit(true, false, false, true);
        emit IPrivacyVault.DepositWithAuthorization(finalCommitment, 0, block.timestamp, yieldIndex);
        vm.prank(depositor);
        privacyVault.depositWithAuthorization(_commitment, signature);
        // Each half goes to a different protocol
        assertEq(
            aavePool.getUserBalance(address(privacyVault), address(usdc)),
            privacyVault.DENOMINATION() / 2,
            "Aave should have half the deposit"
        );
    }

    function testMakeWithdrawal() public {
        // make a deposit
        (bytes32 _commitment, bytes32 _nullifier, bytes32 _secret) = _getCommitment();
        bytes memory signature = _getSignature(depositor);
        uint256 yieldIndex = privacyVault.getCurrentBucketedYieldIndex();
        bytes32 finalCommitment = privacyVault.hashLeftRight(_commitment, bytes32(yieldIndex));

        vm.expectEmit(true, false, false, true);
        emit IPrivacyVault.DepositWithAuthorization(finalCommitment, 0, block.timestamp, yieldIndex);
        vm.prank(depositor);
        privacyVault.depositWithAuthorization(_commitment, signature);

        bytes32[] memory leaves = new bytes32[](1);
        leaves[0] = finalCommitment;
        // create a proof (now returns 5 public inputs)
        (bytes memory _proof, bytes32[] memory _publicInputs) =
            _getProof(_nullifier, _secret, recipient, bytes32(yieldIndex), leaves, false);

        // make a withdrawal (now includes collateralNullifierHash at index 2)
        assertEq(usdc.balanceOf(recipient), 0, "Recipient should have 0 balance before withdrawal");
        privacyVault.withdraw(
            _proof,
            _publicInputs[0],
            _publicInputs[1],
            _publicInputs[2], // collateralNullifierHash
            address(uint160(uint256(_publicInputs[3]))),
            uint256(_publicInputs[4])
        );
        uint256 denom = privacyVault.DENOMINATION();
        uint256 fee = (denom * privacyVault.s_withdrawalFeeBps()) / 10000;
        assertEq(
            usdc.balanceOf(recipient), denom - fee, "Recipient should have received the withdrawn funds minus fee"
        );
    }

    function testAnotherAddressSendProof() public {
        (bytes32 _commitment, bytes32 _nullifier, bytes32 _secret) = _getCommitment();
        bytes memory signature = _getSignature(depositor);
        uint256 yieldIndex = privacyVault.getCurrentBucketedYieldIndex();
        bytes32 finalCommitment = privacyVault.hashLeftRight(_commitment, bytes32(yieldIndex));
        vm.expectEmit(true, false, false, true);
        emit IPrivacyVault.DepositWithAuthorization(finalCommitment, 0, block.timestamp, yieldIndex);
        vm.prank(depositor);
        privacyVault.depositWithAuthorization(_commitment, signature);

        // create a proof
        bytes32[] memory leaves = new bytes32[](1);
        leaves[0] = finalCommitment;
        (bytes memory _proof, bytes32[] memory _publicInputs) =
            _getProof(_nullifier, _secret, recipient, bytes32(yieldIndex), leaves, false);

        // make a withdrawal with wrong recipient
        address attacker = makeAddr("attacker");
        vm.prank(attacker);
        vm.expectRevert();
        privacyVault.withdraw(
            _proof, _publicInputs[0], _publicInputs[1], _publicInputs[2], attacker, uint256(_publicInputs[4])
        );
    }

    function test_setWithdrawalFee_onlyOwner() public {
        privacyVault.setWithdrawalFee(50);
        assertEq(privacyVault.s_withdrawalFeeBps(), 50);

        vm.prank(depositor);
        vm.expectRevert();
        privacyVault.setWithdrawalFee(50);
    }

    function test_setWithdrawalFee_exceedsMax() public {
        vm.expectRevert(
            abi.encodeWithSelector(IPrivacyVault.PrivacyVault__FeeTooHigh.selector, 501, 500)
        );
        privacyVault.setWithdrawalFee(501);
    }

    function test_setFeeRecipient_onlyOwner() public {
        address newRecipient = makeAddr("feeRecipient");
        privacyVault.setFeeRecipient(newRecipient);
        assertEq(privacyVault.s_feeRecipient(), newRecipient);

        // Non-owner reverts
        vm.prank(depositor);
        vm.expectRevert();
        privacyVault.setFeeRecipient(newRecipient);
    }

    function test_setFeeRecipient_rejectsZero() public {
        vm.expectRevert(
            abi.encodeWithSelector(IPrivacyVault.PrivacyVault__InvalidFeeRecipient.selector)
        );
        privacyVault.setFeeRecipient(address(0));
    }

    function test_withdrawWithFee() public {
        // Set 0.5% withdrawal fee
        address feeRecipient = makeAddr("feeRecipient");
        privacyVault.setFeeRecipient(feeRecipient);
        privacyVault.setWithdrawalFee(50);

        // Deposit
        (bytes32 _commitment, bytes32 _nullifier, bytes32 _secret) = _getCommitment();
        bytes memory signature = _getSignature(depositor);
        uint256 yieldIndex = privacyVault.getCurrentBucketedYieldIndex();
        bytes32 finalCommitment = privacyVault.hashLeftRight(_commitment, bytes32(yieldIndex));
        vm.prank(depositor);
        privacyVault.depositWithAuthorization(_commitment, signature);

        // Withdraw
        bytes32[] memory leaves = new bytes32[](1);
        leaves[0] = finalCommitment;
        (bytes memory _proof, bytes32[] memory _publicInputs) =
            _getProof(_nullifier, _secret, recipient, bytes32(yieldIndex), leaves, false);

        assertEq(usdc.balanceOf(recipient), 0);
        assertEq(usdc.balanceOf(feeRecipient), 0);

        privacyVault.withdraw(
            _proof,
            _publicInputs[0],
            _publicInputs[1],
            _publicInputs[2],
            address(uint160(uint256(_publicInputs[3]))),
            uint256(_publicInputs[4])
        );

        uint256 expectedPayout = privacyVault.DENOMINATION();
        uint256 expectedFee = (expectedPayout * 50) / 10000;
        assertEq(usdc.balanceOf(feeRecipient), expectedFee, "Fee recipient should receive fee");
        assertEq(usdc.balanceOf(recipient), expectedPayout - expectedFee, "Recipient should receive payout minus fee");
    }

    function test_withdrawWithYieldBuckets() public {
        // make a deposit
        (bytes32 _commitment, bytes32 _nullifier, bytes32 _secret) = _getCommitment();
        bytes memory signature = _getSignature(depositor);
        uint256 yieldIndex = privacyVault.getCurrentBucketedYieldIndex();
        bytes32 finalCommitment = privacyVault.hashLeftRight(_commitment, bytes32(yieldIndex));

        vm.expectEmit(true, false, false, true);
        emit IPrivacyVault.DepositWithAuthorization(finalCommitment, 0, block.timestamp, yieldIndex);
        vm.prank(depositor);
        privacyVault.depositWithAuthorization(_commitment, signature);

        // Simulate 10% yield on both protocols
        aavePool.setNormalizedIncome(address(usdc), 1e27 + 1e26);
        // Morpho: increase backing assets by 10% to simulate yield
        uint256 morphoAssets = morphoVault.totalAssetsBacking();
        morphoVault.setTotalAssets(morphoAssets + morphoAssets / 5); // 20% yield

        bytes32[] memory leaves = new bytes32[](1);
        leaves[0] = finalCommitment;
        // create a proof
        (bytes memory _proof, bytes32[] memory _publicInputs) =
            _getProof(_nullifier, _secret, recipient, bytes32(yieldIndex), leaves, false);

        // make a withdrawal
        assertEq(usdc.balanceOf(recipient), 0, "Recipient should have 0 balance before withdrawal");
        privacyVault.withdraw(
            _proof,
            _publicInputs[0],
            _publicInputs[1],
            _publicInputs[2],
            address(uint160(uint256(_publicInputs[3]))),
            uint256(_publicInputs[4])
        );

        // With 10% yield on Aave and 20% on Morpho, blended yield is 15%
        uint256 expectedAmount = (privacyVault.DENOMINATION() * 115) / 100; // 1.15x
        assertApproxEqRel(
            usdc.balanceOf(recipient), expectedAmount, 0.01e18, "Recipient should have received funds with yield"
        );
    }
}
