#!/usr/bin/env node
// AZ1 oracle helper: turn the solc --combined-json output and the generated
// Poseidon creation bytecode into standard {abi, bytecode} artifact JSONs that
// the oracle's generic driver already reads (no driver deploy changes needed).
//
//   node make_artifacts.js <combined.json> <poseidon3.hex> <poseidon4.hex> <outDir>
"use strict";
const fs = require("fs");
const path = require("path");

const [combinedPath, p3Path, p4Path, outDir] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });

function write(name, abi, binHex) {
  const bytecode = binHex.startsWith("0x") ? binHex : "0x" + binHex;
  fs.writeFileSync(
    path.join(outDir, name + ".json"),
    JSON.stringify({ abi, bytecode }, null, 1) + "\n"
  );
}

// solc combined-json: { contracts: { "file:Name": { abi, bin } } }
const combined = JSON.parse(fs.readFileSync(combinedPath, "utf8"));
for (const [key, c] of Object.entries(combined.contracts || {})) {
  const name = key.slice(key.lastIndexOf(":") + 1);
  const abi = typeof c.abi === "string" ? JSON.parse(c.abi) : c.abi;
  if (!c.bin) continue;
  write(name, abi, c.bin);
}

// Poseidon libraries: raw creation bytecode, minimal ABI (deploy-only; the
// consumer calls them internally, the oracle only needs their addresses).
const poseidonAbi = (n) => [
  {
    type: "function",
    name: "poseidon",
    stateMutability: "pure",
    inputs: [{ type: `uint256[${n}]`, name: "input" }],
    outputs: [{ type: "uint256", name: "" }],
  },
];
write("Poseidon3", poseidonAbi(3), fs.readFileSync(p3Path, "utf8").trim());
write("Poseidon4", poseidonAbi(4), fs.readFileSync(p4Path, "utf8").trim());

console.log("wrote artifacts to", outDir);
