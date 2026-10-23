# D1-02 continuation 01 — initial-scope target search

Date: 23 October 2026. **Task progress: DONE. Initial-scope selection gate:
PASSED WITH QUALIFICATIONS (hashcloak Semaphore-Noir). Research verdict:
UNKNOWN.** This continues the ACTIVE [D1-02](D1-02.md) screen. That report is
unchanged.

## Objective, completion criteria and frozen limits

[D1-02](D1-02.md) recommended a separately frozen screen of at most two more
Noir/ACIR batched EVM families. The task was complete when either (a) one
pinned, licensed candidate was found with a source mapping, a documented
honest local proof route and policy provenance, or (b) every candidate's
failure was recorded and a scope decision was handed to the user.

The [continuation protocol](../protocols/d1/d1-02-continuation-01.json)
(SHA-256 `a4f5914f…6d13`, frozen 16:33:30 UTC) was written before any pinned
source was read. Its limits were:

- two substantive families;
- at most 60 files per family and 1.5 MB per file;
- a 30-second timeout per request and 30 GitHub API requests;
- no dependency installs, builds, proofs or solver runs.

Selection required every criterion to be source-supported. Recursion, hash and
Merkle relations could remain explicit assumptions, but deferral, aggregation
and splitting had to be recorded as fragment gaps.

## Discovery and exposure

Discovery ran before the freeze. It used four web searches, eight anonymous
GitHub repository-search queries and repository metadata; the raw responses
are under `results/raw/D1-02/continuation-01/discovery/`. Two things were seen
before the freeze:

- the path inventory of Semaphore-Noir's main branch (file names and sizes,
  no file contents); and
- a search summary saying Semaphore-Noir batches proofs recursively and
  verifies them in Solidity.

Discovery-only leads that were not screened are listed in the
[intake record](../metadata/d1/d1-02-continuation-01-intake.json):
distributed-lab/noir-semaphore (single proof), Kakushi-Arc (single proof,
ten days old), three Noir rollup demos without licenses, a Stellar consumer,
and TACEO Merces (no public repository found). The licensed, maintained
Noir/ACIR batched-EVM population turned out to be small. This is a convenience
screen, not a census.

## Counts and provenance

- **46/46 files fetched:** 37 from Semaphore-Noir and 9 from Aztec. Each was
  checked against its pinned Git blob ID and length, then hashed with SHA-256.
- **GitHub API requests:** 9 (2 commits and 7 tree objects).
- **Policy pages:** 2 documentation snapshots.
- **Nothing executed:** 0 builds, proofs, replays, solver runs or analyzer
  results, and 0 validated findings or confirmed safe controls.

| Family | Pinned revision | License | Decision |
| --- | --- | --- | --- |
| hashcloak/semaphore-noir | `6e24a48b2cb22c05a0c13361b5228d5e1c99bd0d` (main, 2025-08-27) | MIT | **Selected initial-scope target, with qualifications** |
| AztecProtocol/aztec-packages | `0219f11d8133970df3974fe5ae65e006bf8c193a` (v6.0.0) | Apache-2.0 | Not selected |

## Semaphore-Noir

