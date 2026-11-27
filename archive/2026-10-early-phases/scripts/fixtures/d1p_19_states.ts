/** Build the canonical D1P-19 S_DOM and S_SRC states from locked hash libraries. */
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const [honestPath, foreignPath, executionPath, outputPath, backendNodeModules] = process.argv.slice(2);
if (!honestPath || !foreignPath || !executionPath || !outputPath || !backendNodeModules) {
  throw new Error("usage: d1p_19_states.ts HONEST FOREIGN MSRC_EXEC OUTPUT BACKEND_NODE_MODULES");
}
const resolver = createRequire(path.join(backendNodeModules, "d1p19-resolver.cjs"));
Promise.all([
  import(pathToFileURL(resolver.resolve("poseidon-lite")).href),
  import(pathToFileURL(resolver.resolve("@zkpassport/poseidon2")).href),
]).then(([poseidonLite, poseidon2Package]: any[]) => {
const { poseidon1, poseidon2, poseidon3 } = poseidonLite;
const { permute } = poseidon2Package;

const P = 21888242871839275222246405745257275088548364400416034343698204186575808495617n;
const IV = 3n << 64n;
const DOMAIN_SILO = 3361878420n;
const DOMAIN_UNIQUE = 226850429n;
const DOMAIN_NODE = 2982624097n;
const read = (file: string) => JSON.parse(fs.readFileSync(file, "utf8"));
const sha256 = (file: string) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");

type Term = { id: string; function: string; inputs: string[]; output: string };
const terms: Term[] = [];
const bn = (name: "H1" | "H2" | "H3", inputs: bigint[], id: string): bigint => {
  const output = BigInt(name === "H1" ? poseidon1(inputs) : name === "H2" ? poseidon2(inputs) : poseidon3(inputs));
  terms.push({ id, function: `BN254-${name}`, inputs: inputs.map(String), output: String(output) });
  return output;
};
const p2 = (domain: bigint, left: bigint, right: bigint, id: string): bigint => {
  const output = BigInt(permute([domain, left, right, IV])[0]);
  terms.push({ id, function: "P2-H3", inputs: [domain, left, right].map(String), output: String(output) });
  return output;
};

function zeroRoots(depth: number, hash: (left: bigint, right: bigint, id: string) => bigint, prefix: string) {
  const zero = [0n];
  for (let level = 0; level < depth - 1; level++) {
    zero.push(hash(zero[level], zero[level], `${prefix}-zero-${level}`));
  }
  return zero;
}

function twoLeafTree(
  depth: number, leftLeaf: bigint, rightLeaf: bigint,
  hash: (left: bigint, right: bigint, id: string) => bigint, prefix: string,
) {
  const zero = zeroRoots(depth, hash, prefix);
  let node = hash(leftLeaf, rightLeaf, `${prefix}-node-0`);
  for (let level = 1; level < depth; level++) {
    node = hash(node, zero[level], `${prefix}-node-${level}`);
  }
  return {
    root: node,
    left: { leafIndex: 0, path: [rightLeaf, ...zero.slice(1)] },
    right: { leafIndex: 1, path: [leftLeaf, ...zero.slice(1)] },
    zeroRoots: zero,
  };
}

function oneLeafTree(
  depth: number, leaf: bigint,
  hash: (left: bigint, right: bigint, id: string) => bigint, prefix: string,
) {
  const zero = zeroRoots(depth, hash, prefix);
  let node = leaf;
  for (let level = 0; level < depth; level++) {
    node = hash(node, zero[level], `${prefix}-node-${level}`);
  }
  return { root: node, leafIndex: 0, path: zero, zeroRoots: zero };
}

const honest = read(honestPath);
const foreign = read(foreignPath);
const execution = read(executionPath);
const h = honest.proofInputs;
const x = foreign.proofInputs;
const amount = BigInt(h.amount);
const precommitment = bn("H3", [BigInt(h.nullifier_preimage), BigInt(h.secret), BigInt(h.chain_id)], "s-dom-common-precommitment");
const commitment = bn("H2", [precommitment, amount], "s-dom-common-commitment");
const nullifier = bn("H1", [BigInt(h.nullifier_preimage)], "s-dom-common-nullifier");
assertEqual(nullifier, BigInt(h.nullifier), "D1P-15 nullifier");
const wtSilo = p2(DOMAIN_SILO, BigInt(h.aztec_merkle_data.contract_address), commitment, "s-dom-wt-silo");
const wtNote = p2(DOMAIN_UNIQUE, BigInt(h.aztec_merkle_data.leaf_nonce), wtSilo, "s-dom-wt-unique");
const xSilo = p2(DOMAIN_SILO, BigInt(x.aztec_merkle_data.contract_address), commitment, "s-dom-x-silo");
const xNote = p2(DOMAIN_UNIQUE, BigInt(x.aztec_merkle_data.leaf_nonce), xSilo, "s-dom-x-unique");
const noteTree = twoLeafTree(42, wtNote, xNote, (left, right, id) => p2(DOMAIN_NODE, left, right, id), "s-dom-p2");
const gigaTree = oneLeafTree(5, noteTree.root, (left, right, id) => bn("H2", [left, right], id), "s-dom-giga");
const destinationRoot = BigInt(h.destination_local_root);
assertEqual(destinationRoot, BigInt(x.destination_local_root), "D1P-15 common destination root");
if (destinationRoot === noteTree.root) throw new Error("S_DOM L1 and Aztec roots must be disjoint");

const sSrcTermsStart = terms.length;
const sourceBurns = execution.sSrc.burns.map((burn: any, index: number) => {
  const recomputedPrecommitment = bn(
    "H3", [BigInt(burn.nullifierPreimage), BigInt(burn.secret), 31337n], `s-src-burn-${index}-precommitment`,
  );
  const recomputedCommitment = bn("H2", [recomputedPrecommitment, BigInt(burn.amount)], `s-src-burn-${index}-commitment`);
  assertEqual(recomputedPrecommitment, BigInt(burn.preCommitment), `S_SRC burn ${index} precommitment`);
  assertEqual(recomputedCommitment, BigInt(burn.commitment), `S_SRC burn ${index} commitment`);
  return { ...burn, preCommitment: recomputedPrecommitment, commitment: recomputedCommitment };
});
const srcOne = oneLeafTree(32, sourceBurns[0].commitment, (left, right, id) => bn("H2", [left, right], id), "s-src-one");
const srcTwo = twoLeafTree(32, sourceBurns[0].commitment, sourceBurns[1].commitment, (left, right, id) => bn("H2", [left, right], id), "s-src-two");
assertEqual(srcOne.root, BigInt(sourceBurns[0].root), "S_SRC first execution root");
assertEqual(srcTwo.root, BigInt(sourceBurns[1].root), "S_SRC second execution root");

const historical = [
  { name: "D1P-15 honest", record: honest, canonicalIndex: 0, canonicalPath: noteTree.left.path },
  { name: "D1P-15 foreign", record: foreign, canonicalIndex: 1, canonicalPath: noteTree.right.path },
].map(({ name, record, canonicalIndex, canonicalPath }) => {
  const inputs = record.proofInputs;
  const differences = [];
  if (BigInt(inputs.origin_local_root) !== noteTree.root) differences.push("origin_local_root");
  if (BigInt(inputs.giga_root) !== gigaTree.root) differences.push("giga_root");
  if (BigInt(inputs.aztec_merkle_data.leaf_index) !== BigInt(canonicalIndex)) differences.push("aztec leaf_index");
  if (inputs.aztec_merkle_data.hash_path.map(BigInt).some((item: bigint, i: number) => item !== canonicalPath[i])) {
    differences.push("aztec hash_path");
  }
  return {
    fixture: name,
    directlyAdmittedFromFrozenSDom: differences.length === 0,
    differences,
    historical: {
      originLocalRoot: BigInt(inputs.origin_local_root),
      gigaRoot: BigInt(inputs.giga_root),
      leafIndex: BigInt(inputs.aztec_merkle_data.leaf_index),
      hashPath: inputs.aztec_merkle_data.hash_path.map(BigInt),
    },
    frozen: { originLocalRoot: noteTree.root, gigaRoot: gigaTree.root, leafIndex: canonicalIndex, hashPath: canonicalPath },
    unchangedAdmittedDestinationRoot: BigInt(inputs.destination_local_root) === destinationRoot,
  };
});

const output = {
  schema: "bindcheck.d1p19.canonical-states/v1",
  fieldModulus: P,
  construction: {
    p2H3: "state=[domain,left,right,3*2^64]; one locked width-4 permutation; lane 0",
    bn254: "locked poseidon-lite H1/H2/H3",
    pathConvention: "little-endian leaf-index bits; sibling path leaf-to-root; recursive empty-subtree roots",
  },
  sources: {
    d1p15Honest: { path: honestPath, sha256: sha256(honestPath) },
    d1p15Foreign: { path: foreignPath, sha256: sha256(foreignPath) },
    mSrcExecution: { path: executionPath, sha256: sha256(executionPath) },
  },
  S_DOM: {
    classification: "synthetic fixed admitted state; no cross-chain reachability claim",
    A_WT: BigInt(h.aztec_warptoad_address),
    A_X: BigInt(x.aztec_merkle_data.contract_address),
    A_WT_nonzero: BigInt(h.aztec_warptoad_address) !== 0n,
    distinctSiloAddresses: BigInt(h.aztec_warptoad_address) !== BigInt(x.aztec_merkle_data.contract_address),
    commitment: { amount, precommitment, commitment, nullifier },
    notes: {
      WarpToad: { siloed: wtSilo, unique: wtNote, ...noteTree.left },
      foreign: { siloed: xSilo, unique: xNote, ...noteTree.right },
    },
    aztecNoteTree: { depth: 42, root: noteTree.root, zeroRoots: noteTree.zeroRoots },
    admittedGigaTree: { depth: 5, root: gigaTree.root, leaf: noteTree.root, leafIndex: 0, path: gigaTree.path },
    l1LocalRootHistory: [destinationRoot],
    l1RootDisjointFromAztecRoot: destinationRoot !== noteTree.root,
    nullifierSet: [],
    historicalFixtureAdmission: historical,
    historicalConclusion: "neither D1P-15 execution is directly admitted from frozen S_DOM; both used separate single-leaf/all-zero-path Aztec roots and distinct giga roots",
  },
  S_SRC: {
    classification: "owned-local admitted source state hash-recorded from two actual burn executions",
    privilegedInitialization: execution.sSrc.privilegedInitialization,
    burns: sourceBurns,
    admittedRootHistory: [srcOne.root, srcTwo.root],
    firstTree: { depth: 32, root: srcOne.root, leafIndex: 0, path: srcOne.path },
    secondTree: { depth: 32, root: srcTwo.root, left: srcTwo.left, right: srcTwo.right },
    distinctAmounts: BigInt(sourceBurns[0].amount) !== BigInt(sourceBurns[1].amount),
    executionBacked: true,
    noCrossChainReachabilityClaim: true,
    groundTermRange: [sSrcTermsStart, terms.length - 1],
  },
  groundHashInstances: terms,
  checks: {
    bothNotesInOneFrozenAztecRoot: true,
    frozenAztecRootInFrozenGigaRoot: true,
    sourceRootsMatchActualExecution: true,
    allValuesCanonical: terms.every((term) => [...term.inputs, term.output].every((item) => BigInt(item) < P)),
  },
};

fs.writeFileSync(outputPath, JSON.stringify(output, (_key, item) => typeof item === "bigint" ? item.toString() : item, 2) + "\n");

function assertEqual(actual: bigint, expected: bigint, label: string) {
  if (actual !== expected) throw new Error(`${label}: ${actual} != ${expected}`);
}
});
