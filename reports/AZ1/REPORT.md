# AZ1 — Detection case study: a binding checker and the Aztec Connect incident
Status: DONE
Verdict/outcome: Real target: BindCheck freeze 2 `UNKNOWN` on every pattern (no consumer recovered); Slither raises no warning on the fault; R-EXTENT's interface cannot express the case. Testbed: fault reproduced on an owned local chain with a real Groth16 verifier, and the fix removes it; BindCheck P1 `UNKNOWN`/P5 `VERIFIED_WITHIN_SCOPE` on **both** variants (no detection); Slither output identical on both variants (no detection).

AI disclosure: run by Claude Code (Anthropic), model Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-17/18 UTC, worktree `$BC/wt-AZ1`, branch `sprint/AZ1`. The human author has not inspected the outputs yet.

## What was done

1. Collected and hashed the public write-ups (step 1).
2. Ran the hold-out guard, then read `AztecProtocol/aztec-connect` at a pinned commit. Located the decode, hash, settlement and caller-access lines. Confirmed that the deployed implementation's verified source equals the pinned files (step 2).
3. Ran BindCheck freeze 2 and Slither on the real contract, and analysed whether D1 `R-EXTENT` can express the case (step 3).
4. Built a minimal faulty/fixed synthetic testbed (Circom 2.2.3 + snarkjs 0.7.6 Groth16, Anvil). Ran it end to end (53/53 steps as expected), then ran BindCheck and Slither on both variants (step 4).
5. Defined extent binding (step 5).

## Mechanism (with code lines)

Source: `AztecProtocol/aztec-connect` @ `69de49b1be49ae3757ccb53f07d9cb04a1987184`. This is the head of PR #67 (`cl/ejector`, "Ejector changes in prep for shutdown", 2024-04-11), the PR that adds `RollupProcessorV3.sol`. PR #67 shows as not merged; the deployed V3 came from this branch.

**Correspondence (source-confirmed, not bytecode-checked by me).** Sourcify's verified-source record for implementation `0x7d65…2728` (the address named by Rekt and BlockSec) holds 20 files. `RollupProcessorV3.sol` (sha256 `7d78725e…6d31`) and `Decoder.sol` (`92e8ebe3…6078`) are **byte-identical** to the pinned commit. The recorded compiler is solc 0.8.10, with 2000 optimizer runs.

| question | location | finding |
|---|---|---|
| where `numRealTxs` is decoded | `contracts/src/core/Decoder.sol:342` (layout comment `:33`, offsets `:73`, `:78`) | `numTxs := and(calldataload(add(inPtr, NUM_REAL_TRANSACTIONS_OFFSET)), 0xffffffff)`. Bytes `0x11c0–0x11c4` lie **after** the `ROLLUP_HEADER_LENGTH = 4544` (`0x11c0`) header. |
| public-inputs hash, and over which rows | `Decoder.sol:455–515` | sha256 over the header (`calldatacopy … ROLLUP_HEADER_LENGTH`, `:470`), then one sha256 per non-empty inner rollup over **all** `numJoinSplitsPerRollup` rows (`rollupDataSize`, `:458`, loop `:481–488`), then zero-hashes for empty chunks. `numTxs` only selects how many chunks count as non-empty (`:461–463`). It is not part of the hash preimage. |
| circuit side | `aztec-connect-cpp/src/rollup/proofs/rollup/rollup_circuit.cpp:264,362,402,419–421`; `root_rollup/root_rollup_circuit.cpp:366–385,396` | Inner `num_txs` is a **private witness** (`:264`). It gates `is_real` (`:362`) and is tied to non-padding proofs (`:402`). The inner hash covers the whole padded chunk (`:419–421`). The root header fields (`:367–379`) do not contain `num_txs`. The only public input is the hash (`:396`). |
| settlement loop bound | `contracts/src/core/processors/RollupProcessorV3.sol:1186`, loop `:1190–1256` | `end := add(proofDataPtr, mul(_numTxs, TX_PUBLIC_INPUT_LENGTH))`. Deposits call `decreasePendingDepositBalance` (`:1245`), and withdrawals call `withdraw` (`:1249`), only for rows `< numTxs`. |
| order of effects | `RollupProcessorV3.sol:1009–1010` | `verifyProofAndUpdateState` (state roots for every proved row), then `processDepositsAndWithdrawals(_proofData, _numTxs, …)`. |
| why rows past the count are proved but not settled | as above | The proof binds every row of the chunk plus a header that omits the count. The contract takes the count from unhashed calldata. A deposit row placed past `numRealTxs` updates the proved L2 state without consuming an L1 pending deposit. |
| caller capability | `RollupProcessorV3.sol:665–675` vs `RollupProcessorV2.sol:686–701` | V2 requires `rollupProviders[msg.sender]` or an open escape hatch. **V3 drops that check, so any caller can submit**, matching BlockSec ("opened proof submission to all users"). Rekt calls this a contributing condition, not the root cause. |

