# F2 — Oracle soundness fixes, then S4d obligations
Status: DONE
Verdict/outcome: the five oracle soundness findings in scope (XR-01, 02, 07, 08,
09) are fixed, each with a test that would have caught it; two owned-local
negative controls behave as specified; the retained real-case E4 results survive
the stricter gates; and the AZ1 extent-binding testbed is confirmed from the
oracle alone (undischarged deposit obligation on the faulty consumer via
`FREE_ARG` on the row count; `NOT_CONFIRMED` on the fixed consumer).

AI disclosure: implemented by the F2 AI coder on Claude Opus (claude-opus-4-8 in
Claude Code). All code and results were executed and inspected by the author; the
reported verdicts come from real runs, not from model assertion.

## Part A — soundness fixes

All changes are in `oracle/` and `tests/oracle/` (F2-owned). The entitlement-only
policy contract, the operators, and the no-fork posture are unchanged.

### XR-01 — a protected effect must be state-corroborated
A `Transfer` log is no longer sufficient. For every mint-shaped protected effect,
the driver reads the recipient's token state at the mutated tx's block and the
block before (`balanceOf` for ERC-20, `ownerOf` for ERC-721, historical calls on
the owned local chain). The recipient balance must rise by exactly the logged
value, or the recipient must own the logged token id. An effect with no matching
state makes the trial `UNKNOWN` (`EFFECT_NOT_STATE_CORROBORATED`), never E4.
(`oracle/evm_runner.cjs`: `corroborateEffect`, verdict gate.)

### XR-02 — the verifier must accept on the mutated path
E4 now requires evidence, from the **call trace of the mutated transaction**
(`debug_traceTransaction` `callTracer`), that one of the unchanged verifier
contracts was invoked and returned boolean true. The standalone check of the
original proof (`verifierAccepts`) is kept only as an E3 preflight
(`verifier_accepted_preflight`). If the verifier is not shown to accept on the
mutated path, the trial is `UNKNOWN` (`VERIFIER_PATH_NOT_ESTABLISHED`).
(`oracle/evm_runner.cjs`: `callTrace`, `flattenCalls`, `verifierOnMutatedPath`.)

### XR-07 — obligation quantity and multiplicity
Obligation matching now compares `value` (and `token_id`) and is scored as an
occurrence-preserving multiset: the mutated tx must discharge the obligation to
the honest occurrence count. A +1 fee no longer discharges a required +50 fee,
and one event cannot satisfy two same-shaped obligations.
(`oracle/evm_runner.cjs`: `matchesObligation`, `obligationCount`, honest-count
conditioning.)

### XR-08 — preparatory commands cannot fork or dial a public chain
Chosen approach: a **command-token denylist enforced for every manifest command**
(`prepare`/`proof`/`transform`/`build` and the driver), plus a narrowed safety
claim. `runner.py` rejects any command whose argv or manifest-set env contains
`--fork-url`, `--broadcast`, `--unlocked`, or a URL whose host is not loopback,
before the command is launched. This blocks the concrete fork/public-RPC/
broadcast vectors while still allowing local Anvil (127.0.0.1) and package
installs that take no URL argument. It is a denylist, not a full network sandbox;
the claim is stated at that boundary. (`oracle/runner.py`:
`_assert_local_only_command`, called from `_command`.)

### XR-09 — oracle tests + two negative controls
`tests/oracle/test_oracle_gates.py` (19 Python unit tests) covers the XR-08
command gate, the verdict-free-policy and fork gates, and the pure verdict
helpers (XR-02 verifier-path detection, XR-07 quantity/multiplicity). Two
owned-local integration controls:

- **XR-01 control** `neg_fakeeffect` — a consumer emits a `Transfer` with no
  balance change. Result: `UNKNOWN (EFFECT_NOT_STATE_CORROBORATED)`.
