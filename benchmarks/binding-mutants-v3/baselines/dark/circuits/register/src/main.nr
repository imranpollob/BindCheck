// SPDX-License-Identifier: MIT OR Apache-2.0
//! C1 `dark_register` (§6, §4 "Registration"): I know the s behind this public key.
//!
//! Public inputs, canonical order (§19 C1, DarkKeyRegistry.register):
//!   [0] chain_id  [1] registry  [2] account  [3] pk.x  [4] pk.y
//!
//! Binding chain, registry and caller is what stops a proof being replayed on another chain
//! or front-run into someone else's registration.
use dark_lib::{assert_key, assert_valid_point, bind, scalar};
use std::embedded_curve_ops::EmbeddedCurvePoint;

fn main(
    s_lo: Field,
    s_hi: Field,
    chain_id: pub Field,
    registry: pub Field,
    account: pub Field,
    pk: pub EmbeddedCurvePoint,
) {
    assert_valid_point(pk);
    assert_key(pk, scalar(s_lo, s_hi));
    bind([chain_id, registry, account]);
}
