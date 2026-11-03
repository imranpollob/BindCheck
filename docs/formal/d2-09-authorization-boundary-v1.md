# D2-09 bounded authorization-boundary interface (version 1)

Status: development specification for an `UNREVIEWED_DEVELOPMENT_FIXTURE`.
It does not amend the D2-07 `INCONCLUSIVE` Gate A decision, supply a reviewed
policy, authorize scored execution, or state a result about a project target.

## Purpose and common interpretation

The prototype asks a narrow implication question for each protected effect
occurrence:

> On every bounded relying assignment covered by the declared abstraction, do
> supported producer guarantees supply the exact object/context and field
> relation required by one policy permission for this effect?

Full BindCheck and strong simple composition receive the same canonical
`BoundaryInput` bytes. There is no arm-specific enrichment, default policy,
name matching, or hidden relation. The equal-arm envelope records the common
input, policy, and fact-set SHA-256 values and compares semantic outputs after
removing only the arm name. This is an interface-parity control, not a
comparative experiment.

The implementation is
`bindcheck_d1.core.authorization_boundary_v1`. Its public schemas are:

- `bindcheck.poe-policy/v1`;
- `bindcheck.authorization-obligation/v1`;
- `bindcheck.protected-effect/v1`;
- `bindcheck.authorization-boundary-input/v1`;
- `bindcheck.authorization-boundary-result/v1`; and
- `bindcheck.authorization-boundary-equal-input-arms/v1`.

## Supported fragment

Version 1 supports a finite-domain, single-transition, occurrence-level
fragment. Each obligation has exactly one protected effect and one-to-one
multiplicity. A permission, obligation, and effect all name the following
fields: action, asset, quantity, beneficiary, domain, and state version. Terms
are either a declared finite-domain variable or a JSON constant. Conditions
are `ALWAYS`, `NEVER`, `UNKNOWN`, or a bounded predicate composed from equality,
inequality, ordered comparison, conjunction, disjunction, and negation.

The query declares every quantified variable, its finite domain, the subset
controlled by the attacker, fixed authenticated context, and a hard assignment
cap. Enumeration is exhaustive only inside those declared finite domains. The
prototype does not model splitting, aggregation, deferral, temporal/liveness
properties, unbounded history, unbounded integers, field/integer conversion,
hash or proof-system soundness, external calls, or two-sided alternative
authorization. Such a construct is `UNKNOWN`; it is never silently treated as
authorized.

An empty obligation set, an inactive/vacuous relying path, an exceeded query
cap, an unsupported fact, or an unknown condition is not establishment.

## Object/context chain and provenance

All security-bearing identities use the Step 8 opaque reference
`bindcheck.compiler-object-context-identity-ref/v1`, with exactly `schema`,
`semantic_hash`, and `canonical_bytes_sha256`. Display names, source paths,
line numbers, and spans remain provenance only.

The fact chain has one convention:

1. A `producer_guarantee` subject is the required authorizing object and
   context. Its object is the exact producer/public value identity whose
   relation is stated by the fact condition.
2. A `consumer_used` subject is the protected effect occurrence. Its object is
   that same producer/public value identity.
3. The producer subject must equal the obligation authorization reference; the
   reliance subject must equal both the obligation and effect protected-effect
   reference; and the producer and reliance objects must be identical opaque
   references.

A broken link yields `UNKNOWN` with a stable reason. It cannot be repaired by
equal spelling, a display role, a source coordinate, or a permission that
happens to match the remaining fields. Adversarial tests cover the same display
name with a different logical object, the same logical object in a different
context, and a swapped protected-effect reference.

The serialized Step 8 bundle remains hash replayable. Each result preserves
fact kind, quantifier, approximation, derivation class, support state, source
reason, and the reason that a fact is or is not eligible for its role.

## Policy, obligations, and effects

`PolicyRecord` is separate from implementation facts. A policy contains one or
more permissions, an explicit review status, source hashes, and optional
author/reviewer references. `HUMAN_REVIEWED` is accepted only when an author or
adopter and a distinct reviewer are both recorded. This prototype supplies no
such humans. Its only policy has the literal status
`UNREVIEWED_DEVELOPMENT_FIXTURE`; the author and reviewer fields are absent.

An absent policy, the fixture policy, a missing role, or a non-distinct role
fails closed. Mechanical queries may still exercise an explicitly labeled
fixture policy, but every effective state remains `UNKNOWN`, evidence remains
E0, `score_eligible` remains false, and `research_verdict` remains `UNKNOWN`.
An AI agent is not a human policy author, adopter, reviewer, annotator, or
adjudicator.

An `AuthorizationObligation` identifies its authorizing object/context,
protected effect occurrence, producer and reliance fact IDs, field terms,
activation and discharge conditions, multiplicity, and assumptions. A
`ProtectedEffect` identifies the occurrence, field terms, relying path,
source-fact IDs, and any independently justified authorization mechanism. The
prototype refuses to infer the other side of an alternative-authorization
claim; an unreviewed alternative makes the obligation `UNKNOWN`.

