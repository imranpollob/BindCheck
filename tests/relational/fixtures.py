from __future__ import annotations

import pathlib


def _write(root: pathlib.Path, circom: str, solidity: str) -> None:
    (root / "circuits").mkdir(parents=True)
    (root / "contracts").mkdir(parents=True)
    (root / "circuits" / "Application.circom").write_text(circom, encoding="utf-8")
    (root / "contracts" / "Application.sol").write_text(solidity, encoding="utf-8")


def _extent(root: pathlib.Path, fixture: str) -> None:
    legitimate = fixture.endswith("_legitimate")
    domains = {
        "bridge_withdrawal": ("activeWithdrawalCount", "withdrawals", "authorizedWithdrawals", "releasedBalances"),
        "payroll_batch": ("activeEmployeeCount", "payments", "authorizedPayments", "employeeBalances"),
        "auction_settlement": ("selectedBidCount", "bids", "authorizedBids", "settledBids"),
        "credential_airdrop": ("validRecipientCount", "allocations", "authorizedAllocations", "mintedAllocations"),
    }
    key = next(name for name in domains if name in fixture)
    extent, values, witness, state = domains[key]
    loop_bound = extent if legitimate else "4"
    circom = f"""pragma circom 2.1.0;

template BatchAuthorization() {{
    signal input {extent};
    signal input {values}[4];
    signal input {witness}[4];
    signal input activeSlot[4];

    {extent} === activeSlot[0] + activeSlot[1] + activeSlot[2] + activeSlot[3];
    for (var i = 0; i < 4; i++) {{
        activeSlot[i] * (activeSlot[i] - 1) === 0;
        activeSlot[i] * ({values}[i] - {witness}[i]) === 0;
        if (i < 3) {{
            activeSlot[i + 1] * (1 - activeSlot[i]) === 0;
        }}
    }}
}}

component main {{public [{extent}, {values}, activeSlot]}} = BatchAuthorization();
"""
    vector = ", ".join(
        [extent] + [f"{values}[{index}]" for index in range(4)]
        + [f"activeSlot[{index}]" for index in range(4)]
    )
    solidity = f"""pragma solidity ^0.8.20;

interface IVerifier {{
    function verifyProof(bytes calldata proof, uint256[9] calldata publicInputs) external view returns (bool);
}}

contract BatchSettlement {{
    IVerifier public immutable verifier;
    mapping(address => uint256) public {state};

    constructor(IVerifier verifier_) {{ verifier = verifier_; }}

    function settleBatch(
        bytes calldata proof,
        uint256 {extent},
        uint256[4] calldata {values},
        uint256[4] calldata activeSlot,
        address[4] calldata recipients
    ) external {{
        require(verifier.verifyProof(proof, [{vector}]), "invalid batch proof");
        for (uint256 i = 0; i < {loop_bound}; i++) {{
            {state}[recipients[i]] += {values}[i];
        }}
    }}
}}
"""
    _write(root, circom, solidity)


def _mask(root: pathlib.Path, fixture: str) -> None:
    legitimate = fixture.endswith("_legitimate")
    domains = {
        "identity_disclosure": ("disclosureMask", "attributes", "authenticatedAttributes", "registeredAttributes"),
        "order_settlement": ("selectedOrder", "orders", "authenticatedOrders", "settledOrders"),
        "oracle_update": ("publishedObservation", "observations", "authenticatedObservations", "latestObservations"),
        "ballot_tally": ("enabledContest", "votes", "authenticatedVotes", "contestTallies"),
    }
    key = next(name for name in domains if name in fixture)
    selector, values, witness, state = domains[key]
    guard_open = f"if ({selector}[i] == 1) {{" if legitimate else ""
    guard_close = "}" if legitimate else ""
    circom = f"""pragma circom 2.1.0;

template SelectiveAuthorization() {{
    signal input {selector}[4];
    signal input {values}[4];
    signal input {witness}[4];

    for (var i = 0; i < 4; i++) {{
        {selector}[i] * ({selector}[i] - 1) === 0;
        {selector}[i] * ({values}[i] - {witness}[i]) === 0;
    }}
}}

component main {{public [{selector}, {values}]}} = SelectiveAuthorization();
"""
    vector = ", ".join(
        [f"{selector}[{index}]" for index in range(4)]
        + [f"{values}[{index}]" for index in range(4)]
    )
    solidity = f"""pragma solidity ^0.8.20;

interface IVerifier {{
    function verifyProof(bytes calldata proof, uint256[8] calldata publicInputs) external view returns (bool);
}}

contract SelectiveRegistry {{
    IVerifier public immutable verifier;
    mapping(uint256 => uint256) public {state};

    constructor(IVerifier verifier_) {{ verifier = verifier_; }}

    function applySelection(
        bytes calldata proof,
        uint256[4] calldata {selector},
        uint256[4] calldata {values},
        uint256[4] calldata recordIds
    ) external {{
        require(verifier.verifyProof(proof, [{vector}]), "invalid selection proof");
        for (uint256 i = 0; i < 4; i++) {{
            {guard_open}
                {state}[recordIds[i]] = {values}[i];
            {guard_close}
        }}
    }}
}}
"""
    _write(root, circom, solidity)