All sources agree on the root cause. Aztec Labs (primary): "it is possible to submit a row that is accepted by the proof, but that the settlement code never processes". BlockSec: "`num_txs` is not exposed as a public input". Rekt and Halborn say the same. Incident transaction (citation only, never queried): `0x074ec9317d8336db37e8c348fbdd7515573ff4088239c77ab429f522509aeeb1`, 2026-06-14 12:26 UTC, rollupIds 13277–13290.

## Evidence (paths, hashes, commands, exit codes, tool versions)

Sources (fetched 2026-11-18 UTC, `results/raw/AZ1/sources/`):

| source | URL | date | sha256 (raw HTML) |
|---|---|---|---|
| Aztec Labs incident report (primary) | https://aztec-labs.com/blog/aztec-connect-incident.html | 2026-06-15 | `a84935dc0f2d8646c22039fd1d0e289cfaa9c7cf01468335461dd2cc4ab6d912` |
| BlockSec weekly | https://blocksec.com/blog/web3-security-aztec-raydium-more | 2026-06-17 | `32abb2d7b0d1dc4c1f6ce07e56a41da9f7a29897f1729fe426c7a001d0d3e583` |
| Rekt | https://rekt.news/aztec-connect-rekt | 2026-06-18 | `8e1cc96ed2d08cde7885f04a2a91afdd0612a1c4c8321efadb24fda7a20149f7` |
| Halborn | https://www.halborn.com/blog/post/explained-the-aztec-connect-hack-june-2026 | 2026-06-23 | `a45a7cf1be5b287642dc9c80975e06c79acebbe2fbe22aadd9b4565692cb42eb` |
| Blockaid | https://blockaid.io/blog/219m-drained-on-aztec-how-blockaid-flagged-an-exploit-before-it-happened | — | `b23e5a7f1458d005bff636aa5cbd46c2edd38b56026a7df28b164ef09334f8d4` |
| Cointelegraph (SlowMist quote) | https://cointelegraph.com/news/aztec-exploited-21-million-previous-hack-slowmist | — | `38dde46102b6ae8ef98a055b19fb1ed8739a8c9868eb88c980bd91a783a48acd` |
| web3isgoinggreat | https://web3isgoinggreat.com/single/aztec-connect-exploit | — | `7595ae1209684c889249f234977a4232b3920534223e0b83a4c1055b287728d6` |
| SlowMist (Medium) | https://slowmist.medium.com/analysis-of-the-2-19-million-asset-theft-from-aztec-connect-d867c59b1fc6 | — | **HTTP 403, not obtained** (the stored file is the error page, `b2c36dae…`) |

Real-target tool runs: canonical run `bash prototypes/az1/tools_real.sh` → `results/raw/AZ1/az1-real-20261118T042002Z-1646017/` (guard, clone, checkout and Sourcify fetch all exit 0; correspondence `IDENTICAL` for V3 and Decoder; BindCheck and Slither results identical to the earlier hand runs in `results/raw/AZ1/tools-real/`). Commands:

- Hold-out guard: `python3 scripts/check_holdout.py AztecProtocol/aztec-connect AztecProtocol/aztec-connect-contracts AztecProtocol/aztec-packages` → ALLOWED, ALLOWED, FORBIDDEN (exit 1). aztec-packages was never opened.
- BindCheck: `./freeze.sh` → `92789fad12050a3058a21cc5c2326e7d41604ad5ade0f09f72a35789437e6c1a`. `python3 -m bindcheck_zk.cli analyze results/raw/AZ1/deployed-source/files --consumer src/core/processors/RollupProcessorV3.sol` → exit 0. The same command on the full checkout with `--consumer contracts/src/core/processors/RollupProcessorV3.sol` → exit 0.
- Slither 0.11.3 (crytic-compile 0.3.11), solc 0.8.10 (sha256 `c7effacf…6d89`), run on a copy outside the worktree. The worktree `foundry.toml` otherwise overrides the compiler. Command: `slither src/core/processors/RollupProcessorV3.sol --solc <solc0.8.10> --solc-remaps "<Sourcify remappings>" --solc-args "--optimize --optimize-runs 2000 --evm-version london" --json …` → exit 255 (results present), `success: true`.

Testbed: `bash prototypes/az1/run.sh` → exit 0, `steps=53 fail=0`. Canonical run on the clean committed tree (`ec688bb`, `workspace_dirty_files=0`): `results/raw/AZ1/az1-20261118T042012Z-1646945/`. It reproduces the first run (`az1-20261118T022518Z-1603188`, dirty tree), with the same state assertions and an identical detector summary. The run directory holds `steps.tsv`, `environment.txt` and `checksums.sha256` (27 files), plus per-step logs and receipts. Tools: circom 2.2.3 (sha256 `599552d8…cb7`, T0 pin), snarkjs 0.7.6, circomlib 2.0.5, circomlibjs 0.1.7 (root `package-lock.json` `63679f1e…0006`), solc 0.8.11 (`717c239f…cd4f`), anvil/cast 1.4.1-stable, node v24.19.0, Python 3.12.12. The circuit has 3,432 constraints, 12 private inputs and 2 public outputs.

## Results (tables; exact counts)

### Tool × target × verdict

| tool | target | result | reason |
|---|---|---|---|
| BindCheck freeze 2 | real V3 (verified source; also full checkout) | P1–P5 all `UNKNOWN`, grade E0, `NO_APPLICABLE_TRIPLE`; discovery 0 circuits / 0 consumers / 0 verifiers | The verifier is called through inline-assembly `staticcall` with the hand-built selector `0xac318c5d` (`RollupProcessorV3.sol:1079–1095`), so no verify call or consumer is recovered. The circuits are C++ (barretenberg), which has no frontend. Inline assembly is out of scope (contract §5.4). |
| Slither (default) | real V3 | 167 results, **none about the fault** | 36 assembly, 78 naming, 14 divide-before-multiply (6 in `decodeProof` on `numTxs` arithmetic: rounding, not binding), 3 uninitialized-state (proxy storage), 1 arbitrary-send-erc20, 1 incorrect-exp, 1 tautology, 1 reentrancy-no-eth, among others. No detector models proof coverage. |
| D1 `R-EXTENT` | real V3 | not run: `UNKNOWN` (no producer frontend for C++; consumer extent is not a verifier word) | See the interface row below. |
| D1 `R-EXTENT` interface | the case's shape (ASSUMED facts) | `covered: true`, `status: EXACT`, no warning | `static_analyzer_v1.py:697`: `producer_kind == "always"` ⇒ covered. The rule checks *consumer reliance ⊆ producer binding* (Payy direction). Aztec is the converse, *producer-attested obligations ⊄ consumer discharge*, which the interface cannot express. Step 74 of the run records this. |
| BindCheck freeze 2 | testbed **faulty** | P1 `UNKNOWN` `PROTECTED_EFFECT_NOT_RECOVERED`; P2/P3 same; P4 `VERIFIED_WITHIN_SCOPE`; P5 `VERIFIED_WITHIN_SCOPE` (`PUBLIC_INPUT_COUNT_AND_ORDER_MATCH`); discovery 1/1/1/1 | The triple is recovered. The settlement effect, a decrement of `userPendingDeposits`, is not a recognised protected effect (the mapping heuristic keys on names containing balance/claim/mint), and P1 has no loop-extent model. P5 is correct for what it checks. **No detection.** Not renamed to fit the detector. |
| BindCheck freeze 2 | testbed **fixed** | identical to faulty (unhinted and explicit) | Does not separate fault from fix. |
| Slither (default) | testbed faulty / fixed | 54 results each, the same multiset of checks | `calls-loop`/`costly-loop` on `processBatch`, plus 3 `incorrect-return` and other items, all in the generated verifier. **No detection.** |

