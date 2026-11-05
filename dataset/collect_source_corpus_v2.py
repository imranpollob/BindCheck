#!/usr/bin/env python3
"""Collect the v2 GitHub source inventory without running a security analyzer.

Eligibility is deliberately syntactic: a pinned repository tree must contain a
first-party circuit path and a Solidity file must match a frozen verifier-call
regex.  The script records paths, hashes, regex identifiers, and line numbers;
it does not infer a bug, policy, effect, or security verdict.
"""

from __future__ import annotations

import argparse
import base64
import csv
import datetime as dt
import gzip
import hashlib
import http.client
import json
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
SCANNER_VERSION = "github-inventory-v2-regex-1"
ADDRESS_RE = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
DEPLOY_RE = re.compile(r"\b(mainnet|deployed|deployment|contract address)\b", re.I)
AUDIT_RE = re.compile(r"\b(audit(?:ed|s)?|zksecurity|veridise|trail of bits|zellic|openzeppelin|code4rena|sherlock|cantina)\b", re.I)
PRODUCTION_RE = re.compile(r"\b(production|mainnet|protocol|live)\b", re.I)
HACKATHON_RE = re.compile(r"\b(ethglobal|devfolio|hackathon|student|university)\b", re.I)
VERIFIER_PATH_RE = re.compile(r"(?:verifier|verification|groth|plonk|ultra|honk)", re.I)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def token_from_gh() -> str:
    result = subprocess.run(["gh", "auth", "token"], text=True, capture_output=True, check=True)
    token = result.stdout.strip()
    if not token:
        raise RuntimeError("gh auth token returned an empty credential")
    return token


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "__", value)


def read_gzip_json(path: pathlib.Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def write_gzip_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True, separators=(",", ":"))
        handle.write("\n")


class GitHub:
    def __init__(self, token: str):
        self.token = token

    def get(self, url: str, cache: pathlib.Path, *, tolerate: tuple[int, ...] = (404, 409, 422)) -> tuple[Any | None, dict[str, str]]:
        if cache.exists():
            wrapper = read_gzip_json(cache)
            return wrapper.get("payload"), wrapper.get("headers", {})
        for attempt in range(8):
            request = urllib.request.Request(url, headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "bindcheck-academic-dataset-v2",
            })
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    payload = json.load(response)
                    headers = {key.lower(): value for key, value in response.headers.items()}
                write_gzip_json(cache, {"url": url, "status": 200, "headers": headers, "payload": payload})
                remaining = int(headers.get("x-ratelimit-remaining", "1") or 1)
                reset = int(headers.get("x-ratelimit-reset", "0") or 0)
                if remaining == 0 and reset:
                    time.sleep(max(1, reset - int(time.time()) + 2))
                return payload, headers
            except urllib.error.HTTPError as exc:
                headers = {key.lower(): value for key, value in exc.headers.items()}
                if exc.code in tolerate:
                    write_gzip_json(cache, {"url": url, "status": exc.code, "headers": headers, "payload": None})
                    return None, headers
                if exc.code in (403, 429):
                    reset = int(headers.get("x-ratelimit-reset", "0") or 0)
                    delay = max(2, reset - int(time.time()) + 2) if reset else min(60, 2 ** attempt)
                    print(f"GitHub rate-limit wait {delay}s", flush=True)
                    time.sleep(delay)
                    continue
                if exc.code >= 500 and attempt + 1 < 8:
                    time.sleep(min(30, 2 ** attempt))
                    continue
                raise
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, http.client.IncompleteRead, json.JSONDecodeError):
                if attempt + 1 == 8:
                    raise
                time.sleep(min(30, 2 ** attempt))
        raise RuntimeError("unreachable")

    def graphql(self, query: str, cache: pathlib.Path) -> Any:
        if cache.exists():
            return read_gzip_json(cache)["payload"]
        body = json.dumps({"query": query}).encode()
        for attempt in range(8):
            request = urllib.request.Request(
                f"{GITHUB_API}/graphql",
                data=body,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {self.token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "Content-Type": "application/json",
                    "User-Agent": "bindcheck-academic-dataset-v2",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    payload = json.load(response)
                    headers = {key.lower(): value for key, value in response.headers.items()}
                if payload.get("errors") and not payload.get("data"):
                    raise RuntimeError(f"GitHub GraphQL errors: {payload['errors']}")
                write_gzip_json(cache, {"url": f"{GITHUB_API}/graphql", "status": 200, "headers": headers, "payload": payload})
                return payload
            except urllib.error.HTTPError as exc:
                if exc.code in (403, 429) or exc.code >= 500:
                    reset = int(exc.headers.get("X-RateLimit-Reset", "0") or 0)
                    delay = max(2, reset - int(time.time()) + 2) if reset else min(60, 2 ** attempt)
                    time.sleep(delay)
                    continue
                raise
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, http.client.IncompleteRead, json.JSONDecodeError):
                if attempt + 1 == 8:
                    raise
                time.sleep(min(30, 2 ** attempt))
        raise RuntimeError("unreachable")


def fetch_raw(url: str, attempts: int = 5) -> bytes | None:
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "bindcheck-academic-dataset-v2"})
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code in (404, 410):
                return None
            if exc.code not in (429, 500, 502, 503, 504):
                return None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, http.client.IncompleteRead):
            pass
        time.sleep(min(20, 2 ** attempt))
    return None


