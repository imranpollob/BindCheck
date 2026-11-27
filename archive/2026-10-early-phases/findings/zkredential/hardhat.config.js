require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: { enabled: true, runs: 200 },
      viaIR: true,
    },
  },
  networks: { hardhat: { chainId: 31337 } },
  paths: {
    sources: "./contracts-v2",
    tests: "./test",
    cache: "./cache-v2",
    artifacts: "./artifacts-v2",
  },
  mocha: { timeout: 200000 },
};
