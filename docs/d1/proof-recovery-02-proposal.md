# Proposed recovery 02: one memory-conserving link attempt

23 October 2026. **Proposal for review, not an executed experiment or a frozen
authorization.** Recovery 01 used both build attempts. Its corrected build
compiled the dependencies and failed at final linking with `Cannot allocate
memory`; it did not time out and did not run a proof. See the
[report](../../reports/D1-03-proof-recovery-01.md).

## Recommendation

Retain the same source, lockfile, compiler, bb, circuit keys, harness, 4 GiB
address-space cap and two jobs. Reuse the ignored compiled dependency cache.
Try GNU BFD for the final harness link, with `--no-keep-memory` and
`--strip-debug`. GNU documents the former as reducing symbol-table caching;
the latter discards debugging symbols. Both options exist in this host's
GNU Binutils 2.42. This is a plausible engineering workaround, not an observed
success. See the [GNU linker manual](https://sourceware.org/binutils/docs/ld/Options.html).

Do not increase the memory ceiling, alter the circuit/consumer, remove a
constraint, update a dependency, or turn this into another T22 solver campaign.
An infrastructure failure has not tested the D1 research hypothesis. Switching
to another research direction is premature on this evidence.

## Proposed completion criterion and limits

- One warm build, at most 600 seconds, using a fresh log directory.
- If the build succeeds: one unchanged honest four-stage proof chain, at most
  1,800 seconds and at most four prove calls; preserve every input,
  output and native verify call. No proof retries.
- If a final proof exists: original and tampered-input native controls, at most
  300 seconds each, then one 600-second run of the five unchanged-consumer
  harness tests. Original must verify; tampered input must be rejected; honest
  settlement must commit the expected registry/root/height effects and all
  rejection controls must preserve state.
- Total 3,600 seconds, no downloads, no new solver queries, no held-out data.
  A failure remains UNKNOWN with its exact failing stage. No second build.

Before execution, freeze a new protocol and record cache/input hashes. Copy
the local library-path environment from recovery 01's `build-02/command.json`.
Keep `CARGO_TARGET_DIR`, `CARGO_BUILD_JOBS=2`,
`RUSTFLAGS="--cfg tracing_unstable"` and `TS_RS_EXPORT_DIR` identical. Supply
the following additional flags only to the selected test target, so dependency
artifacts need not be rebuilt:

```text
cargo +1.91.0 rustc --offline --locked
  --manifest-path "build/D1-03/proof-recovery-01/payy-B/Cargo.toml"
  -p zk-circuits --test t13_mint --
  -C linker=/usr/bin/cc
  -C link-arg=-fuse-ld=bfd
  -C link-arg=-Wl,--no-keep-memory
  -C link-arg=-Wl,--strip-debug
```

The displayed multiline command is an argv specification, not a shell script.
The old bounded runner must not be used to bypass its exhausted build counter.
The proof/replay helpers in recovery 01 are prepared but unexecuted and must
be adapted to the new output namespace and successful-build record, reviewed
and checked before use.

## What success would and would not resolve

Success restores a real honest local proof/replay fixture. The current
synthetic S1/S2 seeds and funded v2 state family are not replaced by that
fixture. Any proposal to use proof-derived seeds must explicitly version the
seed/state definition and preserve the v2 record before evaluation.

D1-03 still requires full symbolic composition, a concrete faulty development
case, repaired NONVAC and a scoped no-violation result. D1-04 stays blocked
until those criteria pass; the review stops after D1-04/D1-06 and before
held-out evaluation remain in force.
