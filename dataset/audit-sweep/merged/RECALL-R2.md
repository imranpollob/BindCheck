# Sweep recall against the earlier R2 audit census

The R2 census (`origin/sprint/R2:reports/R2/findings.csv`, 54 AI-labelled findings from 68 audits) was compiled independently of this sweep and hidden from every sweep agent. Here it serves as an external check of what the sweep missed. Generated 2026-11-22 by the orchestrator.

| Outcome | Count | Notes |
|---|---:|---|
| Found and logged (KEEP 14, BORDERLINE 15, DROP 11) | **40** | The DROPs are mostly definition differences. Example: R2 labels reentrancy before the nullifier write as P3; protocol v1 excludes it as `ORDERING-REENTRANCY`. |
| Correctly out of scope (non-EVM consumer) | 4 | DarkFi (1) and Tongo on Starknet (3). |
| **Screening error**: report wrongly marked OUT | 3 | Zellic Nori Bridge (Ethereum–Mina) was marked `NON-EVM`, but its Ethereum contract verifies SP1 proofs, so it should be IN. |
| **Finding-level miss**: report IN, finding not logged | 3 | Veridise SP1 V-SP1-VUL-004 and -008; Trail of Bits AZTEC v1 #8 (a Fiat–Shamir challenge of 0 or 1 accepts invalid proofs). |
| **Source gap**: auditor not in the source list | 4 | ABDK Railgun CVF-20/58/60 (ABDK was not a listed source; now added) and Zokyo Railgun #2 (Zokyo still pending in firms-2). |

**Recall on in-scope R2 findings: 40 of 50 = 80%.**

**Pattern in the misses.** Six of the seven screening and finding-level misses are **P4-type verifier-soundness issues**: recursion or vk binding, Fiat–Shamir, curve or subgroup checks. Agents tend to skip verifier-internal findings as "not about the consumer". This also explains why P4 looks rare in the candidate pool (3 KEEP). That rarity is at least partly a screening artifact.

**Corrective actions:**

1. Add ABDK as a source (assigned to firms-2).
2. Run a targeted P4 re-screen of all IN reports, and correct the Nori Bridge screen.
3. Re-run this recall check after both are done.

## Re-check after the rescreen lane (2026-11-22)

| Outcome | Count |
|---|---:|
| Found | **45** (Nori 3.1, 3.2 and 3.3 matched by content; R2 uses hash IDs) |
| Correctly out of scope (non-EVM) | 4 |
| Pending (source not yet swept) | 4: ABDK Railgun CVF-20, -58 and -60, and Zokyo Railgun #2 (firms-2 has ABDK and Zokyo queued) |
| True miss | 1: Veridise SP1 V-SP1-VUL-008 (the SP1VerifierGateway owner can route proofs to a malicious verifier) |

**Recall on in-scope R2 findings: 45/50 = 90%.** It rises to 49/50 if ABDK and Zokyo land.

**Caveat on the definition.** Most of the recovered P4 items are proof-system-soundness bugs (Fiat–Shamir or curve checks inside recursion verifiers). Whether they belong to the binding class is an open scope decision, flagged as `scope-question` in `candidates.csv` for the labeling guide to settle.

## Final check after rescreen-2 (2026-11-23)

| Outcome | Count |
|---|---:|
| Found | **49** |
| Correctly out of scope (non-EVM) | 4 |
| True miss | 1: Veridise SP1 V-SP1-VUL-008 (a trusted gateway owner can route proofs to a malicious verifier; arguably admin trust, not binding) |

- **Recall on in-scope R2 findings: 49/50 = 98%.**
- The 49 include ABDK Railgun CVF-58 and CVF-60. The sweep logs the same mechanisms as CVF-59 ("Snark pairing check always returns true") and CVF-61 ("Proof elements not checked to be curve points"), so the numbering differs between the two lists.

**Note on text extraction.** 173 of 220 ABDK PDFs extract as letter-spaced, garbled text with `pdftotext`. All ABDK reports were re-scanned with `pdftohtml -xml`: only 2 OUT reports showed ZK signals (a Polyhedra whitepaper review and Zcoin Lelantus), and both are correctly OUT. All 27 ABDK KEEP and BORDERLINE quotes verify against the `pdftohtml` text, ignoring spaces.
