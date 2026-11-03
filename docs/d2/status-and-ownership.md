# D2 status, ownership, and reproduction registry

**Status:** Steps 0–10 complete only within bounded scopes; Steps 11–17 have read-only audits and were not executed; Gate A is `INCONCLUSIVE`, Gate B is `NOT_EVALUATED`, Gate C is `NOT_REACHED`; Step 18's documentary status manuscript is complete but `NOT_SUBMISSION_READY`; Step 19 is `PARTIAL_DEVELOPMENT_ARTIFACT / FINAL_ARTIFACT_BLOCKED`; Step 20's evidence audit is complete; D2 research claims remain `UNKNOWN`

**Authority:** `docs/research-contract.md`, then `README.md`, then immutable reports

**Development boundary:** [`protocols/d2/development-boundary-v1.json`](../../protocols/d2/development-boundary-v1.json)

This record maps the repository that exists. It does not authorize a new
architecture, reserved-data access, or a research conclusion. The integration
lead owns shared interfaces and merges; workers own only their assigned task
files and raw namespace unless this table says otherwise.

## Actual modules and interface ownership

| Surface | Existing location | Owner | Coordination rule |
|---|---|---|---|
| Public CLI | `src/bindcheck_d1/cli.py`, `bin/bindcheck` | integration lead | CLI/schema changes require integration review and focused compatibility tests. |
| Cross-layer static analysis | `src/bindcheck_d1/static_analyzer_v1.py` | core-method owner; integration lead is interface owner | Preserve `VIOLATION` / `VERIFIED_WITHIN_SCOPE` / `UNKNOWN`; no worker adds rules through a runner mask. |
| Integrated development interface | `src/bindcheck_d1/integrated_analyzer_v1.py`, `scripts/d2_step1_integrated.py` | integration lead | Compose existing rules only; preserve component support/provenance, stable/source IDs, frozen association scoring, and legacy CLI compatibility. |
| Typed role correspondence | `src/bindcheck_d1/role_binding.py` | core-method owner | Consume the documented analyzer facts; do not bypass extraction gates. |
| Compiler-backed object/context identity | `src/bindcheck_d1/roles/compiler_identity_v1.py`, `scripts/d2_step8_identity.py` | core-method owner | Security identity uses canonical object/context bytes; names, source lines, and display provenance do not determine it. |
| Authorization boundary | `src/bindcheck_d1/core/authorization_boundary_v1.py`, `scripts/d2_step9_authorization_boundary.py` | core-method owner + policy reviewer | Fail closed on absent or unreviewed policy; mechanical fixtures are `UNREVIEWED_DEVELOPMENT_FIXTURE` and unscored. |
| Typed extraction trust | `src/bindcheck_d1/typed_extraction_v1.py`, `scripts/d2_step10_typed_extraction.py` | extraction owner | Preserve quantifier, condition, approximation, derivation, support, identity, mapping, and provenance uncertainty; corrected protocol v2/run-02 controls. |
| Producer frontends and recursive mapping | `src/bindcheck_d1/frontends/acir_*`, `recursive_public_mapping_v1.py` | extraction owner | Changes require positive/negative semantic controls and provenance. |
| Consumer extraction | `src/bindcheck_d1/frontends/solidity_ast_v1_1.py` and related frontend modules | extraction owner | Fail closed on unsupported paths; effect-table changes require explicit protocol review. |
| Evidence validation | `src/bindcheck_d1/validation_v1.py`, `src/bindcheck_d1/xav_core.py`, `scripts/xav*` | validation owner | Evidence grades follow contract §8; mock components cannot promote E1 to E2. |
| Development benchmark | `benchmarks/binding-mutants/`, `scripts/d1p_31_*`, `scripts/d1p_34_*` | evaluation owner | Labels and denominators are sealed before scored execution. |
| Ablations | `scripts/d1p_41_ablation_preliminary.py`, `scripts/d1p_43_role_ablation_preliminary.py`, `docs/ablations/` | evaluation owner | D1P-41 and D1P-43 remain separate versioned experiments. |
| Baselines | `baselines/foundry/`, `docs/baselines/`, `paper/baselines.md` | baseline owner | Generic/default and same-policy arms receive equal information and validation opportunity. |
| Historical D1 artifact reproduction | `scripts/artifact/fetch_inputs.*`, `scripts/artifact/reproduce.py`, `ARTIFACT.md` | artifact owner | Preserve pinned inputs and historical expected results; do not silently substitute tools. |
| D2 partial development artifact | `artifact/`, `reports/D2-19-artifact.md`, `reports/D2-19-fresh-reproduction.md` | artifact owner | Same-host development reproduction only; no final artifact, sidecar, container-portability, anonymity, or independent-human claim. |
| D2 evidence review | `docs/mock-reviews/`, `docs/d2/claim-ledger-v3.json`, `reports/D2-20-review.md` | review owner | Preserve the Step 18 manuscript/PDF bytes; missing-evidence concerns are not factual contradictions or new experiment results. |
| D2 coordination primitives | `scripts/d2_foundation.py`, this document, `protocols/d2/` | integration lead | Run manifests and seals are coordination evidence, not research results. |
| Tests | `tests/`, `tests/d1/` | module owner for focused tests; integration lead for suite gate | Record unavailable ignored inputs or dependencies as blockers, not passing tests. |
| Living status | `README.md`, `docs/project-status.md` | integration lead | Update only when a bounded task changes project state; preserve earlier rows. |
| Immutable evidence reports | `reports/` | assigned task author; integration lead reviews | Never rewrite a completed report to match a later conclusion. |

