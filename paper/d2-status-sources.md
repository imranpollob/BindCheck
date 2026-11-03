# D2 status manuscript source and evidence record

**Version:** D2-18-v1, 2 November 2026

**Purpose:** provenance for `paper/d2-status-draft.md`; this is not an
anonymous submission artifact and not evidence of submission readiness.

The manuscript uses two source classes. Repository reports and sealed raw
records support statements about BindCheck. Primary papers, publisher or
official conference pages, and official artifacts support related-work and
venue statements. A failed installation or inaccessible full text is recorded
as an access limit, never as evidence about a method.

## Repository evidence

| Evidence | Role in manuscript | SHA-256 |
|---|---|---|
| `docs/research-contract.md` | Controlling thesis, threat model, P/O/E semantics, evidence ladder, capability gate | Read as the controlling revision-3 contract; hash is deliberately not copied because this living authority may be updated only through its own change control |
| `paper/draft.md` | Preserved D1P-P07 historical manuscript snapshot; not edited by Step 18 | `d8aa536992f9391b19405836796e4620a639dc79d191c404eb99140de6b77217` |
| `docs/d2/claim-ledger-v1.json` | D2-03 claim audit through D2-01 | `203138460143fd31446e2550c93142cf0874fbc24feed1ae9f57d2d23f13a405` |
| `docs/d2/related-work-matrix-v1.json` | D2-03 primary-source related-work audit | `c3a31ab52e3d2e552ef23e3db73a1ae35b83814618881b68fda669e5f9dcedec` |
| `reports/D2-01.md` | Integrated exposed-development interface, versioned counts, Payy layers, and independent-attempt reconciliation | `ee13591c20fc4078ac71ce720b53ff2c1af7e51fa50f0a974fe4a2a6a74cba3f` |
| `reports/D2-03.md` | Claim corrections and closest-work positioning | `4b053390b1269dd7d1a47c7c374c768ee58c8fc532cc5f524f4f3ac9f6d844f3` |
| `reports/D2-04.md` | Taxonomy preparation and missing human study | `09d62d959c1a35be1eae515f0d23f18db73a6c59d0f5e324a716fcd36c93e811` |
| `reports/D2-06A.md` | Internal-arm and transformation construction; no score | `daf6fbe1c00c2184f541b09d4cf5cbe6eadb1aaf2903a742c53113d7d364c321` |
| `reports/D2-06B.md` | External inventory and same-policy smoke; no score | `465ae8a9e91ee5008ef1ac00dfe2fcf48dd33d2768db81e909cabc4bf6fe4240` |
| `reports/D2-07.md` | Gate A `INCONCLUSIVE`, four blockers, zero score rows | `fcdff01dbadade6f7f28116e46ee2c6016fb2945767492c822acaef87a60f07a` |
| `reports/D2-08.md` | Compiler-backed identity prototype, mechanical only | `aaca4aa036a0604febd6869604e8dfcfc3709a72a15c8fa588717309316fd2cd` |
| `reports/D2-09.md` | Authorization-boundary prototype, synthetic mechanical fixture only | `f7254e4ccb510a8ccfea9954cfd341c81620084147159a81dfa52c3f6595cf03` |
| `reports/D2-10.md` | Corrected typed-extraction prototype and authoritative run-02 interpretation | `848acceef83d32d5054e37686ff5bc3b94baa45c5618490a0fe8e41bb9db018a` |
| `protocols/d2/d2-10-typed-extraction-v2.json` | Corrected authoritative Step 10 protocol | `910ce6464a947fa552be08d34a596d97b179669401305adc577676d5172ce3ec` |
| `results/raw/D2-10/run-02/run-summary.json` | Corrected Step 10 counts and effective result | `0ebf8ca1f555701a6cbc942b0140df1440e7e5e60eb4daec87fd4bffb1dc42ab` |
| `results/raw/D2-10/run-02/content-seal-v1.json` | Corrected Step 10 content seal, independently replayed 9/9 | `c5bb3163283c7b16a0d341067c6f2c3f8fa9965d85ab13dc761d4e948fcf21e6` |
| `reports/D2-11-14-dependency-audit.md` | Public read-only record that Steps 11-14 were not executed and Gate B was not evaluated | `b2210759f71ed4a2fb323d933d7e517a1043d20f94c5b5150cb84a2baff52b96` |
| `protocols/d2/d2-11-14-dependency-disposition-v1.json` | Machine-readable Steps 11-14 dependency disposition | `d2acbf45720baf425fc7b71847b75de1db48195b1ca4a4604aaa0e069c6fdf78` |
| `reports/D2-15-17-readiness-audit.md` | Public read-only record that Steps 15-17 were not executed and Gate C was not reached | `4734b3f269999e2042779b091c069eac1813f86281a1314d19a48a62debf7cdd` |
| `protocols/d2/d2-15-17-readiness-v1.json` | Machine-readable Steps 15-17 non-execution/readiness disposition | `15406a13e1f3a03f58e4788d75445f1cc5e665afa63fd3a36a5d9e59fd8f4d54` |

