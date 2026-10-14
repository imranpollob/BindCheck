// Compares checker verdicts with the independently written oracle labels (Foundry-side).
// Shares no verdict logic with the checker: it only joins by executionId and compares fields.
// usage: node bindcheck/compare.js <checker_verdicts.json> <oracle_dir> <out.md> <out.json>
const fs = require("fs");
const path = require("path");
const [vF, oracleDir, outMd, outJson] = process.argv.slice(2);
const verdicts = JSON.parse(fs.readFileSync(vF, "utf8")).results;
const oracle = {};
for (const f of fs.readdirSync(oracleDir).filter((f) => f.endsWith(".json"))) {
  const o = JSON.parse(fs.readFileSync(path.join(oracleDir, f), "utf8"));
  oracle[o.executionId] = o;
}
const key = (m) => `${m.row}:${m.amount}:${m.fundedButUnconsumed}`;
const rows = [];
let allAgree = true;
for (const v of verdicts) {
  const o = oracle[v.executionId];
  let agree = false, detail = "no oracle entry";
  if (o) {
    const gotMissing = (v.findings || []).filter((f) => f.kind === "missing_consumption").map((f) => key({ row: f.row, amount: f.amount, fundedButUnconsumed: f.fundedButUnconsumed })).sort();
    const wantMissing = o.expectedMissing.map((m) => key({ row: m.row, amount: m.amount, fundedButUnconsumed: m.fundedButUnconsumed })).sort();
    const gotDeficit = v.accounting ? v.accounting.missingConsumption : "0";
    const verdictOk = v.verdict === o.expectedVerdict;
    const missingOk = JSON.stringify(gotMissing) === JSON.stringify(wantMissing);
    const deficitOk = gotDeficit === o.expectedDeficit;
    agree = verdictOk && missingOk && deficitOk;
    detail = agree ? "verdict, missing rows/amounts and deficit agree" : `verdict ${verdictOk ? "ok" : `MISMATCH (${v.verdict} vs ${o.expectedVerdict})`}; missing ${missingOk ? "ok" : `MISMATCH (${gotMissing} vs ${wantMissing})`}; deficit ${deficitOk ? "ok" : `MISMATCH (${gotDeficit} vs ${o.expectedDeficit})`}`;
  }
  const unmatched = Object.keys(oracle).filter((id) => !verdicts.some((x) => x.executionId === id));
  if (!agree) allAgree = false;
  rows.push({ executionId: v.executionId, checkerVerdict: v.verdict, oracleVerdict: o ? o.expectedVerdict : null, checkerMissing: (v.findings || []).filter((f) => f.kind === "missing_consumption").map((f) => ({ row: f.row, amount: f.amount })), agree, detail });
  if (unmatched.length) { allAgree = false; rows.push({ executionId: "(oracle without record)", detail: unmatched.join(",") , agree: false }); break; }
}
for (const id of Object.keys(oracle)) if (!verdicts.some((v) => v.executionId === id)) { allAgree = false; rows.push({ executionId: id, agree: false, detail: "oracle entry without checker verdict" }); }
const md = ["| executionId | checker verdict | oracle verdict | missing (checker) | agree |", "|---|---|---|---|---|",
  ...rows.map((r) => `| ${r.executionId} | ${r.checkerVerdict ?? "-"} | ${r.oracleVerdict ?? "-"} | ${(r.checkerMissing || []).map((m) => `row ${m.row}: ${m.amount}`).join("; ") || "-"} | ${r.agree ? "yes" : "NO: " + r.detail} |`)].join("\n") + "\n";
fs.writeFileSync(outMd, md);
fs.writeFileSync(outJson, JSON.stringify({ allAgree, rows }, null, 2) + "\n");
console.log(md);
console.log(allAgree ? "ORACLE AGREEMENT: all records agree" : "ORACLE AGREEMENT: DISAGREEMENT");
process.exit(allAgree ? 0 : 1);
