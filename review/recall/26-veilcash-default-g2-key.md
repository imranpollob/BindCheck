# Recall card 26 — veilcash-default-g2-key

`veilcash-default-g2-key`

| Field | Value |
|---|---|
| Repository | DK27ss/VeilCash-5K-PoC |
| DSL (ledger) | Circom/Solidity or generated Groth16 verifier |
| Ledger pattern / impact | gamma equals delta / unrandomized Groth16 key / proof-to-execution mismatch |
| Class v1 → v2 | `integration` → `integration` |
| Vulnerable → fixed | MISSING (not-publicly-pinned) → MISSING (not-publicly-pinned) |
| Exposure | not exposed by C2 |
| L4 proposal | **NEEDS-SCOPE-DECISION** |

## 1. Source report (verbatim)

> Veil Cash — the verifying key set delta equal to gamma, so the pairing equation accepted proofs nobody had to compute — Veil Cash / Base — 2026-02-20 Loss 2.9 ETH (~$5,000) — the entire 0.1 ETH privacy pool, drained through 29 fraudulent withdraw() calls in a single transaction with fabricated nullifier hashes and forged proofs, by an address that had never deposited. Decurity detected the attack and rescued the remaining pools; the exploiter returned the funds unprompted. Days later FoomCash was drained through the same misconfiguration. The dollar figure is trivial and close to irrelevant — what was broken was the soundness of the proof system, and the same key misconfiguration in a pool o […]

<sub>Source: https://onchainattack.org/document/examples/2026-02-veil-cash-groth16-verifying-key-delta-gamma-forgery/ (text extracted from HTML `results/raw/groundtruth/sources/veilcash.txt`, sha256 a4c675fde3af…)</sub>

## 2. Vulnerable vs fixed code

_No pinned source revision: vulnerable and fixed code are **MISSING**._


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** n/a (verifier key)
- **Consumer consequence:** yes - 2.9 ETH pool drained then returned (source page)
- **Fix locus:** MISSING
- **P1–P5 mappable:** yes - P4
- **Research-contract scope:** contract s5.4 trusted-setup failure: initially OUT of scope
- **Relational class:** VERIFIER-ONLY — verification-key constants
- **Proposed expected pattern:** `P4`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `MISSING`
- **Location basis:** no pin
- **Concerns:**
  - Ledger repository DK27ss/VeilCash-5K-PoC is a third-party exploit PoC repository ('groth16 verifier had delta2 == gamma2'), not the victim project; a PoC repo is not a vulnerable/fixed revision pair.

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
