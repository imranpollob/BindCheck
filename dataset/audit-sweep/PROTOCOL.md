# Audit sweep protocol: binding findings in public ZK audit reports

**Version:** v1. **Date:** 2026-11-22. **Drafted by:** the orchestrator (Claude Code, Opus 5.5), revised after the Zellic pilot.
**Approval:** scope widening approved by the author on 2026-11-22 ("widen the scope, write v1 and launch agents"). Every change from v0 is logged in §11.

## 1. Purpose

Build a systematic, auditable list of **published, auditor-confirmed proof-to-effect binding flaws**. It becomes the candidate pool for the audit benchmark (study set + reserved set). Every report enumerated is logged, including those with no hits, so the paper can show a full funnel:

> sources → reports enumerated → reports in scope → findings screened → binding findings → acquirable (public + pinned).

This sweep **screens and records**. It does not label (humans do that), build, run or reproduce anything.

## 2. Definition: what counts as a binding flaw

A finding is a **binding candidate** if all three hold:

1. **Proof accepted.** A ZK proof (SNARK or STARK) is verified and accepted, or a verifier that should reject it does not.
2. **Effect committed.** A consumer (the code that acts after verification) then commits an effect: it pays, mints, records, marks spent, grants access, updates a state root, or changes other state.
3. **Value not fixed.** Some value that decides **who, how much, what, which policy, which state, or how often** is **not fixed by the proved statement**. It may be caller-chosen, not a public input, mismatched in order or encoding, aliasable, or taken from an unchecked config.

**Front-running rule (new in v1).** If a third party can take an observed valid proof and resubmit it so that the effect goes to them, or changes in their favour, that is a **binding** flaw: P1 if the recipient, amount or refund changes, P2 if the caller or context changes. It is **not** `ORDERING-REENTRANCY`. That code is only for reentrancy or call-ordering bugs where every value the effect uses *is* fixed by the proof.

**Pattern guess** (AI only; humans confirm later):

| Code | Pattern |
|---|---|
| P1 | Unbound effect: recipient, amount, refund, identity or stored value not fixed by the proof |
| P2 | Context binding: caller, chain, contract, config, policy or domain not bound |
| P3 | Replay key / nullifier not bound, aliased through the field, or no replay protection |
| P4 | Verifier invariants: missing range checks, forgeable or constant-true verifier, bad or default key |
| P5 | Public-input count, order or encoding mismatch between consumer and circuit |
| OTHER | Binding-shaped but fits none of the above (e.g. extent or prefix binding); explain in notes |

**Decision values:**

| Value | Meaning |
|---|---|
| `KEEP` | The auditor's text supports all three criteria. |
| `BORDERLINE` | Exactly one criterion is unclear from the text, or the effect is only implied. |
| `DROP` | At least one criterion clearly fails. Give a reason code. |

## 3. Scope (widened in v1)

**In scope:** any system where an **EVM contract verifies a ZK proof and acts on it**, whatever the proof system or circuit language. This includes Circom, Noir, Halo2, gnark, Plonky2/3, Cairo/STARK, zkVMs (SP1, RISC Zero), recursive and aggregation verifiers, zk light clients, zk bridges and zk-rollup L1 verifiers.

- Always record `circuit_lang` and `proof_system`. Later reproduction will be prioritized by toolchain, but screening does not filter on it.
- A report that audits only the circuits, or only the contracts, of such a system is still **IN** if the system has an EVM consumer of the proof. Record which side was in the audit scope.

**Attested verification (v1.3).** A proof can be verified off-chain by an attestation network (e.g. Aligned Layer operators or an EigenLayer AVS), with the EVM contract acting on a signed or batch-inclusion attestation that the proof verified. Such systems are **IN**, with `proof_system` noted as `attested:<system>`. The binding question is unchanged: does the consumer act only on what the proof fixes? This applies both to reports auditing the attestation layer itself and to consumers that use it.

**Recorded but excluded:**

- The consumer is not on the EVM (Solana, Bitcoin, Cosmos, Mina-native, off-chain only) → `NON-EVM`.
- The "proof" is not a ZK proof (Merkle inclusion only, signatures only, optimistic fraud proofs, TEE attestations) → `NO-ZK-COMPONENT`.

## 4. Sources and agent assignment

