// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

interface IPrivacyVault {
    // ---- Structs ----
    struct Loan {
        uint256 principalAmount;
        uint256 borrowYieldIndex;
        uint256 depositYieldIndex;
        bool active;
    }

    // ---- Events ----
    event DepositWithAuthorization(bytes32 indexed commitment, uint32 leafIndex, uint256 timestamp, uint256 yieldIndex);
    event Withdrawal(address to, bytes32 nullifierHash, uint256 payout);
    event PoolUpdated(address newAavePool, address newMorphoVault);
    event Borrow(bytes32 indexed collateralNullifierHash, address borrower, uint256 amount, uint256 yieldIndex);
    event Repay(bytes32 indexed collateralNullifierHash, address repayer, uint256 amount);
    event FeeUpdated(uint256 newFeeBps);
    event FeeRecipientUpdated(address newFeeRecipient);

    // ---- Errors ----
    error PrivacyVault__DepositValueMismatch(uint256 expected, uint256 actual);
    error PrivacyVault__InvalidRecipient(address expected, address actual);
    error PrivacyVault__PaymentFailed(address recipient, uint256 amount);
    error PrivacyVault__NoteAlreadySpent(bytes32 nullifierHash);
    error PrivacyVault__UnknownRoot(bytes32 root);
    error PrivacyVault__InvalidWithdrawProof();
    error PrivacyVault__CommitmentAlreadyAdded(bytes32 commitment);
    error PrivacyVault__InvalidYieldIndex();
    error PrivacyVault__InvalidPoolAddress(string protocol, address provided);
    error PrivacyVault__LoanAlreadyActive(bytes32 collateralNullifierHash);
    error PrivacyVault__NoActiveLoan(bytes32 collateralNullifierHash);
    error PrivacyVault__CollateralLocked(bytes32 collateralNullifierHash);
    error PrivacyVault__InvalidBorrowProof();
    error PrivacyVault__BorrowAmountExceedsLTV(uint256 maxBorrow, uint256 requested);
    error PrivacyVault__DepositAlreadyWithdrawn(bytes32 collateralNullifierHash);
    error PrivacyVault__FeeTooHigh(uint256 feeBps, uint256 maxFeeBps);
    error PrivacyVault__InvalidFeeRecipient();

    // ---- View / Pure ----
    function token() external view returns (IERC20);
    function DENOMINATION() external view returns (uint256);
    function initialMorphoSharePrice() external view returns (uint256);
    function totalBorrowed() external view returns (uint256);

    function s_nullifierHashes(bytes32) external view returns (bool);
    function s_commitments(bytes32) external view returns (bool);
    function s_loans(bytes32)
        external
        view
        returns (uint256 principalAmount, uint256 borrowYieldIndex, uint256 depositYieldIndex, bool active);
    function s_collateralSpent(bytes32) external view returns (bool);

    function getMorphoNormalizedIncome() external view returns (uint256);
    function getCurrentBucketedYieldIndex() external view returns (uint256);
    function getDebt(bytes32 _collateralNullifierHash) external view returns (uint256);
    function s_withdrawalFeeBps() external view returns (uint256);
    function s_feeRecipient() external view returns (address);
    function getRepaymentAmount(bytes32 _collateralNullifierHash) external view returns (uint256);

    // ---- State-changing ----
    function setPools(address _aavePool, address _morphoVault) external;
    function setWithdrawalFee(uint256 _feeBps) external;
    function setFeeRecipient(address _feeRecipient) external;

    function depositWithAuthorization(bytes32 _innerCommitment, bytes calldata _receiveAuthorization) external;

    function withdraw(
        bytes calldata _proof,
        bytes32 _root,
        bytes32 _nullifierHash,
        bytes32 _collateralNullifierHash,
        address _recipient,
        uint256 _yieldIndex
    ) external;

    function borrow(
        bytes calldata _proof,
        bytes32 _root,
        bytes32 _collateralNullifierHash,
        address _recipient,
        uint256 _yieldIndex,
        uint256 _borrowAmount
    ) external;

    function repayWithAuthorization(bytes32 _collateralNullifierHash, bytes calldata _receiveAuthorization) external;
}
