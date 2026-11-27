"""Fail-closed frame rule for finite successful internal guard executions.

This checks noninterference with protected storage and caller values, not the
truth of a guard. Normal return and revert remain possible; written roots must
remain in the abstract state. It is not a complete consumer transition model.
"""
import hashlib
import json
from pathlib import Path
from .consumer_boundary_v1 import walk
from ..model_v2 import Unsupported


RULE = 'solc-0.8.20-internal-frame-v1'
# Every supported construct is storage-neutral except the separately inspected
# assignment/increment/delete and internal-call rules. No assembly, new,
# external calls, function values, try/catch or function-call options.
NODES = frozenset('Block ExpressionStatement VariableDeclarationStatement VariableDeclaration '
    'ElementaryTypeName ElementaryTypeNameExpression UserDefinedTypeName IdentifierPath '
    'ArrayTypeName Mapping ParameterList Identifier Literal BinaryOperation UnaryOperation '
    'Assignment FunctionCall MemberAccess IndexAccess TupleExpression IfStatement '
    'ForStatement WhileStatement DoWhileStatement Break Continue Return RevertStatement '
    'Conditional'.split())
BUILTINS = frozenset(('require', 'assert', 'revert', 'keccak256', 'sha256', 'ripemd160',
                      'ecrecover', 'addmod', 'mulmod'))
BINARY = frozenset(('+','-','*','/','%','**','<<','>>','&','|','^','==','!=','<','>','<=','>=','&&','||'))
UNARY = frozenset(('!','~','-','++','--','delete'))
ASSIGN = frozenset(('=','+=','-=','*=','/=','%=','<<=','>>=','&=','|=','^='))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def fail(reason, value):
    raise Unsupported(reason, str(value))


def scalar(decl):
    kind=decl.get('typeDescriptions',{}).get('typeIdentifier','')
    return (kind.startswith(('t_uint','t_int','t_bytes')) and '_ptr' not in kind and
            kind not in ('t_bytes_storage','t_bytes_memory')) or kind.startswith(('t_bool','t_address','t_enum'))


def target_roots(boundary, target):
    kind=target['nodeType']
    if kind=='TupleExpression':
        return set().union(*(target_roots(boundary,x) for x in target['components'] if x))
    if kind=='MemberAccess':return target_roots(boundary,target['expression'])
    if kind=='IndexAccess':return target_roots(boundary,target['baseExpression'])
    if kind!='Identifier':fail('FRAME_WRITE_TARGET_UNSUPPORTED',kind)
    ref=target.get('referencedDeclaration');decl=boundary.nodes.get(ref)
    if not decl or decl['nodeType']!='VariableDeclaration':fail('FRAME_WRITE_DECLARATION_MISSING',ref)
    if decl.get('stateVariable'):return {ref}
    # Never guess a storage alias's origin, even when a name looks harmless.
    if decl.get('storageLocation') in ('storage','calldata'):
        fail('FRAME_REFERENCE_WRITE_UNSUPPORTED',ref)
    if decl.get('storageLocation')=='memory':fail('FRAME_MEMORY_WRITE_UNSUPPORTED',ref)
    if not scalar(decl):fail('FRAME_LOCAL_WRITE_TYPE_UNSUPPORTED',ref)
    return set()


def internal_target(boundary, expression):
    ref,target=boundary.resolve_call(expression)
    if target is None:return None
    if target['nodeType']=='ErrorDefinition':return 'error'
    if target['nodeType']!='FunctionDefinition':fail('FRAME_CALL_TARGET_UNSUPPORTED',ref)
    if target.get('visibility') not in ('internal','private') or target.get('body') is None:
        fail('FRAME_EXTERNAL_OR_DYNAMIC_CALL',ref)
    # A MemberAccess must be an internal library dispatch, not x.f() merely
    # resolving to a function declaration. Compiler type is also pinned.
    if expression['nodeType']=='MemberAccess':
        base=expression['expression'];owner=boundary.nodes.get(base.get('referencedDeclaration'),{})
        if base['nodeType']!='Identifier' or owner.get('nodeType')!='ContractDefinition' or owner.get('contractKind')!='library':
            fail('FRAME_MEMBER_DISPATCH_UNSUPPORTED',ref)
    elif expression['nodeType']!='Identifier':fail('FRAME_CALL_EXPRESSION_UNSUPPORTED',ref)
    return ref


