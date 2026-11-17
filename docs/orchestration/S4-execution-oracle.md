# S4 — Execution oracle: confirm binding flaws by running them

**Goal for the paper:**

- Every claimed flaw is confirmed by execution, not by human labels. Freeze-2
  precision rests on author-rated cards, and reviewers distrust that.
- Hand-performed E4 validation becomes an automatic step that runs on every
  VIOLATION in held-out v3.
- The paper sentence this enables: "N of M warnings were confirmed end to end
  with real proofs; no human labelling was needed for confirmation."

**Branch:** `sprint/S4`.

**Owns:** `oracle/`, `tests/oracle/`, `reports/S4/`, `results/raw/S4/`.

**Must not edit:** `bindcheck_zk/`, `findings/` (read-only reference).

## Design

The input is a **case manifest** (YAML or JSON) with these fields:

| Field | Content |
|---|---|
| `source` | Pinned repository and commit, and build commands |
| `proof` | How to produce one honest accepted proof: input generator, prover and toolchain versions |
| `deploy` | Deploy script for verifier and consumer on a local Hardhat or Anvil chain, with synthetic assets and accounts |
| `honest_tx` | The honest consumer call (function, arguments, sender) |
| `policy` | Supplied by the human, kept in a separate file: which effects are protected, and who is entitled to them |
| `warning` | Optional BindCheck VIOLATION JSON. It selects which mutation operators to run first. |

The policy follows research contract §6: it states roles, never the expected
verdict.

**Mutation operators.** Each mutates only what the proof does not fix:

| Operator | Mutation |
|---|---|
| `CALLER` | Same calldata from a different sender |
| `FREE_ARG` | Change each consumer argument that is not passed to the verifier, such as recipient or amount |
| `ALIAS` | Add r to each public input the consumer also reads, separately per position |
| `REPLAY` | Submit the honest transaction again after it succeeds |
| `DOMAIN` | Deploy a second consumer instance, or change the chain id, and submit the same proof there |

There is **no** verifier-key forging operator; that is outside the content
limits. γ = δ stays a static finding.

**Observer.** Record protected effects from the state diff of each transaction:

- ERC-20, ERC-721 and ERC-1155 balance and ownership changes;
- native value transfers;
- storage writes to mappings named in the policy (nullifier and claimed sets);
- emitted events.

Use `debug_traceTransaction` with a prestate/diff tracer on the local node.

**Confirmation rule:** `E4-CONFIRMED` requires both of the following.

1. The mutated transaction succeeds through the **unchanged** verifier and
   consumer.
2. Its protected effects violate the policy:
   - an effect goes to someone not entitled to it; or
   - an amount differs from what the proof fixes; or
   - a single-use authorization is consumed twice.

Otherwise the result is `NOT_CONFIRMED`, with the reason (reverted, effects
identical, or policy-permitted), or `UNKNOWN` (build, proving or deploy
failure). Every confirmed result writes a self-contained replay bundle and a
`result.json` in the format of `findings/*/run.sh`.

**Fork mode.** Design an `anvil --fork-url` option, but leave it disabled. It
requires the human's written authorization (H1), and none is recorded yet.

## Steps

1. **Build** `oracle/` with a CLI:

   ```text
   python3 -m oracle run <manifest> --out results/raw/S4/<run-id>
   ```

   A Node/Hardhat or Foundry backend is fine; pick whichever makes state diffs
   easiest, and justify the choice.
2. **ZKredential.** Write manifests that reproduce it from
   `findings/zkredential/` (real snarkjs proof, unchanged contracts). The
   **oracle alone** must reach E4 via `CALLER`/`FREE_ARG`, with no test file
   written for the case.
3. **RacePass.** Same as step 2, from `findings/racepass/`.
4. **Negative controls.** Apply the existing `repair.py` to each case. The
   oracle must return `NOT_CONFIRMED` for every operator on the repaired
   consumer, and the honest transaction must still succeed.
5. **Synthetic controls,** in `tests/oracle/`:
   - a correctly bound consumer, where every operator gives `NOT_CONFIRMED`;
   - a raw-keyed nullifier consumer behind a verifier with no canonical check,
     where `ALIAS` gives `E4-CONFIRMED`;
   - a missing `spent` write, where `REPLAY` gives `E4-CONFIRMED`.
6. **Measure** wall time per operator and per case.

## Completion criteria

- **Real findings.** ZKredential and RacePass reach `E4-CONFIRMED` from their
  manifests alone, and both repaired versions give `NOT_CONFIRMED` for all
  operators.
- **Synthetic controls.** All three behave as specified.
- **Report.** `reports/S4/REPORT.md` follows the handoff template, including:
  - an operator × case result matrix;
  - runtimes;
  - the manifest-writing effort per case, in minutes (the paper must disclose
    manual effort);
  - limitations, such as unsupported proxies or external calls.

## Watch-outs

- **Paths.** The current `findings/*/run.sh` scripts hard-code macOS paths under
  `../bindcheck-zk/`. Make manifests path-independent.
- **Policy is not the verdict.** Policy files must state entitlement, never
  "this should be a VIOLATION". The reviewer will check.
