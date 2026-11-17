# Sprint plan: EuroS&P 2027 ("Proved, but Not Authorized")

Drafted 2026-11-17. Planning document only. Task prompts and the workflow live in
[`docs/orchestration/`](orchestration/README.md). The research contract, README and
task reports stay authoritative. This plan proposes contract revision 4 (task S0).

## Deadlines (EuroS&P 2027 CFP, AoE)

| Date | Event |
|---|---|
| Wed 25 Nov 2026 | Abstract registration (title, abstract, authors, topics, conflicts) |
| Wed 2 Dec 2026 | Paper submission: 13 pages of body, A4, EuroS&P template |
| 28 Jan 2027 | Early reject |
| 24 Feb – 1 Mar 2027 | Rebuttal |
| 18 Mar 2027 | Notification (accept or reject; there is no revision option) |

## What the paper must make reviewers learn

1. **A lens:** applications use a ZK proof as a signature over an action. Binding
   flaws are the classic signature failures one layer up. P1–P5 map to:
   - P1: an unsigned message field;
   - P2: missing domain separation;
   - P3: nonce reuse or canonicalization;
   - P4: a weak or rogue key;
   - P5: a message-format mismatch.
2. **A property:** the same proof and public inputs, applied to the same state,
   must always produce the same protected effects. This is the contract's
   authorization and coverage property, stated as one sentence.
3. **Evidence that the problem is real and current:** binding flaws confirmed by
   execution in audited or deployed applications, found by a frozen tool on
   held-out data.
