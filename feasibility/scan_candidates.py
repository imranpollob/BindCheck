#!/usr/bin/env python3
"""Cheap source-only Circom/Groth16/Solidity integration feasibility scan.

The scanner intentionally emits candidates and UNKNOWNs, never safety claims.
It does not execute contracts, generate proofs, or contact deployments.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable


ROLE_WORDS = (
    "recipient", "receiver", "beneficiary", "to", "amount", "value",
    "fee", "relayer", "target", "destination", "withdrawal", "payout",
)
NULLIFIER_WORDS = ("nullifier", "nullifierhash", "nullifier_hash")
GENERATED_MARKERS = (
    "pairingProd4", "verifyingKey", "SNARK_SCALAR_FIELD", "VK_ALPHA",
    "Pairing.G1Point", "staticcall(sub(gas()", "generated with [snarkjs",
    "uint256 constant r", "IC0x", "vk.IC", "pairing.pairing",
)
PLACEHOLDER_MARKERS = (
    "placeholder", "simulated", "always returns false", "return true; //",
    "simplified version", "simulate proof verification", "dummy verifier",
)


@dataclass
class CircuitFact:
    path: str
    main_template: str | None
    public_signals: list[str]
    signal_count: int | None
    binding: dict[str, str]
    parse_notes: list[str] = field(default_factory=list)


@dataclass
class SolidityFact:
    path: str
    kind: str
    verifier_input_count: int | None = None
    canonical_public_inputs: bool | None = None
    verify_vector: list[str] = field(default_factory=list)
    verify_vector_count: int | None = None
    effect_roles: list[str] = field(default_factory=list)
    has_nullifier: bool = False
    replay_read: bool = False
    replay_write: bool = False


@dataclass
class Candidate:
    repository: str
    commit: str | None
    provenance: str
    eligibility: str
    circuit: str | None
    verifier: str | None
    consumer: str | None
    public_signals: list[str]
    verifier_input_count: int | None
    consumer_vector: list[str]
    checks: dict[str, list[str]]
    evidence_grade: str
    verdict: str
    limitations: list[str]


def run(*args: str, cwd: Path | None = None) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        return ""


def strip_comments(text: str) -> str:
    """Remove comments before identifying executable declarations/calls."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def split_csv(text: str) -> list[str]:
    return [x.strip() for x in text.replace("\n", " ").split(",") if x.strip()]


def balanced_block(text: str, start: int) -> str | None:
    opening = text.find("{", start)
    if opening < 0:
        return None
    depth = 0
    for i in range(opening, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1:i]
    return None


def remove_disabled_static_blocks(body: str, constants: dict[str, int]) -> tuple[str, list[str]]:
    """Prune simple Circom compile-time ``if (parameter)`` blocks set to zero."""
    notes: list[str] = []
    for name, value in constants.items():
        if value != 0:
            continue
        pattern = re.compile(rf"\bif\s*\(\s*{re.escape(name)}\s*\)\s*\{{")
        while True:
            match = pattern.search(body)
            if not match:
                break
            opening = body.find("{", match.start())
            depth = 0
            end = None
            for i in range(opening, len(body)):
                if body[i] == "{":
                    depth += 1
                elif body[i] == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end is None:
                break
            body = body[:match.start()] + (" " * (end - match.start())) + body[end:]
            notes.append(f"pruned-static-if:{name}=0")
    return body, notes


def flatten_signal(name: str, size: str | None) -> tuple[list[str], bool]:
    if size is None:
        return [name], True
    if not size.isdigit():
        return [f"{name}[?]"], False
    n = int(size)
    if n > 64:
        return [f"{name}[0..{n - 1}]"], False
    return [f"{name}[{i}]" for i in range(n)], True


