// Confirms the public-signal order three ways rather than assuming it:
//   1. the .sym file names for witness indices 1..nPublic,
//   2. public.json values vs the values expected from input.json,
//   3. the verification key's nPublic / IC length.
// usage: node scripts/check_public_order.js <input.json> <public.json> <circuit.sym> <verification_key.json>
const fs = require("fs");
const [inputF, publicF, symF, vkF] = process.argv.slice(2);
const input = JSON.parse(fs.readFileSync(inputF));
const pub = JSON.parse(fs.readFileSync(publicF));
const vk = JSON.parse(fs.readFileSync(vkF));

const expectedNames = [
  ...[0, 1, 2, 3].map((i) => `main.amount[${i}]`),
  ...[0, 1, 2, 3].map((i) => `main.active[${i}]`),
  "main.oldCommitment",
  "main.newCommitment",
];
const expectedVals = [...input.amount, ...input.active, input.oldCommitment, input.newCommitment];

// .sym lines: labelIdx,witnessIdx,componentIdx,name
const byWitness = {};
for (const line of fs.readFileSync(symF, "utf8").split("\n")) {
  const p = line.split(",");
  if (p.length === 4 && Number(p[1]) >= 0) byWitness[Number(p[1])] = p[3];
}
const symNames = expectedNames.map((_, k) => byWitness[k + 1]);

const fail = [];
if (JSON.stringify(symNames) !== JSON.stringify(expectedNames)) fail.push(`sym order mismatch: ${symNames}`);
if (JSON.stringify(pub) !== JSON.stringify(expectedVals)) fail.push("public.json values differ from expected order");
if (vk.nPublic !== expectedNames.length) fail.push(`vk.nPublic=${vk.nPublic}`);
if (vk.IC.length !== expectedNames.length + 1) fail.push(`vk.IC.length=${vk.IC.length}`);

console.log("idx | witness idx | sym name | public.json value");
expectedNames.forEach((n, k) => console.log(`${k} | ${k + 1} | ${symNames[k]} | ${pub[k]}`));
console.log(`vk.protocol=${vk.protocol} vk.curve=${vk.curve} vk.nPublic=${vk.nPublic} vk.IC.length=${vk.IC.length}`);
if (fail.length) { console.error("FAIL:\n" + fail.join("\n")); process.exit(1); }
console.log("PUBLIC ORDER CHECK: OK");
