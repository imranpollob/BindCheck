# Circom/Groth16 + Solidity pivot feasibility scan

**Cutoff:** 2026-11-03

**Repository base:** `4c51de6b4faf62c4c729789858ec972f3b4d46d0`

**Disposition:** **NO-GO for a full pivot; retain only as a bounded follow-up
pilot.**

## Executive result

The literature gap is credible, and a 50-project source corpus can be assembled,
but this scan did not establish the empirical or validation base needed for a
full pivot:

- the requested 2025–2026 venue sweep found **no qualifying paper** that joins
  circuit constraints to the consuming Solidity contract's decoding, state and
  effects;
- no published comprehensive scan of **deployed** degenerate Groth16
  verification keys was found;
- 50 public projects were pinned, but only 8 circuit/verifier/consumer triples
  were sufficiently paired for these cheap checks; 41 remain pairing-UNKNOWN
  and one is an explicit placeholder;
- checks A, B and C produced **0 adjudicated hits** and **0 E1 warnings**;
- therefore there were **0 exploit-eligible findings, 0 E3 proofs and 0 E4
  local consumer replays**; and
- historical screening recognizes the exact nullifier-field-alias predicate in
  3/3 in-scope reports, but no historical vulnerable revision was rebuilt or
  replayed. This is E1 mechanism evidence, not end-to-end recall.

No transaction, chain RPC, fork, live deployment, disclosure or maintainer
contact occurred. No likely real vulnerability was found, so the requested
private-stop condition was not triggered. Every project verdict remains
`UNKNOWN`; a clean cheap screen is not evidence of safety.

## 1. Literature completion

The full venue-by-venue result, inclusion rule, close calls and exact queries
are in [LITERATURE.md](LITERATURE.md).

### Result

| Question | Result at cutoff |
| --- | --- |
| Joint circuit + Solidity-consumer analysis at S&P, USENIX Security, CCS, NDSS, FC, ICSE or FSE in 2025–2026 | **none found** |
| Closest requested-window systems | CCS 2025 Circuzz and S&P 2026 zkFuzz; both stop at circuit/proof-pipeline analysis |
| Closest cross-layer framing | USENIX Security 2024 SNARK vulnerability SoK; outside the requested years and not a joint analyzer |
| Published comprehensive scan of deployed Groth16 keys after Veil/FoomCash | **none found** |
| Closest key-scan evidence | public Veil/FoomCash incident reproductions; a 2026 `zkjac` source scan reporting 20/20 insecure committed Zeto verifier sources, conditional on deployment |

The negative result is a bounded title/abstract/full-text follow-up sweep, not
proof of absence. FC 2026 has weaker coverage because a complete DBLP
post-proceedings table of contents was not available at the cutoff.

## 2. Candidate acquisition and freeze

The seed ledger contains 85 entries and 83 unique repository/provenance pairs.
The acquisition pass fetched 82; one failed. The broad source scanner returned
6 heuristic triples, 53 unresolved pairings, 23 missing-layer rows and one
fetch failure. Fifty rows with public circuit, verifier and consumer paths were
then frozen in [candidate-set.csv](candidate-set.csv).

GitHub discovery used these query forms, followed by repository-local source
validation:

```text
snarkjs groth16 verifier verifyProof
component main verifyProof
Groth16Verifier verifyProof circom
.circom Solidity verifier
```

Known ecosystem projects and `0xPARC/zk-bug-tracker`/ZK-bug references were
added for recall. The durable input is [candidate-seeds.tsv](candidate-seeds.tsv);
[fetch_candidates.sh](fetch_candidates.sh) records the source-only clone
procedure. All 50 frozen commits are 40-hex Git object IDs. The corpus records
only public metadata and source/committed build artifacts; it performs no
transaction or deployment lookup.

### Corpus accounting

| Property | Count |
| --- | ---: |
| Frozen projects | 50 |
| Manual pair + committed R1CS/SYM | 1 |
| Manual source pair | 1 |
| Heuristic source pairs | 6 |
| Pairing unresolved | 41 |
| Explicit placeholder, excluded from findings | 1 |
| Consumer/verifier roots accepted by local `solc` AST pass | 13 |
| AST compile/import/version failure, recorded fail-closed | 37 |
| E0 / E1 / E2 / E3 / E4 | 50 / 0 / 0 / 0 / 0 |
| Verdict `UNKNOWN` | 50 |

