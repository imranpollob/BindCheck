# Typed role-binding interface

> **D2-08 prospective correction:** the D1P-43 implementation below inferred
> security-relevant roles from identifier spelling. Its exact implementation
> remains in `role_binding.py` for historical audit, but the public entry point
> now quarantines it and returns an `UNKNOWN` support failure. Names and source
> locations are display annotations only. A validated
> `bindcheck.compiler-identity-bundle/v1` is required, and identities alone
> still cannot produce a warning until the separate Step 9 reviewed P/O/E
> boundary check exists. Historical sealed D1/D2 outputs keep their original
> interpretation; they are not retroactively rescored.

The remainder of this document describes the historical D1P-43 interface and
must not be read as the current public security-conclusion path.

`src/bindcheck_d1/role_binding.py` is a separate, fail-closed rule module. It
does not register with or modify the consumer frontends or
`static_analyzer_v1.py`.

```python
from bindcheck_d1.role_binding import analyze_role_binding

role_result = analyze_role_binding(
    analysis,                         # successful static_analyzer_v1 result
    producer_source=noir_main,
    producer_support_sources=[hashing_library],
)
```

The module verifies that:

- the input has a supported static-analysis schema and an extracted relation;
- the exact relation file still matches the hash recorded by the analyzer;
- relation, normalized consumer facts, and producer ABI have equal word widths;
- relation boundary origins agree with the analyzer's normalized words; and
- the Noir source's scalar public declaration order agrees with the decoded
  artifact ABI.

It then returns `bindcheck.role-binding.v1`, including one producer and
consumer role record for every verifier word. Producer records contain the ABI
role and hash/commitment/tree computations inferred from calls whose signatures
are present in the supplied support sources. Consumer records contain the
boundary role, successful-path guards and the committed effects they authorize,
state identity and admission polarity, and direct committed-effect operand
roles from the analyzer-checked relation.

`R-ROLE` warning evidence has a `kind` field:

- `boundary-role`: the word position has different producer/consumer types;
- `domain-identity`: both sides have a domain type but name different
  application/chain identities;
- `producer-state-membership`: a branch authenticates the wrong root member;
- `state-identity`: a root is checked against a differently typed state set;
- `polarity`: a root/replay key uses the wrong admission direction or replay
  write behavior;
- `effect-authorization`: a principal amount is not the producer
  commitment's amount input; or
- `effect-beneficiary`: a principal effect is not directed to the
  authenticated recipient role.

Any failed precondition raises `RoleBindingUnsupported`. Callers must report
that as `UNKNOWN`; they must not convert it to an empty warning list. In
particular, this module is called only after the main analyzer, so an analyzer
mapping or memory-dependency gate remains controlling.

The rule is a bounded E1 diagnostic. Identifier roles, extracted relations,
and source call structure do not prove reachability or establish a
`VIOLATION` verdict.
