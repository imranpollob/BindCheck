#!/usr/bin/env python3
"""B3 binding-mutant generator (TEST data; never share with a tool-building lane).

Each mutant/decoy is ONE fail-closed exact-match edit of a vendored baseline in baselines/<host>/:
the anchor must occur exactly once in the named file, or the whole run aborts.

  python3 make_mutants.py --out DIR      # DIR/<ID>/ = baseline copy + edit; DIR/generation-record.json
  python3 make_mutants.py --write-md     # (re)write mutants/<ID>.md and decoys/<ID>.md from this file
  python3 make_mutants.py --check        # verify every anchor matches exactly once; write nothing

Operators are defined in OPERATORS.md (each cites LABELS-v1 finding IDs).
"""
import argparse, hashlib, json, pathlib, shutil, sys

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE / "baselines"

# Fields: id, host, pattern, side (S consumer/verifier, C circuit, G zkVM guest), op, file, anchor, repl,
#         gt_file, gt_function, unbound, broken, effect, related, notes
M = []
def mut(**k): M.append(dict(kind="mutant", **k))
def decoy(**k): M.append(dict(kind="decoy", pattern="none", **k))

TK = "contracts/TransactionKeeper.sol"; ZC = "circuits/circuit.circom"; ZV = "circuits/verifier.sol"
# ---------------------------------------------------------------- zkerc20 (Circom/Groth16)
mut(id="ZK-C01", host="zkerc20", pattern="P1", side="C", op="OP-C1",
    file=ZC,
    anchor="        // either owner is 0 (salt only auth)\n        // or owner is the sender (owner+salt auth)\n        commitments[i].owner * (sender - commitments[i].owner) === 0;\n",
    repl="",
    gt_file="TransactionKeeper.sol", gt_function="split",
    unbound="spender identity of an owner-locked input note (note owner vs public `sender`)",
    broken="input note's `owner` is no longer constrained to be 0 or the public `sender`",
    effect="ZKERC20.transferFrom -> TransactionKeeper.split nullifies a victim's owner-locked notes and inserts attacker-chosen output commitments (theft of the note's value); same for Node.unlock -> drop",
    related="circuits/circuit.circom Split (input-note loop); TransactionKeeper._checkProof (pub[0]=sender); Node.unlock; ZKERC20.transferFrom",
    notes="Circuit-only edit; verifier.sol unchanged (built from the clean circuit). Exploit needs the note salt, which the note's creator (payer) knows.")
mut(id="ZK-C02", host="zkerc20", pattern="P2", side="C", op="OP-C2",
    file=ZC,
    anchor="        // either the commitment is in the tree\n        // or it represents zero tokens\n        merkleValid[i] <== verifiers[i].root - root;\n        merkleValid[i] * amounts[i] === 0;\n",
    repl="        merkleValid[i] <== verifiers[i].root - root;\n",
    gt_file="TransactionKeeper.sol", gt_function="_checkProof",
    unbound="membership of spent notes in the consumer's stored Merkle root (`MerkleTree.root`)",
    broken="input commitments are no longer required to be in the tree under the public `root`",
    effect="spend notes that were never deposited: split mints value, unlock (Node.unlock -> drop) releases locked ERC-20s",
    related="circuits/circuit.circom Split; TransactionKeeper._checkProof pub[1]=MerkleTree.root; Node.unlock",
    notes="Circuit-only edit; verifier unchanged.")
mut(id="ZK-C03", host="zkerc20", pattern="P3", side="C", op="OP-C3",
    file=ZC, anchor="        commitments[i].nullifier === nullifiers[i];\n", repl="",
    gt_file="TransactionKeeper.sol", gt_function="_checkProof",
    unbound="nullifier (replay key) of each input note",
    broken="public `nullifiers[i]` no longer equal the input note's derived nullifier",
    effect="the same note is spent repeatedly with fresh arbitrary nullifiers; `spent[]` never collides (double spend / unlock drain)",
    related="circuits/circuit.circom Split; TransactionKeeper._checkProof spent[] loop",
    notes="Circuit-only edit; verifier unchanged.")
mut(id="ZK-C04", host="zkerc20", pattern="P1", side="C", op="OP-C1",
    file=ZC, anchor="    left.commitment === leftCommitment;\n", repl="",
    gt_file="TransactionKeeper.sol", gt_function="drop",
    unbound="value of the left output note (public `leftCommitment`)",
    broken="public `leftCommitment` is not tied to (asset, leftAmount, salt, owner) of the conserved split",
    effect="drop/unlock: contract-computed burn commitment for `amount` is accepted regardless of input value -> Node.unlock transfers `amount` ERC-20s; split inserts an arbitrary left note",
    related="circuits/circuit.circom Split (output commitments); TransactionKeeper.split/insert; Node.unlock",
    notes="Circuit-only edit; verifier unchanged.")
