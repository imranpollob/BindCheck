# Evidence ledger: warning → experiment correspondence (X-AV v1.1 + TC02/TE04/TE05)

Date: 2026-10-30 (lane-x-muse). Status: ACTIVE (supersedes the v1.1
`results.json` grades where noted; does not rewrite immutable reports).

## 0. Grading rule (author policy review, 2026-10-30)

Every E4 row must show the claimed defect — not setup or an inherited bug —
causes the effect: run the SAME transaction on original and defective (and
repaired) versions with MATCHING keys and identical initial state.
Cross-key verification failure is not a contrast. Mock-verifier rows do not
meet the contract's E2 (a model satisfying the ACTUAL compiled producer
relation, decoder and consumer model): the mock stands in for proof
acceptance, so they are graded **E1+mock** (consumer-logic demonstration
contingent on assumed proof acceptance), never E2. WarpToad policy is
scoped to the proof-consuming `mint` path (the dev contract's
`getFreeShit` faucet is out of scope; all replays below use `mint`).
Payy's legitimate substitute-recipient mechanism (`substituteBurn` /
`substitutedBurns`) is excluded when judging PY-S03: no substitute was
registered in that run, so the substitute path was inactive.

## 1. Plan-timing flags (disclosure)

- D1P-31 warnings known: report commit `88bf69c` (2026-10-28 02:27).
- `witness_synth_v1.py` plans WRITTEN after: commit `7488dcd`
  (2026-10-28 03:28). Authors knew the warning inventory and mutant ground
  truth when writing plans.
- Plans REVISED after initial results: shape dispatch + Payy mock harness,
  commit `c7097be` (2026-10-28 11:21), after the v1 run and after the
  WarpToad→Payy misgrade incident (caught before reporting; fixed by
  routing all PY-* rows to `run_payy`).
- Mitigation (not cure): `plan_for` dispatches by warning SHAPE
  (rule + location + evidence-path spelling), never by mutant name; every
  plan names its mutated word(s) as data. Consequence: the plans
  demonstrate warnings are drivable to proofs/effects, NOT blind automatic
  discovery on the benchmark. Any discovery claim needs a frozen-plan
  rerun on unseen warnings.

## 2. Row-by-row correspondence (E>=2 in v1.1 `results.json`)

Format: warning word == mutant edit word == experiment word; effect;
location. `results.json` grade → ledger grade.

Adjudication keys (tracked: `warning_key` in `src/bindcheck_d1/xav_core.py`):
`(target, rule, public word, effect)` — R-BIND takes the ABI leaf/range,
R-EFFECT the paths range + sorted effect kinds (line numbers excluded as
version-volatile), R-CONSUMER the evidence consumer path,
R-POLARITY `single-use` + polarity. Warning ids (`W001`, …) and `:line`
locations are analyzer-version-specific and informational only, so the
AI1/AI2 v2.0 re-run remaps mechanically: extract keys from the new
warnings file, join against `OVERRIDES`, and re-assert totals. Rows whose
key is absent keep the driver grade (plus the E1+mock rule, §5).

### WarpToad circuit rows (mutant circuits, pinned consumer)

| row | same word | same effect | same location | grade |
|---|---|---|---|---|
| WT-C01 W001 R-BIND | `nullifier`: warning `abi.nullifier`, mutant removes the nullifier assert, plan substitutes `0x111…` | double mint from two proofs (honest note + attacker nullifier both spend) | circuit `main.nr:66`, consumer mint path | E4, stands |
| WT-C04 W001/W002 R-BIND | `giga_root` / `destination_local_root`: warnings `abi.giga_root` + `abi.destination_local_root`, mutant removes `evm_merkle_verify`, anchor-tree plan fabricates origin | mint from fabricated origin root | circuit `main.nr:45`, consumer mint path | E4/E4, stand (one repair covers both) |
| WT-C07 W001 R-BIND | `chain_id`: warning `abi.chain_id`, mutant binds commitment to 0, plan sets public word `0x1` over attacker tree | proof verifies; consumer reverts dataless (contained same-chain; cross-chain argued only; OOG not excluded) | circuit `main.nr:65` | E3, stands as contained |
| WT-C08 W001 R-BIND + W002 R-EFFECT | `recipient_address`: warning `abi.recipient_address` + `:171` effect, mutant removes nonzero-recipient assert, plan sets `0x0` | proof verifies; consumer reverts `ERC20InvalidReceiver` (contained; scope note: experiment used the zero address — an owner-chosen NONZERO recipient may be permitted per policy review) | circuit `main.nr:57`, consumer `:171` | E3/E3, stand as contained |
| WT-C02 W001 R-BIND | `max_fee`: warning `abi.max_fee`, mutant removes the bound, plan sets `0x0` | proof verifies; consumer reverts `_relayerFee is larger than _maxFee` (contained) | circuit `main.nr:28` | E3-contained stands, BUT warning-quality flag (§4): the restored assert still accepts `max_fee=0` (see repair row) |
| WT-C03 W001 R-BIND | `aztec_warptoad_address`: warning word 5, M-DOM reuse mutant, aztec-branch plan | fresh E3 on byte-identical artifact + preserved D1P-15 foreign-note E4 (2 counted manual steps) | circuit word 5 | E4-preserved, stands |

