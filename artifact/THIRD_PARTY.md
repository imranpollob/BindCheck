# Third-party and release boundary

Status: **PARTIAL_DEVELOPMENT_ARTIFACT / FINAL_ARTIFACT_BLOCKED**

This directory does not redistribute tool binaries, upstream source trees,
dependency trees, proof material, or a retained raw-evidence sidecar. The
development workspace used the following pinned public inputs:

| Input | Pin or version | Recorded SHA-256 / identity | Current disposition |
| --- | --- | --- | --- |
| WarpToad | `973e7d1e4b60d0d8a8ca299b0cabd9193b147ef8` | source hashes in the D2-01 seal | Manifest reference only |
| Payy earlier | `c4d2c9021b8fb9988816eb6987a734b830bfce15` | exact source/artifact hashes in `d2-01-external-inputs-v1.json` | Manifest reference only |
| Payy check-added | `dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36` | exact source/artifact hashes in `d2-01-external-inputs-v1.json` | Manifest reference only |
| Nargo | `1.0.0-beta.22` | `37f7d55d9795af0da3b471db2306e0296fa34c528386a828ce556fc3ebbf6e7b` | Not redistributed |
| solc | `0.8.29+commit.ab55807c` | `66fabdd17c8c0091311997ec7d17b4d92e1b7b2c2d213dc14e4ff28c3de864d1` | Not redistributed |
| Foundry Forge | `1.8.6`, commit `6bad0a66de7c83f7b33695044138f0f5fa4c5990` | `f63f468bdeb5ea66b0379722657ddfacdd0141f1fab80fe542da345eb2961f07` | Not redistributed |
| forge-std / Solidity dependencies | hashes in the Step 6B protocol and input manifest | tree/file hashes retained locally | Not redistributed |

The existing `scripts/artifact/fetch_inputs.py` is a historical D1 workflow.
It performs network downloads, Git fetches and npm installation; is
Darwin/arm64-specific; embeds archived local provenance paths; and reproduces
older D1 tables. It is not invoked by this artifact and must not be described
as the D2 reproduction route.

Before any public release, a human must review upstream licenses, binary
redistribution terms, source attribution, privacy of retained absolute paths,
responsible-disclosure constraints, and the venue's anonymity requirements.
No such review is claimed here.

