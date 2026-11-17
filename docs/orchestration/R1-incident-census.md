# R1 — Incident and bug-bounty census (2019–2026)

**Goal for the paper:** answer the reviewer question "Has this class of flaw
caused real harm?" with a complete, sourced table. The table must show:

- every public case where a contract accepted a zero-knowledge (ZK) proof but
  the action was not bound to the proved statement;
- every case where the verifier or deployment layer let proofs be forged;
- the money lost, or the money at risk, for each case.

This table supports the paper's motivation section and the gate decision on
21 Nov.

**Branch:** `sprint/R1`.

**Owns:** `reports/R1/`, `results/raw/R1/` (ignored).

**Must not edit:** any other path.

This is research only: reading public web pages, advisories and write-ups. Do
not run code against any system.

## Scope: what counts

Classify each case into exactly one class. Use these codes:

| Code | Class | Examples |
|---|---|---|
| P1 | Unbound effect: recipient, amount, asset, identity or credential not fixed by the proof | proof copied from the mempool with a new recipient |
| P2 | Unbound context: chain id, contract address, scope or external nullifier missing | proof valid on a second chain or a second app |
| P3 | Replay: nullifier not stored, not unique, not canonical (x and x + r), or replay key on malleable proof bytes | Semaphore #90, zkDrops, Nightfall, Aztec 2.0, StealthDrop, Groth16 malleability |
| P4 | Verifier layer: weak or wrong verifier key (γ = δ, uncontributed setup), wrong key deployed, test verifier left in production, verifier that always returns true | FoomCash, Veil Cash, ZKSwap |
| P5 | Public-input format: count, order or width mismatch between circuit, verifier and contract | — |
| OUT | Neighbour class, recorded but not counted: under-constrained circuit, proof-system bug, Fiat–Shamir bug | Tornado MiMC 2019, Frozen Heart, zkSync Era soundness |

## Sources to search (minimum)

**Incident databases:**

- rekt.news leaderboard and articles;
- DefiLlama hacks;
- SlowMist Hacked;
- the Immunefi "bugfix review" articles.

**Bug trackers and advisories:**

- 0xPARC `zk-bug-tracker` (read the whole page; it is long);
- GitHub security advisories (GHSA) for circom, snarkjs, Noir, Barretenberg,
  aztec-packages, gnark, Semaphore, Tornado Cash, World ID, Railgun and Privacy
  Pools.

**Security blogs:** zkSecurity, Trail of Bits, Veridise, Zellic, OpenZeppelin,
ChainLight, Dedaub, Spearbit, Nethermind.

**Known leads to confirm with primary sources:**

- FoomCash (Feb 2026, about $2.26M);
- Veil Cash (Feb 2026, about $5.7K, returned);
- ZKSwap (Jul 2025, about $5M);
- Xion PR #608 (Sep 2026, UltraHonk X + r);
- Semaphore #90;
- EIP-7520;
- Zcash 2018 counterfeiting.

## Rules

- **Primary source.** Prefer a primary source for each fact: a post-mortem, an
  advisory, a commit or an on-chain explorer page. Mark a fact that only has a
  secondary source as `SECONDARY`.
- **Loss amounts.** Keep the claimed loss separate from the confirmed loss.
  Record the recovered amount when known. Record the currency and the date of
  the USD value.
- **Unknown values.** If you cannot find a value, write `UNKNOWN`. Never
  estimate.
- **Held-out guard.** For each project, run
  `python3 scripts/check_holdout.py <owner/repo>` on its main repository. If
  the result is FORBIDDEN, record the case but **do not open the repository
  code**, and set `holdout_flag=FORBIDDEN`. Reading the incident write-up is
  allowed.
- **No live interaction.** Do not interact with any live contract, and do not
  contact any project.
- **AI labels.** The class labels are AI-proposed. Write `label_source=AI` in
  the CSV. The author must review them later.

## Output

### 1. `reports/R1/incidents.csv`

One row per case, with these columns:

```text
case_id,project,date_disclosed,date_incident,class,mechanism_one_line,
exploited(yes/no/whitehat),loss_claimed_usd,loss_confirmed_usd,recovered_usd,
value_at_risk_usd,usd_date,chain,proof_system,toolchain,
primary_source_url,secondary_source_urls,retrieved_utc,holdout_flag,label_source,notes
```

### 2. `reports/R1/REPORT.md`, in the handoff template of `docs/orchestration/README.md`

It must contain:

- the count of cases per class, and the count of exploited cases per class;
- the total confirmed loss per class, and the total value at risk per class;
- a timeline (year × class);
- the five most important cases, with 3–5 lines each;
- a clear answer to: **"Is there any public money loss in classes P1, P2, P3 or
  P5?"** Answer yes or no, with the evidence;
- a list of the searches you ran, with the query text and the date.

## Completion criteria

- **Coverage.** Every source in the minimum list was searched, and the report
  lists each search.
- **Leads.** Every known lead above is in the CSV with a primary source, or with
  the reason a primary source is missing.
- **Class totals.** The per-class totals in the report match the CSV exactly.

## Time box

One day.
