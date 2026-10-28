# D1P-32 — baselines on the binding-mutant benchmark

Date: 2026-10-28

Repository base: `ba571ffb8a218ffc6205753d69cd128331163deb`

Frozen protocol and scoring: `paper/baselines.md`

Raw evidence: `results/raw/D1P-32/`

## Result

The generic compiler/static-analysis baselines emitted no diagnostic that
described a proof-to-execution mismatch. Under the frozen scoring rule, Noir
earned **10 detected-E1-lint** cells by naming an unused value at the mutant
locus and Slither earned **13 detected-E1-lint** cells by naming the affected
variable or function. These credits are deliberately separate from mismatch
detections and include nondiscriminating warnings.

All 30 frozen mutants were materialized and compiled successfully before
scoring. For the WarpToad circuit mutants, the recorded honest-witness outcome
matched the manifest's expected accept/reject bit in every case where that
control is specified.

The new handwritten Foundry same-policy arm detected eight of the nine
WarpToad consumer mutants and the already archived M-SRC variant. Its generic
G1/G2/G4/G5 suite detected the two nullifier-accounting mutants and the
removed verifier gate; G4 supply accounting passed every case and added no
detection. The policy arm passed pinned WarpToad and M-DOM. It missed
WT-S06 because the frozen D1P-32 property covers mint amount/beneficiary,
admitted roots, verifier gating, single-use nullifiers, and rollback, not a
maximum-fee ceiling. No Payy or circuit-mutant fuzzer harness was invented
after seeing results; those cells remain unresolved.

Echidna 2.3.3 is installed, but all three WarpToad attempts stopped before
fuzzing because its combined-JSON loader rejected unlinked `LazyIMT` (the
first full-source attempt similarly rejected `GigaBridge`). Removing unrelated
sources did not cure the library-link boundary. These are unresolved runs, not
misses. CCC-Check and SmartAxe retain their D1P-22 installation dispositions;
Picus retains its native-input disposition. No adapter was introduced.

No `bb` or `nargo` process was present before the build and analysis runs.
The benchmark is development evidence over already-exposed WarpToad and Payy
families; it is not held-out evidence and does not establish prevalence or
transfer.

## Scoring key and operator classes

- **D** — detected: the tool/property describes the seeded defect at E1 or
  higher;
- **E** — detected-E1-lint: a warning names its location or variable but does
  not describe the mismatch;
- **M** — missed after a completed applicable run;
- **U** — unsupported/not applicable to the input or arm;
- **R** — unresolved: timeout, pre-analysis failure, or missing required
  harness. It is never treated as safe.

For the compact table, the 30 frozen manifest operators are grouped without
changing any per-mutant score: **G** guards/gates (9), **P** public-input
exposure/private substitution (5), **A** state/accounting (3), **W** word
mapping/control-flow (6), **S** root/check swaps (2), **V** value/domain/
beneficiary binding (4), and **C** commitment binding (1). A cell such as
`E3/M2/U4` reports counts, not precedence.

## Paper-ready tool × operator-class table

| Tool / arm | G (9) | P (5) | A (3) | W (6) | S (2) | V (4) | C (1) | Total (30) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Noir checks, generic | E3/M2/U4 | E5 | U3 | M2/U4 | M1/U1 | E1/M1/U2 | E1 | **E10/M6/U14** |
| Noir checks, same-policy | U9 | U5 | U3 | U6 | U2 | U4 | U1 | **U30** |
| Slither, generic | E3/M1/U5 | U5 | E3 | E4/U2 | E1/U1 | E2/U2 | U1 | **E13/M1/U16** |
| Slither, same-policy | U9 | U5 | U3 | U6 | U2 | U4 | U1 | **U30** |
| Mythril, generic | U5/R4 | U5 | R3 | U2/R4 | U1/R1 | U2/R2 | U1 | **U16/R14** |
| Mythril, same-policy | U5/R4 | U5 | R3 | U2/R4 | U1/R1 | U2/R2 | U1 | **U16/R14** |
| Foundry G1/G2/G4/G5 | D1/M2/R6 | R5 | D2/R1 | M1/R5 | M1/R1 | M2/R2 | R1 | **D3/M6/R21** |
| Foundry same-policy | D3/R6 | R5 | D2/R1 | D1/R5 | D1/R1 | D1/M1/R2 | R1 | **D8/M1/R21** |
| Echidna generic | R9 | R5 | R3 | R6 | R2 | R4 | R1 | **R30** |
| Echidna same-policy | R9 | R5 | R3 | R6 | R2 | R4 | R1 | **R30** |
| CCC-Check, generic | U9 | U5 | U3 | U6 | U2 | U4 | U1 | **U30** |
| Picus, generic | U9 | U5 | U3 | U6 | U2 | U4 | U1 | **U30** |
| SmartAxe, generic | U6/R3 | U5 | U1/R2 | U5/R1 | U1/R1 | U2/R2 | U1 | **U21/R9** |

