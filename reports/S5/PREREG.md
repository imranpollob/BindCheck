# S5 held-out v3 preregistration (reserve draw)

Status: PROSPECTIVE, written 2026-11-19 before any reserve acquisition, prebuild,
analyzer or oracle output. Binds the run to the approved protocol
`docs/orchestration/S5-PROTOCOL-DRAFT.md` (approved and frozen by the author on
2026-11-19). Any change after the first reserve output requires a new dated
amendment, not an edit.

## Population

- Units: **1,105** (repository, commit) pairs, listed in
  `reports/S5/reserve-manifest.csv`, SHA-256
  `b1752eede4ccabaf5dea45d827fbdd0c388346349a51129b2ace125322374278`.
- Derived from `dataset/source-corpus-v2.csv` (in-scope EVAL rows), minus the 278
  freeze-2 spent pairs in `reports/heldout/selected-families.csv`, minus
  `warptoad/warp-toad`. The manifest hash is the population identity; no other
  draw is used.
- Reporting stratum: audited or deployed (`maturity` in
  `audited-production`, `deployed-address-in-docs`): **390** units.
- Unit of analysis: the (repository, commit) pair. Each unit is one attempt.

## Frozen tools

- Analyzer: freeze 3, `BINDCHECK_ZK_CONTENT_SHA256=753c6e2a0f3f75255eb2fdc354402f3ef7aac1541206b0794a9d09cd7d485315`, tag `freeze-3`.
- Oracle: the state at `d093ef2` plus the F5 change, which cleared XR4.
- Circom 2.1.9, circomlib 2.0.5 (vendor lock, `bindcheck_zk/vendor-lock.json`).
- Timeouts as in freeze 2: analyzer 150 s outer; acquisition 300 s per step.

## Procedure

1. Acquire each unit at its pinned commit (shallow, filtered). Failure or
   mismatch is recorded as `ACQUISITION_FAILED`; it is never dropped.
2. Prebuild the recorded circuits with the vendor-locked circomlib. Failure is
   `BUILD_FAILED`, with its reason.
3. Run the frozen analyzer once per unit. Timeout is `HARNESS_TIMEOUT`. A unit
   with no recovered triple is `UNSUPPORTED` and is still counted.
4. Warnings: each VIOLATION or P4 warning is written as a blind card (code,
   location, applicable rule) for the author's adjudication. Tool identity and
   confidence are hidden from the rater.
5. Oracle: each VIOLATION is written as a manifest **before** its analyzer output
   is inspected. Policies state entitlement only. The oracle decides E4 on owned
   local Anvil only.
6. Arm C (the strong baseline) and the contract-plus-verifier comparison run on
   the same pinned checkouts, with the same budgets.

## Reported denominators (all predeclared)

Every one of the 1,105 units appears in the funnel, with counts for
acquisition failed, build failed, timeout, unsupported, analyzable, per-pattern
VIOLATION / VERIFIED_WITHIN_SCOPE / UNKNOWN, oracle E4 / NOT_CONFIRMED /
UNKNOWN, blind adjudication TP / FP / unclear, and incorrect certifications.
Headline precision uses all attempted units as the denominator. The 390 stratum
is reported separately. WarpToad is excluded and listed with its reason.

## Exposure controls

- The guard `scripts/check_holdout.py` refuses reserved families. The run may
  open them only through the authorized reserve entry point, which requires:
  the manifest hash above, the freeze-3 tag at HEAD, and an authorization record
  `reports/S5/AUTHORIZATION.json` that names the author's approval.
- Any unit whose (repository, commit) appears in the 278 spent set is refused.
- No unit outside the manifest is opened.

## Unresolved items (author)

- The stratum count 390 versus the sprint plan's 391 is not reconciled.
- Adjudication labels come from the author. AI labels are not independent.

## Approval

Author approval of this preregistration: [pending, to be given in chat]
