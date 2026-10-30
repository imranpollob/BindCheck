// BindCheck TE06 harness (NEW file; no upstream file is modified). Chained
// double-settlement batch for PY-S02: batch 1 settles a mint (control
// shape); batch 2 re-processes the SAME mint utxo against the advanced
// tree and re-exports the SAME mint words with old_root == batch-1
// new_root. Expected on pinned circuits: both batches prove + verify
// (spent tracking is consumer-side only; notes have no nullifiers), giving
// a genuinely chained height-2 block for the S02 real-verifier contrast.
// If the circuit rejects batch 2, that itself is the finding (double
// settlement unprovable at the proof level).
// Output: $T15_OUT_DIR/harness.json. Captures via $T10_CAPTURE_DIR.
use barretenberg_cli::CliBackend;
use element::Element;
use std::time::Instant;
use zk_circuits::circuits::generated::agg_agg::AggAggInput;
use zk_circuits::{BbBackend, Prove, Verify};
use zk_primitives::{
    AggAgg, AggProof, AggUtxo, AggUtxoProof, AggUtxoPublicInput, InputNote, MerklePath, Note, ProofBytes, Utxo,
    UtxoKind, UtxoProof, UtxoProofBundleWithMerkleProofs, bridged_polygon_usdc_note_kind,
    get_address_for_private_key,
};

fn hex32(e: &Element) -> String {
    format!("0x{}", e.to_be_bytes().iter().map(|x| format!("{x:02x}")).collect::<String>())
}

fn send_note(value: u64, address: Element, psi: u64) -> Note {
    Note { kind: Element::new(2), value: Element::new(value), address, contract: bridged_polygon_usdc_note_kind(), psi: Element::new(psi) }
}

fn insert_allow_existing(tree: &mut smirk::Tree<161, ()>, c: Element) {
    // Attacker-client modeling for the re-settlement batch: re-referencing
    // an already-present note commitment is the double-spend itself. The
    // circuit checks membership paths, not insertion history, so a
    // present commitment is kept and its current path is used.
    if c == Element::ZERO { return; }
    match tree.insert(c, ()) {
        Ok(()) => {},
        Err(e) => {
            let s = format!("{e:?}");
            assert!(s.contains("Collision"), "unexpected insert error: {s}");
        }
    }
}

async fn process_utxo_for_agg(backend: &dyn BbBackend, tree: &mut smirk::Tree<161, ()>, utxo: &Utxo) -> (UtxoProof, [MerklePath<161>; 4], Element) {
    process_utxo_for_agg_inner(backend, tree, utxo, false).await
}

async fn process_utxo_for_agg_resettle(backend: &dyn BbBackend, tree: &mut smirk::Tree<161, ()>, utxo: &Utxo) -> (UtxoProof, [MerklePath<161>; 4], Element) {
    process_utxo_for_agg_inner(backend, tree, utxo, true).await
}

async fn process_utxo_for_agg_inner(backend: &dyn BbBackend, tree: &mut smirk::Tree<161, ()>, utxo: &Utxo, allow_existing: bool) -> (UtxoProof, [MerklePath<161>; 4], Element) {
    let utxo_proof = utxo.prove(backend).await.unwrap();
    let c1 = utxo.input_notes[0].note.commitment();
    let p1: MerklePath<161> = MerklePath::new(tree.path_for(c1).siblings.to_vec());
    if c1 != Element::ZERO { tree.remove(c1).unwrap(); }
    let c2 = utxo.input_notes[1].note.commitment();
    let p2: MerklePath<161> = MerklePath::new(tree.path_for(c2).siblings.to_vec());
    if c2 != Element::ZERO { tree.remove(c2).unwrap(); }
    let o1 = utxo.output_notes[0].commitment();
    if o1 != Element::ZERO {
        if allow_existing { insert_allow_existing(tree, o1); } else { tree.insert(o1, ()).unwrap(); }
    }
    let p3: MerklePath<161> = MerklePath::new(tree.path_for(o1).siblings.to_vec());
    let o2 = utxo.output_notes[1].commitment();
    if o2 != Element::ZERO {
        if allow_existing { insert_allow_existing(tree, o2); } else { tree.insert(o2, ()).unwrap(); }
    }
    let p4: MerklePath<161> = MerklePath::new(tree.path_for(o2).siblings.to_vec());
    (utxo_proof, [p1, p2, p3, p4], tree.root_hash())
}

