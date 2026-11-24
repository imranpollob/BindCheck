# Hunt leads (not investigated; not part of B2)

- **porco-rosso-j/safe-recovery-noir** @ `3740261eb5e343ea54830b772d8fc5b38af4207b` (Safe grant project, 11 stars). Dropped as a B2 host because its baseline is not clean for P1.
- `src/RecoveryPluginNoir.sol`: `proposeSecretRecover` (and apparently `proposeEcrecoverRecover`) build `publicInputs` only from the stored `hashed_secret` / the caller-supplied `_message`. `_oldAddresses`, `_newAddresses` and `_newThreshold` are never part of the proved statement, so whoever holds or observes a valid proof can propose any owner replacement.
- Replay protection is `keccak256(_proof)`, which binds the proof bytes and not the statement. Seen from a read-through only; unverified, no proof was built.