mut(id="ZK-S01", host="zkerc20", pattern="P3", side="S", op="OP-R1",
    file=TK, anchor="            spent[nullifiers[i]] = true;\n", repl="",
    gt_file="TransactionKeeper.sol", gt_function="_checkProof",
    unbound="replay key (nullifiers are checked but never recorded)",
    broken="spent-nullifier set is never written",
    effect="the same unlock/transfer proof (or the same notes) is accepted repeatedly; Node.unlock drains the locked ERC-20s",
    related="TransactionKeeper._checkProof; Node.unlock; ZKERC20._burn",
    notes="")
mut(id="ZK-S02", host="zkerc20", pattern="P4", side="S", op="OP-V2",
    file=ZV, anchor="            checkField(calldataload(add(_pubSignals, 128)))\n", repl="",
    gt_file="verifier.sol", gt_function="verifyProof",
    unbound="canonical form of public input 4 (nullifiers[0])",
    broken="verifier no longer range-checks nullifiers[0] < r; the consumer keys `spent[]` on the raw uint",
    effect="nullifiers[0] + k*r verifies as the same statement but is a fresh key in `spent[]` -> double spend / repeated unlock",
    related="TransactionKeeper._checkProof (spent[nullifiers[i]]); Groth16Verifier.verifyProof",
    notes="Verifier is generated (snarkjs 0.7.6) and vendored; edit in the vendored verifier.")
mut(id="ZK-S03", host="zkerc20", pattern="P4", side="S", op="OP-V1",
    file=ZV, anchor="            mstore(0, isValid)\n", repl="            mstore(0, 1)\n",
    gt_file="verifier.sol", gt_function="verifyProof",
    unbound="proof validity (pairing result discarded)",
    broken="verifyProof returns true for any proof with in-field inputs",
    effect="any statement is accepted: arbitrary splits/unlocks drain the Node",
    related="TransactionKeeper._checkProof; TransactionKeeper._verifyInsertProof", notes="")
mut(id="ZK-S04", host="zkerc20", pattern="P5", side="S", op="OP-E1",
    file=TK, anchor="        localIndex = _insert(localCommitment);\n", repl="        localIndex = _insert(remoteCommitment);\n",
    gt_file="TransactionKeeper.sol", gt_function="bridge",
    unbound="which proved output commitment is stored locally (role of public slots left/right)",
    broken="consumer stores the proved remote (left) commitment in the local tree instead of the proved local (right) one",
    effect="the bridged note exists on both chains (local copy + remote message) -> value duplicated",
    related="Node.bridge; BridgeManager._sendMessage; TransactionKeeper._checkProof (left/right order)", notes="")
mut(id="ZK-S05", host="zkerc20", pattern="P5", side="S", op="OP-E1",
    file="contracts/Node.sol",
    anchor="            destChainId,\n            remoteCommitment\n        );\n",
    repl="            destChainId,\n            localCommitment\n        );\n",
    gt_file="Node.sol", gt_function="bridge",
    unbound="which proved output commitment is sent to the destination chain",
    broken="the message carries the proved local commitment instead of the proved remote one",
    effect="the local remainder note is minted on the destination too (duplicated); destination mint not backed by the proved remote output",
    related="TransactionKeeper.bridge; BridgeManager._sendMessage/receiveMessage; Node._receiveMessage", notes="")
decoy(id="ZK-D01", host="zkerc20", side="S", op="DEC-1",
    file=TK, anchor="        require(valid, \"_checkProof: invalid proof\");\n", repl="",
    gt_file="TransactionKeeper.sol", gt_function="_checkProof",
    why_bound="`if (!valid) { return false; }` follows, and every caller wraps _checkProof in require(...)")

# ---------------------------------------------------------------- dark (Noir / UltraHonk)
DT = "circuits/transfer/src/main.nr"
mut(id="DK-C01", host="dark", pattern="P1", side="C", op="OP-C1",
    file=DT, anchor="    assert(multi_scalar_mul([pk_r], [r]) == ct_dr, \"ct.D_recipient != r*pk_recipient\");\n", repl="",
    gt_file="DarkVault.sol", gt_function="transfer",
    unbound="recipient decryption handle ct.D_recipient (hence the amount credited to `to`)",
    broken="D_recipient is not constrained to r*pk_recipient, so the recipient's credited ciphertext is not tied to the debited amount",
    effect="DarkVault.transfer adds an arbitrary handle to the recipient's pending balance; a colluding recipient (key known) can set it so the credit decrypts to any value -> withdraw more USDG than was debited",
    related="circuits/transfer/src/main.nr main; DarkVault._transferInputs (pi[17..18]); DarkVault.applyPending; DarkVault.withdraw",
    notes="Circuit-only edit; committed transfer verifier unchanged.")
