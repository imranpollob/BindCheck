// Checker unit tests (node --test). Inputs are the REAL exported records (results/raw/T06/records),
// perturbed by deletion/renaming. Tests marked SYNTHETIC build a record that was never executed; they
// exist only to exercise checker logic and are never part of the scenario evaluation table.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");
const { checkRecord, batchIdOf } = require("../checker.js");

const root = path.join(__dirname, "..", "..");
const spec = JSON.parse(fs.readFileSync(path.join(root, "bindcheck/spec/batch_backing.spec.json"), "utf8"));
const recDir = path.join(root, "results/raw/T06/records");
const load = (id) => JSON.parse(fs.readFileSync(path.join(recDir, `${id}.json`), "utf8"));
const clone = (o) => JSON.parse(JSON.stringify(o));
const del = (rec, p) => { const ks = p.split("."); let c = rec; for (const k of ks.slice(0, -1)) c = c[k]; delete c[ks.at(-1)]; return rec; };
const verdict = (rec) => checkRecord(rec, spec).verdict;
const CLEAN = ["NO_VIOLATION", "REVERTED_UNCHANGED"];

const real = Object.fromEntries(fs.readdirSync(recDir).map((f) => f.replace(".json", "")).map((id) => [id, load(id)]));
const base = Object.fromEntries(Object.entries(real).map(([id, r]) => [id, verdict(r)]));

test("baseline: records are present and every verdict is definite", () => {
  assert.strictEqual(Object.keys(real).length, 7);
  for (const v of Object.values(base)) assert.ok(["NO_VIOLATION", "VIOLATION", "REVERTED_UNCHANGED"].includes(v), v);
});

test("renaming executionId, addresses and chain metadata does not change verdicts", () => {
  for (const [id, r] of Object.entries(real)) {
    const c = clone(r);
    c.executionId = "renamed-" + id.split("").reverse().join("");
    c.consumer = "0x" + "ab".repeat(20);
    c.verifier = "0x" + "cd".repeat(20);
    c.chain = { chainId: "1", blockNumber: "999", timestamp: "5" };
    assert.strictEqual(verdict(c), base[id], id);
  }
});

test("swapping executionIds between records: verdict follows the evidence, not the id", () => {
  const a = clone(real["exec-02"]), b = clone(real["exec-01"]);
  [a.executionId, b.executionId] = [b.executionId, a.executionId];
  assert.strictEqual(verdict(a), base["exec-02"]);
  assert.strictEqual(verdict(b), base["exec-01"]);
});

test("checker source and spec contain no scenario/variant names and no hard-coded row or amount rules", () => {
  // Comments and regex length quantifiers such as {40} (hex digits of an address) are not business rules.
  const src = fs.readFileSync(path.join(root, "bindcheck/checker.js"), "utf8").replace(/\/\/.*$/gm, "").replace(/\{\d+\}/g, "{}");
  const specTxt = fs.readFileSync(path.join(root, "bindcheck/spec/batch_backing.spec.json"), "utf8");
  for (const txt of [src, specTxt]) {
    assert.doesNotMatch(txt, /mutant|repaired|numRealTxs|BackedBatch|scenario|oracle|expectedVerdict|exec-0/i);
    assert.doesNotMatch(txt, /\b(40|350|390|1350|1390|100|250)\b/);
    assert.doesNotMatch(txt, /row\s*(===?|==)\s*[0-9]/);
  }
});

test("missing required evidence is never a clean verdict", () => {
  const settled = ["exec-01", "exec-02", "exec-03", "exec-05", "exec-07"];
  const reverted = ["exec-04", "exec-06"];
  const requiredAll = ["submission.status", "publicInputs", "publicInputLayout", "batchId", "consumer", "pre", "post",
    "pre.commitment", "pre.consumedBacking", "pre.ethBalance", "pre.rows", "post.commitment", "post.consumedBacking", "post.ethBalance", "post.rows"];
  const requiredSettled = ["verifierCall", "verifierCall.observed", "verifierCall.calldata", "verifierCall.revertedInScope"];
  for (const id of [...settled, ...reverted]) {
    for (const p of [...requiredAll, ...(settled.includes(id) ? requiredSettled : [])]) {
      const v = verdict(del(clone(real[id]), p));
      assert.strictEqual(v, "INCONCLUSIVE", `${id} without ${p} -> ${v}`);
    }
    for (let i = 0; i < 4; i++) {
      for (const k of ["funded", "amount", "consumed"]) {
        for (const side of ["pre", "post"]) {
          const c = clone(real[id]); delete c[side].rows[i][k];
          assert.strictEqual(verdict(c), "INCONCLUSIVE", `${id} ${side}.rows[${i}].${k}`);
        }
      }
    }
    const c = clone(real[id]); c.pre.rows.pop();
    assert.strictEqual(verdict(c), "INCONCLUSIVE", `${id} short rows`);
  }
});

test("a settled record whose verifier call was not observed is inconclusive (even if state looks fine)", () => {
  const c = clone(real["exec-01"]);
  c.verifierCall = { observed: false };
  assert.strictEqual(verdict(c), "INCONCLUSIVE");
});

test("optional fields may be absent without changing verdicts", () => {
  for (const [id, r] of Object.entries(real)) {
    const c = clone(r);
    delete c.verifierRecheck; delete c.chain; delete c.verifier; delete c.executionId;
    if (c.submission) delete c.submission.revertData;
    assert.strictEqual(verdict(c), base[id], id);
  }
});

