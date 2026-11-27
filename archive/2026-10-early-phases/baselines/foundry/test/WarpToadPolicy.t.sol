// SPDX-License-Identifier: MIT
pragma solidity 0.8.29;

import {Test} from "forge-std/Test.sol";
import {Vm} from "forge-std/Vm.sol";
import {WarpToadCore, IVerifier} from "../contracts/core/WarpToadCore.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract GigaProviderStub {
    uint256 public gigaRoot = 0x111;
}

contract RelationalVerifierStub is IVerifier {
    bytes32[11] internal expected;
    bytes32 internal expectedProofHash;
    bool internal rejectAll;

    function configure(bytes memory proof, bytes32[11] memory words, bool reject) external {
        expectedProofHash = keccak256(proof);
        expected = words;
        rejectAll = reject;
    }

    function verify(bytes calldata proof, bytes32[] calldata words) external view returns (bool) {
        if (rejectAll || keccak256(proof) != expectedProofHash || words.length != 11) return false;
        for (uint256 i; i < 11; ++i) if (words[i] != expected[i]) return false;
        return true;
    }
}

contract WarpToadHarness is WarpToadCore {
    constructor(address verifier) WarpToadCore(16, verifier, address(0)) ERC20("WarpToad test", "WTT") {}
}

contract WarpToadPolicyHandler {
    Vm internal constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));
    bytes32 internal constant TRANSFER_TOPIC = keccak256("Transfer(address,address,uint256)");
    struct MintCaseArgs { uint256 n; uint256 amount; uint256 giga; uint256 local; address recipient; bytes proof; }
    WarpToadHarness public immutable token;
    RelationalVerifierStub public immutable verifier;
    uint256 public immutable admittedGigaRoot;
    uint256 public immutable admittedLocalRoot;
    uint256 public immutable admittedAztecAddress;

    bool public amountOrBeneficiaryMismatch;
    bool public unadmittedRootAccepted;
    bool public replayAccepted;
    bool public rollbackFailure;
    bool public verifierGateFailure;
    bool public validCallRejected;
    bool public supplyAccountingFailure;

    constructor(WarpToadHarness t, RelationalVerifierStub v, uint256 giga, uint256 local, uint256 aztec) {
        token = t; verifier = v; admittedGigaRoot = giga; admittedLocalRoot = local;
        admittedAztecAddress = aztec;
    }

    function words(uint256 n, uint256 amount, uint256 giga, uint256 local,
                   uint256 feeFactor, uint256 priorityFee, uint256 maxFee,
                   address relayer, address recipient) internal view returns (bytes32[11] memory w) {
        w[0]=bytes32(n); w[1]=bytes32(block.chainid); w[2]=bytes32(amount); w[3]=bytes32(giga);
        w[4]=bytes32(local); w[5]=bytes32(admittedAztecAddress); w[6]=bytes32(feeFactor);
        w[7]=bytes32(priorityFee); w[8]=bytes32(maxFee);
        w[9]=bytes32(uint256(uint160(relayer))); w[10]=bytes32(uint256(uint160(recipient)));
    }

    function mintCase(uint256 n, uint128 amount, bytes calldata proof, uint8 rootMode) external {
        MintCaseArgs memory c = MintCaseArgs({n:n, amount:amount,
            giga: rootMode & 1 == 0 ? admittedGigaRoot : (n | (1 << 255)),
            local: rootMode & 2 == 0 ? admittedLocalRoot : (n | (1 << 254)),
            recipient: address(0xBEEF), proof: proof});
        _runMintCase(c);
    }

    function _runMintCase(MintCaseArgs memory c) internal {
        bool gigaWasAdmitted = token.isValidGigaRoot(c.giga);
        bool localWasAdmitted = token.isValidLocalRoot(c.local);
        bool alreadySpent = token.nullifiers(c.n);
        verifier.configure(c.proof, words(c.n, c.amount, c.giga, c.local, 0, 0, 0, address(0), c.recipient), false);
        uint256 beforeRecipient = token.balanceOf(c.recipient);
        uint256 beforeSupply = token.totalSupply();
        bool ok = _callMint(c);
        if (ok) {
            if (!gigaWasAdmitted || !localWasAdmitted) unadmittedRootAccepted = true;
            if (token.balanceOf(c.recipient)-beforeRecipient != c.amount || token.totalSupply()-beforeSupply != c.amount)
                amountOrBeneficiaryMismatch = true;
            bool replayOk = _callMint(c);
            if (replayOk) replayAccepted = true;
        } else {
            if (!alreadySpent && gigaWasAdmitted && localWasAdmitted) validCallRejected = true;
            if (token.nullifiers(c.n) != alreadySpent || token.balanceOf(c.recipient) != beforeRecipient ||
                token.totalSupply() != beforeSupply) rollbackFailure = true;
        }
    }

    function _callMint(MintCaseArgs memory c) internal returns (bool ok) {
        ok = _callAndCheckSupply(abi.encodeCall(token.mint,
            (c.n, c.amount, c.giga, c.local, 0, 0, 0, address(0), c.recipient, c.proof)));
    }

    function feeBeneficiaryCase(uint256 n) external {
        if (token.nullifiers(n)) return;
        bytes memory proof = hex"02";
        verifier.configure(proof, words(n, 3, admittedGigaRoot, admittedLocalRoot,
            1, 1, 1, address(0xCAFE), address(0xBEEF)), false);
        uint256 rb = token.balanceOf(address(0xCAFE));
        uint256 pb = token.balanceOf(address(0xBEEF));
        bool ok = _callFeeMint(n, proof);
        if (!ok) { validCallRejected = true; return; }
        if (token.balanceOf(address(0xCAFE))-rb != 1 || token.balanceOf(address(0xBEEF))-pb != 2)
            amountOrBeneficiaryMismatch = true;
    }

    function _callFeeMint(uint256 n, bytes memory proof) internal returns (bool ok) {
        ok = _callAndCheckSupply(abi.encodeCall(token.mint,
            (n, 3, admittedGigaRoot, admittedLocalRoot, 1, 1, 1, address(0xCAFE), address(0xBEEF), proof)));
    }

    function rejectedProofMustNotMint(uint256 n) external {
        if (token.nullifiers(n)) return;
        uint256 amount = 1;
        address recipient = address(0xBEEF);
        bytes memory proof = hex"01";
        verifier.configure(proof, words(n, amount, admittedGigaRoot, admittedLocalRoot, 0, 0, 0, address(0), recipient), true);
        bool ok = _callAndCheckSupply(abi.encodeCall(token.mint,
            (n, amount, admittedGigaRoot, admittedLocalRoot, 0, 0, 0, address(0), recipient, proof)));
        if (ok) verifierGateFailure = true;
    }

    // Arbitrary ABI tails exercise decoder rejection and rollback through the same stub boundary.
    function submitArbitraryMintCalldata(bytes calldata abiTail) external {
        bytes memory callData = bytes.concat(WarpToadCore.mint.selector, abiTail);
        uint256 supplyBefore = token.totalSupply();
        bool ok = _callAndCheckSupply(callData);
        if (!ok && token.totalSupply() != supplyBefore) rollbackFailure = true;
    }

    function _callAndCheckSupply(bytes memory callData) internal returns (bool ok) {
        uint256 supplyBefore = token.totalSupply();
        vm.recordLogs();
        (ok,) = address(token).call(callData);
        Vm.Log[] memory logs = vm.getRecordedLogs();
        uint256 minted;
        uint256 burned;
        for (uint256 i; i < logs.length; ++i) {
            if (logs[i].emitter != address(token) || logs[i].topics.length != 3 ||
                logs[i].topics[0] != TRANSFER_TOPIC) continue;
            address from = address(uint160(uint256(logs[i].topics[1])));
            address to = address(uint160(uint256(logs[i].topics[2])));
            uint256 value = abi.decode(logs[i].data, (uint256));
            if (from == address(0)) minted += value;
            if (to == address(0)) burned += value;
        }
        if (supplyBefore + minted < burned || token.totalSupply() != supplyBefore + minted - burned)
            supplyAccountingFailure = true;
    }
}

