# D1P-C02 — bounded baseline availability

**27 October 2026 UTC. Installation/self-test gate blocked in this session.**
Nine requested candidates (seven tools and two Noir versions) are
`UNAVAILABLE` under the current host/network conditions. None is certified
`AVAILABLE` or experimentally classified `UNSUPPORTED`. **No bundled
example/self-test completed, and no target analysis ran.** This is an
environment-specific availability report, not an algorithmic comparison or
a claim that these tools cannot be installed elsewhere.

Worktree: `/Users/imranpollob/Coding/bc/bindcheck-lane-c`; initial clean HEAD:
`785ff402793d0b2cf5f28de2735a97a338e1ad4d`. The requested
`bindcheck-lane-d/paper/baselines.md` was read only and snapshotted into
[raw provenance](../../results/raw/D1P-C02/baseline-preregistration.md),
SHA-256 `97575b3dcbcc0a0f3999d994096680dc87f7a990c9ee165e3de7a0bf571cbc9e`.
A concurrent D1P-D03 edit of that same permitted file was observed and
[preserved separately](../../results/raw/D1P-C02/baseline-preregistration-d03.md),
SHA-256 `be04ffc28fa63aef5e31946a1c83d9ae3434f12e392da44e39c2332ad3aa0b00`.
The [source-change record](../../results/raw/D1P-C02/baseline-source-change.json)
and diff preserve both observations; this task did not modify lane D.
No other lane artifact was used. The research contract governs evidence and
unsupported-input treatment; availability classes below are not security
verdicts.

## Scope, bounds, and network access

The [prospective plan](../../results/raw/D1P-C02/plan.json) records the pins,
scope, host, origin failure, and a **1,200-second wall limit per tool**. Both
Noir versions conservatively share one limit. The
[step runner](../../results/raw/D1P-C02/run_step.py) records exact commands,
working directories, environment overrides, UTC times, timeout/exit results,
and SHA-256 hashes of stdout/stderr. It caps each subprocess at the remaining
tool budget and kills its process group on timeout. No attempt exhausted the
bound. Preparation and the final reporting interval are accounted for
separately in the [timing record](../../results/raw/D1P-C02/timing.json).

Writes are confined to this document and `results/raw/D1P-C02/`. Python venvs,
isolated Cargo caches/targets, source snapshots, logs, and temporary directories
are under the raw namespace. Global binaries/caches were inspected read-only;
the compiler cache was copied before the offline build. No dependency source
was altered to make a failed pin compile, and no older release was substituted.
No Payy, WarpToad, or other application was submitted to any tool. No new
application was discovered or screened. No shared-status edit, commit, push,
or merge was made.

Initial `curl` to the requested CCC-Check GitHub origin failed with exit **6**
(DNS resolution). A supported `exec_command` escalation request was rejected
**before execution**: the runtime reported `sandbox_approval: false` and
`rules: false`. It also reported `request_permissions: true`, but no such
request tool was exposed in the available tool inventory. No mirror, browser,
proxy, alternate address, or connector was used to evade the rejection.

After the user stated that permissions were updated and reaffirmed installation
authorization, direct retries still returned exit **6** for GitHub and PyPI.
The escalation retry received the same runtime rejection. See
[permission-update.json](../../results/raw/D1P-C02/permission-update.json).
This is a runtime access failure despite user authorization. The original
20-minute limits and no-target-run restriction were retained.

## Classification rules

- **AVAILABLE:** requested pinned installation is usable, an own bundled
  example/self-test passes, and native input support for the intended
  component is evidenced. This alone would not validate target integration.
- **UNAVAILABLE:** the requested usable installation cannot be obtained in
  this bounded environment. An artifact/pin gate can prevent the installer
  from launching; that differs from an installer failure and is recorded.
- **UNSUPPORTED:** installation succeeds but the native input cannot accept
  the intended target component. No candidate reached that prerequisite here.

The supplied preregistration's native-language descriptions (including the
explicitly identified D1P-D03 update) are reported
separately from new pinned-source inspection and runtime confirmation.
Missing installations, unsupported inputs, missing examples, and access
failures are not misses or safety results. Research conclusions remain
`UNKNOWN`.

## Candidate outcomes

Full structured records are in
[availability.json](../../results/raw/D1P-C02/availability.json). Ellipses
below denote unresolved commit **prefixes from the supplied document**, not
full immutable revision identities verified by this task.

