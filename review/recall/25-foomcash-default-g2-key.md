# Recall card 25 — foomcash-default-g2-key

`foomcash-default-g2-key`

| Field | Value |
|---|---|
| Repository | MISSING |
| DSL (ledger) | Circom/Solidity or generated Groth16 verifier |
| Ledger pattern / impact | gamma equals delta / unrandomized Groth16 key / proof-to-execution mismatch |
| Class v1 → v2 | `integration` → `integration` |
| Vulnerable → fixed | MISSING (not-publicly-pinned) → MISSING (not-publicly-pinned) |
| Exposure | not exposed by C2 |
| L4 proposal | **NEEDS-SCOPE-DECISION** |

## 1. Source report (verbatim)

> FoomCash's FoomLottery is a Tornado-style shielded pool: you play() to deposit FOOM behind a commitment, and later collect() a reward by presenting a Groth16 zero-knowledge proof that you own an unspent note in the Merkle tree. Feb 2026 • Ethereum • auth • 10 min read Loss 19,695,576,757,802.19 FOOM (~$1.3M) — the FOOM Lottery pool drained to dust in one tx Chain Ethereum Category auth Date Feb 2026 Source Crypto Training PoC & write-up PoC for your local evm-hack-analyzer Attack tx EVM Playground Source-level debugger — step opcodes and Solidity in sync evm-hack-analyzer The attack is replayed in an in-browser EVM preloaded with the exact dumped fork state. The execution tree shows every ca […]

<sub>Source: https://crypto.training/hacks/2026-02-foomcash_groth16/ (text extracted from HTML `results/raw/groundtruth/sources/foomcash.txt`, sha256 9ecea473604e…)</sub>

## 2. Vulnerable vs fixed code

_No pinned source revision: vulnerable and fixed code are **MISSING**._


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** n/a (verifier key)
- **Consumer consequence:** yes - pool drained (reported ~$1.3M)
- **Fix locus:** MISSING (no repository/pins)
- **P1–P5 mappable:** yes - P4 (gamma == delta)
- **Research-contract scope:** contract s5.4 lists 'toxic-waste compromise or trusted-setup failures' as initially OUT of scope; P4 checks it anyway
- **Relational class:** VERIFIER-ONLY — verification-key constants
- **Proposed expected pattern:** `P4`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `MISSING`
- **Location basis:** no repository in ledger
- **Concerns:**
  - repository empty and both pins not-publicly-pinned; deployed bytecode exists but the lane brief forbids interacting with deployed contracts beyond read-only public data, and no source pin is recorded.

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
