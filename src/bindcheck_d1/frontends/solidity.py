"""Bounded consumer extraction from the solc JSON AST (documented subset; everything else is Unsupported -> UNKNOWN).

Supported subset (D1-03):
  * internal functions with value parameters; Block, VariableDeclarationStatement, ExpressionStatement, IfStatement,
    Return, EmitStatement (events are not protected effects and are ignored), Assignment `=` to locals/storage members,
    UnaryOperation `!` and `delete` on a storage mapping entry, TupleExpression destructuring of a low-level call;
  * expressions: Identifier, Literal (number/bool), BinaryOperation (+ == != on supported terms), IndexAccess on a calldata
    `bytes32[]` (relative to the scan index) or a storage mapping, MemberAccess on mapping structs / `.length` /
    `.call`, elementary type conversions (bytes32/uint256 identity under A4; address(uint160(.)) truncation),
    require/revert, keccak256(abi.encode(..)) (uninterpreted), abi.encodeCall(IERC20.transfer, ..) with a low-level
    `.call` modelled by A5, abi.decode(returndata, (bool)) under A5;
  * exactly one loop shape: `uint i = s; uint end = s + n; while (i < end) { i = f(i, a); }` (monotone scan).
The executor enumerates paths; conditions are kept symbolic. Terms are tuples (see `T*` helpers).
"""
import json
from dataclasses import dataclass, field
from pathlib import Path


class Unsupported(Exception):
    pass


# ---------------------------------------------------------------------------------------------- terms
def C(v): return ("const", int(v))
def W(off): return ("word", off)          # publicInputs[index + off], a field word under A4
def IDX(off): return ("idx", off)         # index + off
TRUE, FALSE = ("bool", True), ("bool", False)


def t_not(c):
    if c == TRUE: return FALSE
    if c == FALSE: return TRUE
    if c[0] == "not": return c[1]
    return ("not", c)


def t_eq(a, b):
    if a[0] == "const" and b[0] == "const": return TRUE if a[1] == b[1] else FALSE
    if a == b: return TRUE
    return ("eq", a, b)


def t_and(a, b):
    if FALSE in (a, b): return FALSE
    if a == TRUE: return b
    if b == TRUE: return a
    return ("and", a, b)


def t_or(a, b):
    if TRUE in (a, b): return TRUE
    if a == FALSE: return b
    if b == FALSE: return a
    return ("or", a, b)


@dataclass
class Path_:
    cond: list = field(default_factory=list)      # conjunction of boolean terms
    effects: list = field(default_factory=list)   # ("write", var, key, member, value) | ("delete", var, key) | ("transfer", token, to, value, ok)
    reads: set = field(default_factory=set)       # calldata offsets read relative to index
    ret: object = None
    revert: object = None                         # None or message string
    oks: int = 0                                  # counter for fresh transfer-success booleans

    def fork(self):
        return Path_(list(self.cond), list(self.effects), set(self.reads), self.ret, self.revert, self.oks)


class _Return(Exception):
    pass


@dataclass
class Case:
    cond: list
    step: object          # int (positions advanced) or None for revert
    effects: list
    reads: set
    revert: object


@dataclass
class ScanSummary:
    function: str
    cases: list
    src: dict             # function name -> AST src location
    loop: dict            # extracted loop facts
    link: dict            # extracted verifyRollup facts
    assumed: list         # environment calls/facts taken as ASSUMED
    unsupported: list


# ---------------------------------------------------------------------------------------------- AST access
class Ast:
    def __init__(self, artifact_json):
        d = json.loads(Path(artifact_json).read_text())
        self.root = d["ast"]
        self.fns, self.by_id, self.state_vars = {}, {}, {}
        self._index(self.root)

    def _index(self, n):
        if isinstance(n, dict):
            if "id" in n:
                self.by_id[n["id"]] = n
            if n.get("nodeType") == "FunctionDefinition" and n.get("kind") == "function":
                self.fns.setdefault(n["name"], []).append(n)
            if n.get("nodeType") == "VariableDeclaration" and n.get("stateVariable"):
                self.state_vars[n["id"]] = n["name"]
            for v in n.values():
                self._index(v)
        elif isinstance(n, list):
            for v in n:
                self._index(v)

    def fn(self, name):
        fs = self.fns.get(name, [])
        if len(fs) != 1:
            raise Unsupported(f"function {name!r} has {len(fs)} definitions")
        return fs[0]


