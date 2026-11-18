# S4b — Reachable-state and value binding for confirmed effects
Status: DONE
Verdict/outcome: every `E4-CONFIRMED` trial now carries a signed protected-effect
magnitude and the admitted initial state it was reached from; the
correctly-bound synthetic control still returns `NOT_CONFIRMED` for all
operators.

AI disclosure: implemented by the S4 AI coder on Claude Opus (claude-opus-4-8 in
Claude Code). All code and results were executed and inspected by the author.

## What was done

Extended the execution oracle (`oracle/`, S4) so a confirmed binding violation
reports *how much* value it moves, measured against a declared starting state,
without leaving the owned local chain.

- **Admitted initial state.** A manifest may declare `scenario.initial_state`: a
  list of setup transactions applied on the local Anvil chain after deploy and
  `post_deploy`, before any honest or mutated call. Each trial records which
  steps were applied, so a magnitude is measured against a non-trivial baseline
  rather than a blank chain. The honest reference run applies the same baseline.
- **Value-at-risk observer.** Immediately before the mutated transaction (after
  deploy + initial_state + any prelude) and again after it, the driver snapshots
  `totalSupply()` and every named signer's `balanceOf(...)` on each token-like
  contract (ERC-20 amounts and ERC-721 holding counts; missing views skipped).
  It reports the signed per-account and per-supply deltas. These are **read-only
  view calls on owned local deployments** — no `balanceOf` against any real
  deployment (that remains gated on H6), no fork, no broadcast.
- **Per-effect magnitude.** Each committed protected effect carries a signed
  `magnitude` (ERC-20 value in token-wei, or one `nft-unit` per minted token id)
  and its recipient, surfaced under `value_at_risk.effects` in every trial's
  `result.json` and in each confirmed trial's replay bundle.

No change to the verdict logic, the operators, the safety gates, or the
entitlement-only policy contract. Fork mode stays built-but-disabled.

## Evidence (paths, commands, tool versions)

Same toolchain as S4 (node v24.19.0; ethers 6.13.4; anvil/forge 1.4.1; circom
2.2.3 / 2.1.9; snarkjs per project). Commands:

```
python3 -m oracle run tests/oracle/bound.manifest.json  --out results/raw/S4/s4b-bound-<ts>
python3 -m oracle run tests/oracle/alias.manifest.json  --out results/raw/S4/s4b-alias-<ts>
python3 -m oracle run tests/oracle/replay.manifest.json --out results/raw/S4/s4b-replay-<ts>
python3 -m oracle run oracle/cases/zkredential/manifest.json --out results/raw/S4/s4b-zk-<ts>
python3 -m oracle run oracle/cases/racepass/manifest.json    --out results/raw/S4/s4b-rp-<ts>
```

Each `result-<variant>.json` trial now contains `value_at_risk`
{`admitted_initial_state`, `deltas`, `effects`}. Raw evidence under ignored
`results/raw/S4/s4b-*`.

## Results

Final clean run set (`results/raw/S4/final-*-051421`), all `status=DONE`. Every
`E4-CONFIRMED` trial now carries a signed magnitude and the admitted initial
state; the bound control and all repaired variants stay `NOT_CONFIRMED`.

**Value at risk for each confirmed trial:**

| Case / variant / operator | signed magnitude | recipient | admitted initial state |
|---|---|---|---|
| ZKredential original · CALLER | +1.0e18 token-wei (ERC-20), total supply 0 → 1e18 | attacker (acct #2) | blank baseline |
| RacePass original · FREE_ARG(credHash) | +1 nft-unit (ERC-721) | holder (acct #1) | blank baseline |
| Synthetic alias · ALIAS-0 | +1000 token-wei | holder | `mint` 500000 baseline applied |
| Synthetic replay · REPLAY | +1000 token-wei | holder | `mint` 500000 baseline applied |

For the synthetic double-spend controls, the +1000 magnitude is the *second*
(unauthorized) mint, measured against the 500000-unit baseline established by the
admitted initial state — demonstrating a non-trivial starting state, not a blank
chain.

**Full verdict matrix (unchanged from S4, now with value fields):** both repaired
real variants and the bound synthetic control return `NOT_CONFIRMED` for all
operators; `synthetic-alias` confirms only `ALIAS-0`, `synthetic-replay` only
`REPLAY`, ZKredential only `CALLER`, RacePass only `FREE_ARG(credHash)`.

Runtimes (wall, per full run): ZKredential 427 s, RacePass 395 s, synthetic
bound/alias/replay 152 / 161 / 160 s.

**Robustness fix found during S4b.** Adding per-trial value snapshots exposed a
latent nonce/estimate-gas race on the repaired variants' redeploys (the error
transactions were deploy bytecode). Fixed by explicit sequential nonce
management (`signer.getNonce("latest")` per write), a fixed deploy `gasLimit`
that skips a flaky `eth_estimateGas`, and a static-network provider. After the
fix, isolated and batched reruns are deterministic (all repaired trials
`NOT_CONFIRMED`).

## Assumptions and limitations

- Value magnitudes are **local and synthetic** — test tokens of no value on an
  owned chain. They state the size and direction of the committed effect, not a
  claim about any deployed system's funds; deployed value at risk stays `UNKNOWN`
  and gated on H6.
- The observer watches named signers and token `totalSupply`; value routed to an
  unnamed address or held in a non-`balanceOf` contract is not scored (it still
  appears as a protected effect and in the prestate diff).
- The admitted initial state is whatever the manifest declares; it is disclosed
  verbatim in each result so a reader can judge whether the baseline is adequate.
- All S4 limitations (provisional policies, synthetic verifiers for the controls,
  unsupported proxy/external-call surface) carry over unchanged.

## Failed approaches / surprises

- Measuring deltas by reconstructing "before" from the effect value was dropped
  in favour of an explicit before/after snapshot, so a prelude or initial_state
  can shift the baseline and the delta stays exact.

## Held-out hygiene statement

No new third-party source was opened. Only the two DEV families already used in
S4 (F30 ethpanda-org/ETHShanghai-2025, F39 Servesh21/RacePass; both ALLOWED) were
re-run. `bindcheck_zk/` and `findings/` untouched; no EVAL/held-out family
opened.

## Recommended next task

**S4c — multi-effect and obligation accounting.** Extend the observer to score a
required-obligation that is *omitted* (an expected effect that did not commit,
e.g. a nullifier write or a fee transfer), not only effects that did commit, so
the oracle can confirm undischarged-obligation violations (research-contract §8
E4 "undischarged required obligation") as well as unauthorized effects.
Completion criterion: a synthetic control where the honest tx commits effect A
and a required effect B, and a mutated tx commits A while omitting B, is reported
`E4-CONFIRMED` with the omitted obligation named; the fully-bound control stays
`NOT_CONFIRMED`.
