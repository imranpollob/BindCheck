# S1 — Do generated verifiers accept non-canonical public inputs?
Status: PARTIAL
Verdict/outcome: per generator/version in [`generators.csv`](generators.csv). Summary: **no generated Solidity verifier accepted the same honest proof under an aliased encoding (n + r, n + 5r).** Native Barretenberg verification through bb.js 3.0.0-manual.20251030 with the default (Poseidon2) transcript **accepts** both aliases: `CONFIRMED_KNOWN` (burnt-labs/xion PR #608). Native bb/bb.js 5.0.0 and 6.0.0 reject (`PATCHED_IN_5.0.0`, dated by npm marker). Four Solidity templates are **split** (raw value in the transcript, reduced value in the arithmetic): bb.js ≤ 3.0.3 keccak/keccakZK and snarkjs 0.7.6 PLONK/fflonk. They are source-read and **unconfirmed**. The bb.js Solidity guard is present from 4.0.1 (`PATCHED_IN_4.0.1`, marker-based).

AI disclosure: run by Claude Code (Anthropic), model Claude Opus 5.5 (`claude-opus-5-5`), on 2026-11-17/18 in worktree `$BC/wt-S1`, branch `sprint/S1`. The human author has not yet inspected the outputs. An earlier session in the same worktree left an untested prototype. It was reviewed, partly rewritten, and its forge test, which hard-coded the expected outcome, was deleted. Its raw run is preserved (see Evidence).

PARTIAL because: step 3 (detector fixture) and step 4 (exposure list) were not done, and the split templates are unconfirmed. Both depend on author decisions that are still pending: whether a modified prover may be built on the local testbed, and how one local development family may be handled. The orchestrator's 18 Nov ruling limited this pass to decision-independent work.

## What was done

0. **Origin of the lead.** `grep` over `results/raw`, `reports`, `docs` (log `results/raw/S1/step0/grep_lead.txt`). The phrase appears only in the S1 prompt, the sprint plan and the orchestration README. **Not found**: no run, report or raw log records where the lead came from.
1. **Generator sources.** Line references come from the verifiers generated in this run (pinned binaries/packages), the snarkjs 0.7.6 `.ejs` templates, and gnark v0.16.5 `solidity.go`. `AztecProtocol/aztec-packages` is FORBIDDEN by `scripts/check_holdout.py` (family `v2-family:481e9487608e6e49df68`), even though the prompt lists Barretenberg/Aztec as allowed. Per the orchestrator ruling it was **not opened**. Barretenberg C++ source (native path) was therefore not read.
2. **Experiments** with `prototypes/s1-honk-canon/run.sh` (owned circuits `circuit/` (Noir) and `circom/s1.circom`: one public input `n = 9`, `secret² = n`):
   - native `bb verify` (5.0.0, 6.0.0) for targets `evm`, `evm-no-zk`, `noir-recursive`;
   - bb.js `verifyProof` (3.0.0-manual.20251030 with nargo beta.14; 5.0.0 with nargo beta.22) for each transcript mode;
   - snarkjs 0.7.6 JS `verify` for Groth16/PLONK/fflonk;
   - **15 generated Solidity verifiers** deployed on a local Anvil (chain 31337, `127.0.0.1`), each called with the same honest proof at `n`, `n + r` and `n + 5r` (k = 5 is the largest k with n + k·r < 2²⁵⁶). Variants: bb 5.0.0/6.0.0 × {evm, evm-no-zk} × {plain, `--optimized`}; bb.js 3.0.0 keccak/keccakZK; bb.js 5.0.0 evm/evm-no-zk; snarkjs Groth16/PLONK/fflonk. The driver `anvil_replay.py` records return value, revert selector, gas and runtime size only. It encodes no expected outcome and refuses any chain ID other than 31337 or a non-local RPC.
3. **Step 5 upstream check**: GitHub REST API (unauthenticated) on guard-ALLOWED repos only, sha512-verified npm tarballs of `@aztec/bb.js` (marker bisection), a shallow gnark clone, and a sparse Noir docs checkout.
4. **gnark (optional)**: source read only. Go is not installed, so no experiment.

## Evidence (paths, hashes, commands, exit codes, tool versions)

Command: `bash prototypes/s1-honk-canon/run.sh` → exit 0. Run dir (ignored): `results/raw/S1/run-20261118T203045Z/` (base `47ae961e5d4f2817028e8e82f4f1e70ee0b571c2`, untracked prototype files present at run time).

- `run.log`: full log, tool versions and input/binary checksums
- `anvil/results.json` (sha256 `c051cc9c…14fa72`), `anvil/results.tsv` (sha256 `da0ee50e…208c80`)
- `native/bb-<v>/<target>/verify_<case>.log`, `bbjs-<v>.json`, `snarkjs/js-verify/summary.tsv`
- `output-sha256.txt`: 54 checksums of every generated verifier, proof, public-input file, VK and calldata

Superseded/preserved runs, not deleted: `results/raw/S1/{run.log,3.0.0-manual.20251030,5.0.0,6.0.0}` (earlier session; its bb 5/6 verifiers are byte-identical to this run's, sha256 `7a85d7d7…` and `6c50e1fd…`) and `results/raw/S1/run-20261118T202946Z/` (first run of the current script; external-library linking missing, so 7 variants errored). Step 5 raw: `results/raw/S1/step5/` (API JSON, `markers-{1,2,3}.tsv`, `npm-tarballs-sha256.txt`, `gnark-template-sha256.txt`). The npm tarballs and the empty Barretenberg mirror clone were deleted after hashing.

Tool versions: forge/anvil/cast 1.4.1-stable (`cf774604`); solc 0.8.29 (optimizer, 1 run, cancun); node v24.19.0; nargo 1.0.0-beta.14 (`6774e1f9…`) and 1.0.0-beta.22 (`d57714db…`); bb 5.0.0 (`07e14e5a…`) and 6.0.0 (`97242cb2…`) from T0; bb.js 3.0.0-manual.20251030 and 5.0.0 from T0 lockfiles; circom 2.2.3; snarkjs 0.7.6 (npm `latest`, 2026-01-12); gnark v0.16.5 (`6c651a19`). The snarkjs ceremony is a local throwaway with fixed entropy. It is synthetic and not a trusted setup.

## Results (tables; exact counts)

### Generated Solidity verifiers on local Anvil (same honest proof; gas from a local tx with a 30M gas limit)

| Verifier | Behaviour (source) | n | n + r | n + 5r | Runtime bytes |
|---|---|---|---|---|---|
| bb 5.0.0 evm plain | reject (L577) | true, 1,871,539 | revert `ValueGeFieldOrder`, 281,005 | same | 16,878 |
| bb 5.0.0 evm optimized | reject (L1528–1543) | true, 588,940 | revert `ValueGeFieldOrder`, 183,910 | same | 13,582 |
| bb 5.0.0 evm-no-zk plain | reject (L574) | true, 946,673 | revert `ValueGeFieldOrder`, 169,822 | same | 15,916 |
| bb 5.0.0 evm-no-zk optimized | reject (L1295–1310) | true, 514,402 | revert `ValueGeFieldOrder`, 148,050 | same | 12,066 |
| bb 6.0.0 evm plain | reject (L570) | true, 1,874,293 | revert `ValueGeFieldOrder`, 281,063 | same | 16,899 |
| bb 6.0.0 evm optimized | reject (L1536–1551) | true, 589,511 | revert `ValueGeFieldOrder`, 183,910 | same | 13,695 |
| bb 6.0.0 evm-no-zk plain | reject (L567) | true, 949,167 | revert `ValueGeFieldOrder`, 169,884 | same | 15,885 |
| bb 6.0.0 evm-no-zk optimized | reject (L1303–1318) | true, 514,988 | revert `ValueGeFieldOrder`, 148,050 | same | 12,188 |
| bb.js 5.0.0 evm | reject (= bb 5.0.0 evm plain, byte-identical) | true, 1,871,671 | revert `ValueGeFieldOrder`, 281,137 | same | 16,878 |
| bb.js 5.0.0 evm-no-zk | reject (byte-identical) | true, 946,673 | revert `ValueGeFieldOrder`, 169,822 | same | 15,916 |
| bb.js 3.0.0-manual keccak | **split** (L540 raw transcript; L167 `% MODULUS`) | true, 1,046,056 | revert `SumcheckFailed`, 312,016 | same | 23,090 |
| bb.js 3.0.0-manual keccakZK | **split** (L541; L167) | true, 1,947,119 | revert `SumcheckFailed`, 426,812 | same | 23,721 |
| snarkjs Groth16 | reject (template L155) | true, 214,268 | false, 32,590 | false, 32,590 | 1,346 |
| snarkjs PLONK | **split** (template L281 raw; L424–436 reduced) | true, 292,531 | false, 292,977 | false, 294,225 | 5,075 |
| snarkjs fflonk | **split** (template L270–272 raw; L528–533 reduced) | true, 214,117 | false, 51,090 (inverse check) | false, 51,090 | 13,628 |

15/15 deployed; 15/15 accepted the honest input; 0/30 aliased calls accepted. All runtimes are under EIP-170 (24,576 bytes). Anvil ran with `--disable-code-size-limit`, which therefore had no effect. In the split templates the aliased call fails because the raw bytes change the Fiat–Shamir challenges, not because of a range check. That shows only that the **same** proof does not transfer. Whether a proof whose transcript is computed over n + r would be accepted is the open question, and testing it requires a modified prover (not authorized).

### Off-chain / native verification (same honest proof)

| Path | n | n + r | n + 5r |
|---|---|---|---|
| bb.js 3.0.0-manual `verifyProof`, default (Poseidon2) | accept | **accept** | **accept** |
| bb.js 3.0.0-manual `verifyProof`, keccak / keccakZK | accept | reject | reject |
| bb.js 5.0.0 `verifyProof`, default / evm / evm-no-zk | accept | reject | reject |
| `bb verify` 5.0.0 and 6.0.0, evm / evm-no-zk / noir-recursive (exit code) | 0 | 1 (`Non-canonical public input: value >= field modulus`) | 1 |
| snarkjs 0.7.6 JS `verify`, Groth16 / PLONK / fflonk | OK | `Public inputs are not valid.` | same |

### npm marker bisection of `@aztec/bb.js` (sha512 integrity verified for each tarball)

| Version (published) | Solidity guard `require(uint256(publicInputs[i]) < P` | reducing `uint256(value) % MODULUS` | native `Non-canonical public input` |
|---|---|---|---|
| 2.1.11 (2026-01-22) | 0 | 6 | 0 |
| 3.0.0-manual.20251030 (2025-10-30) | 0 | 6 | 0 |
| 3.0.3 (2026-01-20) | 0 | 14 | 0 |
| 4.0.1 (2026-02-27) | 12 | 0 | 0 |
| 4.1.0, 4.2.0, 4.3.0, 4.4.0 | 12 | 0 | 0 |
| 5.0.0 (2026-07-13) | 12 | 0 | 6 |

Markers are static string counts, not behaviour. Native 4.x behaviour was not run.

### Step 5: prior knowledge (retrieved 2026-11-18)

| Source | Date | Wording / content |
|---|---|---|
| [burnt-labs/xion PR #608](https://github.com/burnt-labs/xion/pull/608) | merged 2026-09-04 | Title "Fix Barretenberg public inputs modulo vulnerability". Body: "UltraHonk public inputs were silently reduced modulo the BN254 scalar prime and mutated input (X + r) verifies as valid. we have added range check for inputs so that every input should be smaller than BN254 prime number before Barretenberg FFI call." |
| `AztecProtocol/barretenberg` (ALLOWED) | archived; HEAD `654cc60e` | Mirror emptied: description "Archived. See …/aztec-packages/tree/master/barretenberg"; all 492 tags point to the archive commit (no source). Issue search for "canonical public input", "ValueGeFieldOrder", "public inputs modulus": no relevant hit (#1626, #414 unrelated). No advisory found. History lives in aztec-packages (FORBIDDEN, not searched). |
| npm `@aztec/bb.js` | see table | Solidity guard first in 4.0.1; native error first in 5.0.0. No changelog wording retrieved (changelog is in aztec-packages). |
| [iden3/snarkjs PR #480](https://github.com/iden3/snarkjs/pull/480) | merged 2024-04-08 | "fix: Groth16Verifier solidity scalar size check. (security vulnerability)": public signals must be checked `< r`, not `< q` (the known `checkField` baseline). |
| [iden3/snarkjs PR #359](https://github.com/iden3/snarkjs/pull/359) | merged 2025-03-18 | "Add public inputs checks in groth16/plonk and fflonk verifiers". Changed `src/{groth16,plonk,fflonk}_verify.js` and both Solidity templates, but the template additions are proof-data checks only (curve membership, proof element field range). **No public-signal range check was added to the PLONK/fflonk Solidity templates.** |
| [iden3/snarkjs issue #573](https://github.com/iden3/snarkjs/issues/573) | opened 2025-05-22, open | "Inconsistencies with non-canonically encoded `publicSignals`", about the JS verifiers' input typing and encoding, not the Solidity templates. |
| Noir docs (`noir-lang/noir` `6e40954c`, `docs/docs/language/data_types/fields.md` L86–110) | 2026-11-18 | Only in-circuit byte conversion: "…greater than or equal to the field modulus then the result will silently wrap around. Use `from_be_bytes_checked` when canonical inputs are required." Nothing on verifier public-input canonicality. |
| gnark v0.16.5 | tag | Groth16 template comment: "Public input elements are not automatically reduced"; reverts `PublicInputNotInField`. PLONK template comment: "@param public_inputs (must be reduced)", enforced by `check_inputs_size`. |

No audit report of the Honk Solidity verifier was located through allowed sources. That is an UNKNOWN, not an absence.

## Assumptions and limitations

- **Split ≠ accepted.** The four split templates are source-read and unconfirmed. Acceptance of an alias needs a prover whose transcript absorbs n + r. That experiment was not run (author decision pending). Their verdict is NOT_REPRODUCED for same-proof replay only. Neither safe nor vulnerable is claimed.
- The native 3.0.0 mechanism (reduce for Poseidon2, reject for keccak) is observed behaviour. The C++ source was not read because aztec-packages is FORBIDDEN.
- bb 3.0.0-manual native binary is BLOCKED (T0). All 3.0.0 results use the version-matched bb.js WASM package.
- Dating by npm markers assumes the packaged native/WASM binaries embed the Solidity templates verbatim. That holds for 5.0.0, where the generated output matches.
- Latest native bb release tested: 6.0.0. The npm `latest` tag for bb.js is 5.3.0 (2026-10-26), which was not tested. bb.js 6.x exists on npm only as `6.0.0-nightly.*` prereleases.
- gnark: no experiment (Go not installed). Verdict UNKNOWN despite a source-read reject.
- Step 3 (detector fixture): not done. No Solidity generator accepted an alias in the tested same-proof setting, and an off-chain consumer fixture for the native 3.0.0 path was outside the orchestrator's scope for this pass.
- Step 4 (exposure list): **not done**. The orchestrator limited this pass to decision-independent work, and the principal local Noir/Honk development family is under a pending author decision.

## Failed approaches / surprises

- **Surprise:** bb.js 3.0.0 native verification aliases only on the default Poseidon2 transcript; keccak/keccakZK reject. Xion's report does not say which transcript was affected.
- **Surprise:** bb `--optimized` templates absorb the raw inputs into the transcript (`calldatacopy`) *before* the range check, but still revert on `valid_inputs` before returning. The net behaviour is reject.
- **Surprise:** snarkjs PR #359's title says it adds public-input checks to the PLONK/fflonk verifiers, but in the Solidity templates it adds only proof-data checks. The JS verifiers do reject.
- fflonk returns `false` early (51,090 gas) on the alias. The cause is the prover-supplied inverse check failing under changed challenges, not a range check.
- Earlier session's forge test hard-coded `!plusR && !maxK`; removed (AGENTS.md: no encoded expected verdicts).
- First run of the current script failed for 7 variants: the plain ZK templates need external libraries (`RelationsLib`, `ZKTranscriptLib`). Linking was added and the run repeated. The failed run is preserved.
- `AztecProtocol/barretenberg` mirror contains no source at any tag. `gh` CLI not installed, so the unauthenticated REST API was used (a gnark issue search was rejected by the API).
- zsh did not word-split a command variable during ad-hoc scratch tests; those were rerun under bash.

## Held-out hygiene statement (which families were read; confirm no unused EVAL family was opened)

Guard results (`python3 scripts/check_holdout.py`): ALLOWED: `AztecProtocol/barretenberg`, `burnt-labs/xion`, `iden3/snarkjs`, `Consensys/gnark`, `noir-lang/noir`. **FORBIDDEN: `AztecProtocol/aztec-packages`, not opened.** Read: generated outputs of pinned toolchains, npm package contents (`@aztec/bb.js`, `snarkjs`), the gnark v0.16.5 templates, Noir docs, and GitHub API metadata for the PRs and issues cited above. No third-party application repository's contents were read. Before the 17 Nov stop, a filename-only listing was run on one local development-family checkout under `tools/cases/`, and no file contents were read. That event is recorded in the ignored stop note under `results/raw/S1/stop/`. No unused EVAL family was opened.

## Recommended next task (one, with a measurable completion criterion)

**S1b, conditional on the author authorizing a local modified-prover experiment:** for each of the 4 split templates (bb.js 3.0.0 keccak, keccakZK; snarkjs 0.7.6 PLONK, fflonk), record on local Anvil whether a proof whose transcript absorbs n + r is accepted. Completion criterion: 4 rows added to `generators.csv`, each with an observed accept/reject from `run.sh`, raw logs and checksums. If authorization is refused, S2b should instead flag these templates statically as split with verdict UNKNOWN.
