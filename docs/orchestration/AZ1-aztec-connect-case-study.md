# AZ1 — Detection case study: a binding checker and the Aztec Connect incident

## Research context and authorization (read first)

This is authorized **defensive** security research for an academic paper
targeting IEEE EuroS&P 2027. The project, BindCheck, is a static analyzer that
**detects** a class of smart-contract bug where a contract accepts a valid
zero-knowledge proof but acts on a value the proof does not bind. The goal of
this task is to measure whether such a detector flags the fault behind a
**publicly disclosed, already-patched-by-deprecation** incident.

Scope and safety, which this task does not exceed:

- The incident is public. Aztec Labs, rekt, SlowMist, Halborn, BlockSec and
  Blockaid have all published the root cause. This task adds detection
  analysis, not new offensive knowledge.
- No real or live system is touched. The reproduction uses an **owned,
  synthetic, minimal testbed contract** on a local chain, with test tokens of
  no value. No mainnet fork, no RPC to public chains, no transaction broadcast.
- The deliverable is a **regression fixture and a detector evaluation**, like a
  test case in a fuzzing or static-analysis paper. It is not an exploit tool
  and must not be usable as one against any deployed system.
- No maintainer is contacted and nothing is disclosed from this task.

This framing matches how top security venues (IEEE S&P, EuroS&P, USENIX
Security, CCS) expect vulnerability-detection work to be done: reconstruct a
known fault on a controlled testbed, then measure whether the tool catches it.

## Goal for the paper

On 14 June 2026 a publicly disclosed incident caused about **$2.1M** in losses
from Aztec Connect's immutable, deprecated `RollupProcessorV3`. The documented
root cause:

- The rollup proof committed to a full 32-row inner chunk.
- The contract settled only the first `numRealTxs` rows, and `numRealTxs` was
  caller-supplied and **not bound by the proof**.
- Rows past `numRealTxs` were proved but never settled on L1, so later
  settlement paid out more than was actually funded.

This is the paper's thesis shown in a real loss: **a valid proof, and a
contract acting on a value the proof does not fix.**

The same shape, "the proof covers N items, but the consumer acts on a range set
by an unbound count", is the Payy `agg_agg` message-tail advisory that this
project already reproduced (`reports/D1P-42.md`, rule `R-EXTENT`). AZ1 links the
two so the paper has one named pattern with one advisory and one real-loss
instance.

AZ1 must give the paper four things:

1. A source-cited explanation of the fault, for the motivating example.
2. A faithful **minimal synthetic testbed** with a **real** verifier, run end to
   end on a local chain, as a detector regression fixture, plus the fix that
   removes the fault.
3. An honest answer to "**which tools flag this fault, and does BindCheck?**"
4. A precise definition of the "extent binding" pattern for the taxonomy.

**Branch:** `sprint/AZ1`.

**Start directory:** `$BC/wt-AZ1`.

**Owns:** `prototypes/az1/`, `reports/AZ1/`, `results/raw/AZ1/` (ignored).

**Must not edit:** `bindcheck_zk/`, `findings/`, other tasks' paths.

## Hard rules

- **Hold-out guard.** Run `python3 scripts/check_holdout.py <owner/repo>` before
  you open any repository.
  - `AztecProtocol/aztec-connect` and `AztecProtocol/aztec-connect-contracts`
    are ALLOWED.
  - **`AztecProtocol/aztec-packages` is FORBIDDEN.** Do not open it.
- **Local and synthetic only.** Owned local chains (Anvil or Hardhat) with test
  tokens. No mainnet fork (H1 is not approved), no RPC to public chains, no
  broadcast. Reading a public block-explorer web page or a post-mortem is fine.
- **Defensive output only.** The synthetic testbed demonstrates the *detection
  target*, not a reusable weapon. Keep it minimal and self-contained. Do not
  write anything that targets, or could be pointed at, a real deployment. Do not
  include real contract addresses as call targets.
