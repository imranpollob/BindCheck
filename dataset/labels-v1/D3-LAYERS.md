# D3: Which artifacts are needed to decide each binding flaw

**Status: AI-proposed, pending author check.** The tags were proposed by the datajobs lane (Claude) from the Pass 1, report-only label records. No author or rater has reviewed them yet. A stratified spot-check of 15 items is listed at the end of this file.

## 1. Tagging rule (frozen 2026-11-25 before tagging)

**Disclosure.** Before writing this rule, the lane had seen the full label records of six items: L001, L003, L007, L008, L010 and L011. Any later change to the rule is logged in §1.4 as a dated amendment.

### 1.1 Question

What is the **minimal set of artifacts** a reviewer must read to establish C3 (the effect-relevant value is not fixed by the accepted proof), given the report's description of the flaw? "Contract" means the on-chain consumer, including the call site that assembles public inputs for the verifier. "Circuit" means the circuit or statement, including its public-input/output declaration.

### 1.2 Tags (apply the first that fits, in this order)

1. **VERIFIER/OFFCHAIN.** The flaw is decided in neither the consumer contract nor the application circuit. It lives in one of these places:
   - the verifier or proof system: a forgeable verifier, a transcript or Fiat–Shamir flaw, a broken pairing check, or a verifier-key/setup problem;
   - a zkVM or recursion framework, where the guest program is not application code;
   - off-chain prover, SDK, library, parser or precompile code that produces the "verified" value, such as L003's DKIM parsers and L008's client executor.

   PSS = Y items land here almost by construction, so the core-87 cross-tab is the informative one.
2. **CONTRACT-ONLY.** The flaw can be seen from the consumer and its verify call site alone, under the report's description of what the statement exposes. Typical cases:
   - the effect-relevant value is never passed to the verifier;
   - the contract fills it in after verification;
   - a root, nullifier, chain or context check against stored state is missing;
   - a replay or front-running redirect happens because the contract uses `msg.sender` or a caller argument rather than the proven value.
3. **CIRCUIT-ONLY.** The consumer passes the value through correctly, but the statement leaves it unconstrained, unexposed, or not tied to the witness data it should commit to. The circuit alone shows the gap.
4. **BOTH.** Deciding requires comparing the two sides. Typical cases:
   - an ordering, encoding or width mismatch between the public-input layout and the consumer (P5);
   - a value the consumer relies on but whose binding depends jointly on what the circuit exposes and what the contract checks, where the report attributes the gap to the interface rather than to one side;
   - the report states that the fix could be on either side.

### 1.3 Tie-breakers

- If the report says the value "is not a public input" and the contract uses a caller-supplied copy, tag **CONTRACT-ONLY** when the report frames the fix as a contract check, and **BOTH** when the fix requires adding a public input to the circuit as well.
- When the evidence is thin (no quote, a vague rationale), tag the most likely layer and set `confidence = low`.
- `evidence_fields` lists the label fields that were non-empty, and therefore available, for the item: T (title), Q (auditor quote), E (effect), U (unbound value), R (rationale). It does not record which field was decisive.

### 1.4 Amendments

**A1 (2026-11-25, during tagging; clarifications forced by edge cases, no tag was changed after the cross-tab was seen):**

- **(a)** For zkVM applications, the application's guest program is the "circuit/statement". The zkVM, the recursion stack and the SDK verifiers are VERIFIER/OFFCHAIN. Applied to L023, L091, L119, L131, L179 and L186.
- **(b)** A calldata or interface mismatch between the consumer and the *on-chain* verifier contract, where verifier soundness is not at issue, is CONTRACT-ONLY. Applied to L040.
- **(c)** When the only consumer is off-chain and the missing check is in that consumer, the tag is VERIFIER/OFFCHAIN. Applied to L124.
- **(d)** A lossy encoding performed entirely inside the consumer, with no circuit-layout mismatch, is CONTRACT-ONLY rather than BOTH. Applied to L013 and L089.

**A2 (2026-11-25, written after the cross-tab was first seen, in response to review):**

- **The conflict.** §1.2(2) sends `msg.sender` and caller-argument redirects to CONTRACT-ONLY. The §1.3 tie-breaker sends "the fix adds a public input" to BOTH. The two rules conflict: L017 was tagged CONTRACT-ONLY although its report fix adds the sender to the proof inputs, while L001 was tagged BOTH.
- **Precedence.** The tag follows where the flaw is *decided*, not where the fix lands. §1.2 wins, and the §1.3 tie-breaker applies only when the report does not say what the statement exposes, so that reading the circuit is needed to know the value is absent (as for L001). No primary tag was changed.
- **Sensitivity column.** `alt_tag_fix_side` re-tags as BOTH the 15 CONTRACT-ONLY items whose report remedy binds the value into the statement: L010, L015, L017, L035, L041, L043, L059, L066, L074, L088, L094, L102, L106, L126 and L193. All 15 are core. The cross-tab reports both readings, and the true split under a fix-side reading lies between them.

