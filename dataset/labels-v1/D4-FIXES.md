# D4: How binding flaws were (or would be) fixed

**Status: AI-proposed, pending author check.** The datajobs lane (Claude) proposed these classes from report-derived text already in the dataset. No source code, fix diff, Pass 2 file or `labeling-a` was opened. The local report copies recorded in `in_reports.csv` (`local_path` under `/tmp`) no longer exist, so the evidence consists of these fields:

- `LABELS-v1.csv`: auditor quote, intended policy, rationale, notes and `fix_note`;
- `audit-sweep/merged/all_findings.csv`: quote, mechanism, `fix_source` and notes;
- the `notes`, `fix_commit_source` and `fix_confidence` fields of `audit-sweep/acquire*/acquisition.csv`;
- the triage reasons.

## 1. Rule (frozen 2026-11-25 before reading the fix evidence)

**Disclosure.** The lane had already read the D3 fields (title, quote, effect, unbound value, rationale) for all 103 items. The fix-specific fields (`fix_source`, acquisition notes, triage reasons, `fix_note`) were unread when this rule was written.

### 1.1 Unit and question

There is one row per binding item (103; core = PSS ≠ Y, 87). The question: what change does the report (or the recorded fix description) say removes the flaw? If no fix is stated, what change is directly implied by the missing element the report names?

### 1.2 Classes (the first that fits, in this order)

1. **PIN/CHECK-VERIFIER.** The fix pins which verifier, verifying key, program ID or vk root is accepted. It also covers a fix that makes the consumer actually call the verifier, or check its return value, pairing result or call status.
2. **ENCODING.** The fix adds a canonical-encoding, range (field-modulus, bit-width), length or ordering check, or corrects the public-input layout or order between the parties. This includes range checks on nullifiers (x vs x + p).
3. **REPLAY-KEY.** The fix makes a statement-derived replay key unique and enforced. Examples: a deterministic nullifier, a nullifier tied to the spent note or key, distinct nullifiers within one action, a nonce, a corrected replay-guard key, or a requirement that the slot or epoch advance.
4. **CONTEXT-CHECK.** The fix binds or checks a context value. Examples: chain ID, contract or verifier address, domain, Merkle or state root, previous state, epoch or timestamp, configuration or config hash, block anchor. It counts whether the value is added to the public inputs or compared against stored state.
5. **ADD-TO-STATEMENT.** The fix adds an effect-relevant, non-context value to the public inputs or a hashed commitment. Examples: recipient, amount, sender, fee, pool, relayer, output commitments, request ID.
6. **OTHER/UNKNOWN**, with a mandatory `fix_subtype`:
   - `constrain-value`: a circuit constraint ties a value the statement already exposes to the authenticated witness data. This is ZK-specific. A signature always fixes what is signed, so there is no signature analogue.
   - `proof-system`: a transcript, Fiat-Shamir, aggregation or recursion soundness repair.
   - `logic`: application logic, such as a default config or a skipped branch.
   - `unknown`: the evidence names neither a fix nor a single missing element.

### 1.3 Fields

- **`fix_class`.** One of the six classes above.
- **`fix_subtype`.** Short free text; mandatory for OTHER/UNKNOWN.
- **`fix_evidence`:**
  - **STATED**: a recommendation, remediation text or recorded fix description says what to change;
  - **IMPLIED**: no fix is stated, but the report names the single missing element, so the fix is its inverse;
  - **NONE**.
- **`secondary_class`.** Optional, when the report names two changes.
- **`confidence`.** high/medium/low.
- **`rationale`.** One line.

### 1.4 Signature-analogy test (pre-specified)

The paper claims binding flaws are the ZK analogue of signature misuse: "signing too little". The three textbook signature-misuse remedies are:

- sign every effect-relevant field → **ADD-TO-STATEMENT**;
- domain separation → **CONTEXT-CHECK**;
- a nonce or replay protection → **REPLAY-KEY**.

**Strict analogue share.** (ADD-TO-STATEMENT + CONTEXT-CHECK + REPLAY-KEY) / n.

**Broad analogue share.** This adds two classes to the strict set:

- **ENCODING**, which corresponds to signature malleability and non-canonical encodings;
- **PIN/CHECK-VERIFIER**, which corresponds to verifying against the right public key or checking the verify result.