### WarpToad consumer rows (pinned circuit, mutant consumers)

| row | same word | same effect | same location | grade |
|---|---|---|---|---|
| WT-S01 W001 R-CONSUMER | `destination_local_root`: evidence path names the word, mutant removes K2 admission, anchor-tree plan mints over unadmitted root (`localRootAdmitted:false`) | unauthorized mint over unadmitted root | consumer K2 line (R-CONSUMER prints no line — location gap recorded) | E4, stands |
| WT-S02 W001 R-CONSUMER | `giga_root`: evidence path names the word, mutant removes K1 admission | v1.1 run: mint over fabricated `0x1234` with `gigaRootAdmitted:true` | consumer K1 line (no line printed) | v1.1 E4 WITHDRAWN as run — setup artifact (§3); defect isolated by corrected experiment (E4 for the K1 defect with honest-seeded history) |
| WT-S03 W001 R-CONSUMER | `nullifier`: evidence path names the word, mutant removes check+write, replay plan double-submits honest proof | same note mints twice | consumer nullifier lines (no line printed) | E4, stands |
| WT-S06 W001 R-CONSUMER | `max_fee`: evidence path names the word, mutant removes fee-cap admission, plan proves `max_fee=0` | relayer over-charge above stated max (`~0.24e18` over `0`) | consumer fee-cap line (no line printed) | E4, stands (new in v1.1) |
| WT-S09 W001 R-POLARITY | nullifier polarity: mutant drops the write (check kept), replay plan resubmits | same note mints twice | consumer nullifier write (no line printed) | E4, stands |

### Payy rows

| row | correspondence | grade |
|---|---|---|
| PY-C02 W001 R-BIND `messages[0]..messages[999]` | warning range covers the removed `:74` export assert; mutant proves attacker mint @0–3 (TC02 slot 009) and attacker burn @4–8; TE05 wraps the ACTIVE proof to a verifying mutant final proof; original/repaired reject the same witness at ACVM | E3 on its own mutation (TE05). The v1.1 E4 rode on the tail block — corrected. |
| PY-C02 W002 R-EFFECT `:850` | same block under both keys reverts `Mint value invalid` BEFORE proof verification (gate order `RollupV1.sol:349` before `:357`); zero state change | E1 (contained). The v1.1 E4 rode on TE04's tail block — corrected. |
| PY-C02 W003 R-CONSUMER `commit_hash` | offchain (Celestia) commitment placeholder; no experiment | E1, stands — author-labeled out of scope (data availability) per the 2026-10-30 policy addendum (`39ebeab`): structurally accurate, not a false positive, not a confirmed defect; acceptable-remaining after a valid repair |
| PY-S01 W002 R-EFFECT `:842` + W004 R-POLARITY `:357` | unregistered-mint admission removed; TE06 real-verifier replay settles the unregistered mint on the mutant (`height 1`, spent) while the same transaction reverts `Mint value invalid` on pinned (zero state change) | E4 (TE06, zero mock). Same word/effect/location; committed-key proofs, matching keys. |
| PY-S02 W002 `:850` + W004 `:357` | single-use removed; real proof settles honestly on both sides (also the Payy honest control) | E3: second settlement UNPROVABLE at circuit level — re-processing the same mint note fails at witness construction (`CollisionError`) and, with re-reference tolerated, at the `agg_utxo` output-slot emptiness check (`:140`). The missing spent check is defense-in-depth removal; the effect is unreachable with real proofs alone (§10). Mock double kept as logic illustration only. |
| PY-S03 W002 `:851` | burn recipient misbound to the note-kind word; TE06 real-verifier replay settles on both sides with the same proof: mutant pays 7 to the note-kind-derived address, pinned pays 7 to the message recipient (`0xdead`); NO substitute registered either side | E4 (TE06, zero mock). Substitute path inactive both sides. |
| PY-S04 W002 `:853` | dead kind-4 settled as burn in the mock replay (recipient +1000) | E1+mock retained: no pinned-producible kind-4 export exists (inner proofs only yield kinds 2/3; a kind-4 word needs the export-removal mutation, i.e. a different defect). Real-proof lift infeasible by construction; recorded, not attempted. |
| all other Payy rows (31) | no real inner-proof vector (Rust stack) | E1, stand |