def parse_circuit(path: Path, repo_root: Path) -> CircuitFact:
    text = strip_comments(read_text(path))
    notes: list[str] = []
    main = re.search(
        r"component\s+main\s*(?:\{\s*public\s*\[([^\]]*)\]\s*\})?\s*=\s*([A-Za-z_]\w*)\s*\((.*?)\)\s*;",
        text,
        re.S,
    )
    if not main:
        return CircuitFact(str(path.relative_to(repo_root)), None, [], None, {}, ["main-not-parsed"])
    explicit_raw = split_csv(main.group(1) or "")
    template_name = main.group(2)
    invocation_args = split_csv(main.group(3) or "")
    tmpl = re.search(
        rf"template\s+{re.escape(template_name)}\s*\(([^)]*)\)\s*\{{", text
    )
    body = balanced_block(text, tmpl.start()) if tmpl else None
    if body is None:
        notes.append("main-template-body-not-local")
        body = text
    else:
        template_args = split_csv(tmpl.group(1))
        constants = {
            name: int(value)
            for name, value in zip(template_args, invocation_args)
            if re.fullmatch(r"[A-Za-z_]\w*", name) and re.fullmatch(r"\d+", value)
        }
        body, static_notes = remove_disabled_static_blocks(body, constants)
        notes.extend(static_notes)

    outputs: list[str] = []
    complete = True
    for match in re.finditer(r"signal\s+output\s+([A-Za-z_]\w*)\s*(?:\[\s*([^\]]+)\s*\])?", body):
        expanded, exact = flatten_signal(match.group(1), match.group(2))
        outputs.extend(expanded)
        complete &= exact

    explicit: list[str] = []
    for item in explicit_raw:
        if "[" in item:
            explicit.append(item)
            continue
        declaration = re.search(
            rf"signal\s+(?:input|output)\s+{re.escape(item)}\s*(?:\[\s*([^\]]+)\s*\])?",
            body,
        )
        expanded, exact = flatten_signal(item, declaration.group(1) if declaration else None)
        explicit.extend(expanded)
        complete &= exact
    public_signals = outputs + explicit
    if not public_signals:
        notes.append("no-public-list-recovered")
    if not complete:
        notes.append("symbolic-or-large-public-array")
    binding: dict[str, str] = {}
    for signal in public_signals:
        base = signal.split("[")[0]
        constrained = False
        witnessed_only = False
        for line in body.splitlines():
            if not re.search(rf"\b{re.escape(base)}\b", line):
                continue
            if "<==" in line or "==>" in line or "===" in line:
                constrained = True
            elif "<--" in line or "-->" in line:
                witnessed_only = True
        binding[signal] = "constraint-referenced" if constrained else (
            "witness-only" if witnessed_only else "no-constraint-reference"
        )
    return CircuitFact(
        str(path.relative_to(repo_root)), template_name, public_signals,
        len(public_signals) if public_signals and complete else None, binding, notes,
    )


def extract_call(text: str, marker_start: int) -> str | None:
    opening = text.find("(", marker_start)
    if opening < 0:
        return None
    depth = 0
    for i in range(opening, len(text)):
        if text[i] in "([":
            depth += 1
        elif text[i] in ")]":
            depth -= 1
            if depth == 0:
                return text[opening + 1:i]
    return None


def top_level_args(text: str) -> list[str]:
    args: list[str] = []
    depth = 0
    start = 0
    for i, char in enumerate(text):
        if char in "([{" :
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            args.append(text[start:i].strip())
            start = i + 1
    args.append(text[start:].strip())
    return [x for x in args if x]


def recover_vector(text: str) -> list[str]:
    text = strip_comments(text)
    matches = list(re.finditer(r"\.[A-Za-z_]*verify[A-Za-z_]*Proof\s*\(", text, re.I))
    for match in matches:
        call = extract_call(text, match.start())
        if not call:
            continue
        args = top_level_args(call)
        if len(args) < 2:
            continue
        last = args[-1].strip()
        if last.startswith("[") and last.endswith("]"):
            return split_csv(last[1:-1])
        var = re.sub(r"\s.*", "", last).strip()
        if re.fullmatch(r"[A-Za-z_]\w*", var):
            declaration = re.search(
                rf"uint(?:256)?\s*\[\s*(\d+)\s*\]\s*(?:calldata|memory|storage)?\s*{re.escape(var)}\b",
                text,
            )
            if declaration:
                return [f"{var}[{i}]" for i in range(int(declaration.group(1)))]
            assigned: dict[int, str] = {}
            for am in re.finditer(rf"\b{re.escape(var)}\s*\[\s*(\d+)\s*\]\s*=(?!=)\s*([^;]+);", text):
                assigned[int(am.group(1))] = am.group(2).strip()
            if assigned:
                return [assigned[i] for i in range(max(assigned) + 1) if i in assigned]
    return []


