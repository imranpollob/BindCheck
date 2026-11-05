# Integration dataset v2 inventory report

Date: 2026-11-04  
Branch: `zk-dataset-v2`  
Inventory revision: `7353297`  
Status: bounded data-only inventory complete; human label review and EVAL tag pending

## 1. Objective, boundary, and result

Dataset v1 was circuit-first: it retained 841 EVAL rows but found only seven
rows whose pinned trees contained a circuit, a verifier, and a consumer path.
Dataset v2 reverses the collection direction. It freezes searches for Solidity
verifier calls and Circom/Noir integration repositories, scans pinned repository
trees with documented path and call regexes, passively matches exact consumer
source hashes to Sourcify exports, and re-dispositions all v1 rows under the
relaxed rule that a committed generated verifier is optional.

This task is inventory only. It ran zero BindCheck analyzers, zero
`screen_consumers.py` or `scan_p4.py` calls, zero Track B calls, and no bug
search. It made no RPC request, transaction, proof submission, deployed-contract
call, balance read, maintainer contact, or disclosure. The 43 private P4
addresses from v1 were not used as seeds and were not traced. The resulting
labels are syntactic inventory dispositions, not security verdicts or evidence
of ecosystem prevalence.

The main result is [`source-corpus-v2.csv`](source-corpus-v2.csv): 5,024 rows,
including all 897 v1 rows followed by 4,127 new EVAL rows. After family
deduplication, it contains **1,384 in-scope EVAL-only families**, exceeding the
goal of 100. No EVAL row has been analyzed.

## 2. Fixed GitHub collection

### 2.1 Eligibility rules

[`source-queries-v2.json`](source-queries-v2.json) freezes the queries, order,
page budgets, path rules, call regexes, and maturity heuristics. A pinned
repository revision is mechanically in scope before family deduplication when:

1. its recursive tree has at least one path matching
   `(?i)\.(circom|nr|zok)$` outside the fixed first-party exclusion regex; and
2. a non-excluded Solidity file of at most 2,000,000 bytes matches at least one
   fixed call regex for member `verifyProof`, member `verifyTx`, a named
   verifier's `verify`, a verifier-interface cast followed by a call, or a
   direct `verifyProof`/`verifyTx` call that is not a declaration line.

The fixed exclusions cover `node_modules`, `vendor`, `third_party`,
`third-party`, caches, build output, `target`, and selected library paths.
Circuit-bearing repositories receive a complete non-excluded Solidity
inventory capped at 2,000 files. When a repository has no circuit path, only
the exact Solidity paths returned by GitHub code search are fetched. Comments
are stripped before call matching. Each match records its rule identifier,
line, source SHA-256, and path.

A committed verifier is recorded by a verifier-like path heuristic but is not
required. This deliberately admits applications that generate the verifier at
build time. It also means that tests, tutorials, adapters, stale sources, or
non-production entry points can qualify; author review must not treat
`in-scope` as a deployment or security label.

Collection used GitHub search, batched GraphQL repository metadata, recursive
tree, and raw-content endpoints rather than full repository clones. Every
result page and pinned scan is cached under the ignored
`dataset/raw/source-corpus-2026-11-03-v2/` snapshot.

### 2.2 Per-query yield

The queries ran in the order below. `Unique repos` is within that query;
`marginal` is the number newly added to the cumulative candidate union at that
point; and `in scope` is the number of that query's repositories whose final
pre-dedup scan had both a circuit path and consumer call. These columns overlap
across queries and must not be summed as independent repositories.

