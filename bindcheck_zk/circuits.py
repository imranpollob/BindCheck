from __future__ import annotations

import dataclasses
import json
import os
import pathlib
import re
import shutil
import struct
import tempfile
from collections import defaultdict, deque
from typing import Any

from .models import Budget, sha256_file
from .subprocesses import run


@dataclasses.dataclass
class Circuit:
    path: pathlib.Path
    relative_path: str
    language: str
    sha256: str
    public_order: list[str]
    public_count: int | None
    order_complete: bool
    parse_notes: list[str]
    components: list[dict[str, Any]]
    r1cs: pathlib.Path | None = None
    sym: pathlib.Path | None = None
    compiled: bool = False
    build: dict[str, Any] | None = None


def _expand_circom_name(name: str, declarations: dict[str, int]) -> list[str]:
    size = declarations.get(name)
    if size is None:
        return [name]
    return [f"{name}[{index}]" for index in range(size)]


def parse_circom(path: pathlib.Path, root: pathlib.Path) -> Circuit:
    text = path.read_text(encoding="utf-8", errors="replace")
    declarations: dict[str, int] = {}
    declaration_order: list[str] = []
    outputs: list[str] = []
    for match in re.finditer(r"\bsignal\s+(input|output)\s+([A-Za-z_]\w*)\s*(?:\[\s*(\d+)\s*\])?\s*;", text):
        direction, name, raw_size = match.groups()
        declarations[name] = int(raw_size) if raw_size else 0
        declaration_order.append(name)
        if direction == "output":
            outputs.extend(_expand_circom_name(name, declarations) if raw_size else [name])
    main = re.search(r"\bcomponent\s+main\s*\{\s*public\s*\[(.*?)\]\s*\}\s*=", text, re.S)
    public_order: list[str] = []
    notes: list[str] = []
    complete = True
    if main:
        for name in re.findall(r"\b[A-Za-z_]\w*\b", main.group(1)):
            size = declarations.get(name)
            if size is None:
                public_order.append(name)
                notes.append(f"public declaration for {name} was not recovered")
                complete = False
            elif size:
                public_order.extend(f"{name}[{index}]" for index in range(size))
            else:
                public_order.append(name)
    else:
        notes.append("component main public list was not recovered")
        complete = False
    # Circom outputs precede public inputs in witness/public-signal order.  We
    # keep this explicit rather than silently treating all declarations alike.
    if outputs:
        public_order = outputs + [name for name in public_order if name not in outputs]
        notes.append("declared outputs included before public inputs")
    components: list[dict[str, Any]] = []
    for output in re.finditer(r"\b([A-Za-z_]\w*)\.out\s*(?:===|==>)\s*([A-Za-z_]\w*)", text):
        component, commitment = output.groups()
        inputs = {
            int(index): value
            for index, value in re.findall(
                rf"\b{re.escape(component)}\.inputs?\s*\[\s*(\d+)\s*\]\s*<==\s*([^;]+);", text
            )
        }
        if inputs:
            components.append({
                "name": component,
                "commitment": commitment,
                "inputs": [inputs[index].strip() for index in sorted(inputs)],
                "line": text.count("\n", 0, output.start()) + 1,
            })
    return Circuit(
        path=path,
        relative_path=path.relative_to(root).as_posix(),
        language="circom",
        sha256=sha256_file(path),
        public_order=public_order,
        public_count=len(public_order) if public_order else None,
        order_complete=complete,
        parse_notes=notes,
        components=components,
    )


def parse_noir(path: pathlib.Path, root: pathlib.Path) -> Circuit:
    text = path.read_text(encoding="utf-8", errors="replace")
    main = re.search(r"\bfn\s+main\s*\((.*?)\)\s*(?:->[^\{]+)?\{", text, re.S)
    order: list[str] = []
    notes: list[str] = []
    complete = True
    if main:
        for part in re.split(r",(?=(?:[^\[]|\[[^\]]*\])*$)", main.group(1)):
            if "pub" not in part:
                continue
            name = re.search(r"\b([A-Za-z_]\w*)\s*:", part)
            size = re.search(r";\s*(\d+)\s*\]", part)
            if not name:
                complete = False
                notes.append("public Noir parameter name unresolved")
                continue
            if size:
                order.extend(f"{name.group(1)}[{index}]" for index in range(int(size.group(1))))
            else:
                order.append(name.group(1))
    else:
        notes.append("Noir main signature not recovered")
        complete = False
    return Circuit(
        path=path,
        relative_path=path.relative_to(root).as_posix(),
        language="noir",
        sha256=sha256_file(path),
        public_order=order,
        public_count=len(order) if order else None,
        order_complete=complete,
        parse_notes=notes,
        components=[],
    )


