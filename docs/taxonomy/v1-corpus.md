# Taxonomy corpus v1 — seed-only (0xPARC zk-bug-tracker)

Date: 2026-10-28. Lane-X seed night. Source snapshot: tracker commit
`56a996672fb50486279126c8e12530f2bf933d0b` (remote HEAD equaled the pin;
README sha256 `31a39587…aff9e86`). 27/27 wild entries screened: 19 include, 8 exclude, 0 unresolved. Machine-readable entries:
`v1-corpus-ledger.json` (schema-valid, 0 errors) and `v1-corpus-entries.json`.

**Status of AI labels.** Every mechanism label below is AI-SUGGESTED
(ledger fact status ASSUMED) for the human annotator. None is a final
label, rater vote, or tie-break. The `human_label` column is intentionally empty.

**Deviation note.** Tonight's task explicitly directed extraction from the two
seed endpoints, which required reading seed listing bodies. The frozen plan's
agent_access_rule is metadata-only with custodian sanitization; that flow is
still owed before any annotation round, and all 23 families read tonight are
logged as exposed (ledger `exposure_events`) and can never be held out.
Linked issues, commits, papers, and reports were NOT opened. The SoK dataset
has no standalone agent-reachable endpoint under tonight's constraint
(paper body + 107 audit reports out of scope); custodian identification still owed.