| Agent | Sources |
|---|---|
| `firms-1` | Zellic (github.com/Zellic/publications; re-screen under v1), Trail of Bits (github.com/trailofbits/publications), Veridise, OpenZeppelin (blog.openzeppelin.com/security-audits), Consensys Diligence (diligence.consensys.io/audits) |
| `firms-2` | zkSecurity (reports.zksecurity.xyz), PSE audits, Spearbit portfolio (github.com/spearbit/portfolio), Cantina portfolio, Nethermind, ChainSecurity, OtterSec, Hexens, Sigma Prime, Least Authority, yAcademy, Oxorio, Zokyo |
| `contests` | Code4rena (code4rena.com/reports; `code-423n4/*-findings` repos), Sherlock (`sherlock-audit/*-judging` repos), Cantina competitions |
| `curated` | 0xPARC zk-bug-tracker, zkSecurity zkbugs dataset, GitHub Security Advisories, Solodit |
| `firms-3` (v1.1) | Halborn, Quantstamp, Cyfrin, Hacken, Runtime Verification, Kudelski Security, Dedaub, MixBytes, Ackee Blockchain, CertiK (keyword search of its public audit list only) |
| `browser` (v1.1) | Login-walled or bot-checked sources handled in the author's browser: Consensys Diligence, Solodit, Sherlock contests 805 and 618, 5 Cantina competitions |
| `rescreen` (v1.1) | No new sources. Re-screens all IN reports for missed findings (especially verifier-soundness/P4) and corrects screen-1 errors |
| `firms-2` addition (v1.1) | ABDK Consulting |

**Enumeration rule:** list **every** report in each source. If a source has no public index, write that in `blocked.md` and notify the orchestrator (§8).

- **Contest platforms:** enumerate every contest, then screen it by contest name, description and scope (screen 1). Read the findings only for contests that are in scope.
- **Aggregators and advisory databases:** run the fixed terms in §6 and log every query.

**Do not read** before or during the sweep: `reports/R-ledger.md`, any `origin/sprint/R2` content, or `reports/R2/`. These are used afterwards to measure what the sweep missed.

**Zellic exception:** `firms-1` may reuse the pilot's downloaded PDFs (`/tmp/claude-1000/audit-sweep/pilot-zellic/pdf/`) and must re-screen every Zellic report under v1. The pilot output in `dataset/audit-sweep/pilot-zellic/` may be consulted for Zellic only. Pilot decisions are not carried over without re-checking them against v1, especially the front-running rule (Nocturne 3.3).

## 5. Procedure per report

**Screen 1 (report level).**

1. Decide IN or OUT from the title, the scope section and a **full-text keyword scan**. The keywords are: `zk`, `zero-knowledge`, `snark`, `stark`, `groth16`, `plonk`, `halo2`, `gnark`, `plonky`, `circom`, `noir`, `cairo`, `sp1`, `risc zero`, `verifier`, `verifyProof`, `public input`, `nullifier`.
2. A keyword hit alone is not IN. Confirm it against the scope section.
3. Fill one row in `reports.csv`, with screen-1 reason codes from §7.

**Screen 2 (finding level, IN reports only).**

- Read every finding. Count all of them in `findings_total`, excluding "Discussion" or "Informational notes" sections.
- Log in `findings.csv` every finding that involves a proof, verifier, public input, nullifier, commitment, signature challenge, verification key, or an effect that runs only after a proof is accepted.
- **Verifier-soundness findings must be logged (v1.1).** This covers: a verifier or recursion layer that can accept an invalid proof, or a proof for the wrong program or key; Fiat–Shamir transcript or challenge flaws; missing curve or subgroup checks; constant-true or always-succeeding verification; an unpinned vk/vk_root/program ID; and gateway or router misrouting. These are **P4 candidates even when the auditor describes no consumer effect**: the consumer's effect follows from accepting the proof. Use `BORDERLINE` if the effect is only implied.
- **BORDERLINE discipline (v1.2).** `BORDERLINE` is for findings where at least two of the three §2 criteria are clearly met and the third is plausible but unstated. It is not a catch-all. Use `DROP` for:
  - **Liveness or denial-of-service only**: a user's own bad input blocks their claim, or the system halts. → `NO-EFFECT-DESCRIBED`. Exception: one party's valid proof blocks or consumes *another* party's state (e.g. marks a victim's nullifier spent) is binding.
  - Gas, memory-layout, event, or code-quality issues with no acceptance or effect consequence. → `NOT-BINDING-CONTRACT-ONLY`.
  - Circuit-internal under-constraints in a zkVM, rollup or recursion circuit that do not concern the public inputs, the program/vk identity, or what the on-chain verifier is told. → `NOT-BINDING-CIRCUIT-ONLY`.
  - Off-chain prover or client bugs that cannot make the on-chain verifier accept a wrong statement. → `NOT-BINDING-CONTRACT-ONLY`, with a note.
