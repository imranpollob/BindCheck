# D1P-C02R — baseline availability retry

**27 October 2026 UTC. Outcome: 0 AVAILABLE, 9 UNAVAILABLE, 0
UNSUPPORTED.** The retry recovered and installed the two exact pinned Noir
binaries, recorded their hashes and runtime flags, and resolved Picus's R1CS
CLI path. Neither Noir installation passed the required bundled check because
Nargo panicked before loading the upstream test when it could not lock its
hard-coded `$HOME/nargo/.package-cache` outside the writable worktree. The
other seven pinned candidates remain unavailable because their artifacts were
not present locally and the supported network escalation was rejected before
execution. No target was run.

This is a host/session availability result, not a tool-quality comparison and
not a security verdict. Missing installation, a blocked self-test, or an
unsupported native frontend is never evidence that a target is safe or that a
baseline missed a defect.

## Scope and preservation

The read-only preregistration was snapshotted at SHA-256
`be04ffc28fa63aef5e31946a1c83d9ae3434f12e392da44e39c2332ad3aa0b00`.
The prospective [plan](../../results/raw/D1P-C02R/plan.json) caps each of the
nine candidates at 1,200 wall seconds; unlike D1P-C02, beta.14 and beta.22
have separate budgets. Only version/help and upstream-bundled examples or
self-tests were permitted. Payy, WarpToad, and all other targets were
untouched.

The earlier `results/raw/D1P-C02/` tree and
[availability.md](availability.md) were not modified. Before retry work, the
old report hash was
`c3e131b531132dfb617cd3059aa7cf88e87c0ba7db58373599eaa7276dfa8c31`
and its raw tree contained 113,838 files. Final preservation checks are in the
retry raw namespace.

Classification follows the frozen retry gate:

- **AVAILABLE:** exact pinned usable installation, passing own bundled check,
  and native intended-component input support established.
- **UNAVAILABLE:** an exact usable installation cannot be completed on this
  bounded host. A copied binary whose project command fails before its bundled
  check is not promoted to AVAILABLE.
- **UNSUPPORTED:** installation succeeds but the project's native target
  component cannot be accepted. This class is secondary to installation; a
  tool that never installs remains UNAVAILABLE even if documentation already
  shows the native target format is unsupported.

## Candidate results

The structured record is
[availability.json](../../results/raw/D1P-C02R/availability.json).

| Candidate pin | Class | Installation, version, hash, and bundled check | Native input support |
| --- | --- | --- | --- |
| **Slither 0.11.6**, `050cc0a…` | **UNAVAILABLE** | Python 3.13 venv created. Approved package download was rejected before execution; offline install found no local distribution. No candidate binary/hash or bundled check. | Solidity/Vyper via crytic-compile; consumer-side only, not Noir/ACIR. |
| **Mythril 0.24.8**, `9e9ee39a…` | **UNAVAILABLE** | Python 3.9 venv created. Approved package download was rejected before execution; offline install found no local distribution. No candidate binary/hash or bundled check. | EVM bytecode/Solidity; consumer-side only, not Noir/ACIR. |
| **Echidna 2.3.3**, `4454f3a3…` | **UNAVAILABLE** | No pinned local artifact. Installed 2.2.7 was not substituted (noncandidate SHA-256 `658a90f2…`). No bundled check. | Solidity through crytic-compile; property/assertion/foundry modes. No producer input. |
| **Foundry 1.8.6**, `6bad0a66…` | **UNAVAILABLE** | No pinned local artifact. Installed Forge 1.4.1 was not substituted (noncandidate SHA-256 `e8eb3031…`). No bundled check. | Solidity tests/invariants; no native producer or joint proof-to-execution input. |
| **CCC-Check**, HEAD prefix `7ed87b8c…` | **UNAVAILABLE** | Exact user-specified GitHub request rejected; local matches were project prose only. Full immutable revision, binary/hash, and bundled check remain unavailable. | Preregistration reports analysis over CirC IR. Native Noir, ACIR, or a compatible serialization of another IR this project actually produces was **not established**. No adapter was assumed. |
| **SmartAxe**, `7ca21f72…` | **UNAVAILABLE** | Repository snapshot identifies official Figshare share `985aae83fe5bc1291758`; its approved retrieval was rejected. No binary/hash or bundled check. | EVM bytecode plus cross-chain deposit/withdraw pairing; no Noir/ACIR. Single-chain acceptance remains unresolved. |
| **Picus**, `138b151d…` | **UNAVAILABLE** | No pinned local artifact; no install or bundled Decoder run. | Circom source, iden3 binary R1CS, and gnark `.sr1cs`. Exact R1CS route: `./run-picus <source.r1cs>`. Native Noir/ACIR is absent, so the project targets are unsupported **as compiled**; an ACIR→R1CS adapter would be a separately charged adaptation. |
| **Noir 1.0.0-beta.14**, `60ccd48e…` | **UNAVAILABLE** | Exact binary installed and version matched; SHA-256 `a0528f1c7a070f51addcefc707f889f2f9cbd85b17261e43f4b8dcf3d1d81eb8`. Upstream `assert_message` test and format check both exited 101 before execution on the cache lock. A focused upstream Rust self-test was also blocked offline by missing `clap-markdown@450d7595…`. | Native Noir→ACIR. Runtime help confirms both skip-check flags and the opt-in Brillig lookback flag for `check` and `compile`. |
| **Noir 1.0.0-beta.22**, `c57152f9…` | **UNAVAILABLE** | Exact binary installed and version matched; SHA-256 `37f7d55d9795af0da3b471db2306e0296fa34c528386a828ce556fc3ebbf6e7b`. Upstream `assert_message` test and format check both exited 101 before execution on the same cache lock. | Native Noir→ACIR. Runtime help confirms both skip-check flags for `check` and `compile`; beta.14's lookback flag is absent. |

