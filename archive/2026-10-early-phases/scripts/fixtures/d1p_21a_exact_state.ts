/** D1P-21A exact-state honest controls for pinned, M-DOM, and M-SRC. */
import { it } from "node:test";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import { bytesToHex, keccak256, toHex } from "viem";
import { Barretenberg, UltraHonkBackend } from "@aztec/bb.js";
import { Noir } from "@noir-lang/noir_js";

import { deployEvmContracts } from "./helpers/deploy-evm.js";
import { createCommitment } from "./helpers/setup.js";
import { INITIAL_BALANCE } from "./helpers/constants.js";
import { sendGigaRoot, updateGigaRoot } from "../lib/bridging.js";
import { getGigaMerkleData } from "../lib/proving.js";
import { hashCommitment, hashNullifier } from "../lib/hashing.js";

const PAIRING = process.env.D1P21_PAIRING!;
const RESULT = process.env.D1P21_RESULT!;
const PROOF_RESULT = process.env.D1P21_PROOF_RESULT!;
const CANONICAL_STATE = process.env.D1P21_CANONICAL_STATE!;
const SDOM_SEED = process.env.D1P21_SDOM_SEED!;
const SSRC_ANCHOR = process.env.D1P21_SSRC_ANCHOR!;
const ARTIFACT = process.env.D1P21_ARTIFACT!;
const VK = process.env.D1P21_VK!;
const VERIFIER_SOURCE = process.env.D1P21_VERIFIER_SOURCE!;
const CONSUMER_SOURCE = process.env.D1P21_CONSUMER_SOURCE!;
const PREFLIGHT = process.env.D1P21_PREFLIGHT === "1";
if (!PAIRING || !RESULT || !PROOF_RESULT || !CANONICAL_STATE || !SDOM_SEED || !SSRC_ANCHOR ||
    !ARTIFACT || !VK || !VERIFIER_SOURCE || !CONSUMER_SOURCE) {
  throw new Error("D1P-21A fixture environment is incomplete");
}

const PAIRINGS: Record<string, { state: "S_DOM" | "S_SRC"; producer: "pinned" | "M-DOM"; consumer: "pinned" | "M-SRC" }> = {
  "pinned-sdom": { state: "S_DOM", producer: "pinned", consumer: "pinned" },
  "m-dom-sdom": { state: "S_DOM", producer: "M-DOM", consumer: "pinned" },
  "pinned-ssrc": { state: "S_SRC", producer: "pinned", consumer: "pinned" },
  "m-src-ssrc": { state: "S_SRC", producer: "pinned", consumer: "M-SRC" },
};
if (!(PAIRING in PAIRINGS)) throw new Error(`unknown pairing ${PAIRING}`);
const SPEC = PAIRINGS[PAIRING];
const CHAIN_ID = 31337n;
const PRIORITY_FEE = 100_000_000n;
const FIELD_MODULUS = 21888242871839275222246405745257275088548364400416034343698204186575808495617n;

const readJson = (path: string) => JSON.parse(fs.readFileSync(path, "utf8"));
const json = (path: string, value: unknown) => fs.writeFileSync(
  path, JSON.stringify(value, (_key, item) => typeof item === "bigint" ? item.toString() : item, 2) + "\n",
);
const sha256 = (bytes: Buffer | Uint8Array) => crypto.createHash("sha256").update(bytes).digest("hex");
const fileRecord = (path: string) => {
  const bytes = fs.readFileSync(path);
  return { path, sha256: sha256(bytes), bytes: bytes.length };
};
const word = (value: bigint) => toHex(value, { size: 32 }).toLowerCase();
const errorRecord = (error: any, depth = 0): any => !error || depth > 8 ? null : ({
  name: error.name ?? null,
  shortMessage: error.shortMessage ?? null,
  details: error.details ?? null,
  message: String(error.message ?? error).slice(0, 12000),
  data: error.data ?? error.cause?.data ?? null,
  cause: error.cause && error.cause !== error ? errorRecord(error.cause, depth + 1) : null,
});

