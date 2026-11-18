# BindCheck execution oracle (`oracle/`)

Local-only, manifest-driven **execution oracle** (test harness) that confirms a
binding finding by running a faulty/fixed consumer with a **real accepted proof**
on an **owned local chain** and observing committed protected effects. It is the
E4 step of the research-contract evidence ladder (§8), automated.

See the authorization and scope header in
[`docs/orchestration/S4-execution-oracle.md`](../docs/orchestration/S4-execution-oracle.md).
Summary of the hard limits this code enforces:

- **Local only.** Deployments run on an in-process **Anvil** node the runner
  starts and stops itself, on synthetic accounts with test tokens of no value.
- **No fork.** `--fork-url` is parsed but always rejected: it needs written
  author authorization (H1), none is recorded. `_validate_manifest` also refuses
  any manifest that does not assert `safety.local_only=true` and
  `safety.fork_enabled=false`.
- **No forged proofs.** The oracle never forges a proof or a verifier key. It
  re-runs an *already valid* snarkjs proof against the **unchanged** verifier and
  consumer, and only varies the surrounding call (the mutation operators).
- **No public RPC, no broadcast.** There is no network-fetch or public-RPC path.
  Source must already exist locally at its pinned revision.

## Why Anvil + a standalone ethers driver (not Hardhat tests)

The confirmation must come from **the oracle alone**, with *no test file written
for the case* (S4 steps 2–3). So the driver (`evm_runner.cjs`) is fully generic:
it reads compiled artifacts (both Hardhat `artifacts/**/<Name>.json` and Foundry
`out/**/<Name>.json` shapes), deploys and calls contracts by ABI from a
declarative **scenario** in the manifest, and applies the mutation operators
mechanically. No per-case JavaScript is loaded. Anvil is used because its
`debug_traceTransaction` prestate/diff tracer gives clean committed-state diffs
and its deterministic dev accounts make synthetic signers reproducible.

## CLI

```bash
python3 -m oracle run <manifest.json> --out results/raw/S4/<run-id>
```

`runner.py`: validates the manifest, stages pinned source (`git archive` of a
local repo, or a local copy inside this worktree), runs the declared `prepare` /
`proof` / `build` commands, starts a private Anvil per variant, hands the
scenario + resolved paths to `evm_runner.cjs`, and writes a self-contained
`result.json` (plus a replay bundle per `E4-CONFIRMED` trial). Any build, proof
or deploy failure is recorded as `UNKNOWN` — never as safe.

## Manifest schema (v1)

Top level: `schema_version:1`, `case_id`, `safety{local_only,fork_enabled}`,
`source{kind:git_archive|local_copy,...}`, `policy` (path to a separate policy
file), command lists `prepare`/`proof`, and one or more `variants`. Each variant
has `build` commands, an `artifacts` dir list, a `proofs` map (name → proof.json
/ public.json produced by the `proof` steps), and a `scenario`.

`scenario` is declarative and case-independent:

| key | meaning |
|---|---|
| `signers` | ordered names bound to Anvil dev accounts 0,1,2,… |
| `deploy` | `[{name, artifact, args, from?}]` — deploy by ABI, in order |
| `post_deploy` | `[{target, function, args, from}]` — e.g. `transferOwnership` |
| `honest_tx` | `{target, function, from, value?, args:[{name,value,class}]}` |
| `operators` | subset of `CALLER FREE_ARG ALIAS REPLAY DOMAIN` |
| `free_args` | `{argName:{mutation:<expr>}}` — which args `FREE_ARG` varies |
| `alias` | `{arg, proof, positions}` — which pub positions `ALIAS` offsets by r |
| `caller_candidates` | senders `CALLER` substitutes |
| `domain` | deploy entries `DOMAIN` re-instantiates |

**Value expressions** (one `$`-key object, or a bare literal):
`$lit $signer $addr $proofPart $pubArray $pub $pubAsAddress $keccakUtf8 $bytes
$uint $nowPlus $nowMinus $tuple $emptyArray`. The driver resolves them against
signers, prior deployments and the loaded proofs.

