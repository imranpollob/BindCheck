# Policy review of validated effects — 2026-10-30

Status: author review assisted by an external AI advisor. The reviewer
checked the reports against each application's intended policy and pinned
source; the reviewer did **not** replay any experiment. Execution outcomes
are as reported in `docs/x-experiment/AUTO-VALIDATE.md` and `reports/TE04.md`.

Pinned sources consulted:

- WarpToad `WarpToadCore.sol` and withdraw circuit at `973e7d1e`;
- Payy `RollupV1.sol` at `c4d2c902`;
- Payy whitepaper (withdrawal requires a burned backing note).

## TE04 — attribution correction

The forged-burn payout (7 test-token units to `0xdead`) violates Payy's
withdrawal policy. However, TE04 used the **tail** candidate, and TC02
shows the original `c4d2c90` circuit also accepts that candidate. The pinned
contrast verified the mutant's proof under the original key, which fails for
any proof and is not a same-transaction contrast.

Defensible claim: *the inherited Payy message-tail vulnerability is
reproduced end-to-end with real proofs, the real verifier and the real
consumer.* End-to-end exploitation of PY-C02's own mutation is **not
established**. That requires the active-prefix candidate run on the original,
mutant and repaired circuits, each with its own matching proof and key.

## Per-case policy judgments

| Cases | Judgment |
|---|---|
| WT-C01, WT-S03, WT-S09 (repeated minting) | Unauthorized if the same underlying note is spent again (single use). |
| WT-S06 (excessive relayer fee) | Unauthorized if the payment exceeds the proof-authorized maximum fee. Clear case. |
| WT-C03, WT-C04, WT-S01 (foreign/unauthenticated source) | Violates source authorization if the mint relies on a foreign application's note or an unadmitted root. Synthetic root setup limits the deployment claim. |
| WT-S02 (fabricated giga root) | **Unresolved.** Initialization trusts the configured provider's root; the mock may make the root acceptable to the original contract too. Needs an original-consumer replay with identical state. |
| WT-C02, WT-C07, WT-C08 | No completed unauthorized effect. For C08, an owner-chosen nonzero recipient may be permitted. |
| PY-S01–S04 | Unfunded mint, duplicate settlement, wrong payout destination, invalid message kind violate the corresponding rules, but evidence uses mock proof acceptance. For S03, exclude Payy's legitimate substitute-recipient mechanism. |

## Payy control warning — R-CONSUMER on `commitHash`

Target: the check-added (repaired) Payy artifact with the pinned consumer
`RollupV1.sol` at `c4d2c902`. `verifyRollup` (lines 314–371) passes public
input 2 (`commitHash`) only to `verifyCommitHash` (lines 381–382), an empty
placeholder commented "asserting the commit hash is stored on Celestia".
Validator signatures cover `newRoot`, `height` and `otherHashFromBlockHash`,
not `commitHash`. The proof verifier still receives `commitHash` as a public
input.

**Author label: Out of scope (data availability).** The missing on-chain
publication check is confirmed. No unauthorized committed effect is
established. Any state-reconstruction or withdrawal disruption depends on
off-chain availability guarantees that the contract alone does not determine.

Not recorded as "true positive, low": being out of scope does not imply low
severity, and "Placeholder" shows unfinished enforcement, not an accepted
design choice.

Paper and triage use: count this as a structurally accurate warning outside
the threat model. It is not a false positive and not a confirmed defect. It
illustrates that R-CONSUMER reports missing use without knowing the
application's policy.

## Scope corrections

- WarpToad's pinned development contract has a public minting faucet; the
  policy concerns the **proof-consuming withdrawal path** only.
- Every E4 row must show the claimed defect, not the setup or an inherited
  bug, causes the effect: run the same transaction on original and defective
  (and repaired) versions with matching keys and identical initial state.