The Mythril row records the bounded bytecode runs as unresolved unless its
output localizes a seeded operator; the same-policy row is unresolved on the
14 consumer mutants because no frozen assertion wrapper exists. Circuit
inputs are unsupported. SmartAxe is unresolved only on WarpToad consumer
bytecode because the official artifact remains unavailable; its other cells
are outside the tool's admitted input/scope.

## Per-mutant classifications

The table shows the informative generic arm for Noir, Slither, and Mythril,
both Foundry arms, and Echidna same-policy. Unsupported/unavailable tools have
the uniform dispositions above.

| Mutant | Frozen operator | Noir G | Slither G | Mythril G | Foundry G | Foundry sigma | Echidna sigma |
|---|---|---:|---:|---:|---:|---:|---:|
| WT-C01 | `leave-public-unconstrained` | E | U | U | R | R | R |
| WT-C02 | `leave-public-unconstrained` | E | U | U | R | R | R |
| WT-C03 | `replace-public-with-private` | E | U | U | R | R | R |
| WT-C04 | `remove-guard` | E | U | U | R | R | R |
| WT-C05 | `swap-checks` | M | U | U | R | R | R |
| WT-C06 | `unbind-amount` | M | U | U | R | R | R |
| WT-C07 | `unbind-domain` | E | U | U | R | R | R |
| WT-C08 | `remove-guard` | E | U | U | R | R | R |
| WT-C09 | `misorder-words` | M | U | U | R | R | R |
| WT-S01 | `remove-guard` | U | E | R | M | D | R |
| WT-S02 | `remove-guard` | U | E | R | M | D | R |
| WT-S03 | `drop-accounting` | U | E | R | D | D | R |
| WT-S04 | `remove-gate` | U | E | R | D | D | R |
| WT-S05 | `swap-checks` | U | E | R | M | D | R |
| WT-S06 | `unbind-fee` | U | E | R | M | M | R |
| WT-S07 | `misdirect-beneficiary` | U | E | R | M | D | R |
| WT-S08 | `misorder-words` | U | E | R | M | D | R |
| WT-S09 | `drop-write` | U | E | R | D | D | R |
| PY-C01 | `remove-guard` | M | U | U | R | R | R |
| PY-C02 | `leave-public-unconstrained` | E | U | U | R | R | R |
| PY-C03 | `remove-guard` | M | U | U | R | R | R |
| PY-C04 | `unbind-commitment` | E | U | U | R | R | R |
| PY-C05 | `remove-config-check` | E | U | U | R | R | R |
| PY-C06 | `leave-public-unconstrained` | E | U | U | R | R | R |
| PY-C07 | `misorder-words` | M | U | U | R | R | R |
| PY-S01 | `remove-guard` | U | M | R | R | R | R |
| PY-S02 | `drop-single-use` | U | E | R | R | R | R |
| PY-S03 | `misbind-word` | U | E | R | R | R | R |
| PY-S04 | `activate-dead-path` | U | E | R | R | R | R |
| PY-S05 | `offset` | U | E | R | R | R | R |

### Why the localized lints count, but only as E1 lint

Noir named the newly unused variables in WT-C01/02/03/04/07/08 and
PY-C02/04/05/06. Slither's naming, boolean, reentrancy, or uninitialized-state
reports named the seeded variable/function on every WarpToad consumer mutant
and on PY-S02 through PY-S05; PY-S01 had no such report. None related producer
enforcement to the consumer effect, so none is a mismatch detection.

## Fairness fix A — sequential Mythril retry

The five D1P-22 targets were started strictly one after another, each with a
fresh isolated Mythril state directory and the same 1,800-second analysis cap.
The earlier concurrent records remain unchanged under `results/raw/D1P-22/`;
the retry is under `results/raw/D1P-32/mythril-sequential-*`.

| Target | Old D1P-22 result | Sequential retry | Scored disposition |
|---|---|---|---|
| Payy earlier | 1,800 s timeout | outer kill at 1,810.16 s; no JSON | R (unchanged) |
| Payy check-added | 1,800 s timeout | internal 1,800 s cap; exit `1`, valid JSON with 45 generic issues | R control (unchanged) |
| WarpToad pinned | startup data-directory race | `SIGSEGV`/exit `-11` at 30.22 s; no JSON | R control; startup-race reason replaced by isolated crash |
| M-DOM | exit `-11` during concurrent startup | internal 1,800 s cap; exit `1`, valid JSON with 28 generic issues | R; concurrent-crash reason replaced by bounded incomplete analysis |
| M-SRC | 1,800 s timeout | internal 1,800 s cap; exit `1`, valid JSON with 28 generic issues | R (unchanged) |