mut(id="DK-C02", host="dark", pattern="P2", side="C", op="OP-C4",
    file=DT, anchor="    assert(a <= as_u64(max_transfer), \"a > max_transfer\");\n", repl="",
    gt_file="DarkVault.sol", gt_function="transfer",
    unbound="per-transfer policy cap `max_transfer` (stored `_caps.maxTransfer`)",
    broken="the consumer passes its stored cap as a public input but the circuit no longer enforces a <= max_transfer",
    effect="confidential transfers above the configured cap are accepted (cap policy bypass)",
    related="DarkVault._transferInputs pi[20]; DarkVault.setCaps/tightenCaps", notes="Circuit-only edit.")
mut(id="DK-S01", host="dark", pattern="P4", side="S", op="OP-V3",
    file="circuits/verifiers/withdraw/Verifier.sol",
    anchor="        require(verifyShplemini(p, vk, t), Errors.ShpleminiFailed());\n", repl="",
    gt_file="Verifier.sol", gt_function="verify",
    unbound="proof soundness (PCS opening / final pairing check skipped)",
    broken="the withdraw verifier skips the Shplemini batch-opening check",
    effect="forged withdraw proofs pass; DarkVault.withdraw pays USDG not backed by the encrypted balance",
    related="DarkVault.withdraw; DarkVault._withdrawInputs", notes="Edit in the committed (vendored) bb verifier.")
decoy(id="DK-D01", host="dark", side="S", op="DEC-2",
    file="contracts/src/DarkVault.sol",
    anchor="        a.netInflow = amount >= a.netInflow ? 0 : uint128(a.netInflow - amount);\n        a.nonce += 1;\n",
    repl="        a.netInflow = amount >= a.netInflow ? 0 : uint128(a.netInflow - amount);\n",
    gt_file="DarkVault.sol", gt_function="withdraw",
    why_bound="replay of the same withdraw proof is still rejected: the statement includes the account's available ciphertext, which every withdraw changes (amount >= 1)")

# ---------------------------------------------------------------- davinci (Circom/Groth16)
CM = "solidity/src/CouncilManager.sol"
mut(id="DV-C01", host="davinci", pattern="P1", side="C", op="OP-C1",
    file="circuits/deal.circom", anchor="        masked[i] === u.out[i] * (s[i] + mask[i].out);\n", repl="",
    gt_file="CouncilManager.sol", gt_function="deal",
    unbound="masked share values (public masked[i]) stored for each recipient",
    broken="masked[i] no longer equals s_i + mask_i, so the stored shares are not tied to the Feldman-committed polynomial",
    effect="CouncilManager.deal stores arbitrary masked shares in the recovery record while folding the dealer's commitments into the key; members recover wrong shares (decryption blocked or steered)",
    related="circuits/deal.circom Deal (4); CouncilManager.deal pub[71+i], rec.masked", notes="Circuit-only edit; DealVerifier unchanged.")
mut(id="DV-S01", host="davinci", pattern="P2", side="S", op="OP-X3",
    file=CM, anchor="                CouncilCurve.authenticate(x, y, c.participants[i].compressedX);\n", repl="",
    gt_file="CouncilManager.sol", gt_function="deal",
    unbound="recipient roster keys X_i (rosterKeys calldata)",
    broken="caller-supplied roster keys are no longer authenticated against the stored participants",
    effect="a dealing whose shares are encrypted to attacker-chosen keys is accepted and folded into the ceremony key; the attacker learns other members' shares",
    related="CouncilManager.deal pub[39..70]; CouncilCurve.authenticate; c.participants", notes="")
mut(id="DV-S02", host="davinci", pattern="P3", side="S", op="OP-R1",
    file=CM, anchor="        if (c.qualBitmap & bit != 0) revert AlreadyDealt();\n", repl="",
    gt_file="CouncilManager.sol", gt_function="deal",
    unbound="replay key of a dealing (dealer bit in qualBitmap)",
    broken="a dealer's slot is no longer checked before accepting a dealing",
    effect="anyone can resubmit a signed, proven dealing; its commitments are folded twice and dealtCount over-counts",
    related="CouncilManager.deal (_fold, qualBitmap, dealtCount); CouncilManager.finalize", notes="")