def parse_solidity(path: Path, repo_root: Path) -> SolidityFact:
    text = read_text(path)
    lower = text.lower()
    has_verify = bool(re.search(r"function\s+[A-Za-z_]*verify[A-Za-z_]*Proof\s*\(", text, re.I))
    generated_score = sum(marker.lower() in lower for marker in GENERATED_MARKERS)
    external_verify = bool(re.search(r"\b[A-Za-z_]\w*\.[A-Za-z_]*verify[A-Za-z_]*Proof\s*\(", text, re.I))
    effect_matches = re.findall(
        r"[^;\n]*(?:safeTransferFrom|safeTransfer|transferFrom|transfer|_mint|mint|\.call)\s*\([^;]+",
        text,
        re.I,
    )
    effect_roles = sorted({
        word for match in effect_matches for word in ROLE_WORDS
        if re.search(rf"\b{re.escape(word)}\w*\b", match, re.I)
    })
    if any(marker in lower for marker in PLACEHOLDER_MARKERS):
        kind = "placeholder"
    elif has_verify and generated_score >= 2 and not effect_roles:
        kind = "verifier"
    elif external_verify or (has_verify and effect_roles):
        kind = "consumer"
    else:
        kind = "other"

    count = None
    for match in re.finditer(r"function\s+[A-Za-z_]*verify[A-Za-z_]*Proof\s*\((.*?)\)\s*(?:public|external|internal)", text, re.S | re.I):
        params = top_level_args(match.group(1))
        if not params:
            continue
        # snarkjs/arkworks verifier APIs put public inputs last. Proof point
        # arrays earlier in the signature must not be counted as inputs.
        public_param = params[-1]
        fixed = re.search(r"uint(?:256)?\s*\[\s*(\d+)\s*\]", public_param)
        dynamic = re.search(r"uint(?:256)?\s*\[\s*\]", public_param)
        if fixed:
            count = int(fixed.group(1))
        elif dynamic:
            count = None
    canonical = None
    if kind == "verifier":
        modulus = "21888242871839275222246405745257275088548364400416034343698204186575808495617"
        canonical = bool(
            ("SNARK_SCALAR_FIELD" in text or modulus in text or re.search(r"\bconstant\s+r\s*=", text))
            and (re.search(r"\blt\s*\(", text) or re.search(r">=\s*(?:SNARK_SCALAR_FIELD|r\b)", text))
        )

    vector = recover_vector(text) if kind == "consumer" else []
    nullifier = any(word in lower for word in NULLIFIER_WORDS)
    replay_read = bool(re.search(r"(?:require|if)\s*\([^;\n]*(?:spent|nullifier|used)", text, re.I))
    replay_write = bool(re.search(r"(?:spent|nullifier|used)\w*\s*\[[^\]]+\]\s*=\s*(?:true|1)", text, re.I))
    return SolidityFact(
        str(path.relative_to(repo_root)), kind, count, canonical, vector,
        len(vector) if vector else None, effect_roles, nullifier, replay_read, replay_write,
    )


def normalized(value: str) -> str:
    value = re.sub(r"\b(?:uint\d*|bytes\d*|address)\s*\(", "", value)
    return re.sub(r"[^a-z0-9]", "", value.lower())


def name_match(a: str, b: str) -> bool:
    na, nb = normalized(a), normalized(b)
    if not na or not nb:
        return False
    return na == nb or (min(len(na), len(nb)) >= 3 and (na.endswith(nb) or nb.endswith(na)))


def score_pair(circuit: CircuitFact, consumer: SolidityFact, verifier: SolidityFact | None) -> int:
    score = 0
    if circuit.signal_count is not None and consumer.verify_vector_count is not None:
        score += 6 if circuit.signal_count == consumer.verify_vector_count else -3
    if verifier and circuit.signal_count is not None and verifier.verifier_input_count is not None:
        score += 4 if circuit.signal_count == verifier.verifier_input_count else -2
    stem_tokens = set(re.findall(r"[a-z0-9]+", Path(circuit.path).stem.lower()))
    path_tokens = set(re.findall(r"[a-z0-9]+", consumer.path.lower()))
    score += len(stem_tokens & path_tokens)
    score += 2 * sum(
        any(name_match(signal, expr) for expr in consumer.verify_vector)
        for signal in circuit.public_signals
    )
    score += 2 if consumer.replay_write else 0
    score += len(consumer.effect_roles)
    return score