# ---------------------------------------------------------------------------------------------- executor
class Exec:
    def __init__(self, ast):
        self.ast = ast
        self.visited = {}

    def run_function(self, name, args):
        """args: list of terms for parameters. Returns list of finished Path_ (ret or revert set)."""
        f = self.ast.fn(name)
        self.visited[name] = f["src"]
        if f.get("modifiers"):
            raise Unsupported(f"modifiers on {name}")
        env = {}
        params = f["parameters"]["parameters"]
        if len(params) != len(args):
            raise Unsupported(f"arity mismatch calling {name}")
        for p, a in zip(params, args):
            env[p["id"]] = a
        return self.block(f["body"], [(Path_(), env)])

    # statements map (path, env) to a list of (path, env); a finished path carries ret or revert
    def stmt(self, st, path, env):
        k = st["nodeType"]
        if k == "Block":
            return self._block_states(st, path, env)
        if k == "VariableDeclarationStatement":
            if st.get("initialValue") is None:
                raise Unsupported("declaration without initializer")
            outs = []
            for p, val in self.expr(st["initialValue"], path, env):
                e2 = dict(env)
                decls = st["declarations"]
                if len(decls) == 1:
                    e2[decls[0]["id"]] = val
                else:
                    if val[0] != "tuple" or len(val[1]) != len(decls):
                        raise Unsupported("tuple destructuring shape")
                    for d, v in zip(decls, val[1]):
                        if d is not None:
                            e2[d["id"]] = v
                outs.append((p, e2))
            return outs
        if k == "ExpressionStatement":
            return self.expr_stmt(st["expression"], path, env)
        if k == "EmitStatement":
            return [(path, env)]
        if k == "Return":
            outs = []
            if st.get("expression") is None:
                p = path.fork(); p.ret = ("void",); return [(p, env)]
            for p, val in self.expr(st["expression"], path, env):
                p.ret = val
                outs.append((p, env))
            return outs
        if k == "IfStatement":
            outs = []
            for p, c in self.expr(st["condition"], path, env):
                for branch, cc in ((st["trueBody"], c), (st.get("falseBody"), t_not(c))):
                    if cc == FALSE:
                        continue
                    q = p.fork()
                    if cc != TRUE:
                        q.cond.append(cc)
                    if branch is None:
                        outs.append((q, env)); continue
                    sub = branch if branch["nodeType"] == "Block" else {"nodeType": "Block", "statements": [branch]}
                    outs += self._block_states(sub, q, env)
            return outs
        raise Unsupported(f"statement {k}")

    def _block_states(self, blk, path, env):
        live, out = [(path, env)], []
        for st in blk["statements"]:
            nxt = []
            for p, e in live:
                for p2, e2 in self.stmt(st, p, e):
                    (out if (p2.ret is not None or p2.revert is not None) else nxt).append((p2, e2))
            live = nxt
        return out + live

    def block(self, blk, states):
        res = []
        for path, env in states:
            res += self._block_states(blk, path, env)
        return [p for p, _ in res]

    def expr_stmt(self, e, path, env):
        k = e["nodeType"]
        if k == "Assignment":
            if e["operator"] != "=":
                raise Unsupported(f"assignment operator {e['operator']}")
            outs = []
            for p, v in self.expr(e["rightHandSide"], path, env):
                lhs = e["leftHandSide"]
                if lhs["nodeType"] == "Identifier" and lhs["referencedDeclaration"] in env:
                    e2 = dict(env); e2[lhs["referencedDeclaration"]] = v; outs.append((p, e2))
                elif lhs["nodeType"] == "MemberAccess":
                    for p2, (var, key) in self.mapping_entry(lhs["expression"], p, env):
                        p2.effects.append(("write", var, key, lhs["memberName"], v))
                        outs.append((p2, env))
                else:
                    raise Unsupported("assignment target")
            return outs
        if k == "UnaryOperation" and e["operator"] == "delete":
            outs = []
            for p, (var, key) in self.mapping_entry(e["subExpression"], path, env):
                p.effects.append(("delete", var, key)); outs.append((p, env))
            return outs
        if k == "FunctionCall":
            return [(p, env) for p, _ in self.expr(e, path, env)]
        raise Unsupported(f"expression statement {k}")

    def mapping_entry(self, e, path, env):
        if e["nodeType"] != "IndexAccess" or e["baseExpression"]["nodeType"] != "Identifier":
            raise Unsupported("mapping entry shape")
        ref = e["baseExpression"]["referencedDeclaration"]
        if ref not in self.ast.state_vars:
            raise Unsupported("index base is not a state mapping")
        return [(p, (self.ast.state_vars[ref], key)) for p, key in self.expr(e["indexExpression"], path, env)]

    # expressions return list of (path, term)
    def expr(self, e, path, env):
        k = e["nodeType"]
        if k == "Literal":
            if e["kind"] == "number":
                return [(path, C(int(e["value"], 0)))]
            if e["kind"] == "bool":
                return [(path, TRUE if e["value"] == "true" else FALSE)]
            raise Unsupported(f"literal kind {e['kind']}")
        if k == "Identifier":
            ref = e.get("referencedDeclaration")
            if ref in env:
                return [(path, env[ref])]
            raise Unsupported(f"identifier {e['name']} not a local/parameter")
        if k == "BinaryOperation":
            outs = []
            for p, a in self.expr(e["leftExpression"], path, env):
                for p2, b in self.expr(e["rightExpression"], p, env):
                    outs.append((p2, self.binop(e["operator"], a, b)))
            return outs
        if k == "UnaryOperation" and e["operator"] == "!":
            return [(p, t_not(v)) for p, v in self.expr(e["subExpression"], path, env)]
        if k == "IndexAccess":
            base = e["baseExpression"]
            if base["nodeType"] == "Identifier" and base.get("referencedDeclaration") in env and env[base["referencedDeclaration"]] == ("pi",):
                outs = []
                for p, ix in self.expr(e["indexExpression"], path, env):
                    if ix[0] != "idx":
                        raise Unsupported("calldata index not relative to the scan index")
                    q = p.fork(); q.reads.add(ix[1]); outs.append((q, W(ix[1])))
                return outs
            return [(p, ("state", var, key, None)) for p, (var, key) in self.mapping_entry(e, path, env)]
        if k == "MemberAccess":
            m = e["memberName"]
            inner = e["expression"]
            if inner["nodeType"] == "IndexAccess":
                return [(p, ("state", var, key, m)) for p, (var, key) in self.mapping_entry(inner, path, env)]
            if m == "length":
                return [(p, ("length", v)) for p, v in self.expr(inner, path, env)]
            raise Unsupported(f"member access .{m}")
        if k == "FunctionCall":
            return self.call(e, path, env)
        if k == "TupleExpression":
            if len(e["components"]) != 1:
                raise Unsupported("tuple expression")
            return self.expr(e["components"][0], path, env)
        raise Unsupported(f"expression {k}")

    def binop(self, op, a, b):
        if op in ("==", "!=") and a[0] == "length" and a[1][0] == "returndata" and b == C(0):
            # A5: a standard token returns a 32-byte `true` on success; a code-less address returns empty data.
            r = t_eq(a[1][1], C(0))
            return r if op == "==" else t_not(r)
        if op == "+":
            if a[0] == "idx" and b[0] == "const": return IDX(a[1] + b[1])
            if a[0] == "const" and b[0] == "const": return C(a[1] + b[1])
            raise Unsupported("addition outside index arithmetic")
        if op == "==": return t_eq(a, b)
        if op == "!=": return t_not(t_eq(a, b))
        raise Unsupported(f"operator {op}")

    def call(self, e, path, env):
        f = e["expression"]
        kind = e.get("kind")
        args = e["arguments"]
        if kind == "typeConversion":
            tname = f.get("typeName", {}).get("name") if f["nodeType"] == "ElementaryTypeNameExpression" else None
            if tname in ("uint256", "bytes32", "uint"):
                return self.expr(args[0], path, env)                      # identity under A4 (canonical field word)
            if tname == "uint160":
                return [(p, ("low160", v)) for p, v in self.expr(args[0], path, env)]
            if tname == "address":
                outs = []
                for p, v in self.expr(args[0], path, env):
                    if v[0] == "low160" or (v[0] == "const" and v[1] == 0):
                        outs.append((p, v if v[0] == "low160" else C(0)))
                    else:
                        raise Unsupported("address conversion of a non-uint160 term")
                return outs
            raise Unsupported(f"type conversion {tname}")
        if f["nodeType"] == "Identifier" and f["name"] in ("require", "revert") and f.get("referencedDeclaration", 0) < 0:
            if f["name"] == "revert":
                p = path.fork(); p.revert = args[0].get("value", "revert") if args else "revert"; return [(p, ("void",))]
            outs = []
            msg = args[1].get("value", "require") if len(args) > 1 else "require"
            for p, c in self.expr(args[0], path, env):
                if c != TRUE:
                    q = p.fork(); q.revert = msg
                    if c != FALSE: q.cond.append(t_not(c))
                    outs.append((q, ("void",)))
                if c != FALSE:
                    q = p.fork()
                    if c != TRUE: q.cond.append(c)
                    outs.append((q, ("void",)))
            return outs
        if f["nodeType"] == "Identifier" and f["name"] == "keccak256" and f.get("referencedDeclaration", 0) < 0:
            inner = args[0]
            if not (inner["nodeType"] == "FunctionCall" and inner["expression"]["nodeType"] == "MemberAccess"
                    and inner["expression"]["memberName"] == "encode"):
                raise Unsupported("keccak256 of non-abi.encode")
            return [(p, ("keccak_abi_encode", tuple(vs))) for p, vs in self.args(inner["arguments"], path, env)]
        if f["nodeType"] == "MemberAccess" and f["memberName"] == "call" and kind == "functionCall":
            return self.low_level_transfer(f, args, path, env)
        if f["nodeType"] == "FunctionCall" and f["expression"]["nodeType"] == "MemberAccess" and f["expression"]["memberName"] == "call":
            raise Unsupported("call with value/gas options")
        if f["nodeType"] == "MemberAccess" and f["memberName"] == "decode":
            if len(args) == 2 and args[1]["nodeType"] == "TupleExpression" and len(args[1]["components"]) == 1 \
                    and args[1]["components"][0].get("typeName", {}).get("name") == "bool":
                outs = []
                for p, v in self.expr(args[0], path, env):
                    if v[0] != "returndata":
                        raise Unsupported("abi.decode of non-returndata")
                    outs.append((p, TRUE))                                   # A5: standard token returns true when it succeeds
                return outs
            raise Unsupported("abi.decode shape")
        if f["nodeType"] == "Identifier" and f.get("referencedDeclaration", -1) > 0:
            decl = self.ast.by_id.get(f["referencedDeclaration"])
            if decl and decl.get("nodeType") == "FunctionDefinition":
                if decl.get("visibility") not in ("internal", "private") or decl.get("kind") != "function":
                    raise Unsupported(f"call to non-internal function {decl['name']}")
                outs = []
                for p, vs in self.args(args, path, env):
                    for q, v in self.call_internal(decl, vs, p):
                        outs.append((q, v))
                return outs
        raise Unsupported(f"call {f.get('name') or f.get('memberName') or f['nodeType']}")

    def call_internal(self, decl, vals, path):
        """Inline an internal call. Returns (path, value): reverted paths keep `revert`; returning paths have `ret`
        cleared so the caller continues, and the return value is passed separately."""
        self.visited[decl["name"]] = decl["src"]
        if decl.get("modifiers"):
            raise Unsupported(f"modifiers on {decl['name']}")
        env = {p["id"]: v for p, v in zip(decl["parameters"]["parameters"], vals)}
        outs = []
        for q, _ in self._block_states(decl["body"], path.fork(), env):
            if q.revert is not None:
                outs.append((q, ("void",)))
            else:
                v = q.ret if q.ret is not None else ("void",)
                q.ret = None
                outs.append((q, v))
        return outs

    def args(self, args, path, env):
        acc = [(path, [])]
        for a in args:
            nxt = []
            for p, vs in acc:
                for p2, v in self.expr(a, p, env):
                    nxt.append((p2, vs + [v]))
            acc = nxt
        return acc

    def low_level_transfer(self, f, args, path, env):
        """`token.call(abi.encodeCall(IERC20.transfer, (to, value)))` under A5 (standard atomic ERC20).
        token == address(0): no code, call succeeds with empty returndata, no transfer.
        Otherwise a fresh boolean `ok` decides success; success transfers `value` to `to`."""
        if len(args) != 1:
            raise Unsupported("low-level call arguments")
        enc = args[0]
        if not (enc["nodeType"] == "FunctionCall" and enc["expression"]["nodeType"] == "MemberAccess"
                and enc["expression"]["memberName"] == "encodeCall"):
            raise Unsupported("low-level call payload is not abi.encodeCall")
        target = enc["arguments"][0]
        if not (target["nodeType"] == "MemberAccess" and target["memberName"] == "transfer"
                and target["expression"].get("name") == "IERC20"):
            raise Unsupported("encodeCall target is not IERC20.transfer")
        tup = enc["arguments"][1]
        if tup["nodeType"] != "TupleExpression" or len(tup["components"]) != 2:
            raise Unsupported("transfer argument tuple")
        outs = []
        for p, token in self.expr(f["expression"], path, env):
            for p2, (to, value) in self.args(tup["components"], p, env):
                q = p2.fork()
                q.oks += 1
                ok = ("ok", q.oks)
                q.effects.append(("transfer", token, to, value, ok))
                success = t_or(t_eq(token, C(0)), ok)
                retdata = ("returndata", token, ok)
                outs.append((q, ("tuple", (success, retdata))))
        return outs