contract WarpToadPolicyInvariant is Test {
    WarpToadPolicyHandler internal handler;

    function setUp() public {
        RelationalVerifierStub verifier = new RelationalVerifierStub();
        WarpToadHarness token = new WarpToadHarness(address(verifier));
        GigaProviderStub provider = new GigaProviderStub();
        uint256 aztec = 0xA22EC;
        token.initialize(address(provider), address(0xB1), aztec);
        handler = new WarpToadPolicyHandler(token, verifier, provider.gigaRoot(), token.localRoot(), aztec);
        targetContract(address(handler));
    }

    function invariant_amount_and_beneficiary_bound() public view { assertFalse(handler.amountOrBeneficiaryMismatch()); }
    function invariant_roots_are_admitted() public view { assertFalse(handler.unadmittedRootAccepted()); }
    function invariant_nullifier_single_use() public view { assertFalse(handler.replayAccepted()); }
    function invariant_reverts_roll_back() public view { assertFalse(handler.rollbackFailure()); }
    function invariant_verifier_gates_mint() public view { assertFalse(handler.verifierGateFailure()); }
    function invariant_valid_relation_is_accepted() public view { assertFalse(handler.validCallRejected()); }
    function invariant_supply_matches_transfer_events() public view { assertFalse(handler.supplyAccountingFailure()); }
}
