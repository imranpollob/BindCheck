# Feasibility v2: real circuit-to-consumer findings

Date: 2026-11-03  
Workspace revision at execution: `cf24426516a5871e1bde407450cda547bc56ec5c`  
Status: bounded task complete; two corpus findings are E4 `VIOLATION`; the
ecosystem-wide security state and every unvalidated warning remain `UNKNOWN`.

This report supersedes the zero-hit interpretation of `feasibility/REPORT.md`
without changing that earlier report. The first scan was a useful acquisition
attempt, but 37/50 Solidity builds failed and 41/50 circuit/consumer pairings
were unresolved. V2 treats those projects as not yet evaluated, fetches all 50
exact revisions, screens 4,251 Solidity files, and builds only adjudicated
signals. All execution was local against archived source. No public RPC,
transaction, maintainer contact, disclosure, or live-system test occurred.

## Private stop notice: P4 and a fund-moving P3/P4 candidate

The source census found 16 verifier files whose parsed Groth16 key has
`gamma == delta ==` the default BN254 G2 generator, one verifier with duplicate
IC points, and 33 verifier files with no detected canonical public-input
`< r` check. These are E1 source warnings and `UNKNOWN`, not confirmed
vulnerabilities: source-to-deployment, bytecode, key, and current-value
correspondence were not established.

The highest-priority stopped lead is `SovereignWave/qwer` commit
`d588661d8e803000c1390a65911c7f0e805ec69d`. Its
`privatecrypmix/.../Verifier.sol` has the default `gamma == delta` key and no
detected public-input field guard; its fund-moving `PrivateCrypMix.withdraw`
also checks and records a raw verifier-bound nullifier without a detected
canonicality guard. The repository mentions Polygon/deployment workflows, but
the inspected source supplied no address that established a currently deployed
funded instance. Per the safety rule, no proof, deployment, call, bytecode
probe, or exploit test was attempted. Treat this as a private E1/`UNKNOWN`
lead until a separately authorized, passive deployment-correspondence review
establishes whether any live instance exists. Do not publish the lead or test
an address.

The other P4 source leads are listed in Section 5. None was tested. In
particular, this report makes no claim that any listed source is deployed,
reachable, funded, or exploitable.

## 1. Confirmed findings, ordered by demonstrated impact

### 1.1 ZKredential: proof for one wallet mints a caller-selected amount to another caller

- Project/revision: `ethpanda-org/ETHShanghai-2025`, ZKredential subtree,
  `23917814522bac494150c7e99a123aa15a448155`.
- Pattern: P1, unproven effect amount plus proof-wallet/effect-recipient
  mismatch.
- Verdict/evidence: E4 `VIOLATION`, local only.
- Consumer: unchanged `ComplianceGateway.verifyAndExecute`; token and
  `PropertyFyVerifier` are unchanged source from the pinned archive.

The property proof exposes a wallet address, but the gateway does not require
that wallet to equal `msg.sender`. For the mint action, the gateway forwards
`msg.sender` as recipient and an independent calldata `amount`; the proof
commits to neither effect value. A proof whose public wallet is
`0x7099...79C8` was submitted by `0x3C44...93BC` with the caller-selected amount
`123456789012345678901234`. The real verifier accepted, and the unchanged
gateway/token minted exactly that amount to the caller while the credential
owner's balance remained zero. The one-time proof hash prevents a second use,
but does not constrain the first effect.

The run rebuilt `propertyfy_circuit.circom` with pinned Circom 2.2.3, verified
the rebuilt R1CS against the committed phase-2 zkey, generated a fresh proof,
verified it off-chain, and executed the unchanged consumer in Hardhat's local
EVM. The repository-wide Hardhat build has an unrelated broken
`../ZKRWARegistry.sol` import; the runner compiles an exact-source slice of the
verifier, gateway, token, adapter, registry, and interfaces without modifying
the target sources.

Reproduce:

```sh
./feasibility/v2/run_zkredential_e4.sh
```

Primary evidence:
`results/raw/feasibility-v2/zkredential-e4-20261103T183338Z-51083/`.
The run records all step exits, environment versions, a source tar hash,
artifact hashes, the proof hash, public wallet, caller, amount, and final
balances.

