# S4 — Execution oracle: confirm binding findings by running them
Status: DONE
Verdict/outcome: E4-CONFIRMED on both real findings (ZKredential, RacePass) from
their manifests alone; all repaired variants and the correctly-bound synthetic
control return NOT_CONFIRMED for every operator; the two targeted synthetic
controls confirm via exactly their intended operator.

AI disclosure: implemented by the S4 AI coder running on Claude Opus (claude-opus-4-8
in Claude Code). All generated code, manifests, policies and results were
executed and inspected by the author; the reported verdicts come from real runs,
not from model assertion.

## What was done

Built `oracle/`, a local-only, manifest-driven **execution oracle** (test
harness) that automates the research-contract §8 **E4** step: it re-runs an
already-valid snarkjs proof against the **unchanged** verifier and consumer on an
owned local **Anvil** chain, applies five mutation operators mechanically, and
judges each mutated transaction's committed effects against a human
entitlement-only policy.

- **`oracle/runner.py`** — orchestration and safety gates: refuses any manifest
  not asserting `safety.local_only=true` / `fork_enabled=false`; refuses a policy
  that encodes a verdict (forbidden keys/phrases, checked structurally); `--fork-url`
  always rejected (H1 not approved); stages pinned source by `git archive`; runs
  the declared build/proof commands; starts and tears down a private Anvil per
  variant; writes a self-contained `result.json` and a replay bundle per
  confirmed trial. Any build/proof/deploy failure becomes `UNKNOWN`, never safe.
- **`oracle/evm_runner.cjs`** — a fully **generic** ethers-v6 driver (no per-case
  JavaScript). It loads compiled artifacts (Hardhat and Foundry shapes), deploys
  and calls contracts by ABI from a declarative scenario, resolves a small
  value-expression DSL (`$signer $addr $proofPart $pubArray $pub $pubAsAddress
  $pubAsBytes32 $keccakUtf8 $nowPlus $tuple …`), observes ERC-20/721 effects from
  receipts plus `debug_traceTransaction` prestate diffs, and evaluates the
  entitlement/single-use policy. The confirmation came from the oracle alone; **no
  test file was written for either real case.**
- **Operators.** `CALLER` (same calldata, different sender), `FREE_ARG` (a
  consumer argument not fed to the verifier), `ALIAS` (a read public input offset
  by the field modulus r), `REPLAY` (honest tx resubmitted), `DOMAIN` (same proof
  against a second consumer instance). `ALIAS`/`REPLAY` run the honest tx first so
  single-use is tested against an already-consumed authorization.
- **Policies** (`oracle/cases/*/policy.json`, `tests/oracle/*.policy.json`) state
  entitlement only — who may receive the protected effect, and how often an
  authorization may be used — reduced to canonical field keys. They never state
  the expected verdict; `runner.py` enforces this.
- **Fork mode** designed (CLI shape + manifest flag) but **disabled and
  fail-closed**; no `anvil --fork-url` path is reachable.

## Evidence (paths, hashes, commands, exit codes, tool versions)

Commands (all exit 0 unless noted):

```
python3 -m oracle run oracle/cases/zkredential/manifest.json --out results/raw/S4/zk-final-043621
python3 -m oracle run oracle/cases/racepass/manifest.json    --out results/raw/S4/rp-final-043621
python3 -m oracle run tests/oracle/bound.manifest.json       --out results/raw/S4/bound-regress-043621
python3 -m oracle run tests/oracle/alias.manifest.json       --out results/raw/S4/alias-042217
python3 -m oracle run tests/oracle/replay.manifest.json      --out results/raw/S4/replay-042429
python3 -m oracle run oracle/cases/zkredential/manifest.json --out results/raw/S4/forktest --fork-url … # exit 2, rejected
```

Tool versions / revisions:

- node v24.19.0, npm 11.17.0; ethers pinned **6.13.4** (driver).
- anvil / forge 1.4.1-stable (Foundry).
- circom 2.2.3 (`bindcheck-zk/tools/circom-src`) for ZKredential; circom 2.1.9
  (`bindcheck-zk/tools/circom-2.1.9`) for RacePass; snarkjs from each project.
- ZKredential source: `ethpanda-org/ETHShanghai-2025@23917814522bac494150c7e99a123aa15a448155`, `projects/ZKredential` (DEV family F30; holdout check: ALLOWED).
- RacePass source: `Servesh21/RacePass@abd54b5c541ac9d26f938a6bdbd78545526249e5` (DEV family F39; holdout check: ALLOWED).
- Workspace HEAD at run: `571e01a`.

Evidence locations (ignored `results/raw/S4/`): per-run `result.json`,
`result-<variant>.json`, `logs/NN-*.log` (every command with cwd/argv/exit),
`proofs/` (real proof.json/public.json + off-chain `snarkjs groth16 verify`
pass), `driver-<variant>.json`, and `replay-bundles/<slug>/` (manifest + policy +
result.json + `run.sh`) for each confirmed trial:

- `results/raw/S4/zk-final-043621/replay-bundles/original-CALLER-attacker/`
- `results/raw/S4/rp-final-043621/replay-bundles/original-FREE_ARG-credHash/`
- `results/raw/S4/alias-042217/replay-bundles/synthetic-ALIAS-0/`
- `results/raw/S4/replay-042429/replay-bundles/synthetic-REPLAY/`

## Results (tables; exact counts)

**Operator × case matrix** (E4 = E4-CONFIRMED, NOT = NOT_CONFIRMED). Every real
run established real-verifier acceptance and honest-tx success first.

