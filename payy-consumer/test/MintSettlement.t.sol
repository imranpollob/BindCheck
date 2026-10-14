// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {VmSafe} from "forge-std/Vm.sol";
import {RollupV1, Signature} from "../src/rollup3/RollupV1.sol";
import {IVerifier} from "../src/noir/IVerifier.sol";
import {TransparentUpgradeableProxy} from "@openzeppelin/contracts/proxy/transparent/TransparentUpgradeableProxy.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// LOCAL TEST TOKEN (test-only): the token the mint's note kind maps to. Real balance changes are what the assertions check.
contract MintTestToken is ERC20 {
    constructor() ERC20("Local test token", "LTT") {}

    function mintTo(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

/// T13: one effectful mint through the ACTUAL Payy consumer (eth/contracts/rollup3/RollupV1.sol at dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36
/// behind a TransparentUpgradeableProxy) and the ACTUAL Honk verifier (committed .bin, library-linked as deploy.ts does). The proof and its
/// 1003 public inputs are the T13 artifacts (one mint message). No mock verifier, no storage overwrite, no consumer change, no signature bypass.
/// Local testbed only. Not advisory reproduction, not a vulnerability claim, not BindCheck detection.
contract MintSettlementTest is Test {
    bytes32 constant REGISTRY_KEY = 0x0701c58cb73e870b8da74294bb1a820e346546e4d3cdca393aa84d3716d3787c; // as in T12 / deploy.ts
    uint32 constant MESSAGES = 1000;
    bytes32 constant OTHER_HASH = keccak256("T13 otherHashFromBlockHash (local, arbitrary)");
    bytes32 constant CONTRACT_INITIAL_ROOT = 0x0577b5b4aa3eaba75b2a919d5d7c63b7258aa507d38e346bf2ff1d48790379ff; // hard-coded by initialize
    uint256 constant HEIGHT = 1;
    uint256 constant PI_FIELDS = 1003;
    // public-input indices (circuit ABI order: old_root, new_root, commit_hash, messages[1000])
    uint256 constant I_KIND = 3;
    uint256 constant I_NOTE_KIND = 4;
    uint256 constant I_VALUE = 5;
    uint256 constant I_HASH = 6;
    uint256 constant MINTER_FUNDS = 1000;

    address owner = makeAddr("owner");
    address prover = makeAddr("prover");
    address proxyAdminOwner = makeAddr("proxyAdminOwner");
    address minter = makeAddr("minter");
    uint256 validatorPk = uint256(keccak256("T13 validator private key (local test key)"));
    address validator;

    MintTestToken token;
    address verifier;
    address implementation;
    RollupV1 rollup;

    bytes proof;
    bytes32[] pis;
    bytes32 noteKind;
    bytes32 mintHash;
    uint256 mintValue;

    struct State {
        bytes32 rootHash;
        uint256 blockHeight;
        bytes32 mintKind;
        uint256 mintAmount;
        bool mintSpent;
        uint256 balRollup;
        uint256 balMinter;
        uint256 balProver;
        uint256 balOwner;
        address registryVerifier;
    }

    struct Result {
        bool ok;
        bytes ret;
        uint256 gasUsed;
        bool verifierCalled;
        bool verifierCallExact;
        bool verifierCallRevertedInScope;
        VmSafe.Log[] logs;
    }

    // ------------------------------------------------------------------ deployment (same pattern as T12)
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
        for (uint256 i = 0; i < PI_FIELDS; i++) {
            bytes32 w;
            assembly { w := mload(add(add(raw, 32), mul(i, 32))) }
            pis.push(w);
        }
        assertEq(uint256(pis[I_KIND]), 2, "message kind must be mint (2)");
        noteKind = pis[I_NOTE_KIND];
        mintValue = uint256(pis[I_VALUE]);
        mintHash = pis[I_HASH];

        validator = vm.addr(validatorPk);
        verifier = _deployVerifier();
        token = new MintTestToken();
        implementation = address(new RollupV1());
        address[] memory validators = new address[](1);
        validators[0] = validator;
        // initialNoteKind = the note kind carried by the mint message, so tokens[noteKind] = token (normal initialize path)
        bytes memory init = abi.encodeCall(
            RollupV1.initialize, (owner, address(token), verifier, prover, validators, REGISTRY_KEY, MESSAGES, noteKind)
        );
        rollup = RollupV1(address(new TransparentUpgradeableProxy(implementation, proxyAdminOwner, init)));
        token.mintTo(minter, MINTER_FUNDS);
    }

    // ------------------------------------------------------------------ helpers
    function _state() internal view returns (State memory s) {
        s.rootHash = rollup.rootHash();
        s.blockHeight = rollup.blockHeight();
        (s.mintKind, s.mintAmount, s.mintSpent) = rollup.mints(mintHash);
        s.balRollup = token.balanceOf(address(rollup));
        s.balMinter = token.balanceOf(minter);
        s.balProver = token.balanceOf(prover);
        s.balOwner = token.balanceOf(owner);
        (s.registryVerifier,) = rollup.getZkVerifier(REGISTRY_KEY);
    }

    function _assertSame(State memory a, State memory b) internal pure {
        assertEq(a.rootHash, b.rootHash, "rootHash changed");
        assertEq(a.blockHeight, b.blockHeight, "blockHeight changed");
        assertEq(a.mintKind, b.mintKind, "mint note_kind changed");
        assertEq(a.mintAmount, b.mintAmount, "mint amount changed");
        assertEq(a.mintSpent, b.mintSpent, "mint spent flag changed");
        assertEq(a.balRollup, b.balRollup, "rollup balance changed");
        assertEq(a.balMinter, b.balMinter, "minter balance changed");
        assertEq(a.balProver, b.balProver, "prover balance changed");
        assertEq(a.balOwner, b.balOwner, "owner balance changed");
        assertEq(a.registryVerifier, b.registryVerifier, "registry changed");
    }

    function _copy() internal view returns (bytes32[] memory out) {
        out = new bytes32[](pis.length);
        for (uint256 i = 0; i < pis.length; i++) out[i] = pis[i];
    }

    function _sigs(bytes32 newRoot) internal view returns (Signature[] memory sigs) {
        bytes32 digest = rollup.debugGetSignatureMessageHash(newRoot, HEIGHT, OTHER_HASH);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(validatorPk, digest);
        sigs = new Signature[](1);
        sigs[0] = Signature({r: r, s: s, v: uint256(v)});
    }

    /// Normal contract interface: ERC20 approve + RollupV1.mint(hash, value, noteKind) by `minter`. Returns gas and logs of the registration.
    function _register(bytes32 hash, uint256 value) internal returns (uint256 gasUsed, VmSafe.Log[] memory logs) {
        vm.prank(minter);
        token.approve(address(rollup), value);
        vm.recordLogs();
        vm.prank(minter);
        uint256 g = gasleft();
        rollup.mint(hash, bytes32(value), noteKind);
        gasUsed = g - gasleft();
        logs = vm.getRecordedLogs();
    }

    function _submit(bytes32[] memory inputs) internal returns (Result memory r) {
        bytes memory data = abi.encodeCall(RollupV1.verifyRollup, (HEIGHT, REGISTRY_KEY, proof, inputs, OTHER_HASH, _sigs(pis[1])));
        bytes memory expectedVerifierCall = abi.encodeCall(IVerifier.verify, (proof, inputs));
        vm.recordLogs();
        vm.startStateDiffRecording();
        vm.prank(prover);
        uint256 g = gasleft();
        (r.ok, r.ret) = address(rollup).call(data);
        r.gasUsed = g - gasleft();
        VmSafe.AccountAccess[] memory acc = vm.stopAndReturnStateDiff();
        r.logs = vm.getRecordedLogs();
        for (uint256 i = 0; i < acc.length; i++) {
            bool isCall = acc[i].kind == VmSafe.AccountAccessKind.Call || acc[i].kind == VmSafe.AccountAccessKind.StaticCall;
            if (isCall && acc[i].account == verifier && acc[i].accessor == address(rollup)) {
                r.verifierCalled = true;
                r.verifierCallExact = keccak256(acc[i].data) == keccak256(expectedVerifierCall);
                r.verifierCallRevertedInScope = acc[i].reverted;
            }
        }
    }

    function _reason(bytes memory ret) internal view returns (string memory) {
        if (ret.length >= 4 && bytes4(ret) == bytes4(keccak256("Error(string)"))) {
            bytes memory body = new bytes(ret.length - 4);
            for (uint256 i = 0; i < body.length; i++) body[i] = ret[i + 4];
            return abi.decode(body, (string));
        }
        if (ret.length >= 4) {
            if (bytes4(ret) == bytes4(keccak256("SumcheckFailed()"))) return "verifier custom error SumcheckFailed()";
            return string.concat("custom error selector ", vm.toString(bytes32(bytes4(ret))));
        }
        return "empty revert data";
    }

    function _stateJson(State memory s) internal view returns (string memory) {
        return string.concat(
            '{"rootHash":"', vm.toString(s.rootHash), '","blockHeight":"', vm.toString(s.blockHeight), '","mint":{"noteKind":"', vm.toString(s.mintKind),
            '","amount":"', vm.toString(s.mintAmount), '","spent":', s.mintSpent ? "true" : "false", '},"tokenBalances":{"rollup":"', vm.toString(s.balRollup),
            '","minter":"', vm.toString(s.balMinter), '","prover":"', vm.toString(s.balProver), '","owner":"', vm.toString(s.balOwner), '"}}'
        );
    }

    function _logsJson(VmSafe.Log[] memory logs) internal view returns (string memory out) {
        out = "[";
        for (uint256 i = 0; i < logs.length; i++) {
            out = string.concat(out, i == 0 ? "" : ",", '{"emitter":"', logs[i].emitter == address(rollup) ? "consumer" : (logs[i].emitter == address(token) ? "token" : "other"),
                '","topic0":"', vm.toString(logs[i].topics[0]), '"}');
        }
        out = string.concat(out, "]");
    }

    function _observe(string memory name, string memory registeredValue, uint256 regGas, Result memory r, State memory pre, State memory post) internal {
        vm.createDir("results/raw/T13/observations", true);
        string memory head = string.concat(
            '{"schema":"bindcheck.consumer-observation/v0-compact","name":"', name, '","revision":"dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36","consumerProxy":"',
            vm.toString(address(rollup)), '","verifier":"', vm.toString(verifier), '","registryKey":"', vm.toString(REGISTRY_KEY), '",'
        );
        string memory mintInfo = string.concat(
            '"mintMessage":{"kind":"2","noteKind":"', vm.toString(noteKind), '","value":"', vm.toString(mintValue), '","hash":"', vm.toString(mintHash),
            '"},"registeredValue":"', registeredValue, '","registrationGas":"', vm.toString(regGas), '",'
        );
        string memory outcome = string.concat(
            '"status":"', r.ok ? "success" : "reverted", '","reason":"', r.ok ? "" : _reason(r.ret), '","settlementGas":"', vm.toString(r.gasUsed),
            '","verifierCall":{"observed":', r.verifierCalled ? "true" : "false", ',"calldataEqualsExpected":', r.verifierCallExact ? "true" : "false",
            ',"revertedInScope":', r.verifierCallRevertedInScope ? "true" : "false", '},"settlementLogs":', _logsJson(r.logs),
            r.ok ? "" : ',"settlementLogsNote":"recorder also lists events emitted inside reverted frames; a chain would discard them"', ","
        );
        vm.writeFile(string.concat("results/raw/T13/observations/", name, ".json"), string.concat(head, mintInfo, outcome, '"pre":', _stateJson(pre), ',"post":', _stateJson(post), "}"));
    }

    // ------------------------------------------------------------------ the effectful settlement
    function test_mintRegistrationAndSettlement() public {
        assertEq(rollup.rootHash(), CONTRACT_INITIAL_ROOT);
        assertEq(pis[0], CONTRACT_INITIAL_ROOT, "block starts at the consumer's own initial root: no setRoot needed");

        // 1. registration through the normal interface
        State memory beforeReg = _state();
        (uint256 regGas, VmSafe.Log[] memory regLogs) = _register(mintHash, mintValue);
        State memory pre = _state();
        assertEq(pre.balMinter, beforeReg.balMinter - mintValue, "minter paid the mint value");
        assertEq(pre.balRollup, beforeReg.balRollup + mintValue, "consumer escrowed the mint value");
        assertEq(pre.mintKind, noteKind);
        assertEq(pre.mintAmount, mintValue);
        assertFalse(pre.mintSpent);
        assertEq(regLogs.length, 2, "registration logs: token Transfer then MintAdded");
        assertEq(regLogs[0].emitter, address(token));
        assertEq(regLogs[1].emitter, address(rollup));
        assertEq(regLogs[1].topics[0], keccak256("MintAdded(bytes32,uint256,bytes32)"));
        assertEq(regLogs[1].topics[1], mintHash);

        // 2. settlement through verifyRollup
        Result memory r = _submit(_copy());
        State memory post = _state();
        assertTrue(r.ok, string.concat("settlement reverted: ", _reason(r.ret)));
        assertTrue(r.verifierCalled && r.verifierCallExact && !r.verifierCallRevertedInScope, "real verifier called with exactly (proof, publicInputs)");
        assertEq(post.rootHash, pis[1], "root advanced to the block's new root");
        assertTrue(pre.rootHash != post.rootHash);
        assertEq(post.blockHeight, HEIGHT);
        // mint consumed: spent flag set, amount/kind unchanged; the escrowed tokens stay in the consumer (no transfer at settlement)
        assertEq(post.mintKind, noteKind);
        assertEq(post.mintAmount, mintValue);
        assertTrue(post.mintSpent, "mint must be marked spent");
        assertEq(post.balRollup, pre.balRollup);
        assertEq(post.balMinter, pre.balMinter);
        assertEq(post.balProver, pre.balProver);
        assertEq(post.balOwner, pre.balOwner);
        // exactly two consumer events in order: Minted(hash, value, noteKind) then RollupVerified(height, newRoot); nothing from the token
        assertEq(r.logs.length, 2, "settlement emits exactly two events");
        assertEq(r.logs[0].emitter, address(rollup));
        assertEq(r.logs[0].topics[0], keccak256("Minted(bytes32,bytes32,bytes32)"));
        assertEq(r.logs[0].topics[1], mintHash);
        (bytes32 evValue, bytes32 evKind) = abi.decode(r.logs[0].data, (bytes32, bytes32));
        assertEq(uint256(evValue), mintValue);
        assertEq(evKind, noteKind);
        assertEq(r.logs[1].emitter, address(rollup));
        assertEq(r.logs[1].topics[0], keccak256("RollupVerified(uint256,bytes32)"));
        assertEq(uint256(r.logs[1].topics[1]), HEIGHT);
        assertEq(abi.decode(r.logs[1].data, (bytes32)), pis[1]);
        _observe("mint_settlement", vm.toString(mintValue), regGas, r, pre, post);
    }

    // ------------------------------------------------------------------ controls (each runs on a fresh equivalent deployment via setUp)

    // Control A1: encoded mint amount changed (100 -> 101), original proof, the ORIGINAL 100-unit registration in place.
    function test_control_amountAltered() public {
        (uint256 regGas,) = _register(mintHash, mintValue);
        State memory pre = _state();
        bytes32[] memory bad = _copy();
        bad[I_VALUE] = bytes32(mintValue + 1);
        Result memory r = _submit(bad);
        State memory post = _state();
        assertFalse(r.ok);
        _assertSame(pre, post);
        assertEq(_reason(r.ret), "RollupV1: Mint value invalid"); // consumer's verifyMint: registered amount != encoded amount
        assertFalse(r.verifierCalled, "rejected by the consumer before the verifier");
        _observe("control_amount_altered", vm.toString(mintValue), regGas, r, pre, post);
    }

    // Control A2 (additional): same altered amount, but a mint of that altered amount IS registered, so the consumer's own checks pass and the
    // real verifier must reject the altered public input.
    function test_control_amountAltered_matchingRegistration_reachesVerifier() public {
        (uint256 regGas,) = _register(mintHash, mintValue + 1);
        State memory pre = _state();
        bytes32[] memory bad = _copy();
        bad[I_VALUE] = bytes32(mintValue + 1);
        Result memory r = _submit(bad);
        State memory post = _state();
        assertFalse(r.ok);
        _assertSame(pre, post);
        assertTrue(r.verifierCalled && r.verifierCallExact, "verifier reached with the exact altered calldata");
        assertTrue(r.verifierCallRevertedInScope);
        assertFalse(post.mintSpent, "spent flag rolled back");
        _observe("control_amount_altered_matching_registration", vm.toString(mintValue + 1), regGas, r, pre, post);
    }

    // Control B: the encoded mint HASH (the only identity the message carries; there is no recipient field) changed, original registration in place.
    function test_control_mintHashAltered() public {
        (uint256 regGas,) = _register(mintHash, mintValue);
        State memory pre = _state();
        bytes32 altHash = bytes32(uint256(mintHash) ^ 1);
        (bytes32 altKind, uint256 altAmount, bool altSpent) = rollup.mints(altHash);
        bytes32[] memory bad = _copy();
        bad[I_HASH] = altHash;
        Result memory r = _submit(bad);
        State memory post = _state();
        assertFalse(r.ok);
        _assertSame(pre, post);
        (bytes32 k2, uint256 a2, bool s2) = rollup.mints(altHash);
        assertTrue(k2 == altKind && a2 == altAmount && s2 == altSpent, "entry for the altered hash untouched");
        assertEq(_reason(r.ret), "RollupV1: Mint value invalid"); // unregistered hash has amount 0 != 100
        assertFalse(r.verifierCalled);
        _observe("control_mint_hash_altered", vm.toString(mintValue), regGas, r, pre, post);
    }

    // Control C: required mint registration omitted, original proof.
    function test_control_registrationOmitted() public {
        State memory pre = _state();
        assertEq(pre.mintAmount, 0);
        Result memory r = _submit(_copy());
        State memory post = _state();
        assertFalse(r.ok);
        _assertSame(pre, post);
        assertEq(_reason(r.ret), "RollupV1: Mint value invalid"); // mints[hash].amount (0) != 100
        assertFalse(r.verifierCalled, "rejected by the consumer before the verifier");
        _observe("control_registration_omitted", "0", 0, r, pre, post);
    }
}
