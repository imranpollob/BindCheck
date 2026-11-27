#!/usr/bin/env python3
"""Solver-free D1-02 intake/preservation audit, aware of sealed checkpoints.

Living document evolution is separate from immutable historical bytes.
No original audit, baseline, index, source, or old raw evidence is modified.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'results/raw/D1-02'
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
CHECKS, COMMANDS = [], []


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def load(p):
    return json.loads(Path(p).read_text())


def check(name, passed, **details):
    CHECKS.append({'check': name, 'passed': bool(passed), **details})


def git(root, args):
    p = subprocess.run(['git', *args], cwd=root, env=ENV, capture_output=True)
    COMMANDS.append({'argv': ['git', *args], 'cwd': str(root), 'exit_status': p.returncode,
                     'stdout': p.stdout.decode(errors='replace') if args[0] != 'show' else None,
                     'stderr': p.stderr.decode(errors='replace')})
    if p.returncode:
        raise RuntimeError(COMMANDS[-1])
    return p.stdout


def main():
    initial = load(RAW / 'initial-state.json')
    seal_path = ROOT / 'metadata/d1/d1-01-evidence-manifest.json'
    seal = load(seal_path)
    check('original_D1_01_seal_unchanged', sha(seal_path) == initial['seal_sha256'])
    old_raw = {str(p.relative_to(ROOT)) for p in (ROOT / 'results/raw/D1-01').rglob('*') if p.is_file()}
    bad = [p for p, d in seal['raw_files'].items()
           if sha(ROOT / p) != d['sha256'] or (ROOT / p).stat().st_size != d['bytes']]
    check('all_49_old_raw_files_and_exact_set', not bad and old_raw == set(seal['raw_files']), differences=bad)
    living = {'README.md', 'docs/d1/roadmap.md', 'docs/project-status.md'}
    archive = load(RAW / 'prior-checkpoint-manifest.json')
    for row in archive['files']:
        name, expected = row['sealed_path'], seal['deliverable_sha256'][row['sealed_path']]
        b = git(ROOT, ['show', archive['reviewed_commit'] + ':' + name])
        check('historical_checkpoint_' + name, sha(ROOT / row['archived_path']) == expected
              == hashlib.sha256(b).hexdigest())
        if name not in living:
            check('immutable_current_deliverable_' + name, sha(ROOT / name) == expected)
    check('all_nine_checkpoint_files_archived', len(archive['files']) == 9)
    check('old_verifier_unchanged', sha(ROOT / 'scripts/d1_01_verify.py')
          == seal['deliverable_sha256']['scripts/d1_01_verify.py'])

    # Reuse only an unchanged historical filesystem-inventory routine. Do not
    # run that audit's main(): its task-start HEAD/index are a different gate.
    sys.path.insert(0, str(ROOT / 'scripts'))
    import d1_01_verify as old
    expected = load(RAW / 'original-source-inventory.json')
    actual = old.inventory(Path('/home/pollmix/Coding/BindCheck'))
    diff = [k for k in sorted(set(expected) | set(actual)) if expected.get(k) != actual.get(k)]
    check('original_checkout_full_inventory', not diff, entries=len(expected), differences=diff)
    expected = initial['preserved_D1_00']
    actual = {str(p.relative_to(ROOT)): sha(p) for p in (ROOT / 'results/raw/D1-00').rglob('*') if p.is_file()}
    check('entire_D1_00_archive', expected == actual, entries=len(expected))
    for key in ('original', 'worktree'):
        st = initial[key]
        check(key + '_index_unchanged', sha(st['index_path']) == st['index_sha256'])
        for c in st['commands']:
            args = c['argv'][1:]
            if key == 'worktree' and (args[0] == 'status' or args == ['diff', '--binary']):
                continue
            check(key + '_' + ' '.join(args), git(Path(st['root']), args).decode() == c['stdout'])
    allowed = living | {'AGENTS.md', 'docs/d1/workspace.md'}
    bad = [p for p, h in initial['tracked_sha256'].items() if p not in allowed and sha(ROOT / p) != h]
    check('all_other_initial_tracked_files_unchanged', not bad, differences=bad)
    check('new_diff_whitespace', git(ROOT, ['diff', '--check']) == b'')
    for p in ['reports/D1-02.md', 'scripts/d1_02_fetch.py', 'scripts/d1_02_verify.py']:
        proc = subprocess.run(['git', 'diff', '--no-index', '--check', '/dev/null', p], cwd=ROOT, env=ENV, capture_output=True)
        check('new_file_whitespace_' + p, proc.returncode in (0, 1) and not proc.stdout and not proc.stderr,
              exit_status=proc.returncode, output=proc.stdout.decode(), stderr=proc.stderr.decode(),
              note='--no-index can return 1 for differing files; whitespace diagnostics must be empty')
    before = (RAW / 'prior-checkpoint/docs/project-status.md').read_text()
    after = (ROOT / 'docs/project-status.md').read_text()
    rows = [l for l in before.splitlines() if l.startswith('| 2026-')]
    now_rows = [l for l in after.splitlines() if l.startswith('| 2026-')]
    check('prior_checkpoint_rows_preserved', now_rows[:len(rows)] == rows)
    done = re.findall(r'\b(\w+)\["([^"\n]*\[DONE\])"\]', before)
    check('prior_completed_nodes_preserved', all(f'{n}["{label}"]' in after for n, label in done))

    pins = load(RAW / 'pins.json')
    check('intake_protocol_frozen_identity', sha(ROOT / 'protocols/d1/d1-02-intake.json') == pins['protocol_sha256'])
    fetched = []
    for filename in ('fetch-log-01.json', 'fetch-log-02.json'):
        log = load(RAW / filename)
        check('fetch_plan_' + filename, sha(ROOT / log['plan']) == log['plan_sha256'])
        for r in log['requests']:
            p = ROOT / r['path']
            b = p.read_bytes()
            check('source_' + r['path'].removeprefix('results/raw/D1-02/sources/'),
                  r['status'] == 'FETCHED' and r['http_status'] == 200
                  and len(b) == r['bytes'] and sha(p) == r['sha256']
                  and hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()
                  == r['git_blob_expected'] == r['git_blob_actual'])
            fetched.append(r['path'])
    check('65_unique_sources', len(fetched) == len(set(fetched)) == 65)
    for p in pins['families']:
        base = RAW / 'sources' / p['repo'].replace('/', '--')
        tree = load(base / 'tree.json')
        commit = load(base / 'commit.json')
        object_tree = load(base / 'tree-by-object.json')
        resolution = next(r for r in load(RAW / 'tree-object-resolution.json') if r['repo'] == p['repo'])
        check('pinned_tree_' + p['repo'], sha(base / 'tree.json') == p['tree_sha256']
              and commit['sha'] == p['revision']
              and object_tree['sha'] == commit['commit']['tree']['sha']
              and object_tree['tree'] == tree['tree']
              and sha(base / 'tree-by-object.json') == resolution['sha256']
              and resolution['http_status'] == 200
              and not tree.get('truncated') and not object_tree.get('truncated'))
        check('per_family_source_bound_' + p['repo'], sum(1 for f in (base / 'files').rglob('*') if f.is_file()) <= 60)

    matrix = load(ROOT / 'metadata/d1/d1-02-intake.json')
    check('honest_task_gate_status', matrix['task_progress'] == 'ACTIVE' and matrix['selection_gate'] == 'UNRESOLVED'
          and matrix['selected_initial_scope_target'] is None and matrix['substantive_families_screened'] == 2)
    check('no_unrun_success_claims', all(matrix[k] == 0 for k in ('builds_attempted', 'proofs_generated', 'solver_queries',
          'validated_findings', 'confirmed_safe_controls'))
          and all(c['security_verdict'] == 'UNKNOWN' and c['build_status'] == 'NOT_RUN' for c in matrix['candidates']))
    for c in matrix['candidates']:
        for name, loc in c['citations'].items():
            check('citation_' + c['id'] + '_' + name, sha(ROOT / loc['path']) == loc['sha256']
                  and all(0 < n <= len((ROOT / loc['path']).read_text().splitlines()) for n in loc['lines'])
                  and c['revision'] in loc['url'])
    missing = []
    for name in ('README.md', 'AGENTS.md', 'docs/d1/roadmap.md', 'docs/d1/workspace.md', 'docs/project-status.md', 'reports/D1-02.md'):
        p = ROOT / name
        for t in re.findall(r'!?\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)', p.read_text()):
            t = unquote(t.strip('<>').split('#', 1)[0])
            if t and not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', t) and not (p.parent / t).exists():
                missing.append({'document': name, 'target': t})
    check('local_links', not missing, missing=missing)
    check('raw_evidence_ignored', git(ROOT, ['check-ignore', 'results/raw/D1-02']).decode().strip() == 'results/raw/D1-02')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', required=True, type=Path)
    args = ap.parse_args()
    if args.output.exists():
        ap.error('Refusing to overwrite audit evidence')
    try:
        main()
    except Exception as exc:
        check('audit_execution', False, error=type(exc).__name__ + ': ' + str(exc))
    result = {'task': 'D1-02', 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'PASS' if all(c['passed'] for c in CHECKS) else 'FAIL',
              'verifier_sha256': sha(__file__), 'checks': CHECKS, 'commands': COMMANDS,
              'meaning': 'Checkpoint/evidence consistency; no build, security, proof or selection success claim',
              'historical_seal_interpretation': '49 raw files and six immutable deliverables unchanged at current paths; all nine historical deliverables byte-exact in archive and reviewed Git revision; three living documents evolve prospectively'}
    with args.output.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps({'status': result['status'], 'checks': len(CHECKS),
                      'failed': [c for c in CHECKS if not c['passed']]}))
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