`constrain-value` and `proof-system` have no signature analogue.

**Pre-specified criteria.** The analogy is **supported** for the core class if the strict share is at least 50% with a Wilson lower bound above 0.40. It is **partly supported** if the broad share is at least 50% but the strict criterion fails. Otherwise it is **not supported**. The test is reported for core 87, for all 103, and for STATED-only rows.

### 1.5 Amendments

**A1 (2026-11-25, during classification, before the cross-tab).** Several reports say a finding was acknowledged and not fixed (for example L015, L020, L041). A `fix_status` column was therefore added, with values FIXED, PARTIAL, NOT-FIXED or UNKNOWN, taken from the recorded status text. For a NOT-FIXED item, `fix_class` is the remedy the report implies, not a change that was made. `secondary_class` was never needed and is left empty. No class definition changed.

## 2. Procedure and provenance

- **Inputs.** Only the dataset fields listed at the top of this file. Acquisition notes include fix-commit *messages* and touched *file names*. No diff or source file was read. The reading of test-split records is covered by the 2026-11-25 datajobs entry in `audit-sweep/EXPOSURE.md`, which is updated for D4.
- **Output.** `D4-fixes.csv`, with one row per binding item. The columns are `fix_class`, `fix_subtype`, `fix_evidence`, `fix_status`, `confidence` and a one-line `rationale`.
- **Cross-tabs.** Generated by the command below (Python 3.12.3, exit 0):

```
python3 -I /home/pollmix/Coding/bc/BindCheck/dataset/labels-v1/analysis/d4_crosstab.py
```

## 3. Results

<!-- generated by analysis/d4_crosstab.py; do not hand-edit this block -->
- Input: `D4-fixes.csv` sha256 `fd835964d777da187c901244b74005ed2ce8f9772466d49879d699a8023f824f`; `LABELS-v1.csv` sha256 `606a8745a977e0628e4e0d9ba213a7be420898730b422e6ec918e140c4c29665`

#### All binding: fix class x pattern (n = 103)

| fix class | P1 | P2 | P3 | P4 | P5 | OTHER | total | % |
|---|---|---|---|---|---|---|---|---|
| ADD-TO-STATEMENT | 16 | 0 | 0 | 0 | 0 | 0 | 16 | 16% |
| CONTEXT-CHECK | 0 | 22 | 0 | 0 | 0 | 0 | 22 | 21% |
| REPLAY-KEY | 0 | 0 | 11 | 0 | 0 | 0 | 11 | 11% |
| PIN/CHECK-VERIFIER | 0 | 0 | 0 | 15 | 0 | 0 | 15 | 15% |
| ENCODING | 1 | 0 | 4 | 2 | 7 | 1 | 15 | 15% |
| OTHER/UNKNOWN | 6 | 1 | 0 | 16 | 0 | 1 | 24 | 23% |
| total | 23 | 23 | 15 | 33 | 7 | 2 | 103 | |

#### Core (PSS != Y): fix class x pattern (n = 87)

| fix class | P1 | P2 | P3 | P4 | P5 | OTHER | total | % |
|---|---|---|---|---|---|---|---|---|
| ADD-TO-STATEMENT | 16 | 0 | 0 | 0 | 0 | 0 | 16 | 18% |
| CONTEXT-CHECK | 0 | 22 | 0 | 0 | 0 | 0 | 22 | 25% |
| REPLAY-KEY | 0 | 0 | 11 | 0 | 0 | 0 | 11 | 13% |
| PIN/CHECK-VERIFIER | 0 | 0 | 0 | 15 | 0 | 0 | 15 | 17% |
| ENCODING | 1 | 0 | 4 | 2 | 7 | 1 | 15 | 17% |
| OTHER/UNKNOWN | 6 | 1 | 0 | 0 | 0 | 1 | 8 | 9% |
| total | 23 | 23 | 15 | 17 | 7 | 2 | 87 | |

#### Core, STATED fix evidence only (n = 21)

