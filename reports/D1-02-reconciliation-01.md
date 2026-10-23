# D1-02 reconciliation 01 — recover the documented continuation

Date: 23 October 2026. **Reconciliation: DONE. D1-02 availability selection:
DONE with qualifications. Research verdict: UNKNOWN.** No experiment was repeated.

## Objective and limits

Reconcile this copied workspace with inherited evidence before continuing the
roadmap. The [audit protocol](../protocols/d1/d1-02-reconciliation-01.json)
was frozen at 17:00:55 UTC: 45 minutes maximum, no new families, network
requests, dependency installations, builds, solver runs, proofs or replays.
Completion requires a provenance audit, preservation of old evidence,
an accurate selection decision and a documented next gate.

Read AGENTS, the research contract, README, roadmap, workspace guide,
D1-00/01/02 reports and the available D1-01 completion review first.
No later reviewer report was found in this workspace or the literature
repository's phase3 report inventory. AI inspection is not independent review.

## Recovered state

The working files were clean at `481ee07e2155e4b4307b300470d6aa0155d411b3`,
but ignored files included a later D1-02 continuation and D1-03 setup.
Their controlling files were absent from this copy. A planned exclusive-create
of `continuation-01` failed before writing anything; no new intake ran.

A read-only lookup in the sibling `/home/pollmix/Coding/BindCheck-d1`
found the missing files. Six exact copies were archived and restored:
the continuation protocol, intake metadata, fetch helper and report, and
both D1-03 protocol files. See
`results/raw/D1-02/reconciliation-01/recovery.json` for full paths, hashes and
lengths. The D1-02 protocol matches the pre-existing `pins.json` hash
`a4f5914f7e81412a84745ba154c6400ef100f14c02cb135036cc2b6a661a6d13`.
Both D1-03 protocols match the inherited freeze record. Other restored files
are exact sibling snapshots; their historical authorship/timing is not
independently established by a new signature or seal.

The recovered [continuation report](D1-02-continuation-01.md) selects
**hashcloak Semaphore-Noir** at
`6e24a48b2cb22c05a0c13361b5228d5e1c99bd0d`, with explicit qualifications.
The present source inspection supports its availability-level decision:
Noir batch circuits, Solidity per-occurrence nullifier writes, MIT source,
policy comments and a Hardhat test route generating and consuming batched
proofs. State writes are already permitted by the research contract.
Cryptographic batching is not itself a new asset-aggregation policy.

This is a plausible transfer target, **not a successful build, a supported
automatic extraction, or a safe application**. CLI version, circuit/key/
verifier correspondence, the 16-word proof prefix and batch policy remain
unresolved. Preserve its disclosed source/key/array exposure; do not tune
on it or call those mechanisms blind holdouts. The original D1-02 report's
earlier unresolved gate remains historical evidence and is unchanged.

Aztec remains unselected: the retained consumer path includes deferred
Outbox consumption and epoch rewards, and the snapshot does not establish
a self-contained producer/proving route. No impossibility or ecosystem-wide
absence is inferred. The old intake's `RewardLib` line reference is stale
(the inspected call is at line 184); the old metadata is preserved.

## Checks and evidence

The offline [auditor](../scripts/d1_02_reconcile.py) checks source blobs and
sizes against commit-linked tree entries, recomputes Git tree object hashes,
checks plans and logged URLs, and checks restored files and old seals.
It reads no network and invokes no compiler, prover or solver.

- All **46 retained source files** match their logged SHA-256, Git blob ID
  and tree length (37 Semaphore-Noir, 9 Aztec).
- The initial capture hashes **163 tracked files and 664 prior raw files**.
  All prior raw bytes and nonliving tracked files remain preserved.
- All 12 D1-02 sealed deliverables were archived before living-document
  edits. Its 105 sealed raw files remain unchanged.
- HEAD and the shared Git index retain their captured identities.

Commands run from this copy, with assertions enabled:

```sh
python3 -I scripts/d1_02_reconcile.py --output results/raw/D1-02/reconciliation-01/audit-01.json
python3 -I scripts/d1_02_reconcile.py --output results/raw/D1-02/reconciliation-01/audit-02.json
python3 -I scripts/d1_02_reconcile.py --output results/raw/D1-02/reconciliation-01/audit-03.json
python3 -I scripts/d1_02_reconcile.py --output results/raw/D1-02/reconciliation-01/audit-04.json
```

The first audit exited 1 (128/135 checks): it wrongly compared the seven
annotated tree JSON files directly to HTTP-response hashes. Those files
contain `bindcheck_prefix` and pretty printing. The failed audit and its exact
script bytes are preserved. The corrected audit removes only that local
field and serializes compact UTF-8 JSON without a newline; all seven
reconstructed response hashes match. It additionally recomputes 236 Git
tree identities, rather than relying only on JSON reconstruction.
Audit 02 exited 0, 371/371 checks, before recovery checks were added.
Audits 03 and 04 exit 0 with 386/386 recovery/preservation checks; audit 04
also follows the D1-03 preflight and final living-document updates. This is
consistency validation, not a semantic PASS. The tracked
[audit summary](../metadata/d1/d1-02-reconciliation-01.json) binds the raw
records. Python 3.12.12 and Git 2.43.0 were used.

## Limits and next task

The copied `.git` points to the sibling worktree's administrative directory.
This copy therefore shares its index; it is not an independently registered
worktree. No Git mutation, staging, registration change, commit or push was
performed. Do not run old hardcoded workspace verifiers as if this were the
original D1-00 checkpoint. The new audit explicitly checks this copy.

The inherited D1-03 setup logs report four successful producer compilations
and a successful consumer build. These were **not rerun here** and do not
establish joint semantics, replay, or completion. No D1-03 report exists in
either copy at lookup time. Its protocol is recovered intact, not revised.

**Next bounded task: D1-03 protocol preflight.** Check the recovered completion
criteria against its admitted transfer behavior and the original consumer.
Completion means a source-backed consistency decision before any new solver
or replay allocation. If proceeding requires a policy, evaluation or budget
change, stop for the user's review. D1-04 remains dependent on D1-03 completion.