Limits: no deployed gateway/token address was found in the checked-in
manifests. The result is a real local proof-to-effect violation, not a claim of
current on-chain exposure, financial loss, or independent-human confirmation.

### 1.2 RacePass EventPass: one proof authorizes repeated caller-directed pass mints

- Project/revision: `Servesh21/RacePass`,
  `abd54b5c541ac9d26f938a6bdbd78545526249e5`.
- Pattern: P1, unproven recipient plus an unbound credential/replay effect.
- Verdict/evidence: E4 `VIOLATION`, local only.
- Consumer: unchanged `EventPass`; unchanged committed `AgeVerifier` and
  `KYCVerifier`.

`EventPass.mintPass` verifies age and KYC public values, then mints to a
caller-supplied `recipient` and stores a caller-supplied linked credential.
Neither effect value nor `msg.sender` is bound by the two proofs, and no spent
proof/nullifier state is recorded. The test generated fresh real proofs once
and submitted those exact proof bytes twice. The unchanged consumer minted
token 0 and token 1 to two different caller-selected recipients and stored two
different caller-selected credential hashes.

The committed proving artifacts were sensitive to compiler version. Compiling
with Circom 2.2.3 produced a non-corresponding R1CS. The committed `circom.exe`
identified 2.1.9; after building exact Circom 2.1.9 at
`2eaaa6dface934356972b34cab64b25d382e59de`, both rebuilt WASM hashes matched
the committed WASM files and both R1CS/ptau/zkey correspondence checks passed.
The real committed Solidity verifiers then accepted the fresh proofs on local
Anvil.

Reproduce:

```sh
./feasibility/v2/run_racepass_e4.sh
```

Primary evidence:
`results/raw/feasibility-v2/racepass-e4-20261103T184530Z-61766/`.

Limits: only testnet verifier addresses, not a deployed EventPass instance,
were found in the repository material. This is not a current-deployment or
loss claim. The result still needs author-owned policy adjudication independent
of the AI-generated screening and harness.

### 1.3 Historical zkDrops: one real proof transfers the airdrop twice

- Project/revision: `a16z/zkdrops`, vulnerable parent
  `4002962fb632578dd12477346d2e5c4159ffb2ef`; public fix
  `f6f58020911cd2a19e1639f0dc93ec9fca2a9e17`.
- Public record: <https://github.com/a16z/zkdrops/pull/2>.
- Pattern: P3, verifier field alias versus raw Solidity spent key.
- Verdict/evidence: E4 `VIOLATION`, historical/local only.

The v2 P3 check fires on the exact vulnerable source and clears on the exact
fixed source. The dynamic reconstruction used the vulnerable parent,
project-owned build, committed real PLONK artifacts/verifier, and unchanged
consumer. The same proof hash was accepted once with nullifier `h` and once
with `h + r`; the verifier reduced the input in the field while Solidity used
the two calldata integers as distinct mapping keys. The unchanged consumer
transferred two 10,000-unit airdrops, leaving the redeemer at 20,000 and the
contract at 60,000.

Reproduce:

```sh
./feasibility/v2/run_zkdrops_alias_e4.sh
```

Primary evidence:
`results/raw/feasibility-v2/zkdrops-alias-e4-20261103T183918Z-54527/`.
This is a reconstruction of a known disclosed bug, not a new finding.

## 2. First experiment: does Groth16 bind an unused declared public input?

Yes. The three-line circuit has public signals `bound` and `unused`, with only
`bound === 1` in the relation. With snarkjs 0.7.6 and Circom 2.2.3:

1. The original proof for public values `[1, 7]` verified.
2. Changing only `unused` after proving to `123463` made verification fail.
3. Changing constrained `bound` after proving also made verification fail.
4. A fresh proof created with unconstrained `unused = 123463` verified.

Therefore, “mutate an unused public input on an existing proof” is not a valid
pattern for snarkjs Groth16. The retained pattern is narrower: a malicious
prover may choose any value for a declared public signal whose relation imposes
no policy constraint, but the chosen value is still cryptographically bound to
that fresh proof.

Reproduce:

```sh
./feasibility/v2/run_public_input_experiment.sh
```

Primary evidence:
`results/raw/feasibility-v2/public-input-20261103T175718Z-28272/`.
The earlier failed run is preserved separately rather than overwritten.

## 3. Pattern yield

The wide screen covered all 50 frozen repositories, 4,251 Solidity files, and
42,668 parsed function bodies. It found ten functions containing both a
verifier call and a recognized state effect; nine emitted at least one warning.
Counts below are warning functions, not vulnerability prevalence.

| Pattern | Screened | Built/validated | Warned | Confirmed |
|---|---:|---:|---:|---:|
| P1 unproven effect parameter | 50 repos / 4,251 files | 3 warned projects adjudicated; 2 fully built | 3 functions | 2 E4 `VIOLATION` |
| P2 missing context binding | same | 2 warning projects fully built for their P1 paths | 7 functions | 0; all remain `UNKNOWN` as P2 |
| P3 replay-key handling | same, plus 2 historical pairs | 1 historical dynamic build; 2 vulnerable/fixed source pairs reconstructed | 1 corpus function; 2/2 historical vulnerable revisions | 1 historical E4; corpus lead `UNKNOWN` |
| P4 broken verifier constants/guards | 116 key-bearing files / 98 unique source hashes | 0, safety stop | 16 default `gamma == delta`; 1 duplicate IC; 33 no detected `< r` guard | 0; all `UNKNOWN` |
| P5 input order/count/meaning | same consumer screen | 0 | 0 | 0 |

The third P1 warning, Nethermind SPSC, was a lexical false positive: recipient
and amount flow through the consumer's `extDataHash`/public-vector construction
instead of appearing as direct identifiers. It was not counted as a finding.
P2 warnings are intentionally coarse and do not account for all protocol
barriers, deployment uniqueness, roots, nullifiers, or application state. P5
currently detects only fixed-vector arity mismatches; zero warnings do not
establish semantic order/meaning correctness.

Machine-readable outputs are `consumer-screen.json`, `consumer-screen.csv`,
`p4-census.json`, and `p4-census.csv`. Regenerate the consumer and P4 screens:

```sh
./feasibility/v2/run_static_screens.sh
```

## 4. Recall on historical positives

The v2 historical runner reconstructs exact source snapshots for two public P3
bugs and their fixes:

| Case | Vulnerable revision | Fixed revision | Vulnerable check | Fixed control | Dynamic grade |
|---|---|---|---|---|---|
| zkDrops PR #2 | `4002962...` | `f6f5802...` | fires | clear | E4 `VIOLATION` |
| Semaphore issue #16 | `8d703c1...` | `3dcf79f...` | fires | no record after fixed consumer shape/guard | E1 `UNKNOWN` |

Public Semaphore record: <https://github.com/semaphore-protocol/semaphore/issues/16>.
The fixed Semaphore revision changes the consumer effect shape, so it no longer
enters this screen's proof-plus-effect prefilter; its verifier-side `< r` repair
is source-confirmed. This is 2/2 predicate recall on the two exact vulnerable
source revisions, not end-to-end recall: only zkDrops was dynamically rebuilt
to E4 in this task.

The repository also preserves the earlier Payy historical E4 chain in
`reports/T15.md` through `reports/T20.md` and `docs/payy-case-study.md`. It is
valid prior historical evidence but was not rerun or relabeled here. Thus the
workspace contains two historical E4 reconstructions (Payy and zkDrops), while
v2 itself newly executes one. No claim of blind, held-out, or independent-human
recall follows.

Reproduce exact-revision source recall:

```sh
./feasibility/v2/run_historical_recall.sh
```

Primary source-recall evidence:
`results/raw/feasibility-v2/historical-recall-20261103T183910Z-54302/`.

## 5. P4 census

The scanner identifies source constants and guard shapes; it does not infer
deployment status. At the frozen corpus revisions:

- 50 repositories scanned;
- 116 key-bearing Solidity files;
- 98 unique source hashes;
- 16 files with `gamma == delta` and default BN254 G2 `delta`;
- one file with duplicated parsed IC points;
- 33 verifier files with no detected canonical public-input guard; and
- one key-bearing verifier with incomplete G2 parsing.