| ID | Source | System | One-line mechanism | AI-suggested label | human_label |
| --- | --- | --- | --- | --- | --- |
| CF-01 | [tracker#dark-forest-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#dark-forest-1) | dark-forest-1 | RangeProof accepted out-of-range moves: LessThan inputs never bit-constrained. [include] | C_REPRESENTATION |  |
| CF-02 | [tracker#bigint-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#bigint-1) | bigint-1 | BigMod remainder unconstrained to n bits: library-level circuit gap, no evidenced consumer. [exclude] | — (excluded) |  |
| CF-03 | [tracker#circom-pairing-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#circom-pairing-1) | circom-pairing-1 | Range-check outputs computed but never constrained: out-of-range pubkeys verify. [include] | C_RELATION_GAP |  |
| CF-04 | [tracker#semaphore-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#semaphore-1) | semaphore-1 | Consumer accepted uint256 group ids the field-bound verifier always rejects: availability break. [include] | C_REPRESENTATION |  |
| CF-05 | [tracker#zk-kit-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#zk-kit-1) | zk-kit-1 | Tree init admitted above-field zero leaves that later inclusion proofs cannot use. [include] | C_REPRESENTATION |  |
| CF-06 | [tracker#aztec-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#aztec-1) | aztec-1 | Unconstrained 32-bit index assumption let one note mint many nullifiers: double spend. [include] | C_OCCURRENCE_ACCOUNTING |  |
| CF-07 | [tracker#aztec-2](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#aztec-2) | aztec-2 | Verifier accepted forged proofs via inconsistent point-at-infinity handling. [exclude] | — (excluded) |  |
| CF-08 | [tracker#stealthdrop-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#stealthdrop-1) | stealthdrop-1 | Signature-malleability gave many valid nullifiers per claim: repeated airdrop claims. [include] | C_OCCURRENCE_ACCOUNTING |  |
| CF-09 | [tracker#zkdrops-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#zkdrops-1) | zkdrops-1 | EVM/field width gap: x and x%p both accepted as fresh nullifiers. [include] | C_REPRESENTATION |  |
| CF-10 | [tracker#maci-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#maci-1) | maci-1 | Coordinator applied votes to wrong keys to mark them invalid: censored tally proved. [include] | C_ACTIVATION_EXTENT |  |
| CF-11 | [tracker#bulletproofs-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#bulletproofs-1) | bulletproofs-1 | Paper's Fiat-Shamir omitted the commitment: forged range proofs. [exclude] | — (excluded) |  |
| CF-12 | [tracker#plonk-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#plonk-1) | plonk-1 | Implementations hashed too few public inputs: proof forgery to varying extent. [exclude] | — (excluded) |  |
| CF-13 | [tracker#zcash-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#zcash-1) | zcash-1 | Extra setup parameters leaked toxic waste: counterfeit proofs possible. [exclude] | — (excluded) |  |
| CF-14 | [tracker#mimc-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#mimc-1) | mimc-1 | Assignment instead of constraint let attackers set the hash output: faked merkle roots paid out. [include] | C_RELATION_GAP |  |
| CF-15 | [tracker#pse-zkevm-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#pse-zkevm-1) | pse-zkevm-1 | Missing k*n+r<2^256 bound let provers prove false remainders: wrong state updates verified. [include] | C_REPRESENTATION |  |
| CF-16 | [tracker#pse-zkevm-2](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#pse-zkevm-2) | pse-zkevm-2 | Shift-byte shf0 not bound to shift's first byte: false shift proofs verified. [include] | C_RELATION_GAP |  |
| CF-17 | [tracker#dusk-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#dusk-1) | dusk-1 | Proofs leaked witness material: privacy failure with no execution effect. [exclude] | — (excluded) |  |
| CF-18 | [tracker#nightfall-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#nightfall-1) | nightfall-1 | Same EVM/field width gap as CF-09 in a private-transfer system: n and n+p both spend. [include] | C_REPRESENTATION |  |
| CF-19 | [tracker#summa-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#summa-1) | summa-1 | Solvency gate compared against a prover-settable cell: false solvency proved. [include] | C_RELATION_GAP |  |
| CF-20 | [tracker#polygon-zkevm-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#polygon-zkevm-1) | polygon-zkevm-1 | Remainder never bounded below divisor: B=E/A-1, C=(E%A)+A verifies. [include] | C_REPRESENTATION |  |
| CF-21 | [tracker#hexens-polygonzkevm-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#hexens-polygonzkevm-1) | hexens-polygonzkevm-1 | Unconstrained path bit let attackers bind arbitrary values to faked keys. [include] | C_FIELD_MAPPING |  |
| CF-22 | [tracker#hexens-polygonzkevm-2](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#hexens-polygonzkevm-2) | hexens-polygonzkevm-2 | CTX set to 0 aliased global/tx variables: sequencer paid oldStateRoot-sized gas. [include] | C_CONTEXT_IDENTITY |  |
| CF-23 | [tracker#hexens-polygonzkevm-3](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#hexens-polygonzkevm-3) | hexens-polygonzkevm-3 | Unconstrained jump flag allowed arbitrary zkPC: SSTORE gadget set balances. [include] | C_ACTIVATION_EXTENT |  |
| CF-24 | [tracker#zendoo-polynomial-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#zendoo-polynomial-1) | zendoo-polynomial-1 | Untrimmed zero coefficients broke degree assumptions: panics/DoS, no proof effect. [exclude] | — (excluded) |  |
| CF-25 | [tracker#aleo-encryption-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#aleo-encryption-1) | aleo-encryption-1 | input_hash not binding on input across caller/callee: same id, different inputs. [include] | C_RELATION_GAP |  |
| CF-26 | [tracker#light-protocol-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#light-protocol-1) | light-protocol-1 | Same-signer concurrent tree updates interleaved: unpaid merge, no proof disagreement. [exclude] | — (excluded) |  |
| CF-27 | [tracker#zkemail-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#zkemail-1) | zkemail-1 | ^ anchor re-triggerable by 0xff bytes in mail: victim address extracted from subject as from. [include] | C_ACTIVATION_EXTENT |  |

## Counts per AI-suggested mechanism (included findings only)

| Mechanism | Count |
| --- | --- |
| C_ACTIVATION_EXTENT | 3 |
| C_CONTEXT_IDENTITY | 1 |
| C_FIELD_MAPPING | 1 |
| C_OCCURRENCE_ACCOUNTING | 2 |
| C_RELATION_GAP | 5 |
| C_REPRESENTATION | 7 |
| (excluded, no label) | 8 |

## One example per mechanism

- **C_ACTIVATION_EXTENT** — CF-10 (maci-1): Coordinator applied votes to wrong keys to mark them invalid: censored tally proved.
- **C_CONTEXT_IDENTITY** — CF-22 (hexens-polygonzkevm-2): CTX set to 0 aliased global/tx variables: sequencer paid oldStateRoot-sized gas.
- **C_FIELD_MAPPING** — CF-21 (hexens-polygonzkevm-1): Unconstrained path bit let attackers bind arbitrary values to faked keys.
- **C_OCCURRENCE_ACCOUNTING** — CF-06 (aztec-1): Unconstrained 32-bit index assumption let one note mint many nullifiers: double spend.
- **C_RELATION_GAP** — CF-03 (circom-pairing-1): Range-check outputs computed but never constrained: out-of-range pubkeys verify.
- **C_REPRESENTATION** — CF-01 (dark-forest-1): RangeProof accepted out-of-range moves: LessThan inputs never bit-constrained.

## Excluded (with reason)

- **CF-02** (bigint-1): pure circuit-library gap, no evidenced consumer (protocol s2).
- **CF-07** (aztec-2): verifier soundness break, out of scope (contract s5.4).
- **CF-11** (bulletproofs-1): proof-protocol soundness guidance flaw, no application layer.
- **CF-12** (plonk-1): proof-system implementation soundness, multi-implementation aggregate.
- **CF-13** (zcash-1): trusted-setup compromise, out of scope (contract s5.4).
- **CF-17** (dusk-1): privacy leakage unrelated to execution consistency, out of scope.
- **CF-24** (zendoo-polynomial-1): library availability bug (panics/DoS), no proof/consumer disagreement.
- **CF-26** (light-protocol-1): consumer concurrency bug, no proof/consumer disagreement (protocol s2).