4. **Where the flaws come from:** root causes in toolchains and templates,
   including generator defaults (γ = δ from uncontributed setups, credited to
   Zeto #186; the Honk canonicality lead if it confirms) and copied tutorial
   code. Each comes with a fix at the generator or template.

Each of the four needs evidence. The table below maps the remaining work to the
blockers recorded in `docs/PROJECT-CLOSEOUT-2026-11-11.md` §3.

| Closeout blocker | Fixed by |
|---|---|
| 1. No high-impact finding | S1 (Honk lead), S5 (impact-weighted held-out) |
| 2. Numbers rest on known γ = δ | S5, S7 (γ = δ demoted to a root-cause finding) |
| 3. No held-out reproduced flaw | S4 (oracle), S5 |
| 4. Weak benchmark | S6 (seeded mutations into real repaired apps) |
| 5. No recall or comparison | S6 |
| 6. Novelty unclear | S8 (novelty table; the lens, the oracle and circuit queries) |
| 7. Paper unfinished | S8 |

## Untouched held-out pool

Dataset v2 has 1,384 EVAL-only in-scope families. The 278 used by the freeze-2
run are spent and are now DEV. That leaves **1,106 families never analyzed**:

| Maturity label (heuristic) | Circom | Noir | Other |
|---|---:|---:|---:|
| audited-production | 113 | 32 | 3 |
| deployed-address-in-docs | 169 | 67 | 7 |
| hackathon-student | 16 | 4 | 2 |
| unclassified | 462 | 176 | 55 |

The **391 audited or deployed families** become the held-out v3 population
(S5). Rule: any family touched while investigating the Honk lead (S1) or while
fixing the analyzer is moved to DEV by a dated amendment **before** freeze 3.

## Tasks, gates and dates

### S0 — Contract revision 4 (Tue 17 Nov)

- **Record:**
  - the venue;
  - the new framing (signature lens, binding property);
  - the execution oracle as the precision instrument;
  - the freeze-3 change list;
  - the held-out v3 population and its exclusion rule.
- **Authorization:** record the user's scope authorization for local-fork replay
  of public transactions. Nothing is ever broadcast.
- **Done when:** the dated change-control entry is committed.

### S1 — Honk canonicality lead (Tue 17 – Thu 19 Nov)

1. **Read the generated verifier.** Using the pinned bb versions, check whether
   the generated `HonkVerifier` reduces or rejects public inputs ≥ the BN254
   scalar field.
2. **List the exposure.** List DEV-side Noir consumers that key a nullifier or
   replay map on the raw `bytes32` value.
3. **Reproduce.** On a local chain with an owned deployment, accept an honest
   proof. Then submit the same proof with the aliased input (x + r) and observe
   a second withdrawal.
4. **Check for prior knowledge:**
   - Aztec/Barretenberg changelogs, issues and security advisories;
   - Noir docs;
   - audit reports.
5. **Stop rule.** If a funded deployment is plausibly affected, stop and hand it
   to the advisor for private disclosure.

**Done when:** one of `CONFIRMED_NEW`, `CONFIRMED_KNOWN` (cite it),
`NOT_REPRODUCED` or `PATCHED_IN <version>`, with evidence.

### S2 — Freeze-3 analyzer fixes, DEV only (Wed 18 – Sat 21 Nov)

1. **P4:** already done. The BN254 G2 constant was fixed in freeze 2
   (`docs/FREEZE-2.md`); the note in `paper/zk/STATUS.md` §4a predates the fix.
2. **P5 false positives:**
   - exclude proof-array arguments;
   - model PLONK pairing-point inputs;
   - fix circuit selection.
3. **P1 and P3 false positives:** fix the 6/15 in each, from the Set H review
   cards.
4. **Canonicality rule:** add a P3 variant that fires when a verifier admits
   non-canonical inputs and the consumer keys state on the raw value. It covers
   both Groth16 and Honk verifier layouts. Today Honk layouts return UNKNOWN.
5. **zk-relational branch:** removed by the author on 17 Nov, so it is out of
   scope.

**Done when:** all regressions pass and the DEV rerun reports deltas.

### S3 — Circuit-targeted queries (Thu 19 – Sat 21 Nov)

For each security-critical signal the consumer uses, ask the circuit four
questions:

- Is the nullifier a deterministic function of committed secrets?
- Is the scope or external nullifier mixed into it?
- Is the public input actually constrained, or did the compiler optimize it
  away?
- Is the recipient or amount part of the statement?

**Done when:** at least one DEV case is shown where the verdict depends on the
circuit. Otherwise the paper narrows its "cross-layer" claim honestly.

### S4 — Execution oracle (Wed 18 – Sat 21 Nov)

Start from an accepted (proof, public inputs, calldata, pre-state) on a local
chain or a local fork. Mutate only what the proof does not fix:

- `msg.sender`;
- free calldata arguments;
- field aliases (x + r);
- resubmission;
- another contract or chain-id domain;
- the verifier key.

A finding is `E4-CONFIRMED` when the mutated transaction is accepted and a
protected effect differs: recipient, amount, nullifier set, mint or credential
state.

**Gate A, Sat 21 Nov:**

- the oracle reproduces Z1 and R1 to E4 automatically, with no hand steps; and
- S1 has a verdict.

### S5 — Freeze 3 and the held-out v3 run (Sun 22 – Wed 25 Nov)

1. **Freeze.** Declare `docs/FREEZE-3.md` with the content hash and tag.
2. **Preregister** (`reports/heldout-v3/PREREG.md`):
   - the 391 families and the exclusion amendment;
   - scoring rules;
   - confirmation means oracle E4, with human policy answers for intent.
3. **Run once.** Run the oracle on every VIOLATION.
4. **Triage** the confirmed findings by impact:
   - value at risk;
   - audit status;
   - deployment status (source reading only);
   - fork lineage.
5. **Get policy answers.** The human answers a policy question for each top
   finding, as was done for Z1/R1.

**Gate B, Wed 25 Nov (also the registration day).** Continue the sprint only if
either holds:

- at least one held-out E4-confirmed binding flaw in an audited or deployed
  application; or
- S1 is `CONFIRMED_NEW`.

Otherwise register nothing, switch to the long track, and keep the held-out v3
results.

### S6 — Comparison, recall and ablation (Thu 26 – Fri 27 Nov)

1. **Seeded-mutation recall:** inject P1/P3/P5 breaks into the repaired Z1, R1
   and held-out repaired applications. Each mutant must compile, stay reachable
   and change the property.
2. **Same-policy baseline:** Foundry property tests, following the D1P-32
   design.
3. **Circuit-withheld ablation.**
4. **Other tools:**
   - Circomspect and Picus, reported as structurally inapplicable;
   - ZKAP if obtainable, otherwise state why not;
   - ELSA if an API is available.

### S7 — Disclosure and ethics (from Gate B; must be sent before submission)

- **Who sends.** The advisor sends Z1, R1 and every new finding. Record the
  dates. The CFP allows disclosure while the paper is under submission.
- **Census.** The γ = δ census stays private. No addresses appear in the paper.
- **Required paper sections.** Write the harms discussion (required in the body)
  and the data-availability statement.

### S8 — Paper (Sat 28 Nov – Tue 1 Dec)

- Switch to the EuroS&P 2027 A4 template. The current draft uses US letter for
  S&P.
- Rewrite around the four lessons above. Close every `\MISSING`.
- Add the novelty table: SNARK SoK, ZKAP, Circomspect, Picus, zkFuzz, CIVER,
  ELSA, Coda.
- Disclose:
  - AI use (in acknowledgments, with sections named);
  - the author-rater;
  - development-case origins.
- Prepare an anonymized artifact via Anonymous GitHub (GitHub itself is not
  allowed for review).

**Wed 2 Dec:** final consistency pass and submit.

## Paper outline (13 pages)

1. **Introduction:**
   - Figure 1: one real accepted proof redirects the payout;
   - the lens;
   - the four lessons;
   - the headline numbers.
2. **Background:** ZK applications and generated verifiers.
3. **Binding as a signature:**
   - the property;
   - P1–P5 mapped to signature failures;
   - grounding in the SoK and incidents.
4. **BindCheck:** cross-layer extraction, targeted circuit queries and the
   execution oracle.
5. **Evaluation:**
   - held-out v3 funnel;
   - E4 confirmation rate;
   - recall on seeded mutations;
   - baselines;
   - the circuit ablation;
   - cost.
6. **What we found:**
   - case studies;
   - root causes: generator defaults and template lineage;
   - repairs.
7. **Disclosure and ethics.**
8. **Lessons for toolchain authors and auditors.**
9. **Related work**, with the novelty table.
10. **Limitations.**

## Long track (if Gate B fails)

Keep S0–S6. Add:

- raise the benchmark build rate;
- extend Noir/Honk depth;
- recruit two non-author raters who do not use AI.

Pick the venue once held-out v3 has results, and check that CFP's resubmission
rules then.
