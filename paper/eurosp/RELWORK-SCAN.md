# RELWORK-SCAN — related-work scan and citation verification (TODO W4)

Lane: relwork (W4). Date: 2026-11-25. Scope: `sections/related.tex` and `refs.bib` only.

## Method

- Candidates came from the existing bib, targeted web searches using generic technical terms only, and
  the reference lists of the closest papers (SoK [sok-snark-bugs], Kolozyan et al. [zk-tools-sok]).
- Each entry was verified by opening one of the following: (C) the Crossref record for its DOI
  (`api.crossref.org/works`), (P) the publisher or official page, (A) the arXiv API record
  (`export.arxiv.org/api/query`), or (R) the official repository or standard page (HTTP 200,
  title checked). DBLP refused automated access, and Semantic Scholar rate-limited it, so neither was used.
- Title, author list, venue and year were compared field by field against the source. Where a
  paper says only "accepted at X" on arXiv, Crossref was checked for a published DOI. If one
  exists, the bib cites the published version; otherwise it cites the arXiv version with "to appear".
- Closeness to our claim is rated H (high), M (medium) or L (low). Our claim: an effect value of a
  ZK-consuming contract is not fixed by the proved statement (P1–P5); the detector combines an LLM,
  a ledger procedure, deterministic tools and sandboxed attack tests.
- Full text was read for the closest works (SoK §6 and Table 5/7, 0xPARC tracker README, Kolozyan
  et al. §VII–VIII, Portal abstract and §IV, bridge SoK §Wormhole). For the others, the abstract or
  metadata was read.

## Table

