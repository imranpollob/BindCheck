/** D1P-14A owned-local WarpToad fee-cap execution harness. */
import { it } from "node:test";
import assert from "node:assert/strict";
import fs from "fs";
import os from "os";
import crypto from "crypto";
import { bytesToHex, encodeFunctionData, toHex } from "viem";

import { deployEvmContracts } from "./helpers/deploy-evm.js";
import { createCommitment, getTestFeeFactor } from "./helpers/setup.js";
import {
  DEFAULT_FEE,
  INITIAL_BALANCE,
  TEST_COMMITMENT_1,
  TEST_COMMITMENT_2,
} from "./helpers/constants.js";
import { createProof, getProofInputs } from "../lib/proving.js";

const MODE = process.env.D1P14A_MODE!;
const RESULT_OUTPUT = process.env.D1P14A_RESULT!;
const PROOF_OUTPUT = process.env.D1P14A_PROOF;
const POS_OUTPUT = process.env.D1P14A_POS;
const NEG_OUTPUT = process.env.D1P14A_NEG;
const ZERO_OUTPUT = process.env.D1P14A_ZERO;
const ATTEMPT_MARKER = process.env.D1P14A_ATTEMPT_MARKER;
const ATTEMPT_NUMBER = Number(process.env.D1P14A_ATTEMPT_NUMBER ?? "0");
const ATTEMPT_REASON = process.env.D1P14A_ATTEMPT_REASON ?? "";
const REUSE_PROOF = process.env.D1P14A_REUSE_PROOF;

const MAX_FEE = 1_000_000_000_000_000_000n;
const POS_BASE_FEE = 100_000_000n;
const NEG_BASE_FEE = 2_000_000_000n;
const TX_MAX_FEE = 10_000_000_000n;
const TX_GAS = 12_000_000n;

function replacer(_key: string, value: unknown) {
  return typeof value === "bigint" ? value.toString() : value;
}

function writeJson(path: string, value: unknown) {
  fs.writeFileSync(path, JSON.stringify(value, replacer, 2) + "\n");
}

function digestHex(value: `0x${string}`) {
  return crypto.createHash("sha256").update(Buffer.from(value.slice(2), "hex")).digest("hex");
}

function errorRecord(error: any, depth = 0): any {
  if (!error || depth > 8) return null;
  return {
    name: error.name ?? null,
    shortMessage: error.shortMessage ?? null,
    details: error.details ?? null,
    message: String(error.message ?? error).slice(0, 12000),
    data: error.data ?? error.cause?.data ?? null,
    cause: error.cause && error.cause !== error ? errorRecord(error.cause, depth + 1) : null,
  };
}

async function rpc(client: any, method: string, params: any[] = []) {
  return await client.request({ method, params });
}

async function setNextBaseFee(client: any, value: bigint) {
  await rpc(client, "hardhat_setNextBlockBaseFeePerGas", [toHex(value)]);
}

async function consumerState(evm: any, relayer: `0x${string}`, recipient: `0x${string}`, nullifier: bigint) {
  return {
    nullifierExists: await evm.l1WarpToad.read.nullifierExists([nullifier]),
    relayerTokenBalance: await evm.l1WarpToad.read.balanceOf([relayer]),
    recipientTokenBalance: await evm.l1WarpToad.read.balanceOf([recipient]),
    totalSupply: await evm.l1WarpToad.read.totalSupply(),
    backingTokenBalance: await evm.nativeToken.read.balanceOf([evm.l1WarpToad.address]),
    cachedLocalRoot: await evm.l1WarpToad.read.cachedLocalRoot(),
    gigaRoot: await evm.l1WarpToad.read.gigaRoot(),
  };
}

async function envelopeState(evm: any, relayer: `0x${string}`) {
  return {
    relayerNativeBalance: await evm.publicClient.getBalance({ address: relayer }),
    relayerTransactionCount: await evm.publicClient.getTransactionCount({ address: relayer }),
    blockNumber: await evm.publicClient.getBlockNumber(),
  };
}

