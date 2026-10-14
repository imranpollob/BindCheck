// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";

/// T07 BASELINE: a conventional direct Foundry property over one settlement attempt.
/// Standalone: reads raw storage with vm.load and shares no code with the JavaScript checker.
/// It is an EXTENSION of the T04-T06 raw-storage oracle assertions, not independent researcher
/// validation: it encodes the same semantics (see SHARED ASSUMPTIONS).
///
/// SHARED ASSUMPTIONS (identical in the trace checker's manual spec):
///  - public-input layout [0..3] amount, [4..7] active flag, [8] old commitment, [9] new commitment
///  - a row is active iff its flag == 1 (the T01 circuit forces Boolean flags)
///  - deposit identity (batchId,row) with batchId = keccak256(abi.encode(ten public inputs))
///  - 1 unit = 1 wei; backing policy: every active row needs a funded, exact-amount, unconsumed
///    entry that the settlement consumes; sum(newly consumed) == change in consumedBacking
///  - consumer storage layout: slot0 currentCommitment, slot1 consumedBacking, slot2 escrows mapping,
///    Escrow = {amount} then {funded (byte 0), consumed (byte 1)} in the next slot
///  - proof acceptance is NOT checked here; it relies on the consumer enforcing the verifier result,
///    which T07 confirms separately for each evaluated consumer.
abstract contract BaselineProperty is Test {
    uint256 internal constant B_ROWS = 4;
    uint256 internal constant B_ACTIVE_OFFSET = 4;
    uint256 internal constant B_SLOT_COMMITMENT = 0;
    uint256 internal constant B_SLOT_BACKING = 1;
    uint256 internal constant B_SLOT_ESCROWS = 2;

    struct RawSnap {
        uint256 commitment;
        uint256 backing;
        uint256 eth;
        uint256[4] amount;
        bool[4] funded;
        bool[4] consumed;
    }

    struct Eval {
        bool success;
        bool commitmentOk;
        bool accountingOk;
        bool stateUnchanged;
        uint256 violationMask; // bit r set: active row r lacks a matching funded->consumed transition
        uint256 fundedButUnconsumedMask;
        uint256 missingAmount;
        bool holds; // the direct property
    }

    function _rawSnap(address c, bytes32 id) internal view returns (RawSnap memory s) {
        s.commitment = uint256(vm.load(c, bytes32(B_SLOT_COMMITMENT)));
        s.backing = uint256(vm.load(c, bytes32(B_SLOT_BACKING)));
        s.eth = c.balance;
        for (uint256 r = 0; r < B_ROWS; r++) {
            bytes32 base = keccak256(abi.encode(r, keccak256(abi.encode(id, B_SLOT_ESCROWS))));
            uint256 packed = uint256(vm.load(c, bytes32(uint256(base) + 1)));
            s.amount[r] = uint256(vm.load(c, base));
            s.funded[r] = (packed & 0xff) == 1;
            s.consumed[r] = ((packed >> 8) & 0xff) == 1;
        }
    }

    function _same(RawSnap memory a, RawSnap memory b) internal pure returns (bool) {
        if (a.commitment != b.commitment || a.backing != b.backing || a.eth != b.eth) return false;
        for (uint256 r = 0; r < B_ROWS; r++) {
            if (a.amount[r] != b.amount[r] || a.funded[r] != b.funded[r] || a.consumed[r] != b.consumed[r]) return false;
        }
        return true;
    }

    /// Evaluates the property for one attempt. Does not assert (the experiment needs the result for violating cases too).
    function _evaluate(bool success, uint256[10] memory p, RawSnap memory pre, RawSnap memory post)
        internal
        pure
        returns (Eval memory e)
    {
        e.success = success;
        if (!success) {
            e.stateUnchanged = _same(pre, post);
            e.holds = e.stateUnchanged;
            return e;
        }
        e.commitmentOk = pre.commitment == p[8] && post.commitment == p[9];
        uint256 newlyConsumed;
        for (uint256 r = 0; r < B_ROWS; r++) {
            if (!pre.consumed[r] && post.consumed[r]) newlyConsumed += pre.amount[r];
            if (p[B_ACTIVE_OFFSET + r] != 1) continue;
            bool ok = pre.funded[r] && pre.amount[r] == p[r] && !pre.consumed[r] && post.consumed[r];
            if (!ok) {
                e.violationMask |= 1 << r;
                e.missingAmount += p[r];
                if (pre.funded[r] && pre.amount[r] == p[r] && !pre.consumed[r] && !post.consumed[r]) {
                    e.fundedButUnconsumedMask |= 1 << r;
                }
            }
        }
        e.accountingOk = post.backing - pre.backing == newlyConsumed;
        e.holds = e.commitmentOk && e.accountingOk && e.violationMask == 0;
    }

    /// The standalone assertion form of the property.
    function assertCoverageProperty(Eval memory e, string memory ctx) internal pure {
        if (!e.success) {
            require(e.stateUnchanged, string.concat(ctx, ": reverted settlement changed protected state"));
            return;
        }
        require(e.commitmentOk, string.concat(ctx, ": commitment does not match authenticated old/new"));
        require(e.violationMask == 0, string.concat(ctx, ": an active row lacks a matching funded->consumed transition"));
        require(e.accountingOk, string.concat(ctx, ": newly consumed amounts != consumedBacking change"));
    }
}
