# Dataset and DEV joint-analysis report

Date: 2026-11-03  
Workspace revision at protocol freeze: `f59e62cb00b1cc3583d7a38c04c53956c44b98f9`  
Branch: `zk-integration`  
Status: bounded task complete; no commit made

## Private stop notice — do not publish the P4 deployment ledger

The passive Sourcify/RPC census found **43 exact-runtime-matched deployed
verifier rows (43 unique chain/address pairs; 37 runtime hashes)** whose
runtime bytecode contains all four default BN254 G2 generator coordinates at
least twice. This is the bytecode signature expected when generated Groth16
verifiers use `gamma == delta == default G2`, the Veil/FoomCash-class failure.
The rows are on Ethereum (13), Optimism (7), Base (22), and Polygon (1).

This is E1/`UNKNOWN`, not an exploitation claim. All 43 verifier-address
native-balance reads at the recorded block tags returned zero.
The verifier is normally not the fund-holding contract: **zero consumer links
were source-confirmed, and consumer TVL is therefore `UNKNOWN`**. No positive
verifier-native balance was observed, but that does not establish that no
consumer is funded.

Per the stop rule, work stopped at passive bytecode and balance reads. No proof
was submitted, no verifier was called, no transaction was broadcast, no
consumer was tested, and no maintainer was contacted. The address-level local
ledger is [`onchain-census.csv`](onchain-census.csv); it should remain private
until the advisor decides how correspondence, consumer tracing, and
notification will be handled. `funded_vulnerable_consumer_instances = 0` in
the summary means **none established**, not none exist.

## 1. Scope and evidence semantics

This task produced three datasets and one DEV-only joint analysis:

- A1 inventories source candidates. Newly collected repositories are EVAL and
  were not passed to a vulnerability analyzer.
- A2 performs only public Sourcify export and JSON-RPC reads.
- A3 inventories public historical/audit positives; it does not yet measure
  recall.
- Track B runs only on 24 synthetic development controls and three declared
  DEV cases.

The report uses only `VIOLATION`, `VERIFIED_WITHIN_SCOPE`, and `UNKNOWN` as
research verdicts. Inventory labels, bytecode heuristics, build failures, and
unavailable RPC results are not safety evidence.

## 2. A1 source corpus

### Fixed collection protocol

[`source-queries.json`](source-queries.json) freezes 14 GitHub code queries,
their page budgets, three awesome-list URLs, and six historical DEV revisions.
The queries cover Circom and Noir entry points; `verifyProof`/`verifyTx`;
Groth16, PLONK, Ultra, and Honk verifier names; Tornado, Semaphore, and zkDrops
fork terms; and ETHGlobal/Devfolio terms. [`collect_source_corpus.py`](collect_source_corpus.py)
records the raw query result pages, GraphQL metadata, exact default-branch
commit, README hash, path evidence, fork ancestry, and exact shared circuit
blob hashes. [`label_dev_maturity.py`](label_dev_maturity.py) applies the same
recorded maturity heuristic to pinned DEV revisions.

The split was fixed before any Track B implementation:

- DEV: the existing feasibility 50 plus six vulnerable/fixed historical
  revisions.
- EVAL: every newly collected repository.

`eval_analyzer_runs` is zero in both the corpus summary and Track B output.

### Counts per stage

| Stage | Rows/repos | Families | Meaning |
| --- | ---: | ---: | --- |
| Final pinned ledger | 897 rows / 890 unique repositories | 774 | Multiple exact revisions remain separate rows. |
| DEV | 56 rows / 52 repositories | 52 | 50 existing rows plus six historical revisions; some repositories repeat. |
| EVAL inventory | 841 rows / 838 repositories | 722 | Metadata/path inventory only. |
| EVAL duplicate-family disposition | 119 rows | included above | Non-canonical member of a fork or exact shared-circuit-blob family. |
| EVAL in-scope by path evidence | 7 rows | not analyzed | Circuit plus verifier plus consumer paths recovered. |
| EVAL no consumer | 69 rows | not analyzed | Circuit and verifier, no consumer path recovered. |
| EVAL no verifier | 638 rows | not analyzed | Circuit candidate, no verifier path recovered. |
| EVAL unavailable | 8 rows | not analyzed | Repository/default-branch metadata unavailable. |

Every candidate has a disposition; `dup`, `no consumer`, `no verifier`, and
`unavailable` remain in the ledger rather than being silently dropped.

Family IDs are based on GitHub fork ancestry where available, otherwise exact
shared circuit blob SHA, otherwise repository identity. This is a conservative
family proxy, not a clone-detector completeness claim.

### Maturity strata

| Maturity label | All rows | DEV | EVAL |
| --- | ---: | ---: | ---: |
| `deployed-address-in-docs` | 78 | 15 | 63 |
| `audited-production` | 150 | 14 | 136 |
| `hackathon-student` | 54 | 4 | 50 |
| `unclassified` | 615 | 23 | 592 |