| Candidate pin | Outcome | Installation and bundled-test evidence | Native input support and remaining gaps |
| --- | --- | --- | --- |
| **Slither 0.11.6**, `050cc0a0…` | **UNAVAILABLE** | Isolated Python 3.13.7 venv created. Pinned pip install exited 1: no matching accessible distribution. PyPI probe exited 6. Local caches contain only 0.11.3/0.11.5. Bundled test **not run**. | Supplied preregistration reports Solidity/Vyper, hence consumer-side input only. Exact 0.11.6, solc compatibility, proxy behavior, and Hardhat 3 path were not checked. |
| **Mythril 0.24.8**, `9e9ee39a…` | **UNAVAILABLE** | Isolated Python 3.9.6 venv created. Pinned pip install exited 1: no matching accessible distribution; no matching cache. Bundled test **not run**. | Supplied preregistration reports EVM bytecode/Solidity. Pairing/precompile behavior, large inputs, and pinned native acceptance remain untested. |
| **Echidna 2.3.3**, `4454f3a3…` | **UNAVAILABLE** | Artifact gate blocked before installer launch. Installed 2.2.7 is the wrong pin; requested release not in inspected caches. Bundled test **not run**. | Supplied preregistration reports Solidity through crytic-compile and property/assertion/foundry modes. Exact pinned integration and Hardhat 3 support remain untested. |
| **Foundry 1.8.6**, `6bad0a66…` | **UNAVAILABLE** | Artifact gate blocked before installer launch. Installed Forge 1.4.1 is the wrong pin; requested release not in inspected caches. Bundled test **not run**. | Supplied preregistration reports Solidity tests/invariants. This does not provide native joint Noir/ACIR analysis. Requested-version behavior and any harness port remain untested. |
| **CCC-Check**, `7ed87b8c…` reported by concurrent D1P-D03 update | **UNAVAILABLE** | Initial preregistration had no commit/tag; updated document supplies a prefix. Origin blocked; full pin resolution and installation/test did not complete. | Updated preregistration reports **CirC IR** from the artifact README. Native Noir, ACIR, or another project-produced IR acceptance remains **unresolved**; a reported IR name is not a verified frontend or compatible serialization. |
| **SmartAxe**, `InPlusLab/FSE24-SmartAxe@7ca21f72…` | **UNAVAILABLE** | Repository/artifact not cached. Supplied document does not give the Figshare artifact ID or binary hash. Denied repository access prevents resolving that artifact; no installer/test launched. | Supplied preregistration reports EVM bytecode with bridge deposit/withdraw pairing. Single-chain fixture acceptance and any required deployment/event metadata remain unresolved. |
| **Picus**, `138b151d…` | **UNAVAILABLE** | No cached pinned tool or bundled `.r1cs` example. No installer/test launched. Full revision, exact invocation, and local example path not recovered. | Updated preregistration reports Circom ≥2.0.6 source, **binary R1CS in iden3 `r1csfile` format**, and gnark `.sr1cs`. Native ACIR ingestion is not established. The runtime CLI/local-example path remains **unresolved**, as detailed below. |
| **Noir 1.0.0-beta.14**, `60ccd48e18ad8ce50d5ecda9baf813b712145051` | **UNAVAILABLE** | Exact source recovered from local compiler Git cache. Isolated `cargo install --offline --locked` exited **101** on uncached `clap-markdown@450d759532c88f0dba70891ceecdbc9ff8f25d2b`. No binary produced; bundled example/test **not run**. | **Pinned source confirmed:** Noir packages compile to ACIR; both default-check disable flags and opt-in Brillig lookback exist. Runtime behavior is untested. |
| **Noir 1.0.0-beta.22**, `c57152f9…` | **UNAVAILABLE** | No installed nargo; requested source object absent from the compiler cache (`rev-parse` exited **128**). No source install or bundled test launched. | Noir source is documented by the supplied preregistration; version-specific flags/check behavior remain unverified. |

Pip's “no matching distribution” output is **not** evidence that either
requested release does not exist. No accessible index result was established.
Similarly, a cache miss means absent from the explicitly inspected cache
locations, not globally absent from the host or ecosystem.

### CCC-Check and Picus input gates

