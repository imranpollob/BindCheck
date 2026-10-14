// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.27;

import {Test} from "forge-std/Test.sol";
import {console2} from "forge-std/console2.sol";
import {HonkVerifier} from "../src/AggFinalHonkVerifier.sol";

/// T11: the T10 zero-message agg_final proof against the REAL generated Solidity verifier
/// (payy eth/noir/agg_final.sol @ dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36, byte-identical to `bb write_solidity_verifier`
/// output from the committed agg_final key, see T09). No mock, no modification of the verifier, no format conversion:
///   proof        = the bb `proof` file as written (10560 bytes = 330 x 32; its first 16 fields are the pairing-point object)
///   publicInputs = the bb `public_inputs` file read as 1003 big-endian bytes32 words (old_root, new_root, commit_hash, messages[1000])
/// This demonstrates local Solidity verification of a zero-message proof. It is not consumer settlement, effectful-message
/// generation, advisory reproduction or BindCheck detection.
contract AggFinalVerifyTest is Test {
    uint256 constant GAS_LIMIT = 30_000_000; // explicit per-call bound
    bytes32 constant PROOF_SHA256 = 0x2191d1a1e9dffc1b4567b6bbbc5ee75ecfb900062012f6be050a37163b6b715c;
    bytes32 constant PI_SHA256 = 0x1b0aa08a9715b107f395724810caf78500b3f6289ce74e665b7080914e549488;
    uint256 constant PROOF_BYTES = 10560;
    uint256 constant PI_FIELDS = 1003;

    HonkVerifier verifier;
    bytes proof;
    bytes32[] pis;

    function setUp() public {
        proof = vm.readFileBinary("results/raw/T10/agg_final_new/proof");
        bytes memory raw = vm.readFileBinary("results/raw/T10/agg_final_new/public_inputs");
        // These must be exactly the T10 artifacts.
        assertEq(sha256(proof), PROOF_SHA256, "proof differs from the T10 artifact");
        assertEq(sha256(raw), PI_SHA256, "public inputs differ from the T10 artifact");
        assertEq(proof.length, PROOF_BYTES);
        assertEq(raw.length, PI_FIELDS * 32);
        for (uint256 i = 0; i < PI_FIELDS; i++) {
            bytes32 w;
            assembly { w := mload(add(add(raw, 32), mul(i, 32))) }
            pis.push(w);
        }
        verifier = new HonkVerifier();
    }

    function _name(bytes4 sel) internal pure returns (string memory) {
        if (sel == bytes4(keccak256("SumcheckFailed()"))) return "SumcheckFailed()";
        if (sel == bytes4(keccak256("ShpleminiFailed()"))) return "ShpleminiFailed()";
        if (sel == bytes4(keccak256("ConsistencyCheckFailed()"))) return "ConsistencyCheckFailed()";
        if (sel == bytes4(keccak256("PublicInputsLengthWrong()"))) return "PublicInputsLengthWrong()";
        if (sel == bytes4(keccak256("ProofLengthWrong()"))) return "ProofLengthWrong()";
        if (sel == bytes4(keccak256("ProofLengthWrongWithLogN(uint256,uint256,uint256)"))) return "ProofLengthWrongWithLogN(logN,actual,expected)";
        if (sel == bytes4(keccak256("GeminiChallengeInSubgroup()"))) return "GeminiChallengeInSubgroup()";
        return "unknown selector";
    }

    function test_positive_realVerifierAcceptsT10Proof() public {
        console2.log("verifier runtime code bytes:", address(verifier).code.length);
        // Copy storage -> memory first so the measurement excludes ~1,300 cold SLOADs of the test fixture itself.
        bytes memory p = proof;
        bytes32[] memory q = pis;
        uint256 g0 = gasleft();
        bool ok = verifier.verify{gas: GAS_LIMIT}(p, q);
        uint256 used = g0 - gasleft();
        console2.log("POSITIVE verify() returned:", ok);
        console2.log("POSITIVE gas used (call incl. ABI-encoding of args; excludes fixture loading; cap 30,000,000):", used);
        assertTrue(ok, "real verifier must accept the T10 proof with its original public inputs");
    }

    function test_negative_messages0_zero_to_one_rejected() public {
        assertEq(pis[3], bytes32(0), "messages[0] is the field at index 3 and is zero in the T10 proof");
        bytes32[] memory bad = new bytes32[](PI_FIELDS);
        for (uint256 i = 0; i < PI_FIELDS; i++) bad[i] = pis[i];
        bad[3] = bytes32(uint256(1)); // old_root=0, new_root=1, commit_hash=2, messages[0]=3
        bytes memory p = proof;
        uint256 g0 = gasleft();
        try verifier.verify{gas: GAS_LIMIT}(p, bad) returns (bool r) {
            console2.log("NEGATIVE verify() returned (no revert):", r);
            console2.log("NEGATIVE gas used:", g0 - gasleft());
            assertFalse(r, "altered public input must not verify");
        } catch (bytes memory reason) {
            bytes4 sel = reason.length >= 4 ? bytes4(reason) : bytes4(0);
            console2.log("NEGATIVE verify() REVERTED, error:", _name(sel));
            console2.log("NEGATIVE gas used:", g0 - gasleft());
            assertGt(reason.length, 3, "revert must carry a selector");
        }
    }

    // Interface-strictness checks: they document that the verifier accepts only the pinned formats, which is why no padding,
    // truncation or offset adjustment is applied anywhere in this task.
    function test_interface_rejectsWrongLengths_noGuessing() public {
        // 1019 public inputs (key-header count, with 16 appended zero words) is NOT accepted.
        bytes32[] memory withZeros = new bytes32[](1019);
        for (uint256 i = 0; i < PI_FIELDS; i++) withZeros[i] = pis[i];
        try verifier.verify{gas: GAS_LIMIT}(proof, withZeros) returns (bool) {
            revert("1019-field public inputs must not be accepted");
        } catch (bytes memory r) {
            assertEq(bytes4(r), bytes4(keccak256("PublicInputsLengthWrong()")));
            console2.log("1019 public inputs ->", _name(bytes4(r)));
        }
        // 1002 public inputs
        bytes32[] memory shortPis = new bytes32[](PI_FIELDS - 1);
        for (uint256 i = 0; i < PI_FIELDS - 1; i++) shortPis[i] = pis[i];
        try verifier.verify{gas: GAS_LIMIT}(proof, shortPis) returns (bool) {
            revert("1002-field public inputs must not be accepted");
        } catch (bytes memory r) {
            assertEq(bytes4(r), bytes4(keccak256("PublicInputsLengthWrong()")));
        }
        // proof one byte short
        bytes memory shortProof = new bytes(PROOF_BYTES - 1);
        for (uint256 i = 0; i < PROOF_BYTES - 1; i++) shortProof[i] = proof[i];
        try verifier.verify{gas: GAS_LIMIT}(shortProof, pis) returns (bool) {
            revert("short proof must not be accepted");
        } catch (bytes memory r) {
            assertEq(bytes4(r), bytes4(keccak256("ProofLengthWrongWithLogN(uint256,uint256,uint256)")));
            console2.log("proof 1 byte short ->", _name(bytes4(r)));
        }
    }
}