mut(id="DV-S03", host="davinci", pattern="P3", side="S", op="OP-R1",
    file=CM, anchor="        if (r.partialBitmap & bit != 0) revert AlreadyPartial();\n", repl="",
    gt_file="CouncilManager.sol", gt_function="submitPartial",
    unbound="replay key of a partial decryption (member bit in partialBitmap)",
    broken="a member's partial for a request is no longer checked before acceptance",
    effect="a published partial can be resubmitted; per-request partial accounting (_published) over-counts",
    related="CouncilManager.submitPartial; CouncilManager._published; CouncilManager.combine", notes="")
mut(id="DV-S04", host="davinci", pattern="P4", side="S", op="OP-V1",
    file=CM, anchor="        if (!IPartialVerifier(partialVerifier).verifyProof(pA, pB, pC, pub)) revert ProofInvalid();\n",
    repl="        IPartialVerifier(partialVerifier).verifyProof(pA, pB, pC, pub);\n",
    gt_file="CouncilManager.sol", gt_function="submitPartial",
    unbound="partial-decryption proof validity (boolean result ignored)",
    broken="the Groth16 verifier returns false on an invalid proof; the consumer discards the result",
    effect="unproven decryption shares D are accepted and published for combine",
    related="PartialVerifier.verifyProof; CouncilManager.combine", notes="")
mut(id="DV-S05", host="davinci", pattern="P4", side="S", op="OP-V1",
    file="solidity/src/verifiers/DealVerifier.sol", anchor="            mstore(0, isValid)\n", repl="            mstore(0, 1)\n",
    gt_file="DealVerifier.sol", gt_function="verifyProof",
    unbound="dealing proof validity (pairing result discarded)",
    broken="DealVerifier returns true for any in-field input",
    effect="unproven dealings (arbitrary commitments and shares) are folded into the ceremony key",
    related="CouncilManager.deal", notes="Edit in the committed snarkjs verifier.")
decoy(id="DV-D01", host="davinci", side="C", op="DEC-3",
    file="circuits/deal.circom",
    anchor="    pubSq[0] <== ctxHi * ctxHi;\n    pubSq[1] <== ctxLo * ctxLo;\n",
    repl="    pubSq[0] <== 0;\n    pubSq[1] <== 0;\n",
    gt_file="deal.circom", gt_function="Deal",
    why_bound="ctxHi/ctxLo still appear in constraints (Num2Bits(128) range checks and the Poseidon mask inputs), so they keep a non-zero verifier coefficient and stay bound")

# ---------------------------------------------------------------- kakushi (Noir / UltraHonk)
KP = "packages/contracts/src/privacy/KakushiPool.sol"; KC = "packages/zk/circuits/shielded_withdraw/src/main.nr"
NATIVE = "            address(recipient).sendNative(denomination - fee);\n            if (fee > 0) address(relayer).sendNative(fee);\n"
mut(id="KK-C01", host="kakushi", pattern="P3", side="C", op="OP-C3",
    file=KC, anchor="    assert(nullifier_hash_of(nullifier) == nullifier_hash, \"nullifier hash mismatch\");\n", repl="",
    gt_file="KakushiPool.sol", gt_function="_spend",
    unbound="nullifier hash (replay key)", broken="public nullifier_hash is not derived from the note's nullifier",
    effect="one deposit is withdrawn repeatedly under fresh nullifier hashes",
    related="shielded_withdraw main; KakushiPool._spend nullifierHashes; KakushiPool.withdraw", notes="Circuit-only edit; verifier unchanged.")
mut(id="KK-C02", host="kakushi", pattern="P2", side="C", op="OP-C2",
    file=KC, anchor="    assert(compute_root(commitment, path, path_bits) == root, \"commitment not in tree\");\n", repl="",
    gt_file="KakushiPool.sol", gt_function="_spend",
    unbound="membership of the spent commitment in a known pool root",
    broken="the note commitment is no longer proven to be under the public `root`",
    effect="withdraw without a deposit (drains the pool)",
    related="shielded_withdraw main; KakushiPool._spend isKnownRoot", notes="Circuit-only edit; verifier unchanged.")
