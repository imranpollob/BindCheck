// SPDX-License-Identifier: MIT

pragma solidity ^0.8.24;

import {IVerifier} from "./Verifier.sol";
import {IncrementalMerkleTree, Poseidon2} from "./IncrementalMerkleTree.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {IAavePool} from "./interfaces/IAavePool.sol";
import {IMorphoVault} from "./interfaces/IMorphoPool.sol";
import {IPrivacyVault} from "./interfaces/IPrivacyVault.sol";

contract PrivacyVault is IncrementalMerkleTree, ReentrancyGuard, Ownable, IPrivacyVault {
    using SafeERC20 for IERC20;

    // keccak256("receiveWithAuthorization(address,address,uint256,uint256,uint256,bytes32,uint8,bytes32,bytes32)")[0:4]
    bytes4 private constant _RECEIVE_WITH_AUTHORIZATION_SELECTOR = 0xef55bec6;

    /// @dev Aave uses 27-decimal Ray units for liquidity index
    uint256 private constant RAY = 1e27;

    /// @dev Bucket precision: round yield index to this granularity (daily bucket ≈ 1e23)
    uint256 private constant BUCKET_PRECISION = 1e23;

    /// @dev 1 full share in MetaMorpho (18 decimals)
    uint256 private constant ONE_SHARE = 1e18;

    /// @dev LTV: 70% (7000 basis points)
    uint256 private constant LTV_BPS = 7000;
    uint256 private constant BPS = 10000;

    IERC20 public immutable token;
    IAavePool public aavePool;
    IMorphoVault public morphoVault;

    IVerifier public immutable i_verifier;
    IVerifier public immutable i_borrowVerifier;
    uint256 public immutable DENOMINATION;

    /// @dev Morpho share price at deployment, used to normalize to RAY-scale index
    uint256 public immutable initialMorphoSharePrice;

    mapping(bytes32 => bool) public s_nullifierHashes; // nullifierHash => bool (prevents double spend of notes)
    mapping(bytes32 => bool) public s_commitments; // commitment => bool (prevents duplicate deposits)

    mapping(bytes32 => Loan) public s_loans; // collateralNullifierHash => Loan
    mapping(bytes32 => bool) public s_collateralSpent; // collateralNullifierHash => bool (prevents borrow if deposit already withdrawn)
    uint256 public totalBorrowed; // for monitoring total outstanding debt

    uint256 private constant MAX_FEE_BPS = 500; // 5% cap
    uint256 public s_withdrawalFeeBps; // fee in basis points, withdrawal only
    address public s_feeRecipient;


    constructor(
        IVerifier _verifier,
        IVerifier _borrowVerifier,
        Poseidon2 _hasher,
        uint32 _merkleTreeDepth,
        uint256 _denomination,
        IERC20 _token,
        IAavePool _aavePool,
        IMorphoVault _morphoVault
    ) IncrementalMerkleTree(_merkleTreeDepth, _hasher) Ownable(msg.sender) {
        if (address(_verifier) == address(0)) revert PrivacyVault__InvalidWithdrawProof();
        if (address(_borrowVerifier) == address(0)) revert PrivacyVault__InvalidBorrowProof();
        if (address(_hasher) == address(0)) revert PrivacyVault__InvalidWithdrawProof();
        if (_denomination == 0) revert PrivacyVault__DepositValueMismatch({expected: _denomination, actual: 0});
        if (address(_token) == address(0)) {
            revert PrivacyVault__InvalidRecipient({expected: address(0), actual: address(0)});
        }
        if (address(_aavePool) != address(0) && address(_aavePool).code.length == 0) {
            revert PrivacyVault__InvalidPoolAddress("Aave", address(_aavePool));
        }
        if (address(_morphoVault) != address(0) && address(_morphoVault).code.length == 0) {
            revert PrivacyVault__InvalidPoolAddress("Morpho", address(_morphoVault));
        }

        i_verifier = _verifier;
        i_borrowVerifier = _borrowVerifier;
        DENOMINATION = _denomination;
        token = _token;
        aavePool = _aavePool;
        morphoVault = _morphoVault;

        // Record Morpho share price at deployment to compute normalized growth
        initialMorphoSharePrice = _morphoVault.convertToAssets(ONE_SHARE);

        s_feeRecipient = msg.sender;
        s_withdrawalFeeBps = 5; // 0.05% default
    }

    // Trusted function to update strategy addresses in case of upgrades or emergencies.
    function setPools(address _aavePool, address _morphoVault) external onlyOwner {
        if (_aavePool != address(0) && _aavePool.code.length == 0) {
            revert PrivacyVault__InvalidPoolAddress("Aave", _aavePool);
        }
        if (_morphoVault != address(0) && _morphoVault.code.length == 0) {
            revert PrivacyVault__InvalidPoolAddress("Morpho", _morphoVault);
        }
        if (_aavePool == address(aavePool) || _morphoVault == address(morphoVault)) {
            revert PrivacyVault__InvalidPoolAddress("New pool address must be different from current", address(0));
        }

        if (address(_aavePool) != address(0)) aavePool = IAavePool(_aavePool);
        if (address(_morphoVault) != address(0)) morphoVault = IMorphoVault(_morphoVault);

        emit PoolUpdated(address(aavePool), address(morphoVault));
    }

    function setWithdrawalFee(uint256 _feeBps) external onlyOwner {
        if (_feeBps > MAX_FEE_BPS) revert PrivacyVault__FeeTooHigh(_feeBps, MAX_FEE_BPS);
        s_withdrawalFeeBps = _feeBps;
        emit FeeUpdated(_feeBps);
    }

    function setFeeRecipient(address _feeRecipient) external onlyOwner {
        if (_feeRecipient == address(0)) revert PrivacyVault__InvalidFeeRecipient();
        s_feeRecipient = _feeRecipient;
        emit FeeRecipientUpdated(_feeRecipient);
    }

    /**
     * @dev Returns Morpho's share price scaled to RAY units (starts at RAY, grows with yield).
     *      Analogous to Aave's getReserveNormalizedIncome.
     */
    function getMorphoNormalizedIncome() public view returns (uint256) {
        uint256 currentPrice = morphoVault.convertToAssets(ONE_SHARE);
        return (currentPrice * RAY) / initialMorphoSharePrice;
    }

    /**
     * @dev Returns a blended yield index averaging Aave and Morpho, bucketed for privacy.
     *
     *      blendedIndex = (aaveIndex + morphoIndex) / 2
     *
     *      Both indices are in RAY scale (start at ~1e27). The approximation error of using
     *      a simple average vs computing each half independently is negligible when both
     *      protocols lend the same asset on the same chain (<0.01% for typical yield spreads).
     */
    function getCurrentBucketedYieldIndex() public view returns (uint256) {
        uint256 aaveIndex = aavePool.getReserveNormalizedIncome(address(token));
        uint256 morphoIndex = getMorphoNormalizedIncome();
        uint256 blendedIndex = (aaveIndex + morphoIndex) / 2;
        return (blendedIndex / BUCKET_PRECISION) * BUCKET_PRECISION;
    }

    /**
     * @dev Returns the current un-bucketed blended yield index.
     */
    function _getCurrentBlended() internal view returns (uint256) {
        uint256 aaveIndex = aavePool.getReserveNormalizedIncome(address(token));
        uint256 morphoIndex = getMorphoNormalizedIncome();
        return (aaveIndex + morphoIndex) / 2;
    }

    /**
     * @param _innerCommitment the inner commitment Poseidon2(nullifier, secret), computed off-chain
     * @param _receiveAuthorization the calldata for EIP-3009 receiveWithAuthorization function
     * @dev Contract computes finalCommitment = Poseidon2(innerCommitment, yieldIndex) on-chain
     */
    function depositWithAuthorization(bytes32 _innerCommitment, bytes calldata _receiveAuthorization)
        external
        nonReentrant
    {
        // Compute yield index and final commitment on-chain (user cannot fake yield index)
        uint256 yieldIndex = getCurrentBucketedYieldIndex();
        bytes32 finalCommitment = hashLeftRight(_innerCommitment, bytes32(yieldIndex));

        if (s_commitments[finalCommitment]) revert PrivacyVault__CommitmentAlreadyAdded(finalCommitment);
        s_commitments[finalCommitment] = true;

        (address from, address to, uint256 amount) =
            abi.decode(_receiveAuthorization[0:96], (address, address, uint256));

        if (amount != DENOMINATION) {
            revert PrivacyVault__DepositValueMismatch({expected: DENOMINATION, actual: amount});
        }
        if (to != address(this)) revert PrivacyVault__InvalidRecipient({expected: address(this), actual: to});

        // Transfer USDC from depositor to vault via EIP-3009
        (bool success,) =
            address(token).call(abi.encodePacked(_RECEIVE_WITH_AUTHORIZATION_SELECTOR, _receiveAuthorization));
        if (!success) revert PrivacyVault__PaymentFailed({recipient: address(this), amount: amount});

        // Supply USDC to Morpho and Aave to earn yield (50/50 split)
        uint256 depositSplit = amount / 2;

        token.approve(address(morphoVault), depositSplit);
        morphoVault.deposit(depositSplit, address(this));

        token.approve(address(aavePool), depositSplit);
        aavePool.supply(address(token), depositSplit, address(this), 0);
        uint32 insertedIndex = _insert(finalCommitment);

        emit DepositWithAuthorization(finalCommitment, insertedIndex, block.timestamp, yieldIndex);
    }

    function withdraw(
        bytes calldata _proof,
        bytes32 _root,
        bytes32 _nullifierHash,
        bytes32 _collateralNullifierHash,
        address _recipient,
        uint256 _yieldIndex
    ) external nonReentrant {
        if (s_nullifierHashes[_nullifierHash]) {
            revert PrivacyVault__NoteAlreadySpent({nullifierHash: _nullifierHash});
        }
        if (!isKnownRoot(_root)) revert PrivacyVault__UnknownRoot({root: _root});
        if (_yieldIndex == 0) revert PrivacyVault__InvalidYieldIndex();
        if (_recipient == address(0) || _recipient == address(this)) {
            revert PrivacyVault__InvalidRecipient({expected: address(0), actual: _recipient});
        }

        // Block withdrawal if active loan exists on this collateral
        if (s_loans[_collateralNullifierHash].active) {
            revert PrivacyVault__CollateralLocked({collateralNullifierHash: _collateralNullifierHash});
        }

        // Mark collateral as spent (prevents future borrows on this deposit)
        s_collateralSpent[_collateralNullifierHash] = true;

        // Verify proof with 5 public inputs
        bytes32[] memory publicInputs = new bytes32[](5);
        publicInputs[0] = _root;
        publicInputs[1] = _nullifierHash;
        publicInputs[2] = _collateralNullifierHash;
        publicInputs[3] = bytes32(uint256(uint160(_recipient)));
        publicInputs[4] = bytes32(_yieldIndex);

        if (!i_verifier.verify(_proof, publicInputs)) revert PrivacyVault__InvalidWithdrawProof();

        s_nullifierHashes[_nullifierHash] = true;

        // Calculate yield-adjusted payout using blended index (Aave + Morpho)
        uint256 currentAaveIndex = aavePool.getReserveNormalizedIncome(address(token));
        uint256 currentMorphoIndex = getMorphoNormalizedIncome();
        uint256 currentBlended = (currentAaveIndex + currentMorphoIndex) / 2;
        uint256 payout = (DENOMINATION * currentBlended) / _yieldIndex;

        uint256 fee = (payout * s_withdrawalFeeBps) / BPS;

        // Withdraw proportionally to each protocol's current share of the yield.
        uint256 totalIndex = currentAaveIndex + currentMorphoIndex;
        uint256 aaveWithdraw = (payout * currentAaveIndex) / totalIndex;
        uint256 morphoWithdraw = payout - aaveWithdraw;

        morphoVault.withdraw(morphoWithdraw, address(this), address(this));
        aavePool.withdraw(address(token), aaveWithdraw, address(this));

        token.safeTransfer(_recipient, payout - fee);
        if (fee > 0) {
            token.safeTransfer(s_feeRecipient, fee);
        }

        emit Withdrawal(_recipient, _nullifierHash, payout - fee);
    }

    function borrow(
        bytes calldata _proof,
        bytes32 _root,
        bytes32 _collateralNullifierHash,
        address _recipient,
        uint256 _yieldIndex,
        uint256 _borrowAmount
    ) external nonReentrant {
        // 1. Check deposit not already withdrawn
        if (s_collateralSpent[_collateralNullifierHash]) {
            revert PrivacyVault__DepositAlreadyWithdrawn({collateralNullifierHash: _collateralNullifierHash});
        }
        // 2. Check no active loan on this collateral
        if (s_loans[_collateralNullifierHash].active) {
            revert PrivacyVault__LoanAlreadyActive({collateralNullifierHash: _collateralNullifierHash});
        }
        // 3. Validate root is known
        if (!isKnownRoot(_root)) revert PrivacyVault__UnknownRoot({root: _root});
        if (_yieldIndex == 0) revert PrivacyVault__InvalidYieldIndex();
        if (_recipient == address(0) || _recipient == address(this)) {
            revert PrivacyVault__InvalidRecipient({expected: address(0), actual: _recipient});
        }

        // 4. Verify ZK proof (borrow circuit: 4 public inputs)
        bytes32[] memory publicInputs = new bytes32[](4);
        publicInputs[0] = _root;
        publicInputs[1] = _collateralNullifierHash;
        publicInputs[2] = bytes32(uint256(uint160(_recipient)));
        publicInputs[3] = bytes32(_yieldIndex);
        if (!i_borrowVerifier.verify(_proof, publicInputs)) revert PrivacyVault__InvalidBorrowProof();

        // 5. LTV check
        uint256 currentBlended = _getCurrentBlended(); // get current blended yield index to calculate collateral value
        uint256 collateralValue = (DENOMINATION * currentBlended) / _yieldIndex; // adjust collateral value based on yield growth since deposit
        uint256 maxBorrow = (collateralValue * LTV_BPS) / BPS; // max borrow = collateral value * LTV (e.g. if collateral is now worth 1.04 * DENOMINATION and LTV is 70%, max borrow is 0.728 * DENOMINATION)
        if (_borrowAmount > maxBorrow) {
            revert PrivacyVault__BorrowAmountExceedsLTV({maxBorrow: maxBorrow, requested: _borrowAmount});
        }

        // 6. Record loan
        s_loans[_collateralNullifierHash] = Loan({
            principalAmount: _borrowAmount,
            borrowYieldIndex: currentBlended,
            depositYieldIndex: _yieldIndex,
            active: true
        });
        totalBorrowed += _borrowAmount;

        // 7. Withdraw from Aave/Morpho proportionally, send to recipient
        uint256 currentAaveIndex = aavePool.getReserveNormalizedIncome(address(token));
        uint256 currentMorphoIndex = getMorphoNormalizedIncome();
        uint256 totalIndex = currentAaveIndex + currentMorphoIndex;
        uint256 aaveAmt = (_borrowAmount * currentAaveIndex) / totalIndex;
        uint256 morphoAmt = _borrowAmount - aaveAmt;

        morphoVault.withdraw(morphoAmt, address(this), address(this));
        aavePool.withdraw(address(token), aaveAmt, address(this));

        token.safeTransfer(_recipient, _borrowAmount);

        emit Borrow(_collateralNullifierHash, _recipient, _borrowAmount, currentBlended);
    }

    function getDebt(bytes32 _collateralNullifierHash) public view returns (uint256) {
        Loan memory loan = s_loans[_collateralNullifierHash];
        if (!loan.active) return 0;
        uint256 currentBlended = _getCurrentBlended(); // e.g. 1.04e27
        // Debt grows with the blended yield index since the borrow time, similar to how the payout
        return (loan.principalAmount * currentBlended) / loan.borrowYieldIndex;
    }

    function getRepaymentAmount(bytes32 _collateralNullifierHash) external view returns (uint256) {
        return getDebt(_collateralNullifierHash);
    }

    function repayWithAuthorization(bytes32 _collateralNullifierHash, bytes calldata _receiveAuthorization)
        external
        nonReentrant
    {
        Loan storage loan = s_loans[_collateralNullifierHash];
        if (!loan.active) revert PrivacyVault__NoActiveLoan({collateralNullifierHash: _collateralNullifierHash});

        uint256 debt = getDebt(_collateralNullifierHash);

        // Validate EIP-3009 authorization matches debt amount
        (address from, address to, uint256 amount) =
            abi.decode(_receiveAuthorization[0:96], (address, address, uint256));
        require(amount >= debt, "Insufficient repayment");
        require(to == address(this), "Wrong recipient");

        // Receive USDC via EIP-3009
        (bool success,) =
            address(token).call(abi.encodePacked(_RECEIVE_WITH_AUTHORIZATION_SELECTOR, _receiveAuthorization));
        require(success, "Transfer failed");

        // Re-deposit debt into Aave/Morpho (50/50)
        uint256 split = debt / 2;
        token.approve(address(morphoVault), split);
        morphoVault.deposit(split, address(this));
        token.approve(address(aavePool), debt - split);
        aavePool.supply(address(token), debt - split, address(this), 0);

        // Clear loan
        loan.active = false;
        totalBorrowed -= loan.principalAmount;

        emit Repay(_collateralNullifierHash, from, debt);
    }
}
