# Independent held-out evaluation protocol, version 2

**Status:** FINAL TEXT FOR APPROVAL, 30 October 2026. It becomes frozen
only when the approval block (§19) records two planner approvals and the
custodian's agreement against the SHA-256 given there. Nothing in this
protocol has been executed. No search was run, no candidate repository was
opened, and no draw was made while writing it.
**Author:** AI 3 (independent evaluation design). This is AI output and not an
independent annotation (contract §10). Authors must inspect it before
freezing it.
**Controls:** [research contract](../research-contract.md) revision 3, then
[taxonomy protocol v0.2.0](../taxonomy/protocol.md) §§3, 7–8, then this
document. If they conflict, the higher-ranked source wins and the conflict is
reported. The amendments in §14 apply only to this tool-transfer evaluation.

The inputs read for this design were AGENTS.md, the research contract, the
taxonomy protocol, the
[2026-10-28 reservation commitment](../taxonomy/reservation-commitment-2026-10-28.json),
[D1P-33](../../reports/D1P-33.md), [D1P-35](../../reports/D1P-35.md),
[D1P-36](../../reports/D1P-36.md),
[D1P-40](../../reports/D1P-40-correctness-audit.md),
[D1P-41](../../reports/D1P-41-ablation-preliminary.md), the
[2026-10-30 policy review](../validation/policy-review-2026-10-30.md), the
[evidence ledger](../x-experiment/EVIDENCE-LEDGER.md),
`scripts/taxonomy/reserve_families.py` and `paper/draft.md`. No candidate
repository's code was opened.

## 1. Purpose and what version 1 lacked

This protocol tests whether a frozen BindCheck transfers to independently
developed Noir/EVM projects. That is the generality question: contract RQ4
transfer and capability-gate item (d). The first held-out attempt had these
weaknesses, and this version addresses each one:

| Weakness observed | Where | Response in v2 |
| --- | --- | --- |
| The frame had 8 candidates and 4 reserved projects, from one AI-prepared search | commitment file; D1P-33 | Target frame of about 30 candidates and about 10 reserved (§3, §7) |
| No search source or query string was recorded | commitment file | Exact sources, queries, caps and timestamps logged (§3.3) |
| The commitment did not state how many groups were reserved | commitment file | Public counts per stratum and a hash of the grouped list (§7.3) |
| No check of the opening against the commitment was recorded | D1P-33 | Opening check is a mandatory gate before retrieval (§7.4) |
| The selection procedure for the unseen Set B was not recorded | D1P-36 | Every evaluated project comes from the logged frame (§3) |
| A tool change motivated by the first attempt ended first-attempt status for the reserved set | D1P-35 §6; D1P-36 | Development uses only the non-reserved pool; reserved projects get one run with one frozen tool (§8, §10) |
| A 0/4 and a 0/8 result told us only where the tool stopped | D1P-33; D1P-36 | Analysis-time facts recorded for every project, with completed analyses, warnings and confirmed defects counted separately (§10.5, §12) |

The D1P-33 and D1P-36 results are not relabeled. Those runs completed 0/4
and 0/8 analyses, and no rule ran on any project. They are neither misses nor
safety evidence. The eight projects involved remain in their own reported
strata and are excluded from the v2 frame (§5).

## 2. Roles and separation

| Role | Who | May see | Must not see before the stated gate |
| --- | --- | --- | --- |
| **Custodian** | Repository owner (human), working in a plain terminal outside every agent session | Everything in §§3–7 | Nothing is restricted. Must not read circuit or consumer *logic* of any candidate during the screen (§4.1) |
| **Search operator** | The custodian, or one dedicated agent session with no development or evaluation role | Search results (names, URLs, repository metadata) | Repository contents. Its output goes only to the custodian and never into a Git worktree |
| **AI 1 (development)** | Development agent lane | The released development set (§8) and the exposed development cases | The full frame, the grouped list, reserved membership, and the search result lists |
| **Evaluation executor** | A fresh agent session that has had no development role, or a human | The reserved set, after the tool freeze (§9) and the opening check (§7.4) | Reserved membership before the freeze |
| **Triagers** | Two humans; a third human adjudicates (§13) | Warnings, source and project documentation | Validation results and the other triager's labels before sealing |
| **AI 4 (validation)** | Validation agent lane | Triaged warnings marked for validation (§13.4) | Triage labels before they are sealed; reserved membership before the opening |
| **AI 3** | This design | This protocol | Any candidate repository. AI 3 has opened none |