mut(id="KK-S01", host="kakushi", pattern="P1", side="S", op="OP-P1",
    file=KP, anchor=NATIVE,
    repl="            address(recipient).sendNative(denomination - fee);\n            if (fee > 0) address(msg.sender).sendNative(fee);\n",
    gt_file="KakushiPool.sol", gt_function="withdraw",
    unbound="fee payee (msg.sender instead of the proved relayer)",
    broken="the relayer fee is paid to the transaction sender, not to the relayer in the statement",
    effect="anyone who copies a pending withdraw from the mempool collects the fee",
    related="KakushiPool._publicInputs pi[3]; KakushiPool._spend", notes="")
mut(id="KK-S02", host="kakushi", pattern="P2", side="S", op="OP-X2",
    file=KP,
    anchor="        if (!isKnownRoot(root)) {\n            if (address(rootOracle) == address(0) || !rootOracle.isKnownRoot(address(this), root)) {\n                revert Errors.UnknownRoot(root);\n            }\n        }\n",
    repl="",
    gt_file="KakushiPool.sol", gt_function="_spend",
    unbound="Merkle root (caller-supplied, not checked against stored root history)",
    broken="the proved root is never compared with the pool's roots or the root oracle",
    effect="a proof over an attacker-built tree withdraws `denomination` without a deposit",
    related="KakushiPool.isKnownRoot; IRootOracle.isKnownRoot; KakushiPool.withdraw/withdrawAndCall", notes="")
mut(id="KK-S03", host="kakushi", pattern="P3", side="S", op="OP-R1",
    file=KP, anchor="        nullifierHashes[nullifierHash] = true;\n", repl="",
    gt_file="KakushiPool.sol", gt_function="_spend",
    unbound="replay key (nullifier hash checked but never recorded)", broken="spent set never written",
    effect="the same withdraw proof is accepted again until the pool is drained",
    related="KakushiPool.withdraw; KakushiPool.withdrawAndCall", notes="")
mut(id="KK-S04", host="kakushi", pattern="P1", side="S", op="OP-P2",
    file=KP,
    anchor="        return uint256(keccak256(abi.encode(target, data, refundTo, block.chainid, address(this)))) % FIELD_SIZE;\n",
    repl="        return uint256(keccak256(abi.encode(target, refundTo, block.chainid, address(this)))) % FIELD_SIZE;\n",
    gt_file="KakushiPool.sol", gt_function="withdrawAndCall",
    unbound="private-call calldata `data`", broken="ext_data_hash no longer commits to the call data",
    effect="a front-runner replays the proof with different calldata to the same target (e.g. a payment router paying the attacker)",
    related="KakushiPool.extDataHash; PrivateCallExecutor.execute", notes="Clients must use the contract's extDataHash/callPublicInputs (the honest path does).")
mut(id="KK-S05", host="kakushi", pattern="P5", side="S", op="OP-E2",
    file=KP, anchor=NATIVE,
    repl="            address(relayer).sendNative(denomination - fee);\n            if (fee > 0) address(recipient).sendNative(fee);\n",
    gt_file="KakushiPool.sol", gt_function="withdraw",
    unbound="role of proved addresses (recipient vs relayer) in the payout",
    broken="the consumer pays the principal to the proved relayer and the fee to the proved recipient",
    effect="the relayer named in the proof receives denomination - fee", related="KakushiPool._publicInputs pi[2], pi[3]", notes="")
mut(id="KK-S06", host="kakushi", pattern="P4", side="S", op="OP-V1",
    file=KP,
    anchor="        // the bb verifiers revert (rather than return false) on most failures: normalise both\n",
    repl="", gt_file="KakushiPool.sol", gt_function="_spend",
    unbound="proof validity (verifier revert swallowed)", broken="(set below)", effect="(set below)", related="", notes="")
mut(id="KK-S07", host="kakushi", pattern="P1", side="S", op="OP-P1",
    file=KP, anchor="                (bool ok,) = recipient.call{value: refund}(\"\");\n",
    repl="                (bool ok,) = payable(msg.sender).call{value: refund}(\"\");\n",
    gt_file="KakushiPool.sol", gt_function="withdraw",
    unbound="refund payee (msg.sender instead of the proved recipient)",
    broken="the native refund is sent to the transaction sender, not the recipient in the statement",
    effect="ERC-20 withdraw with refund > 0: the submitting relayer gets back the native refund it is paid (via the proved fee) to deliver to the recipient; the proved recipient receives no refund",
    related="KakushiPool._publicInputs pi[5]; KakushiPool._spend (msg.value == refund)", notes="Weaker than KK-S01: the refund is funded by msg.value of the submitting transaction, so the loss is the recipient's prepaid gas top-up.")