def analyze_repo(repository: str, provenance: str, repo_root: Path) -> Candidate:
    limitations: list[str] = []
    try:
        commit = run("git", "rev-parse", "HEAD", cwd=repo_root)
    except Exception:
        commit = None
    excluded = {".git", "node_modules", "vendor", "cache", "artifacts", "build", "out"}
    circuit_paths = sorted(
        p for p in repo_root.rglob("*.circom")
        if not (excluded & set(p.parts)) and p.stat().st_size <= 2_000_000
    )
    sol_paths = sorted(
        p for p in repo_root.rglob("*.sol")
        if not (excluded & set(p.parts))
        and not ({"test", "tests", "lib"} & set(p.parts))
        and not p.name.endswith(".t.sol")
        and p.stat().st_size <= 2_000_000
    )
    circuits = [parse_circuit(p, repo_root) for p in circuit_paths]
    solids = [parse_solidity(p, repo_root) for p in sol_paths]
    verifiers = [x for x in solids if x.kind == "verifier"]
    consumers = [x for x in solids if x.kind == "consumer"]
    parsed_circuits = [x for x in circuits if x.main_template]

    if not circuit_paths or not sol_paths:
        return Candidate(
            repository, commit, provenance, "ineligible-missing-layer",
            circuit_paths[0].relative_to(repo_root).as_posix() if circuit_paths else None,
            verifiers[0].path if verifiers else None,
            consumers[0].path if consumers else None, [], None, [],
            {"A": [], "B": [], "C": []}, "E0", "UNKNOWN",
            [f"circom_files={len(circuit_paths)}", f"solidity_files={len(sol_paths)}"],
        )
    if not parsed_circuits or not verifiers or not consumers:
        limitations.extend([
            f"parsed_main={len(parsed_circuits)}", f"verifiers={len(verifiers)}",
            f"consumers={len(consumers)}",
        ])
        circuit = parsed_circuits[0] if parsed_circuits else circuits[0]
        # Keep the best available paths for corpus accounting even when strict
        # classification cannot establish a pair. These rows stay UNKNOWN.
        verifier_fallback = verifiers[0] if verifiers else next(
            (x for x in solids if "verifier" in Path(x.path).stem.lower()), None
        )
        consumer_fallback = consumers[0] if consumers else next(
            (
                x for x in solids
                if x.path != (verifier_fallback.path if verifier_fallback else "")
                and any(token in x.path.lower() for token in ("contract", "pool", "mixer", "withdraw", "app"))
            ),
            None,
        )
        return Candidate(
            repository, commit, provenance, "unresolved-pairing",
            circuit.path, verifier_fallback.path if verifier_fallback else None,
            consumer_fallback.path if consumer_fallback else None, circuit.public_signals,
            verifier_fallback.verifier_input_count if verifier_fallback else None,
            consumer_fallback.verify_vector if consumer_fallback else [],
            {"A": [], "B": [], "C": []}, "E0", "UNKNOWN", limitations,
        )

    ranked: list[tuple[int, CircuitFact, SolidityFact, SolidityFact | None]] = []
    for circuit in parsed_circuits:
        for consumer in consumers:
            best_verifier = max(verifiers, key=lambda v: score_pair(circuit, consumer, v))
            ranked.append((score_pair(circuit, consumer, best_verifier), circuit, consumer, best_verifier))
    ranked.sort(key=lambda x: x[0], reverse=True)
    _, circuit, consumer, verifier = ranked[0]

    circuit_tokens = set(re.findall(r"[a-z0-9]+", Path(circuit.path).stem.lower()))
    consumer_tokens = set(re.findall(r"[a-z0-9]+", consumer.path.lower()))
    circuit_tokens -= {"circuit", "circuits", "main", "verify", "verifier"}
    semantic_matches = sum(
        any(name_match(signal, expr) for expr in consumer.verify_vector)
        for signal in circuit.public_signals
    )
    if not (circuit_tokens & consumer_tokens) and semantic_matches < 2:
        limitations.append(
            f"pair-confidence-insufficient: path_overlap=0; signal_matches={semantic_matches}"
        )
        return Candidate(
            repository, commit, provenance, "unresolved-pairing", circuit.path,
            verifier.path if verifier else None, consumer.path, circuit.public_signals,
            verifier.verifier_input_count if verifier else None, consumer.verify_vector,
            {"A": [], "B": [], "C": []}, "E0", "UNKNOWN", limitations,
        )

    checks: dict[str, list[str]] = {"A": [], "B": [], "C": []}
    for i, expr in enumerate(consumer.verify_vector):
        if i >= len(circuit.public_signals):
            continue
        signal = circuit.public_signals[i]
        if not any(word in normalized(expr) for word in ROLE_WORDS):
            continue
        binding = circuit.binding.get(signal)
        if binding in {"witness-only", "no-constraint-reference"}:
            checks["A"].append(
                f"public[{i}] {signal} -> {expr}; circuit binding={binding}; effects={','.join(consumer.effect_roles) or 'role-use-only'}"
            )

    nullifier_positions = [
        i for i, value in enumerate(consumer.verify_vector)
        if any(word in normalized(value) for word in NULLIFIER_WORDS)
    ]
    if nullifier_positions:
        if not (consumer.replay_read and consumer.replay_write):
            checks["B"].append(
                f"nullifier public positions {nullifier_positions}; spent read={consumer.replay_read}; write={consumer.replay_write}"
            )
        if verifier and verifier.canonical_public_inputs is False and (consumer.replay_read or consumer.replay_write):
            checks["B"].append(
                "nullifier stored/compared but verifier canonical public-input check was not detected"
            )

    counts = {
        "circuit": circuit.signal_count,
        "verifier": verifier.verifier_input_count if verifier else None,
        "consumer": consumer.verify_vector_count,
    }
    known_counts = {v for v in counts.values() if v is not None}
    if len(known_counts) > 1:
        checks["C"].append(f"public-input count mismatch: {counts}")
    if (
        len(circuit.public_signals) == len(consumer.verify_vector)
        and len(circuit.public_signals) > 1
    ):
        direct = sum(name_match(a, b) for a, b in zip(circuit.public_signals, consumer.verify_vector))
        cross = sum(any(name_match(a, b) for b in consumer.verify_vector) for a in circuit.public_signals)
        if direct > 0 and cross >= 2 and direct < cross and (circuit_tokens & consumer_tokens):
            checks["C"].append(
                f"possible order mismatch: direct-name-matches={direct}, set-name-matches={cross}"
            )

    hits = sum(len(x) for x in checks.values())
    if circuit.parse_notes:
        limitations.extend(circuit.parse_notes)
    limitations.append("source-only lexical analysis; compiled R1CS/solc AST not yet checked")
    return Candidate(
        repository, commit, provenance, "source-pair",
        circuit.path, verifier.path if verifier else None, consumer.path,
        circuit.public_signals, verifier.verifier_input_count if verifier else None,
        consumer.verify_vector, checks, "E1" if hits else "E0", "UNKNOWN", limitations,
    )


