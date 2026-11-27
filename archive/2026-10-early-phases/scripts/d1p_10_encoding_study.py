#!/usr/bin/env python3
"""D1P-10 bounded selected-cone producer-encoding study.

Preparation is solver-free.  Execution reuses the frozen D1P-07 native-macOS
runner and resource policy.  The subject is only the historical check-added
N=8 selected producer cone, never the full producer relation.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bindcheck_d1.conservative_propagation_v1 import (  # noqa: E402
    State,
    normalize,
    opcode_witnesses,
    polynomial_witnesses,
    substitute,
)
from bindcheck_d1.model_v2 import FIELD_MODULUS as P  # noqa: E402


PRINTED_ACIR = ROOT / "results/artifacts/d1-n8/b_agg_agg_check_added_.compile.stdout"
ABI = ROOT / "results/artifacts/d1-n8/b_agg_agg_check_added_.abi.json"
SPEC = ROOT / "scripts/t22_specs/payy_agg_agg.json"
LEGACY = ROOT / "scripts/t22_v3_tailspec.py"
SPECIALIZER = ROOT / "scripts/d1p_04_specialize.py"
D1P09_OFFLINE = ROOT / "scripts/d1p_09_offline.py"
D1P07_RUNNER = ROOT / "scripts/d1p_07_track_a.py"
D1P07_POLICY = ROOT / "metadata/d1/d1p-07-resource-policy.json"
D1P06_MANIFEST = ROOT / "metadata/d1/d1p-06-input-manifest.json"
D1P09_AUDIT = ROOT / "metadata/d1/d1p-09-propagation-audit.json"
PROTOCOL = ROOT / "docs/d1-paper/d1p-10-protocol.md"
RESOURCE_POLICY = ROOT / "metadata/d1/d1p-10-resource-policy.json"
TESTS = ROOT / "tests/d1/test_d1p_10_encoding_study.py"

PINS = {
    PRINTED_ACIR: "1743e5dcdeaf36172fbbde66fda165e79db9081f8a3a980ee4bbf31f61a2875a",
    ABI: "8b288933d3330874c2e5c9b00443d6b0748302fce46d5aedf7ece6536b3cbebb",
    LEGACY: "81a1cd43cd3e6e735dc325535f05d9b2a88c6c9794b434ab53e834061ff700c8",
    SPECIALIZER: "afb0d15492b8b5aafdba1a52a18b11a96fe7a02485111083ae7b8f4a1b1cf9c3",
    D1P09_OFFLINE: "bcf032210c676f438fc795485896217238d5f54a1d26c8b330e0d6f06e9841a5",
    D1P07_RUNNER: "cba540dcb8cd310c6d12a010c2833f79fdd09fe9ec17c900f5d5fc5b401dd6fe",
    D1P07_POLICY: "d292323e8123c0f4bf38469c3bfeb7ba9a2733f709a0e5229be0c34913ffc885",
    D1P06_MANIFEST: "67f588f4e1254b28cc17e226b31039574c6d2b26db4b16214c9d63a813b0fef5",
    D1P09_AUDIT: "ff590c3b57ffdeddaf8854810693977ee45f8fd8272e965264070a4bf7fbb90f",
}
EXPECTED_SOLVER = "a083a7f56a3f61691583b699076322bbcbf6732decfb4f6dc41850dbcc3df027"
SOLVER_ARGUMENTS = ("--lang=smt2", "--ff-solver=split")
OUTER = tuple(range(1275, 1283))
STREAMS = (
    {"activation": 508, "words": tuple(range(511, 519))},
    {"activation": 1143, "words": tuple(range(2293, 2301))},
)
OBLIGATIONS = ("cone", "nonvacuous", "prefix", "tail")
CANDIDATES = ("radix4", "radix16", "radix256")
RADIX = {"radix4": 4, "radix16": 16, "radix256": 256}
PROFILE_OBLIGATIONS = ("cone", "nonvacuous")
CELLS = ("inactive", "active_empty", "length_4", "length_5", "truncated_8")
CELL_LENGTH = {"inactive": 0, "active_empty": 0, "length_4": 4,
               "length_5": 5, "truncated_8": 8}
RSS_CUTOFF = 4 * 1024**3
SAMPLE_INTERVAL = 0.05
PROFILE_SECONDS = 30.0
VALIDATION_SECONDS = 30.0
UNSPLIT_SECONDS = 300.0
PARTITION_SECONDS = 300.0
CELL_SECONDS = 12.0


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def relative(path: Path) -> str:
    return str(Path(path).resolve().relative_to(ROOT))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def write_fresh(path: Path, data: bytes) -> dict[str, Any]:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"fresh output required: {path}")
    path.write_bytes(data)
    return {"path": relative(path), "sha256": sha256_bytes(data), "bytes": len(data)}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_pins() -> None:
    for path, expected in PINS.items():
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"pinned input changed: {relative(path)}: {actual}")


def ff_const(value: int) -> str:
    return f"(as ff{value % P} F)"


def ff_add(terms: Iterable[str]) -> str:
    values = list(terms)
    if not values:
        return ff_const(0)
    if len(values) == 1:
        return values[0]
    return "(ff.add " + " ".join(values) + ")"


def ff_mul(terms: Iterable[str]) -> str:
    values = list(terms)
    if not values:
        return ff_const(1)
    if len(values) == 1:
        return values[0]
    return "(ff.mul " + " ".join(values) + ")"


def poly_term(poly: dict[tuple[int, ...], int]) -> str:
    terms = []
    for monomial, coefficient in sorted(poly.items()):
        factors = []
        if coefficient % P != 1 or not monomial:
            factors.append(ff_const(coefficient))
        factors.extend(f"w{witness}" for witness in monomial)
        terms.append(ff_mul(factors))
    return ff_add(terms)


def expression_term(expression: Iterable[tuple[int, list[int]]],
                    values: dict[int, int] | None = None) -> str:
    poly = normalize(expression)
    if values:
        poly = substitute(poly, values)
    return poly_term(poly)


def bool_and(terms: Iterable[str]) -> str:
    values = list(terms)
    if not values:
        return "true"
    if len(values) == 1:
        return values[0]
    return "(and " + " ".join(values) + ")"


def xor(left: str, right: str) -> str:
    return f"(or (and {left} (not {right})) (and {right} (not {left})))"


class ComponentEncoder:
    """Serialize selected-cone constraints without changing ACIR semantics."""

    def __init__(self, witness_ids: Iterable[int], range_mode: str,
                 range_namespace: str = "r") -> None:
        self.range_mode = range_mode
        self.range_namespace = range_namespace
        self.witness_ids = tuple(sorted(set(witness_ids)))
        self.auxiliary: list[str] = []
        self._auxiliary_set: set[str] = set()

    def declare_aux(self, name: str) -> str:
        if name not in self._auxiliary_set:
            self._auxiliary_set.add(name)
            self.auxiliary.append(name)
        return name

    def declarations(self) -> list[str]:
        return ([f"(declare-const w{witness} F)" for witness in self.witness_ids]
                + [f"(declare-const {name} F)" for name in self.auxiliary])

    def range_constraints(self, source: int,
                          expression: Iterable[tuple[int, list[int]]],
                          bits: int) -> list[str]:
        if bits >= 254:
            return []
        target = expression_term(expression)
        if bits == 1 or self.range_mode == "bits":
            digits = [self.declare_aux(f"{self.range_namespace}_{source}_{index}")
                      for index in range(bits)]
            roots = [f"(= {ff_mul((digit, ff_add((digit, ff_const(-1)))))} {ff_const(0)})"
                     for digit in digits]
            reconstruction = ff_add(
                digit if index == 0 else ff_mul((ff_const(2**index), digit))
                for index, digit in enumerate(digits)
            )
            return roots + [f"(= {target} {reconstruction})"]

        base = RADIX[self.range_mode]
        width = base.bit_length() - 1
        if bits % width:
            raise ValueError(f"{bits}-bit range not divisible by radix width {width}")
        count = bits // width
        digits = [self.declare_aux(f"{self.range_namespace}_{source}_{index}")
                  for index in range(count)]
        roots = []
        for digit in digits:
            factors = [ff_add((digit, ff_const(-value))) for value in range(base)]
            roots.append(f"(= {ff_mul(factors)} {ff_const(0)})")
        reconstruction = ff_add(
            digit if index == 0 else ff_mul((ff_const(base**index), digit))
            for index, digit in enumerate(digits)
        )
        return roots + [f"(= {target} {reconstruction})"]

    def groups_from_original(self, indexed: Iterable[tuple[int, tuple]]) -> dict[str, list[str]]:
        groups = {"assertions": [], "ranges": [], "memory": []}
        blocks: dict[int, list[str]] = {}
        for source, opcode in indexed:
            kind = opcode[0]
            if kind == "assert":
                groups["assertions"].append(
                    f"(= {expression_term(opcode[1])} {ff_const(0)})"
                )
            elif kind == "range":
                groups["ranges"].extend(self.range_constraints(source, opcode[1], opcode[2]))
            elif kind == "init":
                blocks[opcode[1]] = [expression_term(value) for value in opcode[2]]
            elif kind in ("read", "write"):
                block = opcode[1]
                if block not in blocks:
                    raise RuntimeError(f"memory b{block} used before init")
                index_term = expression_term(opcode[3] if kind == "read" else opcode[2])
                values = blocks[block]
                groups["memory"].append(bool_and(
                    f"(= {index_term} {ff_const(offset)})" for offset in range(len(values))
                ).replace("(and (=", "(or (=", 1) if len(values) > 1 else
                    f"(= {index_term} {ff_const(0)})")
                # The replacement above only changes the outer connective.
                if len(values) > 1:
                    groups["memory"][-1] = "(or " + " ".join(
                        f"(= {index_term} {ff_const(offset)})"
                        for offset in range(len(values))
                    ) + ")"
                if kind == "read":
                    selected = values[-1]
                    for offset in range(len(values) - 2, -1, -1):
                        selected = f"(ite (= {index_term} {ff_const(offset)}) {values[offset]} {selected})"
                    groups["memory"].append(
                        f"(= {expression_term(opcode[2])} {selected})"
                    )
                else:
                    value = expression_term(opcode[3])
                    blocks[block] = [
                        f"(ite (= {index_term} {ff_const(offset)}) {value} {old})"
                        for offset, old in enumerate(values)
                    ]
            else:
                raise RuntimeError(f"unsupported selected opcode {kind}")
        return groups

    def groups_from_state(self, state: State,
                          all_original_ranges: Iterable[tuple[int, tuple]]) -> dict[str, list[str]]:
        residual = state.residual()
        groups = {"assertions": [], "ranges": [], "memory": []}
        for _, poly in sorted(residual.assertions.items(), key=lambda item: str(item[0])):
            groups["assertions"].append(f"(= {poly_term(poly)} {ff_const(0)})")
        # D1P-10 deliberately retains every original range constraint.
        for source, opcode in all_original_ranges:
            groups["ranges"].extend(self.range_constraints(source, opcode[1], opcode[2]))

        blocks: dict[int, list[str]] = {}
        for source in residual.memory:
            opcode = state.opcodes[source]
            kind = opcode[0]
            if kind == "init":
                blocks[opcode[1]] = [expression_term(value, state.values) for value in opcode[2]]
            elif kind in ("read", "write"):
                block = opcode[1]
                if block not in blocks:
                    raise RuntimeError(f"residual memory b{block} used before init")
                index_term = expression_term(
                    opcode[3] if kind == "read" else opcode[2], state.values
                )
                values = blocks[block]
                groups["memory"].append("(or " + " ".join(
                    f"(= {index_term} {ff_const(offset)})"
                    for offset in range(len(values))
                ) + ")")
                if kind == "read":
                    selected = values[-1]
                    for offset in range(len(values) - 2, -1, -1):
                        selected = f"(ite (= {index_term} {ff_const(offset)}) {values[offset]} {selected})"
                    groups["memory"].append(
                        f"(= {expression_term(opcode[2], state.values)} {selected})"
                    )
                else:
                    value = expression_term(opcode[3], state.values)
                    blocks[block] = [
                        f"(ite (= {index_term} {ff_const(offset)}) {value} {old})"
                        for offset, old in enumerate(values)
                    ]
            else:
                raise RuntimeError(f"unsupported residual memory opcode {kind}")
        return groups


def header() -> list[str]:
    return [
        "(set-logic QF_FF)",
        "(set-option :produce-models true)",
        f"(define-sort F () (_ FiniteField {P}))",
    ]


def component_script(encoder: ComponentEncoder, groups: dict[str, list[str]],
                     extra_assertions: Iterable[str], suffix: str,
                     model_witnesses: Iterable[int]) -> bytes:
    constraints = [*groups["assertions"], *groups["ranges"], *groups["memory"],
                   *list(extra_assertions)]
    lines = [*header(), *encoder.declarations()]
    lines.extend(f"(assert {constraint})" for constraint in constraints)
    if suffix:
        lines.extend(suffix.rstrip("\n").splitlines())
    lines.append("(check-sat)")
    values = " ".join(f"w{witness}" for witness in sorted(set(model_witnesses)))
    lines.append(f"(get-value ({values}))")
    return ("\n".join(lines) + "\n").encode("ascii")


def baseline_instrumented(parent: dict[str, Any], witnesses: Iterable[int],
                          cone_only: bool) -> tuple[bytes, str]:
    projection = "(get-value (" + " ".join(
        f"w{witness}" for witness in sorted(set(witnesses))
    ) + "))\n"
    if cone_only:
        core = parent["producer_prefix"] + b"(check-sat)\n"
    else:
        lines = parent["raw"].splitlines(keepends=True)
        if not lines[-1].startswith(b"(get-value "):
            raise RuntimeError("unexpected parent trailer")
        core = b"".join(lines[:-1])
    return core + projection.encode("ascii"), sha256_bytes(core)


def selected_cone():
    require_pins()
    tail = load_module("d1p10_tail", LEGACY)
    specializer = load_module("d1p10_specializer", SPECIALIZER)
    offline = load_module("d1p10_offline", D1P09_OFFLINE)
    acir = tail.Acir(PRINTED_ACIR.read_text())
    abi = json.loads(ABI.read_text())
    spec = json.loads(SPEC.read_text())
    messages, streams = tail.build(spec, acir, abi)
    seeds = set()
    for expression in messages:
        seeds |= tail.expr_wits(expression)
    for words, activation in streams:
        for expression in words:
            seeds |= tail.expr_wits(expression)
        if activation:
            seeds |= tail.expr_wits(activation)
    selected, witnesses = tail.cone(acir, seeds)
    indexed = [(index, acir.ops[index]) for index in selected]
    if len(indexed) != 620 or len(witnesses) != 540:
        raise RuntimeError(f"selected-cone identity changed: {len(indexed)}/{len(witnesses)}")
    counts = Counter(opcode[0] for _, opcode in indexed)
    if counts != Counter({"assert": 546, "range": 58, "read": 15, "init": 1}):
        raise RuntimeError(f"selected-cone inventory changed: {counts}")
    return tail, specializer, offline, acir, indexed, set(witnesses)


def cell_facts(offline, cell: dict[str, Any]) -> tuple[dict[int, int], dict[int, str], set[int]]:
    fixed: dict[int, int] = {}
    basis: dict[int, str] = {}
    predicate_witnesses: set[int] = set()
    for name, stream in ((cell["left"], STREAMS[0]), (cell["right"], STREAMS[1])):
        item_fixed, item_basis, item_witnesses = offline.single_cell_facts(name, stream)
        fixed.update(item_fixed)
        basis.update(item_basis)
        predicate_witnesses |= item_witnesses
    return fixed, basis, predicate_witnesses


def triviality(obligation: str, cell: dict[str, Any]) -> str:
    if obligation == "cone":
        return "no_goal"
    total = cell["total_length"]
    if obligation == "nonvacuous":
        return "literal_true" if 1 <= total <= 8 else "literal_false"
    if obligation == "prefix":
        if total > 8:
            return "literal_true"
        if total == 0:
            return "literal_false"
        return "nontrivial"
    if obligation == "tail":
        return "literal_false" if total >= 8 else "nontrivial"
    raise ValueError(obligation)


def parent_for(specializer, obligation: str) -> dict[str, Any]:
    query = "nonvacuous" if obligation == "cone" else obligation
    return specializer.parse_parent("check_added", query)


def original_suffix(parent: dict[str, Any], obligation: str) -> str:
    if obligation == "cone":
        return ""
    return parent["walk"] + parent["goal_line"]


def item_record(path_info: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {**path_info, **extra}


def range_boundary_script(mode: str, value: int) -> bytes:
    encoder = ComponentEncoder([1], mode, "boundary")
    groups = {"assertions": [], "ranges": encoder.range_constraints(1, [(1, [1])], 32),
              "memory": []}
    return component_script(encoder, groups, [f"(= w1 {ff_const(value)})"], "", [1])


def lost_equality_script() -> bytes:
    # Exact T22 regression shape from test_d1p_09_offline: case w1=7,
    # original w9=w1, residual reconstruction w9=7.
    lines = [*header(), "(declare-const w1 F)", "(declare-const w9 F)",
             f"(define-fun original () Bool (= w9 w1))",
             f"(define-fun residual () Bool (= w9 {ff_const(7)}))",
             f"(assert (= w1 {ff_const(7)}))",
             f"(assert {xor('original', 'residual')})", "(check-sat)"]
    return ("\n".join(lines) + "\n").encode("ascii")


def validation_script(indexed: list[tuple[int, tuple]], witnesses: set[int],
                      state: State, predicate: str) -> bytes:
    ranges = [(source, opcode) for source, opcode in indexed if opcode[0] == "range"]
    encoder = ComponentEncoder(witnesses, "bits", "shared")
    original = encoder.groups_from_original(indexed)
    residual = encoder.groups_from_state(state, ranges)
    original_formula = bool_and(original["assertions"] + original["ranges"] + original["memory"])
    reconstruction = [f"(= w{witness} {ff_const(value)})"
                      for witness, value in sorted(state.values.items())]
    residual_formula = bool_and(
        residual["assertions"] + residual["ranges"] + residual["memory"] + reconstruction
    )
    lines = [*header(), *encoder.declarations(), f"(assert {predicate})",
             f"(assert {xor(original_formula, residual_formula)})", "(check-sat)"]
    return ("\n".join(lines) + "\n").encode("ascii")


def prepare(args) -> int:
    output = args.output.resolve()
    manifest_path = args.manifest.resolve()
    if output.exists() or manifest_path.exists():
        raise FileExistsError("fresh D1P-10 preparation paths required")
    output.mkdir(parents=True)
    tail, specializer, offline, _, indexed, witnesses = selected_cone()
    ranges = [(source, opcode) for source, opcode in indexed if opcode[0] == "range"]
    parents = {obligation: parent_for(specializer, obligation) for obligation in OBLIGATIONS}

    baseline = []
    for obligation in OBLIGATIONS:
        data, core_hash = baseline_instrumented(
            parents[obligation], witnesses, obligation == "cone"
        )
        info = write_fresh(output / "baseline" / f"{obligation}.smt2", data)
        baseline.append(item_record(
            info, arm="baseline", obligation=obligation,
            parent_sha256=parents[obligation]["hash"],
            constraint_and_goal_through_check_sat_sha256=core_hash,
            only_change="post-check-sat get-value projection enlarged to all 540 cone witnesses",
        ))

    candidates: dict[str, list[dict[str, Any]]] = {}
    for mode in CANDIDATES:
        rows = []
        for obligation in OBLIGATIONS:
            encoder = ComponentEncoder(witnesses, mode, mode)
            groups = encoder.groups_from_original(indexed)
            data = component_script(
                encoder, groups, [], original_suffix(parents[obligation], obligation), witnesses
            )
            info = write_fresh(output / "candidates" / mode / f"{obligation}.smt2", data)
            rows.append(item_record(
                info, arm="alternative", candidate=mode, radix=RADIX[mode],
                obligation=obligation,
                original_walk_sha256=(parents[obligation]["walk_hash"]
                                      if obligation != "cone" else None),
                original_goal_sha256=(parents[obligation]["goal_hash"]
                                      if obligation != "cone" else None),
                range_auxiliaries=len(encoder.auxiliary),
            ))
        candidates[mode] = rows

    cells = specializer.cell_pairs()
    propagated: dict[str, list[dict[str, Any]]] = {obligation: [] for obligation in OBLIGATIONS}
    validations = []
    state_summaries = []
    for cell in cells:
        fixed, basis, predicate_witnesses = cell_facts(offline, cell)
        state = State(indexed, fixed, basis, set(OUTER) | {
            stream["activation"] for stream in STREAMS
        } | {word for stream in STREAMS for word in stream["words"]}).run()
        audit = state.audit(witnesses, predicate_witnesses, cell["predicate"])
        state_summaries.append({
            "cell": cell["id"],
            "assigned_witnesses": len(state.values),
            "residual_original_opcodes_before_range_retention": audit["residual"]["original_opcodes"],
            "residual_relation_witnesses": audit["residual"]["relation_witnesses"],
            "reconstruction_equalities": len(state.values),
            "free_extension_witnesses": len(audit["residual"]["free_extension_witnesses"]),
        })
        validation_data = validation_script(indexed, witnesses, state, cell["predicate"])
        validation_info = write_fresh(
            output / "validation" / "propagation" / f"{cell['id']}.smt2",
            validation_data,
        )
        validations.append(item_record(
            validation_info, kind="propagation_equivalence", expected="unsat",
            cell=cell["id"], predicate=cell["predicate"],
        ))
        reconstruction = [f"(= w{witness} {ff_const(value)})"
                          for witness, value in sorted(state.values.items())]
        for obligation in OBLIGATIONS:
            encoder = ComponentEncoder(witnesses, "bits", f"cell_{cell['index']}")
            groups = encoder.groups_from_state(state, ranges)
            data = component_script(
                encoder, groups, [cell["predicate"], *reconstruction],
                original_suffix(parents[obligation], obligation), witnesses,
            )
            info = write_fresh(
                output / "propagated" / obligation / f"{cell['id']}.smt2", data
            )
            propagated[obligation].append(item_record(
                info, arm="propagated_cells", obligation=obligation,
                cell_index=cell["index"], cell=cell["id"],
                predicate=cell["predicate"],
                triviality=triviality(obligation, cell),
                reconstruction_equalities=len(state.values),
                ranges_retained=58,
                original_walk_sha256=(parents[obligation]["walk_hash"]
                                      if obligation != "cone" else None),
                original_goal_sha256=(parents[obligation]["goal_hash"]
                                      if obligation != "cone" else None),
            ))

    lost = write_fresh(output / "validation/t22-lost-equality.smt2", lost_equality_script())
    validation_special = [item_record(
        lost, kind="t22_lost_equality", expected="unsat",
        meaning="original w9=w1 under w1=7 equals retained reconstruction w9=7",
    )]
    range_controls: dict[str, list[dict[str, Any]]] = {}
    for mode in CANDIDATES:
        rows = []
        for name, value, expected in (
            ("zero", 0, "sat"),
            ("maximum", 2**32 - 1, "sat"),
            ("first_outside", 2**32, "unsat"),
            ("field_minus_one", P - 1, "unsat"),
        ):
            info = write_fresh(
                output / "validation" / "range" / mode / f"{name}.smt2",
                range_boundary_script(mode, value),
            )
            rows.append(item_record(info, kind="range_boundary", candidate=mode,
                                    name=name, value=str(value), expected=expected))
        range_controls[mode] = rows

    d1p06 = json.loads(D1P06_MANIFEST.read_text())
    controls = [dict(item) for item in d1p06["controls"]]
    for item in controls:
        if sha256(ROOT / item["path"]) != item["sha256"]:
            raise RuntimeError(f"control hash changed: {item['name']}")

    profile_schedule = []
    for arm in ("baseline", *CANDIDATES):
        source = baseline if arm == "baseline" else candidates[arm]
        for obligation in PROFILE_OBLIGATIONS:
            item = next(row for row in source if row["obligation"] == obligation)
            profile_schedule.append({
                "arm": arm, "obligation": obligation, "path": item["path"],
                "sha256": item["sha256"], "bytes": item["bytes"],
            })

    manifest = {
        "task": "D1P-10",
        "status": "PREPARED_BEFORE_ANY_D1P10_SOLVER_CALL",
        "created_at_utc": utc_now(),
        "scope": "historical check-added N=8 selected producer cone only; not full producer relation",
        "repository_head": subprocess.run(
            ["/usr/bin/git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
            stdout=subprocess.PIPE, check=True,
        ).stdout.strip(),
        "generator": {"path": relative(Path(__file__)), "sha256": sha256(Path(__file__))},
        "protocol": {"path": relative(PROTOCOL), "sha256": sha256(PROTOCOL)},
        "resource_policy": {"path": relative(RESOURCE_POLICY), "sha256": sha256(RESOURCE_POLICY)},
        "dependencies": {relative(path): sha256(path) for path in PINS},
        "input": {
            "printed_acir_sha256": sha256(PRINTED_ACIR),
            "selected_opcodes": len(indexed), "selected_witnesses": len(witnesses),
            "opcode_counts": dict(sorted(Counter(opcode[0] for _, opcode in indexed).items())),
            "range_bits": dict(sorted(Counter(
                opcode[2] for _, opcode in indexed if opcode[0] == "range"
            ).items())),
            "interface_witnesses": {
                "outer": list(OUTER),
                "streams": STREAMS,
            },
        },
        "candidate_pool": {
            "fixed_before_profiling": list(CANDIDATES),
            "universal_argument": (
                "digit root polynomial has exactly the distinct canonical radix roots; "
                "radix reconstruction is below the pinned field modulus in both directions"
            ),
            "selection_rule": [
                "more resolved SAT/UNSAT profiling obligations",
                "lower aggregate elapsed with unresolved charged 30 seconds",
                "lower aggregate observed peak RSS; missing ranks last",
                "smaller aggregate profiling input bytes",
                "fixed order radix4, radix16, radix256",
            ],
        },
        "profile_schedule": profile_schedule,
        "baseline": baseline,
        "candidates": candidates,
        "propagated": propagated,
        "propagation_state_summaries": state_summaries,
        "validation": {
            "controls": controls,
            "propagation_equivalence": validations,
            "special": validation_special,
            "range_boundaries": range_controls,
        },
        "counts": {
            "profile_calls": len(profile_schedule),
            "baseline_primary": len(baseline),
            "propagated_primary": sum(len(rows) for rows in propagated.values()),
            "candidate_primary_per_candidate": len(OBLIGATIONS),
            "propagation_equivalence": len(validations),
        },
        "solver_observations": 0,
        "research_verdict": "UNKNOWN",
    }
    write_json(manifest_path, manifest)
    summary = {
        "task": "D1P-10", "status": manifest["status"],
        "manifest": relative(manifest_path), "manifest_sha256": sha256(manifest_path),
        "profile_calls": len(profile_schedule), "primary_inputs": 108,
        "validation_queries_prepared": 25 + 1 + 12,
        "solver_calls": 0,
    }
    write_json(output / "prepare-summary.json", summary)
    print(json.dumps(summary, indent=2))
    return 0


def all_manifest_items(manifest: dict[str, Any]) -> Iterable[dict[str, Any]]:
    yield from manifest["baseline"]
    for rows in manifest["candidates"].values():
        yield from rows
    for rows in manifest["propagated"].values():
        yield from rows
    yield from manifest["validation"]["propagation_equivalence"]
    yield from manifest["validation"]["special"]
    for rows in manifest["validation"]["range_boundaries"].values():
        yield from rows
    yield from manifest["validation"]["controls"]


def verify_manifest(path: Path) -> tuple[dict[str, Any], int]:
    manifest = json.loads(path.read_text())
    checked = 0
    for item in all_manifest_items(manifest):
        actual = sha256(ROOT / item["path"])
        if actual != item["sha256"]:
            raise RuntimeError(f"input hash mismatch: {item['path']}: {actual}")
        checked += 1
    return manifest, checked


def preflight(args) -> int:
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"fresh preflight required: {output}")
    output.mkdir(parents=True)
    checks: dict[str, bool] = {}
    error = None
    try:
        require_pins()
        checks["pinned_dependencies"] = True
        checks["native_macos_arm64"] = platform.system() == "Darwin" and platform.machine() == "arm64"
        solver = args.solver.resolve()
        checks["solver_identity"] = solver.is_file() and sha256(solver) == EXPECTED_SOLVER
        manifest, checked = verify_manifest(args.manifest.resolve())
        checks["prepared_inputs"] = checked == 156
        checks["profile_schedule"] = len(manifest["profile_schedule"]) == 8
        checks["protocol_recorded"] = PROTOCOL.is_file() and RESOURCE_POLICY.is_file()
        prior = json.loads((ROOT / "results/raw/D1P-07/preflight-macos/preflight.json").read_text())
        checks["d1p07_runner_preflight_preserved"] = prior.get("status") == "PASS"
        checks["d1p07_runner_hash"] = sha256(D1P07_RUNNER) == PINS[D1P07_RUNNER]
        if not all(checks.values()):
            raise RuntimeError("one or more preflight checks failed")
        status = "PASS"
    except Exception as exc:
        status = "FAIL"
        error = f"{type(exc).__name__}: {exc}"
        checked = 0
        solver = args.solver.resolve()
    record = {
        "task": "D1P-10", "status": status, "error": error,
        "recorded_at_utc": utc_now(), "solver_calls": 0,
        "checks": checks, "prepared_items_checked": checked,
        "solver": {"path": str(solver), "sha256": sha256(solver) if solver.is_file() else None,
                   "arguments": list(SOLVER_ARGUMENTS)},
        "manifest": {"path": relative(args.manifest), "sha256": sha256(args.manifest)},
        "platform": {"system": platform.system(), "machine": platform.machine(),
                     "release": platform.release(), "python": platform.python_version()},
        "preserved_d1p07_preflight": {
            "path": "results/raw/D1P-07/preflight-macos/preflight.json",
            "sha256": sha256(ROOT / "results/raw/D1P-07/preflight-macos/preflight.json"),
        },
    }
    write_json(output / "preflight.json", record)
    print(json.dumps({"status": status, "checks": checks, "items": checked}, sort_keys=True))
    return 0 if status == "PASS" else 2


def freeze_profile(args) -> int:
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"fresh profiling freeze required: {output}")
    manifest, checked = verify_manifest(args.manifest.resolve())
    preflight_path = args.preflight.resolve()
    preflight_record = json.loads(preflight_path.read_text())
    if preflight_record.get("status") != "PASS":
        raise RuntimeError("cannot freeze after failed preflight")
    solver = Path(preflight_record["solver"]["path"])
    value = {
        "task": "D1P-10", "status": "PROFILING_FROZEN_BEFORE_SOLVER_CALL_1",
        "frozen_at_utc": utc_now(),
        "repository_head": manifest["repository_head"],
        "scope": manifest["scope"],
        "solver": {"path": str(solver), "sha256": sha256(solver),
                   "arguments": list(SOLVER_ARGUMENTS)},
        "preflight": {"path": relative(preflight_path), "sha256": sha256(preflight_path)},
        "manifest": {"path": relative(args.manifest), "sha256": sha256(args.manifest),
                     "items_checked": checked},
        "schedule": manifest["profile_schedule"],
        "candidate_pool": manifest["candidate_pool"],
        "limits": {"calls_max": 10, "planned_calls": 8,
                   "seconds_per_call": PROFILE_SECONDS, "aggregate_seconds": 300.0,
                   "sequential": True, "attempts_per_query": 1,
                   "rss_cutoff_bytes": RSS_CUTOFF},
        "frozen_files": [
            {"path": relative(path), "sha256": sha256(path)}
            for path in (Path(__file__), TESTS, PROTOCOL, RESOURCE_POLICY,
                         D1P07_RUNNER, D1P07_POLICY, args.manifest.resolve())
        ],
        "research_verdict": "UNKNOWN",
    }
    write_json(output, value)
    print(json.dumps({"status": value["status"], "schedule": len(value["schedule"]),
                      "freeze": relative(output)}, sort_keys=True))
    return 0


def verify_frozen_files(freeze: dict[str, Any]) -> None:
    for item in freeze["frozen_files"]:
        actual = sha256(ROOT / item["path"])
        if actual != item["sha256"]:
            raise RuntimeError(f"frozen file changed: {item['path']}: {actual}")
    solver = Path(freeze["solver"]["path"])
    if sha256(solver) != freeze["solver"]["sha256"]:
        raise RuntimeError("solver changed after freeze")


def load_runner():
    require_pins()
    return load_module("d1p10_d1p07_runner", D1P07_RUNNER)


def parse_solver_result(stdout_path: Path) -> tuple[str, bool]:
    lines = stdout_path.read_text(errors="replace").splitlines()
    if not lines:
        return "missing", False
    result = lines[0].strip().lower()
    if result not in ("sat", "unsat", "unknown"):
        return "malformed", False
    return result, result == "sat" and len(lines) > 1


def execute_call(runner, *, index: int, phase: str, name: str,
                 item: dict[str, Any], seconds: float, solver: Path,
                 logs: Path, monitor) -> dict[str, Any]:
    record = runner.run_monitored(
        index=index, kind=phase, name=name,
        argv=[solver, *SOLVER_ARGUMENTS], logs_dir=logs, monitor=monitor,
        input_path=ROOT / item["path"], timeout_seconds=seconds,
        rss_cutoff_bytes=RSS_CUTOFF, sample_interval_seconds=SAMPLE_INTERVAL,
    )
    parsed, model = parse_solver_result(ROOT / record["stdout_path"])
    usable = (record["status"] == "COMPLETED" and record["exit_status"] == 0
              and parsed in ("sat", "unsat", "unknown"))
    record.update({
        "phase": phase, "attempts": 1, "input_path": item["path"],
        "input_sha256": item["sha256"], "parsed": parsed,
        "model_output_present": model,
        "result": parsed.upper() if usable else "UNKNOWN",
    })
    runner.write_json(ROOT / record["record_path"], record)
    return record


INFRA_FAILURE = {"LAUNCH_ERROR", "MONITOR_ERROR", "RUNNER_ERROR",
                 "EXIT_WAIT_TIMEOUT", "TERMINATION_ERROR"}


def profile(args) -> int:
    output = args.output.resolve()
    ledger_path = args.ledger.resolve()
    if output.exists() or ledger_path.exists():
        raise FileExistsError("fresh profiling output and ledger required")
    output.mkdir(parents=True)
    freeze_path = args.freeze.resolve()
    freeze = json.loads(freeze_path.read_text())
    verify_frozen_files(freeze)
    runner = load_runner()
    monitor = runner.D1P05.MacProcessTreeMonitor()
    solver = Path(freeze["solver"]["path"])
    records = []
    stop_reason = None
    phase_started = time.monotonic()
    for index, item in enumerate(freeze["schedule"], 1):
        if index > 10 or index * PROFILE_SECONDS > 300.0:
            stop_reason = "profiling budget exhausted"
            break
        record = execute_call(
            runner, index=index, phase="profile", name=f"{item['arm']}__{item['obligation']}",
            item=item, seconds=PROFILE_SECONDS, solver=solver,
            logs=output / "calls", monitor=monitor,
        )
        record.update({"arm": item["arm"], "obligation": item["obligation"]})
        runner.write_json(ROOT / record["record_path"], record)
        records.append(record)
        if record["status"] in INFRA_FAILURE:
            stop_reason = f"infrastructure failure at call {index}: {record['status']}"
            break
    ledger = {
        "task": "D1P-10", "phase": "profiling",
        "status": "COMPLETE" if len(records) == 8 and stop_reason is None else "STOPPED",
        "recorded_at_utc": utc_now(), "stop_reason": stop_reason,
        "freeze": {"path": relative(freeze_path), "sha256": sha256(freeze_path)},
        "limits": freeze["limits"], "records": records,
        "counts": dict(Counter(record["result"] for record in records)),
        "solver_call_elapsed_seconds": round(sum(r["elapsed_seconds"] for r in records), 6),
        "phase_elapsed_seconds": round(time.monotonic() - phase_started, 6),
        "research_verdict": "UNKNOWN",
    }
    write_json(output / "profiling-ledger.json", ledger)
    write_json(ledger_path, ledger)
    print(json.dumps({"status": ledger["status"], "calls": len(records),
                      "counts": ledger["counts"],
                      "seconds": ledger["solver_call_elapsed_seconds"]}, sort_keys=True))
    return 0 if ledger["status"] == "COMPLETE" else 2


def select_candidate(args) -> int:
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"fresh selection record required: {output}")
    ledger_path = args.profile_ledger.resolve()
    ledger = json.loads(ledger_path.read_text())
    if ledger.get("status") != "COMPLETE" or len(ledger.get("records", [])) != 8:
        raise RuntimeError("profiling did not complete the frozen eight-call schedule")
    manifest, _ = verify_manifest(args.manifest.resolve())
    rows = []
    for rank, candidate in enumerate(CANDIDATES):
        records = [record for record in ledger["records"] if record["arm"] == candidate]
        if len(records) != 2:
            raise RuntimeError(f"missing profiling records for {candidate}")
        resolved = sum(record["result"] in ("SAT", "UNSAT") for record in records)
        charged = sum(record["elapsed_seconds"] if record["result"] in ("SAT", "UNSAT")
                      else PROFILE_SECONDS for record in records)
        peaks = [record["peak_tree_rss_bytes"] for record in records]
        rss_missing = any(value is None for value in peaks)
        rss_sum = sum(value or 0 for value in peaks)
        bytes_total = sum(record["input_bytes"] for record in records)
        score = (-resolved, round(charged, 6), 1 if rss_missing else 0,
                 rss_sum, bytes_total, rank)
        rows.append({
            "candidate": candidate, "resolved": resolved,
            "charged_seconds": round(charged, 6), "rss_missing": rss_missing,
            "peak_rss_sum_bytes": rss_sum, "profiling_input_bytes": bytes_total,
            "fixed_order_rank": rank, "score": list(score),
            "records": [record["record_path"] for record in records],
        })
    selected = min(rows, key=lambda row: tuple(row["score"]))["candidate"]
    value = {
        "task": "D1P-10", "status": "ALTERNATIVE_SELECTED_AND_FROZEN",
        "selected": selected, "radix": RADIX[selected],
        "selected_at_utc": utc_now(),
        "profile_ledger": {"path": relative(ledger_path), "sha256": sha256(ledger_path)},
        "input_manifest": {"path": relative(args.manifest), "sha256": sha256(args.manifest)},
        "selection_rule": manifest["candidate_pool"]["selection_rule"],
        "ranking": sorted(rows, key=lambda row: tuple(row["score"])),
        "no_post_primary_tuning": True,
        "does_not_establish": "range constraints are the bottleneck",
        "research_verdict": "UNKNOWN",
    }
    write_json(output, value)
    print(json.dumps({"status": value["status"], "selected": selected,
                      "ranking": [row["candidate"] for row in value["ranking"]]}, sort_keys=True))
    return 0


def validate(args) -> int:
    output = args.output.resolve()
    ledger_path = args.ledger.resolve()
    if output.exists() or ledger_path.exists():
        raise FileExistsError("fresh validation output and ledger required")
    output.mkdir(parents=True)
    selection_path = args.selection.resolve()
    selection = json.loads(selection_path.read_text())
    selected = selection["selected"]
    manifest, _ = verify_manifest(args.manifest.resolve())
    runner = load_runner()
    monitor = runner.D1P05.MacProcessTreeMonitor()
    solver = args.solver.resolve()
    if sha256(solver) != EXPECTED_SOLVER:
        raise RuntimeError("solver identity mismatch")
    schedule = []
    for item in manifest["validation"]["controls"]:
        schedule.append({**item, "validation_kind": "control"})
    for item in manifest["validation"]["range_boundaries"][selected]:
        schedule.append({**item, "validation_kind": "range_boundary"})
    for item in manifest["validation"]["special"]:
        schedule.append({**item, "validation_kind": "t22_lost_equality"})
    for item in manifest["validation"]["propagation_equivalence"]:
        schedule.append({**item, "validation_kind": "propagation_equivalence"})
    if len(schedule) != 32 or len(schedule) > 70:
        raise RuntimeError(f"unexpected validation schedule: {len(schedule)}")
    records = []
    stop_reason = None
    started = time.monotonic()
    for index, item in enumerate(schedule, 1):
        if index * VALIDATION_SECONDS > 2100.0:
            stop_reason = "validation budget exhausted"
            break
        name = item.get("cell", item.get("name", f"item_{index}"))
        record = execute_call(
            runner, index=index, phase="validation",
            name=f"{item['validation_kind']}__{name}", item=item,
            seconds=VALIDATION_SECONDS, solver=solver,
            logs=output / "calls", monitor=monitor,
        )
        expected = item["expected"].upper()
        record.update({
            "validation_kind": item["validation_kind"], "expected": expected,
            "passed": record["result"] == expected,
        })
        if "cell" in item:
            record["cell"] = item["cell"]
        runner.write_json(ROOT / record["record_path"], record)
        records.append(record)
        if record["status"] in INFRA_FAILURE:
            stop_reason = f"infrastructure failure at call {index}: {record['status']}"
            break
    controls = [r for r in records if r["validation_kind"] == "control"]
    ranges = [r for r in records if r["validation_kind"] == "range_boundary"]
    lost = [r for r in records if r["validation_kind"] == "t22_lost_equality"]
    propagation = [r for r in records if r["validation_kind"] == "propagation_equivalence"]
    control_pass = len(controls) == 2 and all(r["passed"] for r in controls)
    alternative_eligible = control_pass and len(ranges) == 4 and all(r["passed"] for r in ranges)
    propagation_eligible = (control_pass and len(lost) == 1 and lost[0]["passed"]
                            and len(propagation) == 25 and all(r["passed"] for r in propagation))
    ledger = {
        "task": "D1P-10", "phase": "controls_and_transformation_validation",
        "status": "COMPLETE" if len(records) == 32 and stop_reason is None else "STOPPED",
        "recorded_at_utc": utc_now(), "stop_reason": stop_reason,
        "selection": {"path": relative(selection_path), "sha256": sha256(selection_path),
                      "selected": selected},
        "manifest": {"path": relative(args.manifest), "sha256": sha256(args.manifest)},
        "limits": {"calls_max": 70, "planned_calls": 32,
                   "seconds_per_call": VALIDATION_SECONDS,
                   "aggregate_seconds": 2100.0},
        "records": records,
        "counts": {"planned": 32, "attempted": len(records),
                   "passed": sum(r["passed"] for r in records)},
        "eligibility": {
            "baseline": control_pass,
            "propagated_cells": propagation_eligible,
            "alternative": alternative_eligible,
        },
        "solver_call_elapsed_seconds": round(sum(r["elapsed_seconds"] for r in records), 6),
        "phase_elapsed_seconds": round(time.monotonic() - started, 6),
        "universal_arguments": {
            "range": "protocol Section 4.1; solver boundary calls are supplemental regressions",
            "propagation": "protocol Section 4.2; 25 XOR calls validate this exact serialization",
        },
        "research_verdict": "UNKNOWN",
    }
    write_json(output / "validation-ledger.json", ledger)
    write_json(ledger_path, ledger)
    print(json.dumps({"status": ledger["status"], "attempted": len(records),
                      "passed": ledger["counts"]["passed"],
                      "eligibility": ledger["eligibility"],
                      "seconds": ledger["solver_call_elapsed_seconds"]}, sort_keys=True))
    return 0 if ledger["status"] == "COMPLETE" and all(ledger["eligibility"].values()) else 2


def primary_schedule(manifest: dict[str, Any], selected: str) -> list[dict[str, Any]]:
    schedule = []
    for obligation in OBLIGATIONS:
        item = next(row for row in manifest["baseline"] if row["obligation"] == obligation)
        schedule.append({"arm": "baseline", "obligation": obligation, "items": [item]})
    for obligation in OBLIGATIONS:
        schedule.append({"arm": "propagated_cells", "obligation": obligation,
                         "items": manifest["propagated"][obligation]})
    for obligation in OBLIGATIONS:
        item = next(row for row in manifest["candidates"][selected]
                    if row["obligation"] == obligation)
        schedule.append({"arm": "alternative", "obligation": obligation, "items": [item]})
    return schedule


def freeze_main(args) -> int:
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"fresh main freeze required: {output}")
    selection_path = args.selection.resolve()
    selection = json.loads(selection_path.read_text())
    validation_path = args.validation_ledger.resolve()
    validation = json.loads(validation_path.read_text())
    if validation.get("status") != "COMPLETE":
        raise RuntimeError("validation phase did not complete")
    manifest, checked = verify_manifest(args.manifest.resolve())
    selected = selection["selected"]
    schedule = primary_schedule(manifest, selected)
    frozen_inputs = [item for slot in schedule for item in slot["items"]]
    value = {
        "task": "D1P-10", "status": "MAIN_COMPARISON_FROZEN_BEFORE_PRIMARY_RESULT",
        "frozen_at_utc": utc_now(), "repository_head": manifest["repository_head"],
        "scope": manifest["scope"],
        "selection": {"path": relative(selection_path), "sha256": sha256(selection_path),
                      "selected": selected, "radix": RADIX[selected]},
        "validation": {"path": relative(validation_path), "sha256": sha256(validation_path),
                       "eligibility": validation["eligibility"]},
        "manifest": {"path": relative(args.manifest), "sha256": sha256(args.manifest),
                     "items_checked": checked},
        "solver": {"path": str(args.solver.resolve()), "sha256": sha256(args.solver),
                   "arguments": list(SOLVER_ARGUMENTS)},
        "limits": {"obligations": 4, "arms": 3,
                   "seconds_per_arm_obligation": UNSPLIT_SECONDS,
                   "partition_cell_seconds": CELL_SECONDS,
                   "partition_cells": 25, "aggregate_seconds": 3600.0,
                   "sequential": True, "attempts_per_query": 1},
        "schedule": schedule,
        "frozen_input_count": len(frozen_inputs),
        "frozen_input_order_sha256": sha256_bytes("".join(
            item["sha256"] + "\n" for item in frozen_inputs
        ).encode()),
        "frozen_files": [
            {"path": relative(path), "sha256": sha256(path)}
            for path in (Path(__file__), TESTS, PROTOCOL, RESOURCE_POLICY,
                         D1P07_RUNNER, args.manifest.resolve(), selection_path,
                         validation_path)
        ],
        "stop_rules": [
            "no candidate or input change after this freeze",
            "partition SAT requires original-cone/case/goal reconstruction validation",
            "partition UNSAT requires all 25 cells UNSAT",
            "missing, timeout, invalid, or unrun cell makes aggregate UNKNOWN",
            "no unused budget transfer between phases or slots",
        ],
        "research_verdict": "UNKNOWN",
    }
    if sha256(args.solver) != EXPECTED_SOLVER:
        raise RuntimeError("solver identity mismatch")
    write_json(output, value)
    print(json.dumps({"status": value["status"], "selected": selected,
                      "inputs": len(frozen_inputs), "slots": len(schedule)}, sort_keys=True))
    return 0


MODEL_RE = re.compile(r"\(w(\d+)\s+(?:#f(\d+)m\d+|\(as ff(\d+) \(_ FiniteField \d+\)\))\)")


def parse_model(path: Path) -> dict[int, int]:
    text = path.read_text(errors="replace")
    values = {}
    for witness, compact, old in MODEL_RE.findall(text):
        values[int(witness)] = int(compact or old) % P
    return values


def eval_poly(poly: dict[tuple[int, ...], int], values: dict[int, int]) -> int:
    total = 0
    for monomial, coefficient in poly.items():
        term = coefficient % P
        for witness in monomial:
            term = term * values[witness] % P
        total = (total + term) % P
    return total


def eval_expression(expression: Iterable[tuple[int, list[int]]], values: dict[int, int]) -> int:
    return eval_poly(normalize(expression), values)


def check_original_cone(indexed: list[tuple[int, tuple]], values: dict[int, int]) -> list[str]:
    failures = []
    blocks: dict[int, list[int]] = {}
    for source, opcode in indexed:
        kind = opcode[0]
        try:
            if kind == "assert":
                if eval_expression(opcode[1], values) != 0:
                    failures.append(f"assert:{source}")
            elif kind == "range":
                if eval_expression(opcode[1], values) >= 2 ** opcode[2]:
                    failures.append(f"range:{source}")
            elif kind == "init":
                blocks[opcode[1]] = [eval_expression(item, values) for item in opcode[2]]
            elif kind in ("read", "write"):
                block = opcode[1]
                index = eval_expression(opcode[3] if kind == "read" else opcode[2], values)
                if block not in blocks or index >= len(blocks[block]):
                    failures.append(f"memory-index:{source}")
                elif kind == "read":
                    if eval_expression(opcode[2], values) != blocks[block][index]:
                        failures.append(f"read:{source}")
                else:
                    blocks[block][index] = eval_expression(opcode[3], values)
        except KeyError as exc:
            failures.append(f"missing-witness:{source}:w{exc.args[0]}")
    return failures


def cell_holds(cell: dict[str, Any], values: dict[int, int]) -> bool:
    records = {2: 4, 3: 5, 4: 5}
    observed = []
    for expected, stream in ((cell["left"], STREAMS[0]), (cell["right"], STREAMS[1])):
        active = values[stream["activation"]] != 0
        words = [values[witness] for witness in stream["words"]]
        first = words[0]
        predicates = {
            "inactive": not active,
            "active_empty": active and first not in records,
            "length_4": active and first == 2 and words[4] not in records,
            "length_5": active and first in (3, 4) and words[5] not in records,
            "truncated_8": active and (
                (first == 2 and words[4] in records)
                or (first in (3, 4) and words[5] in records)
            ),
        }
        matches = [name for name, holds in predicates.items() if holds]
        observed.append(len(matches) == 1 and matches[0] == expected)
    return all(observed)


def emitted_words(values: dict[int, int]) -> list[int]:
    records = {2: 4, 3: 5, 4: 5}
    emitted = []
    for stream in STREAMS:
        if values[stream["activation"]] == 0:
            continue
        ended = False
        remaining = 0
        for witness in stream["words"]:
            word = values[witness]
            length = records.get(word, 0)
            flag = not ended and (remaining != 0 or length != 0)
            if remaining == 0 and length == 0:
                ended = True
            if ended:
                remaining = 0
            elif remaining:
                remaining -= 1
            else:
                remaining = length - 1
            if flag:
                emitted.append(word)
    return emitted


def goal_holds(obligation: str, values: dict[int, int]) -> bool:
    if obligation == "cone":
        return True
    emitted = emitted_words(values)
    outer = [values[witness] for witness in OUTER]
    total = len(emitted)
    if obligation == "nonvacuous":
        return 1 <= total <= 8
    if obligation == "prefix":
        return total > 8 or any(outer[index] != word
                                for index, word in enumerate(emitted[:8]))
    if obligation == "tail":
        return total <= 8 and any(outer[index] != 0 for index in range(total, 8))
    raise ValueError(obligation)


def validate_sat(stdout_path: Path, indexed: list[tuple[int, tuple]], witnesses: set[int],
                 obligation: str, cell: dict[str, Any] | None) -> dict[str, Any]:
    values = parse_model(stdout_path)
    missing = sorted(witnesses - set(values))
    failures = [] if missing else check_original_cone(indexed, values)
    case_ok = cell_holds(cell, values) if cell is not None and not missing else cell is None
    goal_ok = goal_holds(obligation, values) if not missing else False
    interface_present = all(witness in values for witness in (
        *OUTER, *(stream["activation"] for stream in STREAMS),
        *(word for stream in STREAMS for word in stream["words"]),
    ))
    valid = not missing and not failures and case_ok and goal_ok and interface_present
    return {
        "valid": valid, "model_values": len(values), "missing_witnesses": missing,
        "original_cone_failures": failures, "case_holds": case_ok,
        "original_goal_holds": goal_ok, "interface_bindings_present": interface_present,
        "scope": "original 620-operation selected cone, optional producer cell, and original goal only",
        "not_full_acir_or_proof": True,
    }


def unrun(item: dict[str, Any], arm: str, obligation: str, reason: str) -> dict[str, Any]:
    return {"arm": arm, "obligation": obligation, "input_path": item["path"],
            "input_sha256": item["sha256"], "attempts": 0, "status": "UNRUN",
            "result": "UNRUN", "reason": reason, "elapsed_seconds": 0.0,
            "peak_tree_rss_bytes": None}


def execute_main(args) -> int:
    output = args.output.resolve()
    ledger_path = args.ledger.resolve()
    if output.exists() or ledger_path.exists():
        raise FileExistsError("fresh main output and ledger required")
    output.mkdir(parents=True)
    freeze_path = args.freeze.resolve()
    freeze = json.loads(freeze_path.read_text())
    verify_frozen_files(freeze)
    manifest, _ = verify_manifest(ROOT / freeze["manifest"]["path"])
    _, _, _, _, indexed, witnesses = selected_cone()
    specializer = load_module("d1p10_main_specializer", SPECIALIZER)
    cells = {cell["id"]: cell for cell in specializer.cell_pairs()}
    runner = load_runner()
    monitor = runner.D1P05.MacProcessTreeMonitor()
    solver = Path(freeze["solver"]["path"])
    records = []
    comparison = []
    call_index = 0
    stop_reason = None
    campaign_started = time.monotonic()
    for slot in freeze["schedule"]:
        arm, obligation, items = slot["arm"], slot["obligation"], slot["items"]
        if not freeze["validation"]["eligibility"].get(arm, False):
            slot_records = [unrun(item, arm, obligation, "arm ineligible before main freeze")
                            for item in items]
            records.extend(slot_records)
            comparison.append({"arm": arm, "obligation": obligation,
                               "result": "UNKNOWN", "reason": "arm ineligible",
                               "records": slot_records})
            continue
        slot_started = time.monotonic()
        slot_records = []
        validated_sat = None
        for item_index, item in enumerate(items):
            elapsed_slot = time.monotonic() - slot_started
            remaining = UNSPLIT_SECONDS - elapsed_slot
            per_call = min(CELL_SECONDS, remaining) if arm == "propagated_cells" else remaining
            if per_call <= 0:
                slot_records.extend(unrun(rest, arm, obligation, "shared 300-second slot exhausted")
                                    for rest in items[item_index:])
                break
            call_index += 1
            name = f"{arm}__{obligation}"
            if arm == "propagated_cells":
                name += f"__{item['cell']}"
            record = execute_call(
                runner, index=call_index, phase="main", name=name, item=item,
                seconds=per_call, solver=solver, logs=output / "calls", monitor=monitor,
            )
            record.update({"arm": arm, "obligation": obligation})
            if arm == "propagated_cells":
                record.update({"cell": item["cell"], "cell_index": item["cell_index"],
                               "triviality": item["triviality"]})
            if record["result"] == "SAT":
                cell = cells[item["cell"]] if arm == "propagated_cells" else None
                validation = validate_sat(
                    ROOT / record["stdout_path"], indexed, witnesses, obligation, cell
                )
                record["sat_validation"] = validation
                if validation["valid"]:
                    record["validated_result"] = "SAT"
                    validated_sat = record
                else:
                    record["validated_result"] = "UNKNOWN"
                    record["result"] = "UNKNOWN"
            else:
                record["validated_result"] = record["result"]
            runner.write_json(ROOT / record["record_path"], record)
            slot_records.append(record)
            if record["status"] in INFRA_FAILURE:
                stop_reason = f"infrastructure failure at main call {call_index}: {record['status']}"
                break
            if validated_sat is not None and arm == "propagated_cells":
                slot_records.extend(unrun(rest, arm, obligation, "validated SAT cell resolved partition")
                                    for rest in items[item_index + 1:])
                break
        records.extend(slot_records)
        attempted = [record for record in slot_records if record["attempts"] == 1]
        if validated_sat is not None:
            aggregate = "SAT"
            reason = "validated SAT assignment"
        elif arm == "propagated_cells" and len(attempted) == 25 and all(
                record["validated_result"] == "UNSAT" for record in attempted):
            aggregate = "UNSAT"
            reason = "all 25 cells UNSAT"
        elif arm != "propagated_cells" and len(attempted) == 1 and attempted[0]["validated_result"] == "UNSAT":
            aggregate = "UNSAT"
            reason = "solver UNSAT"
        else:
            aggregate = "UNKNOWN"
            reason = "one or more required results unresolved, invalid, or unrun"
        comparison.append({
            "arm": arm, "obligation": obligation, "result": aggregate,
            "reason": reason,
            "slot_elapsed_seconds": round(time.monotonic() - slot_started, 6),
            "solver_call_elapsed_seconds": round(sum(r["elapsed_seconds"] for r in attempted), 6),
            "attempted": len(attempted),
            "counts": dict(Counter(r["validated_result"] for r in attempted)),
            "peak_tree_rss_bytes": max((r["peak_tree_rss_bytes"] or 0 for r in attempted), default=0) or None,
            "triviality_counts": (dict(Counter(r.get("triviality") for r in attempted))
                                   if arm == "propagated_cells" else None),
        })
        if stop_reason is not None:
            break
    # Preserve omitted slots after an infrastructure stop.
    completed_keys = {(row["arm"], row["obligation"]) for row in comparison}
    if stop_reason:
        for slot in freeze["schedule"]:
            key = (slot["arm"], slot["obligation"])
            if key not in completed_keys:
                pending = [unrun(item, *key, reason=stop_reason) for item in slot["items"]]
                records.extend(pending)
                comparison.append({"arm": key[0], "obligation": key[1],
                                   "result": "UNKNOWN", "reason": stop_reason,
                                   "attempted": 0, "counts": {"UNRUN": len(pending)},
                                   "slot_elapsed_seconds": 0.0,
                                   "solver_call_elapsed_seconds": 0.0,
                                   "peak_tree_rss_bytes": None,
                                   "triviality_counts": None})
    call_elapsed = sum(record["elapsed_seconds"] for record in records if record["attempts"] == 1)
    ledger = {
        "task": "D1P-10", "phase": "main_comparison",
        "status": "COMPLETE" if len(comparison) == 12 and stop_reason is None else "STOPPED",
        "recorded_at_utc": utc_now(), "stop_reason": stop_reason,
        "freeze": {"path": relative(freeze_path), "sha256": sha256(freeze_path)},
        "selected_alternative": freeze["selection"],
        "limits": freeze["limits"], "records": records, "comparison": comparison,
        "counts": {"solver_calls": sum(r["attempts"] for r in records),
                   "unrun": sum(r["attempts"] == 0 for r in records)},
        "solver_call_elapsed_seconds": round(call_elapsed, 6),
        "campaign_elapsed_seconds": round(time.monotonic() - campaign_started, 6),
        "interpretation": (
            "SAT/UNSAT concern only the historical selected cone and stated goal; "
            "UNKNOWN is retained for every broader producer/proof/consumer/security claim"
        ),
        "research_verdict": "UNKNOWN",
    }
    write_json(output / "main-ledger.json", ledger)
    write_json(ledger_path, ledger)
    print(json.dumps({"status": ledger["status"], "calls": ledger["counts"]["solver_calls"],
                      "seconds": ledger["solver_call_elapsed_seconds"],
                      "comparison": [{"arm": r["arm"], "obligation": r["obligation"],
                                      "result": r["result"]} for r in comparison]}, sort_keys=True))
    return 0 if ledger["status"] == "COMPLETE" else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.set_defaults(function=prepare)
    p = sub.add_parser("preflight")
    p.add_argument("--solver", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.set_defaults(function=preflight)
    p = sub.add_parser("freeze-profile")
    p.add_argument("--solver", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--preflight", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.set_defaults(function=freeze_profile)
    p = sub.add_parser("profile")
    p.add_argument("--freeze", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--ledger", type=Path, required=True)
    p.set_defaults(function=profile)
    p = sub.add_parser("select")
    p.add_argument("--profile-ledger", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.set_defaults(function=select_candidate)
    p = sub.add_parser("validate")
    p.add_argument("--solver", type=Path, required=True)
    p.add_argument("--selection", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--ledger", type=Path, required=True)
    p.set_defaults(function=validate)
    p = sub.add_parser("freeze-main")
    p.add_argument("--solver", type=Path, required=True)
    p.add_argument("--selection", type=Path, required=True)
    p.add_argument("--validation-ledger", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.set_defaults(function=freeze_main)
    p = sub.add_parser("execute-main")
    p.add_argument("--freeze", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--ledger", type=Path, required=True)
    p.set_defaults(function=execute_main)
    args = parser.parse_args()
    return args.function(args)


if __name__ == "__main__":
    raise SystemExit(main())