`solc` failures are primarily missing repository dependencies/import remappings
or exact pragma/version differences. They were not hidden by text-only
substitution. Successful compiler runs extract verifier and consumer public
input arities, proof calls, replay-map accesses/writes and effect calls into
the ignored raw AST ledger; compact facts are copied into the frozen CSV.

## 3. Cheap checks

[scan_candidates.py](scan_candidates.py) implements the source pass and
[solc_ast_probe.py](solc_ast_probe.py) implements the compiler-AST pass.
[test_scan_candidates.py](test_scan_candidates.py) contains deterministic
positive regressions for all three checks, the nullifier alias case, AST fact
extraction and Circom compile-time branch pruning.

| Check | Implemented predicate | Paired rows screened | Warnings after adjudication | Likely real hits |
| --- | --- | ---: | ---: | ---: |
| A — redirect/front-run | consumer proof input used as recipient, receiver, amount, value, fee, relayer, target or destination while the corresponding public circuit signal has no constraint reference or only witness assignment | 8 | 0 | 0 |
| B — replay/nullifier | nullifier-like proof input without both spent read and write, or storage/comparison under a verifier for which a `< r` canonical-input guard is not detected | 8 | 0 | 0 |
| C — order/count | disagreement among Circom `main` public outputs/inputs, generated-verifier fixed arity and the consumer `verifyProof` vector; name-based order disagreement is a secondary warning | 8 | 0 | 0 |

The source pairing threshold is deliberately conservative. An early C warning
on `zkemail/proof-of-twitter` was rejected and the parser repaired: the nine
`fromEmailAddrPacks` outputs occur under `if (exposeFrom)`, while `main`
instantiates `exposeFrom = 0`. The effective interface is
`[pubkeyHash, twitterUsername, address]`, matching the three-input verifier and
consumer. A cross-pair between an ECDSA submodule and Semaphore consumer in
`zk-poll` was likewise rejected by the pairing gate. Neither is counted as a
hit or false negative.

### Higher-fidelity negative observation

The `0xbow-io/privacy-pools-core` withdrawal path was the one row with committed
R1CS/SYM artifacts suitable for a stronger local check:

- `snarkjs r1cs info` reports BN128, 36,901 wires, 36,832 constraints, 72
  private inputs, 6 public inputs and 2 outputs;
- the eight `.sym` public positions are `newCommitmentHash`,
  `existingNullifierHash`, `withdrawnValue`, `stateRoot`, `stateTreeDepth`,
  `ASPRoot`, `ASPTreeDepth`, `context`;
- `ProofLib.sol` uses that order, and `WithdrawalVerifier.sol` has fixed arity
  eight with a `< r` check for every public input; and
- `PrivacyPool.withdraw` verifies, spends the existing nullifier, inserts the
  new commitment, binds the withdrawal structure through `context`, and pays
  the proof's withdrawn value to the withdrawal processooor.

This is a bounded **no-warning observation**, still E0/`UNKNOWN`, not
`VERIFIED_WITHIN_SCOPE`.

## 4. Historical recall

The complete case ledger is [historical-recall.csv](historical-recall.csv).

| Recall slice | Recognized / eligible | Highest grade | Meaning |
| --- | ---: | --- | --- |
| Check-B nullifier field aliases: Semaphore issue 16, zkDrops, Nightfall | 3 / 3 | E1 | the source reports/fixes match the rule predicate |
| Full pinned historical build and automatic warning | 0 / 3 | E0 | old vulnerable revisions and exact toolchains were not reconstructed |
| Real matching proof under vulnerable verifier | 0 / 3 | E0 | no E3 attempt |
| Unchanged vulnerable consumer with unauthorized repeated effect | 0 / 3 | E0 | no E4 attempt |
| Check-A exact historical positives in the bounded tracker | 0 / 0 | — | Tornado/Semaphore examples are hardened examples, not positive incidents |
| Check-C exact historical positives in the bounded tracker | 0 / 0 | — | none identified |

Thus **3/3 is predicate/mechanism recall only**, established by reapplying the
rule to primary issue/fix descriptions. It must not be reported as tool recall
or end-to-end validation. StealthDrop and Aztec nondeterministic-nullifier bugs
are declared out of scope: they require uniqueness/determinism reasoning, not
missing spent state or field canonicality. Semaphore issue 90 and zk-kit issue
23 are fail-closed range/domain bugs, not replay-key bugs.

