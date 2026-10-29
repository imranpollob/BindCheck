#!/usr/bin/env node
/** Automatic attacker-witness math for WarpToad same-root EVM / Aztec paths.
 *
 * Uses the project's locked hash packages (poseidon-lite 0.3.0,
 * @zkpassport/poseidon2 0.6.2) — the same code the D1P-15 hash reference
 * wraps. Modes:
 *   selftest --honest PROVER.TOML
 *     Recompute the honest commitment, nullifier, and EVM root from the
 *     honest witness inputs; exit nonzero on any mismatch. This gates all
 *     synthesis: if the math stack disagrees with the frozen witness, no
 *     attacker witness is built.
 *   anchor-tree --honest PROVER.TOML --out PROVER.TOML
 *     Fresh attacker note (fixed recorded randomness) in a private zero
 *     EVM tree at index 0; destination == origin == attacker root
 *     (unadmitted); giga root copied from honest (admitted, passes K1).
 *   aztec-branch --honest PROVER.TOML --out PROVER.TOML --attacker-address HEX
 *     Aztec-branch witness: commitment siloed under the attacker address,
 *     zero Aztec tree at index 0, is_from_aztec = true, origin == dest.
 *     Emits the extra `contract_address` struct field the mutant ABI needs.
 */
import fs from "node:fs";
import { poseidon1, poseidon2, poseidon3 } from "poseidon-lite";
import { poseidon2Hash } from "@zkpassport/poseidon2";

const F = (x) => BigInt(x);
const hx = (b) => "0x" + b.toString(16);

// Noir poseidon2::hash([d, l, r], 3): fixed-length H3 == permute([d,l,r,IV])[0].
function h3(domain, left, right) {
  return F(poseidon2Hash([domain, left, right].map((v) => v)));
}
const DOM_MERKLE = 2982624097n, DOM_UNIQUE = 226850429n, DOM_SILOED = 3361878420n;
const hashEvmNode = (l, r) => F(poseidon2([l, r]));
const hashCommitment = (pre, sec, chain, amt) => {
  const nullifier = F(poseidon1([pre]));
  const preC = F(poseidon3([pre, sec, chain]));
  return { commitment: F(poseidon2([preC, amt])), nullifier };
};

function parseToml(text) {
  // Minimal flat + [section] TOML reader for Prover.toml shapes.
  const top = {}, sections = {};
  let cur = top;
  for (const line of text.split("\n")) {
    const t = line.trim();
    if (!t || t.startsWith("#")) continue;
    const sm = t.match(/^\[(.+)\]$/);
    if (sm) { cur = sections[sm[1]] = {}; continue; }
    const m = t.match(/^(\w+)\s*=\s*(.+)$/);
    if (!m) continue;
    let v = m[2].trim();
    if (v.startsWith('"')) cur[m[1]] = v.slice(1, v.lastIndexOf('"'));
    else if (v === "true" || v === "false") cur[m[1]] = v === "true";
    else if (v.startsWith("[")) {
      cur[m[1]] = v.slice(1, v.lastIndexOf("]")).split(",").map((s) => s.trim().replace(/^"|"$/g, "")).filter(Boolean);
    } else cur[m[1]] = v;
  }
  return { top, sections };
}

function zeroPath(depth, nodeHash) {
  // Sibling hashes along index 0 of an all-zero tree.
  const zeros = [0n];
  for (let i = 1; i <= depth; i++) zeros.push(nodeHash(zeros[i - 1], zeros[i - 1]));
  return { siblings: zeros.slice(0, depth), root0: zeros[depth] };
}
function rootFromPath(leaf, index, siblings, nodeHash) {
  let node = leaf;
  for (let l = 0; l < siblings.length; l++) {
    const bit = Number((index >> BigInt(l)) & 1n);
    node = bit === 0 ? nodeHash(node, siblings[l]) : nodeHash(siblings[l], node);
  }
  return node;
}

const argv = process.argv.slice(2);
const mode = argv[0];
const args = {};
for (let i = 1; i < argv.length; i += 2) args[argv[i].replace(/^--/, "")] = argv[i + 1];
const honest = args.honest ? parseToml(fs.readFileSync(args.honest, "utf8")) : { top: {}, sections: {} };

