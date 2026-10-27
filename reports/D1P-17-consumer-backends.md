# D1P-17 — bounded consumer-arithmetic backend study

Date: 27 October 2026  
Application: WarpToad (`warptoad/warp-toad`)  
Pinned application revision: `973e7d1e4b60d0d8a8ca299b0cabd9193b147ef8`  
Repository base revision: `fc7416a5e546c8c6557ddccc04756034a1d15e4a`  
Task status: **DONE**  
D1 security verdict: **UNKNOWN**

## 1. Outcome

The controlling diagnosis is: **“The current consumer-only encoding times
out; nonlinear fee arithmetic is a suspected bottleneck.”** This study does
not claim that multiplication causes the timeout or that other WarpToad/O1
queries will fail.

D1P-17 added two mutually exclusive backend options to the shared joint
encoder, passed all 16 required deterministic polarity controls, froze the
five-call schedule at SHA-256
`42fb45ede284f11445bf9109e708c60ffd56dcf969fdb134d6e563b9ffe509ba`,
and consumed each scheduled attempt once without tuning:

| Backend/query | Process disposition | Solver answer | Seconds | Result |
|---|---|---|---:|---|
| T-ARITH Q1, producer dropped | completed, exit 0 | `UNSAT` | 8.217012 | abstract diagnostic UNSAT |
| T-ARITH Q2, full producer | timeout; confirmed runner cleanup | none | 300.108170 | `UNKNOWN` |
| T-OVF Q1, producer dropped | timeout; confirmed runner cleanup | none | 300.078000 | `UNKNOWN` |
| T-OVF Q2, full producer | timeout; confirmed runner cleanup | none | 300.096819 | `UNKNOWN` |
| T-OVF Q3, full producer | root-monitor loss; `EPERM`; confirmed -9 | none | 232.712668 | `UNKNOWN` |

Charged solver time was 1,140.929680 seconds, below the 1,500 solver-second
maximum. There was no SAT candidate, proof generation, V-EXEC call, combined
transformation, retry, or post-freeze adjustment.

## 2. T-ARITH

T-ARITH replaces only
`fee_factor * (basefee + priority_fee)` as the value of `fee_amount` with a
fresh 256-bit variable. It retains the original fee/non-fee branch, addition
and multiplication successful-path overflow guards, `fee_amount <= max_fee`,
`fee_amount <= amount`, nonzero-recipient checks, total-supply bound, exact
mint occurrence structure, nullifier write, and unchanged G1–G5 policy. It
adds no convenient numeric bound. The full-producer Q2 also retains the
original circuit constraint `max_fee <= amount`; Q1 retains its pre-existing
D1P-14C definition that drops all of `R_v`, rather than selectively adding a
producer fact.

Preservation argument: take any concrete successful execution and assign the
fresh abstract `fee_amount` the original uint256 value
`fee_factor * (basefee + priority_fee)`. The original execution already
satisfies the retained overflow, cap, amount, branch, beneficiary, mint and
state guards, so it extends to an abstract execution with the same relevant
effects. Therefore the abstract relation over-approximates the concrete fee
computation. Abstract UNSAT transfers only under this inclusion argument.

T-ARITH Q1 returned UNSAT. This resolves that abstract, producer-dropped
diagnostic under the preservation argument; it is not a full-producer result,
semantic-equivalence proof, automatic-extraction claim, `VERIFIED_WITHIN_SCOPE`
verdict, or D1 capability evidence. The consumer summary remains
`MANUAL / ASSUMED`. T-ARITH Q2 timed out and remains `UNKNOWN`.

Any T-ARITH SAT—including NONVAC SAT—would have been only a candidate requiring
validation against the original fee arithmetic, the full producer relation,
and consumer execution. No SAT occurred, so that route was not entered.

## 3. T-OVF

T-OVF leaves the fee equation and every other constraint unchanged and
replaces the two zero-extension/check spellings with cvc5's native unsigned-
overflow predicates:

```text
not bvuaddo(x,y)
not bvumulo(x,y)
```

For unsigned width `w`, the intended identities are:

- `not bvumulo(x,y)` iff the upper `w` bits of the `2w`-bit product of the
  `w`-bit zero extensions of `x` and `y` are zero; and
- `not bvuaddo(x,y)` iff `bvadd(x,y) >=u x` (equivalently for `y`).

Exactly two general symbolic checks ran at the actual width, 256 bits, with
60-second bounds:

| Identity | Answer | Seconds | Disposition |
|---|---|---:|---|
| addition | `UNSAT` for the XOR | 0.163076 | resolved for this check |
| multiplication | no answer / timeout | 60.051940 | unresolved |

The required overall status is **equivalence unresolved**. T-OVF is not
validated. Its deterministic controls and primary attempts are observations,
not a substitute for the unresolved symbolic equivalence.

## 4. Backend scope and controls

`BASE`, `T-ARITH`, and `T-OVF` are declared at the common `encode_query`
boundary. Exactly one option is accepted per generated query; a combined
`T-ARITH+T-OVF` option is rejected. Both transformations are available
identically to Q1, Q2, Q3 and later method arms. Neither demonstrates a
consumer-direction advantage.

All eight D1P-14D fixed-input controls ran under each transformation with a
30-second maximum and the same required polarity:

| Backend | C1 | C2 | C3 | C4 | Result |
|---|---|---|---|---|---|
| T-ARITH | positive SAT / base UNSAT | positive SAT / base UNSAT | positive SAT / base UNSAT | positive SAT / base UNSAT | 8/8 pass |
| T-OVF | positive SAT / base UNSAT | positive SAT / base UNSAT | positive SAT / base UNSAT | positive SAT / base UNSAT | 8/8 pass |

Every control completed in 0.052995–0.161517 seconds with exit zero. These are
regression tests, not proof of either transformation.

## 5. Frozen primary execution and load

Before each primary launch, the runner found no concurrent cvc5, Nargo,
Cargo/rustc/clang, Make/Ninja, Xcode build, or Swift build process. The
recorded macOS load averages are observations, not exclusion criteria:

| Attempt | Load before | Load after | Peak sampled RSS |
|---|---|---|---:|
| T-ARITH Q1 | `{ 13.45 6.75 4.91 }` | `{ 13.44 6.97 5.01 }` | 866,566,144 B |
| T-ARITH Q2 | `{ 13.44 6.97 5.01 }` | `{ 2.86 5.32 4.93 }` | 847,675,392 B |
| T-OVF Q1 | `{ 2.86 5.32 4.93 }` | `{ 3.81 4.30 4.55 }` | 1,376,337,920 B |
| T-OVF Q2 | `{ 3.81 4.30 4.55 }` | `{ 3.84 4.05 4.35 }` | 972,800,000 B |
| T-OVF Q3 | `{ 3.77 4.04 4.34 }` | `{ 9.82 5.02 4.58 }` | 1,439,432,704 B |

T-OVF Q3's root disappeared from libproc at 231.859236 seconds. Exit was not
confirmed during the next 0.5 seconds; a zero-signal probe reported the PID
still existed; group cleanup then failed with `Operation not permitted`; and
`wait()` confirmed `-9`. No successful runner kill was recorded, so the source
of `SIGKILL` is unidentified. See `reports/D1P-17-monitor.md`.

## 6. Tools, tests and commands

Host and tools:

- macOS 27.0.1 arm64;
- Python 3.13.9;
- pytest 9.0.1;
- native arm64 cvc5 1.4.2 git `282d5e0`, GPL/CoCoA, SHA-256
  `a083a7f56a3f61691583b699076322bbcbf6732decfb4f6dc41850dbcc3df027`.

Principal commands, in order:

```text
PYTHONPATH=src python3 scripts/d1p_17_backend_study.py prepare
PYTHONPATH=src pytest -q tests/d1/test_d1p17_backend.py
PYTHONPATH=src python3 scripts/d1p_17_backend_study.py monitor-tests
PYTHONPATH=src python3 scripts/d1p_17_backend_study.py equivalence
PYTHONPATH=src python3 scripts/d1p_17_backend_study.py controls
python3 -m py_compile src/bindcheck_d1/process_runner_d1p17.py scripts/d1p_17_backend_study.py
PYTHONPATH=src pytest -q tests/d1/test_d1p17_backend.py
PYTHONPATH=src python3 scripts/d1p_17_backend_study.py freeze
PYTHONPATH=src python3 scripts/d1p_17_backend_study.py run
```

The focused backend suite passed 6/6 both times. Preparation parse-checked all
16 controls, five primary inputs and two equivalence inputs with pinned cvc5.
The default `BASE` encoder regenerated frozen D1P-14C Q1 byte-identically at
SHA-256 `a188b4a155b41b92a2531d0ae7c92593baaaf373f64f61068c739c66d2a5fa2b`.

## 7. Evidence and changed files

Tracked implementation and protocol:

- `src/bindcheck_d1/joint_warptoad.py`;
- `src/bindcheck_d1/joint_warptoad_d1p14d.py`;
- `src/bindcheck_d1/process_runner_d1p17.py`;
- `scripts/d1p_17_backend_study.py`;
- `tests/d1/test_d1p17_backend.py`;
- `protocols/d1/d1p-17-consumer-backends.json`;
- `metadata/d1/d1p-17-primary-freeze.json`;
- this report and `reports/D1P-17-monitor.md`.

Ignored raw evidence is under `results/raw/D1P-17/` (154 files, approximately
186 MiB), including exact copied predecessor inputs, generated SMT/certificates,
parse preparation, monitor tests, both equivalence calls, all 16 controls,
the primary ledger and per-call stdout/stderr/chronology.

`README.md` and `docs/project-status.md` were not edited. D1P-14B/C/D and all
prior reports and raw evidence were read only. No commit, push, merge, proof,
live-chain action, external contact, or held-out evaluation occurred.

## 8. Assumptions, limitations and next task

The fixed state, application artifact, decoder, DRAFT policy, L0 Poseidon havoc
layer, verifier-soundness assumption, and `MANUAL / ASSUMED` consumer summary
remain as declared by D1P-14C/D. Q1 intentionally drops the producer relation.
The sampled 4 GiB policy is not a hard address-space cap. Native-Mac timings
do not demonstrate performance advantage. Timeouts and monitor loss are
`UNKNOWN`, never safe results.

Unexpected observations were the unresolved 256-bit multiplication
equivalence check and the second Q3 root-loss/`EPERM`/`-9` chronology. Neither
was retried or used to tune an input.

Recommended next task: independently resolve T-OVF multiplication equivalence
without rerunning or tuning these five diagnostics. A measurable completion
criterion is either a checked general 256-bit proof of the stated identity or
an explicit `equivalence unresolved` closure under a separately frozen method;
until then, do not use T-OVF results for a semantic claim.

