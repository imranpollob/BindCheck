#!/usr/bin/env python3
"""Check a local guard frame into a fresh output directory; no security verdict."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from bindcheck_d1.frontends.consumer_boundary_v1 import load_boundaries, walk
from bindcheck_d1.frontends.guard_frame_v1 import check_guard, check_use_site, validate_reuse
from bindcheck_d1.model_v2 import Unsupported


def check(artifacts):
    boundary, identities = load_boundaries(artifacts)

    def one(kind, name):
        found = [n for n in boundary.nodes.values()
                 if n['nodeType'] == kind and n.get('name') == name]
        if len(found) != 1:
            raise Unsupported('FRAME_UNAMBIGUOUS_SELECTION_REQUIRED', name)
        return found[0]

    caller = one('FunctionDefinition', 'verifyRollup')
    guard = one('FunctionDefinition', 'verifyValidatorSignatures')
    retained = one('VariableDeclaration', 'validatorSetIndex')['id']
    protected = sorted(n['id'] for n in boundary.nodes.values()
                       if n.get('stateVariable') and n['id'] != retained)
    calls = [n for n in walk(caller['body']) if n['nodeType'] == 'FunctionCall'
             and n['expression'].get('referencedDeclaration') == guard['id']]
    if len(calls) != 1:
        raise Unsupported('FRAME_UNAMBIGUOUS_USE_SITE_REQUIRED', 'validator guard')
    files = {'policy_sha256': 'protocols/d1/d1-03-joint-semantics-v2.md',
             'bounds_sha256': 'protocols/d1/d1-03-joint-semantics-v2.json',
             'assumptions_sha256': 'protocols/d1/d1-03-joint-semantics.md'}
    context = {k: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
               for k, p in files.items()}
    frame = check_guard(boundary, guard['id'], protected)
    certificate = check_use_site(boundary, caller['id'], calls[0]['id'], frame, context)
    validate_reuse(boundary, certificate, context)
    summary = {'frame_check': 'PASS', 'security_verdict': 'UNKNOWN',
               'complete_consumer_transition': False,
               'guard_bodies': [boundary.nodes[i]['name'] for i in frame['closure']],
               'may_write': [{'id': i, 'name': boundary.nodes[i]['name']}
                             for i in frame['may_write_roots']],
               'protected_root_count': len(protected), 'loops': frame['loops'],
               'call_bindings': certificate['payload']['bindings'],
               'cache_key': certificate['cache_key'],
               'guard_acceptance': 'NOT_ESTABLISHED', 'non_vacuity': 'NOT_ESTABLISHED',
               'primary_queries': 0, 'replays': 0}
    return certificate, identities, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, default=ROOT / 'build/D1-03/v2-design/out')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        certificate, identities, summary = check(args.artifacts)
    except (Unsupported, OSError, ValueError, KeyError) as error:
        summary = {'frame_check': 'INCOMPLETE', 'security_verdict': 'UNKNOWN',
                   'reason': getattr(error, 'reason', type(error).__name__), 'detail': str(error),
                   'complete_consumer_transition': False}
        (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(json.dumps(summary, indent=2))
        return 2
    (args.output / 'certificate.json').write_text(json.dumps(certificate, indent=2) + '\n')
    (args.output / 'artifact-identities.json').write_text(json.dumps(identities, indent=2) + '\n')
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