AI systems are never triagers or adjudicators. An AI session may prepare
an evidence packet of code locations and build logs for the triagers, but
it may not propose a triage label.

## 3. Sampling frame

### 3.1 Targets, not requirements

The design aims for:
- about **30** candidate projects that pass the metadata screen and are not
  exposed; and
- about **10** reserved family groups.

These figures are targets used to set search caps and budgets. They are not
acceptance criteria. The frame is whatever the frozen traversal returns
(§3.4). If it yields 18 groups or 45, the draw proceeds with that number.
The paper reports the actual denominators, and no query is added or rerun
to reach a target.

### 3.2 Unit

The candidate unit is a public GitHub repository that may contain a Noir
circuit and a Solidity/EVM consumer. Family groups (§6) are the unit of the
draw. Projects are the unit of retrieval and analysis.

### 3.3 Sources and exact queries

Freeze this table before any query runs. The search log may correct a
syntax error only before the first query runs, and the correction is
recorded. All queries use the GitHub web search interface, signed in, with
the default "best match" sort. Each query is run once.

| ID | Source | Exact query string | Cap | Rationale |
| --- | --- | --- | --- | --- |
| Q1 | GitHub code search | `"BaseZKHonkVerifier" language:Solidity` | first 100 results | Generated by bb 5.x UltraHonk ZK Solidity verifiers (seen in TE04) |
| Q2 | GitHub code search | `"BaseHonkVerifier" language:Solidity` | first 100 | Generated by non-ZK UltraHonk verifiers |
| Q3 | GitHub code search | `"contract UltraVerifier" language:Solidity` | first 100 | Generated by older UltraPlonk verifiers |
| Q4 | GitHub code search | `"bytes32[] calldata _publicInputs" language:Solidity` | first 100 | Public-input array parameter of generated verifiers |
| Q5 | GitHub repository search | `topic:noir topic:solidity` | first 100 | Self-declared Noir+Solidity projects |
| Q6 | GitHub repository search | `noir verifier solidity in:readme,description` | first 100 | Self-described pairs |
| Q7 | Curated list | Application entries in `noir-lang/awesome-noir` `README.md` at the commit current on the search date (commit recorded) | all entries | Ecosystem listing independent of verifier strings |

Before freezing, the operator checks once that Q1–Q4 match generated
verifiers. The check uses a verifier generated locally by the pinned bb
toolchain, never a search result. A string that no longer occurs in current
bb output is still run and logged, and a zero-result query stays in the log.

**Traversal order:** Q7, Q1, Q2, Q3, Q4, Q5, Q6. The curated list goes
first because it does not depend on verifier strings.

**Post-filters** use repository metadata only:
1. Last push on or after 1 January 2025, the Noir 1.0 beta era. The date
   filter is applied to the metadata, because code search has no date
   qualifier.
2. Organizations `noir-lang` and `AztecProtocol` are excluded as toolchain
   owners whose examples are not applications. Repositories owned by the
   authors are also excluded.
3. A fork is kept as a candidate but grouped with its parent (§6).
4. Hits are deduplicated by repository. Every query that found a
   repository is recorded as one of its discovery routes.

**Search log**, held privately by the custodian. For each query it records:
- the ID and exact string;
- the UTC timestamp;
- the displayed total count;
- the pages read;
- every returned repository URL with its rank;
- the post-filter disposition and reason; and
- failures such as rate limits or errors.

The log's SHA-256 and per-query counts (displayed total, returned, kept after
post-filters) are published in the repository. Repository names are not
published (§7.3).

