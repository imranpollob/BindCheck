// BindCheck T16 harness (NEW file; no upstream file is modified). Copied by scripts/t16.sh to
//   tools/cases/payy-c4d2c90/pkg/zk-circuits/tests/t16_tail_to_agg_final.rs
// Revision c4d2c9021b8fb9988816eb6987a734b830bfce15 ONLY. Does not regenerate the T15 agg_agg proofs: it reads the exact
// on-disk bytes from results/raw/T15/c4d2c90/{control,candidate}/{public_inputs,proof} (env vars below), reconstructs the
// structured AggAggProof losslessly (Proof::<AggAggPublicInputs>::from_raw_proof_bytes splits [public_inputs_bytes ++
// proof_bytes] back into the two parts it already was; no field is computed or altered), and feeds each one into
// AggFinal::new(...).prove(b), exactly as the upstream pipeline does. A witness/constraint failure is returned by
// `Prove::prove` as `Error::ImplementationSpecific` before any bb call; this harness does not catch or alter it.
// Output: $T16_OUT_DIR/{control,candidate}/{proof,public_inputs} (only on success) and $T16_OUT_DIR/harness.json.
use std::time::Instant;
use zk_circuits::circuits::Proof;
use zk_circuits::circuits::generated::agg_agg::AggAggPublicInputs as CircuitAggAggPublicInputs;
use zk_circuits::{BbBackend, Prove, Verify};
use zk_primitives::{AggAggProof, AggFinal};

fn js(s: &str) -> String {
    format!("{s:?}")
}

fn stage_of(e: &zk_circuits::Error) -> &'static str {
    match e {
        zk_circuits::Error::ImplementationSpecific(_) => {
            "witness generation / constraint check (ACVM execution), before any bb call"
        }
        zk_circuits::Error::Backend(_) => "bb backend",
        zk_circuits::Error::VerificationFailed => "bb verification",
    }
}

fn chain(e: &(dyn std::error::Error + 'static)) -> String {
    let mut out = format!("{e}");
    let mut cur = e.source();
    while let Some(c) = cur {
        out.push_str(&format!(" <- {c}"));
        cur = c.source();
    }
    out
}

// Reconstructs the AggAggProof exactly as it was written to disk: no byte is computed. `Proof::from_raw_proof_bytes`
// requires the public_inputs byte length to be an exact multiple of 32 and to match AggAggPublicInputs::FIELD_COUNT (1005
// fields = 32160 bytes here); anything else panics loudly rather than silently truncating or padding.
fn load_agg_agg_proof(pi_path: &str, proof_path: &str) -> AggAggProof {
    let pi_bytes = std::fs::read(pi_path).unwrap_or_else(|e| panic!("cannot read {pi_path}: {e}"));
    let proof_bytes = std::fs::read(proof_path).unwrap_or_else(|e| panic!("cannot read {proof_path}: {e}"));
    assert_eq!(pi_bytes.len(), 1005 * 32, "public_inputs file is not 1005 fields (32160 bytes): {}", pi_bytes.len());
    let mut combined = pi_bytes.clone();
    combined.extend_from_slice(&proof_bytes);
    let circuit_proof = Proof::<CircuitAggAggPublicInputs>::from_raw_proof_bytes(combined);
    assert_eq!(circuit_proof.proof, proof_bytes, "split did not recover the original proof bytes unchanged");
    circuit_proof.into()
}

// One attempt = AggFinal::new(..).prove(b) (ACVM execution, then bb prove), then bb verify on success.
async fn attempt(b: &dyn BbBackend, label: &str, agg_agg_proof: AggAggProof, out_dir: &str) -> String {
    let t = Instant::now();
    let agg_final = AggFinal::new(agg_agg_proof);
    let res = agg_final.prove(b).await;
    let secs = t.elapsed().as_secs_f64();
    let mut verify = "not run (no proof)".to_string();
    let mut proof_bytes_len = 0usize;
    let mut pi_bytes_len = 0usize;
    let mut msgs_hex = String::new();
    let (satisfied, stage, err) = match res {
        Ok(p) => {
            let proof_bytes = p.proof.0.clone();
            let pi_bytes = p.public_inputs.to_bytes();
            proof_bytes_len = proof_bytes.len();
            pi_bytes_len = pi_bytes.len();
            std::fs::create_dir_all(format!("{out_dir}/{label}")).unwrap();
            std::fs::write(format!("{out_dir}/{label}/proof"), &proof_bytes).unwrap();
            std::fs::write(format!("{out_dir}/{label}/public_inputs"), &pi_bytes).unwrap();
            let hx = |e: &element::Element| format!("0x{}", e.to_be_bytes().iter().map(|x| format!("{x:02x}")).collect::<String>());
            let msgs: Vec<String> = p.public_inputs.messages.iter().take(12).map(hx).collect();
            msgs_hex = format!("{msgs:?}");
            verify = match p.verify(b).await { Ok(()) => "ok".into(), Err(e) => format!("FAILED: {e}") };
            (true, "witness satisfied; bb prove ok".to_string(), String::new())
        }
        Err(e) => (false, stage_of(&e).to_string(), chain(&e)),
    };
    format!(
        "\"{label}\": {{\"witness_satisfied_and_proof_generated\": {satisfied}, \"failure_stage\": {}, \"error\": {}, \"secs\": {secs:.1}, \"native_verify_via_harness\": {}, \"proof_bytes\": {proof_bytes_len}, \"public_inputs_bytes\": {pi_bytes_len}, \"public_messages_first12\": {}}}",
        js(&stage), js(&err), js(&verify), if msgs_hex.is_empty() { "null".to_string() } else { msgs_hex }
    )
}

#[tokio::test]
async fn t16_agg_final_tail_propagation() {
    let backend: Box<dyn BbBackend> = Box::new(barretenberg_cli::CliBackend);
    let b = backend.as_ref();
    let out_dir = std::env::var("T16_OUT_DIR").expect("T16_OUT_DIR must be set");
    std::fs::create_dir_all(&out_dir).unwrap();

    let control_proof = load_agg_agg_proof(
        &std::env::var("T16_CONTROL_PI").expect("T16_CONTROL_PI"),
        &std::env::var("T16_CONTROL_PROOF").expect("T16_CONTROL_PROOF"),
    );
    let candidate_proof = load_agg_agg_proof(
        &std::env::var("T16_CANDIDATE_PI").expect("T16_CANDIDATE_PI"),
        &std::env::var("T16_CANDIDATE_PROOF").expect("T16_CANDIDATE_PROOF"),
    );

    let control_json = attempt(b, "control", control_proof, &out_dir).await;
    let candidate_json = attempt(b, "candidate", candidate_proof, &out_dir).await;

    let json = format!("{{\n  {control_json},\n  {candidate_json}\n}}\n");
    std::fs::write(format!("{out_dir}/harness.json"), json).unwrap();
}
