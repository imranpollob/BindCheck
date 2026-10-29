# Taxonomy v1 — blind labeling sheet

Fill this in **before** opening `v1-corpus.md`, so the AI suggestions do not anchor you.
The one-line summary is AI-written; judge from the source link, not the summary.

## Step 1 — include?

Write `Y` if the bug is a disagreement between what the accepted proof establishes and what the consumer (contract, verifier caller, downstream system) treats as authorized. Write `N` for a pure circuit bug with no consumer disagreement, a pure consumer bug, a cryptographic/proof-system soundness break, trusted-setup compromise, privacy-only leak, or DoS with no committed effect. Write `?` if unsure.

## Step 2 — cause label (only if Y; more than one allowed, comma-separated)

| Code | Rule |
| --- | --- |
| C_RELATION_GAP | Accepted constraints omit a dependency needed by consumer interpretation. |
| C_FIELD_MAPPING | Producer/verifier/consumer disagree on identity, order, slice, or forwarded value. |
| C_REPRESENTATION | Field/integer/byte range, width, sign, canonicality, or encoding differs. |
| C_ACTIVATION_EXTENT | Count, prefix, padding, tag, length, or activation differs. |
| C_CONTEXT_IDENTITY | Domain, app, actor, asset, state, or version is not bound to the executing context. |
| C_VERIFICATION_CONFIG | Sound relation selection/key/configuration is interpreted as another relation. |
| C_OCCURRENCE_ACCOUNTING | Identity, multiplicity, or single-use accounting is lost. |
| C_DISCHARGE_TRANSFORMATION | Selection, aggregation, split, cancellation, or pending handling violates policy. |
| C_OTHER_BINDING | Another binding cause; write a short description in the note. |

## Sheet

| ID | Source | System | AI one-line summary | include (Y/N/?) | cause label(s) | note |
| --- | --- | --- | --- | --- | --- | --- |
| CF-01 | [tracker#dark-forest-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#dark-forest-1) | dark-forest-1 | RangeProof accepted out-of-range moves: LessThan inputs never bit-constrained. |  |  |  |
| CF-02 | [tracker#bigint-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#bigint-1) | bigint-1 | BigMod remainder unconstrained to n bits: library-level circuit gap, no evidenced consumer. |  |  |  |
| CF-03 | [tracker#circom-pairing-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#circom-pairing-1) | circom-pairing-1 | Range-check outputs computed but never constrained: out-of-range pubkeys verify. |  |  |  |
| CF-04 | [tracker#semaphore-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#semaphore-1) | semaphore-1 | Consumer accepted uint256 group ids the field-bound verifier always rejects: availability break. |  |  |  |
| CF-05 | [tracker#zk-kit-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#zk-kit-1) | zk-kit-1 | Tree init admitted above-field zero leaves that later inclusion proofs cannot use. |  |  |  |
| CF-06 | [tracker#aztec-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#aztec-1) | aztec-1 | Unconstrained 32-bit index assumption let one note mint many nullifiers: double spend. |  |  |  |
| CF-07 | [tracker#aztec-2](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#aztec-2) | aztec-2 | Verifier accepted forged proofs via inconsistent point-at-infinity handling. |  |  |  |
| CF-08 | [tracker#stealthdrop-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#stealthdrop-1) | stealthdrop-1 | Signature-malleability gave many valid nullifiers per claim: repeated airdrop claims. |  |  |  |
| CF-09 | [tracker#zkdrops-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#zkdrops-1) | zkdrops-1 | EVM/field width gap: x and x%p both accepted as fresh nullifiers. |  |  |  |
| CF-10 | [tracker#maci-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#maci-1) | maci-1 | Coordinator applied votes to wrong keys to mark them invalid: censored tally proved. |  |  |  |
| CF-11 | [tracker#bulletproofs-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#bulletproofs-1) | bulletproofs-1 | Paper's Fiat-Shamir omitted the commitment: forged range proofs. |  |  |  |
| CF-12 | [tracker#plonk-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#plonk-1) | plonk-1 | Implementations hashed too few public inputs: proof forgery to varying extent. |  |  |  |
| CF-13 | [tracker#zcash-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#zcash-1) | zcash-1 | Extra setup parameters leaked toxic waste: counterfeit proofs possible. |  |  |  |
| CF-14 | [tracker#mimc-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#mimc-1) | mimc-1 | Assignment instead of constraint let attackers set the hash output: faked merkle roots paid out. |  |  |  |
| CF-15 | [tracker#pse-zkevm-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#pse-zkevm-1) | pse-zkevm-1 | Missing k*n+r<2^256 bound let provers prove false remainders: wrong state updates verified. |  |  |  |
| CF-16 | [tracker#pse-zkevm-2](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#pse-zkevm-2) | pse-zkevm-2 | Shift-byte shf0 not bound to shift's first byte: false shift proofs verified. |  |  |  |
| CF-17 | [tracker#dusk-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#dusk-1) | dusk-1 | Proofs leaked witness material: privacy failure with no execution effect. |  |  |  |
| CF-18 | [tracker#nightfall-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#nightfall-1) | nightfall-1 | Same EVM/field width gap as CF-09 in a private-transfer system: n and n+p both spend. |  |  |  |
| CF-19 | [tracker#summa-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#summa-1) | summa-1 | Solvency gate compared against a prover-settable cell: false solvency proved. |  |  |  |
| CF-20 | [tracker#polygon-zkevm-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#polygon-zkevm-1) | polygon-zkevm-1 | Remainder never bounded below divisor: B=E/A-1, C=(E%A)+A verifies. |  |  |  |
| CF-21 | [tracker#hexens-polygonzkevm-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#hexens-polygonzkevm-1) | hexens-polygonzkevm-1 | Unconstrained path bit let attackers bind arbitrary values to faked keys. |  |  |  |
| CF-22 | [tracker#hexens-polygonzkevm-2](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#hexens-polygonzkevm-2) | hexens-polygonzkevm-2 | CTX set to 0 aliased global/tx variables: sequencer paid oldStateRoot-sized gas. |  |  |  |
| CF-23 | [tracker#hexens-polygonzkevm-3](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#hexens-polygonzkevm-3) | hexens-polygonzkevm-3 | Unconstrained jump flag allowed arbitrary zkPC: SSTORE gadget set balances. |  |  |  |
| CF-24 | [tracker#zendoo-polynomial-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#zendoo-polynomial-1) | zendoo-polynomial-1 | Untrimmed zero coefficients broke degree assumptions: panics/DoS, no proof effect. |  |  |  |
| CF-25 | [tracker#aleo-encryption-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#aleo-encryption-1) | aleo-encryption-1 | input_hash not binding on input across caller/callee: same id, different inputs. |  |  |  |
| CF-26 | [tracker#light-protocol-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#light-protocol-1) | light-protocol-1 | Same-signer concurrent tree updates interleaved: unpaid merge, no proof disagreement. |  |  |  |
| CF-27 | [tracker#zkemail-1](https://github.com/0xPARC/zk-bug-tracker/blob/56a996672fb50486279126c8e12530f2bf933d0b/README.md#zkemail-1) | zkemail-1 | ^ anchor re-triggerable by 0xff bytes in mail: victim address extracted from subject as from. |  |  |  |
