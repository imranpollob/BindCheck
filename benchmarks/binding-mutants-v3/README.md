# Binding-mutant benchmark v3 (paper: B3)

**TEST benchmark. Never share it, its mutant list, KB section or results with any tool-building lane.**

37 binding mutants (P1 8, P2 7, P3 8, P4 8, P5 6; 11 circuit- or guest-side) and 5 semantic-preserving decoys over 5 hosts outside every dataset family (`HOSTS.md`). The 5 clean hosts are controls. Operators come from the LABELS-v1 binding findings (`OPERATORS.md`). Ground truth is in `mutants/<ID>.md` and `decoys/<ID>.md`, both generated from `make_mutants.py`, which applies fail-closed exact-match edits. The matching rule is `MATCHING.md`, frozen 2026-11-25T08:02Z before any tool run; hashes are in `results/raw/B3/FREEZE-matching.txt`.

## Status (2026-11-25, resumed after the usage-limit stop)
- **Done:**
  - all trees compile;
  - honest paths for all 5 hosts (`results/raw/B3/honest-1`);
  - kill tests for all 42 edited trees (`results/raw/B3/kill-2/kill-results.json`);
  - static tools under the frozen settings, scored by `analyze_static.py`; see `RESULTS-static.md`. In short, Mythril was supported on only 2 of 26 Solidity mutants, with 0 hits; the other 24 are unsupported because no contract was created. A post-hoc arm on local Anvil (not pre-registered) deployed all 26: 0 mechanism-level hits, 1 raw new issue (also on a decoy), 0 clean noise. Only 6 of the 26 got a non-empty second transaction; 12 reached the 300 s budget (UNKNOWN) and 8 (kakushi) never got past one transaction.
- **Kill-test results (37 mutants):** 24 killed, 7 survive the host tests, 6 n/a.
  - **Host-test coverage gaps (survivors).** Each of these survives because the host's own tests do not exercise the broken binding. None of them is an unverified or equivalent mutant: each has its expected-effect argument in `mutants/<ID>.md`.
    - ZK-S01, ZK-S02, ZK-S03, ZK-S04, ZK-S05: the zkerc20 host has only happy-path tests.
    - DK-S01: a forgery needs a crafted proof, and no host test supplies one.
    - XC-G02: no host test covers the lock journal.
  - n/a: Circom circuit mutants ZK-C01..C04 and DV-C01 have no runnable host circuit tests.
  - Decoys DK-D01, KK-D01 and XC-D01 fail tests that pin the removed line; DV-D01 is n/a. This is not evidence that their binding broke.
- **Static tools** (`results/raw/B3/static-1`, `run_static.sh`, resumable): see `RESULTS-static.md`.
  - Mythril caveat: exit 0 with `success: true` and 0 issues does **not** mean the contract was analysed. See "Detecting a vacuous Mythril run" in `RESULTS-static.md`.
  - Picus could not run (no Racket runtime locally), so it is unsupported.

## Dev notes
- 2026-11-25: the resume session (lane mutants3) ran on Claude Opus at medium effort.
  - It found that some Mythril runs under the frozen settings never deployed the contract.
  - It added the `MYV`/`MYX`/`MYTO` knobs to `run_static.sh`. Their defaults reproduce the frozen command exactly.
  - It ran a `-v 4` diagnostic rerun (`static-1-mythril-diag`) and a limiter test (`static-limiter`). Any post-hoc Mythril arm is reported separately in `RESULTS-static.md` and is not pre-registered.
  - It ran the post-hoc Anvil Mythril arm (`anvil/`, `results/raw/B3/static-2-mythril-anvil`, 53 runs, scorer hashes frozen in `FREEZE-scorer.txt` before any mutant result).
  - It added the missing DarkVault targets for DK-S01 (Slither and Mythril) and the missing Connector target for XC-S04 (Mythril).

## Reproduce
```sh
sh benchmarks/binding-mutants-v3/fetch-deps.sh                          # pinned deps -> results/raw/B3/deps (ignored)
CAND=results/raw/B3/candidates sh benchmarks/binding-mutants-v3/export-baselines.sh   # only if baselines/ is absent
OUT=results/raw/B3/run-N sh benchmarks/binding-mutants-v3/build.sh      # fresh OUT; ONLY="ID ..." for a subset
OUT=results/raw/B3/honest-N sh benchmarks/binding-mutants-v3/run_honest.sh
python3 benchmarks/binding-mutants-v3/run_killtests.py --honest results/raw/B3/honest-N --out results/raw/B3/kill-N [--ids ...]
STATIC=results/raw/B3/static-N sh benchmarks/binding-mutants-v3/run_static.sh TOOL ID[@part]   # one target per call
# see RESULTS-static.md for the exact analyze_static.py invocations
```
`CAND` holds clones of the five repos at the pinned commits listed in `HOSTS.md`. Toolchains: forge 1.4.1, solc from svm, nargo 1.0.0-beta.22, circom 2.2.2 and 2.2.3 (`tools/circom-src`), node 22.20, cargo.
