// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Synthetic controls for the BindCheck execution oracle. Owned, local-only,
// test tokens of no value. These contracts isolate one binding behaviour each
// so the oracle's operators can be checked against a known-good answer. The
// verifiers are deliberately trivial stand-ins: synthetic controls test the
// consumer's binding logic and the oracle's judgement, not a real proof system.

uint256 constant FIELD_R =
    21888242871839275222246405745257275088548364400416034343698204186575808495617;

interface IVerifier {
    function verifyProof(
        uint256[2] calldata a,
        uint256[2][2] calldata b,
        uint256[2] calldata c,
        uint256[] calldata pub
    ) external view returns (bool);
}

/// Accepts any proof but enforces canonical public inputs (pub[i] < r), like a
/// verifier that range-checks its field elements.
contract CanonicalVerifier is IVerifier {
    function verifyProof(
        uint256[2] calldata,
        uint256[2][2] calldata,
        uint256[2] calldata,
        uint256[] calldata pub
    ) external pure returns (bool) {
        for (uint256 i = 0; i < pub.length; i++) {
            require(pub[i] < FIELD_R, "non-canonical public input");
        }
        return true;
    }
}

/// Accepts any proof with no canonical range check, so pub and pub+r are both
/// accepted. Models a verifier missing the canonicality guard.
contract PermissiveVerifier is IVerifier {
    function verifyProof(
        uint256[2] calldata,
        uint256[2][2] calldata,
        uint256[2] calldata,
        uint256[] calldata
    ) external pure returns (bool) {
        return true;
    }
}

/// Minimal mintable token. Transfer(from=0) marks a mint the oracle observes.
contract MintToken {
    string public name = "Synthetic";
    string public symbol = "SYN";
    mapping(address => uint256) public balanceOf;
    event Transfer(address indexed from, address indexed to, uint256 value);

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
        emit Transfer(address(0), to, amount);
    }
}

/// Correctly bound: recipient is bound to the proof's public input, the
/// nullifier is canonical and single-use. No operator should confirm.
contract BoundConsumer {
    IVerifier public verifier;
    MintToken public token;
    mapping(bytes32 => bool) public spent;
    uint256 public constant AMOUNT = 1000;

    constructor(IVerifier v, MintToken t) {
        verifier = v;
        token = t;
    }

    function claim(
        uint256[2] calldata a,
        uint256[2][2] calldata b,
        uint256[2] calldata c,
        uint256[] calldata pub,
        address recipient
    ) external {
        require(verifier.verifyProof(a, b, c, pub), "proof");
        bytes32 nullifier = bytes32(pub[0]);
        require(!spent[nullifier], "spent");
        spent[nullifier] = true;
        require(recipient == address(uint160(pub[1])), "recipient not bound to proof");
        token.mint(recipient, AMOUNT);
    }
}

/// Raw-keyed nullifier behind a non-canonical verifier: the nullifier set is
/// keyed on the raw integer pub[0], so pub[0] and pub[0]+r are distinct keys.
/// ALIAS should confirm a double spend of one logical authorization.
contract AliasConsumer {
    IVerifier public verifier; // permissive (no canonical check)
    MintToken public token;
    mapping(uint256 => bool) public spent; // raw-integer key
    uint256 public constant AMOUNT = 1000;

    constructor(IVerifier v, MintToken t) {
        verifier = v;
        token = t;
    }

    function claim(
        uint256[2] calldata a,
        uint256[2][2] calldata b,
        uint256[2] calldata c,
        uint256[] calldata pub,
        address recipient
    ) external {
        require(verifier.verifyProof(a, b, c, pub), "proof");
        uint256 key = pub[0]; // raw, not reduced mod r
        require(!spent[key], "spent");
        spent[key] = true;
        token.mint(recipient, AMOUNT);
    }
}

/// Missing spent write: the nullifier is read but never recorded, so the same
/// proof can mint repeatedly. REPLAY should confirm a double spend.
contract ReplayConsumer {
    IVerifier public verifier; // canonical
    MintToken public token;
    uint256 public constant AMOUNT = 1000;

    constructor(IVerifier v, MintToken t) {
        verifier = v;
        token = t;
    }

    function claim(
        uint256[2] calldata a,
        uint256[2][2] calldata b,
        uint256[2] calldata c,
        uint256[] calldata pub,
        address recipient
    ) external {
        require(verifier.verifyProof(a, b, c, pub), "proof");
        // nullifier intentionally never recorded: no replay guard.
        token.mint(recipient, AMOUNT);
    }
}

/// Obligation-accounting control (vulnerable). An honest claim both mints the
/// reward (the benefit, effect A) and pays the required fee to the treasury (the
/// obligation, effect B). The fee is gated by a free `skipFee` flag that is NOT
/// bound to the proof, so a claim can mint the reward while omitting the fee:
/// the benefit is granted without the required obligation being discharged. A
/// canonical verifier and a proper single-use nullifier guard isolate this from
/// alias/replay, so FREE_ARG(skipFee) is the only operator that should confirm.
contract ObligationConsumerVulnerable {
    IVerifier public verifier; // canonical
    MintToken public reward;
    MintToken public fee;
    address public treasury;
    mapping(bytes32 => bool) public spent;
    uint256 public constant AMOUNT = 1000;
    uint256 public constant FEE = 50;

    constructor(IVerifier v, MintToken r, MintToken f, address t) {
        verifier = v;
        reward = r;
        fee = f;
        treasury = t;
    }

    function claim(
        uint256[2] calldata a,
        uint256[2][2] calldata b,
        uint256[2] calldata c,
        uint256[] calldata pub,
        address recipient,
        bool skipFee
    ) external {
        require(verifier.verifyProof(a, b, c, pub), "proof");
        bytes32 nullifier = bytes32(pub[0]);
        require(!spent[nullifier], "spent");
        spent[nullifier] = true;
        reward.mint(recipient, AMOUNT); // effect A: the benefit
        if (!skipFee) {
            fee.mint(treasury, FEE); // effect B: the required obligation
        }
    }
}

/// Obligation-accounting control (bound). Identical to the vulnerable consumer
/// but the fee obligation is always discharged, ignoring the free flag. No
/// operator should confirm.
contract ObligationConsumerFixed {
    IVerifier public verifier; // canonical
    MintToken public reward;
    MintToken public fee;
    address public treasury;
    mapping(bytes32 => bool) public spent;
    uint256 public constant AMOUNT = 1000;
    uint256 public constant FEE = 50;

    constructor(IVerifier v, MintToken r, MintToken f, address t) {
        verifier = v;
        reward = r;
        fee = f;
        treasury = t;
    }

    function claim(
        uint256[2] calldata a,
        uint256[2][2] calldata b,
        uint256[2] calldata c,
        uint256[] calldata pub,
        address recipient,
        bool // skipFee is accepted but ignored: the obligation is unconditional
    ) external {
        require(verifier.verifyProof(a, b, c, pub), "proof");
        bytes32 nullifier = bytes32(pub[0]);
        require(!spent[nullifier], "spent");
        spent[nullifier] = true;
        reward.mint(recipient, AMOUNT); // effect A: the benefit
        fee.mint(treasury, FEE); // effect B: always discharged
    }
}
