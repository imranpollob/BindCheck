# S2c — Extent binding beyond discharge

Status: DONE

Verdict/outcome: AZ1 faulty `VIOLATION` (E1), AZ1 fixed
`VERIFIED_WITHIN_SCOPE` (E1), and deployed-source V3 `UNKNOWN` (E0).

## What was done

Added `P1-EXTENT` in [extent.py](../../bindcheck_zk/extent.py) and hooked it
into [analyzer.py](../../bindcheck_zk/analyzer.py). It traces fixed calldata
arrays through a full-region hash to a verifier input, recovers a
zero-based effect loop over the same rows, and compares the loop's
caller-controlled bound with the committed length. It accepts a full-length
bound or a complete tail guard that makes every recognized effect condition
false. Other cases receive an `UNKNOWN` reason when extraction or the extent
comparison is unresolved.

`P1-EXTENT` has its own summary in `patterns` and per-consumer diagnostics
in `extent_findings`. This keeps the existing P1 authorization result and
triple aggregate stable. Extent is about coverage of committed rows, and its
source diagnostic can exist even when the older triple frontend recovers no
applicable triple. The rule contains no target names or expected labels.
[Research contract §§4 and 8](../../docs/research-contract.md)

Added 12 [S2c tests](../../tests/s2c/test_extent.py), including the unchanged
AZ1 pair, independently written equality and opaque-bound controls, a
fixed-length bound, a local bound copy and interface call, proof-bound
signals, a compound guard, a partial tail guard, and an assignment to the
bound. The final candidate was evaluated on the original 56 DEV rows only.
The [project checkpoint](../../docs/project-status.md) records this task.

AI disclosure: OpenAI Codex, GPT-6, executed this task. The developer identifies
the model family as GPT-6. The specific serving variant was unavailable.
Human author review of the implementation and claims is pending.

## Evidence (paths, hashes, commands, exit codes, tool versions)

- Worktree `$BC/wt-S2c`, branch `sprint/S2c`, base revision
  `c82eac653fd53daf71dc0eb013849f3be42dd1ba`. Baseline analyzer hash
  `8ef7a837f4127bfa57fa44419a39b37eee06b90929ed074e5009bc714c346be3`,
  checked from an isolated `git archive HEAD` package with the same local
  dependencies and executable.
- Candidate `BINDCHECK_ZK_CONTENT_SHA256=532ec6b2a428e60909f21cef78a0a9c660e32bfd4b011d4a6419ebba452ba315`.
  `python3 -m bindcheck_zk.freeze` exited 0. See
  `results/raw/S2c/candidate-hash-final.txt` for the per-file manifest.
- Versions: Python 3.12.12, Git 2.43.0, Node.js v24.19.0 and Circom 2.1.9.
  Circom SHA-256
  `1bacd5583e2cc79dc1e2deaefc9c7438f21957968651c5f93dc71073c58435e3`.
  The worktree already had the lock-matching circomlib 2.0.5 tree.
- Tests: the six Freeze-2 modules, S2a, and S2c passed 70/70, exit 0.
  Evidence: `results/raw/S2c/full-suite-final.log` and
  `results/raw/S2c/full-suite-final.exit`.
- Source SHA-256 values:
  `SettlementFaulty.sol` `7c1b34aa6ff8e4479729398ef5aeba12e4bef9ccb151abab36df02488d338db2`,
  `SettlementFixed.sol` `fbb836d170a291899f86379363012675aae9207b2a4afb8d5fdb09a90e343144`,
  `RollupProcessorV3.sol` `7d78725e077c1fe5c06d325678c33d20f278dc81a2121fe3c4f4e8fd7e996d31`,
  and `Decoder.sol` `92e8ebe38667f3a262bad4d2c568fdfb449faccd065b64f9900f4acbf10a6078`.
  The last two match the local verified-source bytes reported by [AZ1](../AZ1/REPORT.md).
- The pre-task project checkpoint is preserved byte-for-byte under
  `results/raw/S2c/prior-checkpoint/` with its SHA-256.

```sh
export BC=/home/pollmix/Coding/bc
export BINDCHECK_CIRCOM=$BC/BindCheck/tools/circom-2.1.9/target/release/circom
export GIT_NO_LAZY_FETCH=1 GIT_OPTIONAL_LOCKS=0

python3 -m unittest -v tests.test_bindcheck_zk_cli tests.test_bindcheck_zk_controls \
  tests.soundness.test_verdict_soundness tests.soundness.test_followup \
  tests.coverage.test_rules tests.freeze2.test_p4_key tests.s2a.test_precision_fixes \
  tests.s2c.test_extent

python3 -m bindcheck_zk.freeze

for variant in Faulty Fixed; do
  python3 -m bindcheck_zk.cli analyze prototypes/az1 \
    --consumer "contracts/Settlement$variant.sol" \
    > "results/raw/S2c/az1-$variant-candidate.json"
done
python3 -m bindcheck_zk.cli analyze "$BC/wt-AZ1/results/raw/AZ1/deployed-source/files" \
  --consumer src/core/processors/RollupProcessorV3.sol \
  > results/raw/S2c/rollup-processor-v3-candidate.json
```

