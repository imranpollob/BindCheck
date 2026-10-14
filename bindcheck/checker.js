// BindCheck T06: trace-based coverage checker for OBSERVED executions.
//
// This is a checker for recorded executions of one manually specified property. It is not a static
// detector and a clean verdict is not a proof that a contract is safe: it says only that the
// recorded evidence for that one execution satisfies the specification.
//
// Inputs: execution records + the manual specification. It reads no expected labels, no contract
// or scenario names, and contains no per-row or per-amount rules; everything comes from the spec.
//
// Verdicts:
//   NO_VIOLATION        settled; every spec obligation is met by the evidence
//   VIOLATION           settled; at least one obligation/binding/accounting finding
//   REVERTED_UNCHANGED  reverted; no committed coverage violation (observed state unchanged)
//   INCONCLUSIVE        required evidence is absent (never a clean verdict)
//   EVIDENCE_ERROR      evidence present but malformed or internally inconsistent
//
// usage: node bindcheck/checker.js <spec.json> <records_dir> <out.json>
const fs = require("fs");
const path = require("path");
const { keccak256 } = require("js-sha3");

const DEC = /^(0|[1-9][0-9]*)$/;
const HEX_ADDR = /^0x[0-9a-fA-F]{40}$/;
const HEX32 = /^0x[0-9a-fA-F]{64}$/;

class Missing extends Error { constructor(p) { super(p); this.path = p; } }
class Bad extends Error { constructor(m) { super(m); } }

const get = (obj, p) => {
  let cur = obj;
  for (const k of p.split(".")) {
    if (cur === null || typeof cur !== "object" || !(k in cur) || cur[k] === undefined) throw new Missing(p);
    cur = cur[k];
  }
  return cur;
};
const dec = (v, where) => {
  if (typeof v !== "string" || !DEC.test(v)) throw new Bad(`${where}: not a canonical decimal string`);
  return BigInt(v);
};
const word = (n) => n.toString(16).padStart(64, "0");

function batchIdOf(inputs) {
  return "0x" + keccak256(Buffer.from(inputs.map(word).join(""), "hex"));
}

function readSnapshot(rec, side, spec) {
  const base = side;
  const snap = {
    commitment: dec(get(rec, `${base}.commitment`), `${base}.commitment`),
    backing: dec(get(rec, `${base}.consumedBacking`), `${base}.consumedBacking`),
    eth: dec(get(rec, `${base}.ethBalance`), `${base}.ethBalance`),
    rows: [],
  };
  const rows = get(rec, `${base}.rows`);
  if (!Array.isArray(rows)) throw new Bad(`${base}.rows not an array`);
  if (rows.length !== spec.publicInputs.amount.length) throw new Missing(`${base}.rows (expected ${spec.publicInputs.amount.length} entries, got ${rows.length})`);
  rows.forEach((r, i) => {
    if (r === null || typeof r !== "object") throw new Missing(`${base}.rows[${i}]`);
    for (const k of ["funded", "amount", "consumed"]) if (!(k in r)) throw new Missing(`${base}.rows[${i}].${k}`);
    if (typeof r.funded !== "boolean" || typeof r.consumed !== "boolean") throw new Bad(`${base}.rows[${i}]: funded/consumed must be booleans`);
    snap.rows.push({ funded: r.funded, amount: dec(r.amount, `${base}.rows[${i}].amount`), consumed: r.consumed });
  });
  return snap;
}

function sameSnapshot(a, b) {
  if (a.commitment !== b.commitment || a.backing !== b.backing || a.eth !== b.eth) return false;
  return a.rows.every((r, i) => r.funded === b.rows[i].funded && r.amount === b.rows[i].amount && r.consumed === b.rows[i].consumed);
}

