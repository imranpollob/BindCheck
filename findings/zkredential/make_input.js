const fs = require("fs");

if (process.argv.length !== 3) {
  throw new Error("usage: node zkredential_make_input.js OUTPUT.json");
}

// Hardhat account #1. The E4 test submits from account #2 to establish that
// the proof's public walletAddress is not tied to the effect recipient.
const credentialOwner = BigInt("0x70997970C51812dc3A010C7d01b50e0d17dc79C8");
const input = {
  actualAge: "30",
  actualCountry: "1",
  kycLevel: "3",
  actualNetWorth: "1000000",
  actualLiquidAssets: "500000",
  isAccreditedInvestor: "1",
  incomeLast12Months: "250000",
  credentialHash: "12345",
  secret: "67890",
  minAge: "18",
  allowedCountry: "1",
  minKycLevel: "2",
  minNetWorth: "100000",
  minLiquidAssets: "100000",
  requireAccredited: "1",
  minIncome: "100000",
  walletAddress: credentialOwner.toString(),
  timestamp: "1793743200",
};
fs.writeFileSync(process.argv[2], JSON.stringify(input, null, 2) + "\n");
