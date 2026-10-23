#!/usr/bin/env python3
"""Check the frozen D1-03 protocol's transfer-failure completion obstacle.

This is a two-row conditional protocol diagnostic, not a joint SMT query,
an ACIR witness, an EVM execution or an implementation correctness test.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        ap.error('Refusing to overwrite a diagnostic')
    frozen = ROOT / 'protocols/d1/d1-03-preflight-01.json'
    protocol = json.loads(frozen.read_text())
    identities = {p: sha(ROOT / p) == expected for p, expected in protocol['inputs'].items()}
    spec = json.loads((ROOT / 'protocols/d1/d1-03-joint-semantics.json').read_text())
    text = (ROOT / 'protocols/d1/d1-03-joint-semantics.md').read_text()
    burn = spec['seeds']['S2'][1]['messages_prefix']
    checks = {
        'input_identities_match_freeze': all(identities.values()),
        'S2_contains_kind_3_burn': int(burn[0], 16) == 3,
        'transfer_success_is_free': spec['prestate']['transfer_success'] == 'free boolean per attempt',
        'DEFER_is_required_goal': 'G-DEFER' in spec['goals'],
        'verified_rule_requires_DEFER_UNSAT': 'AUTH-SHARED, COV-UNMATCHED, COV-SHARED and DEFER goals are all UNSAT' in text,
        'repair_completion_requires_verification': 'and VERIFIED_WITHIN_SCOPE under the' in text,
        'failed_attempt_is_unknown': 'UNKNOWN (`DEFERRAL_UNSUPPORTED`)' in text,
    }
    # Conditional on a matching burn attempt in an otherwise admitted
    # transition. Producer feasibility and replay are deliberately not asserted.
    rows = [{'compatible_burn_attempt': True, 'ok_j': ok,
             'committed_burn_effect': ok, 'G_DEFER_for_this_attempt': not ok,
             'v1_requires_unknown_for_this_branch': not ok} for ok in (False, True)]
    result = {
        'task': 'D1-03 preflight-01', 'at_utc': datetime.now(timezone.utc).isoformat(),
        'argv': [sys.executable, '-I', *sys.argv], 'python': sys.version, 'cwd': str(ROOT),
        'script_sha256': sha(Path(__file__)), 'protocol_sha256': sha(frozen),
        'checks': checks, 'input_identities': identities, 'conditional_truth_table': rows,
        'diagnostic_status': 'PASS' if all(checks.values()) else 'FAIL',
        'protocol_gate': 'REVIEW_REQUIRED', 'research_verdict': 'UNKNOWN',
        'reason': 'For a compatible burn attempt the declared free failure branch triggers G-DEFER; v1 cannot promise a verified repaired result while admitting it and requiring DEFER UNSAT.',
        'limits': 'Conditional Boolean consequence only. No full-query SAT/UNSAT, non-vacuity, proof, replay or flaw in Payy established.',
    }
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'diagnostic_status': result['diagnostic_status'], 'checks': checks,
                      'protocol_gate': result['protocol_gate'], 'research_verdict': 'UNKNOWN'}))
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
