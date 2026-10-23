# D1-03 consumer execution 01

Date: 23 October 2026. **Concrete AST execution/component task DONE;
full symbolic consumer relation, joint D1-03 and replay readiness UNKNOWN.
D1-04 remains WAITING.** This is not completion of the remaining roadmap.

## Objective and limits

The user requested “Finish rest of the tasks.” Resume at the documented
consumer prerequisite, from clean independent branch `chatgpt-codex`, revision
`42bd0ebbf365469fe3147bb13d7359b129319aa2`. Read the contract, README,
roadmap, workspace guide, latest reports and preserved reviewer feedback.
No completed research experiment is repeated or reclassified.

The [protocol](../protocols/d1/d1-03-consumer-execution-01.json), frozen at
22:47:04 UTC before implementation/execution, defines four completion criteria:
concrete AST execution with exact effects/rollback; preserved guard/verifier
boundaries; actual-artifact and independent Solidity component controls; and
an explicit joint-composition readiness decision. Limits are 120 minutes,
24 Python invocations, 12 artifact invocations and four Foundry invocations.
Python/artifact runs have 120 seconds each; Foundry has 600 seconds; all have
4 GiB address-space limits. Zero downloads, installs, primary solver queries,
new proofs, primary candidate replays or held-out evaluation are allowed.

## Implementation and evidence level

- [Consumer interpreter](../src/bindcheck_d1/frontends/consumer_execution_v1.py)
  follows compiler declaration IDs through 12 actual function/modifier bodies:
  `verifyRollup`, `onlyProver`, root/commit checks and the complete message
  helper closure. It executes actual AST branches, checked unsigned arithmetic,
  ordered mapping writes, calldata reads, casts, supported scalar ABI operations
  and events. Unknown node/call kinds fail closed; unhandled dynamic types,
  recursion and step-limit exhaustion remain UNKNOWN.
- The guard's separately checked seven-body frame remains an abstraction.
  It preserves protected storage and calldata, retains arbitrary validator-index
  writes and includes revert. Concrete samples explicitly choose return/revert
  and an index; they do **not** establish signature acceptance, validator-set
  reachability or termination. Missing guard input yields
  `GUARD_ACCEPTANCE_UNRESOLVED`.
- The exact proof bytes/public-input vector passed to the verifier are recorded.
  Missing verifier relation yields `VERIFIER_RELATION_UNRESOLVED`. An explicit
  Boolean used by a component control is an **abstract boundary choice**, never
  a valid proof or accepted full replay. Every interpreter result's security
  verdict is UNKNOWN, including its `RETURN` outcome.
- The external token adapter implements sequential ordinary OZ 5.0.1 ERC20
  transfer under explicit A5/no-overrides/no-callback assumptions. It checks
  address/balance/supply invariants, derives success, and preserves zero/self
  occurrences. This is a hand-implemented, source-backed adapter validated by
  component tests, not automatic extraction or a proof of all token semantics.
- Outer revert discards all modeled events, token transfers and storage writes,
  including registry consumption, root/height updates and guard-index changes.
  Boundary-call diagnostics are kept separately and are not committed effects.
- [V2 admission](../src/bindcheck_d1/consumer_scope_v2.py) separately checks
  canonical fields, N, root, funding, registrations, initially unspent registry,
  no substitutions and consumed burn bounds. It does not add a missing
  implementation constraint or invent P/O correspondence. Failed transfers stay
  outside the immediate fragment with `DEFERRAL_UNSUPPORTED`.

The AST/source artifacts are the **same 20 identities** used by the completed
codebase review. Source contents are checked against solc metadata; AST/bytecode
correspondence remains A6. The interpreter identity includes its implementation,
AST, sources, boundary declarations, guard/context and step limit. No change to
the pinned consumer or third-party source is made.

The new [artifact harness](../scripts/d1_consumer_execution_check.py) supplies
synthetic states and assertions outside analyzer input. Its 29 controls include
last-slot reads, truncated records, duplicate registry consumption, repeated
burn occurrences, exact forwarded inputs, late rejection rollback, high address
bits, zero/self transfers, insufficient liquidity and unknown token code. It
checks balances, registry state, root/height, retained index, events and effects.
These are concrete samples, not a universal symbolic relation or joint NONVAC.

The [Solidity tests](../tests/d1/execution/ConsumerExecution.t.sol) inherit and
expose the unchanged message helpers with test-only state setup. They execute
ordinary pinned ERC20 bytecode and check balances, registry state and transfer
logs. **No verifier is instantiated or mocked, and `verifyRollup` is not run.**
Their late-revert wrapper validates component rollback; the interpreter's late
verifier/height cases remain abstract full-entry controls. Neither is promoted
to an end-to-end security finding.

## Commands, outcomes and failures preserved

Use the [append-only bounded runner](../scripts/d1_consumer_execution_run.py);
its task-specific envelope is historical, not permission for indefinite reruns.
All snapshots, argv/cwd, timestamps, exit statuses, timeout/memory limits and
stdout/stderr are under `results/raw/D1-03/consumer-execution-01/`.

