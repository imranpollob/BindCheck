# Coverage analyzer freeze declaration — 2026-11-09

**Branch:** `zk-coverage`; no tag, push, or merge.

**New analyzer identity:**
`BINDCHECK_ZK_CONTENT_SHA256=a9ec7cb91a9a987ae9dc146142b5cf062114a1ec92551d05ab2eb05bf0e8f07b`
from [`./freeze.sh`](../results/raw/coverage/verification.json), exit status
`0`. The controlling unhinted development run is
[`results/raw/coverage/after-20261109T150206Z-10301/`](../results/raw/coverage/after-20261109T150206Z-10301/manifest.json).

**Reason for revision:** support restricted Pausable and local-lock modifiers,
exact imported ERC721Enumerable mint effects, exact scalar-guard coverage
through a position-preserving verifier wrapper, and fail-closed placeholder
rejection. The exact rules and controls are in
[`docs/verdict-rules.md`](verdict-rules.md) and
[`tests/coverage/test_rules.py`](../tests/coverage/test_rules.py).

**Affected results:** the prior
[`8ea6d2239cd94e2b4478bfae48fe8e764bf448a3b44c58224bbeeb6fa2f70542`](FREEZE-2026-11-09.md)
hash and its DEV decision counts do not describe this analyzer. They remain
immutable historical evidence. The complete per-row transition and count
change is in [`reports/coverage/REPORT.md`](../reports/coverage/REPORT.md) and
[`dev-ledger.csv`](../reports/coverage/dev-ledger.csv). Any later held-out run
must use a separately declared exact hash and must not pool this development
run with the previous hash as one analyzer version. This revision was driven
only by DEV and new synthetic controls; it conveys no held-out result.

**Validation:** the [verification record](../results/raw/coverage/verification.json)
shows the existing controls, soundness and follow-up suites, new coverage
controls, `compileall`, `git diff --check`, and `./freeze.sh` succeeded under
Python `3.15.0`. The declaration does not upgrade any E1 warning to E2–E4
or certify deployment correspondence.
