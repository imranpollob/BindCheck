# Binding-mutant benchmark v2 (B2)

**TEST benchmark. Never share it, its mutant list or its results with any tool-building lane.**

27 injected binding flaws over 3 hosts outside every dataset family (see `HOSTS.md`), each a fail-closed exact-match edit of a vendored pinned baseline (`make_mutants.py`), with the unmutated host as the clean variant. Patterns follow `dataset/audit-sweep/labeling/GUIDE.md`.

| Pattern | n | Mutants |
|---|---|---|
| P1 unbound effect | 4 | RP-S01, PV-S01, PV-S11, OR-S01 |
| P2 context | 8 | RP-S02, RP-C01, PV-S02, PV-S03, PV-C01, OR-S02, OR-S03, OR-S04 |
| P3 replay | 5 | RP-S03, PV-S04, PV-C02, PV-C03, OR-S06 |
| P4 verifier | 5 | RP-S04, RP-S05, PV-S06, OR-S05, OR-S10 |
| P5 interface | 5 | RP-S06, PV-S08, PV-S09, OR-S08, OR-S09 |

`-S` = consumer/verifier edit, `-C` = circuit edit (verifier not regenerated). Ground truth per mutant: `mutants/<ID>.md`.

## Design decisions
- **P5 is not "swap the order".** A swapped order or wrong count makes the honest proof fail closed (denial of service, labelled N in LABELS-v1). Each P5 mutant keeps the verifier call accepting the honest proof and makes the consumer misread or truncate a proved value before using it for the effect (`uint32` address, `uint64` yield index, wrong struct word, `uint64` nullifier). A drafted fail-closed P4 mutant (borrow verified with the withdraw verifier) was dropped for the same reason.
- Weak mutants are flagged in their notes (RP-S05: range check removal, limited exploitability in this consumer; RP-C01/PV-C01..03: circuit-only, verifier unchanged; RP-S06 and OR-S09 rely on ~2^32 grinding).
- Honest-path evidence is partial: all 27 compile (`results/raw/B2/run-4/build-summary.tsv`); for `orc` the host's 32 tests give clean 32/32, and each mutant fails only the tests that assert the removed check (`logs/OR-*-tests.txt`). RedPacket and PrivacyVault tests need node/bb and could not run.

## Reproduce
```sh
sh benchmarks/binding-mutants-v2/fetch-deps.sh                       # pinned deps into results/raw/B2/deps (ignored)
OUT=results/raw/B2/run-N sh benchmarks/binding-mutants-v2/build.sh   # fresh OUT each time; nothing is deleted
RUN=$PWD/results/raw/B2/run-N SCR=<dir with venv/ mvenv/ solcx/> sh benchmarks/binding-mutants-v2/run_static.sh TOOL ID
python3 benchmarks/binding-mutants-v2/analyze_static.py results/raw/B2/run-N
```
Matching rule: `MATCHING.md` (committed in `bbd92b9` before any tool run). Results: `RESULTS-static.md`. Build outputs live under ignored `results/raw/B2/`.
