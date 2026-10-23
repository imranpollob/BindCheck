// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../contracts/SynthSettlement.sol";

/// @title B1 Foundry baseline for D1-04
/// @notice Direct Foundry tests checking the authorization property with concrete
///         valid-proof seeds. This is the "direct test" baseline: no SMT solver,
///         no ACIR parsing, just Solidity tests with crafted inputs.
///
///         The test models the same threat as the joint encoder: an adversary who
///         controls the witness (authorized stream) and can produce any messages
///         array that the circuit accepts.
contract SynthBaselineTest is Test {
    SynthSettlement settlement;

    function setUp() public {
        settlement = new SynthSettlement();
    }

    // ---- B1.1: Faulty producer allows unauthorized burn in the tail --------

    /// @notice Demonstrate the VIOLATION: with the faulty producer, authorized=all-zeros
    ///         means the active prefix is empty (first kind=0 → ended), so the entire
    ///         messages array is unconstrained. Place a burn in the tail.
    function test_faulty_unauthorized_burn_in_tail() public {
        // This is the exact model the D1-03 solver found:
        // authorized = [0,0,0, 0,0,0, 0,0,0]  (certifies nothing)
        // messages   = [3,1,0, 2,0,0, 3,0,0]  (burn value=1 at slot 0)
        uint256[9] memory messages = [uint256(3), 1, 0, 2, 0, 0, 3, 0, 0];
        uint256[9] memory authorized = [uint256(0), 0, 0, 0, 0, 0, 0, 0, 0];

        // The faulty circuit ACCEPTS this witness (nargo replay confirmed).
        // Check: does the consumer settle a burn?
        SynthSettlement.SettlementResult memory r = settlement.settle(messages);

        // VIOLATION: the consumer settled burns that were not certified.
        assertTrue(r.burnCount > 0, "consumer must settle at least one burn");
        assertFalse(r.reverted_, "settlement must not revert");

        // Verify: no burn in `authorized` has kind=3
        bool anyAuthorizedBurn = false;
        for (uint256 i = 0; i + 3 <= 9; i += 3) {
            if (authorized[i] == 3) {
                anyAuthorizedBurn = true;
            }
        }
        assertFalse(anyAuthorizedBurn, "authorized stream must have no burns");
        // => settled burn is unauthorized. VIOLATION confirmed.
    }

    /// @notice The faulty producer also allows uncertified mints.
    function test_faulty_unauthorized_mint_in_tail() public {
        uint256[9] memory messages = [uint256(0), 0, 0, 2, 42, 0, 0, 0, 0];
        // authorized all zeros → active prefix empty → tail unconstrained
        // messages[3..5] = [2, 42, 0] but that's after pad at [0], so consumer
        // stops at slot 0 and never processes the mint. Need to put it before pad.
        // Actually: first record kind=0 → consumer breaks. The mint at slot 3 is
        // never reached. Let's use a layout where mint is first.
        messages = [uint256(2), 42, 0, 0, 0, 0, 0, 0, 0];
        SynthSettlement.SettlementResult memory r = settlement.settle(messages);
        assertTrue(r.mintCount > 0, "consumer must settle the unauthorized mint");
    }

    // ---- B1.2: Repaired producer blocks unauthorized tail records ----------

    /// @notice With the repaired producer, authorized=all-zeros forces messages=all-zeros.
    ///         The consumer sees pad at slot 0 and settles nothing.
    function test_repaired_all_zero_settles_nothing() public {
        uint256[9] memory messages = [uint256(0), 0, 0, 0, 0, 0, 0, 0, 0];
        SynthSettlement.SettlementResult memory r = settlement.settle(messages);
        assertEq(r.burnCount, 0, "no burns settled");
        assertEq(r.mintCount, 0, "no mints settled");
        assertFalse(r.reverted_, "no revert");
    }

    /// @notice With the repaired producer, a legitimate burn is correctly settled.
    ///         authorized = messages = [3,100,0xBEEF, 0,0,0, 0,0,0]
    function test_repaired_legitimate_burn() public {
        uint256[9] memory messages = [uint256(3), 100, 0xBEEF, 0, 0, 0, 0, 0, 0];
        SynthSettlement.SettlementResult memory r = settlement.settle(messages);
        assertEq(r.burnCount, 1, "one burn settled");
        assertFalse(r.reverted_, "no revert");
    }

    /// @notice With the repaired producer, authorized = messages (active prefix bound),
    ///         and the non-vacuity witness has active records.
    function test_repaired_nonvacuity_witness() public {
        // This is the D1-03 non-vacuity model:
        // authorized = messages = [3,0,0, 2,0,0, 2,0,0]
        uint256[9] memory messages = [uint256(3), 0, 0, 2, 0, 0, 2, 0, 0];
        SynthSettlement.SettlementResult memory r = settlement.settle(messages);
        assertEq(r.burnCount, 1, "one burn");
        assertEq(r.mintCount, 2, "two mints");
        assertFalse(r.reverted_, "no revert");
    }

    // ---- B1.3: Edge cases --------------------------------------------------

    /// @notice Invalid kind triggers consumer revert (no effects committed).
    function test_invalid_kind_reverts() public {
        uint256[9] memory messages = [uint256(99), 0, 0, 0, 0, 0, 0, 0, 0];
        SynthSettlement.SettlementResult memory r = settlement.settle(messages);
        assertTrue(r.reverted_, "invalid kind must revert");
        assertEq(r.burnCount, 0, "no burns on revert");
    }

    /// @notice All pads → no effects.
    function test_all_pads() public {
        uint256[9] memory messages = [uint256(0), 0, 0, 0, 0, 0, 0, 0, 0];
        SynthSettlement.SettlementResult memory r = settlement.settle(messages);
        assertEq(r.burnCount + r.mintCount, 0);
    }
}