async function setupHonestBurn(spec: typeof TEST_COMMITMENT_1, feeFactor: bigint) {
  const evm = await deployEvmContracts({ networkName: "edr" });
  const [deployer, relayer, sender, recipient] = evm.wallets;
  assert.notEqual(relayer.account.address.toLowerCase(), "0x0000000000000000000000000000000000000001");

  let hash = await evm.nativeToken.write.getFreeShit([INITIAL_BALANCE], { account: sender.account });
  await evm.publicClient.waitForTransactionReceipt({ hash });
  hash = await evm.nativeToken.write.approve([evm.l1WarpToad.address, INITIAL_BALANCE], { account: sender.account });
  await evm.publicClient.waitForTransactionReceipt({ hash });
  hash = await evm.l1WarpToad.write.wrap([INITIAL_BALANCE], { account: sender.account });
  await evm.publicClient.waitForTransactionReceipt({ hash });

  const chainId = BigInt(await evm.publicClient.getChainId());
  const commitment = createCommitment(spec.amount, chainId, spec.secret, spec.nullifierPreimage);
  hash = await evm.l1WarpToad.write.burn([commitment.preCommitment, commitment.amount], { account: sender.account });
  const burnReceipt = await evm.publicClient.waitForTransactionReceipt({ hash });
  assert.equal(burnReceipt.status, "success");

  const proofInputs = await getProofInputs(
    evm.gigaBridge,
    evm.publicClient,
    evm.l1WarpToad,
    evm.l1WarpToad,
    commitment.amount,
    feeFactor,
    DEFAULT_FEE.priorityFee,
    MAX_FEE,
    relayer.account.address,
    recipient.account.address,
    commitment.nullifierPreimage,
    commitment.secret,
  );
  return { evm, deployer, relayer, sender, recipient, chainId, commitment, burnReceipt, proofInputs };
}

async function generateProof(setup: any) {
  if (REUSE_PROOF) {
    const saved = JSON.parse(fs.readFileSync(REUSE_PROOF, "utf8"));
    assert.deepEqual(saved.proofInputs, setup.proofInputs, "reconstructed inputs must equal saved proof inputs");
    const proofHex = saved.proof as `0x${string}`;
    const proof = {
      proof: Uint8Array.from(Buffer.from(proofHex.slice(2), "hex")),
      publicInputs: saved.publicInputs,
    };
    const verifierAccepted = await setup.evm.withdrawVerifier.read.verify([proofHex, proof.publicInputs]);
    assert.equal(verifierAccepted, true, "generated verifier must accept the reused real proof");
    writeJson(PROOF_OUTPUT!, {
      schema: "bindcheck.d1p14a.reused-proof-validation/v1",
      mode: MODE,
      sourceProofPath: REUSE_PROOF,
      sourceProofSha256: digestHex(proofHex),
      proofBytes: proof.proof.length,
      publicInputCount: proof.publicInputs.length,
      reconstructedProofInputsExact: true,
      generatedVerifierAccepted: verifierAccepted,
      proofGenerationCalls: 0,
    });
    return { proof, proofHex, verifierAccepted };
  }
  assert.ok(ATTEMPT_MARKER, "attempt marker path is required");
  writeJson(ATTEMPT_MARKER!, {
    attemptedAt: new Date().toISOString(),
    attempt: ATTEMPT_NUMBER,
    operation: "pinned createProof(proofInputs, os.cpus().length)",
    threads: os.cpus().length,
    proofMode: "UltraHonk keccakZK:true",
    reason: ATTEMPT_REASON,
  });
  const proof = await createProof(setup.proofInputs, os.cpus().length);
  const proofHex = bytesToHex(proof.proof);
  assert.equal(proof.publicInputs.length, 11);
  const verifierAccepted = await setup.evm.withdrawVerifier.read.verify([proofHex, proof.publicInputs]);
  assert.equal(verifierAccepted, true, "generated verifier must accept the real proof");
  writeJson(PROOF_OUTPUT!, {
    schema: "bindcheck.d1p14a.proof/v1",
    mode: MODE,
    proof: proofHex,
    proofSha256: digestHex(proofHex),
    proofBytes: proof.proof.length,
    publicInputs: proof.publicInputs,
    publicInputCount: proof.publicInputs.length,
    proofInputs: setup.proofInputs,
    generatedVerifierAccepted: verifierAccepted,
  });
  return { proof, proofHex, verifierAccepted };
}

