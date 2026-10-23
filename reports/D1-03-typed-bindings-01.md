# D1-03 typed bindings 01 — prerequisite complete

Date: 23 October 2026. **Typed-decoding/binding task DONE. D1-03 remains
ACTIVE/UNKNOWN; no primary security query or settlement replay.**

The user authorized the next recommendation from
[extraction gate 01](D1-03-v2-extraction-01.md). The
[new task protocol](../protocols/d1/d1-03-typed-bindings-01.json), frozen at
18:53:17 UTC, requires a pinned source intake, typed fields for all six
recursive calls, source-backed ABI mapping, actual-constraint frame binding
certificates, negative controls and preservation. It permits one archive
(64 MiB, 120 seconds), 90 minutes total, three test and four artifact validation
invocations (120 seconds/4 GiB each), and no installs, compilation, primary
solver queries, new proofs or full replays. All completion criteria for this
bounded prerequisite are met; none substitutes for the remaining D1-03 gates.

## Source intake and implementation

Downloaded [Noir at the pinned revision](https://github.com/noir-lang/noir/tree/60ccd48e18ad8ce50d5ecda9baf813b712145051)
once via codeload. HTTP 200; 22,032,361 compressed bytes, 43,007,631 expanded
regular-file bytes, 3.113 seconds including extraction. Archive SHA-256:
`069a7124742b0b0ae2b65ed333e19a35d49dc1ac7ca75062bbe9be09ba616438`.
No dependency or compiler installation. Archive/extracted source remain ignored.
The [schema provenance manifest](../metadata/d1/noir-typed-schema-01.json)
pins inspected source hashes and locations; the fetcher is
[d1_03_typed_intake.py](../scripts/d1_03_typed_intake.py).

Pinned source establishes the separate recursive-call vector fields, legacy
bincode/serde order, gzip/base64 wrapping, field serialization and ordered ABI
flattening into witnesses starting at zero. Source definitions are reviewed
implementation inputs; they are not a new cryptographic soundness proof.

New implementation:

- [Binary decoder](../src/bindcheck_d1/frontends/acir_binary_v1.py): reads the
  supported actual serialized ACIR, including opcode byte ranges, assertions,
  memory, range checks, recursive/Poseidon calls and structural Brillig hints.
  It rejects unsupported variants, wrong versions, malformed/truncated or
  noncanonical encodings, oversized collections and trailing bytes. It does
  not use a magic public-input offset or drop unknown opcodes.
- [Binding certificate generator](../src/bindcheck_d1/frontends/acir_bindings_v1.py):
  recovers ABI paths, associates frames by verification-key witness identities,
  and constructs explicit linear combinations of decoded `AssertZero`
  polynomials. The two zero-test constraints prove the selector's active/padding
  interpretation over the field. Proof/message selection, key hash and enabled
  recursion are then checked. Equal contents are never deduplicated.
- [Separate certificate checker](../src/bindcheck_d1/frontends/binding_certificate_check_v1.py):
  independently accumulates polynomial terms from the cited original opcodes
  and compares them with each claimed equality. It shares no search procedure.
  This is not independent human annotation or a formally verified checker.

Old frontend files, protocols and reports remain unchanged. These are
separately versioned modules; previous gate results are not relabeled.

## Observed results

All four program artifacts decode completely within the supported structural
subset. Their typed ABI declarations match the pinned allocation rule. All six
recursive calls have 115 verification-key fields, 508 proof fields, 1,005
public inputs and proof type 7. Their predicates are proved equal to one.
Flattening their *decoded* fields also reproduces the saved printer's boundary
witness sequence; no printer offset supplies the decoded structure.

| Artifact | Serialized assertions | Saved non-transformed assertions | Checked equalities |
|---|---:|---:|---:|
| A agg_agg | 79,484 | 71,491 | 3,264 |
| B agg_agg | 81,487 | 73,492 | 3,264 |
| A agg_final | 4 | 4 | 1,630 |
| B agg_final | 4 | 4 | 1,630 |

**Unexpected observation:** the serialized producer relation includes additional
compiler-transformed assertions. The printout is explicitly non-transformed.
This task uses the serialized assertions for certificates; it does not assert
identity of the two full relations or reinterpret old T22 results.

The separate checker accepts **9,788 equality certificates**. Of these, 3,042
use at least one actual assertion; 6,746 are direct witness-identity equalities.
Six certificates combine more than one assertion. These counts are provenance
accounting, not independent security obligations or solved primary goals.
The frame selectors have certificates for `root*selector=0` and
`root*inverse+selector-1=0`: zero root forces selector one, and nonzero root
forces selector zero. Brillig hint behavior is not trusted for this deduction.

**27 tests pass**, including a pinned upstream serialization golden fixture,
every truncation of that fixture, unsupported upstream opcodes/foreign calls,
wrong format/field/count boundaries, interleaved/nested ABI mapping, wrong
declaration identities, changed keys/padding vectors/proof types, disabled
recursion, missing constraints, circular equations and tampered certificates.
Reordering recursive calls preserves frame identity. Tests are synthetic or
upstream serialization controls, not new Payy proof/consumer executions.

## Commands, attempts and raw evidence

```sh
timeout 120s python3 scripts/d1_03_typed_intake.py
python3 scripts/d1_03_typed_run.py artifacts   # 01: decode and ABI mapping
python3 scripts/d1_03_typed_run.py artifacts   # 02: add binding certificates
python3 scripts/d1_03_typed_run.py tests       # 01: initial controls
python3 scripts/d1_03_typed_run.py tests       # 02: add proof-type rejection
python3 scripts/d1_03_typed_run.py artifacts   # 03: final checked bindings
```

All child exits are 0. Artifact runs take 4.527, 8.392 and 7.934 seconds;
the final test invocation takes 0.167 seconds including startup. The second
test/third artifact runs follow the explicit added proof-type guard, rather
than retrying a failed primary result. No timeouts or failed experimental
attempts occurred. One artifact and one test allowance remain unused; they
are not transferred into a tuning budget.

The [bounded runner](../scripts/d1_03_typed_run.py) archives each executable
input version before running and records exact argv, environment, Python
3.12.12, wall/address-space caps, stdout/stderr and exit status. Raw evidence is
under `results/raw/D1-03/typed-bindings-01/`; final certificates and summaries
are in `artifacts-03/outputs/`. The
[execution/evidence manifest](../metadata/d1/d1-03-typed-bindings-01.json)
binds outputs, source identities, report and preservation checks.

Starting HEAD is `5f10de21e40f8cf9185dd927ae4d6bbfcffd05ed`, with a clean
working tree before task files. This differs from the previous report's
historical HEAD; no old index is restored. Prior files/raw evidence are checked
against the new intake snapshot. Exact living checkpoint documents are archived
before prospective updates. No commit, push, contact or held-out work occurs.

## Claim boundary and next task

These certificates are local implications of actual constraints. They do not
prove non-vacuity, complete constraint/bytecode equivalence, recursive proof
soundness, artifact/key correspondence, actual seed realizability, the
producer's outer-message relation, or a consumer transition. No authorization
or coverage security verdict is assigned. D1-03 remains incomplete/UNKNOWN;
D1-04 remains blocked. All 28 primary query slots remain unused.

The typed-binding prerequisite now permits the **next task: faithful consumer
transition extraction**, retaining v2's policy and state restrictions. Extract
guards, decoding, state updates, token-call outcomes and rollback semantics
from the pinned consumer AST; validate negative/legitimate controls and expose
unsupported paths. Only after the full joint relation, non-vacuity and replay
prerequisites are ready may the frozen primary matrix run. Routine implementation
within this scope remains authorized; no fresh policy or resource expansion is
implied by this task's success.
