"""Producer extraction from printed ACIR (nargo 1.0.0-beta.14) through a hash-pinned adapter of the T22-v3 parser.

The adapter adds audits the old parser lacked: exactly one ACIR function, ABI-to-witness layout, and a structural
decomposition of flat RECURSIVE_AGGREGATION inputs checked against ABI witnesses. Anything outside this is Unsupported.
"""
import importlib.util
import itertools
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..artifacts import sha256_file

ROOT = Path(__file__).resolve().parents[3]
LEGACY = ROOT / "scripts/t22_v3_tailspec.py"
LEGACY_SHA256 = "81a1cd43cd3e6e735dc325535f05d9b2a88c6c9794b434ab53e834061ff700c8"  # frozen T22-v3 value


class Unsupported(Exception):
    pass


def _legacy():
    got = sha256_file(LEGACY)
    if got != LEGACY_SHA256:
        raise Unsupported(f"legacy ACIR parser hash mismatch: {got}")
    spec = importlib.util.spec_from_file_location("t22_v3_tailspec_pinned", LEGACY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_L = None


def legacy():
    global _L
    if _L is None:
        _L = _legacy()
    return _L


@dataclass
class Recursion:
    index: int                 # position among recursion calls
    vk: list                   # witness ids
    proof: list
    public_inputs: list        # expressions (term lists)
    key_hash: list             # expression
    predicate: list            # expression


@dataclass
class Program:
    ops: list
    public: list
    private: list
    abi: dict
    table: dict                # ABI path -> list of witness ids (parameters only)
    recursions: list
    unmodeled: list            # (blackbox name, outputs)
    path: str = ""
    notes: list = field(default_factory=list)


def _params(text, label):
    m = re.search(rf"^{label}: \[(.*)\]\s*$", text, re.M)
    if not m:
        raise Unsupported(f"missing {label}")
    body = m.group(1).strip()
    return [int(x.strip()[1:]) for x in body.split(",")] if body else []


def _abi_table(abi):
    L = legacy()
    wit = itertools.count(0)
    table = {}
    for p in abi["parameters"]:
        L.leaves(p["type"], p["name"], wit, table)
    return table


def load(acir_path, abi_path):
    text = Path(acir_path).read_text()
    nfunc = len(re.findall(r"^func \d+\s*$", text, re.M))
    if nfunc != 1:
        raise Unsupported(f"expected exactly one ACIR function, found {nfunc}")
    if re.search(r"^\s*CALL ", text, re.M):
        raise Unsupported("ACIR CALL opcode present")
    L = legacy()
    try:
        a = L.Acir(text)
    except L.Unsupported as e:
        raise Unsupported(str(e))
    abi = json.loads(Path(abi_path).read_text())
    abi = abi.get("abi", abi)
    private, public = _params(text, "private parameters"), _params(text, "public parameters")
    table = _abi_table(abi)
    # Layout audit: parameters flatten to w0..w(n-1) in ABI order, with public ABI parameters exactly the public list.
    expect_pub, n = [], 0
    for p in abi["parameters"]:
        ws = table[p["name"]]
        if p.get("visibility") == "public":
            expect_pub += ws
        n += len(ws)
    if sorted(private + public) != list(range(n)) or expect_pub != public:
        raise Unsupported("ABI/witness layout differs from sequential flattening")
    if abi.get("return_type"):
        raise Unsupported("return values not supported in D1-03")
    recs, notes = [], []
    for k, r in enumerate(a.recs):
        if not (isinstance(r, tuple) and r[0] == "flat"):
            raise Unsupported("only flat beta.14 recursion inputs are supported")
        rec, note = _decompose(k, r[1], table)
        recs.append(rec)
        if note:
            notes.append(note)
    return Program(ops=a.ops, public=public, private=private, abi=abi, table=table, recursions=recs,
                   unmodeled=list(a.unmodeled), path=str(acir_path), notes=notes)


def _single(e):
    return e[0][1][0] if len(e) == 1 and e[0][0] == 1 and len(e[0][1]) == 1 else None


def _decompose(k, flat, table):
    """Printed beta.14 layout [vk | proof | public_inputs | key_hash | predicate] (Noir RecursiveAggregation field order).

    The vk slice must be exactly one ABI `...verification_key` leaf; the proof length is that of its sibling `...proof`
    leaf. The proof slice may be multiplexed (e.g. a padding branch) and only its length is checked.
    """
    ws = [_single(e) for e in flat]
    found = []
    for path, leaf in table.items():
        if path.endswith("verification_key") and len(leaf) > 1 and tuple(ws[:len(leaf)]) == tuple(leaf):
            found.append(path)
    if len(found) != 1:
        raise Unsupported(f"recursion call {k}: vk slice matches {len(found)} ABI verification_key leaves")
    vk_path = found[0]
    pf_path = vk_path[: -len("verification_key")] + "proof"
    if pf_path not in table:
        raise Unsupported(f"recursion call {k}: no sibling proof leaf for {vk_path}")
    nv, npf = len(table[vk_path]), len(table[pf_path])
    if len(flat) <= nv + npf + 2:
        raise Unsupported(f"recursion call {k}: too few inputs")
    note = None
    if tuple(ws[nv:nv + npf]) != tuple(table[pf_path]):
        note = f"recursion call {k}: proof slice is not the ABI leaf {pf_path} (multiplexed); length checked only"
    return Recursion(index=k, vk=ws[:nv], proof=ws[nv:nv + npf], public_inputs=flat[nv + npf:-2],
                     key_hash=flat[-2], predicate=flat[-1]), note
