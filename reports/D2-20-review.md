# D2-20 — evidence-review audit and correction disposition

Date: 2 November 2026

Status: **EVIDENCE_AUDIT_COMPLETE_NO_NEW_EXPERIMENT**

Research verdict: **UNKNOWN**

Gate state: **Gate A `INCONCLUSIVE`; Gate B `NOT_EVALUATED`; Gate C
`NOT_REACHED`**

## 1. Outcome

The three PDF-only reviews identify serious missing evidence, but no factual
contradiction in the reviewed D2 status manuscript. The dominant result is
therefore a correction plan, not a correction of primary results.

No versioned correction to `paper/d2-status-draft.md` or
`output/pdf/bindcheck-d2-evidence-status.pdf` is justified. Their central
claims already say that current capability, comparative advantage, transfer,
novelty, and submission readiness are unresolved. The bound Step 18
manuscript, claim map, PDF, and review bytes remain unchanged.

The audit deduplicates the reviews into 12 concerns:

| Primary class | Count | Immediate meaning |
|---|---:|---|
| Writing correction | 1 | Improve reader-facing denominators and packet/reproduction pointers only in a future explicitly versioned manuscript. |
| Existing-data analysis | 4 | Derive coverage/multiplicity, resolve the repository-level historical Payy grade, and incorporate Step 19 reproduction without changing primary rows. |
| New experiment | 5 | Formal semantics/extraction, human policy, byte-level identity/decode, current E1-to-E4 validation, and fair comparison/cost remain unperformed. |
| Enduring limitation | 2 | Practical scope and novelty/closest-work delta remain unresolved. |

No scored row, evidence grade, exposure class, Gate result, or research verdict
was changed. No new experiment, analyzer, baseline, compiler, prover, reserved
input, or human judgment was run.

## 2. Bound review and reproduction inputs

| Input | SHA-256 | Audit use |
|---|---|---|
| Contract-security PDF review | `218697c92f7d3aa27c76f232b1c9cf040acbbc3883055678500c5509572c3e2f` | Threat model, semantic trust, policy, identity/decode, scope, Payy E4, and negative-verdict concerns |
| Empirical-validity PDF review | `d399bec88bd4f26cb115f7e2e2a6b8b67c9ba26ff0b97518d9796f57820bfba4` | Units, denominators, missingness, clustering, exposure, warning multiplicity, comparison, cost, and independence |
| ZK-methodology PDF review | `751643b672fecafeebd1ad9372202066d25e0dd385828734412c4ff45715d2ec` | Formal target, byte-level binding, mechanical identity, sealing, causality, transfer, novelty, and scope |
| Reviewed nine-page PDF | `1697834e0c47de365ad04f8a1108dfd21555af5c7af9e697759d44e5b9f1e12d` | Exact reviewed artifact; all nine rendered pages were inspected and were legible without claim-changing clipping or overlap |
| Step 18 status manuscript | `a1c906e19a3cc8fddf2ffd66afb4f49d95dd7476832e55671223b20b3e2660d7` | Claim wording and qualifications |
| Step 18 claim ledger v2 | `78ec90b4e0c6f2e68fb8f43237b372b8a8dbcd723680ec5dceacd0ee6ce219a9` | Twenty inherited claims |
| Step 18 claim map v1 | `c3cfa1ea2acce7635ca8f67ff8d980044ae21d8c6097daa085254fdc30be3567` | Manuscript-to-evidence mappings |
| Step 19 artifact report | `5130a31fa4bee267013e1cfd43a058fbac833e45cd3511fb59e75e84396bdf63` | Partial-development artifact boundary |
| Step 19 reproducer | `1973a850466aee837fbd05c14bac216f424c95db3fa0eb6c0c1d3f3bbe9d6d91` | Bound fail-closed driver |
| Step 19 checksum list | `7d11a8d8f646f0f08c756ab58f193c9ce52e8c3b16efd9f53ce790847081dc38` | Artifact-owned bytes |
| Fresh reproduction report | `61b6f8a78363c32c626d0e582d673cce2dcaa9c455af565ac61826028bc0e444` | Four-profile same-host reproduction result |

