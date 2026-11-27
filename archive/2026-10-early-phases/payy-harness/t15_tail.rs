// BindCheck T15 harness (NEW file; no upstream file is modified). Copied by scripts/t15.sh to
//   <checkout>/pkg/zk-circuits/tests/t15_tail.rs
// into each of the two separate checkouts (c4d2c90 and dcd5d96) as a cargo integration test. The same source is compiled against each
// revision's own circuit fixtures, key and Rust code (nothing is shared across revisions).
//
// Steps (per revision):
//   1. mint utxo -> agg_utxo (1 real + 2 default padding bundles) -> AggAgg::new([real agg_utxo, padding]) exactly as T13
//      (pkg/aggregator/src/block_prover/prove.rs padding_proof()). The intended active message sequence is the 4 mint words.
//   2. CONTROL: the AggAggInput built by the upstream conversion (`From<AggAgg>`): outer public `messages` = the 4 mint words, then zeros.
//      `Prove::prove` first executes the revision's own compiled agg_agg program in the ACVM (the constraint check; a failure is returned as
//      `Error::ImplementationSpecific` BEFORE any bb call), then calls the pinned `bb prove`; then verify through the pinned `bb`.
//   3. CANDIDATE: the same AggAggInput, same inner proofs, but outer public `messages[4..9]` = a syntactically valid 5-word burn record
//      placed in the first slots after the active sequence (index 4 = messages_index after both inner proofs are consumed).
//      Same path: ACVM execution first; only if it succeeds does bb prove run, then verify.
// Output: $T15_OUT_DIR/harness.json (stage results, error strings, timings). Local testbed only. No circuit, key or constraint is altered.
use barretenberg_cli::CliBackend;
use element::Element;
use std::time::Instant;
use zk_circuits::circuits::generated::agg_agg::AggAggInput;
use zk_circuits::{BbBackend, Prove, Verify};
use zk_primitives::{
    AggAgg, AggProof, AggUtxo, AggUtxoProof, AggUtxoPublicInput, InputNote, MerklePath, Note, ProofBytes, Utxo, UtxoKind, UtxoProof,
    UtxoProofBundleWithMerkleProofs, bridged_polygon_usdc_note_kind, get_address_for_private_key,
};

fn hex32(e: &Element) -> String {
    format!("0x{}", e.to_be_bytes().iter().map(|x| format!("{x:02x}")).collect::<String>())
}

fn send_note(value: u64, address: Element, psi: u64) -> Note {
    Note { kind: Element::new(2), value: Element::new(value), address, contract: bridged_polygon_usdc_note_kind(), psi: Element::new(psi) }
}

// Same helper as T13 / upstream tests.rs `process_utxo_for_agg`.
async fn process_utxo_for_agg(backend: &dyn BbBackend, tree: &mut smirk::Tree<161, ()>, utxo: &Utxo) -> (UtxoProof, [MerklePath<161>; 4], Element) {
    let utxo_proof = utxo.prove(backend).await.unwrap();
    let c1 = utxo.input_notes[0].note.commitment();
    let p1: MerklePath<161> = MerklePath::new(tree.path_for(c1).siblings.to_vec());
    if c1 != Element::ZERO { tree.remove(c1).unwrap(); }
    let c2 = utxo.input_notes[1].note.commitment();
    let p2: MerklePath<161> = MerklePath::new(tree.path_for(c2).siblings.to_vec());
    if c2 != Element::ZERO { tree.remove(c2).unwrap(); }
    let o1 = utxo.output_notes[0].commitment();
    if o1 != Element::ZERO { tree.insert(o1, ()).unwrap(); }
    let p3: MerklePath<161> = MerklePath::new(tree.path_for(o1).siblings.to_vec());
    let o2 = utxo.output_notes[1].commitment();
    if o2 != Element::ZERO { tree.insert(o2, ()).unwrap(); }
    let p4: MerklePath<161> = MerklePath::new(tree.path_for(o2).siblings.to_vec());
    (utxo_proof, [p1, p2, p3, p4], tree.root_hash())
}

fn js(s: &str) -> String { format!("{s:?}") }

// Classify a Prove::prove failure. Execution (constraint) failures are `ImplementationSpecific`, wrapped before any bb call; bb failures are
// `Backend`/`VerificationFailed`. The ACVM error text is in the source chain.
fn chain(e: &(dyn std::error::Error + 'static)) -> String {
    let mut out = format!("{e}"); let mut cur = e.source();
    while let Some(c) = cur { out.push_str(&format!(" <- {c}")); cur = c.source(); }
    out
}
fn stage_of(e: &zk_circuits::Error) -> &'static str {
    match e {
        zk_circuits::Error::ImplementationSpecific(_) => "witness generation / constraint check (ACVM execution), before any bb call",
        zk_circuits::Error::Backend(_) => "bb backend",
        zk_circuits::Error::VerificationFailed => "bb verification",
    }
}

