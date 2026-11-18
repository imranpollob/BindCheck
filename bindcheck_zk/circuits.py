from __future__ import annotations

import dataclasses
import hashlib
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
    temporary_artifacts: pathlib.Path | None = None


def _expand_circom_name(name: str, declarations: dict[str, tuple[int, ...]]) -> list[str]:
    dimensions = declarations.get(name)
    if dimensions is None or not dimensions:
        return [name]
    expanded = [name]
    for size in dimensions:
        expanded = [f"{prefix}[{index}]" for prefix in expanded for index in range(size)]
    return expanded


def is_entry_circuit(path: pathlib.Path) -> bool:
    """Return whether a source declares an analyzable program entry point."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if path.suffix.lower() == ".circom":
        return bool(re.search(r"\bcomponent\s+main\b", text))
    if path.suffix.lower() == ".nr":
        return bool(re.search(r"\bfn\s+main\s*\(", text))
    return False


def _template_body(text: str, name: str) -> str | None:
    match = re.search(rf"\btemplate\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", text)
    if not match:
        return None
    opening = text.find("{", match.start())
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1:index]
    return None


def parse_circom(path: pathlib.Path, root: pathlib.Path) -> Circuit:
    text = path.read_text(encoding="utf-8", errors="replace")
    main_decl = re.search(
        r"\bcomponent\s+main\s*(?:\{\s*public\s*\[(.*?)\]\s*\})?\s*=\s*([A-Za-z_]\w*)\s*\(",
        text,
        re.S,
    )
    main_template = main_decl.group(2) if main_decl else None
    scoped = _template_body(text, main_template) if main_template else None
    declaration_text = scoped if scoped is not None else text
    declarations: dict[str, tuple[int, ...]] = {}
    outputs: list[str] = []
    notes: list[str] = []
    complete = True
    for match in re.finditer(
        r"\bsignal\s+(?:private\s+)?(input|output)\s+([A-Za-z_]\w*)\s*((?:\[[^\]\n]*\]\s*)*);",
        declaration_text,
    ):
        direction, name, raw_dimensions = match.groups()
        if not re.fullmatch(r"(?:\[\s*\d+\s*\]\s*)*", raw_dimensions):
            if direction == "output":
                notes.append(f"public output extent for {name} requires compiled metadata")
                complete = False
            continue
        dimensions = tuple(int(value) for value in re.findall(r"\d+", raw_dimensions))
        declarations[name] = dimensions
        if direction == "output":
            outputs.extend(_expand_circom_name(name, declarations))
    public_order: list[str] = []
    if main_decl and main_decl.group(1) is not None:
        for name in re.findall(r"\b[A-Za-z_]\w*\b", main_decl.group(1)):
            size = declarations.get(name)
            if size is None:
                public_order.append(name)
                notes.append(f"public declaration for {name} was not recovered")
                complete = False
            elif size:
                public_order.extend(_expand_circom_name(name, declarations))
            else:
                public_order.append(name)
    else:
        notes.append("component main public list was not recovered")
        complete = False
    if main_decl and scoped is None:
        notes.append(f"main template body {main_template} was not recovered in this source")
        complete = False
    # Circom outputs precede public inputs in witness/public-signal order.  We
    # keep this explicit rather than silently treating all declarations alike.
    if outputs:
        public_order = outputs + [name for name in public_order if name not in outputs]
        notes.append("declared outputs included before public inputs")
    components: list[dict[str, Any]] = []
    component_text = scoped if scoped is not None else text
    for output in re.finditer(r"\b([A-Za-z_]\w*)\.out\s*(?:===|==>)\s*([A-Za-z_]\w*)", component_text):
        component, commitment = output.groups()
        inputs = {
            int(index): value
            for index, value in re.findall(
                rf"\b{re.escape(component)}\.inputs?\s*\[\s*(\d+)\s*\]\s*<==\s*([^;]+);", component_text
            )
        }
        if inputs:
            components.append({
                "name": component,
                "commitment": commitment,
                "inputs": [inputs[index].strip() for index in sorted(inputs)],
                "line": component_text.count("\n", 0, output.start()) + 1,
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
    supported_scalar = re.compile(r"^(?:Field|bool|u\d+|i\d+)$")

    def flatten_width(type_text: str) -> int | None:
        value = type_text.strip()
        if supported_scalar.fullmatch(value):
            return 1
        array = re.fullmatch(r"\[(.*);\s*(\d+)\s*\]", value, re.S)
        if array:
            inner = flatten_width(array.group(1))
            return inner * int(array.group(2)) if inner is not None else None
        return None

    if main:
        for part in re.split(r",(?=(?:[^\[]|\[[^\]]*\])*$)", main.group(1)):
            if "pub" not in part:
                continue
            name = re.search(r"\b([A-Za-z_]\w*)\s*:", part)
            if not name:
                complete = False
                notes.append("public Noir parameter name unresolved")
                continue
            type_text = re.sub(r"^pub\s+", "", part.split(":", 1)[1].strip())
            width = flatten_width(type_text)
            if width is None:
                complete = False
                notes.append(
                    f"public Noir parameter {name.group(1)} has an unsupported composite type: {type_text}"
                )
                order.append(name.group(1))
            elif width == 1:
                order.append(name.group(1))
            else:
                order.extend(f"{name.group(1)}[{index}]" for index in range(width))
    else:
        notes.append("Noir main signature not recovered")
        complete = False
    return Circuit(
        path=path,
        relative_path=path.relative_to(root).as_posix(),
        language="noir",
        sha256=sha256_file(path),
        public_order=order,
        public_count=len(order) if order and complete else None,
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
    prime = int.from_bytes(header[4:4 + field_size], "little")
    cursor = 4 + field_size
    n_wires, n_pub_out, n_pub_in, n_prv_in = struct.unpack_from("<IIII", header, cursor)
    cursor += 16
    n_labels = struct.unpack_from("<Q", header, cursor)[0]
    cursor += 8
    n_constraints = struct.unpack_from("<I", header, cursor)[0]
    constraints_raw = sections[2]
    cursor = 0
    constraints: list[set[int]] = []
    constraint_terms: list[list[list[dict[str, int]]]] = []
    for _ in range(n_constraints):
        wires: set[int] = set()
        linear_combinations: list[list[dict[str, int]]] = []
        for _lc in range(3):
            if cursor + 4 > len(constraints_raw):
                raise ValueError("truncated R1CS linear combination")
            terms = struct.unpack_from("<I", constraints_raw, cursor)[0]
            cursor += 4
            parsed_terms: list[dict[str, int]] = []
            for _term in range(terms):
                if cursor + 4 + field_size > len(constraints_raw):
                    raise ValueError("truncated R1CS term")
                wire = struct.unpack_from("<I", constraints_raw, cursor)[0]
                coefficient = int.from_bytes(
                    constraints_raw[cursor + 4:cursor + 4 + field_size], "little"
                )
                cursor += 4 + field_size
                parsed_terms.append({"wire": wire, "coefficient": coefficient})
                if wire and coefficient % prime:
                    wires.add(wire)
            linear_combinations.append(parsed_terms)
        constraints.append(wires)
        constraint_terms.append(linear_combinations)
    return {
        "version": version,
        "field_size": field_size,
        "prime": prime,
        "n_wires": n_wires,
        "n_public_outputs": n_pub_out,
        "n_public_inputs": n_pub_in,
        "n_private_inputs": n_prv_in,
        "n_labels": n_labels,
        "n_constraints": n_constraints,
        "constraints": constraints,
        "constraint_terms": constraint_terms,
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
        "r1cs": {
            key: value for key, value in parsed.items()
            if key not in {"constraints", "constraint_terms"}
        },
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


def _tree_digest(root: pathlib.Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        digest.update(sha256_file(path).encode() + b"  " + relative.encode() + b"\n")
        count += 1
    return digest.hexdigest(), count


def _vendor_libraries() -> dict[str, dict[str, Any]]:
    tool_root = pathlib.Path(__file__).resolve().parents[1]
    lock_path = pathlib.Path(__file__).with_name("vendor-lock.json")
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    output: dict[str, dict[str, Any]] = {}
    for item in lock.get("libraries", []):
        installed = tool_root / item["install_path"]
        if not installed.is_dir():
            continue
        observed_tree, observed_files = _tree_digest(installed)
        if observed_tree != item.get("tree_sha256") or observed_files != item.get("files"):
            continue
        output[item["name"]] = {**item, "path": installed}
    return output


def _dependency_versions(root: pathlib.Path) -> dict[str, list[dict[str, str]]]:
    output: dict[str, list[dict[str, str]]] = defaultdict(list)
    for manifest in sorted(root.rglob("package.json")):
        if "node_modules" in manifest.parts:
            continue
        try:
            value = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for section in ("dependencies", "devDependencies", "peerDependencies"):
            for name, version in value.get(section, {}).items():
                output[name].append({
                    "manifest": manifest.relative_to(root).as_posix(),
                    "version": str(version),
                    "section": section,
                })
    return output


def _include_package(raw: str) -> tuple[str | None, str | None]:
    normalized = raw.replace("\\", "/")
    marker = "node_modules/"
    suffix = normalized.split(marker, 1)[1] if marker in normalized else normalized.lstrip("./")
    parts = [part for part in suffix.split("/") if part not in {"", ".", ".."}]
    if not parts:
        return None, None
    if parts[0].startswith("@") and len(parts) > 1:
        return "/".join(parts[:2]), "/".join(parts[2:])
    return parts[0], "/".join(parts[1:])


def resolve_circom_includes(
    circuit: Circuit, root: pathlib.Path, overlay: pathlib.Path
) -> tuple[list[pathlib.Path], list[dict[str, Any]]]:
    dependency_versions = _dependency_versions(root)
    vendors = _vendor_libraries()
    include_roots: list[pathlib.Path] = []
    records: list[dict[str, Any]] = []
    queue = [circuit.path]
    visited_files: set[pathlib.Path] = set()
    visited_edges: set[tuple[pathlib.Path, str]] = set()
    while queue:
        source_path = queue.pop(0).resolve()
        if source_path in visited_files:
            continue
        visited_files.add(source_path)
        try:
            text = source_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        includes = re.findall(r"\binclude\s+[\"']([^\"']+)[\"']\s*;", text)
        for raw in includes:
            edge = (source_path, raw)
            if edge in visited_edges:
                continue
            visited_edges.add(edge)
            direct = (source_path.parent / raw).resolve()
            try:
                from_path = source_path.relative_to(root).as_posix()
            except ValueError:
                from_path = str(source_path)
            if direct.is_file():
                try:
                    direct.relative_to(root)
                    direct_source = "circuit-relative"
                except ValueError:
                    direct_source = "dependency-relative"
                records.append({"include": raw, "from": from_path, "source": direct_source, "path": str(direct)})
                queue.append(direct)
                continue
            package, within = _include_package(raw)
            candidates: list[tuple[pathlib.Path, str, dict[str, Any]]] = []
            if package:
                for ancestor in [circuit.path.parent, *circuit.path.parents]:
                    if ancestor == root.parent:
                        break
                    candidates.append((ancestor / "node_modules" / package, "repository-node-modules", {}))
                    candidates.append((ancestor / package, "repository-library", {}))
                for base in (root / "lib", root / "libs", root / "circuits", root / "packages"):
                    candidates.append((base / package, "repository-common-layout", {}))
                if package in vendors:
                    vendor = vendors[package]
                    candidates.append((vendor["path"], "vendored-pinned", {
                        "version": vendor["version"],
                        "tree_sha256": vendor["tree_sha256"],
                        "source_pin": vendor["source"],
                    }))
            chosen: tuple[pathlib.Path, pathlib.Path, str, dict[str, Any]] | None = None
            for package_root, source, metadata in candidates:
                target = package_root / within if within else package_root
                if target.is_file():
                    chosen = (package_root.resolve(), target.resolve(), source, metadata)
                    break
            if chosen is None:
                records.append({
                    "include": raw,
                    "from": from_path,
                    "source": "unresolved",
                    "package": package,
                    "declared_dependencies": dependency_versions.get(package or "", []),
                })
                continue
            package_root, target, source, metadata = chosen
            leading = len(re.match(r"^(?:\.\./)*", raw).group(0).split("../")) - 1
            base = overlay / f"include-{len(include_roots)}" / pathlib.Path(*(["level"] * leading))
            base.mkdir(parents=True, exist_ok=True)
            normalized = raw.replace("\\", "/")
            remainder = normalized
            while remainder.startswith("../"):
                remainder = remainder[3:]
            package_prefix = remainder.split(package, 1)[0] if package and package in remainder else ""
            link_parent = (base / pathlib.Path(*([".."] * leading)) / package_prefix).resolve()
            link_parent.mkdir(parents=True, exist_ok=True)
            link = link_parent / package if package else link_parent / "library"
            if not link.exists():
                link.symlink_to(package_root, target_is_directory=True)
            include_roots.append(base)
            records.append({
                "include": raw,
                "from": from_path,
                "source": source,
                "package": package,
                "path": str(package_root),
                "declared_dependencies": dependency_versions.get(package or "", []),
                **metadata,
            })
            queue.append(target)
    return include_roots, records


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
    # A repository can contain independent circuits with the same basename.
    # Only reuse a sibling artifact pair. Otherwise build the selected source.
    existing_r1cs = circuit.path.with_suffix(".r1cs")
    existing_sym = circuit.path.with_suffix(".sym")
    if existing_r1cs.is_file() and existing_sym.is_file() and existing_r1cs.stat().st_size <= 500_000_000:
        circuit.r1cs = existing_r1cs
        circuit.sym = existing_sym
        circuit.compiled = True
        circuit.build = {"kind": "existing", "r1cs": str(existing_r1cs), "sym": str(existing_sym)}
        apply_compiled_public_metadata(circuit)
        return
    binary = _circom_binary()
    if binary is None:
        circuit.build = {"kind": "skipped", "reason": "CIRCOM_NOT_AVAILABLE"}
        return
    with tempfile.TemporaryDirectory(prefix="bindcheck-zk-circom-") as temp_name:
        temp = pathlib.Path(temp_name)
        argv = [binary, str(circuit.path), "--r1cs", "--sym", "-o", str(temp)]
        overlay = temp / "includes"
        include_candidates, include_resolution = resolve_circom_includes(circuit, root, overlay)
        include_candidates.extend([root / "node_modules", circuit.path.parent / "node_modules"])
        seen: set[pathlib.Path] = set()
        for include in include_candidates:
            if include.is_dir() and include.resolve() not in seen:
                seen.add(include.resolve())
                argv.extend(["-l", str(include)])
        record = run(argv, cwd=root, timeout=min(timeout, budget.remaining))
        circuit.build = record
        circuit.build["kind"] = "compile"
        circuit.build["include_resolution"] = include_resolution
        if record["exit_status"] == 0 and not record["timed_out"]:
            r1cs = temp / (circuit.path.stem + ".r1cs")
            sym = temp / (circuit.path.stem + ".sym")
            if r1cs.is_file() and sym.is_file():
                retained = pathlib.Path(tempfile.mkdtemp(prefix="bindcheck-zk-r1cs-"))
                circuit.temporary_artifacts = retained
                circuit.r1cs = pathlib.Path(shutil.copy2(r1cs, retained / r1cs.name))
                circuit.sym = pathlib.Path(shutil.copy2(sym, retained / sym.name))
                circuit.compiled = True
                apply_compiled_public_metadata(circuit)