The fresh evaluator observed all four requested profiles as `PASS` with no
unexpected mismatch: metadata, current-workspace retained verification,
recompute, and a fresh mechanical rerun. It was a fresh AI session on the same
host and checkout, not a sidecar run, clean container, fresh machine,
anonymous evaluation, or independent human replication. It did not rerun the
generic D2-01 or D2-06 experiments and did not establish semantic correctness.
The artifact remains exactly
`PARTIAL_DEVELOPMENT_ARTIFACT / FINAL_ARTIFACT_BLOCKED`.

The machine-readable concern inventory binds 64 review, manuscript, report,
protocol, raw-summary/seal, and artifact files with their observed sizes and
SHA-256 values.

## 3. Missing evidence versus contradiction

The reviews use “missing” and “contrary” in materially different ways. This
audit preserves that distinction.

- **No current-manuscript contradiction:** all 12 concerns set
  `contradicts_current_status_manuscript=false`. The manuscript already
  reports `UNKNOWN`, Gate A `INCONCLUSIVE`, no score, no transfer, and no
  submission-ready result.
- **Contrary evidence against stronger readings:** zero eligible Step 10
  producer/effect relations contradict a claim that the current automatic
  capability already exists; one supported lineage contradicts a claim of
  demonstrated two-lineage performance; existing closest-work overlap
  contradicts broad novelty language; and a superseded sealed run contradicts
  treating seals as semantic proof.
- **Missing evidence:** formal extraction/authorization soundness, human policy
  and exact effect grounding, byte-level decode/provenance, current causal
  E1-to-E4 execution, a fair comparison, total cost, supported independent
  transfer, and practical-scope coverage do not exist.
- **PDF-only versus repository evidence:** the PDF does not contain a
  self-contained Payy packet or independently replayable hashes. Repository
  reports and Step 19 can resolve some byte/evidence-location questions without
  converting the PDF into a self-contained or independent replication.

This is why the audit retains the status manuscript while still recording
five concrete experiment dependencies.

## 4. Central claim and denominator audit

| Claim/result | Verified version, exposure, and grade | Exact denominator/status | Consequence |
|---|---|---|---|
| Qualified relational thesis | Research-contract framing; no empirical grade | “Some” judgments may require producer, decode, consumer, and reviewed-policy relations | Framing, not novelty or capability |
| Integrated development interface | D2-01 authoritative recovery; exposed development; E1 | 30 targets; 17 detected/supported; 13 unsupported/UNKNOWN; 0 misses within the frozen supported association disposition; 26 warnings; 23 associated; 3 unassociated | No precision, recall, prevalence, transfer, or security result |
| Coverage/missingness | Existing-data derivation from unchanged D2-01 rows | 17/30 = **56.7%** supported/detected; 13/30 = **43.3%** unsupported/UNKNOWN | All 17 supported/detected targets are WarpToad; current supported results span one effective lineage |
| Versioned benchmark rows | D1P-34, D1P-42, D2-01; E1 | 16/14/0/53; 11/19/0/13; 17/13/0/26 with 23 associated | Changed analyzers; not a trend |
| Corrected ablation | D1P-43 reconciled by D2-01; exposed E1 | producer 3/7, consumer 2/7, unjoined 5/7, full 7/7; E8 UNKNOWN; one matching control | Motivation only; no fair advantage or novelty |
| Historical Payy tail chain | T15/T18/T19; post-disclosure historical development; E4 | One candidate and one repair/legitimate-control contrast | Known mechanism only; not current discovery, current-warning validation, mutant coverage, transfer, or prevalence |
| Step 6 construction/smoke | D2-06A/B; E0/E1 smoke | 78 arm rows = 72 supported + 6 UNKNOWN; no score | Construction facts only |
| Gate A | D2-07 authoritative recovery; NO-SCORE | 13 candidate cases; 6 internal arms; 11 external inventory entries; 0 scored arms; empty objective subset and score rows | `INCONCLUSIVE`, not a tie or negative result |
| Steps 8-10 | `UNREVIEWED_DEVELOPMENT_FIXTURE`; E0 mechanical | Step 8: 5 bundles; Step 9: 10/10 effective UNKNOWN; Step 10: 0 producer guarantees and 0 eligible derived consumer-use facts | No E2-E4, policy verdict, or scored analyzer claim |
| Independent/taxonomy evidence | Unsupported attempts and no-study records | 12 attempts / 8 projects / 4 repeats / 0 supported analyses; 0 D2 human ratings | No transfer, generality, or human-study claim |
| Downstream gates | Read-only audits | Gate B score rows 0; Gate B not evaluated; Gate C not reached | No frozen evaluated release or reserved result |
| Step 19 reproduction | Fresh AI session, same host/workspace; engineering reproduction | 4/4 profiles PASS; 0 unexpected mismatches; 0 sidecar runs | Partial byte/categorical reproducibility only |

