#!/usr/bin/env python3
"""Recompute the numbers cited by the three reviews from the files that hold them.

Writes reports/groundtruth/claims-check.json. Each entry records the value, the
file it was computed from, and how. A value that cannot be recomputed from a
local file is written as "MISSING" with the reason.

Usage:
  python3 -I reports/groundtruth/scripts/claims_check.py \
      --zk-raw /Users/imranpollob/Coding/bc/bindcheck-zk/results/raw \
      --d1 /Users/imranpollob/Coding/bc/bindcheck-d1-paper \
      --legacy-raw /Users/imranpollob/Coding/bc/BindCheck/results/raw
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import statistics
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[3]


def rows(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as h:
        return list(csv.DictReader(h))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zk-raw", required=True, type=pathlib.Path)
    ap.add_argument("--d1", required=True, type=pathlib.Path)
    ap.add_argument("--legacy-raw", required=True, type=pathlib.Path)
    a = ap.parse_args()
    out: dict = {"generated_by": "reports/groundtruth/scripts/claims_check.py"}

    # ---- T25 DEV ledger (current analyzer 2741c40e) ----
    led = [r for r in rows(ROOT / "reports/T25-full-dev-ledger.csv") if r["phase"] == "after"]
    t25 = {"source": "reports/T25-full-dev-ledger.csv (phase=after)", "rows": len(led)}
    for p in ("P1", "P2", "P3", "P4", "P5"):
        t25[p] = {
            "verdicts": dict(Counter(r[f"{p}_verdict"] for r in led)),
            "applicability": dict(Counter(r[f"{p}_applicability"] for r in led)),
            "unknown_among_applicable": sum(1 for r in led if r[f"{p}_verdict"] == "UNKNOWN" and r[f"{p}_applicability"] == "APPLICABLE"),
            "applicable": sum(1 for r in led if r[f"{p}_applicability"] == "APPLICABLE"),
            "decided_among_applicable": sum(1 for r in led if r[f"{p}_verdict"] != "UNKNOWN" and r[f"{p}_applicability"] == "APPLICABLE"),
        }
    t25["violation_rows"] = [{"id": r["id"], "repository": r["repository"], "patterns": [p for p in ("P1", "P2", "P3", "P4", "P5") if r[f"{p}_verdict"] == "VIOLATION"]}
                             for r in led if any(r[f"{p}_verdict"] == "VIOLATION" for p in ("P1", "P2", "P3", "P4", "P5"))]
    t25["rows_with_triples"] = sum(1 for r in led if int(r["triples"] or 0) > 0)
    t25["builds_ok"] = sum(int(r["builds_ok"] or 0) for r in led)
    t25["builds_failed"] = sum(int(r["builds_failed"] or 0) for r in led)
    rt = [float(r["runtime_seconds"]) for r in led]
    t25["runtime_seconds"] = {"sum": round(sum(rt), 6), "max": max(rt), "median": statistics.median(rt)}
    t25["historical_rows_P3"] = {r["id"]: f"{r['repository']}@{r['commit'][:10]} P3={r['P3_verdict']} ({r['P3_reasons']})"
                                 for r in led if r["id"].startswith("DEV-H")}
    out["t25"] = t25

    # ---- warning groups ----
    w24 = rows(ROOT / "reports/T24-warning-adjudication.csv")
    w25 = rows(ROOT / "reports/T25-warning-adjudication.csv")
    retained = w24 + [r for r in w25 if r["status"] == "retained-new"]
    expanded = {(r["row"], r["path"], r["line"], r["pattern"]): int(r["after_instances"]) for r in w25 if r["status"] == "retained-expanded"}
    inst = sum(expanded.get((r["row"], r["path"], r["line"], r["pattern"]), int(r.get("instances") or r.get("after_instances") or 0)) for r in retained)
    out["warnings"] = {
        "source": "reports/T24-warning-adjudication.csv + reports/T25-warning-adjudication.csv",
        "retained_groups": len(retained), "retained_instances": inst,
        "author_labels": dict(Counter(r["adjudication"] for r in retained)),
        "removed_before_final": sum(1 for r in w25 if r["status"] == "removed-before-final"),
        "verifier_flags": "see reports/groundtruth/warning-verifier-flags.csv",
    }
    flags = rows(ROOT / "reports/groundtruth/warning-verifier-flags.csv")
    out["warnings"]["groups_with_any_non_real_verifier"] = sum(int(f["flag_non_real_verifier"]) for f in flags)
    out["warnings"]["groups_with_only_non_real_verifiers"] = sum(int(f["flag_all_verifiers_non_real"]) for f in flags)
    out["warnings"]["author_true_positive_on_only_non_real"] = sum(1 for f in flags if f["author_adjudication"] == "true positive" and f["flag_all_verifiers_non_real"] == "1")

    # ---- corpus ----
    corpus = rows(ROOT / "dataset/source-corpus-v2.csv")
    out["corpus"] = {"source": "dataset/source-corpus-v2.csv", "rows": len(corpus), "split": dict(Counter(r["split"] for r in corpus))}
    out["corpus"].update(json.loads((ROOT / "reports/groundtruth/recounts.json").read_text()))

    # ---- on-chain census ----
    census = json.loads((ROOT / "dataset/onchain-census-summary.json").read_text())
    crow = rows(ROOT / "dataset/onchain-census.csv")
    keycols = [c for c in ("chain_id", "chain", "address") if c in crow[0]]
    uniq = {(r.get("chain_id") or r.get("chain"), r.get("address", "").lower()) for r in crow}
    by_chain = Counter(k[0] for k in uniq)
    out["census"] = {"source": "dataset/onchain-census-summary.json; dataset/onchain-census.csv",
                     **{k: census[k] for k in ("exact_deployment_rows", "unique_deployments", "unique_runtime_hashes",
                                               "default_g2_gamma_delta_signature_unique_deployments",
                                               "source_confirmed_consumer_links", "funded_vulnerable_consumer_instances")},
                     "chains_queried": len(census["chains"]),
                     "recount_unique_by_chain_from_csv": dict(by_chain), "csv_key_columns": keycols,
                     "recount_unique_total": len(uniq)}
    cons = json.loads((ROOT / "dataset/onchain-consumers-v2-summary.json").read_text())
    out["consumer_census"] = {"source": "dataset/onchain-consumers-v2-summary.json", "unique_deployments": cons["unique_deployments"],
                              "unique_github_repositories": cons["unique_github_repositories"], "chain_counts": cons["chain_counts"]}

    # ---- T26 harness ----
    s26 = json.loads((a.zk_raw / "T26/dev-dry-run-network/summary.json").read_text())
    out["t26_dev_dry_run_network"] = {"source": "results/raw/T26/dev-dry-run-network/summary.json (bindcheck-zk worktree)",
                                      "families": s26["families"],
                                      "tools": {t: {"verdicts": {k: v["overall"].get(k) for k in ("VIOLATION", "VERIFIED_WITHIN_SCOPE", "UNKNOWN")},
                                                    "unknown_by_reason": v["overall"].get("unknown_by_reason")} for t, v in s26["tools"].items()}}
    meta = list((a.zk_raw / "T26/eval-metadata-07210625783a/families").iterdir())
    out["t26_eval_metadata"] = {"source": "results/raw/T26/eval-metadata-07210625783a/families/*", "family_dirs": len(meta)}

    # ---- E4 observations ----
    def obs(p: pathlib.Path) -> dict:
        return json.loads(p.read_text()) if p.is_file() else {"MISSING": str(p)}
    out["e4"] = {
        "zkredential": {"source": "results/raw/feasibility-v2/zkredential-e4-20261103T183338Z-51083/observation.json",
                        **{k: v for k, v in obs(a.zk_raw / "feasibility-v2/zkredential-e4-20261103T183338Z-51083/observation.json").items()
                           if k in ("callerChosenAmount", "attackerBalanceAfter", "credentialOwnerBalanceAfter", "realVerifierAccepted", "unchangedGatewayCommittedEffect")}},
        "zkdrops": {"source": "results/raw/feasibility-v2/zkdrops-alias-e4-20261103T183918Z-54527/observation.json",
                    **{k: v for k, v in obs(a.zk_raw / "feasibility-v2/zkdrops-alias-e4-20261103T183918Z-54527/observation.json").items()
                       if k in ("redeemerBalanceAfter", "stateEffects", "vulnerableCommit")}},
    }
    t18 = obs(a.legacy_raw / "T18/90_summary.json")
    case = (t18.get("cases") or {}).get("2_candidate_funded_burn_executes", {})
    out["e4"]["payy"] = {"source": "/Users/imranpollob/Coding/bc/BindCheck/results/raw/T18/90_summary.json",
                         "rollup_before": (case.get("pre_tokenBalances") or {}).get("rollup", "MISSING"),
                         "rollup_after": (case.get("post_tokenBalances") or {}).get("rollup", "MISSING")}
    rp = a.zk_raw / "feasibility-v2/racepass-e4-20261103T184530Z-61766"
    steps = [l.split("\t") for l in (rp / "steps.tsv").read_text().splitlines() if l.strip()]
    out["e4_racepass_steps"] = {"source": "results/raw/feasibility-v2/racepass-e4-20261103T184530Z-61766/steps.tsv",
                                "rows": len(steps), "pass": sum(1 for s in steps if s[-1] == "PASS")}
    sl = json.loads((a.zk_raw / "T23/run-20261104T030439Z-3115/racepass--slither.json").read_text())
    out["t23_slither_racepass_stderr_chars"] = {"source": "results/raw/T23/run-20261104T030439Z-3115/racepass--slither.json .coverage.invocations[0].stderr",
                                                "chars": len(sl["coverage"]["invocations"][0]["stderr"])}
    out["e4"]["racepass"] = {"source": str(rp.relative_to(a.zk_raw.parent.parent)) + "/", "files": sorted(p.name for p in rp.iterdir())[:40]}

    # ---- historical d1 lineage ----
    d2 = obs(a.d1 / "results/raw/D2-01-recovery-01/integrated/benchmark-results.json")
    import re as _re
    by_family = Counter(f"{_re.sub(r'[-_].*', '', t['analysis']['path'].split('/')[-1])}:{t['classification']}" for t in (d2.get("targets") or []))
    out["d1_historical"] = {
        "d2_01_by_target_prefix": {"source": "bindcheck-d1-paper/results/raw/D2-01-recovery-01/integrated/benchmark-results.json (targets[].analysis.path prefix WT=WarpToad, PY=Payy)", **dict(by_family)},
        "d2_01_counts": {"source": "bindcheck-d1-paper/results/raw/D2-01-recovery-01/integrated/benchmark-results.json", **(d2.get("counts") or {"MISSING": True})},
        "d1p32_totals": {"source": "bindcheck-d1-paper/results/raw/D1P-32/summary.json",
                         **{k: v for k, v in (obs(a.d1 / "results/raw/D1P-32/summary.json").get("totals") or {}).items() if k.startswith("foundry")}},
        "d1p43_union_vs_full": {"source": "reports/D1P-43.md:127-128", "unjoined_union": "5/7", "full": "7/7", "recomputed": False},
        "d1p41_union_vs_full": {"source": "reports/D1P-41-ablation-preliminary.md:114-115", "unjoined_union": "6/8", "full": "6/8", "recomputed": False},
    }
    gate_a = a.d1 / "results/raw/D2-07-recovery-01/finalization-summary.json"
    out["d1_historical"]["gate_a"] = {"source": "bindcheck-d1-paper/results/raw/D2-07-recovery-01/finalization-summary.json",
                                      "exists": gate_a.is_file()}
    (ROOT / "reports/groundtruth/claims-check.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: (v if k in ("warnings", "census") else "...") for k, v in out.items()}, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
