/** Save the VK that WarpToad's pinned verifier generator otherwise keeps in memory. */
import { Barretenberg, UltraHonkBackend } from "@aztec/bb.js";
import fs from "node:fs";
import os from "node:os";

const circuitPath = process.env.D1P12R_CIRCUIT!;
const vkPath = process.env.D1P12R_VK!;
const verifierPath = process.env.D1P12R_VK_VERIFIER!;
if (!circuitPath || !vkPath || !verifierPath) throw new Error("D1P12R artifact output environment is incomplete");

const circuit = JSON.parse(fs.readFileSync(circuitPath, "utf8"));
const api = await Barretenberg.new({ threads: os.cpus().length });
const backend = new UltraHonkBackend(circuit.bytecode, api);
const vk = await backend.getVerificationKey({ keccakZK: true });
const verifier = await backend.getSolidityVerifier(vk, { keccakZK: true });
fs.writeFileSync(vkPath, vk);
fs.writeFileSync(verifierPath, verifier);
console.log(JSON.stringify({ threads: os.cpus().length, vkBytes: vk.length, verifierBytes: verifier.length }));
await api.destroy();
