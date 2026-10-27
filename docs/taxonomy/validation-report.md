# D1P-C04 search-plan v0.2.0 validation report

Recorded at `2026-10-27T19:15:38.164202Z`. The pinned local validator exited
`0`; no package installation was used. Network access was limited to
metadata-only `git ls-remote` calls recorded in
[`endpoint-pin-log-v0.2.0.json`](endpoint-pin-log-v0.2.0.json).

## Results

- `search-plan-v0.2.0.json` validates against the ledger schema's
  `search_plan_envelope` and `search_plan` definitions.
- Its canonical `search_plan` payload SHA-256 is
  `f6bfa5980c071c87cb31d83859a220e0efb2b80a1dbf7f68315cd203a7f0a7b6`.
  The file SHA-256 is
  `815b0b62aeaf188122b1f84f4ce602f814b11ee2873790bae7a340b2d6bffcad`.
- The protocol hash in the plan and approval freeze assessment matches
  `protocol.md`:
  `24358dddc1623fd84b0df5df6b76db37a1d0011dda2c83e5daf520f7d3009ed4`.
- Endpoint counts are 2 seeds, 13 backbone indexes, and 2 supplemental
  keyword-query endpoints, for 17 total.
- All three numeric parameters are `PROPOSED`; therefore `design_frozen=false`
  and `design_frozen_at=null`. Reservation and annotation completion remain
  false. A synthetic attempt to mark a number approved with only one planner
  review ID was rejected.
- The complete Codex Astra 6 and Claude Opus 5.5 design-approval records remain
  valid. The exact outstanding gate is their approval of the proposed values
  100 results per endpoint, 1,200 active minutes total, and 3 consecutive
  irrelevant pages.
- `ledger.schema.json` and all three auxiliary schemas pass JSON Schema draft
  2020-12 meta-schema validation. All three valid fixtures were accepted and
  all three invalid fixtures were rejected for their intended reasons. Four
  date/date-time and four protocol-state/source-endpoint controls passed.
- All 16 archived v0.1.0 artifacts still match the archive manifest.
- Five synthetic candidate-list tests and five synthetic family-reservation
  tests passed. No candidate list, reservation draw, screen, or label was
  produced.

Machine-readable evidence is in
[`validation-results.json`](validation-results.json), SHA-256
`0f4aceb8f75e5a0683f02db9d3bbf9d95e5a112575177264b8ae5bb2b068318a`.
The ledger schema SHA-256 is
`5470bd88d50c2d1b31126008fb3e639b5aaf846f9f5ecfc283369ce2e1d33f6f`;
the validator SHA-256 is
`9a4d85717da86497dc3744725371dc1904405cae22c010f2c2194b5474e3c7f2`.

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
  docs/taxonomy/validate_ledger.py --output validation-results.json
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