### Testbed (owned, synthetic, Anvil chain-id 31337)

| step | consumer | `numRealRows` | observed |
|---|---|---:|---|
| snarkjs: honest and fault proofs verify; tampered public signal rejected; no-op row carrying an amount is unsatisfiable | — | — | exit 0, 0, 1, 1 (as expected) |
| tampered `creditTotal` | faulty | 2 | receipt status 0; reason `proof` |
| honest `[dep(alice,100), dep(bob,50), noop, noop]` | faulty | 2 | status 1; credit 150, backing 150, gap 0 |
| fault `[noop, dep(carol,1000), noop, noop]`, carol never deposited, carol submits | faulty | 1 | **status 1; credit 1150, backing 150, gap 1000, pool tokens 150** |
| same fault proof | fixed | 1 | status 0; reason `unsettled row`; state unchanged |
| same fault proof | fixed | 2 | status 0; reason panic 0x11 (carol has no pending deposit) |
| honest | fixed | 2 | status 1; gap 0 |

This is E4 for the testbed: a real proof is accepted by the unchanged verifier and the faulty consumer, leaving an undischarged required obligation on state (coverage violation, contract §4.2). It is a synthetic development fixture, not a historical replay. No withdrawal or payout step was built.

## Extent binding (pattern definition)

**Definition.** A proof covers a sequence `x[0..L)`: its public inputs, or a commitment in them, fix every element, and its effects or state transition depend on all of them. The consumer performs per-element effects or obligation discharges only on a sub-range `[lo, hi)` whose bounds come from inputs the proof does not fix. Extent binding fails when some proved element outside `[lo, hi)` carries a non-neutral effect, or when the consumer relies on an element outside the proved range. There are two directions:

- **(a) Reliance beyond binding** (Payy `agg_agg` tail, `R-EXTENT`): the consumer relies on `x[i]` for `i < messages_length`, but the producer binds `x[i]` only for `i < active_messages_count`. Uncovered region: `active ≤ i < length`.
- **(b) Binding beyond discharge** (Aztec Connect): the producer binds and *applies* `x[i]` for all `i < L` (32-row chunk), while the consumer discharges obligations only for `i < numRealTxs`, and `numRealTxs` is not a public input. Undischarged region: `numRealTxs ≤ i < L` with non-no-op rows.

**Mapping to P1–P5.** This is closest to P1 (an unbound effect extent: a quantity of the effect, here *which rows*, is caller-selectable). P1 in freeze 2 checks only recipient/amount/identity roles of individual effect calls, so it covers neither direction. (b) is a coverage (§4.2) failure rather than an authorization failure.

