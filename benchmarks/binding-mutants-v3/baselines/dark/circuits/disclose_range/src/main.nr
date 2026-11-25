// SPDX-License-Identifier: MIT OR Apache-2.0
//! C4 `dark_disclose_range` (§6): the value behind this ciphertext is in [lo, hi].
//! Off-chain only -- verified in the browser with bb.js, never deployed.
//!
//! Public inputs, canonical order (§19 C1):
//!   [0] context_hash [1,2] pk [3,4] c [5,6] d [7] lo [8] hi
//!
//! `c`/`d` may be a viewer-recomputed sum ciphertext, which is how "flow total in [X, Y]"
//! works with the same circuit.
use dark_lib::{
    assert_key, assert_point_or_identity, assert_u48, assert_valid_point, as_u64, bind, decrypt,
    mul_g, scalar,
};
use std::embedded_curve_ops::EmbeddedCurvePoint;

fn main(
    s_lo: Field,
    s_hi: Field,
    v: u64,
    context_hash: pub Field,
    pk: pub EmbeddedCurvePoint,
    c: pub EmbeddedCurvePoint,
    d: pub EmbeddedCurvePoint,
    lo: pub Field,
    hi: pub Field,
) {
    assert_valid_point(pk);
    assert_point_or_identity(c);
    assert_point_or_identity(d);

    let s = scalar(s_lo, s_hi);
    assert_key(pk, s);

    // c - s*d == v*G.
    assert(decrypt(c, d, s) == mul_g(v), "c - s*d != v*G");

    // lo <= v <= hi < 2^48.
    let lo_u = as_u64(lo);
    let hi_u = as_u64(hi);
    assert_u48(hi_u);
    assert(lo_u <= v, "v < lo");
    assert(v <= hi_u, "v > hi");

    bind([context_hash]);
}
