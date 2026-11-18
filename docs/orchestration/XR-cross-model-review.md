# XR — Cross-model review of the S4 oracle and the S2a analyzer changes

## Research context and authorization (read first)

Authorized **defensive** security research for an academic paper (IEEE
EuroS&P 2027). You are an independent code reviewer. The code under review was
written by other AI agents (Claude, and an earlier Codex session). A reviewer
from a different model family catches different mistakes, and the paper will
say this review was done.

The S4 oracle is a **test harness** that confirms a static analyzer's findings
on owned, synthetic, local Anvil deployments. It re-runs already valid proofs
and varies the surrounding call. It never forges proofs, never forks mainnet,
and never sends anything to a public chain. This task is **read-only review**.

**Branch / worktree:** `sprint/XR`, `$BC/wt-XR`.

**Owns:** `reports/XR/` only. **Edit no code.**

## Review targets

1. **S4 oracle**: `oracle/`, `tests/oracle/`, `reports/S4/REPORT*.md`, and the
   manifests and policies it uses (`findings/*/policy.md`, manifest files under
   `oracle/`).
2. **S2a analyzer changes**: `git diff pre-sprint-freeze2 -- bindcheck_zk/
   tests/s2a/`, and `reports/S2a/REPORT.md`.

## What to look for (in priority order)

1. **Overclaim.** Can the oracle report `E4-CONFIRMED` when the mutated
   transaction did not really succeed through the unchanged verifier and
   consumer, or when the effect is permitted by the policy? Can the analyzer
   report `VERIFIED_WITHIN_SCOPE` for an unresolved fact, a timeout, an excluded
   file or a build failure?
2. **Verdict leakage.** Does any policy, manifest or config encode the expected
   verdict, or name the case in a way the code branches on?
3. **Case-specific code.** Any condition on a repository, file, contract, card
   or case name (grep for them), or logic that only one case can trigger.
4. **Safety gates.** Can a manifest bypass `local_only` or `fork_enabled`, or
   reach a non-local RPC? Is the fork path really fail-closed?
5. **Correctness bugs.** Operators that do not mutate what they claim (e.g.
   `ALIAS` adding r to the wrong position, `REPLAY` reusing state wrongly),
   observer gaps (missed transfers or events), nondeterminism.
6. **Test quality.** Tests whose expected value was copied from the output, or
   fixtures that cannot fail.

You may run the existing tests to confirm a suspicion (`python3 -m pytest
tests/oracle tests/s2a`; the oracle needs local `anvil`, so if the sandbox
blocks it, say so and continue by reading). Do not modify code to test.

## Output

`reports/XR/FINDINGS.md`: one entry per finding, most severe first:

- severity (high, medium, low);
- file:line;
- the claim it breaks;
- a concrete failure scenario (inputs or state → wrong verdict);
- confidence (confirmed by running, or by reading);
- suggested fix (one or two sentences, no code changes).

End with a short list of things you checked and found sound, so the paper can
say what was reviewed. Include the AI disclosure (tool + model).

## Environment limits

No network. Do not `git commit` or push.

Final line of your session: `XR DONE` or `XR BLOCKED: <reason>`.
