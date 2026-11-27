"""Concrete interpretation of a restricted solc AST, with explicit boundaries.

This is NOT a symbolic solver or proof verifier. Guard outcomes are conservative
frame choices, and verifier outcomes are unresolved relation inputs. Every run
therefore has security verdict UNKNOWN, including a successful interpretation.
Statically reachable bodies are checked for supported node/call kinds before
execution. Unhandled dynamic types and inputs also fail closed.
Gas/termination are not proved; a step limit gives UNKNOWN, never revert/safety.
"""
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re

from Crypto.Hash import keccak

from ..model_v2 import Unsupported
from .consumer_boundary_v1 import walk
from .guard_frame_v1 import validate_reuse


class Revert(Exception):
    """A modeled EVM revert, distinct from unsupported analysis."""


class Returned(Exception):
    def __init__(self, value):
        self.value = value


def fail(reason, detail):
    raise Unsupported(reason, str(detail))


def type_name(node):
    return node.get('typeDescriptions', {}).get('typeString', '')


def width(name):
    if name == 'address' or name == 'address payable':
        return 160
    match = re.fullmatch(r'uint(\d*)', name)
    if match:
        return int(match[1] or 256)
    match = re.fullmatch(r'bytes(\d+)', name)
    if match:
        return 8 * int(match[1])
    return None


def default(name):
    if name == 'bool':
        return False
    if width(name) is not None or name.startswith('contract '):
        return 0
    if not name.startswith('mapping(') and '[]' in name:
        return ()
    if name.startswith(('mapping(', 'struct ')):
        return {}
    if name == 'bytes' or name.startswith('bytes '):
        return b''
    fail('EXEC_DEFAULT_TYPE_UNSUPPORTED', name)


def scalar_check(value, name):
    bits = width(name)
    if bits is not None:
        if type(value) is not int or not 0 <= value < 2**bits:
            fail('EXEC_VALUE_TYPE', (name, value))
    elif name == 'bool':
        if type(value) is not bool:
            fail('EXEC_VALUE_TYPE', (name, value))
    elif name.startswith('contract '):
        scalar_check(value, 'address')
    else:
        fail('EXEC_VALUE_TYPE_UNSUPPORTED', name)
    return value


@dataclass
class Token:
    """A5 adapter: exact ordinary OZ 5.0.1 ERC20, no overrides/callbacks.

    Source/code correspondence is an explicit caller assumption, not inferred
    from an address. totalSupply is conserved; sender==recipient uses sequential
    writes. Failure rolls back the token call without reverting its caller.
    """
    address: int
    balances: dict[int, int]
    supply: int
    implementation: str = 'OZ-5.0.1-ERC20-no-overrides'

    def validate(self):
        if self.implementation != 'OZ-5.0.1-ERC20-no-overrides':
            fail('TOKEN_IMPLEMENTATION_UNSUPPORTED', self.implementation)
        scalar_check(self.address, 'address')
        if not self.address:
            fail('TOKEN_IMPLEMENTATION_UNSUPPORTED', 'zero address')
        scalar_check(self.supply, 'uint256')
        for address, amount in self.balances.items():
            scalar_check(address, 'address')
            scalar_check(amount, 'uint256')
        if self.balances.get(0, 0) or sum(self.balances.values()) != self.supply:
            fail('TOKEN_STATE_INCONSISTENT', self.balances)

    def transfer(self, sender, recipient, amount):
        self.validate()
        scalar_check(sender, 'address')
        scalar_check(recipient, 'address')
        scalar_check(amount, 'uint256')
        if sender == 0 or recipient == 0 or self.balances.get(sender, 0) < amount:
            return False
        self.balances[sender] = self.balances.get(sender, 0) - amount
        self.balances[recipient] = self.balances.get(recipient, 0) + amount
        self.validate()
        return True


@dataclass(frozen=True)
class BoundaryChoices:
    # None means missing boundary evidence/input, not success.
    guard_returns: bool | None = None
    guard_writes: dict[int, int] = field(default_factory=dict)
    verifier_returns: bool | None = None