**Budget:** 240 minutes of active search time. If the budget ends before
the traversal completes, the log records the last query and page reached.
The frame is then the incomplete traversal, and the paper says so.

### 3.4 Stopping

Every query is read to its cap, in the frozen order. The search never stops
because a target count was reached, and never stops early because results
look promising or unpromising.

## 4. Metadata screen (human custodian)

### 4.1 Permitted material

For each post-filtered candidate, the custodian may open only:
- the repository's file tree listing;
- the contents of each `Nargo.toml`; and
- the GitHub "about" metadata.

Circuit sources (`*.nr`), Solidity sources, tests, issues, pull requests and
READMEs beyond the first screen are not read. The custodian records this
access in the exposure log (§8.3). Budget: about 5 minutes per candidate.

### 4.2 Fields recorded

| Field | Values |
| --- | --- |
| `nargo_toml_paths` | Every `Nargo.toml` path outside `lib/`, `node_modules/`, `vendor/` and dependency caches |
| `nargo_package_types` | `bin`, `lib` or `contract` for each manifest, as declared |
| `compiler_version_raw` | The `compiler_version` string verbatim, or `absent` |
| `compiler_version_class` | `exact` (one version), `range` (comparator or caret), or `absent` |
| `solidity_paths_count` | Number of `.sol` files outside dependency directories |
| `screen_outcome` | `pass`, `fail`, or `unknown`, with a reason |

### 4.3 Screen rule

- **`pass`**: at least one `bin` Nargo package, and at least one non-vendored
  `.sol` file.
- **`fail`**: no Nargo package, no non-vendored `.sol` file, or only `lib`
  packages. A failed candidate is listed and never drawn.
- **`unknown`**: the custodian cannot decide from the permitted material.
  Examples are a Noir package only inside an unfetched submodule, or Solidity
  only under a path that may be vendored.

The compiler version is **recorded, not screened against tool support.**
Filtering the frame by what the current tool decodes would fit the held-out
set to the tool. The declared version is reported as a covariate.

### 4.4 What the screen cannot establish

The screen admits candidates and nothing more. It cannot establish:
- that any Solidity contract consumes a proof of the screened circuit;
- that a checked-in verifier corresponds to the circuit and key (zkt-research's
  checked-in verifier was a stub, D1P-33 §4.3);
- the number of verifier boundaries (NullProof had two, D1P-36 §4.1);
- the absence of recursion (ZKPassport's `RecursiveAggregation`, D1P-33
  §4.4) or of other unsupported black boxes (`MultiScalarMul`, D1P-36);
- which compiler actually builds the project (IP-NFT declared `>=0.31.0` and
  built only with beta.3, D1P-33 §3); or
- that the project builds at all.

These facts are determined at analysis time and reported for every project
(§10.5). A screened project that turns out to have no verifier pairing, or
that uses recursion, stays in the results with that outcome.

## 5. Exposure exclusions

Candidates in any of the following families are excluded from the draw,
with a reason recorded:
- the development cases Payy, WarpToad, 0xbow Privacy Pools and the Aztec
  epoch rollup;
- the 23 families of the taxonomy v1 corpus;
- all eight candidates of the 2026-10-28 frame, including the four reserved
  projects scanned in D1P-33 and D1P-36; and
- the four D1P-36 Set B projects.

The custodian applies these exclusions from the private name lists. The
public record gives only the count excluded under each heading. A merged
family inherits exposure from any of its members.

The 2026-10-28 reserved projects keep the status recorded in D1P-36. They
were reserved, and their second attempt is reported separately. Moving them
into development requires an explicit recorded decision. This protocol does
not make one.

## 6. Family grouping

The custodian groups screened candidates before the draw, following
taxonomy protocol §3:
- **Merge** candidates linked by demonstrated lineage: a GitHub fork
  relation, a "forked from" or "port of" statement in the about metadata, or
  the same owner publishing renamed copies.
- **Merge** candidates that share an application-specific template, where the
  application circuit or consumer comes from the template.
- **Do not merge** on a shared generic starter, a generated verifier,
  `bb`/`nargo`, a library, a hackathon, or the organization alone.
