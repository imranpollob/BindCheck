# L1 soundness follow-up: exact guards and consumer context

## Objective and status

**Complete for this bounded development task.** This follow-up repairs the
reported P3 guard extraction, rejects guards against the wrong modulus,
resolves a restricted set of modifiers and base-contract effects, and closes
additional paths from missing artifacts to positive verdicts. The controlling
unhinted DEV run used analyzer revision
[`495ea93ac7521f97e618aba866cfc4ec681037cf`](../../results/raw/soundness/after-20261109T061325Z-77918/manifest.json)
and content hash
[`8ea6d2239cd94e2b4478bfae48fe8e764bf448a3b44c58224bbeeb6fa2f70542`](../../results/raw/soundness/verification-2.json).
These are **development outcomes, not evaluation or transfer results**.

The expected-outcome commits preceded their corresponding analyzer changes:
`52ef606`, `0f2cd82`, `c70cba7`, `8d6340a`, `adfa913`, `65a109f`,
`3a566b9`, `1772e43`, `2fda3a7`, and `5ee35c3` contain the new oracle or
corrected control expectations; `ba82dd0`, `ef0ec17`, `0f67ccd`, and
`495ea93` contain the implementation. The complete oracle is
[`test_followup.py`](../../tests/soundness/test_followup.py) with the preserved
[`18 prior cases`](../../tests/soundness/expected.json) and
[`122 existing controls`](../../tests/controls/expected.json).

## What changed

- [`p4.py`](../../bindcheck_zk/p4.py) now derives a word index from the exact
  `checkField(calldataload(add(_pubSignals, K)))` call only when its helper
  rejects values outside the exact BN254 scalar field in its rejecting branch.
  The call must occur on the recovered verifier path; the recognized wrapper
  copies each public input to the raw snarkjs verifier at the same index with
  no intervening vector mutation. The semicolon-spanning generic fallback is
  gone. Numeric guards against the base field or an unresolved name do not
  count. A key-only source or pairing-library helper cannot earn a P4 positive
  verdict.
- [`analyzer.py`](../../bindcheck_zk/analyzer.py) recognizes a prior,
  unconditional, whole-condition `require` on the exact replay key and scalar
  modulus. P1–P3 require matched circuit and verifier implementation artifacts;
  P5 rejects an interface-only verifier. Ambiguous base names fail closed.
- [`solidity.py`](../../bindcheck_zk/solidity.py) resolves a unique local base
  or exact OpenZeppelin import in a restricted subset, a local modifier with a
  single unconditional body placeholder and pure precondition prefix, and
  OpenZeppelin ERC20/ERC721 internal token effects. A missing/conditional
  placeholder, external-call modifier, or override stays `UNKNOWN`.
  [`verdict-rules.md`](../../docs/verdict-rules.md) records the updated scope.

## Verification and exact provenance

The [final verification record](../../results/raw/soundness/verification-2.json)
contains exact argv, cwd, stdout/stderr, elapsed time, tool hashes, versions,
and exit statuses. Its test command exited `0`: the existing
[`122 controls`](../../tests/controls/expected.json), preserved
[`18 soundness cases`](../../tests/soundness/expected.json), and all new
follow-up methods passed. `compileall`, `git diff --check`,
`git diff --cached --check`, and `./freeze.sh`
also [exited `0`](../../results/raw/soundness/verification-2.json).
The recorded environment is [Python 3.13.9, Circom 2.2.3, Git 2.51.0,
and snarkjs 0.7.6](../../results/raw/soundness/verification-2.json).
The snarkjs version probe printed its version and usage but
[exited `99`](../../results/raw/soundness/verification-2.json); it is a probe,
not a passing test. The new [`freeze.sh` content hash](../../results/raw/soundness/verification-2.json)
is `8ea6d2239cd94e2b4478bfae48fe8e764bf448a3b44c58224bbeeb6fa2f70542`.
No tag was created.

The full rerun command was:

```sh
BINDCHECK_CIRCOM=/Users/imranpollob/Coding/bc/bindcheck-zk/tools/circom-src/target/release/circom python3 scripts/run_bindcheck_zk_full_dev.py --phase after --skip-fetch --raw-task soundness --checkout-root /Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev --analyze-jobs 3
```