| Case / variant | CALLER | FREE_ARG | ALIAS | REPLAY | DOMAIN |
|---|---|---|---|---|---|
| **ZKredential** original | **E4** (amount→attacker) | NOT (amount: no proof-fixed amount) | NOT (verifier rejects r-offset) | NOT (proof-use guard) | NOT (effect still to proof wallet) |
| ZKredential repaired | NOT (proof wallet mismatch) | NOT (mint not approved) | NOT | NOT | NOT (mint not approved) |
| **RacePass** original | NOT (presenter not bound) | **E4** (credHash ≠ KYC commitment) | NOT (verifier rejects r-offset) | NOT (both correctly bound) | NOT (new instance correctly bound) |
| RacePass repaired | NOT (recipient mismatch) | NOT (credential mismatch) | NOT | NOT (no 2nd effect) | NOT |
| **Synthetic** bound | NOT | NOT | NOT | NOT | NOT |
| Synthetic alias | NOT | NOT | **E4** (pos 0) | NOT | NOT |
| Synthetic replay | NOT | NOT | NOT | **E4** | NOT |

FREE_ARG for ZKredential varies `amount`; the recipient path is covered by
CALLER (the gateway mints to `msg.sender`). FREE_ARG for RacePass varies
`credHash` and `recipient`; only `credHash` confirms, matching the policy that
firmly binds only the stored credential (README/source-comment supported).
ALIAS enumerates two read positions per case; the synthetic-alias E4 is position
0 (the raw nullifier key), position 1 reverts on the reused nullifier.

**Runtimes** (wall, real runs include per-run dependency install + real proving +
compile; each trial redeploys for isolation):

| Run | total wall | per-trial (approx) |
|---|---|---|
| ZKredential (2 variants, 14 trials) | 434 s | ~25 s (orig), ~29 s (repaired); DOMAIN ~45 s |
| RacePass (2 variants, 14 trials) | 391 s | ~21 s (orig), ~17 s (repaired); DOMAIN ~37 s |
| Synthetic bound / alias / replay | 124 / 132 / 132 s | ~16 s; DOMAIN ~29 s |

**Manifest-writing effort** (AI-assisted authoring in this session; the paper
must disclose manual effort — these are approximate, since per-manifest
wall-clock was not separately timestamped):

| Artifact | approx author time |
|---|---|
| ZKredential manifest + policy (deploy graph, struct ctor, proof pipeline) | ~45 min |
| RacePass manifest + policy (dual proofs, bytes32 normalization) | ~35 min |
| Three synthetic manifests + policies (generated from one template) | ~25 min total |

Most of the per-case effort was transcribing the deployment graph and
constructor arguments from the project source; the proof pipeline steps were
adapted from each `findings/*/run.sh`.

## Assumptions and limitations

- **Policy interpretations are provisional.** The confirmed violations are
  `VIOLATION` only under the stated conditional policies (`findings/*/policy.md`);
  independent author/advisor confirmation is still MISSING. ZKredential's amount
  entitlement and RacePass's presenter/one-pass-per-credential policies are
  deliberately **not** asserted (UNKNOWN), so the oracle reports NOT_CONFIRMED
  there rather than overclaiming.
- **Synthetic verifiers are stand-ins.** The three synthetic controls use trivial
  verifiers to isolate consumer-binding logic and the oracle's judgement; they
  carry no cryptographic or security claim. The two real cases use real snarkjs
  proofs and unchanged verifiers.
- **Single-use detection** assumes the prelude and the mutated transaction share
  the authorization key (true by construction for REPLAY and ALIAS).
- **REPLAY on the RacePass repaired variant** reverted at the client nonce layer
  in this run rather than at the contract guard; the verdict (no second effect,
  NOT_CONFIRMED) is unaffected, and the contract-level `usedCredential` guard is
  shown independently by `findings/racepass/repair.test.js`.
- **Unsupported surface:** proxy/upgradeable consumers, external/oracle calls
  during the consumer path, non-Groth16 proof systems, and any multi-block
  reachability are out of scope; such a case would be `UNKNOWN`.
- **No fork, no broadcast, no live contract, no forged proof** — enforced in code.

## Failed approaches / surprises

- The initial draft used per-case JavaScript "adapters", which would have been a
  test file written for the case (prohibited by S4 steps 2–3). Replaced with the
  generic ABI-driven driver + declarative scenarios.
- `DOMAIN` first produced a false `E4` on RacePass because the view-entitlement
  queried the fixed-name consumer instead of the instance that emitted the
  effect; fixed to resolve the view by the effect's contract address, after which
  DOMAIN correctly reports policy-permitted.
- `racepass/make_inputs.js` needs `circomlibjs` resolved from the staged
  `node_modules`; fixed with a per-step `NODE_PATH`.
- The verdict-token gate initially rejected a policy for the word "verdict" in its
  own prose; narrowed to structural key/phrase checks.

## Held-out hygiene statement

Only the two DEV families already in `findings/` were used (F30
ethpanda-org/ETHShanghai-2025, F39 Servesh21/RacePass); `scripts/check_holdout.py`
returns ALLOWED for both. No EVAL/held-out family in the v3 pool was opened,
cloned, built, or analyzed. `bindcheck_zk/` and `findings/` were read-only; the
DEV checkouts under `bindcheck-zk/` were staged by `git archive` into ignored run
dirs, never modified.

## Recommended next task

**S4b — reachable-state and value binding.** Extend the observer to record a
read-only "value at risk" for a confirmed effect (token supply / `balanceOf`
deltas) and to admit a manifest-declared non-trivial initial state, so the report
can state magnitude, not just direction, of a confirmed violation. Completion
criterion: for each E4-CONFIRMED trial, `result.json` carries a signed
protected-effect magnitude and the admitted initial state it was reached from,
with the correctly-bound synthetic control still returning NOT_CONFIRMED. (Any
on-chain value query against a real deployment remains gated on H6.)