async function balances(warpToad: any, recipient: string, relayer: string, nullifier: bigint) {
  return {
    nullifier: await warpToad.read.nullifierExists([nullifier]),
    recipient: await warpToad.read.balanceOf([recipient]),
    relayer: await warpToad.read.balanceOf([relayer]),
    supply: await warpToad.read.totalSupply(),
  };
}

async function buildSdom(state: any) {
  const s = state.S_DOM;
  const evm = await deployEvmContracts({
    networkName: "edr",
    aztecWarptoadAddress: BigInt(s.A_WT),
    d1p15SyntheticRoot: BigInt(s.aztecNoteTree.root),
    d1p21ExactSyntheticProvider: true,
  } as any);
  const [deployer, relayer, , recipient] = evm.wallets;
  assert.ok(evm.d1p15SyntheticRootProvider);
  assert.equal(await evm.l1WarpToad.read.cachedLocalRoot(), BigInt(s.l1LocalRootHistory[0]));
  assert.equal(await evm.l1WarpToad.read.localRootHistory([BigInt(s.l1LocalRootHistory[0])]), true);

  const providers = [evm.d1p15SyntheticRootProvider.address];
  const update = await updateGigaRoot(evm.publicClient, deployer, evm.gigaBridge, providers);
  assert.equal(update.gigaRootUpdateTx.status, "success");
  const gigaRoot = await evm.gigaBridge.read.gigaRoot();
  assert.equal(gigaRoot, BigInt(s.admittedGigaTree.root));
  const sent = await sendGigaRoot(
    evm.publicClient, deployer, evm.gigaBridge, [evm.l1WarpToad.address], [],
  );
  assert.equal(sent.sendGigaRootTx.status, "success");
  assert.equal(await evm.l1WarpToad.read.gigaRoot(), gigaRoot);
  assert.equal(await evm.l1WarpToad.read.gigaRootHistory([gigaRoot]), true);
  const gigaMerkleData = await getGigaMerkleData(
    evm.gigaBridge, evm.publicClient, BigInt(s.aztecNoteTree.root), 0n, 5,
    Number(update.gigaRootUpdateTx.blockNumber),
  );
  assert.deepEqual(
    gigaMerkleData.hash_path.map(BigInt), s.admittedGigaTree.path.map(BigInt),
  );

  const amount = BigInt(s.commitment.amount);
  const nullifier = BigInt(s.commitment.nullifier);
  const anchor = readJson(SDOM_SEED).proofInputs;
  const aztecMerkleData: any = {
    leaf_index: toHex(BigInt(s.notes.WarpToad.leafIndex)),
    hash_path: s.notes.WarpToad.path.map((item: string) => toHex(BigInt(item))),
    leaf_nonce: anchor.aztec_merkle_data.leaf_nonce,
  };
  if (SPEC.producer === "M-DOM") aztecMerkleData.contract_address = toHex(BigInt(s.A_WT));
  const proofInputs = {
    nullifier: toHex(nullifier), chain_id: toHex(CHAIN_ID), amount: toHex(amount),
    giga_root: toHex(gigaRoot), destination_local_root: toHex(BigInt(s.l1LocalRootHistory[0])),
    aztec_warptoad_address: toHex(BigInt(s.A_WT)), fee_factor: toHex(0n),
    priority_fee: toHex(PRIORITY_FEE), max_fee: toHex(amount),
    relayer_address: toHex(BigInt(relayer.account.address)),
    recipient_address: toHex(BigInt(recipient.account.address)),
    origin_local_root: toHex(BigInt(s.aztecNoteTree.root)), is_from_aztec: true,
    nullifier_preimage: anchor.nullifier_preimage, secret: anchor.secret,
    aztec_merkle_data: aztecMerkleData,
    evm_merkle_data: { leaf_index: toHex(0n), hash_path: Array(32).fill(toHex(0n)) },
    giga_merkle_data: gigaMerkleData,
  };
  return {
    evm, deployer, relayer, recipient, amount, nullifier, proofInputs,
    fixedState: {
      classification: s.classification,
      exactCanonicalState: "S_DOM",
      privilegedInitialization: "D1P-21A-only fixed root provider registered as sole GigaBridge provider at slot 0",
      provider: evm.d1p15SyntheticRootProvider.address,
      providerIndex: 0,
      noteRoot: BigInt(s.aztecNoteTree.root),
      gigaRoot,
      destinationLocalRoot: BigInt(s.l1LocalRootHistory[0]),
      updateReceipt: update.gigaRootUpdateTx,
      sendReceipt: sent.sendGigaRootTx,
      noCrossChainReachabilityClaim: true,
    },
  };
}

