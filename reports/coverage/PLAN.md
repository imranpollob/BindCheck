# Lane C prospective coverage protocol (2026-11-09)

This plan and the control oracle in `tests/coverage/test_rules.py` are committed
before implementing or running the rules they score. The frozen comparison is
the 56-row unhinted DEV output at the `8ea6d223` analyzer hash, specifically
`reports/soundness/full-dev-ledger-2.csv` and the retained raw run named in
`reports/soundness/REPORT-2.md`. EVAL, recall, gate, review and adversarial
sets are excluded.

## Bounded rules and exact control outcomes

1. Resolve an exact OpenZeppelin `Pausable` import and direct `Pausable`
   inheritance for `whenNotPaused`/`whenPaused` only when no same-named local
   modifier exists. A direct public-vector transfer behind the modifier must
   be P1 `VERIFIED_WITHIN_SCOPE`. A missing import, unmatched base, or
   same-named local modifier with an external call must be P1 `UNKNOWN`.
2. Resolve a local, single-placeholder reentrancy lock only when its full body
   is an unconditional rejecting status guard, status assignment before the
   placeholder and reset after it. The two constants must be distinct literal
   values. A direct public-vector transfer behind this form must be P1
   `VERIFIED_WITHIN_SCOPE`. A conditional placeholder, multiple placeholders,
   absent reset, or external call must be P1 `UNKNOWN`.
3. Resolve exact OpenZeppelin `ERC721Enumerable` import and inheritance for a
   standard `_mint` effect, with the existing local-override gate. A directly
   public-bound recipient must be P1 `VERIFIED_WITHIN_SCOPE`. A local `_mint`
   override must be P1 `UNKNOWN`.

These controls are synthetic and establish source-recognizer behavior, not
proof acceptance or application security. A positive result cannot use an
interface-only verifier. No rule may use expected verdicts as analyzer input.

## DEV scoring

After the implementation and control pass, run all 56 rows without path hints
against the pinned read-only DEV checkouts. Preserve the raw run under a fresh
`results/raw/coverage/` namespace. Compare each row and pattern to the frozen
ledger, count `APPLICABLE` decisions separately from `UNKNOWN` and
`NOT_APPLICABLE`, and publish every changed verdict and reason. Inspect source
for every new `VIOLATION` and `VERIFIED_WITHIN_SCOPE`; an unreviewed source
transition is not counted as a validated coverage gain. Do not score a timeout,
failed build or unsupported artifact as a win or miss. Report the complete
UNKNOWN inventory, including nonapplicable and no-triple cells, separately.

The intended DEV paths are `DEV-F12`, `DEV-F29`, `DEV-F44`, and `DEV-F48` for
P1. Their exact resulting verdicts are deliberately not supplied to the tool
or assumed in advance: the control oracle specifies the added semantics;
actual DEV outcomes will be adjudicated after the run.
