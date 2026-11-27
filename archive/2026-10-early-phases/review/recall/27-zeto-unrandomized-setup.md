# Recall card 27 — zeto-unrandomized-setup

`zeto-unrandomized-setup`

| Field | Value |
|---|---|
| Repository | LFDT-Paladin/zeto |
| DSL (ledger) | Circom/Solidity or generated Groth16 verifier |
| Ledger pattern / impact | unrandomized Groth16 phase-2 key / proof-to-execution mismatch |
| Class v1 → v2 | `integration` → `integration` |
| Vulnerable → fixed | MISSING (not-publicly-pinned) → MISSING (not-publicly-pinned) |
| Exposure | not exposed by C2 |
| L4 proposal | **NEEDS-SCOPE-DECISION** |

## 1. Source report (verbatim)

> ## Summary
> 
> All 20 Groth16 verifier contracts in `solidity/contracts/verifiers/impl/` have `deltax1` set to the BN254 G2 generator point:
> 
> ```
> deltax1 = 11559732032986387107991004021392285783925812861821192530917403151452391805634
> ```
> 
> This is the **initial value before any Phase 2 trusted setup contributions**. When delta equals the G2 generator, **anyone can forge valid Groth16 proofs for arbitrary public inputs**, completely breaking soundness.
> 
> ## Affected Files
> 
> All 20 verifiers in `solidity/contracts/verifiers/impl/`:
> - `anon.sol`, `anon_batch.sol`, `anon_enc.sol`, `anon_enc_batch.sol`
> - `anon_enc_nullifier.sol`, `anon_enc_nullifier_kyc.sol`
> - `anon_nullifier_transfer.sol`, `anon_nullifier_kyc_transfer.sol`
> - `burn.sol`, `burn_batch.sol`, `burn_nullifier.sol`, `burn_nullifier_batch.sol`
> - `deposit.sol`, `deposit_kyc.sol`
> - `nf_anon.sol`, `nf_anon_nullifier_transfer.sol`
> - `withdraw […]

<sub>Source: https://github.com/LFDT-Paladin/zeto/issues/186 (API copy `results/raw/groundtruth/sources/zeto-issue-186.json`, sha256 b8df1a293245…, first 900 chars)</sub>

## 2. Vulnerable vs fixed code

_No pinned source revision: vulnerable and fixed code are **MISSING**._


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** n/a (verifier key)
- **Consumer consequence:** claimed (forgery if deployed); no deployment shown
- **Fix locus:** MISSING - issue open (opened 2026-04-05)
- **P1–P5 mappable:** yes - P4 (delta = G2 generator)
- **Research-contract scope:** contract s5.4 trusted-setup failure: initially OUT of scope
- **Relational class:** VERIFIER-ONLY — verification-key constants
- **Proposed expected pattern:** `P4`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^solidity/contracts/verifiers/impl/[A-Za-z_]+\.sol(:\d+)?$`
- **Location basis:** issue lists 20 files under solidity/contracts/verifiers/impl/
- **Concerns:**
  - No fix exists, so no vulnerable/fixed pair can exist yet; a vulnerable-only pin at the issue date could be proposed.
  - LFDT-Paladin/zeto is an EVAL in-scope family (v2-family:9a7acbc2cba3d6a8e481), not in the 278 sample.

## 4. Reviewer decision

| Field | Fill in |
|---|---|
| Decision | ☐ ACCEPT  ☐ EDIT  ☐ DROP |
| Strict scope (keep / demote) | |
| expected_pattern (P1–P5 or NONE) | |
| expected_location_regex | |
| Accept candidate commit? (if shown) | ☐ yes ☐ no ☐ n/a |
| Reviewer | |
| Date | |
| Notes | |
