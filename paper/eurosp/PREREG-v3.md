# Pre-registration: BindCheck v3 blind evaluation

**Written 2026-11-26.** At this point:
- BindCheck v3 is frozen (mvp tag `bindcheck-mvp-v3`, commit 82e5ed2, `tool/FREEZE-v3.md`);
- v3 has not yet run on B3, round 3 or the hunt pool.

This file is committed before the first such run.

**Amendments.**
- Amendments are appended at the bottom with a date and a reason.
- An amendment never applies to results that have already been seen.
- Items marked **[author]** are open decisions. They must be closed, and appended, before the run they affect.

## 1. Tool under test
- **Version.** `bindcheck-mvp-v3`, unchanged: v2 procedure + exploration loop + O1–O6, `--discover none`, Sonnet high, $3 cap per scan.
- **Isolation.** Every run uses a fresh `--cache-dir`. No scaffold or result carries over between runs or benchmarks.
- **Bug fixes.** A bug fix after any blind result is seen makes a new version. That version is not scored on the benchmark that revealed the bug.
- **Infrastructure failures.** A scan that crashes for an infrastructure reason (container, disk, network to a package registry) is re-run up to 2 times. Every re-run is reported.
- **"Unsupported" is not "missed."** A target that cannot be built or scanned counts as **unsupported**, reported separately.

## 2. Benchmarks

### B3 (binding-mutants-v3)
- **Contents.** 37 mutants (P1 8, P2 7, P3 8, P4 8, P5 6; 11 on the circuit or guest side), 5 decoys and 5 clean hosts.
- **Scoring.** `benchmarks/binding-mutants-v3/MATCHING.md`, frozen 2026-11-25 (sha256 prefix 8bea1697c850ce50), applied verbatim for the BindCheck arm:
  - strict, loose and mechanism-level recall;
  - the frozen judge prompt.
- **What we report.**
  - **Recall.** Overall, per pattern, and circuit/guest-side versus consumer-side.
  - **False alarms.** Any warning matching a decoy's location is a false alarm. Warnings on clean hosts are reported as volume.
  - **Evidence.** The E-level of each hit.
- **Static baselines.** Already frozen (`RESULTS-static.md`). The post-hoc Mythril arm stays labelled post-hoc.

### Round 3 (D7)
- **[author] The list is not frozen yet.** The list file is:
  - the unused test-split binding items, plus hard negatives;
  - pin-checked and Pass-2 labeled by a human.

  Its path and sha256 are appended here **before the first v3 run on it**.
- **Target size.** At least 25 positives. If the list has fewer, round 3 is reported as it is, with its n and Wilson CIs. It is never pooled silently with B3.
- **Scoring.** `SCORING-v1.1` rules (strict / loose / mechanism), unchanged.

### B1 / B2
v3 is **not** scored on B1 or B2. Its development saw their v2 results. B1/B2 keep the v2 numbers.

## 3. Repeats and statistics
- **Three runs.** B3 and round 3 each get 3 independent full runs. Stage A is re-run each time, because variance is the quantity of interest.
- **Headline.** The headline is the median run. We report min/median/max, and per-pattern recall with min–max bars.
- **Confidence intervals.** Proportions get Wilson 95 % intervals.
- **Tested vs claim-only.** The comparison uses Fisher's exact test, on pooled phase-2 warnings (§4).

## 4. Ground truth: two phases

### Phase 1 (automatic)
Each warning is matched against the benchmark labels under the rules in §2.

### Phase 2 (human)
- **Which warnings go to phase 2:**
  - every warning that phase 1 does not match on B3 and round 3, including warnings on decoys and clean hosts;
  - every warning from the hunt.
- **Raters.**
  - Two human raters judge independently. **[author]** Rater 2 is named here before phase 2 starts.
  - An AI output is never a rater.
- **What raters see.** The evidence package: the ledger row, code location, reasoning, paths tried, and the executed test with its output.
- **What raters do not see:**
  - the tool's rank or self-assessment;
  - each other's labels;
  - for B3, whether a warning lies in an edited (mutated) file.
- **Rubric.**
  - **C1:** the proof is accepted.
  - **C2:** an effect is committed.
  - **C3:** the effect value is attacker-chosen and not fixed by the statement and state.
  - The threat-model exclusions (trusted admin, self-inflicted denial of service, view-only).
- **Labels:**
  - **TP**: a binding flaw;
  - **policy-bounded**: the value is deliberately open, for example a relayer fee or a caller reward;
  - **FP**;
  - **unsure**.
