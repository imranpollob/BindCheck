#!/usr/bin/env python3
"""Offline audit of inherited D1-02 continuation evidence; never run experiments.

Uses a separately frozen reconciliation protocol. Outputs are exclusive-create.
PASS means byte/provenance consistency, not a security or selection verdict.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'results/raw/D1-02/reconciliation-01'
OLD = ROOT / 'results/raw/D1-02/continuation-01'
LIVING = {'README.md', 'docs/d1/roadmap.md', 'docs/project-status.md', 'docs/d1/workspace.md'}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Refusing to overwrite an audit output')
    checks = []

    def check(name, passed, detail=None):
        checks.append({'name': name, 'passed': bool(passed), 'detail': detail})

    initial = read(RAW / 'initial-state.json')
    protocol = ROOT / 'protocols/d1/d1-02-reconciliation-01.json'
    check('audit protocol unchanged since capture', digest(protocol) == initial['protocol_sha256'])
    check('all inherited raw bytes preserved', all(
        (ROOT / p).is_file() and digest(ROOT / p) == meta['sha256']
        and (ROOT / p).stat().st_size == meta['bytes']
        for p, meta in initial['prior_raw_files'].items()), len(initial['prior_raw_files']))
    check('all nonliving tracked bytes preserved', all(
        (ROOT / p).is_file() and digest(ROOT / p) == meta['sha256']
        for p, meta in initial['tracked_files'].items() if p not in LIVING))
    for name in LIVING:
        check('archived living bytes: ' + name,
              digest(RAW / 'prior-checkpoint' / name) == initial['tracked_files'][name]['sha256'])

    for sealname in ['d1-02-evidence-manifest.json']:
        seal = read(ROOT / 'metadata/d1' / sealname)
        check('sealed raw bytes: ' + sealname, all(
            digest(ROOT / p) == meta['sha256'] and (ROOT / p).stat().st_size == meta['bytes']
            for p, meta in seal['raw_files'].items()), len(seal['raw_files']))
        for name, expected in seal['deliverable_sha256'].items():
            archived = RAW / 'prior-checkpoint' / name
            path = archived if name in LIVING else ROOT / name
            check('sealed deliverable: ' + name, digest(path) == expected)

    pins = read(OLD / 'pins.json')
    trees_by_repo = {}
    for pin in pins['families']:
        repo = pin['repo']
        folder = OLD / 'sources' / repo.replace('/', '--')
        commit = read(folder / 'commit.json')
        check('commit identity: ' + repo, commit['sha'] == pin['revision']
              and commit['commit']['tree']['sha'] == pin['tree'])
        trees = {d['sha']: d for p in (folder / 'trees').glob('*.json') for d in [read(p)]}
        check('all saved trees complete: ' + repo, all(not d.get('truncated') for d in trees.values()))
        # Independently recompute Git tree object IDs, including nested trees
        # present in recursive API responses. JSON formatting is not Git identity.
        for tree_sha, tree in trees.items():
            prefixes = {'': tree_sha}
            prefixes.update({e['path'] + '/': e['sha'] for e in tree['tree'] if e['type'] == 'tree'})
            for prefix, expected_sha in prefixes.items():
                children = [dict(e, path=e['path'][len(prefix):]) for e in tree['tree']
                            if e['path'].startswith(prefix)
                            and '/' not in e['path'][len(prefix):]]
                if not children and prefix:
                    continue  # Non-recursive response; separately saved children checked above.
                children.sort(key=lambda e: (e['path'] + ('/' if e['type'] == 'tree' else '')).encode())
                payload = b''.join((e['mode'].lstrip('0') + ' ' + e['path']).encode()
                                   + b'\0' + bytes.fromhex(e['sha']) for e in children)
                actual_sha = hashlib.sha1(b'tree ' + str(len(payload)).encode() + b'\0' + payload).hexdigest()
                check('Git tree object: ' + repo + ':' + tree_sha + ':' + prefix, actual_sha == expected_sha)
        reachable = {}
        seen = set()

        def walk(tree_sha, prefix=''):
            if (tree_sha, prefix) in seen or tree_sha not in trees:
                return
            seen.add((tree_sha, prefix))
            for e in trees[tree_sha]['tree']:
                name = prefix + e['path']
                if e['type'] == 'blob':
                    reachable[name] = e
                elif e['type'] == 'tree':
                    walk(e['sha'], name + '/')

        walk(pin['tree'])
        check('all saved trees reachable from pinned root: ' + repo,
              set(trees) <= {s for s, _ in seen})
        trees_by_repo[repo] = reachable

    sources = []
    for number in ['01', '02']:
        planpath = OLD / ('fetch-plan-' + number + '.json')
        log = read(OLD / ('fetch-log-' + number + '.json'))
        plan = read(planpath)
        check('fetch plan digest: ' + number, digest(planpath) == log['plan_sha256'])
        expected = {}
        for group in plan:
            for name in group['files']:
                url = f"https://raw.githubusercontent.com/{group['repo']}/{group['revision']}/{name}"
                expected[url] = (group, name)
        check('exact fetch URL set: ' + number,
              set(expected) == {r['url'] for r in log['requests']}
              and len(expected) == len(log['requests']))
        for rec in log['requests']:
            group, name = expected[rec['url']]
            source = ROOT / rec['path']
            expected_path = OLD / 'sources' / group['repo'].replace('/', '--') / 'files' / name
            check('source path: ' + rec['path'], source == expected_path)
            data = source.read_bytes()
            blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            tree_entry = trees_by_repo[group['repo']].get(name, {})
            pin = next(p for p in pins['families'] if p['repo'] == group['repo'])
            check('source bytes and provenance: ' + rec['path'],
                  rec['status'] == 'FETCHED' and rec['http_status'] == 200
                  and rec['final_url'] == rec['url'] and group['revision'] == pin['revision']
                  and digest(source) == rec['sha256']
                  and len(data) == rec['bytes'] == tree_entry.get('size')
                  and blob == rec['git_blob_expected'] == rec['git_blob_actual'] == tree_entry.get('sha'))
            sources.append({'repo': group['repo'], 'revision': group['revision'],
                            'path': name, 'local_path': rec['path'], 'url': rec['url'],
                            'sha256': digest(source), 'git_blob': blob, 'bytes': len(data)})

    for rec in read(OLD / 'api-log.json'):
        path = ROOT / rec['out']
        if 'sha256' in rec:
            check('saved API bytes: ' + rec['out'], digest(path) == rec['sha256'])
        else:
            # These inherited files add a local prefix and pretty-print the
            # response. Keep the failed literal-byte audit, and check a clearly
            # labeled reconstruction rather than calling these original bytes.
            document = read(path)
            prefix = document.pop('bindcheck_prefix')
            reconstructed = json.dumps(document, separators=(',', ':'), ensure_ascii=False).encode()
            check('reconstructed API digest: ' + rec['out'],
                  hashlib.sha256(reconstructed).hexdigest() == rec['response_sha256'],
                  {'saved_sha256': digest(path), 'response_sha256': rec['response_sha256'],
                   'removed_local_prefix': prefix,
                   'transformation': 'remove bindcheck_prefix; compact JSON; UTF-8; no newline'})

    recovery = RAW / 'recovery.json'
    if recovery.exists():
        for rec in read(recovery)['records']:
            check('recovered exact copy: ' + rec['destination'],
                  digest(ROOT / rec['destination']) == digest(ROOT / rec['archive']) == rec['sha256'])
        restored_protocol = ROOT / 'protocols/d1/d1-02-continuation-01.json'
        check('recovered continuation freeze identity', digest(restored_protocol) == pins['protocol_sha256'])
        intake = read(ROOT / 'metadata/d1/d1-02-continuation-01-intake.json')
        for name, expected in intake['evidence_sha256'].items():
            check('recovered intake evidence: ' + name, digest(ROOT / name) == expected)
        freeze = (ROOT / 'results/raw/D1-03/freeze/00_protocol_freeze.txt').read_text()
        for name in ['protocols/d1/d1-03-joint-semantics.md', 'protocols/d1/d1-03-joint-semantics.json']:
            check('recovered D1-03 freeze identity: ' + name, digest(ROOT / name) + '  ' + name in freeze)

    commands = []
    for argv in [['git', 'rev-parse', 'HEAD'], ['git', 'rev-parse', '--git-path', 'index'],
                 ['git', 'diff', '--check'], ['git', 'diff', '--cached', '--quiet']]:
        p = subprocess.run(argv, cwd=ROOT, env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'},
                           capture_output=True, text=True)
        commands.append({'argv': argv, 'exit': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr})
    check('HEAD preserved', commands[0]['exit'] == 0
          and commands[0]['stdout'] == initial['head']['stdout'])
    index = Path(commands[1]['stdout'].strip())
    if not index.is_absolute():
        index = ROOT / index
    check('index preserved', digest(index) == initial['index_sha256'])
    check('tracked whitespace check', commands[2]['exit'] == 0, commands[2])
    check('no staged changes', commands[3]['exit'] == 0)
    missing = [p for p in ['protocols/d1/d1-02-continuation-01.json',
                           'metadata/d1/d1-02-continuation-01-intake.json',
                           'scripts/d1_02c_fetch.py', 'protocols/d1/d1-03-joint-semantics.md',
                           'protocols/d1/d1-03-joint-semantics.json', 'reports/D1-03.md']
               if not (ROOT / p).exists()]
    result = {'task': 'D1-02 reconciliation-01', 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'argv': [sys.executable, '-I', *sys.argv], 'cwd': str(ROOT), 'python': sys.version,
              'script_sha256': digest(Path(__file__)), 'protocol_sha256': digest(protocol),
              'audit_status': 'PASS' if all(c['passed'] for c in checks) else 'FAIL',
              'research_verdict': 'UNKNOWN', 'checks': checks, 'sources': sources,
              'commands': commands, 'missing_artifacts': missing,
              'historical_protocol_digest_unverifiable': pins['protocol_sha256'],
              'limits': 'Offline consistency audit only; historical freeze, runtime success, semantic fidelity and safety are not established.'}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'audit_status': result['audit_status'], 'checks': len(checks),
                      'failed': [c for c in checks if not c['passed']], 'sources': len(sources),
                      'missing_artifacts': missing}))
    return 0 if result['audit_status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
