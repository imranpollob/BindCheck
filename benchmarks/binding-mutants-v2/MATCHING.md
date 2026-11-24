# Static-tool matching rule for B2 (written before any tool was run on B2)

Scope: Slither, Mythril, circomspect, Picus, `nargo check` on the 27 mutants and the 3 clean hosts. It follows the shape of `dataset/labels-v1/SCORING.md` (location first, mechanism second) and is fixed before the first run. Any later amendment is listed at the bottom with its date and may not be applied to results already seen.

## Units and ground truth
- Ground truth of a mutant is in `mutants/<ID>.md`: consumer file, consumer function, unbound value, and the edited file with its edit lines (from `generation-record.json` and the diff against `baselines/`).
- A tool is run on the mutant tree and on the matching clean host tree (`CLEAN-<host>`), same flags.

## Which mutants a tool can score (capability gate)
- Slither, Mythril: Solidity consumer. The analysis target is the consumer contract (`RedPacket.sol`, `PrivacyVault.sol`, `OrcClaim.sol`) with its imports. Circuit mutants (`RP-C01`, `PV-C01`, `PV-C02`, `PV-C03`) are **unsupported** for them: the consumer text is unchanged, so they are reported separately and excluded from the denominator, never counted as misses.
- circomspect, Picus: Circom circuits only (`RP-C01`). All other mutants are unsupported for these tools.
- `nargo check`: Noir circuits only (`PV-C01..03`), and the clean Noir circuits. It is a type and constraint-syntax checker, not a bug detector. It is reported for completeness. It matches only if it emits a diagnostic at an edited line.
- Build or analysis failure, crash, out-of-memory: **unsupported** (log kept). Timeout with no finding: **UNKNOWN**. Neither is a miss and neither is safe.

## Delta rule (what counts as a tool warning for a mutant)
A warning (tool, detector/check id, file basename, function or line) is **new** when no warning with the same tool, detector id, file basename and function (Solidity) or line-region (circuits) exists on the clean host. Only new warnings can match. Warnings that also appear on the clean host are baseline noise and are reported as such.

## Match levels
- **Loose match:** at least one new warning is located in the mutant's GT consumer file and GT function (Solidity), or within 3 lines of an edited line of the circuit (circuits). For a mutation that deletes a statement, the function containing the deletion point is the GT function. For `Verifier.sol` edits (`RP-S04`, `RP-S05`) the GT function pair is `Verifier.verify` or `RedPacket.open`.
- **Strict match:** loose match AND the new warning's detector is on the pre-registered mechanism list below for the mutant's pattern. The mechanism list is fixed here; there is no LLM judge for static tools.

Mechanism lists (detector ids as printed by the tool version used):
| Pattern | Slither | Mythril (SWC) | circomspect | Picus |
|---|---|---|---|---|
| P1 | `arbitrary-send-eth`, `arbitrary-send-erc20` | SWC-105 | n/a | n/a |
| P2 | `unused-return`, `missing-zero-check` | none | warnings on signal assignment `<--`, unused signals/outputs | verdict "unsafe" or "not uniquely determined" where the clean circuit is "safe" |
| P3 | none | none | none | verdict as P2 |
| P4 | `unused-return`, `unchecked-lowlevel`, `unprotected-upgrade` | SWC-104, SWC-105 | n/a | n/a |
| P5 | none | none | n/a | n/a |
"none" means no detector is pre-registered; only a loose match is possible. This is deliberate: the tools carry no binding concept, and the table is not widened after seeing output.

## Reported numbers (raw counts first, no single headline)
Per tool and per pattern: supported targets, detected loose, detected strict, UNKNOWN, unsupported, with Wilson 95% intervals. Also per clean host: baseline warning counts per tool. Also per mutant: count of new warnings that match neither level ("other new warnings"). They are listed and are not dropped; human triage is a later step.

## Honest-path labels
Mutants whose honest path is broken by construction are labeled in `mutants/<ID>.md`. Currently none is labeled honest-breaking (PV-S07 was dropped for that reason; P5 mutants were reworked to keep the honest proof accepted). Honest checks are: compile for all; `forge test` of the host's own tests for OrcClaim only. PrivacyVault's and RedPacket's own tests need node/bb (ffi) or real proofs and were not runnable, so their honest paths are **not executed**. This is stated in RESULTS-static.md.

## Tool settings
- Slither: latest from `pip` at run time, version recorded; `--solc <pinned binary>` with remappings; default detectors; `--json`.
- Mythril: `myth analyze <file> --solv <ver> --solc-json` with the host remappings, `--execution-timeout 300 --max-depth 22 -o json`. One run per consumer contract.
- circomspect: `tools/circomspect-src/target/release/circomspect <circuit>` default level.
- Picus: `tools/picus-src/run-picus` under `timeout 600` per circuit.
- `nargo check` with beta.14 in each Noir package.

## Amendments
(none)