These are automated metadata/README strata. `deployed-address-in-docs` means a
nonzero address and deployment language were found; it is not source/runtime
correspondence. `audited-production` is a text heuristic and requires sampled
human validation before measurement use.

The authoritative row ledger is [`source-corpus.csv`](source-corpus.csv)
(SHA-256 `7031b6a7302220163e9818b0065bef3a6e964f7085da147619479dd8f4466309`),
with aggregate checks in [`source-corpus-summary.json`](source-corpus-summary.json).

## 3. A2 passive on-chain census

### Selection and coverage

[`census_sourcify.py`](census_sourcify.py) uses the official Sourcify v2
Parquet export rather than crawling the contract API. It joins verifier-like
ABI signatures to verifier-named compilations, then retains deployments for
which both `runtime_match` and `runtime_metadata_match` are true. The fixed
chain list is Ethereum, Optimism, Polygon, zkSync Era, Base, Arbitrum One, and
Linea. RPC operations are limited to `eth_getCode` and `eth_getBalance`.

| Reduction | Count |
| --- | ---: |
| Verifier-like ABI signatures | 389 |
| Compilation IDs reached through signatures | 4,923 |
| Verifier-named compiled contracts | 4,189 |
| Exact-runtime deployment rows | 1,049 |
| Unique chain/address deployments | 1,027 |
| Unique runtime hashes | 561 |
| Deployment rows with RPC runtime code | 1,049 |
| Runtime-code reads unavailable | 0 |

| Chain | Exact deployment rows | Unique addresses |
| --- | ---: | ---: |
| Ethereum | 224 | 223 |
| Optimism | 148 | 147 |
| Polygon | 119 | 117 |
| zkSync Era | 0 | 0 |
| Base | 272 | 268 |
| Arbitrum One | 221 | 212 |
| Linea | 65 | 60 |

### P4 results

| Signal | Deployment rows | Interpretation |
| --- | ---: | --- |
| Default G2 appears twice for all four coordinates | 43 (37 runtime hashes) | Strong `gamma == delta == default G2` bytecode signature; E1/`UNKNOWN`; private stop notice applies. |
| Scalar-field modulus absent as PUSH32 | 228 | Missing-`< r` heuristic only; optimizer/template variants can create false results. |
| Repeated non-G2 large PUSH32 coordinate pair | 158 | Duplicate-IC triage heuristic only; not a source-confirmed duplicate-IC result. |
| Positive native balance at a flagged verifier address | 0 observed | Verifier balance is not consumer TVL; all 260 heuristic-flag balance reads completed at pinned block tags. |
| Source-confirmed consuming contracts | 0 | Consumer balances/TVL remain `UNKNOWN`. |

The default-G2 signature should be treated separately from the two weaker
heuristics. The ledger deliberately retains `UNKNOWN` for every row; no
absence-of-warning row is declared safe. See
[`onchain-census-summary.json`](onchain-census-summary.json) for machine-readable
counts and limitations.

### Sixteen source leads and SovereignWave

The prior DEV source census contains 16 default-key source files across eight
repositories: 0xFable (3), Meridian Link (3), SovereignWave (1), zk_voting
(1), zk-flex (1), DendrETH (1), zk-poll (2), and zk-p2p (4).
[`locate_p4_leads.py`](locate_p4_leads.py) records 14 address references across
six source-lead rows, but confirms **zero** source/runtime correspondences.

SovereignWave/qwer at
`d588661d8e803000c1390a65911c7f0e805ec69d` remains `UNKNOWN`: its source has
the default-key signature and no detected public-input guard, but no deployment
reference was found in the fixed evidence paths.

Meridian's committed Sepolia address book explicitly names a verifier,
bridge, and token. Passive reads found the default-G2-twice bytecode signature,
zero native balance at both verifier and bridge, and a nonzero test-token
balance at the bridge. It is a testnet candidate with unknown source/runtime
correspondence and no inferred market value, not a production-funds finding.
Details are in [`p4-deployment-reads.csv`](p4-deployment-reads.csv).

## 4. A3 recall set

The recall ledger contains 40 public cases: 20 strict integration cases and 20
broader integration-or-execution-semantics candidates extracted from the
pinned zkSecurity `zkbugs` snapshot. Thirty-one vulnerable commits and 28 fixed
commits resolve through GitHub. Non-git report references, acknowledged/unfixed
issues, and cases without a public pin remain explicit.

| Stratum | Cases | Vulnerable commit resolved | Fixed commit resolved | Recall run |
| --- | ---: | ---: | ---: | ---: |
| Strict integration | 20 | 16 | 12 | 0 |
| Integration/execution-semantics candidates | 20 | 15 | 16 | 0 |
| Total | 40 | 31 | 28 | 0 |

