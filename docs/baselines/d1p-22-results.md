# D1P-22 — pinned baseline runs

Date: 2026-10-28  
Repository base: `e64adfaed7f3d4136d824ec188c5212cd6dc4080`  
Protocol: `paper/baselines.md`  
Raw evidence: `results/raw/D1P-22/`

## Result

No baseline emitted a warning that described a proof-to-execution mismatch.
Two generic checks did localize known positive targets without explaining the
cross-component defect: Slither named Payy's `verifyBurn` consumer locus, and
the beta.22 Noir compiler named M-DOM's unused
`aztec_warptoad_address`. Slither also named M-SRC's `_localRoot` parameter,
but emitted the same style warning on the pinned control. These are
**detected-E1-lint**, not mismatch detections. BindCheck's already archived
D1P-30 runs remain the only results in this comparison that describe and
separate all three positive mismatches.

The experiment did not turn unavailable, unsupported, crashed, or timed-out
runs into misses. Nor does a generic warning at a control count as a false
proof-to-execution diagnosis: it is reported as nondiscriminating localized
lint.

## Scoring

The five columns are three known-positive development cases (Payy earlier,
M-DOM, M-SRC) and two controls (Payy check-added, WarpToad pinned). The result
codes are:

- **D** — detected: the report describes the proof-to-execution mismatch;
- **E1** — detected-E1-lint: a warning names the defect locus or variable but
  does not describe the mismatch;
- **M** — missed: a completed applicable arm supplied no such warning;
- **U** — unsupported: the arm cannot accept the target or the tool has no
  policy interface;
- **R** — unresolved: the applicable run could not complete, or a required
  harness/property was not present.

For a control, `M (control)` means “no binding signal,” not a false negative.
`E1 (control)` means nondiscriminating lint at the same locus, not a claimed
defect.

### Paper-ready comparison table

| Candidate / arm | Payy earlier (+) | Payy check-added (control) | WarpToad pinned (control) | M-DOM (+) | M-SRC (+) | Evidence / interpretation |
|---|---:|---:|---:|---:|---:|---|
| **Slither generic** | **E1** | **E1 (control)** | M (control) | M | **E1** | 61 findings on each byte-identical Payy consumer; `reentrancy-no-eth` names `verifyBurn`. The three WarpToad runs each have the same 66 detector classes; naming lint names `_localRoot`, but no report relates it to producer enforcement or state anchoring. |
| **Slither same-policy** | U | U | U | U | U | No custom policy detector was present; the preregistered arm is not a generic-detector rerun. |
| **Mythril generic** | **R** | **R (control)** | **R (control)** | **R** | **R** | Payy earlier/fixed and M-SRC reached the 1,800 s cap. Pinned startup lost a concurrent data-directory creation race; M-DOM exited `-11`. No issue report describes a binding mismatch. |
| **Mythril same-policy** | R | R (control) | R (control) | R | R | Mythril supports Solidity assertions, but no frozen assertion wrapper for these five targets was present. |
| **Foundry generic G1–G5** | R | R (control) | R (control) | R | R | No preregistered G1–G5 fuzz harness/port exists for either application. No candidate proof seed was introduced. |
| **Foundry same-policy** | R | M (control) | R (control) | R | R | The available honest Payy property wrapper ran: 7/7 tests passed under 1.8.6. It is a repaired-revision control and does not provide an earlier-revision, honest-only sigma arm. No WarpToad sigma harness exists. |
| **Echidna generic G1–G5** | R | R (control) | R (control) | R | R | No G1–G5 Foundry-mode harness/port exists. |
| **Echidna same-policy** | R | R (control) | R (control) | R | R | The available Payy wrapper reached `setUp` but Echidna rejected Foundry's `readFileBinary` cheatcode. No WarpToad sigma harness exists. |
| **CCC-Check generic** | U | U | U | U | U | The pinned build timed out and, independently, CCC-Check consumes CirC IR rather than Noir ACIR; no predeclared target adapter exists. |
| **CCC-Check same-policy** | U | U | U | U | U | No usable build or admitted annotation route for these targets. |
| **Picus generic** | U | U | U | U | U | Installed and parsed its bundled `TreeHasher.r1cs`; native inputs are `.circom`, iden3 `.r1cs`, and gnark `.sr1cs`, not ACIR. |
| **Picus same-policy** | U | U | U | U | U | No user-policy interface in the preregistered arm. |
| **SmartAxe generic** | U | U | R (control) | R | R | Payy is not a deposit/withdraw bridge pair. WarpToad applicability could not be resolved because the official Figshare artifact was blocked by an AWS WAF challenge. |
| **SmartAxe same-policy** | U | U | U | U | U | No user-property interface. |
| **Pinned Noir checks generic** | M | M (control) | M (control) | **E1** | M | beta.14 default + lookback emitted only an unrelated unused-import warning on both Payy revisions. beta.22 was silent on pinned/M-SRC and named M-DOM's unused public variable at `src/main.nr:20`. |
| **Pinned Noir checks same-policy** | U | U | U | U | U | Compiler checks expose no preregistered user-policy arm. |
| **BindCheck v1 (archived D1P-30; context, not rerun)** | **D** | M (control) | M (control) | **D** | **D** | `R-BIND`/`R-EFFECT` on Payy tail words, `R-BIND` on M-DOM word 5, and `R-ANCHOR` on M-SRC local root; 0/2 control warnings. Manual relation/validation routes remain counted inputs. |

The table gives BindCheck credit only for diagnostics that state the
cross-component reason. The E1 entries are deliberately separate even where
their location happens to be useful to an investigator.

