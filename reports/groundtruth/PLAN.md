# L4 ground-truth lane: pre-registered criteria

Lane: L4 ground truth / auditor. Branch `zk-groundtruth`, base `feb5c19`.
Written and committed **before** the per-case or per-family labels below are
produced, so that the criteria are not tuned on what the data shows.

This lane proposes labels for a human to decide. It decides nothing. It does
not modify `bindcheck_zk/`, `eval/`, `README.md`, or `docs/project-status.md`,
and it runs no analyzer on any EVAL repository.

Observations already made before this file was written (recorded so that they
are not mistaken for later, criteria-driven outputs):

- `dataset/recall-set-v2.csv`: column `scope_class` has 20 `integration` rows;
  column `v2_scope_class` has 27 `integration` rows. The 7 rows that differ have
  `scope_class=integration-or-execution-semantics` and
  `v2_scope_class=integration`.
- Payy (`polybase/payy` at `c4d2c90`): the tree has 25 `.nr` files, 0 `.circom`
  files, and `eth/noir/agg_agg.sol` / `agg_agg_HonkVerifier`.
- T25 retained output gives P3 `VERIFIED_WITHIN_SCOPE` on the vulnerable
  zkDrops (DEV-H01) and Semaphore (DEV-H03) revisions.

## C1. Promoted recall cases: keep / demote

Applies to the 7 rows with `scope_class != integration` and
`v2_scope_class == integration`.

For each row, read the source report text for that finding and record:

1. **Boundary value.** Does the defect concern a value that crosses the
   proof→contract boundary (a public input/output that a Solidity consumer reads
   or forwards)? yes / no / unclear.
2. **Consumer consequence.** Does the report state, or does the source at the
   vulnerable revision show, that the exploit's consequence is a consumer
   effect (state write, transfer, mint, registration, disclosure acceptance)
   that depends on that value? yes / no / unclear.
3. **Fix locus.** Does the fix touch the consumer, the verifier, or the
   circuit's public interface (public signal set, order, width, range of a
   public signal)? Or is it internal to circuit constraint logic only?
4. **P1–P5 mappability.** Can one P1–P5 predicate honestly be named whose
   VIOLATION on the vulnerable revision would correspond to this defect, with a
   source location in a file the analyzer inventories? yes / no.

Proposal rule (fixed now):

- **KEEP strict** iff (1)=yes and (2)=yes and (4)=yes.
- **DEMOTE to broader** iff (4)=no, or the fix locus is internal circuit
  constraint logic with (1)=no.
- **UNCLEAR** otherwise; the human decides.

Research-contract §5.3 scope ("an underconstrained circuit is in scope when its
accepted relation permits a proof-to-execution violation") is recorded
separately from P1–P5 mappability. A row can be in research scope and still not
be scorable by the current P1–P5 analyzer.

## C2. Exposure

A recall case is **EXPOSED** if any of these holds:

- its repository appears in a `split == DEV` row of
  `dataset/source-corpus-v2.csv` (any variant);
- its repository or revision was used in a prior development task with
  retained evidence (T-, D1-, D1P-, D2- reports, or `results/raw/feasibility-v2`);
- it was named in the lane brief as used in development (zkDrops, Semaphore
  field alias, Payy).

Additionally record **RELATED** (not exposed) when a DEV repository belongs to
the same GitHub organisation, and **SAMPLE-OVERLAP** when the repository's
family is also in the 278-family preregistered EVAL sample.

## C3. Gate manifest inclusion

`gate/GATE-MANIFEST.csv` lists every row with `v2_scope_class == integration`
**and** `v2_pair_status == vulnerable-and-fixed-resolved`. Rows with v1
`scope_class == integration` are flagged in a separate column so either
counting rule can be applied. No row is added or dropped on judgment; proposed
demotions appear only as a column.

## C4. Recall card contents

One card per `v2_scope_class == integration` row (27). Each card: source
excerpt (verbatim, with URL), vulnerable vs fixed code at the fix lines (from
the fixed commit's own diff, with presence of the "before" lines checked at the
pinned vulnerable commit), proposed expected pattern and location regex in the
`path:line` format used by `eval/common.py:pattern_locations`, and blank
accept/edit/drop fields. When a pair is incomplete, the missing side is written
`MISSING`.

The proposed pattern/location is derived from the source report and the fix
diff, never from analyzer output.

## C5. Maturity audit rubric (278 sampled families)

Evidence sources: `dataset/source-corpus-v2.csv` columns (`v2_maturity_basis`,
`v2_sourcify_evidence`, `stars`, `archived`, `pushed_at`) and the README at the
pinned commit. No analyzer, no clone, no on-chain query, no explorer request;
explorer links are constructed, not visited.

Proposed label, first match wins:

1. `verified-deployed` — exact Sourcify/GitHub source match recorded in
   `v2_sourcify_evidence`. Confidence **high**.
2. `deployed-address-in-docs` — README contains a 20-byte `0x` address within
   300 characters of a deployment cue (`deploy`, `contract address`, `mainnet`,
   a named mainnet chain, or an explorer URL). Confidence **medium** if a
   mainnet cue is present, **low** if only testnet cues (`sepolia`, `goerli`,
   `holesky`, `testnet`, `amoy`, `mumbai`, `fuji`, ...) are present; the
   testnet-only case is labelled `testnet-address-in-docs`.
3. `audited-production` — README links an audit report (URL containing
   `audit` or a PDF) **or** states "audited by <firm>" / "<firm> audit" for a
   known auditor. Library mentions (e.g. "OpenZeppelin AccessControl") and
   generic words ("production", "live") do not count. Confidence **medium**
   with a link, **low** with a name only.
4. `hackathon-student` — README names a hackathon, bootcamp, course,
   assignment, or student project. Confidence **medium**.
5. `unclassified` — none of the above. Confidence **low**.

Contradiction flags are recorded independently of the label:
`DO-NOT-DEPLOY`, `PROTOTYPE/POC/DEMO`, `NOT-AUDITED`, `TESTNET-ONLY`,
`README-MISSING`, `README-FETCH-FAILED`.

Agreement with the preregistered stratum is reported as a count; disagreement
is a proposal for human review, not a correction. Any correction requires a new
ledger hash and a documented pre-analysis sample refresh (`EVAL-SAMPLE-PLAN-v2.md`).

## C6. Verifier-kind flags for warning groups

For each of the 16 retained warning groups (15 in T24 + 1 `retained-new` in
T25), inspect the verifier source that the warning's triple matched, in the
retained DEV checkout. Assign one kind:

- `REAL` — generated Groth16/PLONK verifier with a pairing precompile call
  (`staticcall` to address 8 / `0x08`) and non-placeholder key constants;
- `PLACEHOLDER` — the source says placeholder/stub/TODO, or key points are
  dummy constants (e.g. every IC equal to the generator `(1,2)`);
- `MOCK` — named or located as mock/test and returns a constant;
- `SIMPLIFIED/STAND-IN` — structural checks only, no pairing check;
- `FAIL-CLOSED` — always returns false or reverts;
- `NO-VERIFIER-MATCHED` / `AMBIGUOUS` — when the triple has none or several.

The blind adjudication sheet shows code excerpts and the rule's claim text,
uses opaque IDs in a seeded random order, and omits the tool's verdict,
confidence, instance counts, the author's label, and the author's reason.
