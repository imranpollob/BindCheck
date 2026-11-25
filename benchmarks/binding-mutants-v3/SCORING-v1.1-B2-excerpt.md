# Copied by the orchestrator from mvp/eval/SCORING-v1.1.md (sections Changes + B2), 2026-11-25. Contains no results.
## Changes
1. **Matcher fix (location).** Function names are compared case-insensitively after stripping `Contract.` / `Contract::` qualifiers and any parameter list; the file basename is also compared case-insensitively. (The v1.0 matcher already stripped qualifiers but was case-sensitive.) Implemented as `loc_match11` in `common.py`. GT files are unchanged, still committed before round 1.
2. **Mechanism-level metric (separate, labelled).** A positive counts as a mechanism-level hit if some warning (a) names a file that exists in the scanned snapshot (same repo) and (b) the judge says its unbound value/mechanism is the same as the GT `unbound_value`, whichever side of the binding the warning's file is on and regardless of function. For dev, snapshots are not materialised, so (a) holds by construction. For the fixed targets the same test gives mechanism-level specificity. Hard negatives have no GT mechanism, so they stay location-only.

## What did not change
- GT locations (`GT-locations.csv`, `GT-locations-dev.csv`), slices, Wilson intervals, strict/loose definitions.
- The mechanism-level metric is more lenient than strict: it can credit a correct mechanism reported in a different file than the GT consumer, so it should not be read as a drop-in replacement for strict.

## Judge workload
`judge.py` now also judges, for positive items, every warning whose file is in the snapshot (previously only location-matched warnings). Verdicts are cached in `judged/<arm>/`.

## B2 mutant benchmark (added 2026-11-24, before any B2 result was scored)
Applies to the tool-v2 arm on `BindCheck/benchmarks/binding-mutants-v2` (27 mutants, vuln trees only, build output stripped; clean hosts not scanned). Implemented in `b2.py`.
- GT from `mutants/<ID>.md`: consumer file and first function token; unbound value + "binding broken" text; expected effect.
- Location (loose): warning file basename + function equal GT (case-insensitive, qualifier-stripped). RP-S04/S05 also accept `Verifier.sol::verify` or `RedPacket.sol::open` (as in MATCHING.md). Circuit mutants (-C) additionally accept any function in the edited circuit file (the consumer is unchanged by construction).
- Strict = loose + frozen judge (`prompts/judge.txt`) says same mechanism. Mechanism-level = any warning whose file exists in the tree is judged same mechanism.
- The static-tool rule in `MATCHING.md` (delta against clean host, detector lists) is not used for the LLM arm; no clean-host scans, so no B2 false-alarm rate is reported.
- Each scan runs once; only NOT ANALYZED scans (no output file, exit 3) were rerun.
