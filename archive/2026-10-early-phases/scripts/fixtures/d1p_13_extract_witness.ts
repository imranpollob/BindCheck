/** Re-execute the saved D1P-12R honest inputs; never invoke a prover. */
import fs from "node:fs";
import crypto from "node:crypto";
import { Noir, acvm } from "@noir-lang/noir_js";

const artifactPath = process.env.D1P13_ARTIFACT!;
const honestProofPath = process.env.D1P13_HONEST_PROOF!;
const outputPath = process.env.D1P13_WITNESS!;
if (!artifactPath || !honestProofPath || !outputPath) {
  throw new Error("D1P-13 witness environment is incomplete");
}

const artifactBytes = fs.readFileSync(artifactPath);
const artifact = JSON.parse(artifactBytes.toString("utf8"));
const priorBytes = fs.readFileSync(honestProofPath);
const prior = JSON.parse(priorBytes.toString("utf8"));
const noir = new Noir(artifact);
const execution = await noir.execute(prior.proofInputs);
const stack = acvm.decompressWitnessStack(execution.witness);
if (stack.length !== 1 || stack[0].index !== 0) {
  throw new Error(`expected only main witness stack item, observed ${stack.length}`);
}
const entries = [...stack[0].witness.entries()]
  .map(([index, value]) => [index, value] as const)
  .sort((left, right) => left[0] - right[0]);
const publicWitnesses = entries.filter(([index]) => index >= 0 && index < 11);
const expectedPublic = prior.publicInputs.map((value: string) => value.toLowerCase());
const observedPublic = publicWitnesses.map(([, value]) => value.toLowerCase());
if (JSON.stringify(expectedPublic) !== JSON.stringify(observedPublic)) {
  throw new Error("executed public witnesses differ from the accepted D1P-12R proof inputs");
}

const sha256 = (bytes: Buffer) => crypto.createHash("sha256").update(bytes).digest("hex");
fs.writeFileSync(outputPath, JSON.stringify({
  schema: "bindcheck.d1p13.honest-witness/v1",
  operation: "Noir.execute(saved D1P-12R proofInputs); no proof generation",
  artifact: { path: artifactPath, sha256: sha256(artifactBytes), noirVersion: artifact.noir_version },
  honestProofInput: { path: honestProofPath, sha256: sha256(priorBytes) },
  stackIndex: stack[0].index,
  witnessCount: entries.length,
  publicWitnesses: publicWitnesses.map(([index, value]) => ({ index, value })),
  publicWitnessesMatchAcceptedProof: true,
  witnesses: Object.fromEntries(entries.map(([index, value]) => [String(index), value])),
}, null, 2) + "\n");
console.log(JSON.stringify({ witnessCount: entries.length, publicWitnessesMatchAcceptedProof: true }));