Corrected totals over the 53 v1.1 warnings (TE06 final): E4: 11
(WT-C01, WT-C04×2, WT-S01, WT-S02-corrected, WT-S03, WT-S06, WT-S09,
PY-S01 W002/W004, PY-S03 W002); E4-preserved: 1 (WT-C03); E3: 7
(WT-C02, WT-C07, WT-C08×2, PY-C02 W001, PY-S02 W002/W004); E1+mock: 1
(PY-S04 W002, infeasible by construction); E1: 33 (incl. PY-C02 W002
and W003). 11+1+7+1+33 = 53, asserted by `reproduce.py ledger`.
The TE04 inherited-tail E4 is recorded at defect level (§6), not as an
extra warning row: it was produced through PY-C02's mutant stack but
the original circuit accepts the same tail block.

## 3. Repair checks (`scripts/xav/repair_check.py`, evidence `results/raw/REPAIR/`)

Each repair restores exactly the removed source line; the script asserts
the repaired file is byte-identical to the pinned baseline (SHA-256)
before running. No new proofs are generated.

Producer-side (pinned circuit, `nargo execute`; attacker must FAIL,
honest `D1P15_12R` must PASS):

| mutant | repair == pinned bytes | honest | attacker | verdict |
|---|---|---|---|---|
| WT-C01 | yes | PASS | BLOCKED (`nullifier doesn't match`) | REPAIR-OK |
| WT-C04 (covers W001+W002) | yes | PASS | BLOCKED (giga membership) | REPAIR-OK |
| WT-C03 | yes (+ hashing lib) | PASS | BLOCKED (aztec binding) | REPAIR-OK |
| WT-C07 | yes | PASS | BLOCKED (commitment) | REPAIR-OK |
| WT-C08 | yes | PASS | BLOCKED (`recipient_address cant be 0`) | REPAIR-OK |
| WT-C02 | yes | PASS | STILL PASSES (`max_fee=0` satisfies `amount >= max_fee`) | REPAIR-UNEXPECTED — warning-quality flag, §4 |

Consumer-side (recorded mutant proofs replayed against the pinned
consumer on Hardhat EDR; `repair-report.json` + `honest-controls/`):

| mutant | repair == pinned bytes | attack on pinned | honest on pinned | verdict |
|---|---|---|---|---|
| WT-S01 | yes | REVERT `_localRoot unknown` | succeeds (D1P-12R pinned honest mint; family evidence S03/S09 `mint_0`) | REPAIR-OK |
| WT-S03 | yes | `mint_0` success + `mint_1` REVERT `nullifier already exists` (both halves in one run) | same run | REPAIR-OK |
| WT-S09 | yes | `mint_0` success + `mint_1` REVERT `nullifier already exists` | same run | REPAIR-OK |
| WT-S06 | yes | REVERT `_relayerFee is larger than _maxFee` | succeeds (D1P-14A FC-POS within-cap mint) | REPAIR-OK |
| WT-S02 | yes | original plan: SUCCESS (artifact, §7); corrected plan (honest-seeded mock): REVERT `_gigaRoot unknown` | D1P-12R pinned honest mint | REPAIR-OK via corrected experiment |
| PY-C02 | repaired == pinned bytes by construction (diff is exactly line 74; pinned sha `c44a67e6…8604d`) | active block contained at `Mint value invalid` (TE05) | control mint registers, stays unspent (TE05) | REPAIR-OK (containment, not discrimination — expected, §6) |

Warning-remains: all WarpToad repairs are pinned bytes and D1P-34 §4
records zero warnings on pinned WarpToad — none remain. PY-C02 repaired
is pinned bytes, which carries the structural `commit_hash` R-CONSUMER
(cf. check-added precedent, D1P-34 §4) — author-labeled out of scope
(data availability), structurally accurate, and acceptable-remaining
after a valid repair, not a vulnerability claim.

