// Builds the honest T01 input independently of the circuit: commitments come
// from circomlibjs Poseidon, the relation is checked in plain BigInt.
// usage: node scripts/make_input.js <out_input.json> [wrong-sum]
// "wrong-sum" is a sanity control only: newBalance is off by one but newCommitment
// is recomputed for it, so only the sum relation is violated.
const fs = require("fs");
const { buildPoseidon } = require("circomlibjs");

const amount = [100n, 250n, 0n, 40n];
const active = [1n, 1n, 0n, 1n];
const oldBalance = 1000n;

(async () => {
  const poseidon = await buildPoseidon();
  const F = poseidon.F;
  const commit = (b) => F.toObject(poseidon([b])).toString();

  let sum = 0n;
  for (let i = 0; i < 4; i++) {
    if (active[i] !== 0n && active[i] !== 1n) throw new Error("active not Boolean");
    if (amount[i] < 0n || amount[i] >= 1n << 32n) throw new Error("amount out of u32");
    if (active[i] === 0n && amount[i] !== 0n) throw new Error("inactive row has amount");
    sum += active[i] * amount[i];
  }
  let newBalance = oldBalance + sum;
  if (process.argv[3] === "wrong-sum") newBalance += 1n;
  if (oldBalance >= 1n << 64n || newBalance >= 1n << 64n) throw new Error("balance out of u64");

  const input = {
    amount: amount.map(String),
    active: active.map(String),
    oldCommitment: commit(oldBalance),
    newCommitment: commit(newBalance),
    oldBalance: oldBalance.toString(),
    newBalance: newBalance.toString(),
  };
  fs.writeFileSync(process.argv[2], JSON.stringify(input, null, 2) + "\n");
  console.log(`oldBalance=${oldBalance} sum=${sum} newBalance=${newBalance}`);
})();
