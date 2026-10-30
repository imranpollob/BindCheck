import { defineConfig } from "hardhat/config";
import hardhatToolboxViem from "@nomicfoundation/hardhat-toolbox-viem";

// Minimal config for automatic-validation replays. The build dir provides:
// contracts/ (app sources + verifier.sol + MockGigaProvider.sol),
// node_modules/ (symlinked reference tree for OZ/zk-kit/poseidon deps).
export default defineConfig({
  plugins: [hardhatToolboxViem],
  solidity: {
    version: "0.8.29",
    path: process.env.BINDCHECK_SOLC_0_8_29,
    settings: { optimizer: { enabled: true, runs: 1 } },
  },
  paths: { sources: "./contracts", tests: "./xav-tests", cache: "./hh-cache", artifacts: "./hh-artifacts" },
});