## 5. Exploit attempts and evidence grades

The exploit gate is conditional on an adjudicated hit. There were no such
hits, so the required attempt matrix is empty:

| Stage | Eligible hits | Attempts | Successes |
| --- | ---: | ---: | ---: |
| Attacker-chosen `snarkjs` proof (E3) | 0 | 0 | 0 |
| Foundry/Anvil deploy and unchanged-consumer replay (E4) | 0 | 0 | 0 |

Local availability was confirmed for `snarkjs 0.7.6`, Foundry/Anvil 1.4.1 and
`solc 0.8.30`; standalone `circom`, Circomspect and ZKAP commands were not
installed. The one committed R1CS/SYM bundle was inspected with `snarkjs`; the
remaining circuit facts therefore stay source-level. No exploit was attempted
against an unresolved pairing or a no-warning row, because that would
manufacture a target rather than validate a reported mismatch.

## 6. Per-candidate grade and verdict

This compact table includes every frozen candidate. The authoritative ledger
with commit, circuit, verifier, consumer, recovered public signals, all three
check results, AST facts, notes and provenance is
[candidate-set.csv](candidate-set.csv).

| # | Project | Pair status | Solidity AST | Grade | Verdict |
| ---: | --- | --- | --- | --- | --- |
| 1 | `0xbow-io/privacy-pools-core` | manual-pair+r1cs | compile-error | E0 | UNKNOWN |
| 2 | `semaphore-protocol/semaphore` | unresolved | compile-error | E0 | UNKNOWN |
| 3 | `privacy-scaling-explorations/maci` | unresolved | compile-error | E0 | UNKNOWN |
| 4 | `Unirep/Unirep` | unresolved | compile-error | E0 | UNKNOWN |
| 5 | `dfdao/arena` | unresolved | ast | E0 | UNKNOWN |
| 6 | `nocturne-xyz/protocol` | heuristic-pair | ast | E0 | UNKNOWN |
| 7 | `anon-aadhaar/anon-aadhaar` | unresolved | ast | E0 | UNKNOWN |
| 8 | `zkp2p/zk-p2p` | heuristic-pair | compile-error | E0 | UNKNOWN |
| 9 | `zk-poll/zk-poll` | unresolved | compile-error | E0 | UNKNOWN |
| 10 | `0xFableOrg/0xFable` | unresolved | compile-error | E0 | UNKNOWN |
| 11 | `NebraZKP/upa` | unresolved | compile-error | E0 | UNKNOWN |
| 12 | `NethermindEth/spsc` | unresolved | ast | E0 | UNKNOWN |
| 13 | `weavedb/zkjson` | unresolved | ast | E0 | UNKNOWN |
| 14 | `RippnerLabs/meridian-link` | unresolved | compile-error | E0 | UNKNOWN |
| 15 | `ava-labs/EncryptedERC` | unresolved | compile-error | E0 | UNKNOWN |
| 16 | `poa-box/POP` | unresolved | compile-error | E0 | UNKNOWN |
| 17 | `zeroauth-dev/ZeroAuth` | unresolved | compile-error | E0 | UNKNOWN |
| 18 | `WTCHAI/zkbiown` | heuristic-pair | compile-error | E0 | UNKNOWN |
| 19 | `raylsnetwork/uniswap-incubator` | unresolved | compile-error | E0 | UNKNOWN |
| 20 | `raycashxyz/erc-7984-single-tx-unwrap` | unresolved | compile-error | E0 | UNKNOWN |
| 21 | `Chronos-Vault/chronos-vault-security` | unresolved | compile-error | E0 | UNKNOWN |
| 22 | `Chronos-Vault/chronos-vault-contracts` | unresolved | compile-error | E0 | UNKNOWN |
| 23 | `QuantSingularity/Fluxion` | unresolved | compile-error | E0 | UNKNOWN |
| 24 | `ramakrishnanhulk20/Z-Tor` | unresolved | compile-error | E0 | UNKNOWN |
| 25 | `Chidubemkingsley/Shadow-Credit-Network` | heuristic-pair | compile-error | E0 | UNKNOWN |
| 26 | `JunaidCD/Credence` | unresolved | ast | E0 | UNKNOWN |
| 27 | `Nitya-003/CropChain` | unresolved | ast | E0 | UNKNOWN |
| 28 | `rudrakumar07/zkfinance` | unresolved | ast | E0 | UNKNOWN |
| 29 | `Veilpayapp/VEILPAY-APP` | heuristic-pair | compile-error | E0 | UNKNOWN |
| 30 | `ethpanda-org/ETHShanghai-2025` | unresolved | compile-error | E0 | UNKNOWN |
| 31 | `emmaguo13/zk-blind` | unresolved | compile-error | E0 | UNKNOWN |
| 32 | `a00012025/email2ether` | heuristic-pair | compile-error | E0 | UNKNOWN |
| 33 | `social-tw/social-tw-website` | unresolved | compile-error | E0 | UNKNOWN |
| 34 | `avitenzer/zk_voting` | unresolved | ast | E0 | UNKNOWN |
| 35 | `sambitsargam/ShadowSats` | unresolved | compile-error | E0 | UNKNOWN |
| 36 | `partik03/aieth` | unresolved | compile-error | E0 | UNKNOWN |
| 37 | `Mahadev-05/BlockChain` | unresolved | ast | E0 | UNKNOWN |
| 38 | `KanishJebaMathewM/Truxify` | unresolved | compile-error | E0 | UNKNOWN |
| 39 | `Servesh21/RacePass` | unresolved | ast | E0 | UNKNOWN |
| 40 | `Blacksaviour/Undertow` | unresolved | compile-error | E0 | UNKNOWN |
| 41 | `hollow-leaf/tobi` | unresolved | compile-error | E0 | UNKNOWN |
| 42 | `hollow-leaf/easyeigen` | unresolved | compile-error | E0 | UNKNOWN |
| 43 | `metacraft-labs/DendrETH` | unresolved | ast | E0 | UNKNOWN |
| 44 | `zkemail/proof-of-twitter` | manual-source-pair | compile-error | E0 | UNKNOWN |
| 45 | `MynaWallet/monorepo` | unresolved | compile-error | E0 | UNKNOWN |
| 46 | `Cipher-Protocol/cipher-core` | unresolved | compile-error | E0 | UNKNOWN |
| 47 | `RayHuang880301/zkUTXO-core` | unresolved | compile-error | E0 | UNKNOWN |
| 48 | `SovereignWave/qwer` | placeholder-excluded | compile-error | E0 | UNKNOWN |
| 49 | `KELLERBABG/Planetary-Entropy-Mining` | unresolved | ast | E0 | UNKNOWN |
| 50 | `Lucklyric/tallymesh` | unresolved | compile-error | E0 | UNKNOWN |

