#!/usr/bin/env python3
"""Assemble the append-only v2 source ledger and family dispositions."""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import pathlib
from collections import defaultdict
from typing import Any


HERE = pathlib.Path(__file__).resolve().parent
V1 = HERE / "source-corpus.csv"
INVENTORY = HERE / "github-source-inventory-v2.csv"
SOURCIFY_MATCHES = HERE / "sourcify-github-matches-v2.csv"
OUTPUT = HERE / "source-corpus-v2.csv"
SUMMARY = HERE / "source-corpus-v2-summary.json"
SAMPLE_PLAN = HERE / "EVAL-SAMPLE-PLAN-v2.md"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class UnionFind:
    def __init__(self, size: int):
        self.parent = list(range(size))

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        left, right = self.find(left), self.find(right)
        if left != right:
            self.parent[right] = left


def main() -> int:
    v1 = rows(V1)
    inventory = rows(INVENTORY)
    match_rows = rows(SOURCIFY_MATCHES) if SOURCIFY_MATCHES.exists() else []
    original_fields = list(v1[0])
    inventory_by_key = {(row["repository"].lower(), row["commit"]): row for row in inventory}
    v1_repositories = {row["repository"].lower() for row in v1}
    matches_by_repo: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in match_rows:
        matches_by_repo[row["repository"].lower()].append(row)

    assembled: list[dict[str, str]] = []

    def enrich(base: dict[str, str], scan: dict[str, str] | None, origin: str) -> dict[str, str]:
        split = base["split"]
        if split == "DEV":
            predup = base["predup_disposition"]
            disposition_basis = "DEV disposition preserved from v1"
            circuit_paths = base["circuit_paths"]
            verifier_paths = base["verifier_paths"]
            consumer_paths = base["consumer_paths"]
            maturity = base["maturity"]
            maturity_basis = base["maturity_basis"]
        elif scan:
            predup = scan["predup_disposition"]
            disposition_basis = scan["disposition_basis"]
            circuit_paths = scan["circuit_paths"]
            verifier_paths = scan["verifier_paths"]
            consumer_paths = scan["consumer_paths"]
            maturity = scan["maturity"]
            maturity_basis = scan["maturity_basis"]
        else:
            predup = "unavailable"
            disposition_basis = "no pinned v2 tree scan available"
            circuit_paths = base["circuit_paths"]
            verifier_paths = base["verifier_paths"]
            consumer_paths = base["consumer_paths"]
            maturity = base["maturity"]
            maturity_basis = base["maturity_basis"]

        exact_matches = []
        source_hashes = set((scan or {}).get("consumer_source_sha256s", "").split("|")) - {""}
        for match in matches_by_repo.get(base["repository"].lower(), []):
            if match["source_sha256"] in source_hashes:
                exact_matches.append(match)
        if exact_matches:
            maturity = "verified-deployed"
            examples = sorted({f"chain={row['chain_id']} address={row['address']} source_sha256={row['source_sha256']}" for row in exact_matches})
            maturity_basis = "exact GitHub/Sourcify consumer-source SHA-256 with runtime and runtime-metadata match; " + "; ".join(examples[:3])

        value = dict(base)
        value.update({
            "v2_disposition": predup,
            "v2_predup_disposition": predup,
            "v2_disposition_basis": disposition_basis,
            "v2_row_origin": origin,
            "v2_query_provenance": (scan or {}).get("query_provenance", ""),
            "v2_circuit_paths": circuit_paths,
            "v2_verifier_paths": verifier_paths,
            "v2_consumer_paths": consumer_paths,
            "v2_consumer_evidence": (scan or {}).get("consumer_evidence", ""),
            "v2_consumer_source_sha256s": (scan or {}).get("consumer_source_sha256s", ""),
            "v2_scan_status": (scan or {}).get("scan_status", "not-rescanned" if split == "DEV" else "unavailable"),
            "v2_tree_cache_sha256": (scan or {}).get("tree_cache_sha256", ""),
            "v2_circuit_fingerprint": (scan or {}).get("circuit_fingerprint", ""),
            "v2_fork_root": (scan or {}).get("fork_root", base.get("fork_root", "")),
            "v2_family_id": "",
            "v2_family_basis": "",
            "v2_family_canonical_repository": "",
            "v2_maturity": maturity,
            "v2_maturity_basis": maturity_basis,
            "v2_sourcify_match_count": str(len(exact_matches)),
            "v2_sourcify_evidence": "|".join(sorted({f"{row['chain_id']}:{row['address']}:{row['source_sha256']}" for row in exact_matches})),
        })
        return value

    for row in v1:
        scan = inventory_by_key.get((row["repository"].lower(), row["commit"]))
        assembled.append(enrich(row, scan, "v1-preserved"))

    for scan in inventory:
        if "v2-consumer-first" not in scan["origins"].split("|"):
            continue
        if scan["repository"].lower() in v1_repositories and any(row["commit"] == scan["commit"] for row in v1 if row["repository"].lower() == scan["repository"].lower()):
            continue
        base = {field: "" for field in original_fields}
        base.update({
            "repository": scan["repository"], "commit": scan["commit"], "split": "EVAL", "variant": "inventory-v2",
            "disposition": "not-in-v1", "predup_disposition": "not-in-v1", "disposition_basis": "new v2 consumer-first row",
            "query_provenance": scan["query_provenance"], "circuit_paths": scan["circuit_paths"], "verifier_paths": scan["verifier_paths"],
            "consumer_paths": scan["consumer_paths"], "maturity": scan["maturity"], "maturity_basis": scan["maturity_basis"],
            "is_fork": scan["is_fork"], "fork_root": scan["fork_root"], "stars": scan["stars"], "archived": scan["archived"],
            "pushed_at": scan["pushed_at"], "readme_path": scan["readme_path"], "readme_sha256": scan["readme_sha256"],
        })
        assembled.append(enrich(base, scan, "v2-consumer-first"))

    # Recompute family components over all rows.  Exact repository identity,
    # GitHub fork root, exact first-party circuit inventory fingerprint, and
    # preserved v1 family evidence are the only merge rules.
    union = UnionFind(len(assembled))
    indexes: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, row in enumerate(assembled):
        values = {
            ("repository", row["repository"].lower()),
            ("fork", row["v2_fork_root"].lower()),
            ("circuit-fingerprint", row["v2_circuit_fingerprint"]),
            ("v1-family", row["family_id"]),
        }
        for kind, value in values:
            if value:
                indexes[(kind, value)].append(index)
    family_reasons: dict[tuple[int, int], set[str]] = defaultdict(set)
    for (kind, _), members in indexes.items():
        first = members[0]
        for member in members[1:]:
            union.union(first, member)
            family_reasons[(min(first, member), max(first, member))].add(kind)
    components: dict[int, list[int]] = defaultdict(list)
    for index in range(len(assembled)):
        components[union.find(index)].append(index)

    maturity_rank = {"verified-deployed": 0, "deployed-address-in-docs": 1, "audited-production": 2, "hackathon-student": 3, "unclassified": 4}
    for members in components.values():
        identities = sorted(f"{assembled[index]['repository'].lower()}@{assembled[index]['commit']}" for index in members)
        family_id = "v2-family:" + hashlib.sha256("\n".join(identities).encode()).hexdigest()[:20]
        bases = set()
        for kind in ("repository", "fork", "circuit-fingerprint", "v1-family"):
            values = defaultdict(int)
            for index in members:
                row = assembled[index]
                value = {"repository": row["repository"].lower(), "fork": row["v2_fork_root"].lower(), "circuit-fingerprint": row["v2_circuit_fingerprint"], "v1-family": row["family_id"]}[kind]
                if value:
                    values[value] += 1
            if any(count > 1 for count in values.values()):
                bases.add(kind)
        canonical = min(members, key=lambda index: (
            assembled[index]["split"] != "DEV",
            assembled[index]["v2_predup_disposition"] != "in-scope",
            maturity_rank.get(assembled[index]["v2_maturity"], 9),
            -int(assembled[index].get("stars") or 0),
            assembled[index]["repository"].lower(),
            assembled[index]["commit"],
        ))
        canonical_name = assembled[canonical]["repository"]
        for index in members:
            row = assembled[index]
            row["v2_family_id"] = family_id
            row["v2_family_basis"] = "+".join(sorted(bases)) if bases else "repository revision singleton"
            row["v2_family_canonical_repository"] = canonical_name
            if index != canonical and len(members) > 1:
                row["v2_disposition"] = "dup"
                row["v2_disposition_basis"] = f"duplicate v2 family; canonical row is {canonical_name}; predup={row['v2_predup_disposition']}"

    new_fields = [
        "v2_disposition", "v2_predup_disposition", "v2_disposition_basis", "v2_row_origin", "v2_query_provenance",
        "v2_circuit_paths", "v2_verifier_paths", "v2_consumer_paths", "v2_consumer_evidence", "v2_consumer_source_sha256s",
        "v2_scan_status", "v2_tree_cache_sha256", "v2_circuit_fingerprint", "v2_fork_root", "v2_family_id", "v2_family_basis",
        "v2_family_canonical_repository", "v2_maturity", "v2_maturity_basis", "v2_sourcify_match_count", "v2_sourcify_evidence",
    ]
    fields = original_fields[:5] + new_fields[:3] + original_fields[5:] + new_fields[3:]
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(assembled)

    # Mechanical append-only check: projection of the first v1 rows onto the
    # original schema must equal the original dictionaries exactly.
    for index, original in enumerate(v1):
        assert {field: assembled[index][field] for field in original_fields} == original
    assert all(row["split"] == "EVAL" for row in assembled[len(v1):])

    def counts(field: str, selected: list[dict[str, str]]) -> dict[str, int]:
        result: dict[str, int] = defaultdict(int)
        for row in selected:
            result[row[field]] += 1
        return dict(sorted(result.items()))

    eval_rows = [row for row in assembled if row["split"] == "EVAL"]
    eval_in_scope = [row for row in eval_rows if row["v2_predup_disposition"] == "in-scope"]
    family_splits: dict[str, set[str]] = defaultdict(set)
    family_maturity: dict[str, set[str]] = defaultdict(set)
    for row in assembled:
        family_splits[row["v2_family_id"]].add(row["split"])
        if row["v2_predup_disposition"] == "in-scope":
            family_maturity[row["v2_family_id"]].add(row["v2_maturity"])
    in_scope_families = {row["v2_family_id"] for row in eval_in_scope}
    eval_only_in_scope_families = {family for family in in_scope_families if family_splits[family] == {"EVAL"}}
    maturity_family_counts: dict[str, int] = defaultdict(int)
    for family in eval_only_in_scope_families:
        labels = family_maturity[family]
        selected = min(labels, key=lambda label: maturity_rank.get(label, 9))
        maturity_family_counts[selected] += 1

    summary: dict[str, Any] = {
        "schema_version": 2,
        "generated_utc": dt.datetime.now(dt.UTC).isoformat(),
        "rows": len(assembled),
        "v1_rows_preserved": len(v1),
        "new_eval_rows": len(assembled) - len(v1),
        "split_counts": counts("split", assembled),
        "eval_v2_disposition_counts": counts("v2_disposition", eval_rows),
        "eval_v2_predup_disposition_counts": counts("v2_predup_disposition", eval_rows),
        "families": len(components),
        "eval_in_scope_families_including_dev_overlap": len(in_scope_families),
        "eval_only_in_scope_families": len(eval_only_in_scope_families),
        "eval_only_in_scope_family_maturity": dict(sorted(maturity_family_counts.items())),
        "verified_deployed_rows": sum(row["v2_maturity"] == "verified-deployed" for row in assembled),
        "eval_analyzer_runs": 0,
        "v1_ledger_sha256": sha256(V1),
        "github_inventory_sha256": sha256(INVENTORY),
        "sourcify_matches_sha256": sha256(SOURCIFY_MATCHES) if SOURCIFY_MATCHES.exists() else "",
        "output_sha256": sha256(OUTPUT),
        "append_only_projection_check": "PASS",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    if len(eval_only_in_scope_families) > 300:
        plan = f"""# Preregistered EVAL family sample plan v2

Date frozen: {dt.date.today().isoformat()}  
Controlling source-ledger SHA-256: `{summary['output_sha256']}`  
Status: inventory-only preregistration; zero EVAL analyzer runs

The eligible population is the {len(eval_only_in_scope_families)} v2 in-scope EVAL-only
families. Families overlapping DEV are excluded. Sampling occurs only after human
review of path/regex eligibility, family membership, and maturity labels.

Strata use the strongest family maturity in this order: `verified-deployed`,
`deployed-address-in-docs`, `audited-production`, `hackathon-student`, and
`unclassified`. Select up to 60 families per stratum, or the whole stratum when
it has fewer than 60. Within a stratum, sort ascending by
`SHA256("bindcheck-eval-v2-family-sample-2026-11-03|" + v2_family_id)` and take
the first quota. This deterministic rule was frozen before any EVAL analysis.

Inventory counts at freeze: `{json.dumps(dict(sorted(maturity_family_counts.items())), sort_keys=True)}`.
No family may move between DEV and EVAL after results are observed. Label or family
corrections made during human review require a new ledger hash and a documented
pre-analysis sample refresh; corrections after analysis are post-hoc and cannot
retain preregistered status.
"""
        SAMPLE_PLAN.write_text(plan)
    elif SAMPLE_PLAN.exists():
        raise RuntimeError("stale sample plan exists although threshold is not exceeded")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
