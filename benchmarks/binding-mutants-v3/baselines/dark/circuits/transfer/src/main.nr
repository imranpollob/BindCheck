// SPDX-License-Identifier: MIT OR Apache-2.0
//! C2 `dark_transfer` (§6): I own this balance, this is a well-formed ciphertext of an amount
//! inside the caps, and what is left over is still a valid 48-bit balance.
//!
//! Public inputs, canonical order (§19 C1, DarkVault._transferInputs):
//!   [0] chain_id [1] vault [2] sender [3] recipient [4] sender_nonce
//!   [5,6] pk_s [7,8] pk_r [9,10] avail.C [11,12] avail.D
//!   [13,14] ct.C [15,16] ct.D_sender [17,18] ct.D_recipient
//!   [19] min_transfer [20] max_transfer
use dark_lib::{
    assert_key, assert_point_or_identity, assert_u48, assert_valid_point, as_u64, bind, commit,
    decrypt, is_identity, mul_g, scalar,
};
use std::embedded_curve_ops::{EmbeddedCurvePoint, multi_scalar_mul};

fn main(
    s_lo: Field,
    s_hi: Field,
    r_lo: Field,
    r_hi: Field,
    a: u64,
    w: u64,
    chain_id: pub Field,
    vault: pub Field,
    sender: pub Field,
    recipient: pub Field,
    sender_nonce: pub Field,
    pk_s: pub EmbeddedCurvePoint,
    pk_r: pub EmbeddedCurvePoint,
    avail_c: pub EmbeddedCurvePoint,
    avail_d: pub EmbeddedCurvePoint,
    ct_c: pub EmbeddedCurvePoint,
    ct_ds: pub EmbeddedCurvePoint,
    ct_dr: pub EmbeddedCurvePoint,
    min_transfer: pub Field,
    max_transfer: pub Field,
) {
    // (1) keys are real points; a stored balance may be the identity (empty account).
    assert_valid_point(pk_s);
    assert_valid_point(pk_r);
    assert_point_or_identity(avail_c);
    assert_point_or_identity(avail_d);

    // (2) the sender owns pk_s.
    let s = scalar(s_lo, s_hi);
    assert_key(pk_s, s);

    let r = scalar(r_lo, r_hi);

    // (4) ct.C == a*G + r*H, with a in range.
    assert_u48(a);
    assert(commit(a, r) == ct_c, "ct.C != a*G + r*H");

    // (5) both handles use the SAME r. D_recipient binds the recipient's key, so a sender
    //     cannot pollute and freeze someone else's pending balance.
    assert(multi_scalar_mul([pk_s], [r]) == ct_ds, "ct.D_sender != r*pk_sender");
    assert(multi_scalar_mul([pk_r], [r]) == ct_dr, "ct.D_recipient != r*pk_recipient");

    // (3) r != 0. The limbs are already non-zero; this is the check that matters, since
    //     n is prime and pk_s is not the identity, r*pk_s == identity iff r == 0 mod n.
    assert(!is_identity(ct_ds), "r is zero mod n");

    // (6) min_transfer <= a <= max_transfer.
    assert(as_u64(min_transfer) <= a, "a < min_transfer");
    assert(a <= as_u64(max_transfer), "a > max_transfer");

    // (7) the remainder is a valid balance: (avail.C - ct.C) - s*(avail.D - ct.D_sender) == w*G.
    //     Spending the whole balance gives w = 0, i.e. the identity.
    assert_u48(w);
    assert(decrypt(avail_c - ct_c, avail_d - ct_ds, s) == mul_g(w), "remainder is not w*G");

    // (8) domain separators.
    bind([chain_id, vault, sender, recipient, sender_nonce]);
}