Strict integration cases:

| Case | Pattern | Vulnerable/fixed status |
| --- | --- | --- |
| `semaphore-nullifier-field-alias` | replay-key field alias | resolved / resolved |
| `zkdrops-nullifier-field-alias` | replay-key field alias | resolved / resolved |
| `nightfall-nullifier-field-alias` | replay-key field alias | not publicly pinned / not publicly pinned |
| `payy-message-tail` | public message extent mismatch | resolved / resolved |
| `foomcash-default-g2-key` | unrandomized/default Groth16 key | not publicly pinned / not publicly pinned |
| `veilcash-default-g2-key` | unrandomized/default Groth16 key | not publicly pinned / not publicly pinned |
| `zeto-unrandomized-setup` | unrandomized phase-2 key | not publicly pinned / not publicly pinned |
| `zkemail-zellic-skipped-subject-prefix` | unproven tail changes authorized subject | resolved / resolved |
| `zkemail-zellic-wrong-public-input-field` | q-vs-r replay-key alias | resolved / resolved |
| `zkemail-zellic-stale-zk-regex-artifact` | stale circuit generation artifact | resolved / resolved |
| `zkemail-zellic-last-timestamp-zero` | accepted proof resets freshness state | resolved / resolved |
| `zkemail-zellic-nine-digit-timestamp` | circuit/contract timestamp semantics | resolved / resolved |
| `zkemail-zellic-overlapping-masks` | masked-subject semantics | resolved / resolved |
| `semaphore-audit-zero-leaf-field` | contract value outside SNARK field | resolved / no public fix pin |
| `semaphore-audit-group-id-field` | external nullifier rejected by verifier | resolved / no public fix pin |
| `semaphore-audit-root-history-collision` | root state missing group context | resolved / resolved |
| `semaphore-audit-unbound-verification-key` | deployed key not checked against circuit | resolved / no public fix pin |
| `zkemail-matterlabs-guardian-repeat` | nullifier scope misses guardian uniqueness | resolved / resolved |
| `zkemail-matterlabs-cross-chain-replay` | missing chain/domain binding | resolved / acknowledged, no fix pin |
| `zkemail-matterlabs-proof-coordinate-range` | proof coordinate field validation | resolved / resolved |

The other 20 cases and exact source links are row-complete in
[`recall-set.csv`](recall-set.csv). They are retained as a distinct candidate
stratum because author review has not yet established that every one is a
contract-integration case rather than a producer/execution-semantics case.
`recall_executed = 0`: this task constructs the set and does not claim a recall
rate. All rows therefore remain E0/`UNKNOWN`.

## 5. Track B — DEV-only joint analysis

### Prospective control freeze

[`track-b-expected.json`](track-b-expected.json) declared 24 control outcomes
and three DEV outcomes before implementation. Its SHA-256 is
`bc993a9eaa5ad0d426b88b98b487a681a58a99a42e95cdf027df31418a8e28b9`.
The raw freeze record at
`results/raw/dataset-track-b/protocol-freeze-20261103T203130Z-74143/`
records `implementation_present=false`, `eval_analyzer_runs=0`, and HEAD
`f59e62c...`.

The frozen rule treats an effect value as bound only if it is directly in the
verifier vector, is `msg.sender` for a recipient, or passes all commitment
conditions: a public commitment, a matching local recomputation/guard, matching
algorithm/domain/order, and compiled-circuit support connecting the effect
signal to that public commitment.

Control composition and result:

| Expected P1 roles | Controls | Observed matches |
| --- | ---: | ---: |
| none | 11 | 11 |
| recipient | 8 | 8 |
| amount | 2 | 2 |
| amount + recipient | 3 | 3 |
| **Total** | **24** | **24** |

These are development decision-rule controls, not independent evaluation.

### SPSC false-positive adjudication

Project: `NethermindEth/spsc@6d07155ecf295e6d68936bf424557621d0c66456`.

The Solidity-only screen still warns on `recipient`, as intended before joint
analysis, but its array-literal recovery now correctly finds
`publicAmountOut` in the 13-element verifier vector. Joint analysis then finds:

- the unchanged consumer transfers `publicAmountOut` to `recipient`;
- `publicAmountOut` is a direct public input in both the circuit declaration
  and recovered Solidity vector;
- the consumer recomputes `extDataHash` as Poseidon over domain 400,
  `recipient`, zero relayer, and `fee`, and rejects a mismatch;
- Solidity and Circom use the same domain value and input order; and
- Circom 2.2.3 compiles the circuit to 59,910 constraints and 13 public inputs.
  In the exported R1CS, the shortest recovered path from `main.recipient` to
  public `main.extDataHash` is 85 wires; every named interior signal is under
  `main.extDataHasher`.