# ---------------------------------------------------------------------------------------------- loop / link checks
def _is_ident(n, ref=None, name=None):
    return n.get("nodeType") == "Identifier" and (ref is None or n.get("referencedDeclaration") == ref) and (name is None or n.get("name") == name)


def check_scan_loop(ast, name="verifyAllMessages"):
    """Recognise exactly `uint i = s; uint end = s + n; while (i < end) { i = f(i, a); }` and return its facts."""
    f = ast.fn(name)
    ps = [p["id"] for p in f["parameters"]["parameters"]]
    st = f["body"]["statements"]
    if len(st) != 3:
        raise Unsupported("scan loop: unexpected statement count")
    d0, d1, w = st
    try:
        i_id = d0["declarations"][0]["id"]
        assert _is_ident(d0["initialValue"], ps[0])
        end_id = d1["declarations"][0]["id"]
        add = d1["initialValue"]
        assert add["nodeType"] == "BinaryOperation" and add["operator"] == "+"
        assert _is_ident(add["leftExpression"], ps[0]) and _is_ident(add["rightExpression"], ps[2])
        assert w["nodeType"] == "WhileStatement"
        c = w["condition"]
        assert c["nodeType"] == "BinaryOperation" and c["operator"] == "<" and _is_ident(c["leftExpression"], i_id) and _is_ident(c["rightExpression"], end_id)
        body = w["body"]["statements"]
        assert len(body) == 1 and body[0]["nodeType"] == "ExpressionStatement"
        asg = body[0]["expression"]
        assert asg["nodeType"] == "Assignment" and asg["operator"] == "=" and _is_ident(asg["leftHandSide"], i_id)
        call = asg["rightHandSide"]
        assert call["nodeType"] == "FunctionCall" and len(call["arguments"]) == 2
        assert _is_ident(call["arguments"][0], i_id) and _is_ident(call["arguments"][1], ps[1])
        callee = ast.by_id[call["expression"]["referencedDeclaration"]]["name"]
    except (AssertionError, KeyError, IndexError, TypeError):
        raise Unsupported("scan loop shape not recognised")
    return {"function": name, "src": f["src"], "body_function": callee, "start_param": 0, "array_param": 1, "length_param": 2}


