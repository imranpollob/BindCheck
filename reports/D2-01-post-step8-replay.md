# D2-01 post-Step-8 historical replay

**Task status:** COMPLETE — non-destructive historical replay `PASS`  
**Live-checkout direct replay:** expected `FAIL`, exactly 1/8,134 mismatch  
**Historical in-memory overlay replay:** `PASS`, 8,134/8,134, zero mismatches  
**Research verdict:** `UNKNOWN`; no result was rescored or relabeled

## 1. Objective and boundary

D2-08 intentionally changed `src/bindcheck_d1/role_binding.py` after D2-01
sealed and executed. The current checkout therefore cannot directly satisfy the
historical D2-01 content seal. This task restores a reproducible way to check
the historical byte set without changing the current implementation or any
historical evidence.

The task did **not** modify:

- `protocols/d2/d2-01-seal-v1.json`;
- `reports/D2-01.md` or either D2-01 raw namespace;
- `scripts/d2_foundation.py`; or
- the current Step-8 `src/bindcheck_d1/role_binding.py`.

The wrapper performs no filesystem substitution. It retrieves one Git blob as
bytes, validates those bytes, and uses them only as the hash input for the one
sealed path during the historical replay.

## 2. Controlling overlay record

The machine-readable record is
`protocols/d2/d2-01-post-step8-replay-v1.json`. It permits exactly one overlay:

| field | frozen value |
|---|---|
| D2-01 seal | `protocols/d2/d2-01-seal-v1.json` |
| seal SHA-256 | `9f47676dd85a81ce0088c742a154f3919d9d94af78c1c8979bdd0386f56ddc06` |
| seal member count | 8,134 |
| overlay path | `src/bindcheck_d1/role_binding.py` |
| immutable base commit | `544656abbfb535dcbe0f1157087240464f38cb0b` |
| Git object | `544656abbfb535dcbe0f1157087240464f38cb0b:src/bindcheck_d1/role_binding.py` |
| historical SHA-256 | `a516f0e339f6fec23fcd96efb52821e9933feb6837e740c99a6d5dbee7bd9028` |
| historical size | 41,698 bytes |
| current SHA-256 | `5bb3012b7d192e75e266cc3f5265e024046e8614c0cb63891c7acd5271eeaa71` |
| current size | 43,263 bytes |
| substitution mode | `IN_MEMORY_BYTES_ONLY` |

The wrapper rejects a different path, commit, object specification, hash,
size, seal, member count, or substitution count before replay.

## 3. Why the live byte differs

D2-08 quarantined the historical name-derived role logic as
`ANNOTATION_ONLY_QUARANTINED`. The public role-binding entry point now fails
closed with `COMPILER_BACKED_IDENTITY_REQUIRED` without a compiler identity
bundle and `AUTHORIZATION_BOUNDARY_CHECK_REQUIRED_STEP9` after bundle
validation. Identifier spelling and display locations cannot support a current
security conclusion.

The wrapper verifies this provenance against:

- `reports/D2-08.md`, SHA-256
  `aaca4aa036a0604febd6869604e8dfcfc3709a72a15c8fa588717309316fd2cd`;
- `protocols/d2/d2-08-compiler-identity-v1.json`, SHA-256
  `b529f9c12ca695cf4737a0f01f10f9f357216fea0f7505a42fc381614c6b04ba`;
  and
- `results/raw/D2-08/content-seal-v1.json`, SHA-256
  `d2195d93fc6e51458a994ecc63838935fb36bad275379ef15e43ca2f9c112343`.

The D2-08 seal itself binds the current role-binding file at SHA-256
`5bb3012b...aa71` and 43,263 bytes. The historical replay preserves D2-01's
original interpretation; it does not undo D2-08 or route the historical logic
back into the current analyzer.

## 4. Replay procedure and result

Command:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/d2_d201_post_step8_replay.py
```

The output schema is
`bindcheck.d2.d2-01-post-step8-historical-replay-result/v1`. The wrapper:

1. validates the overlay record and exact D2-01 seal identity;
2. hashes every live sealed path and requires the exact expected failure set;
3. resolves the full base commit and obtains the pinned path with `git show`;
4. requires the retrieved bytes to hash to `a516f0e339...d9028` and be 41,698
   bytes;
5. rehashes all 8,134 members, using those bytes for only the one overlay path;
6. validates Step-8 provenance; and
7. emits the separate D2-00 retention-gap observation.

Observed result:

| check | status | checked | mismatches | interpretation |
|---|---:|---:|---:|---|
| direct live-checkout replay | `EXPECTED_FAIL` | 8,134 | 1 | only `src/bindcheck_d1/role_binding.py`; sealed `a516f0...`, observed `5bb301...` |
| historical blob identity | `PASS` | 1 | 0 | exact immutable-base byte, held in memory only |
| historical overlay replay | `PASS` | 8,134 | 0 | exactly one in-memory substitution; every other member is the live retained sealed byte |
| Step-8 provenance | `VERIFIED` | 3 artifacts plus seal entry | 0 | explains the authorized post-D2-01 byte change |

This establishes historical reproducibility of the D2-01 seal under its
executed byte set. It does **not** establish that the current checkout is byte-
equivalent to D2-01, that the historical role rule remains current, or that any
warning, capability, safety, or Gate result changed.

## 5. D2-00 retention gap

D2-00 records the pre-report identity of
`docs/d2/status-and-ownership.md` as SHA-256
`afc86272b099d2bca73c785af3cee210b33f323d600cf0e5d96bbf2eb1ca47a0`.
That path is absent from base commit
`544656abbfb535dcbe0f1157087240464f38cb0b`; the current living document had
SHA-256 `90382119...ac41` when the overlay record was created. The old
`afc86272...47a0` content is unavailable in the retained artifacts inspected.

Its disposition remains
`UNAVAILABLE_RETENTION_GAP_NOT_RECONSTRUCTED`. It is not fetched, synthesized,
or included in the D2-01 overlay. The D2-01 historical replay therefore repairs
only the exactly recoverable role-binding byte and does not conceal the
separate D2-00 retention limitation.

## 6. Validation and identities

Validation performed:

- overlay protocol JSON parse: pass;
- focused replay tests: 5/5 pass;
- direct wrapper execution: `PASS`, with the exact live and overlay outcomes
  above;
- complete repository unit suite: 151/151 pass;
- Python AST parse for the new wrapper and tests: pass;
- all D2 JSON parse: pass; and
- `git diff --check`: pass.

Pre-report tracked identities:

| artifact | SHA-256 |
|---|---|
| `scripts/d2_d201_post_step8_replay.py` | `eee0ad0b2e4853ecece363dd5f7f17d04bef17c08acba09a7476b9e2beee78c5` |
| `protocols/d2/d2-01-post-step8-replay-v1.json` | `cbb4208d84885e54f2fbb77331000713aed9953dc2db6950ef94a38e3250200c` |
| `tests/test_d2_d201_post_step8_replay.py` | `48d9625316a342da324ca7c8f0a3ef64d388e763f92dc91dcaafb18185e9958a` |

No raw namespace was created. The command is deterministic over the retained
checkout, the pinned Git object, and the immutable overlay record, and emits
the complete machine-readable result to standard output.
