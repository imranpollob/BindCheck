# `bindcheck-zk.result/v1` additions

The schema identifier remains `bindcheck-zk.result/v1`. T25 adds reporting
fields without changing the research-contract verdict enum:

- `triples[].patterns.Px.applicability` is `APPLICABLE`,
  `NOT_APPLICABLE`, or `UNKNOWN`.
- `triples[].patterns.Px.unknown_reason_code` is `null` unless the verdict is
  `UNKNOWN`; every `UNKNOWN` has exactly one of `MISSING_ARTIFACT`,
  `BUILD_FAILURE`, `AMBIGUOUS_CORRESPONDENCE`, `UNSUPPORTED_CONSTRUCT`,
  `CAP_OR_TIMEOUT`, or `OTHER`.
- `patterns.Px.applicability` is the aggregate applicability. Applicable
  triples are aggregated independently of `NOT_APPLICABLE` triples.
- `patterns.Px.unknown_reason_codes` is the sorted set of fixed codes from the
  applicable unknown triples that control the aggregate. It can contain more
  than one code when retained candidate triples fail for different reasons.

`verdict` remains `VIOLATION`, `VERIFIED_WITHIN_SCOPE`, or `UNKNOWN`.
`NOT_APPLICABLE` is deliberately an applicability value, not a fourth
research verdict. A fully non-applicable pattern therefore has
`verdict: "UNKNOWN"` and `applicability: "NOT_APPLICABLE"`; decision-rate
calculations exclude it. Missing or ambiguous evidence has
`applicability: "UNKNOWN"` or `"APPLICABLE"` with an `UNKNOWN` verdict and is
never counted as safe.
