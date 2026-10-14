// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {VmSafe} from "forge-std/Vm.sol";
import {RollupV1, Signature} from "../src/rollup3/RollupV1.sol";
import {IVerifier} from "../src/noir/IVerifier.sol";
import {TransparentUpgradeableProxy} from "@openzeppelin/contracts/proxy/transparent/TransparentUpgradeableProxy.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// LOCAL TEST TOKEN (test-only, owned by us). Real balance changes are what the assertions check.
contract BurnTestToken is ERC20 {
    constructor() ERC20("Local test token", "LTT") {}

    function mintTo(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

/// T18: does the T16 synthetic burn record produce a token transfer on the EARLIER revision's ACTUAL consumer and ACTUAL verifier?
/// Revision c4d2c9021b8fb9988816eb6987a734b830bfce15 ONLY (matching T15/T16's "A" side). The consumer source
/// (eth/contracts/rollup3/RollupV1.sol) is byte-identical to the later revision (T15); only the agg_final verifier .bin files differ
/// (committed at this revision, build/T18/bins/*) because the agg_agg verification key differs between revisions.
/// Reuses T16's exact control and candidate proof/public-input BYTES: no new proof, no circuit or key change, no storage overwrite,
/// no bypassed check. Local testbed only: owned prover/validator/minter accounts, a local ERC20, Foundry's local EVM.
/// Not advisory reproduction, not a historical-deployment or arbitrary-user-exploit claim: both calls use whitelisted local
/// prover/validator identities we created and control ourselves.
contract BurnPropagationTest is Test {
    // Rust/deploy registry key for the EARLIER revision's agg_final circuit (results/raw/T12/11_hash_derivation.txt: "[c4d2c90] agg_final
    // vk_hash binary -> 0x122d2ac7..."; matches both pkg/contracts/src/rollup.rs and eth/scripts/deploy.ts at that revision). This is
    // NOT the later revision's registry key (0x0701c58c...) used by T12-T14: the two revisions' agg_final keys differ.
    bytes32 constant REGISTRY_KEY = 0x122d2ac7542fa020cbfff0836b5d0c30898330074b19869179bba49b5db69967;
    uint32 constant MESSAGES = 1000;
    bytes32 constant OTHER_HASH = keccak256("T18 otherHashFromBlockHash (local, arbitrary)");
    bytes32 constant CONTRACT_INITIAL_ROOT = 0x0577b5b4aa3eaba75b2a919d5d7c63b7258aa507d38e346bf2ff1d48790379ff;
    uint256 constant HEIGHT = 1;
    uint256 constant PI_FIELDS = 1003;
    // public-input indices (ABI order: old_root, new_root, commit_hash, messages[1000])
    uint256 constant I_MINT_KIND = 3;
    uint256 constant I_MINT_NOTE_KIND = 4;
    uint256 constant I_MINT_VALUE = 5;
    uint256 constant I_MINT_HASH = 6;
    uint256 constant I_BURN_KIND = 7;
    uint256 constant I_BURN_NOTE_KIND = 8;
    uint256 constant I_BURN_VALUE = 9;
    uint256 constant I_BURN_HASH = 10;
    uint256 constant I_BURN_ADDR = 11;
    uint256 constant MINTER_FUNDS = 1000;

    address owner = makeAddr("owner");
    address prover = makeAddr("prover");
    address proxyAdminOwner = makeAddr("proxyAdminOwner");
    address minter = makeAddr("minter");
    uint256 validatorPk = uint256(keccak256("T18 validator private key (local test key)"));
    address validator;

    // Shared across every deployed instance: both are stateless logic (no consumer-specific storage), so sharing them changes
    // nothing about what each proxy instance checks or holds; "same configuration, actual verifier" is satisfied by construction.
    address verifier;
    address implementation;

    bytes controlProof;
    bytes32[] controlPis;
    bytes candidateProof;
    bytes32[] candidatePis;
    bytes32 noteKind;      // shared by both proofs' mint AND burn records (checked equal in setUp)
    bytes32 mintHash;
    uint256 mintValue;
    bytes32 burnHash;
    uint256 burnValue;
    address burnAddr;

    struct Instance {
        RollupV1 rollup;
        BurnTestToken token;
    }

    struct State {
        bytes32 rootHash;
        uint256 blockHeight;
        bytes32 mintKind;
        uint256 mintAmount;
        bool mintSpent;
        uint256 balRollup;
        uint256 balBurnAddr;
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

    // ------------------------------------------------------------------ loading + deployment
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

    // Same linking pattern as T12/T13/T14's _deployVerifier, pointed at the EARLIER revision's own committed .bin files.
    function _deployVerifier() internal returns (address) {
        address lib = _create(vm.parseBytes(string.concat("0x", string(_trimmedText("build/T18/bins/agg_final_ZKTranscriptLib.bin")))));
        bytes memory txt = _trimmedText("build/T18/bins/agg_final_HonkVerifier.bin");
        string memory refs = vm.readFile("build/T18/bins/agg_final_HonkVerifier.linkrefs.json");
        uint256 start = vm.parseJsonUint(refs, "$['agg_final.sol'].ZKTranscriptLib[0].start");
        require(vm.parseJsonUint(refs, "$['agg_final.sol'].ZKTranscriptLib[0].length") == 20, "unexpected link length");
        uint256 at = start * 2;
        require(txt[at] == "_" && txt[at + 1] == "_" && txt[at + 2] == "$" && txt[at + 37] == "$" && txt[at + 38] == "_" && txt[at + 39] == "_", "no placeholder");
        bytes memory libHex = bytes(vm.toString(lib));
        for (uint256 i = 0; i < 40; i++) txt[at + i] = libHex[2 + i];
        return _create(vm.parseBytes(string.concat("0x", string(txt))));
    }

    function _loadPis(string memory proofPath, string memory piPath, string memory summaryPath, string memory field) internal returns (bytes memory proofOut, bytes32[] memory pisOut) {
        proofOut = vm.readFileBinary(proofPath);
        bytes memory raw = vm.readFileBinary(piPath);
        string memory sum = vm.readFile(summaryPath);
        assertEq(vm.toString(sha256(proofOut)), string.concat("0x", vm.parseJsonString(sum, string.concat("$.", field, ".proof_sha256"))), "proof hash differs from the recorded T16 hash");
        assertEq(vm.toString(sha256(raw)), string.concat("0x", vm.parseJsonString(sum, string.concat("$.", field, ".public_inputs_sha256"))), "public inputs hash differs from the recorded T16 hash");
        assertEq(raw.length, PI_FIELDS * 32);
        pisOut = new bytes32[](PI_FIELDS);
        for (uint256 i = 0; i < PI_FIELDS; i++) {
            bytes32 w;
            assembly { w := mload(add(add(raw, 32), mul(i, 32))) }
            pisOut[i] = w;
        }
    }

    function setUp() public {
        (controlProof, controlPis) = _loadPis("results/raw/T16/control/proof", "results/raw/T16/control/public_inputs", "results/raw/T16/40_summary.json", "control");
        (candidateProof, candidatePis) = _loadPis("results/raw/T16/candidate/proof", "results/raw/T16/candidate/public_inputs", "results/raw/T16/40_summary.json", "candidate");

        assertEq(uint256(controlPis[I_MINT_KIND]), 2, "control: message kind must be mint (2)");
        assertEq(uint256(candidatePis[I_MINT_KIND]), 2, "candidate: first message kind must be mint (2)");
        assertEq(uint256(candidatePis[I_BURN_KIND]), 3, "candidate: second message kind must be burn (3)");
        // every field of the control's and the candidate's shared mint record is identical (T16 §2); only indices 7-11 differ.
        for (uint256 i = 0; i <= I_MINT_HASH; i++) assertEq(controlPis[i], candidatePis[i], "control/candidate mint-record fields must match");
        assertEq(controlPis[1], candidatePis[1], "control/candidate new_root must match (T16 finding)");

        noteKind = candidatePis[I_MINT_NOTE_KIND];
        assertEq(noteKind, candidatePis[I_BURN_NOTE_KIND], "mint and burn records share the same note_kind");
        mintHash = candidatePis[I_MINT_HASH];
        mintValue = uint256(candidatePis[I_MINT_VALUE]);
        burnHash = candidatePis[I_BURN_HASH];
        burnValue = uint256(candidatePis[I_BURN_VALUE]);
        burnAddr = address(uint160(uint256(candidatePis[I_BURN_ADDR])));
        assertEq(burnValue, 7, "sanity: T15/T16's synthetic burn value");
        assertEq(burnAddr, 0x000000000000000000000000000000000000dEaD, "sanity: T15/T16's synthetic burn_addr");
        assertTrue(mintValue >= burnValue, "the mint registration this proof requires (100) covers the burn (7): see reports/T18.md limitation");

        validator = vm.addr(validatorPk);
        verifier = _deployVerifier();
        implementation = address(new RollupV1());
    }

    // ------------------------------------------------------------------ one fresh instance, same configuration every time
    function _deployInstance() internal returns (Instance memory inst) {
        inst.token = new BurnTestToken();
        address[] memory validators = new address[](1);
        validators[0] = validator;
        bytes memory init = abi.encodeCall(
            RollupV1.initialize, (owner, address(inst.token), verifier, prover, validators, REGISTRY_KEY, MESSAGES, noteKind)
        );
        inst.rollup = RollupV1(address(new TransparentUpgradeableProxy(implementation, proxyAdminOwner, init)));
    }

    function _state(Instance memory inst) internal view returns (State memory s) {
        s.rootHash = inst.rollup.rootHash();
        s.blockHeight = inst.rollup.blockHeight();
        (s.mintKind, s.mintAmount, s.mintSpent) = inst.rollup.mints(mintHash);
        s.balRollup = inst.token.balanceOf(address(inst.rollup));
        s.balBurnAddr = inst.token.balanceOf(burnAddr);
        s.balProver = inst.token.balanceOf(prover);
        s.balOwner = inst.token.balanceOf(owner);
        (s.registryVerifier,) = inst.rollup.getZkVerifier(REGISTRY_KEY);
    }

    function _assertSame(State memory a, State memory b) internal pure {
        assertEq(a.rootHash, b.rootHash, "rootHash changed");
        assertEq(a.blockHeight, b.blockHeight, "blockHeight changed");
        assertEq(a.mintKind, b.mintKind, "mint note_kind changed");
        assertEq(a.mintAmount, b.mintAmount, "mint amount changed");
        assertEq(a.mintSpent, b.mintSpent, "mint spent flag changed");
        assertEq(a.balRollup, b.balRollup, "rollup balance changed");
        assertEq(a.balBurnAddr, b.balBurnAddr, "burn recipient balance changed");
        assertEq(a.balProver, b.balProver, "prover balance changed");
        assertEq(a.balOwner, b.balOwner, "owner balance changed");
        assertEq(a.registryVerifier, b.registryVerifier, "registry changed");
    }

    // Normal authorized registration: minter approves, then RollupV1.mint(hash, value, noteKind). This is the ONLY documented path
    // that funds a consumer instance while leaving the control/candidate proofs usable unmodified (both require old_root == the
    // consumer's pristine initial root, so no prior settlement may have moved it; see reports/T18.md §"funding").
    function _registerMint(Instance memory inst, uint256 funds) internal returns (uint256 gasUsed, VmSafe.Log[] memory logs) {
        inst.token.mintTo(minter, funds);
        vm.prank(minter);
        inst.token.approve(address(inst.rollup), mintValue);
        vm.recordLogs();
        vm.prank(minter);
        uint256 g = gasleft();
        inst.rollup.mint(mintHash, bytes32(mintValue), noteKind);
        gasUsed = g - gasleft();
        logs = vm.getRecordedLogs();
    }

    function _sigs(Instance memory inst, bytes32 newRoot) internal view returns (Signature[] memory sigs) {
        bytes32 digest = inst.rollup.debugGetSignatureMessageHash(newRoot, HEIGHT, OTHER_HASH);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(validatorPk, digest);
        sigs = new Signature[](1);
        sigs[0] = Signature({r: r, s: s, v: uint256(v)});
    }

    function _submit(Instance memory inst, bytes memory proof, bytes32[] memory inputs) internal returns (Result memory r) {
        bytes memory data = abi.encodeCall(RollupV1.verifyRollup, (HEIGHT, REGISTRY_KEY, proof, inputs, OTHER_HASH, _sigs(inst, inputs[1])));
        bytes memory expectedVerifierCall = abi.encodeCall(IVerifier.verify, (proof, inputs));
        vm.recordLogs();
        vm.startStateDiffRecording();
        vm.prank(prover);
        uint256 g = gasleft();
        (r.ok, r.ret) = address(inst.rollup).call(data);
        r.gasUsed = g - gasleft();
        VmSafe.AccountAccess[] memory acc = vm.stopAndReturnStateDiff();
        r.logs = vm.getRecordedLogs();
        for (uint256 i = 0; i < acc.length; i++) {
            bool isCall = acc[i].kind == VmSafe.AccountAccessKind.Call || acc[i].kind == VmSafe.AccountAccessKind.StaticCall;
            if (isCall && acc[i].account == verifier && acc[i].accessor == address(inst.rollup)) {
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
            if (bytes4(ret) == bytes4(keccak256("SumcheckFailed()"))) return "verifier custom error SumcheckFailed()";
            return string.concat("custom error selector ", vm.toString(bytes32(bytes4(ret))));
        }
        return "empty revert data";
    }

    function _findBurnedEvent(VmSafe.Log[] memory logs) internal pure returns (bool found, bool success, address token, address recipient) {
        bytes32 topic0 = keccak256("Burned(address,bytes32,address,bool,bool)");
        for (uint256 i = 0; i < logs.length; i++) {
            if (logs[i].topics[0] == topic0) {
                found = true;
                token = address(uint160(uint256(logs[i].topics[1])));
                recipient = address(uint160(uint256(logs[i].topics[3])));
                (, success) = abi.decode(logs[i].data, (bool, bool));
                return (found, success, token, recipient);
            }
        }
    }

    function _stateJson(State memory s) internal pure returns (string memory) {
        return string.concat(
            '{"rootHash":"', vm.toString(s.rootHash), '","blockHeight":"', vm.toString(s.blockHeight), '","mint":{"noteKind":"', vm.toString(s.mintKind),
            '","amount":"', vm.toString(s.mintAmount), '","spent":', s.mintSpent ? "true" : "false", '},"tokenBalances":{"rollup":"', vm.toString(s.balRollup),
            '","burnAddr":"', vm.toString(s.balBurnAddr), '","prover":"', vm.toString(s.balProver), '","owner":"', vm.toString(s.balOwner), '"}}'
        );
    }

    function _logsJson(address rollup, address token, VmSafe.Log[] memory logs) internal pure returns (string memory out) {
        out = "[";
        for (uint256 i = 0; i < logs.length; i++) {
            out = string.concat(out, i == 0 ? "" : ",", '{"emitter":"', logs[i].emitter == rollup ? "consumer" : (logs[i].emitter == token ? "token" : "other"),
                '","topic0":"', vm.toString(logs[i].topics[0]), '"}');
        }
        out = string.concat(out, "]");
    }

    function _observe(string memory name, Instance memory inst, Result memory r, State memory pre, State memory post) internal {
        vm.createDir("results/raw/T18/observations", true);
        (bool burnedFound, bool burnedSuccess, , ) = _findBurnedEvent(r.logs);
        string memory head = string.concat(
            '{"schema":"bindcheck.consumer-observation/v0-compact","name":"', name, '","revision":"c4d2c9021b8fb9988816eb6987a734b830bfce15","consumerProxy":"',
            vm.toString(address(inst.rollup)), '","verifier":"', vm.toString(verifier), '","registryKey":"', vm.toString(REGISTRY_KEY), '",'
        );
        string memory burnInfo = string.concat(
            '"burnMessage":{"kind":"3","noteKind":"', vm.toString(noteKind), '","value":"', vm.toString(burnValue), '","hash":"', vm.toString(burnHash),
            '","burnAddr":"', vm.toString(burnAddr), '"},'
        );
        string memory outcome = string.concat(
            '"status":"', r.ok ? "success" : "reverted", '","reason":"', r.ok ? "" : _reason(r.ret), '","settlementGas":"', vm.toString(r.gasUsed),
            '","verifierCall":{"observed":', r.verifierCalled ? "true" : "false", ',"calldataEqualsExpected":', r.verifierCallExact ? "true" : "false",
            ',"revertedInScope":', r.verifierCallRevertedInScope ? "true" : "false", '},"burnedEvent":{"found":', burnedFound ? "true" : "false",
            ',"success":', burnedSuccess ? "true" : "false", '},"settlementLogs":', _logsJson(address(inst.rollup), address(inst.token), r.logs),
            r.ok ? "" : ',"settlementLogsNote":"recorder also lists events emitted inside reverted frames; a chain would discard them"', ","
        );
        vm.writeFile(string.concat("results/raw/T18/observations/", name, ".json"), string.concat(head, burnInfo, outcome, '"pre":', _stateJson(pre), ',"post":', _stateJson(post), "}"));
    }

    // ================================================================= 1) baseline: this instance and verifier work at all (T13-equivalent, revision A)
    function test_1_baseline_mintOnlyControl() public {
        Instance memory inst = _deployInstance();
        assertEq(inst.rollup.rootHash(), CONTRACT_INITIAL_ROOT);
        assertEq(controlPis[0], CONTRACT_INITIAL_ROOT, "control's old_root is the consumer's pristine initial root");
        _registerMint(inst, MINTER_FUNDS);
        State memory pre = _state(inst);
        Result memory r = _submit(inst, controlProof, controlPis);
        State memory post = _state(inst);
        assertTrue(r.ok, string.concat("baseline settlement reverted: ", _reason(r.ret)));
        assertTrue(r.verifierCalled && r.verifierCallExact && !r.verifierCallRevertedInScope, "real verifier called with exactly (proof, publicInputs)");
        assertEq(post.rootHash, controlPis[1]);
        assertTrue(post.mintSpent);
        assertEq(post.balRollup, pre.balRollup, "no transfer out: the control has no burn message");
        _observe("1_baseline_mint_only_control", inst, r, pre, post);
    }

    // ================================================================= 2) the actual test: T16 candidate on a funded, freshly deployed instance
    function test_2_candidate_fundedByNormalMintRegistration_burnExecutes() public {
        Instance memory inst = _deployInstance();
        assertEq(candidatePis[0], CONTRACT_INITIAL_ROOT);
        // Funding: the SAME, mandatory mint registration (the candidate's own mint record requires it to settle at all) escrows
        // 100 units into the rollup contract via the normal, documented RollupV1.mint() path -- no separate/artificial funding step.
        _registerMint(inst, MINTER_FUNDS);
        State memory pre = _state(inst);
        assertEq(pre.balRollup, mintValue, "normal mint registration escrowed exactly the mint value, >= the burn value (7)");
        assertEq(pre.balBurnAddr, 0);

        Result memory r = _submit(inst, candidateProof, candidatePis);
        State memory post = _state(inst);

        assertTrue(r.ok, string.concat("candidate settlement reverted: ", _reason(r.ret)));
        assertTrue(r.verifierCalled && r.verifierCallExact && !r.verifierCallRevertedInScope, "real verifier called with exactly (proof, publicInputs)");
        assertEq(post.rootHash, candidatePis[1], "root advanced to the block's new root");
        assertEq(post.blockHeight, HEIGHT);
        assertTrue(post.mintSpent, "the mint record in the same block also settles");

        // Do not infer success from the event alone: check the token's own balanceOf and the Burned event's own `success` field.
        (bool burnedFound, bool burnedSuccess, address evToken, address evRecipient) = _findBurnedEvent(r.logs);
        assertTrue(burnedFound, "a Burned event was emitted");
        assertTrue(burnedSuccess, "Burned.success == true");
        assertEq(evToken, address(inst.token));
        assertEq(evRecipient, burnAddr);
        assertEq(post.balRollup, pre.balRollup - burnValue, "rollup's own balanceOf dropped by exactly the burn value");
        assertEq(post.balBurnAddr, burnValue, "burn_addr's own balanceOf increased by exactly the burn value");

        _observe("2_candidate_funded_burn_executes", inst, r, pre, post);
    }

    // ================================================================= 3) same candidate proof, same configuration, an UNREGISTERED/UNFUNDED instance:
    // reverts at the mint check before the burn is ever reached. This is the zero-new-proof control item 6 asks for; see reports/T18.md
    // for why a "mint registered but balance below the burn's own 7 units" sub-case is NOT reachable without a new proof (the escrow this
    // exact proof requires, 100, always exceeds the burn's 7).
    function test_3_candidate_unregisteredAndUnfunded_revertsBeforeBurn() public {
        Instance memory inst = _deployInstance();
        State memory pre = _state(inst);
        assertEq(pre.mintAmount, 0);
        assertEq(pre.balRollup, 0);
        Result memory r = _submit(inst, candidateProof, candidatePis);
        State memory post = _state(inst);
        assertFalse(r.ok, "no mint registration means no settlement at all");
        _assertSame(pre, post);
        assertEq(_reason(r.ret), "RollupV1: Mint value invalid"); // mints[hash].amount (0) != 100 -- the mint record, processed before the burn record
        assertFalse(r.verifierCalled, "rejected before the verifier; the burn record is never reached");
        _observe("3_candidate_unregistered_unfunded", inst, r, pre, post);
    }

    // ================================================================= 4) atomicity: resubmitting the SAME candidate on an instance where it
    // already settled must revert and leave state unchanged (item 6's "reverted call leaves all relevant state unchanged").
    function test_4_candidate_resubmission_revertsStateUnchanged() public {
        Instance memory inst = _deployInstance();
        _registerMint(inst, MINTER_FUNDS);
        Result memory r1 = _submit(inst, candidateProof, candidatePis);
        assertTrue(r1.ok);
        State memory afterFirst = _state(inst);
        Result memory r2 = _submit(inst, candidateProof, candidatePis); // old_root no longer matches rootHash
        State memory afterSecond = _state(inst);
        assertFalse(r2.ok);
        assertEq(_reason(r2.ret), "RollupV1: Root hash verification failed");
        _assertSame(afterFirst, afterSecond);
        _observe("4_candidate_resubmission_reverts", inst, r2, afterFirst, afterSecond);
    }

    // ================================================================= 5) the signature-coverage fact predicted in reports/T17.md: the
    // validator signature is a pure function of (newRoot, height, otherHash) only. Since the control and candidate share the same
    // newRoot (T16), the SAME (v,r,s) bytes -- computed once, reused verbatim -- authorize submission of EITHER proof.
    function test_5_sameSignatureBytes_authorizeBothProofs() public {
        Instance memory instA = _deployInstance();
        Instance memory instB = _deployInstance();
        _registerMint(instA, MINTER_FUNDS);
        _registerMint(instB, MINTER_FUNDS);
        Signature[] memory sigForControl = _sigs(instA, controlPis[1]);
        Signature[] memory sigForCandidate = _sigs(instB, candidatePis[1]);
        assertEq(sigForControl[0].r, sigForCandidate[0].r);
        assertEq(sigForControl[0].s, sigForCandidate[0].s);
        assertEq(sigForControl[0].v, sigForCandidate[0].v);
        // submit each with the OTHER's freshly computed (but bit-identical) signature, to show the bytes are interchangeable, not just equal
        bytes memory dataA = abi.encodeCall(RollupV1.verifyRollup, (HEIGHT, REGISTRY_KEY, controlProof, controlPis, OTHER_HASH, sigForCandidate));
        bytes memory dataB = abi.encodeCall(RollupV1.verifyRollup, (HEIGHT, REGISTRY_KEY, candidateProof, candidatePis, OTHER_HASH, sigForControl));
        vm.prank(prover);
        (bool okA, ) = address(instA.rollup).call(dataA);
        vm.prank(prover);
        (bool okB, ) = address(instB.rollup).call(dataB);
        assertTrue(okA, "control settles using the signature computed for the candidate's digest");
        assertTrue(okB, "candidate settles using the signature computed for the control's digest");
    }
}