def check_verify_rollup(ast, name="verifyRollup"):
    """Extract: publicInputs length requirement, root/commit indices, scan call (start, array, length), verifier call args."""
    f = ast.fn(name)
    params = {p["name"]: p["id"] for p in f["parameters"]["parameters"]}
    pi = params.get("publicInputs")
    proof = params.get("aggrProof")
    if pi is None or proof is None:
        raise Unsupported("verifyRollup parameters")
    facts = {"src": f["src"], "modifiers": [m["modifierName"]["name"] for m in f.get("modifiers", [])],
             "index_roles": {}, "scan_call": None, "verifier_call": None, "length_check": None, "internal_calls": []}

    def walk(n):
        if isinstance(n, dict):
            t = n.get("nodeType")
            if t == "VariableDeclarationStatement" and n.get("initialValue", {}).get("nodeType") == "IndexAccess":
                ia = n["initialValue"]
                if _is_ident(ia["baseExpression"], pi) and ia["indexExpression"].get("nodeType") == "Literal":
                    facts["index_roles"][int(ia["indexExpression"]["value"])] = n["declarations"][0]["name"]
            if t == "FunctionCall" and n["expression"].get("nodeType") == "Identifier" and n["expression"].get("referencedDeclaration", -1) > 0:
                callee = ast.by_id.get(n["expression"]["referencedDeclaration"], {})
                facts["internal_calls"].append(callee.get("name"))
                if callee.get("name") == "verifyAllMessages":
                    a = n["arguments"]
                    if a[0].get("nodeType") == "Literal" and _is_ident(a[1], pi) and a[2].get("nodeType") == "MemberAccess" \
                            and a[2]["memberName"] == "messages_length":
                        facts["scan_call"] = {"start": int(a[0]["value"]), "array": "publicInputs", "length": "zkVerifiers[verificationKeyHash].messages_length"}
            if t == "FunctionCall" and n["expression"].get("nodeType") == "MemberAccess" and n["expression"]["memberName"] == "verify":
                a = n["arguments"]
                if len(a) == 2 and _is_ident(a[0], proof) and _is_ident(a[1], pi):
                    facts["verifier_call"] = {"proof": "aggrProof", "public_inputs": "publicInputs (unchanged identifier)", "src": n["src"]}
            if t == "BinaryOperation" and n["operator"] == "==" and n["leftExpression"].get("nodeType") == "MemberAccess" \
                    and n["leftExpression"]["memberName"] == "length" and _is_ident(n["leftExpression"]["expression"], pi):
                r = n["rightExpression"]
                if r.get("nodeType") == "BinaryOperation" and r["operator"] == "+" and r["rightExpression"].get("nodeType") == "Literal":
                    facts["length_check"] = {"publicInputs.length": f"messages_length + {r['rightExpression']['value']}"}
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(f["body"])
    # Any assignment to publicInputs or its elements would break the link; calldata parameters are immutable in Solidity.
    if f["parameters"]["parameters"][[p["name"] for p in f["parameters"]["parameters"]].index("publicInputs")]["storageLocation"] != "calldata":
        raise Unsupported("publicInputs is not calldata")
    for k in ("scan_call", "verifier_call", "length_check"):
        if not facts[k]:
            raise Unsupported(f"verifyRollup: {k} not established")
    return facts


def extract(artifact_json):
    ast = Ast(artifact_json)
    loop = check_scan_loop(ast)
    link = check_verify_rollup(ast)
    ex = Exec(ast)
    paths = ex.run_function(loop["body_function"], [IDX(0), ("pi",)])
    cases = []
    for p in paths:
        if p.revert is not None:
            cases.append(Case(p.cond, None, p.effects, p.reads, p.revert))
            continue
        r = p.ret
        if not (isinstance(r, tuple) and r[0] == "idx" and r[1] >= 1):
            raise Unsupported(f"scan body returns {r}, not index + positive constant")
        cases.append(Case(p.cond, r[1], p.effects, p.reads, None))
    assumed = ["A5 ERC20 model for low-level transfer call", "A4 canonical words for bytes32/uint256 conversions",
               "A7 verifyValidatorSignatures/onlyProver satisfied by owned roles"]
    return ScanSummary(function=loop["body_function"], cases=cases, src=dict(ex.visited), loop=loop, link=link,
                       assumed=assumed, unsupported=[])