- **Uncertain** ancestry is merged conservatively.

Each group records `group_id`, member names, `grouping_basis`,
`newly_eligible`, `exposed`, `tool_transfer_eligibility` and `stratum_id`, in
the existing [grouped-families schema](../taxonomy/grouped-families.schema.json):
- **Strata:** `noir-evm:eligible` for groups whose members all screened
  `pass`, and `noir-evm:unknown` for groups containing an `unknown`.
- **Eligibility:** `tool_transfer_eligibility` is `eligible` or `unknown` to
  match the stratum. It is a screen label, not a support prediction.

## 7. Custodian draw and commitment

### 7.1 Rule

Reserve **one third, rounded up, of the newly eligible, unexposed groups in
each stratum.** With about 30 eligible groups this gives about 10. The
fraction is fixed here, before the grouped list exists. It is never chosen
after the group count is known.

This amends the v0.2.0 default of one half (§14, A-V2-1). The custodian runs
`reserve_families.py --fraction 1/3` (prerequisite P1, §18):
- the private manifest records `"reservation_fraction": "1/3"`, so the
  commitment covers the rule actually applied;
- the default of one half is unchanged and adds no manifest field; and
- unit tests check 30→10 and 8→3 with ceiling rounding per stratum.

The fraction is a command-line argument rather than a grouped-list field,
because the grouped-list schema is the frozen v0.2.0 schema. The default
half rule must never be used in place of 1/3. At the opening, the executor
checks that the manifest carries `reservation_fraction` = `1/3` (§7.4).

### 7.2 Procedure

The custodian runs the amended script in a plain terminal outside every
agent session. The input is the grouped list (§6), and the output goes
outside every Git worktree, as in protocol v0.2.0 §3.

### 7.3 Public record

The repository stores `docs/evaluation/reservation-commitment-v2.json`
containing:
- the commitment `SHA256(nonce ‖ canonical_selection_manifest)`;
- the SHA-256 of the canonical grouped list (`grouped_list_sha256`, already
  in the private manifest);
- the SHA-256 of the private search log and of the screen sheet;
- per-query counts (§3.3);
- per-stratum counts: candidates screened `pass`/`fail`/`unknown`, excluded
  for exposure, groups formed, groups eligible, groups reserved, and groups
  in the development set;
- the fraction and rounding;
- the draw timestamp as the custodian reports it; and
- the custodian attestation and signature.

The record must not contain any name, URL or group ID, or the nonce or
seed. The counts reveal nothing about membership and close the gap left by
the 2026-10-28 file.

### 7.4 Opening check (gate before evaluation)

After the tool freeze (§9), the custodian gives the evaluation executor the
nonce and the private manifest. The executor:
- recomputes the commitment and checks it against the public value;
- checks that `grouped_list_sha256` matches the grouped list the custodian
  provides; and
- checks that the reserved count equals the public count and that the
  manifest records `reservation_fraction` = `1/3`.

The executor records the result in the evaluation report. A mismatch stops
the evaluation, and the stop is reported. As in v0.2.0, the commitment shows
consistency with the opening. It does not show randomness or timing.

## 8. Development set for AI 1

### 8.1 Release

After the draw, the custodian releases to AI 1 the names and URLs of the
**non-reserved groups in the `noir-evm:eligible` stratum**. This is the
development set. Non-reserved groups in the `unknown` stratum stay unopened.
The custodian may later release them by a recorded decision.

AI 1 never receives the full frame, the grouped list, the search log or the
reserved list.

### 8.2 Permitted use

AI 1 may open, build, analyze and debug development projects without
restriction. Uses include:
- adding compiler versions or opcode support;
- fixing frontends; and
- writing validation harnesses.

Every development project becomes exposed for all future evaluations.
Changes motivated by the development set are ordinary development, not
held-out tuning.

### 8.3 Exposure log

AI 1 appends one record per access, in the format of taxonomy protocol §7.
AI 1 may open only projects in the released development set and projects
already exposed.

