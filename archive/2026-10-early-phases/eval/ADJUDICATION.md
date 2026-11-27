# Blind warning adjudication

Rate each distinct BindCheck warning as `TP`, `FP`, or `unclear`. A true
positive means that the warning's stated narrow source property is present; it
does not promote E1 evidence to an exploit, deployment, or E4 claim. Use
`unclear` when the checked artifacts do not support either determination.

Prepare separate, identical blank sheets after the run:

```sh
python3 eval/adjudicate.py prepare results/raw/T26/heldout-<dataset-hash> \
  rater-a.csv rater-b.csv
```

Each rater receives only their own copy. The sheet intentionally omits the
tool's matching confidence, aggregate verdict, and all other-rater fields.
Raters must not exchange labels or reasons before both sheets are sealed. Fill
`label` and `rater_reason` for every row without changing `warning_id`.

Compute agreement only after both sheets are final:

```sh
python3 eval/adjudicate.py kappa rater-a.csv rater-b.csv \
  --output agreement.json
```

The output includes the three-by-three confusion matrix, observed and expected
agreement, and Cohen's kappa. A null kappa means both raters used one identical
constant label, making the chance-corrected denominator zero; it is not perfect
reliability evidence.
