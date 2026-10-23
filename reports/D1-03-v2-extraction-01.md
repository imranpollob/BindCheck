# D1-03 v2 extraction gate 01 — incomplete, UNKNOWN

Date: 23 October 2026. **Core/inventory prototype implemented and bounded
gate assessed; semantic extraction INCOMPLETE. D1-03 remains ACTIVE/UNKNOWN.
D1-04 remains WAITING.** This is not a repaired-case failure or a solver result;
neither primary query nor replay was attempted.

## Objective and frozen execution boundary

Following the authorized [v2 design](D1-03-v2-design.md), implement the first
semantic data structures and establish actual artifact prerequisites before
spending primary query slots. The [extraction protocol](../protocols/d1/d1-03-v2-extraction-01.json)
was frozen at 17:37:04 UTC, before the new code's test or artifact-gate run.
Completion criteria: separate domains/provenance/P/O; located producer/consumer
facts; checked logical-frame/recursive bindings; meaningful regressions and
an honest gate decision; preserved evidence/report/checkpoint.

Limits: 60 minutes; zero network requests, new compilations, solver queries,
proofs or full rollup replays; at most two synthetic test invocations and one
actual-artifact gate invocation, each at 120 seconds and 4 GiB address space.
Only one synthetic invocation was used. The required semantic bindings were
not established, so those completion criteria remain unmet. The gate report
is complete; the extraction implementation is not.

## Implemented and checked

- [Domain/evidence structures](../src/bindcheck_d1/model_v2.py): distinguish
  field elements, EVM words, exact recipient decoding, artifact hashes,
  locations, implementation versus policy provenance, occurrence identities,
  separate permissions/obligations, and UNKNOWN-only extraction results.
- [Concrete semantics](../src/bindcheck_d1/policy_v2.py): count-based injective
  matching for equality keys and sequential standard-token updates. Trace
  assessment has no universal-verdict field. Reverted traces and unsupported
  deferral remain explicit. This is not extracted producer/consumer semantics.
- [ACIR frontend](../src/bindcheck_d1/frontends/acir_v2.py): preserve all
  opcode text, declarations, source line locations and unconstrained bytecode;
  check compiler identity and ABI/declaration counts; reject unknown line
  formats and extra constrained functions. Do not infer ABI witness bindings
  from matching counts or typed recursion from a flat argument list.
- [Solidity frontend](../src/bindcheck_d1/frontends/solidity_v2.py): verify
  source Keccak-256 against compiler metadata, locate eight message-path
  functions/index accesses, and check by AST declaration identity that the
  scanner and verifier receive the same calldata parameter, with scanner
  offset 3. This does not interpret all guards, state updates or call effects.

The [23 synthetic regressions](../tests/d1/test_v2_core.py) all pass. They
cover canonicality, exact address aliases, optional versus mandatory policy,
occurrence multiplicity, duplicate identities, wrong asset/recipient,
rollback/deferral classification, label-input rejection, supply invariants,
sequential transfer behavior, unknown opcodes/functions, absent typed recursion,
ABI mismatch, compiler pin, source tampering and wrong forwarding references.

## Actual artifact gate: UNKNOWN

All twelve inherited compilation-file hashes match the setup record.
The new input freeze binds the four actual N=1000 ACIR/program pairs and
the consumer artifact built during the design task. No compilation was repeated.

| Actual artifact | ASSERT records | Recursive calls | Gate |
|---|---:|---:|---|
| A agg_agg | 71,491 | 2 | Typed recursion/frame binding unresolved |
| B agg_agg | 73,492 | 2 | Typed recursion/frame binding unresolved |
| A agg_final | 4 | 1 | Typed recursion/public-input binding unresolved |
| B agg_final | 4 | 1 | Typed recursion/public-input binding unresolved |
| RollupV1 solc AST | n/a | n/a | Source/forwarding facts extracted; transition semantics unresolved |

The pinned compiler's printed recursive calls contain one flattened `inputs`
list. The historical `scripts/t22_specs/payy_agg_agg.json` supplies
`recursion_public_inputs_start: 623` as an analyst assumption. The new frontend
does **not** upgrade that supplied offset into an extracted fact. The program
ABI also lacks an explicit `param_witnesses` map; matching type widths and
declaration counts alone does not establish path-to-witness identity.

