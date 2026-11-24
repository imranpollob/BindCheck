// SPDX-License-Identifier: MIT

pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {HonkVerifier} from "../src/Verifier.sol";
import {BorrowHonkVerifier} from "../src/BorrowVerifier.sol";
import {PrivacyVault, IVerifier, Poseidon2} from "../src/PrivacyVault.sol";
import {IncrementalMerkleTree} from "../src/IncrementalMerkleTree.sol";
import {MockUSDC} from "./mocks/MockERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {AavePoolMock} from "./mocks/AavePoolMock.sol";
import {MorphoVaultMock} from "./mocks/MorphoVaultMock.sol";
import {IAavePool} from "../src/interfaces/IAavePool.sol";
import {IMorphoVault} from "../src/interfaces/IMorphoPool.sol";
import {IPrivacyVault} from "../src/interfaces/IPrivacyVault.sol";

contract TestBase is Test {
    PrivacyVault public privacyVault;

    IVerifier public withdrawVerifier;
    IVerifier public borrowVerifier;

    Poseidon2 public poseidon;
    AavePoolMock public aavePool;
    MorphoVaultMock public morphoVault;
    MockUSDC public usdc;

    address public depositor;
    uint256 internal depositorKey;
    address public borrower;
    address public recipient;

    uint256 constant DENOMINATION = 100e6; // 100 USDC
    uint256 constant LTV_BPS = 7000;
    uint256 constant BPS = 10000;

    // Counter to ensure unique EIP-3009 nonces across deposits in the same block
    uint256 private _depositNonce;

    function setUp() public virtual {
        (depositor, depositorKey) = makeAddrAndKey("depositor");
        borrower = makeAddr("borrower");
        recipient = makeAddr("recipient");

        usdc = new MockUSDC(10_000_000e6);
        aavePool = new AavePoolMock();
        morphoVault = new MorphoVaultMock(IERC20(usdc));

        // Fund pools for withdrawals
        usdc.mint(address(aavePool), 100_000e6);
        usdc.mint(address(morphoVault), 100_000e6);
        usdc.transfer(depositor, 10_000e6);

        poseidon = new Poseidon2();
        withdrawVerifier = new HonkVerifier();
        borrowVerifier = IVerifier(address(new BorrowHonkVerifier()));

        privacyVault = new PrivacyVault(
            withdrawVerifier,
            borrowVerifier,
            poseidon,
            20,
            DENOMINATION,
            IERC20(usdc),
            IAavePool(address(aavePool)),
            IMorphoVault(address(morphoVault))
        );
    }

    // ---- Helpers ----

    function _getCommitment() internal returns (bytes32 commitment, bytes32 nullifier, bytes32 secret) {
        string[] memory inputs = new string[](3);
        inputs[0] = "npx";
        inputs[1] = "tsx";
        inputs[2] = "js-scripts/generateCommitment.ts";
        bytes memory result = vm.ffi(inputs);
        (commitment, nullifier, secret) = abi.decode(result, (bytes32, bytes32, bytes32));
    }

    function _deposit(bytes32 _nullifier, bytes32 _secret, address _depositor, address _vaultAddress)
        internal
        returns (bytes32 finalCommitment, bytes32 collateralNullifierHash)
    {
        bytes32 inner = privacyVault.hashLeftRight(_nullifier, _secret);
        uint256 yieldIndex = privacyVault.getCurrentBucketedYieldIndex();
        finalCommitment = privacyVault.hashLeftRight(inner, bytes32(yieldIndex));

        bytes memory sig = _getSignature(_depositor);
        vm.prank(_depositor);
        IPrivacyVault(_vaultAddress).depositWithAuthorization(inner, sig);

        // Compute collateral nullifier hash = Poseidon2(nullifier, 1)
        collateralNullifierHash = privacyVault.hashLeftRight(_nullifier, bytes32(uint256(1)));
    }

    function _getProof(
        bytes32 _nullifier,
        bytes32 _secret,
        address _recipient,
        bytes32 _yieldIndex,
        bytes32[] memory leaves,
        bool isBorrow
    ) internal returns (bytes memory proof, bytes32[] memory publicInputs) {
        string memory fileName = isBorrow ? "generateBorrowProof" : "generateProof";
        string[] memory inputs = new string[](7 + leaves.length);
        inputs[0] = "npx";
        inputs[1] = "tsx";
        inputs[2] = string(abi.encodePacked("js-scripts/", fileName, ".ts"));
        inputs[3] = vm.toString(_nullifier);
        inputs[4] = vm.toString(_secret);
        inputs[5] = vm.toString(bytes32(uint256(uint160(_recipient))));
        inputs[6] = vm.toString(_yieldIndex);

        for (uint256 i = 0; i < leaves.length; i++) {
            inputs[7 + i] = vm.toString(leaves[i]);
        }

        bytes memory result = vm.ffi(inputs);
        (proof, publicInputs) = abi.decode(result, (bytes, bytes32[]));
    }

    function _getSignature(address from) internal returns (bytes memory) {
        bytes32 nonce = keccak256(
            abi.encodePacked("nonce", from, address(privacyVault), block.number, block.timestamp, _depositNonce)
        );
        _depositNonce++;
        string[] memory inputs = new string[](12);
        inputs[0] = "npx";
        inputs[1] = "tsx";
        inputs[2] = "js-scripts/generateSignature.ts";
        inputs[3] = vm.toString(depositorKey);
        inputs[4] = vm.toString(address(privacyVault));
        inputs[5] = vm.toString(privacyVault.DENOMINATION());
        inputs[6] = vm.toString(address(usdc));
        inputs[7] = vm.toString(block.chainid);
        inputs[8] = vm.toString(nonce);
        inputs[9] = "USD";
        inputs[10] = "2";
        inputs[11] = vm.toString(block.timestamp);
        return vm.ffi(inputs);
    }

    function _getRepaySignature(address from, uint256 amount) internal returns (bytes memory) {
        bytes32 nonce =
            keccak256(abi.encodePacked("repay-nonce", from, address(privacyVault), block.number, block.timestamp));
        string[] memory inputs = new string[](12);
        inputs[0] = "npx";
        inputs[1] = "tsx";
        inputs[2] = "js-scripts/generateSignature.ts";
        inputs[3] = vm.toString(depositorKey);
        inputs[4] = vm.toString(address(privacyVault));
        inputs[5] = vm.toString(amount);
        inputs[6] = vm.toString(address(usdc));
        inputs[7] = vm.toString(block.chainid);
        inputs[8] = vm.toString(nonce);
        inputs[9] = "USD";
        inputs[10] = "2";
        inputs[11] = vm.toString(block.timestamp);
        return vm.ffi(inputs);
    }

    function _computeMaxBorrow() internal view returns (uint256) {
        uint256 currentBlended =
            (aavePool.getReserveNormalizedIncome(address(usdc)) + privacyVault.getMorphoNormalizedIncome()) / 2;
        uint256 yieldIndex = privacyVault.getCurrentBucketedYieldIndex();
        uint256 collateralValue = (DENOMINATION * currentBlended) / yieldIndex;
        return (collateralValue * LTV_BPS) / BPS;
    }
}