| fix class | P1 | P2 | P3 | P4 | P5 | OTHER | total | % |
|---|---|---|---|---|---|---|---|---|
| ADD-TO-STATEMENT | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 19% |
| CONTEXT-CHECK | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 19% |
| REPLAY-KEY | 0 | 0 | 2 | 0 | 0 | 0 | 2 | 10% |
| PIN/CHECK-VERIFIER | 0 | 0 | 0 | 6 | 0 | 0 | 6 | 29% |
| ENCODING | 1 | 0 | 0 | 1 | 1 | 0 | 3 | 14% |
| OTHER/UNKNOWN | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 10% |
| total | 7 | 4 | 2 | 7 | 1 | 0 | 21 | |

- OTHER/UNKNOWN subtypes (all / core): constrain-value 6/6, logic 2/2, proof-system 16/0.
- Fix evidence (core): IMPLIED 66, STATED 21.
- Fix status (core): FIXED 52, NOT-FIXED 7, PARTIAL 3, UNKNOWN 25.
- Confidence (all): high 76, low 1, medium 26.

#### Signature-analogy test (pre-specified, section 1.4)

| set | n | strict analogue: ADD+CONTEXT+REPLAY [Wilson 95%] | broad: + ENCODING + PIN/CHECK [Wilson 95%] | verdict |
|---|---|---|---|---|
| core 87 | 87 | 49 (0.56 [0.46, 0.66]) | 79 (0.91 [0.83, 0.95]) | supported |
| all 103 | 103 | 49 (0.48 [0.38, 0.57]) | 79 (0.77 [0.68, 0.84]) | partly supported |
| core, STATED only | 21 | 10 (0.48 [0.28, 0.68]) | 19 (0.90 [0.71, 0.97]) | partly supported |
| core, low-confidence removed | 86 | 49 (0.57 [0.46, 0.67]) | 79 (0.92 [0.84, 0.96]) | supported |
| core P1-P3 only | 61 | 49 (0.80 [0.69, 0.88]) | 54 (0.89 [0.78, 0.94]) | supported |

## 4. Reading the results

- **The diagonal is partly built in.** The cross-tab is almost diagonal: P1 → ADD-TO-STATEMENT, P2 → CONTEXT-CHECK, P3 → REPLAY-KEY, P4 → PIN/CHECK-VERIFIER or proof-system, P5 → ENCODING. That shape is partly circular. The patterns are defined by *what is unbound*, and 66 of the 87 core classes are IMPLIED, meaning they are read off as the inverse of the missing element the report names. On IMPLIED rows, the analogy test mostly restates the pattern definitions. The non-circular evidence is the 21 core rows with a STATED fix: the strict share is 10/21 = 0.48 [0.28, 0.68], and the broad share is 19/21 = 0.90 [0.71, 0.97]. Verdict on STATED rows: **partly supported**.
- **Core 87 against the pre-specified criteria.** The strict share is 0.56 [0.46, 0.66], so the criteria say **supported**, but this rests largely on IMPLIED rows (previous point). For all 103 the verdict is partly supported (0.48), because the 16 PSS items are proof-system repairs.
- **Fixes with no signature analogue:**
  - `constrain-value`, 6 core items: a value the statement already exposes must be tied to the authenticated witness. Examples are L023's block heights, L077's committee keys, and L169/L196's header and data hashes. This is the ZK-specific residue: a signature cannot cover a value without fixing it, but a circuit output can be exposed yet unconstrained.
  - `proof-system`, 16 items, all PSS = Y.
  - `logic`, 2 items.
- **Fix status (core).** 52 fixed, 3 partial, 7 not fixed (acknowledged or left to applications), 25 unknown. Fix status is report-recorded and was not checked against code.

## 5. Paper-ready sentences (for §4 "How they were fixed"; AI-proposed classes pending author check)

Fixes for the core binding findings mostly mirror signature-misuse remedies: 56% (49 of 87; Wilson 95% CI 46–66%) add the missing effect value to the statement, bind a context such as chain, contract, root or configuration, or make the replay key unique. Another 34% pin the verifier or program, check its result, or enforce a canonical encoding, the analogues of verifying against the right key and of signature malleability. On the 21 findings whose report or recorded fix states the change explicitly, the shares are 10 of 21 for the three classic remedies and 19 of 21 for the broader set. The ZK-specific residue is 6 findings fixed by constraining a value the circuit already exposed to its authenticated inputs, which has no signature counterpart, since whatever is signed is fixed.
