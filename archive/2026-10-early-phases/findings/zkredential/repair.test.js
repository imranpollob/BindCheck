const fs = require("fs");
const crypto = require("crypto");
const { expect } = require("chai");
const { ethers } = require("hardhat");

function loadProof() {
  const proof = JSON.parse(fs.readFileSync(process.env.ZKREDENTIAL_PROOF, "utf8"));
  const pub = JSON.parse(fs.readFileSync(process.env.ZKREDENTIAL_PUBLIC, "utf8"));
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

describe("ZKredential repaired ComplianceGateway", function () {
  it("rejects the other caller and permits issuer-approved mint to the proof wallet", async function () {
    const [deployer, credentialOwner, attacker] = await ethers.getSigners();
    const realProof = loadProof();
    expect(realProof.pub).to.have.length(12);
    expect(realProof.pub[2]).to.equal("1");
    expect(BigInt(realProof.pub[10])).to.equal(BigInt(credentialOwner.address));
    expect(credentialOwner.address).to.not.equal(attacker.address);

    const Verifier = await ethers.getContractFactory("PropertyFyVerifier");
    const verifier = await Verifier.deploy();
    await verifier.waitForDeployment();
    expect(await verifier.verifyProof(realProof.a, realProof.b, realProof.c, realProof.pub)).to.equal(true);

    const Compliance = await ethers.getContractFactory("ZKComplianceModule");
    const compliance = await Compliance.deploy(await verifier.getAddress(), ethers.ZeroAddress, "propertyfy");
    await compliance.waitForDeployment();

    const Token = await ethers.getContractFactory("ZKRWATokenERC3643");
    const assetInfo = {
      name: "Local validation asset",
      description: "Synthetic owned-local asset",
      totalValue: 10n ** 35n,
      minInvestment: 1n,
      maxSupply: 10n ** 40n,
      platformName: "propertyfy",
      isActive: true,
    };
    const token = await Token.deploy(
      "Validation RWA",
      "VRWA",
      deployer.address,
      await compliance.getAddress(),
      deployer.address,
      assetInfo,
    );
    await token.waitForDeployment();

    const Gateway = await ethers.getContractFactory("ComplianceGateway");
    const gateway = await Gateway.deploy(
      await verifier.getAddress(),
      await verifier.getAddress(),
      await verifier.getAddress(),
      await token.getAddress(),
    );
    await gateway.waitForDeployment();
    await (await token.transferOwnership(await gateway.getAddress())).wait();

    const callerChosenAmount = 123456789012345678901234n;
    await (await gateway.approveMint(credentialOwner.address, callerChosenAmount)).wait();
    await expect(gateway.connect(attacker).verifyAndExecute(
      "propertyfy",
      realProof.a,
      realProof.b,
      realProof.c,
      realProof.pub,
      0,
      callerChosenAmount,
    )).to.be.revertedWith("proof wallet mismatch");
    expect(await token.balanceOf(attacker.address)).to.equal(0n);
    await expect(gateway.connect(credentialOwner).verifyAndExecute(
      "propertyfy", realProof.a, realProof.b, realProof.c, realProof.pub, 0, callerChosenAmount + 1n,
    )).to.be.revertedWith("mint not approved");
    expect(await token.balanceOf(credentialOwner.address)).to.equal(0n);
    await (await gateway.connect(credentialOwner).verifyAndExecute(
      "propertyfy", realProof.a, realProof.b, realProof.c, realProof.pub, 0, callerChosenAmount,
    )).wait();
    expect(await token.balanceOf(credentialOwner.address)).to.equal(callerChosenAmount);
    await expect(gateway.connect(attacker).verifyAndExecute(
      "propertyfy",
      realProof.a,
      realProof.b,
      realProof.c,
      realProof.pub,
      0,
      1n,
    )).to.be.revertedWith("Proof already used");

    const proofBytes = fs.readFileSync(process.env.ZKREDENTIAL_PROOF);
    const observation = {
      sourceCommit: process.env.ZKREDENTIAL_COMMIT,
      proofSha256: crypto.createHash("sha256").update(proofBytes).digest("hex"),
      proofWalletAddress: credentialOwner.address,
      rejectedCaller: attacker.address,
      legitimateMintRecipient: credentialOwner.address,
      issuerApprovedAmount: callerChosenAmount.toString(),
      attackerBalanceAfter: (await token.balanceOf(attacker.address)).toString(),
      credentialOwnerBalanceAfter: (await token.balanceOf(credentialOwner.address)).toString(),
      realVerifierAccepted: true,
      mismatchedCallerReverted: true,
      excessiveAmountReverted: true,
      legitimateMintCommitted: true,
    };
    fs.writeFileSync(process.env.ZKREDENTIAL_REPAIR_OBSERVATION, JSON.stringify(observation, null, 2) + "\n");
    console.log(JSON.stringify(observation));
  });
});