def _representation(root: pathlib.Path, fixture: str) -> None:
    legitimate = fixture.endswith("_legitimate")
    domains = {
        "invoice_decimal": ("digits", [1, 10, 100], "decodedAmount"),
        "bridge_limbs": ("amountLimbs", [1, 65536, 4294967296], "withdrawalAmount"),
        "asset_bytes": ("assetBytes", [1, 256, 65536], "assetIdentifier"),
        "permission_bits": ("permissionBits", [1, 2, 4, 8], "permissionValue"),
    }
    key = next(name for name in domains if name in fixture)
    array, weights, decoded = domains[key]
    consumer_weights = weights if legitimate else list(reversed(weights))
    count = len(weights)
    producer_expression = " + ".join(
        f"{array}[{index}]" if weight == 1 else f"{weight} * {array}[{index}]"
        for index, weight in enumerate(weights)
    )
    consumer_expression = " + ".join(
        f"{array}[{index}]" if weight == 1 else f"{weight} * {array}[{index}]"
        for index, weight in enumerate(consumer_weights)
    )
    circom = f"""pragma circom 2.1.0;

template PackedAuthorization() {{
    signal input packedValue;
    signal input {array}[{count}];

    packedValue === {producer_expression};
}}

component main {{public [packedValue, {array}]}} = PackedAuthorization();
"""
    vector = ", ".join(["packedValue"] + [f"{array}[{index}]" for index in range(count)])
    solidity = f"""pragma solidity ^0.8.20;

interface IVerifier {{
    function verifyProof(bytes calldata proof, uint256[{count + 1}] calldata publicInputs) external view returns (bool);
}}

interface IAsset {{ function transfer(address recipient, uint256 amount) external returns (bool); }}

contract EncodedSettlement {{
    IVerifier public immutable verifier;
    IAsset public immutable asset;

    constructor(IVerifier verifier_, IAsset asset_) {{ verifier = verifier_; asset = asset_; }}

    function settleEncoded(
        bytes calldata proof,
        address recipient,
        uint256 packedValue,
        uint256[{count}] calldata {array}
    ) external {{
        require(verifier.verifyProof(proof, [{vector}]), "invalid encoded proof");
        uint256 {decoded} = {consumer_expression};
        require(asset.transfer(recipient, {decoded}), "asset transfer failed");
    }}
}}
"""
    _write(root, circom, solidity)