The compressed program bytecode is present, but this frontend does not yet
decode its typed recursive opcode schema. No pinned compiler serializer/layout
source is included in this gate's frozen inputs. Padding complicates the next
binding further: logical active-frame vectors and actual recursive arguments
are not interchangeable, and equal vector contents do not establish identity.

Reported reason codes are `RECURSION_LAYOUT_UNESTABLISHED`,
`ABI_WITNESS_BINDING_UNESTABLISHED`, `LOGICAL_FRAME_BINDING_UNESTABLISHED`,
`PRODUCER_RELATION_SEMANTICS_NOT_EXTRACTED` and
`CONSUMER_TRANSITION_SEMANTICS_NOT_EXTRACTED`.
The last two are explicit implementation gaps, not discoveries that Payy's
semantics are inherently unextractable. The inventory frontend currently
cannot issue a passed joint gate; it is not a completed analyzer whose
verification attempt happened to time out.

No conclusion is drawn about SAT/UNSAT, honest non-vacuity, the repaired
control or replay. No N=8 experiment was repeated. All 28 prospective primary
slots remain unused. The D1-03 completion gate is unresolved; D1-04 cannot
begin. No labels, reduced diagnostics or component tests replace that gate.

## Exact commands, outcomes and evidence

```sh
python3 scripts/d1_03_v2_extraction_run.py
```

The [runner](../scripts/d1_03_v2_extraction_run.py) records its pre-execution
hash freeze, tool identity and exact child argv/environment. Child commands:

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/d1 -p test_v2_core.py -v
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 scripts/d1_03_v2_extraction_gate.py --output results/raw/D1-03/v2-extraction-01/artifacts
```

Tests exit **0**, 23/23 pass, 0.171 seconds including process startup.
Artifact gate exits **2**, deliberately signaling the unresolved prerequisite,
in 2.871 seconds; no timeout or unexpected exception. The runner exits 0 to
indicate that both results were recorded; this is not a passing extraction
gate. Python 3.12.12 and the installed PyCryptodome version are pinned in
`execution-freeze.json`; the solc/Noir artifact versions retain the design
and inherited setup identities. No installation occurred.

Raw evidence: `results/raw/D1-03/v2-extraction-01/`, including full opcode
inventories, consumer source locations, summary, stdout/stderr, hashes and
preservation audit. [Tracked metadata](../metadata/d1/d1-03-v2-extraction-01.json)
binds the artifacts. Existing reports, protocols and raw logs match their
starting hashes. Exact design-checkpoint living documents were archived before
the prospective README/roadmap/project-status updates. No commits, pushes,
external contact or held-out work occurred.

The first final preservation audit exited 1 because the shared Git index's
bytes changed during this task: SHA-256 `725e3ac2…` at the start became
`64ba0996…`. No prior file, executable input or archived checkpoint mismatched.
Read-only inspection shows unchanged HEAD and an empty staged diff, as at
the start; it does not establish the cause of the index-byte change. The copy
shares its index with the sibling worktree. No index write was requested by
this task, and no restoration was attempted. Preserve the observed index copy,
full hashes, stat and commands in `index-drift.json` and
`observed-shared-index.bin`; index **byte preservation is not claimed** for
this task. The subsequent audit records this exception rather than masking it.

## Review recommendation

**Next task: typed ACIR artifact decoding and binding certificates.** First
obtain the serializer/opcode and ABI allocation definitions at the already
pinned Noir revision `60ccd48e18ad8ce50d5ecda9baf813b712145051`; then decode
the actual program bytecode and check logical-frame activation/certification
against its constraints. Do not add a trusted magic offset or hand-assert
the desired producer/output relation. Keep the existing primary-query limits.

Concrete proposed intake budget: one pinned compiler-source archive, at most
64 MiB and 120 seconds; no toolchain installation, new proof or solver run.
Archive exact bytes/checksum and inspected source locations. This source intake
exceeds this task's frozen zero-network budget, so it is proposed for review
under the user's resource-change stop rule, not silently executed. It does
not require a new research direction or weakened policy.

Measurable continuation criterion: recover typed verification-key/proof/public
input fields for all six recursive calls across the four compiled artifacts;
map ABI fields to witnesses with pinned compiler provenance; validate logical
active/padding-frame bindings; reject changed layouts or mappings in negative
controls. Only then proceed to full transition extraction and primary-query
generation. This is a necessary next prerequisite, not a promise that it will
finish D1-03 or establish a repaired-case guarantee.
