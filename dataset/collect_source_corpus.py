#!/usr/bin/env python3
"""Build the frozen DEV/EVAL source inventory without analyzing EVAL code.

Raw GitHub responses and README snapshots are written below dataset/raw/ and
ignored. The committed CSV is metadata only: query provenance, pinned HEAD,
fork/blob family, inventory disposition, and a conservative maturity label.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any


GITHUB_API = "https://api.github.com"
GITHUB_GRAPHQL = "https://api.github.com/graphql"
ADDRESS_RE = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
GITHUB_REPO_RE = re.compile(r"https?://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)")
VERIFIER_PATH_RE = re.compile(r"(?:verifier|verification|groth|plonk|honk)", re.I)
HACKATHON_RE = re.compile(r"ethglobal|devfolio|hackathon|student|university", re.I)
AUDIT_RE = re.compile(r"\baudit(?:ed|s)?\b|trail of bits|openzeppelin|veridise|zksecurity|code4rena|sherlock|cantina", re.I)
DEPLOY_RE = re.compile(r"mainnet|deployed|deployment|contract address", re.I)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def request_json(url: str, token: str, *, data: dict[str, Any] | None = None, retries: int = 7) -> tuple[Any, dict[str, str]]:
    encoded = json.dumps(data).encode() if data is not None else None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=encoded)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("User-Agent", "bindcheck-dataset-inventory")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                return json.load(response), {key.lower(): value for key, value in response.headers.items()}
        except urllib.error.HTTPError as exc:
            reset = int(exc.headers.get("X-RateLimit-Reset", "0") or 0)
            if exc.code in (403, 429) and reset:
                delay = max(1, reset - int(time.time()) + 2)
                print(f"rate-limit wait {delay}s for {url}", flush=True)
                time.sleep(min(delay, 60))
                continue
            if exc.code >= 500 and attempt + 1 < retries:
                time.sleep(min(2 ** attempt, 30))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt + 1 == retries:
                raise
            time.sleep(min(2 ** attempt, 30))
    raise RuntimeError("unreachable")


def fetch_bytes(url: str, retries: int = 4) -> bytes | None:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "bindcheck-dataset-inventory"})
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(min(2 ** attempt, 10))
    return None


def token_from_gh() -> str:
    completed = subprocess.run(["gh", "auth", "token"], text=True, capture_output=True, check=True)
    return completed.stdout.strip()


def search_pages(config: dict[str, Any], token: str, raw: pathlib.Path) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, str]]]]:
    candidates: dict[str, dict[str, Any]] = {}
    evidence: dict[str, list[dict[str, str]]] = defaultdict(list)

    def add(repo: str, query_id: str, role: str, path: str = "", blob_sha: str = "", metadata: dict[str, Any] | None = None, *, allow_new: bool = True) -> None:
        repo = repo.removeprefix("github.com/").rstrip("/")
        if repo.count("/") != 1:
            return
        if repo.lower() not in candidates and not allow_new:
            return
        record = candidates.setdefault(repo.lower(), {"repository": repo, "metadata": {}, "sources": set()})
        if metadata:
            record["metadata"].update(metadata)
        record["sources"].add(query_id)
        evidence[repo.lower()].append({"query": query_id, "role": role, "path": path, "blob_sha": blob_sha})

    for query in config["github_code_queries"]:
        for page in range(1, int(query["pages"]) + 1):
            params = urllib.parse.urlencode({"q": query["q"], "per_page": 100, "page": page})
            target = raw / f"code-{query['id']}-p{page:02d}.json"
            if target.exists():
                payload = json.loads(target.read_text())
            else:
                payload, _ = request_json(f"{GITHUB_API}/search/code?{params}", token)
                target.write_text(json.dumps(payload, sort_keys=True) + "\n")
            items = payload.get("items", [])
            for item in items:
                repo = item["repository"]
                add(
                    repo["full_name"], query["id"], query["role"], item.get("path", ""), item.get("sha", ""), repo,
                    allow_new=query["role"] == "circuit",
                )
            print(f"code {query['id']} page {page}: {len(items)} items; candidates={len(candidates)}", flush=True)
            if len(items) < 100:
                break

    for query in config["github_repository_queries"]:
        for page in range(1, int(query["pages"]) + 1):
            params = urllib.parse.urlencode({"q": query["q"], "per_page": 100, "page": page})
            target = raw / f"repo-{query['id']}-p{page:02d}.json"
            if target.exists():
                payload = json.loads(target.read_text())
            else:
                payload, _ = request_json(f"{GITHUB_API}/search/repositories?{params}", token)
                target.write_text(json.dumps(payload, sort_keys=True) + "\n")
            items = payload.get("items", [])
            for repo in items:
                add(repo["full_name"], query["id"], "discovery", metadata=repo)
            print(f"repo {query['id']} page {page}: {len(items)} items; candidates={len(candidates)}", flush=True)
            if len(items) < 100:
                break

    for source in config["awesome_lists"]:
        body = fetch_bytes(source["url"])
        target = raw / f"list-{source['id']}.md"
        if body is None:
            (raw / f"list-{source['id']}.unavailable").write_text(source["url"] + "\n")
            continue
        target.write_bytes(body)
        for repo in GITHUB_REPO_RE.findall(body.decode(errors="replace")):
            add(repo.removesuffix(".git"), source["id"], "discovery")
        print(f"list {source['id']}: candidates={len(candidates)}", flush=True)
    return candidates, evidence


def graphql_metadata(repositories: list[str], token: str, raw: pathlib.Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for offset in range(0, len(repositories), 35):
        batch = repositories[offset:offset + 35]
        fragments = []
        for index, full_name in enumerate(batch):
            owner, name = full_name.split("/", 1)
            fragments.append(
                f'r{index}: repository(owner:{json.dumps(owner)}, name:{json.dumps(name)}) {{ '
                "nameWithOwner url description isFork isArchived stargazerCount pushedAt "
                "parent { nameWithOwner parent { nameWithOwner parent { nameWithOwner } } } "
                "defaultBranchRef { name target { ... on Commit { oid committedDate } } } "
                "repositoryTopics(first:20) { nodes { topic { name } } } }"
            )
        query = "query { " + " ".join(fragments) + " }"
        payload, _ = request_json(GITHUB_GRAPHQL, token, data={"query": query})
        (raw / f"graphql-{offset // 35:03d}.json").write_text(json.dumps(payload, sort_keys=True) + "\n")
        data = payload.get("data", {})
        for index, requested in enumerate(batch):
            value = data.get(f"r{index}")
            if value:
                records[requested.lower()] = value
        print(f"metadata {min(offset + len(batch), len(repositories))}/{len(repositories)}", flush=True)
    return records


def fetch_readme(repo: str, commit: str, raw_readmes: pathlib.Path) -> tuple[str, str, str]:
    safe = repo.replace("/", "__")
    for filename in ("README.md", "readme.md", "Readme.md", "README"):
        url = f"https://raw.githubusercontent.com/{repo}/{commit}/{filename}"
        body = fetch_bytes(url)
        if body is None:
            continue
        (raw_readmes / f"{safe}.md").write_bytes(body)
        return body.decode(errors="replace"), filename, sha256_bytes(body)
    return "", "", ""


def maturity(metadata: dict[str, Any], readme: str, sources: set[str]) -> tuple[str, str]:
    topics = " ".join(node["topic"]["name"] for node in metadata.get("repositoryTopics", {}).get("nodes", []))
    description = metadata.get("description") or ""
    text = " ".join((topics, description, readme[:300_000]))
    addresses = sorted({address.lower() for address in ADDRESS_RE.findall(readme) if int(address, 16) != 0})
    if addresses and DEPLOY_RE.search(text):
        return "deployed-address-in-docs", f"README/deployment language with {len(addresses)} nonzero address(es); first={addresses[0]}"
    if AUDIT_RE.search(text) and re.search(r"production|mainnet|protocol|audit", text, re.I):
        return "audited-production", "audit and production/protocol language in repository metadata or README"
    if HACKATHON_RE.search(text) or any(key in sources for key in ("ethglobal-circom", "devfolio-circom", "repo-ethglobal-circom", "repo-ethglobal-noir", "repo-devfolio-circom")):
        return "hackathon-student", "hackathon/student provenance in query, metadata, or README"
    return "unclassified", "no maturity indicator found by the recorded metadata heuristic"


def fork_root(value: dict[str, Any]) -> str:
    current = value.get("parent")
    root = ""
    while current:
        root = current.get("nameWithOwner") or root
        current = current.get("parent")
    return root


def inventory_flags(items: list[dict[str, str]]) -> tuple[bool, bool, list[str], list[str], list[str]]:
    circuit_paths = sorted({item["path"] for item in items if item["role"] == "circuit" and item["path"]})
    verifier_items = [item for item in items if item["role"] == "verifier"]
    consumer_items = [item for item in items if item["role"] == "consumer"]
    verifier_paths = {item["path"] for item in verifier_items if item["path"]}
    consumer_paths: set[str] = set()
    for item in consumer_items:
        path = item["path"]
        if VERIFIER_PATH_RE.search(path):
            verifier_paths.add(path)
        elif path:
            consumer_paths.add(path)
    return bool(verifier_paths), bool(consumer_paths), circuit_paths, sorted(verifier_paths), sorted(consumer_paths)


def load_dev(root: pathlib.Path, config: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with (root / "feasibility/candidate-set.csv").open(newline="", encoding="utf-8") as handle:
        for item in csv.DictReader(handle):
            has_verifier = bool(item.get("verifier"))
            has_consumer = bool(item.get("consumer"))
            disposition = "in-scope" if has_verifier and has_consumer else "no consumer" if has_verifier else "no verifier"
            rows.append({
                "repository": item["repository"], "commit": item["commit"], "split": "DEV",
                "variant": "feasibility-50", "disposition": disposition,
                "predup_disposition": disposition, "disposition_basis": "preserved feasibility/candidate-set.csv inventory",
                "query_provenance": "existing-feasibility-50", "circuit_paths": item.get("circuit", ""),
                "verifier_paths": item.get("verifier", ""), "consumer_paths": item.get("consumer", ""),
            })
    for item in config["historical_dev"]:
        rows.append({
            "repository": item["repository"], "commit": item["commit"], "split": "DEV",
            "variant": item["variant"], "disposition": "in-scope", "predup_disposition": "in-scope",
            "disposition_basis": f"public historical vulnerable/fixed source pair: {item['source']}",
            "query_provenance": "historical-dev", "circuit_paths": "", "verifier_paths": "", "consumer_paths": "",
        })
    return rows


def main() -> int:
    here = pathlib.Path(__file__).resolve().parent
    root = here.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=pathlib.Path, default=here / "source-queries.json")
    parser.add_argument("--output", type=pathlib.Path, default=here / "source-corpus.csv")
    parser.add_argument("--summary", type=pathlib.Path, default=here / "source-corpus-summary.json")
    args = parser.parse_args()

    config = json.loads(args.config.read_text())
    raw = here / "raw" / config["snapshot_id"]
    raw_readmes = raw / "readmes"
    raw_readmes.mkdir(parents=True, exist_ok=True)
    token = token_from_gh()
    candidates, evidence = search_pages(config, token, raw)
    names = sorted(record["repository"] for record in candidates.values())
    metadata = graphql_metadata(names, token, raw)

    readmes: dict[str, tuple[str, str, str]] = {}
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {}
        for name in names:
            info = metadata.get(name.lower())
            branch = info.get("defaultBranchRef") if info else None
            target = branch.get("target") if branch else None
            commit = target.get("oid", "") if target else ""
            if commit:
                futures[pool.submit(fetch_readme, name, commit, raw_readmes)] = name
        for future in as_completed(futures):
            name = futures[future]
            readmes[name.lower()] = future.result()

    blob_repos: dict[str, set[str]] = defaultdict(set)
    for key, items in evidence.items():
        for item in items:
            if item["role"] == "circuit" and item["blob_sha"]:
                blob_repos[item["blob_sha"]].add(key)
    shared_blob: dict[str, str] = {}
    for blob, repos in blob_repos.items():
        if len(repos) > 1:
            for repo in repos:
                shared_blob.setdefault(repo, blob)

    eval_rows: list[dict[str, str]] = []
    for key in sorted(candidates):
        candidate = candidates[key]
        info = metadata.get(key)
        if not info or not info.get("defaultBranchRef") or not info["defaultBranchRef"].get("target"):
            eval_rows.append({
                "repository": candidate["repository"], "commit": "", "split": "EVAL", "variant": "inventory",
                "disposition": "unavailable", "predup_disposition": "unavailable",
                "disposition_basis": "GitHub GraphQL repository/default-branch metadata unavailable",
                "query_provenance": "|".join(sorted(candidate["sources"])), "circuit_paths": "",
                "verifier_paths": "", "consumer_paths": "", "family_id": f"unavailable:{key}",
                "family_basis": "metadata unavailable", "maturity": "unclassified", "maturity_basis": "metadata unavailable",
                "is_fork": "", "fork_root": "", "stars": "", "archived": "", "pushed_at": "",
                "readme_path": "", "readme_sha256": "",
            })
            continue
        target = info["defaultBranchRef"]["target"]
        commit = target["oid"]
        has_verifier, has_consumer, circuits, verifiers, consumers = inventory_flags(evidence[key])
        predup = "in-scope" if circuits and has_verifier and has_consumer else "no consumer" if circuits and has_verifier else "no verifier"
        root_fork = fork_root(info)
        if root_fork:
            family_id, family_basis = f"fork:{root_fork.lower()}", "GitHub fork ancestry (up to three parent levels)"
        elif key in shared_blob:
            family_id, family_basis = f"blob:{shared_blob[key]}", "identical circuit blob SHA appears in multiple repositories"
        else:
            family_id, family_basis = f"repo:{key}", "no fork or shared-circuit-blob family found"
        readme, readme_path, readme_hash = readmes.get(key, ("", "", ""))
        maturity_label, maturity_basis = maturity(info, readme, candidate["sources"])
        eval_rows.append({
            "repository": info["nameWithOwner"], "commit": commit, "split": "EVAL", "variant": "inventory",
            "disposition": predup, "predup_disposition": predup, "disposition_basis": "query/path inventory only; EVAL analyzer not run",
            "query_provenance": "|".join(sorted(candidate["sources"])),
            "circuit_paths": "|".join(circuits[:25]), "verifier_paths": "|".join(verifiers[:25]),
            "consumer_paths": "|".join(consumers[:25]), "family_id": family_id, "family_basis": family_basis,
            "maturity": maturity_label, "maturity_basis": maturity_basis, "is_fork": str(bool(info.get("isFork"))).lower(),
            "fork_root": root_fork, "stars": str(info.get("stargazerCount", "")), "archived": str(bool(info.get("isArchived"))).lower(),
            "pushed_at": info.get("pushedAt") or "", "readme_path": readme_path, "readme_sha256": readme_hash,
        })

    dev_rows = load_dev(root, config)
    dev_repositories = {row["repository"].lower() for row in dev_rows}
    eval_rows = [row for row in eval_rows if row["repository"].lower() not in dev_repositories]

    family_members: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in eval_rows:
        family_members[row["family_id"]].append(row)
    for family, members in family_members.items():
        if not (family.startswith("fork:") or family.startswith("blob:")) or len(members) < 2:
            continue
        canonical = sorted(members, key=lambda row: (-int(row.get("stars") or 0), row["repository"].lower()))[0]
        for row in members:
            if row is canonical:
                continue
            row["disposition"] = "dup"
            row["disposition_basis"] = f"duplicate family; canonical inventory row is {canonical['repository']}"

    all_rows: list[dict[str, str]] = []
    for row in dev_rows:
        key = row["repository"].lower()
        info = metadata.get(key, {})
        root_fork = fork_root(info) if info else ""
        row.update({
            "family_id": f"fork:{root_fork.lower()}" if root_fork else f"repo:{key}",
            "family_basis": "GitHub fork ancestry" if root_fork else "DEV repository identity",
            "maturity": "unclassified", "maturity_basis": "DEV maturity not re-inferred from EVAL inventory queries",
            "is_fork": str(bool(info.get("isFork"))).lower() if info else "", "fork_root": root_fork,
            "stars": str(info.get("stargazerCount", "")) if info else "", "archived": str(bool(info.get("isArchived"))).lower() if info else "",
            "pushed_at": info.get("pushedAt") or "" if info else "", "readme_path": "", "readme_sha256": "",
        })
        all_rows.append(row)
    all_rows.extend(eval_rows)

    fields = [
        "repository", "commit", "split", "variant", "disposition", "predup_disposition", "disposition_basis",
        "query_provenance", "circuit_paths", "verifier_paths", "consumer_paths", "family_id", "family_basis",
        "maturity", "maturity_basis", "is_fork", "fork_root", "stars", "archived", "pushed_at",
        "readme_path", "readme_sha256",
    ]
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(all_rows)

    def counts(field: str, rows: list[dict[str, str]]) -> dict[str, int]:
        values: dict[str, int] = defaultdict(int)
        for row in rows:
            values[row[field]] += 1
        return dict(sorted(values.items()))

    summary = {
        "schema_version": 1,
        "snapshot_id": config["snapshot_id"],
        "generated_utc": dt.datetime.now(dt.UTC).isoformat(),
        "query_config_sha256": sha256_bytes(args.config.read_bytes()),
        "rows": len(all_rows),
        "unique_repositories": len({row["repository"].lower() for row in all_rows}),
        "split_counts": counts("split", all_rows),
        "eval_disposition_counts": counts("disposition", eval_rows),
        "eval_maturity_counts": counts("maturity", eval_rows),
        "families": len({row["family_id"] for row in all_rows}),
        "eval_families": len({row["family_id"] for row in eval_rows}),
        "eval_analyzer_runs": 0,
        "scope": "inventory and metadata only for EVAL; no BindCheck/static vulnerability checks run on EVAL",
        "raw_directory": str(raw.relative_to(root)),
    }
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (raw / "manifest.json").write_text(json.dumps({
        **summary,
        "output_sha256": sha256_bytes(args.output.read_bytes()),
        "raw_files": sorted(path.relative_to(raw).as_posix() for path in raw.rglob("*") if path.is_file()),
    }, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
