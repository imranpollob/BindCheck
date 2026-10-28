"""BindCheck v1 cross-layer static analyzer.

The rule engine is deliberately application-neutral.  It joins flattened
producer ABI leaves and ACIR witness use with either an extracted consumer
relation or a conservative Solidity source profile.  Target-specific paths
are inputs to the CLI, never conditions in these rules.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any

from .frontends import acir_binary_beta22, acir_binary_v1


SCHEMA = "bindcheck.static-analysis.v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expression_witnesses(expr: dict[str, Any]) -> list[int]:
    result: list[int] = []
    for _coefficient, lhs, rhs in expr.get("mul", []):
        result.extend((lhs, rhs))
    for _coefficient, witness in expr.get("linear", []):
        result.append(witness)
    return result


def _nested_witnesses(value: Any) -> list[int]:
    result: list[int] = []
    if isinstance(value, dict):
        if set(value) == {"witness"}:
            result.append(value["witness"])
        for child in value.values():
            result.extend(_nested_witnesses(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(_nested_witnesses(child))
    return result


def _leaf_bindings(abi: dict[str, Any], bindings: dict[str, list[int]]) -> list[dict[str, Any]]:
    """Return scalar ABI paths in declaration order."""
    leaves: list[dict[str, Any]] = []

    def visit(typ: dict[str, Any], name: str, visibility: str) -> None:
        kind = typ["kind"]
        if kind in {"field", "integer", "boolean"}:
            leaves.append({"path": name, "visibility": visibility, "witness": bindings[name][0]})
        elif kind == "array":
            for index in range(typ["length"]):
                visit(typ["type"], f"{name}[{index}]", visibility)
        elif kind == "struct":
            for field in typ["fields"]:
                visit(field["type"], f"{name}.{field['name']}", visibility)
        else:
            raise ValueError(f"unsupported ABI type after decoder gate: {kind}")

    for parameter in abi["parameters"]:
        visit(parameter["type"], parameter["name"], parameter["visibility"])
    return leaves


def load_producer(path: Path) -> dict[str, Any]:
    artifact = json.loads(path.read_text())
    version = artifact.get("noir_version", "")
    if version == acir_binary_beta22.VERSION:
        decoder = acir_binary_beta22
        decoder_name = "beta.22-msgpack"
    elif version == acir_binary_v1.VERSION:
        decoder = acir_binary_v1
        decoder_name = "beta.14-bincode"
    else:
        raise ValueError(f"unsupported Noir compiler: {version!r}")

    decoded = decoder.decode(path)
    circuit = decoded["functions"][0]
    bindings = decoder.abi_bindings(decoded["abi"], circuit)
    occurrences: Counter[int] = Counter()
    locations: dict[int, list[str]] = {}
    kinds: Counter[str] = Counter()
    for ordinal, opcode in enumerate(circuit["opcodes"]):
        kind = opcode["kind"]
        kinds[kind] += 1
        witnesses = (_expression_witnesses(opcode["expression"])
                     if kind == "AssertZero" else _nested_witnesses(opcode))
        for witness in witnesses:
            occurrences[witness] += 1
            if len(locations.setdefault(witness, [])) < 8:
                locations[witness].append(f"opcode[{opcode.get('opcode_index', ordinal)}]/{kind}")

    leaves = _leaf_bindings(decoded["abi"], bindings)
    public_leaves = []
    for public_index, leaf in enumerate(item for item in leaves if item["visibility"] == "public"):
        leaf = dict(leaf)
        leaf.update({
            "public_index": public_index,
            "occurrence_count": occurrences[leaf["witness"]],
            "occurrence_locations": locations.get(leaf["witness"], []),
        })
        public_leaves.append(leaf)
    return {
        "path": str(path.resolve()),
        "sha256": sha256(path),
        "noir_version": version,
        "decoder": decoder_name,
        "opcode_count": len(circuit["opcodes"]),
        "opcode_counts": dict(sorted(kinds.items())),
        "public_leaves": public_leaves,
        "public_witnesses": circuit["public_parameters"],
    }


def _line_for(source: Path, pattern: str) -> int | None:
    regex = re.compile(pattern)
    for number, line in enumerate(source.read_text().splitlines(), 1):
        if regex.search(line):
            return number
    return None


def _symbols(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        if value.get("op") == "symbol" and value.get("args"):
            result.add(str(value["args"][0]))
        for child in value.values():
            result.update(_symbols(child))
    elif isinstance(value, list):
        for child in value:
            result.update(_symbols(child))
    return result


def load_relation_consumer(source: Path, relation_path: Path, public_count: int) -> dict[str, Any]:
    relation = json.loads(relation_path.read_text())
    boundary = relation["verifier_boundary"]
    words = boundary["public_words"]
    if len(words) != public_count:
        raise ValueError(
            f"consumer/producer public-width mismatch: consumer {len(words)}, producer {public_count}"
        )
    success = [path for path in relation["paths"] if path["status"] == "success"]
    effects: list[dict[str, Any]] = []
    effect_origins: set[str] = set()
    for path in success:
        committed = path["committed"]
        for kind in ("mints", "burns", "transfers"):
            for effect in committed.get(kind, []):
                record = {"kind": kind[:-1], "location": effect.get("location"), "raw": effect}
                effects.append(record)
                effect_origins.update(_symbols(effect))

    anchor_words = []
    for word, producer_hint in zip(words, range(public_count)):
        origin = word["origin"]
        if "root" not in origin.lower():
            continue
        positive = all(any(
            origin in guard and "select(pre." in guard and not guard.startswith("not(")
            for guard in path["guards"]
        ) for path in success)
        anchor_words.append({
            "public_index": producer_hint,
            "origin": origin,
            "must_be_in": positive,
            "evidence": sorted({guard for path in success for guard in path["guards"] if origin in guard}),
        })

    nullifier_words = [word for word in words if "nullifier" in word["origin"].lower()]
    replay = {"applicable": bool(nullifier_words), "must_not_be_in": False, "written": False, "evidence": []}
    for word in nullifier_words:
        origin = word["origin"]
        replay["must_not_be_in"] = all(any(
            origin in guard and "select(pre." in guard and ("== false" in guard or "not(select" in guard)
            for guard in path["guards"]
        ) for path in success)
        writes = [write for path in success for write in path["committed"].get("storage_writes", [])
                  if origin in str(write.get("key", ""))]
        replay["written"] = bool(writes)
        replay["evidence"] = [write.get("location") for write in writes]

    effect_word_indices = sorted({
        word["index"] for word in words
        if word["origin"] in effect_origins
    })
    return {
        "kind": "extracted-relation",
        "source": str(source.resolve()),
        "source_sha256": sha256(source),
        "relation": str(relation_path.resolve()),
        "relation_sha256": sha256(relation_path),
        "relation_schema": relation.get("schema"),
        "scope": relation.get("scope"),
        "verifier_location": f"{source.name}:{_line_for(source, r'withdrawVerifier.*\.verify') or '?'}",
        "public_words": words,
        "anchor_words": anchor_words,
        "effect_word_indices": effect_word_indices,
        "effects": effects,
        "replay": replay,
        "limitations": [],
    }


def load_source_consumer(source: Path, public_leaves: list[dict[str, Any]]) -> dict[str, Any]:
    """Conservative source-only profile for array-oriented Solidity verifiers.

    This scanner identifies behavior from syntax and ABI names.  It does not
    pretend to be a Solidity semantic extractor; unsupported shapes are
    reported rather than guessed.
    """
    text = source.read_text()
    messages = [leaf for leaf in public_leaves if re.fullmatch(r"messages\[\d+\]", leaf["path"])]
    has_message_dispatch = bool(re.search(r"function\s+verifyMessages\b", text))
    has_effect = bool(re.search(r"function\s+verify(?:Mint|Burn)\b", text))
    effect_indices = [leaf["public_index"] for leaf in messages] if has_message_dispatch and has_effect else []
    # Source-only mode has no semantic producer roles.  Restrict the anchor
    # candidate to names whose direction is explicit; e.g. ``new_root`` is a
    # transition output, not a pre-state membership obligation.
    roots = [leaf for leaf in public_leaves
             if "root" in leaf["path"].lower()
             and any(role in leaf["path"].lower() for role in ("old", "current", "previous"))]
    anchor_words = []
    for leaf in roots:
        name = leaf["path"].split(".")[-1]
        variants = {name, re.sub(r"_([a-z])", lambda m: m.group(1).upper(), name)}
        matched = any(re.search(rf"\b{re.escape(candidate)}\b\s*==\s*\b\w*[Rr]oot\w*", text)
                      or re.search(rf"\b\w*[Rr]oot\w*\s*==\s*\b{re.escape(candidate)}\b", text)
                      for candidate in variants)
        # A local alias is common (bytes32 oldRoot = publicInputs[0]).
        if name == "old_root" and re.search(r"verifyRootHash\s*\(\s*oldRoot\s*\)", text):
            matched = True
        anchor_words.append({
            "public_index": leaf["public_index"], "origin": leaf["path"],
            "must_be_in": matched,
            "evidence": [f"{source.name}:{_line_for(source, r'function\s+verifyRootHash') or '?'}"] if matched else [],
        })

    verifier_line = (_line_for(source, r"\.verifier\.verify\s*\(")
                     or _line_for(source, r"\.verify\s*\("))
    limitations = []
    if not messages:
        limitations.append("SOURCE_PROFILE_NO_PUBLIC_MESSAGE_ARRAY")
    if not has_message_dispatch:
        limitations.append("SOURCE_PROFILE_NO_MESSAGE_DISPATCH")
    replay_applicable = bool(re.search(r"\.spent\s*==\s*false", text))
    replay_written = bool(re.search(r"\.spent\s*=\s*true", text))
    return {
        "kind": "conservative-source-profile",
        "source": str(source.resolve()),
        "source_sha256": sha256(source),
        "relation": None,
        "scope": "source-detected verifier call and committed message effects",
        "verifier_location": f"{source.name}:{verifier_line or '?'}",
        "public_words": [{"index": leaf["public_index"], "origin": leaf["path"]} for leaf in public_leaves],
        "anchor_words": anchor_words,
        "effect_word_indices": effect_indices,
        "effects": ([{"kind": "message-dispatched mint/burn", "location": f"{source.name}:"
                      f"{_line_for(source, r'function\s+verifyMessages') or '?'}"}]
                    if effect_indices else []),
        "replay": {
            "applicable": replay_applicable,
            "must_not_be_in": replay_applicable,
            "written": replay_written,
            "evidence": [f"{source.name}:{_line_for(source, r'\.spent\s*=\s*true') or '?'}"] if replay_written else [],
        },
        "limitations": limitations + ["SOURCE_PROFILE_IS_NOT_FULL_SOLIDITY_SEMANTICS"],
    }


def _ranges(leaves: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Group adjacent array leaves while leaving scalars separate."""
    groups: list[list[dict[str, Any]]] = []
    for leaf in leaves:
        base = re.sub(r"\[\d+\]$", "", leaf["path"])
        if groups:
            previous = groups[-1][-1]
            previous_base = re.sub(r"\[\d+\]$", "", previous["path"])
            if (base == previous_base and "[" in leaf["path"]
                    and leaf["public_index"] == previous["public_index"] + 1):
                groups[-1].append(leaf)
                continue
        groups.append([leaf])
    return groups


