# D1P-21B prototype

`joint_variant.py` is a prospective wrapper around the preserved D1P-20
adapter. It accepts extractor-validated terminal-path shapes instead of a
fixed 22/19/3 shape, serializes every extracted family, and binds the
source-extracted `aztecWarptoadAddress` and `block.chainid` reads to the
admitted Omega state/environment.

`validate_d1p21b.py` performs only fixed archived-execution, deterministic
control, fixed-input polarity, and parse-only checks. It launches no primary
solver search. `test_d1p21b.py` contains the focused regressions.
