# S5 held-out v3 protocol — DRAFT (not approved, not run)

Status: DRAFT prepared 2026-11-19 in response to the EuroS&P reviewer assessment
(`bindcheck-eurosp-review-2026-11-19.md`). Nothing here authorises a run. The
author must resolve every item marked **DECISION** before the run. Once approved
and committed, this protocol is frozen and is not edited after the run starts.

## 1. Analyzer

Freeze 3, content hash `753c6e2a0f3f75255eb2fdc354402f3ef7aac1541206b0794a9d09cd7d485315`
(`docs/FREEZE-3.md`, tag `freeze-3`). No analyzer change is allowed after the
protocol is committed.

## 2. Oracle

Freeze at the commit that cleared XR4 (`d093ef2`, `ORACLE CLEAR FOR S5`). Every
VIOLATION is confirmed by the oracle; no oracle result is used unless the
manifest for that family is written before its analyzer output is read.

## 3. Population — DECISION 1

The controlling contract (`docs/research-contract.md` revision 3/4, line 267)
reserves **1,106** EVAL-only families of dataset v2's 1,384. The sprint plan
(`docs/sprint-eurosp-2027.md` line 62) names **391** audited or deployed families
as the held-out v3 population.

- Option A: the contract's 1,106 (all reserved EVAL families, in scope).
- Option B: the 391 audited or deployed subset, which the paper's lesson 3 needs.

Whichever is chosen, a dated contract amendment must state it before the run,
with the exclusion counts and the reason the other set is not used.

**Author choice (population): A — the contract's 1,106, with WarpToad excluded (1,105 families).** Reporting stratum, fixed before the run: audited or deployed families, defined as `maturity` in {`audited-production`, `deployed-address-in-docs`} in `dataset/source-corpus-v2.csv` (535 families by corpus count). The sprint plan's 391 could not be reproduced from the corpus and is not used.

## 4. Exclusions — DECISION 2 (decided: A)

WarpToad (`warptoad/warp-toad`) is guard-classified FORBIDDEN as a reserved v3
family, but at least eight earlier reports describe hands-on development work on
it. These reports are listed in `reports/` and cited by file.

- Option A: exclude WarpToad from held-out v3; record the prior exposure.
- Option B: keep it, and report all results with and without it.

**Author choice (WarpToad): A — exclude.** Record the prior-exposure reports listed above.

Sibling check: `jimjimvalkema/zktranswarp` is a separate reserved family (guard `v2-family:cc3c0f35…`), distinct from WarpToad (`v2-family:45bae315…`). Neither is among the 278 spent freeze-2 families. The guard forbids opening either before the run, so a circuit-blob comparison is not possible before approval; the guard's family index is the authority. zktranswarp stays in the 1,105.

Any family with prior exposure beyond the guard list is recorded before the run
and is never silently dropped.

## 5. Reporting denominators (predeclared)

Every attempted family is counted, including:

- acquisition failed, prebuild failed, analyzer timeout;
- unsupported application (no recovered triple);
- analyzable, with per-pattern applicable / UNKNOWN / VIOLATION / VERIFIED counts;
- each VIOLATION: oracle E4 confirmed, NOT_CONFIRMED, or UNKNOWN;
- each warning: blind adjudication by the author; disputed cases reported.

Headline precision uses the **attempted** families as the denominator, not only
the decided ones. Abstention (UNKNOWN) is reported as its own column.

## 6. Comparison (the centre of the results)

For a fixed set of reviewed cases:

- contract-plus-verifier baseline (same policy, same resources);
- BindCheck with the circuit facts;
- the single extra fact that changes the answer, if any;
- an independent check of the correct outcome.

Incorrect certifications, unnecessary warnings, and cases neither system could
decide are reported with equal prominence.

## 7. Policy procedure

Policies are written and committed **before** the analyzer output for that
family is inspected. They state entitlement and required obligations, never an
expected verdict (`_validate_manifest` enforces this). Each policy includes at
least one legitimate delegated or deferred case, where that case exists in the
family, with the reasoning recorded.

## 8. Ethics and disclosure

Local Anvil only; no fork, no public RPC, no broadcast. Any VIOLATION in a
deployed application goes to the author's advisor before any other step. No
maintainer is contacted from this run.

## 9. Timing and what is not in scope

Measured runtime per family is reported from command records, not extrapolated.
The held-out run does not change the freeze-2 development numbers, which keep
their labels.

## Approval

Protocol approved by the author on: ______ (blank)
Commit of approved protocol: ______ (blank)
