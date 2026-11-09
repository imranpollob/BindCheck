from __future__ import annotations

import dataclasses
import pathlib
import re
from typing import Any, Iterator

from ..solidity import (
    Function,
    PublicVector,
    balanced,
    effect_calls,
    functions,
    identifiers,
    mask_comments_and_strings,
    normalize_expression,
    public_vector,
    verification_calls,
)


@dataclasses.dataclass
class ConsumerPath:
    path: pathlib.Path
    relative_path: str
    source: str
    function: Function
    vector: PublicVector


def consumer_paths(root: pathlib.Path, paths: list[pathlib.Path]) -> list[ConsumerPath]:
    output: list[ConsumerPath] = []
    for path in paths:
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for function in functions(source):
            calls = verification_calls(function.body)
            if len(calls) != 1:
                continue
            output.append(ConsumerPath(
                path=path,
                relative_path=path.relative_to(root).as_posix(),
                source=source,
                function=function,
                vector=public_vector(function.body, calls[0]),
            ))
    return output


def canonical_identifier(expression: str) -> str | None:
    expression = normalize_expression(expression)
    names = [name for name in identifiers(expression) if name.lower() not in {
        "proof", "input", "inputs", "publicsignals", "uint160", "uint256",
    }]
    return names[-1] if names else None


def normalized_public_name(value: str) -> str:
    return re.sub(r"^main\.", "", value).replace(" ", "")


def vector_names(vector: PublicVector) -> list[str | None]:
    return [canonical_identifier(item) for item in vector.items]


def _array_declarations(source: str) -> dict[str, int]:
    return {
        name: int(size)
        for name, size in re.findall(
            r"\bsignal\s+(?:input|output)\s+([A-Za-z_]\w*)\s*\[\s*(\d+)\s*\]\s*;",
            source,
        )
    }


def conditional_array(source: str) -> dict[str, Any] | None:
    """Recover a bounded selector*(public-private)==0 enforcement template."""

    compact = mask_comments_and_strings(source)
    pattern = re.compile(
        r"(?P<selector>[A-Za-z_]\w*)\s*\[\s*(?P<index>[A-Za-z_]\w*)\s*\]\s*\*\s*\(\s*"
        r"(?P<values>[A-Za-z_]\w*)\s*\[\s*(?P=index)\s*\]\s*-\s*"
        r"(?P<witness>[A-Za-z_]\w*)\s*\[\s*(?P=index)\s*\]\s*\)\s*===\s*0\s*;"
    )
    match = pattern.search(compact)
    if match is None:
        return None
    arrays = _array_declarations(compact)
    selector, values = match.group("selector"), match.group("values")
    count = arrays.get(selector)
    if count is None or arrays.get(values) != count:
        return None
    extent_signal = None
    for candidate, expression in re.findall(r"\b([A-Za-z_]\w*)\s*===\s*([^;]+);", compact):
        selected = {int(index) for name, index in re.findall(r"([A-Za-z_]\w*)\[(\d+)\]", expression) if name == selector}
        if selected == set(range(count)) and "+" in expression:
            extent_signal = candidate
            break
    prefix = bool(re.search(
        rf"\b{re.escape(selector)}\s*\[\s*{re.escape(match.group('index'))}\s*\+\s*1\s*\]\s*\*\s*"
        rf"\(\s*1\s*-\s*{re.escape(selector)}\s*\[\s*{re.escape(match.group('index'))}\s*\]\s*\)\s*===\s*0",
        compact,
    ))
    return {
        "selector": selector,
        "values": values,
        "witness": match.group("witness"),
        "index": match.group("index"),
        "count": count,
        "extent_signal": extent_signal if prefix else None,
        "prefix_enforced": bool(extent_signal and prefix),
    }


def _loops(body: str) -> Iterator[tuple[str, str, str]]:
    masked = mask_comments_and_strings(body)
    pattern = re.compile(
        r"\bfor\s*\(\s*[^;]*\b([A-Za-z_]\w*)\s*=\s*0\s*;\s*\1\s*<\s*([^;]+);[^)]*\)\s*\{"
    )
    for match in pattern.finditer(masked):
        opening = masked.find("{", match.start())
        parsed = balanced(masked, opening, "{", "}")
        if parsed is not None:
            yield match.group(1), body[match.start(2):match.end(2)].strip(), body[opening + 1:parsed[1] - 1]


def array_reliance(consumer: ConsumerPath, values: str, selector: str | None = None) -> dict[str, Any] | None:
    for index, bound, loop_body in _loops(consumer.function.body):
        if not re.search(rf"\b{re.escape(values)}\s*\[\s*{re.escape(index)}\s*\]", loop_body):
            continue
        has_effect = bool(effect_calls(loop_body, consumer.source)) or bool(re.search(
            r"\b[A-Za-z_]\w*\s*\[[^;]+\]\s*(?:\+=|-=|=)", loop_body
        ))
        if not has_effect:
            continue
        guarded = False
        if selector:
            guarded = bool(re.search(
                rf"\bif\s*\(\s*{re.escape(selector)}\s*\[\s*{re.escape(index)}\s*\]\s*==\s*1\s*\)",
                loop_body,
            ))
        return {"index": index, "bound": normalize_expression(bound), "guarded_by_selector": guarded}
    return None


