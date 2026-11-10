# Passive verifier census, controlling pass

**Objective/status.** Complete a static, read-only classification of the Solidity verifier paths in the whole [source corpus](../../dataset/source-corpus-v2.csv), with the pinned DEV source supplement described in [CENSUS-CORRECTION.md](CENSUS-CORRECTION.md). The controlling output is [pass v5](../../results/raw/heldout/verifier-census-v5/summary.json); its exact [summary](verifier-census-summary.json) and [per-verifier ledger](per-verifier.csv) are tracked here. This is a source-template screen, not an analyzer, proof acceptance, or exploit result. No EVAL analyzer or arm C process was run to produce it.

The source ledger has [5,024 rows](verifier-census-summary.json). The collector processed [11,250 path entries](verifier-census-summary.json), including [316 DEV supplemental entries](verifier-census-summary.json), representing [11,139 distinct source references](verifier-census-summary.json). A path with multiple recognized verifier functions yields multiple ledger rows. The [12,264 ledger rows](verifier-census-summary.json) include [8,410 classified verifier functions](verifier-census-summary.json). Source or parse failures stay outside those classified-function denominators.

| Source/parse status, path or function rows | DEV | EVAL | Total |
| --- | ---: | ---: | ---: |
| Classified function (`FETCHED`) | [283](per-verifier.csv) | [8,127](per-verifier.csv) | [8,410](verifier-census-summary.json) |
| Source fetched, no recognized verifier function | [54](per-verifier.csv) | [3,742](per-verifier.csv) | [3,796](verifier-census-summary.json) |
| Pinned DEV `git show` failed | [51](per-verifier.csv) | [0](per-verifier.csv) | [51](verifier-census-summary.json) |
| Raw source HTTP 404 | [0](per-verifier.csv) | [7](per-verifier.csv) | [7](verifier-census-summary.json) |

The classified-function denominators are **[283 DEV](verifier-census-summary.json)** and **[8,127 EVAL](verifier-census-summary.json)**. Counts below are function-row counts from the [controlling summary](verifier-census-summary.json), with the row's source URL, pinned commit, source SHA-256, function line, guard positions, and extraction snippets in the [ledger](per-verifier.csv).

| Generator or template marker | DEV | EVAL |
| --- | ---: | ---: |
| snarkjs current style | [82](verifier-census-summary.json) | [2,570](verifier-census-summary.json) |
| snarkjs legacy style | [3](verifier-census-summary.json) | [25](verifier-census-summary.json) |
| gnark marker | [1](verifier-census-summary.json) | [235](verifier-census-summary.json) |
| Other or unrecognized | [197](verifier-census-summary.json) | [5,297](verifier-census-summary.json) |

“Current” and “legacy” are template-style labels, **not exact snarkjs versions**. `OTHER` does not prove another generator. The classifier uses explicit source markers; a comment promising future snarkjs generation is not a generated template.

| Recognized public-input range shape | DEV | EVAL |
| --- | ---: | ---: |
| Scalar field `r`, all recovered positions | [38](verifier-census-summary.json) | [1,931](verifier-census-summary.json) |
| Scalar field `r`, partial positions | [0](verifier-census-summary.json) | [1](verifier-census-summary.json) |
| Base field `q`, all recovered positions | [44](verifier-census-summary.json) | [346](verifier-census-summary.json) |
| Base field `q`, partial positions | [0](verifier-census-summary.json) | [0](verifier-census-summary.json) |
| No recognized guard | [90](verifier-census-summary.json) | [1,967](verifier-census-summary.json) |
| Unknown guard or arity | [111](verifier-census-summary.json) | [3,882](verifier-census-summary.json) |

`NONE` means no guard in the classifier's supported syntax; it does not prove a guard is absent. `Q_ALL` is a base-field bound and must not be credited as an `r` canonicality guard. Partial positions are recorded individually in the [ledger](per-verifier.csv). Unknown arity, unrecognized helper checks, and unsupported shapes remain `UNKNOWN`.

