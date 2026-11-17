# S1 — Do generated verifiers accept non-canonical public inputs?

**Goal for the paper:** determine whether a verifier generator lets one valid
proof be accepted under two different public-input encodings (x and x + r).
When it does, any consumer that keys state on the raw value (a nullifier or
replay map) can be paid twice from a single proof. A confirmed, unknown instance
in a widely used generator is the strongest possible headline. A survey table of
"which generators check canonicality" is a paper result either way.

**Branch:** `sprint/S1`.

**Owns:** `prototypes/s1-honk-canon/`, `reports/S1/`, `results/raw/S1/` (ignored).

**Must not edit:** `bindcheck_zk/`, `findings/`.

## Prior work found by the reviewer (17 Nov) — read first

[Xion PR #608](https://github.com/burnt-labs/xion/pull/608), merged
4 Sep 2026, says that **native** Barretenberg UltraHonk verification reduces
public inputs mod r. The cause it gives is `many_from_buffer<uint256_t>`. As a
result, the input X + r also verifies. Xion fixed only its own Go/FFI wrapper,
and the reviewer found no upstream Aztec advisory. This changes the questions S1
must answer:

1. **Solidity HonkVerifier (the main question).** Does the generated Solidity
   verifier also accept X + r? It can reduce the inputs for the arithmetic but
   absorb the **raw** bytes into the Fiat–Shamir transcript. Then X + r changes
   the challenges and the proof fails. Prove the answer by experiment, for each
   bb version.
2. **Native and bb.js verification users.** Look for applications that verify
   Noir/Honk proofs **off-chain or natively** (bb.js `verifyProof`, the bb CLI,
   bb FFI, or another chain module like Xion) and then authorize an action keyed
   on a raw public input. Examples are an airdrop backend, a KYC gate or a
   claim server. Check whether bb.js and the bb CLI reduce inputs the same way.
   Run the hold-out guard on each repository first.
3. **Upstream status.** Is the native behaviour documented, fixed, or reported
   upstream? Cite Xion PR #608 as prior work in every case. The verdict for the
   native path is at best `CONFIRMED_KNOWN`.

## Hard rules

- **Hold-out guard.** Before reading any third-party application repository, run
  `python3 scripts/check_holdout.py <owner/repo>`. If it says FORBIDDEN, do not
  open it. Generator and toolchain repositories are allowed: Barretenberg/Aztec,
  Noir, snarkjs, gnark, halo2-solidity-verifier, sp1/risc0 contracts.
- **Local only.** Use only owned local deployments (Anvil or Hardhat) with
  synthetic assets. No RPC to public chains, no transactions, no contact with
  maintainers.
- **Stop rule.** If any deployed, funded system looks affected, stop. Write
  `STOP-FOR-HUMAN.md` with the facts and do not continue on that system.

## Steps

### 0. Find the origin of the lead

Search the repository and the ignored `results/raw/` for where the claim came
from: "Barretenberg/Honk verifier may accept non-canonical public inputs, and
Noir privacy pools key nullifiers on the raw value".

```bash
rg -n -i "canonical|alias|modulus|>= ?r\b|publicInputs" results/raw reports docs
```

Record what you find, or record "not found".

### 1. Read the generator sources

For each generator and version below, find where the Solidity verifier loads
public inputs. Determine whether it:

- rejects values ≥ r;
- reduces them mod r; or
- uses them raw, for example absorbing raw bytes into the Fiat–Shamir
  transcript while the arithmetic uses them reduced. That split is the dangerous
  case.

Quote file paths and line numbers from the pinned source.

| Generator | Versions |
|---|---|
| bb / bb.js UltraHonk (keccak and keccakZK) | 3.0.0 (Payy), 5.0.0 (WarpToad) and the latest release |
| snarkjs | Groth16, PLONK and fflonk templates, current version (the known `checkField` baseline) |
| gnark | Solidity export |
| Optional | halo2-solidity-verifier; the SP1 and RISC0 verifier contracts |

### 2. Experiment, for each Honk version

1. Write a minimal owned Noir circuit with one public input `n` (a nullifier).
2. Generate the verifier with the pinned bb and produce an honest proof.
3. On local Anvil, call `verify(proof, [n])` and `verify(proof, [n + r])`.
4. Record accept or reject, the gas used, and exact versions and hashes.
5. Repeat steps 3–4 with the input at `n + k·r` for the largest k that still
   fits in 256 bits.

### 3. If any generator accepts the aliased input

1. Write a minimal synthetic consumer, `mapping(bytes32 => bool) spent`, keyed
   on the raw public input.
2. Show two successful withdrawals of synthetic tokens from one proof. That is
   E4 on a synthetic consumer.
3. Write the repair (reject ≥ r, or reduce before keying) and show it rejects
   the second withdrawal while the honest one passes.

### 4. Exposure on allowed code only

- Search DEV families and the spent freeze-2 families only (each repository must
  pass the guard).
- Look for Noir/Honk consumers that key replay state on a raw public input.
- List them with file and line, and state per item whether a canonical guard
  exists upstream of the key.
- **Do not** search GitHub broadly. The held-out v3 run will measure exposure.

### 5. Check prior knowledge

Search the following and record URL, date and exact wording:

- Barretenberg/aztec-packages and Noir changelogs, issues and security
  advisories;
- audit reports of the Honk verifier;
- the Noir docs on public inputs.

## Verdict enum (put it in the report)

`CONFIRMED_NEW` | `CONFIRMED_KNOWN` (with the citation) | `PATCHED_IN_<version>` | `NOT_REPRODUCED`

Give one verdict per generator and version.

## Completion criteria

- **Generator table.** `reports/S1/REPORT.md` contains a table with one row per
  generator/version:
  - canonical behaviour: reject, reduce, raw or split;
  - source lines;
  - experiment result;
  - verdict.
- **Reproducibility.** All experiments are reproducible with
  `prototypes/s1-honk-canon/run.sh`, which uses pinned versions and records
  checksums.
- **Exposure.** The exposure list, with every repository guard-checked.
- **Report.** The report follows the handoff template in
  `docs/orchestration/README.md`, including the held-out hygiene statement.

## Time box

Two days. If step 2 is blocked by toolchain issues for more than about 4 hours,
finish steps 1 and 5, report `PARTIAL`, and list exactly what failed.