| Query ID | Fixed query | Kind | Pages | Items | Unique repos | Marginal | In scope |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `consumer-member-verifyproof` | `".verifyProof(" language:Solidity` | code | 10 | 1,000 | 613 | 613 | 263 |
| `consumer-member-verifytx` | `".verifyTx(" language:Solidity` | code | 4 | 378 | 262 | 248 | 93 |
| `consumer-verifier-verify` | `"verifier.verify(" language:Solidity` | code | 10 | 1,000 | 598 | 550 | 82 |
| `consumer-iverifier-verifyproof` | `"IVerifier" "verifyProof" language:Solidity` | code | 10 | 1,000 | 404 | 253 | 230 |
| `consumer-igroth16` | `"IGroth16Verifier" language:Solidity` | code | 8 | 707 | 236 | 183 | 171 |
| `consumer-groth16` | `"Groth16Verifier" "verifyProof" language:Solidity` | code | 10 | 1,000 | 577 | 306 | 358 |
| `consumer-plonk` | `"PlonkVerifier" language:Solidity` | code | 10 | 1,000 | 217 | 128 | 67 |
| `consumer-ultra` | `"UltraVerifier" language:Solidity` | code | 5 | 500 | 205 | 156 | 77 |
| `consumer-honk` | `"HonkVerifier" language:Solidity` | code | 5 | 500 | 182 | 114 | 90 |
| `consumer-require-verifyproof` | `"verifyProof(" "require(" language:Solidity` | code | 10 | 1,000 | 497 | 217 | 198 |
| `consumer-if-verifyproof` | `"verifyProof(" "if (" language:Solidity` | code | 10 | 1,000 | 462 | 70 | 140 |
| `circom-main-circuits` | `"component main" extension:circom path:circuits` | code | 10 | 1,000 | 536 | 388 | 215 |
| `circom-pragma-circuits` | `"pragma circom" extension:circom path:circuits` | code | 10 | 1,000 | 436 | 106 | 146 |
| `repo-circom-solidity` | `circom solidity in:readme archived:false` | repository | 4 | 397 | 397 | 338 | 186 |
| `repo-zksnark-circom-solidity` | `zk snark circom solidity in:readme archived:false` | repository | 2 | 198 | 198 | 74 | 66 |
| `repo-noir-solidity-verifier` | `noir solidity verifier in:readme archived:false` | repository | 10 | 1,000 | 1,000 | 772 | 266 |
| **Total search responses** | 16 fixed queries |  | **128** | **12,680** |  |  |  |

The query union contains 4,516 candidate repositories. Combining it with v1
pins produced 5,013 unique pinned revision scans. Their preliminary
dispositions in [`github-source-inventory-v2.csv`](github-source-inventory-v2.csv)
are:

| Preliminary scan disposition | Revisions |
| --- | ---: |
| `in-scope` | 1,593 |
| `inventory-incomplete` | 39 |
| `no circuit` | 1,825 |
| `no consumer` | 1,555 |
| `unavailable` | 1 |
| **Total** | **5,013** |

The raw snapshot contains 128 query pages, 168 GraphQL batches, 5,013 trees,
5,013 scan records, 3,648 distinct matched consumer-source objects, and 4,877
README objects. Its total recorded size at completion was 458,015,157 bytes.

## 3. Append-only v1 redisposition and final ledger

### 3.1 Append-only handling, including renamed repositories

The v1 ledger has 897 rows, 890 case-insensitive repository names, and 894
unique `(repository, commit)` keys. Exactly three keys occur twice because
GitHub repository renames caused the same current repository and commit to
enter through two historical identities:

| Current repository | Commit | Preserved v1 family identities |
| --- | --- | --- |
| `valida-xyz/valida` | `5058de8573e239eb1985c8ee8a1cf1b0d0f873c2` | `repo:delendum-xyz/valida`; `repo:valida-xyz/valida` |
| `nulltea/zk-SQL` | `4c3626d383873fdd5e64e7fa874967d26cc61f96` | `repo:nulltea/zk-sql`; `repo:timoth-y/zk-sql` |
| `selfxyz/self` | `be761b35e69d85e48dd1c6f3eca7422a4ae43add` | `repo:selfxyz/self`; `repo:zk-passport/proof-of-passport` |

The append-only check does not assume that `(repository, commit)` is unique.
It keeps v1 as an ordered list, places all 897 enriched rows first, and compares
the projection of each row onto the complete v1 schema with the corresponding
original dictionary at the same index. Thus both copies of every renamed key
must remain present and byte-for-byte equal in every old column. A second
assertion requires every row after the v1 prefix to have `split=EVAL`.

The inventory lookup may supply the same pinned scan to duplicate keys, but it
writes only new `v2_*` columns. Family recomputation can mark a non-canonical
copy `v2_disposition=dup`; it never rewrites the old `disposition`, old family,
DEV fields, or row order. The independent validation repeated this projection
check and confirmed three duplicate keys with one extra row each.

