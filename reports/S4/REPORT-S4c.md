# S4c — Multi-effect and obligation accounting for confirmed violations
Status: DONE
Verdict/outcome: the execution oracle now confirms an **undischarged required
obligation** (a required effect the honest path commits but a mutated tx omits),
not only an unauthorized effect. On the synthetic obligation control, the
vulnerable consumer is `E4-CONFIRMED` via exactly `FREE_ARG(skipFee)` with the
omitted obligation named (`fee-to-treasury`); the correctly-bound consumer
returns `NOT_CONFIRMED` for every operator, including `FREE_ARG(skipFee)`.

AI disclosure: implemented by the S4 AI coder on Claude Opus (claude-opus-4-8 in
Claude Code). All code and results were executed and inspected by the author; the
reported verdicts come from real runs, not from model assertion.

## What was done

Extended the oracle (`oracle/`, S4/S4b) so a policy can declare required
obligations and the oracle scores whether each mutated transaction discharges
them, closing the gap between "committed an unauthorized effect" and "granted the
benefit but skipped a required effect" (research-contract §8 E4, undischarged
required obligation).

- **Obligation policy clause.** A policy may declare `required_obligations:
  [{id, description, match}]`. `match` ({`type`, `from`, `contract_role`, `to`})
  names the committed effect an authorization must produce alongside its benefit
  — e.g. a fee transfer to the treasury, or a nullifier-marking mint. `to` is a
  value expression resolved to the required recipient. The clause states an
  entitlement ("each authorization owes this effect"), never a verdict;
  `runner.py`'s structural gate accepts it unchanged.
- **Honest-conditioned scoring.** The driver records which obligations the
  **honest reference run** discharges and faults a mutated trial only when all
  three hold: the honest path discharged the obligation, this mutated tx granted
  the protected benefit, and the obligation effect is absent. Conditioning on the
  honest path avoids flagging an obligation the real behaviour never produces
  (which would overclaim). A new `undischarged_obligation` violation type carries
  the obligation id and its `discharged_by_honest` / `discharged_by_mutation`
  flags; the confirmation rule reuses the existing E4 gate (real verifier +
  consumer acceptance, benefit committed) with this violation added.
- **Per-trial obligation ledger.** Every trial's `result.json` carries an
  `obligations` array (`id`, `description`, `discharged_by_honest`,
  `discharged_by_mutation`), and the honest block records
  `obligations_discharged`, so a reader sees the full multi-effect accounting,
  not only the faulted case.

No change to the operators, the safety gates, the value-at-risk observer (S4b),
the entitlement-only policy contract, or the existing cases' policies (which
declare no obligations, so the new path is a no-op for them). Fork mode stays
built-but-disabled.

## Evidence (paths, commands, tool versions)

Same toolchain as S4/S4b (node v24.19.0; ethers 6.13.4; anvil/forge 1.4.1;
Solc 0.8.20 for the synthetic). Command:

```
python3 -m oracle run tests/oracle/obligation.manifest.json --out results/raw/S4/s4c-obligation-<ts>
```

Run used for the results below: `results/raw/S4/s4c-obligation-20261118T133614Z`
(status DONE, wall 371 s; manifest sha256 `1d6c3a63…`, policy sha256
`f262bf62…`). Confirmed-trial replay bundle:
`.../replay-bundles/vulnerable-FREE_ARG-skipFee/` (manifest + policy +
result.json + run.sh). Regression: an existing control
(`tests/oracle/bound.manifest.json`, `results/raw/S4/s4c-regress-bound-<ts>`) was
re-run under the changed driver and still returns `NOT_CONFIRMED` for all five
operators with the honest tx succeeding. Raw evidence under ignored
`results/raw/S4/s4c-*`.

New/changed tracked files: `tests/oracle/synthetic/src/Synthetic.sol`
(`ObligationConsumerVulnerable`, `ObligationConsumerFixed`),
`tests/oracle/obligation.manifest.json`, `tests/oracle/obligation.policy.json`,
`oracle/evm_runner.cjs` (obligation matcher + scoring + ledger),
`oracle/README.md` (schema + confirmation rule), `docs/project-status.md`.

## Results

Synthetic obligation control, two variants sharing one entitlement-only policy.
The honest path of each variant mints the reward (`+1000` to the proof-bound
holder) **and** pays the fee (`+50` to the treasury) — so both discharge the
`fee-to-treasury` obligation. The free `skipFee` flag is not bound to the proof.