def discover(root: pathlib.Path, paths: list[pathlib.Path]) -> list[Circuit]:
    output: list[Circuit] = []
    for path in paths:
        if path.suffix == ".circom":
            output.append(parse_circom(path, root))
        elif path.suffix == ".nr":
            output.append(parse_noir(path, root))
    return output


def parse_sym(path: pathlib.Path) -> tuple[dict[int, list[str]], dict[str, int]]:
    names: dict[int, list[str]] = defaultdict(list)
    by_name: dict[str, int] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = raw.split(",", 3)
        if len(parts) != 4:
            continue
        try:
            wire = int(parts[1])
        except ValueError:
            continue
        if wire < 0:
            continue
        name = parts[3]
        names[wire].append(name)
        by_name[name] = wire
    return names, by_name


def parse_r1cs(path: pathlib.Path) -> dict[str, Any]:
    data = path.read_bytes()
    if len(data) < 12 or data[:4] != b"r1cs":
        raise ValueError("not an R1CS binary")
    version, count = struct.unpack_from("<II", data, 4)
    offset = 12
    sections: dict[int, bytes] = {}
    for _ in range(count):
        if offset + 12 > len(data):
            raise ValueError("truncated R1CS section table")
        section_type, size = struct.unpack_from("<IQ", data, offset)
        offset += 12
        if offset + size > len(data):
            raise ValueError("truncated R1CS section")
        sections[section_type] = data[offset:offset + size]
        offset += size
    if 1 not in sections or 2 not in sections:
        raise ValueError("R1CS header or constraints section missing")
    header = sections[1]
    field_size = struct.unpack_from("<I", header, 0)[0]
    cursor = 4 + field_size
    n_wires, n_pub_out, n_pub_in, n_prv_in = struct.unpack_from("<IIII", header, cursor)
    cursor += 16
    n_labels = struct.unpack_from("<Q", header, cursor)[0]
    cursor += 8
    n_constraints = struct.unpack_from("<I", header, cursor)[0]
    constraints_raw = sections[2]
    cursor = 0
    constraints: list[set[int]] = []
    for _ in range(n_constraints):
        wires: set[int] = set()
        for _lc in range(3):
            if cursor + 4 > len(constraints_raw):
                raise ValueError("truncated R1CS linear combination")
            terms = struct.unpack_from("<I", constraints_raw, cursor)[0]
            cursor += 4
            for _term in range(terms):
                if cursor + 4 + field_size > len(constraints_raw):
                    raise ValueError("truncated R1CS term")
                wire = struct.unpack_from("<I", constraints_raw, cursor)[0]
                cursor += 4 + field_size
                if wire:
                    wires.add(wire)
        constraints.append(wires)
    return {
        "version": version,
        "field_size": field_size,
        "n_wires": n_wires,
        "n_public_outputs": n_pub_out,
        "n_public_inputs": n_pub_in,
        "n_private_inputs": n_prv_in,
        "n_labels": n_labels,
        "n_constraints": n_constraints,
        "constraints": constraints,
    }


def named_path(r1cs: pathlib.Path, sym: pathlib.Path, start: str, end: str, namespace: str) -> dict[str, Any] | None:
    parsed = parse_r1cs(r1cs)
    names, by_name = parse_sym(sym)
    variants = lambda value: [value, f"main.{value}"]
    start_name = next((value for value in variants(start) if value in by_name), None)
    end_name = next((value for value in variants(end) if value in by_name), None)
    if start_name is None or end_name is None:
        return None
    source, target = by_name[start_name], by_name[end_name]
    incident: dict[int, list[int]] = defaultdict(list)
    for index, wires in enumerate(parsed["constraints"]):
        for wire in wires:
            incident[wire].append(index)
    queue = deque([source])
    previous: dict[int, int | None] = {source: None}
    previous_constraint: dict[int, int] = {}
    while queue and target not in previous:
        wire = queue.popleft()
        for constraint in incident[wire]:
            for neighbour in parsed["constraints"][constraint]:
                if neighbour not in previous:
                    previous[neighbour] = wire
                    previous_constraint[neighbour] = constraint
                    queue.append(neighbour)
    if target not in previous:
        return None
    steps: list[dict[str, Any]] = []
    wire: int | None = target
    while wire is not None:
        steps.append({"wire": wire, "constraint": previous_constraint.get(wire), "names": names.get(wire, [])})
        wire = previous[wire]
    steps.reverse()
    interior = [name for step in steps[1:-1] for name in step["names"]]
    qualified = namespace if namespace.startswith("main.") else f"main.{namespace}"
    return {
        "length_wires": len(steps),
        "namespace": qualified,
        "namespace_ok": bool(interior) and all(name.startswith(qualified + ".") for name in interior),
        "path": steps,
        "r1cs": {key: value for key, value in parsed.items() if key != "constraints"},
    }