mut(id="KK-S08", host="kakushi", pattern="P5", side="S", op="OP-E2",
    file=KP,
    anchor="            if (fee > 0) token.safeTransfer(relayer, fee);\n            token.safeTransfer(address(executor), amount);\n",
    repl="            if (fee > 0) token.safeTransfer(address(executor), fee);\n            token.safeTransfer(relayer, amount);\n",
    gt_file="KakushiPool.sol", gt_function="withdrawAndCall",
    unbound="role of proved payees (relayer vs executor) in the ERC-20 private call",
    broken="the principal goes to the proved relayer and only the fee to the executor",
    effect="the relayer named in the proof receives denomination - fee; the private call runs on the fee",
    related="KakushiPool._spend; PrivateCallExecutor.execute", notes="")
decoy(id="KK-D01", host="kakushi", side="C", op="DEC-4",
    file=KC, anchor="    recipient.assert_max_bit_size::<160>();\n", repl="",
    gt_file="main.nr", gt_function="main",
    why_bound="recipient is still a public input of the committed UltraHonk verifier (bound by the transcript), and the consumer always passes a uint160 address")

# ---------------------------------------------------------------- xchain (RISC Zero / Steel)
CN = "smart-contracts/src/connectors/Connector.sol"; AD = "smart-contracts/src/zk-proof/adapters/RiscZeroAdapter.sol"
mut(id="XC-G01", host="xchain", pattern="P2", side="G", op="OP-G1",
    file="zk-proofs/risc_zero/non_accept_event/core/src/lib.rs",
    anchor="    if block_timestamp < ack_deadline {\n        return Err(NonAcceptValidationError::TooEarly {\n            ack_deadline,\n            block_timestamp,\n        });\n    }\n",
    repl="",
    gt_file="Connector.sol", gt_function="submitNonAcceptanceProof",
    unbound="the destination block the non-acceptance observation is taken at (may predate ackDeadline)",
    broken="guest no longer requires the observed destination block to be at/after ackDeadline",
    effect="a refund on the origin is proven from a destination state before the lock could be accepted; the destination can still accept and later pay -> same deposit released twice",
    related="non_accept_event guest main.rs; Connector.submitNonAcceptanceProof (refund); Connector.submitLockProof",
    notes="Guest-side edit in the core crate (compiled natively with cargo check). Disjoint from KB-1 (anchor of the remote state).")
mut(id="XC-G02", host="xchain", pattern="P5", side="G", op="OP-G2",
    file="zk-proofs/risc_zero/lock_event/core/src/lib.rs", anchor="        receiver: event.receiver,\n", repl="        receiver: event.sender,\n",
    gt_file="Connector.sol", gt_function="submitLockProof",
    unbound="receiver field of the lock journal (encoded from the wrong event field)",
    broken="the guest commits the depositor in the receiver slot",
    effect="the destination records `to` = depositor and later pays the depositor, not the receiver named in DepositLocked",
    related="lock_event guest main.rs; Connector._submitLockProofImpl; _expectedDestinationLockCommitment; submitAckProof",
    notes="Guest-side edit in the core crate.")
mut(id="XC-S01", host="xchain", pattern="P1", side="S", op="OP-P1",
    file=CN, anchor="        IERC20(tx_.currencyTo).safeTransfer(tx_.to, tx_.amount);\n",
    repl="        IERC20(tx_.currencyTo).safeTransfer(msg.sender, tx_.amount);\n",
    gt_file="Connector.sol", gt_function="submitAckProof",
    unbound="payout recipient (msg.sender instead of the stored, proved receiver)",
    broken="release pays the (permissionless) proof submitter",
    effect="whoever submits the ack proof first takes the bridged tokens", related="Connector._recordDestinationLockTx", notes="")
mut(id="XC-S02", host="xchain", pattern="P3", side="S", op="OP-R1",
    file=CN,
    anchor="        // proof is safe to submit at any time after MINTED_IN_HOLDING is reached.\n        _cleanupTx(_txId);\n",
    repl="        // proof is safe to submit at any time after MINTED_IN_HOLDING is reached.\n",
    gt_file="Connector.sol", gt_function="submitAckProof",
    unbound="replay key of the ack (tx status not consumed)", broken="the transfer record/status is not cleared on release",
    effect="the same ack proof releases tx_.amount repeatedly", related="Connector._cleanupTx; requireStatus(MINTED_IN_HOLDING)", notes="")