fn js(s: &str) -> String { format!("{s:?}") }

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
async fn te06_chained_double_settlement() {
    let backend: Box<dyn BbBackend> = Box::new(CliBackend);
    let b = backend.as_ref();
    let out_dir = std::env::var("T15_OUT_DIR").expect("T15_OUT_DIR must be set");
    std::fs::create_dir_all(&out_dir).unwrap();

    let secret_key = Element::new(101);
    let address = get_address_for_private_key(secret_key);
    let mut tree = smirk::Tree::<161, ()>::new();
    let empty_root = tree.root_hash();

    let out1 = send_note(100, address, 1);
    let utxo = Utxo {
        input_notes: [InputNote::padding_note(), InputNote::padding_note()],
        output_notes: [out1.clone(), Note::padding_note()],
        kind: UtxoKind::Mint,
        burn_address: None,
    };
    // ---- BATCH 1 (control shape) ----
    let (utxo_proof1, paths1, new_root1) = process_utxo_for_agg(b, &mut tree, &utxo).await;
    zk_circuits::circuits::Proof::from(utxo_proof1.clone()).verify(b).await.expect("utxo1 proof verifies");
    let agg_utxo1 = AggUtxo::new(
        [UtxoProofBundleWithMerkleProofs::new(utxo_proof1, &paths1), UtxoProofBundleWithMerkleProofs::default(), UtxoProofBundleWithMerkleProofs::default()],
        empty_root,
        new_root1,
    );
    let agg_utxo_proof1 = agg_utxo1.prove(b).await.unwrap();
    agg_utxo_proof1.verify(b).await.expect("agg_utxo1 proof verifies");
    let padding = AggProof::AggUtxo(Box::new(AggUtxoProof { proof: ProofBytes::default(), public_inputs: AggUtxoPublicInput::default() }));
    let agg_agg1 = AggAgg::new([AggProof::AggUtxo(Box::new(agg_utxo_proof1)), padding.clone()]);
    let active = agg_agg1.messages_count();
    assert_eq!(active, 4);
    let batch1 = AggAggInput::from(agg_agg1.clone());
    let batch1_json = attempt(b, "batch1", batch1, active).await;
    let batch1_words: Vec<String> = agg_agg1.messages().iter().take(active).map(hex32).collect();

    // ---- BATCH 2: same mint note re-processed against the advanced tree ----
    // (re-reference tolerated: the note is already present from batch 1).
    let (utxo_proof2, paths2, new_root2) = process_utxo_for_agg_resettle(b, &mut tree, &utxo).await;
    zk_circuits::circuits::Proof::from(utxo_proof2.clone()).verify(b).await.expect("utxo2 proof verifies");
    let agg_utxo2 = AggUtxo::new(
        [UtxoProofBundleWithMerkleProofs::new(utxo_proof2, &paths2), UtxoProofBundleWithMerkleProofs::default(), UtxoProofBundleWithMerkleProofs::default()],
        new_root1,
        new_root2,
    );
    let agg_utxo_proof2 = agg_utxo2.prove(b).await.unwrap();
    agg_utxo_proof2.verify(b).await.expect("agg_utxo2 proof verifies");
    let agg_agg2 = AggAgg::new([AggProof::AggUtxo(Box::new(agg_utxo_proof2)), padding]);
    let batch2_words: Vec<String> = agg_agg2.messages().iter().take(active).map(hex32).collect();
    assert_eq!(batch1_words, batch2_words, "batch 2 must re-export the same mint words");
    let batch2 = AggAggInput::from(agg_agg2);
    let batch2_json = attempt(b, "batch2_resettle", batch2, active).await;

    let json = format!(
        "{{\n  \"batch1_new_root\": {},\n  \"batch2_new_root\": {},\n  \"resettled_words\": {batch1_words:?},\n  {batch1_json},\n  {batch2_json}\n}}\n",
        js(&hex32(&new_root1)), js(&hex32(&new_root2)),
    );
    std::fs::write(format!("{out_dir}/harness.json"), json).unwrap();
}
