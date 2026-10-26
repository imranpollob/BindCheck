/** D1P-12R owned-local honest WarpToad proof-to-mint evidence harness. */
import { it } from "node:test";
import assert from "node:assert/strict";
import fs from "fs";
import os from "os";
import crypto from "crypto";
import { bytesToHex, encodeFunctionData, toHex } from "viem";

import { deployEvmContracts } from "./helpers/deploy-evm.js";
import {
  createCommitment,
  getTestFeeFactor,
} from "./helpers/setup.js";
import {
  DEFAULT_FEE,
  INITIAL_BALANCE,
  TEST_COMMITMENT_1,
} from "./helpers/constants.js";
import { createProof, getProofInputs } from "../lib/proving.js";

const P = 21888242871839275222246405745257275088548364400416034343698204186575808495617n;
const OUTPUT = process.env.D1P12R_RESULT!;
const PROOF_OUTPUT = process.env.D1P12R_PROOF!;
const RECEIPT_OUTPUT = process.env.D1P12R_RECEIPT!;
const CANONICALITY_OUTPUT = process.env.D1P12R_CANONICALITY!;
const ATTEMPT_MARKER = process.env.D1P12R_ATTEMPT_MARKER!;

function replacer(_key: string, value: unknown) {
  return typeof value === "bigint" ? value.toString() : value;
}

function writeJson(path: string, value: unknown) {
  fs.writeFileSync(path, JSON.stringify(value, replacer, 2) + "\n");
}

function digestHex(value: `0x${string}`) {
  return crypto.createHash("sha256").update(Buffer.from(value.slice(2), "hex")).digest("hex");
}

function errorRecord(error: any): any {
  if (!error) return null;
  return {
    name: error.name ?? null,
    shortMessage: error.shortMessage ?? null,
    details: error.details ?? null,
    message: String(error.message ?? error).slice(0, 12000),
    data: error.data ?? error.cause?.data ?? null,
    cause: error.cause && error.cause !== error ? errorRecord(error.cause) : null,
  };
}

const word = (value: bigint) => toHex(value, { size: 32 }).toLowerCase();

