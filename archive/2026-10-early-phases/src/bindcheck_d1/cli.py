"""Command-line entry point for the integrated BindCheck development tool."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from .integrated_analyzer_v1 import analyze_integrated, readable as readable_integrated
from .static_analyzer_v1 import analyze as analyze_static, readable as readable_static
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
    analyze_parser.add_argument(
        "--producer-source", type=Path,
        help="Noir semantic source used for extent and typed-role facts",
    )
    analyze_parser.add_argument(
        "--producer-support-source", type=Path, action="append", default=[],
        help="support source declaring producer semantic operations (repeatable)",
    )
    analyze_parser.add_argument(
        "--mapping-bridge", type=Path,
        help="recursive verifier/configuration artifact required by an exact mapping certificate",
    )
    analyze_parser.add_argument(
        "--no-role-binding", action="store_true",
        help="intentionally disable R-ROLE even when a producer source is supplied",
    )
    analyze_parser.add_argument(
        "--integrated", action="store_true",
        help="emit the integrated support/provenance schema even without integration inputs",
    )
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
            integrated = bool(
                args.integrated
                or args.producer_source
                or args.producer_support_source
                or args.mapping_bridge
                or args.no_role_binding
            )
            if integrated:
                result = analyze_integrated(
                    args.producer_artifact,
                    args.consumer_source,
                    consumer_ir,
                    args.label,
                    producer_source=args.producer_source,
                    producer_support_sources=args.producer_support_source,
                    mapping_bridge=args.mapping_bridge,
                    role_binding=False if args.no_role_binding else None,
                )
                rendered = readable_integrated(result)
                exit_code = 0 if result["support_status"] == "SUPPORTED" else 2
            else:
                result = analyze_static(
                    args.producer_artifact,
                    args.consumer_source,
                    consumer_ir,
                    args.label,
                )
                rendered = readable_static(result)
                exit_code = 0
            _write_json(args.json, result)
            print(json.dumps(result, indent=2, sort_keys=True) if args.json_stdout else rendered)
            return exit_code
        result = validate(args.warning, args.validation_index, args.repository.resolve())
        _write_json(args.json, result)
        print(json.dumps(result, indent=2, sort_keys=True) if args.json_stdout else readable_validation(result))
        return 0 if result["status"] == "PASS" else 2
    except Exception as exc:  # fail closed with a stable CLI diagnostic
        print(f"bindcheck: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