function mintArgs(setup: any, proofHex: `0x${string}`) {
  const p = setup.proofInputs;
  return [
    BigInt(p.nullifier), BigInt(p.amount), BigInt(p.giga_root),
    BigInt(p.destination_local_root), BigInt(p.fee_factor),
    BigInt(p.priority_fee), BigInt(p.max_fee), p.relayer_address,
    p.recipient_address, proofHex,
  ] as const;
}

async function runPreflight() {
  const evm = await deployEvmContracts({ networkName: "edr" });
  const before = await evm.publicClient.getBlockNumber();
  const snapshot = await rpc(evm.publicClient, "evm_snapshot");
  const probeBaseFee = 123_456_789n;
  await setNextBaseFee(evm.publicClient, probeBaseFee);
  await rpc(evm.publicClient, "evm_mine");
  const block = await evm.publicClient.getBlock({ blockTag: "latest" });
  assert.equal(block.baseFeePerGas, probeBaseFee);
  const reverted = await rpc(evm.publicClient, "evm_revert", [snapshot]);
  assert.equal(reverted, true);
  const after = await evm.publicClient.getBlockNumber();
  assert.equal(after, before);
  writeJson(RESULT_OUTPUT, {
    schema: "bindcheck.d1p14a.preflight/v1",
    status: "PASS",
    network: { kind: "Hardhat edr-simulated", fork: false, liveChain: false },
    checks: {
      snapshotAndRevert: true,
      setNextBlockBaseFeePerGas: true,
      requestedBaseFee: probeBaseFee,
      observedBaseFee: block.baseFeePerGas,
      blockNumberRestored: after === before,
    },
    proofGenerationCalls: 0,
  });
}