## CCC-Check and Picus input findings

CCC-Check remains unresolved at the parser/frontend level. The only available
source claim says its analysis operates on CirC IR. That does not demonstrate
a Noir frontend, an ACIR loader, or a compatible serialization emitted by
BindCheck. Because the artifact did not install, the primary class is
UNAVAILABLE rather than UNSUPPORTED.

Picus's saved README (SHA-256
`e7e4dc3c027daf03a9483c5a1b1bf16549d61b8043010895886735cda50b7991`)
resolves the earlier ambiguity. Its positional `<source>` accepts `.circom`,
`.r1cs`, or `.sr1cs`; the `.r1cs` route is the iden3 `r1csfile` binary format:

```text
./run-picus <source.r1cs>
```

The bundled kick-the-tires command instead uses
`./benchmarks/circomlib-cff5ab6/Decoder@multiplexer.circom`. Neither path is
ACIR. No target conversion or adapter was created or run.

## Network and failed approaches

The exact requests and common runtime rejection are preserved in
[network-denial.json](../../results/raw/D1P-C02R/network-denial.json). Requests
covered the user-specified CCC-Check GitHub URL, exact Slither and Mythril
package downloads, and SmartAxe's official Figshare share. Every request used
the supported `require_escalated` mechanism and was rejected before execution
because this session exposes no sandbox/rules approval. After that denial, no
mirror, proxy, browser download, alternate origin, or unapproved direct
network command was used.

For Noir, changing `TMPDIR` and `XDG_CACHE_HOME` did not redirect the cache:
both pinned sources hard-code the dependency lock to `$HOME/nargo`. The task
did not repurpose `HOME`, modify either external evidence store, patch Nargo,
or substitute an authored test. The beta.14 Cargo self-test attempt stayed
offline and failed during workspace dependency resolution; it did not run a
test.

## Evidence and limits

The [bounded runner](../../results/raw/D1P-C02R/run_step.py) records argv,
cwd, environment overrides, UTC times, timeouts, exits, and stdout/stderr
hashes. The decisive retry evidence is:

- Slither/Mythril: `*/create-venv.json`, `*/install-pinned-offline.json`.
- Echidna/Foundry/CCC-Check/SmartAxe/Picus: `*/local-pin-search.json` plus
  the network-denial record.
- Noir: `*/version*.json`, `*/check-help.json`, `*/compile-help.json`, and
  `*/bundled-*` records.
- Source snapshots: `results/raw/D1P-C02R/sources/`.

No baseline target analysis, solver comparison, finding, proof, replay, or
security conclusion follows. A future retry can close the gate only with
approved access (or independently supplied exact artifacts), an isolated
writable Nargo home mechanism that does not alter the pinned binaries, and one
passing upstream bundled check per candidate.
