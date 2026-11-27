# Freeze-2 DEV warning review index

This index covers the [18 applicable `VIOLATION` cells](../../reports/freeze2/dev-ledger.csv) at analyzer SHA-256 `92789fad12050a3058a21cc5c2326e7d41604ad5ade0f09f72a35789437e6c1a` ([freeze declaration](../../docs/FREEZE-2.md)). [F34](DEV-F34.md) intentionally combines its P3 and P4 cells and explains the public-output meaning mismatch and unconstrained nullifier as well. The cards are **AI opinions** for human review, not independent annotation or new E2–E4 results. The [precommitted review rules](../../reports/validate/PLAN.md) define the labels.

| Cell | Card | AI opinion | Human final label | Human initials/date |
| --- | --- | --- | --- | --- |
| DEV-F08 P4 | [zkp2p](DEV-F08-P4.md) | FALSE-ALARM |  |  |
| DEV-F09 P4 | [zk-poll](DEV-F09-P4.md) | FALSE-ALARM |  |  |
| DEV-F10 P4 | [0xFable](DEV-F10-P4.md) | TRUE |  |  |
| DEV-F14 P1 | [meridian-link amount](DEV-F14-P1.md) | TRUE |  |  |
| DEV-F14 P4 | [meridian-link key](DEV-F14-P4.md) | TRUE |  |  |
| DEV-F25 P3 | [Shadow Credit Network](DEV-F25-P3.md) | UNDECIDABLE |  |  |
| DEV-F27 P3 | [CropChain](DEV-F27-P3.md) | UNDECIDABLE |  |  |
| DEV-F30 P1 | [ZKredential](DEV-F30-P1.md) | UNDECIDABLE |  |  |
| DEV-F34 P3 | [zk_voting joint card](DEV-F34.md) | TRUE |  |  |
| DEV-F34 P4 | [zk_voting joint card](DEV-F34.md) | TRUE |  |  |
| DEV-F35 P1 | [ShadowSats](DEV-F35-P1.md) | UNDECIDABLE |  |  |
| DEV-F38 P3 | [Truxify](DEV-F38-P3.md) | FALSE-ALARM |  |  |
| DEV-F39 P1 | [RacePass](DEV-F39-P1.md) | UNDECIDABLE |  |  |
| DEV-F44 P1 | [proof-of-twitter](DEV-F44-P1.md) | TRUE |  |  |
| DEV-F48 P3 | [PrivateCrypMix replay](DEV-F48-P3.md) | FALSE-ALARM |  |  |
| DEV-F48 P4 | [PrivateCrypMix key](DEV-F48-P4.md) | FALSE-ALARM |  |  |
| DEV-F49 P1 | [Planetary Entropy Mining](DEV-F49-P1.md) | INTENDED-BEHAVIOUR |  |  |
| DEV-H01 P3 | [historical zkDrops](DEV-H01-P3.md) | TRUE |  |  |

## Suggested human review order

1. Decide the exact recipient, amount, and credential policies in [ZKredential](DEV-F30-P1.md) and [RacePass](DEV-F39-P1.md). Their cards state the questions and link the existing provisional policies and local real-proof evidence.
2. Check [zk_voting](DEV-F34.md) against its compiled R1CS, verifier and the paper lane's §4(b) correction. Label P3 and P4 separately in the one card.
3. Confirm the source-to-consumer wiring distinctions for [zkp2p](DEV-F08-P4.md), [zk-poll](DEV-F09-P4.md), [Truxify](DEV-F38-P3.md) and [PrivateCrypMix](DEV-F48-P4.md). These are the easiest places to overcount a source-key or replay warning.
4. Fill every blank human field, including a reason for any change from the AI opinion. Keep unresolved policy or wiring as unresolved; do not turn it into a tool win or miss.
