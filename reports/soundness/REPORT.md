# L1 soundness hardening report

## Objective and status

This lane addressed the four source-review objections to positive BindCheck verdicts: path-insensitive effect guards, treating `msg.sender` as a proof-authorized identity, verifier-wide rather than replay-key-specific canonicality, and connectivity/name-based commitment evidence. The bounded implementation task is complete. This report makes no global soundness claim: unsupported control flow and unsupported cryptographic constructions now produce `UNKNOWN`, while commitment evidence is a screen and cannot produce `VERIFIED_WITHIN_SCOPE`.

The work started from commit [`feb5c19`](../../results/raw/T27/verification-final/verification.json) and the controlling analyzer run used revision [`6a991bf1a61d09e430c107653891ad46a11a0453`](../../results/raw/T27/verification-final/verification.json). No live-chain transaction, deployed-contract interaction, maintainer contact, held-out evaluation, recall-set read, push, merge, or tag was performed.

## Authority and preserved disagreement

The research contract governed verdict semantics. The baseline README records overlapping historical T25/T26 freeze hashes, while the immutable task reports preserve the evidence associated with their respective runs. This lane did not rewrite that history or edit `README.md`. It uses the exact baseline and after-run artifacts named in [`full-dev-summary.json`](full-dev-summary.json). Per the lane instruction, it also did not edit `docs/project-status.md`; that instruction overrides the living-checkpoint update for this task.

## Expected outcomes were committed first

The regression oracle was committed before production fixes as [`1dc60f977bd6c16a18d849d127353e1955a57810`](../../results/raw/T27/verification-final/verification.json). Running it against the pre-fix implementation produced exactly [12 mismatches](../../results/raw/T27/verification-final/verification.json), covering all four review concerns. The final oracle contains [18 declared soundness cases](../../results/raw/T27/verification-final/verification.json), and its expected verdict/reason pairs are preserved in [`tests/soundness/expected.json`](../../tests/soundness/expected.json).

Two expectation refinements were also committed before the corresponding implementation:

- [`802a2aa`](../../tests/controls/expected.json) declares when the existing synthetic controls intentionally use the explicit “any caller may receive” policy and when unresolved inheritance must remain `UNKNOWN`.
- [`dd48736`](../../tests/soundness/expected.json) changes the post-effect guard case to `UNKNOWN / POST_EFFECT_GUARD_SEMANTICS_UNRESOLVED`, because the analyzer cannot prove whether a later check safely dominates every committed effect under all relevant external-call and rollback semantics.

## Concern a: guards must protect the effect path

### Property and fix

An equality is positive P1/P2 evidence only when the analyzer can show that it is enforced before the protected effect on every successfully committing path represented by the supported control-flow model. The implementation now recognizes a preceding `require`/`assert`, a rejecting inequality branch, and an effect inside the equality branch. A guard in an irrelevant branch does not count. A guard after the effect is unresolved. Modifiers and inherited behavior that may affect the result but cannot be resolved produce `UNKNOWN`; delegatecall remains `UNKNOWN`.

P2 local-context checks use the same path-sensitive test and examine all recovered effects rather than accepting a verifier-wide name match. The complete rule, justification, negative controls, and positive controls are recorded in [`docs/verdict-rules.md`](../../docs/verdict-rules.md); the executable cases are in [`test_verdict_soundness.py`](../../tests/soundness/test_verdict_soundness.py).

### Regression coverage

The adversarial cases cover an irrelevant branch, a guard after the effect, an unresolved modifier, and unresolved inheritance. Legitimate positives cover a preceding `require`, a rejecting inequality branch, and an effect nested in the equality branch. Expected results and case identifiers are linked in [`expected.json`](../../tests/soundness/expected.json).

## Concern b: caller identity is policy, not proof identity

### Property and fix

`msg.sender` no longer counts as bound merely because it receives the effect. It is positive evidence only when it is equated, under the supported path model, to a recovered proof public input. The other permitted case is an explicit analysis policy, `any_caller_may_receive`, which means the application intentionally allows any caller to receive the effect; the policy is recorded in result inputs and exposed by `--any-caller-may-receive`.

