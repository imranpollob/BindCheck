#!/usr/bin/env python3
"""Wide Solidity-first screen for proof-to-effect integration patterns.

The output is triage evidence (E1/UNKNOWN), not a security verdict. The screen
never compiles or executes project code and never contacts a deployment.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
from collections import Counter

from scan_p4 import canonical_guard, named_constants


EXCLUDED = {".git", "node_modules", "out", "cache", "artifacts", "build", "vendor", "test", "tests"}
EFFECT_NAMES = {"transfer", "safetransfer", "handletransfer", "mint", "_mint", "safemint", "_safemint"}
IDENTIFIER = re.compile(r"\b[A-Za-z_]\w*\b")
KEYWORDS = {
    "address", "bool", "bytes", "calldata", "contract", "false", "memory", "msg",
    "payable", "storage", "this", "true", "uint", "uint256",
}


def local_canonicality_guard(body: str, name: str) -> bool:
    """Recognize either an allow-form `< r` check or a reject-form `>= r` check."""
    value = rf"(?:u?int(?:256)?\s*\(\s*)?\b{re.escape(name)}\b\s*\)?"
    modulus = rf"(?:21888242871839275222246405745257275088548364400416034343698204186575808495617|[A-Za-z_]\w*(?:SNARK|SCALAR|FIELD)[A-Za-z_]*|[A-Za-z_]\w*(?:snark|scalar|field)[A-Za-z_]*)"
    comparisons = (
        rf"{value}\s*<\s*{modulus}",
        rf"{modulus}\s*>\s*{value}",
        rf"{value}\s*>=\s*{modulus}",
        rf"{modulus}\s*<=\s*{value}",
    )
    return any(re.search(pattern, body) for pattern in comparisons)


def expression_pattern(expression: str) -> str:
    pieces: list[str] = []
    for part in re.split(r"(\W+)", expression.strip()):
        if not part:
            continue
        if part[0].isalnum() or part[0] == "_":
            pieces.append(re.escape(part))
            continue
        for char in part:
            if char.isspace():
                pieces.append(r"\s*")
            else:
                pieces.extend((r"\s*", re.escape(char), r"\s*"))
    return "".join(pieces)


def expression_canonicality_guard(body: str, expression: str) -> bool:
    value = rf"(?:u?int(?:256)?\s*\(\s*)?{expression_pattern(expression)}\s*\)?"
    modulus = rf"(?:21888242871839275222246405745257275088548364400416034343698204186575808495617|[A-Za-z_]\w*(?:SNARK|SCALAR|FIELD)[A-Za-z_]*|[A-Za-z_]\w*(?:snark|scalar|field)[A-Za-z_]*)"
    return any(re.search(pattern, body) for pattern in (
        rf"{value}\s*<\s*{modulus}", rf"{modulus}\s*>\s*{value}",
        rf"{value}\s*>=\s*{modulus}", rf"{modulus}\s*<=\s*{value}",
    ))


def strip_comments_preserve_lines(text: str) -> str:
    def blank(match: re.Match[str]) -> str:
        return "".join("\n" if char == "\n" else " " for char in match.group(0))
    text = re.sub(r"/\*.*?\*/", blank, text, flags=re.S)
    return re.sub(r"//[^\n]*", blank, text)


def balanced(text: str, opening: int, left: str, right: str) -> tuple[str, int] | None:
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == left:
            depth += 1
        elif text[index] == right:
            depth -= 1
            if depth == 0:
                return text[opening + 1:index], index + 1
    return None


def split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start = 0
    for index, char in enumerate(text):
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    parts.append(text[start:].strip())
    return [part for part in parts if part]


def parameters(header: str) -> set[str]:
    opening = header.find("(")
    parsed = balanced(header, opening, "(", ")") if opening >= 0 else None
    if parsed is None:
        return set()
    result: set[str] = set()
    for parameter in split_top_level(parsed[0]):
        tokens = IDENTIFIER.findall(parameter)
        tokens = [token for token in tokens if token.lower() not in KEYWORDS and not re.fullmatch(r"u?int\d+", token)]
        if tokens:
            result.add(tokens[-1])
    return result


def functions(text: str):
    pattern = re.compile(r"\bfunction\s+([A-Za-z_]\w*)\s*\(")
    for match in pattern.finditer(text):
        params = balanced(text, text.find("(", match.start()), "(", ")")
        if params is None:
            continue
        body_open = text.find("{", params[1])
        semicolon = text.find(";", params[1], body_open if body_open >= 0 else len(text))
        if body_open < 0 or semicolon >= 0:
            continue
        body = balanced(text, body_open, "{", "}")
        if body is None:
            continue
        yield {
            "name": match.group(1),
            "start": match.start(),
            "line": text.count("\n", 0, match.start()) + 1,
            "header": text[match.start():body_open],
            "body": body[0],
        }


def calls(body: str, pattern: str):
    for match in re.finditer(pattern, body, flags=re.I):
        opening = body.find("(", match.start())
        parsed = balanced(body, opening, "(", ")") if opening >= 0 else None
        if parsed is not None:
            yield match, split_top_level(parsed[0]), parsed[0]


def identifiers(expression: str) -> set[str]:
    return {token for token in IDENTIFIER.findall(expression) if token.lower() not in KEYWORDS}


def public_vector(body: str, args: list[str]) -> tuple[str | None, set[str], int | None]:
    if not args:
        return None, set(), None
    expression = args[-1].strip()
    sources = identifiers(expression)
    count: int | None = None
    if expression.startswith("[") and expression.endswith("]"):
        values = split_top_level(expression[1:-1])
        return expression, set().union(*(identifiers(value) for value in values)), len(values)
    if re.fullmatch(r"[A-Za-z_]\w*", expression):
        name = expression
        assignments: dict[int, str] = {}
        for index, value in re.findall(rf"\b{re.escape(name)}\s*\[\s*(\d+)\s*\]\s*=\s*([^;]+);", body):
            assignments[int(index)] = value.strip()
        if assignments:
            sources |= set().union(*(identifiers(value) for value in assignments.values()))
            count = max(assignments) + 1
        declaration = re.search(rf"\buint(?:256)?\s*\[\s*(\d+)\s*\]\s+(?:memory|calldata|storage)?\s*{re.escape(name)}\b", body)
        if declaration:
            count = int(declaration.group(1))
    array_type = re.search(r"\buint(?:256)?\s*\[\s*(\d+)\s*\]", expression)
    if array_type:
        count = int(array_type.group(1))
    return expression, sources, count


def verifier_arities(text: str) -> set[int]:
    arities: set[int] = set()
    for match in re.finditer(r"\bfunction\s+verify(?:Tx|Proof)\s*\(", text, flags=re.I):
        parsed = balanced(text, text.find("(", match.start()), "(", ")")
        if parsed is None:
            continue
        args = split_top_level(parsed[0])
        if not args:
            continue
        fixed = re.search(r"\buint(?:256)?\s*\[\s*(\d+)\s*\]", args[-1])
        if fixed:
            arities.add(int(fixed.group(1)))
    return arities


def effect_roles(name: str, args: list[str]) -> list[tuple[str, str]]:
    lowered = name.lower()
    if lowered in EFFECT_NAMES and len(args) >= 2:
        return [("recipient", args[0]), ("amount", args[1])]
    return []


def direct_parameter(expression: str, params: set[str]) -> str | None:
    stripped = expression.strip()
    stripped = re.sub(r"^(?:payable|address|uint(?:256)?)\s*\(", "", stripped)
    stripped = stripped.rstrip(")").strip()
    return stripped if stripped in params else None


def git_head(repo: pathlib.Path) -> str | None:
    if not (repo / ".git").exists():
        return None
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, text=True, capture_output=True)
    return result.stdout.strip() if result.returncode == 0 else None


def analyze_function(
    repository: str,
    commit: str | None,
    repo: pathlib.Path,
    path: pathlib.Path,
    source_hash: str,
    item: dict[str, object],
    repo_arities: set[int],
    repo_verifier_canonical_guard: bool,
) -> dict[str, object] | None:
    body = str(item["body"])
    verify_calls = list(calls(body, r"(?:\b[A-Za-z_]\w*\s*\.)?verify(?:Tx|Proof)\s*\("))
    if not verify_calls:
        return None
    effect_calls = list(calls(body, r"(?<![A-Za-z0-9_])(_?safeMint|_?mint|safeTransfer|handleTransfer|transfer|insert)\s*\("))
    if not effect_calls:
        return None

    params = parameters(str(item["header"]))
    all_public_sources: set[str] = set()
    public_expressions: list[str] = []
    public_counts: list[int] = []
    for _, verify_args, _ in verify_calls:
        expression, sources, count = public_vector(body, verify_args)
        if expression:
            public_expressions.append(expression)
        all_public_sources |= sources
        if count is not None:
            public_counts.append(count)

    warnings: dict[str, list[str]] = {"P1": [], "P2": [], "P3": [], "P5": []}
    effects: list[dict[str, str]] = []
    for match, args, _ in effect_calls:
        name = match.group(1)
        for role, expression in effect_roles(name, args):
            effects.append({"call": name, "role": role, "expression": expression})
            parameter = direct_parameter(expression, params)
            if parameter is None:
                continue
            sender_bound = role == "recipient" and "msg.sender" in expression.replace(" ", "")
            if parameter not in all_public_sources and not sender_bound:
                warnings["P1"].append(
                    f"effect {name}.{role} uses function parameter {parameter} absent from recovered verifier public-input sources"
                )

    joined_public = " ".join(public_expressions + sorted(all_public_sources)).lower()
    has_context = any(token in joined_public for token in ("chainid", "chain_id", "domain", "app", "contract", "verifyingcontract"))
    has_context = has_context or "block.chainid" in body or "address(this)" in body.replace(" ", "")
    if not has_context:
        warnings["P2"].append("no chain id, contract address, or explicit app/domain value recovered in verifier inputs or local guards")

    nullifiers = sorted(
        token for token in (all_public_sources | params)
        if any(word in token.lower() for word in ("nullifier", "serial", "nullhash"))
    )
    for nullifier in nullifiers:
        indexed = re.findall(rf"\b([A-Za-z_]\w*)\s*\[\s*{re.escape(nullifier)}\s*\]", body)
        read = bool(indexed) and bool(re.search(rf"(?:require|if)\s*\([^;]*{re.escape(nullifier)}", body, flags=re.S))
        write = bool(re.search(rf"\[[^\]]*{re.escape(nullifier)}[^\]]*\]\s*=\s*(?:true|1)\b", body))
        helper = bool(re.search(rf"\b[A-Za-z_]*(?:nullifier|spent|use)[A-Za-z_]*\s*\([^;]*\b{re.escape(nullifier)}\b", body, flags=re.I))
        if not (read and write) and not helper:
            warnings["P3"].append(f"proof-related replay key {nullifier}: local spent read={read}, write={write}, helper barrier={helper}")
        elif nullifier in all_public_sources and indexed and not (
            local_canonicality_guard(body, nullifier) or repo_verifier_canonical_guard
        ):
            warnings["P3"].append(
                f"raw spent key {nullifier} is a verifier public input but neither the consumer nor a repository verifier has a detected < r canonicality guard"
            )

    inferred_keys = {
        key.strip()
        for mapping_name, key in re.findall(
            r"\b([A-Za-z_]\w*)\s*\[\s*([A-Za-z_]\w*(?:\s*\[\s*[^\]\n]+\s*\])?)\s*\]",
            body,
            flags=re.I,
        )
        if any(word in mapping_name.lower() for word in ("nullifier", "spent", "used"))
    }
    for key in sorted(inferred_keys):
        if re.fullmatch(r"[A-Za-z_]\w*", key) and key in nullifiers:
            continue
        key_re = expression_pattern(key)
        read = bool(re.search(rf"(?:require|if)\s*\([^;]*\b[A-Za-z_]\w*\s*\[\s*{key_re}\s*\]", body, flags=re.S | re.I))
        write = bool(re.search(rf"\b[A-Za-z_]\w*\s*\[\s*{key_re}\s*\]\s*=\s*(?:true|1)\b", body, flags=re.I))
        public_bound = bool(identifiers(key) & all_public_sources) or any(key in expression for expression in public_expressions)
        if read and write and public_bound and not (expression_canonicality_guard(body, key) or repo_verifier_canonical_guard):
            warnings["P3"].append(
                f"raw spent-key expression {key} is verifier-bound but neither the consumer nor a repository verifier has a detected < r canonicality guard"
            )

    for count in sorted(set(public_counts)):
        if repo_arities and count not in repo_arities:
            warnings["P5"].append(f"consumer vector count {count} not among repository verifier arities {sorted(repo_arities)}")

    if not any(warnings.values()):
        return None
    return {
        "repository": repository,
        "commit": commit,
        "path": path.relative_to(repo).as_posix(),
        "source_sha256": source_hash,
        "function": item["name"],
        "line": item["line"],
        "function_parameters": sorted(params),
        "public_input_expressions": public_expressions,
        "public_input_sources": sorted(all_public_sources),
        "public_input_counts": sorted(set(public_counts)),
        "repo_verifier_arities": sorted(repo_arities),
        "effects": effects,
        "warnings": warnings,
        "evidence_grade": "E1",
        "verdict": "UNKNOWN",
    }


def main() -> int:
    here = pathlib.Path(__file__).resolve().parent
    root = here.parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos", type=pathlib.Path, default=root / "feasibility/work/v2/repos")
    parser.add_argument("--repo", action="append", type=pathlib.Path, help="scan this repository/archive directory directly (repeatable)")
    parser.add_argument("--output-json", type=pathlib.Path, default=here / "consumer-screen.json")
    parser.add_argument("--output-csv", type=pathlib.Path, default=here / "consumer-screen.csv")
    args = parser.parse_args()

    records: list[dict[str, object]] = []
    scanned_files = 0
    scanned_functions = 0
    proof_effect_functions = 0
    repos = sorted(args.repo) if args.repo else sorted(path for path in args.repos.iterdir() if (path / ".git").exists())
    for repo in repos:
        repository = repo.name.replace("__", "/", 1)
        commit = git_head(repo)
        sources: list[tuple[pathlib.Path, str, str]] = []
        arities: set[int] = set()
        for path in sorted(repo.rglob("*.sol")):
            if not path.is_file() or EXCLUDED & set(path.relative_to(repo).parts) or path.stat().st_size > 5_000_000:
                continue
            raw = path.read_text(encoding="utf-8", errors="replace")
            text = strip_comments_preserve_lines(raw)
            sources.append((path, raw, text))
            arities |= verifier_arities(text)
        verifier_guard = any(
            re.search(r"\bverify(?:Tx|Proof)\s*\(", text, flags=re.I)
            and canonical_guard(text, named_constants(text))
            for _, _, text in sources
        )
        scanned_files += len(sources)
        for path, raw, text in sources:
            source_hash = hashlib.sha256(raw.encode()).hexdigest()
            for item in functions(text):
                scanned_functions += 1
                body = str(item["body"])
                if not re.search(r"verify(?:Tx|Proof)\s*\(", body, flags=re.I) or not re.search(r"(?<![A-Za-z0-9_])(?:_?safeMint|_?mint|safeTransfer|handleTransfer|transfer|insert)\s*\(", body, flags=re.I):
                    continue
                proof_effect_functions += 1
                record = analyze_function(repository, commit, repo, path, source_hash, item, arities, verifier_guard)
                if record is not None:
                    records.append(record)

    pattern_counts = Counter(
        pattern for record in records for pattern, messages in record["warnings"].items() if messages  # type: ignore[union-attr]
    )
    summary = {
        "generated_utc": dt.datetime.now(dt.UTC).isoformat(),
        "scope": "lexical Solidity function screen; warnings require adjudication",
        "repositories": len(repos),
        "solidity_files_screened": scanned_files,
        "functions_screened": scanned_functions,
        "proof_and_effect_functions": proof_effect_functions,
        "warning_functions": len(records),
        "warning_functions_by_pattern": dict(sorted(pattern_counts.items())),
    }
    args.output_json.write_text(json.dumps({"summary": summary, "records": records}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with args.output_csv.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["repository", "commit", "path", "function", "line", "P1", "P2", "P3", "P5", "evidence_grade", "verdict"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({
                "repository": record["repository"], "commit": record["commit"], "path": record["path"],
                "function": record["function"], "line": record["line"],
                **{pattern: " | ".join(record["warnings"][pattern]) for pattern in ("P1", "P2", "P3", "P5")},  # type: ignore[index]
                "evidence_grade": record["evidence_grade"], "verdict": record["verdict"],
            })
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