- If a Discussion item describes a binding issue, log it with `finding_id` `D.<n>` and decision `BORDERLINE`.
- Each logged row gets:
  - a decision (§2) and a reason code (§7);
  - a **verbatim quote** of the mechanism or impact, at most 40 words, taken from the description or impact text (not the recommendation);
  - a page or section reference.

**Artifact check (KEEP and BORDERLINE only):**

1. Find the public repo, the audited commit and the fix commit. The fix commit can come from the report, a linked PR, or the repo history.
2. **Check that each commit exists via the web URL**, not the API: `curl -s -o /dev/null -w '%{http_code}' https://github.com/<owner>/<repo>/commit/<sha>`. A 200 means it exists; a 404 means it doesn't, or the repo is private or missing.
3. Check file presence with `https://raw.githubusercontent.com/<owner>/<repo>/<sha>/<path>` when you know the path. Use the GitHub tree API only when the path is unknown.
   - The API is shared and unauthenticated: 60 calls per hour across **all** agents. Use at most ~10 API calls per hour.
   - On HTTP 403 or 429, queue the item and continue with other work.
4. Record whether the circuit, verifier and consumer files are present. Use `N/A` when a check is impossible (e.g. a private repo).
5. **Do not clone, build or read code beyond file names.** Deep reading would contaminate cases that later land in the reserved set.

**Held-out guard.** Before touching any repository, run:

```sh
python3 dataset/audit-sweep/tools/check_holdout.py owner/repo
```

If it returns `FORBIDDEN`, record the finding from the report text only, set `holdout_flag=FORBIDDEN`, and do not open the repo.

## 6. Fixed search terms (aggregators, advisories, contest search boxes)

Use each term on each searchable source, and log query, source and result count in `queries.csv`:

`circom`, `noir`, `groth16`, `plonk verifier`, `zk proof`, `public input`, `public signals`, `nullifier`, `verifyProof`, `front-run proof`, `proof replay`, `not bound to proof`, `snarkjs`, `halo2`, `gnark`, `sp1`.

## 7. Codes

**Screen-1 reason codes:**

| Code | Meaning |
|---|---|
| `IN` | Some EVM contract verifies a ZK proof (§3) |
| `NO-ZK-COMPONENT` | No ZK proof in the audited system |
| `NON-EVM` | ZK proof, but the consumer is not on the EVM |
| `NOT-A-SECURITY-AUDIT` | e.g. a white paper or a formal-verification summary with no findings |
| `UNREADABLE` | Corrupt PDF, or the text cannot be extracted; explain in notes |

**Finding reason codes:**

`BINDING`, `NOT-BINDING-CIRCUIT-ONLY` (under-constraint with no consumer effect described), `NOT-BINDING-CONTRACT-ONLY`, `ORDERING-REENTRANCY` (see the front-running rule in §2), `SETUP-CRS`, `NO-EFFECT-DESCRIBED`, `DUPLICATE`, `OTHER` (explain in notes).

**Acquirability:**

| Value | Meaning |
|---|---|
| `PINNED` | Public repo, audited commit exists, and circuit, verifier and consumer are all visible |
| `PARTIAL` | Public, but a commit or one artifact is missing |
| `PRIVATE-OR-MISSING` | The repo URL returns 404 |
| `NO-COMMIT` | The report names no commit, and none can be found |
| `FORBIDDEN` | The held-out guard refused the repo |
| `N/A (DROP)` | Not checked because the finding was dropped |

## 8. Output files (per agent, in `dataset/audit-sweep/<agent>/`)

**`reports.csv`:**

```
report_key,agent,source,auditor_or_platform,report_title,report_date,report_url,report_sha256,retrieved_utc,protocol,protocol_repos,audit_scope_side,proof_system,circuit_lang,has_evm_consumer,holdout_flag,findings_total,findings_logged,screen1,screen1_reason,notes
```

- `report_key` = `<auditor-slug>-<protocol-slug>-<YYYY-MM>`. Add `-2`, `-3`, … for repeats.
- `audit_scope_side` is one of `circuits`, `contracts`, `both`, `UNKNOWN`.
- For OUT rows, fill only what screen 1 needs. Leave the rest blank.