## 2. Procedure and provenance

- **Inputs.** Only the Pass 1 report-only fields of `LABELS-v1.csv`: finding title, auditor quote, effect, unbound value and rationale. No project source code, Pass 2 file, `labeling-a`, `mvp/` or mutant material was opened. The reading of test-split label text is logged in `audit-sweep/EXPOSURE.md` (2026-11-25 datajobs entry).
- **Output.** One row per binding item in `D3-layers.csv`. The columns are `layer_tag`, `confidence` (high/medium/low), `evidence_fields` (which label fields were non-empty), a one-line `rationale`, and `tag_source`.
- **Cross-tabs.** They are generated by the command below (Python 3.12.3, exit 0). Pattern totals are asserted equal to CHARACTERIZATION.md (23/23/15/33/7/2). Severity buckets use `characterize.py`'s `sev()`.

```
python3 -I /home/pollmix/Coding/bc/BindCheck/dataset/labels-v1/analysis/d3_crosstab.py
```

## 3. Results

<!-- generated by analysis/d3_crosstab.py; do not hand-edit this block -->
- Input: `D3-layers.csv` sha256 `690f4607c3877ed25d42bda510d14d1523efc031b5d79d6d8f10f7717b27aa1d`; `LABELS-v1.csv` sha256 `606a8745a977e0628e4e0d9ba213a7be420898730b422e6ec918e140c4c29665`

#### All binding: layer x pattern (n = 103)

| layer | P1 | P2 | P3 | P4 | P5 | OTHER | total | % |
|---|---|---|---|---|---|---|---|---|
| CONTRACT-ONLY | 18 | 9 | 6 | 6 | 4 | 0 | 43 | 42% |
| CIRCUIT-ONLY | 5 | 6 | 8 | 0 | 0 | 1 | 20 | 19% |
| BOTH | 0 | 5 | 0 | 0 | 2 | 0 | 7 | 7% |
| VERIFIER/OFFCHAIN | 0 | 3 | 1 | 27 | 1 | 1 | 33 | 32% |
| total | 23 | 23 | 15 | 33 | 7 | 2 | 103 | |

#### Core (PSS != Y): layer x pattern (n = 87)

| layer | P1 | P2 | P3 | P4 | P5 | OTHER | total | % |
|---|---|---|---|---|---|---|---|---|
| CONTRACT-ONLY | 18 | 9 | 6 | 6 | 4 | 0 | 43 | 49% |
| CIRCUIT-ONLY | 5 | 6 | 8 | 0 | 0 | 1 | 20 | 23% |
| BOTH | 0 | 5 | 0 | 0 | 2 | 0 | 7 | 8% |
| VERIFIER/OFFCHAIN | 0 | 3 | 1 | 11 | 1 | 1 | 17 | 20% |
| total | 23 | 23 | 15 | 17 | 7 | 2 | 87 | |

#### All binding: layer x auditor severity (n = 103)

| layer | Critical | High | Medium | Low | Info | Unrated | total | % |
|---|---|---|---|---|---|---|---|---|
| CONTRACT-ONLY | 9 | 13 | 3 | 3 | 0 | 15 | 43 | 42% |
| CIRCUIT-ONLY | 10 | 2 | 1 | 1 | 0 | 6 | 20 | 19% |
| BOTH | 1 | 2 | 1 | 2 | 1 | 0 | 7 | 7% |
| VERIFIER/OFFCHAIN | 12 | 7 | 1 | 0 | 0 | 13 | 33 | 32% |
| total | 32 | 24 | 6 | 6 | 1 | 34 | 103 | |

#### Core: layer x auditor severity (n = 87)

| layer | Critical | High | Medium | Low | Info | Unrated | total | % |
|---|---|---|---|---|---|---|---|---|
| CONTRACT-ONLY | 9 | 13 | 3 | 3 | 0 | 15 | 43 | 49% |
| CIRCUIT-ONLY | 10 | 2 | 1 | 1 | 0 | 6 | 20 | 23% |
| BOTH | 1 | 2 | 1 | 2 | 1 | 0 | 7 | 8% |
| VERIFIER/OFFCHAIN | 7 | 2 | 1 | 0 | 0 | 7 | 17 | 20% |
| total | 27 | 19 | 6 | 6 | 1 | 28 | 87 | |

