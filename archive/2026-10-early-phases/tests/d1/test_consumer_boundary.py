"""Synthetic transitive-coverage controls; no execution or verification claim."""
import unittest
from bindcheck_d1.frontends.consumer_boundary_v1 import Boundary
from bindcheck_d1.model_v2 import Unsupported


class BoundaryTests(unittest.TestCase):
    def node(self,node_type,id,**extra):return dict(nodeType=node_type,id=id,src='0:1:0',**extra)

    def call(self,id,target,name='helper'):
        return self.node('FunctionCall',id,kind='functionCall',expression=self.node('Identifier',id+100,referencedDeclaration=target,name=name),arguments=[])

    def function(self,id,name,body,modifiers=None):
        return self.node('FunctionDefinition',id,name=name,body=self.node('Block',id+1000,statements=body),modifiers=modifiers or [],stateMutability='nonpayable')

    def boundary(self,nodes):return Boundary([('synthetic',self.node('SourceUnit',0,nodes=nodes),b'x')])

    def test_transitive_function_and_modifier_are_included(self):
        modifier=self.node('ModifierDefinition',3,name='guard',body=self.node('Block',1003,statements=[self.call(20,4)]))
        invoke=self.node('ModifierInvocation',10,modifierName=self.node('IdentifierPath',11,referencedDeclaration=3))
        entry=self.function(1,'entry',[self.call(21,2)],modifiers=[invoke])
        helpers=[self.function(2,'helper',[]),self.function(4,'nested',[])]
        audit=self.boundary([entry,modifier,*helpers]).audit(1)
        self.assertEqual({f['function_id'] for f in audit['functions']},{1,2,3,4})

    def test_missing_transitive_call_rejected(self):
        with self.assertRaises(Unsupported):self.boundary([self.function(1,'entry',[self.call(20,99)])]).audit(1)

    def test_missing_modifier_rejected(self):
        invoke=self.node('ModifierInvocation',10,modifierName=self.node('IdentifierPath',11,referencedDeclaration=99))
        with self.assertRaises(Unsupported):self.boundary([self.function(1,'entry',[],[invoke])]).audit(1)

    def test_reachable_overload_only(self):
        nodes=[self.function(1,'entry',[self.call(20,2)]),self.function(2,'helper',[]),self.function(3,'helper',[self.call(21,99)])]
        audit=self.boundary(nodes).audit(1)
        self.assertEqual(len(audit['functions']),2)

    def test_storage_alias_write_not_lost(self):
        alias=self.node('VariableDeclaration',5,name='alias',storageLocation='storage',stateVariable=False)
        assignment=self.node('Assignment',8,leftHandSide=self.node('MemberAccess',9,expression=self.node('Identifier',10,referencedDeclaration=5),memberName='spent'))
        result=self.boundary([self.function(1,'entry',[alias,assignment])]).audit(1)
        self.assertEqual(result['state_writes'][0]['roots'][0]['kind'],'storage_alias')

    def test_nested_mapping_write_keeps_root(self):
        state=self.node('VariableDeclaration',5,name='mints',storageLocation='default',stateVariable=True)
        target=self.node('MemberAccess',9,expression=self.node('IndexAccess',10,baseExpression=self.node('Identifier',11,referencedDeclaration=5)),memberName='spent')
        assignment=self.node('Assignment',8,leftHandSide=target)
        result=self.boundary([state,self.function(1,'entry',[assignment])]).audit(1)
        self.assertEqual(result['state_writes'][0]['roots'][0]['name'],'mints')

    def test_external_interface_is_not_assumed_implemented(self):
        target=self.node('FunctionDefinition',2,name='verify',body=None,stateMutability='view')
        result=self.boundary([self.function(1,'entry',[self.call(20,2)]),target]).audit(1)
        self.assertEqual(result['calls'][0]['kind'],'external_interface')
        self.assertEqual(result['security_verdict'],'UNKNOWN')

    def test_loop_condition_and_builtin_recorded(self):
        loop=self.node('WhileStatement',40,condition=self.node('Literal',41,value='true'),body=self.node('Block',42,statements=[]))
        result=self.boundary([self.function(1,'entry',[loop,self.call(20,-1,'ecrecover')])]).audit(1)
        self.assertEqual(len(result['loops']),1)
        self.assertEqual(result['calls'][0]['name'],'ecrecover')

    def test_id_collision_rejected(self):
        with self.assertRaises(Unsupported):self.boundary([self.function(1,'one',[]),self.function(1,'two',[])])


if __name__=='__main__':unittest.main()
