# D1-03 guard frame 01 — review stop

Date: 23 October 2026. **Guard-summary prerequisite ACTIVE/UNKNOWN. Final
artifact validation is incomplete. D1-03 remains incomplete; D1-04 WAITING.**

## Objective, frozen limits and decision

Continue after [typed bindings](D1-03-typed-bindings-01.md) and the
[consumer-boundary audit](D1-03-consumer-boundary-01.md), without narrowing
v2's state family or assuming signature acceptance. The
[protocol](../protocols/d1/d1-03-guard-frame-01.json) was frozen at
19:24:10 UTC: 45 minutes, two synthetic test invocations and one pinned-artifact
check, each capped at 120 seconds and 4 GiB; zero network, compilation, solver
queries, proofs or settlement replays.

Completion requires a fail-closed transitive frame checker, checked use-site
bindings, invalidation controls, a current-version artifact check, and preserved
evidence/report/checkpoint. The checker and 22 controls are implemented.
**The current version has no artifact-check result.** The one permitted
artifact run passed before a subsequent correctness hardening. Its result
is historical, not transferable to the current checker. Do not use that
certificate as a completed summary gate. Both synthetic slots and the single
artifact slot are consumed; continuing requires review of an additional
artifact-check budget. No limits were increased in this task.

## Implementation and preservation argument

[guard_frame_v1.py](../src/bindcheck_d1/frontends/guard_frame_v1.py) walks the
actual internal guard's transitive declaration graph. It checks a restricted
Solidity AST subset and records direct state writes. It rejects writes through
storage aliases, memory-reference arguments, external/dynamic calls, assembly,
unknown constructs and nonempty entry returns. The final version additionally
rejects virtual internal functions and user-defined operator dispatch.

The proposed local rule is a structural frame argument under the existing
solc AST/bytecode correspondence assumption A6: for any finite successful
execution of the supported guard, every storage root outside the computed
may-write set is unchanged. Storage-neutral expressions and builtins cannot
write those roots; assignments are checked; composition of internal calls
and each finite sequence of loop iterations preserves the same property.
Scalar arguments are passed by value and calldata is immutable. Possible
reverts are retained and roll back the invocation. No bound on signature or
validator-set array length, termination claim, or guard-acceptance theorem
follows from this argument.

The summary retains arbitrary post-values for written roots, rather than
removing validator state. The task checks all state declarations except the
explicitly retained validator index as protected. This is a local frame
projection, not a policy assertion that validator state is irrelevant to all
later code. Full-transition composition must retain its effect on later
behavior or check an additional projection argument. Reverting paths, gas
failure, signature failure and cryptographic outputs are not assumed away.

The use-site check verifies the actual internal call and each scalar/calldata
argument declaration. Its cache identity binds the full AST, source bytes,
caller/call/argument identities, protected roots, policy, bounds, assumptions,
and (after hardening) the checker source hash. It recomputes the structural
check rather than accepting a supplied write set. These checks do not yet
implement full symbolic consumer execution, exact token effects, verifier
semantics, or a solver-side summary application. Author inspection is not
independent human annotation or an independent proof of extraction soundness.

## Executions and unexpected observations

Exact commands, versions, limits, hashes, executable snapshots, output and
statuses are in `results/raw/D1-03/guard-frame-01/`:

| Command | Observed result | Interpretation |
|---|---|---|
| `python3 scripts/d1_03_guard_frame_run.py tests` (tests-01) | exit 0; 18 controls; 0.116346 s | Initial checker controls pass |
| `python3 scripts/d1_03_guard_frame_run.py artifacts` (artifacts-01) | exit 0; 0.467051 s | Initial version's local frame gate passes; security verdict UNKNOWN |
| `python3 scripts/d1_03_guard_frame_run.py tests` (tests-02) | exit 0; 22 controls; 0.116412 s | Hardened version's controls pass; no artifact rerun permitted |

Python is 3.12.12. The runner enforces the limits, preserves input snapshots
and never overwrites an attempt. The compiled source input is the already
available, source-hash-checked solc 0.8.20 artifact set; no compiler ran here.

The initial artifact run follows seven bodies: `verifyValidatorSignatures`,
`getSignatureMessageHash`, `getValidators`, `updateValidatorSetIndex`, and
ECDSA's referenced `tryRecover`, `recover`, `_throwError`. It records two
loops, four argument bindings, 21 protected state declarations and one
may-write root: `validatorSetIndex` (declaration 292). Guard acceptance and
non-vacuity remain `NOT_ESTABLISHED`. These are precisely the initial-version
observations, not a claim about final-version artifact execution.

Post-run code review found that an internal call's referenced declaration can
be insufficient in the presence of virtual dispatch; the initial checker did
not reject that case. User-defined operator dispatch was also not excluded,
and the certificate cache did not bind the checker version. The final code
rejects those unsupported dispatch mechanisms and includes its source hash in
the certificate identity. Four added controls pass. This hardening invalidates
reuse of the initial certificate; its source snapshots and result are preserved.
No old result is relabeled as a final-version pass. No known Payy vulnerability
or security verdict is inferred from this checker defect.

Controls also cover transitive protected writes, aliases, tuple/delete writes,
mutable reference arguments, missing callees, low-level and external calls,
storage push/pop, selfdestruct, unknown AST constructs, calldata binding,
changed source/AST/argument/policy/bounds/assumptions, forged write sets, and
unbounded loops being only a frame rule. The controls test rejection behavior;
they do not establish signature validity or reachable settlement effects.

## Review recommendation and measurable next task

Authorize **one fresh pinned-artifact check of the hardened checker**, under a
new freeze and output directory: at most 120 seconds/4 GiB, zero network,
compilation, solver, proof or replay work. Freeze the unchanged final code,
policy, assumptions, source and compiled artifacts. Completion is either a
matching current-version frame/use-site certificate or an explicit UNKNOWN
with the failing condition; do not retry or weaken exclusions after a failure.
No new policy assumption or narrower validator state family is recommended.

Only after this prerequisite passes, continue to exact message traversal,
registry/token effects and whole-transition rollback, including the retained
validator-state update and the external verifier boundary. That work needs its
own prospective implementation/check limits and still cannot establish D1-03
without actual producer composition, direct joint queries, concrete replay,
non-vacuity and repaired controls. All 28 primary query slots remain unused.
D1-04, D1-06 and held-out review boundaries remain unchanged.

## Files, evidence and preservation

New files are the checker, [synthetic controls](../tests/d1/test_guard_frame.py),
[artifact entrypoint](../scripts/d1_03_guard_frame.py),
[bounded runner](../scripts/d1_03_guard_frame_run.py), task protocol, this report
and [metadata seal](../metadata/d1/d1-03-guard-frame-01.json). README, roadmap
and project checkpoint are prospectively updated after archiving their exact
consumer-audit checkpoint versions. Raw snapshots, both test outputs, the old
artifact certificate and preservation checks remain under the task raw path.
Previous reports, protocols, source, certificates and raw records are checked
against the starting snapshot; the seal records counts and any Git index drift.
No prior evidence is replaced, and no commit, push, held-out evaluation or
external contact is performed.

Final preservation matches all 1,060 prior files, archived living documents,
every attempt input snapshot and the final synthetic-test inputs. Only the
checker and its tests changed after the artifact attempt, as disclosed above.
HEAD is unchanged. The shared index byte hash changed again; cause is not
established and no restoration was attempted. The preservation record carries
both observed hashes; this is not a claim of index-byte preservation.