#### All binding: layer x tier (n = 103)

| layer | FULL | LIGHT | PSS | total | % |
|---|---|---|---|---|---|
| CONTRACT-ONLY | 16 | 27 | 0 | 43 | 42% |
| CIRCUIT-ONLY | 4 | 16 | 0 | 20 | 19% |
| BOTH | 2 | 5 | 0 | 7 | 7% |
| VERIFIER/OFFCHAIN | 4 | 6 | 23 | 33 | 32% |
| total | 26 | 54 | 23 | 103 | |

#### All binding: layer x confidence (n = 103)

| layer | high | medium | low | total | % |
|---|---|---|---|---|---|
| CONTRACT-ONLY | 22 | 19 | 2 | 43 | 42% |
| CIRCUIT-ONLY | 11 | 8 | 1 | 20 | 19% |
| BOTH | 2 | 4 | 1 | 7 | 7% |
| VERIFIER/OFFCHAIN | 25 | 8 | 0 | 33 | 32% |
| total | 60 | 39 | 4 | 103 | |

#### Core, low-confidence tags removed: layer x pattern (n = 83)

| layer | P1 | P2 | P3 | P4 | P5 | OTHER | total | % |
|---|---|---|---|---|---|---|---|---|
| CONTRACT-ONLY | 17 | 9 | 5 | 6 | 4 | 0 | 41 | 49% |
| CIRCUIT-ONLY | 5 | 6 | 7 | 0 | 0 | 1 | 19 | 23% |
| BOTH | 0 | 4 | 0 | 0 | 2 | 0 | 6 | 7% |
| VERIFIER/OFFCHAIN | 0 | 3 | 1 | 11 | 1 | 1 | 17 | 20% |
| total | 22 | 22 | 13 | 17 | 7 | 2 | 83 | |

- Core decidable from the consumer contract alone: 43/87 (49%).
- Core needing the circuit/statement (CIRCUIT-ONLY or BOTH): 27/87 (31%).
- Core needing both sides compared: 7/87 (8%).
- Core needing the consumer contract at all (CONTRACT-ONLY or BOTH): 50/87 (57%).
- Core decided in verifier/off-chain code: 17/87 (20%).
- Alternative reading (amendment A2 sensitivity: a CONTRACT-ONLY item whose report fix adds the value to the statement counts as BOTH): CONTRACT-ONLY 28/87 (32%), CIRCUIT-ONLY 20/87 (23%), BOTH 22/87 (25%), VERIFIER/OFFCHAIN 17/87 (20%).

#### Core, alternative fix-side reading: layer x pattern (n = 87)

| layer | P1 | P2 | P3 | P4 | P5 | OTHER | total | % |
|---|---|---|---|---|---|---|---|---|
| CONTRACT-ONLY | 4 | 8 | 6 | 6 | 4 | 0 | 28 | 32% |
| CIRCUIT-ONLY | 5 | 6 | 8 | 0 | 0 | 1 | 20 | 23% |
| BOTH | 14 | 6 | 0 | 0 | 2 | 0 | 22 | 25% |
| VERIFIER/OFFCHAIN | 0 | 3 | 1 | 11 | 1 | 1 | 17 | 20% |
| total | 23 | 23 | 15 | 17 | 7 | 2 | 87 | |

- FULL tier: CONTRACT-ONLY 16, CIRCUIT-ONLY 4, BOTH 2, VERIFIER/OFFCHAIN 4 (n = 26).

### Author spot-check sample (15 items; seed 20261125; floor 3 per tag, remainder to the largest tags)

