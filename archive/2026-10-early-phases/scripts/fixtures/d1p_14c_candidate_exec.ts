/** D1P-14C V-EXEC consumer stage using the section 6(b) exact-vector stub. */
import { it } from "node:test";
import assert from "node:assert/strict";
import fs from "fs";
import { encodeAbiParameters, keccak256, toHex } from "viem";

import { deployEvmContracts } from "./helpers/deploy-evm.js";
import { deployFromArtifact } from "./helpers/artifacts.js";
import { createCommitment } from "./helpers/setup.js";
import { INITIAL_BALANCE, TEST_COMMITMENT_1 } from "./helpers/constants.js";

const INPUT = process.env.D1P14C_CANDIDATE!;
const OUTPUT = process.env.D1P14C_EXECUTION!;

function replacer(_key: string, value: unknown) {
  return typeof value === "bigint" ? value.toString() : value;
}

async function rpc(client: any, method: string, params: any[] = []) {
  return await client.request({ method, params });
}

it("executes the D1P-14C candidate against unchanged T_mint", async () => {
  const candidate = JSON.parse(fs.readFileSync(INPUT, "utf8"));
  const words = candidate.public_words.map((value: string) => BigInt(value));
  assert.equal(words.length, 11);
  const wordHex = words.map((value: bigint) => toHex(value, { size: 32 })) as `0x${string}`[];
  const vectorHash = keccak256(encodeAbiParameters([{ type: "bytes32[]" }], [wordHex]));

  const evm = await deployEvmContracts({ networkName: "edr" });
  const [_deployer, relayer, sender] = evm.wallets;
  assert.equal(relayer.account.address.toLowerCase(), candidate.msg_sender.toLowerCase());
  let hash = await evm.nativeToken.write.getFreeShit([INITIAL_BALANCE], { account: sender.account });
  await evm.publicClient.waitForTransactionReceipt({ hash });
  hash = await evm.nativeToken.write.approve([evm.l1WarpToad.address, INITIAL_BALANCE], { account: sender.account });
  await evm.publicClient.waitForTransactionReceipt({ hash });
  hash = await evm.l1WarpToad.write.wrap([INITIAL_BALANCE], { account: sender.account });
  await evm.publicClient.waitForTransactionReceipt({ hash });
  const chainId = BigInt(await evm.publicClient.getChainId());
  const commitment = createCommitment(TEST_COMMITMENT_1.amount, chainId, TEST_COMMITMENT_1.secret, TEST_COMMITMENT_1.nullifierPreimage);
  hash = await evm.l1WarpToad.write.burn([commitment.preCommitment, commitment.amount], { account: sender.account });
  await evm.publicClient.waitForTransactionReceipt({ hash });

  const stub = await deployFromArtifact("D1P14BVectorVerifier", [vectorHash], evm.deployer, evm.publicClient);
  const runtime = await evm.publicClient.getBytecode({ address: stub.address });
  assert.ok(runtime);
  await rpc(evm.publicClient, "hardhat_setCode", [evm.withdrawVerifier.address, runtime]);
  const configuredHash = await evm.publicClient.readContract({
    address: evm.withdrawVerifier.address, abi: stub.abi,
    functionName: "expectedVectorHash",
  });
  assert.equal(configuredHash, vectorHash);

  const basefee = BigInt(candidate.basefee);
  await rpc(evm.publicClient, "hardhat_setNextBlockBaseFeePerGas", [toHex(basefee)]);
  const args = [
    words[0], words[2], words[3], words[4], words[6], words[7], words[8],
    toHex(words[9], { size: 20 }), toHex(words[10], { size: 20 }), "0x",
  ] as const;
  const pre = {
    nullifier: await evm.l1WarpToad.read.nullifierExists([words[0]]),
    totalSupply: await evm.l1WarpToad.read.totalSupply(),
  };
  let error: any = null;
  let receipt: any = null;
  try {
    hash = await evm.l1WarpToad.write.mint(args as any, {
      account: relayer.account, maxPriorityFeePerGas: 0n,
      maxFeePerGas: basefee === (1n << 256n) - 1n ? basefee : basefee + 1n,
      gas: 12_000_000n,
    });
    receipt = await evm.publicClient.waitForTransactionReceipt({ hash });
  } catch (caught: any) {
    error = { name: caught?.name ?? null, shortMessage: caught?.shortMessage ?? null,
      details: caught?.details ?? null, message: String(caught?.message ?? caught).slice(0, 12000) };
  }
  const post = {
    nullifier: await evm.l1WarpToad.read.nullifierExists([words[0]]),
    totalSupply: await evm.l1WarpToad.read.totalSupply(),
  };
  fs.writeFileSync(OUTPUT, JSON.stringify({
    schema: "bindcheck.d1p14c.vexec-consumer/v1",
    exactVectorVerifier: { vectorHash, stubArtifact: "D1P14BVectorVerifier", proofIgnored: true },
    unchangedConsumer: true,
    candidate: { public_words: candidate.public_words, basefee: candidate.basefee, msg_sender: candidate.msg_sender },
    pre, post, receipt, error,
    accepted: receipt?.status === "success" && post.nullifier === true,
  }, replacer, 2) + "\n");
});