mut(id="XC-S03", host="xchain", pattern="P5", side="S", op="OP-E2",
    file=CN, anchor="            from: _from,\n            to: _to,\n", repl="            from: _to,\n            to: _from,\n",
    gt_file="Connector.sol", gt_function="_recordDestinationLockTx",
    unbound="role of proved addresses (sender vs receiver) in the stored transfer",
    broken="the proved receiver is stored as `from` and the proved sender as `to`",
    effect="submitAckProof later pays the depositor instead of the receiver",
    related="Connector._submitLockProofImpl; Connector.submitAckProof", notes="")
mut(id="XC-S04", host="xchain", pattern="P4", side="S", op="OP-V4",
    file=AD, anchor="        _RISC0_VERIFIER.verify(seal, imageId, commitment);\n", repl="",
    gt_file="RiscZeroAdapter.sol", gt_function="verify",
    unbound="seal validity (RISC Zero verifier call skipped)",
    broken="the adapter returns the caller's journal digest without verifying the seal",
    effect="any journal digest is accepted on every route: mint into holding, release, refund",
    related="Connector._verifyProof; all submit*Proof routes", notes="")
mut(id="XC-S05", host="xchain", pattern="P3", side="S", op="OP-R1",
    file=CN, anchor="        if (destinationLockAccepted[_txId]) revert Errors.DestinationLockAlreadyAccepted(_txId);\n", repl="",
    gt_file="Connector.sol", gt_function="_enforceDestinationLockPreconditions",
    unbound="durable replay key of the lock route (destinationLockAccepted)",
    broken="after a transfer is released/cleaned up, the same lock proof is accepted again",
    effect="the same deposit is minted into holding again and (with the same ack proof) paid out again",
    related="Connector._submitLockProofImpl; Connector._cleanupTx; Connector.submitAckProof", notes="")
mut(id="XC-S06", host="xchain", pattern="P2", side="S", op="OP-X4",
    file=CN, anchor="        _enforceFinality(tx_.sourceChainId, tx_.ackDeadline);\n", repl="",
    gt_file="Connector.sol", gt_function="submitRefundClaimProof",
    unbound="finality of the observed origin state (refund-claim event)",
    broken="destination accepts a refund-claim proof without the configured finality delay after ackDeadline",
    effect="a refund claim from a non-final (reorgable) origin block unlocks the destination burn path while the origin transfer may still complete",
    related="Connector._enforceFinality; Connector.executeBurn", notes="Weak: needs an origin reorg past ackDeadline.")
mut(id="XC-S07", host="xchain", pattern="P4", side="S", op="OP-K1",
    file=CN,
    anchor="        if (proofImageId != expected) {\n            revert Errors.ImageIdRouteMismatch(uint8(_route), proofImageId, expected);\n        }\n",
    repl="",
    extra=[(AD, "        if (!_allowedImageIds[imageId]) revert Errors.ImageIdNotAllowed(imageId);\n", "")],
    gt_file="RiscZeroAdapter.sol", gt_function="verify",
    unbound="RISC Zero image ID (program identity) taken from the caller's proof payload",
    broken="neither the route's stored image ID nor the adapter allowlist is enforced (two-line edit: both pins removed)",
    effect="a proof of an attacker-written guest with any journal is accepted on every route: unbacked mints into holding and releases",
    related="Connector._checkRouteImageId; Connector._verifyProof; RiscZeroAdapter.verify; all submit*Proof routes",
    notes="Two-site edit by design: removing only one of the two pins stays bound (see decoy XC-D01).")
decoy(id="XC-D01", host="xchain", side="S", op="DEC-5",
    file=AD, anchor="        if (!_allowedImageIds[imageId]) revert Errors.ImageIdNotAllowed(imageId);\n", repl="",
    gt_file="RiscZeroAdapter.sol", gt_function="verify",
    why_bound="every Connector route calls _checkRouteImageId first, which pins the payload's image ID to the route's stored image ID")

# KK-S06 is defined by a two-step edit (comment + catch body); keep it a single contiguous anchor:
for m in M:
    if m["id"] == "KK-S06":
        m.update(
            anchor="        // the bb verifiers revert (rather than return false) on most failures: normalise both\n"
                   "        try verifier.verify(proof, _publicInputs(root, nullifierHash, recipient, relayer, fee, refund, extHash)) returns (\n"
                   "            bool ok\n        ) {\n            if (!ok) revert Errors.InvalidProof();\n        } catch {\n            revert Errors.InvalidProof();\n        }\n",
            repl="        try verifier.verify(proof, _publicInputs(root, nullifierHash, recipient, relayer, fee, refund, extHash)) returns (\n"
                 "            bool ok\n        ) {\n            if (!ok) revert Errors.InvalidProof();\n        } catch {}\n",
            broken="a reverting verifier call (how the bb verifier rejects invalid proofs) is swallowed by an empty catch",
            effect="any proof bytes are accepted: withdraw/withdrawAndCall pay out without a valid proof",
            related="ShieldedWithdrawVerifier.verify; KakushiPool.withdraw; KakushiPool.withdrawAndCall")


