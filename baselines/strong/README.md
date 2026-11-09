# Strong straightforward baseline

This directory implements the L3 comparison without importing
`bindcheck_zk` or consuming its verdict logic.

- **Arm A** runs five custom Slither detectors plus a bounded lexical fallback:
  protected effect roles, guard dominance, replay-key binding, exact-position
  scalar canonicality, and generated-verifier count/order.  When a case has a
  policy and harness, it also runs the same-policy Foundry template with an
  always-true mock verifier.  A mock-verifier failure is E1 policy screening,
  never real-proof or E4 evidence.
- **Arm B** retains full native outputs from Circomspect, `circom --inspect`,
  Picus, and ZKAP when installed.  Circuit-only output always keeps the
  integration verdict `UNKNOWN`.
- **Arm C** is A union B plus name, position, commitment-order, array-extent,
  length-signal, mask-disjointness, and nullifier-scope joins.  It does not
  solve R1CS constraints.

Every output uses `bindcheck-redteam.strong-result/v1`. `run.status` and
`run.fatal_reason` are separate from `result.verdict` and findings. Native
stdout/stderr are written in full to adjacent files and referenced by path,
hash, and byte length; they are never truncated.

Run one local case:

```sh
PYTHONPATH=. python3 -m baselines.strong.cli \
  redteam/adversarial/ADV-V01 \
  --output results/raw/redteam/manual-ADV-V01
```

Run a campaign into a fresh ignored namespace, then summarize it:

```sh
PYTHONPATH=. python3 -m baselines.strong.run_campaign \
  --campaign synthetic \
  --output results/raw/redteam/synthetic-<fresh-id>
PYTHONPATH=. python3 -m baselines.strong.summarize \
  results/raw/redteam/synthetic-<fresh-id> --synthetic
```

The DEV runner reconstructs rows only from `feasibility/candidate-set.csv`
and `dataset/source-queries.json:historical_dev`. Repositories named by the L3
data wall are scheduled but never cloned; each arm records
`UNKNOWN / DATA_WALL_BLOCKED`. All other clones are created below the ignored
campaign `work/` directory and removed after their row finishes.

Policy files state authorization roles and permitted transformations. They do
not contain expected verdicts or missing implementation relations. The frozen
AI-authored oracle is `redteam/adversarial/expected.json`; it is development
data and requires human review before paper use.
