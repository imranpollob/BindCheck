import test from "node:test";
import assert from "node:assert/strict";

import {
  IV_H3,
  buildAztecNoteTree,
  groundMerkleRoot,
  hashAztecMerkleNode,
  hashBn1,
  hashBn2,
  hashBn3,
  poseidon2H3Trace,
} from "./d1p_15_hash_reference.ts";

const PREIMAGE = 4321n;
const SECRET = 1234n;
const CHAIN_ID = 31337n;
const AMOUNT = 5_000_000_000_000_000_000n;
const COMMITMENT = 18657061007963497385873439993474320070394536285434801550476755170557711333402n;

test("BN254 constructions and the ground EVM tree reproduce fixed known values", () => {
  assert.equal(hashBn1(PREIMAGE), 11073944447358252977412171491011187728107721062193052377268397448625136347320n);
  const preCommitment = hashBn3(PREIMAGE, SECRET, CHAIN_ID);
  assert.equal(preCommitment, 6623066489464621701802254125941223588827815953538474237249022404516174581199n);
  assert.equal(hashBn2(preCommitment, AMOUNT), COMMITMENT);
  const tree = groundMerkleRoot(COMMITMENT, 0n, Array(32).fill(0n), hashBn2);
  assert.equal(tree.root, 4185573118082272294431114682221392212882719581807977195739250308368267659392n);
});

test("H3 exposes the exact initialization, absorption, and lane selection", () => {
  const trace = poseidon2H3Trace(2982624097n, 1n, 2n);
  assert.deepEqual(trace.initialState, [0n, 0n, 0n, IV_H3]);
  assert.deepEqual(trace.absorbedState, [2982624097n, 1n, 2n, IV_H3]);
  assert.equal(trace.outputLane, 0);
  assert.equal(trace.output, trace.permutedState[0]);
});

test("ground Aztec tree reproduces both injected O1 roots", () => {
  const path = Array(42).fill(0n);
  const honest = buildAztecNoteTree(COMMITMENT, 0x123456789abcdefn, 0xabcden, 0n, path);
  assert.equal(honest.siloed, 11478906936304517070250487489927795541483571503686645159342431518673288526742n);
  assert.equal(honest.unique, 5721894706942154383654721859197615494167711442710008267424307330393073375310n);
  assert.equal(honest.root, 3135907748845717830443488355540369956875592267363388105579762865688042964914n);

  const foreign = buildAztecNoteTree(COMMITMENT, 0xfedcba987654321n, 0xabcden, 0n, path);
  assert.equal(foreign.siloed, 9688943432914205116743614369224771961951674794720809742334635998114222065405n);
  assert.equal(foreign.unique, 21295477198461621604184384510342901615688370868754085956544331680237973039615n);
  assert.equal(foreign.root, 11363979766525370050262098377889229867316435477982289683297233947360433242380n);
  assert.equal(honest.levels.length, 42);
  assert.equal(foreign.levels.length, 42);
  assert.equal(hashAztecMerkleNode(honest.unique, 0n), honest.levels[0].parent);
});
