# Rater guide: auditor-reported binding findings

Read this once before your first item (about 30 minutes) and keep it open while you label.

**The rules that make these labels count:**

- **No AI, no discussion.** Do not use an AI assistant for any item. Do not discuss items or labels with the other rater until both sheets are sealed (README, step 4).
- **Judge from the source.** Open `report_url`, find the finding (`finding_id` / `where_in_report`), and read its description and impact. `auditor_quote` is a verbatim excerpt to help you find it. It is not the whole finding.
- **The sheet is blind on purpose.** It does not show how the item was selected or what anyone else thought of it. Do not try to find out.

---

## 1. What "binding" means

A ZK application has three parts:

1. a **circuit**, which defines what a proof establishes;
2. a **verifier**, which checks the proof against its public inputs;
3. a **consumer**: the contract (or code) that acts once the proof is accepted. It pays, mints, records, marks spent, updates a state root, or grants access.

A proof only vouches for its **public inputs** and for whatever the circuit constrains them to mean. Every other value the consumer uses is chosen freely by whoever sends the transaction: function arguments, `msg.sender`, `msg.value`, stored configuration. Valid proofs are also public in the mempool, so anyone can copy one and resubmit it with different arguments.

A finding is a **binding flaw** when all three of these hold:

| | Criterion | Ask yourself |
|---|---|---|
| **C1** | A proof is accepted, or a verifier accepts what it should reject. | Does the issue happen on or after proof acceptance? |
| **C2** | A consumer commits an effect. | Does something actually happen: a transfer, mint, state write, access grant? |
| **C3** | A value that decides **who, how much, what, which policy, which state, or how often** is **not fixed by the proved statement**. | Could an attacker change that value while keeping the proof valid? |

**Front-running counts.** If a third party can resubmit an observed valid proof so that the effect goes to them, or changes in their favour (recipient, refund, fee, slippage), that is binding. It is not an "ordering" bug.

## 2. Patterns

| Code | Pattern | Typical shape |
|---|---|---|
| **P1** | Unbound effect | Recipient, amount, refund, fee, identity or stored value is caller-chosen, not a public input or hash-committed |
| **P2** | Context binding | Caller, chain ID, contract address, config or policy ID, or domain is not bound, so a proof works in a context it was not made for |
| **P3** | Replay | Nullifier or replay key not bound to the proof, aliasable through the field (`x` and `x + r`), or no replay protection at all |
| **P4** | Verifier invariants (integration level) | The deployed verifier or its configuration is wrong: missing public-input range checks, constant-true result, unchecked pairing result, forgeable key (γ = δ), vk or program ID not pinned in the consumer, misrouting gateway |
| **P5** | Interface mismatch | The consumer passes public inputs in a different count, order, endianness or encoding than the circuit expects |
| **OTHER** | Binding, but none of the above | Explain in `notes` (example: the extent/prefix case below) |
| **NA** | Not binding | — |

### Worked examples (none of these is an item in your sheet)

- **P1, ZKredential (our own finding).** The gateway mints to a caller-supplied recipient. The proof's public `walletAddress` is checked by the registry but not by the gateway, and the replay key covers the proof, not the caller. Anyone who submits an unused proof first receives the mint. C1 met, C2 met (mint), C3 met (recipient not fixed).
- **P1/P3, RacePass (our own finding).** The contract stores and revocation-checks a caller-supplied `credHash` that is never tied to the KYC proof's `credentialHash`. The effect is acted on for an unproven credential.
- **OTHER (extent), Payy message tail.** The circuit leaves the tail of a 1000-word public array unconstrained, while the consumer parses the whole array. The prover controls values the consumer acts on.
- **P4, synthetic.** `verifyProof` computes the pairing but returns `true` regardless of the result. Every proof is accepted, so every effect is unauthorized.
- **P5, synthetic.** The circuit outputs `[state, pinCode]`, but the contract reads index 0 as `pinCode`. The consumer acts on swapped identity attributes.
- **P3, synthetic.** The contract marks `spent[nullifier]` using the raw uint, while the verifier reduces inputs mod r. Then `nullifier + r` passes as a fresh nullifier.

