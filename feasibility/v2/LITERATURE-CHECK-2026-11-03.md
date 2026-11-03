# Literature check: joint circuit + smart-contract analysis (3 Nov 2026)

Question: has anyone published a tool or study that analyzes a ZK circuit together with the smart contract that consumes its proofs (the "integration layer")?

**Answer: No such tool was found. Primary sources explicitly name it as an open gap, as recently as July 2026.**

## Primary evidence of the gap

| Source | What it says |
|---|---|
| Chaliasos et al., *SoK: What Don't We Know? Understanding Security Vulnerabilities in SNARKs*, USENIX Security 2024 (arXiv 2402.15293) | "there are currently no specific defenses developed for vulnerabilities in the integration layer of SNARK systems". Integration is excluded from its defense table "as no defense detects bugs in that layer". It suggests "multi-layer testing and verification techniques" targeting client code (Solidity/JS) and circuits as future work. Integration-layer bugs are a minority of its dataset (about 11 of 141 by impact table). It notes the nullifier mod-field double spend "is common at the integration layer". |
| Kolozyan, Sorger, Hicks, Chaliasos, *ZKP Security Tools and Verification*, arXiv 2607.23752 (July 2026) | Evaluates 6 tools on 70 Circom bugs, all circuit-level. Practitioners cite "major gaps around … integrations". Survey: system integration is rated hard to detect manually by 26% and adequately covered by tools by 5%. The paper leaves integration targets to future work. |

## Recent work: all circuit- or toolchain-only

- ZKAP (Wen et al., USENIX Security 2024): Circom circuit static analysis.
- CCC-Check (Kolozyan et al., IEEE S&P 2026; ePrint 2025/2120): computation–constraint inconsistencies; 15 new bugs in 6 projects. Circuits only.
- Zequal (ePrint 2025/916), zkFuzz (arXiv 2504.11961), zkCraft (arXiv 2602.00667): circuits.
- Liezz, *Lie to Me* (arXiv 2608.30648, Aug 2026): ZK DSL toolchain soundness.
- Picus/QED², CIVER, Circomspect: circuits.
- FreeVer (USENIX Security 2025): Polygon zkEVM free inputs, not application contracts.

## Adjacent

- 2026 arXiv protocol papers (e.g. zk-X509 2603.25190, ZK-ACE 2603.07974, 2606.20760) design-in public-input binding (sender, chain id, `address(this)`). They show awareness of the problem, but none is an analysis tool.
- Datasets: 0xPARC zk-bug-tracker; zkSecurity zkbugs (about 89 documented, about 22 reproduced; circuit-focused).
- Real 2026 incidents: Veil Cash (about 20 Feb 2026) and FoomCash (about $1.6–2.3M) were exploited through Groth16 verifiers deployed with γ = δ (a skipped setup step). Proofs were forged. This is a deployment/verification-configuration failure, outside the current threat model, but statically detectable in deployed verifiers.

## Caveats

- Not exhaustive: web search plus abstracts and two full texts. DBLP/ACM full-text search of 2025–26 CCS/NDSS/USENIX proceedings was not done, and audit firms' internal tools would not appear.
- The bug class is real but historically small (about 11/141 in the SoK), and exploited cases are rare. Yield of new bugs is the main risk; the feasibility scan must test it.
- Pattern viability: modern snarkjs verifiers reject public inputs ≥ the field modulus, which may already prevent the classic nullifier-aliasing bug in newer code. Choose patterns from scan evidence, not from history alone.
- Competition: the Chaliasos group authored both gap statements and is active (S&P 2026, July 2026 preprint). Expect others to target this gap.
