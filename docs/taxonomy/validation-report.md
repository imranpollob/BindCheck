# D1P-C04 search-plan v0.2.0 validation report

Freeze validation recorded at `2026-10-27T21:58:34.187992Z`. The pinned local validator exited
`0`; no package installation was used. Network access was limited to
metadata-only `git ls-remote` calls recorded in
[`endpoint-pin-log-v0.2.0.json`](endpoint-pin-log-v0.2.0.json).

## Results

- `search-plan-v0.2.0.json` validates against the ledger schema's
  `search_plan_envelope` and `search_plan` definitions.
- Its canonical `search_plan` payload SHA-256 is
  `4bc618d626e8b02fe1c8da583cebd4a33a64c762448672070609fe2cafc575d2`.
  The file SHA-256 is
  `2bb517717bfe5ff0ab4c56321e938fb5e2472002609401347e244f984639edfa`.
- The protocol hash in the plan and approval freeze assessment matches
  `protocol.md`:
  `fa06ef9abe7aeea1de6133d771856339834be5f1c3b0b6a202afa9b8a67459a9`.
- Endpoint counts are 2 seeds, 13 backbone indexes, and 2 supplemental
  keyword-query endpoints, for 17 total.
- All three numeric parameters are `APPROVED` by the two recorded search-plan
  reviews. The 1,200-minute budget applies to all tiers; the 100-result cap and
  three-consecutive-irrelevant-page stop apply only to supplemental keyword
  endpoints. A synthetic one-review approval was rejected.
- Frozen backbone indexes require complete traversal subject to exact access
  failure and the total budget. Incomplete endpoints record their last
  cursor/page and remaining coverage where known. Relevance uses the broad
  inclusion scope, and stopping never establishes absence.
- `design_frozen=true` at `2026-10-27T21:56:27Z`; the protocol and search-plan
  hashes and both Codex Astra 6 and Claude Opus 5.5 approval records are
  present. `missing_requirements` is empty. Reservation and annotation
  completion remain false and null-timestamped.
- `ledger.schema.json` and all three auxiliary schemas pass JSON Schema draft
  2020-12 meta-schema validation. All three valid fixtures were accepted and
  all three invalid fixtures were rejected for their intended reasons. Four
  date/date-time and four protocol-state/source-endpoint controls passed.
- All 16 archived v0.1.0 artifacts still match the archive manifest.
- Five synthetic candidate-list tests and five synthetic family-reservation
  tests passed. No candidate list, reservation draw, screen, or label was
  produced.

Machine-readable freeze evidence is in
[`validation-results-freeze.json`](validation-results-freeze.json), SHA-256
`d0c8761efe325b1750482937314da9a58eddc6893014968f6725fa2e17bdc4f6`.
The earlier [`validation-results.json`](validation-results.json) remains as the
pre-approval draft validation record.
The ledger schema SHA-256 is
`42d62abc8d03b336e057af87680e35074a565f5828fcd4940dbba96d7fdac493`;
the validator SHA-256 is
`d8a34347c5c925dfaa5e22dea8d08af44e15099cd0ca51d5bfb3d2e9c605629e`.

## Custodian verification queue

Every `to_verify_by_custodian` item is listed here and in the machine report:

1. `seed-snark-sok-bug-dataset`
2. `backbone-ottersec-audits`
3. `backbone-veridise-audits`
4. `backbone-zksecurity-audits`
5. `backbone-leastauthority-audits`
6. `backbone-cantina-portfolio`
7. `backbone-chainsecurity-audits`
8. `backbone-sherlock-contests`
9. `backbone-cantina-competitions`

The first item has no URL because none was supplied or safely established.
The remaining records preserve known organization/listing URLs but require the
custodian to verify the exact index path and listing format without exposing
finding text to an agent.

## Commands

```sh
PYTHONDONTWRITEBYTECODE=1 docs/taxonomy/.venv-validation/bin/python -B \
  docs/taxonomy/validate_ledger.py --output validation-results-freeze.json
PYTHONDONTWRITEBYTECODE=1 python3 -B \
  scripts/taxonomy/test_candidate_list.py
PYTHONDONTWRITEBYTECODE=1 python3 -B \
  scripts/taxonomy/test_reserve_families.py
```

## Limits

This is a design artifact and structural validation only. D1P-C04 did not
open an index page, finding, report body, bug description, application code,
or family result. It performed no screening, labeling, deduplication, family
grouping, reservation, or empirical annotation. Web endpoint validity and
listing-format safety remain human-custodian checks as marked.
