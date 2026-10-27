/** D1P-14B fixed-S0 reconstruction. No proof generation and no live/fork RPC. */
import { it } from "node:test";
import assert from "node:assert/strict";
import fs from "fs";

import { deployEvmContracts } from "./helpers/deploy-evm.js";
import { createCommitment } from "./helpers/setup.js";
import { INITIAL_BALANCE, TEST_COMMITMENT_1 } from "./helpers/constants.js";

const OUTPUT = process.env.D1P14B_STATE!;

function replacer(_key: string, value: unknown) {
  return typeof value === "bigint" ? value.toString() : value;
}

it("reconstructs the exact D1P-12R pre-mint state", async () => {
  const evm = await deployEvmContracts({ networkName: "edr" });
  const [deployer, relayer, sender, recipient] = evm.wallets;
  const initialLocalRoot = await evm.l1WarpToad.read.cachedLocalRoot();
  const initialGigaRoot = await evm.l1WarpToad.read.gigaRoot();
  assert.equal(await evm.l1WarpToad.read.localRootHistory([initialLocalRoot]), true);
  assert.equal(await evm.l1WarpToad.read.gigaRootHistory([initialGigaRoot]), true);

  let hash = await evm.nativeToken.write.getFreeShit([INITIAL_BALANCE], { account: sender.account });
  await evm.publicClient.waitForTransactionReceipt({ hash });
  hash = await evm.nativeToken.write.approve([evm.l1WarpToad.address, INITIAL_BALANCE], { account: sender.account });
  await evm.publicClient.waitForTransactionReceipt({ hash });
  hash = await evm.l1WarpToad.write.wrap([INITIAL_BALANCE], { account: sender.account });
  await evm.publicClient.waitForTransactionReceipt({ hash });

  const chainId = BigInt(await evm.publicClient.getChainId());
  const commitment = createCommitment(
    TEST_COMMITMENT_1.amount, chainId, TEST_COMMITMENT_1.secret,
    TEST_COMMITMENT_1.nullifierPreimage,
  );
  hash = await evm.l1WarpToad.write.burn(
    [commitment.preCommitment, commitment.amount], { account: sender.account },
  );
  await evm.publicClient.waitForTransactionReceipt({ hash });
  const burnedLocalRoot = await evm.l1WarpToad.read.cachedLocalRoot();
  assert.equal(await evm.l1WarpToad.read.localRootHistory([burnedLocalRoot]), true);
  assert.equal(burnedLocalRoot, BigInt("20419743986860794548232381865258329306313806197552198584473571389746156968437"));
  assert.equal(initialGigaRoot, BigInt("19712377064642672829441595136074946683621277828620209496774504837737984048981"));

  const result = {
    schema: "bindcheck.d1p14b.fixed-s0/v1",
    network: { kind: "Hardhat edr-simulated", fork: false, liveChain: false, chainId },
    privilegedInitialization: "deployer-only one-shot initialize in pinned deployEvmContracts",
    accounts: {
      deployer: deployer.account.address,
      relayer: { name: "ordinary-local-relayer", address: relayer.account.address },
      sender: sender.account.address,
      recipient: recipient.account.address,
    },
    deployment: {
      nativeToken: evm.nativeToken.address,
      verifier: evm.withdrawVerifier.address,
      warpToad: evm.l1WarpToad.address,
      gigaBridge: evm.gigaBridge.address,
      aztecWarptoadAddress: await evm.l1WarpToad.read.aztecWarptoadAddress(),
    },
    giga_root_history: [initialGigaRoot],
    local_root_history: [initialLocalRoot, burnedLocalRoot],
    nullifiers: [],
    total_supply: await evm.l1WarpToad.read.totalSupply(),
    balances: {
      [relayer.account.address.toLowerCase()]: await evm.l1WarpToad.read.balanceOf([relayer.account.address]),
      [recipient.account.address.toLowerCase()]: await evm.l1WarpToad.read.balanceOf([recipient.account.address]),
      [sender.account.address.toLowerCase()]: await evm.l1WarpToad.read.balanceOf([sender.account.address]),
    },
    burn: { commitment, localRoot: burnedLocalRoot },
    proofGenerationCalls: 0,
  };
  fs.writeFileSync(OUTPUT, JSON.stringify(result, replacer, 2) + "\n");
});