def edits(m):
    return [(m["file"], m["anchor"], m["repl"])] + list(m.get("extra", []))


def apply_one(text, mid, host, f, anchor, repl):
    n = text.count(anchor)
    if n != 1:
        raise SystemExit(f"FAIL-CLOSED {mid}: anchor occurs {n}x in {host}/{f}")
    return text.replace(anchor, repl, 1)


def apply(text, m):  # primary edit only (kept for --check of the first site)
    return apply_one(text, m["id"], m["host"], m["file"], m["anchor"], m["repl"])


def sha(b): return hashlib.sha256(b).hexdigest()


def main():
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--out"); g.add_argument("--check", action="store_true"); g.add_argument("--write-md", action="store_true")
    a = ap.parse_args()
    ids = [m["id"] for m in M]; assert len(ids) == len(set(ids))
    if a.check:
        for m in M:
            for f, an, rp in edits(m): apply_one((BASE / m["host"] / f).read_text(), m["id"], m["host"], f, an, rp)
        print(f"ok: {sum(m['kind']=='mutant' for m in M)} mutants, {sum(m['kind']=='decoy' for m in M)} decoys")
        return
    if a.write_md:
        write_md(); return
    out = pathlib.Path(a.out)
    if out.exists(): raise SystemExit(f"{out} exists (never overwritten)")
    out.mkdir(parents=True); rec = []
    for m in M:
        dst = out / m["id"]; shutil.copytree(BASE / m["host"], dst, symlinks=False)
        files = []
        for fn, an, rp in edits(m):
            f = dst / fn; before = f.read_bytes(); after = apply_one(before.decode(), m["id"], m["host"], fn, an, rp).encode()
            f.write_bytes(after); files.append({"file": fn, "sha256_before": sha(before), "sha256_after": sha(after)})
        rec.append({k: m[k] for k in ("id", "kind", "host", "pattern", "side", "op")} | {"edits": files})
    (out / "generation-record.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(f"wrote {len(rec)} trees to {out}")


def write_md():
    for m in M:
        d = HERE / ("mutants" if m["kind"] == "mutant" else "decoys"); d.mkdir(exist_ok=True)
        parts = []
        for fn, an, rp in edits(m):
            parts += [f"--- baselines/{m['host']}/{fn}", *("-" + l for l in an.rstrip("\n").split("\n")),
                      "+++ edited", *("+" + l for l in rp.rstrip("\n").split("\n") if rp)]
        diff = "\n".join(parts)
        if m["kind"] == "mutant":
            body = f"""# {m['id']} ({m['host']}, {m['pattern']}, {'circuit' if m['side']=='C' else 'guest' if m['side']=='G' else 'consumer/verifier'}-side)

| Field | Value |
|---|---|
| Operator | {m['op']} (see `OPERATORS.md`) |
| Pattern | {m['pattern']} |
| Broken binding | {m['broken']} |
| Unbound value | {m['unbound']} |
| GT consumer file | `{m['gt_file']}` |
| GT function (where the unbound value enters the effect) | `{m['gt_function']}` |
| Edited file(s) | {", ".join("`baselines/" + m["host"] + "/" + e[0] + "`" for e in edits(m))} |
| Related locations | {m['related']} |
| Attacker effect | {m['effect']} |
| Notes | {m['notes'] or '-'} |

## Edit (exact match, applied by `make_mutants.py`)
```diff
{diff}
```
"""
        else:
            body = f"""# {m['id']} (decoy, {m['host']}, {'circuit' if m['side']=='C' else 'consumer/verifier'}-side)

Semantic-preserving edit: looks like a removed binding check, but the binding still holds.

| Field | Value |
|---|---|
| Decoy operator | {m['op']} (see `OPERATORS.md`) |
| Edited file(s) | {", ".join("`baselines/" + m["host"] + "/" + e[0] + "`" for e in edits(m))} |
| Location | `{m['gt_file']}` / `{m['gt_function']}` |
| Why it stays bound | {m['why_bound']} |

Any binding warning on this tree counts as a false alarm (`MATCHING.md`).

## Edit
```diff
{diff}
```
"""
        (d / f"{m['id']}.md").write_text(body)
    print("wrote md")


if __name__ == "__main__":
    main()