Result: no P1 role remains. The source/compiled-relation result is
`VERIFIED_WITHIN_SCOPE` at E1. It does not claim zkey, deployed hasher, or
deployment correspondence.

### Retained findings

| DEV case | Expected / observed P1 role | Grade | Verdict | Evidence |
| --- | --- | --- | --- | --- |
| RacePass `EventPass.mintPass` | recipient / recipient | E4 | `VIOLATION` | Prior local real age/KYC proofs, real verifier, unchanged consumer, two caller-selected recipients. |
| ZKredential `ComplianceGateway.verifyAndExecute` | amount / amount | E4 | `VIOLATION` | Prior local real PropertyFy proof, real verifier, unchanged consumer, caller-selected amount/recipient. |
| SPSC `transact` | none / none | E1 | `VERIFIED_WITHIN_SCOPE` | Exact source plus newly compiled R1CS commitment path. |

All 24 controls and all three DEV expectations match. Track B read zero EVAL
rows. Machine-readable evidence is in [`track-b-results.json`](track-b-results.json)
and [`track-b-results.csv`](track-b-results.csv).

## 6. Toolchain and reproducibility

One-command entry points from the repository root:

```sh
./dataset/setup_dataset.sh
./dataset/run_source_collection.sh
./dataset/build_recall_set.py
./dataset/locate_p4_leads.py
./dataset/raw/venv/bin/python dataset/read_p4_candidates.py
./dataset/run_onchain_census.sh
./dataset/run_track_b.sh
```

Important versions and pins:

- Circom 2.2.3 at `ad44e915a12bb047b05745c2884aad9cc8326bc6`;
- snarkjs 0.7.6;
- SPSC project dependency `circomlib@2.0.5`, installed by its own `npm ci`;
- DuckDB 1.4.1 in ignored `dataset/raw/venv`;
- Sourcify export snapshot read on 2026-11-03;
- `zkbugs` at `ee4eb3ab693adc14acb9a6e1842b1794e481e9f9`.

The source collector and recall builder require authenticated `gh` access.
Clones, query pages, Parquet cache/database, compiled R1CS/JSON, audit PDFs,
RPC responses, and installed dependencies remain ignored under `dataset/raw/`
or `dataset/clones/`. Ledgers, configurations, scripts, and summaries are
tracked-ready. No commit was created.

### Coverage limits and routed failures

- DuckDB cannot enumerate the Sourcify HTTP wildcard directly; the census
  routes through the export bucket's prefix listing and records the explicit
  Parquet object list.
- The first source collection was interrupted after circuit queries; fixed
  query pages were preserved and reused, then the remaining queries completed.
- The old Solidity screen missed fixed-size array-literal initializers. The
  parser now recovers them; a DEV-only rerun preserves RacePass and
  ZKredential and removes only SPSC's spurious amount warning. Recipient still
  requires the joint commitment analysis.
- Initial `latest` RPC reruns were nondeterministic. The final census records a
  block tag per chain and caches successful code/balance reads; all 1,049 rows
  have code at those tags. Reproduction must use the recorded tags.
- The duplicate-IC and missing-guard bytecode checks are deliberately triage
  heuristics. Source confirmation is still required.
- A verifier address is not a consumer graph. The global census did not infer
  consumer TVL and must not be presented as having ruled out funded exposure.

## 7. Paper recommendation and next two weeks

The strongest supported framing is **a tool paper with a measurement-study
protocol**, not yet a completed ecosystem measurement. The evidence supports
the integration-layer problem, two real E4 development findings, a concrete
compiled-circuit commitment analysis that removes an important false positive,
prospectively frozen controls, a 40-case recall set, and a scalable passive P4
census. It does not yet support EVAL precision/recall, prevalence, independent
annotation, or a claim that the 43 P4 deployments have funded vulnerable
consumers.

Recommended two-week sequence:

1. Advisor-only review of the private P4 ledger; decide whether and how to
   establish consumer correspondence and coordinate notification. Do not test
   the listed deployments.
2. Author-review all 40 recall cases and maturity/family labels, preserving the
   strict-integration and broader-semantic strata.
3. Freeze the Track B implementation and hashes, then—only after explicit
   authorization—open EVAL and run the frozen tool once on the seven currently
   in-scope rows plus a preregistered family-stratified sample.
4. Build every EVAL warning with a plausible local route; record unsupported
   cases as `UNKNOWN`, and pursue E3/E4 only with synthetic local assets.
5. Reconstruct vulnerable/fixed commits for the 24 cases where both revisions
   resolve, and report predicate recall separately from build and E4 recall.
6. Add independent author annotation and bootstrap confidence intervals over
   family-level, not row-level, yields.

Completion criterion for the next task: a content-hashed frozen analyzer, a
human-reviewed recall/maturity ledger, and a preregistered EVAL run protocol
that has still executed zero EVAL analyses.