test("malformed or inconsistent evidence is an evidence error, never clean", () => {
  const mut = (id, f) => { const c = clone(real[id]); f(c); return verdict(c); };
  assert.strictEqual(mut("exec-01", (c) => { c.pre.rows[0].amount = "0x64"; }), "EVIDENCE_ERROR");
  assert.strictEqual(mut("exec-01", (c) => { c.pre.rows[0].amount = 100; }), "EVIDENCE_ERROR");
  assert.strictEqual(mut("exec-01", (c) => { c.pre.rows[0].amount = "-1"; }), "EVIDENCE_ERROR");
  assert.strictEqual(mut("exec-01", (c) => { c.pre.rows[0].amount = "0100"; }), "EVIDENCE_ERROR");
  assert.strictEqual(mut("exec-01", (c) => { c.batchId = "0x" + "11".repeat(32); }), "EVIDENCE_ERROR");
  assert.strictEqual(mut("exec-01", (c) => { c.submission.status = "maybe"; }), "EVIDENCE_ERROR");
  assert.strictEqual(mut("exec-01", (c) => { c.publicInputs.pop(); }), "EVIDENCE_ERROR");
  assert.strictEqual(mut("exec-01", (c) => { c.publicInputLayout.active = [3, 4, 5, 6]; }), "EVIDENCE_ERROR");
  assert.strictEqual(mut("exec-01", (c) => { c.verifierCall.revertedInScope = true; }), "EVIDENCE_ERROR");
  assert.strictEqual(mut("exec-01", (c) => { c.verifierRecheck.result = false; }), "EVIDENCE_ERROR");
  // verifier received different inputs than the settlement inputs
  assert.strictEqual(mut("exec-01", (c) => { c.verifierCall.calldata = c.verifierCall.calldata.slice(0, -2) + "ff"; }), "EVIDENCE_ERROR");
  // wrong selector
  assert.strictEqual(mut("exec-01", (c) => { c.verifierCall.calldata = "0x00000000" + c.verifierCall.calldata.slice(10); }), "EVIDENCE_ERROR");
  // reverted but the observed state moved: inconsistent with revert semantics
  assert.strictEqual(mut("exec-04", (c) => { c.post.consumedBacking = "1"; }), "EVIDENCE_ERROR");
  assert.strictEqual(mut("exec-04", (c) => { c.post.rows[0].consumed = true; }), "EVIDENCE_ERROR");
  assert.strictEqual(mut("exec-06", (c) => { c.post.ethBalance = "0"; }), "EVIDENCE_ERROR");
  // flag outside {0,1}
  assert.strictEqual(mut("exec-01", (c) => { c.publicInputs[4] = "2"; c.batchId = batchIdOf(c.publicInputs.map(BigInt)); }), "EVIDENCE_ERROR");
});

test("no clean verdict when a settled record's per-row evidence is altered to hide a shortfall", () => {
  // exec-07: row 3 funded but not consumed. Flipping evidence cannot produce a clean verdict unless it is consistently rewritten.
  const c = clone(real["exec-07"]);
  assert.strictEqual(verdict(c), "VIOLATION");
  c.post.rows[3].consumed = true; // consumed flag now claims coverage, but consumedBacking delta no longer matches
  assert.ok(!CLEAN.includes(verdict(c)));
});

test("commitment value is not the success indicator: unchanged commitment with unmet obligation is still a finding", () => {
  const c = clone(real["exec-02"]);
  c.post.commitment = c.pre.commitment; // state did not follow the authenticated new commitment
  const r = checkRecord(c, spec);
  assert.strictEqual(r.verdict, "VIOLATION");
  assert.ok(r.findings.some((f) => f.kind === "commitment_binding_mismatch"));
  assert.ok(r.findings.some((f) => f.kind === "missing_consumption"));
});

test("SYNTHETIC: a legitimate no-op (all rows inactive, old == new commitment) is clean though the commitment value is unchanged", () => {
  const c = clone(real["exec-05"]);
  const ins = ["0", "0", "0", "0", "0", "0", "0", "0", real["exec-05"].publicInputs[8], real["exec-05"].publicInputs[8]];
  c.publicInputs = ins;
  c.batchId = batchIdOf(ins.map(BigInt));
  // verifier calldata carries the same public inputs
  const head = c.verifierCall.calldata.slice(0, 2 + 8 + 8 * 64);
  c.verifierCall.calldata = head + ins.map((v) => BigInt(v).toString(16).padStart(64, "0")).join("");
  // state: nothing consumed, nothing changes, commitment unchanged
  c.pre = clone(c.pre); c.pre.rows = c.pre.rows.map(() => ({ funded: false, amount: "0", consumed: false }));
  c.pre.commitment = ins[8]; c.pre.consumedBacking = "0";
  c.post = clone(c.pre);
  const r = checkRecord(c, spec);
  assert.strictEqual(r.verdict, "NO_VIOLATION", JSON.stringify(r));
});

test("SYNTHETIC: replayed settlement (entry already consumed before the call) is reported with its own reason", () => {
  const c = clone(real["exec-01"]);
  c.pre.rows = clone(c.post.rows); // entries already consumed before this call
  c.pre.consumedBacking = c.post.consumedBacking;
  const r = checkRecord(c, spec);
  assert.strictEqual(r.verdict, "VIOLATION");
  assert.ok(r.findings.every((f) => f.kind !== "missing_consumption" || f.reason === "already_consumed_before_settlement"));
});
