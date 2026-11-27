// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {VmSafe} from "forge-std/Vm.sol";
import {RollupV1, Signature} from "../src/rollup3/RollupV1.sol";
import {IVerifier} from "../src/noir/IVerifier.sol";
import {TransparentUpgradeableProxy} from "@openzeppelin/contracts/proxy/transparent/TransparentUpgradeableProxy.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract ObligationTestToken is ERC20 {
    constructor() ERC20("Local test token", "LTT") {}

    function mintTo(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

/// THE DIRECT PROPERTY (plain Solidity, written from the circuit / Rust / consumer SOURCE; no BindCheck code or verdict logic).
///
/// Plain language. For one call of RollupV1.verifyRollup with public inputs P = [old_root, new_root, commit_hash, messages[1000]]:
///   (1) If the call is REJECTED, every protected value is exactly as before (root, height, each watched mint entry, all token balances).
///   (2) If the call is ACCEPTED:
///       a. the stored root was P.old_root and becomes P.new_root, and the height strictly increases to the submitted height;
///       b. for EVERY mint record (kind 2) decoded from P.messages with identity h, note kind k and value v:
///            - before the call a registration existed: mints[h] = (k, v, unspent)   [identity, kind and value all match]
///            - after the call it is spent and its kind and amount are unchanged     [one-time consumption]
///            - the consumer's token balance covers the sum of consumed values       [backing is held]
///       c. no mint entry other than those named in P.messages changed;
///       d. no token moved (settlement releases nothing: the escrow stays);
///       e. no identity is consumed twice by the same call.
///   (3) With no mint record in P, (2b) is vacuous and (2c) says no watched mint entry changes.
/// The decoder below re-implements the message grammar from noir/agg_agg (kind 2 = 4 words, kind 3 = 5 words), noir/agg_utxo and
/// pkg/zk-primitives/src/utxo.rs `messages()` ([2, note_kind, value, mint_hash, 0]); it does not call the consumer.
abstract contract MintProperty is Test {
    uint256 constant W = 3; // number of watched mint identities

    struct Snap {
        bytes32 root;
        uint256 height;
        bytes32[W] kind;
        uint256[W] amount;
        bool[W] spent;
        uint256 balConsumer;
        uint256 balMinter;
        uint256 balProver;
        uint256 balOwner;
    }

    struct MintMsg {
        bytes32 hash;
        bytes32 noteKind;
        uint256 value;
    }

    /// Decodes messages from public inputs (index 3 on). `supported` is false on a burn/unknown kind (outside this property).
    function decodeMints(bytes32[] memory p) internal pure returns (MintMsg[] memory out, bool supported) {
        uint256 n;
        uint256 i = 3;
        supported = true;
        while (i < p.length) {
            uint256 k = uint256(p[i]);
            if (k == 0) i += 1;
            else if (k == 2) { n++; i += 4; }
            else { supported = false; break; }
        }
        out = new MintMsg[](n);
        i = 3;
        uint256 j;
        while (i < p.length && supported) {
            uint256 k = uint256(p[i]);
            if (k == 0) i += 1;
            else { out[j++] = MintMsg({noteKind: p[i + 1], value: uint256(p[i + 2]), hash: p[i + 3]}); i += 4; }
        }
    }

    /// Memory structs are references in Solidity; hand-built snapshots must be deep-copied.
    function cp(Snap memory s) internal pure returns (Snap memory c) {
        c.root = s.root; c.height = s.height; c.balConsumer = s.balConsumer; c.balMinter = s.balMinter; c.balProver = s.balProver; c.balOwner = s.balOwner;
        for (uint256 i = 0; i < W; i++) { c.kind[i] = s.kind[i]; c.amount[i] = s.amount[i]; c.spent[i] = s.spent[i]; }
    }

    function same(Snap memory a, Snap memory b) internal pure returns (bool) {
        if (a.root != b.root || a.height != b.height) return false;
        if (a.balConsumer != b.balConsumer || a.balMinter != b.balMinter || a.balProver != b.balProver || a.balOwner != b.balOwner) return false;
        for (uint256 i = 0; i < W; i++) if (a.kind[i] != b.kind[i] || a.amount[i] != b.amount[i] || a.spent[i] != b.spent[i]) return false;
        return true;
    }

    function slot(bytes32[W] memory watched, bytes32 h) internal pure returns (uint256 idx, bool found) {
        for (uint256 i = 0; i < W; i++) if (watched[i] == h) return (i, true);
        return (0, false);
    }

    function property(bool accepted, Snap memory pre, Snap memory post, bytes32[] memory p, uint256 submittedHeight, bytes32[W] memory watched)
        internal
        pure
        returns (bool ok, string memory why)
    {
        if (!accepted) return same(pre, post) ? (true, "rejected: state unchanged") : (false, "rejected call changed protected state");
        if (pre.root != p[0]) return (false, "accepted although stored root != old_root");
        if (post.root != p[1]) return (false, "root did not advance to new_root");
        if (!(post.height == submittedHeight && post.height > pre.height)) return (false, "height not advanced to submitted height");
        if (post.balConsumer != pre.balConsumer || post.balMinter != pre.balMinter || post.balProver != pre.balProver || post.balOwner != pre.balOwner) {
            return (false, "tokens moved at settlement");
        }
        (MintMsg[] memory msgs, bool supported) = decodeMints(p);
        if (!supported) return (false, "unsupported message kind (outside this property)");
        bool[W] memory consumed;
        uint256 sum;
        for (uint256 m = 0; m < msgs.length; m++) {
            (uint256 s, bool found) = slot(watched, msgs[m].hash);
            if (!found) return (false, "decoded mint identity is not a watched identity (test setup)");
            if (consumed[s]) return (false, "identity consumed twice by one call");
            consumed[s] = true;
            if (pre.amount[s] != msgs[m].value || pre.kind[s] != msgs[m].noteKind) return (false, "accepted a mint without a registration matching identity, kind and value");
            if (pre.spent[s]) return (false, "accepted a mint that was already spent");
            if (!post.spent[s]) return (false, "mint not consumed (spent flag not set)");
            if (post.amount[s] != pre.amount[s] || post.kind[s] != pre.kind[s]) return (false, "registration changed");
            sum += msgs[m].value;
        }
        if (pre.balConsumer < sum) return (false, "consumer holds less than the consumed mint values");
        for (uint256 i = 0; i < W; i++) {
            if (!consumed[i] && (post.kind[i] != pre.kind[i] || post.amount[i] != pre.amount[i] || post.spent[i] != pre.spent[i])) {
                return (false, "a mint entry not named in the messages changed");
            }
        }
        return (true, msgs.length == 0 ? "accepted: no mint obligation, no mint entry changed" : "accepted: every mint record matched a registration and was consumed");
    }
}

/// T14. Local testbed only; the real consumer behind a TransparentUpgradeableProxy and the real Honk verifier, as in T12/T13.
/// Not a vulnerability claim, not advisory reproduction, not BindCheck.
contract MintObligationTest is MintProperty {
    bytes32 constant REGISTRY_KEY = 0x0701c58cb73e870b8da74294bb1a820e346546e4d3cdca393aa84d3716d3787c;
    uint32 constant MESSAGES = 1000;
    bytes32 constant OTHER_HASH = keccak256("T14 otherHashFromBlockHash (local, arbitrary)");
    uint256 constant HEIGHT = 1;
    uint256 constant PI_FIELDS = 1003;
    uint256 constant MINTER_FUNDS = 1000;

    address owner = makeAddr("owner");
    address prover = makeAddr("prover");
    address proxyAdminOwner = makeAddr("proxyAdminOwner");
    address minter = makeAddr("minter");
    uint256 validatorPk = uint256(keccak256("T14 validator private key (local test key)"));

    ObligationTestToken token;
    address verifier;
    address implementation;
    RollupV1 rollup;

    bytes mintProof;
    bytes32[] mintPis;
    bytes zeroProof;
    bytes32[] zeroPis;
    bytes32 noteKind;
    bytes32 mintHash;
    uint256 mintValue;
    bytes32[W] watched;

    struct Result {
        bool ok;
        bytes ret;
        uint256 gasUsed;
        bool verifierCalled;
        bool verifierCallExact;
        bool verifierCallRevertedInScope;
        uint256 consumerLogs;
        bytes32 firstLogTopic;
    }

    // ------------------------------------------------------------------ deployment (T12/T13 pattern)
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
        uint256 at = vm.parseJsonUint(refs, "$['agg_final.sol'].ZKTranscriptLib[0].start") * 2;
        require(vm.parseJsonUint(refs, "$['agg_final.sol'].ZKTranscriptLib[0].length") == 20, "unexpected link length");
        require(txt[at] == "_" && txt[at + 1] == "_" && txt[at + 2] == "$" && txt[at + 37] == "$" && txt[at + 38] == "_" && txt[at + 39] == "_", "no placeholder");
        bytes memory libHex = bytes(vm.toString(lib));
        for (uint256 i = 0; i < 40; i++) txt[at + i] = libHex[2 + i];
        return _create(vm.parseBytes(string.concat("0x", string(txt))));
    }

    function _loadPis(string memory path) internal view returns (bytes32[] memory out, bytes memory raw) {
        raw = vm.readFileBinary(path);
        require(raw.length == PI_FIELDS * 32, "public input length");
        out = new bytes32[](PI_FIELDS);
        for (uint256 i = 0; i < PI_FIELDS; i++) {
            bytes32 w;
            assembly { w := mload(add(add(raw, 32), mul(i, 32))) }
            out[i] = w;
        }
    }

    function setUp() public {
        // T13 mint proof and T10 zero-message proof, both checked against their recorded hashes
        mintProof = vm.readFileBinary("results/raw/T13/agg_final_mint/proof");
        zeroProof = vm.readFileBinary("results/raw/T10/agg_final_new/proof");
        (bytes32[] memory a, bytes memory rawA) = _loadPis("results/raw/T13/agg_final_mint/public_inputs");
        (bytes32[] memory b, bytes memory rawB) = _loadPis("results/raw/T10/agg_final_new/public_inputs");
        string memory s13 = vm.readFile("results/raw/T13/40_proof_summary.json");
        string memory s10 = vm.readFile("results/raw/T10/90_summary.json");
        assertEq(vm.toString(sha256(mintProof)), string.concat("0x", vm.parseJsonString(s13, "$.agg_final_proof.proof_sha256")), "T13 proof hash");
        assertEq(vm.toString(sha256(rawA)), string.concat("0x", vm.parseJsonString(s13, "$.agg_final_proof.public_inputs_sha256")), "T13 public inputs hash");
        assertEq(vm.toString(sha256(zeroProof)), string.concat("0x", vm.parseJsonString(s10, "$.agg_final_proof.proof_sha256")), "T10 proof hash");
        assertEq(vm.toString(sha256(rawB)), string.concat("0x", vm.parseJsonString(s10, "$.agg_final_proof.public_inputs_sha256")), "T10 public inputs hash");
        for (uint256 i = 0; i < PI_FIELDS; i++) { mintPis.push(a[i]); zeroPis.push(b[i]); }

        (MintMsg[] memory msgs, bool ok) = decodeMints(a);
        require(ok && msgs.length == 1, "T13 proof must carry exactly one mint record");
        noteKind = msgs[0].noteKind; mintValue = msgs[0].value; mintHash = msgs[0].hash;
        (MintMsg[] memory none, bool ok0) = decodeMints(b);
        require(ok0 && none.length == 0, "T10 proof must carry no message");
        watched = [mintHash, bytes32(uint256(mintHash) ^ 1), bytes32(0)];

        verifier = _deployVerifier();
        token = new ObligationTestToken();
        implementation = address(new RollupV1());
        address[] memory validators = new address[](1);
        validators[0] = vm.addr(validatorPk);
        bytes memory init = abi.encodeCall(RollupV1.initialize, (owner, address(token), verifier, prover, validators, REGISTRY_KEY, MESSAGES, noteKind));
        rollup = RollupV1(address(new TransparentUpgradeableProxy(implementation, proxyAdminOwner, init)));
        token.mintTo(minter, MINTER_FUNDS);
    }

    // ------------------------------------------------------------------ helpers
    function _snap() internal view returns (Snap memory s) {
        s.root = rollup.rootHash();
        s.height = rollup.blockHeight();
        for (uint256 i = 0; i < W; i++) (s.kind[i], s.amount[i], s.spent[i]) = rollup.mints(watched[i]);
        s.balConsumer = token.balanceOf(address(rollup));
        s.balMinter = token.balanceOf(minter);
        s.balProver = token.balanceOf(prover);
        s.balOwner = token.balanceOf(owner);
    }

    function _register(bytes32 h, uint256 value) internal {
        vm.prank(minter);
        token.approve(address(rollup), value);
        vm.prank(minter);
        rollup.mint(h, bytes32(value), noteKind); // normal public interface
    }

    function _copy(bytes32[] storage src) internal view returns (bytes32[] memory out) {
        out = new bytes32[](src.length);
        for (uint256 i = 0; i < src.length; i++) out[i] = src[i];
    }

    function _submit(bytes memory proof, bytes32[] memory inputs) internal returns (Result memory r) {
        bytes32 newRoot = inputs[1];
        bytes32 digest = rollup.debugGetSignatureMessageHash(newRoot, HEIGHT, OTHER_HASH);
        (uint8 v, bytes32 rr, bytes32 ss) = vm.sign(validatorPk, digest);
        Signature[] memory sigs = new Signature[](1);
        sigs[0] = Signature({r: rr, s: ss, v: uint256(v)});
        bytes memory data = abi.encodeCall(RollupV1.verifyRollup, (HEIGHT, REGISTRY_KEY, proof, inputs, OTHER_HASH, sigs));
        bytes memory expected = abi.encodeCall(IVerifier.verify, (proof, inputs));
        vm.recordLogs();
        vm.startStateDiffRecording();
        vm.prank(prover);
        uint256 g = gasleft();
        (r.ok, r.ret) = address(rollup).call(data);
        r.gasUsed = g - gasleft();
        VmSafe.AccountAccess[] memory acc = vm.stopAndReturnStateDiff();
        VmSafe.Log[] memory logs = vm.getRecordedLogs();
        for (uint256 i = 0; i < acc.length; i++) {
            bool isCall = acc[i].kind == VmSafe.AccountAccessKind.Call || acc[i].kind == VmSafe.AccountAccessKind.StaticCall;
            if (isCall && acc[i].account == verifier && acc[i].accessor == address(rollup)) {
                r.verifierCalled = true;
                r.verifierCallExact = keccak256(acc[i].data) == keccak256(expected);
                r.verifierCallRevertedInScope = acc[i].reverted;
            }
        }
        for (uint256 i = 0; i < logs.length; i++) if (logs[i].emitter == address(rollup)) r.consumerLogs++;
        if (logs.length > 0) r.firstLogTopic = logs[0].topics[0];
    }

    function _reason(bytes memory ret) internal view returns (string memory) {
        if (ret.length >= 4 && bytes4(ret) == bytes4(keccak256("Error(string)"))) {
            bytes memory body = new bytes(ret.length - 4);
            for (uint256 i = 0; i < body.length; i++) body[i] = ret[i + 4];
            return abi.decode(body, (string));
        }
        if (ret.length >= 4 && bytes4(ret) == bytes4(keccak256("SumcheckFailed()"))) return "verifier custom error SumcheckFailed()";
        return ret.length >= 4 ? string.concat("custom error selector ", vm.toString(bytes32(bytes4(ret)))) : "empty revert data";
    }

    function _stateJson(Snap memory s) internal view returns (string memory) {
        return string.concat(
            '{"root":"', vm.toString(s.root), '","height":"', vm.toString(s.height), '","mint":{"kind":"', vm.toString(s.kind[0]), '","amount":"', vm.toString(s.amount[0]),
            '","spent":', s.spent[0] ? "true" : "false", '},"consumerTokens":"', vm.toString(s.balConsumer), '","minterTokens":"', vm.toString(s.balMinter), '"}'
        );
    }

    function _record(string memory name, string memory desc, Result memory r, Snap memory pre, Snap memory post, bool propHolds, string memory why) internal {
        vm.createDir("results/raw/T14/observations", true);
        vm.writeFile(
            string.concat("results/raw/T14/observations/", name, ".json"),
            string.concat(
                '{"case":"', name, '","description":"', desc, '","status":"', r.ok ? "success" : "reverted", '","rejectingCheck":"', r.ok ? "" : _reason(r.ret),
                '","verifierReached":', r.verifierCalled ? "true" : "false", ',"verifierCalldataExact":', r.verifierCallExact ? "true" : "false", ',"verifierRevertedInScope":',
                r.verifierCallRevertedInScope ? "true" : "false", ',"gas":"', vm.toString(r.gasUsed), '","consumerEvents":"', vm.toString(r.consumerLogs), '","propertyHolds":',
                propHolds ? "true" : "false", ',"propertyWhy":"', why, '","pre":', _stateJson(pre), ',"post":', _stateJson(post), "}"
            )
        );
    }

    function _check(string memory name, string memory desc, Result memory r, Snap memory pre, Snap memory post, bytes32[] memory p) internal {
        (bool holds, string memory why) = property(r.ok, pre, post, p, HEIGHT, watched);
        _record(name, desc, r, pre, post, holds, why);
        assertTrue(holds, why);
    }

    // ------------------------------------------------------------------ the five cases
    // Case 1: matching registration + original valid mint proof -> intended successful transition.
    function test_case1_matchingRegistration_originalProof() public {
        _register(mintHash, mintValue);
        Snap memory pre = _snap();
        bytes32[] memory p = _copy(mintPis);
        Result memory r = _submit(mintProof, p);
        Snap memory post = _snap();
        assertTrue(r.ok, _reason(r.ret));
        assertTrue(r.verifierCalled && r.verifierCallExact && !r.verifierCallRevertedInScope);
        assertTrue(!pre.spent[0] && post.spent[0]);
        assertEq(post.root, mintPis[1]);
        _check("case1_matching_registration", "matching registration (100) + original T13 mint proof", r, pre, post, p);
    }

    // Case 2: no matching registration, original proof.
    function test_case2_noRegistration_originalProof() public {
        Snap memory pre = _snap();
        bytes32[] memory p = _copy(mintPis);
        Result memory r = _submit(mintProof, p);
        Snap memory post = _snap();
        assertFalse(r.ok);
        assertEq(_reason(r.ret), "RollupV1: Mint value invalid");
        assertFalse(r.verifierCalled);
        _check("case2_no_registration", "no registration + original T13 mint proof", r, pre, post, p);
    }

    // Case 3: registration for the same message identity with the wrong value (101), original proof.
    function test_case3_wrongValueRegistration_originalProof() public {
        _register(mintHash, mintValue + 1);
        Snap memory pre = _snap();
        bytes32[] memory p = _copy(mintPis);
        Result memory r = _submit(mintProof, p);
        Snap memory post = _snap();
        assertFalse(r.ok);
        assertEq(_reason(r.ret), "RollupV1: Mint value invalid");
        assertFalse(r.verifierCalled);
        _check("case3_wrong_value_registration", "registration for the same identity with value 101 + original T13 mint proof", r, pre, post, p);
    }

    // Case 4: original registration (100), changed public message value (101), original proof reused.
    function test_case4_originalRegistration_changedPublicValue() public {
        _register(mintHash, mintValue);
        Snap memory pre = _snap();
        bytes32[] memory p = _copy(mintPis);
        p[5] = bytes32(mintValue + 1); // public-input index 5 = messages[2] = mint value
        Result memory r = _submit(mintProof, p);
        Snap memory post = _snap();
        assertFalse(r.ok);
        assertEq(_reason(r.ret), "RollupV1: Mint value invalid");
        assertFalse(r.verifierCalled);
        _check("case4_changed_public_value", "original registration (100) + public value changed to 101, original proof reused", r, pre, post, p);
    }

    // Additional reference (not one of the five): changed value AND a matching 101 registration, so the registration check passes and
    // only the verifier can reject. Shows the registration check runs before the verifier, and that the verifier is the backstop.
    function test_case4b_changedPublicValue_matchingChangedRegistration_reachesVerifier() public {
        _register(mintHash, mintValue + 1);
        Snap memory pre = _snap();
        bytes32[] memory p = _copy(mintPis);
        p[5] = bytes32(mintValue + 1);
        Result memory r = _submit(mintProof, p);
        Snap memory post = _snap();
        assertFalse(r.ok);
        assertTrue(r.verifierCalled && r.verifierCallExact && r.verifierCallRevertedInScope);
        _check("case4b_changed_value_matching_registration", "public value 101 + a matching 101 registration, original proof reused (reference)", r, pre, post, p);
    }

    // Case 5: the zero-message T10 proof as a control, no mint registration. Its old_root is not the consumer's initial root (T10's
    // synthetic tree already held notes), so the owner aligns the stored root with the normal setRoot, exactly as in T12.
    function test_case5_zeroMessageProof_noRegistration() public {
        vm.prank(owner);
        rollup.setRoot(zeroPis[0]);
        Snap memory pre = _snap();
        bytes32[] memory p = _copy(zeroPis);
        Result memory r = _submit(zeroProof, p);
        Snap memory post = _snap();
        assertTrue(r.ok, _reason(r.ret));
        assertTrue(r.verifierCalled && r.verifierCallExact);
        assertEq(post.root, zeroPis[1]);
        assertEq(r.consumerLogs, 1); // only RollupVerified: no Minted
        _check("case5_zero_message_control", "zero-message T10 proof, no mint registration (root aligned by owner setRoot)", r, pre, post, p);
    }

    // ------------------------------------------------------------------ self-check of the direct property on HAND-BUILT snapshots
    // (not executions): the property must be able to say "no".
    function _base() internal view returns (Snap memory pre, Snap memory post, bytes32[] memory p) {
        p = _copy(mintPis);
        pre.root = p[0]; pre.height = 0; pre.kind[0] = noteKind; pre.amount[0] = mintValue; pre.balConsumer = mintValue; pre.balMinter = 900;
        post = cp(pre);
        post.root = p[1]; post.height = HEIGHT; post.spent[0] = true;
    }

    function test_propertySelfCheck_handBuiltSnapshots() public view {
        (Snap memory pre, Snap memory post, bytes32[] memory p) = _base();
        bool ok;
        (ok,) = property(true, pre, post, p, HEIGHT, watched);
        assertTrue(ok, "intended transition must satisfy the property");

        Snap memory x = cp(post); x.spent[0] = false;                      // accepted but not consumed
        (ok,) = property(true, pre, x, p, HEIGHT, watched); assertFalse(ok, "unconsumed");
        Snap memory y = cp(pre); y.amount[0] = mintValue + 1;              // accepted with a registration of the wrong value
        (ok,) = property(true, y, post, p, HEIGHT, watched); assertFalse(ok, "wrong-value registration");
        y = cp(pre); y.amount[0] = 0; y.kind[0] = bytes32(0);              // accepted with no registration
        (ok,) = property(true, y, post, p, HEIGHT, watched); assertFalse(ok, "no registration");
        y = cp(pre); y.spent[0] = true;                                    // accepted although already spent
        (ok,) = property(true, y, post, p, HEIGHT, watched); assertFalse(ok, "already spent");
        x = cp(post); x.balConsumer = 0;                                   // escrow released at settlement
        (ok,) = property(true, pre, x, p, HEIGHT, watched); assertFalse(ok, "escrow released");
        x = cp(post); x.amount[1] = 7;                                     // an unrelated mint entry changed
        (ok,) = property(true, pre, x, p, HEIGHT, watched); assertFalse(ok, "unrelated entry changed");
        x = cp(post); x.root = bytes32(uint256(1));                        // root not the proof's new root
        (ok,) = property(true, pre, x, p, HEIGHT, watched); assertFalse(ok, "root");
        x = cp(pre); x.root = bytes32(uint256(2));                         // rejected call that changed state
        (ok,) = property(false, pre, x, p, HEIGHT, watched); assertFalse(ok, "rejected but changed");
        (ok,) = property(false, pre, cp(pre), p, HEIGHT, watched); assertTrue(ok, "rejected and unchanged is fine");
        // zero-message block: no mint entry may change; no change is fine
        bytes32[] memory z = _copy(zeroPis);
        Snap memory zp = cp(pre); zp.root = z[0];
        Snap memory zq = cp(zp); zq.root = z[1]; zq.height = HEIGHT;
        (ok,) = property(true, zp, zq, z, HEIGHT, watched); assertTrue(ok, "zero-message no-change is fine");
        zq.spent[0] = true;
        (ok,) = property(true, zp, zq, z, HEIGHT, watched); assertFalse(ok, "zero-message block must not consume a mint");
    }
}
