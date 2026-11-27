// BindCheck T14 (NEW untracked file, copied by scripts/t14.sh to pkg/zk-circuits/tests/t14_hash_check.rs). No proving.
// Question: is the mint hash in the (verified) T13 public inputs the hash of the two output notes' psi values (what the circuit and
// Utxo::mint_hash() implement) or the hash of the two commitments (what the RollupV1.sol comment says)?
// Inputs mirror payy-harness/t13_mint.rs exactly. $T14_PI_FILE is the T13 `public_inputs` file; $T14_OUT_DIR receives hash_check.json.
use element::Element;
use zk_primitives::{InputNote, Note, Utxo, UtxoKind, bridged_polygon_usdc_note_kind, get_address_for_private_key};

fn hex32(e: &Element) -> String {
    format!("0x{}", e.to_be_bytes().iter().map(|x| format!("{x:02x}")).collect::<String>())
}

#[test]
fn t14_mint_hash_derivation() {
    let address = get_address_for_private_key(Element::new(101));
    let out1 = Note { kind: Element::new(2), value: Element::new(100), address, contract: bridged_polygon_usdc_note_kind(), psi: Element::new(1) };
    let pad = Note::padding_note();
    let utxo = Utxo { input_notes: [InputNote::padding_note(), InputNote::padding_note()], output_notes: [out1.clone(), pad.clone()], kind: UtxoKind::Mint, burn_address: None };

    let from_psi = hash::hash_merge([out1.psi, pad.psi]);                       // circuit: Poseidon2([psi0, psi1]); utxo.rs mint_hash()
    let from_commitments = hash::hash_merge([out1.commitment(), pad.commitment()]); // the RollupV1.sol comment's reading
    let api = utxo.mint_hash();
    let msgs = utxo.messages();

    let pi = std::fs::read(std::env::var("T14_PI_FILE").unwrap()).unwrap();
    let word = |i: usize| -> String { format!("0x{}", pi[i * 32..(i + 1) * 32].iter().map(|x| format!("{x:02x}")).collect::<String>()) };
    let proof_hash = word(6); // public-input index 6 = messages[3] = mint hash
    let json = format!(
        "{{\n  \"mint_hash_in_verified_public_inputs\": \"{}\",\n  \"hash_merge([psi0, psi1])\": \"{}\",\n  \"Utxo::mint_hash()\": \"{}\",\n  \"hash_merge([commitment0, commitment1])\": \"{}\",\n  \"psi0\": \"{}\",\n  \"psi1_padding\": \"{}\",\n  \"commitment0\": \"{}\",\n  \"commitment1_padding\": \"{}\",\n  \"rust_message_words\": [\"{}\", \"{}\", \"{}\", \"{}\", \"{}\"],\n  \"equals_psi_hash\": {},\n  \"equals_commitment_hash\": {}\n}}\n",
        proof_hash, hex32(&from_psi), hex32(&api), hex32(&from_commitments), hex32(&out1.psi), hex32(&pad.psi), hex32(&out1.commitment()), hex32(&pad.commitment()),
        hex32(&msgs[0]), hex32(&msgs[1]), hex32(&msgs[2]), hex32(&msgs[3]), hex32(&msgs[4]),
        proof_hash == hex32(&from_psi), proof_hash == hex32(&from_commitments)
    );
    let out = std::env::var("T14_OUT_DIR").unwrap();
    std::fs::create_dir_all(&out).unwrap();
    std::fs::write(format!("{out}/hash_check.json"), json).unwrap();
}
