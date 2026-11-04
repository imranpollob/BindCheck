from __future__ import annotations

import hashlib
import pathlib


def freeze_manifest(root: pathlib.Path) -> tuple[str, list[tuple[str, str]]]:
    paths = [root / "bindcheck-zk", root / "requirements-bindcheck-zk.txt"]
    paths.extend(sorted((root / "bindcheck_zk").glob("*.py")))
    paths.append(root / "bindcheck_zk" / "config.json")
    entries: list[tuple[str, str]] = []
    for path in paths:
        if path.is_file():
            entries.append((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    payload = "".join(f"{digest}  {name}\n" for name, digest in entries).encode()
    return hashlib.sha256(payload).hexdigest(), entries


def main() -> int:
    root = pathlib.Path(__file__).resolve().parents[1]
    digest, entries = freeze_manifest(root)
    for name, item_digest in entries:
        print(f"{item_digest}  {name}")
    print(f"BINDCHECK_ZK_CONTENT_SHA256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
