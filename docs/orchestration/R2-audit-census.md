# R2 — Audit-finding census: how often do auditors find binding flaws in funded protocols?

**Goal for the paper:** show that proof-to-action binding flaws are frequent in
professional audits of real, funded protocols, even where no theft happened. A
large count of High and Critical findings is the strongest evidence that the
problem matters. The census also measures two things a reviewer will ask about:

- **Does a finding need the circuit to be seen?** This tests the "Slither plus
  20 lines finds your bugs" critique.
- **Which classes do auditors find most?** This tells us where the tool must be
  strong.

**Branch:** `sprint/R2`.

**Owns:** `reports/R2/`, `results/raw/R2/` (ignored).

**Must not edit:** any other path.

This is research only: reading public audit reports and contest findings.

## Sources (minimum)

**Solodit** (solodit.cyfrin.io), the aggregated audit-finding search. Run each
query below.

**Contest platforms:** Code4rena, Sherlock, Cantina and Hats. Use contests for
ZK applications, bridges, rollup contracts and identity or airdrop systems.

**Public audit PDFs:** Trail of Bits, Zellic, Veridise, zkSecurity,
OpenZeppelin, Spearbit, Least Authority, Nethermind, Consensys Diligence and
Hacken. Target protocols, at minimum:

| Area | Protocols |
|---|---|
| Privacy | Railgun, Privacy Pools (0xbow), Tornado Cash forks |
| Identity | Semaphore, World ID contracts, zkPassport, Self/OpenPassport, Anon Aadhaar |
| Email / proofs | zkEmail, Sismo |
| ZK platforms | Aztec / Aztec Connect, Succinct SP1 contracts and SP1 Helios, RISC Zero verifier contracts |
| Rollups and bridges | Polygon zkEVM and AggLayer, Scroll, Taiko, Linea, zkSync contracts, Polyhedra zkBridge |

**Query terms.** Combine each with `proof`, `zk`, `verifier` or `nullifier`:

```text
front-run / frontrun proof; recipient not included in proof; msg.sender not bound;
proof can be reused; replay proof; nullifier not checked / not stored / not unique;
public input not validated; field modulus / SNARK_SCALAR_FIELD / >= p;
malleable proof / proof malleability; chainId not in public inputs; cross-chain replay;
external nullifier / scope; verifying key / vkey mismatch; wrong verifier;
public input order / length mismatch; unchecked public signals
```

## Inclusion rule

Include a finding when the auditor states that **a valid, accepted proof** leads
to one of these:

- an effect the prover did not authorize;
- a duplicated effect;
- a misdirected effect;
- a forged acceptance through the verifier or key configuration.

Record pure circuit under-constraint findings separately as `OUT`, with a count
only.

## Output

### 1. `reports/R2/findings.csv`

One row per finding, with these columns:

```text
finding_id,protocol,auditor_or_platform,report_date,severity(C/H/M/L/I),class(P1-P5/OUT),
mechanism_one_line,fixed(yes/no/unknown),needs_circuit_to_detect(yes/no/unclear),
needs_circuit_reason,contract_only_tool_could_flag(yes/no/unclear),
protocol_tvl_usd_at_report(or UNKNOWN),tvl_source,finding_url,report_url,
retrieved_utc,holdout_flag,label_source
```

Column meanings:

- `needs_circuit_to_detect = yes` means a tool that reads only the Solidity code
  cannot decide the finding. An example is a public input that the contract
  passes to the verifier but the circuit does not constrain.
- `holdout_flag` is the output of
  `python3 scripts/check_holdout.py <owner/repo>` for the protocol repository.
  If FORBIDDEN, record the finding from the audit text only. **Do not open the
  repository code.**
- `label_source = AI`. The author reviews the labels later.

### 2. `reports/R2/REPORT.md`, in the handoff template of `docs/orchestration/README.md`

It must contain:

- the number of audits read, and the number of findings included;
- counts by class × severity;
- the count and percentage of findings with `needs_circuit_to_detect = yes`;
  **this is the key number**;
- the count and percentage of findings with `contract_only_tool_could_flag = yes`;
- the protocols with the most value (TVL) that had a High or Critical binding
  finding;
- 5 representative findings, with a short quote and a link for each;
- a clear answer to: **"Are binding flaws (P1–P3, P5) frequent in audits of
  funded protocols?"** Answer yes or no, with the numbers.

## Rules

- **Read the text.** Read the finding text before you include it. Do not
  include a finding from its title alone.
- **Unknown values.** If severity or TVL is unknown, write `UNKNOWN`. Never
  estimate.
- **Reading only.** Do not interact with live contracts, and do not contact any
  auditor or project.

## Completion criteria

- **Audits read.** At least 40 audits or contest reports read, across at least
  15 protocols.
- **Queries.** Every Solodit query was run, and its result count is recorded.
- **Totals.** The per-class totals in the report match the CSV exactly.

## Time box

Two days. At the end of day 1, commit and push a partial CSV, so that the
reviewer can check the labelling early.