def analyze(artifact_path: Path, source_path: Path, relation_path: Path | None = None,
            label: str | None = None) -> dict[str, Any]:
    started = time.monotonic()
    producer = load_producer(artifact_path)
    consumer = (load_relation_consumer(source_path, relation_path, len(producer["public_leaves"]))
                if relation_path else load_source_consumer(source_path, producer["public_leaves"]))
    warnings: list[dict[str, Any]] = []

    def warning(rule: str, location: str, explanation: str, suggested_fix: str,
                evidence: dict[str, Any], confidence: str = "high") -> None:
        warnings.append({
            "id": f"W{len(warnings) + 1:03d}", "rule": rule,
            "severity": "warning", "confidence": confidence,
            "location": location, "explanation": explanation,
            "suggested_fix": suggested_fix, "evidence": evidence,
        })

    unused = [leaf for leaf in producer["public_leaves"] if leaf["occurrence_count"] == 0]
    for group in _ranges(unused):
        paths = [leaf["path"] for leaf in group]
        indices = [leaf["public_index"] for leaf in group]
        witnesses = [leaf["witness"] for leaf in group]
        label_paths = paths[0] if len(paths) == 1 else f"{paths[0]}..{paths[-1]}"
        warning(
            "R-BIND",
            f"{artifact_path.name}:abi.{label_paths}",
            f"Consumer-constructed verifier argument(s) {label_paths} have no occurrence in the decoded "
            "proof-enforced ACIR. Their values can vary without directly constraining the producer relation.",
            "Constrain every exposed verifier argument in the producer, or remove it from the consumer-visible "
            "effect surface; rebuild the artifact, key, and verifier together.",
            {"public_indices": indices, "witnesses": witnesses, "occurrence_counts": [0] * len(group)},
        )

    unused_indices = {leaf["public_index"] for leaf in unused}
    vulnerable_effect = sorted(unused_indices.intersection(consumer["effect_word_indices"]))
    if vulnerable_effect:
        effect_leaves = [producer["public_leaves"][index] for index in vulnerable_effect]
        warning(
            "R-EFFECT",
            consumer["effects"][0]["location"] if consumer["effects"] else consumer["verifier_location"],
            "The consumer interprets producer public words as effect amount, beneficiary, or message data, but "
            "one or more of those words are absent from all proof-enforced ACIR opcodes.",
            "Bind every effect-decoded public word in the producer and keep the consumer effect derived only from "
            "those bound public inputs.",
            {"public_indices": vulnerable_effect, "paths": [leaf["path"] for leaf in effect_leaves],
             "effect_kinds": sorted({effect["kind"] for effect in consumer["effects"]})},
        )

    for anchor in consumer["anchor_words"]:
        if not anchor["must_be_in"]:
            leaf = producer["public_leaves"][anchor["public_index"]]
            warning(
                "R-ANCHOR",
                consumer["verifier_location"],
                f"Producer anchor {leaf['path']} (consumer origin {anchor['origin']}) is proof-visible but no "
                "must-be-in check against consumer chain state was found on every successful path.",
                "Before accepting the proof, require this root/anchor to be admitted by the appropriate on-chain "
                "history or current-state mapping.",
                {"public_index": anchor["public_index"], "path": leaf["path"],
                 "polarity": "must-be-in", "observed_guard_evidence": anchor["evidence"]},
            )

    replay = consumer["replay"]
    if replay["applicable"] and (not replay["must_not_be_in"] or not replay["written"]):
        missing = []
        if not replay["must_not_be_in"]:
            missing.append("pre-state must-not-be-in guard")
        if not replay["written"]:
            missing.append("successful nullifier/spent-key write")
        warning(
            "R-POLARITY",
            consumer["verifier_location"],
            "Replay protection is incomplete across two transactions: missing " + " and ".join(missing) + ".",
            "Check the replay key is absent before verification and write the same key atomically on success.",
            {"polarity": "must-not-be-in", "guard": replay["must_not_be_in"],
             "write": replay["written"], "evidence": replay["evidence"]},
        )

    for item in warnings:
        item["target_identity"] = {
            "artifact_sha256": producer["sha256"], "consumer_sha256": consumer["source_sha256"],
            "rule": item["rule"],
        }
    elapsed = time.monotonic() - started
    return {
        "schema": SCHEMA,
        "generated_at_utc": utc_now(),
        "target": label or f"{artifact_path.stem}+{source_path.name}",
        "producer": producer,
        "consumer": consumer,
        "rules": {
            "R-BIND": "consumer-constructed verifier arguments occur in proof-enforced producer opcodes",
            "R-ANCHOR": "producer roots/anchors have must-be-in consumer state checks",
            "R-EFFECT": "effect amount/beneficiary/message words are producer-bound public inputs",
            "R-POLARITY": "anchors are must-be-in; replay keys are must-not-be-in and written on success",
        },
        "polarity": {"anchors": consumer["anchor_words"], "replay": replay},
        "warnings": warnings,
        "warning_count": len(warnings),
        "manual_inputs": ([{"kind": "checked_consumer_relation", "path": consumer["relation"]}]
                          if consumer["relation"] else []),
        "limitations": consumer["limitations"] + [
            "ACIR occurrence establishes syntactic proof-enforced use, not cryptographic injectivity or intent",
            "Brillig is inventoried as witness-generation machinery; it does not by itself discharge a binding",
            "single-target analysis uses no reference-version oracle",
        ],
        "runtime_seconds": round(elapsed, 6),
    }


def readable(result: dict[str, Any]) -> str:
    lines = [f"BindCheck v1: {result['target']}",
             f"  producer: {result['producer']['sha256']} ({result['producer']['decoder']})",
             f"  consumer: {result['consumer']['source_sha256']} ({result['consumer']['kind']})",
             f"  warnings: {result['warning_count']}  runtime: {result['runtime_seconds']:.3f}s"]
    for warning in result["warnings"]:
        lines.extend([
            "",
            f"{warning['id']} {warning['rule']} at {warning['location']}",
            f"  {warning['explanation']}",
            f"  Fix: {warning['suggested_fix']}",
        ])
    if not result["warnings"]:
        lines.append("  No warning in the supported static scope.")
    return "\n".join(lines)