async function runFeeCap() {
  const evidence: any = {
    schema: "bindcheck.d1p14a.fee-cap-execution/v1",
    startedAt: new Date().toISOString(),
    network: { kind: "Hardhat edr-simulated", fork: false, liveChain: false },
    executionOrder: "FC-NEG then FC-POS, so the rejected call leaves the nullifier available and the successful mint remains in final state",
  };
  try {
    const feeFactor = getTestFeeFactor();
    assert.equal(feeFactor, 974_405_002n);
    assert.ok(MAX_FEE < TEST_COMMITMENT_1.amount);
    const setup = await setupHonestBurn(TEST_COMMITMENT_1, feeFactor);
    evidence.accounts = {
      deployer: setup.deployer.account.address,
      relayer: { name: "ordinary-local-relayer", address: setup.relayer.account.address },
      sender: setup.sender.account.address,
      recipient: setup.recipient.account.address,
    };
    evidence.deployment = {
      privilegedInitialization: "deployer-only one-shot initialize performed by the pinned deployEvmContracts helper",
      fixedPreState: "fresh in-process EDR chain; freshly deployed token, generated verifier, WarpToad and GigaBridge; same-chain route",
      nativeToken: setup.evm.nativeToken.address,
      verifier: setup.evm.withdrawVerifier.address,
      warpToad: setup.evm.l1WarpToad.address,
      gigaBridge: setup.evm.gigaBridge.address,
      chainId: setup.chainId,
      crossChainReachabilityClaim: false,
    };
    evidence.burn = {
      transactionHash: setup.burnReceipt.transactionHash,
      blockNumber: setup.burnReceipt.blockNumber,
      commitment: setup.commitment,
      localRoot: await setup.evm.l1WarpToad.read.cachedLocalRoot(),
    };
    evidence.proofInputs = setup.proofInputs;

    const { proof, proofHex, verifierAccepted } = await generateProof(setup);
    evidence.verifierAccepted = verifierAccepted;
    const args = mintArgs(setup, proofHex);
    const calldata = encodeFunctionData({ abi: setup.evm.l1WarpToad.abi, functionName: "mint", args: args as any });
    const calldataSha256 = digestHex(calldata);
    const nullifier = BigInt(setup.proofInputs.nullifier);

    // FC-NEG: only the next block base fee differs. Explicit gas ensures a real
    // reverting transaction is sent instead of stopping at client estimation.
    await setNextBaseFee(setup.evm.publicClient, NEG_BASE_FEE);
    const negPre = await consumerState(setup.evm, setup.relayer.account.address, setup.recipient.account.address, nullifier);
    const negEnvelopePre = await envelopeState(setup.evm, setup.relayer.account.address);
    const negHash = await setup.relayer.sendTransaction({
      account: setup.relayer.account,
      to: setup.evm.l1WarpToad.address,
      data: calldata,
      gas: TX_GAS,
      maxFeePerGas: TX_MAX_FEE,
      maxPriorityFeePerGas: DEFAULT_FEE.priorityFee,
    });
    const negReceipt = await setup.evm.publicClient.waitForTransactionReceipt({ hash: negHash });
    assert.equal(negReceipt.status, "reverted");
    const negBlock = await setup.evm.publicClient.getBlock({ blockNumber: negReceipt.blockNumber });
    assert.equal(negBlock.baseFeePerGas, NEG_BASE_FEE);
    const negComputedFee = feeFactor * (NEG_BASE_FEE + DEFAULT_FEE.priorityFee);
    assert.ok(negComputedFee > MAX_FEE);
    const negPost = await consumerState(setup.evm, setup.relayer.account.address, setup.recipient.account.address, nullifier);
    const negEnvelopePost = await envelopeState(setup.evm, setup.relayer.account.address);
    assert.deepEqual(negPost, negPre, "reverting FC-NEG must not change consumer state");
    let negCallError: any = null;
    try {
      await setup.evm.publicClient.call({
        account: setup.relayer.account.address,
        to: setup.evm.l1WarpToad.address,
        data: calldata,
        gas: TX_GAS,
      });
      assert.fail("FC-NEG replayed eth_call unexpectedly succeeded");
    } catch (error: any) {
      negCallError = errorRecord(error);
    }
    let trace: any = null;
    let traceError: any = null;
    try {
      trace = await rpc(setup.evm.publicClient, "debug_traceTransaction", [negHash, {
        disableMemory: true, disableStack: true, disableStorage: true,
      }]);
    } catch (error: any) {
      traceError = errorRecord(error);
    }
    const reasonHex = "5f72656c61796572466565206973206c6172676572207468616e205f6d6178466565";
    const callContainsExactReason = JSON.stringify(negCallError).includes("_relayerFee is larger than _maxFee");
    const traceContainsExactReason = JSON.stringify(trace).toLowerCase().includes(reasonHex);
    assert.ok(callContainsExactReason || traceContainsExactReason, "revert reason must be present in call error or transaction trace");
    writeJson(NEG_OUTPUT!, {
      schema: "bindcheck.d1p14a.fc-neg/v1",
      proofSha256: digestHex(proofHex),
      calldata,
      calldataSha256,
      receipt: negReceipt,
      block: { number: negBlock.number, hash: negBlock.hash, baseFeePerGas: negBlock.baseFeePerGas },
      proofBoundInputsUnchanged: {
        feeFactor: BigInt(setup.proofInputs.fee_factor),
        priorityFee: BigInt(setup.proofInputs.priority_fee),
        maxFee: BigInt(setup.proofInputs.max_fee),
      },
      computedRelayerFee: negComputedFee,
      capExceeded: negComputedFee > MAX_FEE,
      verifierAcceptedBeforeCall: verifierAccepted,
      exactRevertReason: "_relayerFee is larger than _maxFee",
      pinnedRevertLocation: "backend/contracts/core/WarpToadCore.sol:166",
      ethCallErrorAtLatestRevertedBlock: negCallError,
      debugTrace: trace,
      debugTraceError: traceError,
      exactRevertEvidence: { callContainsExactReason, traceContainsExactReason },
      consumerState: { pre: negPre, post: negPost, unchanged: true },
      transactionEnvelopeState: {
        pre: negEnvelopePre,
        post: negEnvelopePost,
        note: "A mined reverting transaction consumes sender nonce/native gas; these envelope effects are separate from the atomically unchanged consumer contract state.",
      },
    });

    // FC-POS: exact same proof and calldata, with only the local block base fee changed.
    await setNextBaseFee(setup.evm.publicClient, POS_BASE_FEE);
    const posPre = await consumerState(setup.evm, setup.relayer.account.address, setup.recipient.account.address, nullifier);
    const posHash = await setup.relayer.sendTransaction({
      account: setup.relayer.account,
      to: setup.evm.l1WarpToad.address,
      data: calldata,
      gas: TX_GAS,
      maxFeePerGas: TX_MAX_FEE,
      maxPriorityFeePerGas: DEFAULT_FEE.priorityFee,
    });
    const posReceipt = await setup.evm.publicClient.waitForTransactionReceipt({ hash: posHash });
    assert.equal(posReceipt.status, "success");
    const posBlock = await setup.evm.publicClient.getBlock({ blockNumber: posReceipt.blockNumber });
    assert.equal(posBlock.baseFeePerGas, POS_BASE_FEE);
    const computedRelayerFee = feeFactor * (POS_BASE_FEE + DEFAULT_FEE.priorityFee);
    assert.ok(computedRelayerFee > 0n);
    assert.ok(computedRelayerFee <= MAX_FEE);
    const posPost = await consumerState(setup.evm, setup.relayer.account.address, setup.recipient.account.address, nullifier);
    assert.equal(posPre.nullifierExists, false);
    assert.equal(posPost.nullifierExists, true);
    assert.equal(posPost.relayerTokenBalance - posPre.relayerTokenBalance, computedRelayerFee);
    assert.equal(posPost.recipientTokenBalance - posPre.recipientTokenBalance, setup.commitment.amount - computedRelayerFee);
    assert.equal(posPost.totalSupply - posPre.totalSupply, setup.commitment.amount);
    assert.equal(
      (posPost.relayerTokenBalance - posPre.relayerTokenBalance) +
      (posPost.recipientTokenBalance - posPre.recipientTokenBalance),
      setup.commitment.amount,
    );
    writeJson(POS_OUTPUT!, {
      schema: "bindcheck.d1p14a.fc-pos/v1",
      proofSha256: digestHex(proofHex),
      proofBytes: proof.proof.length,
      calldata,
      calldataSha256,
      sameProofAndCalldataAsFcNeg: true,
      receipt: posReceipt,
      block: { number: posBlock.number, hash: posBlock.hash, baseFeePerGas: posBlock.baseFeePerGas },
      verifierAcceptedBeforeCall: verifierAccepted,
      pre: posPre,
      post: posPost,
      effects: {
        nullifierConsumed: !posPre.nullifierExists && posPost.nullifierExists,
        relayerDelta: posPost.relayerTokenBalance - posPre.relayerTokenBalance,
        recipientDelta: posPost.recipientTokenBalance - posPre.recipientTokenBalance,
        totalSupplyDelta: posPost.totalSupply - posPre.totalSupply,
        conserved: (posPost.relayerTokenBalance - posPre.relayerTokenBalance) +
          (posPost.recipientTokenBalance - posPre.recipientTokenBalance) === setup.commitment.amount,
      },
      fees: {
        feeFactor,
        priorityFee: DEFAULT_FEE.priorityFee,
        maxFee: MAX_FEE,
        amount: setup.commitment.amount,
        maxFeeBelowAmount: MAX_FEE < setup.commitment.amount,
        baseFeePerGas: posBlock.baseFeePerGas,
        computedRelayerFee,
        nonzeroAndWithinCap: computedRelayerFee > 0n && computedRelayerFee <= MAX_FEE,
      },
    });
    evidence.identity = {
      proofSha256: digestHex(proofHex),
      calldataSha256,
      fcNegAndFcPosProofUnchanged: true,
      fcNegAndFcPosCalldataUnchanged: true,
    };
    evidence.fcNeg = { transactionHash: negReceipt.transactionHash, status: negReceipt.status, computedRelayerFee: negComputedFee };
    evidence.fcPos = { transactionHash: posReceipt.transactionHash, status: posReceipt.status, computedRelayerFee };
    evidence.status = "PASS";
    evidence.finishedAt = new Date().toISOString();
    writeJson(RESULT_OUTPUT, evidence);
  } catch (error: any) {
    evidence.status = "FAIL";
    evidence.error = errorRecord(error);
    evidence.finishedAt = new Date().toISOString();
    writeJson(RESULT_OUTPUT, evidence);
    throw error;
  }
}

