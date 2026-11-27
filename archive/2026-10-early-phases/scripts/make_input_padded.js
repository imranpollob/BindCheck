// T05: second honest input for the SAME circuit: a padded batch [100,250,0,0], flags [1,1,0,0],
// balance 1000 -> 1350. Commitments from circomlibjs Poseidon; relation checked in plain BigInt.
// usage: node scripts/make_input_padded.js <out_input.json>
const fs = require("fs");
const { buildPoseidon } = require("circomlibjs");
const amount = [100n, 250n, 0n, 0n];
const active = [1n, 1n, 0n, 0n];
const oldBalance = 1000n;
(async () => {
  const poseidon = await buildPoseidon();
  const commit = (b) => poseidon.F.toObject(poseidon([b])).toString();
  let sum = 0n;
  for (let i = 0; i < 4; i++) {
    if (active[i] !== 0n && active[i] !== 1n) throw new Error("active not Boolean");
    if (amount[i] >= 1n << 32n) throw new Error("amount out of u32");
    if (active[i] === 0n && amount[i] !== 0n) throw new Error("inactive row has amount");
    sum += active[i] * amount[i];
  }
  const newBalance = oldBalance + sum;
  const input = {
    amount: amount.map(String), active: active.map(String),
    oldCommitment: commit(oldBalance), newCommitment: commit(newBalance),
    oldBalance: oldBalance.toString(), newBalance: newBalance.toString(),
  };
  fs.writeFileSync(process.argv[2], JSON.stringify(input, null, 2) + "\n");
  console.log(`oldBalance=${oldBalance} sum=${sum} newBalance=${newBalance}`);
  console.log(`oldCommitment=${input.oldCommitment}\nnewCommitment=${input.newCommitment}`);
})();