async function buildSsrc(state: any) {
  const s = state.S_SRC;
  const evm = await deployEvmContracts({ networkName: "edr" });
  const [deployer, relayer, sender, recipient] = evm.wallets;
  let tx = await evm.nativeToken.write.getFreeShit([INITIAL_BALANCE], { account: sender.account });
  await evm.publicClient.waitForTransactionReceipt({ hash: tx });
  tx = await evm.nativeToken.write.approve([evm.l1WarpToad.address, INITIAL_BALANCE], { account: sender.account });
  await evm.publicClient.waitForTransactionReceipt({ hash: tx });
  tx = await evm.l1WarpToad.write.wrap([INITIAL_BALANCE], { account: sender.account });
  await evm.publicClient.waitForTransactionReceipt({ hash: tx });

  const burnReceipts: any[] = [];
  for (const [index, burn] of s.burns.entries()) {
    const amount = BigInt(burn.amount);
    const commitment = createCommitment(amount, CHAIN_ID, BigInt(burn.secret), BigInt(burn.nullifierPreimage));
    const leaf = hashCommitment(commitment.preCommitment, amount);
    assert.equal(commitment.preCommitment, BigInt(burn.preCommitment));
    assert.equal(leaf, BigInt(burn.commitment));
    tx = await evm.l1WarpToad.write.burn([commitment.preCommitment, amount], { account: sender.account });
    const receipt = await evm.publicClient.waitForTransactionReceipt({ hash: tx });
    const root = await evm.l1WarpToad.read.cachedLocalRoot();
    assert.equal(root, BigInt(burn.root));
    assert.equal(await evm.l1WarpToad.read.localRootHistory([root]), true);
    burnReceipts.push({ index, receipt, root, commitment: leaf });
  }
  const first = s.burns[0];
  const amount = BigInt(first.amount);
  const nullifier = hashNullifier(BigInt(first.nullifierPreimage));
  const anchor = readJson(SSRC_ANCHOR).proofInputs;
  const gigaRoot = await evm.l1WarpToad.read.gigaRoot();
  assert.equal(gigaRoot, BigInt(anchor.giga_root));
  assert.equal(await evm.l1WarpToad.read.gigaRootHistory([gigaRoot]), true);
  const firstRoot = BigInt(s.firstTree.root);
  const proofInputs = {
    nullifier: toHex(nullifier), chain_id: toHex(CHAIN_ID), amount: toHex(amount),
    giga_root: toHex(gigaRoot), destination_local_root: toHex(firstRoot),
    aztec_warptoad_address: toHex(0n), fee_factor: toHex(0n),
    priority_fee: toHex(PRIORITY_FEE), max_fee: toHex(amount),
    relayer_address: toHex(BigInt(relayer.account.address)),
    recipient_address: toHex(BigInt(recipient.account.address)),
    origin_local_root: toHex(firstRoot), is_from_aztec: false,
    nullifier_preimage: toHex(BigInt(first.nullifierPreimage)), secret: toHex(BigInt(first.secret)),
    aztec_merkle_data: {
      leaf_index: toHex(0n), hash_path: Array(42).fill(toHex(0n)), leaf_nonce: toHex(0n),
    },
    evm_merkle_data: {
      leaf_index: toHex(BigInt(s.firstTree.leafIndex)),
      hash_path: s.firstTree.path.map((item: string) => toHex(BigInt(item))),
    },
    giga_merkle_data: { leaf_index: toHex(0n), hash_path: Array(5).fill(toHex(0n)) },
  };
  return {
    evm, deployer, relayer, recipient, amount, nullifier, proofInputs,
    fixedState: {
      classification: s.classification,
      exactCanonicalState: "S_SRC",
      privilegedInitialization: s.privilegedInitialization,
      actualBurnReceipts: burnReceipts,
      admittedRootHistory: s.admittedRootHistory.map(BigInt),
      finalCachedLocalRoot: await evm.l1WarpToad.read.cachedLocalRoot(),
      withdrawalOriginAndDestinationRoot: firstRoot,
      gigaRoot,
      noCrossChainReachabilityClaim: true,
    },
  };
}

