# D1-03 consumer transition boundary 01

Date: 23 October 2026. **Transitive coverage audit DONE; consumer semantic
extraction INCOMPLETE/UNKNOWN. D1-03 remains ACTIVE; D1-04 remains WAITING.**

## Objective, prerequisites and limits

[Typed bindings 01](D1-03-typed-bindings-01.md) discharged the preceding
typed producer/decoder prerequisite. Continue within the authorized v2 scope
by identifying the complete consumer transition boundary, including modifiers,
transitive helper/library calls, guards, loops, storage writes and external
calls. A function-name list or a passing component test is not an implemented
transition relation.

The [task protocol](../protocols/d1/d1-03-consumer-boundary-01.json) was frozen
at 19:11:18 UTC. Completion criteria: transitive located AST inventory, honest
coverage decision, synthetic controls, one actual-artifact audit, preservation
and report/checkpoint. Limits: 45 minutes, two synthetic test invocations and
one actual audit, each 120 seconds/4 GiB; zero network, compilations, solver
queries, proofs or full replays. All audit criteria are met. The larger
faithful-transition implementation criterion remains unmet.

## Implementation and actual source facts

The [new frontend](../src/bindcheck_d1/frontends/consumer_boundary_v1.py)
loads the already-built solc 0.8.20 artifacts, checks each source's Keccak-256
against compiler metadata, rejects conflicting AST identities, and follows
declaration references rather than matching function names. It includes
modifiers and the actually referenced library overloads. Unresolved calls
are rejected. Writes through storage aliases are explicitly distinguished
from direct state-variable writes; they are not presumed harmless.

The actual `verifyRollup` closure contains **19 function/modifier bodies**,
including `onlyProver`, validator-set selection, signature recovery and
message processing. Located evidence records 18 defined-function call sites,
one modifier, one external verifier interface call and one low-level token
call, alongside builtins, ABI operations, casts and error/event constructors.
The report does not classify those located categories as implemented semantics.

Three loops are reachable:

| Function | Extracted condition | Current modeling boundary |
|---|---|---|
| `verifyAllMessages` | `i < end` | N=8/1000 message bound is declared in v2 |
| `verifyValidatorSignatures` | `i < signatures.length` | No numeric signature-array bound or implemented checked summary |
| `updateValidatorSetIndex` | `i < validatorSets.length` | No numeric validator-set-array bound or implemented checked summary |

The audit also locates direct writes to `rootHash`, `blockHeight`,
`validatorSetIndex`, `mints[hash].spent` and `substitutedBurns[...]` (the last
is on the substitution branch excluded by the v2 pre-state). Source order
shows validator processing before message effects, verifier acceptance after
message effects, and a later height guard. A rejected later check must roll
back all earlier effects, including validator-state updates. The old token
component tests do not establish this whole transition.

Four Keccak calls and one `ecrecover` are in the reachable closure. The
referenced ECDSA implementation contains failure/revert paths. Locating those
calls is not a proof of their semantics, a license to assume signature
acceptance, or a claim that cryptographic operations are inherently impossible
to abstract. The external verifier/token behaviors still require the declared
A1/A5 boundaries and concrete replay where claimed.

## Gate decision and concrete recommendation

**UNKNOWN: full consumer transition semantics are not yet implemented.**
The numeric message bound and owned-prover/validator capability do not supply
a numeric bound on signature or validator-set arrays. The gate has no
non-vacuity result, primary SAT/UNSAT result or full replay. This is an
implementation/coverage finding, not a newly discovered Payy vulnerability
or a failed repaired-case experiment.

Do not silently fix one validator, one signature or one set and retain v2's
claim over its broader admitted family. Such a choice would be a prospective
scope restriction requiring the user's stipulated review. Also do not assume
that signature checks succeed or drop caller/state guards merely because the
replay environment is owned.

**Recommended next task: preservation-checked consumer guard summaries,
followed by the exact message-effect transition.** Retain v2's state family.
Check, from the transitive AST, which guard helpers can modify protected state
or values used by message processing, including storage aliases and external
calls. A proposed conservative summary may allow extra guard outcomes only
after a checked implication/frame argument establishes preservation of all
admitted successful concrete effects; resulting SAT candidates still require
full original-consumer replay. Pure-call classification by itself is insufficient.

Measurable completion: explicit summary preconditions and use-site checks;
no unaccounted protected writes, aliases or callbacks; tests that inserting a
protected write or changing a calldata dependency invalidates summary reuse;
and exact message traversal, mint/burn effects and whole-transition rollback
in the executable boundary model. If that cannot be justified within existing
assumptions, stop for review of a separately versioned state restriction or
additional budget. No new restriction or cryptographic assumption is approved
or implemented by this report. This remains D1-03 semantic fidelity work,
not the later consumer-directed optimization experiment.

## Checks, attempts and raw evidence

```sh
python3 scripts/d1_03_consumer_boundary_run.py
python3 scripts/d1_03_consumer_boundary_run.py --resume-after-test-failure
```

The first test invocation exits **1**: five of nine tests error before the
intended check because the synthetic node factory's parameter `kind` collides
with Solidity AST's `kind` field. No actual artifact audit runs on that attempt.
Its source snapshots, freeze and error log are preserved. Rename the test
factory parameter to `node_type`; no frontend semantics or control is weakened.

The second and final permitted test invocation exits **0**, **9/9 pass**,
0.118 seconds including startup. Controls cover transitive functions/modifiers,
missing callees, overload resolution, storage aliases, nested mapping writes,
external-interface incompleteness, loops/builtins and AST identity collisions.
The single actual-artifact audit exits **0**, 0.172 seconds: the audit completed,
while its explicit security status is UNKNOWN and
`complete_transition_implemented` is false. No experimental retry beyond the
two frozen synthetic slots occurred; no actual security experiment was run.

The [runner](../scripts/d1_03_consumer_boundary_run.py) preserves exact commands,
input hashes, Python 3.12.12, caps, stdout/stderr and child statuses. The
[audit entrypoint](../scripts/d1_03_consumer_boundary.py) stores the complete
located transition inventory and artifact identities under
`results/raw/D1-03/consumer-boundary-01/artifacts/`. The tracked
[metadata manifest](../metadata/d1/d1-03-consumer-boundary-01.json) binds the
report, code, test and raw evidence. The entry-call list is an AST preorder
inventory, not a concrete execution trace or a path-feasibility proof.

## Preservation and remaining work

Prior reports, protocol freezes, typed-binding certificates, code and raw logs
are checked against this task's starting snapshot. Exact living documents
from the typed-binding checkpoint are archived before prospective updates.
No historical report or verdict is rewritten. No compilation, proof, solver,
settlement replay, held-out work, commit, push or external contact occurs.

All 28 primary slots remain unused. The approved source intake and typed
bindings are complete; full producer/consumer composition, consumer semantic
preservation, honest non-vacuity, repaired verification and concrete candidate
replay remain unresolved. Baselines cannot begin until those D1-03 gates pass.

Preservation checks match all 1,027 prior files, both attempt freezes and the
archived living documents. HEAD is unchanged. The shared index byte hash
changed during the task; its cause is unestablished. This task used read-only
Git commands with optional locks disabled and did not restore or mutate the
index. Both observed hashes and final index bytes are preserved in raw evidence.
