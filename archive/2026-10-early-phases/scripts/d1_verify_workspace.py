#!/usr/bin/env python3
"""Read-only D1-00 preservation audit. Emits JSON; never restores or stages files."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
BASE = json.loads((ROOT / 'metadata/d1/baseline.json').read_text())
SOURCE = Path(BASE['source_root'])
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
checks = []
commands = []


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def git(root, *args):
    proc = subprocess.run(['git', *args], cwd=root, env=ENV, capture_output=True)
    commands.append({'argv': ['git', *args], 'cwd': str(root),
                     'exit_status': proc.returncode,
                     'stdout': proc.stdout.decode(errors='replace') if args[-1] == '--check' else None,
                     'stderr': proc.stderr.decode(errors='replace')})
    if proc.returncode:
        raise RuntimeError(f'git {args}: {proc.stderr.decode(errors="replace")}')
    return proc.stdout


def record(name, passed, **details):
    checks.append({'check': name, 'passed': bool(passed), **details})


def entry(path):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        return {'kind': 'symlink', 'target': os.readlink(path), 'mode': stat.S_IMODE(info.st_mode)}
    if stat.S_ISREG(info.st_mode):
        return {'kind': 'file', 'bytes': info.st_size, 'sha256': sha(path), 'mode': stat.S_IMODE(info.st_mode)}
    return None


def inventory(root):
    result = {}
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d != '.git')
        for name in sorted(names + list(dirs)):
            if name == '.git':
                continue
            path = Path(base) / name
            item = entry(path)
            if item:
                result[str(path.relative_to(root))] = item
    return result


def compare(name, expected, actual):
    differences = [key for key in sorted(set(expected) | set(actual))
                   if expected.get(key) != actual.get(key)]
    record(name, not differences, expected_count=len(expected), actual_count=len(actual), differences=differences)


def main():
    full_path = ROOT / BASE['full_inventory']
    record('inventory_manifest_hash', sha(full_path) == BASE['source_inventory_sha256'])
    original = json.loads(full_path.read_text())
    compare('original_working_files_modes_and_symlinks', original, inventory(SOURCE))
    index_path = Path(git(SOURCE, 'rev-parse', '--git-path', 'index').decode().strip())
    if not index_path.is_absolute():
        index_path = SOURCE / index_path
    record('original_index_bytes', sha(index_path) == BASE['original_index_sha256'])
    for root, branch in [(SOURCE, BASE['original_branch']), (ROOT, BASE['branch'])]:
        record(f'{root.name}_head', git(root, 'rev-parse', 'HEAD').decode().strip() == BASE['base_head'])
        record(f'{root.name}_branch', git(root, 'branch', '--show-current').decode().strip() == branch)
        record(f'{root.name}_staged_patch', hashlib.sha256(git(root, 'diff', '--cached', '--binary')).hexdigest() == BASE['staged_patch_sha256'])
    record('original_unstaged_patch', hashlib.sha256(git(SOURCE, 'diff', '--binary')).hexdigest() == BASE['unstaged_patch_sha256'])
    record('original_status', git(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all').decode() == BASE['original_status'])
    for path_key, hash_key in [('staged_backup', 'staged_patch_sha256'), ('unstaged_backup', 'unstaged_patch_sha256'), ('index_backup', 'original_index_sha256')]:
        record(path_key, sha(ROOT / BASE[path_key]) == BASE[hash_key])
    raw = {name.removeprefix('results/raw/'): item for name, item in original.items() if name.startswith('results/raw/')}
    compare('independent_raw_backup', raw, inventory(ROOT / BASE['raw_backup']))
    alias_paths = []
    for name, item in raw.items():
        if item['kind'] == 'file':
            src = SOURCE / 'results/raw' / name
            dst = ROOT / BASE['raw_backup'] / name
            if os.path.samefile(src, dst):
                alias_paths.append(name)
    record('raw_regular_files_not_hardlinked', not alias_paths, aliases=alias_paths)
    allowed = {'README.md', 'AGENTS.md', 'docs/research-contract.md', 'docs/project-status.md'}
    changed = []
    tracked = git(SOURCE, 'ls-files', '-z').decode().split('\0')
    for name in filter(None, tracked):
        if name in allowed:
            continue
        before = original.get(name)
        path = ROOT / name
        after = entry(path) if path.exists() or path.is_symlink() else None
        # Git preserves executability, not all permission bits of working files.
        if before and after:
            before = dict(before, mode=before['mode'] & 0o111)
            after = dict(after, mode=after['mode'] & 0o111)
        if before != after:
            changed.append(name)
    record('inherited_code_reports_and_user_additions', not changed, changed=changed)
    old_status = (ROOT / 'results/raw/D1-00/source-snapshots/docs/project-status.md').read_text()
    new_status = (ROOT / 'docs/project-status.md').read_text()
    old_rows = [line for line in old_status.splitlines() if line.startswith('| 2026-')]
    new_rows = [line for line in new_status.splitlines() if line.startswith('| 2026-')]
    record('prior_checkpoint_rows_preserved_in_order', new_rows[:len(old_rows)] == old_rows, count=len(old_rows))
    done_nodes = re.findall(r'\b(\w+)\["([^"\n]*\[DONE\])"\]', old_status)
    record('completed_checkpoint_nodes_preserved', all(f'{node}["{label}"]' in new_status for node, label in done_nodes), count=len(done_nodes))
    record('historical_contract_exact', sha(ROOT / 'docs/history/research-contract-2026-10-20.md') == original['docs/research-contract.md']['sha256'])
    historical = json.loads((ROOT / 'metadata/d1/historical-evidence.json').read_text())['files']
    record('historical_manifest_matches_baseline', all(original.get(p) == info for p, info in historical.items()), count=len(historical))
    inputs = json.loads((ROOT / 'metadata/d1/literature-inputs.json').read_text())['files']
    failed_inputs = [item['copied_path'] for item in inputs if sha(ROOT / item['copied_path']) != item['sha256']]
    record('literature_snapshot_hashes', not failed_inputs, differences=failed_inputs)
    docs = [ROOT / p for p in ['README.md', 'docs/research-contract.md', 'docs/project-status.md', 'reports/D1-00.md']]
    docs += sorted((ROOT / 'docs/d1').glob('*.md'))
    missing = []
    for path in docs:
        for target in re.findall(r'!?\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)', path.read_text()):
            target = unquote(target.strip('<>').split('#', 1)[0])
            if not target or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target):
                continue
            if not (path.parent / target).exists():
                missing.append({'document': str(path.relative_to(ROOT)), 'target': target})
    record('local_markdown_link_targets', not missing, missing=missing, note='File existence only; anchors and external URLs not checked')
    record('new_unstaged_diff_whitespace', git(ROOT, 'diff', '--check') == b'')
    # Preserve rather than fix the user's two existing Markdown hard-break spaces.
    proc = subprocess.run(['git', 'diff', '--cached', '--check'], cwd=ROOT, env=ENV, capture_output=True)
    source_proc = subprocess.run(['git', 'diff', '--cached', '--check'], cwd=SOURCE, env=ENV, capture_output=True)
    commands.append({'argv': ['git', 'diff', '--cached', '--check'], 'cwd': str(ROOT), 'exit_status': proc.returncode, 'stdout': proc.stdout.decode(), 'stderr': proc.stderr.decode()})
    commands.append({'argv': ['git', 'diff', '--cached', '--check'], 'cwd': str(SOURCE), 'exit_status': source_proc.returncode, 'stdout': source_proc.stdout.decode(), 'stderr': source_proc.stderr.decode()})
    record('staged_whitespace_diagnostics_unchanged', (proc.returncode, proc.stdout, proc.stderr) == (source_proc.returncode, source_proc.stdout, source_proc.stderr), exit_status=proc.returncode, diagnostics=proc.stdout.decode())


try:
    main()
except Exception as exc:
    record('audit_execution', False, error=str(exc))
result = {'task': 'D1-00', 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
          'status': 'PASS' if all(c['passed'] for c in checks) else 'FAIL',
          'verifier_sha256': sha(Path(__file__)), 'python_version': sys.version,
          'git_version': subprocess.check_output(['git', '--version'], env=ENV).decode().strip(),
          'research_experiments_executed': 0, 'checks': checks, 'commands': commands}
print(json.dumps(result, indent=2))
sys.exit(0 if result['status'] == 'PASS' else 1)