## 4. Warning-quality flag: WT-C02 R-BIND `max_fee`

The v1.1 warning claims `max_fee` has no proof-enforced occurrence, but
the pinned circuit constrains it (`assert(!amount.lt(max_fee))`,
`main.nr:47`) and the pinned `nargo execute` ACCEPTS the attacker
witness `max_fee=0` exactly as the mutant does. Discrimination pair on
pinned bytes (`results/raw/REPAIR/c02-discrimination/`: `max_fee=0`
exit 0; `max_fee=2^64` exit 1, `Failed assertion at src/main.nr:47:5`):
the word IS bounded above by `amount`; the X-AV attacker merely
satisfies the bound. The analyzer undercounts this word's occurrence
(integer-comparison path) — evidence for AI1, no analyzer change made
here. The E3-contained demonstration stands (real proof, consumer
fee-cap containment), but the warning's "unbound" claim is not
confirmed — possible false warning at warning level. Follow-up for AI1:
reconcile occurrence counting for integer-comparison opcodes against
the pinned ACIR; do not tune on held-out cases.

## 5. Mock-verifier relabel rationale

Contract E2 requires a model satisfying the ACTUAL compiled producer
relation, decoder AND consumer model. `MockVerifier` (the project's own
`eth/test` pattern) decides proof acceptance by test configuration, not
by the pinned relation — the consumer-model leg is counterfactual. Rows
that keep only a mock demonstration are therefore E1+mock: genuine
consumer-logic demonstrations (same word, same effect, same location;
reports self-label the mock) contingent on assumed proof acceptance.
They earn detection credit at E1, not E2. The v1.1 `results.json` string
`E2 (mock-verifier-scoped)` is retained verbatim as generated evidence;
this ledger is the grading correction.

TE06 lifts three of the six mock rows to zero-mock E4 (PY-S01 W002/W004,
PY-S03 W002; PY-S02 pending, §10); PY-S04 W002 stays E1+mock
(infeasible by construction). Mock subtlety found during the lift: the
v1.1 S02 mock double-settlement rewrote `oldRoot` in the second block's
public inputs, which a mock verifier cannot bind — under a real verifier
that rewrite is unprovable, so the mock "effect" was doubly counterfactual
(proof acceptance AND input binding both assumed). Mock demonstrations
must freeze public inputs across submits; TE06 replays do.

## 6. TE04 attribution correction + TE05 (PY-C02's own E3)

- TE04 wrapped TC02 slot `007` (forged kind-3 burn at messages 4–8).
  TC02 proves the ORIGINAL `c4d2c90` circuit also accepts that candidate
  (control/tail both prove+verify on pinned). The pinned "contrast" in
  TE04 verified the mutant's proof under the original key, which fails
  for any proof. Defensible claim: the inherited Payy message-tail
  vulnerability reproduced end to end (real inner proof, real mutant-keyed
  final proof, real verifier, pinned consumer settles 100→93 / pays 7 to
  `0xdead`, `SumcheckFailed` under the pinned key for the tail block).
  End-to-end exploitation of PY-C02's own export-removal was NOT
  established by TE04.
