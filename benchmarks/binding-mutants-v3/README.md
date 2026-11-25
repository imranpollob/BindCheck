# Binding-mutant benchmark v3 (paper: B3)

**TEST benchmark. Never share it, its mutant list, KB section or results with any tool-building lane.**

37 binding mutants (P1 8, P2 7, P3 8, P4 8, P5 6; 11 circuit- or guest-side) and 5 semantic-preserving decoys over 5 hosts outside every dataset family (`HOSTS.md`). The 5 clean hosts are controls. Operators come from the LABELS-v1 binding findings (`OPERATORS.md`). Ground truth is in `mutants/<ID>.md` and `decoys/<ID>.md`, both generated from `make_mutants.py`, which applies fail-closed exact-match edits. The matching rule is `MATCHING.md`, frozen 2026-11-25T08:02Z before any tool run; hashes are in `results/raw/B3/FREEZE-matching.txt`.

## Status (2026-11-25)
- **Done:**
  - hosts gated;
  - baselines exported from the pinned SHAs;
  - all 42 edited trees (37 + 5) and the 5 clean hosts compile (`results/raw/B3/run-1-*`, `run-0-clean-b`, `run-0-clean-c`);
  - honest paths executed for all 5 hosts (`results/raw/B3/honest-1`, all exit 0);
  - kill tests partly done (below).
- **Kill-test evidence so far** (`results/raw/B3/kill-2/kill-results.json`): host tests that pass on clean and fail on the edit.
  - Killed: DK-C01, DK-C02, KK-C01 and KK-C02.
  - DK-S01 survives the host's flipped-input tests. This is expected, because sumcheck still rejects a flipped honest proof; the forgery needs a crafted proof.
  - Decoys DK-D01 and KK-D01 fail tests that pin the removed line (nonce count, range-check message). That shows the edit was exercised, not that a binding broke. Their bound-ness argument is in `decoys/`.
  - Not yet run for the other hosts' mutants.
- **Not done yet:** static tool runs and `RESULTS-static.md`. The B3 run scripts `run_static.sh` and `analyze_static.py` are not yet written; adapt them from B2's scripts.

## Reproduce
```sh
sh benchmarks/binding-mutants-v3/fetch-deps.sh                          # pinned deps -> results/raw/B3/deps (ignored)
CAND=results/raw/B3/candidates sh benchmarks/binding-mutants-v3/export-baselines.sh   # only if baselines/ is absent
OUT=results/raw/B3/run-N sh benchmarks/binding-mutants-v3/build.sh      # fresh OUT; ONLY="ID ..." for a subset
OUT=results/raw/B3/honest-N sh benchmarks/binding-mutants-v3/run_honest.sh
python3 benchmarks/binding-mutants-v3/run_killtests.py --honest results/raw/B3/honest-N --out results/raw/B3/kill-N [--ids ...]
```
`CAND` holds clones of the five repos at the pinned commits listed in `HOSTS.md`. Toolchains: forge 1.4.1, solc from svm, nargo 1.0.0-beta.22, circom 2.2.2 and 2.2.3 (`tools/circom-src`), node 22.20, cargo.
