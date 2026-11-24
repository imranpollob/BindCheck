# B2 hosts

Three hosts, none in a LABELS-v1 family, none FORBIDDEN by `scripts/check_holdout.py` (run 2026-11-24, all `ALLOWED`). All three are excluded from the hunt pool from this point on. Hosts were chosen from the spent-family ledger (`reports/S2a/revision1/spent-family-ledger-278.csv`) where possible.

| Host | Repo @ pinned commit | Layers | Fixed in clean host | Stars | Ledger / corpus |
|---|---|---|---|---|---|
| `redpacket` | `michaelliao/red-packet-contract` @ `9c100cd65ed3f41b3f5c9e10e4a5336ae58db4b8` | Circom/Groth16 (`passcode.circom`), snarkjs `Verifier.sol`, `RedPacket.sol` (ETH/ERC-20 payout) | claimer address is a public input; payout to `msg.sender`; once-per-address key | 38 | spent ledger #12, `verified-deployed`, family `v2-family:20b51f548f42649f064b`, not a fork |
| `privacyvaults` | `0xbri3t/Privacy-Vaults` @ `d3735bff5c69f43f8bb6dec31a2e4465336f1f7b` | Noir (nargo beta.14, `poseidon` v0.1.1) + bb UltraHonk `Verifier.sol`/`BorrowVerifier.sol`, `PrivacyVault.sol` (USDC withdraw and borrow) | recipient, root, nullifier, yield index in the statement; root and nullifier checked in the consumer | 0 | spent ledger #107, `audited-production`, family `v2-family:be902a67abd22d46e60b`, not a fork |
| `orc` | `felduque/orc-zktls-oracle` @ `87c1956a7a5606ba51c8c3270b61d45346b64f8a` | SP1 guest (not mutated; no SP1 toolchain), Foundry consumer `OrcClaim.sol` | sender, chain, campaign, repo, notary, snapshot bound by consumer checks; nullifier set | 0 | not in `source-corpus-v2.csv` (new repo, not a fork) |

Family check: the 26 repositories named in `LABELS-v1.csv` map to 13 `v2_family_id`s in `source-corpus-v2.csv`; neither `redpacket` nor `privacyvaults` is in that set, and the `family` column names do not match any host. `orc` is absent from the corpus altogether.

## Limits you should know about
- **`orc` is a proof of concept** (0 stars, README says unaudited, testnet only). It is the zkVM fallback: no real SP1/RISC Zero application with a token effect built here. Its effect is a nullifier write plus an event (a state write, so C2 holds), and its honest path runs on `SP1MockVerifier`. Mutants are consumer-side only; guest-side mutants would need the SP1 toolchain.
- **`privacyvaults` and `redpacket`**: the host tests need `node`/`bb` (ffi) or real proofs and could not run, so their honest paths were compile-checked only. Circuit mutants (`*-C*`) leave the committed verifier unchanged; they are circuit-layer targets, not end-to-end exploitable as built.
- **Clean hosts may contain flaws of their own.** The unmutated baselines were not audited for binding flaws. The delta rule in `MATCHING.md` subtracts tool output on the clean host, but a real baseline flaw would make a clean-variant "negative" unreliable. A read-through noted that `PrivacyVault.borrow` takes `_borrowAmount` unproved (bounded only by an on-chain LTV check): treat that as policy, not a labelled flaw.
- Rejected candidates: `porco-rosso-j/safe-recovery-noir` (baseline already unbound for proposal owners, see `HUNT-LEADS.md`); `charonAMM/charonAMM` (Tornado Nova lineage); `partylikeits1983/proof-of-time` (Noir 0.36-era syntax does not build with available nargo); `z0r0z/tacit` (FORBIDDEN).