For [CCC-Check](https://github.com/ArmanKolozyan/CCC-Check), the repository URL
is user-supplied; its contents were not retrieved. The concurrent D1P-D03
update reports HEAD prefix `7ed87b8c…` and analysis over **CirC IR**, citing
the artifact README. Neither a full immutable candidate pin nor parser/loader
entry points were independently available here. Therefore all
three questions—native **Noir**, native **ACIR**, or another **IR we actually
produce**—remain unresolved. No converter or adapter was invented, implemented,
or assumed. This cannot be called `UNSUPPORTED` under the requested definition
because installation did not succeed.

For **Picus**, distinguish the reported input format from an executable path:

| Required item | Recorded state |
| --- | --- |
| Reported native route | **Binary R1CS in the iden3 `r1csfile` format**, distinct from Circom ≥2.0.6 source and gnark `.sr1cs`, per the D1P-D03 README summary |
| Actual local bundled `.r1cs` file path | **null — unavailable**, not a guessed filename |
| Exact CLI argument/flag accepting the R1CS path | **unresolved**; supplied `run-picus --solver cvc5` lacks an input argument and is not a complete runnable invocation |
| Native Noir/ACIR import | Not established; the supplied document reports no documented ACIR→R1CS route |
| Adapter or translated target | None; no adapter/translation was run |

The documented binary-R1CS route is now recorded at the preregistration
evidence level. Its concrete CLI/example-path check is **unfinished due to
artifact access**; the `.r1cs` extension alone is not a runtime confirmation. A future
authorized continuation must locate and run the pinned tool's own R1CS example
and record its exact path, bytes/hash, and invocation before making the input
support claim.

### Noir beta.14 source findings

[Native-input and flag evidence](../../results/raw/D1P-C02/noir/native-input-and-flags.json)
pins and hashes the inspected files. At the exact cached revision:

- `tooling/nargo_cli/src/cli/compile_cmd.rs` defines compilation of a Noir
  package to ACIR and flattens `CompileOptions`.
- `compiler/noirc_driver/src/lib.rs:152` defines
  `--skip-underconstrained-check`; line 158 introduces
  `--skip-brillig-constraints-check`. Both are opt-out Boolean flags, false
  unless supplied. Their source comments describe disabling production checks.
- The same file at line 172 defines
  `--enable-brillig-constraints-check-lookback` as an opt-in Boolean flag.
- `tooling/nargo_cli/src/cli/check_cmd.rs` accepts the flattened options but
  follows the parse/prepare/frontend-check and ABI-template path. Accepting a
  flag under `nargo check` is not evidence that lowering/ACIR constraint passes
  execute there. No runtime flag experiment occurred.

The source archive declares minimum/toolchain Rust 1.85.0. The isolated
offline attempt used the already installed Rust/Cargo **1.91.0**, recorded as
a host-build-toolchain deviation; it failed while resolving dependencies,
before producing a compiler. We did not fetch the denied `clap-markdown`
origin, remove the dependency, or change the lockfile. Nothing here confirms
the beta.22 flags or establishes a compiler-check result on a target.

## Hashes, commands, and evidence

[binary-hashes.json](../../results/raw/D1P-C02/binary-hashes.json) records
`null` with a reason for **each requested candidate binary**: no requested
binary was produced or found. Two existing, explicitly **noncandidate**
binaries were hashed and invoked only with `--version` to rule out pin matches:

| Existing binary (not used as the candidate) | Version observed | SHA-256 |
| --- | --- | --- |
| `~/.foundry/bin/forge` | `1.4.1-v1.4.1`, commit `cf7746048646f2ecff48246dd61e265e49ab16f0` | `e8eb303175e7213fb2861d2872632c07a606bf8b8630318aead56a678126ec98` |
| Homebrew `echidna` | `2.2.7` | `658a90f229efb7697c2adcbc93dcbf649bb22f4db1fb7dd610a422e09808e403` |

These hashes do **not** satisfy the requested 1.8.6/2.3.3 binary-hash gates.
The [installed inventory](../../results/raw/D1P-C02/installed-candidate-inventory.json)
preserves paths, sizes, exact commands, exits, and version text. The
[Python cache inventory](../../results/raw/D1P-C02/python-candidate-cache-inventory.json)
and [release-cache inventory](../../results/raw/D1P-C02/release-cache-inventory.json)
record the bounded read-only cache checks.

Decisive actual install commands, run in the corresponding isolated raw
directory (full argv, cwd, overrides, duration, and log hashes are in JSON):

```text
slither: ./venv/bin/python -m pip install --no-cache-dir --retries 0 --timeout 15 slither-analyzer==0.11.6
mythril: ./venv/bin/python -m pip install --no-cache-dir --retries 0 --timeout 15 mythril==0.24.8
noir beta.14: cargo install --offline --locked --path tooling/nargo_cli --root ../install-beta14 --jobs 2
```

Primary step records:
[Slither](../../results/raw/D1P-C02/slither/install-pinned.json),
[Mythril](../../results/raw/D1P-C02/mythril/install-pinned.json),
[Noir beta.14](../../results/raw/D1P-C02/noir/beta14-install-offline.json),
[Noir beta.22 cache check](../../results/raw/D1P-C02/noir/beta22-cache-pin-check.json).
The five remaining tools have `pinned-artifact-gate.json` and adjacent output
under their named raw subdirectories. The artifact-gate helper exits **78**
for a missing permitted pinned artifact; this is **our pre-install gate**, not
an upstream installer/test exit. None of these gate logs asserts a bundled
test was attempted.

## Unfinished work and next gate

The requested installations, candidate-binary hashes, bundled checks, CCC-Check
frontend determination, and Picus's exact R1CS invocation/path cannot be
completed under the observed access conditions. Source-only beta.14 findings
and preregistration descriptions are retained at their actual evidence levels.
No runtime support result or comparison is inferred.

Next task requires working supported origin approval/download access and
full immutable CCC-Check/SmartAxe artifact pins (CCC-Check's prefix is now
reported, but was not resolved here). Preserve this attempt's logs, use
a fresh raw continuation namespace with a newly authorized budget, and require
each candidate's exact version/hash plus one passing own bundled example or
self-test. Resolve frontend/input-path questions from that same pin. Targets
remain untouched until separately authorized.
