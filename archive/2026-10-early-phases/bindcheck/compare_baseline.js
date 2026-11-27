// T07 comparison: trace checker (bindcheck/checker.js, run over records only) vs the direct Foundry baseline results.
// Joins by case id. Baseline files and the design-intent prediction are used ONLY here, never as checker input.
// usage: node bindcheck/compare_baseline.js <spec.json> <records_dir> <baseline_dir> <out_dir>
const fs = require("fs");
const path = require("path");
const { performance } = require("perf_hooks");
const { checkDir } = require("./checker.js");

const [specF, recDir, baseDir, outDir] = process.argv.slice(2);
const spec = JSON.parse(fs.readFileSync(specF, "utf8"));

// ---- checker run (timed in-process: reads + parses records, evaluates the spec) ----
const t0 = performance.now();
const results = checkDir(spec, recDir);
const firstMs = performance.now() - t0;
const reps = [];
for (let i = 0; i < 20; i++) { const s = performance.now(); checkDir(spec, recDir); reps.push(performance.now() - s); }
reps.sort((a, b) => a - b);
const timing = { records: results.length, firstRunMs: +firstMs.toFixed(2), medianOf20Ms: +reps[10].toFixed(2), perRecordMedianMs: +(reps[10] / results.length).toFixed(3) };

const byId = Object.fromEntries(results.map((r) => [r.executionId, r]));
const base = fs.readdirSync(baseDir).filter((f) => f.endsWith(".json")).sort().map((f) => JSON.parse(fs.readFileSync(path.join(baseDir, f), "utf8")));

// ---- design-intent prediction from configuration only (independent of both methods) ----
const FIX = {
  original: { amount: [100, 250, 0, 40], active: [1, 1, 0, 1] },
  padded: { amount: [100, 250, 0, 0], active: [1, 1, 0, 0] },
};
function predict(c) {
  const f = FIX[c.fixture];
  const act = [0, 1, 2, 3].filter((r) => f.active[r] === 1);
  const funded = new Set(c.fundedRows);
  const L = c.limit === null ? 4 : Number(c.limit);
  const prefixActive = act.filter((r) => r < L);
  const outside = act.filter((r) => r >= L);
  let succeeds;
  if (c.consumer === "correct") succeeds = act.every((r) => funded.has(r));
  else if (c.consumer === "mutant") succeeds = prefixActive.every((r) => funded.has(r));
  else succeeds = outside.length === 0 && prefixActive.every((r) => funded.has(r));
  if (!succeeds) return { verdict: "REVERTED_UNCHANGED", missing: [] };
  const omitted = c.consumer === "correct" ? [] : outside;
  if (omitted.length === 0) return { verdict: "NO_VIOLATION", missing: [] };
  return { verdict: "VIOLATION", missing: omitted.map((r) => `${r}:${f.amount[r]}:${funded.has(r)}`).sort() };
}

const cls = (v) => (v === "NO_VIOLATION" || v === "VIOLATION" ? "settled" : v === "REVERTED_UNCHANGED" ? "reverted" : "unclassified");
const rows = [];
const dims = { classification: 0, violationFlag: 0, affectedRowsAndAmounts: 0, missingAmount: 0, stateAfterRejection: 0, commitmentAndAccounting: 0 };
const dis = [];
const tally = {};
const inc = (o, k) => { o[k] = (o[k] || 0) + 1; };
let predChecker = 0, predBaseline = 0;