| Invocation | Observed result |
| --- | --- |
| `python3 scripts/d1_consumer_execution_run.py python`, python-01 | exit 1; 108 discovered tests, 16 fixture errors: the node factory's `kind` argument collided with Solidity's `kind` field. Rename factory parameter; preserve failed run. |
| python-02 | exit 0; 108 tests pass, including 27 new controls |
| python-03 | exit 0; 118 tests pass after adding admission and fail-closed controls |
| python-04 | exit 0; **119 tests pass** (81 existing plus 38 new), 0.216 s; adds nested-write provenance regression |
| `python3 scripts/d1_consumer_execution_run.py artifact`, artifact-01 | exit 1; harness passed arguments in the wrong ABI order. Fix order and add compiler-type validation of entry/internal arguments and storage. |
| artifact-02 | exit 2; several controls UNKNOWN because bare `bytes` declarations lacked a default-type case |
| artifact-03 | exit 2; successful transfers reach unsupported ABI bool decoding; actual solc encodes the one-element type tuple as `type(bool)` |
| artifact-04 | exit 0; 29/29 concrete artifact controls pass after structural bool-type decoding fix |
| artifact-05 | exit 0; 29/29 pass with strengthened balance/input/state checks and separate v2 admission |
| artifact-06 | exit 0; **29/29 pass**, 13.789 s; final interpreter fixes storage-write provenance to point at the assignment rather than the index expression |
| `python3 scripts/d1_consumer_execution_run.py forge`, forge-01 | exit 0; **13 passed, 0 failed, 0 skipped**, 12.944 s including compilation |

Foundry command: `/home/pollmix/.foundry/bin/forge test --root
'<checkout>/build/D1-03/consumer-execution-01' --offline -vvvv`.
Python 3.12.12; Forge 1.4.1-stable (`cf7746048646f2ecff48246dd61e265e49ab16f0`);
solc 0.8.20+commit.a1b79de6, viaIR, optimizer 200, Shanghai; OZ 5.0.1. Exact
executable/source/configuration hashes are in `solidity-inputs.json`; versions
and exit statuses are in `versions.json`. No compiler/prover dependency setup
is concealed in the test result. The legacy Node setup blocker is unchanged.

Two details are source/locally component-confirmed, not new vulnerability claims:

1. A default registry entry with zero amount and zero note kind can be consumed
   by the matching mint record. Adding an inferred “entry exists” guard would
   strengthen the implementation incorrectly.
2. A helper can read beyond its logical scan end if actual calldata has those
   words. The enclosing `verifyRollup` length check supplies the necessary bound.
   The N=1 helper-only control is explicitly outside v2; it is not a new primary
   scope or a relaxation of the N=8/N=1000 tasks.

## Readiness decision and review recommendation

**Do not start D1-04.** This task supplies a concrete execution engine and
component evidence, not the frozen method's symbolic consumer relation.
Missing work includes positive-advance/reachable-position symbolic lowering,
exact finite-field/word/address and registry/token-state composition, all live
producer constraints, full joint queries, candidate ACIR execution, accepted
consumer replay and independent policy-oracle/non-vacuity gates. No one of
these is inferred from the passing tests. All **28 primary slots remain unused**.

The replay intake also finds a concrete prerequisite problem. The unchanged
T13/T16/T18/T19 harnesses require historical proof/public-input bundles and
hash summaries. Their required local paths are absent. A read-only inventory
of this checkout, the original checkout and sibling raw directories finds no
files with the conventional proof/public-input names checked. See
`replay-availability.json` and `replay-prerequisites.json`. This is a statement
about inspected local availability, not evidence that the historical experiments
failed or that no backup exists elsewhere. Pinned verifier bytecode is present
in source checkouts; a missing old `build/T12` path alone is not a proof blocker.

The existing protocol explicitly permits **zero new real proofs**. A1 verifier
soundness does not supply an accepting proof; A8's synthetic-seed realizability
assumption does not supply replay bytes. ACIR execution and an assumed accepting
verifier must not be silently relabeled as accepted proof-to-settlement replay.
The task stops for the user's required resource/evaluation review, **not because
its engineering invocation budget was exhausted**. No proof budget or replay
criterion has been changed, and no solver timeout/failure is claimed.

**Recommended next bounded task: restore and qualify the replay inputs.**
First locate an archival T13 mint-control and T16 control/candidate bundle,
including their original summaries. Copy into a fresh D1 namespace, verify
hashes against the preserved records and match source/key/public-input identity.
Then explicitly test compatibility with the frozen v2 SEED/FREE cases. Restored
historical controls are not automatically the S1/S2 seeds and cannot silently
replace them. Completion is a manifest identifying compatible accepted replay
inputs, or an evidenced incompatibility/missing-artifact result.

If no compatible archive is available, prepare a separately versioned proposal
for bounded proof provisioning and any necessary seed/evaluation change before
execution. Retain UNKNOWN meanwhile. After replay feasibility is resolved,
finish symbolic composition under the unchanged solver controls, and advance
only if the full D1-03 gates pass. The review stops after D1-04/D1-06 and before
held-out work remain unchanged. The user has been asked for the archive location;
no automatic external contact, scope change or backup search outside these
project references is authorized by this report.

## Preservation and handoff

Exact prior README/roadmap/checkpoint copies are archived before prospective
updates; `prior-files.json` inventories 1,496 pre-existing tracked/raw files.
The [task metadata](../metadata/d1/d1-03-consumer-execution-01.json) seals the new
implementation, protocol, tests, report, living documents and raw evidence.
Historical reports, protocols, raw logs, source checkout and sibling remain
unchanged. No commit, push, held-out evaluation or contact with others occurred.
