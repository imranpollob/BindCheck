# B2 static-tool results (run-4, 2026-11-24)

Matching rule: `MATCHING.md`, sha256 `07c38919b68fd01b99d5646d3f27a669f27837be678b2af31005dad772ca0027`, committed in `bbd92b9` before any tool ran. No amendment was made. Raw outputs: `results/raw/B2/run-4/static/<tool>/` (ignored); per-mutant table `static/matches.tsv`, summary `static/summary.tsv`, produced by `analyze_static.py`.

## Headline (raw counts; no single number)
**The two Solidity static tools found none of the 23 consumer-layer binding mutants at the mechanism level.** Slither produced two incidental location-only matches (below), Mythril produced no issue on any contract. The only mechanism-level hit is circomspect on the one Circom circuit mutant, and it flags an unnecessary `<--`, not binding.

| Tool | Pattern | Supported | Loose | Strict | UNKNOWN | Unsupported | Loose 95% Wilson |
|---|---|---|---|---|---|---|---|
| Slither | P1 | 2 | 0 | 0 | 0 | 2 | 0.00-0.66 |
| Slither | P2 | 4 | 0 | 0 | 0 | 4 | 0.00-0.49 |
| Slither | P3 | 2 | 2 | 0 | 0 | 3 | 0.34-1.00 |
| Slither | P4 | 4 | 0 | 0 | 0 | 1 | 0.00-0.49 |
| Slither | P5 | 3 | 0 | 0 | 0 | 2 | 0.00-0.56 |
| Mythril | P1 | 4 | 0 | 0 | 0 | 0 | 0.00-0.49 |
| Mythril | P2 | 6 | 0 | 0 | 0 | 2 | 0.00-0.39 |
| Mythril | P3 | 3 | 0 | 0 | 0 | 2 | 0.00-0.56 |
| Mythril | P4 | 5 | 0 | 0 | 0 | 0 | 0.00-0.43 |
| Mythril | P5 | 5 | 0 | 0 | 0 | 0 | 0.00-0.43 |
| circomspect | P2 | 1 | 1 | 1 | 0 | 0 | 0.21-1.00 |
| Picus | P2 | 1 | 0 | 0 | 1 | 0 | 0.00-0.79 |
| nargo check | P2 | 1 | 1 | 0 | 0 | 0 | 0.21-1.00 |
| nargo check | P3 | 2 | 1 | 0 | 0 | 0 | 0.09-0.91 |

"Unsupported" = the tool cannot see that layer (circuit mutants for Slither/Mythril, 4 mutants) or the run failed (Slither on all 8 PrivacyVault consumer mutants). It is not a miss and not safe. Slither's 2 loose P3 matches out of 2 supported are incidental (next section); do not read them as detection.

## Details a reader needs
- **Slither loose matches are incidental.** RP-S03: new `missing-zero-check` on the added `to` argument (a P2-list detector, not the P3 mechanism). OR-S06: new `uninitialized-state` on `nullifierUsed`, because the only write was deleted. Both fire because the edit changed code shape, not because the tool saw a missing replay or sender binding. Neither is a strict match under the pre-registered table.
- **Slither on PrivacyVault: run failed** (`AssertionError` in `constants_folding._post_identifier`, slither 0.11.6, solc 0.8.28, OZ 5.5.0 + poseidon2-evm). All 8 PV consumer mutants and the clean host are therefore unsupported for Slither. No workaround was applied, so every tool sees identical snapshots.
- **Mythril**: v0.24.8, `--execution-timeout 300 --max-depth 22 --no-onchain-data`, one run on the consumer contract. Longest run 103 s, so none hit the timeout; clean hosts and all 23 consumer mutants returned `success: true` with zero issues. Zero issues here means "no finding", not safe. It was run from a Python 3.10 venv (pip build of `pyethash` fails on the default 3.12). RedPacket, PrivacyVault and OrcClaim compiled with solc 0.8.17 / 0.8.28 / 0.8.20.
- **circomspect** (`tools/circomspect-src` @ `50010b62…`): clean circuit 0 issues; RP-C01 2 new warnings at the edited line (unnecessary `<--`, value never read). That equals a strict match under the table (it lists `<--` warnings), but it is a code-style pass rather than a binding detector: it would flag any `<--`, including benign ones.
- **Picus** (`tools/picus-src` @ `138b151d…`, Racket 9.3 minimal + `rackunit-lib` + `math-lib`, cvc5 from `tools/cvc5-1.4.2-gpl`): clean circuit "properly constrained" (17 s); RP-C01 "Cannot determine whether the circuit is properly constrained" (17 s). That is not "unsafe" or "not uniquely determined" in the pre-registered list, so it is recorded as UNKNOWN (verdict changed from safe, no counterexample). It is not counted as detection.
- **nargo check** (beta.14) is a compiler, not a detector. Its "loose" matches are `unused variable` warnings at the edited line (PV-C01 `computed_root`, PV-C02 `computed_nullifier_hash`); PV-C03 produced no diagnostic at the edit. A benign refactor would give the same warnings.
- **Clean-host baselines**: Slither RedPacket 16 findings (weak-prng, timestamp, assembly, reentrancy-events, low-level-calls, naming, ...), OrcClaim 3 (timestamp x2, cyclomatic-complexity), PrivacyVault n/a (run failed). Mythril, circomspect: 0. Per-mutant "other new warnings": 0 for every tool and mutant (no new warning outside the GT function).

## Caveats
- **Detection by static tools is not the benchmark's validity claim.** Mutants are predictions of binding flaws; none was confirmed with a real proof (E4). Honest paths are partial: compile for all 27; `orc` host tests only (clean 32/32; every OR mutant fails only tests asserting the removed check, OR-S09 fails assertions that read the full-nullifier key). RedPacket and PrivacyVault tests need node/bb ffi, so their honest paths were not executed.
- Circuit mutants (`RP-C01`, `PV-C01..03`) change a circuit without regenerating the verifier. They are targets for circuit tools only.
- Exploitability notes per mutant are in `mutants/<ID>.md`; RP-S05, RP-S06, OR-S09 are weak or grind-dependent.
- The matching table pre-registered no detector for P3 and P5 (Slither, Mythril); loose is the only reachable level there. That was deliberate (these tools have no binding concept) and was not widened after seeing results.
- 27 mutants on 3 hosts: per-pattern n is 4-8, so intervals are wide. Hosts are small (one is a PoC). Results describe these hosts, not ZK applications in general.

## Environment
Linux x86_64; slither-analyzer 0.11.6 (py3.12 venv); mythril 0.24.8 (py3.10 venv); circomspect and Picus from `tools/` at the revisions above; forge 1.4.1; circom 2.2.2 (circuit compile); nargo 1.0.0-beta.14 (compile, check); solc 0.8.17/0.8.20/0.8.28 (solc-select artifacts). Dependencies pinned in `fetch-deps.sh`. Build run: `results/raw/B2/run-4` (earlier runs run-1..3 kept; run-1/2 were superseded by design changes, run-3 by an OR-S10 fix).
