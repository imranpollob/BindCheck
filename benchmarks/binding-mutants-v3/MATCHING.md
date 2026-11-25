# B3 matching rule (frozen 2026-11-25, before any tool was run on any B3 tree)

**TEST benchmark. Never share B3, its mutant list, this file's KB section or any result with a tool-building lane.**

Scope: every tool arm on `benchmarks/binding-mutants-v3`: 37 mutants (`mutants/<ID>.md`), 5 decoys (`decoys/<ID>.md`) and 5 clean hosts (`CLEAN-<host>`, the unmutated baselines). Any amendment is appended at the bottom with its date and is never applied to results already seen.

## 1. Source rules, used verbatim
- `SCORING-v1.1-B2-excerpt.md` (copied by the orchestrator from `mvp/eval/SCORING-v1.1.md`, sections Changes and B2) is used **verbatim** for the LLM/BindCheck arm. That means the matcher fix (case-insensitive basename, qualifier-stripped and parameter-stripped function), the strict / loose / mechanism-level definitions, and the frozen judge `prompts/judge.txt`. In it, read `binding-mutants-v2` as `binding-mutants-v3`.
- `../binding-mutants-v2/MATCHING.md` (B2 static rule) is used for the static tools: capability gate, delta rule, detector mechanism lists and tool settings. The B3 changes are listed in §4.
- Provenance gap: `mvp/eval/SCORING-v1.1.md` itself was not read (wall). Only the excerpt was used.

## 2. Ground truth per mutant
From `mutants/<ID>.md`, generated from `make_mutants.py`: the GT consumer file and GT function where the unbound value enters the effect, the unbound value, the broken binding, the attacker effect, and the edited file(s) with exact edit lines.

The location for loose matching is the GT file plus the GT function, with these additional accepted locations:

| Mutant(s) | Also accepted (file::function) |
|---|---|
| ZK-S02, ZK-S03 (verifier.sol) | `TransactionKeeper.sol::_checkProof` |
| DK-S01 (withdraw Verifier.sol) | `DarkVault.sol::withdraw` |
| DV-S05 (DealVerifier.sol) | `CouncilManager.sol::deal` |
| XC-S04 (RiscZeroAdapter.sol) | `Connector.sol::_verifyProof` |
| XC-S07 (two sites) | `Connector.sol::_checkRouteImageId`, `Connector.sol::_verifyProof` |
| XC-S05 | `Connector.sol::_submitLockProofImpl` |
| XC-S03 | `Connector.sol::_submitLockProofImpl`, `Connector.sol::submitAckProof` |
| every circuit (`-C`) or guest (`-G`) mutant | any function in an edited circuit/guest file (excerpt rule), or within 3 lines of an edited line (B2 static rule) |

A deletion's location is the function that contained the deleted lines.

## 3. Capability gate (static tools)
| Tool | Supported targets | Unsupported (reported separately, never a miss) |
|---|---|---|
| Slither, Mythril | `-S` mutants (Solidity consumer or vendored verifier) and the Solidity part of clean hosts and decoys `ZK-D01`, `DK-D01`, `XC-D01` | all `-C`, all `-G`, decoys `DV-D01`, `KK-D01` |
| circomspect, Picus | `-C` mutants of zkerc20 and davinci, `DV-D01`, clean zkerc20 and davinci circuits | everything else |
| `nargo check` (beta.22) | `-C` mutants of dark and kakushi, `KK-D01`, clean dark and kakushi circuits | everything else |
| (none) | — | `XC-G01`, `XC-G02`: no static tool here analyses a RISC Zero guest. They are unsupported for every static tool. |

Analysis targets per host:

| Host | Slither / Mythril target |
|---|---|
| zkerc20 | `contracts/Node.sol` (imports ZKERC20, TransactionKeeper, verifier) |
| dark | `contracts/src/DarkVault.sol`; for DK-S01 also `circuits/verifiers/withdraw/Verifier.sol` |
| davinci | `solidity/src/CouncilManager.sol` (imports the verifiers through interfaces). DV-S05 is analysed on `solidity/src/verifiers/DealVerifier.sol`. |
| xchain | `smart-contracts/src/connectors/Connector.sol` and `smart-contracts/src/zk-proof/adapters/RiscZeroAdapter.sol` |
| kakushi | `packages/contracts/src/privacy/KakushiPool.sol` |

