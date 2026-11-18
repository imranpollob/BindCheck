# S2c — Extent-binding rule, direction (b) (DEV only)

## Research context (read first)

Authorized **defensive** research for an academic paper (IEEE EuroS&P 2027).
This is static-analyzer engineering: add a detector rule. No network, no live
systems, no chain access.

**Goal for the paper.** AZ1 showed that BindCheck freeze 2, Slither and D1
`R-EXTENT` all miss the fault class behind the Aztec Connect incident. Read
`reports/AZ1/REPORT.md`, section "Extent binding". Direction (b), *binding
beyond discharge*: the proof commits to a sequence of length L, but the
consumer performs per-element effects or obligation discharges only on a prefix
whose bound comes from calldata that the proof does not fix. The paper must be
able to say: "freeze 2 missed it; the extent rule catches it, and here is its
cost on DEV".

**Branch / worktree:** `sprint/S2c`, `$BC/wt-S2c`.

**Owns:** `bindcheck_zk/extent.py` (new), a **minimal** hook in
`bindcheck_zk/analyzer.py`, `tests/s2c/`, `reports/S2c/`, `results/raw/S2c/`.

**Must not edit:** `findings/`, `oracle/`, `prototypes/`, other analyzer logic.
Another lane (S2a2) is editing `bindcheck_zk/analyzer.py` and
`bindcheck_zk/solidity.py` in parallel. Keep your hook small so the merge is
easy.

## Rule specification

Emit a candidate on a consumer function when **all** hold:

1. A verifier call is recovered whose public input is (or is derived from) a
   commitment/hash computed over a calldata region R.
2. A loop in the same transaction performs per-element effects (token
   transfers, balance/mapping writes, external calls) over elements of R.
3. The loop bound is derived from calldata **outside** what the proof fixes
   (not a public input, not derived from one, not a constant equal to the
   committed length).
4. The committed length L (from the hashing loop or region size) can exceed
   the loop bound, i.e. there is no `require(bound == L)` or equivalent.

Verdicts, fail closed:

- All four facts established → `VIOLATION` (new pattern ID `P1-EXTENT`, or a
  P1 sub-reason; justify the choice in the report).
- Bound proved equal to the committed length, or every skipped element is
  checked to be a no-op by the consumer → `VERIFIED_WITHIN_SCOPE`.
- Any fact unresolved (inline assembly not modeled, commitment not recovered,
  circuit padding semantics needed) → `UNKNOWN` with a reason code. Whether the
  circuit forces skipped rows to be neutral is a circuit fact. Without the
  circuit, never say VERIFIED on that ground alone.

## Steps

1. Read `reports/AZ1/REPORT.md`, `prototypes/az1/contracts/SettlementFaulty.sol`
   and `SettlementFixed.sol`, `docs/research-contract.md`, `docs/FREEZE-2.md`.
2. Implement the rule in `bindcheck_zk/extent.py`. General code only: no
   repository, file or contract names.
3. Tests in `tests/s2c/`: the AZ1 faulty contract gives VIOLATION and the
   fixed contract does not. Add at least two more synthetic variants you write
   yourself: bound equals the committed length (VERIFIED), and an unresolved
   bound source (UNKNOWN).
4. Report what the rule says on the real `RollupProcessorV3` (read-only verified-source copy at
   `$BC/wt-AZ1/results/raw/AZ1/deployed-source/files/`; if absent, state UNKNOWN; do not fetch). It uses
   inline assembly, so UNKNOWN with a precise reason is an acceptable answer.
5. False-positive cost: run the analyzer with the rule over the original 56 DEV
   rows using `python3 scripts/run_bindcheck_zk_full_dev.py --phase after
   --skip-fetch --checkout-root $BC/BindCheck/feasibility/work/full-dev`
   (redirect raw output to `results/raw/S2c/`). List every new extent warning
   with file:line and your judgement (TP/FP/unsure). Do not tune on these
   results beyond fixing clear bugs, and record each change you make.
6. Full test suite as in `docs/FREEZE-2.md`, with
   `BINDCHECK_CIRCOM=$BC/BindCheck/tools/circom-2.1.9/target/release/circom`.
   Everything must pass.

## Environment limits

- No network. Do not `git commit` or push: the sandbox cannot write the git
  directory. Leave your changes in the working tree; the reviewer commits them.
- Before reading any third-party repository, run
  `python3 scripts/check_holdout.py <owner/repo>`. If it prints FORBIDDEN, do not open it.

## Completion criteria

- AZ1 faulty → VIOLATION; AZ1 fixed → not VIOLATION; synthetic variants as
  specified; full suite green.
- DEV warning list with a judgement for each warning.
- `reports/S2c/REPORT.md` in the handoff template of
  `docs/orchestration/README.md`, including the AI disclosure (tool + model)
  and the new candidate content hash (`python3 -m bindcheck_zk.freeze`). Do not
  declare a freeze.
- Final line of your session: `S2c DONE` or `S2c BLOCKED: <reason>`.
