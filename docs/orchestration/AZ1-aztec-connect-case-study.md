# AZ1 — Case study: would a binding checker have caught the Aztec Connect exploit?

**Goal for the paper:**

On 14 June 2026, an attacker took about **$2.1M** from Aztec Connect's
immutable `RollupProcessorV3`:

- The rollup proof committed to a full 32-row inner chunk.
- The contract settled only the first `numRealTxs` rows, and the attacker chose
  `numRealTxs`, which the proof did not bind.
- Proved fake deposit rows past `numRealTxs` were never collected on L1, and
  real withdrawals then paid out.

This is the paper's thesis in a real loss: **the proof was valid, but the
contract acted on something the proof did not state.**

The same shape, "the proof covers N items, but the consumer acts on a range
chosen by an unbound count", is the Payy `agg_agg` message-tail advisory that
this project already reproduced (`reports/D1P-42.md`, rule `R-EXTENT`).

AZ1 must give the paper four things:

1. An exact, source-cited explanation of the flaw, as the paper's motivating
   example.
2. A faithful **minimal analog** with a **real** verifier, reproduced end to end
   (E4) on a local chain, plus a repair that blocks it.
3. An honest answer to "**would existing tools, and BindCheck, have flagged
   it?**"
4. A precise description of the "extent binding" pattern, shared by Payy and
   Aztec Connect, for the taxonomy and for a rule.

**Branch:** `sprint/AZ1`.

**Start directory:** `$BC/wt-AZ1`.

**Owns:** `prototypes/az1/`, `reports/AZ1/`, `results/raw/AZ1/` (ignored).

**Must not edit:** `bindcheck_zk/`, `findings/`, other tasks' paths.

## Hard rules

- **Hold-out guard.** Run `python3 scripts/check_holdout.py <owner/repo>` before
  you open any repository.
  - `AztecProtocol/aztec-connect` and `AztecProtocol/aztec-connect-contracts`
    are ALLOWED.
  - **`AztecProtocol/aztec-packages` is FORBIDDEN.** Do not open it, even if a
    write-up links to it.
- **Local only.** Use only owned local chains (Anvil or Hardhat). Do not use a
  mainnet fork: H1 is not approved. You may read the exploit transaction and
  contract source on a block explorer **web page**, but make no RPC calls to
  public chains.
- **Content limits.** Do not reproduce the attack against the real contract,
  and do not publish step-by-step exploit content beyond what a public
  post-mortem already contains. The minimal analog is an owned, synthetic
  contract.
- **AI disclosure.** Record which AI coder and model ran the task.

## Steps

1. **Sources.** Collect primary and secondary sources: the Aztec Labs statement,
   rekt, SlowMist, Halborn, BlockSec and Blockaid. Find the exploit transaction
   hash (R1 has `0x074ec931…eeb1`) and the `RollupProcessorV3` verified source.
   Record URL, date and hash for each source.
2. **Code reading.** In `AztecProtocol/aztec-connect` (pinned commit), locate:
   - where `processRollup` decodes `numRealTxs`;
   - how the public-inputs hash is computed, and over which rows;
   - the settlement loop bound;
   - why the fake rows were proved but not settled.

   Quote file paths and line numbers. State the attacker's capability (any
   caller, or a registered rollup provider?).
3. **Tool answers.** For each tool, record the exact command, version and
   output:

   | Tool | Expectation and instruction |
   |---|---|
   | **BindCheck freeze 2** (`bindcheck_zk`, hash `92789fad…`) | Its circuits are Circom/Noir, and Aztec Connect's are C++ (barretenberg). Expect UNKNOWN on the circuit side. **Record what the consumer-side patterns P1 and P5 report on `RollupProcessorV3`.** |
   | **D1 line `R-EXTENT`** (`reports/D1P-42.md`) | State whether its interface can express this case, and run it if it can. |
   | **Slither** | Default detectors. |

   Do **not** change any analyzer. If a tool cannot run, record UNKNOWN with
   the reason. Never record it as "missed".
4. **Minimal analog: E4 with a real verifier.** Write a small Circom (or Noir)
   circuit that proves a fixed-size batch of N rows, with a commitment over all
   N rows as a public input. Write a Solidity consumer that settles only the
   first `k` rows, with `k` taken from calldata and not bound by the proof.

   On a local chain with synthetic tokens, show:
   - an honest batch settles correctly;
   - a batch with proved "deposit" rows past `k` lets real "withdrawal" rows pay
     out without the matching deposits being collected. **That is E4.**
   - **Repair:** bind `k` into the public inputs, or require that every row
     past `k` is a proved no-op. The repair rejects the attack, and the honest
     batch still settles.

   Then run BindCheck freeze 2 and Slither on the analog, and record the
   results.
5. **Pattern.** Write a one-page definition of **extent binding**:
   - the proof covers a sequence of length L;
   - the consumer acts on a sub-range whose bounds are not fixed by the proof.

   Show that Payy (`agg_agg` message tail) and Aztec Connect are both instances.
   Map it to the classes P1–P5. Reviewer's view: P1, an unbound effect extent.
   Say what facts a checker needs to decide it:
   - the consumer loop bound;
   - the public-input coverage;
   - the circuit's padding or no-op semantics.

   Also say whether the decision **needs the circuit**.

## Output

`reports/AZ1/REPORT.md` in the handoff template of
`docs/orchestration/README.md`, with:

- the mechanism, with code lines;
- a tool-answer table: tool × target (real contract, analog) × verdict, with the
  reason;
- the E4 analog results and the repair result;
- the pattern definition;
- one paragraph written as the paper's motivating example: at most 150 words,
  plain, with no exploit recipe.

Also:

- `prototypes/az1/run.sh`, which reproduces the analog with pinned tools and
  records checksums;
- reuse T0's `scripts/setup_linux_tools.sh` toolchain.

## Completion criteria

- The mechanism is explained with source lines and at least one primary or two
  independent secondary sources.
- The analog reaches E4 with a real Groth16 or UltraHonk verifier, and the
  repair is validated.
- Every tool cell has a recorded command and result, or an UNKNOWN reason.
- The extent-binding definition covers both Payy and Aztec Connect.

## Time box

Two days. If the analog is blocked for more than about 4 hours, finish steps 1,
2, 3 and 5, report PARTIAL, and list the blocker.
