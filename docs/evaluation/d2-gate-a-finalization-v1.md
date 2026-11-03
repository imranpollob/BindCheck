# D2 Gate A blocked finalization

Date: 2 November 2026

Status: **BLOCKED BEFORE SCORE — ZERO SCORED ARMS**

Gate A decision: **INCONCLUSIVE**

Research verdict: **UNKNOWN**

## Purpose and boundary

This document finalizes the exposed-development Gate A attempt without running
a scored comparison. It applies the decision semantics and stop rules frozen in
`protocols/d2/d2-05-early-comparison-draft-v1.json` to the final Step 6a and
Step 6b construction evidence.

No analyzer, baseline, proof system, fuzzer, warning matcher, or human scorer is
dispatched by Step 7. No reserved material is opened. Construction warnings,
native smoke output, and historical evidence remain non-scored. There are no
`DETECTED` or `MISSED` rows, and empty denominators do not mean zero misses,
zero false warnings, or perfect performance.

## Completeness and information-parity audit

| Requirement | Evidence | Final disposition |
|---|---|---|
| Exact exposed candidate inventory | 13 Step 6a case appearances across Payy, WarpToad M-DOM/M-SRC, and D1P-43 E1–E9 | Retained; every candidate is `UNRESOLVED` and outside scored denominators |
| Six internal arms | 78 construction case-arms, 72 `SUPPORTED` and six E8 `UNKNOWN` | Construction only; not score rows |
| Equal information for strong versus full | Both share extracted implementation facts, but strong simple can consume generic direct P/O/E obligations while full only records the policy hash | `UNRESOLVED_EQUAL_POLICY_INTERFACE`; scored comparison prohibited |
| Human policy provenance | All 13 Step 6a case outputs record `policy_author=null` and `review_status=NOT_SUPPLIED`; the existing Step 6b WarpToad policy was AI-authored with no recorded human inspection | Human author/adopter `UNRESOLVED` |
| Distinct policy review | All 13 Step 6a case outputs record `policy_reviewer=null`; Step 6b independently records the different reviewer as unresolved | `UNRESOLVED` |
| External/same-policy arms | Foundry has one two-case construction smoke; other tools are native-only, unsupported, unavailable, or lack the required adaptation | No fair sealed same-policy comparator set |
| Subjective scoring | No two independent human scores or distinct adjudicator record exists | Ambiguous diagnosis, localization, and non-target rows would remain `UNRESOLVED` |
| Transformations | Four narrow transforms retain mappings, builds, two producer vectors, exact consumer algebra vectors, ABI correspondence, and semantic warning IDs; two application transforms were rejected before mutation | Accepted as bounded controls, not formal/general equivalence proofs; no score denominator exists in this finalization |
| Failures and recoveries | D2-06A construction-01/02 and D2-06B's failed environment-spelling attempt are preserved alongside final construction namespaces | Historical reconciliation complete; no failure becomes a miss or scientific retry |

The central comparison is globally ineligible because the evaluated full and
strong arms do not consume the same reviewed policy interface. Missing human
policy adoption and independent review independently prevent the same-policy
arm from entering a scored packet. Although Step 5 permits unrelated fully
objective rows to proceed when subjective scorers are unavailable, no row here
survives the equal-information and fair-arm gates. The exact objective subset
is therefore empty.

## Cases, targets, and outcomes

The packet retains these exact candidate IDs:

- `GA-PAYY-TAIL-EARLIER`
- `GA-PAYY-TAIL-CHECK-ADDED`
- `GA-WARPTOAD-MDOM`
- `GA-WARPTOAD-MSRC`
- `GA-WARPTOAD-RELATIONSHIP-E1` through
  `GA-WARPTOAD-RELATIONSHIP-E9`

Their semantic target sources remain the output-independent, provenance-
recorded Step 5 and D2-01 development associations. Step 7 does not revise
those associations from construction output. It also does not claim that a
target is fully adopted policy: every row is `UNRESOLVED` because the policy
and information-parity gates are missing.

E8 remains `UNKNOWN`. E9 remains an honest matching control, not a positively
verified globally safe negative. The Payy check-added revision remains an
exact repair contrast rather than a global safe control. Unsupported,
not-applicable, unavailable, build-failed, timeout, and unresolved comparator
cells remain visible outside any miss denominator.

The scored denominators are all zero:

- objective case-arm rows: 0;
- target detection: 0;
- diagnosis: 0;
- safe-control false warnings: 0;
- validation: 0;
- transformation stability: 0; and
- external comparator rows: 0.

Construction accounting remains separate: 78 Step 6a case-arms, six planned
transformations with four attempted and two rejected, two completed Step 6b
recovery smoke cases with passing adapter self-checks (the M-SRC native command
correctly exited 1 on its invariant failure), and two retained case failures
from the pre-compilation environment-spelling attempt.

## Warning matching and human dependencies

Had an objective subset been eligible, matching would have required the frozen
case/revision, producer relation or permitted producer locus, decoded identity
and index set, consumer effect/obligation locus, property kind/direction, and
evidence grade. Multiple reports could satisfy a target only under its frozen
union rule and only if every required identity or index were covered. Warning
ordinal and source line would not create independent findings.