def _circom_binary() -> str | None:
    configured = os.environ.get("BINDCHECK_CIRCOM")
    if configured and pathlib.Path(configured).is_file():
        return configured
    found = shutil.which("circom")
    if found:
        return found
    repository_candidate = pathlib.Path(__file__).resolve().parents[1] / "tools" / "circom-src" / "target" / "release" / "circom"
    return str(repository_candidate) if repository_candidate.is_file() else None


def apply_compiled_public_metadata(circuit: Circuit) -> None:
    if circuit.r1cs is None or circuit.sym is None:
        return
    try:
        parsed = parse_r1cs(circuit.r1cs)
        names, _ = parse_sym(circuit.sym)
    except (OSError, ValueError, struct.error) as exc:
        circuit.parse_notes.append(f"compiled public metadata unavailable: {exc}")
        return
    count = parsed["n_public_outputs"] + parsed["n_public_inputs"]
    recovered: list[str] = []
    complete = True
    for wire in range(1, count + 1):
        candidates = [name for name in names.get(wire, []) if name.startswith("main.")]
        top_level = [name for name in candidates if "." not in name.removeprefix("main.")]
        chosen = (top_level or candidates or [None])[0]
        if chosen is None:
            complete = False
            recovered.append(f"<compiled-public-wire:{wire}>")
        else:
            recovered.append(chosen.removeprefix("main."))
    circuit.public_count = count
    if recovered:
        circuit.public_order = recovered
        circuit.order_complete = complete
    circuit.parse_notes.append("public count/order recovered from compiled R1CS and sym metadata")


def attach_or_build(circuit: Circuit, root: pathlib.Path, budget: Budget, timeout: float) -> None:
    candidates = list(root.rglob(circuit.path.stem + ".r1cs"))
    candidates = [path for path in candidates if path.stat().st_size <= 500_000_000]
    if candidates:
        chosen = min(candidates, key=lambda path: len(path.parts))
        sym = chosen.with_suffix(".sym")
        circuit.r1cs = chosen
        circuit.sym = sym if sym.is_file() else None
        circuit.compiled = circuit.sym is not None
        circuit.build = {"kind": "existing", "r1cs": str(chosen), "sym": str(sym) if sym.is_file() else None}
        if circuit.compiled:
            apply_compiled_public_metadata(circuit)
        return
    binary = _circom_binary()
    if binary is None:
        circuit.build = {"kind": "skipped", "reason": "CIRCOM_NOT_AVAILABLE"}
        return
    with tempfile.TemporaryDirectory(prefix="bindcheck-zk-circom-") as temp_name:
        temp = pathlib.Path(temp_name)
        argv = [binary, str(circuit.path), "--r1cs", "--sym", "-o", str(temp)]
        include_candidates = [root / "node_modules", circuit.path.parent / "node_modules"]
        for include in include_candidates:
            if include.is_dir():
                argv.extend(["-l", str(include)])
        record = run(argv, cwd=root, timeout=min(timeout, budget.remaining))
        circuit.build = record
        circuit.build["kind"] = "compile"
        if record["exit_status"] == 0 and not record["timed_out"]:
            r1cs = temp / (circuit.path.stem + ".r1cs")
            sym = temp / (circuit.path.stem + ".sym")
            if r1cs.is_file() and sym.is_file():
                retained = pathlib.Path(tempfile.mkdtemp(prefix="bindcheck-zk-r1cs-"))
                circuit.r1cs = pathlib.Path(shutil.copy2(r1cs, retained / r1cs.name))
                circuit.sym = pathlib.Path(shutil.copy2(sym, retained / sym.name))
                circuit.compiled = True
                apply_compiled_public_metadata(circuit)
