/** Payy consumer replay (mock-verifier-scoped E2, explicitly NOT E4).
 *
 * The project's own eth tests deploy MockVerifier with "0x00" proofs; this
 * harness reuses that pattern to exercise CONSUMER-side defects (mint
 * admission, single-use, burn-recipient binding, dead-kind activation).
 * The mock stands in for proof acceptance, which is orthogonal to these
 * defects; every row is labeled E2 (mock-verifier-scoped), never E4.
 *
 * Env: XAV_PAYY_PLAN (JSON), XAV_PAYY_REPORT (JSON out).
 * Plan: { label, consumer: {abi, bytecode}, mockUsdc: {abi, bytecode},
 *   mockVerifier: {abi, bytecode}, noteKind, vkHash, messagesLen,
 *   validatorKey, actions: [...] }
 * Actions: {register:{hash,value}} | {settle:{height,oldRoot,newRoot,commitHash,otherHash,words:[...]}} |
 *   {fund:{to,value}} | {approve:{spender,value}}
 * Anvil endpoint via XAV_ANVIL_URL. Deployer holds MockUSDC supply.
 */
import fs from "node:fs";
import { createPublicClient, createWalletClient, http, encodeFunctionData, type Address, type Hex } from "viem";
import { privateKeyToAccount } from "viem/accounts";

const plan = JSON.parse(fs.readFileSync(process.env.XAV_PAYY_PLAN!, "utf8"));
const report: any = { label: plan.label, verifier: "MockVerifier (project test mock; NOT the pinned verifier)", steps: [], state: {} };
const anvil = process.env.XAV_ANVIL_URL!;
const deployer = privateKeyToAccount("0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80" as Hex);
const publicClient: any = createPublicClient({ transport: http(anvil) });
const wallet: any = createWalletClient({ transport: http(anvil) });

