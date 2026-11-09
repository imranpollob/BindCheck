# E2 held-out measurement, freeze 2

**Status.** The preregistered EVAL draw ran once with frozen BindCheck and arm C on the same pinned checkouts. The [run command record](../../results/raw/heldout/e2-freeze2-once-command-record.json) records an observed exit status of [0](../../results/raw/heldout/e2-freeze2-once-command-record.json); the [completed manifest](../../results/raw/heldout/e2-freeze2-once/run-manifest.json) records the analyzer content hash, dataset hash, tags, run HEAD, start and end times, and zero remaining checkouts. All [277 eligible family results](../../results/raw/heldout/e2-freeze2-once/run-manifest.json) are retained under [raw EVAL evidence](../../results/raw/heldout/e2-freeze2-once/families/). The exposed [rank 259 family](../../results/raw/heldout/e2-freeze2-once/run-manifest.json) was excluded before analysis. No family was replaced or rerun. The [family ledger](measurement-family-ledger.csv) links each pinned revision to its raw result and prebuild record.

This is a measurement of **source evidence and checker coverage**. Warning counts are not confirmed vulnerability counts. Human precision, false alarm rate, and comparative localized detection are **MISSING** until the blind cards receive independent human labels. No live-chain transaction, third-party contract interaction, maintainer contact, or E4 local-proof exploit validation occurred in this lane.

## Draw and build funnel

| Stage or outcome | Families | Evidence and interpretation |
| --- | ---: | --- |
| Selected source families | [278](../../results/raw/heldout/e2-freeze2-once/run-manifest.json) | Byte-exact [preregistered selection](selected-families.csv). |
| Exposed, excluded before either tool | [1](../../results/raw/heldout/e2-freeze2-once/run-manifest.json) | [Rank 259](../../results/raw/heldout/e2-freeze2-once/run-manifest.json); no substitution. |
| Build-only preflight `BUILT` | [163](prebuild-summary-v3.json) | At least one recorded entry circuit produced R1CS and symbol files. |
| Build-only preflight `BUILD_FAILED` | [46](prebuild-summary-v3.json) | Exact compiler diagnostics and failure causes are in the [per-family prebuild ledger](prebuild-status-v3.csv). |
| Build-only preflight `NO_ENTRY_CIRCOM` | [68](prebuild-summary-v3.json) | No recorded existing Circom path was recognized as an entry circuit. |
| EVAL acquisitions ready | [277](measurement-summary.json) | Pinned checkout acquired; [zero acquisition failures](measurement-summary.json). |
| EVAL families with matched triples | [246](measurement-summary.json) | At least one recovered circuit–verifier–consumer triple; this is the family-level analyzable denominator. |
| EVAL families without matched triples | [31](measurement-summary.json) | Includes tool timeouts; these are coverage losses, not safe results or misses. |