## Fact strength and approximation direction

The following table states the only admissible discharge/use roles.

| Role | Quantifier | Approximation | Derivation | Support | Meaning |
| --- | --- | --- | --- | --- | --- |
| Producer discharge | `MUST` | `EXACT` | `DERIVED` | `SUPPORTED` | The conditional relation is asserted on every covered producer behavior. |
| Consumer reliance coverage | `MAY` | `EXACT` or `OVER_APPROXIMATION` | `DERIVED` | `SUPPORTED` | Possible relevant uses are retained. This fact selects relying paths; it does not discharge a MUST obligation. |

`MAY` producer facts, underapproximated producer facts, annotations, assumptions,
unsupported/unknown facts, or unknown conditions cannot discharge a MUST
obligation. An overapproximated reliance summary may introduce extra candidate
paths, which is conservative for finding a possible mismatch; it cannot by
itself establish a producer guarantee. A `NEVER` path does not establish safety
because non-vacuity is absent.

## Conditional bounded check

For every finite assignment `a`, the checker evaluates:

1. all eligible producer conditions;
2. all reliance conditions, the effect path, and obligation activation;
3. the obligation discharge condition; and
4. whether one permission has the exact authorizing identity, protected-effect
   identity, active condition, and equal action/asset/quantity/beneficiary/
   domain/state-version values.

Assignments failing steps 1 or 2 are outside that obligation's relying set. A
nonempty relying set with a failed discharge or no matching permission gives a
bounded mechanical `MISMATCH_CANDIDATE` and preserves one assignment. A
nonempty relying set for which every enumerated assignment matches gives
mechanical `ESTABLISHED` within the declared finite interpretation. Any
insufficient input gives mechanical `UNKNOWN` with reasons. Under the fixture
policy, the effective state is always `UNKNOWN` regardless of mechanical
state.

The three states therefore mean:

- `ESTABLISHED`: the bounded implication held for every nonvacuous relying
  assignment under eligible facts and, outside this fixture phase, a valid
  reviewed policy;
- `MISMATCH_CANDIDATE`: bounded enumeration found an assignment that reaches a
  protected effect without a matching permission; it still requires supported
  concrete validation before any research verdict; and
- `UNKNOWN`: policy, extraction, identity correspondence, approximation,
  non-vacuity, or resource evidence is insufficient.

These states are not the research-contract verdicts `VIOLATION`,
`VERIFIED_WITHIN_SCOPE`, and `UNKNOWN`. The prototype never emits the first two.

## The `p = private_x` counterexample

The synthetic counterexample fixes the authorized quantity to zero while the
attacker chooses `p` and `private_x` independently from `{0, 1}`. The producer
relation is `p = private_x`; the consumer uses `p` as the transfer quantity;
and the fixture policy permits only the fixed authorized quantity. The
assignment `p = 1`, `private_x = 1`, `authorized_x = 0` satisfies the producer
relation and reaches the effect while failing the permission. Equality with an
attacker-adjustable private object therefore does not, by itself, supply the
required authorization relation.

The paired control changes only the producer relation to
`p = authorized_x`. It is a mechanical known-answer control over the same
finite domains, not evidence about a real producer, consumer, compiler, or
reviewed policy.

Additional negative controls force `UNKNOWN` for an annotation-only producer,
a `MAY` producer, an underapproximate producer, unknown extraction support, an
unsupported extraction condition, an inactive path, and an unreviewed
alternative authorization. An object/context
mismatch control preserves exact field values while changing the authorizing
context, so role or field equality cannot substitute for identity.

## Limited implementation obligation, not a soundness theorem

For the supported finite fragment, `evaluate_boundary` is intended to satisfy
this implementation obligation: if validation succeeds, all fact-chain links
match exact opaque identities, every producer fact is MUST/EXACT/DERIVED/
SUPPORTED, every reliance fact is a conservative MAY summary, the assignment
space does not exceed the declared cap, and the relying set is nonempty, then
its mechanical state agrees with exhaustive evaluation of the encoded
permission implication over that finite assignment space.

Unit tests and recorded queries exercise that obligation but do not prove it.
No claim is made about compiler extraction fidelity, concrete-program
coverage, cryptographic soundness, policy correctness, real execution,
generalization, or comparative advantage.

## Reproduction and evidence boundary

The versioned protocol is
`protocols/d2/d2-09-authorization-boundary-v1.json`. The runner
`scripts/d2_step9_authorization_boundary.py` validates all bound hashes,
constructs only declared fixtures, records exact common-input hashes and query
counts, and refuses to overwrite `results/raw/D2-09/`. It does not dispatch the
integrated analyzer, a scored baseline, a proof system, a replay, a network
request, or reserved data.

Human researcher time is not inferred from AI-agent execution. The manifest
counts setup and specification items, records observed machine wall time, and
leaves researcher-day consumption unresolved without a human time log. This
is required rather than pretending that automated work supplies an independent
human role or a human-effort measurement.