for (const b of base) {
  const r = byId[b.caseId];
  const key = `${b.consumer}/${b.fixture}`;
  tally[key] = tally[key] || { cases: 0, success: 0, reverted: 0, checker: {}, baseline: {} };
  const T = tally[key]; T.cases++; T[b.status === "success" ? "success" : "reverted"]++;
  if (!r) { dis.push({ caseId: b.caseId, why: "no checker verdict" }); continue; }
  inc(T.checker, r.verdict);
  const bVerdict = b.status === "success" ? (b.baseline.holds ? "CLEAN" : "VIOLATION") : (b.baseline.stateUnchanged ? "REVERTED_UNCHANGED" : "REVERTED_CHANGED");
  inc(T.baseline, bVerdict);

  const bViol = b.status === "success" && !b.baseline.holds;
  const cViol = r.verdict === "VIOLATION";
  const bRows = b.baseline.violations.map((v) => `${v.row}:${v.amount}:${v.fundedButUnconsumed}`).sort();
  const cRows = (r.findings || []).filter((f) => f.kind === "missing_consumption").map((f) => `${f.row}:${f.amount}:${f.fundedButUnconsumed}`).sort();
  const cCommitOrAcct = (r.findings || []).some((f) => f.kind === "commitment_binding_mismatch" || f.kind === "backing_accounting_mismatch");
  const bCommitOrAcct = b.status === "success" && (!b.baseline.commitmentOk || !b.baseline.accountingOk);
  const checks = {
    classification: cls(r.verdict) === b.status.replace("success", "settled"),
    violationFlag: cViol === bViol,
    affectedRowsAndAmounts: JSON.stringify(cRows) === JSON.stringify(bRows),
    missingAmount: (r.accounting ? r.accounting.missingConsumption : "0") === b.baseline.missingAmount,
    stateAfterRejection: b.status === "success" ? true : (r.verdict === "REVERTED_UNCHANGED") === b.baseline.stateUnchanged,
    commitmentAndAccounting: cCommitOrAcct === bCommitOrAcct,
  };
  for (const [k, v] of Object.entries(checks)) { if (v) dims[k]++; else dis.push({ caseId: b.caseId, dim: k, checker: r.verdict, baseline: bVerdict, cRows, bRows }); }

  const p = predict(b);
  const cMatch = r.verdict === p.verdict && JSON.stringify(cRows) === JSON.stringify(p.missing);
  const bPredVerdict = bVerdict === "CLEAN" ? "NO_VIOLATION" : bVerdict;
  const bMatch = bPredVerdict === p.verdict && JSON.stringify(bRows) === JSON.stringify(p.missing);
  if (cMatch) predChecker++; else dis.push({ caseId: b.caseId, dim: "design-prediction(checker)", predicted: p, checker: r.verdict, cRows });
  if (bMatch) predBaseline++; else dis.push({ caseId: b.caseId, dim: "design-prediction(baseline)", predicted: p, baseline: bVerdict, bRows });
  rows.push({ caseId: b.caseId, consumer: b.consumer, fixture: b.fixture, fundedRows: b.fundedRows, limit: b.limit, status: b.status, checker: r.verdict, baseline: bVerdict, predicted: p.verdict, checks });
}
const total = base.length;
const summary = { total, recordsChecked: results.length, baselineFiles: base.length, timing, dimensionAgreement: dims, designPredictionAgreement: { checker: predChecker, baseline: predBaseline }, byConsumerFixture: tally, disagreements: dis };
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, "comparison.json"), JSON.stringify({ summary, rows }, null, 2) + "\n");
fs.writeFileSync(path.join(outDir, "checker_verdicts.json"), JSON.stringify({ specId: spec.specId, specAssumptions: spec.assumptions || [], results }, null, 2) + "\n");

const md = [];
md.push(`Cases: ${total}; checker verdicts: ${results.length}; baseline results: ${base.length}\n`);
md.push("| consumer/fixture | cases | success | reverted | checker verdicts | baseline verdicts |\n|---|---|---|---|---|---|");
for (const [k, v] of Object.entries(tally)) md.push(`| ${k} | ${v.cases} | ${v.success} | ${v.reverted} | ${JSON.stringify(v.checker)} | ${JSON.stringify(v.baseline)} |`);
md.push("\n| dimension | agree / total |\n|---|---|");
for (const [k, v] of Object.entries(dims)) md.push(`| ${k} | ${v} / ${total} |`);
md.push(`| design-intent prediction vs checker | ${predChecker} / ${total} |`);
md.push(`| design-intent prediction vs baseline | ${predBaseline} / ${total} |`);
md.push(`\nChecker time (in-process, ${timing.records} records, read+parse+evaluate): first run ${timing.firstRunMs} ms, median of 20 runs ${timing.medianOf20Ms} ms (${timing.perRecordMedianMs} ms/record)`);
md.push(`\nDisagreements: ${dis.length}`);
fs.writeFileSync(path.join(outDir, "comparison.md"), md.join("\n") + "\n");
console.log(md.join("\n"));
process.exit(dis.length === 0 ? 0 : 1);
