# D1-03 proof recovery 01

Date: 23 October 2026. **Bounded recovery attempt complete; proof recovery
UNKNOWN due to final-link allocation failure. D1-03 remains incomplete and
D1-04 WAITING.** Both build slots are consumed; no proof, native proof check,
or consumer replay ran.

## Objective and authorization

The user requested committing/pushing and trying different approaches, with
internet help where useful. Existing consumer-execution work was committed as
`cafe4dac50a24b36107ed9ef187abc2666156593` and pushed to `chatgpt-codex`;
the remote ref was checked. The new task addresses the missing proof-bundle
prerequisite by rebuilding an honest proof from pinned source, rather than
assuming that the unavailable historical bytes exist.

The [protocol](../protocols/d1/d1-03-proof-recovery-01.json) was frozen at
23:20:48 UTC before setup or execution. Completion requires pinned tooling and
isolated source, one attempted honest proof chain, independent verification and
unchanged-consumer replay if a proof is generated, or a precise evidenced
blocker. It also requires preservation, reporting and checkpoint updates.

Limits: 7,200 seconds total; two builds of at most 1,200 seconds each; one
honest chain of at most 1,800 seconds and four prove calls; two independent
native verification controls of 300 seconds; two Forge invocations of 600
seconds. Setup has twelve 600-second slots; other checks twelve 120-second
slots. Each child inherits a 4 GiB address-space limit; Cargo has two jobs.
Timeouts and failures remain failures. No primary solver query, held-out
evaluation, live transaction, or third-party system test is authorized here.

This is a new, prospective recovery budget. The earlier v2 zero-new-proof
budget, numeric S1/S2 seeds, policy, assumptions and 28 primary slots are
unchanged. A recovered historical mint control is not automatically an S1/S2
realization or an admitted v2 state.

## Reproduction and implementation

The [runner](../scripts/d1_proof_recovery_run.py) writes each command, selected
environment, runner hash, stdout/stderr, duration, exit status, timeout and
child maximum RSS under a new numbered directory. Counts and total elapsed
time are checked against the frozen protocol. Earlier runner versions are
preserved; later versions also copy themselves beside each command. The
runner's task-specific deadline is historical, not permission for unlimited
reruns.

The [source setup](../scripts/d1_proof_recovery_setup.py) extracts Git revision
`dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36` into
`build/D1-03/proof-recovery-01/payy-B`. It copies the existing T13 integration
harness byte-for-byte. No file in `tools/cases` is edited. The original source
manifest includes Cargo.lock, circuit programs and keys. Before proving, the
[proof launcher](../scripts/d1_proof_recovery_prove.py) checks every original
file against that manifest and records the built harness hash.

