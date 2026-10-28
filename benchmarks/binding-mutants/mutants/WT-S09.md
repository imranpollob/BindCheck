# WT-S09 — nullifier write dropped, check kept (WarpToad consumer)

- Family: WarpToad consumer. Operator: drop state write (vs S03, which
  drops check and write).
- Change: `nullifiers[_nullifier] = true;` removed; the pre-check stays.
- Ground truth: single-use enforcement has no effect — the check reads a
  mapping that is never written. Expected effect: identical successful
  replay mints again (same as S03 observably; different mechanism, so a
  localization-sensitive tool should distinguish them).
- Reachability (cheap): solc compile + diff audit.
