# PP — Reproducible paper tables, figures and artifact README

Status: DONE  
Verdict/outcome: PP DONE

AI disclosure: OpenAI Codex (GPT-6 family) implemented and checked the
pipeline, transcribed the report-only results through parsers, and drafted
the documentation. The exact model variant was unavailable. This task adds
no independent annotation or new research verdict.

## What was done

- Added `make paper-tables`, the stdlib generator at
  [scripts/paper/build.py](../../scripts/paper/build.py), and the read-only
  freshness check at [scripts/paper/check.py](../../scripts/paper/check.py).
- Generated ten booktabs fragments and their JSON companions, plus
  [numbers.tex](../../paper/generated/numbers.tex) and
  [numbers.json](../../paper/generated/numbers.json). Every table records
  source paths, SHA-256 digests and parser types. Numeric prose macros
  include a source and definition comment.
- Inventoried the required evidence in [INVENTORY.md](INVENTORY.md) and
  reconciled differences in [DISCREPANCIES.md](DISCREPANCIES.md). Added the
  sprint reviewer workflow to [ARTIFACT.md](../../ARTIFACT.md), retaining
  its historical body byte-for-byte.
- Left the work on `sprint/PP`. The base and index are unchanged. PP is a
  packaging task with no change in research state, so the lane's file
  ownership and the checkpoint rule require no new project-status entry.

## Evidence (paths, hashes, commands, exit codes, tool versions)

Base revision `c82eac653fd53daf71dc0eb013849f3be42dd1ba`.
Python 3.12.12, GNU Make 4.3, Git 2.43.0. Analyzer controls used the installed
Linux Circom 2.1.9 pin with binary SHA-256
`1bacd5583e2cc79dc1e2deaefc9c7438f21957968651c5f93dc71073c58435e3`
and the existing npm dependencies. The locally recomputed candidate hash,
`8ef7a837f4127bfa57fa44419a39b37eee06b90929ed074e5009bc714c346be3`,
matches the tracked S2a identity. The freeze-2 identity is
`92789fad12050a3058a21cc5c2326e7d41604ad5ade0f09f72a35789437e6c1a`.

Raw command and timing logs are in ignored
`results/raw/PP/verify-CstI9Y/`. Exact per-input hashes are in the inventory
and the generated JSON.

| Command | Observed result |
|---|---|
| `make paper-tables`, twice on a temporary source-only export | Both exit 0. The export used `git archive HEAD` for the 15 tracked build inputs plus a copy of the PP implementation. All 22 files were byte-identical across both builds and matched the working tree. Each build took about 0.08 s. |
| `python3 -B scripts/paper/check.py` | Exit 0, all 22 artifacts current. Negative controls exited 1 for a source-byte change with no numeric change, a modified TeX file, an extra file, a missing input, and appearance or disappearance of the optional S1 source. |
| `python3 -B results/raw/PP/verify-CstI9Y/validate_pipeline.py` | Final exit 0. Tested both S1 paths, TeX escaping of a CSV cell, and failure before writes on missing input. Reconciled R1 and R2 helper results, original freeze-2 DEV, both spent-family scopes, Set H and generated-source digests. See `pipeline-final.log`. |
| `BINDCHECK_CIRCOM=/home/pollmix/Coding/bc/BindCheck/tools/circom-2.1.9/target/release/circom PYTHONDONTWRITEBYTECODE=1 npm_config_offline=true python3 -m unittest -v tests.test_bindcheck_zk_cli tests.test_bindcheck_zk_controls tests.soundness.test_verdict_soundness tests.soundness.test_followup tests.coverage.test_rules tests.freeze2.test_p4_key tests.s2a.test_precision_fixes` | Exit 0. 58 passed, 4.749 s unittest time and 5.07 s process wall. See `analyzer-tests.log`. |
| `python3 -m bindcheck_zk.freeze` | Exit 0, S2a revision 1 candidate content hash above. |
| `git diff --check` and `git diff --cached --exit-code` | Both exit 0. Scope and whitespace of new files were checked separately. |

## Results (tables; exact counts)

| Output | Result |
|---|---|
| Source inventory | 53 tracked files, 15 used directly by the generated outputs. |
| T-incidents | 50 cases. P1–P5 counts are 0, 0, 7, 4 and 4, plus 35 other. Aztec Connect's project-confirmed loss is USD 2,100,000. Totals preserve unknown amounts separately. |
| T-audits | 68 audits, 54 included findings, 34 binding findings, and 17 high/critical binding findings in seven audits. The circuit-needed share is 13/34 for binding findings and 24/54 overall. |
| T-aztec-tools and T-aztec-testbed | Seven report rows per table. The recorded synthetic run has 53 checks and zero failures. The real bindcheck-zk case carries UNKNOWN on every pattern. |
| T-freeze-dev | 56 original DEV rows, 159 applicable cells, 45 decided. |
| T-spent-patterns | 278 selected, one excluded, 277 attempted, 265 analyzed in both runs, seven candidate timeouts and five candidate acquisition failures. |
| T-dev-precision | 55 compared Set H cards, four unavailable for the S2a candidate. Freeze-2 → candidate retained-warning precision is P1 9/15 → 9/10, P3 9/15 → 9/12, P4 canonicality 7/10 → 5/5 on available cards, and P5 2/15 → 2/8. |
| T-oracle and T-oracle-runtimes | Nine case/variant rows, five E4-confirmed operator cells across S4 and S4c. Eleven reported full-run wall times across S4, S4b and S4c. |
| T-generators and prose macros | Explicit S1 TODO because the tracked CSV is absent. 53 generated macros with source bindings. |

## Assumptions and limitations

- Spent evaluation data are DEV for the S2a comparison. This includes the
  earlier freeze-2 and Set H observations, whose historical reports describe
  the original evaluation. The README's earlier “EVAL remains unopened”
  statements precede the once-run evidence tracked in the held-out report.
- R1 and R2 use their tracked class labels and carry the original label and
  sample limitations. The pipeline preserves reported USD categories and
  keeps R2's Solodit and report-time funding limitations explicit.
- AZ1 and S4 use report Markdown where a CSV is absent. The pipeline
  reproduces the reported numbers and does not repeat their executions.
  Linux toolchain installation also stayed outside this offline task.
- A LaTeX engine was unavailable, so verified output is at the fragment and
  byte level. The manuscript lies outside PP's owned files. Public packaging
  and real-case dissemination still require author review.
- The private on-chain census is outside the inputs. Its addresses are
  absent from the generated outputs and the report.

## Failed approaches / surprises

- The first reconciliation attempted to match the 277-row full table to
  `spent-family-delta.json` and exited 1. The JSON covers 272 acquisition-ready
  rows. Adding the five failure ledger rows makes every cell agree. The
  first failure and corrected checks are retained in the ignored logs.
- The R2 helper's high/critical count label and two S2a precision descriptions
  require the qualifications in [DISCREPANCIES.md](DISCREPANCIES.md).
- The AZ1 runner requires the historical freeze-2 checkout. The artifact
  instructions pin the reported revision because the PP checkout carries
  the later S2a candidate.

## Held-out hygiene statement

Only project-owned tracked files and installed tools were read. Family data
came from existing project ledgers for census intake, the original DEV set,
and the 278 selected spent families. No unused EVAL family repository was
opened, cloned, built or analyzed. No network, live chain queries, external
communication or transaction broadcasts occurred.

## Recommended next task

Integrate the PP fragments and macros in the EuroS&P manuscript. Complete
the task when every PP-scope number cited in the manuscript resolves to a
generated table cell or macro, the manuscript compiles with booktabs, and
the freshness checker passes on the release-approved inputs.
