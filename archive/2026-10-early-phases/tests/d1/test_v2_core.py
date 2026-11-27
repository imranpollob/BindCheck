"""Synthetic, adversarial controls for domains/policy and artifact boundaries."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from bindcheck_d1.model_v2 import (Artifact, EvidenceGrade, EvmWord, FieldWord,
                                 FIELD_MODULUS, GateResult, Key, Occurrence,
                                 Policy, Provenance, Unsupported, Verdict)
from bindcheck_d1.policy_v2 import assess_trace, standard_transfer
from bindcheck_d1.frontends.acir_v2 import inventory
from bindcheck_d1.frontends.solidity_v2 import inventory as sol_inventory
from Crypto.Hash import keccak


P = Provenance(Artifact('synthetic', '0'*64), 'fixture', EvidenceGrade.SYNTHETIC)
K = Key('test-rollup', 'burn', 'token', 7, 42, 0xdead)


def occurrence(i, key=K):
    return Occurrence(('frame', i), key, P)


class DomainAndPolicyTests(unittest.TestCase):
    def test_no_field_modulo_coercion(self):
        for value in (-1, FIELD_MODULUS, 2**256, True):
            with self.assertRaises(Unsupported):
                FieldWord(value)
        with self.assertRaises(Unsupported):
            EvmWord(FIELD_MODULUS).field()

    def test_exact_address_alias(self):
        self.assertEqual(EvmWord(2**160 + 0xdead).address(), 0xdead)
        self.assertEqual(EvmWord(2**160).address(), 0)

    def test_optional_is_not_required(self):
        policy = Policy((occurrence(0),), (), 'optional permission')
        result = assess_trace(policy, (), committed=True)
        self.assertFalse(result.authorization_deficits or result.coverage_deficits)

    def test_mandatory_missing_is_coverage_deficit(self):
        policy = Policy((occurrence(0),), (occurrence(0),), 'mandatory')
        self.assertEqual(assess_trace(policy, (), committed=True).coverage_deficits, ((K, 1),))

    def test_multiplicity_not_membership(self):
        effects = (occurrence(2), occurrence(3))
        one = Policy((occurrence(0),), (), 'one permission')
        two = Policy((occurrence(0), occurrence(1)), (), 'two active equal records')
        self.assertEqual(assess_trace(one, effects, committed=True).authorization_deficits, ((K, 1),))
        self.assertFalse(assess_trace(two, effects, committed=True).authorization_deficits)

    def test_duplicate_occurrence_identity_rejected(self):
        with self.assertRaises(Unsupported):
            Policy((occurrence(0), occurrence(0)), (), 'duplicate id')

    def test_wrong_asset_and_recipient(self):
        policy = Policy((occurrence(0),), (occurrence(0),), 'mandatory')
        for key in (replace(K, asset='wrong'), replace(K, recipient=0xbeef)):
            result = assess_trace(policy, (occurrence(1, key),), committed=True)
            self.assertTrue(result.authorization_deficits and result.coverage_deficits)

    def test_reverted_trace_not_committed_effect(self):
        result = assess_trace(Policy((), (), 'empty'), (occurrence(0),), committed=False)
        self.assertEqual(result.reason, 'TRANSITION_REVERTED')
        self.assertFalse(result.authorization_deficits)

    def test_deferral_cannot_be_joint_verification(self):
        policy = Policy((occurrence(0),), (occurrence(0),), 'mandatory')
        result = assess_trace(policy, (), committed=True, deferred=True)
        self.assertEqual(result.reason, 'DEFERRAL_UNSUPPORTED')
        self.assertFalse(hasattr(result, 'verdict'))
        self.assertEqual(GateResult('test', (), (), ()).verdict, Verdict.UNKNOWN)

    def test_expected_verdict_cannot_enter_policy(self):
        with self.assertRaises(TypeError):
            Policy((), (), 'rationale', expected_verdict='VERIFIED_WITHIN_SCOPE')
        with self.assertRaises(TypeError):
            Policy((), (), 'rationale', case_label='repaired')

    def test_policy_provenance_not_implementation_fact(self):
        record = replace(occurrence(0), provenance=replace(P, grade=EvidenceGrade.EXTRACTED))
        with self.assertRaises(Unsupported):
            Policy((record,), (), 'implementation assertion is not policy')

    def test_transfer_sequence_and_failure_state(self):
        original = {1: 10}
        first = standard_transfer(original, 1, EvmWord(2), 7)
        second = standard_transfer(first.balances, 1, EvmWord(2), 7)
        self.assertTrue(first.success)
        self.assertFalse(second.success)
        self.assertEqual(second.balances, {1: 3, 2: 7})
        self.assertEqual(original, {1: 10})

    def test_zero_self_alias_and_funding(self):
        for word, amount, success, expected in [(0, 7, False, {1: 100}),
                                               (1, 7, True, {1: 100}),
                                               (2**160 + 2, 7, True, {1: 93, 2: 7}),
                                               (2, 0, True, {1: 100, 2: 0})]:
            got = standard_transfer({1: 100}, 1, EvmWord(word), amount)
            self.assertEqual((got.success, got.balances), (success, expected))

    def test_token_supply_invariant_checked(self):
        with self.assertRaises(Unsupported):
            standard_transfer({1: 2**256-1, 2: 1}, 1, EvmWord(2), 1)


class AcirBoundaryTests(unittest.TestCase):
    def fixture(self, extra='', public='w1'):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        acir, program = root/'input.txt', root/'program.json'
        acir.write_text('Compiled ACIR for main (non-transformed):\nfunc 0\n'
                        'private parameters: [w0]\npublic parameters: ['+public+']\nreturn values: []\n'
                        'ASSERT w1 - w0 = 0\nBLACKBOX::RECURSIVE_AGGREGATION inputs: [w0, w1]\n'+extra)
        program.write_text(json.dumps({'noir_version': '1.0.0-beta.14+60ccd48e18ad8ce50d5ecda9baf813b712145051',
                                      'abi': {'parameters': [{'name':'secret','visibility':'private','type':{'kind':'field'}},
                                                             {'name':'public','visibility':'public','type':{'kind':'field'}}]}}))
        return acir, program

    def test_no_flat_offset_guess(self):
        result = inventory(*self.fixture())
        self.assertIsNone(result['recursive_calls'][0]['typed_public_inputs'])
        self.assertIn('RECURSION_LAYOUT_UNESTABLISHED', result['reason_codes'])
        self.assertEqual(result['opcodes'][0].text, 'ASSERT w1 - w0 = 0')

    def test_extra_acir_function_not_silently_dropped(self):
        with self.assertRaises(Unsupported) as caught:
            inventory(*self.fixture('func 1\nASSERT w1 = 0\n'))
        self.assertEqual(caught.exception.reason, 'ACIR_FUNCTION_CALL_UNSUPPORTED')

    def test_unknown_opcode_rejected(self):
        with self.assertRaises(Unsupported):
            inventory(*self.fixture('CALL f1\n'))

    def test_abi_count_mismatch_rejected(self):
        with self.assertRaises(Unsupported):
            inventory(*self.fixture(public='w1, w2'))

    def test_unconstrained_bytecode_preserved(self):
        result = inventory(*self.fixture('unconstrained func 0: invert\n0: stop\n'))
        self.assertEqual(result['opcode_counts']['UNCONSTRAINED_BYTECODE'], 2)

    def test_missing_compiler_pin_rejected(self):
        acir, program = self.fixture()
        data = json.loads(program.read_text()); data['noir_version'] = 'unreviewed'
        program.write_text(json.dumps(data))
        with self.assertRaises(Unsupported):
            inventory(acir, program)


class SolidityBoundaryTests(unittest.TestCase):
    def fixture(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        root = Path(tmp.name); source = root/'source.sol'; output = root/'artifact.json'
        source.write_text('synthetic AST fixture, not Solidity execution')
        common = {'src': '0:9:0'}
        def ident(ref): return {'nodeType':'Identifier','referencedDeclaration':ref, **common}
        proof = {'nodeType':'FunctionCall','id':101,'expression':{'nodeType':'MemberAccess','memberName':'verify'},
                 'arguments':[ident(9),ident(7)], **common}
        scan = {'nodeType':'FunctionCall','id':102,'expression':ident(11),
                'arguments':[{'nodeType':'Literal','value':'3'},ident(7),ident(8)], **common}
        names = ['verifyRollup','verifyAllMessages','verifyMessages','verifyMint','verifyBurn',
                 'bytes32ToAddress','executeBurn','executeBurnToAddress']
        functions = [{'nodeType':'FunctionDefinition','name':n,'id':10+i,'body':{},
                      'parameters':{'parameters':[]}, **common} for i,n in enumerate(names)]
        functions[0]['parameters']['parameters'] = [{'name':'publicInputs','id':7,'storageLocation':'calldata'}]
        functions[0]['body'] = {'calls':[proof, scan]}
        data = {'rawMetadata':json.dumps({'compiler':{'version':'0.8.20+commit.a1b79de6'},
                'sources':{'synthetic.sol':{'keccak256':'0x'+keccak.new(digest_bits=256,data=source.read_bytes()).hexdigest()}}}),
                'ast':{'absolutePath':'synthetic.sol','nodes':[{'nodeType':'ContractDefinition','name':'RollupV1','nodes':functions}]}}
        output.write_text(json.dumps(data))
        return output, source, data

    def test_direct_forwarding_fact_only(self):
        output, source, _ = self.fixture()
        result = sol_inventory(output, source)
        self.assertEqual(result['scanner_literal_offset'], 3)
        self.assertIn('CONSUMER_TRANSITION_SEMANTICS_NOT_EXTRACTED', result['reason_codes'])

    def test_wrong_forwarded_reference_rejected(self):
        output, source, data = self.fixture()
        data['ast']['nodes'][0]['nodes'][0]['body']['calls'][0]['arguments'][1]['referencedDeclaration'] = 99
        output.write_text(json.dumps(data))
        with self.assertRaises(Unsupported):
            sol_inventory(output, source)

    def test_source_tampering_rejected(self):
        output, source, _ = self.fixture(); source.write_text('changed')
        with self.assertRaises(Unsupported):
            sol_inventory(output, source)


if __name__ == '__main__':
    unittest.main()