The 16 default-key files occur in these source revisions:

| Repository @ revision | Files |
|---|---:|
| `0xFableOrg/0xFable@f4aece4...` | 3 |
| `RippnerLabs/meridian-link@5a5a9f6...` | 3 |
| `SovereignWave/qwer@d588661...` | 1 |
| `avitenzer/zk_voting@18d3a27...` | 1 |
| `ethpanda-org/ETHShanghai-2025@2391781...` (`zk-flex`) | 1 |
| `metacraft-labs/DendrETH@1707b18...` | 1 |
| `zk-poll/zk-poll@4a93d95...` | 2 |
| `zkp2p/zk-p2p@fa4274d...` (Paylah) | 4 |

`Servesh21/RacePass@abd54b5...` has the single duplicated-IC source warning in
`ReputationVerifier.sol`; that is separate from the Age/KYC E4 path above.

No census warning was promoted above E1. Identical-looking source constants can
be placeholders, unused files, test artifacts, or non-deployed generated code.
The next safe step is passive source/bytecode/key/deployment correspondence,
not proof generation or contract interaction. If passive review establishes a
currently deployed funded instance, work must stop and the result must remain
private.

## 6. Toolchain and project coverage

### Acquisition and static coverage

- `fetch_corpus.py` fetched 50/50 repositories at the exact commits in
  `feasibility/candidate-set.csv`; ledger:
  `results/raw/feasibility-v2/corpus-fetch-20261103T175825Z.json`.
- The consumer screen read 50/50 repositories, 4,251 Solidity files and 42,668
  functions.
- The P4 census read 116 key-bearing files / 98 unique source hashes.
- All third-party checkouts stay in ignored `feasibility/work/v2/`; no checkout
  source was edited.

### Build coverage

V2 deliberately builds signal-positive cases rather than treating bulk project
compilation as the denominator. Both selected non-P4 corpus signals with a
plausible local E4 route built and reached E4: 2/2 selected, or 2/50 of the
whole source corpus. The historical zkDrops dynamic target also built and
reached E4. This is targeted validation coverage, not a 50-project build rate.

- RacePass used its `package-lock.json`/`npm ci`, exact Circom 2.1.9, snarkjs,
  Hardhat, and local Anvil.
- ZKredential used its frozen pnpm lock with `pnpm@10.18.3`, Circom 2.2.3,
  snarkjs, and a project-local Hardhat exact-source slice.
- zkDrops used its `package-lock.json`/`npm ci` and project-owned Hardhat
  compile/test path with committed PLONK artifacts.

Pinned tools:

- Circom 2.2.3 at `ad44e915a12bb047b05745c2884aad9cc8326bc6`;
- Circom 2.1.9 at `2eaaa6dface934356972b34cab64b25d382e59de`;
- snarkjs 0.7.6;
- Circomspect at `50010b623ed4f3bff9d1b0363cfe952385b47af3`
  (crate version 0.9.0);
- Foundry/Anvil/Cast 1.4.1;
- Node 26.12.0 and npm 11.20.0 in the final dynamic runs.

Set up the ignored toolchain:

```sh
./feasibility/v2/setup_toolchain.sh
```

Circomspect parsed the toy, RacePass age/KYC, and ZKredential circuits. It
reported no issue on RacePass age, CA01/CS0017 on RacePass KYC, CS0006 on
PropertyFy, and CA01/CS0006 on the unused-public toy. It did not report either
consumer integration violation, as expected for a circuit-only tool. Evidence:
`results/raw/feasibility-v2/circomspect-20261103T183638Z-52625/`.

## 7. Failed approaches and unexpected observations

- RacePass compiled under Circom 2.2.3 but did not correspond to the committed
  zkey. This was not reported as a target failure: exact 2.1.9 provenance was
  recovered, the committed WASM hashes matched, and correspondence passed.
  The failed 2.2.3 attempt remains at
  `results/raw/feasibility-v2/racepass-e4-20261103T184035Z-58831/`.
- ZKredential's full Solidity build failed on an unrelated broken import. The
  exact target-source slice built and exercised the real dependency path; no
  consumer/verifier/token source was repaired or mocked.