If AI 1 opens any other Noir/EVM repository, it logs the access. At the
opening (§7.4), the executor intersects AI 1's log with the reserved set,
and any reserved group that AI 1 accessed is reported as exposed. It is then
moved out of the reserved denominator. It is never silently dropped and
never kept as held-out.

Residual risk: AI 1 knows the frozen queries and could rerun them. AI 1's
instructions forbid running the frame queries. This constraint is
procedural, and the paper discloses it.

## 9. Tool freeze

Before the opening check, AI 1 freezes the evaluation tool. The freeze
consists of:
- a Git tag; and
- a file-hash manifest covering everything that can change a result: the
  analyzer, frontends, decoders, rule conditions, the effect table, the
  validation index and the evaluation driver.

A D1P-35-style freeze manifest is sufficient. The tag, manifest hash and
freeze timestamp are recorded before the custodian releases the opening.

After the freeze, no file in the manifest changes until every reserved
project has its single run. A post-run comparison must show every manifest
file byte-identical. Any later change makes a new tool version, and results
from that version on the reserved set are labeled as later attempts, never
as held-out first attempts.

## 10. Evaluation execution

### 10.1 Retrieval

Clone each reserved project recursively at the default-branch head on the
retrieval date. Record:
- the commit and tree hashes;
- every submodule SHA; and
- the clone exit status.

A deleted, private or unreachable repository is recorded as
`retrieval_failed` and stays in the denominator.

### 10.2 Build rules (fixed now)

**Producer:**
1. Use the exact project pin if there is one: `compiler_version` exact, or a
   CI or toolchain file.
2. Otherwise, make one attempt with the version that the project's own
   lockfiles, CI or documentation evidence (as for IP-NFT, D1P-33 §3).
3. Otherwise, make one attempt with the latest stable Noir release at the
   freeze date.

**Consumer:**
1. Use the project's Foundry or Hardhat configuration and its `solc` pin.
2. Otherwise, use the default resolution.
3. A scoped build of the consumer and verifier contracts is permitted after a
   failed full build (as for e-voting, D1P-36 §3).

**General:**
- No source patch is made to obtain a build.
- At most three build attempts per side, and 120 minutes of active build
  time per project.
- Every attempt is preserved with its command, versions, exit status and
  log hash.
- If the build fails, the project is recorded as `build_failed` with a
  named reason and stays in the results.

### 10.3 Target-pair selection (fixed now)

An analysis target is a pair of one compiled Noir `bin` package and one
consumer contract that calls a verifier. The executor determines the pairs
at analysis time:
1. List the `bin` packages that compiled.
2. List the Solidity contracts whose source contains a call to a function
   taking `(bytes, bytes32[])`, or to a contract generated by bb.
3. Pair packages with consumers using evidence from the project's own
   deployment scripts, tests, imports, or the verifier key embedded in the
   generated verifier.
4. Analyze every determinable pair, up to five per project, in lexicographic
   order of package path. Pairs beyond five are recorded as `not_analyzed:
   cap`.
5. If no pair can be determined, record `no_pairing_determined` with the
   reason.

### 10.4 Single run

Each pair gets **exactly one** invocation of the frozen `bindcheck analyze`.
- **Exit:** the result is final whatever the exit status.
- **Wall cap:** 30 minutes. A timeout is `UNKNOWN (timeout)`.
- **Setup retry:** an environment failure that prevents the tool process
  from starting (for example the missing `PYTHONPATH` in D1P-33 §2) may be
  fixed and retried once, with both attempts recorded.
- **No rerun:** once the tool process has started and returned, it is not
  rerun.

Any consumer relation the run needs is generated by the frozen driver and
counted as a manual analysis input. Not even a diagnostic re-invocation of
the analyzer is permitted. A separate extractor diagnostic, like D1P-36's
for NullProof, is allowed only if the tool's own driver does not depend on
it, and it is labeled as a diagnostic.

### 10.5 Analysis-time facts (reported for every project)

