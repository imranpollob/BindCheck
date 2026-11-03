# D2 Step 8 compiler-backed object/context identity

Status: authorized mechanical prototype under
`UNREVIEWED_DEVELOPMENT_FIXTURE`

Research verdict: `UNKNOWN`

## Boundary

This prototype separates a logical object/context identity from the compiler
and source evidence used to support it. It does not define or evaluate P/O/E
authorization, emit a security warning, score an arm, or prove semantic
equivalence. Its only inputs are exposed D1P-42 construction artifacts and the
four bounded Step 6a transformations.

The implementation is
`bindcheck_d1.roles.compiler_identity_v1`. It exports:

- `ObjectIdentity` and `ContextIdentity`;
- `CompilerProvenance` and `IdentityRecord`;
- typed `IdentityFact` records;
- `MappingEntry` and `MappingCertificate`; and
- `IdentityBundle`, `identity_reference`, and `validate_bundle`.

## Hash domains

An identity's canonical bytes contain only:

```text
object = {
  kind, logical_slot, representation, state_scope,
  encoding, value_type, attributes
}
context = {
  kind, domain, deployment, state_version,
  actor, epoch, attributes
}
```

`canonical_bytes_sha256` hashes this canonical JSON. `semantic_hash` is a
short, typed presentation of that digest. The exact opaque reference handed to
Step 9 is:

```json
{
  "schema": "bindcheck.compiler-object-context-identity-ref/v1",
  "semantic_hash": "OCI-...",
  "canonical_bytes_sha256": "..."
}
```

Compiler artifact hashes, compiler/language/version, artifact schema, AST node
or public ABI index, source hash/span, mapping ID, derivation class,
assumptions, annotations, support/reason, and display hints live in a separately
hashed provenance record. Surface identifier spelling, source path/line,
display label, warning text/ordinal, physical ABI index, and artifact hash
cannot affect the semantic identity hash.

This split has an important limit: a stable semantic hash is only as meaningful
as the explicit logical-slot and context construction. It is not proof that an
annotation correctly captures protocol meaning.

## Facts and provenance

`IdentityFact` provides the Step 10 extraction boundary:

- stable `fact_id` and `fact_kind`;
- subject and optional object exact opaque identity references (schema,
  semantic hash, and full canonical-bytes digest);
- `MUST` or `MAY` quantification;
- a structured condition;
- `EXACT`, over-approximate, under-approximate, or unknown direction;
- `DERIVED`, `ANNOTATED`, `ASSUMED`, or `UNKNOWN` derivation;
- independent support/reason;
- compiler provenance, parent fact, assumption, annotation, and mapping
  references.

The bundle validator reconstructs every identity and fact, replays every hash,
rejects duplicate fact IDs, and requires an ordinary `parent_fact_id` to resolve
inside the same bundle. A deliberately external parent must use the explicit
`external:` namespace. Fact provenance must resolve to an identity provenance
hash in the bundle or the same external namespace. Assumption, annotation, and
mapping references are resolved by the run's separate hash-bound input
inventory; the bundle declares this resolution boundary instead of treating an
opaque string as self-authenticating.

Step 8 permits canonical structured extraction conditions with a mandatory
`kind`, but assigns them no authorization meaning. Step 9 is intentionally
stricter: its P/O/E boundary accepts only its versioned condition vocabulary
(`ALWAYS`, `NEVER`, `UNKNOWN`, or `PREDICATE`) and otherwise remains
`UNKNOWN`.

The D1P-42 runner emits two facts per logical public word:

1. a compiler-derived exact public ABI position; and
2. an annotated logical-slot correspondence conditioned on the mapping
   certificate.

The logical slots are explicitly frozen as:

```text
d1p42.batch.element[0]
d1p42.batch.element[1]
d1p42.batch.element[2]
d1p42.batch.element[3]
d1p42.batch.extent
```

They are `ANNOTATION:D1P42_LOGICAL_SLOT_MAP_V1`, not independently reviewed
policy and not an automatic semantic recovery result.

The preserved Noir artifact provides compiler version, program artifact hash,
public ABI positions and types, bytecode, and debug/file-map material. It does
not expose a stable SSA identity used here, so the producer record states that
limitation and anchors each word at the compiled public ABI index. The solc AST
provides the checked public-input `IndexAccess` node and source span. The
explicit mapping certificate carries per-word interpretation.