def strip_comments(text: str) -> str:
    def replace_block(match: re.Match[str]) -> str:
        value = match.group(0)
        return "".join("\n" if char == "\n" else " " for char in value)

    text = re.sub(r"/\*.*?\*/", replace_block, text, flags=re.S)
    return re.sub(r"//[^\n]*", lambda match: " " * len(match.group(0)), text)


def consumer_matches(text: str, rules: list[dict[str, str]]) -> list[dict[str, Any]]:
    clean = strip_comments(text)
    found: list[dict[str, Any]] = []
    for rule in rules:
        expression = re.compile(rule["regex"])
        line_exclude = re.compile(rule["line_exclude_regex"]) if rule.get("line_exclude_regex") else None
        for match in expression.finditer(clean):
            line = clean.count("\n", 0, match.start()) + 1
            line_text = clean.splitlines()[line - 1] if clean.splitlines() else ""
            if line_exclude and line_exclude.search(line_text):
                continue
            found.append({"rule": rule["id"], "line": line, "match": re.sub(r"\s+", " ", match.group(0))[:160]})
    unique = {(item["rule"], item["line"], item["match"]): item for item in found}
    return [unique[key] for key in sorted(unique)]


def excerpt(text: str, match: re.Match[str] | None, width: int = 180) -> str:
    if not match:
        return ""
    start = max(0, match.start() - width // 2)
    end = min(len(text), match.end() + width // 2)
    return re.sub(r"\s+", " ", text[start:end]).strip()[:width]


def maturity(metadata: dict[str, Any], readme: str, provenance: list[str]) -> tuple[str, str]:
    topics = " ".join(item if isinstance(item, str) else item.get("name", "") for item in metadata.get("topics", []))
    description = metadata.get("description") or ""
    text = "\n".join((description, topics, readme[:500_000], " ".join(provenance)))
    addresses = sorted({value.lower() for value in ADDRESS_RE.findall(readme) if int(value, 16)})
    deploy = DEPLOY_RE.search(text)
    if addresses and deploy:
        return "deployed-address-in-docs", f"nonzero_address={addresses[0]}; deployment_excerpt={excerpt(text, deploy)}"
    audit = AUDIT_RE.search(text)
    production = PRODUCTION_RE.search(text)
    if audit and production:
        return "audited-production", f"audit_term={audit.group(0)}; production_term={production.group(0)}; audit_excerpt={excerpt(text, audit)}"
    hackathon = HACKATHON_RE.search(text)
    if hackathon:
        return "hackathon-student", f"term={hackathon.group(0)}; excerpt={excerpt(text, hackathon)}"
    return "unclassified", "no recorded maturity regex matched repository metadata or README"


def raw_url(repo: str, commit: str, path: str) -> str:
    owner, name = repo.split("/", 1)
    quoted = urllib.parse.quote(path, safe="/")
    return f"https://raw.githubusercontent.com/{owner}/{name}/{commit}/{quoted}"


def scan_repository(
    repo: str,
    commit: str,
    metadata: dict[str, Any],
    provenance: list[str],
    search_paths: set[str],
    github: GitHub,
    raw: pathlib.Path,
    config: dict[str, Any],
    config_sha: str,
) -> dict[str, Any]:
    key = safe_name(f"{repo}--{commit}")
    record_path = raw / "scans" / f"{key}.json.gz"
    if record_path.exists():
        record = read_gzip_json(record_path)
        if record.get("scanner_version") == SCANNER_VERSION and record.get("config_sha256") == config_sha:
            return record

    tree_cache = raw / "trees" / f"{key}.json.gz"
    tree_url = f"{GITHUB_API}/repos/{repo}/git/trees/{urllib.parse.quote(commit, safe='')}?recursive=1"
    tree, _ = github.get(tree_url, tree_cache)
    base = {
        "scanner_version": SCANNER_VERSION,
        "config_sha256": config_sha,
        "repository": repo,
        "commit": commit,
        "tree_cache_sha256": sha256_bytes(tree_cache.read_bytes()) if tree_cache.exists() else "",
    }
    if not tree or not isinstance(tree.get("tree"), list):
        record = {**base, "scan_status": "tree-unavailable", "tree_truncated": False, "circuit_paths": [], "verifier_paths": [], "consumer_files": [], "solidity_files_considered": 0, "solidity_files_fetched": 0, "solidity_fetch_failures": 0, "circuit_fingerprint": ""}
        write_gzip_json(record_path, record)
        return record

    path_config = config["path_rules"]
    circuit_re = re.compile(path_config["circuit_include_regex"])
    solidity_re = re.compile(path_config["solidity_include_regex"])
    exclude_re = re.compile(path_config["first_party_exclude_regex"])
    maximum_bytes = int(path_config["maximum_solidity_bytes"])
    blobs = [item for item in tree["tree"] if item.get("type") == "blob" and item.get("path")]
    circuits = [item for item in blobs if circuit_re.search(item["path"]) and not exclude_re.search(item["path"])]
    solidity = [item for item in blobs if solidity_re.search(item["path"]) and not exclude_re.search(item["path"]) and int(item.get("size") or 0) <= maximum_bytes]
    # Circuit-bearing repositories receive a complete first-party Solidity
    # inventory.  For consumer-search repositories with no circuit path, only
    # the exact GitHub search-hit paths are fetched; this preserves deployed
    # source matching without downloading unrelated monorepo Solidity trees.
    if not circuits:
        solidity = [item for item in solidity if item["path"] in search_paths]
    solidity.sort(key=lambda item: (item["path"] not in search_paths, item["path"].lower()))
    maximum_files = int(path_config.get("maximum_solidity_files_per_repository", 2000))
    capped = len(solidity) > maximum_files
    solidity = solidity[:maximum_files]

    def inspect(item: dict[str, Any]) -> tuple[dict[str, Any], bytes | None, list[dict[str, Any]]]:
        body = fetch_raw(raw_url(repo, commit, item["path"]))
        if body is None:
            return item, None, []
        matches = consumer_matches(body.decode(errors="replace"), config["consumer_call_rules"])
        return item, body, matches

    consumers: list[dict[str, Any]] = []
    fetched = 0
    failures = 0
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(inspect, item) for item in solidity]
        for future in as_completed(futures):
            item, body, matches = future.result()
            if body is None:
                failures += 1
                continue
            fetched += 1
            if not matches:
                continue
            digest = sha256_bytes(body)
            source_cache = raw / "matched-sources" / f"{digest}.sol.gz"
            if not source_cache.exists():
                source_cache.parent.mkdir(parents=True, exist_ok=True)
                with gzip.open(source_cache, "wb") as handle:
                    handle.write(body)
            consumers.append({"path": item["path"], "blob_sha": item.get("sha", ""), "source_sha256": digest, "bytes": len(body), "matches": matches})

    readme_candidates = sorted((item for item in blobs if re.fullmatch(r"(?i)(?:[^/]+/)?readme(?:\.[a-z0-9]+)?", item["path"])), key=lambda item: (item["path"].count("/"), item["path"].lower()))
    readme_text = ""
    readme_path = ""
    readme_sha = ""
    if readme_candidates:
        readme_path = readme_candidates[0]["path"]
        body = fetch_raw(raw_url(repo, commit, readme_path))
        if body is not None:
            readme_text = body.decode(errors="replace")
            readme_sha = sha256_bytes(body)
            target = raw / "readmes" / f"{key}.md.gz"
            target.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(target, "wb") as handle:
                handle.write(body)
    maturity_label, maturity_basis = maturity(metadata, readme_text, provenance)
    circuit_blob_shas = sorted(item.get("sha", "") for item in circuits if item.get("sha"))
    circuit_fingerprint = sha256_bytes("\n".join(circuit_blob_shas).encode()) if circuit_blob_shas else ""
    status_parts = []
    if bool(tree.get("truncated")):
        status_parts.append("tree-truncated")
    if capped:
        status_parts.append("solidity-cap-reached")
    if failures:
        status_parts.append("source-fetch-failures")
    scan_status = "+".join(status_parts) if status_parts else "complete"
    record = {
        **base,
        "scan_status": scan_status,
        "tree_truncated": bool(tree.get("truncated")),
        "circuit_paths": [{"path": item["path"], "blob_sha": item.get("sha", ""), "bytes": int(item.get("size") or 0)} for item in circuits],
        "verifier_paths": sorted(item["path"] for item in solidity if VERIFIER_PATH_RE.search(item["path"])),
        "consumer_files": sorted(consumers, key=lambda item: item["path"].lower()),
        "solidity_files_considered": len(solidity),
        "solidity_files_fetched": fetched,
        "solidity_fetch_failures": failures,
        "circuit_fingerprint": circuit_fingerprint,
        "readme_path": readme_path,
        "readme_sha256": readme_sha,
        "maturity": maturity_label,
        "maturity_basis": maturity_basis,
    }
    write_gzip_json(record_path, record)
    return record


def main() -> int:
    here = pathlib.Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=pathlib.Path, default=here / "source-queries-v2.json")
    parser.add_argument("--v1-ledger", type=pathlib.Path, default=here / "source-corpus.csv")
    parser.add_argument("--output", type=pathlib.Path, default=here / "github-source-inventory-v2.csv")
    parser.add_argument("--summary", type=pathlib.Path, default=here / "github-source-inventory-v2-summary.json")
    args = parser.parse_args()

    config = json.loads(args.config.read_text())
    config_sha = sha256_bytes(args.config.read_bytes())
    raw = here / "raw" / config["snapshot_id"]
    raw.mkdir(parents=True, exist_ok=True)
    github = GitHub(token_from_gh())
    candidates: dict[str, dict[str, Any]] = {}
    query_stats: dict[str, dict[str, Any]] = {}

    def candidate(repo: str, query_id: str, path: str = "") -> None:
        if repo.count("/") != 1:
            return
        value = candidates.setdefault(repo.lower(), {"repository": repo, "queries": set(), "paths": set()})
        value["queries"].add(query_id)
        if path:
            value["paths"].add(path)

    per_page = int(config["per_page"])
    for kind, queries, endpoint in (
        ("code", config["github_code_queries"], "code"),
        ("repository", config["github_repository_queries"], "repositories"),
    ):
        for query in queries:
            repositories_before_query = set(candidates)
            stats = {"kind": kind, "query": query["q"], "page_budget": int(query["pages"]), "pages_fetched": 0, "items": 0, "unique_repositories": set()}
            for page in range(1, int(query["pages"]) + 1):
                sort = "indexed" if kind == "code" else "updated"
                params = urllib.parse.urlencode({"q": query["q"], "per_page": per_page, "page": page, "sort": sort, "order": "desc"})
                cache = raw / "query-pages" / f"{kind}-{query['id']}-p{page:02d}.json.gz"
                payload, _ = github.get(f"{GITHUB_API}/search/{endpoint}?{params}", cache, tolerate=())
                items = payload.get("items", []) if payload else []
                stats["pages_fetched"] += 1
                stats["items"] += len(items)
                for item in items:
                    repository = item["repository"] if kind == "code" else item
                    repo = repository["full_name"]
                    path = item.get("path", "") if kind == "code" else ""
                    candidate(repo, query["id"], path)
                    stats["unique_repositories"].add(repo.lower())
                print(f"{kind} query {query['id']} page {page}: {len(items)} items; candidates={len(candidates)}", flush=True)
                if len(items) < per_page:
                    break
            stats["unique_repositories"] = len(stats["unique_repositories"])
            stats["marginal_new_repositories"] = len(set(candidates) - repositories_before_query)
            query_stats[query["id"]] = stats

    with args.v1_ledger.open(newline="", encoding="utf-8") as handle:
        v1_rows = list(csv.DictReader(handle))
    v1_by_repo: dict[str, list[tuple[int, dict[str, str]]]] = defaultdict(list)
    for index, row in enumerate(v1_rows):
        v1_by_repo[row["repository"].lower()].append((index, row))

    repo_names = {row["repository"].lower(): row["repository"] for row in v1_rows}
    repo_names.update({key: value["repository"] for key, value in candidates.items()})
    metadata: dict[str, dict[str, Any]] = {}
    # GraphQL batches carry both repository metadata and the exact default HEAD,
    # avoiding one REST metadata request plus one commit request per candidate.
    # Any REST pages left by an interrupted earlier attempt remain preserved as
    # raw evidence but are not mixed into the final batch snapshot.
    missing_metadata: list[tuple[str, str]] = [(key, repo_names[key]) for key in sorted(repo_names)]
    for offset in range(0, len(missing_metadata), 30):
        batch = missing_metadata[offset:offset + 30]
        fragments = []
        for index, (_, repo) in enumerate(batch):
            owner, name = repo.split("/", 1)
            fragments.append(
                f'r{index}: repository(owner:{json.dumps(owner)},name:{json.dumps(name)}) {{ '
                "nameWithOwner description isFork isArchived stargazerCount pushedAt url "
                "repositoryTopics(first:20) { nodes { topic { name } } } "
                "parent { nameWithOwner parent { nameWithOwner parent { nameWithOwner } } } "
                "defaultBranchRef { name target { ... on Commit { oid } } } }"
            )
        query = "query { " + " ".join(fragments) + " }"
        cache = raw / "graphql-metadata" / f"batch-{offset // 30:04d}.json.gz"
        payload = github.graphql(query, cache)
        data = payload.get("data", {})
        for index, (key, requested) in enumerate(batch):
            item = data.get(f"r{index}")
            if not item:
                continue
            parent = item.get("parent")
            root = ""
            while parent:
                root = parent.get("nameWithOwner") or root
                parent = parent.get("parent")
            branch = item.get("defaultBranchRef") or {}
            target = branch.get("target") or {}
            metadata[key] = {
                "full_name": item.get("nameWithOwner") or requested,
                "description": item.get("description"),
                "fork": bool(item.get("isFork")),
                "archived": bool(item.get("isArchived")),
                "stargazers_count": item.get("stargazerCount", 0),
                "pushed_at": item.get("pushedAt") or "",
                "topics": [node["topic"]["name"] for node in item.get("repositoryTopics", {}).get("nodes", [])],
                "default_branch": branch.get("name") or "",
                "default_commit": target.get("oid") or "",
                "source": {"full_name": root} if root else None,
            }
        print(f"batched repository metadata {min(offset + len(batch), len(missing_metadata))}/{len(missing_metadata)}", flush=True)

    targets: dict[tuple[str, str], dict[str, Any]] = {}
    for index, row in enumerate(v1_rows):
        if not row["commit"]:
            continue
        key = (row["repository"].lower(), row["commit"])
        target = targets.setdefault(key, {"repository": row["repository"], "commit": row["commit"], "origins": set(), "v1_indexes": [], "queries": set(), "paths": set()})
        target["origins"].add("v1-preserved")
        target["v1_indexes"].append(index)
        if row["repository"].lower() in candidates:
            target["queries"].update(candidates[row["repository"].lower()]["queries"])
            target["paths"].update(candidates[row["repository"].lower()]["paths"])

    for key, item in candidates.items():
        if any(row["commit"] for _, row in v1_by_repo.get(key, [])):
            continue
        info = metadata.get(key)
        commit = info.get("default_commit") if info else ""
        if not commit:
            branch = info.get("default_branch") if info else ""
            if not branch:
                continue
            cache = raw / "default-commits" / f"{safe_name(item['repository'])}.json.gz"
            payload, _ = github.get(f"{GITHUB_API}/repos/{item['repository']}/commits/{urllib.parse.quote(branch, safe='')}", cache)
            commit = payload.get("sha", "") if payload else ""
        if not commit:
            continue
        target = targets.setdefault((key, commit), {"repository": item["repository"], "commit": commit, "origins": set(), "v1_indexes": [], "queries": set(), "paths": set()})
        target["origins"].add("v2-consumer-first")
        target["queries"].update(item["queries"])
        target["paths"].update(item["paths"])

    records: list[dict[str, Any]] = []
    for offset, ((repo_key, commit), target) in enumerate(sorted(targets.items()), 1):
        info = metadata.get(repo_key, {})
        scan = scan_repository(target["repository"], commit, info, sorted(target["queries"]), set(target["paths"]), github, raw, config, config_sha)
        fork_root = ((info.get("source") or {}).get("full_name") or (info.get("parent") or {}).get("full_name") or "")
        consumers = scan["consumer_files"]
        circuits = scan["circuit_paths"]
        if scan["scan_status"] == "tree-unavailable":
            predup = "unavailable"
            basis = "pinned GitHub tree unavailable"
        elif (scan["tree_truncated"] or "cap-reached" in scan["scan_status"] or scan["solidity_fetch_failures"]) and not (circuits and consumers):
            predup = "inventory-incomplete"
            basis = f"syntactic inventory incomplete: {scan['scan_status']}"
        elif circuits and consumers:
            predup = "in-scope"
            basis = "first-party circuit path plus Solidity verifier-call regex; committed verifier optional"
        elif circuits:
            predup = "no consumer"
            basis = "first-party circuit path found; no Solidity verifier-call regex matched"
        else:
            predup = "no circuit"
            basis = "no first-party .circom/.nr/.zok path found in pinned tree"
        evidence = []
        for source in consumers:
            rules = sorted({match["rule"] for match in source["matches"]})
            lines = sorted({match["line"] for match in source["matches"]})
            evidence.append(f"{source['path']}@sha256:{source['source_sha256']}#rules={'+'.join(rules)}#lines={'+'.join(map(str, lines))}")
        records.append({
            "repository": target["repository"], "commit": commit,
            "origins": "|".join(sorted(target["origins"])), "v1_row_indexes": "|".join(map(str, sorted(target["v1_indexes"]))),
            "query_provenance": "|".join(sorted(target["queries"])), "predup_disposition": predup, "disposition_basis": basis,
            "circuit_paths": "|".join(item["path"] for item in circuits[:200]), "verifier_paths": "|".join(scan["verifier_paths"][:200]),
            "consumer_paths": "|".join(item["path"] for item in consumers[:200]), "consumer_evidence": "||".join(evidence),
            "consumer_source_sha256s": "|".join(sorted({item["source_sha256"] for item in consumers})),
            "circuit_fingerprint": scan["circuit_fingerprint"], "fork_root": fork_root,
            "is_fork": str(bool(info.get("fork"))).lower() if info else "", "stars": str(info.get("stargazers_count", "")) if info else "",
            "archived": str(bool(info.get("archived"))).lower() if info else "", "pushed_at": info.get("pushed_at", "") if info else "",
            "readme_path": scan.get("readme_path", ""), "readme_sha256": scan.get("readme_sha256", ""),
            "maturity": scan.get("maturity", "unclassified"), "maturity_basis": scan.get("maturity_basis", "metadata unavailable"),
            "scan_status": scan["scan_status"], "tree_cache_sha256": scan["tree_cache_sha256"],
            "tree_truncated": str(scan["tree_truncated"]).lower(), "solidity_files_considered": str(scan["solidity_files_considered"]),
            "solidity_files_fetched": str(scan["solidity_files_fetched"]), "solidity_fetch_failures": str(scan["solidity_fetch_failures"]),
        })
        if offset % 25 == 0:
            print(f"repository scans {offset}/{len(targets)}; in-scope={sum(row['predup_disposition'] == 'in-scope' for row in records)}", flush=True)

    v2_target_repositories = {
        repo_key
        for (repo_key, _), target in targets.items()
        if "v2-consumer-first" in target["origins"]
    }
    for key, item in sorted(candidates.items()):
        if any(row["commit"] for _, row in v1_by_repo.get(key, [])) or key in v2_target_repositories:
            continue
        records.append({
            "repository": item["repository"], "commit": "", "origins": "v2-consumer-first", "v1_row_indexes": "",
            "query_provenance": "|".join(sorted(item["queries"])), "predup_disposition": "unavailable",
            "disposition_basis": "GitHub repository/default-branch commit metadata unavailable",
            "circuit_paths": "", "verifier_paths": "", "consumer_paths": "", "consumer_evidence": "", "consumer_source_sha256s": "",
            "circuit_fingerprint": "", "fork_root": "", "is_fork": "", "stars": "", "archived": "", "pushed_at": "",
            "readme_path": "", "readme_sha256": "", "maturity": "unclassified", "maturity_basis": "metadata unavailable",
            "scan_status": "metadata-unavailable", "tree_cache_sha256": "", "tree_truncated": "false",
            "solidity_files_considered": "0", "solidity_files_fetched": "0", "solidity_fetch_failures": "0",
        })

    fields = list(records[0]) if records else []
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(records)

    repo_dispositions = {row["repository"].lower(): row["predup_disposition"] for row in records}
    for query_id, stats in query_stats.items():
        query_repos = {key for key, item in candidates.items() if query_id in item["queries"]}
        stats["in_scope_repositories"] = sum(repo_dispositions.get(key) == "in-scope" for key in query_repos)
    disposition_counts: dict[str, int] = defaultdict(int)
    for row in records:
        disposition_counts[row["predup_disposition"]] += 1
    summary = {
        "schema_version": 2,
        "snapshot_id": config["snapshot_id"],
        "generated_utc": dt.datetime.now(dt.UTC).isoformat(),
        "scanner_version": SCANNER_VERSION,
        "scope": "path and verifier-call regex inventory only; no BindCheck, screen_consumers.py, scan_p4.py, Track B, or vulnerability analysis",
        "config_sha256": config_sha,
        "v1_ledger_sha256": sha256_bytes(args.v1_ledger.read_bytes()),
        "candidate_repositories": len(candidates),
        "scanned_repository_revisions": len(records),
        "predup_disposition_counts": dict(sorted(disposition_counts.items())),
        "query_yields": query_stats,
        "output_sha256": sha256_bytes(args.output.read_bytes()),
        "eval_analyzer_runs": 0,
    }
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (raw / "manifest.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
