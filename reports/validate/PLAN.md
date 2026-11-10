# E3 DEV warning review protocol — 2026-11-09

## Frozen inputs and expected review set

The input is the freeze-2 unhinted DEV ledger at analyzer SHA-256
`92789fad12050a3058a21cc5c2326e7d41604ad5ade0f09f72a35789437e6c1a`.
The expected review set is exactly the 18 applicable `VIOLATION` cells in
`reports/freeze2/dev-ledger.csv`: F08/P4, F09/P4, F10/P4, F14/P1, F14/P4,
F25/P3, F27/P3, F30/P1, F34/P3, F34/P4, F35/P1, F38/P3, F39/P1, F44/P1,
F48/P3, F48/P4, F49/P1, H01/P3. This is an expected *inventory*, not an
expected true-positive count. F34's two cells share one card because its four
interacting defects need joint review. Every other cell gets its own card.

## Adjudication rules fixed before source review

1. A detection needs the correct mechanism **and** the correct consumer/key
   location. Source-key equality on a copy or an unused test verifier is not
   an application finding. A warning on a repaired or legitimate revision is a
   false alarm. An unsupported/missing artifact, failed setup, or timeout is
   unresolved; it is never a win or a miss.
2. Record the verifier as real pairing, placeholder, stub/stand-in, mock, or
   fail-closed from its *body*, with file and line. A matching name or parsed
   key alone is insufficient. For P4, distinguish parsed source-key equality
   from an accepting Groth16 implementation. For P3, distinguish a source
   alias/nonbinding key from a feasible replay through an accepting verifier.
3. Trace consumer wiring with imports, constructor/deployment arguments and
   scripts. Mark `USED`, `NOT USED`, or `UNRESOLVED` with evidence. Do not infer
   deployment or key correspondence from a lexical triple.
4. Quote the intended permission, beneficiary, quantity, replay rule, and
   accepted proof purpose from code or project docs. If policy is absent or
   could permit the behavior, say so and ask the human the exact decision.
5. For every P4 equality, inspect repository setup/export scripts for a
   contribution after `groth16 setup`. Record whether the local script would
   create an uncontributed `_0000.zkey`; absent scripts are `MISSING`.
6. AI opinion categories: `TRUE` when the correct live source path and stated
   policy support the warning; `INTENDED-BEHAVIOUR` when the path is real but
   source policy permits it; `FALSE-ALARM` for wrong location, unused copy,
   fail-closed path, or repaired/legitimate case; `UNDECIDABLE` when policy or
   wiring is unresolved. These are review aids, never independent labels or
   E2–E4 validation. Human fields stay blank.

## Scope

Read pinned DEV checkouts and existing raw results only. No live RPC,
transaction, deployment, maintainer contact, held-out analysis, analyzer
change, or new proof is part of this task. The 18 cells are E1 warnings, not
18 vulnerabilities. Record exact source revisions, source excerpts, scripts,
raw result paths and any missing evidence. Do not alter historical reports.
