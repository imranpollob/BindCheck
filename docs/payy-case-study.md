# Payy message-tail case study

This is a single entry point for the existing T09–T20 Payy experiment. It uses public Payy source at pinned commits, synthetic notes and token balances, and owned accounts in Foundry's local EVM. It reproduces the mechanism in the [public advisory](https://github.com/polybase/payy/security/advisories/GHSA-fhxc-63vg-9gwr); it does not establish what happened on a live deployment.

## What is being checked

Payy's `agg_agg` circuit combines inner proofs and exports a 1,000-word public `messages` array. A counter marks the end of the active inner messages. At the earlier commit, the circuit equates the active prefix with the inner proofs, but places no constraint on the remaining outer words. `agg_final` carries those words into its final proof. The Solidity consumer scans the whole array and treats a five-word kind-3 record as a burn. The local candidate keeps an ordinary mint prefix and adds a synthetic burn record in the first five padding words; no burn note or inner burn proof backs that record. The later commit adds `assert_message_tail_zero` and rejects the same candidate at witness generation. [T15](../reports/T15.md), [T16](../reports/T16.md), [T18](../reports/T18.md), and [T19](../reports/T19.md) contain the causal trace and raw-evidence pointers.

| Role | Exact public source commit | Relation to the experiment |
|---|---|---|
| Earlier, untagged Noir revision | `c4d2c9021b8fb9988816eb6987a734b830bfce15` | No outer-tail assertion; used for the candidate proof and consumer settlement |
| Check-added revision | `dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36` | Adds `assert_message_tail_zero`; used for the rejection replay and valid mint control |

The consumer source is byte-identical across these commits. Each circuit run uses its **own** compiled program, key, and verifier; proof and key artifacts are never mixed across revisions. [T20](../reports/T20.md) maps these commits to the advisory and explains why its `zk-circuits-v1.1.12` and `payy v1.3.0` version labels cannot be used as names for this tested pair. The advisory's cited source commit `bf27238761c5839a1538cdbeae4ca29c760031f6` has the same relevant circuit and consumer files as the tested earlier commit.

## Environment and reproduction

Run from the BindCheck repository root on **macOS arm64**. That is the platform of the pinned `nargo` and `bb` downloads in `scripts/t09.sh` and the only platform recorded for the full run. The recorded machine had 8 GiB RAM. The existing scripts also require `git`, `curl`, Python 3, Node/npm, Rust/Cargo with toolchain `1.91.0`, Xcode command-line tools (`xcrun`), and Foundry `forge` (recorded version `1.4.1`). First use needs network access for the public Payy mirror, pinned tool downloads, Rust/Noir packages, Solidity compiler and dependencies, and the proving CRS. `scripts/t09.sh` pins and checks the two tool archives; `scripts/t12.sh` checks OpenZeppelin package integrity. Budget extra time and disk space for the first Rust build and proof setup; T15's first build took about 409 seconds on the recorded machine.

The scripts are sequential and write generated files under ignored `build/`, `tools/`, `payy-consumer/src/`, and `results/raw/`. Run each command only after its predecessor succeeds. T09–T13 establish the ordinary proof and consumer path needed by the differential run. T14 is a separate checker experiment and T17 is a source analysis; neither is a prerequisite for these commands.

```bash
bash scripts/t09.sh  # fetch pinned Payy source and proving tools; check artifact provenance
bash scripts/t10.sh  # generate and verify an ordinary agg_final proof
bash scripts/t12.sh  # stage the real consumer, verifier bytecode, and dependencies
bash scripts/t13.sh  # generate and settle a legitimate mint proof
bash scripts/t15.sh  # same mint prefix plus candidate tail, at both commits
bash scripts/t16.sh  # propagate the earlier commit's candidate through agg_final
bash scripts/t18.sh  # submit that proof to the local consumer; observe token balances
bash scripts/t19.sh  # replay the candidate against the repair; settle a valid mint control
```

T15 also creates a detached earlier-commit worktree at `tools/cases/payy-c4d2c90`. Its recorded run needed a local `Cargo.lock` adjustment in that ignored worktree because the upstream lock file failed `--locked`; the script records that deviation in `results/raw/T15/22_lock_check.txt`. T18 reuses T16's proof bytes; T19 reuses T15's harness and T13's valid mint proof. The scripts write tool versions, commit IDs, artifact hashes, exit codes, and logs to `results/raw/Txx/`. That tree is ignored by Git, so a clone contains the scripts and reports but not the historical raw outputs. This sequence has been run in the author's existing workspace; an independent clean-checkout rehearsal has not been recorded.

## Expected observations and evidence

| Stage | Expected result | Machine-readable file after a run |
|---|---|---|
| T15, earlier `agg_agg` | Control and candidate witnesses satisfy the circuit; candidate proof verifies with the earlier key. Only public message indices 4–8 differ. | `results/raw/T15/90_summary.json` |
| T15, check-added `agg_agg` | Control verifies; the same candidate fails the new `Message is not zero` assertion before a proof is made. | `results/raw/T15/90_summary.json` and `31_noir_diagnostic_dcd5d96.txt` |
| T16, earlier `agg_final` | Candidate proof verifies under the matching final key; the five added words reach final public-input indices 7–11. | `results/raw/T16/90_summary.json` |
| T18, earlier consumer | With the ordinary 100-unit mint escrow registered, the verifier receives the expected calldata, the candidate settles, and `balanceOf` shows rollup 100→93 and burn address 0→7. The mint-only control leaves balances at 100 and 0. | `results/raw/T18/90_summary.json` and `observations/*.json` |
| T19, check-added revision | Candidate fails at circuit witness generation; a separate legitimate mint proof still settles through that revision's own verifier and consumer. | `results/raw/T19/90_summary.json` |

The local candidate uses a burn amount of **7** and recipient `0x…dEaD`; it does not use the advisory's full-balance value. T18 uses a locally owned prover, validator, and minter and checks the ERC20 balances, not just a `Burned` event. Its unregistered-mint and replay controls revert before reaching the verifier, as recorded in the same summary. The repaired commit cannot produce a proof for this candidate, so T19 checks the repair at the earliest rejecting constraint and checks legitimate consumer behavior separately. A cross-revision proof submission would not test the repair because the final verification keys differ.

For artifact review, start with the concise [T20 claim map](../reports/T20.md), then inspect [T15](../reports/T15.md) for the source diff and first proof, [T16](../reports/T16.md) for recursive propagation, [T18](../reports/T18.md) for actual settlement and balance observations, and [T19](../reports/T19.md) for the repair. The source-based prototype in [T21](../reports/T21.md) reports agreement on this known pair and its sibling `agg_utxo`; it is in-sample and does not establish generalization.

## Scope of the conclusion

The local evidence supports a proof-to-execution binding failure at the earlier commit under the test's owned authorization identities, and confirms that the check-added commit rejects this specific witness while accepting a legitimate mint. The advisory is a known public disclosure, not a new BindCheck discovery. Live deployment history, affected-version labels, real-world financial impact, independent clean-machine reproduction, and detection on held-out applications remain unresolved. The current checker work does not establish that BindCheck would have found this issue before disclosure.
