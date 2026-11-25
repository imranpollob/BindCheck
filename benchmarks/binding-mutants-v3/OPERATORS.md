# B3 mutation operators

Each operator models the unbound value and the effect of binding findings in `dataset/labels-v1/LABELS-v1.csv` (`binding = Y`; 103 rows: P4 33, P2 23, P1 23, P3 15, P5 7, OTHER 2). It cites the finding IDs it is modelled on. Operators were designed from the LABELS rows and the hosts' code, and every instance is a fail-closed exact-match edit in `make_mutants.py`.

**Exposure disclosure:**
- `binding-mutants-v2/mutants/` was not read.
- `binding-mutants-v2/README.md` was opened once for layout, before the operators were written. It lists the B2 mutant IDs and notes that B2's P5 mutants keep the honest proof accepted by making the consumer misread a proved value. B3's P5 operators (OP-E1, OP-E2, OP-G2) follow from L007, L063 and L180, and none of them truncates a value.
- `binding-mutants-v2/make_mutants.py` and B2's results were not read.

Side: **S** = consumer or vendored verifier, **C** = circuit, **G** = zkVM guest.

| Operator | Side | Pattern | Edit | Unbound value / effect | Modelled on (LABELS-v1) | Instances |
|---|---|---|---|---|---|---|
| OP-C1 | C | P1 | Delete the constraint tying a public output or effect value to the witness | A value the consumer acts on (note owner, output commitment, credited ciphertext handle, stored share) is prover-chosen | L081, L169, L196, L077, L183, L186, L017 | ZK-C01, ZK-C04, DK-C01, DV-C01 |
| OP-C2 | C | P2 | Delete the membership constraint of a spent note in the public root | The prior state (the consumer's stored root) no longer binds what is spent | L048, L014, L076, L166, L149 | ZK-C02, KK-C02 |
| OP-C3 | C | P3 | Delete the constraint deriving the public nullifier from the note | The replay key is prover-chosen, so one note is spent many times | L020, L128, L197, L105, L176, L038 | ZK-C03, KK-C01 |
| OP-C4 | C | P2 | Delete the enforcement of a policy value that the consumer passes as a public input | A config/policy value is bound but not enforced (cap bypass) | L024, L195, L093 | DK-C02 |
| OP-G1 | G | P2 | Delete the guest's freshness or ordering check on the observed remote block | Remote state from the wrong time window is proven | L093, L184, L008, L131 | XC-G01 |
| OP-G2 | G | P5 | Encode a journal field from the wrong source field | The consumer acts on a misplaced proved value (receiver ← sender) | L007, L180, L040 | XC-G02 |
| OP-P1 | S | P1 | Pay `msg.sender` instead of the proved payee | Recipient, fee or refund payee is caller-chosen, so it can be front-run | L015, L041, L059, L106, L010 | KK-S01, KK-S07, XC-S01 |
| OP-P2 | S | P1 | Drop a field from the binding hash of external data | Call data is not in the statement, so a front-runner can rebind the effect | L183, L088, L094, L102, L126 | KK-S04 |
| OP-X2 | S | P2 | Delete the check of a caller-supplied root against stored root history | The prior state is caller-chosen | L114, L014, L076 | KK-S02 |
| OP-X3 | S | P2 | Delete the authentication of caller-supplied context against stored state | Context (roster keys) is not bound to the consumer's state | L091, L024, L149, L195 | DV-S01 |
| OP-X4 | S | P2 | Delete the finality-delay check on observed remote state | A non-final (reorgable) remote state is accepted | L093, L008 | XC-S06 |
| OP-R1 | S | P3 | Delete the replay-key check, or the write that records the key | The same proof or statement is accepted repeatedly | L184, L124, L164, L122, L162 | ZK-S01, DV-S02, DV-S03, KK-S03, XC-S02, XC-S05 |
| OP-V1 | S | P4 | Discard the verifier result: ignore the boolean, return constant-true from the pairing, or swallow the revert | Proof validity is not enforced | L232, L209, L259, L154, L123 | ZK-S03, DV-S04, DV-S05, KK-S06 |
| OP-V2 | S | P4 | Delete the verifier's field-range check on a public input that the consumer uses as a raw key | The replay key aliases `x` with `x + r` | L062, L095, L049, L175 | ZK-S02 |
| OP-V3 | S | P4 | Skip a soundness check inside the verifier (PCS opening / pairing) | Forged proofs pass | L209, L217, L234, L154 | DK-S01 |
| OP-V4 | S | P4 | Skip the proof-system verify call in an adapter or gateway | Any journal digest is accepted | L245, L123, L042 | XC-S04 |
| OP-K1 | S | P4 | Remove program/image-ID pinning (route pin and adapter allowlist) | The program identity is caller-chosen | L019, L215, L218, L042 | XC-S07 |
| OP-E1 | S | P5 | Use the wrong proved slot for the effect | A proved output commitment is stored or sent in the wrong role, so value is duplicated | L063, L159, L007 | ZK-S04, ZK-S05 |
| OP-E2 | S | P5 | Swap the roles of two proved values of the same type in the effect or stored record | Proved recipient and relayer, or sender and receiver, act in swapped roles | L007, L040, L180 | KK-S05, KK-S08, XC-S03 |

## Required coverage
| Requirement | Mutants |
|---|---|
| Consumer-side | 26 `-S` mutants |
| Circuit/guest-side (≥8) | 11: ZK-C01..C04, DK-C01, DK-C02, DV-C01, KK-C01, KK-C02, XC-G01, XC-G02 |
| Domain/context removals (chain, contract, program ID) | KK-S04 (ext-data hash: call data dropped while the chain and pool stay bound), DV-S01 (context: roster), XC-G01 (remote-state window), XC-S07 (program ID) |
| Key-pinning removals | XC-S07 (OP-K1) |
| Encoding/order changes | OP-E1, OP-E2, OP-G2 (6 mutants) |
| Replay-key changes | OP-R1, OP-C3, OP-V2 (9 mutants) |

**Chain-ID and contract-address removals are absent as standalone mutants.** On every B3 host the chain ID and the consumer address are bound twice:
- dark binds them through the public inputs and through the vault-address input;
- kakushi binds them through the public inputs and through `extDataHash`;
- xchain binds them through the commitment preimage and through the guest's event filter.

Removing one site stays bound, which is the decoy shape; removing every site is a broader edit than the operator family allows. Two context mutants stand in for them: KK-S04 removes a field from a domain-bound hash, and XC-S07 removes the program-ID pin. This is a stated limit of B3.

## Per pattern and host
| | zkerc20 | dark | davinci | xchain | kakushi | Total |
|---|---|---|---|---|---|---|
| P1 | 2 | 1 | 1 | 1 | 3 | 8 |
| P2 | 1 | 1 | 1 | 2 | 2 | 7 |
| P3 | 2 | 0 | 2 | 2 | 2 | 8 |
| P4 | 2 | 1 | 2 | 2 | 1 | 8 |
| P5 | 2 | 0 | 0 | 2 | 2 | 6 |
| **Total** | 9 | 3 | 6 | 9 | 10 | **37** |

dark has only three mutants because its consumer binds every effect value redundantly: the state ciphertexts and the nonce are both in the statement. Single-site consumer edits there are decoys (DK-D01), not flaws.

## Decoy operators (semantic-preserving; all five stay bound)
| Decoy | Edit | Why it stays bound | Instance |
|---|---|---|---|
| DEC-1 | Delete `require(valid)` | A redundant `if (!valid) return false` follows, and every caller requires the result | ZK-D01 |
| DEC-2 | Delete the nonce bump in withdraw | The statement includes the available-balance ciphertext, which every withdraw changes | DK-D01 |
| DEC-3 | Replace the dummy `x·x` rows for the ctx public inputs with 0 | ctx still appears in range and hash constraints, so its verifier coefficient is non-zero | DV-D01 |
| DEC-4 | Delete the recipient's 160-bit range check in a Noir circuit | recipient remains a public input bound by the UltraHonk transcript, and the consumer passes a uint160 | KK-D01 |
| DEC-5 | Delete the adapter image-ID allowlist check | Every route also pins its image ID in `Connector._checkRouteImageId` | XC-D01 |