| Fact | Values |
| --- | --- |
| Producer compiler actually used, and how it was chosen (§10.2) | version, rule step |
| Producer and consumer build outcome | `ok`, `scoped_ok`, `failed:<reason>` |
| Generated verifier present in the checkout | yes or no, with path |
| Verifier corresponds to the rebuilt circuit (regenerate with pinned bb, compare VK hash) | `match`, `mismatch`, `stub`, `undetermined` |
| Consumer verifier-boundary count | integer, or `undetermined` |
| Producer-to-verifier public-input mapping | `established` (full-width identity), or the named fail-closed reason, e.g. `SOLIDITY_PUBLIC_INPUT_MAPPING_AMBIGUOUS` |
| Dynamic-memory dependencies on public leaves | `none`, `exact`, or `UNSUPPORTED_DYNAMIC_MEMORY_DEPENDENCY` |
| Recursion present (named black box) | yes or no |
| Other unsupported operations named by the tool | list |
| Pairs determined, analyzed and capped | counts |
| Tool result per pair | `completed` / `unsupported:<named reason>` / `error:<reason>` / `timeout` |

### 10.6 Baseline arms on the reserved set

Contract §9 requires both arms wherever a baseline applies. The generic arm
runs on the same pairs, once each:
- **Noir compiler warnings.** These come from the producer build log, with
  no extra run. They matter because the pinned Noir compiler's
  unused-variable warning matched every circuit-side BindCheck detection on
  the development benchmark (D1P-32; D1P-41 §5).
- **Slither 0.11.6** in its default configuration on the consumer.

Circom-only tools such as ZKAP, Circomspect and CIVER are recorded as `U`
(input language not accepted), without adapting them. The same-policy arm
does not apply, because no reviewed policy exists for an
unseen project before analysis. Writing one after seeing BindCheck's output
would not give an equal-information comparison. It is recorded as `not
applicable` with that reason.

Baseline outputs are scored on the D1P-32 scale (D, E1, M, U, R) after
BindCheck triage is sealed. A baseline warning that names the same word or
location as a BindCheck warning is recorded as an overlap.

## 11. Retention

Every reserved project stays in every results table, from the draw to the
final report. This includes projects with failed retrieval, failed builds,
no pairing, unsupported analyses, tool errors, timeouts and AI 1 exposure
(§8.3). No reserved project is replaced, resampled or excluded after the
draw. All denominators are the reserved count.

## 12. Outcome counts (reported separately, never combined)

| Count | Definition | Denominator |
| --- | --- | --- |
| **Completed analyses** | Pairs or projects where the frozen tool evaluated every R-* rule and wrote a result, with or without warnings | Analyzed pairs; reserved projects (a project counts as completed if at least one of its pairs completed) |
| **Unsupported / error / timeout** | Each with its named reason | Same as above |
| **Warnings** | Warning objects emitted by completed analyses, by rule | Completed analyses |
| **Triage outcomes** | §13 categories | Warnings |
| **Validated warnings** | Highest E-level reached, each with its causation contrast (§13.4) | Warnings triaged `plausible issue` or `unclear` |
| **Confirmed defects** | Defined in §13.5 | Reserved projects |

Silence on a completed analysis is E0 and is not `VERIFIED_WITHIN_SCOPE`. An
unsupported analysis is not a miss and is not evidence of safety. No
percentage is formed across counts with different denominators.

With about 10 projects, no rate is estimated. Counts are reported with their
exact denominators. An exact binomial interval may accompany the completion
count, labeled descriptive.

## 13. Human triage and validation

### 13.1 Procedure

1. The evaluation executor prepares one packet per warning. A packet holds
   the warning JSON, the cited source spans, and the project's own
   documentation for the word or effect involved. It holds no E-level,
   baseline output or other label.
2. Two human triagers label each packet independently and seal their labels
   before seeing each other's.
3. A third human adjudicates disagreements, citing the rule and the
   evidence. Original labels are kept.
4. If only one human is available, the triage is labeled *single-rater* in
   every table. Agreement is then not reported, and that is disclosed.
5. Triage is sealed before any validation starts.

### 13.2 Step 1: is the structural fact true?

