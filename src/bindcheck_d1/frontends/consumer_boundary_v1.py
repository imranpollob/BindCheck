"""Transitive AST coverage audit, including modifiers and internal library calls.

This is a prerequisite inventory. Located nodes are not an implemented
transition relation, and a pure-call label is not a semantic summary.
"""
import hashlib
import json
from pathlib import Path
from Crypto.Hash import keccak
from ..model_v2 import Unsupported


def walk(value):
    if isinstance(value,dict):
        if 'nodeType' in value:yield value
        for child in value.values():yield from walk(child)
    elif isinstance(value,list):
        for child in value:yield from walk(child)


class Boundary:
    def __init__(self,units):
        self.nodes={};self.sources={};self.node_source={}
        for path,ast,source in units:
            self.sources[path]=source
            for node in walk(ast):
                if 'id' not in node:continue
                key=node['id']
                if key in self.nodes and self.nodes[key]!=node:
                    raise Unsupported('AST_ID_COLLISION',str(key))
                self.nodes[key]=node;self.node_source[key]=path

    def location(self,node):
        path=self.node_source[node['id']]
        start,length,_=map(int,node['src'].split(':'))
        source=self.sources[path]
        if start<0 or length<0 or start+length>len(source):
            raise Unsupported('AST_LOCATION_INVALID',str(node['id']))
        return {'node_id':node['id'],'source':path,'src':node['src'],
                'source_sha256':hashlib.sha256(source).hexdigest(),
                'excerpt':source[start:start+length].decode()}

    def resolve_call(self,expression):
        if expression.get('nodeType')=='FunctionCallOptions':
            return self.resolve_call(expression['expression'])
        ref=expression.get('referencedDeclaration')
        if type(ref) is int and ref>=0:
            target=self.nodes.get(ref)
            if target is None:raise Unsupported('CALL_DECLARATION_MISSING',str(ref))
            return ref,target
        return ref,None

    def storage_roots(self,node):
        if node['nodeType']=='Identifier':
            ref=node.get('referencedDeclaration');decl=self.nodes.get(ref,{})
            if decl.get('stateVariable'):return [{'kind':'state','declaration':ref,'name':decl['name']}]
            if decl.get('storageLocation')=='storage':return [{'kind':'storage_alias','declaration':ref,'name':decl['name']}]
            return []
        if node['nodeType']=='MemberAccess':return self.storage_roots(node['expression'])
        if node['nodeType']=='IndexAccess':return self.storage_roots(node['baseExpression'])
        if node['nodeType']=='TupleExpression':return sum((self.storage_roots(x) for x in node['components'] if x),[])
        raise Unsupported('WRITE_TARGET_UNSUPPORTED',node['nodeType'])

    def audit(self,entry):
        queue=[entry];visited=set();functions=[];calls=[];loops=[];writes=[];guards=[];aliases=[];order=[]
        while queue:
            identity=queue.pop(0)
            if identity in visited:continue
            node=self.nodes.get(identity)
            if node is None or node['nodeType'] not in ('FunctionDefinition','ModifierDefinition'):
                raise Unsupported('FUNCTION_DECLARATION_MISSING',str(identity))
            visited.add(identity)
            if node.get('body') is None:
                raise Unsupported('INTERNAL_BODY_MISSING',node.get('name',''))
            owner={'function_id':identity,'function':node['name']}
            functions.append(dict(owner,mutability=node.get('stateMutability'),location=self.location(node)))
            for modifier in node.get('modifiers',[]):
                ref=modifier['modifierName'].get('referencedDeclaration')
                if ref not in self.nodes:raise Unsupported('MODIFIER_DECLARATION_MISSING',str(ref))
                queue.append(ref)
                calls.append(dict(owner,kind='modifier',target=ref,location=self.location(modifier)))
            for current in walk(node['body']):
                kind=current['nodeType']
                if kind in ('WhileStatement','ForStatement','DoWhileStatement'):
                    condition=current.get('condition')
                    loops.append(dict(owner,kind=kind,location=self.location(current),
                                      condition=None if condition is None else self.location(condition)))
                if kind=='VariableDeclaration' and current.get('storageLocation')=='storage':
                    aliases.append(dict(owner,declaration=current['id'],location=self.location(current)))
                if kind=='Assignment' or (kind=='UnaryOperation' and current['operator'] in ('++','--','delete')):
                    target=current['leftHandSide'] if kind=='Assignment' else current['subExpression']
                    roots=self.storage_roots(target)
                    if roots:writes.append(dict(owner,roots=roots,location=self.location(current)))
                if kind=='InlineAssembly':
                    calls.append(dict(owner,kind='inline_assembly_unmodeled',location=self.location(current)))
                if kind!='FunctionCall':continue
                expression=current['expression']
                if current.get('kind')=='typeConversion':
                    calls.append(dict(owner,kind='cast',location=self.location(current)));continue
                ref,target=self.resolve_call(expression)
                record=dict(owner,location=self.location(current))
                if target is not None and target['nodeType']=='FunctionDefinition':
                    if target.get('body') is not None:
                        queue.append(ref);record.update(kind='defined_function',target=ref,target_name=target['name'])
                    else:
                        record.update(kind='external_interface',target=ref,target_name=target['name'],mutability=target.get('stateMutability'))
                elif target is not None and target['nodeType'] in ('ErrorDefinition','EventDefinition','StructDefinition'):
                    record.update(kind='declaration_constructor',target=ref,target_name=target['name'])
                elif target is not None:
                    raise Unsupported('INDIRECT_CALL_UNRESOLVED',str(ref))
                elif expression.get('nodeType')=='Identifier' and type(ref) is int and ref<0:
                    name=expression['name'];record.update(kind='builtin',name=name)
                    if name in ('require','assert','revert'):guards.append(record)
                elif expression.get('nodeType')=='MemberAccess':
                    base=expression['expression'];member=expression['memberName']
                    if base.get('nodeType')=='Identifier' and base.get('name')=='abi' and base.get('referencedDeclaration',0)<0:
                        record.update(kind='abi_builtin',name=member)
                    elif member in ('call','delegatecall','staticcall'):
                        record.update(kind='low_level_call',name=member)
                    else:
                        raise Unsupported('MEMBER_CALL_UNRESOLVED',member)
                else:
                    raise Unsupported('CALL_TARGET_UNSUPPORTED',expression.get('nodeType',''))
                calls.append(record)
                if identity==entry:order.append(record)
        return {'functions':functions,'calls':calls,'loops':loops,'state_writes':writes,
                'guards':guards,'storage_aliases':aliases,'entry_call_preorder':order,
                'scope':'transitive located AST coverage; no symbolic transition semantics',
                'security_verdict':'UNKNOWN','non_vacuity':'NOT_ESTABLISHED'}


def load_boundaries(directory):
    units={};artifacts=[]
    for path in sorted(Path(directory).glob('*/*.json')):
        if path.parent.name=='build-info':continue
        data=json.loads(path.read_text())
        if 'ast' not in data or 'rawMetadata' not in data:continue
        metadata=json.loads(data['rawMetadata']);ast=data['ast'];name=ast['absolutePath']
        if metadata['compiler']['version']!='0.8.20+commit.a1b79de6':
            raise Unsupported('SOLC_VERSION_UNSUPPORTED',str(path))
        source=Path(name).read_bytes()
        expected=metadata['sources'].get(name,{}).get('keccak256')
        if '0x'+keccak.new(digest_bits=256,data=source).hexdigest()!=expected:
            raise Unsupported('COMPILER_SOURCE_IDENTITY_MISMATCH',name)
        if name in units and units[name][1]!=ast:raise Unsupported('DUPLICATE_SOURCE_AST_MISMATCH',name)
        units[name]=(name,ast,source)
        artifacts.append({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    return Boundary(list(units.values())),artifacts