- TE05 (`reports/TE05.md`): wraps slot `009` (attacker mint at messages
  0–3). Mutant `agg_final` proves + natively verifies (final VK
  byte-identical to TE04's, `0x4ca9f3ce…3a52ccbf`); same consumer and
  initial state as TE04 (control mint 100 registered). Both submits
  revert at `Mint value invalid` — the consumer's message gate
  (`verifyAllMessages`) runs BEFORE `verifier.verify`, so neither proof
  reached onchain verification and the pinned contrast is uninformative
  (recorded, not claimed). Original/repaired circuits admit no proof for
  the same witness (TC02 pinned ACVM rejection; repaired == pinned
  bytes). Grades: W001 E3 on its own mutation (real mutant-keyed proofs
  at both levels + original/repaired rejection + onchain containment);
  W002 E1 (zero state change on both keys).
- Ceiling note: on the pinned consumer an unregistered forged mint
  cannot settle with or without PY-C02, so containment (not E4) is the
  principled ceiling for PY-C02 alone. A combined circuit+consumer gap
  (e.g. PY-C02 × PY-S01 admission removal) is out of single-mutant scope.

## 7. WT-S02: setup artifact + corrected defect isolation

- Trusted history: `MockGigaProvider` is constructed with
  `plan.gigaRoot`; `initialize` writes
  `gigaRootHistory[mock.gigaRoot()] = true` (`WarpToadCore.sol:76-77`).
  The v1.1 plan seeded the mock with the fabricated `0x1234`, so the
  fabricated root was trusted at initialization on BOTH mutant and
  pinned consumers. Replaying the recorded plan against the pinned
  consumer SUCCEEDS (`gigaRootAdmitted:true`) — the v1.1 row as run is a
  setup artifact, not a defect effect. (Side observation, mechanism
  unresolved: pinned-circuit `nargo execute` also accepts `giga_root =
  0x1234` with honest membership data — the in-circuit
  `evm_merkle_verify` call discards its return value
  (`warptoad-nargo-hashing-lib.nr:79-86`); whether the membership check
  constrains anything needs ACIR-level follow-up, not a finding.)
- Corrected experiment (same proof, same initial state except the mock
  seed, matching pinned-circuit key on both sides;
  `results/raw/REPAIR/s02-corrected/`): mock seeded with the honest giga
  root, mint carries `0x1234`. Mutant consumer: SUCCESS with
  `gigaRootAdmitted:false` (K1 defect isolated). Pinned consumer: REVERT
  `_gigaRoot unknown`, zero state change. The K1 defect is real; only the
  v1.1 run's setup was wrong.

## 8. Scope notes applied

- Faucet: `getFreeShit` (`WarpToadCore.sol:199`) is a public dev faucet;
  policy covers the proof-consuming `mint` path only — all replays above
  use `mint`.
- PY-S03 substitute exclusion: the run registered no substitute
  (`payy-report-settle-burn.json` has only fund+settle steps), so payout
  of 1000 to the noteKind-derived address with 0 to the recipient went
  through the direct `executeBurn` path, not `substitutedBurns`. The
  legitimate mechanism (pre-registered `substituteBurn` by an authorized
  substitutor keyed on the exact burn) does not authorize this effect.
- WT-C08 scope: containment shown for the zero address
  (`ERC20InvalidReceiver`); an owner-chosen nonzero recipient may be
  permitted — no claim beyond the tested transaction.

## 10. PY-S02 double-settlement: circuit-level unreachability (TE06)

Two attempts to construct a chained height-2 re-settlement proof, both
failing before any proving — evidence in `results/raw/TE06/double-build-run.log`
(first, collision) and `double-rerun.log` (second, `:140`):

1. Re-processing the same mint utxo against the advanced tree panics at
   witness construction: smirk `CollisionError` — the note commitment is
   already present and the test tree refuses duplicate insertion.
2. With re-reference tolerated (`insert_allow_existing` in the
   attacker-client model), the batch-2 `agg_utxo` proof fails at ACVM:
   output commitments must land in empty slots
   (`validate_null … "Merkle path root does not match"`,
   `agg_utxo/src/main.nr:140`, called from `:167`).

The circuit enforces note uniqueness at output: the same mint words
cannot be re-exported by any party, attacker included, under the pinned
circuit. The consumer-side missing spent check therefore guards an
unreachable state — defense-in-depth removal, graded E3 (real proof +
onchain honest settlement + code-real defect). Reachable variant (NOT
tested, single-mutant scope): PY-C02's export removal would let messages
diverge from inner exports, so a PY-C02 × PY-S02 combined stack could
re-settle; that combination was not constructed. The v1.1 mock double
(which rewrote `oldRoot` per height) is triply counterfactual and is
retained only as consumer-logic illustration.

## 9. Evidence locations

- Generated (ignored, preserved): `results/raw/X-AV/v11/` (53 warnings,
  `results.json`, build dirs with proofs/plans), `results/raw/TC02/`,
  `results/raw/TE04/`, `results/raw/TE05/`, `results/raw/REPAIR/`
  (`repair-report.json`, `s02-corrected/`, `honest-controls/`, `logs/`).
- Tracked drivers: `scripts/xav_run.py`, `scripts/xav/repair_check.py`,
  `scripts/te05_part1.sh`, `scripts/te05_part2.py`,
  `scripts/xav/te05_replay.ts`, `src/bindcheck_d1/witness_synth_v1.py`.
- Reports (immutable): `reports/TC02.md`, `reports/TE04.md`,
  `reports/TE05.md`; policy: `docs/validation/policy-review-2026-10-30.md`.
