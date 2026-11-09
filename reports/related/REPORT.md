# Lane D: related-work assessment (handoff)

**Status:** DONE (read-only research). **Date:** 2026-11-09. **Branch:**
`zk-related` at base `feb5c19`. **Deliverable:** [`RELATED-WORK.md`](../../RELATED-WORK.md).

## Objective

Decide which contribution claims are defensible under two framings:

1. a tool that beats strong baselines; or
2. a benchmark and measurement study with a fail-closed checker.

The work covers the tools and studies listed in the lane prompt, plus a fresh
2024–2026 search.

## Outcome

- **Framing 1:** the comparative sentence is not defensible today. A scoped
  priority sentence is defensible with hedges.
- **Framing 2:** novelty is supported by primary-source negatives, but the
  evidence (N, K, a reviewed benchmark, disclosures) is MISSING.
- **Recommendation:** framing 2.
- **Must-run baselines:**
  1. a purpose-built contract-only detector;
  2. Slither (default detectors);
  3. same-policy Foundry property tests;
  4. Circomspect, Picus, ZKAP, and zkFuzz, plus their union with item 1;
  5. a BindCheck ablation with circuit reasoning disabled.

All of these are in `RELATED-WORK.md` §6.

### New facts established in this lane

1. **ELSA (ISSTA 2026) is Solidity-only.** This was unresolved in
   `docs/d2/related-work-matrix-v2.json`.
   - Its official slides list 7 SWC classes, 3 analyzers, GPT-3.5-turbo, and a
     LLaMA-3.2-3B hint model.
   - Its artifact `Anonymize-gitcode/ELSA@509c987` contains 4,086 `.sol` files
     and 0 circuit or constraint files
     ([inventory](evidence/elsa-artifact-inventory.txt)).
   - The slides say the ZKP set has 2,310 contracts. The artifact's
     `datasets/ZKP_dataset` has 2,311 `.sol` files. The one-file discrepancy is
     recorded as observed, not resolved.
2. **zkbugs@212cc50 has 140 entries, and 0 are located in `.sol` files**
   ([census](evidence/zkbugs-census.txt)).
3. **The tools study 2607.23752 cites only rollup papers ([87]–[89]) for "ZKP
   integrations with smart contracts"** and defers integration
   ([greps](evidence/primary-text-greps.txt)).
4. **SoK Table 5 counts 13 integration vulnerabilities out of 141**
   ([greps](evidence/primary-text-greps.txt)). The earlier root literature
   check said "about 11 of 141". That figure matches the Table 3 soundness
   column for the integration row, not the integration total.
5. **The zkjac scanner link from Zeto #186 returns 404 via the GitHub API.** The
   issue is open. Linked PR #200 is open. A maintainer replied on 2026-08-03.
6. **Live-code reading at `feb5c19`:** no P1 or P3 `VIOLATION` path consumes
   circuit facts. Only P5 can produce a circuit-based `VIOLATION`
   (`RELATED-WORK.md` §5.1).

## Files changed

- `RELATED-WORK.md` (new)
- `reports/related/REPORT.md` (new)
- `reports/related/scripts/collect_evidence.sh` (new)
- `reports/related/evidence/{source-hashes,primary-text-greps,elsa-artifact-inventory,zkbugs-census,t25-dev-verdict-counts}.txt`
  (new; produced by the script)

`README.md`, `docs/project-status.md`, and every other file are untouched, as
the lane rules require. Raw downloads are under the ignored
`results/raw/related/`.

## Commands and observed results

```text
bash reports/related/scripts/collect_evidence.sh      # exit 0
```

Tools used:
- curl (system)
- gh 2.79.0
- git 2.51.0
- pdftotext (poppler) 25.10.0
- Python 3.13.9

The script:
1. downloads 8 papers and the ELSA slides, then records SHA-256 values in
   [`source-hashes.txt`](evidence/source-hashes.txt);
2. greps the primary text into [`primary-text-greps.txt`](evidence/primary-text-greps.txt);
3. lists the ELSA tree at a pinned commit;
4. makes a sparse, blob-filtered clone of zkbugs at a pinned commit into a
   `mktemp` directory and deletes it on exit, printing aggregate counts only;
5. recounts the T25 DEV ledger (`phase=after`).

Earlier interactive steps produced the same facts before the script existed:
- WebSearch, about 15 queries;
- WebFetch of the program page, ePrint landing pages, and Zeto #186;
- `gh api` metadata for the tool repositories.

Pinned repository HEADs read on 2026-11-09:

| Tool | Commit |
|---|---|
| circomspect | `50010b6` |
| circom_civer | `af7d4ed` |
| Picus | `138b151` |
| ZKAP | `fbd1ddd` |
| CCC-Check | `7ed87b8` |
| zkFuzz | `c58639d` |
| FSE24-SmartAxe | `7ca21f7` |
| zk-bug-tracker | `56a9966` |

