# D1P-43 typed role-binding targets (frozen before execution)

Date: 2026-10-30  
Status: **PRELIMINARY development protocol**  
Machine-readable freeze: `protocols/d1/d1p-43-role-binding-preliminary.json`

This file freezes the intended policy, distinguishing execution, and expected
tool outcome before the D1P-43 role rule is executed. The examples are exposed
development cases, not blind or held-out evidence. A matching warning is an E1
diagnostic, not a `VIOLATION` verdict. Silence is not
`VERIFIED_WITHIN_SCOPE`.

The D1P-40 audit is controlling: the current Payy producer has 1005 public
leaves while the reviewed consumer relation exposes 1003 words, and its
dynamic-memory tail is unresolved. PY-S03 and PY-S05 therefore have a semantic
seed expectation but a tool-status expectation of `UNKNOWN`; stale selector-
prefix relations must not be used to manufacture a role match.

| ID | Target | Intended policy and reachable execution | Expected result before execution |
|---|---|---|---|
| R1 | WT-C05 | The cross-root branch proves the private origin local root under the giga root. The same-root path remains reachable; a cross-root witness distinguishes the public destination root substituted as member. | `R-ROLE/producer-state-membership`, word 4; research result remains `UNKNOWN` without a new proof route. |
| R2 | WT-C06 | The amount controlling the principal mint is part of the opened note commitment. The mutant commits literal zero while the independent public amount still reaches checks and minting. | `R-ROLE/effect-authorization`, word 2, naming the principal mint. |
| R3 | WT-C09 | Word 2 is amount and word 8 max fee on both sides. Unequal inputs distinguish the producer ABI swap. | `R-ROLE/boundary-role`, words 2 and 8. |
| R4 | WT-S05 | Giga and local roots are admitted only by their corresponding histories. Honest distinct roots fail crossed checks; wrong-set admission supplies the bypass shape. | `R-ROLE/state-identity`, words 3 and 4; research result remains `UNKNOWN` beyond seeded evidence. |
| R5 | WT-S07 | Recipient authorizes the principal mint; relayer authorizes only the fee. A normal successful withdrawal sends both mints to relayer in the mutant. | `R-ROLE/effect-beneficiary`, words 9 and 10, naming the principal mint. |
| R6 | WT-S08 | Word 2 is amount and word 8 max fee on both sides. Unequal values distinguish the consumer formatter swap. | `R-ROLE/boundary-role`, words 2 and 8. |
| R7 | PY-S03 | Burn transfer beneficiary comes from the recipient field, not note kind. The mutant uses message `i+1` instead of `i+4`. | `UNKNOWN` at the D1P-40 mapping gate; no role score. |
| R8 | PY-S05 | Message parsing skips the three-word header. The mutant starts at zero and reinterprets header words as message fields. | `UNKNOWN` at the D1P-40 mapping gate; no role score. |

The original nine D1P-41 policies and executions remain frozen by its protocol.
For the successor run, the only newly expected target diagnostics are
`R-ROLE/state-identity` for E5/WT-S05 and
`R-ROLE/producer-state-membership` for E6/WT-C05. E8/PY-S01 now also must
return `UNKNOWN` because the later D1P-40 audit supersedes the earlier mapping
assumption. The clean WarpToad control E9 is expected to have no target role
diagnostic, which remains an `UNKNOWN` research result rather than safety
evidence.
