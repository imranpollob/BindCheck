#!/usr/bin/env python3
"""Best-effort solc AST probe for the selected source corpus.

The probe is deliberately offline. It resolves repository-local imports, asks
the installed solc for compact ASTs, and records failures rather than silently
falling back to text parsing.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import subprocess
from pathlib import Path, PurePosixPath


IMPORT_RE = re.compile(
    r"import\s+(?:[^;]*?\s+from\s+)?[\"']([^\"']+)[\"']\s*;",
    re.MULTILINE,
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def resolve_import(repo: Path, source_key: str, imported: str) -> str | None:
    candidates: list[PurePosixPath] = []
    if imported.startswith("."):
        candidates.append(PurePosixPath(source_key).parent / imported)
    else:
        candidates.append(PurePosixPath(imported))
        candidates.extend(PurePosixPath(prefix) / imported for prefix in ("src", "contracts", "lib"))
    for candidate in candidates:
        normalized = PurePosixPath(posixpath.normpath(candidate.as_posix()))
        path = repo / normalized
        if path.is_file():
            return path.relative_to(repo).as_posix()
    return None


def closure(repo: Path, roots: list[str]) -> tuple[dict[str, dict[str, str]], list[str]]:
    sources: dict[str, dict[str, str]] = {}
    missing: set[str] = set()
    queue = list(dict.fromkeys(roots))
    while queue:
        key = queue.pop(0)
        if key in sources:
            continue
        path = repo / key
        if not path.is_file():
            missing.add(f"{key} (root missing)")
            continue
        content = read(path)
        sources[key] = {"content": content}
        for imported in IMPORT_RE.findall(content):
            resolved = resolve_import(repo, key, imported)
            if resolved:
                queue.append(resolved)
            else:
                missing.add(f"{key} -> {imported}")
    return sources, sorted(missing)


def walk(node: object):
    """Yield every Solidity AST dictionary below *node*."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def expression_name(node: object) -> str:
    if not isinstance(node, dict):
        return ""
    kind = node.get("nodeType")
    if kind == "Identifier":
        return str(node.get("name", ""))
    if kind == "MemberAccess":
        prefix = expression_name(node.get("expression"))
        member = str(node.get("memberName", ""))
        return f"{prefix}.{member}" if prefix else member
    if kind == "IndexAccess":
        return expression_name(node.get("baseExpression"))
    if kind == "FunctionCall":
        return expression_name(node.get("expression"))
    return ""


def fixed_array_count(node: object, declarations: dict[int, dict[str, object]]) -> int | None:
    if not isinstance(node, dict):
        return None
    if node.get("nodeType") == "TupleExpression":
        components = [item for item in node.get("components", []) if item is not None]
        return len(components)
    type_string = str(node.get("typeDescriptions", {}).get("typeString", ""))
    match = re.search(r"uint(?:256)?\[(\d+)\]", type_string)
    if match:
        return int(match.group(1))
    referenced = node.get("referencedDeclaration")
    if isinstance(referenced, int) and referenced in declarations:
        return fixed_array_count(declarations[referenced], declarations)
    return None


