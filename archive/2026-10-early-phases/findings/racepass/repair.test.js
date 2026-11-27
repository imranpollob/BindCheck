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

async function expectRejectedMint(pass, caller, args, reason) {
  await expect(pass.connect(caller).mintPass.staticCall(...args)).to.be.revertedWith(reason);
  const tx = await pass.connect(caller).mintPass(...args);
  let receipt;
  try {
    receipt = await tx.wait();
  } catch (error) {
    receipt = error.receipt;
  }
  expect(receipt.status).to.equal(0);
}

describe("RacePass credential/replay repair", function () {
  it("rejects unbound credential and replay while allowing one eligible mint", async function () {
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

    const fakeCredential = ethers.keccak256(ethers.toUtf8Bytes("attacker-selected-credential-1"));
    await expectRejectedMint(pass, attacker, [
      age.a, age.b, age.c, age.pub,
      kyc.a, kyc.b, kyc.c, kyc.pub,
      fakeCredential, "0x0000", attacker.address,
    ], "EventPass: credential mismatch");
    expect((await pass.config()).minted).to.equal(0n);

    const provedCredential = ethers.toBeHex(BigInt(kyc.pub[1]), 32);
    await expectRejectedMint(pass, attacker, [
      age.a, age.b, age.c, age.pub,
      kyc.a, kyc.b, kyc.c, kyc.pub,
      provedCredential, "0x0000", secondRecipient.address,
    ], "EventPass: recipient mismatch");
    expect((await pass.config()).minted).to.equal(0n);

    await (await pass.connect(attacker).mintPass(
      age.a, age.b, age.c, age.pub,
      kyc.a, kyc.b, kyc.c, kyc.pub,
      provedCredential, "0x0000", attacker.address,
    )).wait();
    expect(await pass.ownerOf(0n)).to.equal(attacker.address);
    expect(await pass.linkedCredential(0n)).to.equal(provedCredential);
    expect(await pass.isValid(0n, attacker.address)).to.deep.equal([true, "Valid"]);

    await expectRejectedMint(pass, attacker, [
      age.a, age.b, age.c, age.pub,
      kyc.a, kyc.b, kyc.c, kyc.pub,
      provedCredential, "0x0000", attacker.address,
    ], "EventPass: credential used");
    expect((await pass.config()).minted).to.equal(1n);

    const observation = {
      realVerifiersAccepted: true,
      mismatchedCredentialReverted: true,
      otherRecipientReverted: true,
      legitimateOwner: await pass.ownerOf(0n),
      linkedCredential: await pass.linkedCredential(0n),
      replayReverted: true,
      mintedAfter: (await pass.config()).minted.toString(),
    };
    fs.writeFileSync(process.env.RACEPASS_REPAIR_OBSERVATION, JSON.stringify(observation, null, 2) + "\n");
    console.log(JSON.stringify(observation));
  });
});
