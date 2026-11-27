"""Synthetic AST and state controls. No ignored compiler artifacts required."""
from copy import deepcopy
import unittest

from bindcheck_d1.frontends.consumer_boundary_v1 import Boundary
from bindcheck_d1.frontends.consumer_execution_v1 import Machine, Token, BoundaryChoices
from bindcheck_d1.model_v2 import Unsupported
from bindcheck_d1.consumer_scope_v2 import assess
from bindcheck_d1.frontends.consumer_execution_v1 import Result


class TokenTests(unittest.TestCase):
    def test_sequential_balance_and_atomic_failure(self):
        t = Token(7, {12: 10}, 10)
        self.assertTrue(t.transfer(12, 14, 7))
        before = deepcopy(t)
        self.assertFalse(t.transfer(12, 14, 7))
        self.assertEqual(t, before)

    def test_self_transfer_uses_updated_sender_balance(self):
        t = Token(7, {12: 10}, 10)
        self.assertTrue(t.transfer(12, 12, 10))
        self.assertEqual(t.balances, {12: 10})

    def test_self_transfer_still_requires_funds(self):
        t = Token(7, {12: 10}, 10)
        self.assertFalse(t.transfer(12, 12, 11))

    def test_zero_amount_is_success(self):
        t = Token(7, {12: 0}, 0)
        self.assertTrue(t.transfer(12, 14, 0))

    def test_zero_recipient_fails_even_zero_amount(self):
        t = Token(7, {12: 10}, 10)
        self.assertFalse(t.transfer(12, 0, 0))

    def test_supply_and_addresses_checked(self):
        for t in [Token(7, {12: 10}, 11), Token(0, {}, 0), Token(7, {0: 1}, 1),
                  Token(7, {2**160: 1}, 1), Token(7, {12: -1}, 0),
                  Token(7, {}, 0, 'empty-account')]:
            with self.subTest(token=t), self.assertRaises(Unsupported): t.validate()

    def test_overflow_excluded_by_supply_consistency(self):
        t = Token(7, {12: 2**256 - 1}, 2**256 - 1)
        self.assertTrue(t.transfer(12, 14, 2**256 - 1))
        self.assertEqual(t.balances[14], 2**256 - 1)


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.next_id = 1
        self.extra = []
        self.state = self.decl('state', state=True)
        self.param = self.decl('value')
        self.entry = self.fn('entry', [self.param], [])

    def n(self, node_type, typ='', **kwargs):
        node = dict(nodeType=node_type, id=self.next_id, src='0:1:0',
                    typeDescriptions={'typeString': typ}, **kwargs)
        self.next_id += 1
        return node

    def decl(self, name, typ='uint256', state=False, location='default', type_node=None):
        return self.n('VariableDeclaration', typ, name=name, stateVariable=state,
                      storageLocation=location,
                      typeName=type_node or self.n('ElementaryTypeName', typ, name=typ))

    def ident(self, decl):
        return self.n('Identifier', decl['typeDescriptions']['typeString'], name=decl['name'], referencedDeclaration=decl['id'])

    def lit(self, value, typ='uint256'):
        return self.n('Literal', typ, kind='bool' if type(value) is bool else 'number',
                      value=str(value).lower())

    def binary(self, op, left, right, typ='uint256'):
        return self.n('BinaryOperation', typ, operator=op, leftExpression=left, rightExpression=right)

    def expr_stmt(self, expr): return self.n('ExpressionStatement', expression=expr)

    def assign(self, decl, value):
        return self.expr_stmt(self.n('Assignment', 'uint256', operator='=', leftHandSide=self.ident(decl), rightHandSide=value))

    def call(self, name, args, ref=-18):
        return self.n('FunctionCall', kind='functionCall', arguments=args,
                      expression=self.n('Identifier', name=name, referencedDeclaration=ref))

    def fn(self, name, params, statements):
        return self.n('FunctionDefinition', name=name, visibility='internal', modifiers=[],
                      parameters={'parameters': params}, returnParameters={'parameters': []},
                      body=self.n('Block', statements=statements))

    def machine(self, statements=None, **kwargs):
        if statements is not None: self.entry['body']['statements'] = statements
        boundary = Boundary([('synthetic.sol', self.n('SourceUnit', nodes=[self.state, self.entry] + self.extra), b'x')])
        return Machine(boundary, self.entry['id'], **kwargs)

    def execute(self, machine, args=None, state=None):
        return machine.execute([7] if args is None else args,
                               {self.state['id']: 1} if state is None else state,
                               Token(7, {12: 10}, 10), sender=14, contract=12)

    def test_declaration_ids_not_variable_names(self):
        self.param['name'] = 'same'; self.state['name'] = 'same'
        result = self.execute(self.machine([self.assign(self.state, self.ident(self.param))]))
        self.assertEqual(result.state[self.state['id']], 7)
        self.assertEqual(result.security_verdict, 'UNKNOWN')

    def test_whole_state_rollback_on_require(self):
        result = self.execute(self.machine([self.assign(self.state, self.lit(2)),
                                           self.expr_stmt(self.call('require', [self.lit(False, 'bool')]))]))
        self.assertEqual(result.outcome, 'REVERT')
        self.assertEqual(result.state[self.state['id']], 1)
        self.assertEqual(result.writes, [])

    def test_unknown_rolls_back_partial_writes(self):
        missing = self.n('Identifier', 'uint256', name='missing', referencedDeclaration=99999)
        result = self.execute(self.machine([self.assign(self.state, self.lit(2)), self.expr_stmt(missing)]))
        self.assertEqual(result.outcome, 'UNKNOWN')
        self.assertEqual(result.state[self.state['id']], 1)

    def test_checked_add_overflow_reverts(self):
        expr = self.binary('+', self.lit(2**256 - 1), self.lit(1))
        result = self.execute(self.machine([self.assign(self.state, expr)]))
        self.assertEqual(result.outcome, 'REVERT')
        self.assertEqual(result.reason, 'ARITHMETIC_OVERFLOW')

    def test_checked_sub_underflow_reverts(self):
        result = self.execute(self.machine([self.assign(self.state, self.binary('-', self.lit(0), self.lit(1)))]))
        self.assertEqual(result.outcome, 'REVERT')

    def test_narrow_arithmetic_uses_compiler_width(self):
        result = self.execute(self.machine([self.assign(self.state,
            self.binary('+', self.lit(2**32 - 1, 'uint32'), self.lit(3, 'uint32'), 'uint32'))]))
        self.assertEqual(result.outcome, 'REVERT')

    def test_negative_or_boolean_uint_input_is_unknown(self):
        machine = self.machine([self.assign(self.state, self.ident(self.param))])
        for value in (-1, True, 2**256, b'wrong'):
            with self.subTest(value=value):
                result = self.execute(machine, [value])
                self.assertEqual(result.outcome, 'UNKNOWN')

    def test_short_circuit_does_not_evaluate_reverting_rhs(self):
        rhs = self.binary('==', self.binary('-', self.lit(0), self.lit(1)), self.lit(0), 'bool')
        expr = self.binary('||', self.lit(True, 'bool'), rhs, 'bool')
        result = self.execute(self.machine([self.expr_stmt(self.call('require', [expr]))]))
        self.assertEqual(result.outcome, 'RETURN')

    def test_low160_truncation(self):
        cast = self.n('FunctionCall', 'uint160', kind='typeConversion', arguments=[self.ident(self.param)],
                      expression=self.n('ElementaryTypeNameExpression', typeName=self.n('ElementaryTypeName', name='uint160')))
        result = self.execute(self.machine([self.assign(self.state, cast)]), [2**160 + 14])
        self.assertEqual(result.state[self.state['id']], 14)

    def test_unhandled_bytes_resize_is_unknown(self):
        cast = self.n('FunctionCall', 'bytes4', kind='typeConversion', arguments=[self.lit(1, 'bytes32')],
                      expression=self.n('ElementaryTypeNameExpression', typeName=self.n('ElementaryTypeName', name='bytes4')))
        result = self.execute(self.machine([self.expr_stmt(cast)]))
        self.assertEqual(result.outcome, 'UNKNOWN')

    def test_all_branches_checked_before_execution(self):
        unsupported = self.n('InlineAssembly')
        body = self.n('IfStatement', condition=self.lit(False, 'bool'), trueBody=unsupported)
        with self.assertRaises(Unsupported): self.machine([body])

    def test_unsupported_call_in_dead_branch_rejected(self):
        call = self.expr_stmt(self.call('selfdestruct', [self.lit(3)]))
        with self.assertRaises(Unsupported):
            self.machine([self.n('IfStatement', condition=self.lit(False, 'bool'), trueBody=call)])

    def test_changed_ast_invalidates_interpreter(self):
        machine = self.machine([self.assign(self.state, self.lit(2))])
        self.entry['body']['statements'][0]['expression']['rightHandSide']['value'] = '3'
        with self.assertRaises(Unsupported): self.execute(machine)

    def test_changed_source_invalidates_interpreter(self):
        machine = self.machine([])
        machine.boundary.sources['synthetic.sol'] = b'y'
        with self.assertRaises(Unsupported): self.execute(machine)

    def test_step_limit_is_unknown_not_revert_or_safe(self):
        loop = self.n('WhileStatement', condition=self.lit(True, 'bool'), body=self.n('Block', statements=[]))
        result = self.execute(self.machine([loop], step_limit=20))
        self.assertEqual((result.outcome, result.reason, result.security_verdict), ('UNKNOWN', 'EXEC_STEP_LIMIT', 'UNKNOWN'))

    def test_virtual_dispatch_and_user_operator_rejected(self):
        self.entry['virtual'] = True
        with self.assertRaises(Unsupported): self.machine([])
        self.entry['virtual'] = False
        expr = self.binary('+', self.lit(1), self.lit(2)); expr['function'] = 999
        with self.assertRaises(Unsupported): self.machine([self.expr_stmt(expr)])

    def test_storage_alias_rejected(self):
        alias = self.decl('alias', location='storage')
        with self.assertRaises(Unsupported):
            self.machine([self.n('VariableDeclarationStatement', declarations=[alias], initialValue=self.lit(1))])

    def test_invalid_state_root_rejected(self):
        result = self.execute(self.machine([]), state={99999: 1})
        self.assertEqual(result.outcome, 'UNKNOWN')

    def test_read_only_calldata_and_bounds(self):
        array_type = self.n('ArrayTypeName', baseType=self.n('ElementaryTypeName', name='bytes32'), length=None)
        self.param = self.decl('words', 'bytes32[]', location='calldata', type_node=array_type)
        self.entry['parameters']['parameters'] = [self.param]
        index = self.n('IndexAccess', 'bytes32', baseExpression=self.ident(self.param), indexExpression=self.lit(1))
        machine = self.machine([self.assign(self.state, index)])
        self.assertEqual(self.execute(machine, [[9, 10]]).state[self.state['id']], 10)
        self.assertEqual(self.execute(machine, [[9]]).outcome, 'REVERT')
        write = self.expr_stmt(self.n('Assignment', 'bytes32', operator='=', leftHandSide=index, rightHandSide=self.lit(3)))
        self.assertEqual(self.execute(self.machine([write]), [[9, 10]]).outcome, 'UNKNOWN')

    def test_input_state_not_mutated(self):
        state = {self.state['id']: 1}
        self.execute(self.machine([self.assign(self.state, self.lit(5))]), state=state)
        self.assertEqual(state, {self.state['id']: 1})

    def test_recursive_call_is_unknown(self):
        result = self.execute(self.machine([self.expr_stmt(self.call('entry', [self.lit(1)], self.entry['id']))]))
        self.assertEqual((result.outcome, result.reason), ('UNKNOWN', 'EXEC_RECURSION_UNSUPPORTED'))

    def test_constant_cannot_be_silently_read_as_zero(self):
        self.state['constant'] = True
        with self.assertRaises(Unsupported): self.machine([self.expr_stmt(self.ident(self.state))])

    def test_nested_write_provenance_is_assignment_not_index(self):
        mapping_type = self.n('Mapping', keyType=self.n('ElementaryTypeName', name='uint256'),
                              valueType=self.n('ElementaryTypeName', name='uint256'))
        self.state = self.decl('values', 'mapping(uint256 => uint256)', state=True, type_node=mapping_type)
        target = self.n('IndexAccess', 'uint256', baseExpression=self.ident(self.state), indexExpression=self.lit(4))
        assignment = self.n('Assignment', 'uint256', operator='=', leftHandSide=target, rightHandSide=self.lit(9))
        result = self.execute(self.machine([self.expr_stmt(assignment)]), state={self.state['id']: {}})
        self.assertEqual(result.writes[0]['node'], assignment['id'])
        self.assertEqual(result.writes[0]['path'], [4])


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.roots = dict(rootHash=1, mints=2, tokens=3, substitutedBurns=4)
        self.state = {1: 17, 2: {}, 3: {0x4b: 7}, 4: {}}
        self.token = Token(7, {12: 8*(2**64-1)}, 8*(2**64-1))
        self.result = Result('RETURN', self.state, self.token, [], [], [], [])
        self.words = [17, 18, 19] + [0]*8

    def check(self):
        return assess(n=8, words=self.words, roots=self.roots, state=self.state,
                      token=self.token, contract=12, execution=self.result)

    def test_admission_never_becomes_security_verdict(self):
        admission = self.check()
        self.assertTrue(admission.admitted)
        self.assertEqual(admission.security_verdict, 'UNKNOWN')

    def test_noncanonical_input_not_reduced(self):
        from bindcheck_d1.model_v2 import FIELD_MODULUS
        self.words[10] = FIELD_MODULUS
        self.assertIn('NONCANONICAL_FIELD', self.check().reasons)

    def test_funding_is_explicit_scope_not_execution_constraint(self):
        self.token.balances[12] = 6; self.token.supply = 6
        self.assertIn('INITIAL_FUNDING_OUTSIDE_V2', self.check().reasons)
        self.assertEqual(self.result.outcome, 'RETURN')

    def test_no_substitution_or_initial_spent_entry(self):
        self.state[4][9] = 14
        self.state[2][42] = {'spent': True}
        self.assertEqual(set(self.check().reasons), {'SUBSTITUTION_UNSUPPORTED', 'INITIAL_SPENT_REGISTRY_OUTSIDE_V2'})

    def test_consumed_burn_limits_and_failed_transfer_remain_unknown(self):
        self.result.boundary_calls.append({'kind': 'token', 'arguments': [0, 2**64], 'success': False})
        result = self.check()
        self.assertEqual(set(result.reasons), {'RECIPIENT_OUTSIDE_V2', 'BURN_AMOUNT_OUTSIDE_V2', 'DEFERRAL_UNSUPPORTED'})
        self.assertFalse(result.admitted)

    def test_ignored_words_are_not_misparsed_as_consumed_amounts(self):
        self.words[10] = 2**200
        self.assertTrue(self.check().admitted)  # execution determines consumption, not this admission checker

    def test_revert_is_not_an_admitted_success(self):
        self.result.outcome = 'REVERT'
        self.assertEqual(self.check().reasons, ('TRANSITION_REVERTED',))

    def test_unknown_execution_is_not_admitted_success(self):
        self.result.outcome = 'UNKNOWN'
        self.assertEqual(self.check().reasons, ('EXECUTION_UNRESOLVED',))


if __name__ == '__main__': unittest.main()