### 3.2 Redisposition of v1 EVAL rows

The original disposition remains in `disposition`; the relaxed pre-dedup label
is in `v2_predup_disposition`. The v1 EVAL cross-tab is:

| v1 disposition | v2 `in-scope` | v2 `inventory-incomplete` | v2 `no circuit` | v2 `no consumer` | v2 `unavailable` | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `dup` | 38 | 1 | 0 | 80 | 0 | 119 |
| `in-scope` | 5 | 0 | 0 | 2 | 0 | 7 |
| `no consumer` | 45 | 0 | 1 | 23 | 0 | 69 |
| `no verifier` | 123 | 0 | 89 | 426 | 0 | 638 |
| `unavailable` | 0 | 0 | 0 | 0 | 8 | 8 |
| **Total** | **211** | **1** | **90** | **531** | **8** | **841** |

This is a mechanical re-inventory, not a claim that any previous label was a
security error. In particular, 123 former `no verifier` rows now qualify
because v2 does not require a committed generated verifier.

### 3.3 Family deduplication and final counts

Family connected components are recomputed over all v1 and v2 rows using only:

- case-insensitive repository identity;
- recorded GitHub fork root;
- an exact fingerprint of the sorted first-party circuit blob SHA values; and
- preserved v1 family identity.

The canonical row is chosen by DEV before EVAL, pre-dedup in-scope before
other dispositions, strongest maturity, descending stars, then repository and
commit. Non-canonical members retain their pre-dedup label and receive
`v2_disposition=dup`. These are conservative identity proxies, not complete
clone detection or proof that two applications share semantics.

| Final assembly stage | Count |
| --- | ---: |
| v1 rows preserved | 897 |
| New rows, all EVAL | 4,127 |
| Final rows | 5,024 |
| DEV rows | 56 |
| EVAL rows | 4,968 |
| All v2 families | 4,668 |
| In-scope EVAL families, including four with DEV overlap | 1,388 |
| **In-scope EVAL-only families** | **1,384** |

| EVAL final disposition | Rows |
| --- | ---: |
| `in-scope` | 1,384 |
| `dup` | 352 |
| `inventory-incomplete` | 37 |
| `no circuit` | 1,825 |
| `no consumer` | 1,361 |
| `unavailable` | 9 |
| **Total** | **4,968** |

Before family deduplication the EVAL counts are 1,548 `in-scope`, 38
`inventory-incomplete`, 1,826 `no circuit`, 1,547 `no consumer`, and nine
`unavailable`.

## 4. Passive Sourcify consumer matches

[`census_sourcify_consumers_v2.py`](census_sourcify_consumers_v2.py) starts
only from the 3,648 exact SHA-256 values of GitHub Solidity files that matched
a verifier-call regex. It joins those hashes to the official Sourcify v2
Parquet export, requires the matched source path to be the compiled target's
own source path, requires both `runtime_match=true` and
`runtime_metadata_match=true`, and restricts deployments to the fixed chain
list. It makes no RPC requests and does not read the private P4 address ledger.

The remote join was materialized in five restartable stages:

| Sourcify stage | Rows | Meaning |
| --- | ---: | --- |
| `source_compilations` | 2,437 | Exact GitHub consumer-source hashes found in compilation sources. |
| `relevant_compilations` | 1,030 | Compiled contracts for the reached compilation IDs. |
| `exact_verified` | 8,480 | Verified-contract links with both runtime match flags true. |
| `relevant_deployments` | 609 | Reached deployments on the seven fixed chains. |
| `exact_consumer_deployments` | 390 | Repository/deployment rows where the matched call-site source is the compiled target source. |

After collapsing repeated repository/compilation evidence,
[`onchain-consumers-v2.csv`](onchain-consumers-v2.csv) records 277 unique
chain/address deployments, exact source hashes, source paths, contract names,
verified-contract and compilation IDs, and matched GitHub repository, commit,
path, and regex evidence. The repository-level bridge is retained separately
in [`sourcify-github-matches-v2.csv`](sourcify-github-matches-v2.csv). Eighty-six
GitHub repositories have at least one match.