| item | tier | pattern | layer tag | conf. | rationale |
|---|---|---|---|---|---|
| L010 | FULL | P1 | CONTRACT-ONLY | medium | Market pays batch.prover, which the app proof does not cover; front-run redirect visible at the consumer |
| L088 | LIGHT | P1 | CONTRACT-ONLY | medium | Pool fee tier/relayer fee are caller arguments not fixed by the proof (front-run) |
| L123 | LIGHT | P4 | CONTRACT-ONLY | high | Wrapper forwards caller-chosen calldata to the verifier via low-level call; any true-returning getter passes |
| L173 | LIGHT | P4 | CONTRACT-ONLY | medium | Single-variant attestation contract skips the KZG commitment check on model weights |
| L023 | FULL | P1 | CIRCUIT-ONLY | high | SP1 guest commits block heights from inputs without checking them against the verified headers |
| L091 | LIGHT | P2 | CIRCUIT-ONLY | medium | Guest balance_of.rs commits journal values without fixing which contract was queried |
| L164 | LIGHT | P3 | CIRCUIT-ONLY | low | Two input nullifiers not required to be distinct (layer not stated; thin evidence) |
| L179 | LIGHT | P2 | CIRCUIT-ONLY | medium | L1 config hash in the guest omits fields that change derived L2 blocks |
| L007 | FULL | P5 | BOTH | high | Public-input order mismatch: circuit declares state,pinCode; contract assigns them swapped |
| L063 | LIGHT | P5 | BOTH | high | Contract flattens tokenIds and nullifiers into one input array differently from the circuit layout |
| L172 | LIGHT | P2 | BOTH | medium | Genesis root/fork versions must be exposed in the journal and checked by the contract |
| L050 | FULL | P2 | VERIFIER/OFFCHAIN | medium | vlayer framework does not expose chain ID/ChainSpec in CallAssumptions (prover-side framework) |
| L124 | LIGHT | P3 | VERIFIER/OFFCHAIN | medium | Nullifiers exposed by the selective-transparency proof are not checked by the off-chain consumer (amendment A1-c) |
| L226 | PSS | P4 | VERIFIER/OFFCHAIN | high | Verifying-key hash omits attacker-changeable fields |
| L240 | PSS | P4 | VERIFIER/OFFCHAIN | high | Proofs not hashed into the batch challenge |

## 4. Reading the results

- **Scope disagreement.** `paper/eurosp/TODO.md` (D3) and the `study.tex` TODO ask about *FULL-tier* items coded from *Pass 2* (code) evidence. This lane's brief was all 103 items from report text only, and the Pass 2 file is restricted, so this file follows the brief. The FULL-tier row (n = 26) is given separately so the orchestrator can use either framing.
- **The `\DEMO` placeholder in `study.tex` is not supported.** It reads "61% both; 23% consumer alone". On report evidence, the core 87 split as:

  | reading | contract-only | circuit-only | both | verifier/off-chain |
  |---|---|---|---|---|
  | primary | 43 (49%) | 20 (23%) | 7 (8%) | 17 (20%) |
  | fix-side (A2) | 28 (32%) | 20 (23%) | 22 (25%) | 17 (20%) |

  FULL tier, primary reading: 16 of 26 contract-only, 2 of 26 both.
- **The shares depend on the report's description.** The rule asks for the *minimal* artifact set *given the report's description* of what the statement exposes. For P1 front-running and missing-context items, the report tells the reader the value is not in the public inputs, and the contract alone then shows the flaw. A reviewer without the report would also have to read the public-input declaration. The primary shares therefore lower-bound the cross-layer need of an analyst who starts without the report; the fix-side reading is closer to that analyst.
- **Pattern structure (core 87, primary reading):**
  - P1 is mostly contract-only (18/23), but 14 of those 18 become BOTH under the fix-side reading.
  - P4 is mostly verifier or proof-system code (11/17 core; 27/33 of all 103).
  - P2 is spread across layers (contract 9, circuit 6, both 5, verifier/off-chain 3).
  - P3 leans circuit-side (8/15).
  - BOTH under the primary reading is P2 5 and P5 2. P5's other 5 items are 4 contract-only (encoding or interface flaws inside on-chain code) and 1 verifier/off-chain.
- **Confidence.** 4 of the 103 tags are low-confidence. Removing them moves the core shares by at most 1 point (BOTH 8% → 7%).
- **Seam for the author check.** All 4 FULL-tier VERIFIER/OFFCHAIN items (L003, L008, L030, L050) are framework or library code (vlayer, SP1 contract-call), not verifier soundness. L008 and L050 are close in mechanism to L091 and L131, which are CIRCUIT-ONLY under A1(a) because the guest is application code. The author should decide which side of that line they fall on.
- **Author check.** The 15-item seeded, stratified sample above should be spot-checked. If the author disagrees with more than 2 of the 15, re-tag all items under a revised rule (log it as amendment A3) before any number enters the paper.

## 5. Paper-ready sentences (for §4, "Which layers are needed"; AI-proposed tags pending author check)

Given the audit report's description of what the proved statement exposes, 43 of the 87 core binding findings (49%) can be decided from the consumer contract alone, 20 (23%) from the circuit alone and 7 (8%) only by comparing the two. The remaining 17 (20%) lie in verifier, recursion or off-chain framework code. If a finding counts as cross-layer whenever its reported fix adds the missing value to the statement, the contract-only share falls to 32% (28 of 87) and the both share rises to 25% (22 of 87). Either way, a checker confined to one application layer can decide at most about half of the core class.
