# BindCheck-ZK development controls

`expected.json` is the frozen oracle for analyzer development. It contains the
24 previously frozen Track B outcomes plus 44 new P1–P5 controls. Analyzer code
must not read this file outside the test runner, and the oracle must not be
packaged as runtime configuration.

Positive source/runtime P4 signals remain `UNKNOWN` at E1, consistent with the
research contract; clean P4 controls verify only the narrow parsed-key or
runtime-signature property. P2 absence also remains `UNKNOWN` without a
protocol policy that requires a particular domain binding.
