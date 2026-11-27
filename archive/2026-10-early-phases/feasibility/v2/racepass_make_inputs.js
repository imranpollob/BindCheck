#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const { buildPoseidon } = require("circomlibjs");

async function main() {
  const output = process.argv[2];
  if (!output) throw new Error("usage: node racepass_make_inputs.js OUTPUT_DIR");
  fs.mkdirSync(output, { recursive: true });
  const poseidon = await buildPoseidon();
  const field = poseidon.F;
  const secret = 123456789n;
  const ageCommitment = field.toObject(poseidon([1990n, secret])).toString();
  const kycCommitment = field.toObject(poseidon([1n, secret])).toString();
  const age = {
    birthYear: "1990",
    credentialSecret: secret.toString(),
    currentYear: "2026",
    minAge: "18",
    credentialCommitment: ageCommitment,
  };
  const kyc = {
    kycStatus: "1",
    credentialSecret: secret.toString(),
    credentialHash: kycCommitment,
    revocationRoot: "0",
  };
  fs.writeFileSync(path.join(output, "age-input.json"), JSON.stringify(age, null, 2) + "\n");
  fs.writeFileSync(path.join(output, "kyc-input.json"), JSON.stringify(kyc, null, 2) + "\n");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