def _scope(root: pathlib.Path, fixture: str) -> None:
    legitimate = fixture.endswith("_legitimate")
    domains = {
        "campaign_claim": ("campaignId", "claimNullifier", "claimedByCampaign", "claimAmount"),
        "pool_withdrawal": ("poolId", "withdrawalNullifier", "withdrawnByPool", "withdrawalAmount"),
        "ballot_vote": ("ballotId", "voteNullifier", "votesUsedByBallot", "voteWeight"),
        "vault_redemption": ("vaultId", "redemptionNullifier", "redeemedByVault", "redemptionAmount"),
    }
    key = next(name for name in domains if name in fixture)
    scope, nullifier, mapping, amount = domains[key]
    scope_term = f" + 17 * {scope}" if legitimate else ""
    circom = f"""pragma circom 2.1.0;

template ScopedAuthorization() {{
    signal input identity;
    signal input {nullifier};
    signal input {scope};
    signal input nonce;
    signal input {amount};
    signal input authenticatedIdentity;
    signal input authorizedAmount;

    identity === authenticatedIdentity;
    {amount} === authorizedAmount;
    {nullifier} === 31337 * identity + nonce{scope_term};
}}

component main {{public [identity, {nullifier}, {scope}, nonce, {amount}]}} = ScopedAuthorization();
"""
    solidity = f"""pragma solidity ^0.8.20;

interface IVerifier {{
    function verifyProof(bytes calldata proof, uint256[5] calldata publicInputs) external view returns (bool);
}}

interface IToken {{ function transfer(address recipient, uint256 amount) external returns (bool); }}

contract ScopedRedemption {{
    IVerifier public immutable verifier;
    IToken public immutable token;
    mapping(uint256 => mapping(uint256 => bool)) public {mapping};

    constructor(IVerifier verifier_, IToken token_) {{ verifier = verifier_; token = token_; }}

    function redeem(
        bytes calldata proof,
        uint256 identity,
        uint256 {nullifier},
        uint256 {scope},
        uint256 nonce,
        uint256 {amount},
        address recipient
    ) external {{
        require(verifier.verifyProof(proof, [identity, {nullifier}, {scope}, nonce, {amount}]), "invalid authorization");
        require(!{mapping}[{scope}][{nullifier}], "authorization already used");
        {mapping}[{scope}][{nullifier}] = true;
        require(token.transfer(recipient, {amount}), "redemption failed");
    }}
}}
"""
    _write(root, circom, solidity)


def _role(root: pathlib.Path, fixture: str) -> None:
    legitimate = fixture.endswith("_legitimate")
    domains = {
        "owner_recipient": ("owner", "recipient", "authenticatedOwner", "token.transfer({name}, amount);"),
        "source_destination_root": ("sourceRoot", "destinationRoot", "authenticatedSourceRoot", "require({name} == admittedRoot, 'wrong root'); balances[msg.sender] += amount;"),
        "sender_beneficiary": ("sender", "beneficiary", "authenticatedSender", "token.transfer({name}, amount);"),
        "source_destination_domain": ("sourceDomain", "destinationDomain", "authenticatedSourceDomain", "require({name} == configuredDomain, 'wrong domain'); balances[msg.sender] += amount;"),
    }
    key = next(name for name in domains if name in fixture)
    producer_name, wrong_name, private_name, effect_template = domains[key]
    consumer_name = producer_name if legitimate else wrong_name
    effect = effect_template.format(name=consumer_name)
    circom = f"""pragma circom 2.1.0;

template IdentityAuthorization() {{
    signal input {producer_name};
    signal input amount;
    signal input {private_name};
    signal input authorizedAmount;

    {producer_name} === {private_name} * {private_name};
    amount === authorizedAmount * authorizedAmount;
}}

component main {{public [{producer_name}, amount]}} = IdentityAuthorization();
"""
    solidity = f"""pragma solidity ^0.8.20;

interface IVerifier {{
    function verifyProof(bytes calldata proof, uint256[2] calldata publicInputs) external view returns (bool);
}}

interface IToken {{ function transfer(address recipient, uint256 amount) external returns (bool); }}

contract IdentitySettlement {{
    IVerifier public immutable verifier;
    IToken public immutable token;
    uint256 public admittedRoot;
    uint256 public configuredDomain;
    mapping(address => uint256) public balances;

    constructor(IVerifier verifier_, IToken token_) {{ verifier = verifier_; token = token_; }}

    function settle(bytes calldata proof, address owner, address recipient, address sender, address beneficiary,
        uint256 sourceRoot, uint256 destinationRoot, uint256 sourceDomain, uint256 destinationDomain, uint256 amount) external {{
        require(verifier.verifyProof(proof, [{consumer_name}, amount]), "invalid identity proof");
        {effect}
    }}
}}
"""
    _write(root, circom, solidity)


def write_fixture(root: pathlib.Path, fixture: str) -> None:
    if fixture.startswith("extent_"):
        _extent(root, fixture)
    elif fixture.startswith("mask_"):
        _mask(root, fixture)
    elif fixture.startswith("representation_"):
        _representation(root, fixture)
    elif fixture.startswith("scope_"):
        _scope(root, fixture)
    elif fixture.startswith("role_"):
        _role(root, fixture)
    else:
        raise ValueError(f"unknown relational fixture {fixture}")
