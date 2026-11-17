# S2a — Precision fixes for freeze 3 (DEV only)

**Goal for the paper:**

- Held-out v3 must not repeat the freeze-2 precision problems: P5 was 2/15, P1
  9/15 and P3 9/15 correct (`reports/labels/LABEL-ANALYSIS.md`).
- Honk verifiers must stop being a blanket `UNKNOWN`, because about a quarter of
  the held-out v3 pool is Noir.

**Branch:** `sprint/S2a`.

**Owns:** `bindcheck_zk/`, `tests/s2a/`, `reports/S2a/`, `results/raw/S2a/`.

**Must not edit:** `findings/`, `oracle/`, `prototypes/s1-honk-canon/`.

## Inputs

The 278 freeze-2 held-out families are spent and are now DEV. Their warnings
and human labels are allowed inputs:

- `reports/labels/set-H-ledger.csv`, with columns `final` and `reason_A/B`;
- `reports/heldout/warning-unblind-key.csv`;
- `reports/heldout/per-verifier.csv`;
- raw outputs under `results/raw/heldout/`.

**Forbidden:** any family that `python3 scripts/check_holdout.py` reports as
FORBIDDEN.

## Steps

### 1. False-positive inventory

Classify every `final=FP` card in Set H by root cause, citing the analyzer code
path responsible. There are 13 P5, 6 P1, 6 P3 and 3 P4 canonicality-guard
cards, plus arm-A kinds. Known P5 causes:

- the proof array is counted as public inputs;
- PLONK pairing-point inputs;
- the wrong circuit is selected.

Known P3 cause: the verifier's `checkField` is not credited. See card W0007.

### 2. Fix each cause with a regression

For each root cause:

1. Write a fixture test in `tests/s2a/` reproducing the card. Use a minimal
   excerpt or a pinned copy, never a fabricated "expected" verdict.
2. Fix the analyzer.
3. Confirm the test passes and the TP cards in the same stratum are still
   VIOLATION.

Fail closed: when a fix cannot decide, return `UNKNOWN` with a reason code, not
`VERIFIED_WITHIN_SCOPE`.

### 3. Honk/UltraHonk verifier layout

Parse the bb-generated `HonkVerifier` and `IVerifier.verify(bytes, bytes32[])`:

- the number of public inputs (`NUMBER_OF_PUBLIC_INPUTS`, minus pairing-point
  and aggregation-object inputs where present);
- the position mapping, so P5 and P3 can reason about Noir consumers.

Use the DEV Noir cases: Payy, WarpToad, Semaphore-Noir, and spent freeze-2 Noir
families.

**Do not** implement the Honk canonicality rule here. That is S2b, after S1
reports what the generator does.

### 4. Measure on the full DEV ledger

Rerun the unchanged harness on the full DEV ledger: the 56 original DEV rows
plus the 278 spent families. Report per-pattern applicable, VIOLATION,
VERIFIED_WITHIN_SCOPE and UNKNOWN counts against freeze 2. For every changed
verdict, give the reason. Also report the recomputed precision on the Set H
cards, labelled as **DEV, not held-out**.

### 5. Prepare the freeze-3 candidate

Compute the candidate content hash the same way as `docs/FREEZE-2.md`, but **do
not** declare the freeze or tag it. The reviewer declares freeze 3 after S2b
and S3.

## Completion criteria

- **Tests.** All existing tests still pass, run as in `docs/FREEZE-2.md`, with
  `BINDCHECK_CIRCOM` pointing to a Linux circom 2.1.9 build. New `tests/s2a/`
  tests pass.
- **Set H.** Every Set H FP card is explained. Each is either fixed with a
  regression or documented as an accepted limitation with the reason.
- **P5 cards.** Of the 15 P5 cards, the 13 FPs are no longer VIOLATION, unless
  documented, and the 2 TPs remain VIOLATION.
- **Honk layout.** Honk verifier arity is recovered on every DEV Noir case, or
  its UNKNOWN reason is listed.
- **Report.** `reports/S2a/REPORT.md` follows the handoff template and includes
  the DEV delta table and the candidate hash.

## Watch-outs

- **Fix the cause, not the card.** Fix general causes, never special-case a
  repository or file name. The reviewer will grep for repository-specific
  conditions.
- **Spent families.** They are DEV, but report their numbers separately from the
  original 56 DEV rows.