## Shared interfaces parallel workers must preserve

1. Analysis records remain source- and artifact-hash bound and expose named
   unsupported reasons. Warning identity must not depend on adjudication.
2. Producer, mapping, consumer, role, policy, and validation provenance remain
   separate fields; an analyst-supplied role is not an extracted fact.
3. D1P-40 corrected facts control later runs. D1P-41 and D1P-43 retain their
   original datasets and denominators when cited.
4. Every experiment writes new raw evidence under its own ignored namespace
   and a new tracked report; it never overwrites a frozen run.
5. Any shared CLI, schema, benchmark dispatcher, or artifact materializer
   change is owned and integrated by the lead after worker handoff.

## Step ownership and dependencies

| Step | Owner | Prerequisites | Principal tracked output | State |
|---:|---|---|---|---|
| 0 | integration lead | repository and current instructions | this record, development boundary, manifest/seal tool, `D2-00` report | DONE at foundation level |
| 1 | integration lead + core/interface owners | Step 0; D1P-40/41/42/43 | integrated analyzer, reconciled machine-readable table, `D2-01` report | DONE for exposed development scope |
| 2 | inventory worker | permitted metadata; Step 1 before analyzer triage | population/family/blocker ledger | DONE for bounded exposed-development inventory |
| 3 | evidence/positioning worker | existing evidence; Step 1 results when ready | claim ledger and related-work matrix | DONE for documentary claim/primary-source audit |
| 4 | taxonomy worker | existing taxonomy evidence | codebook, blank packets, agreement implementation | DONE for preparation; human corpus/labels remain separate |
| 5 | evaluation worker | Steps 1 and 3 | prospective early-comparison protocol and effort log | DONE for protocol drafting; `DRAFT_UNSEALED_DO_NOT_SCORE` |
| 6a | baseline worker | Step 5 draft | composition baselines and transformation controls | DONE for construction/smoke only; unscored and `UNKNOWN` |
| 6b | baseline/validation worker | Step 5 draft | same-policy and applicable external comparators | DONE for construction/smoke only; report-local unsealed/do-not-score bytes later included in the Step 7 recovery seal |
| 7 | evaluation lead | Steps 5, 6a, 6b | authoritative recovery packet and Gate A disposition | DONE; recovery seal `PASS`, Gate A `INCONCLUSIVE`, zero scored rows, research `UNKNOWN` |
| 8 | core-method owner | Gate A bounded-prototype authorization | compiler-backed semantic object/context identity prototype | `COMPLETE_MECHANICAL_ONLY`; `UNREVIEWED_DEVELOPMENT_FIXTURE`, unscored, `UNKNOWN` |
| 9 | core-method owner + policy reviewer | relevant Step 8 semantics | common authorization-boundary prototype | `COMPLETE_MECHANICAL_FIXTURE_ONLY`; E0, zero score rows, `UNKNOWN` |
| 10 | extraction owner | frozen Steps 8–9 interface | corrected typed extraction-trust prototype | DONE for bounded protocol v2/run-02; zero producer guarantees, zero eligible derived consumer-use facts, unscored, `UNKNOWN` |
| 11 | frontend owner | new authorization beyond Step 10 | `D2-11-14` dependency audit only | READ-ONLY AUDIT DONE; scientific Step 11 NOT EXECUTED |
| 12 | evaluation lead + custodian | reviewed policy, labels, controls, custody, new authority | `D2-11-14` dependency audit only | READ-ONLY AUDIT DONE; scientific Step 12 NOT EXECUTED |
| 13 | validation owner | eligible actual guarantee/reliance, reviewed policy, frozen procedure, new authority | `D2-11-14` dependency audit only | READ-ONLY AUDIT DONE; scientific Step 13 NOT EXECUTED |
| 14 | integration/evaluation leads | completed Steps 11–13 and separate run authority | `D2-11-14` dependency audit only | READ-ONLY AUDIT DONE; scientific Step 14 NOT EXECUTED; Gate B `NOT_EVALUATED` |
| 15 | custodian/evaluator | Gate B `PASS`, frozen release, isolated handoff | `D2-15-17` readiness audit only | READ-ONLY AUDIT DONE; scientific Step 15 NOT EXECUTED |
| 16 | independent triage/adjudication | immutable Step 15 output and human triage | `D2-15-17` readiness audit only | READ-ONLY AUDIT DONE; scientific Step 16 NOT EXECUTED; Gate C `NOT_REACHED` |
| 17 | exploration owner | sealed Step 15, private destination, candidate list, finite budget, separate approval | `D2-15-17` readiness audit only | READ-ONLY AUDIT DONE; scientific Step 17 NOT EXECUTED |
| 18 | writing owner | current ledger and bounded evidence | `paper/d2-status-draft.md`, claim map/ledger/matrix, `D2-18` report | DONE for documentary status manuscript; `NOT_SUBMISSION_READY`, missing substantive human/coauthor review |
| 19 | artifact owner | stable status tables and retained development evidence | `artifact/`, `D2-19` artifact and fresh-reproduction reports | DONE for `PARTIAL_DEVELOPMENT_ARTIFACT`; `FINAL_ARTIFACT_BLOCKED`, same-host evaluator 4/4 `PASS`, sidecar/container routes blocked |
| 20 | review owner | reviewable status manuscript and partial artifact | three PDF-only reviews, concern inventory, ledger v3, `D2-20` report | `EVIDENCE_AUDIT_COMPLETE_NO_NEW_EXPERIMENT`; 12 concerns, zero current-manuscript factual contradictions, no manuscript correction, research `UNKNOWN` |