- **XR-02 control** `neg_skipverify` — a mutated branch mints without calling the
  verifier. Result: `UNKNOWN (VERIFIER_PATH_NOT_ESTABLISHED)`.
- **XR-07 control** `neg_underpay` — the fee is paid with a wrong (smaller)
  amount. Result: `E4-CONFIRMED` (observed 0 of the required value-50 fee), which
  a quantity-blind check would have marked `NOT_CONFIRMED`.

### Re-confirmation under the stricter gates

Every case was re-run with the stricter gates (`results/raw/F2/reconf*`). The
single confirming trial per case is unchanged from S4/S4c; all other trials are
`NOT_CONFIRMED`:

| Case / variant | Confirming trial (still E4) | Everything else |
|---|---|---|
| **ZKredential** original | `CALLER` → E4 (mint to attacker; verifier accepts on the mutated path; balance +1e18 corroborated) | NOT_CONFIRMED |
| ZKredential repaired | — | all NOT_CONFIRMED |
| **RacePass** original | `FREE_ARG(credHash)` → E4 (pass minted; `ownerOf` corroborated; both verifiers called+true) | NOT_CONFIRMED |
| RacePass repaired | — | all NOT_CONFIRMED |
| **Synthetic alias** | `ALIAS-0` → E4 | NOT_CONFIRMED |
| **Synthetic replay** | `REPLAY` → E4 | NOT_CONFIRMED |
| **Synthetic obligation** vulnerable | `FREE_ARG(skipFee)` → E4 | NOT_CONFIRMED (incl. REPLAY, DOMAIN) |
| Synthetic obligation bound | — | all NOT_CONFIRMED |
| **Synthetic bound** | — | all NOT_CONFIRMED |

No real-case E4 result changed sign because of the fixes: the verifier is
genuinely called and accepts on each confirmed mutated path, and each confirmed
effect is a real balance/ownership change. The one driver incident during
re-confirmation was environmental, not a logic change: installing the AZ1 proof
pipeline put an ethers 5.x at the repo root that shadowed the pinned 6.x; fixed
by loading ethers from an explicit pinned path (`ORACLE_ETHERS_PATH`).

## Part B — S4d obligations

### Real-case obligation review (item 1)
Reviewed `findings/{zkredential,racepass}/policy.md` and source. **Neither real
case has a source-implied required effect that can be asserted without
overclaiming:** ZKredential's own policy states the authorized amount "cannot be
inferred from this code" (no issuance obligation), and RacePass's credential
linkage is already an *entitlement* on the committed pass (handled by
`FREE_ARG(credHash)`), while one-pass-per-credential is explicitly `UNKNOWN`. No
obligation clause was added to either real policy. The AZ1 testbed is the
purpose-built real obligation case.

### View-based effect capability
AZ1's benefit (an L2 credit counter) and obligation (settled backing) are
state-accounting changes with **no `Transfer` event**. The oracle was extended so
a policy can declare `protected_view_effects` and `view_obligations` over named
`state_views` (before/after `view`-call deltas on owned local deployments). A
view obligation is faulted only when the honest path discharged it (backing delta
== credit delta) and the mutated tx granted the credit while moving less backing.
A view effect is state by construction, so it needs no XR-01 corroboration; XR-02
still applies. Proven first on a fast synthetic control (`view_oblig`): the
vulnerable variant confirms only `FREE_ARG(numRealRows)` with
`undischarged_view_obligation` (credit 200, backing 150, shortfall 50); the fixed
variant reverts ("unsettled row").

### AZ1 testbed from the oracle alone (item 2)

The AZ1 manifest (`tests/oracle/az1.manifest.json`, policy `az1.policy.json`,
sources staged under `tests/oracle/az1/`) runs the real pinned proof pipeline as
`proof` steps (circom 2.2.3 compile of `batch4.circom`, toy trusted setup, snarkjs
prove of the honest batch), compiles the real `Settlement{Faulty,Fixed}` +
`TestToken` + the snarkjs `Groth16Verifier` with solc 0.8.11, and deploys the two
Poseidon libraries from their generated creation bytecode (wrapped as standard
`{abi, bytecode}` artifacts by `scripts/make_artifacts.js`, so the generic driver
deploys them unchanged). The honest batch credits L2 by 150 and settles backing
150 (`credit == backing`, obligation discharged).

