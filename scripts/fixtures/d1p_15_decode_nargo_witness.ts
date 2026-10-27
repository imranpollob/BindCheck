/** Decode a witness emitted by pinned `nargo execute`; does not execute/prove. */
import fs from "node:fs";
import crypto from "node:crypto";
import { acvm } from "@noir-lang/noir_js";

const artifactPath = process.argv[2];
const witnessPath = process.argv[3];
const outputPath = process.argv[4];
const fixtureName = process.argv[5];
if (!artifactPath || !witnessPath || !outputPath || !fixtureName) {
  throw new Error("usage: d1p_15_decode_nargo_witness.ts ARTIFACT WITNESS_GZ OUTPUT FIXTURE");
}
const artifactBytes = fs.readFileSync(artifactPath);
const artifact = JSON.parse(artifactBytes.toString("utf8"));
const witnessBytes = fs.readFileSync(witnessPath);
const stack = acvm.decompressWitnessStack(witnessBytes);
if (stack.length !== 1 || stack[0].index !== 0) throw new Error("expected one main witness stack item");
const entries = [...stack[0].witness.entries()].sort((a, b) => a[0] - b[0]);
const sha256 = (bytes: Buffer) => crypto.createHash("sha256").update(bytes).digest("hex");
const result = {
  schema: "bindcheck.d1p15.nargo-witness/v1",
  fixture: fixtureName,
  operation: "pinned beta.22 nargo execute; witness decoded without proof generation",
  artifact: { path: artifactPath, sha256: sha256(artifactBytes), noirVersion: artifact.noir_version },
  compressedWitness: { path: witnessPath, sha256: sha256(witnessBytes), bytes: witnessBytes.length },
  witnessCount: entries.length,
  witnesses: Object.fromEntries(entries.map(([index, value]) => [String(index), value])),
};
fs.writeFileSync(outputPath, JSON.stringify(result, null, 2) + "\n");
console.log(JSON.stringify({ fixture: fixtureName, witnessCount: entries.length }));