### Mythril disposition

The two Payy runtimes are byte-identical (`0108942a…5585`), as are WarpToad
pinned and M-DOM (`f451b1ff…05af`); M-SRC is distinct
(`31d8817e…5940`). Payy earlier, Payy check-added, and M-SRC each ran for the
full 1,800-second per-case cap and were killed by the bounded runner without
stdout. The pinned run returned a JSON `success:false` startup error after a
race creating the shared default Mythril directory, and the concurrent M-DOM
run exited `-11` after 16.48 seconds. Because neither duplicate-bytecode run
is a valid analysis, both are **R**. These setup failures are preserved rather
than promoted to misses, and the identical bytecode fact is not used to claim
a successful run.

## Installation and self-check record

| Candidate pin | Availability | Executable/source SHA-256 | Self-check |
|---|---|---|---|
| Slither `0.11.6` | AVAILABLE | `78a29c91…58f87b` | `slither --version` → `0.11.6` |
| Mythril `0.24.8` | AVAILABLE | `3488e3a3…73284a` | `myth version` → `v0.24.8` |
| Echidna `2.3.3` | AVAILABLE | binary `377218ae…a6fcb`; archive `8e16a43d…a7902` | `Echidna 2.3.3` |
| Foundry `1.8.6` | AVAILABLE | `forge` `f63f468b…1f07`; upstream archive `d6bc05ee…91ec` | version/commit `6bad0a66…` |
| CCC-Check `7ed87b8c…` | **UNAVAILABLE** | source identity `ccc-check.cabal` `49330bab…d9dfe`; no binary | GHC/Cabal installed, but the pinned dependency build exceeded the bounded attempt; no self-test |
| Picus `138b151d…` | AVAILABLE, targets unsupported | `run-picus` `b34c0b65…d113` | bundled `TreeHasher.r1cs --nosolve` parsed and exited 0 |
| SmartAxe Figshare / repo `7ca21f72…` | **UNAVAILABLE** | no artifact | `GET https://figshare.com/s/985aae83fe5bc1291758` returned HTTP 202, `x-amzn-waf-action: challenge`, zero bytes |
| Noir beta.14 | AVAILABLE | `a0528f1c…d81eb8` | `nargo 1.0.0-beta.14`, noirc `60ccd48e…` |
| Noir beta.22 | AVAILABLE | `37f7d55d…f6e7b` | `nargo 1.0.0-beta.22`, noirc `c57152f9…` |

The Python console-entry hashes for Slither/Mythril identify the installed
entry points; their isolated virtual environments and pip transcripts are
preserved with them. The Picus revision is installed in an isolated Racket
user package root. CCC-Check's checkout is exact, but source identity is not a
substitute for the missing executable.

## Native-input disposition

- Slither accepts the pinned Solidity sources. WarpToad was compiled from the
  archived solc standard input; Payy used solc 0.8.20 with the archived
  OpenZeppelin sources. No target dependencies were downloaded.
- Mythril accepts archived EVM runtime bytecode. Payy's pair has identical
  runtime bytes; pinned/M-DOM also have identical runtime bytes; M-SRC differs.
- CCC-Check's documented frontend is CirC IR. The project has no admitted
  Noir/ACIR-to-CirC route, so the requested targets remain unsupported even if
  the source build later succeeds.
- Picus's R1CS path is its direct `.r1cs` reader (`run-picus FILE.r1cs`), with
  optional witness output. The experiment did not introduce an ACIR adapter.
- SmartAxe expects EVM bytecode plus cross-chain bridge pairing. That pairing
  is absent for Payy and unresolved for the same-chain WarpToad fixture.

## G1–G5 and arm completeness

The preregistration requires G1 replay and G2 rollback for both applications,
G3 only for Payy, G4 only for WarpToad, and G5 for both. No Foundry/Echidna
port implementing those generators was present. Running unrelated upstream
tests would not instantiate G1–G5, so those generic arms are **R**, not misses.
The existing Payy Foundry property suite is retained only as evidence for the
repaired honest control. Echidna's attempt on that exact suite failed at an
unsupported cheatcode before fuzzing.

The same-policy arm was also kept distinct from automatic obligation
derivation. A handwritten sigma wrapper is a baseline input, not a result of
extracting the consumer relation. No wrapper was invented after seeing these
outcomes.

## Reproducibility and limits

`results/raw/D1P-22/plan.json` froze the run limits and scoring before target
analysis. Each command record contains argv, working directory, UTC times,
timeout, exit status, environment overrides, and SHA-256 hashes of stdout and
stderr. `tool-manifest.json` records install status and binary hashes.

One discarded Slither setup attempt auto-detected the repository-level
Foundry/Hardhat configuration and invoked `npx hardhat`. Its transcript says
`hardhat@3.21.1` was not local and “will be installed,” followed immediately
by Hardhat `HHE22` (non-local installation unsupported). No target result from
that attempt is used, and no package was added to a target tree. This was an
unintended package-resolution attempt outside the pinned-tool install set; it
is preserved in
`generic-slither-warptoad-pinned/hardhat-artifacts.{json,stdout.txt,stderr.txt}`
rather than omitted. All scored Slither runs use offline archived solc inputs
or already-local dependencies.

This is a bounded comparison on development cases. An E1 warning is not a
proof-to-execution finding; a control with no warning is not a security
verdict; unsupported and unresolved cells do not establish absence of a
defect. The result does not change the paper's separate policy-to-obligation
or held-out-transfer claims.
