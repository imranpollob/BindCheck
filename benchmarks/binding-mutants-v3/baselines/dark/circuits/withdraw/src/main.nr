// SPDX-License-Identifier: MIT OR Apache-2.0
//! C3 `dark_withdraw` (§6): I own this balance and it covers this public amount.
//!
//! Public inputs, canonical order (§19 C1, DarkVault._withdrawInputs):
//!   [0] chain_id [1] vault [2] account [3] to [4] nonce
//!   [5,6] pk [7,8] avail.C [9,10] avail.D [11] amount
//!
//! `to` is a binding input: a withdraw proof is only good for the recipient it was built for.
use dark_lib::{
    assert_key, assert_point_or_identity, assert_u48, assert_valid_point, as_u64, bind, decrypt,
    mul_g, scalar,
};
use std::embedded_curve_ops::EmbeddedCurvePoint;

fn main(
    s_lo: Field,
    s_hi: Field,
    w: u64,
    chain_id: pub Field,
    vault: pub Field,
    account: pub Field,
    to: pub Field,
    nonce: pub Field,
    pk: pub EmbeddedCurvePoint,
    avail_c: pub EmbeddedCurvePoint,
    avail_d: pub EmbeddedCurvePoint,
    amount: pub Field,
) {
    assert_valid_point(pk);
    assert_point_or_identity(avail_c);
    assert_point_or_identity(avail_d);

    let s = scalar(s_lo, s_hi);
    assert_key(pk, s);

    // 1 <= amount < 2^48. A zero withdraw is `AmountZero` on-chain (§19 C4); reject it here too.
    let amt = as_u64(amount);
    assert(amt != 0, "amount is zero");
    assert_u48(amt);

    // (avail.C - amount*G) - s*avail.D == w*G, with the remainder still a valid balance.
    assert_u48(w);
    assert(decrypt(avail_c - mul_g(amt), avail_d, s) == mul_g(w), "remainder is not w*G");

    bind([chain_id, vault, account, to, nonce]);
}
