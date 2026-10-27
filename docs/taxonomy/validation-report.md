# D1P-C03 taxonomy v0.2.0 validation report

Recorded at `2026-10-27T07:53:03.305144Z`. The pinned local validator exited
`0`; no network access or package installation was used.

## Results

- `ledger.schema.json` selects JSON Schema draft 2020-12 and passes the
  standard meta-schema check. Schema version: `0.2.0`; SHA-256:
  `012ee5f97880418d7579886ae525d30a48aeb74f1c8f7def0c54a028cdd5d8b4`.
- `planner-approval.schema.json` and `grouped-families.schema.json` also pass
  the draft 2020-12 meta-schema check.
- All three valid illustrative fixtures were accepted and all three invalid
  fixtures were rejected for their intended reason. Four date/date-time
  format controls passed.
- Four focused controls passed: incomplete design freeze, reservation
  completion, and annotation completion states were rejected; a source-index
  endpoint without an application ID was accepted.
- The pending planner-approval record is structurally valid. Changing it to
  `complete` without two named AI-planner reviewer records is rejected.
- All 16 archived v0.1.0 artifacts match the byte counts and SHA-256 values in
  the archive manifest and the versions introduced by commit
  `785ff402793d0b2cf5f28de2735a97a338e1ad4d`.
- `scripts/taxonomy/test_reserve_families.py` passed five synthetic unit tests:
  deterministic stratified selection with a fixed test seed, exact commitment
  construction, eligibility-aware strata, rejection of an all-unsupported
  pool, and rejection of worktree output.
  The reservation CLI was not run and no draw or selection was produced.

Machine-readable evidence is in
[`validation-results.json`](validation-results.json). Its SHA-256 is
`6d31da79ddad8427665653e9954cc671b194efc79c0e468dd1449484a446c71e`.
The validator SHA-256 is
`431566daa49c4edcb2d472f4d886597ef363a4baa56b8ccb3d38f9b73b82159f`.
The reservation script SHA-256 is
`4a3120ce148970251bf690b99b38ad53b6fb9ed98ccba2fff17188950439a0a4`.

## Commands

```sh
PYTHONDONTWRITEBYTECODE=1 docs/taxonomy/.venv-validation/bin/python -B \
  docs/taxonomy/validate_ledger.py --output validation-results.json
PYTHONDONTWRITEBYTECODE=1 python3 -B \
  scripts/taxonomy/test_reserve_families.py
```

The pinned validation environment uses Python `3.13.7`, `jsonschema 4.26.0`,
`jsonschema-specifications 2025.9.1`, `referencing 0.37.0`, and
`rpds-py 0.30.0`; the unchanged pins remain in
`validation-requirements.txt`.

## Limits and pending empirical gates

These checks establish syntax and synthetic structural behavior only. They do
not establish source coverage, evidence correctness, family independence,
screening or labels, a random/timely reservation draw, human staffing,
annotation reliability, or a BindCheck result.

The task handoff reports approval by two planners but provides no planner
names or dated reviewer records. The typed approval record therefore remains
`pending_reviewer_identity`, and `design_frozen` remains false. The reservation
and annotation states also remain false; no human signature or attestation was
fabricated.
