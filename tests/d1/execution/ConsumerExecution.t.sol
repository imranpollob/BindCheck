// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

import {RollupV1, Mint} from "payy/rollup3/RollupV1.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

interface LogVm {
    struct Log { bytes32[] topics; bytes data; address emitter; }
    function recordLogs() external;
    function getRecordedLogs() external returns (Log[] memory);
}

contract ExecutionToken is ERC20 {
    constructor() ERC20("Owned component token", "TEST") {}
    function fund(address recipient, uint amount) external { _mint(recipient, amount); }
}

// Exposes the unchanged message path, with test-only admitted-state setup.
// No verifier is instantiated. These are component checks, not verifyRollup
// acceptance, proof replay, or a security verdict.
contract ExecutionComponent is RollupV1 {
    function setup(address token) external { tokens[bytes32(uint(0x4b))] = token; }
    function registry(bytes32 hash, bytes32 kind, uint amount) external {
        mints[hash] = Mint(kind, amount, false);
    }
    function run(bytes32[] calldata words, uint32 n) external { verifyAllMessages(3, words, n); }
    function runThenRevert(bytes32[] calldata words, uint32 n) external {
        verifyAllMessages(3, words, n);
        revert("component late failure");
    }
}

contract ConsumerExecutionTest {
    LogVm constant vm = LogVm(address(uint160(uint256(keccak256("hevm cheat code")))));
    address constant RECIPIENT = address(0xdead);
    uint constant MAX_AMOUNT = type(uint64).max;

    function fixture(uint n, uint funds) internal returns (ExecutionToken t, ExecutionComponent c, bytes32[] memory words) {
        t = new ExecutionToken(); c = new ExecutionComponent(); c.setup(address(t));
        t.fund(address(c), funds); words = new bytes32[](n + 3);
    }
    function burn(bytes32[] memory w, uint offset, uint amount, uint recipient) internal pure {
        w[offset] = bytes32(uint(3)); w[offset+1] = bytes32(uint(0x4b));
        w[offset+2] = bytes32(amount); w[offset+3] = bytes32(uint(42)); w[offset+4] = bytes32(recipient);
    }
    function mintRecord(bytes32[] memory w, uint offset) internal pure {
        w[offset] = bytes32(uint(2)); w[offset+1] = bytes32(uint(0x4b));
        w[offset+2] = bytes32(uint(100)); w[offset+3] = bytes32(uint(42));
    }
    function countTransfers(LogVm.Log[] memory logs, address token) internal pure returns (uint count) {
        for (uint i=0; i<logs.length; i++)
            if (logs[i].emitter == token && logs[i].topics.length == 3 &&
                logs[i].topics[0] == keccak256("Transfer(address,address,uint256)")) count++;
    }
    function fails(ExecutionComponent c, bytes32[] memory w, uint32 n) internal returns (bool) {
        (bool ok,) = address(c).call(abi.encodeCall(c.run, (w,n))); return !ok;
    }
    function testLastCompleteBurnAndHighRecipientBits() public {
        (ExecutionToken t, ExecutionComponent c, bytes32[] memory w) = fixture(8,8*MAX_AMOUNT);
        burn(w,6,7,(uint(1)<<160)+uint160(RECIPIENT));
        vm.recordLogs(); c.run(w,8);
        require(t.balanceOf(RECIPIENT)==7 && t.balanceOf(address(c))==8*MAX_AMOUNT-7,"balances");
        require(countTransfers(vm.getRecordedLogs(),address(t))==1,"occurrence");
    }
    function testDuplicateMintRollsBackFirstSpentWrite() public {
        (,ExecutionComponent c,bytes32[] memory w) = fixture(8,8*MAX_AMOUNT);
        c.registry(bytes32(uint(42)),bytes32(uint(0x4b)),100);
        mintRecord(w,3); mintRecord(w,7); require(fails(c,w,8),"must revert");
        (,,bool spent)=c.mints(bytes32(uint(42))); require(!spent,"registry rollback");
    }
    function testMatchingMintAndDefaultZeroEntry() public {
        (,ExecutionComponent c,bytes32[] memory w) = fixture(8,8*MAX_AMOUNT);
        c.registry(bytes32(uint(42)),bytes32(uint(0x4b)),100);
        mintRecord(w,3); c.run(w,8);
        (,,bool spent)=c.mints(bytes32(uint(42))); require(spent,"matching entry");
        w[4]=0; w[5]=0; w[6]=bytes32(uint(43)); c.run(w,8);
        (,,spent)=c.mints(bytes32(uint(43))); require(spent,"default entry is consumable");
    }
    function testWrongAmountAndKindRevert() public {
        (,ExecutionComponent c,bytes32[] memory w) = fixture(8,8*MAX_AMOUNT);
        c.registry(bytes32(uint(42)),bytes32(uint(0x4b)),100); mintRecord(w,3);
        w[5]=bytes32(uint(99)); require(fails(c,w,8),"amount mismatch");
        w[5]=bytes32(uint(100)); w[4]=bytes32(uint(0x4c)); require(fails(c,w,8),"kind mismatch");
    }
    function testLastSlotAndTruncatedMintOverreadRevert() public {
        (,ExecutionComponent c,bytes32[] memory w) = fixture(8,8*MAX_AMOUNT);
        w[10]=bytes32(uint(3)); require(fails(c,w,8),"last burn");
        w[10]=bytes32(uint(100)); w[8]=bytes32(uint(2)); w[9]=bytes32(uint(0x4b));
        require(fails(c,w,8),"short mint");
    }
    function testPartialTransferThenOverreadRollsBack() public {
        (ExecutionToken t,ExecutionComponent c,bytes32[] memory w) = fixture(8,8*MAX_AMOUNT);
        burn(w,3,7,uint160(RECIPIENT)); w[10]=bytes32(uint(2)); require(fails(c,w,8),"late overread");
        require(t.balanceOf(RECIPIENT)==0 && t.balanceOf(address(c))==8*MAX_AMOUNT,"rollback");
    }
    function testExplicitLateRevertRollsBackMixedEffects() public {
        (ExecutionToken t,ExecutionComponent c,bytes32[] memory w) = fixture(1000,1000*MAX_AMOUNT);
        c.registry(bytes32(uint(42)),bytes32(uint(0x4b)),100); mintRecord(w,3); burn(w,7,7,uint160(RECIPIENT));
        (bool ok,)=address(c).call(abi.encodeCall(c.runThenRevert,(w,uint32(1000))));
        (,,bool spent)=c.mints(bytes32(uint(42)));
        require(!ok && !spent && t.balanceOf(RECIPIENT)==0,"all effects rolled back");
    }
    function testRepeatedBurnsRetainMultiplicity() public {
        (ExecutionToken t,ExecutionComponent c,bytes32[] memory w) = fixture(1000,1000*MAX_AMOUNT);
        burn(w,3,7,uint160(RECIPIENT)); burn(w,8,7,uint160(RECIPIENT)); vm.recordLogs(); c.run(w,1000);
        require(t.balanceOf(RECIPIENT)==14,"ordered balances");
        require(countTransfers(vm.getRecordedLogs(),address(t))==2,"two occurrences");
    }
    function testZeroAndSelfTransfersRemainOccurrences() public {
        (ExecutionToken t,ExecutionComponent c,bytes32[] memory w) = fixture(1000,1000*MAX_AMOUNT);
        burn(w,3,0,uint160(RECIPIENT)); burn(w,8,7,uint160(address(c))); vm.recordLogs(); c.run(w,1000);
        require(t.balanceOf(RECIPIENT)==0 && t.balanceOf(address(c))==1000*MAX_AMOUNT,"unchanged balances");
        require(countTransfers(vm.getRecordedLogs(),address(t))==2,"real zero/self events");
    }
    function testSequentialLiquidityFailureIsNotTransfer() public {
        (ExecutionToken t,ExecutionComponent c,bytes32[] memory w) = fixture(1000,10);
        burn(w,3,7,uint160(RECIPIENT)); burn(w,8,7,uint160(RECIPIENT)); vm.recordLogs(); c.run(w,1000);
        require(t.balanceOf(RECIPIENT)==7 && t.balanceOf(address(c))==3,"second failure");
        require(countTransfers(vm.getRecordedLogs(),address(t))==1,"only first effect");
    }
    function testZeroDecodedRecipientHasNoTransfer() public {
        (ExecutionToken t,ExecutionComponent c,bytes32[] memory w) = fixture(8,8*MAX_AMOUNT);
        burn(w,3,7,uint(1)<<160); vm.recordLogs(); c.run(w,8);
        require(t.balanceOf(address(c))==8*MAX_AMOUNT,"preserved funds");
        require(countTransfers(vm.getRecordedLogs(),address(t))==0,"failed call");
    }
    function testInvalidKindRevertsAndPaddingDoesNot() public {
        (,ExecutionComponent c,bytes32[] memory w) = fixture(8,8*MAX_AMOUNT);
        c.run(w,8); w[10]=bytes32(uint(4)); require(fails(c,w,8),"invalid kind");
    }
    function testActualCalldataBoundsNotLogicalSubarray() public {
        (ExecutionToken t,ExecutionComponent c,bytes32[] memory w) = fixture(8,8*MAX_AMOUNT);
        // Helper alone can read beyond its scan end when calldata has words.
        // verifyRollup's separate length guard excludes this state for n=1.
        burn(w,3,7,uint160(RECIPIENT)); c.run(w,1);
        require(t.balanceOf(RECIPIENT)==7,"calldata bound differs from scan end");
    }
}
