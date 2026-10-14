// BindCheck T13 harness (NEW file; no upstream file is modified). Copied by scripts/t13.sh to
//   tools/cases/payy-history/pkg/zk-circuits/tests/t13_mint.rs
// as a cargo integration test (auto-discovered; no Cargo.toml or source edit). It uses only the public APIs and the same helpers,
// ordering and `CliBackend` (the pinned `bb` on PATH) as the upstream test `circuits::tests::test_agg_final`, with a single MINT
// utxo instead of two sends:
//     mint utxo -> agg_utxo (1 real bundle + 2 default padding bundles) -> agg_agg (1 real agg_utxo + 1 padding proof, as
//     pkg/aggregator/src/block_prover/prove.rs builds padding) -> agg_final.
// Output: $T13_OUT_DIR/mint_obligation.json (decoded inputs and the final public-input words as hex). Local testbed only.
use barretenberg_cli::CliBackend;
use element::Element;
use zk_circuits::{BbBackend, Prove, Verify};
use zk_primitives::{
    AggAgg, AggFinal, AggProof, AggUtxo, AggUtxoProof, AggUtxoPublicInput, InputNote, MerklePath, Note, ProofBytes, Utxo,
    UtxoKind, UtxoProof, UtxoProofBundleWithMerkleProofs, bridged_polygon_usdc_note_kind, get_address_for_private_key,
};

fn hex32(e: &Element) -> String {
    let b = e.to_be_bytes();
    format!("0x{}", b.iter().map(|x| format!("{x:02x}")).collect::<String>())
}

// Same construction as upstream `send_note` in pkg/zk-circuits/src/circuits/tests.rs.
fn send_note(value: u64, address: Element, psi: u64) -> Note {
    Note {
        kind: Element::new(2),
        value: Element::new(value),
        address,
        contract: bridged_polygon_usdc_note_kind(),
        psi: Element::new(psi),
    }
}

// Copy of upstream `process_utxo_for_agg` (tests.rs l.124-169), same logic.
async fn process_utxo_for_agg(
    backend: &dyn BbBackend,
    tree: &mut smirk::Tree<161, ()>,
    utxo: &Utxo,
) -> (UtxoProof, [MerklePath<161>; 4], Element) {
    let utxo_proof = utxo.prove(backend).await.unwrap();

    let input_commitment_1 = utxo.input_notes[0].note.commitment();
    let p1: MerklePath<161> = MerklePath::new(tree.path_for(input_commitment_1).siblings.to_vec());
    if input_commitment_1 != Element::ZERO {
        tree.remove(input_commitment_1).unwrap();
    }
    let input_commitment_2 = utxo.input_notes[1].note.commitment();
    let p2: MerklePath<161> = MerklePath::new(tree.path_for(input_commitment_2).siblings.to_vec());
    if input_commitment_2 != Element::ZERO {
        tree.remove(input_commitment_2).unwrap();
    }
    let output_commitment_1 = utxo.output_notes[0].commitment();
    if output_commitment_1 != Element::ZERO {
        tree.insert(output_commitment_1, ()).unwrap();
    }
    let p3: MerklePath<161> = MerklePath::new(tree.path_for(output_commitment_1).siblings.to_vec());
    let output_commitment_2 = utxo.output_notes[1].commitment();
    if output_commitment_2 != Element::ZERO {
        tree.insert(output_commitment_2, ()).unwrap();
    }
    let p4: MerklePath<161> = MerklePath::new(tree.path_for(output_commitment_2).siblings.to_vec());

    (utxo_proof, [p1, p2, p3, p4], tree.root_hash())
}

#[tokio::test]
async fn t13_single_mint_agg_final() {
    let backend: Box<dyn BbBackend> = Box::new(CliBackend);
    let b = backend.as_ref();
    let out_dir = std::env::var("T13_OUT_DIR").expect("T13_OUT_DIR must be set");

    let secret_key = Element::new(101); // same synthetic key as upstream tests
    let address = get_address_for_private_key(secret_key);
    let mut tree = smirk::Tree::<161, ()>::new();
    let empty_root = tree.root_hash();

    // One MINT utxo: no inputs (padding notes), output note 0 carries value 100, output note 1 is padding. Same shape as the mint
    // step in upstream `test_agg_final_with_mint_and_burn`.
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
        [
            UtxoProofBundleWithMerkleProofs::new(utxo_proof, &paths),
            UtxoProofBundleWithMerkleProofs::default(),
            UtxoProofBundleWithMerkleProofs::default(),
        ],
        empty_root,
        new_root,
    );
    let agg_utxo_proof = agg_utxo.prove(b).await.unwrap();
    agg_utxo_proof.verify(b).await.expect("agg_utxo proof verifies");

    // Padding aggregate proof exactly as pkg/aggregator/src/block_prover/prove.rs `padding_proof()`.
    let padding = AggProof::AggUtxo(Box::new(AggUtxoProof {
        proof: ProofBytes::default(),
        public_inputs: AggUtxoPublicInput::default(),
    }));
    let agg_agg = AggAgg::new([AggProof::AggUtxo(Box::new(agg_utxo_proof)), padding]);
    let agg_agg_proof = agg_agg.prove(b).await.unwrap();
    agg_agg_proof.verify(b).await.expect("agg_agg proof verifies");

    let agg_final = AggFinal::new(agg_agg_proof);
    let final_proof = agg_final.prove(b).await.unwrap();
    final_proof.verify(b).await.expect("agg_final proof verifies");

    let pi = &final_proof.public_inputs;
    let msgs: Vec<String> = pi.messages.iter().take(8).map(hex32).collect();
    let nonzero = pi.messages.iter().filter(|m| **m != Element::ZERO).count();
    let json = format!(
        "{{\n  \"empty_tree_root\": \"{}\",\n  \"old_root\": \"{}\",\n  \"new_root\": \"{}\",\n  \"commit_hash\": \"{}\",\n  \"messages_total\": {},\n  \"messages_nonzero\": {},\n  \"messages_first8\": {:?},\n  \"mint_output_note\": {{\"value\": 100, \"psi\": 1, \"commitment\": \"{}\"}}\n}}\n",
        hex32(&empty_root), hex32(&pi.old_root), hex32(&pi.new_root), hex32(&pi.commit_hash), pi.messages.len(), nonzero, msgs, hex32(&out1.commitment())
    );
    std::fs::create_dir_all(&out_dir).unwrap();
    std::fs::write(format!("{out_dir}/mint_obligation.json"), json).unwrap();
}