The [prebuild v3 report](PREBUILD-V3.md) gives its setup, source revisions, limits, and exact command. Prebuild and EVAL are distinct passes: the prebuild tests recorded entry circuits, while the analyzer can discover other paths. The [EVAL family ledger](measurement-family-ledger.csv) shows both statuses per family. The [EVAL manifest](../../results/raw/heldout/e2-freeze2-once/run-manifest.json) records the [freeze-2 hash `92789fad…`](../../results/raw/heldout/e2-freeze2-once/run-manifest.json), and the [dated addendum](PREREG.md#2026-11-09-freeze-2-and-final-warning-inventory-addendum) fixed the warning and γ=δ definitions before execution.

## BindCheck verdicts by pattern

Each cell is a **family-level** verdict/applicability count from the frozen [summary](../../results/raw/heldout/e2-freeze2-once/summary.json). `NOT_APPLICABLE` is an applicability value, never a verdict. All non-applicable and applicability-unknown entries have verdict `UNKNOWN`; all other matrix cells are [zero](../../results/raw/heldout/e2-freeze2-once/summary.json). A decided fraction uses only applicable families as its denominator. It measures decision coverage, not precision.

| Pattern | Applicable | VIOLATION / applicable | VERIFIED_WITHIN_SCOPE / applicable | UNKNOWN / applicable | UNKNOWN / not applicable | UNKNOWN / applicability unknown | Decided / applicable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| P1 | [63](../../results/raw/heldout/e2-freeze2-once/summary.json) | [17](../../results/raw/heldout/e2-freeze2-once/summary.json) | [2](../../results/raw/heldout/e2-freeze2-once/summary.json) | [44](../../results/raw/heldout/e2-freeze2-once/summary.json) | [183](../../results/raw/heldout/e2-freeze2-once/summary.json) | [31](../../results/raw/heldout/e2-freeze2-once/summary.json) | [19/63](../../results/raw/heldout/e2-freeze2-once/summary.json) |
| P2 | [113](../../results/raw/heldout/e2-freeze2-once/summary.json) | [0](../../results/raw/heldout/e2-freeze2-once/summary.json) | [3](../../results/raw/heldout/e2-freeze2-once/summary.json) | [110](../../results/raw/heldout/e2-freeze2-once/summary.json) | [133](../../results/raw/heldout/e2-freeze2-once/summary.json) | [31](../../results/raw/heldout/e2-freeze2-once/summary.json) | [3/113](../../results/raw/heldout/e2-freeze2-once/summary.json) |
| P3 | [86](../../results/raw/heldout/e2-freeze2-once/summary.json) | [33](../../results/raw/heldout/e2-freeze2-once/summary.json) | [19](../../results/raw/heldout/e2-freeze2-once/summary.json) | [34](../../results/raw/heldout/e2-freeze2-once/summary.json) | [160](../../results/raw/heldout/e2-freeze2-once/summary.json) | [31](../../results/raw/heldout/e2-freeze2-once/summary.json) | [52/86](../../results/raw/heldout/e2-freeze2-once/summary.json) |
| P4 | [246](../../results/raw/heldout/e2-freeze2-once/summary.json) | [18](../../results/raw/heldout/e2-freeze2-once/summary.json) | [92](../../results/raw/heldout/e2-freeze2-once/summary.json) | [136](../../results/raw/heldout/e2-freeze2-once/summary.json) | [0](../../results/raw/heldout/e2-freeze2-once/summary.json) | [31](../../results/raw/heldout/e2-freeze2-once/summary.json) | [110/246](../../results/raw/heldout/e2-freeze2-once/summary.json) |
| P5 | [246](../../results/raw/heldout/e2-freeze2-once/summary.json) | [38](../../results/raw/heldout/e2-freeze2-once/summary.json) | [2](../../results/raw/heldout/e2-freeze2-once/summary.json) | [206](../../results/raw/heldout/e2-freeze2-once/summary.json) | [0](../../results/raw/heldout/e2-freeze2-once/summary.json) | [31](../../results/raw/heldout/e2-freeze2-once/summary.json) | [40/246](../../results/raw/heldout/e2-freeze2-once/summary.json) |

The [summary JSON](../../results/raw/heldout/e2-freeze2-once/summary.json) also retains each verdict × applicability matrix by preregistered stratum. `UNKNOWN` reasons below are **nonexclusive**: one family may contribute several reasons, so their counts need not sum to the `UNKNOWN` family count. Codes are the frozen broad unknown-reason categories.

| Pattern | UNKNOWN reasons (family counts) | UNKNOWN reason codes (family counts) |
| --- | --- | --- |
| P1 | [`CALLER_INDEPENDENCE_UNRESOLVED`: 5; `EFFECT_TRANSFORMATION_UNRESOLVED`: 1; `HARNESS_TIMEOUT`: 2; `NO_APPLICABLE_TRIPLE`: 29; `PROTECTED_EFFECT_NOT_RECOVERED`: 207; `UNRESOLVED_CONSUMER_INHERITANCE`: 25; `UNRESOLVED_CONSUMER_MODIFIER`: 13; `UNSUPPORTED_CONSUMER_ASSEMBLY`: 1; `VERIFIER_ARTIFACT_MISSING`: 1](../../results/raw/heldout/e2-freeze2-once/summary.json) | [`HARNESS_TIMEOUT`: 2; `MISSING_ARTIFACT`: 1; `OTHER`: 218; `UNSUPPORTED_CONSTRUCT`: 37](../../results/raw/heldout/e2-freeze2-once/summary.json) |
| P2 | [`CONTEXT_BOUND_BY_LOCAL_GUARD`: 1; `CONTEXT_BOUND_IN_PUBLIC_COMMITMENT`: 2; `CONTEXT_BOUND_IN_PUBLIC_INPUTS`: 1; `CONTEXT_COMPUTATION_NOT_GUARDED`: 30; `HARNESS_TIMEOUT`: 2; `NO_APPLICABLE_TRIPLE`: 29; `NO_CONTEXT_BINDING_RECOVERED`: 79; `PROTECTED_EFFECT_NOT_RECOVERED`: 179; `VERIFIER_ARTIFACT_MISSING`: 10](../../results/raw/heldout/e2-freeze2-once/summary.json) | [`HARNESS_TIMEOUT`: 2; `MISSING_ARTIFACT`: 10; `OTHER`: 262](../../results/raw/heldout/e2-freeze2-once/summary.json) |
| P3 | [`HARNESS_TIMEOUT`: 2; `NO_APPLICABLE_TRIPLE`: 29; `PROTECTED_EFFECT_NOT_RECOVERED`: 162; `REPLAY_BARRIER_HELPER_UNRESOLVED`: 9; `REPLAY_KEY_CANONICAL_AND_CONSUMED`: 1; `REPLAY_KEY_EXPRESSION_UNRESOLVED`: 11; `REPLAY_KEY_NOT_RECOVERED`: 27; `REPLAY_KEY_POSITION_UNRESOLVED`: 6; `VERIFIER_ARTIFACT_MISSING`: 9](../../results/raw/heldout/e2-freeze2-once/summary.json) | [`HARNESS_TIMEOUT`: 2; `MISSING_ARTIFACT`: 9; `OTHER`: 189; `UNSUPPORTED_CONSTRUCT`: 25](../../results/raw/heldout/e2-freeze2-once/summary.json) |
| P4 | [`DUPLICATE_IC_SOURCE_WARNING`: 1; `HARNESS_TIMEOUT`: 2; `NO_APPLICABLE_TRIPLE`: 29; `PUBLIC_INPUT_CANONICALITY_GUARD_NOT_FOUND`: 48; `RUNTIME_BYTECODE_PARSE_INCOMPLETE`: 1; `UNSUPPORTED_VERIFIER_KEY_LAYOUT`: 56; `VERIFICATION_KEY_CHECKS_PASS`: 20; `VERIFICATION_KEY_PARSE_INCOMPLETE`: 11; `VERIFIER_ARTIFACT_MISSING`: 6; `VERIFIER_HELPER_GUARD_UNRESOLVED`: 13; `VERIFIER_IMPLEMENTATION_ARTIFACT_MISSING`: 15](../../results/raw/heldout/e2-freeze2-once/summary.json) | [`HARNESS_TIMEOUT`: 2; `MISSING_ARTIFACT`: 69; `OTHER`: 43; `UNSUPPORTED_CONSTRUCT`: 65](../../results/raw/heldout/e2-freeze2-once/summary.json) |
| P5 | [`CIRCUIT_ARTIFACT_MISSING`: 9; `CIRCUIT_INTERFACE_INCOMPLETE`: 8; `DYNAMIC_PUBLIC_INPUT_LENGTH_GUARDED`: 2; `DYNAMIC_PUBLIC_INPUT_LENGTH_UNRESOLVED`: 21; `HARNESS_TIMEOUT`: 2; `NO_APPLICABLE_TRIPLE`: 29; `PUBLIC_INPUT_COUNT_AND_ORDER_MATCH`: 6; `PUBLIC_INPUT_MEANING_UNRESOLVED`: 48; `PUBLIC_INPUT_ORDER_UNRESOLVED`: 65; `PUBLIC_INPUT_VECTOR_UNRESOLVED`: 33; `VERIFIER_ARTIFACT_MISSING`: 20; `VERIFIER_MATCH_AMBIGUOUS`: 52](../../results/raw/heldout/e2-freeze2-once/summary.json) | [`AMBIGUOUS_CORRESPONDENCE`: 89; `BUILD_FAILURE`: 8; `HARNESS_TIMEOUT`: 2; `MISSING_ARTIFACT`: 29; `OTHER`: 122; `UNSUPPORTED_CONSTRUCT`: 21](../../results/raw/heldout/e2-freeze2-once/summary.json) |

## Arm C and warning inventory

Arm C ran on the same [277 eligible pinned checkouts](measurement-family-ledger.csv). Its [run status](measurement-summary.json) was `completed` for [276](measurement-summary.json) and `UNKNOWN` after [1 timeout](measurement-summary.json). The normalized family-level arm C result is [132 `VIOLATION`, 4 `VERIFIED_WITHIN_SCOPE`, and 141 `UNKNOWN`](measurement-summary.json). A completed run without adjudicated native findings remains `UNKNOWN` rather than a negative result. The [native code ledger](measurement-summary.json) records all emitted finding codes; the [unblinding key](warning-unblind-key.csv) records deduplicated warnings and exact locations. Arm C is a source heuristic, and these normalized labels are **not human-confirmed binding defects**.

| Blind warning source | Deduplicated cards | Located by path and line | Location missing |
| --- | ---: | ---: | ---: |
| BindCheck, all patterns | [331](measurement-summary.json) | [331](measurement-summary.json) | [0](measurement-summary.json) |
| Arm C, native findings | [462](measurement-summary.json) | [394](measurement-summary.json) | [68](measurement-summary.json) |
| Total | [793](measurement-summary.json) | [725](measurement-summary.json) | [68](measurement-summary.json) |

BindCheck's triple-level warning counts are [P1: 21, P2: 0, P3: 53, P4: 185, P5: 72](measurement-summary.json). The P4 cards include source warnings even when the family-level P4 verdict is `UNKNOWN`, as [preregistered](PREREG.md#warning-and-adjudication-rules). Arm C's [native findings](measurement-summary.json) are deduplicated by the preregistered family/code/path/line/message key before cards; they are not credited as matching a BindCheck pattern without human pattern and location adjudication. Findings with missing locations cannot receive localized-detection credit. Right-pattern/right-location matches, TP, FP, repaired-case false alarms, and comparative precision are all **MISSING**.

The [blind index](../../review/heldout/INDEX.md) links every card. [Rater A](../../review/heldout/BLIND-SHEET-rater-a.csv) and [Rater B](../../review/heldout/BLIND-SHEET-rater-b.csv) each have [793 blank rows](measurement-summary.json); the [separate key](warning-unblind-key.csv) is outside the blind review folder. The [card audit](card-audit.csv) records [68 cards without source context at the reported location and 413 without a recovered matched verifier body](measurement-summary.json). These fields say `MISSING` on the cards; they are review limitations, not negative findings. Source files that were captured are retained under the corresponding [raw family directories](../../results/raw/heldout/e2-freeze2-once/families/). Human rater coverage and agreement, precision, E4 validation, and disclosure status remain **MISSING**.

## Verifier source census and γ=δ

These are **different denominators**. The passive census covers classified function rows across the whole source corpus; the γ=δ measure covers unique matched EVAL verifier source artifacts with parsed frozen P4 points. Neither is deployment prevalence. The [per-function census ledger](per-verifier.csv) and [per-artifact γ=δ ledger](gamma-delta-ledger.csv) retain pinned source identity, SHA-256, and raw evidence paths.

| Measure | Observed count and denominator | Source |
| --- | --- | --- |
| Passive census, EVAL classified verifier functions | [8,127 function rows](verifier-census-summary.json) | [CENSUS.md](CENSUS.md) |
| snarkjs current / legacy template markers | [2,570 / 25 of 8,127](verifier-census-summary.json) | [Per-function source ledger](per-verifier.csv) |
| gnark / other template markers | [235 / 5,297 of 8,127](verifier-census-summary.json) | [Per-function source ledger](per-verifier.csv) |
| Recognized scalar `r` guard, all / partial positions | [1,931 / 1 of 8,127](verifier-census-summary.json) | [Per-function source ledger](per-verifier.csv) |
| Recognized base `q` guard, all / partial positions | [346 / 0 of 8,127](verifier-census-summary.json) | [Per-function source ledger](per-verifier.csv) |
| No recognized guard / unknown guard or arity | [1,967 / 3,882 of 8,127](verifier-census-summary.json) | [Per-function source ledger](per-verifier.csv) |
| Unconditional true / dummy constants / simplified marker / rejecting stub | [254 / 0 / 299 / 54 of 8,127](verifier-census-summary.json) | [Per-function source ledger](per-verifier.csv) |
| Matched held-out source artifacts | [654](measurement-summary.json) | [γ=δ ledger](gamma-delta-ledger.csv) |
| Unparsed γ or δ | [310 of 654](measurement-summary.json) | [γ=δ ledger](gamma-delta-ledger.csv) |
| Parsed γ and δ | [344 of 654](measurement-summary.json) | [γ=δ ledger](gamma-delta-ledger.csv) |
| Equal parsed γ=δ | [56 of 344](measurement-summary.json) | [γ=δ ledger](gamma-delta-ledger.csv) |
| Distinct parsed γ≠δ | [288 of 344](measurement-summary.json) | [γ=δ ledger](gamma-delta-ledger.csv) |

The analyzer left [27 triples without both verifier path and source SHA-256](measurement-summary.json), outside the artifact ledger. Repeated triples referencing one source artifact count once. The [ledger](gamma-delta-ledger.csv) records the raw P4 facts used for every parsed classification. Equality is a source-key observation; proof acceptance, consumer reachability, and exploitability require separate evidence.

## Runtime and failures

All times below are exact recorded seconds from [per-family command records](measurement-runtime-ledger.csv), with no extrapolated total. Acquisition sums recorded Git step times per EVAL family; prebuild sums recorded compile-attempt times for families with an attempt. The other rows use the tool's outer command record. `MISSING` means no command record, not zero elapsed time.

| Stage | Recorded families | Minimum seconds | Median seconds | Maximum seconds | Command timeouts |
| --- | ---: | ---: | ---: | ---: | ---: |
| EVAL acquisition | [277](measurement-summary.json) | [0.670472](measurement-summary.json) | [1.708417](measurement-summary.json) | [178.500555](measurement-summary.json) | [0](measurement-summary.json) |
| Prebuild compile attempts | [209](measurement-summary.json) | [0.007083](measurement-summary.json) | [0.314122](measurement-summary.json) | [49.215150](measurement-summary.json) | [4](measurement-summary.json) |
| BindCheck | [277](measurement-summary.json) | [0.116217](measurement-summary.json) | [0.884698](measurement-summary.json) | [150.020694](measurement-summary.json) | [2](measurement-summary.json) |
| Circomspect | [277](measurement-summary.json) | [0.086331](measurement-summary.json) | [0.265539](measurement-summary.json) | [61.668751](measurement-summary.json) | [0](measurement-summary.json) |
| Picus | [277](measurement-summary.json) | [0.090571](measurement-summary.json) | [1.655106](measurement-summary.json) | [124.356174](measurement-summary.json) | [0](measurement-summary.json) |
| Slither | [277](measurement-summary.json) | [0.5364](measurement-summary.json) | [1.190119](measurement-summary.json) | [11.8184](measurement-summary.json) | [0](measurement-summary.json) |
| ZKAP | [0](measurement-summary.json) | MISSING | MISSING | MISSING | MISSING |
| Arm C | [277](measurement-summary.json) | [0.161125](measurement-summary.json) | [6.355762](measurement-summary.json) | [390.106418](measurement-summary.json) | [1](measurement-summary.json) |

The [EVAL family ledger](measurement-family-ledger.csv) identifies the [two BindCheck timeouts and one arm C timeout](measurement-summary.json); the [two timed-out BindCheck output files](measurement-summary.json) are not parseable JSON and remain `UNKNOWN`. The [tool run-status table](measurement-summary.json) also records Circomspect, Picus, Slither, and ZKAP outcomes. ZKAP was unavailable on [all 277 families](../../results/raw/heldout/e2-freeze2-once/summary.json), with no timed command record and no win/miss credit. Prebuild compilation failures, missing entry circuits, unsupported source shapes, absent artifacts, and timeouts remain separate coverage losses. The [prebuild ledger](prebuild-status-v3.csv) has each compiler failure cause, and the [per-pattern summary](../../results/raw/heldout/e2-freeze2-once/summary.json) carries every frozen unknown-reason code.

## Reproduction, limits, and next review

The [command record](../../results/raw/heldout/e2-freeze2-once-command-record.json) gives exact EVAL, summary, card, and ledger commands; observed exit statuses; Python and Git versions; script hashes; and log hashes. The [run manifest](../../results/raw/heldout/e2-freeze2-once/run-manifest.json) records the frozen gate and one-shot run identity. The [reporting derivation](../../eval/derive_heldout_measurement.py) reads preserved raw files and generates the tracked family, runtime, γ=δ, and card-audit ledgers. It does not run a checker or change any verdict. The full [raw result directory](../../results/raw/heldout/e2-freeze2-once/) remains ignored but retained locally.

The sample is a convenience source corpus, so these counts do not support ecosystem prevalence. Source warnings and arm C native findings await human labels; AI output is not independent annotation. The next measurable task is for two human raters to complete their separate blind sheets, then resolve disagreements using the [preregistered adjudication procedure](PREREG.md#warning-and-adjudication-rules). Only then can localized matches and precision be reported. No public disclosure or live-network step is authorized here.
