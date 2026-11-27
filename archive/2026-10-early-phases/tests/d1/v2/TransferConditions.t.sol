// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

import {RollupV1} from "payy/rollup3/RollupV1.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

// Minting is test initialization only. transfer/_transfer/_update are unchanged.
contract OwnedToken is ERC20 {
    constructor() ERC20("Owned synthetic asset", "TEST") {}
    function fund(address recipient, uint256 amount) external { _mint(recipient, amount); }
}

// Exposes the unchanged consumer helper. No verifier is instantiated or mocked;
// this is a component test and does not execute verifyRollup.
contract BurnComponent is RollupV1 {
    function attempt(address token, bytes32 recipientWord, uint256 value) external returns (bool) {
        return executeBurn(token, bytes32ToAddress(recipientWord), bytes32(uint256(42)), value, false);
    }
    function attemptThenRevert(address token, address recipient, uint256 value) external {
        executeBurn(token, recipient, bytes32(uint256(42)), value, false);
        revert("outer transaction rejected");
    }
}

contract TransferConditionsTest {
    event Observation(string name, bool success, uint256 beforeBalance, uint256 afterBalance, uint256 recipientBalance);
    address constant RECIPIENT = address(0xdead);

    function fixture(uint256 funds) internal returns (OwnedToken t, BurnComponent c) {
        t = new OwnedToken();
        c = new BurnComponent();
        t.fund(address(c), funds);
    }

    function testFundedTransferCommits() public {
        (OwnedToken t, BurnComponent c) = fixture(100);
        bool ok = c.attempt(address(t), bytes32(uint256(uint160(RECIPIENT))), 7);
        require(ok && t.balanceOf(address(c)) == 93 && t.balanceOf(RECIPIENT) == 7, "funded");
        emit Observation("funded", ok, 100, 93, 7);
    }

    function testInsufficientBalanceIsFailureAndNoEffect() public {
        (OwnedToken t, BurnComponent c) = fixture(6);
        bool ok = c.attempt(address(t), bytes32(uint256(uint160(RECIPIENT))), 7);
        require(!ok && t.balanceOf(address(c)) == 6 && t.balanceOf(RECIPIENT) == 0, "insufficient");
        emit Observation("insufficient", ok, 6, 6, 0);
    }

    function testZeroRecipientFailsDespiteFunding() public {
        (OwnedToken t, BurnComponent c) = fixture(100);
        bool ok = c.attempt(address(t), bytes32(0), 7);
        require(!ok && t.balanceOf(address(c)) == 100 && t.totalSupply() == 100, "zero recipient");
        emit Observation("zero recipient", ok, 100, 100, 0);
    }

    function testZeroAmountIsLegitimate() public {
        (OwnedToken t, BurnComponent c) = fixture(0);
        bool ok = c.attempt(address(t), bytes32(uint256(uint160(RECIPIENT))), 0);
        require(ok && t.balanceOf(address(c)) == 0 && t.balanceOf(RECIPIENT) == 0, "zero amount");
        emit Observation("zero amount", ok, 0, 0, 0);
    }

    function testSelfTransferPreservesBalance() public {
        (OwnedToken t, BurnComponent c) = fixture(100);
        bool ok = c.attempt(address(t), bytes32(uint256(uint160(address(c)))), 7);
        require(ok && t.balanceOf(address(c)) == 100 && t.totalSupply() == 100, "self transfer");
        emit Observation("self transfer", ok, 100, 100, 100);
    }

    function testSequentialTransfersUseUpdatedBalance() public {
        (OwnedToken t, BurnComponent c) = fixture(10);
        bytes32 word = bytes32(uint256(uint160(RECIPIENT)));
        require(c.attempt(address(t), word, 7), "first");
        bool second = c.attempt(address(t), word, 7);
        require(!second && t.balanceOf(address(c)) == 3 && t.balanceOf(RECIPIENT) == 7, "second");
        emit Observation("second fails", second, 3, 3, 7);
    }

    function testRecipientUsesLow160Bits() public {
        (OwnedToken t, BurnComponent c) = fixture(100);
        bytes32 word = bytes32((uint256(1) << 160) + uint256(uint160(RECIPIENT)));
        bool ok = c.attempt(address(t), word, 7);
        require(ok && t.balanceOf(RECIPIENT) == 7 && t.balanceOf(address(c)) == 93, "truncation");
        emit Observation("high word aliases recipient", ok, 100, 93, 7);
    }

    function testNonzeroWordCanDecodeToZeroAddress() public {
        (OwnedToken t, BurnComponent c) = fixture(100);
        bool ok = c.attempt(address(t), bytes32(uint256(1) << 160), 7);
        require(!ok && t.balanceOf(address(c)) == 100, "decoded zero");
        emit Observation("decoded zero", ok, 100, 100, 0);
    }

    function testOuterRevertRollsBackTransfer() public {
        (OwnedToken t, BurnComponent c) = fixture(100);
        (bool ok,) = address(c).call(abi.encodeCall(c.attemptThenRevert, (address(t), RECIPIENT, 7)));
        require(!ok && t.balanceOf(address(c)) == 100 && t.balanceOf(RECIPIENT) == 0, "rollback");
        emit Observation("outer rollback", ok, 100, 100, 0);
    }

    function testEmptyAccountSuccessIsNotTokenTransfer() public {
        (, BurnComponent c) = fixture(0);
        address emptyAccount = address(0x123456);
        require(emptyAccount.code.length == 0, "not empty");
        bool ok = c.attempt(emptyAccount, bytes32(uint256(uint160(RECIPIENT))), 7);
        require(ok, "low-level call convention");
        emit Observation("empty account outside supported token model", ok, 0, 0, 0);
    }
}