The [runner](../../scripts/run_bindcheck_zk_full_dev.py) reconstructed only
the permitted DEV population and validated the read-only pinned checkouts.
Its [manifest](../../results/raw/soundness/after-20261109T061325Z-77918/manifest.json)
contains each source revision, per-row command, exit status, output hash,
and checkout validation. The run completed [56 rows, 0 crashes, 46 rows with
triples, 45 successful builds and 31 failed build attempts](../../results/raw/soundness/after-20261109T061325Z-77918/per-row-ledger.json).
Build failures remain `UNKNOWN`, not wins. The [manifest SHA-256](../../results/raw/soundness/after-20261109T061325Z-77918/manifest.json)
is `21ecb42b7a45c0d37cac887b374377da038ace0caa2a6005f56a8769bd399db9`.
Earlier noncontrolling follow-up runs are preserved at
[`after-20261109T054204Z-46310`](../../results/raw/soundness/after-20261109T054204Z-46310/manifest.json),
[`after-20261109T054620Z-59155`](../../results/raw/soundness/after-20261109T054620Z-59155/manifest.json),
and [`after-20261109T060051Z-76053`](../../results/raw/soundness/after-20261109T060051Z-76053/manifest.json);
the final ledger below uses only the controlling run.

## Full DEV ledger

The [complete row-and-pattern ledger](full-dev-ledger-2.csv) compares the
prior [T27 after-run](../../results/raw/T27/after-20261109T030552Z-33270/per-row-ledger.json)
with the final [follow-up run](../../results/raw/soundness/after-20261109T061325Z-77918/per-row-ledger.json).
The [machine-readable summary](full-dev-summary-2.json) pins input hashes and
every transition. Counts below have the same [denominator of 56 DEV rows per
pattern](full-dev-summary-2.json):

| Pattern | `VIOLATION` | `VERIFIED_WITHIN_SCOPE` | `UNKNOWN` |
| --- | ---: | ---: | ---: |
| P1 | [5](full-dev-summary-2.json) | [0](full-dev-summary-2.json) | [51](full-dev-summary-2.json) |
| P2 | [0](full-dev-summary-2.json) | [0](full-dev-summary-2.json) | [56](full-dev-summary-2.json) |
| P3 | [6](full-dev-summary-2.json) | [7](full-dev-summary-2.json) | [43](full-dev-summary-2.json) |
| P4 | [0](full-dev-summary-2.json) | [17](full-dev-summary-2.json) | [39](full-dev-summary-2.json) |
| P5 | [0](full-dev-summary-2.json) | [4](full-dev-summary-2.json) | [52](full-dev-summary-2.json) |

Every changed verdict is listed here; the full before/after reasons and
applicability are in the [ledger](full-dev-ledger-2.csv):

| Row | Pattern | Previous → final | Reason for transition |
| --- | --- | --- | --- |
| [DEV-F08](full-dev-ledger-2.csv) | P4 | `VERIFIED` → `UNKNOWN` | A retained triple lacks a supported public-input canonicality guard; `VERIFICATION_KEY_CHECKS_PASS` alone no longer clears the row. |
| [DEV-F10](full-dev-ledger-2.csv) | P4 | `VERIFIED` → `UNKNOWN` | `PUBLIC_INPUT_CANONICALITY_GUARD_NOT_FOUND` after key-only/unguarded recognition is closed. |
| [DEV-F12](full-dev-ledger-2.csv) | P3 | `VIOLATION` → `VERIFIED` | Exact snarkjs `checkField` call covers the replay-key position. |
| [DEV-F14](full-dev-ledger-2.csv) | P1 | `UNKNOWN` → `VIOLATION` | Resolved inheritance exposes `UNBOUND_EFFECT_AMOUNT`. |
| [DEV-F14](full-dev-ledger-2.csv) | P3 | `VIOLATION` → `VERIFIED` | Exact snarkjs guard covers the replay-key position. |
| [DEV-F24](full-dev-ledger-2.csv) | P3 | `VIOLATION` → `VERIFIED` | Exact snarkjs guard covers the replay-key position. |
| [DEV-F29](full-dev-ledger-2.csv) | P3 | `VIOLATION` → `VERIFIED` | The wrapper passes the public inputs position for position to the guarded raw snarkjs verifier; the other retained triple says `REPLAY_KEY_NOT_RECOVERED` and is nonapplicable. |
| [DEV-F30](full-dev-ledger-2.csv) | P1 | `UNKNOWN` → `VIOLATION` | OpenZeppelin `nonReentrant` and inheritance resolve; the mint amount remains `UNBOUND_EFFECT_AMOUNT`. Other retained triples remain `PROTECTED_EFFECT_NOT_RECOVERED`. |
| [DEV-F32](full-dev-ledger-2.csv) | P4 | `VERIFIED` → `UNKNOWN` | `PUBLIC_INPUT_CANONICALITY_GUARD_NOT_FOUND` after the positive path requires an actual guarded verifier. |
| [DEV-F34](full-dev-ledger-2.csv) | P4 | `VERIFIED` → `UNKNOWN` | Its `checkField` helper compares against base field `q`, so a scalar guard is not recovered. |
| [DEV-F35](full-dev-ledger-2.csv) | P1 | `UNKNOWN` → `VIOLATION` | Local modifier resolution exposes `UNBOUND_EFFECT_AMOUNT`; this new E1 warning requires independent validation. |
| [DEV-F39](full-dev-ledger-2.csv) | P1 | `UNKNOWN` → `VIOLATION` | ERC721 inheritance and `_safeMint` resolve; caller-selected recipient is `UNBOUND_EFFECT_RECIPIENT`. |
| [DEV-F45](full-dev-ledger-2.csv) | P4 | `VERIFIED` → `UNKNOWN` | `PUBLIC_INPUT_CANONICALITY_GUARD_NOT_FOUND` after the positive path requires an actual guarded verifier. |
| [DEV-H02](full-dev-ledger-2.csv) | P3 | `VIOLATION` → `VERIFIED` | A prior unconditional `require` guards `nullifierHash` against the exact scalar field before insertion into `pubSignals[1]`. |
| [DEV-H03](full-dev-ledger-2.csv) | P3 | `VERIFIED` → `UNKNOWN` | `VERIFIER_ARTIFACT_MISSING`; P4 already reported the same missing artifact. |
| [DEV-H04](full-dev-ledger-2.csv) | P3 | `VERIFIED` → `UNKNOWN` | `VERIFIER_ARTIFACT_MISSING`; P4 already reported the same missing artifact. |