Other BindCheck evidence read, not modified:
- `TOOL-REPORT.md` §4;
- `bindcheck_zk/analyzer.py`, lines 529–636, 780–850, and 852–895;
- `reports/T26.md`, lines 115–116;
- `dataset/onchain-census-summary.json` (SHA-256 `16d11240…`);
- `dataset/onchain-consumers-v2-summary.json` (`eb239167…`);
- `../bindcheck-d1-paper/results/raw/D1P-32/summary.json` (`d1d484be…`);
- `../bindcheck-d1-paper/src/bindcheck_d1/role_binding.py:945`.

## Query log (fresh search, 2026-11-09)

```text
ELSA "Augmenting Multi-Technique Static Analysis with Large Language Models" ZKP smart contracts
"ELSA" neuro-symbolic smart contract vulnerability detection zero-knowledge proof contracts github artifact
zero-knowledge proof smart contract vulnerability detection circuit and contract joint analysis 2025 2026 arXiv
Circom Solidity verifier consumer contract public input binding vulnerability static analysis tool 2026
arXiv 2026 "zero-knowledge" application "smart contract" "public inputs" unbound "front-running" proof replay detection tool
eprint.iacr.org 2025 2026 ZK application integration bugs verifier contract nullifier circuit cross-layer analysis
Veridise OR zkSecurity OR "Trail of Bits" OR Zellic tool checks Solidity verifier contract public signals bound circuit
LLM agent audit zero-knowledge circuits and smart contracts end-to-end 2026 arXiv benchmark
zkbugs dataset zksecurity github reproducible ZK bugs integration layer verifier contract
empirical study vulnerabilities zero-knowledge decentralized applications circuits and contracts 2025 2026
"verifier contract" "public signals" Groth16 snarkjs Solidity static analyzer detect missing check nullifier
"Towards source mapping for zero-knowledge smart contracts"
"Automated Soundness and Completeness Vetting of Polygon zkEVM" FreeVer
"Automated Detection of Under-Constrained Circuits in Zero-Knowledge Proofs" PLDI 2023 Picus
```

The search also followed citations: the related-work section and references
[79] and [86]–[91] of 2607.23752, and zkCraft's reference [23]. That reference
led to the zkSolc source-mapping paper, which is a name collision only.

## Assumptions and limitations

- **The search is bounded.** No DBLP or ACM full-text search was run for
  2026-autumn proceedings beyond the earlier
  [feasibility/LITERATURE.md](../../feasibility/LITERATURE.md) sweep.
  Unpublished, internal audit-firm tools are invisible.
- **ELSA's full paper was not read.** The ACM DL returned HTTP 403 to scripted
  clients ([hashes](evidence/source-hashes.txt)). ELSA claims rest on the
  authors' official ISSTA slides and the public artifact. The slides could omit
  a circuit component, but the artifact has no circuit files, which makes that
  unlikely. This is not proven.
- **Some sources were seen only through abstracts or search snippets.**
  - Zequal: ePrint PDF returned HTTP 403.
  - CIVER: full text not retrieved.
  - Tang et al. (ePrint 2024/514), CCS 2025 Circuzz, and the rollup paper:
    abstract or snippet only.
  - SlowMist post: HTTP 403.
  - Veil and FoomCash PoCs: taken from the earlier lane file and not
    re-fetched.

  These are marked in the matrix.
- **No tool was installed or run.** A "Part" or "—" cell is a design-scope
  judgement from documentation, not an execution result.
- **Data wall:** `dataset/recall-set*.csv`, `eval/`, EVAL rows, and recall
  organisations' repositories were not opened. zkbugs was read for aggregate
  counts only, and no per-project rows were printed.
- **The claude-review "0 of 8" finding** was re-derived from code paths, not by
  re-running the analyzer.

## Failed approaches and unexpected observations

- ACM DL (`dl.acm.org/doi/pdf/10.1145/3832222`) returned 403 to curl and
  WebFetch. The researchr attachment form (POST) returned the slides PDF.
- `github.com/zk-audit/zk-audit` (the zkjac scanner) returned 404.
- The earlier root check's "about 11/141 integration" figure is a Table 3
  column. The Table 5 total is 13.
- `/Users/imranpollob/Coding/bc/bindcheck-d1-paper` reports the same HEAD
  `feb5c19` as this worktree, so it appears to share the repository.

## Cleanup

- Session scratch downloads, a zkbugs clone, and extracted text were deleted.
- The script's `mktemp` clone is removed by an exit trap.
- One stray file written to `/tmp/claude-501/` was deleted.
- Raw evidence remains only under the ignored `results/raw/related/`.

## Recommended next task

**Build and adjudicate the contract-only comparator before any further
BindCheck rule work.**

Implement a documented Slither custom detector, or an equivalent standalone
rule, that receives the same role annotations as BindCheck. It flags a
protected-effect argument that is neither a verifier argument nor
`msg.sender`, and a nullifier mapping that lacks a read, a write, or a `< r`
check.

Run it on all 56 DEV repositories at their pinned commits.

**Completion criterion:** a per-row table over the 56 DEV rows comparing
BindCheck P1/P3 verdicts with the comparator's output. Each disagreement must be
human-adjudicated, and the count of rows where *only* BindCheck is correct must
be stated. If that count is 0, framing 2 should be adopted formally.
