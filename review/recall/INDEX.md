# Recall review cards

One card per `v2_scope_class == integration` row of `dataset/recall-set-v2.csv` (27).
Each card is a proposal from the L4 audit lane; the decision fields are blank.

| Row | Card | Pair | Exposed | Promoted | L4 proposal |
|---:|---|---|---|---|---|
| 14 | [14-data-are-not-fully-verified-during-state-update.md](14-data-are-not-fully-verified-during-state-update.md) | resolved | EXPOSED | yes | DEMOTE |
| 15 | [15-an-attacker-can-craft-a-fake-non-inclusion-proof-for-a-given.md](15-an-attacker-can-craft-a-fake-non-inclusion-proof-for-a-given.md) | resolved |  | yes | DEMOTE |
| 17 | [17-second-pre-image-attacks-on-packbytesandposeidon-may-be-used.md](17-second-pre-image-attacks-on-packbytesandposeidon-may-be-used.md) | incomplete |  | yes | DEMOTE |
| 18 | [18-forbidden-country-check-bypass-via-packed-byte-overflow.md](18-forbidden-country-check-bypass-via-packed-byte-overflow.md) | incomplete |  | yes | DEMOTE |
| 19 | [19-exclusion-check-of-forbidden-countries-is-unsound-and-incomp.md](19-exclusion-check-of-forbidden-countries-is-unsound-and-incomp.md) | incomplete |  | yes | DEMOTE |
| 20 | [20-incorrect-initialization-in-membership-circuits.md](20-incorrect-initialization-in-membership-circuits.md) | resolved |  | yes | DEMOTE |
| 21 | [21-semaphore-nullifier-field-alias.md](21-semaphore-nullifier-field-alias.md) | resolved | EXPOSED |  | KEEP (v1 strict; not subject to C1) |
| 22 | [22-zkdrops-nullifier-field-alias.md](22-zkdrops-nullifier-field-alias.md) | resolved | EXPOSED |  | KEEP (v1 strict; not subject to C1) |
| 23 | [23-nightfall-nullifier-field-alias.md](23-nightfall-nullifier-field-alias.md) | incomplete |  |  | DROP-CANDIDATE (source and pins MISSING) |
| 24 | [24-payy-message-tail.md](24-payy-message-tail.md) | resolved | EXPOSED |  | KEEP (v1 strict) but DSL label must be corrected |
| 25 | [25-foomcash-default-g2-key.md](25-foomcash-default-g2-key.md) | incomplete |  |  | NEEDS-SCOPE-DECISION |
| 26 | [26-veilcash-default-g2-key.md](26-veilcash-default-g2-key.md) | incomplete |  |  | NEEDS-SCOPE-DECISION |
| 27 | [27-zeto-unrandomized-setup.md](27-zeto-unrandomized-setup.md) | incomplete |  |  | NEEDS-SCOPE-DECISION |
| 28 | [28-zkemail-zellic-skipped-subject-prefix.md](28-zkemail-zellic-skipped-subject-prefix.md) | resolved |  |  | KEEP (v1 strict; not subject to C1) |
| 29 | [29-zkemail-zellic-wrong-public-input-field.md](29-zkemail-zellic-wrong-public-input-field.md) | resolved |  |  | KEEP (v1 strict; not subject to C1) |
| 30 | [30-zkemail-zellic-stale-zk-regex-artifact.md](30-zkemail-zellic-stale-zk-regex-artifact.md) | resolved |  |  | ADVISORY: DEMOTE-CANDIDATE (circuit-internal, no P1-P5 mapping) |
| 31 | [31-zkemail-zellic-last-timestamp-zero.md](31-zkemail-zellic-last-timestamp-zero.md) | resolved |  |  | KEEP (v1 strict; not subject to C1) |
| 32 | [32-zkemail-zellic-nine-digit-timestamp.md](32-zkemail-zellic-nine-digit-timestamp.md) | resolved |  |  | ADVISORY: DEMOTE-CANDIDATE (circuit-internal, no P1-P5 mapping) |
| 33 | [33-zkemail-zellic-overlapping-masks.md](33-zkemail-zellic-overlapping-masks.md) | resolved |  |  | ADVISORY: DROP-CANDIDATE (no code fix; no unauthorised effect) |
| 34 | [34-semaphore-audit-zero-leaf-field.md](34-semaphore-audit-zero-leaf-field.md) | incomplete |  |  | ADVISORY: DROP-CANDIDATE (liveness, not authorization) |
| 35 | [35-semaphore-audit-group-id-field.md](35-semaphore-audit-group-id-field.md) | incomplete | EXPOSED |  | ADVISORY: DROP-CANDIDATE (liveness, not authorization) |
| 36 | [36-semaphore-audit-root-history-collision.md](36-semaphore-audit-root-history-collision.md) | resolved | EXPOSED |  | KEEP (v1 strict) - human to confirm severity |
| 37 | [37-semaphore-audit-unbound-verification-key.md](37-semaphore-audit-unbound-verification-key.md) | incomplete | EXPOSED |  | ADVISORY: DROP-CANDIDATE (no defect, no fix) |
| 38 | [38-zkemail-matterlabs-guardian-repeat.md](38-zkemail-matterlabs-guardian-repeat.md) | resolved |  |  | KEEP (v1 strict; not subject to C1) |
| 39 | [39-zkemail-matterlabs-cross-chain-replay.md](39-zkemail-matterlabs-cross-chain-replay.md) | incomplete |  |  | ADVISORY: NEEDS-POLICY-DECISION (acknowledged as intended) |
| 40 | [40-zkemail-matterlabs-proof-coordinate-range.md](40-zkemail-matterlabs-proof-coordinate-range.md) | resolved |  |  | ADVISORY: NEEDS-PAIR-REPAIR |
| 47 | [47-the-registration-and-disclosure-circuits-lack-range-checks-f.md](47-the-registration-and-disclosure-circuits-lack-range-checks-f.md) | resolved |  | yes | DEMOTE |