The [summary](full-dev-summary-2.json) also preserves reason-only changes
without relabeling their verdicts, including new missing-artifact reasons.

## Case adjudication and limits

Among the named alleged P3 false alarms, [DEV-F12, F14, F24, and F29](full-dev-ledger-2.csv)
are cleared. [DEV-F34 remains a P3 `VIOLATION`](../../results/raw/soundness/after-20261109T061325Z-77918/DEV-F34--result.json):
its [pinned verifier source](/Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev/DEV-F34--avitenzer__zk_voting--18d3a277ccd8/contracts/Verifier.sol)
labels `r` as scalar and `q` as base, and `checkField` uses `q`. The
[consumer source](/Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev/DEV-F34--avitenzer__zk_voting--18d3a277ccd8/contracts/VotingContract.sol)
uses `input[0]` as the nullifier mapping key. Clearing this row would violate
the requested exact-scalar-field rule. This is **source-confirmed E1** only;
proof feasibility and committed effects were not rerun. The remaining P3
violation rows are enumerated in the [raw ledger](../../results/raw/soundness/after-20261109T061325Z-77918/per-row-ledger.json);
their global false-alarm count is **UNKNOWN** without independent case review.

[DEV-H01 stays `VIOLATION / FIELD_ALIAS_REPLAY_KEY`](full-dev-ledger-2.csv).
[DEV-H02 is `VERIFIED_WITHIN_SCOPE / REPLAY_KEY_CANONICAL_AND_CONSUMED`](full-dev-ledger-2.csv)
for this narrow P3 property; its P4 remains `UNKNOWN` because its verifier
does not expose a supported scalar guard. [DEV-H03 and H04](full-dev-ledger-2.csv)
are `UNKNOWN / VERIFIER_ARTIFACT_MISSING` for P3. [DEV-F30 and F39](full-dev-ledger-2.csv)
are now P1 `VIOLATION` at E1 in this run. Their earlier owned-local, real-proof
E4 reproductions are separate [historical feasibility evidence](../../feasibility/v2/REPORT.md),
not new E4 validations here.

The OpenZeppelin summary is restricted to exact import paths and the named
standard internal effects; no full Solidity dispatch, proxy, arbitrary
modifier, external-call, or dependency equivalence proof was performed.
Duplicate base names, overrides, unsupported context, absent artifacts,
and build failures remain `UNKNOWN`. The P3 guard recognizer is source-level;
it does not prove compiler or key correspondence. No recall/EVAL row, held-out
repository, live network, maintainer, or disclosure channel was accessed.

## Recommended next bounded task

Independently adjudicate the remaining P3 DEV violation rows from their pinned
source and, where feasible, a local real-proof replay. Completion means each
row has a source-level explanation, an evidence grade, and either a validated
warning or a precommitted regression for any newly confirmed false alarm.
