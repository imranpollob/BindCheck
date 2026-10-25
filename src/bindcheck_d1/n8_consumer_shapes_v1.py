"""Exact successful N=8 RollupV1 decoding shapes (solver-free)."""

from __future__ import annotations

from dataclasses import dataclass
import itertools
from typing import Iterable


N = 8
WIDTH = {0: 1, 2: 4, 3: 5}
ENUMERATION_ALPHABET = (0, 1, 2, 3, 4)


@dataclass(frozen=True)
class Shape:
    index: int
    kinds: tuple[int, ...]
    starts: tuple[int, ...]

    @property
    def identifier(self) -> str:
        return f"{self.index:02d}_" + "-".join(str(kind) for kind in self.kinds)

    @property
    def fixed_positions(self) -> dict[int, int]:
        return dict(zip(self.starts, self.kinds))

    @property
    def records(self) -> tuple[dict[str, object], ...]:
        return tuple({
            "ordinal": ordinal,
            "kind": kind,
            "start": start,
            "width": WIDTH[kind],
            "payload_positions": list(range(start + 1, start + WIDTH[kind])),
        } for ordinal, (kind, start) in enumerate(zip(self.kinds, self.starts)))

    def matches(self, words: Iterable[int]) -> bool:
        values = tuple(words)
        return len(values) == N and all(values[position] == kind
                                        for position, kind in self.fixed_positions.items())


def _kind_sequences(remaining: int, prefix: tuple[int, ...] = ()):
    if remaining == 0:
        yield prefix
        return
    for kind, width in WIDTH.items():
        if width <= remaining:
            yield from _kind_sequences(remaining - width, prefix + (kind,))


def shapes() -> tuple[Shape, ...]:
    result = []
    for index, kinds in enumerate(sorted(_kind_sequences(N))):
        cursor = 0
        starts = []
        for kind in kinds:
            starts.append(cursor)
            cursor += WIDTH[kind]
        if cursor != N:
            raise AssertionError((kinds, cursor))
        result.append(Shape(index, kinds, tuple(starts)))
    if len(result) != 11:
        raise AssertionError(len(result))
    return tuple(result)


def decode_shape(words: Iterable[int]) -> tuple[str, tuple[int, ...]]:
    values = tuple(words)
    if len(values) != N:
        raise ValueError("N=8 decoder requires eight words")
    cursor = 0
    kinds = []
    while cursor < N:
        kind = values[cursor]
        if kind not in WIDTH:
            return "invalid_kind", tuple(kinds)
        width = WIDTH[kind]
        if cursor + width > N:
            return "truncated", tuple(kinds + [kind])
        kinds.append(kind)
        cursor += width
    return "valid", tuple(kinds)


def validate_exhaustively() -> dict[str, object]:
    defined = shapes()
    counts = {"valid": 0, "invalid_kind": 0, "truncated": 0}
    shape_counts = {shape.identifier: 0 for shape in defined}
    for words in itertools.product(ENUMERATION_ALPHABET, repeat=N):
        status, kinds = decode_shape(words)
        counts[status] += 1
        matches = [shape for shape in defined if shape.matches(words)]
        if status == "valid":
            if len(matches) != 1 or matches[0].kinds != kinds:
                raise AssertionError((words, status, kinds, matches))
            shape_counts[matches[0].identifier] += 1
        elif matches:
            raise AssertionError((words, status, matches))
    return {
        "alphabet": {
            "0": "padding",
            "1": "representative unsupported nonzero kind",
            "2": "mint",
            "3": "burn",
            "4": "producer-supported but consumer-invalid kind",
        },
        "assignments": len(ENUMERATION_ALPHABET) ** N,
        "classification_counts": counts,
        "shape_assignment_counts": shape_counts,
        "coverage_on_structurally_valid_decoding": True,
        "mutual_exclusion_on_structurally_valid_decoding": True,
        "invalid_and_truncated_outside_union": True,
        "scope": (
            "exhaustive over equality/control-flow classes for eight words; payload "
            "field values remain symbolic and guards/state/verifier/commit are excluded"
        ),
    }