Each warning states a structural fact. For example:
- "public word *k* has no proof-enforced occurrence" (R-BIND);
- "calldata word *k* reaches no guard, state or effect" (R-CONSUMER); or
- "replay key lacks its guard or write" (R-POLARITY).

Triagers check that fact against the artifact and source: `true`,
`false` or `undetermined`.

### 13.3 Step 2: categories

| Category | Rule |
| --- | --- |
| **false warning** | The structural fact is false, for example because the word is constrained or used. This is a tool error |
| **intended design** | The fact is true, and the project's source or documentation shows the binding is deliberately absent or enforced elsewhere, with no policy violation following. An example is Payy's off-chain `commit_hash` placeholder |
| **plausible issue** | The fact is true, nothing documents why, and a committed effect or omitted obligation could plausibly follow under the project's stated policy |
| **unclear** | The fact is undetermined, or the policy cannot be established from public material |

Each label records a rationale and a source pinpoint. AI output never
supplies a label.

### 13.4 Validation (AI 4)

**Scope:**
- every `plausible issue` warning, and `unclear` warnings if budget remains;
- in rule-ID order;
- at most two per project; and
- 8 hours of active time per warning.

**Runs:** owned-local only, with synthetic assets, under the evidence
ladder of contract §8.

**Causation contrast.** Following the
[policy review](../validation/policy-review-2026-10-30.md), an E4 counts
only if it shows that the warned binding, not the setup or an inherited
defect, causes the effect. The same transaction must be run with matching
keys and identical initial state on the original version and on a version
repaired at the warned binding. A held-out project has no "defective
variant", so the comparison is between the original and a minimal repair
that adds the missing binding. That repair is validation scaffolding, not a
change to the tool.

Three rules from the [evidence ledger](../x-experiment/EVIDENCE-LEDGER.md)
§0 and TE05 apply:
- verification failure under a *different* key is not a contrast;
- a run that reverts at a consumer gate *before* the verifier call says
  nothing about proof acceptance, and is recorded as uninformative, not as a
  contrast; and
- a run whose proof acceptance comes from a mock verifier is graded
  `E1+mock`, never E2 or above.

An E4 without a valid contrast is reported as `E4, causation pending`.
Manual steps are counted.

### 13.5 Confirmed defect

A **confirmed defect** must satisfy all of the following:
- the warning was triaged `plausible issue` after adjudication;
- it reached E4 with the causation contrast; and
- a human author reviewed it against the project's stated policy.

Maintainer acknowledgment is reported as a separate count. A confirmed
defect supports a submission claim only after responsible disclosure
(contract §9).

## 14. Deviations and amendments

| ID | Change | Relative to |
| --- | --- | --- |
| A-V2-1 | Reserve one third, rounded up per stratum, instead of the default half. Needs prerequisite P1 | Taxonomy protocol §3 "Private family draw" |
| A-V2-2 | The public record adds counts and the hashes of the grouped list, search log and screen sheet, still with no membership | Taxonomy protocol A04 |
| A-V2-3 | The frame is a GitHub search for Noir/EVM projects, not a disclosure index traversal. This evaluation concerns tool transfer, not disclosure taxonomy | Taxonomy protocol §1 |
| A-V2-4 | The custodian may read `Nargo.toml` and file listings to screen. This is metadata beyond names, so it is logged as custodian exposure | Taxonomy protocol §3 "Name-only enumeration" |

## 15. Safety and disclosure

- No transaction is broadcast, no live system is tested, and no maintainer
  is contacted without explicit authorization (AGENTS.md).
- Validation runs only on fresh local chains.
- A confirmed defect is disclosed to its maintainers before any submission
  claim. The report names the project only after disclosure is resolved.
- Raw evidence goes under ignored `results/raw/<task>/`. Tracked reports
  summarize it.

## 16. Report tables (templates)

**Table E1: frame funnel.** Rows: raw hits per query; unique repositories;
kept after post-filters; screened `pass`/`fail`/`unknown`; excluded for
exposure (by heading); groups formed; eligible groups; reserved;
development set.

