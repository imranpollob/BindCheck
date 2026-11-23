# Human labeling package: audit-sweep candidates

## What is here

| File | For | Content |
|---|---|---|
| `GUIDE.md` | Both raters | Definitions, patterns, exclusions, what to fill in, hard cases |
| `sheet-rater-A.csv` | Rater A (author) | All 264 items (FULL 51, LIGHT 152, PSS 61), blind |
| `sheet-rater-B.csv` | Rater B (independent) | 81 items: a seeded 30% stratified overlap, blind, independently shuffled |
| `key/` | **Nobody until both sheets are sealed** | `KEY.csv` maps `item_id` to the candidate and the AI labels; `MANIFEST.md` holds counts, seeds and input hashes |
| `build_sheets.py` | Orchestrator | Regenerates the sheets deterministically from `merged/` |

**Blindness.** The sheets omit the AI decision, the AI pattern, the triage outcome, the inclusion reason, and the AI-written mechanism summary. Only source material is shown: auditor, report, finding ID and title, severity, a verbatim auditor quote, and repo/commits for FULL items.

**Rater requirements.**

- **Rater B** must know ZK and smart contracts, must not be an author, and must not use AI tools.
- **Rater A** is the author; any paper must disclose this.

## Procedure

1. Read `GUIDE.md`.
2. Each rater copies their sheet to a working copy: `sheet-rater-A.work.csv` or `sheet-rater-B.work.csv`. Fill it in with any spreadsheet tool. Do not change `item_id` or any source column.
3. Work through the rows in order. FULL items come first, and they matter most: they become the study/reserved benchmark.
4. **Seal before analysis.** When a sheet is complete, and before anyone looks at agreement, the key, or the other sheet:

   ```sh
   cd dataset/audit-sweep/labeling
   mkdir -p sealed && cp sheet-rater-A.work.csv sealed/LABELS-rater-A.csv
   sha256sum sealed/LABELS-rater-A.csv >> sealed/SEAL.md
   git add sealed && git commit -m "Seal rater A labels"
   ```

   Do the same for rater B. Sealed files are never edited. Corrections after sealing go in a separate `RESOLUTION.csv` with reasons, as in the earlier labeling round (`review/labels/`).
5. Only after both seals: the orchestrator runs the analysis. That covers agreement (κ on `binding`, `pattern` and `proof_system_soundness` for the 81 overlap items), the triage miss rate on the `LIKELY-NOT` validation items, and AI-vs-human accuracy. Disagreements are then resolved jointly into `RESOLUTION.csv`.

## After labeling

- Freeze the labeled candidate set (hash and tag it).
- Apply the author's scope decision on proof-system soundness.
- Exclude held-out families (`holdout_flag = FORBIDDEN`, e.g. Tornado) unless the author moves them out of the held-out pool.
- Split the **FULL** items labeled binding into a **study set** and a **reserved set** before anyone reads their code. Use a seeded split, stratified by pattern.
- Reproduce the study set at E4 (real proof, unmodified verifier and consumer, real unauthorized effect).
