// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {VmSafe} from "forge-std/Vm.sol";
import {RollupV1, Signature} from "../src/rollup3/RollupV1.sol";
import {IVerifier} from "../src/noir/IVerifier.sol";
import {TransparentUpgradeableProxy} from "@openzeppelin/contracts/proxy/transparent/TransparentUpgradeableProxy.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract RepairedMintControlToken is ERC20 {
    constructor() ERC20("Local test token", "LTT") {}
    function mintTo(address to, uint256 amount) external { _mint(to, amount); }
}

/// T19 (2/3): the EXISTING legitimate mint-only control (T13's proof, unchanged) through the CHECK-ADDED revision's own actual
/// consumer and verifier (dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36 -- the same artifacts T12-T14 already used; reused here, not
/// regenerated). Confirms (a) it still settles through the normal registration/signature flow, and (b) it moves no tokens to a
/// burn-shaped address, checked directly via balanceOf -- there is no burn message in this proof to do so. No new proof, no
/// circuit/consumer change. Local testbed only.
contract RepairedMintControlTest is Test {
    bytes32 constant REGISTRY_KEY = 0x0701c58cb73e870b8da74294bb1a820e346546e4d3cdca393aa84d3716d3787c; // revision dcd5d96, as in T12/T13
    uint32 constant MESSAGES = 1000;
    bytes32 constant OTHER_HASH = keccak256("T19 otherHashFromBlockHash (local, arbitrary)");
    uint256 constant HEIGHT = 1;
    uint256 constant PI_FIELDS = 1003;
    uint256 constant I_NOTE_KIND = 4;
    uint256 constant I_VALUE = 5;
    uint256 constant I_HASH = 6;
    address constant SOME_BURN_SHAPED_ADDRESS = 0x000000000000000000000000000000000000dEaD; // same address T15/T16/T18 used; irrelevant here since no burn message exists

    address owner = makeAddr("owner");
    address prover = makeAddr("prover");
    address proxyAdminOwner = makeAddr("proxyAdminOwner");
    address minter = makeAddr("minter");
    uint256 validatorPk = uint256(keccak256("T19 validator private key (local test key)"));
    address validator;

    RepairedMintControlToken token;
    address verifier;
    RollupV1 rollup;
    bytes proof;
    bytes32[] pis;
    bytes32 noteKind;
    bytes32 mintHash;
    uint256 mintValue;

    function _trimmedText(string memory path) internal view returns (bytes memory t) {
        bytes memory raw = bytes(vm.readFile(path));
        uint256 n = raw.length;
        while (n > 0 && (raw[n - 1] == 0x0a || raw[n - 1] == 0x20)) n--;
        t = new bytes(n);
        for (uint256 i = 0; i < n; i++) t[i] = raw[i];
    }

    function _create(bytes memory code) internal returns (address a) {
        assembly { a := create(0, add(code, 0x20), mload(code)) }
        require(a != address(0), "create failed");
    }

    function _deployVerifier() internal returns (address) {
        address lib = _create(vm.parseBytes(string.concat("0x", string(_trimmedText("build/T12/bins/agg_final_ZKTranscriptLib.bin")))));
        bytes memory txt = _trimmedText("build/T12/bins/agg_final_HonkVerifier.bin");
        string memory refs = vm.readFile("build/T12/bins/agg_final_HonkVerifier.linkrefs.json");
        uint256 start = vm.parseJsonUint(refs, "$['agg_final.sol'].ZKTranscriptLib[0].start");
        require(vm.parseJsonUint(refs, "$['agg_final.sol'].ZKTranscriptLib[0].length") == 20, "unexpected link length");
        uint256 at = start * 2;
        require(txt[at] == "_" && txt[at + 1] == "_" && txt[at + 2] == "$" && txt[at + 37] == "$" && txt[at + 38] == "_" && txt[at + 39] == "_", "no placeholder");
        bytes memory libHex = bytes(vm.toString(lib));
        for (uint256 i = 0; i < 40; i++) txt[at + i] = libHex[2 + i];
        return _create(vm.parseBytes(string.concat("0x", string(txt))));
    }

    function setUp() public {
        proof = vm.readFileBinary("results/raw/T13/agg_final_mint/proof");
        bytes memory raw = vm.readFileBinary("results/raw/T13/agg_final_mint/public_inputs");
        string memory sum = vm.readFile("results/raw/T13/40_proof_summary.json");
        assertEq(vm.toString(sha256(proof)), string.concat("0x", vm.parseJsonString(sum, "$.agg_final_proof.proof_sha256")), "proof hash differs from the recorded T13 hash");
        assertEq(vm.toString(sha256(raw)), string.concat("0x", vm.parseJsonString(sum, "$.agg_final_proof.public_inputs_sha256")), "public inputs hash differs");
        assertEq(raw.length, PI_FIELDS * 32);
        pis = new bytes32[](PI_FIELDS);
        for (uint256 i = 0; i < PI_FIELDS; i++) {
            bytes32 w;
            assembly { w := mload(add(add(raw, 32), mul(i, 32))) }
            pis[i] = w;
        }
        noteKind = pis[I_NOTE_KIND];
        mintValue = uint256(pis[I_VALUE]);
        mintHash = pis[I_HASH];
        // sanity: this proof carries no burn message at all (unlike T15/T16/T18's candidate)
        for (uint256 i = 7; i < PI_FIELDS; i++) assertEq(pis[i], bytes32(0), "T13's proof has no message beyond the single mint record");

        validator = vm.addr(validatorPk);
        verifier = _deployVerifier();
        token = new RepairedMintControlToken();
        address implementation = address(new RollupV1());
        address[] memory validators = new address[](1);
        validators[0] = validator;
        bytes memory init = abi.encodeCall(RollupV1.initialize, (owner, address(token), verifier, prover, validators, REGISTRY_KEY, MESSAGES, noteKind));
        rollup = RollupV1(address(new TransparentUpgradeableProxy(implementation, proxyAdminOwner, init)));
        token.mintTo(minter, 1000);
    }

    function _sigs(bytes32 newRoot) internal view returns (Signature[] memory sigs) {
        bytes32 digest = rollup.debugGetSignatureMessageHash(newRoot, HEIGHT, OTHER_HASH);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(validatorPk, digest);
        sigs = new Signature[](1);
        sigs[0] = Signature({r: r, s: s, v: uint256(v)});
    }

    function test_legitimateMintControl_atRepairedRevision_settlesAndMovesNothingToABurnAddress() public {
        // normal, documented registration (same as T13)
        vm.prank(minter);
        token.approve(address(rollup), mintValue);
        vm.prank(minter);
        rollup.mint(mintHash, bytes32(mintValue), noteKind);

        uint256 preRollup = token.balanceOf(address(rollup));
        uint256 preBurnAddr = token.balanceOf(SOME_BURN_SHAPED_ADDRESS);
        assertEq(preBurnAddr, 0);

        bytes memory data = abi.encodeCall(RollupV1.verifyRollup, (HEIGHT, REGISTRY_KEY, proof, pis, OTHER_HASH, _sigs(pis[1])));
        bytes memory expectedVerifierCall = abi.encodeCall(IVerifier.verify, (proof, pis));
        vm.startStateDiffRecording();
        vm.prank(prover);
        (bool ok, bytes memory ret) = address(rollup).call(data);
        VmSafe.AccountAccess[] memory acc = vm.stopAndReturnStateDiff();
        assertTrue(ok, string.concat("settlement reverted unexpectedly: ", string(ret)));

        bool verifierCalled; bool verifierCallExact;
        for (uint256 i = 0; i < acc.length; i++) {
            bool isCall = acc[i].kind == VmSafe.AccountAccessKind.Call || acc[i].kind == VmSafe.AccountAccessKind.StaticCall;
            if (isCall && acc[i].account == verifier && acc[i].accessor == address(rollup)) {
                verifierCalled = true;
                verifierCallExact = keccak256(acc[i].data) == keccak256(expectedVerifierCall);
            }
        }
        assertTrue(verifierCalled && verifierCallExact, "the real dcd5d96 verifier was called with exactly (proof, publicInputs)");
        assertEq(rollup.rootHash(), pis[1], "root advanced: the normal path still works at the repaired revision");
        (, , bool spent) = rollup.mints(mintHash);
        assertTrue(spent, "mint settled");

        // direct balance check, not inferred from any event: nothing moved to a burn-shaped address, because this proof carries no burn message
        uint256 postRollup = token.balanceOf(address(rollup));
        uint256 postBurnAddr = token.balanceOf(SOME_BURN_SHAPED_ADDRESS);
        assertEq(postRollup, preRollup, "mint settlement moves no tokens (escrow stays put, as in T13)");
        assertEq(postBurnAddr, 0, "no tokens reached the burn-shaped address: there is no burn message in this control");

        vm.createDir("results/raw/T19/observations", true);
        vm.writeFile(
            "results/raw/T19/observations/legitimate_mint_control_at_repaired_revision.json",
            string.concat(
                '{"schema":"bindcheck.consumer-observation/v0-compact","name":"legitimate_mint_control_at_repaired_revision",',
                '"revision":"dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36","status":"success","verifierCall":{"observed":', verifierCalled ? "true" : "false",
                ',"calldataEqualsExpected":', verifierCallExact ? "true" : "false", '},"tokenBalances":{"rollup":{"pre":"', vm.toString(preRollup),
                '","post":"', vm.toString(postRollup), '"},"burnShapedAddress":{"pre":"', vm.toString(preBurnAddr), '","post":"', vm.toString(postBurnAddr), '"}}}'
            )
        );
    }
}
