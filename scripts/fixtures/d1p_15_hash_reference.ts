/** Exact hash constructions used by the pinned WarpToad withdraw circuit. */
import fs from "node:fs";
import crypto from "node:crypto";
import { pathToFileURL } from "node:url";
import { permute, poseidon2Hash } from "@zkpassport/poseidon2";
import { poseidon1, poseidon2, poseidon3 } from "poseidon-lite";

export const FIELD_MODULUS = 21888242871839275222246405745257275088548364400416034343698204186575808495617n;
export const RATE = 3;
export const WIDTH = 4;
export const IV_H3 = 3n << 64n;
export const DOM_SEP_MERKLE = 2982624097n;
export const DOM_SEP_UNIQUE = 226850429n;
export const DOM_SEP_SILOED = 3361878420n;

export type H3Trace = {
  initialState: bigint[];
  absorption: bigint[];
  absorbedState: bigint[];
  permutedState: bigint[];
  outputLane: number;
  output: bigint;
};

export function poseidon2H3Trace(domain: bigint, left: bigint, right: bigint): H3Trace {
  const initialState = [0n, 0n, 0n, IV_H3];
  const absorption = [domain, left, right];
  const absorbedState = [domain, left, right, IV_H3];
  // The locked library permutation mutates its argument; retain the boundary
  // state separately so initialization/absorption evidence stays observable.
  const permutedState = permute([...absorbedState]);
  const libraryHash = poseidon2Hash(absorption);
  if (permutedState[0] !== libraryHash) throw new Error("permutation lane 0 differs from fixed-length H3");
  return { initialState, absorption, absorbedState, permutedState, outputLane: 0, output: permutedState[0] };
}

export const hashSiloedNote = (contractAddress: bigint, noteHash: bigint) =>
  poseidon2H3Trace(DOM_SEP_SILOED, contractAddress, noteHash).output;
export const hashUniqueNote = (nonce: bigint, siloedNote: bigint) =>
  poseidon2H3Trace(DOM_SEP_UNIQUE, nonce, siloedNote).output;
export const hashAztecMerkleNode = (left: bigint, right: bigint) =>
  poseidon2H3Trace(DOM_SEP_MERKLE, left, right).output;

export const hashBn1 = (value: bigint) => BigInt(poseidon1([value]));
export const hashBn2 = (left: bigint, right: bigint) => BigInt(poseidon2([left, right]));
export const hashBn3 = (a: bigint, b: bigint, c: bigint) => BigInt(poseidon3([a, b, c]));

export function groundMerkleRoot(
  leaf: bigint,
  leafIndex: bigint,
  path: bigint[],
  nodeHash: (left: bigint, right: bigint) => bigint,
) {
  let node = leaf;
  const levels: Array<{ level: number; bit: number; left: bigint; right: bigint; parent: bigint }> = [];
  for (let level = 0; level < path.length; level++) {
    const bit = Number((leafIndex >> BigInt(level)) & 1n);
    const left = bit === 0 ? node : path[level];
    const right = bit === 0 ? path[level] : node;
    const parent = nodeHash(left, right);
    levels.push({ level, bit, left, right, parent });
    node = parent;
  }
  return { root: node, levels };
}

export function buildAztecNoteTree(
  noteHash: bigint,
  contractAddress: bigint,
  nonce: bigint,
  leafIndex: bigint,
  path: bigint[],
) {
  const siloed = hashSiloedNote(contractAddress, noteHash);
  const unique = hashUniqueNote(nonce, siloed);
  const tree = groundMerkleRoot(unique, leafIndex, path, hashAztecMerkleNode);
  return { noteHash, contractAddress, nonce, leafIndex, path, siloed, unique, ...tree };
}

const asBigInt = (value: string | number | bigint) => BigInt(value);
const hex = (value: bigint) => "0x" + value.toString(16).padStart(64, "0");
const sha256 = (bytes: Buffer) => crypto.createHash("sha256").update(bytes).digest("hex");