The warning counts require particular care. Twenty-three associated warning
objects over 17 detected targets are repeated warning-level observations, not
23 independent correct predictions. The three unassociated warnings are not
automatically false positives. There is no safe-effect denominator or
independently adjudicated confusion matrix.

## 5. Deduplicated concern dispositions

| ID | Primary class | Evidence relation and exact consequence | Required unblock |
|---|---|---|---|
| D2-RC-001 | New experiment | Formal authorization, extraction soundness, and completeness are missing; no current VIOLATION or VERIFIED_WITHIN_SCOPE can rest on the prototype | Freeze a supported fragment and supply formal judgments, rule obligations, translation validation/mechanized proof, and adversarial differential tests |
| D2-RC-002 | New experiment | Human-adopted/reviewed policy and exact protected-effect grounding are missing; Gate A and all current fixtures remain unresolved | Human policy author/adopter, distinct pre-output reviewer, exact P/O/E effect binding, independent scoring and adjudication |
| D2-RC-003 | New experiment | Source/compiler/key/ABI/deployment identity and executable decode validation are missing | Complete canonical provenance chain plus wrong-key/domain, encoding, limb, width, index, and substitution controls |
| D2-RC-004 | New experiment | Current automatic E1-to-E4 causal evidence is absent and zero eligible relations are contrary to any stronger present-capability claim | One frozen actual application carried automatically through extraction, proof, unchanged consumer effect, policy adjudication, repair, and legitimate control |
| D2-RC-005 | Existing-data analysis | Conditional support is 56.7%, UNKNOWN 43.3%, and supported outcomes occupy one lineage; zero misses is not recall | Publish the target-level support table now; future transfer needs reserved independent supported families and family-level analysis |
| D2-RC-006 | Existing-data analysis | Warning multiplicity and three unassociated warnings can be reconstructed, but no precision denominator exists | Publish the complete warning-to-target/effect mapping, then run frozen positive/safe controls with independent adjudication |
| D2-RC-007 | New experiment | Gate A has no eligible row and cost is unmeasured; neither advantage nor tie was tested | Frozen equal-policy/equal-information arms and applicable closest-work arms with full human/AI/machine/setup/failure cost ledger |
| D2-RC-008 | Existing-data analysis | Repository evidence retains historical Payy E4, but the reviewed PDF is not self-contained or independently replayed | Publish an approved case packet with policy, roles, artifacts, proof, pre/post-state, causal contrast, and independent replay if making more than a historical claim |
| D2-RC-009 | Enduring limitation | The one-transition fragment excludes common contract behaviors; broader practical coverage is unmeasured | Machine-checkable supported-fragment specification, corpus coverage, and fail-closed tests before scope expansion |
| D2-RC-010 | Existing-data analysis | Step 19 strengthens byte/categorical reproduction; the old sealed-run defect still shows seals are not semantic proof | Approved sidecar, clean-machine and independent human replay, plus an independent semantic validator |
| D2-RC-011 | Enduring limitation | Broad novelty is precluded by known overlap and the narrow delta is untested | Primary-source/artifact inspection and fair same-policy comparisons before stating a residual delta |
| D2-RC-012 | Writing correction | Existing facts are accurate but a future version can surface coverage, clustering, multiplicity, Payy packet, and Step 19 scope more directly | Make only an explicit next-version prose/table update; preserve all versions, exposures, and evidence grades |

