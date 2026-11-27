/** Automatic E4 replay for one WarpToad mutant (Hardhat EDR, in-process).
 *
 * Env:
 *   XAV_PLAN   JSON file: { proofHex, mint: {nullifier, amount, gigaRoot,
 *              localRoot, feeFactor, priorityFee, maxFee, relayer, recipient},
 *              gigaRoot, aztecAddress, burns: [{preCommitment, amount}],
 *              mintTwice: bool, label }
 *   XAV_REPORT JSON output path.
 *
 * Deploys (libraries, USDcoin, mutant HonkVerifier, L1WarpToad, MockGiga),
 * initializes, optionally burns+stores roots, then mints once (or twice).
 * Reports state effects: recipient/relayer balances, nullifier flag,
 * revert reasons. Exits 0 unless the harness itself fails; a consumer
 * revert is a recorded observation, not a harness failure.
 */
import hre from "hardhat";
import fs from "node:fs";
import { type Address, type Hex, type WalletClient, type PublicClient } from "viem";

function linkBytecode(bytecode: Hex, linkReferences: any, libraries: Record<string, Address>): Hex {
  const raw = bytecode.startsWith("0x") ? bytecode.slice(2) : bytecode;
  let linked = raw;
  for (const [, contractRefs] of Object.entries(linkReferences) as any) {
    for (const [contractName, refs] of Object.entries(contractRefs) as any) {
      const addr = libraries[contractName];
      if (!addr) throw new Error(`Missing library address for ${contractName}`);
      const cleanAddr = (addr as string).slice(2).toLowerCase();
      for (const ref of refs as any[]) {
        const start = ref.start * 2, length = ref.length * 2;
        linked = linked.slice(0, start) + cleanAddr.padStart(length, "0") + linked.slice(start + length);
      }
    }
  }
  return ("0x" + linked) as Hex;
}

async function deploy(name: string, args: any[], deployer: WalletClient, publicClient: PublicClient, libs?: Record<string, Address>) {
  const artifact: any = await hre.artifacts.readArtifact(name);
  let bytecode = artifact.bytecode as Hex;
  if (libs && Object.keys(artifact.linkReferences ?? {}).length > 0)
    bytecode = linkBytecode(bytecode, artifact.linkReferences, libs);
  const hash = await (deployer as any).deployContract({ abi: artifact.abi, bytecode, args });
  const receipt = await publicClient.waitForTransactionReceipt({ hash });
  if (!receipt.contractAddress) throw new Error(`deploy ${name} failed`);
  return { address: receipt.contractAddress as Address, abi: artifact.abi };
}