## Mapping certificates

Each mapping certificate records source and target bundle IDs, one entry per
logical slot, exact opaque source/target identity refs, source/target physical
ABI indices, hash-bound mapping-source refs, and evidence hashes. Properties
are replayed rather than asserted:

- total over the declared source identities;
- injective;
- surjective over the declared target identities;
- order-preserving; and
- semantic-identity-preserving.

Totality additionally requires unique source identities and ABI indices;
injectivity and surjectivity require unique target identities and ABI indices.
Serialized replay binds the entry sets exhaustively to both referenced bundles
and checks each entry's compiler ABI index. Facts reference the preserved Step
6 mapping source through the external registry. The certificate then binds
that source reference to both bundle IDs without creating a bundle/certificate
hash cycle.

Identifier renaming, helper extraction, and equality-operand commutation are
expected to preserve physical order. Matched public-input reordering is
expected to be non-order-preserving while retaining semantic identity through
its explicit bijection.

These are bounded mapping controls. Their Step 6a source arguments, builds,
two producer execution vectors, consumer algebra vectors, ABI correspondence,
and semantic warning-ID checks remain the underlying evidence. Neither Step 6a
nor Step 8 supplies a formal or general equivalence proof.

## Negative fixtures

Five deterministic rows challenge the hash boundary:

| ID | Expected mechanical outcome |
|---|---|
| `NEG-SAME-NAME-DIFFERENT-OBJECT` | mismatch despite equal display name |
| `NEG-SAME-OBJECT-DIFFERENT-CONTEXT` | mismatch despite equal object structure |
| `NEG-OBJECT-CONTEXT-CROSS-SWAP` | mismatch after cross-pairing objects and contexts |
| `CONTROL-MATCHED-REORDER` | same semantic identities through explicit non-order-preserving map |
| `CONTROL-DISPLAY-NAME-IGNORED` | match after display-name-only change |

The negatives are synthetic interface checks. A mismatch means only that the
canonical identity bytes differ; it is not a policy violation.

## Name-dependent legacy path

The historical D1P-43 `R-ROLE` rule inferred roles and identities from tokens
such as `root`, `local`, `recipient`, and `amount`. That implementation remains
as `_analyze_legacy_name_roles` for auditability. It is quarantined with status
`ANNOTATION_ONLY_QUARANTINED`.

The public `analyze_role_binding` entry point:

1. returns the structured `COMPILER_BACKED_IDENTITY_REQUIRED` unknown condition
   when no identity bundle is supplied;
2. validates a supplied bundle; and
3. returns `AUTHORIZATION_BOUNDARY_CHECK_REQUIRED_STEP9` even for a valid
   bundle because identity alone is not a reviewed authorization policy.

An AST audit requires zero symbol references or calls from the public entry point to
`canonical_role`, `semantic_identity`, or the quarantined legacy analyzer.
Legacy calls are counted and retained as annotation-only debt. Historical
sealed D1/D2 warnings keep their original interpretation and are not rescored.

## Step 9 and Step 10 interface

Step 9's `bindcheck_d1.core.authorization_boundary_v1` consumes the exact
opaque reference above in identity facts plus separate provenance/support
records. Its effective state remains `UNKNOWN` for
`UNREVIEWED_DEVELOPMENT_FIXTURE`; display labels do not enter P/O/E matching.

Step 10 consumes separate object/context identities, typed facts and mapping
certificates. It treats the old role labels and semantic tokens as annotations.
Unavailable compiler metadata stays explicit instead of being synthesized.

## Claim limits

- No policy author/adopter or distinct reviewer is supplied here.
- No P/O/E policy correctness or authorization result is claimed.
- No analyzer, proof system, solver, baseline, or scorer is run.
- The evidence foundation makes seven read-only Git metadata subprocess calls
  while preparing the run manifest and content seal; these are infrastructure,
  not analyzer/compiler/policy/proof/score execution.
- No fixture is a safe negative, held-out case, or transfer result.
- No general compiler identity, stable SSA, soundness, completeness, or
  equivalence theorem is claimed.
- The Step 7 Gate A decision remains `INCONCLUSIVE`; research verdict remains
  `UNKNOWN`.
