// ShieldedWithdraw: "I know (nullifier, secret) whose commitment is a leaf of the pool tree with
// this root, and this is its nullifier hash." Verified by KakushiPool.withdraw through
// packages/contracts/src/verifiers/ShieldedWithdrawVerifier.sol.
//
// Encodings (mirrored by packages/attest-core/src/pool.ts and KakushiPool.sol):
//   commitment     = Poseidon2::hash([nullifier, secret], 2)      (the leaf)
//   nullifier_hash = Poseidon2::hash([nullifier], 1)
//   node           = Poseidon2::hash([left, right], 2), depth 20
//   path_bits[i]   = bit i (LSB first) of the leaf index: true = running node is the RIGHT child
//
// Public inputs, in verifier order:
//   0 root, 1 nullifier_hash, 2 recipient, 3 relayer, 4 fee, 5 refund, 6 chain_id, 7 pool,
//   8 ext_data_hash
// recipient/relayer/pool are uint160 addresses, chain_id is block.chainid. They are not used by
// the membership statement itself; they are range-constrained below so they are real circuit
// inputs that the proof commits to (a proof for one recipient/relayer/fee/chain/pool cannot be
// replayed with another, front-run, or replayed across chains or pools).
//
// ext_data_hash binds a private call (KakushiPool.withdrawAndCall): 0 for a plain withdrawal,
// otherwise
//   uint256(keccak256(abi.encode(address target, bytes data, address refundTo,
//                                uint256 chainId, address pool))) mod p
// computed by the pool (KakushiPool.extDataHash), so a relayer cannot change the call target,
// the calldata or where leftovers are refunded. A full field element has no range to check, so it
// is bound by a real gate instead: a private call carries no native refund (the pool always
// passes refund = 0 for withdrawAndCall), enforced through ext_data_hash's is-zero gadget.

use poseidon::poseidon2::Poseidon2;

pub global DEPTH: u32 = 20;

pub fn commitment_of(nullifier: Field, secret: Field) -> Field {
    Poseidon2::hash([nullifier, secret], 2)
}

pub fn nullifier_hash_of(nullifier: Field) -> Field {
    Poseidon2::hash([nullifier], 1)
}

pub fn compute_root(leaf: Field, path: [Field; DEPTH], path_bits: [bool; DEPTH]) -> Field {
    let mut cur = leaf;
    for i in 0..DEPTH {
        if path_bits[i] {
            cur = Poseidon2::hash([path[i], cur], 2);
        } else {
            cur = Poseidon2::hash([cur, path[i]], 2);
        }
    }
    cur
}

fn main(
    root: pub Field,
    nullifier_hash: pub Field,
    recipient: pub Field,
    relayer: pub Field,
    fee: pub Field,
    refund: pub Field,
    chain_id: pub Field,
    pool: pub Field,
    ext_data_hash: pub Field,
    nullifier: Field,
    secret: Field,
    path: [Field; DEPTH],
    path_bits: [bool; DEPTH],
) {
    assert(nullifier_hash_of(nullifier) == nullifier_hash, "nullifier hash mismatch");
    let commitment = commitment_of(nullifier, secret);
    assert(compute_root(commitment, path, path_bits) == root, "commitment not in tree");

    // binding inputs: constrained, so they cannot be optimized away
    recipient.assert_max_bit_size::<160>();
    relayer.assert_max_bit_size::<160>();
    pool.assert_max_bit_size::<160>();
    fee.assert_max_bit_size::<128>();
    refund.assert_max_bit_size::<128>();
    chain_id.assert_max_bit_size::<64>();
    assert(pool != 0, "missing pool");
    assert(chain_id != 0, "missing chain id");
    assert((ext_data_hash == 0) | (refund == 0), "private call with refund");
}