## Confirmation rule (research-contract §8, E4)

A trial is `E4-CONFIRMED` iff **all** of:

1. the mutated tx **succeeds**;
2. the **unchanged verifier is shown to accept on the mutated call path** — its
   contract is invoked and returns true in the mutated tx's `callTracer` trace
   (XR-02). The standalone check of the original proof is only an E3 preflight;
3. every protected transfer effect used to confirm is **state-corroborated** —
   the recipient's `balanceOf`/`ownerOf` actually changed by the logged amount at
   the mutated tx's block (XR-01); and
4. its committed effects violate the policy — an **unauthorized effect** (an
   effect reaches someone not entitled to it, an amount differs from one the
   proof fixes, or a single-use authorization is consumed twice, canonical key
   reduced mod r), an **undischarged required obligation** (the mutated tx grants
   the protected benefit but omits — or under-pays, by value/occurrence — an
   obligation the honest path commits), or an **undischarged view obligation** (a
   state-accounting counter the honest path keeps balanced, e.g. settled backing
   == granted credit, falls short).

Otherwise `NOT_CONFIRMED` (`reverted` / `effects identical` / `policy-permitted`)
or `UNKNOWN` — build/proof/deploy failure, `EFFECT_NOT_STATE_CORROBORATED`
(an event with no matching state), or `VERIFIER_PATH_NOT_ESTABLISHED` (the
verifier was not shown to accept on the mutated path). The policy file states
**entitlement only**; it never states the expected verdict, and `runner.py`
refuses a policy that does, and rejects any manifest command that references a
fork URL, a non-local RPC, or a broadcast flag (XR-08).

**Required obligations (S4c).** A policy may declare `required_obligations:
[{id, description, match}]`, where `match` ({`type`, `from`, `contract_role`,
`to`}) names the committed effect each authorization must produce alongside its
benefit. The oracle conditions on the honest reference: an obligation is faulted
only when the honest path discharges it, this mutated tx grants the protected
effect, and the obligation effect is absent — so a declared obligation the real
path never produces is never flagged. Each trial carries an `obligations` ledger
(`required_occurrences` / `observed_occurrences`). Obligation matches compare
`value` and `token_id` and are scored as an occurrence-preserving multiset, so a
+1 fee does not discharge a required +50 and one event cannot satisfy two
same-shaped obligations (XR-07).

**View-based effects and obligations (S4d).** For state-accounting effects with
no event, a scenario declares `state_views: [{name, contract, function, args?}]`
(read as uints before/after the mutated tx), and a policy declares
`protected_view_effects: [{id, view, min_delta}]` and `view_obligations:
[{id, view, must_equal_credit_of}]`. A view obligation is faulted when the honest
path keeps the obligation view's delta equal to the credited view's delta and the
mutated tx grants the credit while moving less backing. This is how the AZ1
extent-binding testbed (settled backing must equal granted L2 credit) is
confirmed. A view effect is state by construction, so it needs no XR-01
corroboration.

## Mutation operators

| Operator | What varies | Confirms when |
|---|---|---|
| `CALLER` | same calldata, different sender | effect binds to sender but policy binds it to a proof field |
| `FREE_ARG` | a consumer arg not fed to the verifier | effect binds to that arg but policy binds it to a proof field |
| `ALIAS` | a read public input offset by the field modulus r | a non-canonical verifier accepts and a raw-keyed guard is bypassed |
| `REPLAY` | the honest tx submitted again after it succeeds | a single-use guard is missing |
| `DOMAIN` | the same proof against a second consumer instance | the proof is not domain-separated and the effect is unauthorized there |

`ALIAS`/`REPLAY`/`DOMAIN` run the honest tx first (prelude) so single-use is
tested against an already-consumed authorization.

## Layout

```
oracle/
  runner.py         orchestration, safety gates, Anvil lifecycle
  evm_runner.cjs    generic ethers v6 driver: deploy / mutate / observe / judge
  cases/<case>/     manifest.json + policy.json for the two real findings
tests/oracle/       synthetic controls (Foundry): bound / alias / replay / obligation
```
