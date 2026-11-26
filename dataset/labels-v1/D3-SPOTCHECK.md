# D3 spot-check sheet (15 items)

**For the author. AI-proposed tags, from report text only.** For each row, decide whether the tag is the *minimal set of artifacts* needed to decide the flaw, given the report's description. This is the D3-LAYERS.md §1 rule, with amendments A1 and A2. Fill in the last column with `agree`, or `disagree → <tag>`. Allow about 1 minute per row.

**Tags:**
- **CONTRACT-ONLY:** the flaw is visible from the consumer and its verify call site alone.
- **CIRCUIT-ONLY:** the consumer passes the value correctly, but the circuit or statement leaves it unconstrained.
- **BOTH:** the two sides must be compared.
- **VERIFIER/OFFCHAIN:** the flaw is in the verifier, proof system, zkVM/recursion stack, or an off-chain library or consumer.

The sample was drawn by seeded random sampling (seed 20261125) within each tag: 4 CONTRACT-ONLY, 4 CIRCUIT-ONLY, 3 BOTH and 4 VERIFIER/OFFCHAIN.

**Decision rule.** If you disagree with more than 2 of the 15, all 103 tags are redone under a revised rule (amendment A3).

**Seam to watch.** L050 (VERIFIER/OFFCHAIN, framework) and L091/L179 (CIRCUIT-ONLY, application guest) sit on the A1(a) line between "framework" and "application guest".

| ID | project | pattern | proposed tag | flaw summary | decisive evidence | author: agree / disagree + tag |
|---|---|---|---|---|---|---|
| L010 | Boundless marketplace | P1 | **CONTRACT-ONLY** (medium) | Market pays batch.prover, which the app proof does not cover; front-run redirect visible at the consumer | “(report-level quote non-descriptive; sweep mechanism) a fulfillment proof can be copied by a third party and rebound to a different request or prover payee” | |
| L088 | Singularity | P1 | **CONTRACT-ONLY** (medium) | Pool fee tier/relayer fee are caller arguments not fixed by the proof (front-run) | “Attackers front-running calls to uniswapLiquidityProvision can lower the Uniswap fee level for which liquidity will be provided” | |
| L123 | EZKL (halo2 + Solidity verifier + data attestation) | P4 | **CONTRACT-ONLY** (high) | Wrapper forwards caller-chosen calldata to the verifier via low-level call; any true-returning getter passes | “(report-level quote non-descriptive; sweep mechanism) DataAttestation contracts do not validate proof function signature” | |
| L173 | EZKL (halo2 + Solidity verifier + data attestation) | P4 | **CONTRACT-ONLY** (medium) | Single-variant attestation contract skips the KZG commitment check on model weights | “If a verifier fails to validate the initial segment of each proof against the predetermined KZG commitment, a malicious prover can use any values they like for the corresponding inputs, outputs, or parameters.” | |
| L023 | Succinct SP1 Blobstream (Celestia) | P1 | **CIRCUIT-ONLY** (high) | SP1 guest commits block heights from inputs without checking them against the verified headers | “However, these heights are not validated against the actual heights of the headers contained within the trusted_light_block and target_light_block .” | |
| L091 | Malda | P2 | **CIRCUIT-ONLY** (medium) | Guest balance_of.rs commits journal values without fixing which contract was queried | “(report-level quote non-descriptive; sweep mechanism) guest program commits arbitrary data to the journal, permitting spoofed mints” | |
| L164 | Singularity | P3 | **CIRCUIT-ONLY** (low) | Two input nullifiers not required to be distinct (layer not stated; thin evidence) | “it is not ensured that the two nullifiers that are invalidated are distinct.” | |
| L179 | Boundless (RISC Zero) | P2 | **CIRCUIT-ONLY** (medium) | L1 config hash in the guest omits fields that change derived L2 blocks | “(report-level quote non-descriptive; sweep mechanism) L1 config hash preimage incomplete so proof may be accepted under wrong config” | |
| L007 | Anon Aadhaar | P5 | **BOTH** (high) | Public-input order mismatch: circuit declares state,pinCode; contract assigns them swapped | “state and pinCode is declared in circuits in the following order: signal output state; signal output pinCode; However, smart contract and TS code assign pinCode to state and state to pinCode” | |
| L063 | Quantstamp report | P5 | **BOTH** (high) | Contract flattens tokenIds and nullifiers into one input array differently from the circuit layout | “it is possible to insert commitments without nullifying previous commitments. This is done by exploiting the construction of the input array to the Circom Verifiers. The duplicated commitments can later be withdrawn.” | |
| L172 | R0VM Helios (RISC Zero Ethereum light client) | P2 | **BOTH** (medium) | Genesis root/fork versions must be exposed in the journal and checked by the contract | “It is crucial for the light client to correctly identify the chain it is syncing to. Therefore, these two values must be exposed in the journal .” | |
| L050 | vlayer | P2 | **VERIFIER/OFFCHAIN** (medium) | vlayer framework does not expose chain ID/ChainSpec in CallAssumptions (prover-side framework) | “Importantly, the exposed public data must include enough information for a user to validate the correctness of the initial execution environment as some of vLayer’s correctness guarantees rely on the initial execution environme…” | |
| L124 | Data Ownership Protocol (DOP) | P3 | **VERIFIER/OFFCHAIN** (medium) | Nullifiers exposed by the selective-transparency proof are not checked by the off-chain consumer (amendment A1-c) | “(report-level quote non-descriptive; sweep mechanism) nullifiers not checked in selective-transparency path” | |
| L226 | Brevis | P4 | **VERIFIER/OFFCHAIN** (high) | Verifying-key hash omits attacker-changeable fields | “An attacker, given a verifying key for a circuit and public inputs for it, may, without being able to find witnesses that satisfy the constraint system for that circuit, be able to change the above fields” | |
| L240 | nebra | P4 | **VERIFIER/OFFCHAIN** (high) | Proofs not hashed into the batch challenge | “it is possible to craft invalid proofs that are accepted for one particular challenge and public inputs.” | |
