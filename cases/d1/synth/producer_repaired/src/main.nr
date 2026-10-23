// SYNTHETIC D1-03 producer (authored by BindCheck; not derived from any third-party circuit).
// Models the proof-to-effect message-tail property in miniature, with NO recursion, NO hashing and NO
// dynamic counter (fixed 3-word record stride, so the compiled ACIR stays small and solver-friendly).
//
//   `authorized` is the certified record stream the prover is entitled to export.
//   `messages`   is what the consumer settles (public).
// Each record is three words [kind, a, b]. kind 0 = padding/end (a, b must be zero), kind 2 = mint [2, id, 0],
// kind 3 = burn [3, value, recipient]. The first padding record ends the active stream.
//
// REPAIRED variant: records in the tail after the stream ends are forced to zero, so no uncertified record can
// appear. This is the authored analogue of an added message-tail-zero assertion.
global R: u32 = 3; // records
global N: u32 = 9; // words = 3 * R

fn main(authorized: [Field; N], messages: pub [Field; N]) {
    let mut ended = false;
    for r in 0..R {
        let k = r * 3;
        if authorized[k] == 0 {
            ended = true;
        }
        if ended {
            // The certified stream must be compact (well-formedness of `authorized`).
            assert(authorized[k] == 0, "authorized stream must be compact");
            assert(authorized[k + 1] == 0, "authorized stream must be compact");
            assert(authorized[k + 2] == 0, "authorized stream must be compact");
            // REPAIRED: the exported tail must be zero, so no uncertified record can appear.
            assert(messages[k] == 0, "message tail must be zero");
            assert(messages[k + 1] == 0, "message tail must be zero");
            assert(messages[k + 2] == 0, "message tail must be zero");
        } else {
            // Active prefix: every exported word must equal the certified word.
            assert(messages[k] == authorized[k], "active message must be certified");
            assert(messages[k + 1] == authorized[k + 1], "active message must be certified");
            assert(messages[k + 2] == authorized[k + 2], "active message must be certified");
        }
    }
}
