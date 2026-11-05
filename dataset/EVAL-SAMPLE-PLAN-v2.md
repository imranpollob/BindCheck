# Preregistered EVAL family sample plan v2

Date frozen: 2026-11-04  
Controlling source-ledger SHA-256: `07210625783a21a6128ea3f99402fc4a48b36922056241649999547a374b0c95`  
Status: inventory-only preregistration; zero EVAL analyzer runs

The eligible population is the 1384 v2 in-scope EVAL-only
families. Families overlapping DEV are excluded. Sampling occurs only after human
review of path/regex eligibility, family membership, and maturity labels.

Strata use the strongest family maturity in this order: `verified-deployed`,
`deployed-address-in-docs`, `audited-production`, `hackathon-student`, and
`unclassified`. Select up to 60 families per stratum, or the whole stratum when
it has fewer than 60. Within a stratum, sort ascending by
`SHA256("bindcheck-eval-v2-family-sample-2026-11-03|" + v2_family_id)` and take
the first quota. This deterministic rule was frozen before any EVAL analysis.

Inventory counts at freeze: `{"audited-production": 207, "deployed-address-in-docs": 303, "hackathon-student": 81, "unclassified": 755, "verified-deployed": 38}`.
No family may move between DEV and EVAL after results are observed. Label or family
corrections made during human review require a new ledger hash and a documented
pre-analysis sample refresh; corrections after analysis are post-hoc and cannot
retain preregistered status.