def weighted_terms(expression: str) -> tuple[str, dict[int, int]] | None:
    compact = re.sub(r"[()\s]", "", expression)
    terms: dict[int, int] = {}
    array_name: str | None = None
    for raw in compact.split("+"):
        patterns = (
            re.fullmatch(r"(\d+)\*([A-Za-z_]\w*)\[(\d+)\]", raw),
            re.fullmatch(r"([A-Za-z_]\w*)\[(\d+)\]\*(\d+)", raw),
            re.fullmatch(r"([A-Za-z_]\w*)\[(\d+)\]", raw),
        )
        if patterns[0]:
            coefficient, name, index = int(patterns[0].group(1)), patterns[0].group(2), int(patterns[0].group(3))
        elif patterns[1]:
            name, index, coefficient = patterns[1].group(1), int(patterns[1].group(2)), int(patterns[1].group(3))
        elif patterns[2]:
            name, index, coefficient = patterns[2].group(1), int(patterns[2].group(2)), 1
        else:
            continue
        if array_name is not None and name != array_name:
            return None
        array_name = name
        terms[index] = terms.get(index, 0) + coefficient
    return (array_name, terms) if array_name and len(terms) >= 2 else None


def producer_representation(source: str) -> dict[str, Any] | None:
    for left, right in re.findall(r"\b([A-Za-z_]\w*)\s*===\s*([^;]+);", mask_comments_and_strings(source)):
        parsed = weighted_terms(right)
        if parsed is not None:
            array, weights = parsed
            return {"packed": left, "array": array, "weights": weights}
    return None


def consumer_representation(consumer: ConsumerPath, array: str) -> dict[str, Any] | None:
    pattern = re.compile(
        r"\b(?:uint(?:256)?|bytes32)\s+([A-Za-z_]\w*)\s*=\s*([^;]+);"
    )
    for match in pattern.finditer(mask_comments_and_strings(consumer.function.body)):
        parsed = weighted_terms(consumer.function.body[match.start(2):match.end(2)])
        if parsed is None or parsed[0] != array:
            continue
        decoded = match.group(1)
        effects = effect_calls(consumer.function.body, consumer.source)
        if not any(decoded in identifiers(argument) for call in effects for argument in call.args):
            continue
        return {"decoded": decoded, "array": parsed[0], "weights": parsed[1]}
    return None


def nullifier_constraint(source: str) -> dict[str, Any] | None:
    for left, right in re.findall(r"\b([A-Za-z_]\w*nullifier[A-Za-z_]*)\s*===\s*([^;]+);", source, re.I):
        return {"nullifier": left, "expression": right, "dependencies": sorted(identifiers(right))}
    return None


def scoped_replay(consumer: ConsumerPath) -> dict[str, Any] | None:
    body = mask_comments_and_strings(consumer.function.body)
    pattern = re.compile(
        r"\b([A-Za-z_]\w*)\s*"
        r"\[\s*([A-Za-z_]\w*)\s*\]\s*\[\s*([A-Za-z_]\w*nullifier[A-Za-z_]*)\s*\]",
        re.I,
    )
    for match in pattern.finditer(body):
        mapping, scope, nullifier = match.groups()
        if not any(token in mapping.lower() for token in ("claim", "spent", "used", "vote", "withdraw", "redeem")):
            continue
        occurrences = len(list(re.finditer(
            rf"\b{re.escape(mapping)}\s*\[\s*{re.escape(scope)}\s*\]\s*\[\s*{re.escape(nullifier)}\s*\]",
            body,
        )))
        write = bool(re.search(
            rf"\b{re.escape(mapping)}\s*\[\s*{re.escape(scope)}\s*\]\s*\[\s*{re.escape(nullifier)}\s*\]\s*=\s*(?:true|1)",
            body,
        ))
        if occurrences >= 2 and write:
            return {"mapping": mapping, "scope": scope, "nullifier": nullifier, "read": True, "write": True}
    return None


def role(value: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value).lower())
    token_set = set(tokens)
    if {"source", "root"} <= token_set or {"old", "root"} <= token_set:
        return "state-root:source"
    if {"destination", "root"} <= token_set or {"new", "root"} <= token_set:
        return "state-root:destination"
    if {"source", "domain"} <= token_set:
        return "domain:source"
    if {"destination", "domain"} <= token_set:
        return "domain:destination"
    for token in ("owner", "recipient", "sender", "beneficiary"):
        if token in token_set:
            return f"party:{token}"
    if "amount" in token_set or "value" in token_set:
        return "value:amount"
    if "nullifier" in token_set:
        return "replay:nullifier"
    return "unknown"


def source_enforces_identity(source: str, public_name: str) -> bool:
    escaped = re.escape(public_name)
    return bool(re.search(
        rf"(?:\b{escaped}\b\s*===\s*[^;]+|[^;]+\s*===\s*\b{escaped}\b)\s*;",
        mask_comments_and_strings(source),
    ))


def relied_identifier(consumer: ConsumerPath, name: str) -> bool:
    # One occurrence can be the verifier vector itself.  A second occurrence
    # is required in a guard, state update, or modeled effect path.
    return len(re.findall(rf"\b{re.escape(name)}\b", mask_comments_and_strings(consumer.function.body))) >= 2