Mythril's JSON marks the three warning-bearing outputs `success=true`, meaning
that the warning report itself is valid; it does not mean that analysis
completed beyond the configured execution cap. Their warning classes were
generic arithmetic, external-call, state-access, environment, and arbitrary-
storage reports. No retry output localized a benchmark or development-case
binding mismatch. The correction is fairness evidence about startup
isolation, not evidence of absence.

## Fairness fix B — WarpToad same-policy fuzz harness

The harness uses the actual pinned or mutated `WarpToadCore.sol`, not a
reimplementation of `mint`. Its verifier stub is an explicit relational
boundary: it checks the proof hash and all eleven expected public words and
also supports a forced-rejection mode for verifier gating. It is not an
always-successful verifier. The handler generates typed mint calldata plus
arbitrary ABI tails and checks:

- committed total mint and recipient/relayer balances against the public
  amount and beneficiaries (including a fixed nonzero-fee branch);
- membership of every successful giga/local root in the admitted histories;
- rejection of a second identical nullifier use;
- rollback of balances, supply, and the nullifier mapping on reverts; and
- rejection when the verifier boundary returns false.

Foundry used `runs=256`, `depth=100`, `fail_on_revert=false`. The generic G4
control derives net mint/burn amounts from the token's `Transfer` logs and
compares them with the committed total-supply delta. Pinned and M-DOM passed
all seven invariants. M-SRC failed `invariant_roots_are_admitted`. On the
nine WarpToad consumer mutants, S01/S02 failed root admission, S03/S09 failed
single use, S04 failed verifier gating, S05/S08 rejected a valid relational
call, and S07 failed the beneficiary check; S06 passed and is scored missed.
These are E1 property counterexamples under a handwritten stub boundary, not
E4 executions with real proofs.

### Harness effort

| Item | Measured effort |
|---|---:|
| Shared Solidity harness | 156 nonblank, non-comment lines |
| Foundry configuration | 18 nonblank lines |
| Authoring wall time | 0.16 h: 0.14 h initial plus 0.02 h for the preregistered G4 completion |
| Per-mutant source port | 0 new lines; 0.03 h scripted copying/runs |
| Corrections | 7 compile/setup corrections before the first passing run; 1 later completeness correction for G4; all records retained |
| Human inspection | none recorded; AI-authored artifact |

The shared test SHA-256 is
`a33732d2262e8115bd4a1ef66cc5f075f5d015cfbe686df14c2fc58862670370`;
the Foundry configuration SHA-256 is
`0a7b8b389511a9508a444d9eca7c106e13f1bae419f082b659d0b63b8e28363d`.

## Analyst effort and run cost

| Tool | New analyst input | Analysis wall / outcome |
|---|---|---|
| Noir beta.14/beta.22 | 0 property lines; about 0.05 h launch/adjudication | 32 default/lookback commands, 19.55 s aggregate; beta.22 does not accept the lookback flag, retained as setup evidence |
| Slither 0.11.6 | 0 detector lines; about 0.30 h standard-JSON setup and adjudication | 14 scored runs, 313.22 s aggregate |
| Mythril 0.24.8 | 0 property lines; about 0.05 h bytecode preparation | 14 sequential benchmark runs plus 5 fairness retries at a 1,800 s/case analysis cap; all unresolved and no sigma assertion wrapper |
| Foundry 1.8.6 | 174 shared nonblank lines; 0.19 h including ports | 256×100 calls/case; scored runs complete in seconds after compilation |
| Echidna 2.3.3 | reused the pre-G4 150-line Foundry harness; about 0.05 h adapter attempts | 9 attempts, 32.63 s aggregate; stopped before fuzzing on unlinked libraries |
| CCC-Check / Picus / SmartAxe | 0 new lines; D1P-22 dispositions reused | unavailable or unsupported/unresolved as shown; no mutant analysis run claimed |

Machine analysis time is separate from analyst time. Failed setup attempts,
compiler output, hashes, stdout/stderr, and final outputs are all retained.

## Boundaries

The Foundry property is a manually authored policy baseline. It does not
derive obligations, and its success cannot be credited as automatic policy
inference. The relational verifier stub is suitable for E1 property testing,
not for an E3/E4 claim. Likewise, localized compiler/static-analysis warnings
do not establish exploitability, and a missed mutant is not a safety result.
