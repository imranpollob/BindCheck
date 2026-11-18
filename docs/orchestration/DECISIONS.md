# Sprint decision log

Newest entry last. Each entry names the person who decided.

| Date | Decision | By | Notes |
|---|---|---|---|
| 2026-11-17 | Target venue EuroS&P 2027. The S&P 2027 C2 submission was withdrawn. | Author | |
| 2026-11-17 | The reviewer/orchestrator role is given to Claude. AI coders run in `$BC/wt-<ID>` worktrees. | Author | |
| 2026-11-17 | T0, R1 and R2 are accepted and merged into `sprint/eurosp-2027-plan`. | Author + reviewer | R2 is BLOCKED on Solodit (site in maintenance). R2b reruns the Solodit queries later. |
| 2026-11-17 | Payy work uses the WASM substitute `@aztec/bb.js@3.0.0-manual.20251030`, labelled as a substitute. Native bb 3.0.0 cannot be downloaded (bucket deleted). | Author | Any Payy result from it is a "substitute run". |
| 2026-11-17 | R1b (author review of the class labels of the 15 in-class R1 rows, especially R1-005 Aztec Connect) is **deferred**. The author does it later. | Author | Reviewer's view: R1-005 is P1 (unbound effect extent), not P5. **Reminder: do R1b before the paper cites the counts.** |
| 2026-11-17 | Moving `AztecProtocol/aztec-packages` to DEV was approved, but it is **not exercised**. The exploited Aztec Connect code is in `AztecProtocol/aztec-connect`, which is not in the held-out pool (guard: ALLOWED). `aztec-packages` stays held-out. | Author approved; reviewer did not exercise | |
| 2026-11-17 | **Significance gate, early read: continue the binding paper.** Evidence: Aztec Connect lost about $2.1M (June 2026) through a binding flaw (an unbound `numRealTxs` extent). R2 found 17 High/Critical binding findings in 7 audits of 7 protocols, including a Railgun Critical (P1). 38% of binding findings need the circuit to be decided. | Reviewer | Caveats: 10 of the 17 High/Critical findings come from one protocol (Singularity). The TVL at audit time is unknown. Recheck at the 21 Nov gate with S1 and AZ1. |
