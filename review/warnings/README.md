# Blind warning adjudication (16 DEV warning groups)

Each `Wnn.md` card shows one retained DEV warning group: the repository at its pinned commit, the reported
location, the rule's stated property, the code at that location, and the verifier(s) the consumer was matched to.
Cards are in a seeded random order. They omit the tool's verdict, confidence, instance counts, the author's
label and the author's reason.

Procedure (from `eval/ADJUDICATION.md`):

1. Each rater receives only their own copy: `BLIND-SHEET-rater-a.csv` or `BLIND-SHEET-rater-b.csv`.
2. Fill `label` with exactly `TP`, `FP`, or `unclear`, and `rater_reason` with one line. Do not change `warning_id`.
3. Do not exchange labels before both sheets are sealed.
4. Then: `python3 eval/adjudicate.py kappa rater-a.csv rater-b.csv --output agreement.json`.

The un-blinding key is `reports/groundtruth/warning-blind-key.csv`; do not open it before sealing.

## Rule texts

- **UNBOUND_EFFECT_AMOUNT** — P1 effect binding (amount): at least one protected effect role is attacker-selectable independently of the recovered verifier public vector.
- **UNBOUND_EFFECT_RECIPIENT** — P1 effect binding (recipient): at least one protected effect role is attacker-selectable independently of the recovered verifier public vector.
- **REPLAY_KEY_NOT_BOUND_TO_PROOF** — P3 replay key: the consumed replay key is caller-controlled but no supported binding to the verifier public inputs was recovered.
- **FIELD_ALIAS_REPLAY_KEY** — P3 canonicality: the verifier accepts field representatives while Solidity keys replay state by an unguarded raw integer.
- **PUBLIC_INPUT_CANONICALITY_GUARD_NOT_FOUND** — P4 verifier invariant: no supported canonical public-input field guard (input < r) was recovered in this verifier.
- **DUPLICATE_IC_SOURCE_WARNING** — P4 verifier invariant: two or more parsed IC (verification-key input-commitment) entries are identical.

## Cards

- [W01](W01.md) — `KanishJebaMathewM/Truxify` `blockchain/contracts/ZKIdentity.sol:117`
- [W02](W02.md) — `Nitya-003/CropChain` `smart-contracts/contracts/CropChain.sol:865`
- [W03](W03.md) — `Chidubemkingsley/Shadow-Credit-Network` `shadow-credit-network/contracts/CreditDataWithZK.sol:146`
- [W04](W04.md) — `SovereignWave/qwer` `privatecrypmix/packages/contracts/contracts/PrivateCrypMix.sol:200`
- [W05](W05.md) — `KELLERBABG/Planetary-Entropy-Mining` `contracts/src/Verifier.sol:1`
- [W06](W06.md) — `SovereignWave/qwer` `privatecrypmix/packages/contracts/contracts/Verifier.sol:1`
- [W07](W07.md) — `Servesh21/RacePass` `contracts/verifiers/ReputationVerifier.sol:1`
- [W08](W08.md) — `SovereignWave/qwer` `privatecrypmix/packages/contracts/contracts/Verifier.sol:1`
- [W09](W09.md) — `sambitsargam/ShadowSats` `contract/DarkPool.sol:128`
- [W10](W10.md) — `RippnerLabs/meridian-link` `evm-bridge/contracts/evm-bridge.sol:114`
- [W11](W11.md) — `Servesh21/RacePass` `contracts/passes/EventPass.sol:127`
- [W12](W12.md) — `KanishJebaMathewM/Truxify` `blockchain/contracts/ZKPrivacy.sol:79`
- [W13](W13.md) — `partik03/aieth` `hardhat/contracts/Verifier.sol:1`
- [W14](W14.md) — `ethpanda-org/ETHShanghai-2025` `projects/ZKredential/packages/zk-contracts/contracts/core/ComplianceGateway.sol:130`
- [W15](W15.md) — `KanishJebaMathewM/Truxify` `blockchain/contracts/ZKPrivacy.sol:180`
- [W16](W16.md) — `SovereignWave/qwer` `privatecrypmix/packages/contracts/contracts/PrivateCrypMix.sol:136`
