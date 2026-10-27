# D1P-C04 search-plan rationale

The companion [`search-plan-v0.2.0.json`](search-plan-v0.2.0.json) is a draft
for design freeze, not authorization to search or screen. It fixes source
tiers, snapshot handling, English-language coverage, traversal order,
mechanism-keyword groups, the proof-consuming-system inclusion boundary, and
bounded pagination/stopping rules. `design_frozen`, `reservation_completed`,
and `annotation_round_completed` remain false.

## Endpoint frame

| Tier | Count | Purpose |
| --- | ---: | --- |
| Seed | 2 | SNARK SoK dataset and 0xPARC zk-bug-tracker. |
| Backbone index | 13 | Nine audit-firm/portfolio listings, three contest listings, and GitHub Security Advisories. Cantina has separate portfolio and competition endpoints. |
| Supplemental keyword query | 2 | GitHub Search and general web search; never substitutes for source-index traversal. |

Total: **17 endpoints**. Git-hosted endpoints were queried only with
`git ls-remote --symref <url> HEAD`; no clone, fetch, tree, report, finding, or
bug description was read. The resulting commits are recorded in
[`endpoint-pin-log-v0.2.0.json`](endpoint-pin-log-v0.2.0.json). Web URLs were
not opened. Immediately after design freeze, the human custodian records a
content snapshot and hash for every verified web listing without exposing its
body to an agent.

### Custodian verification queue

These nine records are explicitly `to_verify_by_custodian`:

1. `seed-snark-sok-bug-dataset` — no dataset URL was supplied; custodian must
   identify the public listing and provide a sanitized name-only enumeration.
2. `backbone-ottersec-audits` — verify the report-index path under
   `https://osec.io/`.
3. `backbone-veridise-audits` — verify the report-index path under
   `https://veridise.com/`.
4. `backbone-zksecurity-audits` — verify the report-index path under
   `https://www.zksecurity.xyz/`.
5. `backbone-leastauthority-audits` — verify
   `https://leastauthority.com/blog/audits/`.
6. `backbone-cantina-portfolio` — verify
   `https://cantina.xyz/portfolio`.
7. `backbone-chainsecurity-audits` — verify
   `https://www.chainsecurity.com/audits/`.
8. `backbone-sherlock-contests` — verify
   `https://audits.sherlock.xyz/contests`.
9. `backbone-cantina-competitions` — verify
   `https://cantina.xyz/competitions`.

The metadata-only probes of guessed repositories
`https://github.com/Veridise/Audits.git` and
`https://github.com/zksecurity/audits.git` each returned exit 128,
“Repository not found.” Those guessed repository paths are excluded; no
replacement repository was inferred.

## Proposed numeric choices

Every design-choice number remains `PROPOSED` and records its one-line
justification in JSON:

- **100 results per endpoint:** bounds source dominance while retaining a
  substantial returned-order slice. The cap never truncates findings inside a
  selected audit report used for percentages.
- **1,200 active minutes total:** a bounded 20-hour traversal budget across the
  broad index frame, including logged failures and truncations.
- **3 consecutive irrelevant pages:** a source-local saturation signal that
  does not depend on finding a desired number of positives.

The exact remaining design-freeze step is approval of these three values by
two AI planners. If approved without another change, record their review IDs,
change the three statuses to `APPROVED`, recompute the plan hash, and record an
actual UTC `design_frozen_at`. Any amendment requires rehashing and a review of
the amended payload.

## Canonical hash

`search_plan_sha256` is
`f6bfa5980c071c87cb31d83859a220e0efb2b80a1dbf7f68315cd203a7f0a7b6`.
It is SHA-256 over the UTF-8 JSON serialization of the `search_plan` payload
with keys sorted, no insignificant whitespace, and non-ASCII characters left
as UTF-8. The envelope is excluded to avoid a self-referential hash. The
controlling protocol hash is
`24358dddc1623fd84b0df5df6b76db37a1d0011dda2c83e5daf520f7d3009ed4`.

## Content and exposure boundary

D1P-C04 read only local protocol/schema material and remote Git reference
metadata. It opened no source index page, finding, report body, bug
description, candidate application code, or family result. No candidate
application/project names were extracted, so this task created no new
family-specific exposure event. Listings marked mixed or unknown must be
sanitized or classified by the custodian before agent access.