| Chain | Unique consumer deployments |
| --- | ---: |
| Base | 92 |
| Ethereum | 77 |
| Optimism | 38 |
| Polygon | 31 |
| Arbitrum One | 25 |
| Linea | 14 |
| zkSync Era | 0 |
| **Total** | **277** |

This is a targeted source-hash join, not a global consumer scan of the
Sourcify source corpus. Exact source equality strongly supports source reuse
but does not by itself establish repository ownership, deployment intent,
current liveness, proxy routing, funds, or application security. Every
on-chain row therefore remains `UNKNOWN`.

## 5. Maturity strata

`verified-deployed` is the strongest maturity label and is assigned only after
the exact GitHub/Sourcify compiled-target match above. The remaining labels are
fixed metadata/README heuristics:

- `deployed-address-in-docs`: a nonzero 20-byte address plus deployment,
  mainnet, or contract-address language;
- `audited-production`: an audit/auditor term plus production, mainnet, or
  protocol language;
- `hackathon-student`: hackathon, ETHGlobal, Devfolio, student, or university
  language; and
- `unclassified`: none of those rules matched.

The actual matching term, address, and a short README/metadata excerpt are
stored in each row's `maturity_basis` and `v2_maturity_basis`, so a human can
review the basis without re-running collection. At the family level, the
strongest member label is used:

| EVAL-only in-scope family maturity | Families |
| --- | ---: |
| `verified-deployed` | 38 |
| `deployed-address-in-docs` | 303 |
| `audited-production` | 207 |
| `hackathon-student` | 81 |
| `unclassified` | 755 |
| **Total** | **1,384** |

The heuristic labels require human review. In particular, README deployment
text is not deployment correspondence, an audit mention is not evidence that
the inventoried revision was audited, and a repository can contain production
and tutorial code together.

## 6. Recall-set growth

[`recall-set-v2.csv`](recall-set-v2.csv) preserves all 40 v1 rows and appends
seven fixed zkSecurity `zkbugs` records from commit
`ee4eb3ab693adc14acb9a6e1842b1794e481e9f9`. A row is promoted to the strict
integration inventory only when its fixed case-ID regex names an effect or
integration concept and its repository has a v2 circuit-plus-consumer-call
inventory row. Existing v1 strict labels are preserved. This is repository-
level inventory evidence; finding-to-revision correspondence remains
unvalidated.

| Recall measure | v1 | v2 |
| --- | ---: | ---: |
| Strict integration cases | 20 | 27 |
| Broader integration/execution candidates | 20 | 20 |
| Total cases | 40 | 47 |
| Resolved vulnerable commits | 31 | 38 |
| Resolved fixed commits | 28 | 35 |
| Resolved vulnerable/fixed pairs | not separately frozen | 31 |
| Analyzer or recall executions | 0 | 0 |

The strict set grew toward, but did not reach, the requested target of 40.
This pass used the pinned public `zkbugs` extraction, which aggregates several
named audit sources, plus the preserved v1 audit records. It is not a complete
enumeration of every zkSecurity, Veridise, Trail of Bits, Zellic,
OpenZeppelin, Code4rena, Sherlock, or Cantina report. All rows remain E0/
`UNKNOWN` until independently reviewed and, in a later authorized task,
executed under the research contract.

## 7. Preregistered family-stratified sample

Because 1,384 eligible EVAL-only families exceed the threshold of 300,
[`EVAL-SAMPLE-PLAN-v2.md`](EVAL-SAMPLE-PLAN-v2.md) was frozen before any EVAL
analysis. After human eligibility, family, and maturity review, it selects up
to 60 families per maturity stratum by ascending SHA-256 of a fixed salt plus
`v2_family_id`; strata with fewer than 60 contribute their whole population.
DEV-overlapping families are excluded. Any pre-analysis correction requires a
new ledger hash and documented sample refresh; a post-analysis correction
cannot retain preregistered status.

## 8. Reproducibility and raw evidence

The effective collection and build entry points from the repository root were:

```sh
python3 dataset/collect_source_corpus_v2.py
dataset/raw/venv/bin/python dataset/census_sourcify_consumers_v2.py
python3 dataset/build_source_corpus_v2.py
python3 dataset/build_recall_set_v2.py
```

The recall builder verifies that the ignored `dataset/clones/zkbugs` checkout
is exactly `ee4eb3ab693adc14acb9a6e1842b1794e481e9f9` before reading `BUGS.md`.
Relevant tool versions were Python 3.13.9, GitHub CLI 2.79.0, Git 2.51.0, and
DuckDB 1.4.1. The Sourcify snapshot date recorded by the script is 2026-11-03.

Ignored evidence locations:

- `dataset/raw/source-corpus-2026-11-03-v2/`: query pages, GraphQL batches,
  pinned trees, scans, matched sources, and README bytes;
- `dataset/raw/sourcify-consumers-2026-11-03-v2/`: Sourcify object manifest,
  staged SQL, restartable DuckDB database, and output manifest;
- `dataset/raw/integration-recall-2026-11-03-v2/`: commit-resolution records
  and recall manifest; and
- `dataset/clones/zkbugs/`: ignored pinned partial checkout used only for the
  public recall inventory.

The collector's initial one-request-per-repository REST metadata approach was
stopped and replaced by 168 batched GraphQL requests; the earlier raw pages
remain preserved but are not mixed into the final snapshot. Transient
connection resets and incomplete reads caused resumptions, after which bounded
retry handling completed all recorded scans.

An initial one-shot Sourcify join was terminated after approximately 39
minutes without producing a usable result; no count was inferred from it. The
five-stage join above then completed. A nullable block-number formatting error
occurred after the successful stage tables were committed; the corrected
output pass reused those tables. File timestamps bound the successful remote
stages to 4,901 seconds. The final summary explicitly distinguishes that
remote interval from the 0.037-second reused output pass.

## 9. Hash manifest

### 9.1 Authoritative ledgers and frozen plan

| Artifact | SHA-256 |
| --- | --- |
| `source-corpus.csv` (v1) | `7031b6a7302220163e9818b0065bef3a6e964f7085da147619479dd8f4466309` |
| `github-source-inventory-v2.csv` | `e09124ec5ee53ae2b61c290b241d6000d13d3846a1de1fc2dffec8c850a43c06` |
| `source-corpus-v2.csv` | `07210625783a21a6128ea3f99402fc4a48b36922056241649999547a374b0c95` |
| `onchain-consumers-v2.csv` | `dcf0b7f31d11724dca3d25e80c662e2324e271fe5d1850336cb4e6ed89e0a292` |
| `sourcify-github-matches-v2.csv` | `fb29466d660a22f95d55e3851f97b84095553563909461ba4ac4d78ce7c5cada` |
| `recall-set.csv` (v1) | `77d5e0ff7b682e925b52d4188b21182d988c04dca176a13d8a346fbc868a0f14` |
| `recall-set-v2.csv` | `709021bc34020e33d22dbb449066435f1a3938da5c148ae666fa9e3aa0a604f9` |
| `EVAL-SAMPLE-PLAN-v2.md` | `e40380cad2660a74a0ff957acac0aead3cabd4f7be8b6a77d6eb45fd783a4c67` |

### 9.2 Fixed configurations, builders, and summaries

| Artifact | SHA-256 |
| --- | --- |
| `source-queries-v2.json` | `546eb122befcaefd7ef6939ffdef81684b7f4f6ffb080c7d5a54fd587157f136` |
| `recall-queries-v2.json` | `884d00b529385f0ff3bd6675fa14d875f96fda5c8ae69d14514e73c5a1cbe4c6` |
| `collect_source_corpus_v2.py` | `32bad207ec92d2e2bdc984e43651ab771fa9af7b9be081c0b6a20886e5dc7fab` |
| `census_sourcify_consumers_v2.py` | `34daeb048b76f0219c4b7ed72c6a2cea68faa0d5d65ad3311ce83ec8ace83672` |
| `build_source_corpus_v2.py` | `f07e50fd842a67804a088f416ff0ed315c97eb515e0e0a6ae463d6bff9371cbb` |
| `build_recall_set_v2.py` | `6368c8dd6308f5e8d0ca6a26b150c4072b40be1141aba63f0f3ca1462b378538` |
| `github-source-inventory-v2-summary.json` | `c3146a5fa65bd09ffdcf4331a6902fa9a6c6cd4641d7ba472f8438fac13e0871` |
| `source-corpus-v2-summary.json` | `d95af08e4091a85f5ab41a78a8131ffead79cc0cdf08a192e9597e41d530687f` |
| `onchain-consumers-v2-summary.json` | `eb2391679d4b68e95eecbced53d6efe55426adfcd22ee8034338ec4506400d9a` |
| `recall-set-v2-summary.json` | `4cc129c11962908218c902da642dbc1fa86a439e7b5f71c6835831a2d906d4d8` |