async function main() {
  const plan = JSON.parse(fs.readFileSync(process.env.XAV_PLAN!, "utf8"));
  const report: any = { label: plan.label, steps: [], state: {}, reverts: [] };
  const connection: any = await (hre as any).network.connect();
  const wallets = await connection.viem.getWalletClients();
  const deployer = wallets[0];
  const publicClient = await connection.viem.getPublicClient();

  // Libraries come from the pinned reference build-info (read-only); linked at deploy.
  const biDir = process.env.XAV_REF_BUILDINFO!;
  const fromBuildInfo = (sourcePath: string, contractName: string) => {
    for (const f of fs.readdirSync(biDir)) {
      if (!f.endsWith(".output.json")) continue;
      const data = JSON.parse(fs.readFileSync(`${biDir}/${f}`, "utf8"));
      const c = data.output?.contracts?.[sourcePath]?.[contractName];
      if (c) return { abi: c.abi, bytecode: ("0x" + c.evm.bytecode.object) as Hex, linkReferences: data.output.contracts[sourcePath][contractName].evm.bytecode.linkReferences ?? {} };
    }
    throw new Error(`not in build-info: ${sourcePath} ${contractName}`);
  };
  const deployLinked = async (sourcePath: string, contractName: string, libs: Record<string, Address>) => {
    const info: any = fromBuildInfo(sourcePath, contractName);
    let bytecode = info.bytecode as Hex;
    if (Object.keys(info.linkReferences ?? {}).length > 0) bytecode = linkBytecode(bytecode, info.linkReferences, libs);
    const hash = await (deployer as any).deployContract({ abi: info.abi, bytecode, args: [] });
    const receipt = await publicClient.waitForTransactionReceipt({ hash });
    if (!receipt.contractAddress) throw new Error(`deploy ${contractName} failed`);
    return { address: receipt.contractAddress as Address, abi: info.abi };
  };
  const poseidon = await deployLinked("npm/poseidon-solidity@0.0.5/PoseidonT3.sol", "PoseidonT3", {});
  const lazy = await deployLinked("npm/@zk-kit/lazy-imt.sol@2.0.0-beta.12/LazyIMT.sol", "LazyIMT", { PoseidonT3: poseidon.address });
  const libs = { PoseidonT3: poseidon.address, LazyIMT: lazy.address };
  const token = await deploy("USDcoin", [], deployer, publicClient);
  const zkT = await deploy("contracts/verifier/HonkVerifier.sol:ZKTranscriptLib", [], deployer, publicClient);
  const rel = await deploy("contracts/verifier/HonkVerifier.sol:RelationsLib", [], deployer, publicClient);
  const verifier = await deploy("contracts/verifier/HonkVerifier.sol:HonkVerifier", [], deployer, publicClient,
    { ZKTranscriptLib: zkT.address, RelationsLib: rel.address });
  const wt = await deploy("L1WarpToad",
    [32, verifier.address, token.address, "wrpToad-USD Coin", "wrpToad-USDC"],
    deployer, publicClient, libs);
  const mock = await deploy("MockGigaProvider", [plan.gigaRoot], deployer, publicClient);
  report.steps.push({ deploy: { verifier: verifier.address, consumer: wt.address } });

  const wtC: any = { address: wt.address, abi: wt.abi };
  const call = async (fn: string, args: any[]) => {
    const hash = await (deployer as any).writeContract({ address: wt.address, abi: wt.abi, functionName: fn, args });
    return publicClient.waitForTransactionReceipt({ hash });
  };
  const reasonOf = (e: any): string => {
    // Walk viem error causes for the revert reason.
    let cur: any = e, depth = 0;
    while (cur && depth < 6) {
      for (const k of ["reason", "shortMessage", "message", "details"]) {
        if (typeof cur[k] === "string" && /unknown|exists|invalid proof|larger than|denied|revert|ERC20|exceed/i.test(cur[k]))
          return String(cur[k]).slice(0, 200);
      }
      const m = String(cur?.message ?? cur?.details ?? "").match(/reverted with reason string '([^']+)'/);
      if (m) return m[1].slice(0, 200);
      cur = cur?.cause ?? cur?.["cause"];
      depth++;
    }
    return String(e?.shortMessage ?? e?.message ?? e).slice(0, 200);
  };
  const read = async (fn: string, args: any[]) =>
    publicClient.readContract({ address: wt.address, abi: wt.abi, functionName: fn, args });

  await call("initialize", [mock.address, deployer.account.address, BigInt(plan.aztecAddress ?? 0)]);
  // Seed: performer needs wrapped balance for burns; attacker mints need none.
  for (const b of plan.burns ?? []) {
    await call("getFreeShit", [BigInt(b.amount)]);
    await call("burn", [BigInt(b.preCommitment), BigInt(b.amount)]);
  }
  await call("storeLocalRootInHistory", []);

  const m = plan.mint;
  const mintArgs = [BigInt(m.nullifier), BigInt(m.amount), BigInt(m.gigaRoot),
    BigInt(m.localRoot), BigInt(m.feeFactor), BigInt(m.priorityFee), BigInt(m.maxFee),
    m.relayer as Address, m.recipient as Address, plan.proofHex as Hex];
  // plan.mints: ordered mint attempts, each {mint args..., proofHex}.
  // Legacy single-mint plans use plan.mint + plan.proofHex (+ plan.mintTwice).
  const attempts: any[] = plan.mints ?? [{ ...plan.mint, proofHex: plan.proofHex }];
  if (plan.mintTwice && !plan.mints) attempts.push({ ...plan.mint, proofHex: plan.proofHex });
  // Seed check: the witness local root must be admitted unless the plan says otherwise.
  report.seedCheck = { localRoot: plan.mint?.localRoot ?? attempts[0].localRoot,
    admittedBefore: await read("isValidLocalRoot", [BigInt(plan.mint?.localRoot ?? attempts[0].localRoot)]) };
  const { encodeFunctionData, decodeErrorResult } = await import("viem");
  let i = 0;
  for (const a of attempts) {
    const args = [BigInt(a.nullifier), BigInt(a.amount), BigInt(a.gigaRoot),
      BigInt(a.localRoot), BigInt(a.feeFactor), BigInt(a.priorityFee), BigInt(a.maxFee),
      a.relayer as Address, a.recipient as Address, a.proofHex as Hex];
    try {
      const r = await call("mint", args);
      report.steps.push({ [`mint_${i}`]: { status: r.status, gasUsed: r.gasUsed.toString(), nullifier: a.nullifier } });
    } catch (e: any) {
      // Innermost cause carries the raw revert data on this EDR stack.
      let decoded = reasonOf(e);
      try {
        const findData = (x: any, depth: number): string => {
          if (!x || depth > 8) return "";
          if (typeof x?.data === "string" && x.data.startsWith("0x")) return x.data;
          return findData(x?.cause, depth + 1);
        };
        const hex = findData(e, 0);
        if (hex.startsWith("0x08c379a0")) {
          try {
            decoded = String(decodeErrorResult({ abi: wt.abi, data: hex as Hex }).args?.[0]).slice(0, 200);
          } catch { /* keep walker result */ }
        } else if (hex.length > 10) {
          const known: Record<string, string> = {
            "0xec442f05": "ERC20InvalidReceiver (OZ 5.x custom error)",
            "0xe450d38c": "ERC20InsufficientBalance (OZ 5.x custom error)",
            "0xfb8f41b2": "ERC20InvalidSender (OZ 5.x custom error)",
          };
          decoded = `${known[hex.slice(0, 10)] ?? "unknown custom error"} ${hex.slice(0, 74)}`;
        }
      } catch { /* keep walker result */ }
      try {
        const shape: string[] = [];
        let cur: any = e;
        for (let d = 0; d < 4 && cur; d++) {
          shape.push(`${cur?.name ?? "?"}:{${Object.keys(cur).filter((k: string) => /data|reason|message|cause|details|short/i.test(k)).join(",")}}`);
          cur = cur?.cause;
        }
        (report as any).errorShapes = [...((report as any).errorShapes ?? []), { [`mint_${i}`]: shape.join(" <- ") }];
      } catch { /* ignore */ }
      try {
        const data = encodeFunctionData({ abi: wt.abi, functionName: "mint", args });
        await publicClient.call({ to: wt.address, data, account: (deployer as any).account });
      } catch (e2: any) {
        const hex = (e2?.data ?? e2?.cause?.data ?? "") as string;
        if (typeof hex === "string" && hex.startsWith("0x08c379a0")) {
          try {
            decoded = decodeErrorResult({ abi: wt.abi, data: hex as Hex }).args?.[0] as string;
          } catch { /* keep walker result */ }
        } else if (typeof hex === "string" && hex.length > 10) {
          decoded = `raw revert data ${hex.slice(0, 74)}`;
        }
      }
      report.reverts.push({ [`mint_${i}`]: decoded });
      report.steps.push({ [`mint_${i}`]: "REVERT" });
    }
    i++;
  }
  // Minted wrpToad balances live on the consumer (it is the ERC20), not USDcoin.
  const erc20 = (await (hre as any).artifacts.readArtifact("USDcoin")).abi;
  const bal = async (addr: string) =>
    publicClient.readContract({ address: wt.address, abi: erc20, functionName: "balanceOf", args: [addr] });
  void wtC;
  void token;
  report.state = {
    recipientBalance: (await bal(m.recipient)).toString(),
    relayerBalance: (await bal(m.relayer)).toString(),
    nullifierSpent: await read("nullifierExists", [BigInt(m.nullifier)]),
    localRootAdmitted: await read("isValidLocalRoot", [BigInt(m.localRoot)]),
    gigaRootAdmitted: await read("isValidGigaRoot", [BigInt(m.gigaRoot)]),
  };
  fs.writeFileSync(process.env.XAV_REPORT!, JSON.stringify(report, null, 1));
  console.log(JSON.stringify(report));
}

main().catch((e) => { console.error("HARNESS FAIL:", e?.message ?? e); process.exit(2); });