Without either condition, a caller recipient is `VIOLATION / UNBOUND_EFFECT_RECIPIENT`. The negative caller-not-proven case and the two legitimate positives—caller equated to a public input and explicit policy—are linked from [`expected.json`](../../tests/soundness/expected.json). The policy boundary and positive reason are documented in [`verdict-rules.md`](../../docs/verdict-rules.md).

## Concern c: canonicality must cover the replay key position

### Property and fix

P3 now recovers the actual public-input vector position used as each replay key. A positive verdict requires the on-chain canonicality guard to cover that exact position, or a supported loop that covers every position. A guard on position `i` is not evidence for a replay key at position `j`. If the key position cannot be recovered, the result is `UNKNOWN / REPLAY_KEY_POSITION_UNRESOLVED`.

The same position-aware rule is used by P4: fixed-index checks must cover every fixed public-input position, while a recognized dynamic all-position loop may cover the vector. The wrong-position negative, exact-position positive, and all-position-loop positive are linked from [`expected.json`](../../tests/soundness/expected.json) and described in [`verdict-rules.md`](../../docs/verdict-rules.md).

## Concern d: commitment evidence is screen-only

### Chosen policy

This lane chose the conservative option: no current R1CS/source commitment recognizer can yield `VERIFIED_WITHIN_SCOPE`. R1CS parsing now preserves the prime, every coefficient, and each linear-combination term, and excludes zero-coefficient wires from connectivity. That prevents coefficient loss in downstream inspection, but connectivity still does not establish the semantics of Poseidon, MiMC, or another commitment.

Similarly, matching Solidity names does not prove hash-input order, encoding, arity, domain separation, or equality to the circuit construction. Consistent source order and R1CS connectivity therefore yield `UNKNOWN / COMMITMENT_BINDING_SCREEN_ONLY`; an order mismatch yields `UNKNOWN / COMMITMENT_PREIMAGE_ORDER_UNRESOLVED`. Neither reason is eligible for a positive verdict. The policy is explicit in [`verdict-rules.md`](../../docs/verdict-rules.md).

### Regression coverage

Adversarial controls cover connected-but-nonbinding constraints, altered coefficients, and swapped hash-input order. A consistent construction is the legitimate screen-positive: it confirms the recognizer still recovers candidate evidence while deliberately remaining `UNKNOWN`. A direct public-input equality remains a legitimate non-commitment positive. All expected results are linked in [`expected.json`](../../tests/soundness/expected.json).

## Verification

The controlling verification record is [`results/raw/T27/verification-final/verification.json`](../../results/raw/T27/verification-final/verification.json), whose SHA-256 is [`65295e2c07af63dfbb47ba0916ef1c9aa6e1752159938cca7b7a4a7cb944d92e`](evidence.sha256). It records exact argv, cwd, stdout, stderr, elapsed time, and exit status for every command.

- The soundness suite ran [2 test methods over 18 declared cases and exited 0](../../results/raw/T27/verification-final/verification.json).
- The existing control/CLI suite ran [9 test methods and exited 0](../../results/raw/T27/verification-final/verification.json). Its frozen population is [24 legacy Track B controls plus 98 analyzer controls, 122 total](../../results/raw/T27/verification-final/verification.json).
- `python3 -m compileall -q bindcheck_zk tests/soundness tests/test_bindcheck_zk_controls.py scripts/render_soundness_summary.py scripts/run_soundness_verification.py` [exited 0](../../results/raw/T27/verification-final/verification.json).
- `git diff --check` [exited 0](../../results/raw/T27/verification-final/verification.json).
- The verified environment was [Python 3.14.7, Circom 2.2.3, snarkjs 0.7.6, and Git 2.51.0](../../results/raw/T27/verification-final/verification.json). The snarkjs version probe printed its version and usage but [exited 99](../../results/raw/T27/verification-final/verification.json); it is recorded as a probe result, not a successful check.

Existing control expectation changes are intentional and isolated in [`tests/controls/expected.json`](../../tests/controls/expected.json): caller-recipient positives declare the explicit policy, inherited ERC721-style consumers become `UNKNOWN`, and controls aimed at a different unsupported feature use the policy only to avoid confounding their intended reason.