## 10. Final validation

Validation did not regenerate any ledger or run an analyzer. The following
syntax and integrity commands completed with exit status 0:

```sh
python3 -m py_compile dataset/collect_source_corpus_v2.py dataset/census_sourcify_consumers_v2.py dataset/build_source_corpus_v2.py dataset/build_recall_set_v2.py
python3 -m json.tool dataset/source-queries-v2.json
python3 -m json.tool dataset/github-source-inventory-v2-summary.json
python3 -m json.tool dataset/onchain-consumers-v2-summary.json
python3 -m json.tool dataset/recall-queries-v2.json
python3 -m json.tool dataset/recall-set-v2-summary.json
python3 -m json.tool dataset/source-corpus-v2-summary.json
git diff --exit-code 8a1c453 -- dataset/source-corpus.csv dataset/recall-set.csv
git diff --check
```

An independent Python assertion pass, separate from the builders, observed:

- exact row-by-row projection of all 897 v1 rows onto the old schema;
- every one of the 4,127 appended rows has `split=EVAL`;
- exactly the three documented duplicate v1 keys and three excess rows;
- 5,024 source rows, 1,384 EVAL-only in-scope families, and maturity counts
  summing to 1,384;
- 277 on-chain rows, all with both runtime flags true and `UNKNOWN`, with zero
  RPC requests and zero P4 seeds in the summary;
- exact projection of all 40 v1 recall rows, 47 v2 rows, 27 strict cases, and
  zero recall executions; and
- byte-for-byte agreement for all 18 hashes in Section 9.

Every relative link added by this task resolves. A repository-wide link probe
also encountered the already-recorded ignored path
`results/raw/D1P-33/manifest.json`, which is absent from this checkout; this is
pre-existing D1 evidence hygiene and does not affect any dataset-v2 link or
validation result.

## 11. Limitations and handoff

- GitHub search exposes a ranked, capped snapshot under fixed page budgets;
  it is not an exhaustive census of GitHub.
- Path and call regexes trade precision for recall. Dynamic calls, assembly,
  aliases not covered by the fixed rules, non-Solidity consumers, files over
  the size cap, tree truncation, fetch failure, and repositories exceeding the
  Solidity cap can be missed or marked incomplete.
- A `.circom`, `.nr`, or `.zok` path outside dependency directories is only a
  first-party heuristic. The inventory did not build circuits or establish
  that a consumer uses the recorded circuit.
- Generated verifiers are permitted but not reconstructed. No verifier key,
  ABI, deployment configuration, or circuit/verifier correspondence was
  validated.
- Exact circuit-blob fingerprints, fork ancestry, and old family IDs can both
  under-merge renamed/copied projects and over-merge repositories that reuse a
  circuit while implementing different applications.
- Sourcify coverage is limited to exact call-site hashes already found on
  GitHub and verified records present in the export. It does not cover
  unverified contracts, modified copies, proxies, or consumers absent from the
  GitHub search frame.
- README maturity labels and strict recall promotion are prioritization aids,
  not independent annotations. AI-generated inventory output is not an
  independent label.

The recommended next task is author review before tagging: inspect the 38
`verified-deployed` canonical families, all 38 pre-dedup
`inventory-incomplete` rows, and the preregistered maturity-stratified sample;
correct path, family, or maturity labels if necessary; regenerate hashes and
the sample only before analysis; and then freeze the reviewed EVAL inventory.
No analyzer should read EVAL until that review and freeze are complete.
