#!/usr/bin/env node
// AZ1 fixture helper. Owned, synthetic, local-only data.
//   node fixture.js inputs <outdir> <alice> <bob> <carol>
//       writes honest-input.json, fault-input.json, poseidon3.hex, poseidon4.hex,
//       expected.json (commitments/credit computed off-circuit with circomlibjs)
//   node fixture.js castargs <proof.json> <public.json> <input.json> <numRealRows> [tamper]
//       prints the processBatch arguments for `cast send`, one per line
"use strict";
const fs = require("fs");
const path = require("path");

const N = 4;

function row(kind, owner, amount) {
  return { kind: BigInt(kind), owner: BigInt(owner), amount: BigInt(amount) };
}
const NOOP = row(0, 0, 0);

function toInput(rows) {
  return {
    kind: rows.map((r) => r.kind.toString()),
    owner: rows.map((r) => r.owner.toString()),
    amount: rows.map((r) => r.amount.toString()),
  };
}

async function inputs(outdir, alice, bob, carol) {
  const { buildPoseidon, poseidonContract } = require("circomlibjs");
  const poseidon = await buildPoseidon();
  const F = poseidon.F;
  const batches = {
    // two funded deposits, two no-op rows; settled extent = 2
    honest: [row(1, alice, 100), row(1, bob, 50), NOOP, NOOP],
    // a no-op row inside the settled extent, an unfunded deposit just past it
    fault: [NOOP, row(1, carol, 1000), NOOP, NOOP],
  };
  const expected = {};
  for (const [name, rows] of Object.entries(batches)) {
    if (rows.length !== N) throw new Error("bad batch size");
    const hashes = rows.map((r) => poseidon([r.kind, r.owner, r.amount]));
    const commitment = F.toObject(poseidon(hashes));
    const credit = rows.reduce((s, r) => s + r.amount, 0n);
    fs.writeFileSync(path.join(outdir, `${name}-input.json`), JSON.stringify(toInput(rows), null, 1) + "\n");
    expected[name] = { commitment: commitment.toString(), creditTotal: credit.toString() };
  }
  fs.writeFileSync(path.join(outdir, "expected.json"), JSON.stringify(expected, null, 1) + "\n");
  fs.writeFileSync(path.join(outdir, "poseidon3.hex"), poseidonContract.createCode(3) + "\n");
  fs.writeFileSync(path.join(outdir, "poseidon4.hex"), poseidonContract.createCode(4) + "\n");
}

function castargs(proofPath, publicPath, inputPath, numRealRows, tamper) {
  const proof = JSON.parse(fs.readFileSync(proofPath, "utf8"));
  const pub = JSON.parse(fs.readFileSync(publicPath, "utf8")); // [commitment, creditTotal]
  const inp = JSON.parse(fs.readFileSync(inputPath, "utf8"));
  const a = `[${proof.pi_a[0]},${proof.pi_a[1]}]`;
  // snarkjs G2 coordinates are (c0, c1); the Solidity verifier expects (c1, c0)
  const b = `[[${proof.pi_b[0][1]},${proof.pi_b[0][0]}],[${proof.pi_b[1][1]},${proof.pi_b[1][0]}]]`;
  const c = `[${proof.pi_c[0]},${proof.pi_c[1]}]`;
  let credit = BigInt(pub[1]);
  if (tamper === "tamper") credit += 1n;
  const out = [a, b, c, credit.toString(), `[${inp.kind.join(",")}]`, `[${inp.owner.join(",")}]`,
    `[${inp.amount.join(",")}]`, String(numRealRows)];
  process.stdout.write(out.join("\n") + "\n");
}

const [cmd, ...args] = process.argv.slice(2);
if (cmd === "inputs") {
  inputs(...args).then(() => process.exit(0), (e) => { console.error(e); process.exit(1); });
} else if (cmd === "castargs") {
  castargs(...args);
} else {
  console.error("usage: fixture.js inputs|castargs ...");
  process.exit(2);
}
