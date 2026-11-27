import copy
import unittest
from bindcheck_d1.frontends.consumer_boundary_v1 import Boundary
from bindcheck_d1.frontends.guard_frame_v1 import check_guard, check_use_site, validate_reuse
from bindcheck_d1.model_v2 import Unsupported


class GuardFrameTests(unittest.TestCase):
    def setUp(self):
        self.next_id=1
        self.money=self.decl('money',state=True)
        self.index=self.decl('index',state=True)
        self.arg=self.decl('x')
        self.other=self.decl('y')
        self.param=self.decl('x')
        self.guard=self.fn('guard',[self.param],[self.assign(self.index)])
        self.call=self.n('FunctionCall',kind='functionCall',expression=self.ident(self.guard),arguments=[self.ident(self.arg)])
        self.caller=self.fn('caller',[self.arg,self.other],[self.n('ExpressionStatement',expression=self.call)])
        self.context={k:'a'*64 for k in ['policy_sha256','bounds_sha256','assumptions_sha256']}
        self.extra=[]

    def n(self,node_type,**kw):
        i=self.next_id;self.next_id+=1
        return dict(nodeType=node_type,id=i,src='0:1:0',**kw)

    def decl(self,name,state=False,storage='default',typeid='t_uint256'):
        return self.n('VariableDeclaration',name=name,stateVariable=state,storageLocation=storage,
                      typeDescriptions={'typeIdentifier':typeid,'typeString':typeid})

    def ident(self,d):return self.n('Identifier',name=d['name'],referencedDeclaration=d['id'])
    def assign(self,d):return self.n('Assignment',operator='=',leftHandSide=self.ident(d),rightHandSide=self.n('Literal',value='1'))
    def fn(self,name,params,statements):
        return self.n('FunctionDefinition',name=name,visibility='internal',modifiers=[],
                      parameters={'parameters':params},returnParameters={'parameters':[]},body=self.n('Block',statements=statements))

    def boundary(self):
        return Boundary([('synthetic.sol',self.n('SourceUnit',nodes=[self.money,self.index,self.guard,self.caller]+self.extra),b'x')])
    def frame(self,b):return check_guard(b,self.guard['id'],[self.money['id']])
    def cert(self,b):return check_use_site(b,self.caller['id'],self.call['id'],self.frame(b),self.context)
    def rejected(self,b,reason):
        with self.assertRaises(Unsupported) as cm:self.frame(b)
        self.assertEqual(cm.exception.reason,reason)

    def test_write_frame_retains_index_and_revert(self):
        f=self.frame(self.boundary())
        self.assertEqual(f['may_write_roots'],[self.index['id']])
        self.assertEqual(f['abstract_outcomes'][0],'revert')
        self.assertEqual(f['guard_acceptance'],'NOT_ESTABLISHED')

    def test_transitive_protected_write_rejected(self):
        nested=self.fn('nested',[],[self.assign(self.money)]);self.extra.append(nested)
        self.guard['body']['statements'].append(self.n('FunctionCall',kind='functionCall',expression=self.ident(nested),arguments=[]))
        self.rejected(self.boundary(),'FRAME_PROTECTED_WRITE')

    def test_storage_alias_write_rejected(self):
        alias=self.decl('alias',storage='storage',typeid='t_struct_storage_ptr');self.extra.append(alias)
        self.guard['body']['statements'].append(self.assign(alias))
        self.rejected(self.boundary(),'FRAME_REFERENCE_WRITE_UNSUPPORTED')

    def test_memory_reference_parameter_rejected(self):
        self.param.update(storageLocation='memory',typeDescriptions={'typeIdentifier':'t_array_memory_ptr'})
        self.rejected(self.boundary(),'FRAME_MUTABLE_ARGUMENT_UNSUPPORTED')

    def test_unknown_node_and_assembly_rejected(self):
        for kind in ['InlineAssembly','NewExpression','FunctionCallOptions','TryStatement','UncheckedBlock']:
            with self.subTest(kind=kind):
                self.guard['body']['statements'].append(self.n(kind))
                self.rejected(self.boundary(),'FRAME_NODE_UNSUPPORTED')
                self.guard['body']['statements'].pop()

    def test_external_call_with_body_rejected(self):
        nested=self.fn('remote',[],[]);nested['visibility']='public';self.extra.append(nested)
        self.guard['body']['statements'].append(self.n('FunctionCall',kind='functionCall',expression=self.ident(nested),arguments=[]))
        self.rejected(self.boundary(),'FRAME_EXTERNAL_OR_DYNAMIC_CALL')

    def test_lowlevel_and_storage_push_rejected(self):
        for member in ['call','delegatecall','staticcall','push','pop']:
            with self.subTest(member=member):
                self.guard['body']['statements'].append(self.n('FunctionCall',kind='functionCall',expression=self.n('MemberAccess',memberName=member,expression=self.ident(self.index)),arguments=[]))
                self.rejected(self.boundary(),'FRAME_CALL_UNSUPPORTED')
                self.guard['body']['statements'].pop()

    def test_missing_and_indirect_call_rejected(self):
        self.guard['body']['statements'].append(self.n('FunctionCall',kind='functionCall',expression=self.n('Identifier',name='bad',referencedDeclaration=99999),arguments=[]))
        self.rejected(self.boundary(),'CALL_DECLARATION_MISSING')

    def test_builtin_selfdestruct_rejected(self):
        self.guard['body']['statements'].append(self.n('FunctionCall',kind='functionCall',expression=self.n('Identifier',name='selfdestruct',referencedDeclaration=-20),arguments=[]))
        self.rejected(self.boundary(),'FRAME_CALL_UNSUPPORTED')

    def test_unbounded_loop_is_only_a_frame_rule(self):
        self.guard['body']['statements'].append(self.n('WhileStatement',condition=self.n('Literal',value='true'),body=self.n('Block',statements=[])))
        f=self.frame(self.boundary());self.assertEqual(len(f['loops']),1)
        self.assertEqual(f['termination'],'NOT_ESTABLISHED')

    def test_tuple_and_delete_protected_writes_rejected(self):
        for stmt in [self.n('Assignment',operator='=',leftHandSide=self.n('TupleExpression',components=[None,self.ident(self.money)]),rightHandSide=self.n('TupleExpression',components=[])),self.n('UnaryOperation',operator='delete',subExpression=self.ident(self.money))]:
            self.guard['body']['statements'].append(stmt);self.rejected(self.boundary(),'FRAME_PROTECTED_WRITE');self.guard['body']['statements'].pop()

    def test_valid_certificate_rechecked(self):
        b=self.boundary();cert=self.cert(b);self.assertEqual(validate_reuse(b,cert,self.context),cert)

    def test_changed_argument_dependency_invalidates(self):
        b=self.boundary();cert=self.cert(b)
        self.call['arguments']=[self.ident(self.other)]
        with self.assertRaises(Unsupported) as cm:validate_reuse(self.boundary(),cert,self.context)
        self.assertEqual(cm.exception.reason,'FRAME_CACHE_IDENTITY_CHANGED')

    def test_policy_bound_assumption_changes_invalidate(self):
        b=self.boundary();cert=self.cert(b)
        for key in self.context:
            c=dict(self.context);c[key]='b'*64
            with self.subTest(key=key),self.assertRaises(Unsupported):validate_reuse(b,cert,c)

    def test_changed_source_and_ast_invalidate(self):
        b=self.boundary();cert=self.cert(b);b.sources['synthetic.sol']=b'y'
        with self.assertRaises(Unsupported):validate_reuse(b,cert,self.context)
        b.sources['synthetic.sol']=b'x';b.nodes[self.caller['id']]['name']='different'
        with self.assertRaises(Unsupported):validate_reuse(b,cert,self.context)

    def test_forged_frame_rejected(self):
        b=self.boundary();cert=self.cert(b);cert=copy.deepcopy(cert)
        cert['payload']['frame']['may_write_roots']=[]
        with self.assertRaises(Unsupported) as cm:validate_reuse(b,cert,self.context)
        self.assertEqual(cm.exception.reason,'FRAME_CERTIFICATE_CHANGED')

    def test_return_value_not_dropped(self):
        self.guard['returnParameters']['parameters']=[self.decl('returned')]
        self.rejected(self.boundary(),'FRAME_ENTRY_RETURN_UNSUPPORTED')

    def test_virtual_dispatch_rejected(self):
        self.guard['virtual']=True
        self.rejected(self.boundary(),'FRAME_VIRTUAL_DISPATCH_UNSUPPORTED')

    def test_transitive_virtual_dispatch_rejected(self):
        nested=self.fn('nested',[],[]);nested['virtual']=True;self.extra.append(nested)
        self.guard['body']['statements'].append(self.n('FunctionCall',kind='functionCall',expression=self.ident(nested),arguments=[]))
        self.rejected(self.boundary(),'FRAME_VIRTUAL_DISPATCH_UNSUPPORTED')

    def test_user_defined_operator_rejected(self):
        self.guard['body']['statements'].append(self.n('BinaryOperation',operator='+',function=777,leftExpression=self.n('Literal',value='1'),rightExpression=self.n('Literal',value='2')))
        self.rejected(self.boundary(),'FRAME_USER_OPERATOR_UNSUPPORTED')

    def test_checker_version_invalidates_reuse(self):
        b=self.boundary();cert=self.cert(b);cert['payload']['checker_sha256']='0'*64
        with self.assertRaises(Unsupported) as cm:validate_reuse(b,cert,self.context)
        self.assertEqual(cm.exception.reason,'FRAME_CACHE_IDENTITY_CHANGED')

    def test_calldata_binding_checked(self):
        for d in [self.param,self.arg]:
            d.update(storageLocation='calldata',typeDescriptions={'typeIdentifier':'t_array_calldata_ptr','typeString':'uint256[]'})
        b=self.boundary();self.cert(b)
        self.arg['storageLocation']='memory'
        with self.assertRaises(Unsupported) as cm:self.cert(self.boundary())
        self.assertEqual(cm.exception.reason,'FRAME_CALLDATA_BINDING_UNSUPPORTED')


if __name__=='__main__':unittest.main()
