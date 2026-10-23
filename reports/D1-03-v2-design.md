# D1-03 v2 design and component validation

Date: 23 October 2026. **Bounded design task DONE; D1-03 remains incomplete.
Joint research verdict UNKNOWN.** User authorization: “do the recommended
tasks,” following the v2 recommendation in [preflight](D1-03-preflight-01.md).
This authorizes the prospective design change; it is not independent human
policy annotation or acceptance of a security result.

## Objective and frozen limits

Replace the v1 free-transfer-outcome obstacle with an explicit immediate
settlement family, separate permission and obligation policy, preserve failed
transfers as UNKNOWN controls, and freeze prospective claims and attempts.
The [task freeze](../protocols/d1/d1-03-v2-design.json) at 17:23:25 UTC permits
60 minutes, one offline Foundry invocation (600 seconds, 4 GiB address space),
one finite Python enumeration (at most 10,000 cases), and zero network,
dependency installation, primary solver queries, proofs or full rollup replays.
Completion requires source-backed policy/state design, meaningful component
controls, preserved evidence and a checkpoint. It does not require or claim
a completed joint analyzer.

## Delivered design

The [v2 protocol](../protocols/d1/d1-03-joint-semantics-v2.md) and its
[machine-readable matrix](../protocols/d1/d1-03-joint-semantics-v2.json) specify:

- Independent P and O lists, with an explicit analyst rationale for mandatory
  immediate mint/burn settlement; optional permissions remain expressible.
- Logical `(frame, offset)` occurrence identity. Padding contributes nothing;
  equal messages in distinct active frames retain multiplicity. Actual
  activation/certification correspondence must still be extracted.
- Exact low-160 recipient semantics and injective occurrence matching using
  counts of equal semantic keys. V1's pair-sharing heuristics are not reused.
- Standard pinned ERC20 behavior, no substitutions, burn amounts bounded by
  `2^64-1`, decoded nonzero recipients and initial funding `N*(2^64-1)`.
  Sequential token state derives success. This intentionally restricted state
  family excludes insufficient liquidity and does not claim reachable history.
- Seven case/scope rows with four primary slots each: AUTH, COVERAGE, DEFER,
  NONVAC. Maximum 28 attempts, 300 seconds and 4 GiB each (8,400 solver seconds).
  No retries or transfer of unused slots into tuning. Historical N=8 queries
  retain their original scope and results. At most 21 replay candidates have
  separately stated 600-second ACIR/Foundry limits; no new real proofs.

The new matrix is prospective. Exact implementation/query hashes and verified
artifact/binding prerequisites are still required before primary execution.
The test outcomes below are not the required joint NONVAC/repaired-control
results. V1 and its historical freeze remain unchanged.

## Source evidence and observations

Sixteen source files were captured offline from the A/B pinned Git revisions.
Exact commands, object identities, SHA-256 hashes and exit statuses are in
`results/raw/D1-03/v2-design/source-capture.json`. They include the producer
padding/concatenation code, burn layout, whitepaper lifecycle rationale,
unchanged consumer and dependency lock/configuration.

Source-confirmed: padding can substitute the first proof's recursive inputs;
recursive invocation count alone cannot count logical authorizations. The
consumer truncates recipient words to 160 bits and catches failed token calls.
The pinned OZ token checks recipient and balance, and updates balances in
order. Source rationale supports the stated policy choice but is not a
complete protocol specification or independent human annotation.

Locally reproduced component behavior: funded `100 -> 93` and recipient
`0 -> 7`; insufficient funding returns false without effects; zero recipients
fail; zero/self transfers succeed with the expected balances; sequential calls
use updated balances; high recipient bits are truncated; outer revert rolls
back token effects. These use synthetic local assets and the unchanged helper,
not `verifyRollup`, a mocked verifier, real constraints or real proofs.

Unexpected control worth preserving: a low-level call to an empty-code address
returns success through this helper without transferring a token. That address
is outside the pinned-token model. A helper's return flag alone is insufficient
evidence of a protected transfer.

## Commands and results

```sh
python3 scripts/d1_03_v2_design_run.py
```

The [one-shot runner](../scripts/d1_03_v2_design_run.py) freezes exact input and
tool hashes before executing these commands once:

```sh
/home/pollmix/.foundry/bin/forge test --root '/home/pollmix/Coding/BindCheck-d1 (copy)/build/D1-03/v2-design' --offline -vvvv
python3 scripts/d1_03_v2_policy_checks.py
```

Both exit 0. Foundry: **10 passed, 0 failed, 0 skipped**, 12.295 seconds
including compilation. Python: **8,892 cases**: 1,275 matching scenarios,
7,605 funding/sequence scenarios and 12 explicit controls. Matching counts
are cross-checked against exhaustive injective assignments. Funding checks
include both successful and failed sequences. They are finite synthetic
checks, not universal SMT results or a validated analyzer.

Tools: Forge 1.4.1-stable (`cf7746048646f2ecff48246dd61e265e49ab16f0`),
solc 0.8.20+commit.a1b79de6, viaIR/optimizer 200, Python 3.12.12. Component
compiler/runtime target is Shanghai, supported by solc 0.8.20; this is not
validation of the inherited Cancun/verifier configuration. The runner uses
the available explicit 0.8.20 binary and this copy's pinned OZ sources;
it does not use the PATH solc shim or inherited sibling-path remappings.

Raw input freeze, full traces, stdout/stderr, exact argv, times and exit
statuses are in `results/raw/D1-03/v2-design/`. The tracked
[metadata manifest](../metadata/d1/d1-03-v2-design.json) binds them and the
design artifacts. No experimental retry or failed validation invocation
occurred. No primary solver, nargo execution, new proof, full settlement
replay, held-out analysis, commit, push or external contact occurred.

## Preservation, limitations and next task

All 695 prior raw files and 177 pre-existing project files were inventoried.
Only README, roadmap and project-status are prospectively updated in this
task; their exact prior bytes are archived under `prior-checkpoint/` in the
raw directory. All other inventoried files and the shared Git index must
match the preservation check. Previously edited workspace guidance remains
unchanged. New files are the design/task protocols, component test, two
validation scripts, report and metadata; build outputs/raw logs remain ignored.

The policy is analyst supplied and source motivated. A3 key correspondence
and synthetic seed realizability remain assumptions. The component tests do
not show a valid Payy proof, producer/decoder correspondence, universal
coverage, a repaired-case guarantee, novelty or baseline advantage.

**Next task:** implement the D1-03 v2 extraction and analysis path, first
checking the actual artifact and logical-frame bindings; freeze its executable
inputs before primary queries. Completion requires all D1-03 gates, including
real-constraint candidate execution, committed consumer replay, independent
oracle confirmation, repaired-case non-vacuity/verification and UNKNOWN
regressions. A missing binding or unsupported path must stop that candidate
as UNKNOWN. D1-04 remains blocked until the gate passes. No renewed approval
is needed for routine work within the authorized v2 scope; further scope,
policy or resource changes still require review.
