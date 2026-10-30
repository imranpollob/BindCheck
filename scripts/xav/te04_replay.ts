/** TE04 E4 replay: real mutant agg_final verifier + pinned consumer on anvil.
 * Zero mock components on the proof path (no MockVerifier). MockUSDC is the
 * synthetic asset (project's own test token; a stand-in asset is required).
 * Env: XAV_TE04_PLAN (JSON), XAV_TE04_REPORT (out).
 * Plan: { consumer:{abi,bytecode}, usdc, verifiers:{mutant:{abi,bytecode},pinned:{...}},
 *   proxy:{abi,bytecode}, noteKind, finalVkHash, pinnedVkHash, messagesLen, validatorKey,
 *   proofHex, publicInputs:[...], mint:{hash,value}, fundNoteKind }
 */
import fs from "node:fs";
import { createPublicClient, createWalletClient, http, encodeFunctionData, type Address, type Hex } from "viem";
import { privateKeyToAccount } from "viem/accounts";

const plan = JSON.parse(fs.readFileSync(process.env.XAV_TE04_PLAN!, "utf8"));
const report: any = { label: "TE04-e4", steps: [], state: {} };
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

async function submit(tag: string, rollup: Address, vkHash: string, height: number, oldRoot: string, newRoot: string) {
  const { keccak256: kk, encodeAbiParameters: enc, encodePacked: epp, toHex, parseSignature } = await import("viem");
  const otherHash = "0x3333333333333333333333333333333333333333333333333333333333333333";
  const proposalHash = kk(enc([{ type: "bytes32" }, { type: "uint256" }, { type: "bytes32" }], [newRoot as Hex, BigInt(height), otherHash as Hex]));
  const acceptMsg = kk(enc([{ type: "uint256" }, { type: "bytes32" }], [BigInt(height + 1), proposalHash]));
  const netLen = new Uint8Array(8); new DataView(netLen.buffer).setBigUint64(0, 4n, false);
  const sigMsg = kk(epp(["bytes", "bytes", "bytes"], [toHex(netLen), toHex("Payy"), acceptMsg]));
  const validator = privateKeyToAccount(plan.validatorKey as Hex);
  const parsed = parseSignature(await validator.sign({ hash: sigMsg as Hex }));
  try {
    const r = await call(rollup, plan.consumer.abi, "verifyRollup",
      [height, vkHash, plan.proofHex, plan.publicInputs, otherHash, [{ r: parsed.r, s: parsed.s, v: Number(parsed.v ?? 27) }]]);
    report.steps.push({ [tag]: r.status });
    return "success";
  } catch (e: any) {
    const stack = String(e?.stack ?? e?.message ?? e).split("\n").slice(0, 4).join(" | ").slice(0, 300);
    report.steps.push({ [tag]: "REVERT" });
    report[`revert_${tag}`] = stack;
    return "revert";
  }
}

async function main() {
  const step = async (tag: string, fn: () => Promise<Address>) => {
    try { const a = await fn(); console.log(`deploy-ok ${tag} ${a}`); return a; }
    catch (e: any) { console.error(`deploy-FAIL ${tag}:`, String(e?.shortMessage ?? e?.message ?? e).slice(0, 400)); throw e; }
  };
  const usdc = await step("usdc", () => deploy(plan.usdc.abi, plan.usdc.bytecode as Hex, []));
  const vMut = await step("vMut", () => deploy(plan.verifiers.mutant.abi, plan.verifiers.mutant.bytecode as Hex, []));
  const vPin = await step("vPin", () => deploy(plan.verifiers.pinned.abi, plan.verifiers.pinned.bytecode as Hex, []));
  const impl = await step("impl", () => deploy(plan.consumer.abi, plan.consumer.bytecode as Hex, []));
  const validator = privateKeyToAccount(plan.validatorKey as Hex);
  const initData = encodeFunctionData({ abi: plan.consumer.abi, functionName: "initialize",
    args: [deployer.address, usdc, vMut, deployer.address, [validator.address],
           plan.finalVkHash, plan.messagesLen, plan.noteKind] });
  const rollup = await step("proxy", () => deploy(plan.proxy.abi, plan.proxy.bytecode as Hex, [impl, initData]));
  report.steps.push({ deploy: { usdc, vMut, vPin, impl, rollup } });

  // Register the honest inner mint (deposit 100 of MockUSDC into the rollup).
  await call(usdc, plan.usdc.abi, "approve", [rollup, BigInt(plan.mint.value)]);
  const reg = await call(rollup, plan.consumer.abi, "mint", [plan.mint.hash, plan.mint.value, plan.noteKind]);
  report.steps.push({ register_honest_mint: reg.status });
  // Register the pinned-keyed verifier on the same consumer for contrast.
  const add = await call(rollup, plan.consumer.abi, "addZkVerifier", [plan.pinnedVkHash, vPin, plan.messagesLen]);
  report.steps.push({ add_pinned_verifier: add.status });

  const oldRoot = plan.publicInputs[0], newRoot = plan.publicInputs[1];
  const before = await read(usdc, plan.usdc.abi, "balanceOf", [plan.watch]);
  // Contrast FIRST at height 1 (root/chain checks pass; rejection must come
  // from proof verification under the pinned key).
  await submit("pinned_contrast", rollup, plan.pinnedVkHash, 1, oldRoot, newRoot);
  await submit("mutant_block", rollup, plan.finalVkHash, 1, oldRoot, newRoot);
  const after = await read(usdc, plan.usdc.abi, "balanceOf", [plan.watch]);
  const rollupBal = await read(usdc, plan.usdc.abi, "balanceOf", [rollup]);
  const mintState = await read(rollup, plan.consumer.abi, "getMint", [plan.mint.hash]);
  report.state = { watch: plan.watch, before: before.toString(), after: after.toString(),
    rollupBal: rollupBal.toString(), mint: mintState,
    blockHeight: (await read(rollup, plan.consumer.abi, "blockHeight", [])).toString() };
  fs.writeFileSync(process.env.XAV_TE04_REPORT!, JSON.stringify(report, (_k, v) => typeof v === "bigint" ? v.toString() : v, 1));
  console.log("TE04-REPLAY-OK");
}
main().catch((e) => { console.error("TE04-FAIL:", String(e?.message ?? e).slice(0, 300)); process.exit(2); });
