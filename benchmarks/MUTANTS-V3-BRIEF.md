# Lane mutants3: fresh binding-mutant benchmark B3 (test data)

B2 (`binding-mutants-v2/`) used 3 small hosts and is no longer blind for the next tool version. You build **B3**: a fresh, larger benchmark on **real open-source ZK applications**. Read `docs/EVAL-PLAN.md`, `dataset/audit-sweep/labeling/GUIDE.md` (patterns P1–P5, C1–C3) and `dataset/labels-v1/LABELS-v1.csv`.

## Walls
- **Do not read anything under `/home/pollmix/Coding/bc/mvp`.** That is the tool, its runs and its outputs.
- **Do not read `binding-mutants-v2/mutants/`.** Design your operators independently.
- B3 is test data. Never share it with a tool-building lane.

## Hosts
Pick 5 hosts. Each must:
- be an open-source ZK application with a circuit or zkVM guest, a verifier, and an EVM consumer;
- belong to **none** of the families in `LABELS-v1.csv` (column `family`) and none of the B2 hosts (`binding-mutants-v2/HOSTS.md`);
- pass `dataset/audit-sweep/tools/check_holdout.py`;
- build locally.

**Coverage required:**
- at least one Circom/Groth16 host;
- at least one Noir host;
- at least one zkVM host (RISC Zero or SP1 guest plus a Solidity consumer that decodes the journal / public values; a mock verifier is fine for its honest path);
- at least two **non-toy** hosts (real deployed-style apps, more than about 300 consumer LOC).

List the hosts in `binding-mutants-v3/HOSTS.md` with commit, licence and LOC. These hosts are then excluded from the hunt pool.

## Operators derived from real findings
Derive the mutation operators from the **unbound values and effects** of the binding findings in `LABELS-v1.csv` (`binding = Y`), so the benchmark reflects the real distribution rather than our imagination. Write `OPERATORS.md`: one operator per row, each citing the finding IDs it is modelled on. Cover:
- consumer-side and circuit/guest-side edits;
- domain/context removals (chain, contract, program ID);
- key-pinning removals;
- encoding/order changes;
- replay-key changes.

## Mutants
- **Count:** at least 35, at least 6 per pattern P1–P5, spread over hosts. At least 8 are circuit- or guest-side.
- **Form:** minimal, realistic, fail-closed exact-match edits, applied by a script.
- **Each mutant's `mutants/<ID>.md` states:**
  - the operator;
  - the broken binding;
  - the exact file and function where the unbound value enters the effect;
  - related locations;
  - the unbound value;
  - the attacker effect.
- **Each mutant must compile.**
- **Each host needs an honest-path test:** an honest proof is accepted (a mock verifier is acceptable for zkVM).
- **Clean controls:** keep every clean host as a control target, and add 5 **semantic-preserving decoys**. These are edits that look suspicious but stay bound (for example, a recipient parameter that is then required to equal a public input), to measure false alarms.

Freeze the matching rule in `binding-mutants-v3/MATCHING.md` before any tool runs. Use the same strict, loose and mechanism levels as `SCORING-v1.1.md`'s B2 section, unless you find a gap; then document it.

## Then
- Run the static tools (Slither, Mythril, circomspect, Picus if under 10 min per circuit, `nargo check`) on all mutants, clean hosts and decoys. Write `RESULTS-static.md`.
- Static tools may eat memory. Run them one at a time, cap memory with `ulimit -v` or `systemd-run --user --scope -p MemoryMax=8G` when available, and save partial results with resume state.
- Local only. No commits (the orchestrator commits). No `rm` outside build dirs, no `nohup`, no background jobs.
- Messages: `/home/pollmix/.local/bin/hc send t3z "mutants3: ..."` for milestones and blockers; `"mutants3 DONE"` at the end.
- **Deadline:** mutants and controls frozen by **2026-11-28 12:00**; static results by **2026-11-28 20:00**.