it("generates one real proof and executes the unchanged mint", async () => {
  const evidence: any = {
    schema: "bindcheck.d1p12r.execution/v1",
    startedAt: new Date().toISOString(),
    network: { kind: "Hardhat edr-simulated", fork: false, liveChain: false },
    stages: [],
  };
  try {
    const evm = await deployEvmContracts({ networkName: "edr" });
    const [deployer, relayer, sender, recipient] = evm.wallets;
    const publicClient = evm.publicClient;
    assert.ok(relayer.account.address.toLowerCase() !== "0x0000000000000000000000000000000000000001");
    evidence.accounts = {
      deployer: deployer.account.address,
      relayer: { name: "ordinary-local-relayer", address: relayer.account.address },
      sender: sender.account.address,
      recipient: recipient.account.address,
    };
    evidence.deployment = {
      privilegedInitialization: "deployer-only one-shot initialize performed by the pinned deployEvmContracts helper",
      fixedPreState: "fresh in-process EDR chain; freshly deployed token, generated verifier, WarpToad and GigaBridge; same-chain route",
      nativeToken: evm.nativeToken.address,
      verifier: evm.withdrawVerifier.address,
      warpToad: evm.l1WarpToad.address,
      gigaBridge: evm.gigaBridge.address,
      gigaRootProvider: await evm.l1WarpToad.read.gigaRootProvider(),
      l1BridgeAdapter: await evm.l1WarpToad.read.l1BridgeAdapter(),
      aztecWarptoadAddress: await evm.l1WarpToad.read.aztecWarptoadAddress(),
      chainId: await publicClient.getChainId(),
      crossChainReachabilityClaim: false,
    };
    evidence.stages.push("deployed-and-initialized");

    let hash = await evm.nativeToken.write.getFreeShit([INITIAL_BALANCE], { account: sender.account });
    await publicClient.waitForTransactionReceipt({ hash });
    hash = await evm.nativeToken.write.approve([evm.l1WarpToad.address, INITIAL_BALANCE], { account: sender.account });
    await publicClient.waitForTransactionReceipt({ hash });
    hash = await evm.l1WarpToad.write.wrap([INITIAL_BALANCE], { account: sender.account });
    await publicClient.waitForTransactionReceipt({ hash });

    const chainId = BigInt(await publicClient.getChainId());
    const commitment = createCommitment(
      TEST_COMMITMENT_1.amount, chainId, TEST_COMMITMENT_1.secret,
      TEST_COMMITMENT_1.nullifierPreimage,
    );
    hash = await evm.l1WarpToad.write.burn(
      [commitment.preCommitment, commitment.amount], { account: sender.account },
    );
    const burnReceipt = await publicClient.waitForTransactionReceipt({ hash });
    const feeFactor = getTestFeeFactor();
    assert.ok(feeFactor > 0n, "fixture requires a nonzero fee factor");
    const proofInputs = await getProofInputs(
      evm.gigaBridge, publicClient, evm.l1WarpToad, evm.l1WarpToad,
      commitment.amount, feeFactor, DEFAULT_FEE.priorityFee, DEFAULT_FEE.maxFee,
      relayer.account.address, recipient.account.address,
      commitment.nullifierPreimage, commitment.secret,
    );
    evidence.burn = {
      transactionHash: burnReceipt.transactionHash,
      blockNumber: burnReceipt.blockNumber,
      commitment,
      localRoot: await evm.l1WarpToad.read.cachedLocalRoot(),
      localRootStored: await evm.l1WarpToad.read.localRootHistory([await evm.l1WarpToad.read.cachedLocalRoot()]),
    };
    evidence.proofInputs = proofInputs;
    evidence.stages.push("honest-witness-constructed");

    writeJson(ATTEMPT_MARKER, {
      attemptedAt: new Date().toISOString(),
      operation: "pinned createProof(proofInputs, os.cpus().length)",
      threads: os.cpus().length,
      proofMode: "UltraHonk keccakZK:true",
      reason: "first honest proof attempt",
    });
    const proof = await createProof(proofInputs, os.cpus().length);
    const proofHex = bytesToHex(proof.proof);
    evidence.stages.push("proof-generated-and-js-verified");
    writeJson(PROOF_OUTPUT, {
      schema: "bindcheck.d1p12r.honest-proof/v1",
      proof: proofHex,
      proofSha256: digestHex(proofHex),
      proofBytes: proof.proof.length,
      publicInputs: proof.publicInputs,
      publicInputCount: proof.publicInputs.length,
      proofInputs,
    });

    assert.equal(proof.publicInputs.length, 11);
    const expectedWords = [
      BigInt(proofInputs.nullifier), BigInt(proofInputs.chain_id), BigInt(proofInputs.amount),
      BigInt(proofInputs.giga_root), BigInt(proofInputs.destination_local_root),
      BigInt(proofInputs.aztec_warptoad_address), BigInt(proofInputs.fee_factor),
      BigInt(proofInputs.priority_fee), BigInt(proofInputs.max_fee),
      BigInt(proofInputs.relayer_address), BigInt(proofInputs.recipient_address),
    ].map(word);
    assert.deepEqual(proof.publicInputs.map((x: string) => x.toLowerCase()), expectedWords);
    const consumerWords = await evm.l1WarpToad.read._formatPublicInputs([
      BigInt(proofInputs.nullifier), chainId, BigInt(proofInputs.amount),
      BigInt(proofInputs.giga_root), BigInt(proofInputs.destination_local_root),
      BigInt(proofInputs.aztec_warptoad_address), BigInt(proofInputs.fee_factor),
      BigInt(proofInputs.priority_fee), BigInt(proofInputs.max_fee),
      proofInputs.relayer_address, proofInputs.recipient_address,
    ]);
    assert.deepEqual(consumerWords.map((x: string) => x.toLowerCase()), expectedWords);

    const verifierAccepted = await evm.withdrawVerifier.read.verify([proofHex, proof.publicInputs]);
    assert.equal(verifierAccepted, true, "real generated verifier must accept the proof");
    evidence.verifier = { accepted: verifierAccepted, address: evm.withdrawVerifier.address };

    const canonicalResults: any[] = [];
    for (let index = 0; index < 11; index++) {
      for (const [boundary, value] of [["modulus", P], ["modulus_plus_one", P + 1n]] as const) {
        const mutated = [...proof.publicInputs];
        mutated[index] = word(value) as `0x${string}`;
        try {
          const returned = await evm.withdrawVerifier.read.verify([proofHex, mutated]);
          canonicalResults.push({ index, boundary, word: mutated[index], behavior: "returned", returned });
        } catch (error: any) {
          canonicalResults.push({ index, boundary, word: mutated[index], behavior: "reverted", error: errorRecord(error) });
        }
      }
    }
    writeJson(CANONICALITY_OUTPUT, {
      schema: "bindcheck.d1p12r.canonicality/v1",
      fieldModulus: P,
      generatedVerifier: evm.withdrawVerifier.address,
      honestProofAccepted: verifierAccepted,
      cases: canonicalResults,
    });
    assert.equal(canonicalResults.length, 22);
    assert.ok(canonicalResults.every((x) => x.behavior === "reverted"), "all noncanonical words must be rejected at the boundary");
    evidence.stages.push("canonicality-tested");

    const nullifier = BigInt(proofInputs.nullifier);
    const pre = {
      nullifierExists: await evm.l1WarpToad.read.nullifierExists([nullifier]),
      recipientBalance: await evm.l1WarpToad.read.balanceOf([recipient.account.address]),
      relayerBalance: await evm.l1WarpToad.read.balanceOf([relayer.account.address]),
      totalSupply: await evm.l1WarpToad.read.totalSupply(),
    };
    assert.equal(pre.nullifierExists, false);
    const mintArgs = [
      nullifier, BigInt(proofInputs.amount), BigInt(proofInputs.giga_root),
      BigInt(proofInputs.destination_local_root), BigInt(proofInputs.fee_factor),
      BigInt(proofInputs.priority_fee), BigInt(proofInputs.max_fee),
      proofInputs.relayer_address, proofInputs.recipient_address, proofHex,
    ] as const;
    const mintCalldata = encodeFunctionData({
      abi: evm.l1WarpToad.abi, functionName: "mint", args: mintArgs as any,
    });
    hash = await evm.l1WarpToad.write.mint(mintArgs as any, {
      account: relayer.account,
      maxPriorityFeePerGas: BigInt(proofInputs.priority_fee),
      maxFeePerGas: BigInt(proofInputs.priority_fee) * 100n,
    });
    const receipt = await publicClient.waitForTransactionReceipt({ hash });
    assert.equal(receipt.status, "success");
    const block = await publicClient.getBlock({ blockNumber: receipt.blockNumber });
    const baseFee = block.baseFeePerGas!;
    const computedRelayerFee = BigInt(proofInputs.fee_factor) * (baseFee + BigInt(proofInputs.priority_fee));
    const post = {
      nullifierExists: await evm.l1WarpToad.read.nullifierExists([nullifier]),
      recipientBalance: await evm.l1WarpToad.read.balanceOf([recipient.account.address]),
      relayerBalance: await evm.l1WarpToad.read.balanceOf([relayer.account.address]),
      totalSupply: await evm.l1WarpToad.read.totalSupply(),
    };
    assert.equal(post.nullifierExists, true);
    assert.equal(post.relayerBalance - pre.relayerBalance, computedRelayerFee);
    assert.equal(post.recipientBalance - pre.recipientBalance, commitment.amount - computedRelayerFee);
    assert.equal(post.totalSupply - pre.totalSupply, commitment.amount);
    writeJson(RECEIPT_OUTPUT, {
      schema: "bindcheck.d1p12r.mint-receipt/v1",
      receipt, block: { number: block.number, hash: block.hash, baseFeePerGas: baseFee },
      calldata: mintCalldata, calldataSha256: digestHex(mintCalldata), pre, post,
      effects: {
        nullifierConsumed: !pre.nullifierExists && post.nullifierExists,
        recipientDelta: post.recipientBalance - pre.recipientBalance,
        relayerDelta: post.relayerBalance - pre.relayerBalance,
        totalSupplyDelta: post.totalSupply - pre.totalSupply,
      },
      fees: {
        feeFactor: BigInt(proofInputs.fee_factor), priorityFee: BigInt(proofInputs.priority_fee),
        maxFee: BigInt(proofInputs.max_fee), baseFeePerGas: baseFee,
        computedRelayerFee, nonzeroFeeExample: computedRelayerFee > 0n,
      },
    });
    evidence.mint = { transactionHash: receipt.transactionHash, status: receipt.status, pre, post, computedRelayerFee };
    evidence.stages.push("actual-mint-succeeded");

    const replay: any = { identicalCalldata: true, calldataSha256: digestHex(mintCalldata) };
    try {
      const replayHash = await evm.l1WarpToad.write.mint(mintArgs as any, {
        account: relayer.account,
        maxPriorityFeePerGas: BigInt(proofInputs.priority_fee),
        maxFeePerGas: BigInt(proofInputs.priority_fee) * 100n,
      });
      replay.transactionHash = replayHash;
      replay.receipt = await publicClient.waitForTransactionReceipt({ hash: replayHash });
      replay.rejected = replay.receipt.status === "reverted";
    } catch (error: any) {
      replay.rejected = true;
      replay.error = errorRecord(error);
    }
    assert.equal(replay.rejected, true, "identical proof/calldata must be rejected on replay");
    assert.equal(await evm.l1WarpToad.read.nullifierExists([nullifier]), true);
    evidence.replay = replay;
    evidence.stages.push("same-proof-replay-rejected");
    evidence.finishedAt = new Date().toISOString();
    evidence.status = "PASS";
    writeJson(OUTPUT, evidence);
  } catch (error: any) {
    evidence.finishedAt = new Date().toISOString();
    evidence.status = "FAIL";
    evidence.error = errorRecord(error);
    writeJson(OUTPUT, evidence);
    throw error;
  }
});