@dataclass
class Result:
    outcome: str
    state: dict
    token: Token
    events: list
    transfers: list
    writes: list
    boundary_calls: list
    reason: str = ''
    detail: str = ''
    security_verdict: str = 'UNKNOWN'
    evidence: str = 'AST_EXECUTION_WITH_ABSTRACT_BOUNDARIES'


class Slot:
    def __init__(self, store, path, names, writable, machine, state_root=None):
        self.store, self.path, self.names = store, path, names
        self.writable, self.machine, self.state_root = writable, machine, state_root

    def get(self):
        current = self.store
        for key, name in zip(self.path, self.names):
            if isinstance(current, (list, tuple, bytes)):
                if type(key) is not int or not 0 <= key < len(current):
                    raise Revert('CALLDATA_BOUNDS')
                current = current[key]
            elif isinstance(current, dict):
                current = current.get(key, default(name))
            else:
                fail('EXEC_REFERENCE_BASE', type(current).__name__)
        return current

    def put(self, value):
        if not self.writable:
            fail('EXEC_REFERENCE_WRITE_UNSUPPORTED', self.path)
        scalar_check(value, self.names[-1])
        current = self.store
        for key, name in zip(self.path[:-1], self.names[:-1]):
            if key not in current:
                current[key] = default(name)
            current = current[key]
        before = self.get()
        current[self.path[-1]] = value
        if self.state_root is not None:
            self.machine.writes.append({'root': self.state_root, 'path': self.path[1:],
                                        'before': before, 'after': value,
                                        'node': self.machine.current_node})


SUPPORTED = frozenset(('Block ExpressionStatement VariableDeclarationStatement '
    'VariableDeclaration ElementaryTypeName ArrayTypeName Mapping UserDefinedTypeName '
    'IdentifierPath ElementaryTypeNameExpression Identifier Literal BinaryOperation '
    'UnaryOperation Assignment FunctionCall MemberAccess IndexAccess TupleExpression '
    'IfStatement WhileStatement Return EmitStatement PlaceholderStatement').split())
BINARY = frozenset(('+', '-', '*', '==', '!=', '<', '>', '<=', '>=', '&&', '||'))
UNARY = frozenset(('!', 'delete'))