Each target is analysed identically on the mutant tree and on `CLEAN-<host>`.

Build failure, crash, out-of-memory or no output file is **unsupported** (log kept). A timeout with no finding is **UNKNOWN**. Neither is a miss and neither is safe.

## 4. Levels for static tools (B2 rule plus the v1.1 mechanism level)
- **New warning (delta rule, unchanged from B2):** a warning is new when no warning with the same tool, detector id, file basename and function (Solidity) or line region ±3 (circuits) exists on the clean host. Only new warnings can match.
- **Loose:** at least one new warning at a §2 location.
- **Strict:** loose, and the warning's detector is on the B2 mechanism list for the mutant's pattern. The table is copied unchanged from B2 `MATCHING.md` and is not widened after output is seen. `nargo check` has no list, so it is loose only.
- **Mechanism-level (v1.1 change 2, static form):** some *new* warning anywhere in the tree whose detector is on the mechanism list for the mutant's pattern. Static tools have no judge, so the pre-registered detector list replaces "the judge says same mechanism". This is the documented gap: the static form is a proxy, more lenient than strict, and is not comparable one-to-one with the LLM arm's mechanism level.

## 5. Clean controls and decoys (B3 addition, orchestrator rule 2026-11-25)
- **False alarm** means any *binding warning* on a clean host or a decoy tree, wherever it is located. A binding warning is:
  - for the LLM/BindCheck arm, any emitted warning, since the arm emits binding warnings only;
  - for the static tools, any warning whose detector is on the mechanism list of any pattern (P1–P5);
  - on decoys, only warnings that are *new* relative to the clean host count (delta rule); on clean hosts, the absolute count is reported.
- Reported: false alarms per clean host and per decoy, the decoy false-alarm rate (decoys with ≥1 false alarm / 5, Wilson 95%), and the clean-host false-alarm count per tool.
- Decoys are not positives and are never counted toward recall.

## 6. Known baseline issues (pre-registered, mechanism level)
These were found by a source read-through of the clean hosts before any tool run. They are unverified: no proof was built. A warning *matches a KB* when it is on that host's tree and states the KB mechanism below (the judge decides for the LLM arm, the human triager for static tools). A KB-matching warning is reported in a separate KB column. It is **neither a false alarm nor a match** for any mutant. Every mutant's GT mechanism is disjoint from both KBs.

| KB | Host | Mechanism |
|---|---|---|
| KB-1 | xchain | The remote chain state that the guests read (block header and storage/log proofs) is not anchored to a block hash the consumer verifies on-chain. The journal carries no such commitment and no contract validates one. This includes that the emitting/queried contract address is a private guest input that is not committed. |
| KB-2 | zkerc20 | The commitment tree can be extended without a proof or a deposit: a tree-insertion entry point is externally callable on the token contract. |

## 7. Reported numbers
Per tool and per pattern: supported targets, loose, strict and mechanism-level hits, UNKNOWN, unsupported, with Wilson 95% intervals. Raw counts come first and there is no single headline number. Also reported: per-mutant other new warnings (listed, never dropped; human triage later), per-host clean false alarms, decoy false alarms, and KB-matched counts.

## 8. Tool settings (static)
- Slither 0.11.3 (pyenv 3.12.12), default detectors, `--json`, compiled through each tree's build config. The solc binaries come from `~/.local/share/svm`.
- Mythril: latest from pip at run time, version recorded; `--execution-timeout 300 --max-depth 22 --no-onchain-data -o json`, under `timeout 420`, one contract per run.
- circomspect: `tools/circomspect-src/target/release/circomspect -L node_modules <circuit>`, default level.
- Picus: `tools/picus-src/run-picus` under `timeout 600` per circuit (brief: only if under 10 min).
- `nargo check` 1.0.0-beta.22 in the circuit workspace or package.
- Every run is under `systemd-run --user --scope -p MemoryMax=8G`, one at a time, with resume state.

## Amendments
(none)