The exact review-heading mapping, consequence text, and unblock experiment for
each concern are in
`docs/mock-reviews/d2-review-concerns-v1.json`.

## 6. Historical Payy E4 disposition

The PDF-only reviews correctly say that the grade cannot be independently
checked from the PDF. The repository-level audit found the necessary existing
layers:

- T15 binds a real accepted proof for the earlier artifact and a same-witness
  rejection at the check-added revision.
- T18 runs the unchanged earlier local consumer with owned prover/validator
  identities and checks the committed seven-token state delta directly.
- T19 replays the repair rejection and a legitimate check-added control.
- `docs/validation/policy-review-2026-10-30.md`
  (`ca821c23c84ecd3c435f72acd5f1217e39184be8ca513b9f6147d7b59571a0cf`)
  records the author-reviewed Payy withdrawal policy and the inherited-tail
  attribution correction.

This supports retaining **historical E4 for the known, post-disclosure local
mechanism**. It does not create independent review, current automated
discovery, current-warning validation, deployment impact, mutant coverage, or
transfer. A public/self-contained use still needs the case packet in
D2-RC-008.

## 7. Claim-ledger revision and manuscript decision

`docs/d2/claim-ledger-v3.json` is a complete versioned successor to v2. It
preserves all 20 inherited claims and their statuses, adds a review disposition
to every inherited claim, and adds two post-Step18 claims:

1. the scoped four-profile Step 19 reproduction result; and
2. the derived 56.7%/43.3% coverage split and effective one-lineage supported
   result.

The v3 status counts are 15 supported, 3 contradicted, and 4 unresolved over
22 claims. “Contradicted” retains v2's deliberately prohibited stronger
statements; it does not mean the Step18 status manuscript is contradicted.

Artifact hashes before this report was written:

- concern inventory:
  `d66a84c01dbdfb683c6610a0d090d4313e977723826ca600c8875c711941775f`;
- claim ledger v3:
  `08b2dad5eae7d99635e58209eed25e0de6bc54a1de581afe1ead43fb68c8c8ad`.

**Manuscript correction decision:** no concrete factual contradiction justifies
a versioned correction, and no Step18-bound file was edited. D2-RC-012 is a
future writing improvement only. Any future manuscript update must be an
explicit new version and must not silently replace the reviewed PDF.

## 8. Validation

Completed validation:

- all 151 repository unit tests passed with
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv-d1p-00/bin/python -m unittest discover -s tests -v`;
- both new JSON documents parsed and passed their count/status/reference
  assertions;
- the concern inventory contains 12 unique IDs, four exact primary classes,
  64 non-null source bindings, and zero current-manuscript contradictions;
- claim ledger v3 contains 22 unique claim IDs, review dispositions for every
  claim, and the exact 15/3/4 status split;
- every source binding in the concern inventory was rehashed against the
  current byte and size;
- the three reviews, PDF, Step18 manuscript/ledger/map, Step19 package/report,
  and fresh reproduction hashes matched their declared values;
- focused whitespace and `git diff --check` checks passed for the three
  Step20 files.

No raw namespace or seal is created for this documentary audit. The result
remains `UNKNOWN`.