- The first toy-run expectation incorrectly assumed snarkjs would return zero
  while printing invalid. The command actually returned exit 1; the runner was
  corrected and the failed evidence namespace preserved.
- The first P4 guard heuristic counted proof-element checks as public-input
  guards. It was narrowed to public-input forms before the reported census.
- The first archive scan inherited the parent Git worktree's HEAD. Archive
  scans now report no commit rather than a false revision; exact revisions are
  carried by the historical manifest.
- Circomspect's CA01 diagnostics on simple asserted outputs are circuit-level
  warnings, not evidence for either E4 integration finding.

## 8. Paper recommendation and next two weeks

The strongest supported framing is **a tool paper plus a targeted measurement
study**, not an ecosystem-prevalence paper yet. The evidence now supports the
claim that a cheap Solidity-first boundary screen can route real, previously
unvalidated corpus candidates to end-to-end validation: two selected corpus
targets reached E4 with fresh real proofs and unchanged consumers, and the P3
check recognized two exact historical vulnerable revisions. The data do not
yet support prevalence, deployed exposure, broad P2/P5 recall, independence,
or a held-out capability claim.

Recommended 14-day plan:

1. Days 1–3: freeze a versioned rule schema and unit corpus for P1/P3/P4/P5.
   Completion: every warning carries a source span, verifier-call/public-vector
   slice, effect dependency, and explicit unsupported reason; all current
   positives and negative controls replay byte-for-byte.
2. Days 2–5: have two non-author annotators independently adjudicate the nine
   consumer warning functions and the P4 source classes. Completion: frozen
   labels, disagreements, and agreement statistics; no AI label counted as an
   independent annotation.
3. Days 4–8: perform passive P4 source-to-bytecode/key/deployment
   correspondence only. Completion: each of the 16 source hits is classified
   `not deployed`, `deployment unknown`, or `corresponding deployment`; any
   funded/current match triggers the private stop and no testing.
4. Days 5–10: add compiler-backed Solidity AST/dataflow for hashed effect
   bindings and fixed-array order. Completion: SPSC clears automatically;
   RacePass and ZKredential retain their warning identities; at least ten
   authored order/count negative controls and ten clean controls pass.
5. Days 8–12: mine and freeze at least ten public integration-layer audit
   positives across at least five families before running the tool. Completion:
   exact vulnerable/fixed revisions and source-backed ground truth for each;
   report recall and unsupported cases separately.
6. Days 11–14: extend the source screen to at least 500 deduplicated
   repositories/contracts, then deeply build every adjudicated non-P4 high
   signal within a fixed budget. Completion: frozen denominator, acquisition
   rate, supported-analysis rate, build rate, warning yield, adjudicated
   precision, and E3/E4 yield with family separation.

The immediate bounded next task should be the frozen AST/dataflow upgrade.
Measurable exit criterion: automatically clear the SPSC direct-identifier false
positive while preserving both E4 P1 warnings and passing 20 order/count and
hashed-binding controls, with no change made after opening a held-out result.

## 9. Assumptions and limitations

- AI-generated code, labels, citations, and exploit interpretations are not
  independent annotation. Authors must inspect every E4 harness, target policy,
  source citation, and report claim.
- E4 here means a real proof was accepted by the real verifier and the unchanged
  consumer committed the demonstrated local effect. It does not imply a live
  deployment, arbitrary-mainnet attacker, financial loss, or undisclosed
  vulnerability.
- The 50-project corpus is a convenience/frozen candidate set with many
  flagship controls; it is not a random ecosystem sample.
- Static warning counts are not project or verifier prevalence. One source file
  can be unused or duplicated; one function can carry multiple patterns.
- P2 needs deployment/context/state adjudication. P5 remains shallow. P4 needs
  passive deployment correspondence. Zero P2/P5 confirmations are not evidence
  of absence or safety.
- No live transaction, public testnet transaction, fork test, public RPC call,
  maintainer contact, issue, PR, or disclosure was made.
- Prior reports and raw namespaces were preserved. Failed runs were not
  overwritten, and no prior evidence was relabeled.
