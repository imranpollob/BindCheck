#!/usr/bin/env python3
"""D1-01 evidence audit and bounded replay; never changes historical artifacts.

prepare freezes inputs and query bytes without running a solver. run permits one
attempt for each frozen missing slot. collect writes a new six-slot matrix.
All outputs are exclusive-create, including attempt markers, to prevent reruns.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import shlex
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'results/raw/D1-01'
BACK = ROOT / 'results/raw/D1-00/baseline-results/T22'
OLD = BACK / '35_v5_compact'
ART = BACK / '33_v3_primary/20_payy_eval.json.artifacts'
SOLVER = ROOT / 'tools/cvc5-1.4.2-gpl/bin/cvc5'
SOURCE = Path('/home/pollmix/Coding/BindCheck')
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0', PYTHONDONTWRITEBYTECODE='1')
QUERIES = ('nonvacuous', 'prefix', 'tail')
CASES = {'check_added': 'b_agg_agg_check_added_',
         'running_flag': 'm4_b_different_idiom_flag_'}
CAP = 4 * 1024**3


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def write(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x') as f:
        json.dump(obj, f, indent=2)
        f.write('\n')


def relative(p):
    return str(Path(p).relative_to(ROOT))


def command(argv):
    r = subprocess.run([str(a) for a in argv], cwd=ROOT, env=ENV,
                       capture_output=True, text=True, timeout=60)
    rec = {'argv': [str(a) for a in argv], 'cwd': str(ROOT),
           'exit_status': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}
    if r.returncode:
        raise RuntimeError(rec)
    return rec


def load(p):
    return json.loads(Path(p).read_text())


def prepare():
    started = time.monotonic()
    if sys.flags.optimize or not __debug__:
        raise RuntimeError('Assertions must be enabled')
    sys.path.insert(0, str(ROOT / 'scripts'))
    import t22_v5_compact as C
    T = C.T
    checks = []
    frozen = {}
    for line in (OLD / '00_freeze_sha256.txt').read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        p = (ROOT / 'results/raw/D1-00/baseline-results' / name.removeprefix('results/raw/')) if name.startswith('results/raw/') else (SOURCE / name if name.startswith('tools/') else ROOT / name)
        actual = sha(p)
        checks.append({'frozen_path': name, 'resolved_path': str(p),
                       'expected': expected, 'actual': actual, 'pass': actual == expected})
        frozen[str(p)] = actual
    write(RAW / 'freeze-audit.json', checks)
    if not all(c['pass'] for c in checks):
        raise RuntimeError('Frozen input mismatch')

    # Saved evidence search: paths plus all JSON objects, excluding v2/v3/v4
    # candidates from the v5 primary set. Keep diagnostics visible separately.
    search = []
    for base in (ROOT / 'results/raw/D1-00/baseline-results', SOURCE / 'results/raw'):
        paths = sorted(p for p in base.rglob('*') if p.is_file() and '35_v5_compact' in str(p))
        search.append({'root': str(base), 'files': [str(p) for p in paths],
                       'running_flag_path_hits': [str(p) for p in paths if 'flag' in str(p)],
                       'json': [{'path': str(p), 'sha256': sha(p), 'top_keys': sorted(load(p))}
                                for p in paths if p.suffix == '.json']})
    write(RAW / 'evidence-search.json', search)

    count = C.self_check()
    write(RAW / 'self-check.json', {'assertions_enabled': __debug__, 'category_vectors': count,
          'status': 'pass', 'scope': 'Specification rewrite only; no ACIR summary established'})

    # An encoding-only sink replaces solve, retaining the frozen FF header and
    # footer serialization. No cvc5 process or synthetic solver record is saved.
    def capture(ff, values, path=None):
        header = ['(set-logic QF_FF)', '(set-option :produce-models true)',
                  f'(define-sort F () (_ FiniteField {T.P}))']
        script = '\n'.join(header + ff.lines + ['(check-sat)', '(get-value (' + ' '.join(values) + '))']) + '\n'
        with Path(path).open('x') as f:
            f.write(script)
        ff.solver_record = {'execution': 'NOT_EXECUTED_ENCODING_ONLY'}
        return 'not_executed', '', 0
    T.FF.solve = capture
    generated = []
    for case, name in CASES.items():
        a = T.Acir((ART / (name + '.compile.stdout')).read_text())
        abi = load(ART / (name + '.abi.json'))
        messages, streams = T.build(load(ROOT / 'scripts/t22_specs/payy_agg_agg.json'), a, abi.get('abi', abi))
        assert len(messages) == 8 and len(streams) == 2
        out = RAW / 'generated' / case
        out.mkdir(parents=True)
        for q in QUERIES:
            d = C.run_one(a, messages, streams, q, out, 300, True)
            row = {k: d[k] for k in ('query', 'acir_encoded', 'selected_acir_opcodes',
                                     'selected_witnesses', 'unmodeled_blackboxes', 'smt_sha256')}
            row.update(case=case, query_path=relative(out / (q + '.smt2')), execution='NOT_EXECUTED')
            if case == 'check_added':
                p = OLD / 'primary_check_added' / (q + '.json')
                old = load(p)
                sr = load(p.with_name(q + '.smt2.solver.json'))
                assert old['solver_record'] == sr
                assert old['smt_sha256'] == sha(p.with_name(q + '.smt2')) == d['smt_sha256']
                for key in ('selected_acir_opcodes', 'selected_witnesses', 'unmodeled_blackboxes', 'acir_encoded'):
                    assert old[key] == d[key]
                assert old['query'] == q and old['status'] == 'unknown'
                assert sr['timed_out'] is True and sr['exit_status'] == -9
                assert sr['command'][1:] == ['--lang=smt2', '--ff-solver=split']
                assert sr['command'][0] == str(SOURCE / 'tools/cvc5-1.4.2-gpl/bin/cvc5')
                assert 300 <= old['seconds'] < 305
                row['historical_record_valid_for_closure'] = True
                row['validation_limit'] = 'Byte regeneration by the same encoder; historical AS cap inferred from frozen driver, not independently measured'
            generated.append(row)
    write(RAW / 'generation-audit.json', generated)

    audit = command([sys.executable, '-I', ROOT / 'scripts/t22_v5_audit.py',
        '--source', OLD / 'primary_check_added/nonvacuous.smt2',
        '--primary', OLD / 'primary_check_added/nonvacuous.json',
        '--reduced', OLD / 'reductions/prefix_320_confirmed.smt2',
        '--acir', ART / 'b_agg_agg_check_added_.compile.stdout',
        '--abi', ART / 'b_agg_agg_check_added_.abi.json',
        '--spec', ROOT / 'scripts/t22_specs/payy_agg_agg.json',
        '--output', RAW / 'blocker-audit.json'])
    write(RAW / 'blocker-audit-command.json', audit)

    finish_prepare(frozen, generated, started, resume=False)


def finish_prepare(frozen, generated, started, resume):
    # Independent local copies; no runtime resolution into the mutable source.
    origin = SOURCE / 'tools/cvc5-1.4.2-gpl'
    dest = SOLVER.parent.parent
    if not resume:
        dest.mkdir(parents=True, exist_ok=False)
        shutil.copytree(origin / 'bin', dest / 'bin', symlinks=True)
        shutil.copytree(origin / 'lib', dest / 'lib', symlinks=True)
    assert sha(SOLVER) == '2406449e9b2e01c1243b838a6c3eba776db38624b56fa6911566fafabb86732f'
    assert sha(dest / 'lib/libcvc5.so.1.4.2') == 'e617fc072f5dca76a332f18067d0f4c4494562e6855da285cb16a72d5ccddf27'
    assert sha(dest / 'lib/libcvc5parser.so.1.4.2') == '6a47508d986de52c5fee3ee81bdd749f8ce264981ed489160fd73c9110dc098d'
    version = command([SOLVER, '--version'])
    linkage = command(['ldd', SOLVER])
    assert 'not found' not in linkage['stdout']
    # Also inspect transitive bindings from ldd, and pin all resolved libraries.
    runtime = {}
    for line in linkage['stdout'].splitlines():
        for word in line.split():
            if word.startswith('/') and Path(word).is_file():
                assert not Path(word).resolve().is_relative_to(SOURCE)
                runtime[word] = sha(word)
    commands = [version, linkage, command(['git', '--version'])]
    write(RAW / 'dependency-commands.json', commands)
    for p in dest.rglob('*'):
        if p.is_file():
            source_file = origin / p.relative_to(dest)
            assert sha(p) == sha(source_file) and not os.path.samefile(p, source_file)
            frozen[str(p)] = sha(p)
    for p in [Path(__file__), ROOT / 'scripts/t22_v3_tailspec.py', ROOT / 'scripts/t22_v5_compact.py',
              ROOT / 'scripts/t22_v5_audit.py', ROOT / 'scripts/t22_v5_reduce.py', ROOT / 'scripts/t22_v5_protocol.md',
              ROOT / 'scripts/t22_specs/payy_agg_agg.json', RAW / 'initial-state.json']:
        frozen[str(p)] = sha(p)
    for name in CASES.values():
        for suffix in ('.source.nr', '.compile.stdout', '.compile.stderr', '.abi.json'):
            p = ART / (name + suffix)
            frozen[str(p)] = sha(p)
    for r in generated:
        p = ROOT / r['query_path']
        frozen[str(p)] = sha(p)
    attempts = [{'slot': f'running_flag/{q}', 'query_path': relative(RAW / 'generated/running_flag' / (q + '.smt2')),
                 'solver_argv': [str(SOLVER), '--lang=smt2', '--ff-solver=split'],
                 'stdin': 'Exact bytes of query_path', 'seconds': 300, 'rlimit_as_bytes': CAP,
                 'timeout_action': 'SIGKILL entire new process group'} for q in QUERIES]
    elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(load(RAW / 'initial-state.json')['captured_at_utc'])).total_seconds()
    assert elapsed < 3600
    write(ROOT / 'metadata/d1/d1-01-execution-manifest.json', {
        'task': 'D1-01', 'frozen_at_utc': now(), 'repository_head': command(['git', 'rev-parse', 'HEAD'])['stdout'].strip(),
        'scope': 'Reporting closure; original v5 protocol preserved; no tuning or new reductions',
        'python': sys.version, 'platform': platform.platform(), 'assertions_enabled': __debug__,
        'setup_elapsed_seconds': elapsed, 'setup_limit_seconds': 3600,
        'new_attempt_limit_per_slot': 1, 'maximum_new_primary_attempts': 6,
        'maximum_primary_solver_budget_seconds': 1800, 'planned_primary_solver_budget_seconds': 900,
        'limits': {'N': 8, 'seconds_per_query': 300, 'rlimit_as_bytes': CAP, 'ff_solver': 'split'},
        'solver_version_command': version, 'runtime_library_sha256': runtime,
        'frozen_file_sha256': frozen, 'planned_attempts': attempts,
        'skipped_valid_slots': ['check_added/' + q for q in QUERIES],
        'historical_provenance': {'payy_B_revision': 'dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36',
            'nargo': '1.0.0-beta.14', 'noirc': '60ccd48e18ad8ce50d5ecda9baf813b712145051',
            'source': 'reports/T22-v3.md and saved 33_v3_primary/10_run_manifest.txt; no recompilation',
            'cvc5_revision': '282d5e0c84baf49c780704c532f87ba66d8b513d'}})
    print('prepare PASS: 8 freeze entries, 65536 vectors, 3 regenerated historical queries, 3 missing slots frozen')


def resume_prepare():
    # Resume after the recorded dependency path-check failure without rewriting
    # any audit output or copying over the already provisioned dependencies.
    if sys.flags.optimize or not __debug__:
        raise RuntimeError('Assertions must be enabled')
    checks = load(RAW / 'freeze-audit.json')
    assert all(c['pass'] and sha(c['resolved_path']) == c['expected'] for c in checks)
    assert load(RAW / 'self-check.json')['category_vectors'] == 65536
    assert load(RAW / 'blocker-audit-command.json')['exit_status'] == 0
    generated = load(RAW / 'generation-audit.json')
    assert all(sha(ROOT / g['query_path']) == g['smt_sha256'] for g in generated)
    finish_prepare({c['resolved_path']: c['actual'] for c in checks}, generated, time.monotonic(), resume=True)


def run(q):
    manifest_path = ROOT / 'metadata/d1/d1-01-execution-manifest.json'
    m = load(manifest_path)
    for p, expected in {**m['frozen_file_sha256'], **m['runtime_library_sha256']}.items():
        if sha(p) != expected:
            raise RuntimeError('Frozen file mismatch: ' + p)
    a = next(a for a in m['planned_attempts'] if a['slot'] == 'running_flag/' + q)
    out = RAW / 'primary_running_flag'
    out.mkdir(exist_ok=True)
    # Marker is written before spawn; even a failed spawn consumes this slot.
    write(out / (q + '.attempt.json'), {'started_at_utc': now(), 'manifest_sha256': sha(manifest_path), 'attempt': a})
    script = (ROOT / a['query_path']).read_bytes()
    started = time.monotonic()
    def limit():
        resource.setrlimit(resource.RLIMIT_AS, (CAP, CAP))
    p = subprocess.Popen(a['solver_argv'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, start_new_session=True, preexec_fn=limit, env=ENV, cwd=ROOT)
    limits = Path(f'/proc/{p.pid}/limits').read_text()
    with (out / (q + '.limits.txt')).open('x') as f:
        f.write(limits)
    timed_out = False
    try:
        stdout, stderr = p.communicate(script, timeout=300)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(p.pid, signal.SIGKILL)
        stdout, stderr = p.communicate()
    elapsed = time.monotonic() - started
    for suffix, b in [('stdout.txt', stdout), ('stderr.txt', stderr)]:
        with (out / (q + '.' + suffix)).open('xb') as f:
            f.write(b)
    first = stdout.decode(errors='replace').splitlines()
    observation = first[0].strip() if first and first[0].strip() in ('sat', 'unsat', 'unknown') else 'unknown'
    write(out / (q + '.json'), {'query': q, 'case': 'running_flag', 'finished_at_utc': now(),
        'command': a['solver_argv'], 'cwd': str(ROOT), 'stdin_path': a['query_path'],
        'smt_sha256': hashlib.sha256(script).hexdigest(), 'seconds': elapsed,
        'time_limit_seconds': 300, 'memory_limit_bytes': CAP, 'process_group': p.pid,
        'exit_status': p.returncode, 'timed_out': timed_out,
        'stdout': stdout.decode(errors='replace'), 'stderr': stderr.decode(errors='replace'),
        'solver_observation': observation, 'verdict': 'UNKNOWN',
        'reason': 'TIMEOUT' if timed_out else 'SOLVER_OBSERVATION_REQUIRES_ADJUDICATION',
        'manifest_sha256': sha(manifest_path), 'proc_limits_path': relative(out / (q + '.limits.txt'))})
    print(f'running_flag/{q}: {observation}, exit={p.returncode}, timeout={timed_out}, {elapsed:.3f}s', flush=True)


def collect():
    m = load(ROOT / 'metadata/d1/d1-01-execution-manifest.json')
    gen = load(RAW / 'generation-audit.json')
    rows = []
    assumptions = ['Analyst stream roles and walk policy', 'Omitted ACIR components assumed satisfiable',
                   'Recursive proof feasibility unvalidated', 'Printed ACIR parser/cone/encoding correctness unproved',
                   'No consumer decoding, reachable history, proof or committed-effect replay in D1-01']
    for case in CASES:
        for q in QUERIES:
            g = next(g for g in gen if g['case'] == case and g['query'] == q)
            p = (OLD / 'primary_check_added' if case == 'check_added' else RAW / 'primary_running_flag') / (q + '.json')
            d = load(p) if p.exists() else None
            sr = d['solver_record'] if d and case == 'check_added' else d
            rows.append({'slot': case + '/' + q, 'case': case, 'obligation': q,
                'availability': 'PRESERVED_RECORD' if case == 'check_added' else 'NEW_EXECUTION' if d else 'UNAVAILABLE',
                'evidence_path': relative(p) if d else None, 'evidence_sha256': sha(p) if d else None,
                'query_path': relative(OLD / 'primary_check_added' / (q + '.smt2')) if case == 'check_added' else g['query_path'],
                'query_sha256': g['smt_sha256'], 'command': sr['command'] if sr else None,
                'stdin': 'Exact query bytes; solver command reads stdin',
                'driver_command': None, 'driver_command_note': 'Historical launch command was not archived; not reconstructed as an observed command' if case == 'check_added' else 'See frozen manifest and report for wrapper command',
                'solver_version': m['solver_version_command']['stdout'].splitlines()[0], 'solver_sha256': sha(SOLVER),
                'resource_limits': m['limits'], 'resource_evidence': 'Frozen historical main() RLIMIT_AS and seconds in saved record; no per-process limits/RSS saved' if case == 'check_added' else (d['proc_limits_path'] if d else None),
                'exit_status': sr['exit_status'] if sr else None, 'timed_out': sr['timed_out'] if sr else None,
                'elapsed_seconds': d['seconds'] if d else None, 'stdout': sr['stdout'] if sr else None,
                'stderr': sr['stderr'] if sr else None, 'peak_rss_kib': None,
                'solver_observation': d.get('status', d.get('solver_observation')) if d else None,
                'verdict': 'UNKNOWN', 'reason_codes': ['TIMEOUT'] if sr and sr['timed_out'] else ['UNRESOLVED_OR_UNAVAILABLE'],
                'evidence_grade': 'Producer-side solver observation; no decisive semantic result',
                'bounds': {'N': 8, 'streams': 2, 'selected_acir_opcodes': g['selected_acir_opcodes'], 'selected_witnesses': g['selected_witnesses']},
                'nonvacuity': 'UNRESOLVED', 'assumptions': assumptions,
                'unresolved_checks': ['Full extraction/encoding soundness', 'Nonvacuity', 'Concrete proof feasibility and consumer effects'],
                'artifact_provenance': 'metadata/d1/d1-01-execution-manifest.json'})
    write(ROOT / 'metadata/d1/d1-01-query-matrix.json', {'task': 'D1-01', 'created_at_utc': now(),
        'closure_status': 'DONE', 'original_six_primary_execution_records_available': sum(r['availability'] != 'UNAVAILABLE' for r in rows),
        'original_decisive_milestone': 'UNMET', 'research_verdict': 'UNKNOWN', 'rows': rows,
        'diagnostics_excluded_from_primary': ['exploratory_spec_only', 'exploratory_full_check_added', 'reductions', 'self-check', 'generation-audit']})
    print('collected six slots: ' + ', '.join(r['slot'] + '=' + r['verdict'] for r in rows))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action', choices=('prepare', 'resume-prepare', 'run', 'collect'))
    ap.add_argument('--query', choices=QUERIES)
    args = ap.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'resume-prepare':
        resume_prepare()
    elif args.action == 'run':
        if not args.query:
            ap.error('run requires --query')
        run(args.query)
    else:
        collect()
