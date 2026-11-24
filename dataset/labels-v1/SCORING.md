# MVP scoring rule (committed before any tool run; 2026-11-24)

## Units
- **Positive target:** a test FULL item with binding = Y (Pass 2 label), scanned at `vuln_commit`.
- **Fixed target:** the same item at `fix_commit`, where `eval_fixed_negative = yes`.
- **Hard-negative target:** a test FULL item with binding = N (Pass 2), scanned at `vuln_commit`.

## Inputs to the tool and the baseline (identical for both arms)
A cleaned source snapshot: no `.git`, no `audits/` or audit PDFs, and no README/CHANGELOG lines that mention an audit, auditor or finding ID. The same cleaned snapshot goes to every arm.

## Tool output (both arms)
A JSON list of warnings: `pattern`, `consumer_file`, `consumer_function`, `effect`, `unbound_value`, `explanation`, `confidence`.

## Ground truth location
For each test item, the evaluation lane writes `GT-locations.csv` (consumer file, function, unbound value) from the restricted Pass 2 evidence. It is committed **before** the first run and never shown to the build lane.

## Matching
A warning **matches** an item when both hold:
1. **Location:** the `consumer_file` basename equals the GT file, and `consumer_function` equals the GT function (or the GT says the function is n/a).
2. **Mechanism:** a fixed-prompt LLM judge, blind to the arm, says the warning's unbound value / mechanism is the same as the GT `unbound_value` (yes/no).

Reported at two strictness levels: **strict** (1 and 2) and **loose** (1 only).

## Metrics (raw counts first; Wilson 95% intervals; no single headline number)
- **Recall:** positives with ≥1 matching warning / positives.
- **Fixed-version specificity:** fixed targets with no matching warning / fixed targets.
- **Hard-negative specificity:** hard-negative targets with no binding warning at the GT location / hard negatives.
- **Other warnings:** every non-matching warning is counted per target and triaged by a human later as false positive or a possible new finding. It is never silently dropped.
- Each result is reported with and without PSS = Y items, and with and without items whose Pass 1 and Pass 2 labels differ.

## Validity notes
- Public audits may be memorized by the model. Cleaning removes direct leaks only. Both arms share the risk, so the comparison is fair; absolute recall is optimistic.
- Test n is about 13 positives and 13 negatives. Treat it as a pipeline check until the pinning pass grows the set.