function checkWitness(provenance: any, witnessPath: string, proofInputPath: string) {
  const witnessBytes = fs.readFileSync(witnessPath);
  const witnessRecord = JSON.parse(witnessBytes.toString("utf8"));
  const proofBytes = fs.readFileSync(proofInputPath);
  const proofRecord = JSON.parse(proofBytes.toString("utf8"));
  const inputs = proofRecord.proofInputs;
  const witnesses = witnessRecord.witnesses;
  const value = (index: number) => asBigInt(witnesses[String(index)]);
  const checks = provenance.calls.map((call: any) => {
    const observedInput = call.input_witnesses.map((index: number) => value(index));
    const observedOutput = call.output_witnesses.map((index: number) => value(index));
    const expectedOutput = permute([...observedInput]);
    const expectedDomain = BigInt(call.boundary.domain_separator);
    const pass = observedInput[0] === expectedDomain && observedInput[3] === IV_H3 &&
      observedOutput.every((item: bigint, i: number) => item === expectedOutput[i]);
    if (!pass) throw new Error(`Poseidon2 mismatch at opcode ${call.opcode_index}`);
    return {
      ordinal: call.ordinal,
      opcodeIndex: call.opcode_index,
      construction: call.construction,
      merkleLevel: call.merkle_level,
      orientationCandidate: call.orientation_candidate,
      input: observedInput.map(hex),
      output: observedOutput.map(hex),
      outputLane0: hex(observedOutput[0]),
      pass,
    };
  });

  const nullifierPreimage = asBigInt(inputs.nullifier_preimage);
  const secret = asBigInt(inputs.secret);
  const chainId = asBigInt(inputs.chain_id);
  const amount = asBigInt(inputs.amount);
  const preCommitment = hashBn3(nullifierPreimage, secret, chainId);
  const commitment = hashBn2(preCommitment, amount);
  const nullifier = hashBn1(nullifierPreimage);
  if (nullifier !== asBigInt(inputs.nullifier)) throw new Error("BN hash_1/nullifier mismatch");
  const evm = groundMerkleRoot(
    commitment,
    asBigInt(inputs.evm_merkle_data.leaf_index),
    inputs.evm_merkle_data.hash_path.map(asBigInt),
    hashBn2,
  );
  if (evm.root !== asBigInt(inputs.origin_local_root)) throw new Error("BN hash_2 EVM tree root mismatch");

  const aztec = buildAztecNoteTree(
    commitment,
    asBigInt(inputs.aztec_warptoad_address),
    asBigInt(inputs.aztec_merkle_data.leaf_nonce),
    asBigInt(inputs.aztec_merkle_data.leaf_index),
    inputs.aztec_merkle_data.hash_path.map(asBigInt),
  );
  const selectedAztecCandidates = checks.filter((item: any) => item.construction === "merkle_node" && item.orientationCandidate === "node_left");
  const activeAztec = Boolean(inputs.is_from_aztec);
  const indexZeroCandidateMatch = asBigInt(inputs.aztec_merkle_data.leaf_index) === 0n
    ? aztec.root === asBigInt(selectedAztecCandidates.at(-1).outputLane0)
    : null;
  if (activeAztec && indexZeroCandidateMatch === false) {
    throw new Error("ground Poseidon2 Merkle builder differs from active nargo output chain");
  }
  return {
    witness: { path: witnessPath, sha256: sha256(witnessBytes), operation: witnessRecord.operation },
    proofInput: { path: proofInputPath, sha256: sha256(proofBytes) },
    poseidon2: { checkedOpcodes: checks.length, passed: checks.every((item: any) => item.pass), checks },
    bn254: {
      hash1Nullifier: hex(nullifier),
      hash3PreCommitment: hex(preCommitment),
      hash2Commitment: hex(commitment),
      evmTreeRoot: hex(evm.root),
      evmTreeMatchesOriginRoot: true,
    },
    aztecGroundTree: {
      inactiveInThisHonestEvmFixture: !activeAztec,
      siloed: hex(aztec.siloed), unique: hex(aztec.unique), root: hex(aztec.root),
      levels: aztec.levels.map(level => ({ ...level, left: hex(level.left), right: hex(level.right), parent: hex(level.parent) })),
      matchesNargoCandidateChainForIndexZero: activeAztec ? indexZeroCandidateMatch : null,
      inactiveBranchNote: activeAztec ? null : "No root-chain claim: beta.22 predicates the inactive Aztec branch; all 86 permutation input/output tuples are still checked directly.",
    },
  };
}

async function main() {
  const [provenancePath, outputPath, ...pairs] = process.argv.slice(2);
  if (!provenancePath || !outputPath || pairs.length === 0 || pairs.length % 2 !== 0) {
    throw new Error("usage: d1p_15_hash_reference.ts PROVENANCE OUTPUT WITNESS PROOF_JSON [WITNESS PROOF_JSON ...]");
  }
  const provenanceBytes = fs.readFileSync(provenancePath);
  const provenance = JSON.parse(provenanceBytes.toString("utf8"));
  const fixtures = [];
  for (let i = 0; i < pairs.length; i += 2) fixtures.push(checkWitness(provenance, pairs[i], pairs[i + 1]));
  const result = {
    schema: "bindcheck.d1p15.hash-reference-check/v1",
    construction: {
      poseidon2H3: "state=[0,0,0,3*2^64]; add [domain,left,right]; one width-4 permutation; output lane 0",
      bn254: ["poseidon-lite hash_1", "poseidon-lite hash_2", "poseidon-lite hash_3"],
      groundMerkleTree: "little-endian leaf-index bits; siblings ordered leaf-to-root",
    },
    dependencies: { poseidon2: "@zkpassport/poseidon2@0.6.2", poseidonBn254: "poseidon-lite@0.3.0" },
    provenance: { path: provenancePath, sha256: sha256(provenanceBytes) },
    fixtures,
    allPassed: fixtures.every((fixture: any) => fixture.poseidon2.passed),
  };
  fs.writeFileSync(outputPath, JSON.stringify(result, (_, value) => typeof value === "bigint" ? value.toString() : value, 2) + "\n");
  console.log(JSON.stringify({ fixtures: fixtures.length, checkedOpcodes: fixtures.reduce((n, f) => n + f.poseidon2.checkedOpcodes, 0), allPassed: result.allPassed }));
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => {
    console.error(error);
    process.exitCode = 1;
  });
}