- **Agreement and resolution.**
  - Cohen's κ is computed on the 4 labels before any discussion.
  - Disagreements are then resolved by discussion. The resolution is recorded.
  - Unsure items that remain after discussion count as FP for precision. They are listed.
- **Effort.** Rater minutes per warning are logged.
- **Real issues in hosts.** A B3 warning that is a real flaw of the *host* (not the mutant) is labelled TP-host. It becomes a hunt lead and is excluded from B3 recall.

### RQ4 metrics
- **Precision** = (phase-1 matches + phase-2 TP) / all warnings, reported per benchmark and pooled. Policy-bounded warnings are shown separately and are not counted as TP.
- **Tested vs claim-only.** The real-bug rate among warnings with an executed passing test (E2/E3), against claim-only warnings (E1).

## 5. The hunt (RQ3)
1. **[author] Pool and scope.**
   - Recently audited ZK applications.
   - Their families must be outside the dev and test splits, and must not be B3 hosts.
   - Scope is either the audited commits only, or the live versions too. Excluded families are listed.
   - The pool is frozen (list + sha256 appended) before the first scan.
2. **Scanning.** One frozen-v3 run per target. No repeats are needed for discovery.
3. **Triage.** Phase 2 as in §4, on every warning.
4. **Confirmation.** A TP is **confirmed** only with an E3 real-proof test on a local chain, either:
   - produced by the tool; or
   - written by an author when the tool stopped at E1/E2. In that case it is labelled "author-confirmed" in the paper.

   No transaction is sent to any live network.
5. **Disclosure.**
   - Confirmed flaws are reported privately to the maintainers through their security policy.
   - **[author]** The disclosure window, default 90 days.
   - The paper names a project only if it agreed, or the issue is fixed. Otherwise the project is anonymised.

## 6. Contamination (E6)
- **Report-date split.** Detection on audited flaws is split by audit-report date: before vs after the brain model's training cutoff (stated with the model version).
- **Clean evidence.** B3 mutants (synthetic, never published) and the hunt are the contamination-free evidence.

## 7. Integrity
- Every lane that runs these benchmarks has its exposure logged in `dataset/audit-sweep/EXPOSURE.md`.
- No build lane sees any of the material in this file.

## Amendments

### A1 — 2026-11-26: tool under test becomes v4; rounds 1–2 released to dev
- **Reason.** Frozen v3 adds no recall over v2 (dev strict 9/13 for both; test v2 6/22). The author decided to build a stronger v4 before any blind run. **No v3 result on B3, round 3 or the hunt has been run or seen.**
- **Tool under test.** BindCheck v4, built on dev only. Its tag and file hashes are appended here at freeze. Sections 1–7 apply to v4 unchanged, except as below.
- **Rounds 1 and 2 → dev.** Their 13 families leave the test split. They were already scored on v2 and their misses inspected. v4 numbers on these items are **dev numbers** and are never reported as held-out.
  - Split of the 13 families (seed 20261126; rule: check holds 6–8 positives, ≥1 Rust-side positive, ≥2 hard negatives; Boundless forced to tune): **v4-tune** 6 families (15 positives, 11 hard negatives); **v4-check** 7 families (7 positives, 3 hard negatives), held by the orchestrator, scored as aggregate counts only. File: `mvp/tool/dev/split-v4.json`.
- **Round 3.** Restricted to binding items from test families that were not used in rounds 1–2 and are not v4-check. Report-only items from released families are no longer round-3 eligible. The list is still **[author]** and is frozen before the first v4 run on it.
- **Knowledge.** v4 may carry knowledge files distilled from dev findings (dev + v4-tune families, report-only items included) and official SDK documentation. Nothing from test families, B3 hosts, or audit write-ups fetched from the web.
- **v4-check is looked at once.** It is scored a single time, on the v4 freeze candidate (3 runs, as §3). Any change after that look makes v4-check a dev set, and it is reported as such.
- **Dev-v4 numbers are in-sample.** The miss map and the knowledge files were derived from the dev-v4 positives. Dev-v4 recall is reported only as a development number; held-out claims rest on v4-check, B3, round 3 and the hunt.
- **Findings, not locations.** v4 may report one flaw at several locations (proof side, consumer, helper) under one shared finding ID. Recall credits a finding if any of its locations matches. Volume, precision, false alarms on decoys and hard negatives, and phase-2 rating all count **findings**, not locations.
- **Equal run counts.** Any v4-vs-v2 comparison uses the same number of runs per item for both, and specificity and volume come from the same runs as recall.
- **Cost cap.** The $3 per-scan cap is lifted for development. The v4 freeze fixes a new cap, which RQ5 reports.