it(`executes D1P-21A ${PAIRING}${PREFLIGHT ? " preflight" : " proof control"}`, async () => {
  const artifactBytes = fs.readFileSync(ARTIFACT);
  const artifact = JSON.parse(artifactBytes.toString("utf8"));
  const evidence: any = {
    schema: "bindcheck.d1p21a.exact-state-control/v1",
    pairing: PAIRING,
    state: SPEC.state,
    producer: SPEC.producer,
    consumer: SPEC.consumer,
    injected: SPEC.producer !== "pinned" || SPEC.consumer !== "pinned",
    mode: PREFLIGHT ? "preflight-no-proof" : "bounded-proof-attempt",
    network: { kind: "Hardhat edr-simulated", fork: false, liveChain: false },
    identities: {
      artifact: fileRecord(ARTIFACT), vk: fileRecord(VK),
      generatedVerifierSource: fileRecord(VERIFIER_SOURCE), consumerSource: fileRecord(CONSUMER_SOURCE),
    },
    proofGenerationAttempts: [],
  };
  let api: any = null;
  try {
    const state = readJson(CANONICAL_STATE);
    const setup = SPEC.state === "S_DOM" ? await buildSdom(state) : await buildSsrc(state);
    assert.equal(BigInt(await setup.evm.publicClient.getChainId()), CHAIN_ID);
    assert.notEqual(setup.relayer.account.address.toLowerCase(), "0x0000000000000000000000000000000000000001");
    assert.notEqual(setup.relayer.account.address.toLowerCase(), setup.recipient.account.address.toLowerCase());
    evidence.accounts = {
      relayer: { name: "ordinary-local-relayer", address: setup.relayer.account.address },
      recipient: setup.recipient.account.address,
    };
    evidence.fixedState = setup.fixedState;
    evidence.proofInputs = setup.proofInputs;
    const noir = new Noir(artifact);
    const execution = await noir.execute(setup.proofInputs as any);
    evidence.witnessSolved = true;
    if (PREFLIGHT) {
      evidence.status = "PASS";
      evidence.proofAttemptConsumed = false;
      evidence.note = "exact deployment/state assertions and Noir witness generation passed; no backend or proof generation invoked";
      json(RESULT, evidence);
      return;
    }

    const attempt: any = {
      attempt: 1,
      pairing: PAIRING,
      reason: `D1P-21A exact-state honest gate for ${PAIRING}`,
      startedAt: new Date().toISOString(),
      threads: os.cpus().length,
      parameterSearch: false,
    };
    evidence.proofGenerationAttempts.push(attempt);
    api = await Barretenberg.new({ threads: os.cpus().length });
    const backend = new UltraHonkBackend(artifact.bytecode, api);
    const proof = await backend.generateProof(execution.witness, { keccakZK: true });
    attempt.finishedAt = new Date().toISOString();
    attempt.outcome = "generated";
    const jsVerified = await backend.verifyProof(proof, { keccakZK: true });
    assert.equal(jsVerified, true);
    const proofHex = bytesToHex(proof.proof);
    const p = setup.proofInputs;
    const expectedWords = [
      setup.nullifier, CHAIN_ID, setup.amount, BigInt(p.giga_root), BigInt(p.destination_local_root),
      BigInt(p.aztec_warptoad_address), 0n, PRIORITY_FEE, setup.amount,
      BigInt(setup.relayer.account.address), BigInt(setup.recipient.account.address),
    ].map(word);
    assert.deepEqual(proof.publicInputs.map((item: string) => item.toLowerCase()), expectedWords);
    assert.ok(proof.publicInputs.every((item: string) => BigInt(item) < FIELD_MODULUS));
    const verifierAccepted = await setup.evm.withdrawVerifier.read.verify([proofHex, proof.publicInputs]);
    assert.equal(verifierAccepted, true);

    const pre = await balances(setup.evm.l1WarpToad, setup.recipient.account.address, setup.relayer.account.address, setup.nullifier);
    assert.equal(pre.nullifier, false);
    const tx = await setup.evm.l1WarpToad.write.mint([
      setup.nullifier, setup.amount, BigInt(p.giga_root), BigInt(p.destination_local_root),
      0n, PRIORITY_FEE, setup.amount, setup.relayer.account.address,
      setup.recipient.account.address, proofHex,
    ], { account: setup.relayer.account, maxPriorityFeePerGas: PRIORITY_FEE, maxFeePerGas: PRIORITY_FEE * 100n });
    const receipt = await setup.evm.publicClient.waitForTransactionReceipt({ hash: tx });
    assert.equal(receipt.status, "success");
    const post = await balances(setup.evm.l1WarpToad, setup.recipient.account.address, setup.relayer.account.address, setup.nullifier);
    const effects = {
      nullifierWritten: !pre.nullifier && post.nullifier,
      recipientDelta: post.recipient - pre.recipient,
      relayerDelta: post.relayer - pre.relayer,
      totalSupplyDelta: post.supply - pre.supply,
    };
    assert.deepEqual(effects, {
      nullifierWritten: true, recipientDelta: setup.amount, relayerDelta: 0n, totalSupplyDelta: setup.amount,
    });
    const verifierCode = await setup.evm.publicClient.getCode({ address: setup.evm.withdrawVerifier.address });
    const consumerCode = await setup.evm.publicClient.getCode({ address: setup.evm.l1WarpToad.address });
    assert.ok(verifierCode && verifierCode !== "0x" && consumerCode && consumerCode !== "0x");
    const proofRecord = {
      schema: "bindcheck.d1p21a.proof/v1", pairing: PAIRING,
      artifactSha256: sha256(artifactBytes), proof: proofHex,
      proofSha256: sha256(Buffer.from(proofHex.slice(2), "hex")), proofBytes: proof.proof.length,
      publicInputs: proof.publicInputs, proofInputs: setup.proofInputs,
      jsVerified, generatedVerifierAccepted: verifierAccepted,
    };
    json(PROOF_RESULT, proofRecord);
    evidence.execution = {
      verifierAccepted, receipt, pre, post, effects,
      fee: { feeFactor: 0n, priorityFee: PRIORITY_FEE, maxFee: setup.amount, computedRelayerFee: 0n },
      verifier: {
        address: setup.evm.withdrawVerifier.address,
        runtimeCodeKeccak256: keccak256(verifierCode),
        runtimeCodeSha256: sha256(Buffer.from(verifierCode.slice(2), "hex")),
      },
      consumer: {
        address: setup.evm.l1WarpToad.address,
        runtimeCodeKeccak256: keccak256(consumerCode),
        runtimeCodeSha256: sha256(Buffer.from(consumerCode.slice(2), "hex")),
      },
    };
    evidence.proof = { path: PROOF_RESULT, sha256: sha256(fs.readFileSync(PROOF_RESULT)), bytes: fs.statSync(PROOF_RESULT).size };
    evidence.status = "PASS";
    json(RESULT, evidence);
  } catch (error: any) {
    evidence.status = "FAIL";
    evidence.error = errorRecord(error);
    json(RESULT, evidence);
    throw error;
  } finally {
    if (api) await api.destroy();
  }
});