// One attempt = Prove::prove (ACVM execution, then bb prove), then bb verify on success. Returns a JSON object fragment.
async fn attempt(b: &dyn BbBackend, label: &str, input: AggAggInput, active: usize) -> String {
    let t = Instant::now();
    let res = input.prove(b).await;
    let secs = t.elapsed().as_secs_f64();
    let mut verify = "not run (no proof)".to_string();
    let mut pub_msgs = "null".to_string();
    let (satisfied, stage, err) = match res {
        Ok(p) => {
            let first: Vec<String> = p.public_inputs.messages.iter().take(active + 5).map(hex32).collect();
            pub_msgs = format!("{first:?}");
            let ap: zk_primitives::AggAggProof = p.into();
            verify = match ap.verify(b).await { Ok(()) => "ok".into(), Err(e) => format!("FAILED: {e}") };
            (true, "witness satisfied; bb prove ok".to_string(), String::new())
        }
        Err(e) => (false, stage_of(&e).to_string(), chain(&e)),
    };
    format!("\"{label}\": {{\"witness_satisfied_and_proof_generated\": {satisfied}, \"failure_stage\": {}, \"error\": {}, \"secs\": {secs:.1}, \"native_verify_via_harness\": {}, \"public_messages_first9\": {pub_msgs}}}",
        js(&stage), js(&err), js(&verify))
}

#[tokio::test]
async fn t15_agg_agg_tail_differential() {
    let backend: Box<dyn BbBackend> = Box::new(CliBackend);
    let b = backend.as_ref();
    let out_dir = std::env::var("T15_OUT_DIR").expect("T15_OUT_DIR must be set");
    std::fs::create_dir_all(&out_dir).unwrap();

    let secret_key = Element::new(101);
    let address = get_address_for_private_key(secret_key);
    let mut tree = smirk::Tree::<161, ()>::new();
    let empty_root = tree.root_hash();

    let t = Instant::now();
    let out1 = send_note(100, address, 1);
    let utxo = Utxo {
        input_notes: [InputNote::padding_note(), InputNote::padding_note()],
        output_notes: [out1.clone(), Note::padding_note()],
        kind: UtxoKind::Mint,
        burn_address: None,
    };
    let (utxo_proof, paths, new_root) = process_utxo_for_agg(b, &mut tree, &utxo).await;
    zk_circuits::circuits::Proof::from(utxo_proof.clone()).verify(b).await.expect("utxo proof verifies");
    let agg_utxo = AggUtxo::new(
        [UtxoProofBundleWithMerkleProofs::new(utxo_proof, &paths), UtxoProofBundleWithMerkleProofs::default(), UtxoProofBundleWithMerkleProofs::default()],
        empty_root,
        new_root,
    );
    let agg_utxo_proof = agg_utxo.prove(b).await.unwrap();
    agg_utxo_proof.verify(b).await.expect("agg_utxo proof verifies");
    let padding = AggProof::AggUtxo(Box::new(AggUtxoProof { proof: ProofBytes::default(), public_inputs: AggUtxoPublicInput::default() }));
    let agg_agg = AggAgg::new([AggProof::AggUtxo(Box::new(agg_utxo_proof)), padding]);
    let inner_secs = t.elapsed().as_secs_f64();

    // The intended active sequence, derived from the inner proofs' compacted messages (not a rule of ours).
    let active = agg_agg.messages_count();
    let control_messages = agg_agg.messages();
    assert_eq!(active, 4, "expected exactly the 4 mint words as the active sequence");
    assert!(control_messages[active..].iter().all(|m| *m == Element::ZERO));

    // ---- CONTROL ----
    let control = AggAggInput::from(agg_agg.clone());
    let control_json = attempt(b, "control", control, active).await;

    // ---- CANDIDATE: syntactically valid burn record (kind 3 = 5 words) in the first padding slots, active sequence untouched ----
    let tail = [Element::new(3), bridged_polygon_usdc_note_kind(), Element::new(7), Element::new(424242), Element::new(0xdead)];
    let mut cand = AggAggInput::from(agg_agg.clone());
    for (k, w) in tail.iter().enumerate() { cand.messages[active + k] = *w; }
    for k in 0..active { assert_eq!(cand.messages[k], control_messages[k], "active sequence preserved"); }
    let candidate_json = attempt(b, "candidate", cand, active).await;

    let words: Vec<String> = control_messages.iter().take(active).map(hex32).collect();
    let tail_hex: Vec<String> = tail.iter().map(hex32).collect();
    let json = format!(
        "{{\n  \"active_message_count\": {active},\n  \"active_words\": {words:?},\n  \"candidate_tail_index\": {active},\n  \"candidate_tail_words\": {tail_hex:?},\n  \"inner_build_secs\": {inner_secs:.1},\n  {control_json},\n  {candidate_json}\n}}\n"
    );
    std::fs::write(format!("{out_dir}/harness.json"), json).unwrap();
}