## Reproduction registry

| Evidence | Command | Output boundary | Notes |
|---|---|---|---|
| D2 foundation integrity control | `python3 scripts/d2_foundation.py self-test --output-dir results/raw/D2-00/<fresh-id>` | ignored `results/raw/D2-00/` | Prepares a run manifest, seals disposable files, verifies them, tampers one disposable file, and requires detection. |
| Verify a D2 foundation-schema seal | `python3 scripts/d2_foundation.py verify <manifest>` | stdout JSON | Exit 0 is `PASS`; exit 2 is `FAIL` or infrastructure error. Step 10 uses its own v2 seal schema and validation route below. |
| Historical benchmark table | `python3 scripts/artifact/reproduce.py benchmark-table` | ignored artifact-reproduction namespace | Reproduces the historical D1P-34 table, not corrected D2 results. |
| Historical Foundry rows | `python3 scripts/artifact/reproduce.py baseline-table` | ignored artifact-reproduction namespace | Reproduces only the publicly reconstructible Foundry rows. |
| Historical validation table | `python3 scripts/artifact/reproduce.py validation-table` | ignored artifact-reproduction namespace | Expensive proof route; follow its load and tool requirements. |
| Corrected historical evidence ledger | `python3 scripts/artifact/reproduce.py ledger` | ignored artifact-reproduction namespace | Reconciles tracked validation evidence without claiming held-out transfer. |
| D2 Step 1 integrated development run | `PYTHONPATH=src .venv-d1p-00/bin/python scripts/d2_step1_integrated.py --output results/raw/D2-01-recovery-01 --seal protocols/d2/d2-01-seal-v1.json` | `results/raw/D2-01-recovery-01/` | Identical sealed recovery after the preserved `results/raw/D2-01/` sandbox cache-lock stop; produces the 49-row table and `COMPLETE / UNKNOWN` summary. |
| D2-01 post-Step8 historical replay | `PYTHONDONTWRITEBYTECODE=1 python3 scripts/d2_d201_post_step8_replay.py` | stdout JSON only | Wrapper `PASS`: live replay is the required `EXPECTED_FAIL` with exactly one mismatch among 8,134 members; the in-memory historical overlay is 8,134/8,134 `PASS`. This is not current-checkout equivalence. |
| D2 Step 2 inventory validation | `python3 scripts/d2_step2_inventory.py` | stdout JSON only | Rechecks the bounded population, lineage, current-variant, historical-attempt, blocker, and source-hash arithmetic without discovery or analyzer execution. |
| D2 Step 4 agreement known-answer tests | `PYTHONPATH=src .venv-d1p-00/bin/python -m unittest tests.test_d2_taxonomy_agreement -v` | test output only | Tests missingness, undefined kappa, exact-set reporting, human-only/fresh-family gates, and blank artifacts; it does not create ratings. |
| D2-07 authoritative recovery seal | `python3 scripts/d2_foundation.py verify results/raw/D2-07-recovery-01/content-seal-v1.json` | stdout JSON only | `PASS`, 623/623 members, zero mismatches; Gate A remains `INCONCLUSIVE`. |
| D2-08 identity seal | `python3 scripts/d2_foundation.py verify results/raw/D2-08/content-seal-v1.json` | stdout JSON only | `PASS`, 92/92 members, zero mismatches; mechanical fixture only. |
| D2-09 authorization-boundary seal | `python3 scripts/d2_foundation.py verify results/raw/D2-09/content-seal-v1.json` | stdout JSON only | `PASS`, 40/40 members, zero mismatches; mechanical fixture only. |
| D2-10 corrected protocol validation | `PYTHONPATH=src python3 scripts/d2_step10_typed_extraction.py --protocol protocols/d2/d2-10-typed-extraction-v2.json --validate-only` | stdout JSON only | `PASS`, 17 bound inputs; validates corrected protocol v2 without creating a raw namespace or a score. |
| D2 artifact metadata | `python3 artifact/reproduce.py metadata` | stdout JSON only | Verifies package checksums, 53 tracked bindings, Step 18 counts, and the non-final status. |
| D2 retained verification | `python3 artifact/reproduce.py verify-retained --source current-workspace` | stdout JSON only | Profile `PASS` includes the expected live D2-01 mismatch, historical overlay pass, and retained D2-07–10 seals. |
| D2 categorical/count recomputation | `python3 artifact/reproduce.py recompute --source current-workspace` | stdout JSON only | Recomputes selected D2-00–10 and Step 18 categorical/count fields; it does not rerun compilers, analyzers, baselines, proofs, or judgments. |
| D2 fresh mechanical fixtures | `python3 artifact/reproduce.py rerun-mechanical --source current-workspace --run-id <fresh-unused-id>` | ignored `artifact/work/<fresh-unused-id>/` | Runs only Gate A validation and unscored Steps 8–10 fixtures; requires an unused ID. The recorded same-host evaluator completed all four profiles 4/4 `PASS`. |
| Current repository suite | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv-d1p-00/bin/python -m unittest discover -s tests -v` | test output only | Current checkpoint: 151/151 `PASS`; this is software validation, not a research verdict. |

## Manifest and seal policy

Use `prepare-run` before an experiment to record the commit/dirty state,
platform, executable identities, configuration and input hashes, declared
seeds, and numeric budgets. A missing budget is explicitly `null`; it does not
authorize unbounded work. Use `seal` only after the selected files are final.
It refuses overwrite, excludes the seal itself and mutable convenience indexes,
and records every excluded path. `verify` compares size and SHA-256 for every
member.

The authoritative Gate B/Gate C seal must be retained by the custodian outside
the developer workspace. These local hashes provide change detection relative
to that trusted copy, not access isolation, authorship, or secrecy.

## Human dependencies and current limits

- The user must name or confirm a custodian before reserved selection, freeze,
  or release.
- Independent policy review, taxonomy annotation, reserved triage, and final
  adjudication cannot be replaced by agent self-review.
- Substantive author/coauthor review, artifact-release approval, and an
  independent human reproduction remain absent. Step 20's model-assisted
  review is an evidence audit, not a substitute for those roles.
- Practical compute limits are experiment-specific. D2-01 declared 1,800 wall
  seconds and 20 compiler/execution calls; every future run must declare its
  own limits before execution.
- Steps 0–10 are complete only at their stated bounded preparation,
  construction, exposed-development, or mechanical-fixture levels. Steps
  11–17 were not executed; Gate B was not evaluated and Gate C was not reached.
  Step 18 remains not submission-ready, Step 19 remains a partial same-host
  artifact with sidecar/container portability blocked, and Step 20 changes no
  manuscript fact or research result. The D2 research verdict remains
  `UNKNOWN`.