**Operator × variant matrix** (E4 = `E4-CONFIRMED`, NOT = `NOT_CONFIRMED`):

| Variant | CALLER | FREE_ARG(skipFee) | ALIAS-0 | ALIAS-1 | REPLAY | DOMAIN |
|---|---|---|---|---|---|---|
| **vulnerable** (fee gated by free flag) | NOT | **E4** (obligation `fee-to-treasury` omitted) | NOT (verifier rejects r-offset) | NOT (r-offset) | NOT (nullifier spent) | NOT (policy-permitted) |
| **bound** (fee unconditional) | NOT | NOT (fee still paid) | NOT | NOT | NOT (nullifier spent) | NOT |

The single confirmation is `vulnerable · FREE_ARG(skipFee)`: the mutated tx
passes the unchanged canonical verifier and the consumer, commits the reward
(benefit, `+1000` token-wei to the bound holder) and omits the fee. The oracle
reports:

```
undischarged_obligation  fee-to-treasury  discharged_by_honest=true  discharged_by_mutation=false
value_at_risk: reward +1000 token-wei → holder;  omitted obligation (honest): fee +50 → treasury
```

The **bound** variant's `FREE_ARG(skipFee)` is `NOT_CONFIRMED` ("policy-permitted")
because the fixed consumer pays the fee regardless of the flag, so the obligation
is discharged. The nullifier guard and canonical verifier make `REPLAY` and
`ALIAS` revert, isolating the obligation behaviour to the one operator.

Completion criterion met: a control where the honest tx commits effect A (reward)
and a required effect B (fee), and a mutated tx commits A while omitting B, is
`E4-CONFIRMED` with the omitted obligation named; the fully-bound control stays
`NOT_CONFIRMED` for every operator.

Runtimes (wall): full run 371 s (two variants × 6 trials); per-operator ~25 s,
ALIAS ~49 s (two positions), DOMAIN ~37 s (second instance). Confirmed trial 24.7 s.

## Assumptions and limitations

- **Obligation = a committed, observable effect.** The oracle scores obligations
  that surface as ERC-20/721 transfers (a fee payment, a nullifier-marking mint).
  An obligation discharged only as a storage write with no event is visible in
  the prestate diff but is not matched by the transfer-based matcher; such a case
  would need an explicit storage-slot obligation match (future work).
- **Honest-conditioned by design.** An obligation the honest path does not
  discharge is never faulted, even if declared — the oracle will not claim a
  violation the reference behaviour itself exhibits. This is deliberate and
  disclosed in each trial's ledger.
- **Synthetic verifier.** The obligation control uses the trivial canonical
  verifier (like the other synthetic controls) to isolate consumer obligation
  logic; it carries no cryptographic claim. The two real cases (ZKredential,
  RacePass) still use real snarkjs proofs and unchanged verifiers; neither real
  policy declares an obligation yet, so their verdicts are unchanged.
- All S4/S4b limitations (provisional real-case policies, unsupported
  proxy/external-call surface, no fork/broadcast) carry over unchanged.

## Failed approaches / surprises

- Scoring an obligation purely from the policy (not conditioned on the honest
  run) was rejected: it would fault a declared obligation that the real path
  never commits, overclaiming. Conditioning on the honest reference keeps the
  verdict grounded in observed honest behaviour.
- `MintToken` exposes `balanceOf` but no `totalSupply`, so the confirmed trial's
  value-at-risk shows the signed `balanceOf` delta (`holder +1000`) with a null
  supply delta — correct, and the omitted obligation's magnitude (`fee +50 →
  treasury`) is read from the honest reference's effects.

## Held-out hygiene statement

No new third-party source was opened. The obligation control is a new synthetic
contract pair in the already-present `tests/oracle/synthetic` (owned, local-only,
test tokens of no value). The two real DEV families (F30, F39) were not re-run
for S4c and are unaffected. `bindcheck_zk/` and `findings/` untouched; no
EVAL/held-out family opened.

## Recommended next task

**S4d — real-case obligation policies.** Author an obligation clause for the two
real findings where the source implies one (e.g. a nullifier that must be spent,
a fee that must be paid) and re-run ZKredential and RacePass, so the oracle can
report undischarged-obligation violations on real cases, not only the synthetic
control. Completion criterion: for at least one real case, a mutated trial is
`E4-CONFIRMED` (or justified `NOT_CONFIRMED`) on an obligation clause whose
requirement is cited to the project source, with the honest path discharging it.