**Facts a checker needs:** (1) the consumer loop bound and its provenance: public input, derived from a public input, or raw calldata; (2) public-input coverage per element: which elements the proof or commitment fixes, and over what extent (here, the decoder hash covers whole chunks); (3) circuit padding/no-op semantics: whether elements past the true count are forced neutral (here the inner circuit zeroes rows `≥ num_txs`, but that `num_txs` is private and need not equal the consumer's count); (4) which per-element effects are required obligations (deposit consumption). Deciding (b) soundly **needs the circuit** for (3): consumer facts alone give a candidate (an unbound loop bound below a committed length), and the circuit decides whether the skipped elements are provably neutral. The fixed testbed shows a consumer-only repair: requiring skipped rows to be proved no-ops makes (3) a consumer-checked fact.

## Motivating example (≤150 words)

In June 2026, a deprecated, immutable zk-rollup contract lost about $2.1M without any cryptographic failure. Each rollup proof committed to a fixed-size chunk of transaction rows, and the verifier accepted it. The settlement contract, however, processed only a prefix of those rows, whose length was read from calldata and was not fixed by the proof. A row inside the proved chunk but outside that prefix could change the proved rollup state, for example crediting a deposit, while its matching on-chain obligation, collecting the deposited funds, never ran. The proof and the contract disagreed about which rows existed. The verifier was sound and the contract checked the proof, yet the contract acted on a value the proof never bound. We ask whether a checker can find such *extent-binding* gaps from the circuit, the public-input decoding and the settlement loop. A same-shape fault reproduced in a synthetic testbed was missed by both BindCheck and Slither.

## Assumptions and limitations

- Deployed-code correspondence rests on Sourcify's verified-source record. I did not compare runtime bytecode (no chain RPC).
- The circuit lines come from the pinned C++ source and are not executed. That the deployed verification key matches this circuit is ASSUMED.
- The testbed elides the rollup's chunking, Merkle state, signatures and fees. It keeps the essential shape: commitment over all N rows, a calldata count, and two-stage deposits. N = 4, with a toy setup using fixed entropy (insecure by design).
- The fix is consumer-only: skipped rows must be proved no-ops. The alternative fix, binding `k` into the public inputs, was not built.
- The R-EXTENT result is an interface-level call on ASSUMED facts, not extraction. R-EXTENT was not run on the testbed because its producer frontend is Noir/ACIR only.
- Loss figures differ between sources ($2.1M–$2.28M), and so do deprecation dates.

- `AGENTS.md` requires a `docs/project-status.md` checkpoint, but the AZ1 ownership table lists only `prototypes/az1/` and `reports/AZ1/`. I followed `AGENTS.md`: I changed the AZ1 node from `[NEXT]` to `[DONE]` and appended one log row, without touching other rows. The reviewer may drop that hunk at merge.

## Failed approaches / surprises

- Slither failed twice on the real contract. crytic-compile picked up the worktree `foundry.toml` and tried to download solc (HTTP 403). The fix was to run on a copy outside the worktree with a non-versioned solc symlink.
- `git log -S` over the blobless clone was too slow, so I stopped it and used the GitHub API.
- BlockSec notes that the inner circuit *does* force `num_txs` to equal the real-row count. The gap is purely that this value is private and unrelated to the calldata count.
- SlowMist (Medium) and The Defiant returned 403.

## Held-out hygiene statement

Repositories opened: `AztecProtocol/aztec-connect` (guard: ALLOWED). Sourcify's record for one public implementation address was also read (source files only). `AztecProtocol/aztec-packages` (FORBIDDEN) was not opened, cloned or read; Aztec's bb binaries from T0 were not used. No other third-party repository was opened. No live system was contacted, and no transaction was sent outside the local Anvil.

## Recommended next task

Implement direction (b) as a candidate rule, "a consumer loop bound not derived from verifier public inputs, iterating over a proof-committed array", in a branch off freeze 2. Completion criterion: it warns on `SettlementFaulty` and stays silent on `SettlementFixed`, with the 38 freeze-2 tests still passing. Evaluate it only on development cases, since this fixture is now exposed.