No matcher runs here. No AI judgment is substituted for human policy adoption,
independent policy review, subjective scoring, or adjudication. Prior exposure
is explicit: the D1/D2 authors and agents worked with exposed mutations,
labels, construction outputs, and historical results.

## D2-06B effort correction

The D2-06B report says the 6.314872-second successful machine case total is
separate from compilation/setup. The runner actually times each complete
`forge test` command, and the retained native output shows Solidity compilation
inside the 3.289353-second and 3.025519-second intervals. Step 7 therefore
retains 6.314872 seconds only as aggregate command wall time including observed
compilation. It is not compilation-exclusive or analysis-exclusive effort and
supports no time-saving claim. The immutable Step 6b report and raw bytes are
preserved; this is the versioned interpretive correction.

## Timestamped manifest and content seal

`scripts/d2_step7_gate_a.py` fails closed unless all controlling hashes,
machine-readable blockers, candidate IDs, arm IDs, bounded transformation
controls, empty denominators, and the two-researcher-day/eight-machine-hour
prototype cap match the final protocol. It cannot dispatch research tools.

An integration race created `results/raw/D2-07/` while the evaluation lead was
still applying required pre-handoff tracked-document corrections. That first attempt ran zero
scored or research arms and its packet-to-seal check passed at creation, but a
later required corrections changed sealed bytes. Its seal therefore
now verifies `FAIL`. All five raw records are preserved as non-authoritative
history; none is overwritten or deleted.

The sole recovery repeats only the deterministic zero-score finalization in
fresh `results/raw/D2-07-recovery-01/` after every tracked Step 7 byte,
including `reports/D2-07.md`, is final. It contains:

1. a prior-attempt audit that verifies the initial seal's current failure and
   its zero-score summary;
2. a foundation run manifest with zero research calls and no seeds;
3. a timestamped packet manifest enumerating every case, target source, arm,
   resource rule, blank form, runner, and sealed artifact by real hash and size;
4. a zero-score finalization summary;
5. a D2 foundation content seal over the protocol, report, prior evidence,
   historical failures (including the initial D2-07 attempt), Step 7
   code/document/test, and the four pre-seal records; and
6. a post-seal verification record.

Before accepting verification, the runner compares the packet's complete base
member `{path, SHA-256, size}` set with the final seal's member set plus exactly
the declared prior-attempt audit, run-manifest, packet-manifest, and summary
extras. Any missing, extra, or changed byte record fails the finalization,
which closes the independent-enumeration race in a shared workspace.

The seal cannot hash itself. The verification record necessarily depends on
the seal hash and therefore also cannot be a member of that seal. Both
exclusions are explicit. No scored execution is authorized either before or
after sealing.

## Gate decision

The only permitted Gate A decision is **INCONCLUSIVE**. `SUPPORTED_ADVANTAGE`
would require an eligible, fair, transformation-stable discriminating target;
none exists. `CURRENT_CLAIM_CONTRADICTED` would require a fair comparison in
which the strong or other equal-information arm matches or exceeds full
BindCheck; no such comparison ran.

The result supports no novelty, security, generality, prevalence, transfer,
safety, precision, recall, or time-saving claim. The research verdict remains
`UNKNOWN`.

The separate scope recommendation is **BOUNDED PROTOTYPE**. It becomes
effective only after the D2-07-recovery-01 content seal verifies and
`reports/D2-07.md` records both the `INCONCLUSIVE` result and this
recommendation. It authorizes
only the specified Steps 8–10 development on exposed material, under one
combined cap of two researcher-days and eight machine-hours. It does not open
reserved data or authorize a retroactive Gate A rescore.

Before the missing human roles exist, Steps 8–10 may perform mechanical schema,
byte-identical interface, compiler-identity, provenance, determinism, and
bounded-transformation work only under the explicit label
`UNREVIEWED_DEVELOPMENT_FIXTURE`. Such tests cannot establish policy
correctness or comparative advantage. The primary discriminating experiment
remains blocked until a human authors or adopts the exact policy bytes, a
different human reviews them before comparison output, both arms consume the
same frozen identity/policy bytes, and the remaining experiment is sealed.

## Prospective Steps 8–10 prototype, not implemented here

The construction evidence isolates one generalizable missing mechanism: a
shared compiler-backed object/context identity representation plus one common,
versioned P/O/E obligation interface consumed byte-identically by full
BindCheck and strong simple composition.

The frozen primary test would use the exposed D1P-42 producer/consumer pair, a
matched non-violating control, and prospectively controlled identifier-renaming
and public-input-reordering variants. Both arms would receive identical source,
artifact, ABI, mapping, human-authored-or-adopted and independently reviewed
policy bytes, assumptions, and budgets. The identity representation must be
name-independent and stable under the accepted mappings; neither arm may
receive a manual hidden defect relation.

Success requires both arms to record the same policy and identity hashes, full
BindCheck alone to produce the prospectively specified relationship diagnosis
on the positive, neither arm to flag the matched control, and the diagnosis to
remain stable across accepted controls. Failure includes different consumed
fields or hashes, name/manual-relation dependence, control failure,
transformation instability, a strong-arm match, or an unresolved budget stop.

The cap is two researcher-days and eight machine-hours. This prospective
development test is not implemented by Step 7 and cannot retroactively rescore
Gate A.
