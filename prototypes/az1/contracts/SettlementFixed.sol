// SPDX-License-Identifier: MIT
pragma solidity 0.8.11;

import "./Groth16Verifier.sol";
import "./TestToken.sol";

interface IPoseidon3 {
    function poseidon(uint256[3] memory input) external pure returns (uint256);
}

interface IPoseidon4 {
    function poseidon(uint256[4] memory input) external pure returns (uint256);
}

/// @notice AZ1 synthetic detector fixture, FIXED variant. Owned, local-only.
/// Same circuit, verifier and proofs as SettlementFaulty. The fix: every row the
/// proof covers but settlement skips (index >= numRealRows) must be a proved no-op,
/// so the settled extent and the proved extent carry the same effects.
contract SettlementFixed {
    uint256 public constant N = 4;

    Groth16Verifier public immutable verifier;
    TestToken public immutable token;
    IPoseidon3 public immutable poseidon3;
    IPoseidon4 public immutable poseidon4;

    mapping(address => uint256) public userPendingDeposits;
    uint256 public totalL2Credit;   // proof-attested credit (the "L2 state" effect)
    uint256 public settledBacking;  // credit backed by consumed pending deposits

    constructor(Groth16Verifier _verifier, TestToken _token, IPoseidon3 _p3, IPoseidon4 _p4) {
        verifier = _verifier;
        token = _token;
        poseidon3 = _p3;
        poseidon4 = _p4;
    }

    /// @notice Stage 1: move test tokens in and record a pending deposit.
    function depositPendingFunds(uint256 amount) external {
        require(token.transferFrom(msg.sender, address(this), amount), "transfer");
        userPendingDeposits[msg.sender] += amount;
    }

    /// @notice Stage 2: accept a batch proof and settle its rows.
    function processBatch(
        uint256[2] calldata a,
        uint256[2][2] calldata b,
        uint256[2] calldata c,
        uint256 creditTotal,
        uint256[N] calldata kinds,
        uint256[N] calldata owners,
        uint256[N] calldata amounts,
        uint256 numRealRows
    ) external {
        require(numRealRows <= N, "numRealRows");
        uint256 commitment = _commitment(kinds, owners, amounts);
        require(verifier.verifyProof(a, b, c, [commitment, creditTotal]), "proof");

        totalL2Credit += creditTotal;

        for (uint256 i = numRealRows; i < N; i++) {
            require(kinds[i] == 0 && amounts[i] == 0, "unsettled row");
        }

        for (uint256 i = 0; i < numRealRows; i++) {
            if (kinds[i] == 1) {
                address owner = address(uint160(owners[i]));
                userPendingDeposits[owner] -= amounts[i];
                settledBacking += amounts[i];
            }
        }
    }

    function unbackedCredit() external view returns (uint256) {
        return totalL2Credit - settledBacking;
    }

    function _commitment(
        uint256[N] calldata kinds,
        uint256[N] calldata owners,
        uint256[N] calldata amounts
    ) internal view returns (uint256) {
        uint256[4] memory rowHashes;
        for (uint256 i = 0; i < N; i++) {
            rowHashes[i] = poseidon3.poseidon([kinds[i], owners[i], amounts[i]]);
        }
        return poseidon4.poseidon(rowHashes);
    }
}
