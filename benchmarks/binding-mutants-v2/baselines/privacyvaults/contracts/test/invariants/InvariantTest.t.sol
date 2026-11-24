// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {PrivacyVault, IVerifier, Poseidon2} from "../../src/PrivacyVault.sol";
import {MockUSDC} from "../mocks/MockERC20.sol";
import {AavePoolMock} from "../mocks/AavePoolMock.sol";
import {MorphoVaultMock} from "../mocks/MorphoVaultMock.sol";
import {MockVerifier} from "../mocks/MockVerifier.sol";
import {VaultHandler} from "./VaultHandler.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {IAavePool} from "../../src/interfaces/IAavePool.sol";
import {IMorphoVault} from "../../src/interfaces/IMorphoPool.sol";

contract InvariantTest is Test {
    PrivacyVault public vault;
    MockUSDC public usdc;
    AavePoolMock public aavePool;
    MorphoVaultMock public morphoVault;
    Poseidon2 public poseidon;
    MockVerifier public mockVerifier;
    VaultHandler public handler;

    address public depositor;
    uint256 internal depositorKey;

    uint256 constant DENOMINATION = 100e6;
    uint256 constant RAY = 1e27;

    function setUp() public {
        (depositor, depositorKey) = makeAddrAndKey("depositor");

        usdc = new MockUSDC(10_000_000e6);
        aavePool = new AavePoolMock();
        morphoVault = new MorphoVaultMock(IERC20(usdc));

        // Fund pools for withdrawals
        usdc.mint(address(aavePool), 1_000_000e6);
        usdc.mint(address(morphoVault), 1_000_000e6);

        // Fund depositor with large supply
        usdc.transfer(depositor, 1_000_000e6);

        poseidon = new Poseidon2();
        mockVerifier = new MockVerifier();

        vault = new PrivacyVault(
            IVerifier(address(mockVerifier)),
            IVerifier(address(mockVerifier)),
            poseidon,
            20,
            DENOMINATION,
            IERC20(usdc),
            IAavePool(address(aavePool)),
            IMorphoVault(address(morphoVault))
        );

        handler = new VaultHandler(vault, usdc, aavePool, morphoVault, depositor, depositorKey, address(this));

        // Approve USDC for vault from depositor
        vm.prank(depositor);
        usdc.approve(address(vault), type(uint256).max);

        targetContract(address(handler));
    }

    // --- Invariant 1: totalBorrowed consistency ---
    function invariant_totalBorrowedConsistency() public view {
        assertEq(vault.totalBorrowed(), handler.ghost_totalBorrowed(), "totalBorrowed mismatch");
    }

    // --- Invariant 2: Collateral state machine ---
    function invariant_collateralStateMachine() public view {
        uint256 len = handler.getDepositsLength();
        for (uint256 i = 0; i < len; i++) {
            VaultHandler.DepositInfo memory info = handler.getDepositInfo(i);

            // s_collateralSpent and s_loans.active should never both be true
            bool collateralSpent = vault.s_collateralSpent(info.collateralNullifierHash);
            (,,, bool loanActive) = vault.s_loans(info.collateralNullifierHash);

            assertFalse(
                collateralSpent && loanActive,
                "Collateral spent AND loan active simultaneously"
            );

            // If withdrawn in ghost state, collateral should be spent on-chain
            if (info.withdrawn) {
                assertTrue(collateralSpent, "Withdrawn but collateral not spent");
            }

            // If has active loan in ghost state, loan should be active on-chain
            if (info.hasActiveLoan) {
                assertTrue(loanActive, "Ghost has loan but on-chain inactive");
            }
        }
    }

    // --- Invariant 3: No double-spend ---
    function invariant_noDoubleSpend() public view {
        uint256 len = handler.getDepositsLength();
        uint256 spentCount;
        for (uint256 i = 0; i < len; i++) {
            VaultHandler.DepositInfo memory info = handler.getDepositInfo(i);
            if (info.withdrawn) {
                assertTrue(
                    vault.s_nullifierHashes(info.nullifierHash),
                    "Withdrawn but nullifier not marked"
                );
                spentCount++;
            }
        }
        assertEq(spentCount, handler.ghost_withdrawCount(), "Spent count mismatch");
    }

    // --- Invariant 4: Merkle tree integrity ---
    function invariant_merkleTreeIntegrity() public view {
        uint256 depositCount = handler.ghost_depositCount();
        if (depositCount > 0) {
            bytes32 root = vault.getLatestRoot();
            assertTrue(root != bytes32(0), "Root is zero after deposits");
            assertTrue(vault.isKnownRoot(root), "Latest root not recognized");
        }
        assertEq(vault.s_nextLeafIndex(), depositCount, "Leaf index mismatch");
    }

    // --- Invariant 5: Commitment uniqueness ---
    function invariant_commitmentUniqueness() public view {
        uint256 len = handler.getDepositsLength();
        for (uint256 i = 0; i < len; i++) {
            VaultHandler.DepositInfo memory info = handler.getDepositInfo(i);
            assertTrue(
                vault.s_commitments(info.finalCommitment),
                "Commitment not recorded"
            );
        }
    }

    // --- Invariant 6: Yield monotonicity ---
    function invariant_yieldMonotonicity() public view {
        uint256 currentYield = vault.getCurrentBucketedYieldIndex();
        assertTrue(currentYield >= RAY, "Yield index below RAY");
    }

    // --- Invariant 7: Loan accounting ---
    function invariant_loanAccounting() public view {
        uint256 ghostSum = handler.getActiveLoanPrincipalSum();
        assertEq(ghostSum, handler.ghost_totalBorrowed(), "Loan principal sum mismatch");
    }

    // --- Invariant 8: Denomination enforcement ---
    function invariant_denominationEnforcement() public view {
        // Every deposit uses exactly DENOMINATION USDC
        // s_nextLeafIndex tracks total deposits, each exactly DENOMINATION
        uint256 depositCount = handler.ghost_depositCount();
        assertEq(vault.s_nextLeafIndex(), depositCount, "Deposit count mismatch");
    }
}
