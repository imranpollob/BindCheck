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

A trial is `E4-CONFIRMED` iff **both**:

1. the mutated tx succeeds through the **unchanged** verifier and consumer; and
2. its committed effects violate the policy — an **unauthorized effect** (an
   effect reaches someone not entitled to it, an amount differs from one the
   proof fixes, or a single-use authorization is consumed twice, canonical key
   reduced mod r), **or** an **undischarged required obligation** (the mutated tx
   grants the protected benefit but omits an obligation the honest path commits,
   e.g. a fee transfer to the treasury or a nullifier-marking effect).

Otherwise `NOT_CONFIRMED` (`reverted` / `effects identical` / `policy-permitted`)
or `UNKNOWN` (build/proof/deploy failure, or verifier acceptance not
established). The policy file states **entitlement only**; it never states the
expected verdict, and `runner.py` refuses a policy that does.

**Required obligations (S4c).** A policy may declare `required_obligations:
[{id, description, match}]`, where `match` ({`type`, `from`, `contract_role`,
`to`}) names the committed effect each authorization must produce alongside its
benefit. The oracle conditions on the honest reference: an obligation is faulted
only when the honest path discharges it, this mutated tx grants the protected
effect, and the obligation effect is absent — so a declared obligation the real
path never produces is never flagged. Each trial carries an `obligations` ledger
(`discharged_by_honest` / `discharged_by_mutation`).

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