def load_seeds(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            repo, provenance = line.rstrip("\n").split("\t", 1)
            if (repo, provenance) not in rows:
                rows.append((repo, provenance))
    return rows


def write_outputs(candidates: Iterable[Candidate], output_json: Path, output_csv: Path) -> None:
    data = [asdict(x) for x in candidates]
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "repository", "commit", "eligibility", "circuit", "verifier", "consumer",
            "public_signals", "check_A", "check_B", "check_C", "evidence_grade", "verdict",
        ])
        for item in data:
            writer.writerow([
                item["repository"], item["commit"], item["eligibility"], item["circuit"],
                item["verifier"], item["consumer"], json.dumps(item["public_signals"]),
                " | ".join(item["checks"]["A"]), " | ".join(item["checks"]["B"]),
                " | ".join(item["checks"]["C"]), item["evidence_grade"], item["verdict"],
            ])


def main() -> int:
    parser = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    parser.add_argument("--seeds", type=Path, default=here / "candidate-seeds.tsv")
    parser.add_argument("--repos", type=Path, default=here / "work" / "repos")
    parser.add_argument("--json", type=Path, default=here / "raw" / "candidates.json")
    parser.add_argument("--csv", type=Path, default=here / "candidates.csv")
    args = parser.parse_args()

    candidates: list[Candidate] = []
    for repository, provenance in load_seeds(args.seeds):
        repo_root = args.repos / repository.replace("/", "_")
        if not (repo_root / ".git").exists():
            candidates.append(Candidate(
                repository, None, provenance, "fetch-failed", None, None, None, [], None, [],
                {"A": [], "B": [], "C": []}, "E0", "UNKNOWN", ["repository not fetched"],
            ))
            continue
        candidates.append(analyze_repo(repository, provenance, repo_root))
    write_outputs(candidates, args.json, args.csv)
    print(json.dumps({
        "candidates": len(candidates),
        "source_pairs": sum(x.eligibility == "source-pair" for x in candidates),
        "hits_A": sum(bool(x.checks["A"]) for x in candidates),
        "hits_B": sum(bool(x.checks["B"]) for x in candidates),
        "hits_C": sum(bool(x.checks["C"]) for x in candidates),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