## Full DEV unhinted before/after ledger

The machine-readable summary is [`full-dev-summary.json`](full-dev-summary.json), with SHA-256 [`a74919787c4fb52d1e440b5726eedf819597b81cd22a32eb60da5e6b25a84265`](evidence.sha256). The tracked row ledger is [`full-dev-before-after.csv`](full-dev-before-after.csv), with SHA-256 [`edf96ea21de08e9901c96c006528431c00ecea323c41efbcca77fe4e51c83f91`](evidence.sha256). It has [56 baseline rows and the same 56 after rows](full-dev-summary.json). Counts below use all [56 rows per phase](full-dev-summary.json), including build/setup failures as `UNKNOWN`; no unavailable row is counted as a win.

| Pattern | Before verdicts (denominator 56) | After verdicts (denominator 56) | Applicable decided/total, before → after |
|---|---|---|---|
| P1 | 4 `VIOLATION`, 4 `VERIFIED_WITHIN_SCOPE`, 48 `UNKNOWN` | 1 `VIOLATION`, 0 `VERIFIED_WITHIN_SCOPE`, 55 `UNKNOWN` | 8/17 → 1/17 |
| P2 | 0 `VIOLATION`, 1 `VERIFIED_WITHIN_SCOPE`, 55 `UNKNOWN` | 0 `VIOLATION`, 0 `VERIFIED_WITHIN_SCOPE`, 56 `UNKNOWN` | 1/27 → 0/27 |
| P3 | 4 `VIOLATION`, 12 `VERIFIED_WITHIN_SCOPE`, 40 `UNKNOWN` | 11 `VIOLATION`, 4 `VERIFIED_WITHIN_SCOPE`, 41 `UNKNOWN` | 16/23 → 15/23 |
| P4 | 0 `VIOLATION`, 23 `VERIFIED_WITHIN_SCOPE`, 33 `UNKNOWN` | 0 `VIOLATION`, 22 `VERIFIED_WITHIN_SCOPE`, 34 `UNKNOWN` | 23/46 → 22/46 |
| P5 | 0 `VIOLATION`, 4 `VERIFIED_WITHIN_SCOPE`, 52 `UNKNOWN` | 0 `VIOLATION`, 4 `VERIFIED_WITHIN_SCOPE`, 52 `UNKNOWN` | 4/46 → 4/46 |

Every table cell is generated from [`full-dev-summary.json`](full-dev-summary.json); every individual row and reason is in [`full-dev-before-after.csv`](full-dev-before-after.csv). The summary records [9 P1 transitions, 1 P2 transition, 8 P3 transitions, 1 P4 transition, and no P5 transition](full-dev-summary.json). In particular, the new P3 result turns seven formerly positive rows into `FIELD_ALIAS_REPLAY_KEY` violations when their actual replay-key positions are not guarded, and turns one formerly positive row into `UNKNOWN` when its position cannot be recovered; the exact row identifiers are in [`full-dev-summary.json`](full-dev-summary.json).

The controlling after-run completed with [0 analyzer crashes, 46 rows with analyzable triples, 43 successful builds, and 33 failed build attempts](full-dev-summary.json). The build totals exceed the row count because some rows contain multiple candidate triples. The summed analyzer time was [239.481817 seconds](full-dev-summary.json); the slowest row was [DEV-F50 at 45.934566 seconds](full-dev-summary.json). These are exact recorded values, not rounded values.

The controlling after-run manifest is [`results/raw/T27/after-20261109T030552Z-33270/manifest.json`](../../results/raw/T27/after-20261109T030552Z-33270/manifest.json), SHA-256 [`60561481132698e29315d6e33497bd797408a05ecbdddf837e02c9ee88ea2d61`](evidence.sha256). Its raw per-row ledger is [`per-row-ledger.json`](../../results/raw/T27/after-20261109T030552Z-33270/per-row-ledger.json), SHA-256 [`0ccb1b0bb269d2c385039c0820e51ef7bfad6604a9c799965e50cb1d7e821e8a`](evidence.sha256). The pinned baseline source is the preserved T25 artifact named and hashed in [`full-dev-summary.json`](full-dev-summary.json).