def ast_facts(output: dict[str, object], roots: list[str]) -> dict[str, object]:
    ast_roots = [
        value.get("ast")
        for key, value in output.get("sources", {}).items()
        if key in roots and isinstance(value, dict) and value.get("ast")
    ]
    nodes = [node for root in ast_roots for node in walk(root)]
    declarations = {
        node["id"]: node for node in nodes
        if isinstance(node.get("id"), int)
    }

    verifier_arities: set[int] = set()
    proof_call_arities: set[int] = set()
    proof_calls = 0
    effects: set[str] = set()
    replay_reads: set[str] = set()
    replay_writes: set[str] = set()
    replay_words = ("spent", "nullifier", "used")
    effect_words = ("transfer", "transferfrom", "safetransfer", "safetransferfrom", "mint", "call")

    for node in nodes:
        kind = node.get("nodeType")
        if kind == "FunctionDefinition" and "verify" in str(node.get("name", "")).lower():
            parameters = node.get("parameters", {}).get("parameters", [])
            if parameters:
                count = fixed_array_count(parameters[-1], declarations)
                if count is not None:
                    verifier_arities.add(count)
        if kind == "FunctionCall":
            called = expression_name(node.get("expression"))
            lowered = called.lower()
            if "verify" in lowered and "proof" in lowered:
                proof_calls += 1
                arguments = node.get("arguments", [])
                if arguments:
                    count = fixed_array_count(arguments[-1], declarations)
                    if count is not None:
                        proof_call_arities.add(count)
            member = lowered.rsplit(".", 1)[-1]
            if member in effect_words:
                effects.add(member)
        if kind == "IndexAccess":
            base = expression_name(node.get("baseExpression"))
            if any(word in base.lower() for word in replay_words):
                replay_reads.add(base)
        if kind == "Assignment":
            left = node.get("leftHandSide")
            base = expression_name(left)
            if isinstance(left, dict) and left.get("nodeType") == "IndexAccess" and any(
                word in base.lower() for word in replay_words
            ):
                replay_writes.add(base)

    return {
        "verifier_public_input_arities": sorted(verifier_arities),
        "consumer_verify_calls": proof_calls,
        "consumer_public_input_arities": sorted(proof_call_arities),
        "replay_index_reads": sorted(replay_reads),
        "replay_index_writes": sorted(replay_writes),
        "effect_calls": sorted(effects),
    }


def probe(solc: str, repo: Path, roots: list[str]) -> dict[str, object]:
    sources, missing = closure(repo, roots)
    standard_input = {
        "language": "Solidity",
        "sources": sources,
        "settings": {
            "outputSelection": {"*": {"": ["ast"], "*": ["abi"]}},
        },
    }
    try:
        completed = subprocess.run(
            [solc, "--standard-json"],
            input=json.dumps(standard_input),
            text=True,
            capture_output=True,
            timeout=30,
            cwd=repo,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "tool-failed", "sources_loaded": len(sources),
            "missing_imports": missing, "errors": [str(exc)], "ast_files": [],
        }
    raw = completed.stdout
    start = raw.find("{")
    try:
        output = json.loads(raw[start:]) if start >= 0 else {}
    except json.JSONDecodeError as exc:
        return {
            "status": "invalid-output", "sources_loaded": len(sources),
            "missing_imports": missing, "errors": [str(exc), completed.stderr[-1000:]],
            "ast_files": [],
        }
    errors = [
        item.get("formattedMessage", item.get("message", "unknown solc error"))
        for item in output.get("errors", [])
        if item.get("severity") == "error"
    ]
    ast_files = sorted(
        key for key, value in output.get("sources", {}).items()
        if isinstance(value, dict) and value.get("ast")
    )
    status = "ast" if all(root in ast_files for root in roots) else "compile-error"
    return {
        "status": status, "sources_loaded": len(sources),
        "missing_imports": missing, "errors": errors[:10], "ast_files": ast_files,
        "facts": ast_facts(output, roots) if status == "ast" else {},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    parser.add_argument("--candidates", type=Path, default=here / "raw" / "candidates-v5.json")
    parser.add_argument("--repos", type=Path, default=here / "work" / "repos")
    parser.add_argument("--solc", default="solc")
    parser.add_argument("--output", type=Path, default=here / "raw" / "solc-ast.json")
    args = parser.parse_args()

    data = json.loads(args.candidates.read_text(encoding="utf-8"))
    selected = [x for x in data if x.get("circuit") and x.get("verifier") and x.get("consumer")][:50]
    results = []
    for item in selected:
        repo = args.repos / item["repository"].replace("/", "_")
        roots = list(dict.fromkeys([item["verifier"], item["consumer"]]))
        result = probe(args.solc, repo, roots)
        result.update({"repository": item["repository"], "roots": roots})
        results.append(result)
        print(item["repository"], result["status"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary: dict[str, int] = {}
    for item in results:
        summary[item["status"]] = summary.get(item["status"], 0) + 1
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
