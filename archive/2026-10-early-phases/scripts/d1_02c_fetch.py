#!/usr/bin/env python3
"""Fetch listed pinned source files for D1-02 continuation 01; never execute them.

Separately versioned from d1_02_fetch.py (frozen).  Each plan group names a
saved Git tree listing (recursive or per-directory, already pinned to the
protocol revision) that is the allowlist and supplies the expected Git blob
ID.  Each invocation requires new output files; failed requests are data.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/raw/D1-02/continuation-01/sources'
MAX_FILES, MAX_BYTES = 60, 1500000


def load_tree(dest):
    entries = {}
    for t in sorted((dest / 'trees').glob('*.json')):
        d = json.loads(t.read_text())
        prefix = d.get('bindcheck_prefix', '')
        for e in d['tree']:
            entries[prefix + e['path']] = e
    return entries


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--log', type=Path, required=True)
    args = ap.parse_args()
    plan = json.loads(args.plan.read_text())
    if args.log.exists():
        ap.error('Refusing to overwrite request log')
    jobs = []
    for group in plan:
        dest = BASE / group['repo'].replace('/', '--')
        tree = load_tree(dest)
        already = sum(1 for p in (dest / 'files').rglob('*') if p.is_file()) if (dest / 'files').exists() else 0
        assert already + len(group['files']) <= MAX_FILES
        for name in group['files']:
            entry = tree[name]
            assert entry['type'] == 'blob' and entry['size'] <= MAX_BYTES
            p = dest / 'files' / name
            assert p.resolve().is_relative_to((dest / 'files').resolve()) and not p.exists()
            jobs.append((group, name, entry, p))

    def fetch(job):
        group, name, entry, p = job
        url = f"https://raw.githubusercontent.com/{group['repo']}/{group['revision']}/{name}"
        rec = {'url': url, 'path': str(p.relative_to(ROOT)), 'git_blob_expected': entry['sha'],
               'requested_at_utc': datetime.now(timezone.utc).isoformat()}
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'BindCheck-D1-02c-availability-intake'})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read(MAX_BYTES + 1)
                rec.update(http_status=r.status, final_url=r.url)
            assert len(data) == entry['size'] <= MAX_BYTES
            blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            assert blob == entry['sha']
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open('xb') as f:
                f.write(data)
            rec.update(status='FETCHED', bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), git_blob_actual=blob)
        except Exception as exc:
            rec.update(status='UNAVAILABLE', error=type(exc).__name__ + ': ' + str(exc))
        return rec

    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(fetch, jobs))
    with args.log.open('x') as f:
        json.dump({'plan': str(args.plan), 'plan_sha256': hashlib.sha256(args.plan.read_bytes()).hexdigest(),
                   'requests': records}, f, indent=2)
        f.write('\n')
    print(json.dumps({'requested': len(records), 'fetched': sum(r['status'] == 'FETCHED' for r in records),
                      'unavailable': [r['url'] for r in records if r['status'] != 'FETCHED']}))
    return 0 if all(r['status'] == 'FETCHED' for r in records) else 1


if __name__ == '__main__':
    raise SystemExit(main())