| key | paper (venue, year) | verified link | ev. | relevance | close |
|---|---|---|---|---|---|
| sok-snark-bugs | Chaliasos, Ernstberger, Theodore, Wong, Jahanara, Livshits. SoK: What Don't We Know? Understanding Security Vulnerabilities in SNARKs (USENIX Sec 2024) | https://www.usenix.org/conference/usenixsecurity24/presentation/chaliasos | P, A | Layered taxonomy of 141 bugs. Integration layer: 13 bugs, of which 9 are Passing Unchecked Data, 2 Proof Composition, 1 Proof Delegation and 1 ZKP Complementary Logic. They state that "no defense detects bugs in that layer" and call for multi-layer testing. | **H** |
| zk-bug-tracker | 0xPARC. ZK Bug Tracker (repo) | https://github.com/0xPARC/zk-bug-tracker | R | Documents single binding-flaw instances: a zkDrops nullifier that aliases mod p (P3), unused public inputs optimized out, with Tornado squaring the recipient and fee (P1), and Frozen Heart. | **H** |
| zk-tools-sok | Kolozyan, Sorger, Hicks, Chaliasos. ZKP Security Tools and Verification: Coverage, Effectiveness, Adoption, and Challenges (arXiv 2607.23752, 2026) | https://arxiv.org/abs/2607.23752 | A | Six tools on 70 bugs; detection drops from 45.7% to 19.6% on full codebases. Practitioners name system integration as a gap and ask for "reusable LLM skills". Their own scope excludes integration. | **H** |
| portal | Lauinger, Bezmez, Ernstberger, Steinhorst. Portal: Time-Bound and Replay-Resistant ZKPs for Single Sign-On (ICBC 2024) | https://doi.org/10.1109/ICBC59979.2024.10634362 | C, P(pdf) | Shows replay of ZK proofs at identity contracts (P3) and fixes it with a protocol construction, not a detector. | M-H |
| zkvm-study | Jiang, Chu, Xue, Peng, Qin, Luo. Zero-Knowledge VMs: Security and Usability in Practice (ASE 2026) | https://doi.org/10.1145/3832783.3837500 | C | Covers 314 audit vulnerabilities plus commits and issues in zkVMs. The abstract comes from the search index only; the full text was not read. | M |
| zkp-vuln-audit | Tang, Shi, Wang, Charbonnet, Tang, Sun. ZKP Vulnerability Analysis and Security Auditing (ePrint 2024/514) | https://eprint.iacr.org/2024/514 | P | Classifies flaws by completeness, soundness and ZK; mostly circuit-level. | M |
| zkbugs | zkSecurity. zkbugs (repo) | https://github.com/zksecurity/zkbugs | R | Reproducible ZK bug dataset, circuit-centric. | M |
| groth16-randomization | Baghery, Kohlweiss, Siim, Volkhov. Another Look at Extraction and Randomization of Groth's zk-SNARK (FC 2021) | https://doi.org/10.1007/978-3-662-64322-8_22 ; https://eprint.iacr.org/2020/811 | C, P | The ePrint abstract was read: it shows Groth16 achieves a weak SE that "allows proof randomization, while guaranteeing statement non-malleability". Groth16 is re-randomizable but statement non-malleable. This explains why keccak(π) fails as a replay key (P3) and why binding is outside proof-system guarantees. | M |
| sig-of-knowledge | Chase, Lysyanskaya. On Signatures of Knowledge (CRYPTO 2006) | https://doi.org/10.1007/11818175_5 | C | The theory-side nearest neighbour: binds a proof to a message. | M |
| snarky-sigs | Groth, Maller. Snarky Signatures (CRYPTO 2017) | https://doi.org/10.1007/978-3-319-63715-0_20 | C | Simulation-extractable SNARKs with SoK message binding. | M |
| weak-fs | Dao, Miller, Wright, Grubbs. Weak Fiat-Shamir Attacks on Modern Proof Systems (S&P 2023) | https://doi.org/10.1109/SP46215.2023.10179408 | C | Frozen Heart: public values missing from the transcript. A proof-system analogue of an unbound value; P4-adjacent. | M |
| lasir | Wang et al. One Signature, Multiple Payments: Signature Replay in Smart Contracts (ICSE 2026) | https://doi.org/10.1145/3744916.3773198 | C, A | Detector for signature replay, the contract-level analogue of P3 for signatures. | M |
| sso-flaws | Wang, Chen, Wang. Signing Me onto Your Accounts through Facebook and Google (S&P 2012) | https://doi.org/10.1109/SP.2012.30 | C, P(pdf) | Read in the PDF: the relying party uses an email that the IdP signature does not cover (openid.signed is attacker-controlled). This is the P1 'unsigned field' analogue. | M |
| eip712 | Bloemen, Logvinov, Evans. EIP-712 (2017) | https://eips.ethereum.org/EIPS/eip-712 | R | Domain separation for signed messages. It states that replay handling is "specific to the application and out of scope". | M |
| bridge-sok | Lee, Murashkin, Derka, Gorzny. SoK: Not Quite Water Under the Bridge (ICBC 2023) | https://doi.org/10.1109/ICBC56567.2023.10174993 | C, A | Wormhole: the caller supplied the signature-verifier reference. Checked in the PDF; this is the P4 analogue. | M |
| interop-sok | Augusto et al. SoK: Security and Privacy of Blockchain Interoperability (S&P 2024) | https://doi.org/10.1109/SP54263.2024.00255 | C | Survey of bridge and interoperability security. | L-M |
| xscope | Zhang et al. Xscope: Hunting for Cross-Chain Bridge Attacks (ASE 2022) | https://doi.org/10.1145/3551349.3559520 | C | Bridge-attack detector for messages, not proofs. | L-M |
| smartaxe | Liao et al. SmartAxe (FSE 2024, PACMSE 1) | https://doi.org/10.1145/3643738 | C | Cross-chain vulnerability static analysis. | L-M |
| picus | Pailoor et al. Automated Detection of Under-Constrained Circuits in ZKPs (PLDI 2023, PACMPL 7) | https://doi.org/10.1145/3591282 | C | Circuit uniqueness checker; analyzes R only. | L |
| ecne | Wang. Ecne (repo) | https://github.com/franklynwang/EcneProject | R | R1CS uniqueness verification. | L |
| circomspect | Trail of Bits. circomspect (repo) | https://github.com/trailofbits/circomspect | R | Circom linter. | L |
| zkap | Wen, Stephens, Chen, Ferles, Pailoor, Charbonnet, Dillig, Feng. Practical Security Analysis of ZKP Circuits (USENIX Sec 2024) | https://www.usenix.org/conference/usenixsecurity24/presentation/wen | P | Uses circuit dependence graph queries; Circom only. | L |
| zkfuzz | Takahashi, Kim, Jana, Yang. zkFuzz (S&P 2026) | https://doi.org/10.1109/SP63933.2026.00049 | C, A | Circuit fuzzer for under- and over-constrained circuits. | L |
| coda | Liu et al. Certifying ZK Circuits with Refinement Types (S&P 2024) | https://doi.org/10.1109/SP54263.2024.00078 | C | Circuit verification. | L |
| civer | Isabel, Rodríguez-Núñez, Rubio. Scalable Verification of ZK Protocols (S&P 2024) | https://doi.org/10.1109/SP54263.2024.00133 | C | Circom verification. The tool name CIVER is confirmed by the authors' group page (costa.fdi.ucm.es) and by a talk listing; the full text was not read. | L |
| circuzz | Hochrainer, Isychev, Wüstholz, Christakis. Fuzzing Processing Pipelines for ZK Circuits (CCS 2025) | https://doi.org/10.1145/3719027.3744791 | C | Circuit compiler fuzzing. | L |
| mtzk | Xiao, Liu, Peng, Wang. MTZK (NDSS 2025) | https://doi.org/10.14722/ndss.2025.230530 | C | ZK compiler metamorphic testing. | L |
| arguzz | Hochrainer, Wüstholz, Christakis. Arguzz (arXiv 2509.10819) | https://arxiv.org/abs/2509.10819 | A | zkVM soundness and completeness testing. No published DOI found. | L |
| beak | Wen, Ke, Liu, Chen, Feng. Obligation-Targeted Semantic Fuzzing of zkVMs (arXiv 2611.29260; NDSS 2027 per arXiv comment) | https://arxiv.org/abs/2611.29260 | A | zkVM semantic fuzzing. No DOI yet, so it is cited as "to appear". | L |
| zkvm-miscompile | Tan, Chaliasos, Donaldson. Proving the Wrong Program (arXiv 2611.04701) | https://arxiv.org/abs/2611.04701 | A | Compiler bugs as a zkVM threat. Related to our zkVM-guest misses. | L-M |
| slither | Feist, Grieco, Groce. Slither (WETSEB 2019) | https://doi.org/10.1109/WETSEB.2019.00008 | C | Baseline. | L |
| mythril | ConsenSys Diligence. Mythril (repo) | https://github.com/ConsenSysDiligence/mythril | R | Baseline. | L |
| manticore | Mossberg et al. Manticore (ASE 2019) | https://doi.org/10.1109/ASE.2019.00133 | C | Symbolic execution. | L |
| securify | Tsankov et al. Securify (CCS 2018) | https://doi.org/10.1145/3243734.3243780 | C | Static analysis. | L |
| echidna | Grieco, Song, Cygan, Feist, Groce. Echidna (ISSTA 2020) | https://doi.org/10.1145/3395363.3404366 | C | Property fuzzer. | L |
| ityfuzz | Shou, Tan, Sen. ItyFuzz (ISSTA 2023) | https://doi.org/10.1145/3597926.3598059 | C | Fuzzer. | L |
| foundry | Foundry (repo) | https://github.com/foundry-rs/foundry | R | Baseline and test harness. | L |
| smartbugs | Durieux, Ferreira, Abreu, Cruz. Empirical Review of Automated Analysis Tools on 47,587 Ethereum Smart Contracts (ICSE 2020) | https://doi.org/10.1145/3377811.3380364 | C | Tool-effectiveness study. | L |
| exploitable-bugs | Zhang, Zhang, Xu, Lin. Demystifying Exploitable Bugs in Smart Contracts (ICSE 2023) | https://doi.org/10.1109/ICSE48619.2023.00061 | C | Most exploitable bugs are beyond tools. | L-M |
| smartinv | Wang, Pei, Yang. SmartInv (S&P 2024) | https://doi.org/10.1109/SP54263.2024.00126 | C | Invariant inference; a spec-missing problem like ours. | M |
| propertygpt | Liu et al. PropertyGPT (NDSS 2025) | https://doi.org/10.14722/ndss.2025.241357 | C | LLM-generated properties plus formal verification. | M |
| gptscan | Sun et al. GPTScan (ICSE 2024) | https://doi.org/10.1145/3597503.3639117 | C | LLM plus static analysis for logic bugs. | M |
| llm4vuln | Sun, Wu, Xue, Liu, Ma, Zhang, Liu, Li. LLM4Vuln (arXiv 2401.16185) | https://arxiv.org/abs/2401.16185 | A | Evaluation framework that separates LLM reasoning from knowledge. No published DOI found. | L-M |
| iaudit | Ma et al. iAudit: Fine-Tuning and LLM-Based Agents for Smart Contract Auditing (ICSE 2025) | https://doi.org/10.1109/ICSE55347.2025.00027 | C | Agentic auditor with justifications. | M |
| a1-agent | Gervais, Zhou. AI Agent Smart Contract Exploit Generation (FC 2026, LNCS 2027, pp. 233–251) | https://doi.org/10.1007/978-3-032-36697-9_13 | C, P | Agent that writes and runs exploits. Shares our execution loop. | M |
| poco | Andersson, Bobadilla, Hobbelhagen, Monperrus. PoCo (TOSEM 2026) | https://doi.org/10.1145/3816704 | C, A | Agentic PoC generation from audit findings using Foundry. | M |
| rex | Xiao, Wang, Li, Chen. Prompt to Pwn (ACISP 2026) | https://doi.org/10.1007/978-981-92-3012-9_19 | C, A | LLM exploit synthesis with Foundry validation. | L-M |
| egele-crypto-misuse | Egele, Brumley, Fratantonio, Kruegel. Cryptographic Misuse in Android (CCS 2013) | https://doi.org/10.1145/2508859.2516693 | C | CryptoLint; API-parameter misuse. | L |
| cryptoguard | Rahaman et al. CryptoGuard (CCS 2019) | https://doi.org/10.1145/3319535.3345659 | C | Crypto API misuse detection. | L |
| cognicrypt | Krüger, Nadi, Reif, Ali, Mezini, Bodden, Göpfert, Günther, Weinert, Demmler, Kamath. CogniCrypt (ASE 2017) | https://doi.org/10.1109/ASE.2017.8115707 | C | Crypto-API misuse assistant built on CrySL. | L |
| crysl | Krüger, Späth, Ali, Bodden, Mezini. CrySL (TSE 2021) | https://doi.org/10.1109/TSE.2019.2948910 | C | Specification language behind CogniCrypt. | L |
| flashboys | Daian et al. Flash Boys 2.0 (S&P 2020) | https://doi.org/10.1109/SP40000.2020.00040 | C | Front-running; the enabler of P1 theft. | L-M |
| groth16 | Groth. On the Size of Pairing-Based Non-interactive Arguments (EUROCRYPT 2016) | https://doi.org/10.1007/978-3-662-49896-5_11 | C | Background. | – |
| plonk | Gabizon, Williamson, Ciobotaru. PLONK (ePrint 2019/953) | https://eprint.iacr.org/2019/953 | P | Background. | – |

