# D1P-C03 reservation helper

`reserve_families.py` is for the human reservation custodian only. Run it in a
plain terminal outside every agent session, after the name-only grouped list,
strata, rounding rule, and tool-transfer eligibility are frozen. If a source
index displays bug descriptions beside application names, do not give that
index to an agent; prepare a sanitized name-only list manually.

Validate the input against
`docs/taxonomy/grouped-families.schema.json`. Each `stratum_id` must end with
`:eligible`, `:ineligible`, or `:unknown` matching the group's separately
recorded `tool_transfer_eligibility`. The script reserves half of each stratum
using the input's predeclared ceiling/floor rule.

Example invocation (replace both paths; the output must be outside every Git
worktree and must not already exist):

```sh
python3 scripts/taxonomy/reserve_families.py \
  /absolute/path/to/grouped-name-only-list.json \
  --output /absolute/external/private/reservation-opening.json
```

On success, standard output is exactly one 64-hex SHA-256 commitment. Store
only that digest and the custodian attestation in the repository. Do not copy
the output path, nonce, private seed, manifest, counts, or reserved group IDs
into any worktree or agent session. The external file is created mode `0600`
and is never overwritten.

The commitment is
`SHA256(nonce_bytes || canonical_selection_manifest_bytes)`. Canonical JSON is
UTF-8 with sorted keys, no insignificant whitespace, and no ASCII escaping.
The commitment can later be checked against an opening; it does not prove
randomness or timing.

Synthetic unit tests do not run the CLI or persist a draw:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B \
  scripts/taxonomy/test_reserve_families.py
```