def check_guard(boundary, entry, protected):
    if boundary.nodes.get(entry,{}).get('returnParameters',{}).get('parameters'):
        fail('FRAME_ENTRY_RETURN_UNSUPPORTED',entry)
    pending=[entry];seen=set();writes=set();sites=[];loops=[];calls=[]
    protected=set(protected)
    if not protected:fail('FRAME_PROTECTED_SET_EMPTY','')
    for ref in protected:
        if not boundary.nodes.get(ref,{}).get('stateVariable'):fail('FRAME_PROTECTED_ROOT_INVALID',ref)
    while pending:
        identity=pending.pop()
        if identity in seen:continue
        fn=boundary.nodes.get(identity,{})
        if fn.get('nodeType')!='FunctionDefinition' or fn.get('visibility') not in ('internal','private') or fn.get('body') is None:
            fail('FRAME_FUNCTION_UNSUPPORTED',identity)
        if fn.get('virtual'):fail('FRAME_VIRTUAL_DISPATCH_UNSUPPORTED',identity)
        if fn.get('modifiers'):fail('FRAME_MODIFIER_UNSUPPORTED',identity)
        for param in fn['parameters']['parameters']:
            if param.get('storageLocation')!='calldata' and not scalar(param):
                fail('FRAME_MUTABLE_ARGUMENT_UNSUPPORTED',param['id'])
        seen.add(identity)
        for n in walk(fn['body']):
            kind=n['nodeType']
            if kind not in NODES:fail('FRAME_NODE_UNSUPPORTED',kind)
            if kind in ('BinaryOperation','UnaryOperation') and n.get('function') is not None:
                fail('FRAME_USER_OPERATOR_UNSUPPORTED',n['function'])
            if kind=='BinaryOperation' and n['operator'] not in BINARY:fail('FRAME_OPERATOR_UNSUPPORTED',n['operator'])
            if kind=='UnaryOperation' and n['operator'] not in UNARY:fail('FRAME_OPERATOR_UNSUPPORTED',n['operator'])
            if kind=='Assignment' and n['operator'] not in ASSIGN:fail('FRAME_OPERATOR_UNSUPPORTED',n['operator'])
            if kind=='Assignment' or kind=='UnaryOperation' and n['operator'] in ('++','--','delete'):
                roots=target_roots(boundary,n['leftHandSide'] if kind=='Assignment' else n['subExpression'])
                if roots & protected:fail('FRAME_PROTECTED_WRITE',sorted(roots & protected))
                writes.update(roots);sites.append({'node_id':n['id'],'roots':sorted(roots)})
            if kind in ('ForStatement','WhileStatement','DoWhileStatement'):loops.append(n['id'])
            if kind!='FunctionCall':continue
            expr=n['expression']
            if n.get('kind')=='typeConversion':
                if expr.get('nodeType')!='ElementaryTypeNameExpression':fail('FRAME_CAST_UNSUPPORTED',expr['nodeType'])
                continue
            if n.get('kind')!='functionCall':fail('FRAME_CALL_KIND_UNSUPPORTED',n.get('kind'))
            target=internal_target(boundary,expr)
            if target=='error':calls.append({'node_id':n['id'],'kind':'error'});continue
            if target is not None:
                pending.append(target);calls.append({'node_id':n['id'],'kind':'internal','target':target});continue
            ref=expr.get('referencedDeclaration')
            if expr['nodeType']=='Identifier' and type(ref) is int and ref<0 and expr['name'] in BUILTINS:
                calls.append({'node_id':n['id'],'kind':'storage_neutral_builtin','name':expr['name']});continue
            if expr['nodeType']=='MemberAccess':
                base=expr['expression']
                if base['nodeType']=='Identifier' and base.get('name')=='abi' and base.get('referencedDeclaration',0)<0 and expr['memberName'] in ('encode','encodePacked'):
                    calls.append({'node_id':n['id'],'kind':'abi','name':expr['memberName']});continue
            fail('FRAME_CALL_UNSUPPORTED',n['id'])
    return {'rule':RULE,'entry':entry,'closure':sorted(seen),'may_write_roots':sorted(writes),
            'protected_roots':sorted(protected),'write_sites':sites,'calls':calls,'loops':loops,
            'claim':'successful-return frame only; every other storage root and immutable calldata preserved',
            'abstract_outcomes':['revert','return with arbitrary values for may_write_roots'],
            'guard_acceptance':'NOT_ESTABLISHED','termination':'NOT_ESTABLISHED'}