Total cited: 54 entries. For each one, the metadata was verified against the source listed above.

Venue confirmation for LNCS entries: the conference title was read from the Crossref `container-title` of each DOI. The results were EUROCRYPT 2016 (groth16), CRYPTO 2006 (sig-of-knowledge), CRYPTO 2017 (snarky-sigs), FC (groth16-randomization; FC 2021 per ePrint and the Simula page), "Information Security and Privacy" = ACISP (rex), and FC 2026 for a1-agent (landing page, `conference-info` "(FC 2026)"). The Crossref record confirms picus 7(PLDI) and smartaxe 1(FSE). groth16 volume 9666 was not confirmed, so it was dropped.

**Caveat:** this verification is automated metadata matching plus targeted reading, done by an AI lane. Per AGENTS.md, AI output is not independent annotation. The authors must still inspect every entry and every claim in related.tex before submission.

Rejected or not cited:
- zkCraft (arXiv 2602.00667): withdrawn by arXiv administrators because authors were added without consent. Excluded.
- Towards a Formal Foundation for Blockchain ZK Rollups (CCS 2025, 10.1145/3719027.3765115): verified but not cited. It covers censorship resistance and upgradeability, not binding.
- Siguard (ICSE-Companion 2023, 10.1109/ICSE-Companion58688.2023.00019): a short paper superseded by LASiR. Not cited.
- Cheesecloth (TOPS 2025): off topic.
- Trail of Bits, "Coordinated disclosure of vulnerabilities affecting Girault, Bulletproofs, and PlonK" (Frozen Heart, 2022-04-13; https://blog.trailofbits.com/2022/04/13/part-1-coordinated-disclosure-of-vulnerabilities-affecting-girault-bulletproofs-and-plonk/, HTTP 200, title checked). Verified but not cited; the peer-reviewed weak-fs paper is cited instead.
- Practitioner blogs on Groth16 malleability and front-running (ethresear.ch, Beosin, dev.to): not primary or peer-reviewed. Not cited.
- No paper, tool, Slither detector or other static-analyzer rule was found that checks binding between a proof's public inputs and a consumer's effects. A search on 2026-11-25 found only GitHub issues and practitioner checklists.

## Closest prior work and our delta

1. **Chaliasos et al. SoK [sok-snark-bugs].** This is the closest. Their integration layer contains the
   same phenomena: Passing Unchecked Data (9 bugs; V4: "implicit constraints on the public inputs expected by the circuit are not enforced by the application's verifier") *tentatively* overlaps with our P1, P4 and P5. The overlap is pending the RV11 mapping; and the nullifier-misuse
   example is P3. Their 16 Unsafe Verifier back-end bugs overlap with P4 and our 16 "adjacent" findings.
   They also state that no defense covers the integration layer. **Delta:** (a) we define one
   property that spans layers (statement ledger vs. effect ledger), instead of placing bugs by where
   they live; (b) our measurement is about 8x larger for this class (103 binding findings vs. 13
   integration bugs); (c) we build and evaluate the detector they call for. Recommended: map our
   103 onto their V4–V7/V12 categories (TODO RV11).
2. **0xPARC tracker / zkbugs.** These document single instances (nullifier aliasing mod p, an unused
   public recipient optimized out). **Delta:** instances are known, but our contribution is the property,
   the prevalence measurement and the detector. `related.tex` now says this explicitly.
3. **Kolozyan et al. [zk-tools-sok].** Independent recent evidence that tools miss integration bugs and
   that practitioners want "reusable LLM skills" and specification-centred tools. **Delta:** they
   evaluate circuit/core tools and exclude integration; we target integration.
4. **Signatures of knowledge / SE-SNARKs / Groth16 statement non-malleability.** These form the theory-side
   neighbour. **Delta:** they guarantee that a proof cannot be mauled to a different statement. A
   binding flaw arises when an effect value was never in the statement, which no proof-system
   property repairs. The fix is the SoK move of putting the message (the value) into the statement.
5. **Portal [portal].** Shows replay of ZK proofs at contracts (P3) and proposes a construction.
   **Delta:** a single pattern, a design fix and no detection or measurement.
6. **LLM exploit agents (A1, PoCo, ReX) and LLM auditors (GPTScan, iAudit, PropertyGPT).** These share
   the execute-to-confirm loop and the LLM-plus-tools architecture. **Delta:** our procedure is derived
   from a definition and builds exhaustive two-artifact ledgers. Theirs apply general vulnerability
   knowledge to a single contract or start from a known finding (PoCo).

Implication for claims outside this lane, not edited here: the intro's "first measurement study of
the class" and related.tex's "first to define … as a property / measure / detect" hold up against
everything found. A claim of "first to observe" such flaws would not hold. Recommendation for the intro lane:
cite the SoK's statement that the integration layer has no defense, as motivation.

## Bib fixes applied

- `picus`: changed to @article PACMPL 7(PLDI), with DOI 10.1145/3591282. It was "PLDI" inproceedings.
- `zkfuzz`: changed from arXiv misc to **IEEE S&P 2026**, DOI 10.1109/SP63933.2026.00049. Removed VERIFY.
- `zkap`: the author list was checked against the USENIX page and is correct. Removed VERIFY and added the official URL.
- `llm4vuln`: replaced "Yuqiang Sun and others" with the full 8-author list and added arXiv:2401.16185. Removed VERIFY.
- `bridge-sok`: confirmed and added DOI 10.1109/ICBC56567.2023.10174993. Removed VERIFY.
- `mythril`: updated the URL to ConsenSysDiligence/mythril (the old one redirects).
- `sok-snark-bugs`: added the official URL. `groth16`: added volume and DOI. `plonk`: added the ePrint URL.
- Added DOIs to slither, echidna, gptscan, egele-crypto-misuse, cryptoguard and flashboys.
- Added access dates to every @misc repository entry. Removed the "VERIFY before submission" header.
- Kept every existing key, since intro, background and evaluation cite them.
- Added 36 new entries (see table), including CogniCrypt.

## Text claims corrected in related.tex

- `llm4vuln` was cited for "agents that explore code with tools", but it is an evaluation framework. The agent claim now cites A1, PoCo and ReX.
- Egele and CryptoGuard were cited for "unsigned fields, missing domain separation, nonce reuse", but these are API-parameter
  misuse studies. Signature-specific claims now go to EIP-712, LASiR and the SSO study.
- The bridge sentence is now tied to the specific Wormhole case documented in [bridge-sok].
- The SmartBugs and Demystifying sentence was rewritten to give the exact figures (42% of annotated vulnerabilities; over 80% of exploitable bugs beyond tools).
- The SSO analogy was corrected from P2 (relying-party binding) to P1 (unsigned email), as read in the PDF.
- The tracker sentence now states what the tracker says (a replayed proof with a changed, optimized-out public input). It no longer presents Tornado's safeguard as a flaw.
- "classify flaws by where the faulty code lives" now reads "by layer, root cause or broken proof-system property", to cover ePrint 2024/514.
- A1 is no longer said to use Foundry; it validates by execution.
- Removed `\TODO{W4}`.

## Build check

Command as specified in the lane brief (docker `authguard-paper-tex:2022`, pdflatex/bibtex/pdflatex×2).
Result after the final edits: 0 undefined citations in `build/main.log`, `warning$ -- 0` in `build/main.blg`, 54 bibitems. The PDF grew from 12 to 14 pages total; References start on p12 and appendices on p14, so the body ends on p12, at or below the limit of 13. Related Work runs from p11 to p12, about 0.8 pages.

## Recommended next task

RV11 mapping: label each of the 103 binding findings with the SoK category it would receive (V4 PUD, V5, V6, V7, V12 Unsafe Verifier, circuit-layer, or none). Report a contingency table of P1–P5 × SoK category. Done when every finding has exactly one SoK label, the table is in `dataset/` with its source commit, and related.tex states the measured overlap ("k of 103 fall in the SoK integration layer").

## Open items

- RV11 asks for a related-work matrix (layer / spec source / evidence / real-world eval) and a mapping of
  our 103 findings onto SoK V4–V7/V12. Not done: it needs dataset labels, which are outside this lane's walls.
- `zkvm-study` (ASE 2026): only metadata and a search-index abstract were read. Read the full text before
  claiming anything specific about it beyond "studies zkVM vulnerabilities".