The earlier Step 10 v1 protocol and `run-01` remain preserved but are
superseded and non-authoritative. They are not used for manuscript claims.

## Official venue sources

| Source | Inspected statements | Access status |
|---|---|---|
| [IEEE S&P 2027 Call for Papers](https://sp2027.ieee-security.org/cfpapers.html) | Cycle 2 dates and AoE rule; complete abstract/author/ORCID/COI lock; anonymity; artifact-repository freeze; ethics and generative-AI fields; page limit; US-letter IEEEtran 1.8b `conference,compsoc`; 24-hour draft responsibility | Official page inspected 2 November 2026 |
| [IEEE S&P 2027 Call for Artifacts](https://sp2027.ieee-security.org/cfartifacts.html) | Optional post-acceptance artifact evaluation, permanent repository expectation, and availability/functionality/reproduction criteria | Official page inspected 2 November 2026 |

The official CFP gives the second-cycle abstract deadline as 10 November 2026
and paper deadline as 17 November 2026, both 23:59:59 AoE. The abstract must
be full and complete and must include the complete author list with ORCIDs and
conflicts. Title, abstract, and author list cannot change after registration.

## Primary related-work sources

### ZKAP

- [USENIX Security 2024 paper](https://www.usenix.org/system/files/usenixsecurity24-wen_1.pdf)
- [Official USENIX presentation page](https://www.usenix.org/conference/usenixsecurity24/presentation/wen)
- [Official artifact repository](https://github.com/whbjzzwjxq/ZKAP)

The paper and artifact were inspected in the D2-03 audit. They support the
description of a circuit-dependence graph, nine detectors, and direct overlap
with unused-public-input analysis. They do not support an exhaustive claim
about what extensions are impossible.

### CIVER

- [IEEE publisher record](https://ieeexplore.ieee.org/document/10646792/)
- [Official artifact repository](https://github.com/costa-group/circom_civer)

The publisher record and artifact were inspected. The publisher full text was
not retrieved in the bounded audit. Claims are therefore limited to verified
metadata and artifact-documented properties and inputs.

### CCC-Check

- [Author-hosted primary paper](https://vdb.space/papers/zkp2026.pdf)
- [Official artifact repository](https://github.com/ArmanKolozyan/CCC-Check)

The author-hosted paper and artifact were inspected. The paper supports the
description of computation-constraint consistency through CirC IR and its
reported Noir, Circom, and ZoKrates frontend scope. It does not establish
compatibility with the pinned BindCheck targets.

### SmartAxe

- [Author-hosted primary paper](https://people.cs.umass.edu/~juanzhai/papers/fse24liao.pdf)
- [Official artifact index](https://github.com/InPlusLab/FSE24-SmartAxe)

The paper and artifact index were inspected. A runnable target setup was not
established in the retained comparison construction. That is an availability
or applicability limit, not evidence that SmartAxe misses a target.

### ELSA

- [Official ISSTA 2026 page and abstract](https://conf.researchr.org/details/issta-2026/issta-2026-research-papers/131/Augmenting-Multi-Technique-Static-Analysis-with-Large-Language-Models-A-Neuro-Symbol)
- Proceedings DOI: [10.1145/3832222](https://doi.org/10.1145/3832222)

The official page identifies Junxiang Wang, Fu Song, Miaomiao Zhang, Bowen Du,
and Rongcan Pei as the authors. Its abstract describes Ensemble LLM-assisted
Static Analysis, constraint-guided neural semantic reasoning, analyzer
conflict resolution, three open-source datasets, and self-constructed
ZKP-based smart contracts. A primary full paper, artifact, model, prompt,
benchmark, and stochastic protocol were not located or inspected. The DOI
identifier is recorded, but its resolver/full text was inaccessible during
the bounded audit. No stronger ELSA scope or comparison claim is authorized.

## Access and citation limits

- A title or abstract does not establish non-overlap.
- A failed build or unavailable frontend does not establish a miss.
- Repository descriptions support only the behavior they document.
- No source above establishes that BindCheck is first, unique, novel, or
  superior.
- Internal reports trace project evidence but are not substitutes for
  anonymized public citations in a future submission.
