# D1P-C04 search-plan rationale

The companion [`search-plan-v0.2.0.json`](search-plan-v0.2.0.json) is frozen
design, not authorization to search or screen. It fixes source
tiers, snapshot handling, English-language coverage, traversal order,
mechanism-keyword groups, the proof-consuming-system inclusion boundary, and
bounded pagination/stopping rules. `design_frozen` is true; reservation and
annotation completion remain false.

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

## Approved numeric choices and traversal amendment

Codex Astra 6 and Claude Opus 5.5 approved each value on 2026-10-27:

- **100 results per supplemental keyword endpoint:** bounds supplemental
  queries only. It does not cap backbone traversal or findings inside a selected
  audit report used for percentages.
- **1,200 active minutes total:** a bounded 20-hour traversal budget across the
  broad index frame, including logged failures and truncations.
- **3 consecutive irrelevant pages per supplemental keyword endpoint:**
  irrelevant means outside the broad inclusion scope, never failure to support
  the taxonomy or a preferred mechanism.

Every frozen backbone index is traversed completely, subject to exact access
failure and the total budget. Every incomplete endpoint records its last
cursor/page and remaining coverage where known. A cap or stopping rule never
establishes absence of findings. The two approval records and amendment are in
[`planner-approval-v0.2.0.json`](planner-approval-v0.2.0.json).

## Canonical hash

`search_plan_sha256` is
`4bc618d626e8b02fe1c8da583cebd4a33a64c762448672070609fe2cafc575d2`.
It is SHA-256 over the UTF-8 JSON serialization of the `search_plan` payload
with keys sorted, no insignificant whitespace, and non-ASCII characters left
as UTF-8. The envelope is excluded to avoid a self-referential hash. The
controlling protocol hash is
`fa06ef9abe7aeea1de6133d771856339834be5f1c3b0b6a202afa9b8a67459a9`.

## Content and exposure boundary

D1P-C04 read only local protocol/schema material and remote Git reference
metadata. It opened no source index page, finding, report body, bug
description, candidate application code, or family result. No candidate
application/project names were extracted, so this task created no new
family-specific exposure event. Listings marked mixed or unknown must be
sanitized or classified by the custodian before agent access.
