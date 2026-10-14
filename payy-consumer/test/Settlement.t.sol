// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {VmSafe} from "forge-std/Vm.sol";
import {RollupV1, Signature} from "../src/rollup3/RollupV1.sol";
import {IVerifier} from "../src/noir/IVerifier.sol";
import {TransparentUpgradeableProxy} from "@openzeppelin/contracts/proxy/transparent/TransparentUpgradeableProxy.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// LOCAL TEST TOKEN (test-only). Stands in for USDC at the `usdc` / note-kind slot of RollupV1.initialize. It is NOT a mock of
/// verification: its only role is to prove that a zero-message settlement moves no tokens.
contract LocalTestToken is ERC20 {
    constructor() ERC20("Local test token", "LTT") {}

    function mintTo(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

/// T12: one zero-message settlement through the ACTUAL Payy consumer (eth/contracts/rollup3/RollupV1.sol at
/// dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36) behind a TransparentUpgradeableProxy, calling the ACTUAL generated Honk verifier
/// (deployed from Payy's committed agg_final_HonkVerifier.bin, library-linked as eth/scripts/deploy.ts does), with the T10 proof
/// and public inputs. No mock verifier, no storage overwrite, no consumer modification, no signature bypass.
/// Not advisory reproduction, not BindCheck detection.
contract SettlementTest is Test {
    // Registry key exactly as Payy's deploy script / Rust client use it (Poseidon of the key fields; see reports/T12.md).
    bytes32 constant REGISTRY_KEY = 0x0701c58cb73e870b8da74294bb1a820e346546e4d3cdca393aa84d3716d3787c;
    // The verifier's own VK_HASH (keccak-flavored bb hash baked into the generated Solidity). A DIFFERENT value, shown for the record.
    bytes32 constant VERIFIER_VK_HASH = 0x0f8581a994b714ef6fcffeaea9777e69e6bc7c0140a039a23afc764d8e863328;
    uint32 constant MESSAGES = 1000; // DEFAULT_VERIFIER_MESSAGES_COUNT in deploy.ts / AGG_FINAL_MESSAGES in rollup.rs
    bytes32 constant NOTE_KIND = keccak256("T12 local note kind (placeholder, unused by a zero-message settlement)");
    bytes32 constant OTHER_HASH = keccak256("T12 otherHashFromBlockHash (local, arbitrary)");
    bytes32 constant EMPTY_TREE_ROOT = 0x0577b5b4aa3eaba75b2a919d5d7c63b7258aa507d38e346bf2ff1d48790379ff; // hard-coded by initialize
    bytes32 constant PROOF_SHA256 = 0x2191d1a1e9dffc1b4567b6bbbc5ee75ecfb900062012f6be050a37163b6b715c;
    bytes32 constant PI_SHA256 = 0x1b0aa08a9715b107f395724810caf78500b3f6289ce74e665b7080914e549488;
    uint256 constant HEIGHT = 1;
    uint256 constant PI_FIELDS = 1003;
    uint256 constant TOKEN_BALANCE = 1_000_000;

    address owner = makeAddr("owner");
    address prover = makeAddr("prover");
    address proxyAdminOwner = makeAddr("proxyAdminOwner");
    uint256 validatorPk = uint256(keccak256("T12 validator private key (local test key)"));
    address validator;

    LocalTestToken token;
    address verifier;
    address implementation;
    RollupV1 rollup;

    bytes proof;
    bytes32[] pis;

    struct State {
        bytes32 rootHash;
        uint256 blockHeight;
        bytes32 mint0Kind;
        uint256 mint0Amount;
        bool mint0Spent;
        uint256 balRollup;
        uint256 balProver;
        uint256 balOwner;
        address registryVerifier;
        uint32 registryMessages;
    }

    // ------------------------------------------------------------------ deployment (upstream pattern)
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
        // eth/scripts/deploy.ts linkAndDeployVerifier: deploy the library from its .bin, replace the `__$..$__` placeholder text
        // (20 bytes = 40 hex chars at the offset named by linkrefs.json) with the library address, deploy the verifier from its .bin.
        address lib = _create(vm.parseBytes(string.concat("0x", string(_trimmedText("build/T12/bins/agg_final_ZKTranscriptLib.bin")))));
        bytes memory txt = _trimmedText("build/T12/bins/agg_final_HonkVerifier.bin");
        string memory refs = vm.readFile("build/T12/bins/agg_final_HonkVerifier.linkrefs.json");
        uint256 start = vm.parseJsonUint(refs, "$['agg_final.sol'].ZKTranscriptLib[0].start");
        uint256 length = vm.parseJsonUint(refs, "$['agg_final.sol'].ZKTranscriptLib[0].length");
        require(length == 20, "unexpected link length");
        uint256 at = start * 2;
        require(txt[at] == "_" && txt[at + 1] == "_" && txt[at + 2] == "$" && txt[at + 37] == "$" && txt[at + 38] == "_" && txt[at + 39] == "_", "no placeholder at linkref offset");
        bytes memory libHex = bytes(vm.toString(lib)); // "0x" + 40 hex chars
        for (uint256 i = 0; i < 40; i++) txt[at + i] = libHex[2 + i];
        return _create(vm.parseBytes(string.concat("0x", string(txt))));
    }

    function setUp() public {
        proof = vm.readFileBinary("results/raw/T10/agg_final_new/proof");
        bytes memory raw = vm.readFileBinary("results/raw/T10/agg_final_new/public_inputs");
        assertEq(sha256(proof), PROOF_SHA256, "proof differs from the T10 artifact");
        assertEq(sha256(raw), PI_SHA256, "public inputs differ from the T10 artifact");
        assertEq(raw.length, PI_FIELDS * 32);
        for (uint256 i = 0; i < PI_FIELDS; i++) {
            bytes32 w;
            assembly { w := mload(add(add(raw, 32), mul(i, 32))) }
            pis.push(w);
        }

        validator = vm.addr(validatorPk);
        verifier = _deployVerifier();
        token = new LocalTestToken();
        implementation = address(new RollupV1());
        address[] memory validators = new address[](1);
        validators[0] = validator;
        bytes memory init = abi.encodeCall(
            RollupV1.initialize, (owner, address(token), verifier, prover, validators, REGISTRY_KEY, MESSAGES, NOTE_KIND)
        );
        rollup = RollupV1(address(new TransparentUpgradeableProxy(implementation, proxyAdminOwner, init)));
        token.mintTo(address(rollup), TOKEN_BALANCE);
    }

    function _setRootToFixtureOldRoot() internal {
        vm.prank(owner);
        rollup.setRoot(pis[0]); // normal administrative interface: onlyOwner setRoot(bytes32)
    }

    // ------------------------------------------------------------------ helpers
    function _state() internal view returns (State memory s) {
        s.rootHash = rollup.rootHash();
        s.blockHeight = rollup.blockHeight();
        (s.mint0Kind, s.mint0Amount, s.mint0Spent) = rollup.mints(bytes32(0));
        s.balRollup = token.balanceOf(address(rollup));
        s.balProver = token.balanceOf(prover);
        s.balOwner = token.balanceOf(owner);
        (s.registryVerifier, s.registryMessages) = rollup.getZkVerifier(REGISTRY_KEY);
    }

    function _assertSame(State memory a, State memory b) internal pure {
        assertEq(a.rootHash, b.rootHash, "rootHash changed");
        assertEq(a.blockHeight, b.blockHeight, "blockHeight changed");
        assertEq(a.mint0Amount, b.mint0Amount, "mints[0].amount changed");
        assertEq(a.mint0Spent, b.mint0Spent, "mints[0].spent changed");
        assertEq(a.balRollup, b.balRollup, "rollup token balance changed");
        assertEq(a.balProver, b.balProver, "prover token balance changed");
        assertEq(a.balOwner, b.balOwner, "owner token balance changed");
        assertEq(a.registryVerifier, b.registryVerifier, "registry entry changed");
        assertEq(uint256(a.registryMessages), uint256(b.registryMessages), "registry messages_length changed");
    }

    function _sigs(bytes32 newRoot) internal view returns (Signature[] memory sigs) {
        // the digest the consumer itself defines (public pure helper), signed with the owned validator key
        bytes32 digest = rollup.debugGetSignatureMessageHash(newRoot, HEIGHT, OTHER_HASH);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(validatorPk, digest);
        sigs = new Signature[](1);
        sigs[0] = Signature({r: r, s: s, v: uint256(v)});
    }

    function _copy(bytes32[] storage src) internal view returns (bytes32[] memory out) {
        out = new bytes32[](src.length);
        for (uint256 i = 0; i < src.length; i++) out[i] = src[i];
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

    function _submit(bytes32[] memory inputs) internal returns (Result memory r) {
        bytes memory data = abi.encodeCall(
            RollupV1.verifyRollup, (HEIGHT, REGISTRY_KEY, proof, inputs, OTHER_HASH, _sigs(pis[1]))
        );
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

    function _reason(bytes memory ret) internal pure returns (string memory) {
        if (ret.length >= 4 && bytes4(ret) == bytes4(keccak256("Error(string)"))) {
            bytes memory body = new bytes(ret.length - 4);
            for (uint256 i = 0; i < body.length; i++) body[i] = ret[i + 4];
            return abi.decode(body, (string));
        }
        if (ret.length >= 4) {
            bytes4 sel = bytes4(ret);
            if (sel == bytes4(keccak256("SumcheckFailed()"))) return "verifier custom error SumcheckFailed()";
            if (sel == bytes4(keccak256("ShpleminiFailed()"))) return "verifier custom error ShpleminiFailed()";
            return string.concat("custom error selector 0x", vm.toString(bytes32(sel)));
        }
        return "empty revert data";
    }

    function _observe(string memory name, Result memory r, State memory pre, State memory post) internal {
        string memory head = string.concat(
            '{"schema":"bindcheck.consumer-observation/v0-compact","name":"', name, '","revision":"dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36",',
            '"consumerProxy":"', vm.toString(address(rollup)), '","implementation":"', vm.toString(implementation),
            '","verifier":"', vm.toString(verifier), '","registryKey":"', vm.toString(REGISTRY_KEY), '",'
        );
        string memory call_ = string.concat(
            '"call":{"entry":"verifyRollup","height":"', vm.toString(HEIGHT), '","caller":"prover","proofSha256":"', vm.toString(sha256(proof)),
            '","publicInputsCount":"', vm.toString(pis.length), '","publicInputsSha256":"', vm.toString(PI_SHA256),
            '","messagesNonzero":"', vm.toString(_nonzeroMessages(pis)), '","signatures":"1"},'
        );
        string memory outcome = string.concat(
            '"status":"', r.ok ? "success" : "reverted", '","reason":"', r.ok ? "" : _reason(r.ret), '","gasUsed":"', vm.toString(r.gasUsed),
            '","verifierCall":{"observed":', r.verifierCalled ? "true" : "false", ',"calldataEqualsExpected":', r.verifierCallExact ? "true" : "false",
            ',"revertedInScope":', r.verifierCallRevertedInScope ? "true" : "false", '},"logsFromConsumer":"', vm.toString(_consumerLogs(r.logs)), '",'
        );
        vm.writeFile(
            string.concat("results/raw/T12/observations/", name, ".json"),
            string.concat(head, call_, outcome, '"pre":', _stateJson(pre), ',"post":', _stateJson(post), "}")
        );
    }

    function _stateJson(State memory s) internal pure returns (string memory) {
        return string.concat(
            '{"rootHash":"', vm.toString(s.rootHash), '","blockHeight":"', vm.toString(s.blockHeight), '","mint0":{"amount":"',
            vm.toString(s.mint0Amount), '","spent":', s.mint0Spent ? "true" : "false", '},"tokenBalances":{"rollup":"', vm.toString(s.balRollup),
            '","prover":"', vm.toString(s.balProver), '","owner":"', vm.toString(s.balOwner), '"}}'
        );
    }

    function _nonzeroMessages(bytes32[] memory p) internal pure returns (uint256 n) {
        for (uint256 i = 3; i < p.length; i++) if (p[i] != bytes32(0)) n++;
    }

    function _consumerLogs(VmSafe.Log[] memory logs) internal view returns (uint256 n) {
        for (uint256 i = 0; i < logs.length; i++) if (logs[i].emitter == address(rollup)) n++;
    }

    // ------------------------------------------------------------------ the settlement
    function test_settlement_zeroMessageProofThroughActualConsumer() public {
        vm.createDir("results/raw/T12/observations", true);
        _setRootToFixtureOldRoot();
        State memory pre = _state();
        assertEq(pre.rootHash, pis[0], "stored root must equal the fixture's old root before the call");
        assertEq(pre.blockHeight, 0);
        assertEq(pre.registryVerifier, verifier);
        assertEq(uint256(pre.registryMessages), uint256(MESSAGES));

        Result memory r = _submit(_copy(pis));
        State memory post = _state();

        assertTrue(r.ok, string.concat("settlement reverted: ", _reason(r.ret)));
        // the consumer called the intended REAL verifier with exactly (proof, publicInputs)
        assertTrue(r.verifierCalled, "verifier was not called");
        assertTrue(r.verifierCallExact, "verifier calldata != abi.encodeCall(verify, (proof, publicInputs))");
        assertFalse(r.verifierCallRevertedInScope);
        // root advances from the fixture's old root to its new root; source-defined bookkeeping: blockHeight = height
        assertEq(post.rootHash, pis[1], "root did not advance to the fixture's new root");
        assertTrue(pre.rootHash != post.rootHash);
        assertEq(post.blockHeight, HEIGHT);
        // zero messages => no mint/burn dispatch, no token transfer, mints[0] untouched, registry untouched
        assertEq(_nonzeroMessages(pis), 0);
        assertEq(post.balRollup, pre.balRollup);
        assertEq(post.balProver, pre.balProver);
        assertEq(post.balOwner, pre.balOwner);
        assertEq(post.mint0Amount, pre.mint0Amount);
        assertEq(post.mint0Spent, pre.mint0Spent);
        assertEq(post.registryVerifier, pre.registryVerifier);
        // exactly one consumer log: RollupVerified(height, newRoot); no Minted / Burned / token events
        assertEq(_consumerLogs(r.logs), 1, "expected exactly one consumer event");
        assertEq(r.logs.length, 1, "no other emitter (token) may log");
        VmSafe.Log memory l = r.logs[0];
        assertEq(l.topics[0], keccak256("RollupVerified(uint256,bytes32)"));
        assertEq(uint256(l.topics[1]), HEIGHT);
        assertEq(abi.decode(l.data, (bytes32)), pis[1]);
        _observe("settlement_zero_message", r, pre, post);
    }

    // Control 1: messages[0] changed 0 -> 1 (public-input index 3), original proof kept.
    function test_control_messages0_to_1_originalProof() public {
        vm.createDir("results/raw/T12/observations", true);
        _setRootToFixtureOldRoot();
        State memory pre = _state();
        bytes32[] memory bad = _copy(pis);
        bad[3] = bytes32(uint256(1));
        Result memory r = _submit(bad);
        State memory post = _state();
        assertFalse(r.ok, "altered input must be rejected");
        _assertSame(pre, post);
        // Which check fired is observed, not assumed: kind 1 is not a valid message kind, so the consumer's own parser rejects
        // BEFORE the verifier is reached. This control therefore does NOT exercise the verifier.
        assertEq(_reason(r.ret), "RollupV1: Invalid message kind");
        assertFalse(r.verifierCalled, "verifier unexpectedly reached");
        _observe("control_messages0_to_1", r, pre, post);
    }

    // Additional control (not requested): messages[0] = 2 is a syntactically valid zero-valued mint record (kind 2, hash 0), so it
    // passes the consumer's parser and reaches the REAL verifier, which rejects it; the revert also rolls back mints[0].spent.
    function test_additionalControl_messages0_to_2_reachesVerifier() public {
        vm.createDir("results/raw/T12/observations", true);
        _setRootToFixtureOldRoot();
        State memory pre = _state();
        bytes32[] memory bad = _copy(pis);
        bad[3] = bytes32(uint256(2));
        Result memory r = _submit(bad);
        State memory post = _state();
        assertFalse(r.ok);
        _assertSame(pre, post);
        assertTrue(r.verifierCalled, "this variant should reach the verifier");
        assertTrue(r.verifierCallExact);
        assertTrue(r.verifierCallRevertedInScope);
        _observe("additional_control_messages0_to_2", r, pre, post);
    }

    // Control 2: valid proof against an incompatible stored root (fresh deployment; root left at initialize's empty-tree root).
    function test_control_incompatibleStoredRoot() public {
        vm.createDir("results/raw/T12/observations", true);
        State memory pre = _state();
        assertEq(pre.rootHash, EMPTY_TREE_ROOT);
        assertTrue(pre.rootHash != pis[0]);
        Result memory r = _submit(_copy(pis));
        State memory post = _state();
        assertFalse(r.ok);
        _assertSame(pre, post);
        assertEq(_reason(r.ret), "RollupV1: Root hash verification failed");
        assertFalse(r.verifierCalled, "verifier unexpectedly reached");
        _observe("control_incompatible_root", r, pre, post);
    }
}