Result (`results/raw/F2/az1-20261118T205626Z`, status DONE):

| Variant | `CALLER` (any caller) | `FREE_ARG(numRealRows → 1)` |
|---|---|---|
| **faulty** | NOT_CONFIRMED (policy-permitted; credit 150 == backing 150) | **E4-CONFIRMED** — `undischarged_view_obligation`: credit +150, backing +100, **shortfall 50** |
| **fixed** | NOT_CONFIRMED | NOT_CONFIRMED (reverts `"unsettled row"`) |

The confirmation is from the oracle alone: a real Groth16 proof passes the
unchanged verifier on the mutated path, the credit counter rises, and the settled
backing falls short of it because `numRealRows` (not a public input) was lowered.
This is the Aztec-Connect-shaped extent-binding fault — credit granted over all
rows, backing settled over a caller-chosen prefix.

Manifest-writing effort: approximately **30 minutes** (deploy graph with a
raw-bytecode Poseidon pair wrapped as standard artifacts, the ported Groth16
proof pipeline as `proof` steps, and the row data transcribed from the fixture).

## Evidence

Tool versions: node v24.19.0; pinned ethers 6.13.4 (driver, explicit path);
anvil/forge 1.4.1; circom 2.2.3 (`bindcheck-zk/tools`); snarkjs 0.7.6 + circomlibjs
(repo `node_modules`); solc 0.8.11 (AZ1 contracts); Solc 0.8.20 (synthetic).
Raw evidence under ignored `results/raw/F2/`:
- XR controls: `neg_fakeeffect-*`, `neg_skipverify-fix-*`, `neg_underpay-*`
- view capability: `view_oblig-*`
- re-confirmation: `reconf-*`, `reconf2-*`
- AZ1: `az1-*` (with confirmed-trial replay bundle)

New/changed tracked files: `oracle/evm_runner.cjs`, `oracle/runner.py`,
`oracle/README.md`, `tests/oracle/test_oracle_gates.py`,
`tests/oracle/synthetic/src/Synthetic.sol`,
`tests/oracle/{neg_fakeeffect,neg_skipverify,neg_underpay,view_oblig,az1}.{manifest,policy}.json`,
`tests/oracle/az1/` (staged sources + `scripts/make_artifacts.js`),
`reports/F2/REPORT.md`, `docs/project-status.md`.

## Assumptions and limitations
- XR-08 is a denylist at the command layer, not a kernel/network sandbox; the
  safety claim is stated at that boundary.
- View obligations are scored as state-counter deltas; an obligation discharged
  only as an un-viewable storage write would need an explicit storage-slot match.
- AZ1 uses a toy trusted setup with fixed entropy (reproducible, insecure by
  design — fixture only). Real-case policy interpretations remain provisional
  (`findings/*/policy.md`); independent author confirmation is still MISSING.
- All S4/S4b/S4c limitations carry over.

## Held-out hygiene statement
No new third-party EVAL/held-out family was opened. The real cases are the two
DEV families already in `findings/` (F30, F39). The AZ1 testbed is an owned,
synthetic, local-only fixture. `bindcheck_zk/`, `findings/`, and `paper/` were not
edited.

## Recommended next task
**F2b — storage-slot and multi-obligation views.** Extend view obligations to
match an un-viewable storage write (via the prestate diff) and to score several
view obligations per batch, so obligations with no getter are covered.
Completion criterion: a synthetic control whose obligation is a storage write
with no view is `E4-CONFIRMED` when omitted and `NOT_CONFIRMED` when discharged.
