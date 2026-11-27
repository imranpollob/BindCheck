/** TE06 contrast replay: mutant vs pinned consumer, same real proof.
 * Zero mock components (no MockVerifier). MockUSDC is the synthetic asset.
 * Env: XAV_TE06_PLAN (JSON), XAV_TE06_REPORT (out), XAV_ANVIL_URL.
 * Plan: { consumerMutant:{abi,bytecode}, consumerPinned:{abi,bytecode},
 *   usdc, verifier:{abi,bytecode}, proxy:{abi,bytecode}, noteKind,
 *   finalVkHash, messagesLen, validatorKey, proofHex, publicInputs,
 *   register?:{hash,value}, fund?:{value}, submits:[{side,height,tag}],
 *   watch:[addresses], label }
 * Initial state is identical on both sides (fresh chain, same funding and
 * registration); only the consumer implementation differs.
 */
import fs from "node:fs";
import { createPublicClient, createWalletClient, http, encodeFunctionData, type Address, type Hex } from "viem";
import { privateKeyToAccount } from "viem/accounts";

const plan = JSON.parse(fs.readFileSync(process.env.XAV_TE06_PLAN!, "utf8"));
const report: any = { label: plan.label, steps: [], state: {} };
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

async function submit(rollup: Address, abi: any, tag: string, vkHash: string, height: number, oldRoot: string, newRoot: string) {
  const { keccak256: kk, encodeAbiParameters: enc, encodePacked: epp, toHex, parseSignature } = await import("viem");
  const otherHash = "0x3333333333333333333333333333333333333333333333333333333333333333";
  const proposalHash = kk(enc([{ type: "bytes32" }, { type: "uint256" }, { type: "bytes32" }], [newRoot as Hex, BigInt(height), otherHash as Hex]));
  const acceptMsg = kk(enc([{ type: "uint256" }, { type: "bytes32" }], [BigInt(height + 1), proposalHash]));
  const netLen = new Uint8Array(8); new DataView(netLen.buffer).setBigUint64(0, 4n, false);
  const sigMsg = kk(epp(["bytes", "bytes", "bytes"], [toHex(netLen), toHex("Payy"), acceptMsg]));
  const validator = privateKeyToAccount(plan.validatorKey as Hex);
  const parsed = parseSignature(await validator.sign({ hash: sigMsg as Hex }));
  try {
    const r = await call(rollup, abi, "verifyRollup",
      [height, vkHash, plan.proofHex, plan.publicInputs, otherHash, [{ r: parsed.r, s: parsed.s, v: Number(parsed.v ?? 27) }]]);
    report.steps.push({ [tag]: r.status });
    return "success";
  } catch (e: any) {
    const stack = String(e?.stack ?? e?.message ?? e).split("\n").slice(0, 4).join(" | ").slice(0, 300);
    const walk = (o: any, d: number): string => {
      if (!o || d > 4) return "";
      const data = (o as any)?.data;
      if (typeof data === "string" && data.startsWith("0x")) return data.slice(0, 200);
      return walk((o as any)?.cause ?? (o as any)?.error, d + 1);
    };
    const raw = walk(e, 0);
    report.steps.push({ [tag]: "REVERT" });
    report[`revert_${tag}`] = raw ? `${stack} || DATA:${raw}` : stack;
    return "revert";
  }
}

async function main() {
  // Libraries first, in listed order: verifier bytecode is linked to these
  // deterministic addresses (same deployer, fresh chain, fixed nonces).
  for (const lib of plan.libraries ?? []) {
    const addr = await deploy([], lib.bytecode as Hex, []);
    if (addr.toLowerCase() !== lib.address.toLowerCase()) {
      console.error(`TE06-FAIL: lib ${lib.name} at ${addr}, expected ${lib.address}`);
      process.exit(3);
    }
  }
  const usdc = await deploy(plan.usdc.abi, plan.usdc.bytecode as Hex, []);
  const vPin = await deploy(plan.verifier.abi, plan.verifier.bytecode as Hex, []);
  const implM = await deploy(plan.consumerMutant.abi, plan.consumerMutant.bytecode as Hex, []);
  const implP = await deploy(plan.consumerPinned.abi, plan.consumerPinned.bytecode as Hex, []);
  const validator = privateKeyToAccount(plan.validatorKey as Hex);
  const mkInit = (impl: Address) => encodeFunctionData({ abi: plan.consumerPinned.abi, functionName: "initialize",
    args: [deployer.address, usdc, vPin, deployer.address, [validator.address],
           plan.finalVkHash, plan.messagesLen, plan.noteKind] });
  // NOTE: initData uses the pinned ABI (identical interface on mutants).
  const rollM = await deploy(plan.proxy.abi, plan.proxy.bytecode as Hex, [implM, mkInit(implM)]);
  const rollP = await deploy(plan.proxy.abi, plan.proxy.bytecode as Hex, [implP, mkInit(implP)]);
  report.steps.push({ deploy: { usdc, vPin, implM, implP, rollM, rollP } });
  const abiM = plan.consumerMutant.abi, abiP = plan.consumerPinned.abi;
  if (plan.register) {
    for (const [side, roll, abi] of [["mutant", rollM, abiM], ["pinned", rollP, abiP]] as any) {
      await call(usdc, plan.usdc.abi, "approve", [roll, BigInt(plan.register.value)]);
      const r = await call(roll, abi, "mint", [plan.register.hash, plan.register.value, plan.noteKind]);
      report.steps.push({ [`register_${side}`]: r.status });
    }
  }
  if (plan.fund) {
    // Funding == registering a backing mint (same as TE04): approve + mint
    // moves deployer MockUSDC into the rollup so burn payouts can settle.
    for (const [side, roll, abi] of [["mutant", rollM, abiM], ["pinned", rollP, abiP]] as any) {
      await call(usdc, plan.usdc.abi, "approve", [roll, BigInt(plan.fund.value)]);
      const r = await call(roll, abi, "mint", [plan.fund.hash, plan.fund.value, plan.noteKind]);
      report.steps.push({ [`fund_${side}`]: r.status });
    }
  }
  const oldRoot = plan.publicInputs[0], newRoot = plan.publicInputs[1];
  for (const s of plan.submits) {
    const roll = s.side === "mutant" ? rollM : rollP;
    const abi = s.side === "mutant" ? abiM : abiP;
    await submit(roll, abi, s.tag, plan.finalVkHash, s.height, oldRoot, newRoot);
  }
  const state: any = {};
  for (const a of plan.watch ?? []) {
    state[`bal_${a.slice(0, 10)}`] = (await read(usdc, plan.usdc.abi, "balanceOf", [a])).toString();
  }
  for (const [side, roll, abi] of [["mutant", rollM, abiM], ["pinned", rollP, abiP]] as any) {
    state[`${side}_height`] = (await read(roll, abi, "blockHeight", [])).toString();
    state[`${side}_rollupBal`] = (await read(usdc, plan.usdc.abi, "balanceOf", [roll])).toString();
  }
  if (plan.mintHash) {
    for (const [side, roll, abi] of [["mutant", rollM, abiM], ["pinned", rollP, abiP]] as any)
      state[`${side}_mint`] = await read(roll, abi, "getMint", [plan.mintHash]);
  }
  report.state = state;
  fs.writeFileSync(process.env.XAV_TE06_REPORT!, JSON.stringify(report, (_k, v) => typeof v === "bigint" ? v.toString() : v, 1));
  console.log("TE06-REPLAY-OK");
}
main().catch((e) => { console.error("TE06-FAIL:", String(e?.message ?? e).slice(0, 300)); process.exit(2); });
