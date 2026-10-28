"""Command-line entry point for BindCheck v1.1."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from .static_analyzer_v1 import analyze, readable as readable_analysis
from .validation_v1 import validate, readable as readable_validation


REPOSITORY = Path(__file__).resolve().parents[2]
DEFAULT_CONSUMER_INDEX = REPOSITORY / "protocols/d1/d1p-30-consumer-relations.json"


def resolve_consumer_ir(source: Path, explicit: Path | None, index_path: Path) -> Path | None:
    if explicit is not None:
        return explicit
    if not index_path.is_file():
        return None
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    index = json.loads(index_path.read_text())
    matches = [entry for entry in index["relations"] if entry["consumer_sha256"] == source_hash]
    if len(matches) > 1:
        raise ValueError(f"consumer relation index is ambiguous for {source_hash}")
    if not matches:
        return None
    relation = Path(matches[0]["relation"])
    relation = relation if relation.is_absolute() else REPOSITORY / relation
    if not relation.is_file():
        raise ValueError(f"indexed consumer relation is missing: {relation}")
    observed = hashlib.sha256(relation.read_bytes()).hexdigest()
    if observed != matches[0]["relation_sha256"]:
        raise ValueError(f"indexed consumer relation hash mismatch: {relation}")
    return relation


def _write_json(path: Path | None, value: dict) -> None:
    text = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="bindcheck")
    sub = result.add_subparsers(dest="command", required=True)
    analyze_parser = sub.add_parser("analyze", help="analyze one producer and consumer")
    analyze_parser.add_argument("producer_artifact", type=Path)
    analyze_parser.add_argument("consumer_source", type=Path)
    analyze_parser.add_argument("--consumer-ir", type=Path,
                                help="checked compiler-AST consumer relation (or content-indexed relation)")
    analyze_parser.add_argument("--consumer-index", type=Path, default=DEFAULT_CONSUMER_INDEX,
                                help="content-addressed checked-relation index")
    analyze_parser.add_argument("--label")
    analyze_parser.add_argument("--json", type=Path, help="write machine-readable result")
    analyze_parser.add_argument("--json-stdout", action="store_true")

    validate_parser = sub.add_parser("validate", help="validate a warning through the evidence ladder")
    validate_parser.add_argument("warning", help="analysis.json[#WNNN] or standalone warning JSON")
    validate_parser.add_argument("--validation-index", type=Path,
                                 default=Path("protocols/d1/d1p-30-validation-index.json"))
    validate_parser.add_argument("--repository", type=Path, default=Path.cwd())
    validate_parser.add_argument("--json", type=Path, help="write machine-readable result")
    validate_parser.add_argument("--json-stdout", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "analyze":
            consumer_ir = resolve_consumer_ir(args.consumer_source, args.consumer_ir, args.consumer_index)
            result = analyze(args.producer_artifact, args.consumer_source, consumer_ir, args.label)
            _write_json(args.json, result)
            print(json.dumps(result, indent=2, sort_keys=True) if args.json_stdout else readable_analysis(result))
            return 0
        result = validate(args.warning, args.validation_index, args.repository.resolve())
        _write_json(args.json, result)
        print(json.dumps(result, indent=2, sort_keys=True) if args.json_stdout else readable_validation(result))
        return 0 if result["status"] == "PASS" else 2
    except Exception as exc:  # fail closed with a stable CLI diagnostic
        print(f"bindcheck: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