async function deploy(abi: any, bytecode: Hex, args: any[]) {
  const hash = await wallet.deployContract({ abi, bytecode, args, account: deployer });
  const r = await publicClient.waitForTransactionReceipt({ hash });
  if (!r.contractAddress) throw new Error("deploy failed");
  return r.contractAddress as Address;
}
async function call(to: Address, abi: any, fn: string, args: any[]) {
  const hash = await wallet.writeContract({ address: to, abi, functionName: fn, args, account: deployer });
  return publicClient.waitForTransactionReceipt({ hash });
}
async function read(to: Address, abi: any, fn: string, args: any[]) {
  return publicClient.readContract({ address: to, abi, functionName: fn, args });
}
async function main() {
  const usdc = await deploy(plan.mockUsdc.abi, plan.mockUsdc.bytecode as Hex, []);
  const mock = await deploy(plan.mockVerifier.abi, plan.mockVerifier.bytecode as Hex, []);
  const validator = privateKeyToAccount(plan.validatorKey as Hex);
  const impl = await deploy(plan.consumer.abi, plan.consumer.bytecode as Hex, []);
  // Upgradeable pattern (project's own deploy scripts use ERC1967Proxy).
  const initData = encodeFunctionData({ abi: plan.consumer.abi, functionName: "initialize",
    args: [deployer.address, usdc, mock, deployer.address, [validator.address],
           plan.vkHash, plan.messagesLen, plan.noteKind] });
  const rollup = await deploy(plan.proxy.abi, plan.proxy.bytecode as Hex, [impl, initData]);
  report.steps.push({ deploy: { usdc, mock, impl, rollup } });

  const EMPTY_ROOT = "0x0577b5b4aa3eaba75b2a919d5d7c63b7258aa507d38e346bf2ff1d48790379ff";
  void EMPTY_ROOT;
  for (const [idx, a] of plan.actions.entries()) {
    try {
      if (a.register) {
        await call(usdc, plan.mockUsdc.abi, "approve", [rollup, BigInt(a.register.value)]);
        const r = await call(rollup, plan.consumer.abi, "mint",
          [a.register.hash, a.register.value, plan.noteKind]);
        report.steps.push({ [`${idx}_register`]: r.status });
      } else if (a.fund) {
        const r = await call(usdc, plan.mockUsdc.abi, "transfer", [a.fund.to, BigInt(a.fund.value)]);
        report.steps.push({ [`${idx}_fund`]: r.status });
      } else if (a.fund_rollup) {
        const r = await call(usdc, plan.mockUsdc.abi, "transfer", [rollup, BigInt(a.fund_rollup.value)]);
        report.steps.push({ [`${idx}_fund_rollup`]: r.status });
      } else if (a.settle) {
        // ECDSA sig over the contract's message hash.
        const { keccak256: kk, encodeAbiParameters: enc, encodePacked: epp, toHex, parseSignature } = await import("viem");
        const proposalHash = kk(enc([{ type: "bytes32" }, { type: "uint256" }, { type: "bytes32" }],
          [a.settle.newRoot, BigInt(a.settle.height), a.settle.otherHash]));
        const acceptMsg = kk(enc([{ type: "uint256" }, { type: "bytes32" }],
          [BigInt(a.settle.height + 1), proposalHash]));
        const netLen = new Uint8Array(8);
        new DataView(netLen.buffer).setBigUint64(0, 4n, false);
        const sigMsg = kk(epp(["bytes", "bytes", "bytes"],
          [toHex(netLen), toHex("Payy"), acceptMsg]));
        // Raw hash signature: the contract recovers over sigMsg directly (no eth prefix).
        const sigHex = await validator.sign({ hash: sigMsg as Hex });
        const parsed = parseSignature(sigHex);
        const r_ = parsed.r, s_ = parsed.s;
        const v_ = parsed.v === undefined ? 27 : Number(parsed.v);
        const words = [a.settle.oldRoot, a.settle.newRoot, a.settle.commitHash, ...a.settle.words];
        const r = await call(rollup, plan.consumer.abi, "verifyRollup",
          [a.settle.height, plan.vkHash, "0x00", words, a.settle.otherHash,
           [{ r: r_, s: s_, v: v_ }]]);
        report.steps.push({ [`${idx}_settle_h${a.settle.height}`]: r.status });
      }
    } catch (e: any) {
      const m = String(e?.shortMessage ?? e?.message ?? e);
      const mm = m.match(/reverted with reason string '([^']+)'/) ?? m.match(/([A-Za-z0-9 ]*revert[A-Za-z0-9 _:]*)/);
      report.steps.push({ [`${idx}_${a.settle ? "settle" : "register"}`]: "REVERT" });
      report[`revert_${idx}`] = (mm?.[1] ?? m).slice(0, 200);
      report[`stack_${idx}`] = String(e?.stack ?? "").split("\n").slice(0, 6).join(" | ").slice(0, 400);
    }
  }
  // State observations.
  const minted: any = {};
  for (const h of plan.watchHashes ?? []) {
    try { minted[h] = await read(rollup, plan.consumer.abi, "getMint", [h]); } catch { minted[h] = "unreadable"; }
  }
  const bals: any = {};
  for (const w of plan.watchBalances ?? []) {
    try { bals[w] = (await read(usdc, plan.mockUsdc.abi, "balanceOf", [w])).toString(); } catch { bals[w] = "unreadable"; }
  }
  report.state = { mints: minted, usdcBalances: bals, blockHeight: (await read(rollup, plan.consumer.abi, "blockHeight", [])).toString() };
  fs.writeFileSync(process.env.XAV_PAYY_REPORT!, JSON.stringify(report, (_k, v) => typeof v === "bigint" ? v.toString() : v, 1));
  console.log("PAYY-REPLAY-OK");
}
main().catch((e) => { console.error("PAYY-HARNESS-FAIL:", String(e?.message ?? e).slice(0, 300)); process.exit(2); });
