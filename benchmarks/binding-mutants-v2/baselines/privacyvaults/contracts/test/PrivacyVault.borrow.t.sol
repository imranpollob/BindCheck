// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {TestBase} from "./TestBase.t.sol";
import {IPrivacyVault} from "../src/interfaces/IPrivacyVault.sol";

contract PrivacyVaultBorrowTest is TestBase {
    function setUp() public override {
        super.setUp();
    }

    // ---- Tests ----

    function test_borrow_success() public {
        (bytes32 commitment, bytes32 nullifier, bytes32 secret) = _getCommitment();
        (bytes32 finalCommitment, bytes32 collateralHash) =
            _deposit(nullifier, secret, depositor, address(privacyVault));
        uint256 yieldIndex = privacyVault.getCurrentBucketedYieldIndex();
        uint256 maxBorrow = _computeMaxBorrow();
        uint256 borrowAmount = maxBorrow / 2;

        bytes32[] memory leaves = new bytes32[](1);
        leaves[0] = finalCommitment;
        (bytes memory proof, bytes32[] memory publicInputs) =
            _getProof(nullifier, secret, recipient, bytes32(yieldIndex), leaves, true);

        uint256 recipientBefore = usdc.balanceOf(recipient);

        privacyVault.borrow(
            proof,
            publicInputs[0], // root
            publicInputs[1], // collateralNullifierHash
            address(uint160(uint256(publicInputs[2]))), // recipient
            uint256(publicInputs[3]), // yieldIndex
            borrowAmount
        );

        assertEq(usdc.balanceOf(recipient) - recipientBefore, borrowAmount, "Recipient should receive borrowed USDC");

        (uint256 principal,,, bool active) = privacyVault.s_loans(collateralHash);
        assertTrue(active, "Loan should be active");
        assertEq(principal, borrowAmount, "Principal should match borrow amount");
        assertEq(privacyVault.totalBorrowed(), borrowAmount, "totalBorrowed should be updated");
    }

    function test_borrow_exceeds_ltv() public {
        (bytes32 commitment, bytes32 nullifier, bytes32 secret) = _getCommitment();
        (bytes32 finalCommitment,) = _deposit(nullifier, secret, depositor, address(privacyVault));
        uint256 yieldIndex = privacyVault.getCurrentBucketedYieldIndex();
        uint256 maxBorrow = _computeMaxBorrow();

        bytes32[] memory leaves = new bytes32[](1);
        leaves[0] = finalCommitment;
        (bytes memory proof, bytes32[] memory publicInputs) =
            _getProof(nullifier, secret, recipient, bytes32(yieldIndex), leaves, true);

        vm.expectRevert();
        privacyVault.borrow(
            proof,
            publicInputs[0],
            publicInputs[1],
            address(uint160(uint256(publicInputs[2]))),
            uint256(publicInputs[3]),
            maxBorrow + 1
        );
    }

    function test_borrow_after_withdrawal() public {
        (bytes32 commitment, bytes32 nullifier, bytes32 secret) = _getCommitment();
        (bytes32 finalCommitment, bytes32 collateralHash) =
            _deposit(nullifier, secret, depositor, address(privacyVault));
        uint256 yieldIndex = privacyVault.getCurrentBucketedYieldIndex();

        bytes32[] memory leaves = new bytes32[](1);
        leaves[0] = finalCommitment;

        // Withdraw first with real proof
        (bytes memory withdrawProof, bytes32[] memory withdrawInputs) =
            _getProof(nullifier, secret, recipient, bytes32(yieldIndex), leaves, false);
        privacyVault.withdraw(
            withdrawProof,
            withdrawInputs[0],
            withdrawInputs[1], // nullifierHash
            withdrawInputs[2], // collateralNullifierHash
            address(uint160(uint256(withdrawInputs[3]))),
            uint256(withdrawInputs[4])
        );

        // Generate borrow proof
        (bytes memory borrowProof, bytes32[] memory borrowInputs) =
            _getProof(nullifier, secret, borrower, bytes32(yieldIndex), leaves, true);

        // Now try to borrow — should revert because collateral is spent
        vm.expectRevert(
            abi.encodeWithSelector(IPrivacyVault.PrivacyVault__DepositAlreadyWithdrawn.selector, collateralHash)
        );
        privacyVault.borrow(
            borrowProof,
            borrowInputs[0],
            borrowInputs[1],
            address(uint160(uint256(borrowInputs[2]))),
            uint256(borrowInputs[3]),
            10e6
        );
    }

    function test_borrow_double_collateral() public {
        (bytes32 commitment, bytes32 nullifier, bytes32 secret) = _getCommitment();
        (bytes32 finalCommitment, bytes32 collateralHash) =
            _deposit(nullifier, secret, depositor, address(privacyVault));
        uint256 yieldIndex = privacyVault.getCurrentBucketedYieldIndex();
        uint256 borrowAmount = 10e6;

        bytes32[] memory leaves = new bytes32[](1);
        leaves[0] = finalCommitment;
        (bytes memory proof, bytes32[] memory publicInputs) =
            _getProof(nullifier, secret, recipient, bytes32(yieldIndex), leaves, true);

        // First borrow succeeds
        privacyVault.borrow(
            proof,
            publicInputs[0],
            publicInputs[1],
            address(uint160(uint256(publicInputs[2]))),
            uint256(publicInputs[3]),
            borrowAmount
        );

        // Second borrow with same collateral should revert (proof is valid but loan already active)
        vm.expectRevert(abi.encodeWithSelector(IPrivacyVault.PrivacyVault__LoanAlreadyActive.selector, collateralHash));
        privacyVault.borrow(
            proof,
            publicInputs[0],
            publicInputs[1],
            address(uint160(uint256(publicInputs[2]))),
            uint256(publicInputs[3]),
            borrowAmount
        );
    }

    function test_repay_success() public {
        (bytes32 commitment, bytes32 nullifier, bytes32 secret) = _getCommitment();
        (bytes32 finalCommitment, bytes32 collateralHash) =
            _deposit(nullifier, secret, depositor, address(privacyVault));
        uint256 yieldIndex = privacyVault.getCurrentBucketedYieldIndex();
        uint256 borrowAmount = 50e6;

        bytes32[] memory leaves = new bytes32[](1);
        leaves[0] = finalCommitment;
        (bytes memory proof, bytes32[] memory publicInputs) =
            _getProof(nullifier, secret, recipient, bytes32(yieldIndex), leaves, true);

        // Borrow
        privacyVault.borrow(
            proof,
            publicInputs[0],
            publicInputs[1],
            address(uint160(uint256(publicInputs[2]))),
            uint256(publicInputs[3]),
            borrowAmount
        );

        // Get current debt
        uint256 debt = privacyVault.getDebt(collateralHash);
        assertGe(debt, borrowAmount, "Debt should be >= principal");

        // Depositor repays
        bytes memory repaySig = _getRepaySignature(depositor, debt);
        privacyVault.repayWithAuthorization(collateralHash, repaySig);

        // Verify loan is cleared
        (,,, bool active) = privacyVault.s_loans(collateralHash);
        assertFalse(active, "Loan should no longer be active");
        assertEq(privacyVault.totalBorrowed(), 0, "totalBorrowed should be 0");
        assertEq(privacyVault.getDebt(collateralHash), 0, "Debt should be 0 after repayment");
    }

    function test_repay_no_active_loan() public {
        bytes32 fakeHash = bytes32(uint256(999));

        vm.expectRevert(abi.encodeWithSelector(IPrivacyVault.PrivacyVault__NoActiveLoan.selector, fakeHash));
        privacyVault.repayWithAuthorization(fakeHash, hex"00");
    }

    function test_withdraw_blocked_by_loan() public {
        (bytes32 commitment, bytes32 nullifier, bytes32 secret) = _getCommitment();
        (bytes32 finalCommitment, bytes32 collateralHash) =
            _deposit(nullifier, secret, depositor, address(privacyVault));
        uint256 yieldIndex = privacyVault.getCurrentBucketedYieldIndex();

        bytes32[] memory leaves = new bytes32[](1);
        leaves[0] = finalCommitment;

        // Borrow first
        (bytes memory borrowProof, bytes32[] memory borrowInputs) =
            _getProof(nullifier, secret, recipient, bytes32(yieldIndex), leaves, true);
        privacyVault.borrow(
            borrowProof,
            borrowInputs[0],
            borrowInputs[1],
            address(uint160(uint256(borrowInputs[2]))),
            uint256(borrowInputs[3]),
            10e6
        );

        // Try to withdraw — should revert because loan is active
        (bytes memory withdrawProof, bytes32[] memory withdrawInputs) =
            _getProof(nullifier, secret, borrower, bytes32(yieldIndex), leaves, false);
        vm.expectRevert(abi.encodeWithSelector(IPrivacyVault.PrivacyVault__CollateralLocked.selector, collateralHash));
        privacyVault.withdraw(
            withdrawProof,
            withdrawInputs[0],
            withdrawInputs[1],
            withdrawInputs[2],
            address(uint160(uint256(withdrawInputs[3]))),
            uint256(withdrawInputs[4])
        );
    }

    function test_withdraw_after_repay() public {
        (bytes32 commitment, bytes32 nullifier, bytes32 secret) = _getCommitment();
        (bytes32 finalCommitment, bytes32 collateralHash) =
            _deposit(nullifier, secret, depositor, address(privacyVault));
        uint256 yieldIndex = privacyVault.getCurrentBucketedYieldIndex();

        bytes32[] memory leaves = new bytes32[](1);
        leaves[0] = finalCommitment;

        // Borrow
        (bytes memory borrowProof, bytes32[] memory borrowInputs) =
            _getProof(nullifier, secret, recipient, bytes32(yieldIndex), leaves, true);
        privacyVault.borrow(
            borrowProof,
            borrowInputs[0],
            borrowInputs[1],
            address(uint160(uint256(borrowInputs[2]))),
            uint256(borrowInputs[3]),
            10e6
        );

        // Repay
        uint256 debt = privacyVault.getDebt(collateralHash);
        bytes memory repaySig = _getRepaySignature(depositor, debt);
        privacyVault.repayWithAuthorization(collateralHash, repaySig);

        // Withdraw should now succeed
        (bytes memory withdrawProof, bytes32[] memory withdrawInputs) =
            _getProof(nullifier, secret, borrower, bytes32(yieldIndex), leaves, false);
        uint256 recipientBefore = usdc.balanceOf(borrower);
        privacyVault.withdraw(
            withdrawProof,
            withdrawInputs[0],
            withdrawInputs[1],
            withdrawInputs[2],
            address(uint160(uint256(withdrawInputs[3]))),
            uint256(withdrawInputs[4])
        );
        assertTrue(usdc.balanceOf(borrower) > recipientBefore, "Borrower should receive withdrawn funds");
    }

    function test_getDebt_tracks_yield() public {
        (bytes32 commitment, bytes32 nullifier, bytes32 secret) = _getCommitment();
        (bytes32 finalCommitment, bytes32 collateralHash) =
            _deposit(nullifier, secret, depositor, address(privacyVault));
        uint256 yieldIndex = privacyVault.getCurrentBucketedYieldIndex();
        uint256 borrowAmount = 50e6;

        bytes32[] memory leaves = new bytes32[](1);
        leaves[0] = finalCommitment;
        (bytes memory proof, bytes32[] memory publicInputs) =
            _getProof(nullifier, secret, recipient, bytes32(yieldIndex), leaves, true);

        privacyVault.borrow(
            proof,
            publicInputs[0],
            publicInputs[1],
            address(uint160(uint256(publicInputs[2]))),
            uint256(publicInputs[3]),
            borrowAmount
        );

        // Simulate 10% yield on Aave
        aavePool.setNormalizedIncome(address(usdc), 1e27 + 1e26);

        uint256 debt = privacyVault.getDebt(collateralHash);
        assertGt(debt, borrowAmount, "Debt should increase with yield");

        // With 10% Aave yield and 0% Morpho, blended = 5% yield
        uint256 expectedDebt = (borrowAmount * 105) / 100;
        assertApproxEqRel(debt, expectedDebt, 0.02e18, "Debt should track blended yield");
    }

    function test_borrowNoFee() public {
        (bytes32 commitment, bytes32 nullifier, bytes32 secret) = _getCommitment();
        (bytes32 finalCommitment, bytes32 collateralHash) =
            _deposit(nullifier, secret, depositor, address(privacyVault));
        uint256 yieldIndex = privacyVault.getCurrentBucketedYieldIndex();
        uint256 borrowAmount = 50e6;

        bytes32[] memory leaves = new bytes32[](1);
        leaves[0] = finalCommitment;
        (bytes memory proof, bytes32[] memory publicInputs) =
            _getProof(nullifier, secret, recipient, bytes32(yieldIndex), leaves, true);

        uint256 recipientBefore = usdc.balanceOf(recipient);

        privacyVault.borrow(
            proof,
            publicInputs[0],
            publicInputs[1],
            address(uint160(uint256(publicInputs[2]))),
            uint256(publicInputs[3]),
            borrowAmount
        );

        assertEq(usdc.balanceOf(recipient) - recipientBefore, borrowAmount, "Recipient gets full borrow amount");
    }

    function test_repayNoFee() public {
        (, bytes32 nullifier, bytes32 secret) = _getCommitment();
        (bytes32 finalCommitment, bytes32 collateralHash) =
            _deposit(nullifier, secret, depositor, address(privacyVault));

        {
            uint256 yieldIndex = privacyVault.getCurrentBucketedYieldIndex();
            bytes32[] memory leaves = new bytes32[](1);
            leaves[0] = finalCommitment;
            (bytes memory proof, bytes32[] memory publicInputs) =
                _getProof(nullifier, secret, recipient, bytes32(yieldIndex), leaves, true);

            privacyVault.borrow(
                proof,
                publicInputs[0],
                publicInputs[1],
                address(uint160(uint256(publicInputs[2]))),
                uint256(publicInputs[3]),
                50e6
            );
        }

        uint256 debt = privacyVault.getDebt(collateralHash);
        uint256 repaymentAmount = privacyVault.getRepaymentAmount(collateralHash);
        assertEq(repaymentAmount, debt, "Repayment amount should equal debt (no fee)");

        bytes memory repaySig = _getRepaySignature(depositor, repaymentAmount);
        privacyVault.repayWithAuthorization(collateralHash, repaySig);

        (,,, bool active) = privacyVault.s_loans(collateralHash);
        assertFalse(active, "Loan should be cleared");
    }

    function test_multiple_borrows_different_deposits() public {
        // Deposit 1
        (bytes32 commitment1, bytes32 nullifier1, bytes32 secret1) = _getCommitment();
        (bytes32 finalCommitment1, bytes32 collateralHash1) =
            _deposit(nullifier1, secret1, depositor, address(privacyVault));

        // Deposit 2
        (bytes32 commitment2, bytes32 nullifier2, bytes32 secret2) = _getCommitment();
        (bytes32 finalCommitment2, bytes32 collateralHash2) =
            _deposit(nullifier2, secret2, depositor, address(privacyVault));
        uint256 yieldIndex = privacyVault.getCurrentBucketedYieldIndex();

        bytes32[] memory leaves = new bytes32[](2);
        leaves[0] = finalCommitment1;
        leaves[1] = finalCommitment2;

        // Borrow against deposit 1
        (bytes memory proof1, bytes32[] memory inputs1) =
            _getProof(nullifier1, secret1, recipient, bytes32(yieldIndex), leaves, true);
        privacyVault.borrow(
            proof1, inputs1[0], inputs1[1], address(uint160(uint256(inputs1[2]))), uint256(inputs1[3]), 30e6
        );

        // Borrow against deposit 2
        (bytes memory proof2, bytes32[] memory inputs2) =
            _getProof(nullifier2, secret2, borrower, bytes32(yieldIndex), leaves, true);
        privacyVault.borrow(
            proof2, inputs2[0], inputs2[1], address(uint160(uint256(inputs2[2]))), uint256(inputs2[3]), 50e6
        );

        // Both loans should be active
        (uint256 p1,,, bool a1) = privacyVault.s_loans(collateralHash1);
        (uint256 p2,,, bool a2) = privacyVault.s_loans(collateralHash2);
        assertTrue(a1 && a2, "Both loans should be active");
        assertEq(p1, 30e6, "Loan 1 principal");
        assertEq(p2, 50e6, "Loan 2 principal");
        assertEq(privacyVault.totalBorrowed(), 80e6, "Total borrowed should be sum");
    }
}