class Machine:
    def __init__(self, boundary, entry, *, frame_certificate=None, context=None,
                 verifier_declaration=None, transfer_declaration=None, step_limit=100000):
        self.boundary = boundary
        self.entry = entry
        self.frame_certificate = deepcopy(frame_certificate)
        self.context = deepcopy(context)
        self.guard = None
        if frame_certificate is not None:
            validate_reuse(boundary, frame_certificate, context)
            self.guard = frame_certificate['payload']['frame']['entry']
        self.verifier_declaration = verifier_declaration
        self.transfer_declaration = transfer_declaration
        self.step_limit = step_limit
        self.closure = self.validate(entry)
        self.identity = self.digest()

    def value_check(self, value, node):
        """Validate concrete calldata/storage against compiler-declared types."""
        node = node.get('typeName', node)
        kind = node['nodeType']
        if kind == 'ElementaryTypeName':
            name = node['name']
            if name == 'bytes':
                if not isinstance(value, bytes): fail('EXEC_VALUE_TYPE', name)
            else:
                scalar_check(value, name)
        elif kind == 'ArrayTypeName':
            if not isinstance(value, (tuple, list)):
                fail('EXEC_VALUE_TYPE', 'array')
            if node.get('length') is not None:
                fail('EXEC_FIXED_ARRAY_UNSUPPORTED', node['id'])
            for item in value: self.value_check(item, node['baseType'])
        elif kind == 'Mapping':
            if not isinstance(value, dict): fail('EXEC_VALUE_TYPE', 'mapping')
            for key, item in value.items():
                self.value_check(key, node['keyType']); self.value_check(item, node['valueType'])
        elif kind == 'UserDefinedTypeName':
            target = self.boundary.nodes[node['referencedDeclaration']]
            if target['nodeType'] == 'ContractDefinition':
                scalar_check(value, 'address')
            elif target['nodeType'] == 'StructDefinition':
                members = {m['name']: m for m in target['members']}
                if not isinstance(value, dict) or set(value) - set(members):
                    fail('EXEC_VALUE_TYPE', target['name'])
                for name, item in value.items(): self.value_check(item, members[name])
            else:
                fail('EXEC_VALUE_TYPE_UNSUPPORTED', target['nodeType'])
        else:
            fail('EXEC_VALUE_TYPE_UNSUPPORTED', kind)

    def digest(self):
        value = {'ast': self.boundary.nodes, 'sources': {
            p: hashlib.sha256(s).hexdigest() for p, s in self.boundary.sources.items()},
            'entry': self.entry, 'frame': self.frame_certificate, 'context': self.context,
            'verifier': self.verifier_declaration, 'transfer': self.transfer_declaration,
            'step_limit': self.step_limit,
            'interpreter_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

    def validate(self, entry):
        queue = [entry]
        seen = set()
        while queue:
            ref = queue.pop()
            if ref in seen or ref == self.guard:
                continue
            fn = self.boundary.nodes.get(ref, {})
            if fn.get('nodeType') not in ('FunctionDefinition', 'ModifierDefinition') or fn.get('body') is None:
                fail('EXEC_BODY_MISSING', ref)
            if fn.get('virtual') or fn.get('overrides'):
                fail('EXEC_DYNAMIC_DISPATCH', ref)
            if fn['nodeType'] == 'ModifierDefinition':
                statements = fn['body'].get('statements', [])
                placeholders = [n for n in walk(fn['body']) if n['nodeType'] == 'PlaceholderStatement']
                if len(placeholders) != 1 or not statements or statements[-1] != placeholders[0]:
                    fail('EXEC_MODIFIER_POSTLUDE_UNSUPPORTED', ref)
            if ref != entry and fn.get('nodeType') != 'ModifierDefinition' and fn.get('visibility') not in ('internal', 'private'):
                fail('EXEC_EXTERNAL_DISPATCH', ref)
            if fn.get('returnParameters', {}).get('parameters'):
                for p in fn['returnParameters']['parameters']:
                    if p.get('name'):
                        fail('EXEC_NAMED_RETURN_UNSUPPORTED', p['id'])
            seen.add(ref)
            for modifier in fn.get('modifiers', []):
                if modifier.get('arguments'):
                    fail('EXEC_MODIFIER_ARGUMENTS', modifier['id'])
                queue.append(modifier['modifierName']['referencedDeclaration'])
            for n in walk(fn['body']):
                kind = n['nodeType']
                if kind not in SUPPORTED:
                    fail('EXEC_NODE_UNSUPPORTED', (kind, n['id']))
                if kind == 'VariableDeclaration' and n.get('storageLocation') == 'storage':
                    fail('EXEC_STORAGE_ALIAS_UNSUPPORTED', n['id'])
                if kind == 'Identifier':
                    decl = self.boundary.nodes.get(n.get('referencedDeclaration'), {})
                    if decl.get('constant') or decl.get('mutability') == 'immutable':
                        fail('EXEC_CONSTANT_OR_IMMUTABLE_UNSUPPORTED', n['id'])
                if kind in ('BinaryOperation', 'UnaryOperation'):
                    if n.get('function') is not None:
                        fail('EXEC_USER_OPERATOR', n['id'])
                    if n['operator'] not in (BINARY if kind == 'BinaryOperation' else UNARY):
                        fail('EXEC_OPERATOR_UNSUPPORTED', n['operator'])
                if kind == 'Assignment' and n['operator'] != '=':
                    fail('EXEC_ASSIGNMENT_UNSUPPORTED', n['operator'])
                if kind != 'FunctionCall':
                    continue
                expr = n['expression']
                if n.get('kind') == 'typeConversion':
                    if expr['nodeType'] != 'ElementaryTypeNameExpression' or width(type_name(n)) is None:
                        fail('EXEC_CAST_UNSUPPORTED', n['id'])
                    continue
                if n.get('kind') != 'functionCall':
                    fail('EXEC_CALL_KIND', n['id'])
                target = self.boundary.nodes.get(expr.get('referencedDeclaration'), {})
                if target.get('nodeType') == 'FunctionDefinition':
                    if target['id'] == self.verifier_declaration:
                        if target.get('body') is not None or target.get('stateMutability') != 'view' or expr['nodeType'] != 'MemberAccess':
                            fail('EXEC_VERIFIER_BOUNDARY_INVALID', target['id'])
                    elif expr['nodeType'] == 'Identifier':
                        queue.append(target['id'])
                    else:
                        fail('EXEC_MEMBER_DISPATCH_UNSUPPORTED', n['id'])
                    continue
                if target.get('nodeType') == 'EventDefinition':
                    continue
                if expr['nodeType'] == 'Identifier' and expr.get('referencedDeclaration', 0) < 0 and expr['name'] in ('require', 'assert', 'revert', 'keccak256'):
                    continue
                if expr['nodeType'] == 'MemberAccess':
                    base = expr['expression']
                    if base.get('name') == 'abi' and base.get('referencedDeclaration', 0) < 0 and expr['memberName'] in ('encode', 'encodeCall', 'decode'):
                        continue
                    if expr['memberName'] == 'call' and type_name(base) == 'address':
                        continue
                fail('EXEC_CALL_UNSUPPORTED', n['id'])
        return sorted(seen)

    def step(self, node):
        self.steps += 1
        self.current_node = node['id']
        if self.steps > self.step_limit:
            fail('EXEC_STEP_LIMIT', self.step_limit)

    def reference(self, n, env):
        kind = n['nodeType']
        if kind == 'Identifier':
            ref = n['referencedDeclaration']
            decl = self.boundary.nodes.get(ref, {})
            if decl.get('nodeType') != 'VariableDeclaration':
                fail('EXEC_REFERENCE_DECLARATION', ref)
            is_state = decl.get('stateVariable', False)
            writable = is_state or decl.get('storageLocation') not in ('calldata', 'memory', 'storage')
            return Slot(self.state if is_state else env, [ref], [type_name(decl)],
                        writable, self, ref if is_state else None)
        if kind in ('MemberAccess', 'IndexAccess'):
            base = n['expression'] if kind == 'MemberAccess' else n['baseExpression']
            slot = self.reference(base, env)
            key = n['memberName'] if kind == 'MemberAccess' else self.expr(n['indexExpression'], env)
            return Slot(slot.store, slot.path + [key], slot.names + [type_name(n)],
                        slot.writable, self, slot.state_root)
        fail('EXEC_REFERENCE_UNSUPPORTED', kind)

    def checked(self, value, node):
        bits = width(type_name(node))
        if bits is None:
            fail('EXEC_ARITHMETIC_TYPE', type_name(node))
        if not 0 <= value < 2**bits:
            raise Revert('ARITHMETIC_OVERFLOW')
        return value

    def expr(self, n, env):
        self.step(n)
        kind = n['nodeType']
        if kind == 'Literal':
            if n['kind'] == 'number':
                return int(n['value'], 16 if n['value'].startswith('0x') else 10)
            if n['kind'] == 'bool':
                return n['value'] == 'true'
            if n['kind'] == 'string':
                return n['value']
            fail('EXEC_LITERAL_UNSUPPORTED', n['kind'])
        if kind in ('Identifier', 'IndexAccess'):
            return self.reference(n, env).get()
        if kind == 'MemberAccess':
            base = n['expression']
            if n['memberName'] == 'sender' and base.get('name') == 'msg' and base.get('referencedDeclaration', 0) < 0:
                return self.sender
            if n['memberName'] == 'length':
                value = self.expr(base, env)
                if not isinstance(value, (bytes, tuple, list)):
                    fail('EXEC_LENGTH_TYPE', type(value).__name__)
                return len(value)
            return self.reference(n, env).get()
        if kind == 'TupleExpression':
            if n.get('isInlineArray') or any(x is None for x in n['components']):
                fail('EXEC_TUPLE_UNSUPPORTED', n['id'])
            return tuple(self.expr(x, env) for x in n['components'])
        if kind == 'BinaryOperation':
            op = n['operator']
            a = self.expr(n['leftExpression'], env)
            if op in ('&&', '||'):
                scalar_check(a, 'bool')
                if (op == '&&' and not a) or (op == '||' and a):
                    return a
                return scalar_check(self.expr(n['rightExpression'], env), 'bool')
            b = self.expr(n['rightExpression'], env)
            if op == '+': return self.checked(a + b, n)
            if op == '-': return self.checked(a - b, n)
            if op == '*': return self.checked(a * b, n)
            return {'==': lambda: a == b, '!=': lambda: a != b,
                    '<': lambda: a < b, '>': lambda: a > b,
                    '<=': lambda: a <= b, '>=': lambda: a >= b}[op]()
        if kind == 'UnaryOperation':
            if n['operator'] == '!':
                return not scalar_check(self.expr(n['subExpression'], env), 'bool')
            slot = self.reference(n['subExpression'], env)
            self.current_node = n['id']
            slot.put(default(type_name(n['subExpression'])))
            return None
        if kind == 'Assignment':
            value = self.expr(n['rightHandSide'], env)
            slot = self.reference(n['leftHandSide'], env)
            self.current_node = n['id']
            slot.put(value)
            return value
        if kind == 'FunctionCall':
            return self.call_expr(n, env)
        fail('EXEC_EXPRESSION_UNSUPPORTED', kind)

    def call_expr(self, n, env):
        expr = n['expression']
        args = n['arguments']
        if n.get('kind') == 'typeConversion':
            if len(args) != 1:
                fail('EXEC_CAST_ARITY', n['id'])
            value = self.expr(args[0], env)
            if type(value) is not int:
                fail('EXEC_CAST_VALUE', type(value).__name__)
            # Only integer/bytes32/address right-aligned conversions on this path.
            source = type_name(args[0])
            target = type_name(n)
            if source.startswith('bytes') and source != 'bytes32' or target.startswith('bytes') and target != 'bytes32':
                fail('EXEC_FIXED_BYTES_CAST_UNSUPPORTED', (source, target))
            return value % 2**width(target)
        if expr['nodeType'] == 'MemberAccess':
            base = expr['expression']
            member = expr['memberName']
            if base.get('name') == 'abi' and base.get('referencedDeclaration', 0) < 0:
                if member == 'encode':
                    values = [self.expr(a, env) for a in args]
                    for a, v in zip(args, values):
                        scalar_check(v, type_name(a))
                    return b''.join(int(v).to_bytes(32, 'big') for v in values)
                if member == 'encodeCall':
                    if len(args) != 2 or args[0].get('referencedDeclaration') != self.transfer_declaration or self.transfer_declaration is None:
                        fail('EXEC_ABI_CALL_UNSUPPORTED', n['id'])
                    target = self.boundary.nodes[self.transfer_declaration]
                    params = [type_name(p) for p in target['parameters']['parameters']]
                    if target['name'] != 'transfer' or params != ['address', 'uint256']:
                        fail('EXEC_TRANSFER_INTERFACE', target['id'])
                    recipient, amount = self.expr(args[1], env)
                    scalar_check(recipient, 'address'); scalar_check(amount, 'uint256')
                    return bytes.fromhex('a9059cbb') + recipient.to_bytes(32, 'big') + amount.to_bytes(32, 'big')
                if member == 'decode':
                    components = args[1].get('components', []) if len(args) == 2 else []
                    if len(components) != 1 or components[0].get('nodeType') != 'ElementaryTypeNameExpression' or components[0].get('typeName', {}).get('name') != 'bool':
                        fail('EXEC_ABI_DECODE_UNSUPPORTED', n['id'])
                    data = self.expr(args[0], env)
                    if not isinstance(data, bytes) or len(data) < 32 or int.from_bytes(data[:32], 'big') not in (0, 1):
                        raise Revert('ABI_BOOL_DECODE')
                    return bool(int.from_bytes(data[:32], 'big'))
            if member == 'call':
                target = self.expr(base, env)
                data = self.expr(args[0], env)
                if target != self.token.address:
                    fail('TOKEN_IMPLEMENTATION_UNSUPPORTED', target)
                if not isinstance(data, bytes) or len(data) != 68 or data[:4] != bytes.fromhex('a9059cbb'):
                    fail('EXEC_TOKEN_CALL_UNSUPPORTED', n['id'])
                recipient = int.from_bytes(data[4:36], 'big')
                amount = int.from_bytes(data[36:68], 'big')
                success = self.token.transfer(self.contract, recipient, amount)
                self.boundary_calls.append({'kind': 'token', 'target': target,
                                            'arguments': [recipient, amount],
                                            'success': success, 'node': n['id']})
                if success:
                    self.transfers.append({'token': target, 'from': self.contract,
                                           'to': recipient, 'amount': amount, 'node': n['id']})
                # Exact ordinary ERC20 returns ABI true on success, reverts otherwise.
                return success, (1).to_bytes(32, 'big') if success else b''
            if expr.get('referencedDeclaration') == self.verifier_declaration:
                target = self.expr(base, env)
                values = [self.expr(a, env) for a in args]
                self.boundary_calls.append({'kind': 'verifier', 'target': target,
                                            'arguments': deepcopy(values), 'node': n['id']})
                if self.choices.verifier_returns is None:
                    fail('VERIFIER_RELATION_UNRESOLVED', n['id'])
                return scalar_check(self.choices.verifier_returns, 'bool')
        values = [self.expr(a, env) for a in args]
        ref = expr.get('referencedDeclaration')
        if expr['nodeType'] == 'Identifier' and ref is not None and ref < 0:
            name = expr['name']
            if name in ('require', 'assert'):
                if not scalar_check(values[0], 'bool'):
                    raise Revert(values[1] if len(values) > 1 else name)
                return None
            if name == 'revert':
                raise Revert(values[0] if values else 'revert')
            if name == 'keccak256':
                if len(values) != 1 or not isinstance(values[0], bytes):
                    fail('EXEC_HASH_INPUT', n['id'])
                return int.from_bytes(keccak.new(digest_bits=256, data=values[0]).digest(), 'big')
        if ref == self.guard:
            self.boundary_calls.append({'kind': 'guard', 'arguments': deepcopy(values), 'node': n['id']})
            if self.choices.guard_returns is None:
                fail('GUARD_ACCEPTANCE_UNRESOLVED', n['id'])
            scalar_check(self.choices.guard_returns, 'bool')
            roots = self.frame_certificate['payload']['frame']['may_write_roots']
            if set(self.choices.guard_writes) != set(roots):
                fail('GUARD_FRAME_CHOICE_INCOMPLETE', roots)
            if not self.choices.guard_returns:
                raise Revert('ABSTRACT_GUARD_REVERT')
            for root in roots:
                value = scalar_check(self.choices.guard_writes[root], type_name(self.boundary.nodes[root]))
                self.writes.append({'root': root, 'path': [], 'before': self.state.get(root, 0),
                                    'after': value, 'node': n['id'], 'abstract_guard_choice': True})
                self.state[root] = value
            return None
        if expr['nodeType'] != 'Identifier' or ref not in self.closure:
            fail('EXEC_CALL_NOT_IN_CLOSURE', ref)
        return self.function(ref, values)

    def statement(self, n, env, continuation=None):
        self.step(n)
        kind = n['nodeType']
        if kind == 'Block':
            for stmt in n['statements']:
                self.statement(stmt, env, continuation)
        elif kind == 'VariableDeclarationStatement':
            declarations = n['declarations']
            if any(d is None for d in declarations):
                fail('EXEC_DECLARATION_TUPLE_HOLE', n['id'])
            if n.get('initialValue') is None:
                values = [default(type_name(d)) for d in declarations]
            else:
                value = self.expr(n['initialValue'], env)
                values = [value] if len(declarations) == 1 else value
            if len(values) != len(declarations):
                fail('EXEC_DECLARATION_ARITY', n['id'])
            for declaration, value in zip(declarations, values):
                env[declaration['id']] = value
        elif kind == 'ExpressionStatement':
            self.expr(n['expression'], env)
        elif kind == 'IfStatement':
            branch = n['trueBody'] if scalar_check(self.expr(n['condition'], env), 'bool') else n.get('falseBody')
            if branch:
                self.statement(branch, env, continuation)
        elif kind == 'WhileStatement':
            while scalar_check(self.expr(n['condition'], env), 'bool'):
                self.statement(n['body'], env, continuation)
        elif kind == 'Return':
            raise Returned(None if n.get('expression') is None else self.expr(n['expression'], env))
        elif kind == 'EmitStatement':
            call = n['eventCall']
            target = self.boundary.nodes[call['expression']['referencedDeclaration']]
            self.events.append({'event': target['name'], 'declaration': target['id'],
                                'arguments': [self.expr(a, env) for a in call['arguments']], 'node': n['id']})
        elif kind == 'PlaceholderStatement':
            if continuation is None:
                fail('EXEC_MODIFIER_PLACEHOLDER', n['id'])
            continuation()
        else:
            fail('EXEC_STATEMENT_UNSUPPORTED', kind)

    def function(self, ref, values):
        if ref in self.call_stack:
            fail('EXEC_RECURSION_UNSUPPORTED', ref)
        fn = self.boundary.nodes[ref]
        params = fn['parameters']['parameters']
        if len(params) != len(values):
            fail('EXEC_FUNCTION_ARITY', ref)
        for param, value in zip(params, values):
            self.value_check(value, param)
        env = {p['id']: v for p, v in zip(params, values)}
        modifiers = fn.get('modifiers', [])

        def body(index):
            if index == len(modifiers):
                self.statement(fn['body'], env)
            else:
                modifier = self.boundary.nodes[modifiers[index]['modifierName']['referencedDeclaration']]
                self.statement(modifier['body'], {}, lambda: body(index + 1))
        self.call_stack.append(ref)
        try:
            try:
                body(0)
            except Returned as returned:
                return returned.value
        finally:
            self.call_stack.pop()
        return None

    def execute(self, arguments, state, token, *, sender, contract, choices=None):
        if self.digest() != self.identity:
            fail('EXEC_ARTIFACT_CHANGED', self.entry)
        if self.frame_certificate:
            validate_reuse(self.boundary, self.frame_certificate, self.context)
        scalar_check(sender, 'address'); scalar_check(contract, 'address')
        token.validate()
        if not contract:
            fail('EXEC_CONTRACT_ADDRESS', contract)
        original_state, original_token = deepcopy(state), deepcopy(token)
        self.state, self.token = deepcopy(state), deepcopy(token)
        self.sender, self.contract = sender, contract
        self.choices = choices or BoundaryChoices()
        self.steps, self.current_node = 0, None
        self.call_stack = []
        self.events, self.transfers, self.writes, self.boundary_calls = [], [], [], []
        try:
            for root, value in self.state.items():
                declaration = self.boundary.nodes.get(root, {})
                if not declaration.get('stateVariable'):
                    fail('EXEC_STATE_ROOT_INVALID', root)
                self.value_check(value, declaration)
            self.function(self.entry, deepcopy(arguments))
        except (Revert, Unsupported) as error:
            # Trace/events and every storage root (including guard may-writes)
            # are discarded. Boundary call diagnostics are not committed effects.
            return Result('REVERT' if isinstance(error, Revert) else 'UNKNOWN',
                          original_state, original_token, [], [], [], self.boundary_calls,
                          getattr(error, 'reason', str(error)), str(error))
        return Result('RETURN', self.state, self.token, self.events, self.transfers,
                      self.writes, self.boundary_calls)