def check_use_site(boundary, caller, call_id, frame, context):
    # Bind to the entire AST/source set and context, not a function name or
    # isolated callee hash. This makes changed data dependencies invalidate reuse.
    required={'policy_sha256','bounds_sha256','assumptions_sha256'}
    if set(context)!=required or any(not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for v in context.values()):
        fail('FRAME_CONTEXT_INCOMPLETE',context)
    fn=boundary.nodes.get(caller,{})
    if fn.get('nodeType')!='FunctionDefinition':fail('FRAME_CALLER_INVALID',caller)
    calls=[n for n in walk(fn['body']) if n.get('id')==call_id and n['nodeType']=='FunctionCall']
    if len(calls)!=1:fail('FRAME_USE_SITE_MISSING',call_id)
    call=calls[0]
    if internal_target(boundary,call['expression'])!=frame['entry']:fail('FRAME_USE_SITE_TARGET_CHANGED',call_id)
    callee=boundary.nodes[frame['entry']];params=callee['parameters']['parameters']
    if len(params)!=len(call['arguments']):fail('FRAME_ARGUMENT_COUNT',call_id)
    binding=[]
    for param,arg in zip(params,call['arguments']):
        if arg['nodeType']!='Identifier':fail('FRAME_ARGUMENT_EXPRESSION_UNSUPPORTED',arg['nodeType'])
        decl=boundary.nodes.get(arg.get('referencedDeclaration'),{})
        if decl.get('nodeType')!='VariableDeclaration':fail('FRAME_ARGUMENT_DECLARATION_MISSING',arg['id'])
        if param.get('storageLocation')=='calldata':
            if decl.get('storageLocation')!='calldata' or decl.get('typeDescriptions')!=param.get('typeDescriptions'):
                fail('FRAME_CALLDATA_BINDING_UNSUPPORTED',arg['id'])
        elif not scalar(decl) or decl.get('typeDescriptions')!=param.get('typeDescriptions'):
            fail('FRAME_SCALAR_BINDING_UNSUPPORTED',arg['id'])
        binding.append({'parameter':param['id'],'argument_declaration':decl['id'],'argument_node':arg['id']})
    # Recompute rather than trusting a caller-supplied frame certificate.
    checked=check_guard(boundary,frame['entry'],frame['protected_roots'])
    if checked!=frame:fail('FRAME_CERTIFICATE_CHANGED',frame['entry'])
    payload={'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'frame':frame,'caller':caller,'call_id':call_id,'bindings':binding,'context':context,
             'ast_sha256':digest(boundary.nodes),'source_sha256':{p:hashlib.sha256(s).hexdigest() for p,s in sorted(boundary.sources.items())}}
    return {'payload':payload,'cache_key':digest(payload),'scope':'local guard frame, not full transition/replay or security verdict'}


def validate_reuse(boundary, certificate, context):
    old=certificate['payload']
    current=check_use_site(boundary,old['caller'],old['call_id'],old['frame'],context)
    if current!=certificate:fail('FRAME_CACHE_IDENTITY_CHANGED',old['call_id'])
    return current