## 3. What is NOT binding (label `binding = N`)

- **Reentrancy or ordering** when every value the effect uses *is* fixed by the proof. (Front-running that redirects an effect is binding; see §1.)
- **Liveness or denial of service only**: a user's own bad input blocks their own claim, or the system halts. Exception: one party's valid proof consuming or blocking *another* party's state (e.g. marking a victim's nullifier spent) **is** binding.
- **Admin or owner trust**: "a compromised owner can drain", "no timelock", "owner can set any verifier". The proof is not the problem. (Note it if you disagree.)
- **Gas, memory, events, code quality.**
- **Circuit-internal under-constraint** with no effect on what the consumer is told or acts on.
- **Off-chain prover or client bugs** that cannot make the on-chain verifier accept a wrong statement.
- **Trusted-setup ceremony issues.**

## 4. Proof-system soundness (the `proof_system_soundness` column, every item)

Answer **Y** if the finding is a soundness bug **inside the proof system or a recursion/aggregation verifier**: Fiat–Shamir transcript flaws, missing curve or subgroup checks inside a recursion circuit, STARK/FRI parameter bugs, or a zkVM chip constraint letting the prover forge a proof of a wrong execution. Answer **N** if it concerns how an application integrates with a (sound) proof system.

Label `binding` **independently** of this column: say whether, under §1, it binds an effect. The author will decide later whether proof-system-soundness items belong in the core class. Your answers on both columns let that decision be made without relabeling.

## 5. What to fill in, by tier

| Column | FULL | LIGHT | PSS | Values |
|---|---|---|---|---|
| `binding` | ✔ | ✔ | ✔ | `Y` / `N` / `U` (U = the report text cannot settle it) |
| `proof_system_soundness` | ✔ | ✔ | ✔ | `Y` / `N` |
| `pattern` | ✔ | ✔ | ✔ | `P1`–`P5` / `OTHER` / `NA` (use NA when binding = N) |
| `c1_proof_accepted`, `c2_effect_committed`, `c3_value_not_fixed` | ✔ | optional | optional | `met` / `fails` / `unclear` |
| `effect` | ✔ | – | – | Short phrase: what the consumer does (e.g. "mints tokens to recipient") |
| `unbound_value` | ✔ | – | – | Which value is not fixed (e.g. "recipient address") |
| `intended_policy` | ✔ | – | – | What the application *should* allow, in one sentence, with where you got it (report, README, code comments) |
| `confidence` | ✔ | ✔ | ✔ | `H` / `M` / `L` |
| `minutes` | ✔ | ✔ | ✔ | Rough time spent |
| `notes` | as needed | as needed | as needed | Free text. Required for OTHER, U, or any disagreement with §3. |

**Time targets:** FULL about 10 minutes, LIGHT about 3, PSS 1–2. If an item takes more than twice its target, give your best label with `confidence = L` and move on.

**FULL items** also show `repo`, `vuln_commit` and `fix_commit`. You may use the repo **README and the report** to state `intended_policy`. **Do not read the project's source code or diffs.** Some of these items will become a reserved test set that must stay unstudied until the tool is frozen.

## 6. Hard cases

- **The auditor says "low impact" or "informational", but the mechanism is binding.** Label by mechanism (`binding = Y`) and put the severity mismatch in `notes`.
- **The effect happens on another chain or off-chain**, e.g. a Mina contract or an off-chain indexer. C2 is `met` only if a consumer commits the effect. The audited consumer need not be EVM for your label; say where it is in `notes`.
- **Attested verification** (Aligned, AVS): an operator network verifies the proof and the EVM contract acts on its signature. Treat the attestation as "proof accepted" (C1).
- **Signature instead of proof.** If the issue is purely an ECDSA/EIP-712 signature with no ZK proof involved, C1 `fails`, so `binding = N`, unless the signature is checked *inside* the circuit or bound to the proof's statement.
- **Several issues in one finding.** Label the main mechanism and mention the rest in `notes`.
- **The report is unavailable or the link is dead.** Set `binding = U` and `notes = "source unavailable"`. Do not search for other sources.