function checkRecord(rec, spec) {
  const out = { executionId: rec && typeof rec.executionId === "string" ? rec.executionId : null, verdict: null, summary: "", findings: [], accounting: null, notes: [] };
  const finish = (verdict, summary) => { out.verdict = verdict; out.summary = summary; return out; };
  try {
    // ---- required evidence (absence => INCONCLUSIVE) ----
    const status = get(rec, "submission.status");
    const rawInputs = get(rec, "publicInputs");
    const layout = get(rec, "publicInputLayout");
    const recBatchId = get(rec, "batchId");
    const pre = readSnapshot(rec, "pre", spec);
    const post = readSnapshot(rec, "post", spec);

    // ---- format / consistency of the statement (malformed => EVIDENCE_ERROR) ----
    if (status !== "success" && status !== "reverted") throw new Bad(`submission.status must be "success" or "reverted"`);
    if (!Array.isArray(rawInputs) || rawInputs.length !== spec.publicInputs.count) throw new Bad(`publicInputs must have ${spec.publicInputs.count} entries`);
    const inputs = rawInputs.map((v, i) => dec(v, `publicInputs[${i}]`));
    if (JSON.stringify(layout) !== JSON.stringify({ amount: spec.publicInputs.amount, active: spec.publicInputs.active, oldCommitment: spec.publicInputs.oldCommitment, newCommitment: spec.publicInputs.newCommitment })) {
      throw new Bad("recorded publicInputLayout differs from the specification layout");
    }
    if (typeof recBatchId !== "string" || !HEX32.test(recBatchId)) throw new Bad("batchId must be 0x + 32 bytes");
    if (recBatchId.toLowerCase() !== batchIdOf(inputs)) throw new Bad("batchId does not match the specification's derivation from the public inputs");
    const consumer = get(rec, "consumer");
    if (typeof consumer !== "string" || !HEX_ADDR.test(consumer)) throw new Bad("consumer must be an address");

    const rows = spec.publicInputs.amount.map((ai, i) => {
      const flag = inputs[spec.publicInputs.active[i]];
      let active;
      if (flag === BigInt(spec.activation.activeValue)) active = true;
      else if (flag === BigInt(spec.activation.inactiveValue)) active = false;
      else throw new Bad(`row ${i}: activation flag ${flag} is neither ${spec.activation.activeValue} nor ${spec.activation.inactiveValue}`);
      return { row: i, active, amount: inputs[ai] * BigInt(spec.conversion.weiPerUnit) };
    });
    const oldC = inputs[spec.publicInputs.oldCommitment];
    const newC = inputs[spec.publicInputs.newCommitment];

    // ---- reverted settlement: protected state must be unchanged ----
    if (status === "reverted") {
      if (!sameSnapshot(pre, post)) throw new Bad("submission reverted but observed protected state differs; inconsistent with revert semantics (exporter or observation fault)");
      return finish("REVERTED_UNCHANGED", "reverted; no committed coverage violation");
    }

    // ---- successful settlement ----
    // The verifier-call evidence is required: without it we cannot say the statement was verified.
    const vc = get(rec, "verifierCall");
    if (vc.observed !== true) throw new Missing("verifierCall.observed (no evidence that the verifier was called)");
    const calldata = get(rec, "verifierCall.calldata");
    if (typeof vc.revertedInScope !== "boolean") throw new Missing("verifierCall.revertedInScope");
    if (vc.revertedInScope) throw new Bad("settlement succeeded but the recorded verifier call is marked reverted");
    if (typeof calldata !== "string" || !/^0x([0-9a-fA-F]{2})+$/.test(calldata)) throw new Bad("verifierCall.calldata not hex");
    const sel = keccak256(spec.verifierCall.signature).slice(0, 8);
    if (calldata.slice(2, 10).toLowerCase() !== sel) throw new Bad("verifier call selector differs from the specification");
    const body = calldata.slice(10);
    const off = spec.verifierCall.publicInputsWordOffset * 64;
    const n = spec.verifierCall.publicInputsWordCount;
    if (body.length < off + n * 64) throw new Bad("verifier calldata too short for the specified public-input words");
    for (let i = 0; i < n; i++) {
      const w = BigInt("0x" + body.slice(off + i * 64, off + (i + 1) * 64));
      if (w !== inputs[i]) throw new Bad(`public input ${i}: verifier received a different value than the recorded settlement inputs`);
    }
    if (rec.verifierRecheck && rec.verifierRecheck.result === false) throw new Bad("direct verifier re-check rejects the recorded statement although settlement succeeded");

    // commitment binding: authenticated old/new commitments (not "did the value change")
    if (pre.commitment !== oldC) out.findings.push({ kind: "commitment_binding_mismatch", detail: `pre-state commitment ${pre.commitment} != authenticated old commitment ${oldC}` });
    if (post.commitment !== newC) out.findings.push({ kind: "commitment_binding_mismatch", detail: `post-state commitment ${post.commitment} != authenticated new commitment ${newC}` });

    // per-row obligations
    let required = 0n, covered = 0n, newlyConsumed = 0n;
    for (const r of rows) {
      const a = pre.rows[r.row], b = post.rows[r.row];
      const newly = !a.consumed && b.consumed;
      if (newly) newlyConsumed += a.amount;
      if (!r.active) {
        if (newly) out.findings.push({ kind: "unexpected_consumption", row: r.row, amount: a.amount.toString(), detail: "inactive row's escrow entry was consumed" });
        continue;
      }
      required += r.amount;
      let reason = null;
      if (!a.funded) reason = "unfunded";
      else if (a.amount !== r.amount) reason = "amount_mismatch";
      else if (a.consumed) reason = "already_consumed_before_settlement";
      else if (!b.consumed) reason = "not_consumed_by_settlement";
      if (reason === null) { covered += r.amount; continue; }
      out.findings.push({
        kind: "missing_consumption", row: r.row, amount: r.amount.toString(), reason,
        fundedButUnconsumed: a.funded && a.amount === r.amount && !a.consumed && !b.consumed,
        escrowAmountHeld: a.funded ? a.amount.toString() : "0",
      });
    }

    // consumed amounts vs consumedBacking change (total ETH held is NOT used as a substitute)
    const deltaBacking = post.backing - pre.backing;
    if (deltaBacking !== newlyConsumed) out.findings.push({ kind: "backing_accounting_mismatch", detail: `sum of newly consumed entries ${newlyConsumed} != consumedBacking change ${deltaBacking}` });

    const missing = out.findings.filter((f) => f.kind === "missing_consumption").reduce((s, f) => s + BigInt(f.amount), 0n);
    out.accounting = {
      requiredCredit: required.toString(), coveredByConsumption: covered.toString(), missingConsumption: missing.toString(),
      newlyConsumedTotal: newlyConsumed.toString(), consumedBackingDelta: deltaBacking.toString(),
      ethBefore: pre.eth.toString(), ethAfter: post.eth.toString(),
    };
    if (out.findings.some((f) => f.fundedButUnconsumed)) out.notes.push("Some missing obligations have escrow physically held but unconsumed: a consumption shortfall, not absent funds.");
    if (out.findings.some((f) => f.kind === "missing_consumption" && f.reason === "unfunded")) out.notes.push("Some missing obligations are unfunded: no escrow was present for them.");
    if (out.findings.length === 0) return finish("NO_VIOLATION", "settled; all specified obligations met by the recorded evidence");
    return finish("VIOLATION", `settled; ${out.findings.length} finding(s), missing consumption ${missing}`);
  } catch (e) {
    if (e instanceof Missing) { out.findings = []; out.notes = [`missing required evidence: ${e.path}`]; return finish("INCONCLUSIVE", `required evidence absent: ${e.path}`); }
    if (e instanceof Bad) { out.findings = []; out.notes = [e.message]; return finish("EVIDENCE_ERROR", e.message); }
    throw e;
  }
}

function checkDir(spec, dir) {
  return fs.readdirSync(dir).filter((f) => f.endsWith(".json")).sort().map((f) => {
    let rec;
    try { rec = JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")); }
    catch (e) { return { file: f, executionId: null, verdict: "EVIDENCE_ERROR", summary: `unparseable record: ${e.message}`, findings: [], accounting: null, notes: [] }; }
    return { file: f, ...checkRecord(rec, spec) };
  });
}

module.exports = { checkRecord, checkDir, batchIdOf };

if (require.main === module) {
  const [specF, dir, outF] = process.argv.slice(2);
  if (!specF || !dir || !outF) { console.error("usage: node bindcheck/checker.js <spec.json> <records_dir> <out.json>"); process.exit(2); }
  const spec = JSON.parse(fs.readFileSync(specF, "utf8"));
  const results = checkDir(spec, dir);
  fs.writeFileSync(outF, JSON.stringify({ specId: spec.specId, results }, null, 2) + "\n");
  for (const r of results) console.log(`${r.file}\t${r.verdict}\t${r.summary}`);
}
