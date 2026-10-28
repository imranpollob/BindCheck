#!/usr/bin/env node
/** Prove + verify a compiled circuit + witness with bb.js UltraHonk (keccakZK).
 * Usage: node prove.mjs --artifact ARTIFACT.json --witness WITNESS.gz --out DIR
 * Writes proof, publicInputs.json, vk, verifier.sol. Exits nonzero on failure.
 * All stdout is one JSON line (plus bb.js stderr noise).
 */
import fs from "node:fs";
import os from "node:os";
import { Barretenberg, UltraHonkBackend } from "@aztec/bb.js";

const argv = process.argv.slice(2);
const args = {};
for (let i = 0; i < argv.length; i += 2) args[argv[i].replace(/^--/, "")] = argv[i + 1];
fs.mkdirSync(args.out, { recursive: true });

const artifact = JSON.parse(fs.readFileSync(args.artifact, "utf8"));
const api = await Barretenberg.new({ threads: 1 });
try {
  const backend = new UltraHonkBackend(artifact.bytecode, api, { threads: 1 });
  const witness = new Uint8Array(fs.readFileSync(args.witness));
  const proof = await backend.generateProof(witness, { keccakZK: true });
  fs.writeFileSync(`${args.out}/proof`, proof.proof);
  fs.writeFileSync(`${args.out}/publicInputs.json`, JSON.stringify(proof.publicInputs));
  const vk = await backend.getVerificationKey({ keccakZK: true });
  fs.writeFileSync(`${args.out}/vk`, vk);
  const verifier = await backend.getSolidityVerifier(vk, { keccakZK: true });
  fs.writeFileSync(`${args.out}/verifier.sol`, verifier);
  const ok = await backend.verifyProof(proof, { keccakZK: true });
  console.log(JSON.stringify({ verified: ok, proofBytes: proof.proof.length, publicInputs: proof.publicInputs.length }));
  if (!ok) process.exit(1);
} finally {
  await api.destroy();
}