Rust is pinned to 1.91.0. The Linux bb archive is the upstream manual
`3.0.0-manual.20251030` release, SHA256
`88586691621fdbf6105e064aca1b6e4f1f5345f2e75560d1d385693019480697`.
Its URL and hash come from the
[pinned upstream setup source](https://github.com/polybase/payy/blob/dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36/pkg/xtask/src/setup/bb.rs),
also retained as a Git blob in the raw evidence. The binary's unusual version
string is not used as a substitute for its archive/executable hashes.

The first build found a missing host `libclang` required by `zstd-sys` bindgen.
The [local compiler-library setup](../scripts/d1_proof_recovery_clang.py)
checks fixed Ubuntu package SHA256 values, then extracts libclang 18, its
headers and LLVM 18 into the ignored build directory. No system package is
installed, no circuit/verifier source is patched, and no dependency version
is updated. The second build supplies the local library and header paths.

The [bb recorder](../scripts/d1_bb_recorder.py) executes the real pinned binary
and returns its status/output. It preserves ephemeral witness, program, key,
proof and public-input bytes. Its only added bb option is an explicit local
CRS directory. It refuses a fifth prove call. The historical harness builds
mint UTXO, agg_utxo, agg_agg and agg_final proofs and natively verifies each.

The [replay preparation](../scripts/d1_proof_recovery_replay.py), used only if
a final proof exists, changes only file paths in the historical five-test T13
consumer harness. It copies the pinned unchanged consumer, interface and
committed library-linked verifier binaries. The test uses the normal proxy
initializer, local token registration and owned validator signature; it
contains no mocked verifier, storage overwrite or signature bypass. Native
original/tampered-input checks precede Forge execution.

## Alternative approaches and evidence boundaries

The old committed upstream proof fixture is already documented as incompatible
in T09; this task does not repeat that failed route or relabel the fixture.
Rebuilding the matching modern chain is the new recovery approach.

Internet research also considered alternative solver theories. The abstract of
[Satisfiability Modulo Finite Fields](https://eprint.iacr.org/2023/091) reports
native-field performance advantages over integer/bit-vector encodings on its
benchmarks. That is not a result about BindCheck. The abstract of
[Bounded Verification for Finite-Field-Blasting](https://eprint.iacr.org/2023/778)
describes bounded validation of compiler encoding rules; it does not validate
our frontend. A future fallback needs a checked exact translation, identical
constraints and controls, and a separately frozen comparison. No alternative
solver query or new research direction was executed in this recovery task.

Full symbolic producer/consumer composition, concrete primary candidates,
repaired NONVAC/no-violation gates and the D1 baseline comparison remain
separate work. Successful honest execution alone establishes none of those.

## Observed outcomes and failed approaches

Raw evidence: `results/raw/D1-03/proof-recovery-01/`. Each numbered invocation
has `command.json`, `result.json`, `stdout.log` and `stderr.log`; the command
records contain exact argv and selected environment. The
[tracked manifest](../metadata/d1/d1-03-proof-recovery-01.json) seals raw files
and deliverables. Downloads, compiler libraries, source archives and the Cargo
cache remain ignored and are identified by hashes/pins rather than committed.

| Invocation | Observed outcome |
| --- | --- |
| setup-01 | Rust 1.91.0 minimal toolchain installation, exit 0 |
| setup-02/03 | Linux bb download/checksum and isolated source extraction, exit 0 |
| build-01 | Exit 101 after 296.719 s; `zstd-sys` bindgen cannot locate `libclang`. Failure preserved. |
| setup-04/05/06 | Download and locally extract three checksum-pinned compiler-library packages; all exit 0 |
| build-02 | Exit 101 after 1,086.043 s; dependencies compile, then `rust-lld` fails opening the final `t13_mint` output with `Cannot allocate memory`. No timeout. |
| check-01/02/03 | bb help, initial Python syntax inspection, and tool-version collection; exit 0 |
| check-04 | **119 Python tests pass**, exit 0 |
| check-05 | Local GNU BFD version/options inspected; both proposed low-memory flags are available. No alternative link executed. |
| check-06 | Preservation audit passes: 11 prior sealed deliverables (living versions archived exactly), 836 prior raw files, 79 starting deliverables and 2,667 original upstream files match. Frozen protocol matches. |
| check-07 | Final syntax inspection of all seven recovery scripts and `git diff --check` pass. Prepared proof/replay helpers remain unexecuted. |

Both builds used the same locked command:

```text
cargo +1.91.0 test --locked
  --manifest-path "build/D1-03/proof-recovery-01/payy-B/Cargo.toml"
  -p zk-circuits --test t13_mint --no-run
```

The multiline display is an argv specification; exact executable invocations
are preserved in `build-01/command.json` and `build-02/command.json`. The second
attempt added `LIBCLANG_PATH`, local `LD_LIBRARY_PATH` and the local Clang
resource directory. Neither command changed the source/lockfile. The first
failure is an environment prerequisite; the second is a linker allocation
failure under the frozen address-space ceiling. It is not evidence that a
proof is invalid, that a repaired circuit is safe, or that the research
hypothesis is false. Recorded maximum child RSS is not total process-group
memory and must not be conflated with the address-space limit.
Build 1 records 536,220 KiB maximum child RSS; build 2 records 1,699,104 KiB.

The proof launcher, bb recorder and real-consumer replay preparer are
**prepared, not validated by execution**: build failure prevented their use.
The configured runtime threading/stack settings were recorded prospectively;
they did not run. Zero new proofs, primary queries, candidate replays or
held-out evaluations occurred. All 28 v2 primary slots remain unused.

## Review checkpoint and recommendation

The final-link failure consumes the second and last build slot. Stop here for
the resource review required by the user's original roadmap instructions;
unused proof slots do not authorize extra builds. The two-hour overall ceiling
was not exhausted. There is no automatic scope or theory pivot.

The [concrete successor proposal](../docs/d1/proof-recovery-02-proposal.md)
uses the compiled cache for **one 600-second warm build with GNU BFD,
`--no-keep-memory` and `--strip-debug`, retaining 4 GiB and two jobs**. GNU's
[linker documentation](https://sourceware.org/binutils/docs/ld/Options.html)
supports the memory-saving rationale; success on this harness is untested.
If successful, one honest proof chain, original/tampered native checks and the
five unchanged-consumer controls must pass within a new one-hour envelope.
Otherwise preserve UNKNOWN and the failing stage. This is preferable to
changing the research theory because no proof or D1 method was tested here.

Changed files are the frozen recovery protocol, seven orchestration/setup/audit
scripts linked above, this report and its manifest, the successor proposal,
README, roadmap and living checkpoint. The analyzer implementation, previous
reports, research contract, v2 evaluation protocol and holdout are unchanged.

After recovery, symbolic composition and the v2 seed-realization question
remain. A real historical mint proof cannot silently replace the frozen S1/S2
seeds or supply repaired verification. D1-04 cannot begin on setup success.
