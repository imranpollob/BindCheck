// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {PrivacyVault, Poseidon2} from "../../src/PrivacyVault.sol";
import {IPrivacyVault} from "../../src/interfaces/IPrivacyVault.sol";
import {MockUSDC} from "../mocks/MockERC20.sol";
import {AavePoolMock} from "../mocks/AavePoolMock.sol";
import {MorphoVaultMock} from "../mocks/MorphoVaultMock.sol";

contract VaultHandler is Test {
    struct DepositInfo {
        bytes32 finalCommitment;
        bytes32 nullifierHash;
        bytes32 collateralNullifierHash;
        uint256 yieldIndex;
        bool withdrawn;
        bool hasActiveLoan;
        uint256 loanPrincipal;
    }

    PrivacyVault public vault;
    MockUSDC public usdc;
    AavePoolMock public aavePool;
    MorphoVaultMock public morphoVault;

    address public depositor;
    uint256 internal depositorKey;
    address public mockOwner; // owner of AavePoolMock & MorphoVaultMock (onlyOwner)

    uint256 public ghost_totalBorrowed;
    uint256 public ghost_depositCount;
    uint256 public ghost_withdrawCount;
    uint256 public ghost_previousYieldIndex;

    DepositInfo[] public deposits;

    uint256 private _commitmentCounter;
    uint256 private _nonceCounter;

    uint256 private constant RAY = 1e27;
    uint256 private constant LTV_BPS = 7000;
    uint256 private constant BPS = 10000;

    bytes32 public constant RECEIVE_WITH_AUTHORIZATION_TYPEHASH = keccak256(
        "ReceiveWithAuthorization(address from,address to,uint256 value,uint256 validAfter,uint256 validBefore,bytes32 nonce)"
    );

    constructor(
        PrivacyVault _vault,
        MockUSDC _usdc,
        AavePoolMock _aavePool,
        MorphoVaultMock _morphoVault,
        address _depositor,
        uint256 _depositorKey,
        address _mockOwner
    ) {
        vault = _vault;
        usdc = _usdc;
        aavePool = _aavePool;
        morphoVault = _morphoVault;
        depositor = _depositor;
        depositorKey = _depositorKey;
        mockOwner = _mockOwner;
        ghost_previousYieldIndex = RAY;
    }

    function deposit(uint256) external {
        bytes32 innerCommitment = keccak256(abi.encodePacked("deposit", _commitmentCounter));
        _commitmentCounter++;

        // Ensure innerCommitment is within the field size
        innerCommitment = bytes32(uint256(innerCommitment) % vault.FIELD_SIZE());

        uint256 yieldIndex = vault.getCurrentBucketedYieldIndex();
        bytes32 finalCommitment = vault.hashLeftRight(innerCommitment, bytes32(yieldIndex));

        // Skip if commitment already exists (extremely unlikely but possible)
        if (vault.s_commitments(finalCommitment)) return;

        bytes memory sig = _buildReceiveAuth(address(vault), vault.DENOMINATION());

        vm.prank(depositor);
        vault.depositWithAuthorization(innerCommitment, sig);

        // Derive unique nullifier and collateral hashes using keccak256
        bytes32 nullifierHash = keccak256(abi.encodePacked("nullifier", _commitmentCounter));
        nullifierHash = bytes32(uint256(nullifierHash) % vault.FIELD_SIZE());
        bytes32 collateralNullifierHash = keccak256(abi.encodePacked("collateral", _commitmentCounter));
        collateralNullifierHash = bytes32(uint256(collateralNullifierHash) % vault.FIELD_SIZE());

        deposits.push(
            DepositInfo({
                finalCommitment: finalCommitment,
                nullifierHash: nullifierHash,
                collateralNullifierHash: collateralNullifierHash,
                yieldIndex: yieldIndex,
                withdrawn: false,
                hasActiveLoan: false,
                loanPrincipal: 0
            })
        );

        ghost_depositCount++;
    }

    function withdraw(uint256 depositSeed) external {
        if (deposits.length == 0) return;

        uint256 idx = bound(depositSeed, 0, deposits.length - 1);
        DepositInfo storage info = deposits[idx];

        if (info.withdrawn || info.hasActiveLoan) return;

        bytes32 root = vault.getLatestRoot();
        address recipient = depositor;

        bytes memory dummyProof = new bytes(0);
        bytes32[] memory publicInputs = new bytes32[](5);
        publicInputs[0] = root;
        publicInputs[1] = info.nullifierHash;
        publicInputs[2] = info.collateralNullifierHash;
        publicInputs[3] = bytes32(uint256(uint160(address(recipient))));
        publicInputs[4] = bytes32(info.yieldIndex);

        vault.withdraw(dummyProof, root, info.nullifierHash, info.collateralNullifierHash, recipient, info.yieldIndex);

        info.withdrawn = true;
        ghost_withdrawCount++;
    }

    function borrow(uint256 depositSeed, uint256 amount) external {
        if (deposits.length == 0) return;

        uint256 idx = bound(depositSeed, 0, deposits.length - 1);
        DepositInfo storage info = deposits[idx];

        if (info.withdrawn || info.hasActiveLoan) return;

        // Calculate max borrow
        uint256 currentBlended = _getCurrentBlended();
        uint256 collateralValue = (vault.DENOMINATION() * currentBlended) / info.yieldIndex;
        uint256 maxBorrow = (collateralValue * LTV_BPS) / BPS;

        if (maxBorrow == 0) return;
        amount = bound(amount, 1, maxBorrow);

        bytes32 root = vault.getLatestRoot();
        address recipient = depositor;

        bytes memory dummyProof = new bytes(0);

        vault.borrow(dummyProof, root, info.collateralNullifierHash, recipient, info.yieldIndex, amount);

        info.hasActiveLoan = true;
        info.loanPrincipal = amount;
        ghost_totalBorrowed += amount;
    }

    function repay(uint256 depositSeed) external {
        if (deposits.length == 0) return;

        // Find a deposit with an active loan
        uint256 idx = bound(depositSeed, 0, deposits.length - 1);
        DepositInfo storage info = deposits[idx];

        if (!info.hasActiveLoan) return;

        uint256 debt = vault.getDebt(info.collateralNullifierHash);
        if (debt == 0) return;

        uint256 repaymentAmount = debt;

        // Ensure depositor has enough USDC for repayment
        if (usdc.balanceOf(depositor) < repaymentAmount) {
            usdc.mint(depositor, repaymentAmount);
        }

        bytes memory sig = _buildReceiveAuth(address(vault), repaymentAmount);

        vault.repayWithAuthorization(info.collateralNullifierHash, sig);

        ghost_totalBorrowed -= info.loanPrincipal;
        info.hasActiveLoan = false;
        info.loanPrincipal = 0;
    }

    function simulateYield(uint256 aaveIncrease, uint256 morphoIncrease) external {
        // Bound increases to 0-10% per call
        aaveIncrease = bound(aaveIncrease, 0, RAY / 10);
        morphoIncrease = bound(morphoIncrease, 0, RAY / 10);

        uint256 currentAave = aavePool.getReserveNormalizedIncome(address(usdc));
        uint256 newAave = currentAave + aaveIncrease;

        // Set new Aave income (monotonically increasing)
        vm.prank(mockOwner);
        aavePool.setNormalizedIncome(address(usdc), newAave);

        // For Morpho, increase totalAssetsBacking
        uint256 currentMorphoAssets = morphoVault.totalAssetsBacking();
        if (currentMorphoAssets > 0) {
            // Increase by proportional amount: morphoIncrease / RAY * currentAssets
            uint256 assetIncrease = (currentMorphoAssets * morphoIncrease) / RAY;
            if (assetIncrease > 0) {
                vm.prank(mockOwner);
                morphoVault.setTotalAssets(currentMorphoAssets + assetIncrease);
            }
        }
    }

    // --- View helpers for invariant assertions ---

    function getDepositsLength() external view returns (uint256) {
        return deposits.length;
    }

    function getDepositInfo(uint256 idx) external view returns (DepositInfo memory) {
        return deposits[idx];
    }

    function getActiveLoanPrincipalSum() external view returns (uint256) {
        uint256 sum;
        for (uint256 i = 0; i < deposits.length; i++) {
            if (deposits[i].hasActiveLoan) {
                sum += deposits[i].loanPrincipal;
            }
        }
        return sum;
    }

    // --- Internal helpers ---

    function _getCurrentBlended() internal view returns (uint256) {
        uint256 aaveIndex = aavePool.getReserveNormalizedIncome(address(usdc));
        uint256 morphoIndex = vault.getMorphoNormalizedIncome();
        return (aaveIndex + morphoIndex) / 2;
    }

    function _buildReceiveAuth(address to, uint256 value) internal returns (bytes memory) {
        bytes32 nonce = keccak256(abi.encodePacked("inv-nonce", _nonceCounter));
        _nonceCounter++;

        bytes32 structHash = keccak256(
            abi.encode(
                RECEIVE_WITH_AUTHORIZATION_TYPEHASH,
                depositor,
                to,
                value,
                uint256(0),
                type(uint256).max,
                nonce
            )
        );

        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", usdc.DOMAIN_SEPARATOR(), structHash));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(depositorKey, digest);

        return abi.encode(depositor, to, value, uint256(0), type(uint256).max, nonce, v, r, s);
    }
}
