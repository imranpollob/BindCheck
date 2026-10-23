# D1-03 preflight 01 — transfer-failure gate requires review

Date: 23 October 2026. **Preflight complete; D1-03 INCOMPLETE, progress ACTIVE.
Research verdict: UNKNOWN. Stop for review before new implementation or runs.**

## Objective, authority and frozen limits

After [D1-02 reconciliation](D1-02-reconciliation-01.md), check whether the
recovered D1-03 v1 protocol can support its required repaired control without
changing assumptions or criteria. The [preflight protocol](../protocols/d1/d1-03-preflight-01.json)
was frozen at 17:09:25 UTC. Limits: 20 minutes, zero network requests, builds,
solver queries, proofs, replays or analyzer runs; at most one two-row Boolean
diagnostic. Completion means a source-backed consistency decision, evidence
preservation and a concrete next recommendation. It does not mean D1-03 is done.

The [research contract](../docs/research-contract.md) requires unsupported
deferral to remain UNKNOWN and distinguishes permissions from required
obligations. The user's execution request requires a review stop before
changing policy assumptions, evaluation criteria or resource budgets. Those
rules control over the recovered protocol. No protocol or policy was revised.

## Finding 1 — the admitted failure branch obstructs the required clean control

The unchanged [D1-03 v1 protocol](../protocols/d1/d1-03-joint-semantics.md)
contains all of these choices:

1. Section 1 requires the repaired revision B to have non-vacuity, replay and
   `VERIFIED_WITHIN_SCOPE` for D1-03 completion.
2. Section 3 admits arbitrary rollup token balance and a free `ok_j` Boolean
   per transfer attempt. S2 contains a burn of seven units to `0xdead`.
3. Section 4 classifies a compatible failed attempt as unsupported deferral,
   and requires `G-DEFER` UNSAT for `VERIFIED_WITHIN_SCOPE`.

Conditional on a matching burn attempt in an otherwise admitted successful
transition, the consequence is immediate:

| `ok_j` | Committed transfer | This attempt satisfies `G-DEFER` | v1 consequence |
| --- | --- | --- | --- |
| false | no | yes | UNKNOWN: DEFERRAL_UNSUPPORTED |
| true | yes | no | Other obligations still need checking |

The producer relation does not constrain the separate free transfer-success
Boolean. Repairing a circuit message boundary does not remove this modeled
environmental branch. A successful honest replay with a funded token would
show one successful execution, not eliminate the admitted failing executions.

The source supports keeping this branch visible. The preserved
`build/D1-03/consumer/src/rollup3/RollupV1.sol`, SHA-256
`7062065cc95f447fea8bb28242d51c836c3cf9e39f1625180ecf9c240a5ffd8f`, has:

- `verifyBurn`, lines 459–469: with no substitutor, calls `executeBurn` and
  then advances the message cursor without requiring its returned success;
- `executeBurn`, lines 504–513: emits the success flag and returns it;
- `executeBurnToAddress`, lines 516–533: catches a failed low-level transfer
  and returns false; and
- `verifyRollup`, lines 349–362: later proof verification can still revert
  the whole transaction. The preflight does not assume that later checks pass.

This is **not** a full joint SAT result, a producer witness, demonstrated
reachable deferral or a Payy vulnerability. It is a conditional inconsistency
between the declared broad transfer model and a promise to obtain the
required clean result. If no matching burn transition is feasible, the
required S2 honest control instead needs explanation; no vacuous verification
may replace it. A complete model might reveal additional blockers.

**Gate decision:** do not build toward a promised clean result by silently
setting `ok_j=true`, removing `G-DEFER`, fixing surrounding state after a
result, or treating a funded replay as universal non-deferral. Retaining v1
is legitimate, but its failed/UNKNOWN clean gate must leave D1-03 incomplete
and D1-04 waiting. No full-query outcome is assigned by this diagnostic.

## Finding 2 — coverage policy needs an explicit reviewed basis

V1 Section 4 makes every parsed permission a required coverage obligation.
The research contract permits separate permissions and obligations and says
authorization does not require every permission to be exercised. The v1
reference to Payy's compact message format explains record decoding; it does
not by itself justify the obligation assigned to every record, deduplication
of equal certified vectors, or the legal discharge rule after transfer failure.

This policy may be appropriate for a defined Payy transition. It is not
established by this preflight, and the source's handling of failed transfers
does not by itself establish the protocol's intended obligation policy.
Require an explicit analyst-reviewed policy rationale before using these
choices as evaluation ground truth. This is a missing justification, not a
finding that the policy is necessarily false. AI review is not independent
human annotation.

## Checks, commands and evidence

```sh
python3 -I scripts/d1_03_preflight.py --output results/raw/D1-03/preflight-01/diagnostic.json
```

Exit 0. Seven input/protocol checks pass; exactly two Boolean rows were
enumerated. The [diagnostic helper](../scripts/d1_03_preflight.py) labels its
result as conditional protocol logic, with research verdict UNKNOWN. It is
not an analyzer or replay oracle. The inputs match their preflight SHA-256
freeze. Python 3.12.12 was used; no solver/compiler/prover version was invoked
in this task. The inherited v1 tool pins retain their historical meaning.

Raw evidence is under `results/raw/D1-03/preflight-01/`, including the freeze,
diagnostic, source excerpts and preservation check. The tracked
[preflight metadata](../metadata/d1/d1-03-preflight-01.json) binds those files.
The source excerpts are read-only copies of the exact consumer/protocol bytes.

No failed experimental attempt occurred in this preflight. The unexpected
observation was the above conflict in the recovered protocol. The earlier
reconciliation's failed directory creation and first audit are recorded in
its own report. Inherited compilation logs were not repeated, and no new
D1-03 code is represented as validated.

## Concrete recommendation for review

**Authorize a separately versioned D1-03 v2 design, not more v1 solver time.**
Keep the supported fragment at immediate occurrence-level discharge. Before
execution, specify an explicitly restricted successful-transfer pre-state
family and model the relevant standard-token balance/recipient/amount
conditions that imply transfer success. Do not merely assert a free success
flag. State that the resulting guarantee excludes failed-transfer histories.
Keep an insufficient-funding/failing-transfer control reported UNKNOWN under
the unsupported-deferral rule. No historical N=8 query or guarantee changes.

The next design task is complete only when it supplies:

- separate permission and obligation records with cited policy provenance
  and reviewed justification for multiplicity/deduplication;
- explicit admitted-state bounds and source-backed success preconditions;
- a preserved failing-transfer control and a non-vacuous honest control;
- a revised claim/evaluation table that distinguishes admitted-state
  verification, ACIR execution and real-proof consumer replay; and
- a new prospective run manifest retaining the original 300-second/query
  and 4-GiB limits, with a stated total attempt budget and treatment of the
  inherited setup artifacts.

This narrows v1's admitted states and changes its evaluation contract, so it
requires the user's review under the requested stop rule. It is a proposal,
not an implemented or approved change. The alternative is to retain v1,
accept the unresolved feasibility gate and stop D1; implementing general
pending obligations would be a separate scope decision.

**Achieved:** completed availability reconciliation and identified the next
protocol obstacle without spending experiment budget. **Unresolved:** D1-03
joint extraction, non-vacuity, replay and clean controls; all later roadmap
tasks remain dependent. **User-side action:** review the proposed v2 boundary
and coverage rationale before authorizing resumed implementation. No setup,
commit, push, external contact or held-out evaluation is needed for review.
