from __future__ import annotations

import collections
import pathlib
from dataclasses import dataclass
from typing import Any

from ..circuits import parse_r1cs, parse_sym


@dataclass
class CompiledRelation:
    """A small, auditable view of a compiled R1CS and its symbol table."""

    metadata: dict[str, Any]
    names: dict[int, list[str]]
    by_name: dict[str, int]
    constraints: list[set[int]]

    @classmethod
    def load(cls, r1cs: pathlib.Path, sym: pathlib.Path) -> "CompiledRelation":
        parsed = parse_r1cs(r1cs)
        constraints = parsed.pop("constraints")
        names, by_name = parse_sym(sym)
        return cls(parsed, names, by_name, constraints)

    def wire(self, source_name: str) -> int | None:
        candidates = [source_name, f"main.{source_name}"]
        exact = [self.by_name[name] for name in candidates if name in self.by_name]
        if len(set(exact)) == 1:
            return exact[0]
        suffix = f".{source_name}"
        matched = {wire for name, wire in self.by_name.items() if name.endswith(suffix)}
        return next(iter(matched)) if len(matched) == 1 else None

    def participates(self, source_name: str) -> bool:
        wire = self.wire(source_name)
        return wire is not None and any(wire in constraint for constraint in self.constraints)

    def shares_constraint(self, left: str, right: str) -> bool:
        left_wire, right_wire = self.wire(left), self.wire(right)
        if left_wire is None or right_wire is None:
            return False
        return any(left_wire in constraint and right_wire in constraint for constraint in self.constraints)

    def connected(self, left: str, right: str, *, max_wires: int = 10000) -> bool:
        """Return graph connectivity without treating it as algebraic binding.

        Callers use a negative answer only after a source-level exact-template
        check.  A positive answer never establishes semantic equivalence.
        """

        source, target = self.wire(left), self.wire(right)
        if source is None or target is None:
            return False
        incident: dict[int, list[int]] = collections.defaultdict(list)
        for index, wires in enumerate(self.constraints):
            for wire in wires:
                incident[wire].append(index)
        queue = collections.deque([source])
        seen = {source}
        while queue and len(seen) <= max_wires:
            wire = queue.popleft()
            for constraint_index in incident.get(wire, []):
                for neighbour in self.constraints[constraint_index]:
                    if neighbour == target:
                        return True
                    if neighbour not in seen:
                        seen.add(neighbour)
                        queue.append(neighbour)
        return source == target
