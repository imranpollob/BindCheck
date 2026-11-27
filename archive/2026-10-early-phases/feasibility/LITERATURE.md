# Literature completion: Circom/Groth16–Solidity integration security

**Cutoff:** 2026-11-03

**Result:** no 2025–2026 paper was found in the requested venues that jointly
extracts or analyzes a ZK circuit relation and the state/effects of its
consuming smart contract. This is a title/abstract/full-text follow-up sweep,
not a formal systematic review.

## Inclusion rule

A paper counts as an integration-layer analysis hit only if its analysis joins
facts from both sides of the boundary: the circuit/constraint relation and the
contract's public-input decoding, guards, storage, or protected effects. A
paper does not count merely because it generates a Solidity verifier, deploys a
ZK application, analyzes circuits alone, analyzes ZK compiler/prover pipelines,
or analyzes smart contracts alone.

## Requested venue sweep

| Venue/year | Result | Closest title-level material and adjudication |
| --- | --- | --- |
| IEEE S&P 2025 | none found | `CoBBL`, `HydraProofs`, `Zero-Knowledge Location Privacy`, and `FairZK` concern proof systems/circuits/applications, not a joint circuit–consumer analyzer. [DBLP TOC](https://dblp.org/db/conf/sp/sp2025.html) |
| IEEE S&P 2026 | none found | `zkFuzz` analyzes Circom program/constraint consistency only. Its abstract describes under/over-constrained circuit detection and no Solidity consumer model. [accepted papers](https://www.ieee-security.org/TC/SP2026/accepted-papers.html), [paper page](https://www.cs.columbia.edu/~junfeng/papers/zkfuzz/?publication=zkfuzz-sp26) |
| USENIX Security 2025 | none found | ZK title hit `DeepFold` is a polynomial-commitment/proof-system paper. [DBLP TOC](https://dblp.org/db/conf/uss/uss2025.html) |
| USENIX Security 2026 | none found | The official technical-session search exposed zkVM/proof-system papers but no Circom/Solidity integration analysis. [technical sessions](https://www.usenix.org/conference/usenixsecurity26/technical-sessions) |
| ACM CCS 2025 | none found | `Fuzzing Processing Pipelines for Zero-Knowledge Circuits` tests compiler/witness/prover/verifier pipelines, not consuming-contract semantics. `Towards a Formal Foundation for Blockchain ZK Rollups` models L1 rollup governance, queues, blacklisting, and upgrades in Alloy, not a circuit–contract join. [DBLP TOC](https://dblp.org/db/conf/ccs/ccs2025.html), [Circuzz paper](https://doi.org/10.1145/3719027.3744791), [rollup paper](https://doi.org/10.1145/3719027.3765115) |
| ACM CCS 2026 | none found | The accepted program includes `Formal Verification of Circuit-Soundness in zkWasm` and ZK primitive/application papers, but no joint circuit–consumer analysis. The conference was forthcoming at the cutoff, so this uses the accepted-paper/program pages. [accepted papers](https://www.sigsac.org/ccs/CCS2026/program/accepted-papers.html), [schedule](https://www.sigsac.org/ccs/CCS2026/program/schedule.html) |
| NDSS 2025 | none found | Smart-contract work such as `PropertyGPT` is contract-only; no matching ZK circuit join was found. [DBLP TOC](https://dblp.org/db/conf/ndss/ndss2025.html) |
| NDSS 2026 | none found | ZK title hits (`VeriLoRA`, `ZKSL`) concern verifiable ML; the DBLP page contains no `smart contract` title match. [DBLP TOC](https://dblp.org/db/conf/ndss/ndss2026.html), [accepted papers](https://www.ndss-symposium.org/ndss2026/accepted-papers/) |
| FC 2025 | none found | ZK material includes Jolt semantics, a ZKP market, a Powers-of-Tau SoK, and set-membership proofs; none joins Circom and Solidity program analysis. [DBLP part I](https://dblp.org/db/conf/fc/fc2025-1.html), [part II](https://dblp.org/db/conf/fc/fc2025-2.html) |
| FC 2026 | none found in accessible title/abstract sources | The official conference and CFP pages were searchable, but a complete DBLP post-proceedings TOC was not located. This row therefore has weaker coverage than the other venue-years. [conference](https://fc26.ifca.ai/), [CFP](https://fc26.ifca.ai/cfp.html) |
| ICSE 2025 | none found | Smart-contract defect, audit, and crypto-defect papers do not jointly analyze ZK constraints and a consumer. [DBLP TOC](https://dblp.org/db/conf/icse/icse2025.html) |
| ICSE 2026 | none found | DBLP/ACM title and keyword queries over the main and companion proceedings returned smart-contract work but no qualifying circuit–consumer analysis. [DBLP venue index](https://dblp.org/db/conf/icse/index.html) |
| ACM FSE 2025 | none found | ACM/DBLP TOC and full-site keyword queries returned EVM and software-analysis work, but no qualifying ZK integration paper. [FSE site](https://conf.researchr.org/home/fse-2025) |
| ACM FSE 2026 | none found | The main PACMSE/FSE and companion TOCs contain no qualifying title/abstract hit. [FSE site](https://conf.researchr.org/home/fse-2026/), [DBLP companion](https://dblp.org/db/conf/sigsoft/fse2026c.html) |

## Closest work outside the requested venue/year cells

- Chaliasos et al., `SoK: What Don't We Know? Understanding Security
  Vulnerabilities in SNARKs`, USENIX Security 2024, is the closest framing.
  It studies 141 vulnerabilities across the SNARK stack and explicitly notes
  compositional/cross-layer failures, but it is a vulnerability SoK rather
  than an analyzer that joins Circom and Solidity. [paper](https://www.usenix.org/system/files/usenixsecurity24-chaliasos.pdf)
- Kolozyan et al., `ZKP Security Tools and Verification: Coverage,
  Effectiveness, Adoption, and Challenges` (arXiv, 2026) evaluates six tools on
  70 real Circom vulnerabilities. The reported tools and formal-verification
  work focus primarily on circuit/constraint correctness; it does not report a
  circuit–consumer Solidity analyzer. [preprint](https://arxiv.org/abs/2607.23752),
  [evaluation data](https://zkbugs.com/tools-evaluation)
- `Fuzzing Processing Pipelines for Zero-Knowledge Circuits` (CCS 2025) and
  `zkFuzz` (S&P 2026) are the two closest new automated systems, but their
  analyzed boundary ends at proof verification rather than the application
  contract's interpretation and effects.

## Degenerate Groth16 verification-key scan

**Requested result:** no peer-reviewed paper or published comprehensive census
of *deployed* Groth16 verifiers with degenerate keys was found through the
cutoff.

What was found:

- Public post-incident PoCs document `gamma2 == delta2` in the deployed Veil
  Cash and FoomCash verifiers and the resulting proof forgeries. These are
  incident analyses, not ecosystem scans. [Veil PoC](https://github.com/DK27ss/VeilCash-5K-PoC),
  [FoomCash reproduction](https://crypto.training/hacks/2026-02-foomcash_groth16/)
- A public April 2026 issue says the `zkjac Groth16 Setup Scanner` found all 20
  committed verifier sources in `LFDT-Paladin/zeto` using an uncontributed
  Phase-2 key (`gamma == delta ==` the BN254 G2 generator). The issue is
  conditional about deployment (`if any ... are deployed`) and therefore does
  not establish a scan of deployed contracts. [issue #186](https://github.com/LFDT-Paladin/zeto/issues/186)

This leaves two separable gaps: (1) integration-layer program analysis, and
(2) a reproducible deployed-bytecode/key census. The second gap is outside the
three checks implemented in this feasibility task and would require a separate
chain-data protocol.

## Query log

The sweep used DBLP pages, ACM/venue accepted-paper pages, ACM DOI/full-text
follow-up for plausible hits, and general web indexes. Exact high-signal
queries included:

```text
site:dblp.org/db/conf/sp/sp2025.html OR site:dblp.org/db/conf/sp/sp2026.html
  ("zero-knowledge" OR zkSNARK OR Circom OR Groth16)
  ("smart contract" OR Solidity OR blockchain)

site:dblp.org/db/conf/uss/uss2025.html OR site:dblp.org/db/conf/uss/uss2026.html
  ("zero-knowledge" OR zkSNARK OR Circom OR Groth16)
  ("smart contract" OR Solidity OR blockchain)

site:dblp.org/db/conf/ccs/ccs2025.html OR site:dblp.org/db/conf/ccs/ccs2026.html
  ("zero-knowledge" OR zkSNARK OR Circom OR Groth16)
  ("smart contract" OR Solidity OR blockchain)

site:dblp.org/db/conf/ndss/ndss2025.html OR site:dblp.org/db/conf/ndss/ndss2026.html
  ("zero-knowledge" OR zkSNARK OR Circom OR Groth16)
  ("smart contract" OR Solidity OR blockchain)

site:dblp.org/db/conf/fc/ 2025 2026
  ("zero-knowledge" OR zkSNARK OR Circom OR Groth16) smart contract

site:dblp.org/db/conf/icse/ 2025 2026
  ("zero-knowledge" OR zkSNARK OR Circom OR Groth16) smart contract

site:dblp.org/db/conf/sigsoft/ 2025 2026
  ("zero-knowledge" OR zkSNARK OR Circom OR Groth16) smart contract

2025 2026 ("integration layer" OR "cross-layer")
  zero knowledge circuit smart contract security paper

2025 2026 Circom Solidity joint analysis paper
2025 2026 SNARK circuit smart contract vulnerability analysis

("Veil Cash" OR VeilCash OR FoomCash) Groth16 verifier
  degenerate verification key gamma delta scan deployed

"Groth16 Setup Scanner" OR zkjac "insecure delta" verifier

site:arxiv.org OR site:eprint.iacr.org deployed Groth16 verifier scan
  verification keys Ethereum gamma delta 2025 2026

"deployed Groth16 verifiers" security scan
```

Negative search results are reported as of the cutoff and should not be read as
proof that no unpublished, unindexed, or differently worded work exists.