The offline DEV command used the prescribed runner's `main()` and arguments.
Its `--raw-task` validator rejects `S2c`, so a wrapper set only its raw
output root. The runner, checkout paths, row selection and budgets were
unchanged. Stdout and stderr are in `results/raw/S2c/dev-final.log`.

```sh
/usr/bin/time -p python3 - --phase after --skip-fetch \
  --checkout-root "$BC/BindCheck/feasibility/work/full-dev" \
  > results/raw/S2c/dev-final.log 2>&1 <<'PY'
from scripts import run_bindcheck_zk_full_dev as runner
runner.RAW_ROOT = runner.ROOT / "results" / "raw" / "S2c" / "T24"
raise SystemExit(runner.main())
PY
```

## Results (tables, exact counts)

| Target | P1-EXTENT | Reason and evidence |
| --- | --- | --- |
| AZ1 faulty | `VIOLATION` (E1) | [SettlementFaulty.sol:60](../../prototypes/az1/contracts/SettlementFaulty.sol#L60). The verifier vector carries the commitment over four rows, and the calldata count can select a shorter prefix with no tail check. |
| AZ1 fixed | `VERIFIED_WITHIN_SCOPE` (E1) | [SettlementFixed.sol:65](../../prototypes/az1/contracts/SettlementFixed.sol#L65). The preceding tail loop requires kind zero, so the settlement branch that requires kind one cannot run for a skipped row. |
| Synthetic fixed-length controls | `VERIFIED_WITHIN_SCOPE` (E1) | The equality guard, equivalent paired inequalities, and fixed-array length expression each establish the committed length as the bound. |
| Synthetic opaque bound | `UNKNOWN` (E0) | `EXTENT_BOUND_SOURCE_UNSUPPORTED`. The bound returned by an unmodeled helper could not be traced to calldata or a recognized fixed extent. |
| Verified-source `RollupProcessorV3` | `UNKNOWN` (E0) | `EXTENT_ASSEMBLY_VERIFIER_INPUT_UNSUPPORTED` at `src/core/processors/RollupProcessorV3.sol:1103`. The verifier call and arguments are assembled by hand, and the analyzer cannot recover which calldata region becomes the verifier input. |

All three direct CLI runs exited 0. The analyzer completed the requested
source scan on V3 with an `UNKNOWN` research verdict. The E1 result on the
faulty control complements [AZ1's previously recorded E4 fixture evidence](../AZ1/REPORT.md).
S2c ran source analysis and regression tests.

### DEV warning adjudication

The final runner exited 0 after 155.37 s. All 56 checkouts matched their
pinned revisions, and every analyzer process exited 0. There were zero
crashes or row-level timeouts. The legacy analyzer recovered triples in 46
rows and recorded 41 successful and 35 failed circuit builds, including
three per-build timeouts.

| P1-EXTENT outcome | Rows |
| --- | ---: |
| `VIOLATION` | 0 |
| `VERIFIED_WITHIN_SCOPE` | 0 |
| `UNKNOWN` | 56 |

**New E1 warnings: 0.** The adjudication list is empty (TP 0, FP 0, unsure 0).
Eleven rows generated 14 E0 diagnostics, listed below. The other 45 returned
`EXTENT_CONSUMER_NOT_FOUND`. These counts show the warning and triage cost
of the supported fragment on this DEV set. They leave the false-positive
rate and recall unresolved.

| DEV row | File and line | Diagnostic | Judgement |
| --- | --- | --- | --- |
| DEV-F04 | `packages/contracts/contracts/Unirep.sol:360` | `EXTENT_STRUCTURE_PARSE_INCOMPLETE` | Unsure (E0) |
| DEV-F10 | `packages/contracts/src/Game.sol:475` | `EXTENT_ENTRY_CONTEXT_UNSUPPORTED` | Unsure (E0) |
| DEV-F12 | `contracts/circom/src/SPSC.sol:253` | `EXTENT_ENTRY_CONTEXT_UNSUPPORTED` | Unsure (E0) |
| DEV-F15 | `contracts/EncryptedERC.sol:822` | `EXTENT_ENTRY_CONTEXT_UNSUPPORTED` | Unsure (E0) |
| DEV-F15 | `contracts/EncryptedERC.sol:919` | `EXTENT_ENTRY_CONTEXT_UNSUPPORTED` | Unsure (E0) |
| DEV-F15 | `contracts/EncryptedERC.sol:989` | `EXTENT_ENTRY_CONTEXT_UNSUPPORTED` | Unsure (E0) |
| DEV-F15 | `contracts/EncryptedERC.sol:1078` | `EXTENT_ENTRY_CONTEXT_UNSUPPORTED` | Unsure (E0) |
| DEV-F30 | `projects/ZKredential/packages/zk-contracts/contracts/core/ZKRWARegistryMultiPlatform.sol:300` | `EXTENT_ENTRY_CONTEXT_UNSUPPORTED` | Unsure (E0) |
| DEV-F31 | `contracts/Blind.sol:49` | `EXTENT_PUBLIC_VECTOR_UNSUPPORTED` | Unsure (E0) |
| DEV-F32 | `contracts/src/email-account/EmailAccount.sol:138` | `EXTENT_ENTRY_CONTEXT_UNSUPPORTED` | Unsure (E0) |
| DEV-F35 | `contract/DarkPool.sol:152` | `EXTENT_ENTRY_CONTEXT_UNSUPPORTED` | Unsure (E0) |
| DEV-F44 | `packages/contracts/src/ProofOfTwitter.sol:95` | `EXTENT_STRUCTURE_PARSE_INCOMPLETE` | Unsure (E0) |
| DEV-F50 | `contracts/src/BatchSettlement.sol:389` | `EXTENT_PUBLIC_VECTOR_UNSUPPORTED` | Unsure (E0) |
| DEV-H03 | `semaphorejs/contracts/Semaphore.sol:88` | `EXTENT_STRUCTURE_PARSE_INCOMPLETE` | Unsure (E0) |

Raw evidence is under `results/raw/S2c/T24/after-20261118T201101Z-4/`.
The manifest and ledger record the pinned revision, command, and exit status
for every row. `results/raw/S2c/summarize-dev.py` checked all 56 result hashes
and candidate identities and wrote `extent-diagnostics.tsv`.

| Raw artifact | SHA-256 |
| --- | --- |
| `manifest.json` | `769d879915ab2a20452bae8c5bad559c0609432a348cc8d30b9165844e92358d` |
| `per-row-ledger.json` | `1090013653dfb3b8abe2f49d9ed8ecac9659b26d00ad678e8dcbf2c730d49240` |
| `extent-diagnostics.tsv` | `6e6da13093851b07a47cafbba857ca9cc28d230b1ed0b7c2b04a3e62dbfdbce9` |

## Assumptions and limitations

- The supported fragment uses fixed, same-length calldata word arrays and
  one simple settlement prefix in the same function as a checked verifier
  call. It recognizes ABI-encoded hash inputs and a helper that hashes rows
  into a fixed digest array before reducing it. It supports direct state
  writes, token-style calls and effects on a locally declared interface.
  Dynamic regions, unrecognized copies and calldata decoders, unmodeled
  calls, modifiers, inline assembly, and more complex control flow can
  yield `UNKNOWN`.
- E1 assumes correspondence to a verifier that authenticates its supplied
  vector and binding of the recognized hashes. It establishes a static
  extent gap within that consumer model. Whether a proof can attest a
  non-neutral omitted row and whether the protocol requires its discharge
  require separate producer and policy evidence. The verified controls
  establish equality or a consumer-enforced no-op for this extent check.
- The verified-source copy is a local input pinned by hash. AZ1 supplies its
  source correspondence evidence. This lane did not independently compare
  deployed bytecode, run proofs, or interact with a chain.
- The DEV sample estimates warning cost only for the exercised fragment. Low
  applicability leaves recall, transfer, and ecosystem false-positive rates
  unresolved.

## Failed approaches / surprises

- The first assembly diagnostic also flagged an unrelated precompile call
  in V3. Tightening it to a `staticcall` with a verifier-named destination
  left the single diagnostic at line 1103.
- Pre-adjudication review found two source-analysis gaps. Bound dependence
  can flow through cast aliases, and an opaque proof argument can hide
  additional checks. Added a transitive dependency check, restricted
  recovered proof arguments to simple identifiers, and added one regression
  for each. The earlier DEV attempt was already running. The runner returned exit 1
  after processing all 56 rows because it observed two candidate hashes.
  Preserved that attempt in `results/raw/S2c/dev-run.log` and
  `results/raw/S2c/T24/after-20261118T200824Z-4/`. The final run uses one
  candidate throughout.
- Both AZ1 fixtures get P4 `VIOLATION / GAMMA_EQUALS_DELTA_SOURCE_KEY` on
  this lane pre-change and on the candidate, whereas the historical AZ1
  report describes P4 as `VERIFIED_WITHIN_SCOPE` under its analyzer
  invocation. Re-running the worktree base from an isolated archive confirmed
  identical P1–P5 summaries before and after S2c on both variants. The
  historical result is preserved.
- `hc get "$HC_TERMINAL_ID"` could not open its lock in the read-only core
  state directory. The validation ran in the managed shell instead.

## Held-out hygiene statement

Before opening any third-party source, reconstructed the 56 DEV rows with
the runner's `dev_rows()`, collected their 52 distinct repository names,
added `AztecProtocol/aztec-connect`, and passed the sorted list to
`python3 scripts/check_holdout.py`. All 53 names returned `ALLOWED`
(exit 0, `results/raw/S2c/holdout-guard.log`). Only the guarded DEV
checkouts and the named AZ1 verified-source copy were analyzed. No unused
EVAL family was opened. The checker used the supplied local inputs with
`--skip-fetch`.

## Recommended next task

Add a producer-side padding check to the DEV controls. Completion requires
the same consumer source to produce distinct E2 outcomes for two pinned
compiled producer relations, one permitting a non-neutral omitted row and
one forcing every omitted row neutral under an authenticated count, plus
`UNKNOWN` when the producer correspondence is missing.
