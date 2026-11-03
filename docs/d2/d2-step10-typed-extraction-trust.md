# D2 Step 10 typed extraction trust

Status: bounded prototype, construction and regression evidence only  
Fixture class: `UNREVIEWED_DEVELOPMENT_FIXTURE`  
Research verdict: `UNKNOWN`  
Scoring: prohibited

## Purpose

Step 10 provides a typed adapter between the existing static/integrated
analysis records and the frozen Step 8 object/context identity plus Step 9
policy/obligation/effect interfaces. It does not alter the analyzer, discover
policy, prove authorization, run a primary case, or rescore Gate A.

The authoritative corrected protocol and exact frozen inputs are in
`protocols/d2/d2-10-typed-extraction-v2.json`. The authoritative raw run is
sealed under `results/raw/D2-10/run-02/`. Protocol v1 and `run-01` are retained
byte-for-byte as a superseded first attempt; they are not result evidence.

## Trust boundary

The adapter preserves three boundaries that the older records did not express
uniformly:

1. Semantic object/context references use the exact Step 8 opaque triple:
   schema, semantic hash, and canonical-bytes SHA-256. Names and source lines
   remain display provenance.
2. Every exported fact records quantifier, structured condition,
   approximation direction, derivation class, support, reason, identity refs,
   provenance refs, and external assumption/annotation/mapping refs.
3. Raw source fields remain in a separately hash-bound observation ledger.
   They are not folded into semantic identity.

The inventory hash covers the augmented identity bundle, exported fact set,
observations, mappings, reference registry, unknowns, unmapped indices, and
claim limits. Validation replays bundle/fact/observation hashes and checks
provenance, parents, mappings, and external-reference declarations.
Version 2 additionally replays exact recursive Step 9 predicate/term shapes,
serialized mapping certificates against their declared IDs, the source hash,
UNKNOWN ledger, unmapped set, summary counts, and completion status.

## Fact semantics

The full sixteen-row inventory is in the protocol and raw
`fact-type-inventory.json`. The important distinctions are:

| input | declared semantics | Step 10 treatment |
|---|---|---|
| compiler object/context identity | exact mapping | exact opaque ref; context swaps change identity |
| proof-enforced occurrence/binding record | may-dependency | conservative evidence only; not an authorization guarantee |
| caller-linked authorization identity | annotation | `producer_binding_candidate`, `MAY`, over-approximation, annotated |
| Brillig witness generation | annotation | never proof-enforced binding |
| dynamic memory dependency | may-dependency | over-approximation/`UNKNOWN`, never “unused” |
| consumer use/effect reachability | annotation over may-reachability | structural use is source evidence; the caller-linked effect identity is an annotated candidate |
| extent relation | conditional guarantee | exact only with a supported antecedent and compiler-backed condition identity |
| role correspondence | annotation | identifier roles cannot become identity or `MUST` facts |
| transformation correspondence | mapping | total/injective/surjective/semantic-identity preserving required |
| policy/manual input | assumption | unresolved or unreviewed inputs fail closed |
| warning/candidate | diagnostic | never an implementation or safety fact |

Most importantly, current static occurrence evidence does not establish the
relational producer guarantee required by Step 9. Step 10 therefore emits
zero `producer_guarantee` facts. Even an otherwise exact candidate remains
`MAY`, over-approximated, and `ANNOTATED`; it cannot discharge a `MUST`
obligation. The same rule applies to the caller-linked protected-effect
identity: Step 10 emits `consumer_reliance_candidate`, not a derived
`consumer_used` fact. This deliberately reduces apparent capability instead
of promoting a syntactic occurrence or external identity link to a relational
fact.

## Identity-chain convention

For any future fact strong enough to enter Step 9, the frozen convention is:

- producer subject = required authorizing object/context;
- producer object = exact producer/public value;
- reliance subject = protected effect occurrence;
- reliance object = the same producer/public value.

The initial Step 9 prototype checked referenced fact IDs but did not enforce
this complete chain. That pre-result defect was fixed before any Step 9 or
Step 10 result. Permanent regressions now require `UNKNOWN` for:

- the same display name with a different object;
- the same object in a different context; and
- a swapped protected-effect identity.

These checks are mechanical fixtures, not policy conclusions.

## Conditions and approximations

Existing lowercase `always` and `never` conditions are normalized to Step 9's
`ALWAYS` and `NEVER`. A supported prefix becomes a structured predicate only
when its extent has a compiler-backed variable identity or an exact integer
value. Surface-only extents are `UNKNOWN`. Unjoined disjunctions remain
`UNKNOWN`; the adapter does not invent a path merge.

Semantic mapping certificates must be bijective and preserve exact identity.
An encoding change is rejected. A valid certificate is retained on facts, but
Step 9 still returns `UNKNOWN` until that mapping is explicitly bound to the
relevant bundles; carrying a mapping ID is not discharge.

## Permanent regressions and controls

The runner exercises:

- all five D1P-40 repairs: dynamic memory, ambiguous public-input mapping,
  method-plus-signature effect identity, literal loop-tail bounds, and
  guard-independent R-ANCHOR candidate construction;
- the five corrected Payy unsupported dispositions;
- dynamic memory aliasing, prefix boundaries, inactive padding,
  unjoined verifier paths, mapping binding, encoding mismatch, and unmapped
  public inputs; and
- the three identity-chain swaps above.

All controls pass in the authoritative corrected raw run. The exact fixture has identity-chain
status `PASS` and equal-input parity between the Step 9 arms, but its
mechanical and effective obligation results remain `UNKNOWN` because the
producer and reliance records are only candidates and the policy is unreviewed.

## Preserved correction history

After sealing `run-01`, a self-audit found that its validator checked predicate
operator names without replaying their exact operand shapes, did not replay the
mapping-ID list against serialized certificates, and treated the externally
linked effect identity as derived. No scored or research result depended on
that run. Its protocol, raw files, and seal remain unchanged and are marked
non-authoritative. Protocol v2 records the reasons, binds the preserved seal,
and authorizes only non-overwriting `run-02`.

## Supported use and limitations

`build_inventory` accepts a current static or integrated analysis, a Step 8
`IdentityBundle`, optional mapping certificates, explicit compiler-backed
condition-variable names, and exact authorization/effect identity refs. A
missing or colliding ABI identity, unsupported condition, missing identity
link, unresolved dynamic address, or non-semantic mapping is retained as
`UNKNOWN` or rejected rather than guessed.

This prototype does not support aggregation, splitting, deferral, unbounded
paths, general loop equivalence, unsupported external calls, or a relational
producer proof. The evidence is synthetic and compiler-free apart from the
preserved D1P-40 helper regressions. Differential and targeted testing can
find errors but does not prove universal extraction soundness. No human policy,
real proof, committed effect, score, safety claim, or paper contribution
follows from this work.