**`findings.csv`:**

```
finding_key,report_key,finding_id,title,severity,page_or_anchor,finding_url,quote,mechanism_one_line,consumer_effect,unbound_value,pattern_guess,decision,reason_code,repo,vuln_commit,vuln_commit_http,fix_commit,fix_commit_http,fix_source,circuit_present,verifier_present,consumer_present,proof_system,circuit_lang,acquirability,holdout_flag,label_source,notes
```

- `finding_key` = `<report_key>-<finding_id>`.
- **Multiple fix commits** are semicolon-separated in `fix_commit`, with HTTP codes in the same order in `fix_commit_http`.
- `label_source` is always `AI`.

**Other files:**

| File | Contents |
|---|---|
| `queries.csv` | `source,term,result_count,retrieved_utc,notes` |
| `progress.md` | Running log: the last item done and the next one up, so the work can resume after a crash |
| `blocked.md` | Every login wall, CAPTCHA or rate limit. Record it; never bypass it. |
| `notes.md` | Protocol ambiguities met (quote the clause), the agent's own spot-check results, and the time taken |

**On any block, notify the orchestrator immediately** with `hc send t3z "BLOCKED: <source> <url> <login|captcha|rate-limit>"`, then continue with other sources. The author can log in, and the orchestrator will then handle that source through the author's browser.

**Downloads** go to `/tmp/claude-1000/audit-sweep/<agent>/`; they are never committed. Record the SHA-256 of every downloaded report. You may delete the PDFs of OUT reports after screening them, once the hash is recorded. Report URLs must be permalinks where possible (a commit-pinned GitHub blob).

## 9. Conduct

- **Allowed tools:** `curl`, `jq`, `pdftotext`, `python3 -I` (only for parsing downloaded files and writing CSVs), `git ls-remote`, and the held-out guard. `gh` is not installed.
- No builds, no cloning, and no executing project code.
- Never interact with deployed contracts, RPC endpoints or live systems. Never contact projects or auditors. Never log in, create accounts, or bypass CAPTCHAs.
- Do not invent findings, commits or URLs. If something is unknown, write `UNKNOWN`.
- Do not start subagents. Do not edit files outside your own output folder.
- If you are stuck on one item for more than ~15 minutes, log it and move on.

## 10. Quality control

The orchestrator will:

- check every KEEP and ~10% of other rows against the original report (quotes verified verbatim);
- deduplicate across agents on `(protocol, auditor, finding_id)`;
- measure sweep recall against the earlier R2 census **after** the sweep;
- publish the merged funnel.

An agent whose spot-check error rate exceeds ~10% is re-run with corrected instructions.

## 11. Change log

| Version | Date | Change |
|---|---|---|
| v0 | 2026-11-22 | Draft for the pilot (Zellic only). |
| v1 | 2026-11-22 | Author-approved scope widening. The scope (§3) now covers any EVM consumer of a ZK proof in any proof system; `proof_system` and `audit_scope_side` were added. Added: the front-running rule (§2), definitions of KEEP/BORDERLINE/DROP, screen-1 reason codes, full-text keyword scanning, the multi-commit format, the `report_key` format, `N/A` values, web-URL commit checks (API quota), the allowed tools, and treatment of Discussion items. More firms were added to §4. Pilot evidence: `dataset/audit-sweep/pilot-zellic/pilot-notes.md` (415/415 enumerated; calibration found 19/19 R2 Zellic reports; 16/16 quotes verified verbatim). |
| v1.1 | 2026-11-22 | After the R2 recall check (`merged/RECALL-R2.md`: 40/50 = 80%; 6 of 7 screening misses were verifier-soundness issues), §5 now explicitly requires logging verifier-soundness findings as P4 candidates. ABDK added as a source (firms-2). A targeted re-screen lane was added; the firms-3 lane was added for further firms. |
| v1.2 | 2026-11-22 | BORDERLINE discipline (§5): rescreen's first 40 reports produced 126 BORDERLINE out of 143 rows, mixing real misses with denial-of-service, memory and circuit-internal noise. Liveness-only, gas/memory and non-interface circuit-internal findings are now DROP. |
| v1.3 | 2026-11-23 | Attested verification (§3): rescreen2 found Aligned Layer reports screened inconsistently (2 IN, 1 OUT), and Nori Bridge is IN via an Aligned path. Systems where an off-chain attestation network verifies the proof and an EVM contract acts on the attestation are IN. |