**Producer.** The leaf circuit is
[`circuits-noir/src/main.nr`](https://github.com/hashcloak/semaphore-noir/blob/6e24a48b2cb22c05a0c13361b5228d5e1c99bd0d/packages/circuits-noir/src/main.nr).
It is a Semaphore membership circuit with four public values: hashed scope,
hashed message, Merkle root and nullifier. There are two batch circuits:

- [`batch_2_leaves`](https://github.com/hashcloak/semaphore-noir/blob/6e24a48b2cb22c05a0c13361b5228d5e1c99bd0d/packages/noir-proof-batch/circuits/batch_2_leaves/src/main.nr)
  verifies two inner proofs with `std::verify_proof`, then outputs `keccak256`
  of the 8×32 public-input bytes, reduced into a Field.
- [`batch_2_nodes`](https://github.com/hashcloak/semaphore-noir/blob/6e24a48b2cb22c05a0c13361b5228d5e1c99bd0d/packages/noir-proof-batch/circuits/batch_2_nodes/src/main.nr)
  combines two batch hashes in the same way.

**Consumer.**
[`SemaphoreNoir.validateBatchedProof`](https://github.com/hashcloak/semaphore-noir/blob/6e24a48b2cb22c05a0c13361b5228d5e1c99bd0d/packages/contracts-noir/contracts/SemaphoreNoir.sol)
(L189–232) works in four steps:

1. It checks that each nullifier is unused and that the batch has no
   duplicates.
2. `verifyBatchedProof` (L249–356) validates each item's root. It then
   recomputes the pairwise keccak tree mod the field modulus and compares the
   result to `publicInputs[0]`. An odd count duplicates the last item, and a
   lone node is promoted.
3. It calls `verifier.verify(proofBytes, publicInputs, 0, true)`.
4. It writes `nullifiers[nullifiers[i]] = true` into group `groupIds[i]` for
   every item.

The protected effects are per-item nullifier state writes with occurrence
identity `(groupId, nullifier)`. There is no token transfer. The only external
call is the view call to the verifier. The test harness appends a 16-word
proof prefix to `publicInputs`; its meaning is not yet established.

**Policy provenance.** The Semaphore V4 contracts reference (snapshot SHA-256
`6bc20cc4…541d`) says validation checks that a nullifier is unused, verifies,
then saves it. The ISemaphoreNoir NatSpec says the batched arrays describe
"all the child proofs batched in this proof". Batch-specific policy exists
only at source-comment level. It has not been frozen or reviewed by a human.

**Honest route.** This is source-supported but was not executed. The
`# batchVerify` tests run on Hardhat's in-process network with no fork. They
create a group, add members, generate 5 or 6 real Semaphore proofs, batch them
through the `bb` CLI (`keccak=true`), and call `validateBatchedProof`. The
pinned packages are bb.js 0.82.2, noir_js/noir_wasm 1.0.0-beta.3 and solc
0.8.27.

**Fit with the initial scope.** The producer is Noir/ACIR. Settlement is a
batch on EVM. Effects can be discharged one occurrence at a time, with no
aggregation, splitting or deferral, and the path is non-reentrant. Recursion
stays an explicit backend assumption, as it is for Payy. Keccak and the
Field-versus-`uint256` reduction need explicit modeling at the byte/integer
boundary.

**Qualifications that remain open:**

- The `bb` CLI version is not pinned in source.
- Compiled circuits and VKs come from `@zk-kit/artifacts` downloads. Their
  correspondence with the in-repo Nargo sources, `HonkVerificationKey.sol` and
  the generated verifier has not been validated. The large verifier/key files
  were inventoried but not fetched.
- The meaning of the 16-word public-input prefix is not established.
- A batch policy still has to be frozen by the analyst.

## Aztec v6.0.0 — not selected

The [`EpochProofLib`](https://github.com/AztecProtocol/aztec-packages/blob/0219f11d8133970df3974fe5ae65e006bf8c193a/l1-contracts/src/core/libraries/rollup/EpochProofLib.sol)
builds the root-rollup public inputs (L290–434) and verifies them (L589–607).
It does not qualify for these reasons:

- L2→L1 effects are deferred. The epoch inserts an out-hash into the Outbox,
  and users consume it later with a Merkle path, which is pending-obligation
  semantics.
- Fees and rewards are aggregated per epoch.
- The public inputs include blob/KZG and attestation-derived data.
- The README places the node and prover in the `labs` submodule
  (`update = none`), which is outside the pinned tree.

No self-contained honest epoch-proving route was found within the screening
bounds. The verdict is UNKNOWN and nothing was built.

## Independence, exposure and limits

**Independence.** Semaphore-Noir is a hashcloak fork of the PSE Semaphore
repository, with no Payy lineage observed. It shares the Noir/Barretenberg
recursive-aggregation pattern with Payy's aggregation circuits; this is
disclosed, and full ancestry was not audited.

**Exposure.** While mapping the source, two things were noticed incidentally:

- the batch circuits take `verification_key` and `key_hash` as private
  inputs; and
- the consumer only partly checks the length relations among its arrays.

Neither was investigated, tested or classified, and no finding is claimed.
Semaphore-Noir cannot serve as a blind holdout for those mechanisms. Before
D1-07, its transfer policy must be frozen without reference to them, and the
exposure must be reported. All mappings were inspected by hand; nothing was
recovered automatically. AI assistance is not independent annotation.

## Commands

```sh
python3 -I scripts/d1_02c_fetch.py --plan results/raw/D1-02/continuation-01/fetch-plan-01.json --log results/raw/D1-02/continuation-01/fetch-log-01.json   # 37/37, exit 0
python3 -I scripts/d1_02c_fetch.py --plan results/raw/D1-02/continuation-01/fetch-plan-02.json --log results/raw/D1-02/continuation-01/fetch-log-02.json   # 9/9, exit 0
```

`scripts/d1_02c_fetch.py` is a new, separately versioned copy of the frozen
D1-02 fetcher that reads per-directory tree listings. Commit and tree pins are
in `pins.json`, API calls in `api-log.json`, and policy snapshots in
`policy/`. Copies of the README, roadmap and project status as they were
before this update are in `prior-living-docs/`, with Git blob IDs. The tool
versions were Python 3.12.12 and Git 2.43.0.

## Failed approaches

- The `gh` CLI is not installed, so anonymous REST calls were used.
- At v6.0.0, `noir-projects/` contains only `fnd/`; the Aztec protocol
  circuits are under `noir-projects/fnd/noir-protocol-circuits`.
- `packages/contracts-noir/contracts/README.md` does not exist; the package
  README was used instead.

## Next task

D1-03 may use Semaphore-Noir only as the reserved transfer target. It must
not be used for development or tuning. D1-03 itself proceeds on the Payy
development case, as the roadmap specifies.