**Table E2: per reserved project.** Columns:
- anonymized ID;
- stratum;
- declared compiler-version class;
- compiler used;
- build outcome;
- verifier correspondence;
- boundary count;
- recursion;
- pairs analyzed;
- tool result and named reason;
- warnings;
- triage outcomes;
- best E-level with its causation contrast; and
- baseline overlap.

**Table E3: counts.** One row for each count in §12, with its denominator.
These counts are never combined.

**Table E4: prior attempts (not relabeled).** D1P-33 completed 0/4 analyses,
and D1P-36 completed 0/8. No rule ran in either. Both are reported as
separate strata.

## 17. Permitted claims

| Result | Permitted statement |
| --- | --- |
| 0 completed analyses | "The frozen tool completed no analysis on *n* reserved projects." Report the named stopping reasons. This is not a miss rate or a safety statement |
| ≥1 completed analysis | "The frozen tool completed *c* of *n* analyses on projects reserved before development." Warning counts and triage are reported. Transfer is shown only for what was triaged and validated |
| ≥1 confirmed defect | Capability-gate item (d) evidence, subject to disclosure. The paper must still compare with the baseline arms (§10.6) |
| Completed analyses with no warnings | E0 per project. Not `VERIFIED_WITHIN_SCOPE` |

No prevalence or ecosystem claim follows from a frame of this size or from
GitHub search.

## 18. Prerequisites and completion criteria

| Step | Owner | Completion criterion |
| --- | --- | --- |
| P1: fractional draw support | Integrator | **Implemented, uncommitted (30 October 2026).** `reserve_families.py --fraction p/q`; non-default fractions are recorded in the private manifest; `scripts/taxonomy/test_reserve_families.py` passes 9/9, including 30→10 and 8→3 per stratum and a default-unchanged check. Becomes DONE when committed |
| P2: freeze this protocol | Two planners and the custodian | Approval block (§19) filled against the recorded SHA-256, before any query runs |
| S1: search and screen | Custodian or search operator | Search-log and screen-sheet hashes published, with per-query and per-stratum counts |
| S2: draw | Custodian | `reservation-commitment-v2.json` committed with counts, hashes and a signed attestation |
| S3: release development set | Custodian → AI 1 | Release recorded with count and date. AI 1 exposure log started |
| S4: tool freeze | AI 1 | Tag and manifest hash recorded before the opening |
| S5: opening check and evaluation | Evaluation executor | Opening check passed. One run per pair. Post-run byte-identity of frozen files. All §16 tables filled for every reserved project |
| S6: triage | Human triagers | Sealed labels and adjudication record |
| S7: validation | AI 4 | Every eligible warning has an E-level and a causation-contrast status |

The venue dates (abstract 10 November 2026, paper 17 November 2026) are
external constraints. If S5 cannot finish in time, the paper
reports the stages that are done and the stage at which the protocol stopped.
It must not substitute a smaller frame.

## 19. Approval block

**Hash rule.** `protocol_sha256` is the SHA-256 of this file's UTF-8 bytes
from the first byte up to, but not including, the line `## 19. Approval
block`. Filling in this block does not change the hash. Any edit above the
line does, and voids every approval recorded below. Recompute with:

```sh
python3 -c "import hashlib,sys; b=open(sys.argv[1],'rb').read(); \
print(hashlib.sha256(b[:b.index(b'## 19. Approval block')]).hexdigest())" \
  docs/evaluation/independent-protocol-v2.md
```

```text
protocol_sha256: cd80f5f7f1eb555caeb566a140f03d8ad880b96bba6d89a132d708dacfb99d9d
recorded:        2026-10-30 by AI 3 (computed, not an approval)
```

| Role | Identity | Decision | Date (UTC) | Scope approved | Note |
| --- | --- | --- | --- | --- | --- |
| Planner 1 | | | | | |
| Planner 2 | | | | | |
| Custodian (human) | | | | | |

Do not invent an identity, signature or date to fill this table (taxonomy
protocol §6). Leaving it empty means the protocol is not frozen.

