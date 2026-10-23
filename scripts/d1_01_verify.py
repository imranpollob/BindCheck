#!/usr/bin/env python3
"""Read-only D1-01 preservation/result checks; output must be a new file.

Does not run a solver and does not establish extraction or encoding soundness.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'results/raw/D1-01'
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
CHECKS = []
COMMANDS = []


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def load(p):
    return json.loads(Path(p).read_text())


def inventory(root):
    out = {}
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d != '.git')
        for name in sorted(names + dirs):
            if name == '.git':
                continue
            p = Path(base) / name
            s = p.lstat()
            if p.is_symlink():
                e = {'kind': 'symlink', 'target': os.readlink(p), 'mode': stat.S_IMODE(s.st_mode)}
            elif p.is_file():
                e = {'kind': 'file', 'sha256': sha(p), 'bytes': s.st_size, 'mode': stat.S_IMODE(s.st_mode)}
            else:
                continue
            out[str(p.relative_to(root))] = e
    return out


def check(name, passed, **data):
    CHECKS.append({'check': name, 'passed': bool(passed), **data})


def compare(name, expected, actual):
    diff = [p for p in sorted(set(expected) | set(actual)) if expected.get(p) != actual.get(p)]
    check(name, not diff, expected_count=len(expected), actual_count=len(actual), differences=diff)


def git(root, *argv):
    p = subprocess.run(['git', *argv], cwd=root, env=ENV, capture_output=True, text=True)
    COMMANDS.append({'argv': ['git', *argv], 'cwd': str(root), 'exit_status': p.returncode,
                     'stdout': p.stdout, 'stderr': p.stderr})
    if p.returncode:
        raise RuntimeError(COMMANDS[-1])
    return p.stdout


def main():
    initial = load(RAW / 'initial-state.json')
    source = Path('/home/pollmix/Coding/BindCheck')
    compare('original_source_files_modes_symlinks', initial['source_inventory'], inventory(source))
    compare('entire_D1_00_archive', initial['d1_00_inventory'], inventory(ROOT / 'results/raw/D1-00'))
    for key, root in [('source', source), ('worktree', ROOT)]:
        before = initial[key]
        check(key + '_index_bytes', sha(before['index_path']) == before['index_sha256'])
        for c in before['commands']:
            args = c['command'][1:]
            if key == 'worktree' and args in (['status', '--porcelain=v1', '--untracked-files=all'], ['diff', '--binary']):
                continue
            check(key + '_' + ' '.join(args), git(root, *args) == c['stdout'])
    allowed = {'README.md', 'docs/d1/roadmap.md', 'docs/project-status.md'}
    changes = [p for p, h in initial['tracked_inventory'].items() if p not in allowed and sha(ROOT / p) != h]
    check('historical_reports_code_and_other_tracked_files', not changes, changed=changes)
    check('new_diff_whitespace', git(ROOT, 'diff', '--check') == '')
    check('staged_diff_still_empty', git(ROOT, 'diff', '--cached', '--binary') == '')
    old = git(ROOT, 'show', initial['worktree']['commands'][0]['stdout'].strip() + ':docs/project-status.md')
    new = (ROOT / 'docs/project-status.md').read_text()
    old_rows = [s for s in old.splitlines() if s.startswith('| 2026-')]
    new_rows = [s for s in new.splitlines() if s.startswith('| 2026-')]
    check('checkpoint_rows_preserved', new_rows[:len(old_rows)] == old_rows, count=len(old_rows))
    nodes = re.findall(r'\b(\w+)\["([^"\n]*\[DONE\])"\]', old)
    check('completed_nodes_preserved', all(f'{n}["{label}"]' in new for n, label in nodes), count=len(nodes))

    manifests = ['33_v3_freeze/00_sha256.txt', '35_v5_compact/00_freeze_sha256.txt',
                 '35_v5_compact/20_reducer_sha256.txt', '35_v5_compact/30_audit_sha256.txt']
    for name in manifests:
        entries = []
        for line in (ROOT / 'results/raw/D1-00/baseline-results/T22' / name).read_text().splitlines():
            expected, filename = line.split(maxsplit=1)
            if filename.startswith('results/raw/'):
                p = ROOT / 'results/raw/D1-00/baseline-results' / filename.removeprefix('results/raw/')
            else:
                p = ROOT / filename
            entries.append({'path': str(p), 'expected': expected, 'actual': sha(p)})
        check('historical_freeze_' + name, all(e['expected'] == e['actual'] for e in entries), entries=entries)

    manifest_path = ROOT / 'metadata/d1/d1-01-execution-manifest.json'
    m = load(manifest_path)
    bad = [p for p, h in {**m['frozen_file_sha256'], **m['runtime_library_sha256']}.items() if sha(p) != h]
    check('D1_01_frozen_inputs_and_runtime', not bad, changed=bad)
    check('setup_budget', m['setup_elapsed_seconds'] < m['setup_limit_seconds'] == 3600)
    gen = load(RAW / 'generation-audit.json')
    matrix = load(ROOT / 'metadata/d1/d1-01-query-matrix.json')
    rows = matrix['rows']
    expected_slots = {c + '/' + q for c in ('check_added', 'running_flag') for q in ('nonvacuous', 'prefix', 'tail')}
    check('six_unique_primary_slots', len(rows) == 6 and {r['slot'] for r in rows} == expected_slots)
    attempts = list((RAW / 'primary_running_flag').glob('*.attempt.json'))
    check('one_attempt_per_missing_slot', len(attempts) == 3 and {p.name for p in attempts} == {q + '.attempt.json' for q in ('nonvacuous', 'prefix', 'tail')})
    check('primary_budget', len(attempts) * 300 == 900 <= m['maximum_primary_solver_budget_seconds'] == 1800)
    for r in rows:
        q, case = r['obligation'], r['case']
        p = ROOT / r['evidence_path']
        d = load(p)
        sr = d['solver_record'] if case == 'check_added' else d
        g = next(g for g in gen if g['case'] == case and g['query'] == q)
        check('row_integrity_' + r['slot'], sha(p) == r['evidence_sha256']
              and sha(ROOT / r['query_path']) == r['query_sha256'] == d['smt_sha256'] == g['smt_sha256']
              and r['exit_status'] == sr['exit_status'] and r['timed_out'] == sr['timed_out']
              and r['elapsed_seconds'] == d['seconds'] and r['command'] == sr['command']
              and r['stdout'] == sr['stdout'] and r['stderr'] == sr['stderr'])
        check('timeout_verdict_' + r['slot'], r['verdict'] == 'UNKNOWN'
              and sr['timed_out'] is True and sr['exit_status'] == -9 and 300 <= d['seconds'] < 305)
        if case == 'running_flag':
            attempt = load(p.with_name(q + '.attempt.json'))
            limits = (ROOT / d['proc_limits_path']).read_text()
            check('runtime_limit_' + q, bool(re.search(r'Max address space\s+4294967296\s+4294967296\s+bytes', limits)))
            check('prefrozen_execution_' + q, d['manifest_sha256'] == sha(manifest_path)
                  == attempt['manifest_sha256'] and attempt['started_at_utc'] > m['frozen_at_utc'])
            check('raw_streams_' + q, p.with_name(q + '.stdout.txt').read_text() == sr['stdout']
                  and p.with_name(q + '.stderr.txt').read_text() == sr['stderr'])
    check('self_check_assertions_enabled', load(RAW / 'self-check.json')['assertions_enabled'] is True
          and load(RAW / 'self-check.json')['category_vectors'] == 65536)
    check('saved_blocker_audit', load(RAW / 'blocker-audit.json')['status'] == 'pass'
          and load(RAW / 'blocker-audit-command.json')['exit_status'] == 0)
    live = load(RAW / 'live-runtime-prefix.json')
    check('observed_local_runtime', live['no_original_checkout_mapping'] is True
          and live['exe'] == str(ROOT / 'tools/cvc5-1.4.2-gpl/bin/cvc5')
          and all(sha(p) == h for p, h in live['loaded_file_sha256'].items()))
    remaining = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            if (p / 'exe').resolve() == ROOT / 'tools/cvc5-1.4.2-gpl/bin/cvc5':
                remaining.append(p.name)
        except (FileNotFoundError, PermissionError):
            pass
    check('no_primary_solver_process_left_running', not remaining, pids=remaining)

    docs = [ROOT / p for p in ('README.md', 'docs/d1/roadmap.md', 'docs/project-status.md', 'reports/D1-01.md')]
    missing = []
    for p in docs:
        for target in re.findall(r'!?\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)', p.read_text()):
            t = unquote(target.strip('<>').split('#', 1)[0])
            if t and not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', t) and not (p.parent / t).exists():
                missing.append({'document': str(p), 'target': t})
    check('local_markdown_links', not missing, missing=missing, scope='Targets only; no anchor or external URL check')
    check('raw_and_toolchain_ignored', git(ROOT, 'check-ignore', 'results/raw/D1-01', 'tools/cvc5-1.4.2-gpl').splitlines()
          == ['results/raw/D1-01', 'tools/cvc5-1.4.2-gpl'])


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        ap.error('Refusing to overwrite existing validation output')
    try:
        main()
    except Exception as exc:
        check('verification_execution', False, error=str(exc))
    result = {'task': 'D1-01', 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'PASS' if all(c['passed'] for c in CHECKS) else 'FAIL',
              'verifier_sha256': sha(__file__), 'checks': CHECKS, 'commands': COMMANDS,
              'scope': 'Evidence consistency and preservation; not an independent encoding/proof audit'}
    with args.output.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps({'status': result['status'], 'checks': len(CHECKS),
                      'failed': [c['check'] for c in CHECKS if not c['passed']]}))
    sys.exit(0 if result['status'] == 'PASS' else 1)