## 7. Reproduction

The source scan and frozen-ledger construction are deterministic once the
pinned repositories exist under the ignored `feasibility/work/repos/` tree:

```sh
python3 feasibility/scan_candidates.py \
  --json feasibility/raw/candidates-v5.json \
  --csv feasibility/candidates.csv
python3 feasibility/solc_ast_probe.py
python3 feasibility/build_candidate_set.py
python3 -m unittest feasibility/test_scan_candidates.py -v
```

The final regression result is 4/4 passing. The frozen ledger has 50 unique
repositories, 50 40-hex commits, 13 AST successes, 37 explicit compiler
failures, 50 E0 grades and 50 `UNKNOWN` verdicts.

## 8. Recommendation

**NO-GO for the proposed full pivot.** The novelty surface is plausible, but
the present corpus has insufficient pair resolution and reproducibility, the
cheap checks found no candidate to validate, and the scan supplies no E3/E4
evidence. Pivoting now would exchange a difficult established program for a
new program whose dominant cost is artifact/toolchain recovery rather than the
three analyses themselves.

A narrow follow-up pilot is defensible only if it is gated prospectively by:

1. at least 10 independent projects with exact circuit/verifier/consumer
   pairing, reproducible R1CS/SYM and matching proving artifacts;
2. pinned historical reconstruction of at least two in-scope bugs through E4,
   plus matching fixed controls;
3. at least 80% automatic pair resolution on the frozen pilot corpus; and
4. one non-historical E3/E4 result or a predeclared stop after the zero-hit
   screen, with the same private handling and no-contact rule.

The deployed-degenerate-key census should remain a separate project: it needs
chain selection, bytecode/key extraction, deduplication and an explicit
on-chain data protocol, none of which follows from this metadata/source-only
scan.
