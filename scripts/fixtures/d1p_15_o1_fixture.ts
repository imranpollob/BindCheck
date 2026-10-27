/** D1P-15 injected M-DOM concrete V-EXEC gate. */
import { it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import crypto from "node:crypto";
import { bytesToHex, keccak256, toHex } from "viem";
import { Barretenberg, UltraHonkBackend } from "@aztec/bb.js";
import { Noir } from "@noir-lang/noir_js";

import { deployEvmContracts } from "./helpers/deploy-evm.js";
import { sendGigaRoot, updateGigaRoot } from "../lib/bridging.js";
import { getGigaMerkleData } from "../lib/proving.js";
import {
  buildAztecNoteTree,
  hashBn1,
  hashBn2,
  hashBn3,
} from "../lib/d1p15-hash-reference.js";

const RESULT = process.env.D1P15_RESULT!;
const HONEST_PROOF = process.env.D1P15_HONEST_PROOF!;
const FOREIGN_PROOF = process.env.D1P15_FOREIGN_PROOF!;
const PINNED_ARTIFACT = process.env.D1P15_PINNED_ARTIFACT!;
const MUTATION_ARTIFACT = process.env.D1P15_MUTATION_ARTIFACT!;
if (!RESULT || !HONEST_PROOF || !FOREIGN_PROOF || !PINNED_ARTIFACT || !MUTATION_ARTIFACT) {
  throw new Error("D1P-15 fixture environment is incomplete");
}

const A_WT = 0x123456789abcdefn;
const A_X = 0xfedcba987654321n;
const NOTE_NONCE = 0xabcden;
const NULLIFIER_PREIMAGE = 0x10e1n;
const SECRET = 0x4d2n;
const AMOUNT = 5_000_000_000_000_000_000n;
const PRIORITY_FEE = 100_000_000n;
const AZTEC_DEPTH = 42;
const EVM_DEPTH = 32;
const GIGA_DEPTH = 5;

const sha256Bytes = (bytes: Buffer | Uint8Array) => crypto.createHash("sha256").update(bytes).digest("hex");
const json = (path: string, value: unknown) => fs.writeFileSync(path, JSON.stringify(value, (_, item) => typeof item === "bigint" ? item.toString() : item, 2) + "\n");
const word = (value: bigint) => toHex(value, { size: 32 }).toLowerCase();
const errorRecord = (error: any, depth = 0): any => !error || depth > 8 ? null : ({
  name: error.name ?? null,
  shortMessage: error.shortMessage ?? null,
  details: error.details ?? null,
  message: String(error.message ?? error).slice(0, 12000),
  data: error.data ?? error.cause?.data ?? null,
  cause: error.cause && error.cause !== error ? errorRecord(error.cause, depth + 1) : null,
});

async function constructCase(noteContractAddress: bigint) {
  const chainId = 31337n;
  const preCommitment = hashBn3(NULLIFIER_PREIMAGE, SECRET, chainId);
  const commitment = hashBn2(preCommitment, AMOUNT);
  const nullifier = hashBn1(NULLIFIER_PREIMAGE);
  const aztecTree = buildAztecNoteTree(
    commitment, noteContractAddress, NOTE_NONCE, 0n, Array(AZTEC_DEPTH).fill(0n),
  );
  const evm = await deployEvmContracts({
    networkName: "edr",
    aztecWarptoadAddress: A_WT,
    d1p15SyntheticRoot: aztecTree.root,
  });
  const [deployer, relayer, , recipient] = evm.wallets;
  assert.notEqual(relayer.account.address.toLowerCase(), "0x0000000000000000000000000000000000000001");
  assert.notEqual(relayer.account.address.toLowerCase(), recipient.account.address.toLowerCase());
  assert.equal(BigInt(await evm.publicClient.getChainId()), chainId);
  assert.equal(await evm.l1WarpToad.read.aztecWarptoadAddress(), A_WT);
  assert.ok(evm.d1p15SyntheticRootProvider);

  const providers = [evm.l1WarpToad.address, evm.d1p15SyntheticRootProvider.address];
  const update = await updateGigaRoot(evm.publicClient, deployer, evm.gigaBridge, providers);
  assert.equal(update.gigaRootUpdateTx.status, "success");
  const gigaRoot = await evm.gigaBridge.read.gigaRoot();
  const sent = await sendGigaRoot(
    evm.publicClient, deployer, evm.gigaBridge, [evm.l1WarpToad.address], [],
  );
  assert.equal(sent.sendGigaRootTx.status, "success");
  assert.equal(await evm.l1WarpToad.read.gigaRoot(), gigaRoot);
  assert.equal(await evm.l1WarpToad.read.gigaRootHistory([gigaRoot]), true);
  const destinationLocalRoot = await evm.l1WarpToad.read.cachedLocalRoot();
  assert.equal(await evm.l1WarpToad.read.localRootHistory([destinationLocalRoot]), true);
  const gigaMerkleData = await getGigaMerkleData(
    evm.gigaBridge,
    evm.publicClient,
    aztecTree.root,
    1n,
    GIGA_DEPTH,
    Number(update.gigaRootUpdateTx.blockNumber),
  );

  const proofInputs = {
    nullifier: toHex(nullifier),
    chain_id: toHex(chainId),
    amount: toHex(AMOUNT),
    giga_root: toHex(gigaRoot),
    destination_local_root: toHex(destinationLocalRoot),
    aztec_warptoad_address: toHex(A_WT),
    fee_factor: toHex(0n),
    priority_fee: toHex(PRIORITY_FEE),
    max_fee: toHex(AMOUNT),
    relayer_address: toHex(BigInt(relayer.account.address)),
    recipient_address: toHex(BigInt(recipient.account.address)),
    origin_local_root: toHex(aztecTree.root),
    is_from_aztec: true,
    nullifier_preimage: toHex(NULLIFIER_PREIMAGE),
    secret: toHex(SECRET),
    aztec_merkle_data: {
      leaf_index: toHex(0n),
      hash_path: Array(AZTEC_DEPTH).fill(toHex(0n)),
      leaf_nonce: toHex(NOTE_NONCE),
      contract_address: toHex(noteContractAddress),
    },
    evm_merkle_data: { leaf_index: toHex(0n), hash_path: Array(EVM_DEPTH).fill(toHex(0n)) },
    giga_merkle_data: gigaMerkleData,
  };
  return {
    evm, deployer, relayer, recipient, preCommitment, commitment, nullifier,
    aztecTree, update, sent, gigaRoot, destinationLocalRoot, proofInputs,
  };
}

async function executeMint(setup: any, proofHex: `0x${string}`) {
  const p = setup.proofInputs;
  const pre = {
    nullifier: await setup.evm.l1WarpToad.read.nullifierExists([setup.nullifier]),
    recipient: await setup.evm.l1WarpToad.read.balanceOf([setup.recipient.account.address]),
    relayer: await setup.evm.l1WarpToad.read.balanceOf([setup.relayer.account.address]),
    supply: await setup.evm.l1WarpToad.read.totalSupply(),
  };
  const args = [
    setup.nullifier, AMOUNT, setup.gigaRoot, setup.destinationLocalRoot,
    0n, PRIORITY_FEE, AMOUNT, setup.relayer.account.address,
    setup.recipient.account.address, proofHex,
  ] as const;
  const hash = await setup.evm.l1WarpToad.write.mint(args as any, {
    account: setup.relayer.account,
    maxPriorityFeePerGas: PRIORITY_FEE,
    maxFeePerGas: PRIORITY_FEE * 100n,
  });
  const receipt = await setup.evm.publicClient.waitForTransactionReceipt({ hash });
  assert.equal(receipt.status, "success");
  const post = {
    nullifier: await setup.evm.l1WarpToad.read.nullifierExists([setup.nullifier]),
    recipient: await setup.evm.l1WarpToad.read.balanceOf([setup.recipient.account.address]),
    relayer: await setup.evm.l1WarpToad.read.balanceOf([setup.relayer.account.address]),
    supply: await setup.evm.l1WarpToad.read.totalSupply(),
  };
  assert.equal(pre.nullifier, false);
  assert.equal(post.nullifier, true);
  assert.equal(post.recipient - pre.recipient, AMOUNT);
  assert.equal(post.relayer - pre.relayer, 0n);
  assert.equal(post.supply - pre.supply, AMOUNT);
  return { receipt, pre, post, effects: { nullifierWritten: true, recipientDelta: AMOUNT, relayerDelta: 0n, totalSupplyDelta: AMOUNT } };
}

it("passes the injected honest and foreign-contract concrete gates", async () => {
  const mutationBytes = fs.readFileSync(MUTATION_ARTIFACT);
  const pinnedBytes = fs.readFileSync(PINNED_ARTIFACT);
  const mutationArtifact = JSON.parse(mutationBytes.toString("utf8"));
  const pinnedArtifact = JSON.parse(pinnedBytes.toString("utf8"));
  const mutationNoir = new Noir(mutationArtifact);
  const pinnedNoir = new Noir(pinnedArtifact);
  const api = await Barretenberg.new({ threads: os.cpus().length });
  const backend = new UltraHonkBackend(mutationArtifact.bytecode, api);
  const evidence: any = {
    schema: "bindcheck.d1p15.o1-injected-execution/v1",
    injected: true,
    mutation: "M-DOM: private note contract_address replaces public consumer-fixed address in silo hash",
    network: { kind: "Hardhat edr-simulated", fork: false, liveChain: false },
    configuredWarpToadAddress: A_WT,
    foreignContractAddress: A_X,
    artifacts: {
      mutation: { path: MUTATION_ARTIFACT, sha256: sha256Bytes(mutationBytes), noirVersion: mutationArtifact.noir_version },
      pinned: { path: PINNED_ARTIFACT, sha256: sha256Bytes(pinnedBytes), noirVersion: pinnedArtifact.noir_version },
    },
    proofGenerationAttempts: [],
    cases: {},
  };
  try {
    for (const [name, noteContractAddress] of [["honest", A_WT], ["foreign", A_X]] as const) {
      const setup = await constructCase(noteContractAddress);
      const pinnedExecution: any = { expected: name === "honest" ? "accept" : "reject" };
      try {
        await pinnedNoir.execute(setup.proofInputs as any);
        pinnedExecution.outcome = "accepted";
      } catch (error: any) {
        pinnedExecution.outcome = "rejected";
        pinnedExecution.error = errorRecord(error);
      }
      assert.equal(pinnedExecution.outcome, name === "honest" ? "accepted" : "rejected");

      const attempt = {
        attempt: evidence.proofGenerationAttempts.length + 1,
        case: name,
        reason: name === "honest" ? "M-DOM honest-note mint gate" : "M-DOM foreign-contract V-EXEC differential gate",
        startedAt: new Date().toISOString(),
      };
      evidence.proofGenerationAttempts.push(attempt);
      const execution = await mutationNoir.execute(setup.proofInputs as any);
      const proof = await backend.generateProof(execution.witness, { keccakZK: true });
      const jsVerified = await backend.verifyProof(proof, { keccakZK: true });
      assert.equal(jsVerified, true);
      const proofHex = bytesToHex(proof.proof);
      const expectedWords = [
        setup.nullifier, 31337n, AMOUNT, setup.gigaRoot, setup.destinationLocalRoot,
        A_WT, 0n, PRIORITY_FEE, AMOUNT,
        BigInt(setup.relayer.account.address), BigInt(setup.recipient.account.address),
      ].map(word);
      assert.deepEqual(proof.publicInputs.map((value: string) => value.toLowerCase()), expectedWords);
      const verifierAccepted = await setup.evm.withdrawVerifier.read.verify([proofHex, proof.publicInputs]);
      assert.equal(verifierAccepted, true);
      const mint = await executeMint(setup, proofHex);
      const verifierCode = await setup.evm.publicClient.getCode({ address: setup.evm.withdrawVerifier.address });
      assert.ok(verifierCode && verifierCode !== "0x");
      const proofRecord = {
        schema: "bindcheck.d1p15.injected-proof/v1",
        injected: true,
        case: name,
        proof: proofHex,
        proofSha256: sha256Bytes(Buffer.from(proofHex.slice(2), "hex")),
        proofBytes: proof.proof.length,
        publicInputs: proof.publicInputs,
        proofInputs: setup.proofInputs,
        jsVerified,
        generatedVerifierAccepted: verifierAccepted,
      };
      json(name === "honest" ? HONEST_PROOF : FOREIGN_PROOF, proofRecord);
      evidence.cases[name] = {
        noteContractAddress,
        relationshipToConfiguredAddress: noteContractAddress === A_WT ? "equal" : "distinct",
        preCommitment: setup.preCommitment,
        commitment: setup.commitment,
        nullifier: setup.nullifier,
        aztecTree: {
          siloed: setup.aztecTree.siloed,
          unique: setup.aztecTree.unique,
          root: setup.aztecTree.root,
          leafIndex: setup.aztecTree.leafIndex,
          depth: setup.aztecTree.path.length,
        },
        rootAdmission: {
          classification: "D1P-15-only synthetic fixed-state provider registered at GigaBridge construction",
          privilegedInitialization: true,
          provider: setup.evm.d1p15SyntheticRootProvider.address,
          providerIndex: 1,
          updateReceipt: setup.update.gigaRootUpdateTx,
          sendReceipt: setup.sent.sendGigaRootTx,
          gigaRoot: setup.gigaRoot,
          destinationLocalRoot: setup.destinationLocalRoot,
          noCrossChainReachabilityClaim: true,
        },
        accounts: {
          relayer: { name: "ordinary-local-relayer", address: setup.relayer.account.address },
          recipient: setup.recipient.account.address,
        },
        pinnedExecution,
        mutationExecution: { witnessSolved: true, jsVerified, verifierAccepted },
        verifier: {
          address: setup.evm.withdrawVerifier.address,
          runtimeCodeKeccak256: keccak256(verifierCode),
          runtimeCodeSha256: sha256Bytes(Buffer.from(verifierCode.slice(2), "hex")),
          runtimeCodeBytes: (verifierCode.length - 2) / 2,
        },
        mint,
      };
    }
    evidence.status = "PASS";
    evidence.gates = {
      honestMutationMint: evidence.cases.honest.mint.receipt.status === "success",
      foreignMutationVExec: evidence.cases.foreign.mint.receipt.status === "success",
      foreignPinnedRejects: evidence.cases.foreign.pinnedExecution.outcome === "rejected",
      ownGeneratedVerifierExecuted: evidence.cases.honest.mutationExecution.verifierAccepted &&
        evidence.cases.foreign.mutationExecution.verifierAccepted &&
        evidence.cases.honest.verifier.runtimeCodeBytes > 0 && evidence.cases.foreign.verifier.runtimeCodeBytes > 0,
      linkedRuntimeHashesDifferAcrossDeployments:
        evidence.cases.honest.verifier.runtimeCodeKeccak256 !== evidence.cases.foreign.verifier.runtimeCodeKeccak256,
      runtimeHashNote: "Expected difference: each verifier runtime links freshly deployed transcript/relation library addresses; source/VK identity is recorded separately.",
    };
    json(RESULT, evidence);
  } catch (error: any) {
    evidence.status = "FAIL";
    evidence.error = errorRecord(error);
    json(RESULT, evidence);
    throw error;
  } finally {
    await api.destroy();
  }
});
