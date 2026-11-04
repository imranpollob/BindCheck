#!/usr/bin/env python3
"""Record deployment-reference dispositions for the 16 DEV P4 source leads.

This is deliberately a source-reference locator, not a correspondence claim.
An address in repository documentation remains a candidate until its deployed
runtime is shown to match the flagged source artifact.
"""

from __future__ import annotations

import csv
import json
import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[1]
P4 = ROOT / "feasibility" / "v2" / "p4-census.json"
REPOS = ROOT / "feasibility" / "work" / "v2" / "repos"
OUT = ROOT / "dataset"
ADDRESS = re.compile(r"0x[a-fA-F0-9]{40}")


# Fixed, reviewable evidence locations.  They are intentionally narrower than
# a repository-wide address scrape, which would mostly collect test vectors,
# tokens, deployers, and unrelated projects from the ETHShanghai monorepo.
EVIDENCE = {
    "0xFableOrg/0xFable": [],
    "RippnerLabs/meridian-link": ["config/sepolia_address_book.json"],
    "SovereignWave/qwer": [],
    "avitenzer/zk_voting": [],
    "ethpanda-org/ETHShanghai-2025": [],
    "metacraft-labs/DendrETH": ["README.md"],
    "zk-poll/zk-poll": ["README.md"],
    "zkp2p/zk-p2p": [],
}


def line_for(text, address):
    return text[:text.index(address)].count("\n") + 1


def main():
    source = json.loads(P4.read_text())
    leads = [record for record in source["records"] if
             record.get("gamma_equals_delta") or record.get("delta_is_default_bn254_g2")]
    if len(leads) != 16:
        raise SystemExit(f"expected 16 source leads, found {len(leads)}")
    rows = []
    for lead in leads:
        repository = lead["repository"]
        repo = REPOS / repository.replace("/", "__", 1)
        references = []
        for relative in EVIDENCE.get(repository, []):
            path = repo / relative
            text = path.read_text(errors="replace")
            for address in sorted(set(ADDRESS.findall(text)), key=str.lower):
                # Meridian's key is an explicit verifier address.  Other
                # README addresses are consuming/application contracts only.
                if repository == "RippnerLabs/meridian-link":
                    prefix = text[max(0, text.index(address) - 80):text.index(address)].lower()
                    if "verifiersmartcontractaddress" not in prefix:
                        continue
                    relation = "explicit-verifier-address-key"
                    network = "sepolia-11155111"
                elif repository == "zk-poll/zk-poll":
                    if address.lower() != "0x426bf8b7c4f5cb67eb838ce2585116598ce3019a":
                        continue
                    relation = "consumer-address-in-readme"
                    network = "goerli-5"
                else:
                    # DendrETH's deployment table is useful location evidence,
                    # but none of its entries establish which verifier runtime
                    # was embedded or referenced.
                    relation = "consumer-address-in-deployment-table"
                    network = "documented-network-see-evidence"
                references.append({"address": address.lower(), "network": network,
                                   "relation": relation, "evidence": f"{relative}:{line_for(text, address)}"})
        if references:
            disposition = "candidate deployment reference; runtime/source correspondence UNKNOWN"
        else:
            disposition = "unavailable; no verifier/consumer deployment reference in fixed evidence paths"
        rows.append({
            "repository": repository, "commit": lead["commit"], "source_path": lead["path"],
            "source_sha256": lead["sha256"], "source_warning": "|".join(lead["warnings"]),
            "deployment_disposition": disposition,
            "candidate_addresses": "|".join(item["address"] for item in references),
            "candidate_networks": "|".join(item["network"] for item in references),
            "reference_relations": "|".join(item["relation"] for item in references),
            "evidence_locations": "|".join(item["evidence"] for item in references),
            "correspondence": "UNKNOWN", "verdict": "UNKNOWN",
        })
    with (OUT / "p4-source-lead-deployments.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    summary = {
        "schema_version": 1, "source_leads": len(rows),
        "unique_repositories": len({row['repository'] for row in rows}),
        "leads_with_candidate_reference": sum(bool(row["candidate_addresses"]) for row in rows),
        "candidate_addresses": len({address for row in rows for address in row["candidate_addresses"].split("|") if address}),
        "source_correspondence_confirmed": 0, "live_funded_vulnerable_instances": 0,
        "safety_stop_triggered": False,
        "sovereignwave": next(row for row in rows if row["repository"] == "SovereignWave/qwer"),
    }
    (OUT / "p4-source-lead-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