- **AI disclosure.** Record which AI coder and model ran the task.

## Steps

1. **Sources.** Collect the public primary and secondary write-ups (Aztec Labs
   statement, rekt, SlowMist, Halborn, BlockSec, Blockaid). Record URL, date and
   a content hash for each. Note the disclosed incident transaction hash from
   the write-ups for citation only; do not query it on a live node.
2. **Code reading.** In `AztecProtocol/aztec-connect` at a pinned commit, locate
   and quote (file path + line):
   - where `processRollup` decodes `numRealTxs`;
   - how the public-inputs hash is computed and over which rows;
   - the settlement loop bound;
   - why rows past the processed count were proved but not settled.

   State the caller capability the write-ups describe (any caller, or a
   permissioned rollup provider).
3. **Tool answers.** For each tool record the exact command, version and output.
   Change no analyzer.

   | Tool | Instruction |
   |---|---|
   | **BindCheck freeze 2** (`bindcheck_zk`, `92789fad…`) | Aztec Connect circuits are C++ (barretenberg), so expect circuit-side UNKNOWN. Record what consumer-side patterns P1 and P5 report on `RollupProcessorV3`. |
   | **D1 line `R-EXTENT`** (`reports/D1P-42.md`) | State whether its interface expresses this case; run it if so. |
   | **Slither** | Default detectors. |

   A tool that cannot run is UNKNOWN with a reason, never "missed".
4. **Minimal synthetic testbed: detector fixture.** Write a small Circom or Noir
   circuit that proves a fixed-size batch of N rows with a commitment over all N
   rows as a public input. Write a Solidity settlement contract that processes
   only the first `k` rows, with `k` from calldata and **not** bound by the
   proof. On a local chain with test tokens, record three runs:
   - an honest batch settles correctly;
   - a batch whose rows past `k` are not settled shows the accounting gap the
     incident describes — the fault condition, demonstrated on the owned
     testbed;
   - the **fixed** contract (bind `k` into the public inputs, or require each
     row past `k` to be a proved no-op) rejects the faulty batch and still
     settles the honest one.

   Then run BindCheck freeze 2 and Slither on both the faulty and fixed testbed
   and record what each reports. This mirrors the existing `findings/*/run.sh`
   fixtures: a faulty/fixed pair with a real verifier, used to evaluate the
   detector.
5. **Pattern.** Write a one-page definition of **extent binding**: the proof
   covers a sequence of length L; the consumer acts on a sub-range whose bounds
   the proof does not fix. Show Payy (`agg_agg` tail) and Aztec Connect are both
   instances. Map it to P1–P5 (reviewer's view: P1, an unbound effect extent).
   List the facts a checker needs to decide it (consumer loop bound,
   public-input coverage, circuit padding/no-op semantics) and whether the
   decision needs the circuit.

## Output

`reports/AZ1/REPORT.md` in the handoff template of
`docs/orchestration/README.md`, with:

- the mechanism, with code lines;
- a tool × target (real contract, testbed) × verdict table, with reasons;
- the testbed fixture results and the fix result;
- the pattern definition;
- a motivating-example paragraph for the paper, at most 150 words, plain prose,
  describing the fault and the detection question, with no step-by-step recipe
  and no live-system targeting.

Also:

- `prototypes/az1/run.sh`, which reproduces the testbed with pinned tools and
  records checksums;
- reuse of T0's `scripts/setup_linux_tools.sh` toolchain.

## Completion criteria

- The mechanism is explained with source lines and at least one primary or two
  independent secondary sources.
- The synthetic faulty/fixed testbed runs end to end with a real Groth16 or
  UltraHonk verifier on a local chain, and the fix removes the fault.
- Every tool cell has a recorded command and result, or an UNKNOWN reason.
- The extent-binding definition covers both Payy and Aztec Connect.

## Time box

Two days. If the testbed is blocked for more than about 4 hours, finish steps 1,
2, 3 and 5, report PARTIAL, and list the blocker.
