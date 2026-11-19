# F3 — residual oracle false-E4 boundaries

Status: DONE (EVM evidence run by the reviewer outside the Codex sandbox; see "Reviewer EVM evidence")
Verdict/outcome: Source-level gates and regression tests are implemented; EVM before/after controls and the required re-confirmation matrix remain `UNKNOWN`. The reviewer later ran the owned-local EVM controls and the full re-confirmation; see the section below.

AI disclosure: OpenAI Codex, GPT-6 family (exact serving model ID unavailable). The AI-authored code, labels and claims require human inspection; the helper probes are not independent policy annotation.

## What was done

- XR-01: mint-shaped ERC-721 effects require the recipient to own the token after the transaction, a +1 recipient `balanceOf` change, and no prior `ownerOf` result naming the same recipient. The `from`/`to` mint direction is checked. A pre-mint `ownerOf` revert is tolerated only under the declared standard ERC-721 semantics and corroborating balance change.
- XR-02: the mutated transaction's `callTracer` root must be the consumer with matching calldata. Every declared verifier check must match a distinct direct consumer-to-verifier call by address and exact ABI calldata and return boolean true. `ALIAS` changes the expected public-input array for the relevant proof; other proof parts remain exact.
- XR2-01: every declared or policy-referenced state view must have bigint observations before and after the honest and mutated transactions. A failed or absent read now yields `UNKNOWN / VIEW_READ_FAILED`, never a zero baseline.
- XR-07: a global occurrence allocation prevents one committed effect from discharging two policy clauses. XR-08's command-token denylist is described at its actual boundary in `oracle/README.md`; the driver no longer attempts a network package install when pinned ethers is absent. XR-09: focused unit tests now cover the new gates.
- Added three owned-local Solidity scenarios and entitlement-only manifests/policies: pre-owned ERC-721 recipient with a false mint-shaped log, a two-verifier consumer whose mutated branch skips one required verifier, and getters that become readable after a transaction without a credit increase.

## Evidence (paths, hashes, commands, exit codes, tool versions)

Base checkout: `9d340eb362090415b9c68b7eeab720a1bc3a0a74`. Python 3.12.12, pytest 9.0.1, Node v24.19.0, ethers 6.13.4 from an already-installed offline cache copied into ignored `results/raw/F3/.driver/`, Forge/Anvil 1.4.1-stable (`cf7746048646f2ecff48246dd61e265e49ab16f0`). No network install was run.

- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/oracle -q` → exit 0, **25 passed**.
- `forge build --root tests/oracle/synthetic` → exit 0; the first F3 control runner's build compiled the changed source with Solc 0.8.20, exit 0. The final direct build reported no files changed, exit 0.
- `node --check oracle/evm_runner.cjs` and `git diff --check` → exit 0.
- `_validate_manifest` on all three `tests/oracle/f3_*.manifest.json` files → exit 0, three validated.
- `anvil --silent --port 38555 --chain-id 31337` → exit 1, `Error: Operation not permitted (os error 1)`; starting a local socket is unavailable in this managed session.
- `python3 -m oracle run tests/oracle/f3_existing_owner.manifest.json --out results/raw/F3/pre-existing-owner` → exit 2, `Operation not permitted` after `forge_build` exit 0. Equivalent attempts for `f3_two_verifier` and `f3_late_view` → exit 2 at Anvil start after `forge_build` exit 0. Their `result.json` files are `UNKNOWN` and contain no variant result. The `pre-*` names are attempt identifiers; **none is an EVM pre-fix result**.
- `git show HEAD:oracle/evm_runner.cjs` captured the original helper implementation under ignored `results/raw/F3/baseline-evm_runner.cjs`. `ORACLE_ETHERS_PATH=$PWD/results/raw/F3/.driver/node_modules/ethers node results/raw/F3/helper_probe.cjs before` and `... after` → exit 0. Outputs: [`helper-before.json`](../../results/raw/F3/helper-before.json) and [`helper-after.json`](../../results/raw/F3/helper-after.json). These are source-level helper probes with stand-in state/trace objects, **not E4 trials**.

Current SHA-256: `oracle/evm_runner.cjs` `2ed174707d69740e65a48d5eb21401450fee83d261a8ce150151171247bc23d6`; `oracle/runner.py` `1c8753ad7adbd201ebbdb3335e6d3f40e0859a33e0f38d2428ec6fe2b2b6e9b0`; `tests/oracle/synthetic/src/Synthetic.sol` `08e91bffd0f6ae7d299bd9fdb29c026b59e641f71be3212c41c93296165abfe1`.

## Results (exact counts)

| Boundary | Original helper probe | Patched helper probe | Owned-local EVM before/after |
|---|---|---|---|
| XR-01 pre-owned ERC-721 recipient | `corroborated: true` | `corroborated: false` | `UNKNOWN` / Anvil unavailable |
| XR-02 one of two verifier calls | `established: true` | `established: false` | `UNKNOWN` / Anvil unavailable |
| XR2-01 missing view baseline | inferred `credit: +150` | throws missing-before error, caught as `VIEW_READ_FAILED` in trial path | `UNKNOWN` / Anvil unavailable |

Required re-confirmation matrix under the patched EVM gates:

| Case | Patched EVM verdict |
|---|---|
| ZKredential original / repaired | `UNKNOWN` — not rerun; Anvil unavailable |
| RacePass original / repaired | `UNKNOWN` — not rerun; Anvil unavailable |
| Synthetic alias / replay / obligation / bound | `UNKNOWN` — not rerun; Anvil unavailable |
| Synthetic F2 controls (fake effect / skip verifier / underpay / view obligation) | `UNKNOWN` — not rerun; Anvil unavailable |
| AZ1 faulty / fixed | `UNKNOWN` — not rerun; Anvil unavailable |

No claim is made that F2's recorded E4 results survive these gates. No full oracle EVM verdict changed **in this session**, because no EVM replay completed.

## Assumptions and limitations

The ERC-721 fallback from a pre-mint `ownerOf` revert to a precise `balanceOf` increase assumes standard atomic ERC-721 accounting. Exact verifier calldata and true call results establish trace correspondence for declared checks; they do not prove the consumer semantically used the returned boolean in every possible control-flow shape. The command-token denylist does not stop wrapper-script URL construction, inherited environment variables or redirects. The three negative controls use synthetic trivial verifiers and cannot carry a real-proof E4 claim. No EVM before/after control or retained real-case proof pipeline ran in this environment.

## Failed approaches / surprises

The local Anvil binary fails with `Operation not permitted` even when invoked directly. The runner captures the same failure as `UNKNOWN` after successful Forge builds. An initial unit test exposed a bigint diagnostic-serialization error in the new view gate; it was corrected and the complete 25-test suite passed.

## Held-out hygiene statement

Only the F3-owned synthetic fixtures, existing F2/XR2 reports, and existing DEV manifest metadata were read. No unused EVAL family, third-party checkout, live deployment, local fork or public RPC was opened. `bindcheck_zk/`, `findings/`, and `paper/` were not edited.

## Recommended next task

Run F3 in a local environment where Anvil can bind loopback: first replay each three-control manifest against base commit `9d340eb...` to obtain the predicted false E4, then against this working tree to obtain `UNKNOWN` or `NOT_CONFIRMED`; rerun all retained cases in the matrix and require `python3 -m pytest tests/oracle` green. Completion criterion: all three EVM before/after pairs and the full re-confirmation matrix are recorded with hashes and exact verdicts before declaring F3 done.

## Reviewer EVM evidence (added by the orchestrator, 2026-11-18)

The Codex sandbox could not bind a loopback socket for Anvil. The reviewer ran
the same manifests outside the sandbox (Anvil 1.4.1, local chain 31337 only, no
fork, no RPC to public chains). Raw outputs are in the ignored
`results/raw/F3/after-*/` (patched) and, for the baseline, in a detached
worktree of base commit `9d340eb` with only the three F3 manifests/policies and
`Synthetic.sol` copied in (`results/raw/S4/F3-before-*/`, because the base
runner only accepts S4-owned output paths).

### Before/after controls

| Control | Base oracle (`9d340eb`) | Patched oracle (F3) |
|---|---|---|
| XR-01 pre-owned ERC-721 + mint-shaped log | `E4-CONFIRMED` (FREE_ARG-recipient) — the false E4 | `UNKNOWN / EFFECT_NOT_STATE_CORROBORATED: ownership_change_mismatch` |
| XR-02 mutated branch skips one of two verifiers | `E4-CONFIRMED` (FREE_ARG-skipSecond) — the false E4 | `UNKNOWN / VERIFIER_PATH_NOT_ESTABLISHED` |
| XR2-01 getter unreadable before the tx | `E4-CONFIRMED` (FREE_ARG-omitBacking) — the false E4 | `UNKNOWN / VIEW_READ_FAILED` |

Each control reproduces the XR2 scenario on the old logic and is closed by F3.

### Re-confirmation matrix (patched oracle; every manifest; honest tx succeeded in every variant)

| Case / variant | E4-CONFIRMED trials | Other trials |
|---|---|---|
| ZKredential original | `CALLER-attacker` | NOT_CONFIRMED |
| ZKredential repaired | — | all NOT_CONFIRMED |
| RacePass original | `FREE_ARG-credHash` | NOT_CONFIRMED |
| RacePass repaired | — | all NOT_CONFIRMED |
| Synthetic alias | `ALIAS-0` | NOT_CONFIRMED |
| Synthetic replay | `REPLAY` | NOT_CONFIRMED |
| Synthetic obligation, vulnerable / bound | `FREE_ARG-skipFee` / — | NOT_CONFIRMED |
| Synthetic bound | — | all NOT_CONFIRMED |
| View obligation, vulnerable / fixed | `FREE_ARG-numRealRows` / — | NOT_CONFIRMED |
| AZ1 testbed, faulty / fixed | `FREE_ARG-numRealRows` / — | NOT_CONFIRMED |
| neg_fakeeffect | — | `UNKNOWN / EFFECT_NOT_STATE_CORROBORATED` |
| neg_skipverify | — | `UNKNOWN / VERIFIER_PATH_NOT_ESTABLISHED` |
| neg_underpay | `FREE_ARG-feeAmount` (required 50-unit fee not paid) | NOT_CONFIRMED |

No real-case or synthetic E4 changed under the stricter gates. All 17 manifest
runs exited 0. `python3 -m pytest tests/oracle` reported 25 passed in the lane.
