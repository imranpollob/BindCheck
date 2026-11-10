# E3 — freeze-2 DEV warning cards

**Objective and status:** COMPLETE for the bounded card-writing task. The [review index](../../review/dev-warnings/INDEX.md) gives a human one card per frozen warning cell, except [DEV-F34](../../review/dev-warnings/DEV-F34.md), whose P3/P4 cells share a joint card covering four interacting defects. The [audit output](audit.json) verifies coverage of all [18 cells](../freeze2/dev-ledger.csv) by [17 cards](audit.json). Human labels remain blank. These are AI opinions, not independent annotation, a precision estimate, or new E2–E4 security evidence.

## Frozen input and review protocol

The controlling analyzer content SHA-256 is [`92789fad12050a3058a21cc5c2326e7d41604ad5ade0f09f72a35789437e6c1a`](../../docs/FREEZE-2.md). The [DEV ledger](../freeze2/dev-ledger.csv) SHA-256 is [`6edc51ef213402e1e70578c91e1c2c757e02af01da76b6ff93327495a459275a`](audit.json). The ignored [raw manifest](</Users/imranpollob/Coding/bc/bindcheck-zk/results/raw/coverage/after-20261109T165844Z-58315/manifest.json>) SHA-256 is `17c375f02a382bfe667a72a11669eca55e632d6de1cf1012069dfe7694ab441c` (observed by the `shasum` command below). Each raw result hash, source revision and card hash is in [audit.json](audit.json). [PLAN.md](PLAN.md), committed as `7f9af7c` before the card audit, fixes the inventory and scoring rules.

The cards inspect the pinned, read-only DEV checkouts named in the [ledger](../freeze2/dev-ledger.csv), the source code and documentation at those revisions, the earlier [verifier-kind flags](../groundtruth/warning-verifier-flags.csv), and the existing [case policies](../../findings/zkredential/policy.md) and [RacePass policy](../../findings/racepass/policy.md). The independent paper lane's [STATUS §4(b)](</Users/imranpollob/Coding/bc/bindcheck-zk-paper/paper/zk/STATUS.md>) supplies the compiled-R1CS cross-check for F34. No EVAL checkout, network target, RPC, transaction, maintainer, or newly generated proof was used.

## Summary for human adjudication

Every numeric entry below is recomputable from [audit.json](audit.json) and the [review index](../../review/dev-warnings/INDEX.md). `TRUE` means an AI source/policy opinion under the [fixed rules](PLAN.md), never a confirmed vulnerability count.

| Pattern | Frozen VIOLATION cells | AI TRUE | AI INTENDED-BEHAVIOUR | AI FALSE-ALARM | AI UNDECIDABLE |
| --- | ---: | ---: | ---: | ---: | ---: |
| P1 | [6](../freeze2/dev-ledger.csv) | [2](audit.json) | [1](audit.json) | [0](audit.json) | [3](audit.json) |
| P3 | [6](../freeze2/dev-ledger.csv) | [2](audit.json) | [0](audit.json) | [2](audit.json) | [2](audit.json) |
| P4 | [6](../freeze2/dev-ledger.csv) | [3](audit.json) | [0](audit.json) | [3](audit.json) | [0](audit.json) |
| **All** | [18](audit.json) | [7](audit.json) | [1](audit.json) | [5](audit.json) | [5](audit.json) |

The high-impact adjudication pivots are concrete:

- [F08/P4](../../review/dev-warnings/DEV-F08-P4.md): equal-key paylah verifier files were matched to Namecheap and Garanti consumers importing different verifiers. [F09/P4](../../review/dev-warnings/DEV-F09-P4.md): equal-key alternatives are used by a test, while the repository deployment script selects a distinct-key verifier. Both are source-key observations, but these exact consumer/key pairs should not be counted as application findings.
- [F10/P4](../../review/dev-warnings/DEV-F10-P4.md), [F14/P4](../../review/dev-warnings/DEV-F14-P4.md), and [F34](../../review/dev-warnings/DEV-F34.md) have real pairing verifiers at the identified consumer path. The F10 Makefile and F14 Makefile export keys directly after `groth16 setup`; F34's README does likewise. F14 also documents a contributed ceremony elsewhere, which conflicts with its Makefile.
- [F38/P3](../../review/dev-warnings/DEV-F38-P3.md) matched fail-closed local verifier files. [F48/P3](../../review/dev-warnings/DEV-F48-P3.md) and [F48/P4](../../review/dev-warnings/DEV-F48-P4.md) matched a used stand-in that returns true without pairing; the field-alias and gamma/delta explanations do not describe its actual acceptance rule.
- [F49/P1](../../review/dev-warnings/DEV-F49-P1.md) pays a constructor-fixed miner from caller-supplied `msg.value`, as its own policy states. [F30/P1](../../review/dev-warnings/DEV-F30-P1.md) and [F39/P1](../../review/dev-warnings/DEV-F39-P1.md) have owned-local real-proof observations but need human decisions on quantity, recipient and gifting policy. Their cards ask the exact questions.
- [F34](../../review/dev-warnings/DEV-F34.md) reconciles the paper note: the R1CS has zero public inputs and one `isVoteValid` output, the intended nullifier is not constrained, the consumer treats output position zero as a nullifier, and the source key has gamma = delta. The P3/P4 E1 result is not an E3/E4 replay claim.

## Commands, environment and results

The first command was `git merge zk-integration` in this worktree; it fast-forwarded `b0cdad7` to `9466c4b` with exit status `0`. The review protocol was committed on `zk-validate` before the audit. Read-only inspection used `rg -n` on pinned source files and scripts, plus Python line-numbered excerpts; card citations give the exact source locations. The consistency command was:

```sh
PATH=/opt/homebrew/bin:$PATH /opt/homebrew/bin/python3 reports/validate/audit.py > reports/validate/audit.json
```

It exited `0` after a parser fix. [audit.json](audit.json) confirms each cell's raw analyzer hash and verdict, each pinned checkout's `git rev-parse HEAD`, the index/card match, blank human fields and the AI-label tally. The first attempt exited `1` because `audit.py` split Markdown links on `)(` rather than `](`; it produced no audit data and was fixed before the successful run. `git diff --check` exited `0`. `/opt/homebrew/bin/python3 --version` returned `Python 3.15.0`; `git --version` returned `git version 2.51.0`. The raw manifest hash command was:

```sh
shasum -a 256 /Users/imranpollob/Coding/bc/bindcheck-zk/results/raw/coverage/after-20261109T165844Z-58315/manifest.json
```

No Picus run or temporary checkout was made, so no Picus TMPDIR or process-group cleanup was needed. No toolchain/dependency was installed.

## Assumptions, limits, and authority discrepancy

Source-key equality, a real pairing body, and a source-level consumer call are distinct from matching deployed bytecode, a valid matching proof, and a reachable committed effect. The card opinions use the repository's code/docs as provisional policy, sometimes with conflicting demo/deployment scripts. A human must decide policy and final labels. Cases with mocks, stand-ins or fail-closed verifiers cannot be promoted to real-proof findings. `UNKNOWN`, missing wiring and missing proof evidence were not scored as tool misses or wins.

The [research contract](../../docs/research-contract.md) still describes an initial Noir/ACIR D1 fragment, whereas the [freeze declaration](../../docs/FREEZE-2.md) and this task concern Circom/Groth16. This known scope disagreement is recorded without editing the higher-authority contract. The inherited README also still displays older analyzer hashes; the freeze-2 document controls this evaluation. The user explicitly prohibited editing `README.md` and `docs/project-status.md`, so this lane did not apply AGENTS.md's normal living-checkpoint edit and did not rewrite historical reports.

**Files changed:** [PLAN.md](PLAN.md), [audit.py](audit.py), [audit.json](audit.json), this report, and the [review cards/index](../../review/dev-warnings/INDEX.md). No analyzer, README, project-status or earlier report changed.

**Recommended next bounded task:** have two human authors independently fill every blank field in the [index](../../review/dev-warnings/INDEX.md), resolve the exact F30/F39 policy questions, and reconcile disagreements in a signed adjudication file. Completion criterion: every [frozen cell](../freeze2/dev-ledger.csv) has a final label, reviewer/date, cited source reason, and explicit unresolved status where policy or wiring remains missing; only then compute a DEV warning precision table.