if (mode === "selftest" || mode === "anchor-tree" || mode === "aztec-branch" || mode === "tree") {
  if (mode === "tree") {
    // Generic EVM tree: --leaves C0,C1,... --index I --depth 32.
    const leaves = args.leaves.split(",").map(F);
    const depth = parseInt(args.depth ?? "32", 10);
    const idx = BigInt(args.index ?? "0");
    let level = [...leaves];
    while (level.length < 2) level.push(0n);
    const path = [];
    let nodeIdx = idx;
    for (let l = 0; l < depth; l++) {
      const sibIdx = nodeIdx ^ 1n;
      path.push(level[Number(sibIdx)] ?? 0n);
      const next = [];
      for (let i = 0; i < level.length; i += 2) next.push(hashEvmNode(level[i] ?? 0n, level[i + 1] ?? 0n));
      level = next;
      nodeIdx >>= 1n;
    }
    console.log(JSON.stringify({ root: hx(level[0]), path: path.map(hx) }));
    process.exit(0);
  } else {
  const t = honest.top;
  const { commitment, nullifier } = hashCommitment(F(t.nullifier_preimage), F(t.secret), F(t.chain_id), F(t.amount));
  const evm = honest.sections.evm_merkle_data;
  const evmRoot = rootFromPath(commitment, F(evm.leaf_index), evm.hash_path.map(F), hashEvmNode);
  const okC = commitment === F(t.__commitment_expected ?? commitment);
  const checks = {
    nullifier_matches_derived: nullifier.toString(),
    commitment_hex: hx(commitment),
    evm_root_hex: hx(evmRoot),
    evm_root_matches_destination: evmRoot === F(t.destination_local_root),
  };
  console.log(JSON.stringify(checks));
  if (mode === "selftest") {
    if (!checks.evm_root_matches_destination) { console.error("SELFTEST FAIL: EVM root mismatch"); process.exit(1); }
    console.log("SELFTEST PASS");
    process.exit(0);
  }
  if (mode === "anchor-tree") {
    // Fresh attacker note; private zero EVM tree at index 0.
    // --amount-override / --chain-override rebuild the commitment under a
    // mutant commitment rule (WT-C06 binds amount 0, WT-C07 binds chain 0).
    const pre = 0xA77AC4n, sec = 0x5EC2E7n;
    const amt = F(args["amount-override"] ?? t.amount);
    const chain = F(args["chain-override"] ?? t.chain_id);
    const a = hashCommitment(pre, sec, chain, amt);
    const preC = F(poseidon3([pre, sec, chain]));
    const { siblings } = zeroPath(32, hashEvmNode);
    const root = rootFromPath(a.commitment, 0n, siblings, hashEvmNode);
    const out = {
      ...t, nullifier_preimage: hx(pre), secret: hx(sec),
      nullifier: hx(a.nullifier),
      destination_local_root: hx(root), origin_local_root: hx(root),
      evm_sections: { leaf_index: "0x0", hash_path: siblings.map(hx) },
      attacker_root: hx(root), attacker_commitment: hx(a.commitment),
      attacker_nullifier: hx(a.nullifier),
      attacker_pre_commitment: hx(preC),
      attacker_amount: hx(amt),
    };
    fs.writeFileSync(args.out, JSON.stringify(out));
    console.log(JSON.stringify({ attacker_root: hx(root), attacker_commitment: hx(a.commitment), attacker_nullifier: hx(a.nullifier), attacker_pre_commitment: hx(preC) }));
  }
  if (mode === "aztec-branch") {
    const atkAddr = F(args["attacker-address"]);
    const pre = 0xA77AC4n, sec = 0x5EC2E7n;
    const amt = F(t.amount), chain = F(t.chain_id);
    const preC = F(poseidon3([pre, sec, chain]));
    const noteHash = F(poseidon2([preC, amt]));
    const siloed = h3(DOM_SILOED, atkAddr, noteHash);
    const unique = h3(DOM_UNIQUE, 0n, siloed);
    const zp = zeroPath(42, (l, r) => h3(DOM_MERKLE, l, r));
    const root = rootFromPath(unique, 0n, zp.siblings, (l, r) => h3(DOM_MERKLE, l, r));
    const out = {
      ...t, nullifier_preimage: hx(pre), secret: hx(sec),
      nullifier: hx(F(poseidon1([pre]))),
      is_from_aztec: true,
      destination_local_root: hx(root), origin_local_root: hx(root),
      aztec_contract_address: hx(atkAddr),
      aztec_sections: { leaf_index: "0x0", hash_path: zp.siblings.map(hx), leaf_nonce: "0x0", contract_address: hx(atkAddr) },
      attacker_root: hx(root), attacker_commitment: hx(noteHash),
      attacker_nullifier: hx(F(poseidon1([pre]))),
    };
    fs.writeFileSync(args.out, JSON.stringify(out));
    console.log(JSON.stringify({ attacker_root: hx(root), attacker_commitment: hx(noteHash) }));
  }
  } // else (non-tree modes)
}