| Source behavior shape | DEV | EVAL |
| --- | ---: | ---: |
| Unconditional `return true` | [17](verifier-census-summary.json) | [254](verifier-census-summary.json) |
| Dummy key constants | [2](verifier-census-summary.json) | [0](verifier-census-summary.json) |
| Simplified or stand-in marker | [18](verifier-census-summary.json) | [299](verifier-census-summary.json) |
| Unconditional false or reverting stub | [4](verifier-census-summary.json) | [54](verifier-census-summary.json) |
| Recognized pairing-verifier shape | [101](verifier-census-summary.json) | [4,272](verifier-census-summary.json) |
| Unresolved behavior | [141](verifier-census-summary.json) | [3,248](verifier-census-summary.json) |

These shapes are not independent vulnerability labels. In particular, a `Mock` name without a recognized unconditional or explicit simplified body can remain `UNKNOWN`; a pairing-shaped function has not been validated against a real proof. The census does not infer deployability, consumer reachability, or ecosystem prevalence.

## Source-level cross-checks

| Known DEV row | Ledger evidence | Observed source shape |
| --- | --- | --- |
| DEV-F34, `avitenzer/zk_voting` | [Pinned `contracts/Verifier.sol:59`, SHA `464722e3…`](per-verifier.csv) | snarkjs current style; `Q_ALL`, not scalar `r` |
| DEV-F36, `partik03/aieth` | [Pinned supplemented `hardhat/contracts/Verifier.sol:14`, SHA `cb3871bf…`](per-verifier.csv) | `OTHER`, `NONE`, dummy constants; the recorded `DIDVerifier.sol` has no recognized verifier function |
| DEV-F38, `KanishJebaMathewM/Truxify` | [Pinned `AggregatedVerifier.sol:22`, SHA `77312923…`](per-verifier.csv) | named `verifyAggregatedProof` is a rejecting stub |
| DEV-F49, `KELLERBABG/Planetary-Entropy-Mining` | [Pinned supplemented `contracts/src/Verifier.sol:20`, SHA `07fcd37e…`](per-verifier.csv) | `OTHER`, `NONE`, explicit stand-in/simplified behavior; DEV pinned Git source recovered despite an earlier raw HTTP 404 |

## Reproduction and limits

The exact controlling command, run from this worktree, was:

```sh
PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3 eval/run_verifier_census.py --output results/raw/heldout/verifier-census-v5 --reuse-source-cache results/raw/heldout/verifier-census-v3/sources --workers 24 > results/raw/heldout/verifier-census-v5-run.log 2>&1
```

It exited [0](../../results/raw/heldout/verifier-census-v5/command-record.json). Python was [`3.15.0`](../../results/raw/heldout/verifier-census-v5/command-record.json); Git was [`2.51.0`](../../results/raw/heldout/verifier-census-v5/command-record.json). The source corpus SHA-256 is [`07210625783a…`](verifier-census-summary.json); the controlling ledger SHA-256 is [`336c41171038…`](verifier-census-summary.json). The classifier and collector are [verifier_census.py](../../eval/verifier_census.py) (SHA-256 `ddd1e25bda6f…`) and [run_verifier_census.py](../../eval/run_verifier_census.py) (SHA-256 `fd00224aed65…`). The synthetic labels were committed before corpus classification in [test_verifier_census.py](../../tests/test_verifier_census.py). The source-fetch cache is retained under ignored [v5 raw evidence](../../results/raw/heldout/verifier-census-v5/); source bytes were capped at [8 MiB](verifier-census-summary.json) per path. Older census passes remain raw but are not pooled, as [documented](CENSUS-CORRECTION.md).

**Unexpected observations and next task.** The preserved DEV verifier inventory omitted a pinned base verifier and a DEV raw source URL failed despite a valid pinned local blob; both caused documented protocol corrections. Some source behavior stays unknown by design. Next, finish the preregistered build-only pass and report its complete family-level statuses and failure causes, with every temporary checkout removed. This has a measurable completion criterion: one recorded status for every [selected family](selected-families.csv), including the exposed exclusion, and zero remaining prebuild checkouts.
