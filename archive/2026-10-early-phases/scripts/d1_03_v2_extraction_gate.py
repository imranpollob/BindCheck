#!/usr/bin/env python3
"""Audit actual compiled artifact prerequisites once; UNKNOWN blocks queries."""
import argparse
from dataclasses import asdict, is_dataclass
from enum import Enum
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from bindcheck_d1.frontends import acir_v2, solidity_v2
from bindcheck_d1.model_v2 import Unsupported


def encode(value):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Enum):
        return value.value
    raise TypeError(type(value).__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    results = []
    for revision in ('A', 'B'):
        for layer in ('agg_agg', 'agg_final'):
            name = f'{revision}-1000-{layer}'
            try:
                result = acir_v2.inventory(ROOT / f'build/D1-03/acir/{name}.acir.txt',
                                           ROOT / f'build/D1-03/acir/{name}.program.json')
                (args.output / (name + '.json')).write_text(json.dumps(result, default=encode) + '\n')
                results.append({'artifact': name, 'counts': result['opcode_counts'],
                                'recursive_calls': len(result['recursive_calls']),
                                'reason_codes': result['reason_codes']})
            except Unsupported as error:
                results.append({'artifact': name, 'reason_codes': [error.reason], 'detail': str(error)})
    try:
        result = solidity_v2.inventory(ROOT / 'build/D1-03/v2-design/out/RollupV1.sol/RollupV1.json',
                                        ROOT / 'build/D1-03/consumer/src/rollup3/RollupV1.sol')
        (args.output / 'consumer.json').write_text(json.dumps(result, default=encode, indent=2) + '\n')
        results.append({'artifact': 'consumer', 'functions': list(result['functions']),
                        'scanner_literal_offset': result['scanner_literal_offset'],
                        'reason_codes': result['reason_codes']})
    except Unsupported as error:
        results.append({'artifact': 'consumer', 'reason_codes': [error.reason], 'detail': str(error)})
    summary = {'verdict': 'UNKNOWN', 'primary_queries': 0, 'replays': 0,
               'gate_passed': False, 'scope': 'artifact extraction prerequisites only',
               'non_vacuity': 'NOT_ESTABLISHED', 'artifacts': results,
               'message': 'Current frontend does not establish typed recursive/frame bindings or full consumer transition semantics.'}
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