async function runZeroFee() {
  const evidence: any = {
    schema: "bindcheck.d1p14a.zero-fee-execution/v1",
    startedAt: new Date().toISOString(),
    network: { kind: "Hardhat edr-simulated", fork: false, liveChain: false },
  };
  try {
    const setup = await setupHonestBurn(TEST_COMMITMENT_2, 0n);
    const { proof, proofHex, verifierAccepted } = await generateProof(setup);
    const args = mintArgs(setup, proofHex);
    const calldata = encodeFunctionData({ abi: setup.evm.l1WarpToad.abi, functionName: "mint", args: args as any });
    const nullifier = BigInt(setup.proofInputs.nullifier);
    await setNextBaseFee(setup.evm.publicClient, POS_BASE_FEE);
    const pre = await consumerState(setup.evm, setup.relayer.account.address, setup.recipient.account.address, nullifier);
    const hash = await setup.relayer.sendTransaction({
      account: setup.relayer.account,
      to: setup.evm.l1WarpToad.address,
      data: calldata,
      gas: TX_GAS,
      maxFeePerGas: TX_MAX_FEE,
      maxPriorityFeePerGas: DEFAULT_FEE.priorityFee,
    });
    const receipt = await setup.evm.publicClient.waitForTransactionReceipt({ hash });
    assert.equal(receipt.status, "success");
    const block = await setup.evm.publicClient.getBlock({ blockNumber: receipt.blockNumber });
    assert.equal(block.baseFeePerGas, POS_BASE_FEE);
    const post = await consumerState(setup.evm, setup.relayer.account.address, setup.recipient.account.address, nullifier);
    const relayerDelta = post.relayerTokenBalance - pre.relayerTokenBalance;
    const recipientDelta = post.recipientTokenBalance - pre.recipientTokenBalance;
    assert.equal(relayerDelta, 0n);
    assert.equal(recipientDelta, setup.commitment.amount);
    assert.equal(post.totalSupply - pre.totalSupply, setup.commitment.amount);
    assert.equal(pre.nullifierExists, false);
    assert.equal(post.nullifierExists, true);
    writeJson(ZERO_OUTPUT!, {
      schema: "bindcheck.d1p14a.zero-fee/v1",
      accounts: {
        relayer: { name: "ordinary-local-relayer", address: setup.relayer.account.address },
        sender: setup.sender.account.address,
        recipient: setup.recipient.account.address,
      },
      burn: { transactionHash: setup.burnReceipt.transactionHash, receipt: setup.burnReceipt, commitment: setup.commitment },
      proofSha256: digestHex(proofHex),
      proofBytes: proof.proof.length,
      proofInputs: setup.proofInputs,
      verifierAcceptedBeforeCall: verifierAccepted,
      calldata,
      calldataSha256: digestHex(calldata),
      receipt,
      block: { number: block.number, hash: block.hash, baseFeePerGas: block.baseFeePerGas },
      pre,
      post,
      effects: {
        nullifierConsumed: !pre.nullifierExists && post.nullifierExists,
        relayerDelta,
        recipientDelta,
        totalSupplyDelta: post.totalSupply - pre.totalSupply,
        noFeeMint: relayerDelta === 0n,
        conserved: relayerDelta + recipientDelta === setup.commitment.amount,
      },
    });
    evidence.status = "PASS";
    evidence.proofSha256 = digestHex(proofHex);
    evidence.transactionHash = receipt.transactionHash;
    evidence.verifierAccepted = verifierAccepted;
    evidence.finishedAt = new Date().toISOString();
    writeJson(RESULT_OUTPUT, evidence);
  } catch (error: any) {
    evidence.status = "FAIL";
    evidence.error = errorRecord(error);
    evidence.finishedAt = new Date().toISOString();
    writeJson(RESULT_OUTPUT, evidence);
    throw error;
  }
}

it(`runs D1P-14A mode ${MODE}`, async () => {
  if (MODE === "preflight") return await runPreflight();
  if (MODE === "fee-cap" || MODE === "fee-cap-resume") return await runFeeCap();
  if (MODE === "zero-fee") return await runZeroFee();
  throw new Error(`unknown D1P14A_MODE: ${MODE}`);
});
