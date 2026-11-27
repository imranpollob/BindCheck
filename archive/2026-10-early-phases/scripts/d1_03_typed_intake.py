#!/usr/bin/env python3
"""One pinned source archive, strict download/expanded caps, no install."""
import datetime
import hashlib
import json
from pathlib import Path
import tarfile
import time
import urllib.request

REV = '60ccd48e18ad8ce50d5ecda9baf813b712145051'
URL = 'https://codeload.github.com/noir-lang/noir/tar.gz/' + REV
RAW = Path('results/raw/D1-03/typed-bindings-01')
DEST = Path('build/D1-03/noir-source-' + REV)


def main():
    start = time.monotonic()
    record = {'url': URL, 'revision': REV, 'started_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'byte_cap': 64*1024**2, 'wall_cap_seconds': 120}
    with (RAW/'intake-started.json').open('x') as f:
        json.dump(record, f)
    archive = RAW/'noir-source.tar.gz'
    try:
        request = urllib.request.Request(URL, headers={'User-Agent':'BindCheck-pinned-source-intake'})
        with urllib.request.urlopen(request, timeout=120) as response, archive.open('xb') as out:
            record.update(status=response.status, resolved_url=response.url, headers=dict(response.headers))
            size = 0
            while True:
                block = response.read(65536)
                if not block:
                    break
                size += len(block)
                if size > record['byte_cap'] or time.monotonic()-start > 120:
                    raise RuntimeError('approved download cap reached')
                out.write(block)
        record.update(bytes=size, sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
        DEST.mkdir(exist_ok=False)
        total = 0
        with tarfile.open(archive, 'r:gz') as tf:
            for member in tf:
                if not member.isfile():
                    continue
                path = Path(member.name)
                if path.is_absolute() or '..' in path.parts or path.parts[0] != 'noir-'+REV:
                    raise RuntimeError('unsafe archive path')
                total += member.size
                if total > 512*1024**2:
                    raise RuntimeError('expanded archive cap reached')
                dest = DEST/Path(*path.parts[1:])
                dest.parent.mkdir(parents=True, exist_ok=True)
                with tf.extractfile(member) as source, dest.open('xb') as out:
                    out.write(source.read())
        record.update(expanded_regular_bytes=total, destination=str(DEST), exit=0)
    except Exception as error:
        record.update(exit=1, error=repr(error))
        raise
    finally:
        record['elapsed_seconds'] = time.monotonic()-start
        (RAW/'intake.json').write_text(json.dumps(record, indent=2)+'\n')
        print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
