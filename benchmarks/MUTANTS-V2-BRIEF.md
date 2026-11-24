# Lane mutants: binding-mutant benchmark v2 (B2)

Read `docs/EVAL-PLAN.md` and `benchmarks/binding-mutants/README.md` (the existing 30 WarpToad/Payy mutants). Patterns P1–P5 are defined in `dataset/audit-sweep/labeling/GUIDE.md`.

## Goal
Build `benchmarks/binding-mutants-v2/`, a benchmark of **injected** binding flaws for measuring per-pattern recall, with a matching clean variant for each.

## Hosts
Pick 3–4 open-source ZK applications (circuit + EVM verifier + consumer) that:
- are in **none** of the families in `dataset/labels-v1/LABELS-v1.csv` (column `family`);
- are not FORBIDDEN by `tools/check_holdout.py` (run it before touching a repo);
- are small enough to build locally;
- ideally span Circom/Groth16, Noir and an SP1/RISC Zero app.

List them in `binding-mutants-v2/HOSTS.md`. These hosts are then excluded from the hunt pool.

## Mutants
At least 3 mutants per pattern P1–P5, across hosts, each a minimal, realistic edit (fail-closed exact-match edits, as in `make_mutants.py`). For each mutant write `mutants/<ID>.md`:
- the operator;
- which binding is broken;
- the exact consumer file and function;
- the unbound value;
- the expected effect.

Each mutant must compile. Do a cheap honest-execution check where possible.

## Then run the static tools on all mutants and their clean hosts
- Slither;
- Mythril (venv; skip it if the install fails);
- circomspect at `tools/circomspect-src/target/release/circomspect` for Circom;
- Picus at `tools/picus-src/run-picus`, if under 10 minutes per circuit;
- `nargo check` for Noir.

Commit the matching rule into `binding-mutants-v2/MATCHING.md` before running, then write `binding-mutants-v2/RESULTS-static.md`.

## Rules
- This is a **test** benchmark: never share it with any tool-building lane.
- Local only. No commits (the orchestrator commits).
- No `rm` outside the benchmark's build dirs, no `nohup`, no background jobs.
- Use `/home/pollmix/.local/bin/hc`: `hc send t3z "mutants: ..."` at milestones and for blockers.