## SPSC reassessment

SPSC does **not** clear after the hardening. For [`DEV-F12`, `NethermindEth/spsc` at commit `6d07155ecf295e6d68936bf424557621d0c66456`](full-dev-summary.json), P1 changes from `VERIFIED_WITHIN_SCOPE / EFFECT_VALUES_BOUND_BY_COMPILED_COMMITMENT` to `UNKNOWN / UNRESOLVED_CONSUMER_MODIFIER` ([row evidence](full-dev-before-after.csv)). The entry point uses `nonReentrant`, whose effect on the supported path model is not resolved. Independently, even if modifier handling were added, the old commitment evidence is now screen-only and cannot produce a positive verdict. Thus the prior SPSC positive was not retained merely to preserve an evaluation outcome.

## Freeze result

`./freeze.sh` [exited 0](../../results/raw/T27/verification-final/verification.json). It printed package digest [`d68b0f44c776fe25806c1c5b77fccd5c25d58c799ee039481a98150695d5419c`](../../results/raw/T27/verification-final/verification.json) and `BINDCHECK_ZK_CONTENT_SHA256=`[`bca703515661a19bac0b0086ce8e885b7140bdb9270e794a4f981a5b10af5a77`](../../results/raw/T27/verification-final/verification.json). No tag was created.

## Evidence, commands, and provenance

The full DEV command, environment, candidate-set hash, query hash, revisions, per-row commands, exit statuses, stdout/stderr paths, and tool probes are preserved in the [controlling manifest](../../results/raw/T27/after-20261109T030552Z-33270/manifest.json). The report summary was deterministically rendered by [`scripts/render_soundness_summary.py`](../../scripts/render_soundness_summary.py); final test and freeze evidence was captured by [`scripts/run_soundness_verification.py`](../../scripts/run_soundness_verification.py).

The controlling run reused the read-only pinned Circom and npm artifacts from the preservation checkout. The executable Circom SHA-256 is [`7d0bd3cc8d0c4942813f5060bd5f9c011f3469e46755a067926101ee74d4e202`](../../results/raw/T27/verification-final/verification.json), and the snarkjs CLI SHA-256 is [`ce5d4938e03a798a416d062f0b689b8d0220d36ab1feea34618211b241082a53`](../../results/raw/T27/verification-final/verification.json). Generated dependencies, compiler output, and raw logs remain ignored.

## Assumptions and limitations

- The path model is intentionally restricted. It does not claim to resolve modifier expansion, inheritance dispatch, proxy/delegatecall behavior, arbitrary aliasing, reentrancy, or all Solidity rollback subtleties. These cases fail closed to `UNKNOWN`.
- The explicit “any caller may receive” policy is an application-policy assertion supplied by the analyst. It does not prove a ZK identity relation and is recorded as such.
- The R1CS parser preserves coefficient evidence, but no coefficient-aware Poseidon/MiMC semantic recognizer was implemented. Commitment evidence therefore remains screen-only.
- Full DEV is a development-set rerun, not independent held-out validation. No recall or EVAL artifact was inspected.
- A first after-run was preserved as noncontrolling evidence in [`results/raw/T27/after-20261109T030109Z-28584/manifest.json`](../../results/raw/T27/after-20261109T030109Z-28584/manifest.json). It exposed an applicability-order regression; that regression was fixed in [`6a991bf`](../../results/raw/T27/verification-final/verification.json), and the complete DEV run was repeated rather than selectively patched.

## Recommended next bounded task

Add a modifier-expansion front end for statically resolvable, local Solidity modifiers only. Completion should require precommitted negatives for a modifier that skips the body, executes the body conditionally, or performs a relevant external call; precommitted positives for a pure precondition modifier and the SPSC `nonReentrant` shape; all existing and soundness controls passing; and a fresh full-DEV ledger showing whether `DEV-F12` remains `UNKNOWN` for commitment-screen reasons after the modifier itself is resolved. Do not broaden this task to inherited or proxy-resolved modifiers without separate expected outcomes.
