"""Separate small checker for an explicit AssertZero linear-combination proof.

No candidate search or simplification is shared with the certificate generator.
This proves only the supplied equality, not a security verdict or non-vacuity.
"""
from collections import Counter
from ..model_v2 import FIELD_MODULUS, Unsupported


def verify(circuit, certificate):
    accumulated=Counter()
    for index,scalar in certificate['linear_combination']:
        if type(index) is not int or not 0<=index<len(circuit['opcodes']):
            raise Unsupported('CERTIFICATE_INDEX_INVALID',str(index))
        op=circuit['opcodes'][index]
        if op['kind']!='AssertZero':
            raise Unsupported('CERTIFICATE_NON_ASSERT_REFERENCE',str(index))
        expr=op['expression']
        accumulated[()] += scalar*expr['constant']
        for coefficient,witness in expr['linear']:
            accumulated[(witness,)] += scalar*coefficient
        for coefficient,left,right in expr['mul']:
            accumulated[tuple(sorted((left,right)))] += scalar*coefficient
    claimed={}
    for monomial,coefficient in certificate['goal']:
        key=tuple(monomial)
        if tuple(sorted(key))!=key or key in claimed:
            raise Unsupported('CERTIFICATE_GOAL_ENCODING_INVALID','')
        claimed[key]=coefficient % FIELD_MODULUS
    actual={k:v % FIELD_MODULUS for k,v in accumulated.items() if v % FIELD_MODULUS}
    claimed={k:v for k,v in claimed.items() if v}
    if actual!=claimed:
        raise Unsupported('CERTIFICATE_CHECK_FAILED','polynomial identity differs')
    return True


def verify_tree(circuit, tree):
    count=0
    if isinstance(tree,dict):
        if set(tree)=={'goal','linear_combination'}:
            verify(circuit,tree)
            return 1
        for value in tree.values():count+=verify_tree(circuit,value)
    elif isinstance(tree,list):
        for value in tree:count+=verify_tree(circuit,value)
    return count
