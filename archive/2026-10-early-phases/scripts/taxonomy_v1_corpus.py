#!/usr/bin/env python3
"""Build docs/taxonomy/v1-corpus-ledger.json (lane-x, seed endpoints only).

Reads nothing except the pinned 0xPARC zk-bug-tracker snapshot text supplied
via --tracker-readme (local path, recorded by sha256). All mechanism labels
are AI-SUGGESTED (fact status ASSUMED) for the human annotator; never final.
Run: python3 scripts/taxonomy_v1_corpus.py --tracker-readme PATH --tracker-sha256 HEX --out docs/taxonomy/v1-corpus-ledger.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PIN = "56a996672fb50486279126c8e12530f2bf933d0b"
TRACKER_URI = "https://github.com/0xPARC/zk-bug-tracker.git"
NOW = "2026-10-28T00:00:00Z"
ACTOR = "lane-x-muse"
PLAN_RULE = "planning_agents_must_not_open_or_read_findings_report_bodies_or_bug_descriptions"

# Deviation note: tonight's task explicitly directs extraction from the two
# seed endpoints, which requires reading the seed listing bodies. The frozen
# plan's agent_access_rule is metadata-only; the custodian-sanitized flow is
# still owed before any annotation round. Recorded here and in v1-corpus.md.


def ev(anchor: str) -> dict:
    return {"source_id": "src-0xparc-tracker", "location": anchor,
            "revision": PIN, "sha256": None,
            "pin_gap": "README bytes not hashed; git revision pin only"}


def stage(status: str, rationale: str, evidence: list) -> dict:
    base = {"status": status, "decided_at": NOW if status != "not_attempted" else None,
            "actor_id": ACTOR if status != "not_attempted" else None,
            "reason_codes": ["AI_SEED_SCREEN"] if status != "not_attempted" else [],
            "rationale": rationale if status != "not_attempted" else None,
            "evidence": evidence, "missing_prerequisites": []}
    return base


def funnel() -> dict:
    na = {"status": "not_attempted", "decided_at": None, "actor_id": None,
          "reason_codes": [], "rationale": None, "evidence": [],
          "missing_prerequisites": ["tool-feasibility review after reservation"]}
    return {"artifacts_available": dict(na), "supported": dict(na),
            "analyzed": dict(na), "validated": dict(na)}


def ai_label(fid: str, code: str, locus: str, why: str, anchor: str) -> dict:
    return {"id": f"{fid}-ai-label",
            "claim": f"AI-SUGGESTED mechanism {code}; failure locus: {locus}. {why}",
            "status": "ASSUMED", "evidence": [ev(anchor)],
            "preconditions": ["independent human annotation"],
            "limitations": ["AI suggestion only; never a final label, rater vote, or tie-break"]}


def finding(fid: str, title: str, fam: str, app: str, anchor: str, one_line: str,
            decision: str, rationale: str, label: tuple | None,
            boundary: dict) -> dict:
    fams = [fam] if fam else []
    apps = [app] if app else []
    facts = [ai_label(fid, label[0], label[1], label[2], anchor)] if label else []
    gaps = list(boundary.get("gaps", []))
    if decision == "include":
        gaps = gaps + ["exact disclosure date unresolved; upper-bounded by tracker snapshot commit 2024-12-18, inside the publication window"]
    rel = {"screened": stage("met", f"Seed screen of tracker section {anchor} by {ACTOR}.", [ev(anchor)]),
           "relevant": stage("met" if decision == "include" else "not_met", rationale, [ev(anchor)])}
    return {
        "id": fid, "title": title, "family_ids": fams, "application_ids": apps,
        "source_ids": ["src-0xparc-tracker"], "disclosed_on": None,
        "date_status": "in_window" if decision == "include" else "unresolved",
        "duplicate_of": None, "duplicate_status": "unreviewed", "duplicate_rationale": None,
        "duplicate_evidence": [], "manifestations": [], "related_variant_ids": [],
        "boundary": {"accepted_relation": boundary.get("rel"),
                     "program_key_configuration": boundary.get("key"),
                     "public_statement": boundary.get("stmt"),
                     "decoder_consumer_interpretation": boundary.get("interp"),
                     "independent_policy": boundary.get("policy"),
                     "protected_effect_or_obligation": boundary.get("effect"),
                     "mismatch_argument": boundary.get("arg"),
                     "feasibility_and_gaps": gaps,
                     "evidence": [ev(anchor)]},
        "relevance": {"decision": decision, "reason_codes": ["AI_SEED_SCREEN"],
                      "rationale": rationale, "actor_id": ACTOR, "decided_at": NOW,
                      "evidence": [ev(anchor)]},
        "artifacts": [], "facts": facts,
        "capability_review": {"status": "unassessed", "reviewer_actor_id": None,
                              "reviewed_at": None, "fragment_version": None,
                              "policy_version": None, "bounds": [], "assumptions": [],
                              "unsupported_features": [], "evidence": []},
        "attempts": [], "evidence_claims": [], "result": None,
        "annotation_round_ids": [], "discovery_routes": ["seed_0xparc"],
        "disclosure_assessment": rel, "tool_funnel": funnel(),
        "_x_one_line": one_line, "_x_anchor": anchor,
    }


ENTRIES: list = []

# (fid, title, family-id, family-name, app-id, app-name, repo-uri, producer, consumer, anchor)
APPS = [
    ("F-dark-forest", "Dark Forest", "A-dark-forest", "Dark Forest v0.3 circuits",
     "https://github.com/darkforest-eth/circuits", ["circom"], ["Solidity"], "dark-forest-1"),
    ("F-circom-ecdsa", "circom-ecdsa BigInt", "A-circom-ecdsa", "circom-ecdsa bigint.circom",
     "https://github.com/0xPARC/circom-ecdsa", ["circom"], [], "bigint-1"),
    ("F-circom-pairing", "circom-pairing / Succinct bridge", "A-circom-pairing", "circom-pairing CoreVerifyPubkeyG1",
     "https://github.com/yi-sun/circom-pairing", ["circom"], ["bridge protocol"], "circom-pairing-1"),
    ("F-semaphore", "Semaphore", "A-semaphore", "Semaphore contracts",
     "https://github.com/semaphore-protocol/semaphore", ["circom"], ["Solidity"], "semaphore-1"),
    ("F-zk-kit", "zk-kit IMT", "A-zk-kit", "zk-kit IncrementalBinaryTree",
     "https://github.com/privacy-scaling-explorations/zk-kit", [], ["Solidity"], "zk-kit-1"),
    ("F-aztec", "Aztec 2.0 notes", "A-aztec", "Aztec 2.0 note circuits",
     "https://github.com/AztecProtocol/aztec-packages", ["circom"], ["Solidity"], "aztec-1"),
    ("F-aztec-verifier", "Aztec Plonk verifier", "A-aztec-verifier", "Aztec Plonk verifier (C++)",
     "https://github.com/AztecProtocol/barretenberg", ["plonk"], ["C++ verifier"], "aztec-2"),
    ("F-stealthdrop", "0xPARC StealthDrop", "A-stealthdrop", "StealthDrop claim circuits",
     "https://github.com/0xPARC/stealthdrop", ["circom"], ["Solidity"], "stealthdrop-1"),
    ("F-zkdrops", "a16z ZkDrops", "A-zkdrops", "ZkDrops contracts",
     "https://github.com/a16z/zkdrops", ["circom"], ["Solidity"], "zkdrops-1"),
    ("F-maci", "MACI", "A-maci", "MACI 1.0 ProcessMessages",
     "https://github.com/privacy-scaling-explorations/maci", ["circom"], ["Solidity"], "maci-1"),
    ("F-bulletproofs", "Bulletproofs protocol", "A-bulletproofs", "Bulletproofs paper Fiat-Shamir",
     "urn:unresolved:paper-protocol-no-application", ["bulletproofs"], [], "bulletproofs-1"),
    ("F-plonk", "Plonk implementations", "A-plonk", "affected Plonk implementations",
     "urn:unresolved:multiple-implementations", ["plonk"], [], "plonk-1"),
    ("F-zcash", "Zcash Sprout setup", "A-zcash", "Zcash modified-Pinocchio setup",
     "https://github.com/zcash/zcash", ["pinocchio"], [], "zcash-1"),
    ("F-circomlib", "circomlib MiMC / Tornado Cash", "A-tornado-cash", "Tornado Cash via circomlib MiMC",
     "https://github.com/tornadocash/tornado-core", ["circom"], ["Solidity"], "mimc-1"),
    ("F-scroll-zkevm", "PSE-Scroll zkEVM", "A-scroll-zkevm", "zkevm-circuits gadgets",
     "https://github.com/privacy-scaling-explorations/zkevm-circuits", ["halo2"], ["L1 rollup"], "pse-zkevm-1"),
    ("F-dusk", "Dusk Plonk", "A-dusk", "Dusk Plonk implementation",
     "https://github.com/dusk-network/plonk", ["plonk"], [], "dusk-1"),
    ("F-nightfall", "EY Nightfall", "A-nightfall", "Nightfall nullifier handling",
     "https://github.com/EYBlockchain/nightfall", ["zokrates"], ["Solidity"], "nightfall-1"),
    ("F-summa", "Summa solvency", "A-summa", "summa-solvency LessThan gate",
     "https://github.com/summa-dev/summa-solvency", ["halo2"], ["solvency verifier"], "summa-1"),
    ("F-polygon-zkevm", "Polygon zkEVM", "A-polygon-zkevm", "Polygon zkEVM ROM/PIL",
     "https://github.com/0xPolygonHermez/zkevm-proverjs", ["zkasm/pil"], ["L1 rollup"], "polygon-zkevm-1"),
    ("F-zendoo", "Zendoo ginger-lib", "A-zendoo", "ginger-lib dense polynomials",
     "https://github.com/HorizenOfficial/ginger-lib", ["rust-backend"], [], "zendoo-polynomial-1"),
    ("F-snarkvm", "Aleo snarkVM", "A-aleo", "snarkVM InputID::Private",
     "https://github.com/AleoHQ/snarkVM", ["aleo"], ["network verifier"], "aleo-encryption-1"),
    ("F-light-protocol", "Light Protocol v1", "A-light-protocol", "light-protocol-v1 Merkle processor",
     "https://github.com/Lightprotocol/light-protocol-v1", ["groth16"], ["Solana"], "light-protocol-1"),
    ("F-zkemail", "ZK Email", "A-zkemail", "zk-regex EmailAuth circuit",
     "https://github.com/zkemail/zk-regex", ["circom"], ["Solidity"], "zkemail-1"),
]


def build_findings() -> list:
    out = []

    out.append(finding(
        "CF-01", "Dark Forest v0.3 RangeProof bit-length", "F-dark-forest", "A-dark-forest",
        "dark-forest-1", "RangeProof accepted out-of-range moves: LessThan inputs never bit-constrained.",
        "include", "Game contract consumes RangeProof outcomes to authorize moves; the accepted relation admits out-of-range inputs the consumer treats as in-range.",
        ("C_REPRESENTATION", "circuit",
         "LessThan bit-width precondition unconstrained; fix constrains both inputs to bits."),
        {"rel": "RangeProof over (in, max_abs_value) via circomlib LessThan without input bit constraints.",
         "key": None, "stmt": "claimed in-range move coordinates.",
         "interp": "Game contract treats an accepted RangeProof as authorization for the move.",
         "policy": "Unreviewed game-move policy; recorded as gap, not asserted.",
         "effect": "Unauthorized in-game move/state effect.",
         "arg": "Accepted proofs exist for out-of-range inputs; consumer cannot distinguish them.",
         "gaps": ["no independent policy review", "fix commit not opened"]}))
    out.append(finding(
        "CF-02", "circom-ecdsa BigMod remainder bit-length", "F-circom-ecdsa", "A-circom-ecdsa",
        "bigint-1", "BigMod remainder unconstrained to n bits: library-level circuit gap, no evidenced consumer.",
        "exclude", "Pure circuit-library gap: the entry names no consuming system whose interpretation of an accepted proof disagrees with the relation. Per protocol s2, pure circuit bugs are excluded absent that disagreement.",
        None,
        {"rel": "BigMod quotient/remainder without remainder range check.", "key": None,
         "stmt": None, "interp": None, "policy": None, "effect": None,
         "arg": "Excluded: no evidenced proof-consuming interpretation in the entry; consumer harm is hypothetical.",
         "gaps": ["no consuming system evidenced", "fix PR not opened"]}))
    out.append(finding(
        "CF-03", "circom-pairing unchecked BigLessThan outputs", "F-circom-pairing", "A-circom-pairing",
        "circom-pairing-1", "Range-check outputs computed but never constrained: out-of-range pubkeys verify.",
        "include", "Bridge protocol depends on pubkey range admission; the accepted relation admits pubkey>=q which the protocol treats as admitted.",
        ("C_RELATION_GAP", "circuit",
         "Comparison outputs unconstrained; fix constrains each output to 1."),
        {"rel": "CoreVerifyPubkeyG1 with unconstrained BigLessThan outputs.",
         "key": None, "stmt": "admitted BLS pubkey limbs.",
         "interp": "Bridge protocol treats accepted proofs as well-formed-key operations.",
         "policy": "Unreviewed bridge admission policy; recorded as gap.",
         "effect": "Operations on malformed keys accepted as authorized.",
         "arg": "Proofs with pubkey>=q verify; consumer admits them.",
         "gaps": ["no independent policy review", "fix commit not opened"]}))
    out.append(finding(
        "CF-04", "Semaphore group-id field check missing", "F-semaphore", "A-semaphore",
        "semaphore-1", "Consumer accepted uint256 group ids the field-bound verifier always rejects: availability break.",
        "include", "Verifier contract (consumer side of the proof boundary) and group-creation admission disagree on admissible public inputs: EVM uint256 vs snark scalar field.",
        ("C_REPRESENTATION", "consumer",
         "Canonicality/range admission missing at group creation; fix requires groupId < SNARK_SCALAR_FIELD."),
        {"rel": "Semaphore membership proofs over group id; verifier requires inputs < scalar field.",
         "key": None, "stmt": "group id as public input.",
         "interp": "Group creation treats any uint256 id as a usable group; verifier rejects ids >= field order.",
         "policy": "Unreviewed group-lifecycle policy; recorded as gap.",
         "effect": "Inoperable group (omitted required usability obligation).",
         "arg": "Admitted state (created group) and accepted-statement domain disagree; no proof can ever verify for it.",
         "gaps": ["availability-side finding; no unauthorized effect", "issue/PR not opened"]}))
    out.append(finding(
        "CF-05", "zk-kit IMT zero-leaf field check missing", "F-zk-kit", "A-zk-kit",
        "zk-kit-1", "Tree init admitted above-field zero leaves that later inclusion proofs cannot use.",
        "include", "On-chain tree (consumer state) admits values outside the proof field; Semaphore inclusion proofs over them overflow. Same representation class as CF-04.",
        ("C_REPRESENTATION", "consumer",
         "Zero-leaf admission missing range check; fix requires zero < SNARK_SCALAR_FIELD."),
        {"rel": "Merkle inclusion proofs over tree leaves; leaves must be < scalar field.",
         "key": None, "stmt": "leaf/root values consumed by proofs.",
         "interp": "Tree init treats any uint256 zero leaf as valid tree state.",
         "policy": "Unreviewed tree-init policy; recorded as gap.",
         "effect": "Unusable tree roots; later proofs overflow.",
         "arg": "Admitted consumer state disagrees with the proof field domain.",
         "gaps": ["issue/PR not opened"]}))
    out.append(finding(
        "CF-06", "Aztec 2.0 nondeterministic nullifier (index width)", "F-aztec", "A-aztec",
        "aztec-1", "Unconstrained 32-bit index assumption let one note mint many nullifiers: double spend.",
        "include", "On-chain nullifier set is the consumer single-use accounting; the accepted relation admits many nullifiers per note, which the consumer treats as distinct spends.",
        ("C_OCCURRENCE_ACCOUNTING", "boundary",
         "Nullifier multiplicity lost via missing bit-length check on the note index."),
        {"rel": "Note-spend proofs with nullifier derived from a 32-bit-assumed index.",
         "key": None, "stmt": "spend authorization plus nullifier.",
         "interp": "Rollup contract treats each unseen nullifier as a fresh authorized spend.",
         "policy": "Unreviewed spend policy; recorded as gap.",
         "effect": "Repeated spends of one note (duplicate).",
         "arg": "Relation admits index values whose low 32 bits collide; consumer records distinct nullifiers.",
         "gaps": ["disclosure note not opened", "no independent policy review"]}))
    out.append(finding(
        "CF-07", "Aztec Plonk verifier zero-point acceptance", "F-aztec-verifier", "A-aztec-verifier",
        "aztec-2", "Verifier accepted forged proofs via inconsistent point-at-infinity handling.",
        "exclude", "Cryptographic verifier soundness break: out of scope per contract s5.4 (breaking the verifier). Not a proof-to-execution interpretation disagreement.",
        None,
        {"rel": "Plonk verifier equation checking with mishandled zero points.", "key": None,
         "stmt": None, "interp": None, "policy": None, "effect": None,
         "arg": "Excluded: verifier soundness failure, explicitly out of scope; no consumer-interpretation layer involved.",
         "gaps": ["finder PDF not opened"]}))
    out.append(finding(
        "CF-08", "StealthDrop nondeterministic ECDSA nullifier", "F-stealthdrop", "A-stealthdrop",
        "stealthdrop-1", "Signature-malleability gave many valid nullifiers per claim: repeated airdrop claims.",
        "include", "Claim contract's spent-nullifier set is the single-use accounting; the relation admits distinct nullifiers per claim, each treated as a fresh claim.",
        ("C_OCCURRENCE_ACCOUNTING", "boundary",
         "Nullifier derivation not deterministic in the claim; fix constrains signature generation with the private key in-circuit."),
        {"rel": "Claim proofs with nullifier = ECDSA signature over claim message.",
         "key": None, "stmt": "claim authorization plus nullifier.",
         "interp": "Airdrop contract treats each unseen nullifier as a fresh claim.",
         "policy": "Unreviewed claim policy; recorded as gap.",
         "effect": "Repeated claims (duplicate).",
         "arg": "Malleable signatures yield distinct valid nullifiers for one claim.",
         "gaps": ["announcement thread not opened"]}))
    out.append(finding(
        "CF-09", "ZkDrops nullifier field-overflow double claim", "F-zkdrops", "A-zkdrops",
        "zkdrops-1", "EVM/field width gap: x and x%p both accepted as fresh nullifiers.",
        "include", "Spent-nullifier mapping (consumer) disagrees with the circuit's reduced field view: two stored nullifiers, one checked value.",
        ("C_REPRESENTATION", "boundary",
         "Canonicality admission missing consumer-side; fix requires nullifier < SNARK_FIELD."),
        {"rel": "Claim proofs reducing nullifier modulo the scalar field.",
         "key": None, "stmt": "claim plus 256-bit nullifier.",
         "interp": "Contract stores 256-bit nullifiers and treats unseen ones as fresh.",
         "policy": "Unreviewed claim policy; recorded as gap.",
         "effect": "Double claim (duplicate).",
         "arg": "x and x%p are distinct on-chain but identical in-circuit.",
         "gaps": ["fix PR not opened"]}))
    out.append(finding(
        "CF-10", "MACI 1.0 vote-censorship via message mismatch", "F-maci", "A-maci",
        "maci-1", "Coordinator applied votes to wrong keys to mark them invalid: censored tally proved.",
        "include", "Tally contract treats the accepted result proof as a correct count; the relation admits tallies with targeted votes forced invalid.",
        ("C_ACTIVATION_EXTENT", "circuit",
         "Vote-to-key binding missing before invalid-marking; fix constrains leaf index to message stateIndex first."),
        {"rel": "ProcessMessages tally over coordinator-ordered leaves and messages.",
         "key": None, "stmt": "vote batch plus claimed tally.",
         "interp": "Tally consumer treats an accepted proof as the censorship-free count.",
         "policy": "Unreviewed tally-correctness policy; recorded as gap.",
         "effect": "Valid votes omitted from the committed tally (coverage).",
         "arg": "Relation admits censored tallies; consumer cannot distinguish them.",
         "gaps": ["issue not opened", "no independent policy review"]}))
    out.append(finding(
        "CF-11", "Bulletproofs Fiat-Shamir omission", "F-bulletproofs", "A-bulletproofs",
        "bulletproofs-1", "Paper's Fiat-Shamir omitted the commitment: forged range proofs.",
        "exclude", "Proof-protocol soundness guidance flaw; no proof-consuming application layer in the entry. Out of scope per contract s5.4 (proof-system soundness).",
        None,
        {"rel": "Bulletproofs non-interactive challenge derivation without commitment binding.", "key": None,
         "stmt": None, "interp": None, "policy": None, "effect": None,
         "arg": "Excluded: protocol-level forgery class, no consumer-interpretation disagreement evidenced.",
         "gaps": ["explainer not opened"]}))
    out.append(finding(
        "CF-12", "Plonk Fiat-Shamir public-input omissions", "F-plonk", "A-plonk",
        "plonk-1", "Implementations hashed too few public inputs: proof forgery to varying extent.",
        "exclude", "Proof-system implementation soundness; entry aggregates multiple implementations with no single consuming system. Out of scope per contract s5.4.",
        None,
        {"rel": "Plonk FS transcripts missing public inputs across implementations.", "key": None,
         "stmt": None, "interp": None, "policy": None, "effect": None,
         "arg": "Excluded: verifier-side soundness class, not a proof-to-execution boundary case.",
         "gaps": ["explainer not opened"]}))
    out.append(finding(
        "CF-13", "Zcash Sprout trusted-setup parameter leak", "F-zcash", "A-zcash",
        "zcash-1", "Extra setup parameters leaked toxic waste: counterfeit proofs possible.",
        "exclude", "Trusted-setup compromise: explicitly out of scope per contract s5.4. Never exploited per the entry.",
        None,
        {"rel": "Modified-Pinocchio setup emitting toxic parameters.", "key": None,
         "stmt": None, "interp": None, "policy": None, "effect": None,
         "arg": "Excluded: setup-ceremony failure, not a relation/consumer disagreement.",
         "gaps": ["announcement not opened"]}))
    out.append(finding(
        "CF-14", "circomlib MiMC unconstrained output (Tornado Cash root forgery)", "F-circomlib", "A-tornado-cash",
        "mimc-1", "Assignment instead of constraint let attackers set the hash output: faked merkle roots paid out.",
        "include", "Withdraw contract pays on roots the relation never binds to deposits: accepted proof, unauthorized effect. Canonical proof-to-execution shape.",
        ("C_RELATION_GAP", "boundary",
         "Hash output assigned, not constrained; fix changes = to <==."),
        {"rel": "MiMC sponge step with outs[0] assigned from the S-box output.",
         "key": None, "stmt": "withdrawal authorization over a claimed root.",
         "interp": "Pool contract treats an accepted proof as deposit-backed withdrawal.",
         "policy": "Unreviewed withdrawal policy; recorded as gap.",
         "effect": "Payout against a forged root (authorization).",
         "arg": "Attacker-chosen hash outputs verify; consumer releases funds.",
         "gaps": ["post and fix PR not opened"]}))
    out.append(finding(
        "CF-15", "PSE-Scroll zkEVM modulo overflow (k*n+r)", "F-scroll-zkevm", "A-scroll-zkevm",
        "pse-zkevm-1", "Missing k*n+r<2^256 bound let provers prove false remainders: wrong state updates verified.",
        "include", "L1 rollup consumer finalizes state roots over admitted transitions; the relation admits false modular steps the consumer treats as executed.",
        ("C_REPRESENTATION", "circuit",
         "Range bound on the quotient-overflow term missing; fix constrains k*n+r below 2^256."),
        {"rel": "Modulo gadget via MulAddWords mod 2^256 without overflow bound.",
         "key": None, "stmt": "claimed state transition.",
         "interp": "Rollup contract treats verified batches as correctly executed transitions.",
         "policy": "Unreviewed state-transition policy; recorded as gap.",
         "effect": "Finalized incorrect state (authorization of a false transition).",
         "arg": "False remainders verify; consumer finalizes them.",
         "gaps": ["issue/PR not opened"]}))
    out.append(finding(
        "CF-16", "PSE-Scroll zkEVM SHL/SHR shf0 unconstrained", "F-scroll-zkevm", "A-scroll-zkevm",
        "pse-zkevm-2", "Shift-byte shf0 not bound to shift's first byte: false shift proofs verified.",
        "include", "Same consuming system as CF-15; assigned-but-unconstrained auxiliary input diverges from the constrained relation the consumer assumes.",
        ("C_RELATION_GAP", "circuit",
         "Auxiliary byte unconstrained; fix adds shf0 == shift.le_bytes[0]."),
        {"rel": "SHL/SHR opcode gadget computing 2^shf0 with shf0 free.",
         "key": None, "stmt": "claimed state transition.",
         "interp": "Rollup contract treats verified batches as correctly executed transitions.",
         "policy": "Unreviewed state-transition policy; recorded as gap.",
         "effect": "Finalized incorrect state.",
         "arg": "Attacker-assigned shf0 verifies; consumer finalizes.",
         "gaps": ["issue/spec PR not opened"]}))
    out.append(finding(
        "CF-17", "Dusk Plonk missing blinding factors", "F-dusk", "A-dusk",
        "dusk-1", "Proofs leaked witness material: privacy failure with no execution effect.",
        "exclude", "Privacy leakage unrelated to execution consistency: out of scope per contract s5.4. No authorized/required-effect disagreement.",
        None,
        {"rel": "Plonk prover polynomials without blinding shifts.", "key": None,
         "stmt": None, "interp": None, "policy": None, "effect": None,
         "arg": "Excluded: witness-extractability is a privacy property, not a proof-to-execution mismatch.",
         "gaps": ["issue/PR not opened"]}))
    out.append(finding(
        "CF-18", "Nightfall nullifier field-overflow double spend", "F-nightfall", "A-nightfall",
        "nightfall-1", "Same EVM/field width gap as CF-09 in a private-transfer system: n and n+p both spend.",
        "include", "Spent-nullifier set (consumer) vs reduced field view (circuit): same boundary class as CF-09, independent family.",
        ("C_REPRESENTATION", "boundary",
         "Consumer-side range check missing; fix requires inputs < zokratesPrime."),
        {"rel": "Spend proofs reducing the nullifier modulo the circuit field.",
         "key": None, "stmt": "private spend plus 256-bit nullifier.",
         "interp": "Token contracts treat unseen nullifiers as fresh spends.",
         "policy": "Unreviewed spend policy; recorded as gap.",
         "effect": "Double spend (duplicate).",
         "arg": "n and n+p distinct on-chain, identical in-circuit.",
         "gaps": ["issue/PR not opened"]}))
    out.append(finding(
        "CF-19", "Summa solvency check wired to assignable advice", "F-summa", "A-summa",
        "summa-1", "Solvency gate compared against a prover-settable cell: false solvency proved.",
        "include", "Solvency verifier (consumer of the proof) treats acceptance as assets>=liabilities; the relation admits the opposite.",
        ("C_RELATION_GAP", "circuit",
         "Gate output taken from assignable advice; fix compares against constant 1."),
        {"rel": "LessThan solvency gate with check cell assigned at witness time.",
         "key": None, "stmt": "claimed solvency (assets_sum >= liabilities_sum).",
         "interp": "Protocol treats an accepted proof as a true solvency claim.",
         "policy": "Unreviewed solvency policy; recorded as gap.",
         "effect": "False solvency attestation relied upon.",
         "arg": "Malicious prover sets check=0; proof verifies for lhs>rhs.",
         "gaps": ["issue/PR not opened"]}))
    out.append(finding(
        "CF-20", "Polygon zkEVM div remainder bound (C<A)", "F-polygon-zkevm", "A-polygon-zkevm",
        "polygon-zkevm-1", "Remainder never bounded below divisor: B=E/A-1, C=(E%A)+A verifies.",
        "include", "L1 rollup consumer finalizes batches whose division steps the relation admits falsely.",
        ("C_REPRESENTATION", "circuit",
         "Remainder-vs-divisor bound missing (C<E checked instead of C<A); fix swaps the comparison."),
        {"rel": "divARITH subroutine A*B+C=D+E without C<A.",
         "key": None, "stmt": "claimed state transition.",
         "interp": "Rollup contract treats verified batches as correctly executed transitions.",
         "policy": "Unreviewed state-transition policy; recorded as gap.",
         "effect": "Finalized incorrect state.",
         "arg": "Forged quotient/remainder pairs satisfy the equation; consumer finalizes.",
         "gaps": ["explainer thread not opened"]}))
    out.append(finding(
        "CF-21", "Polygon zkEVM SMT fake inclusion (rkeyBit)", "F-polygon-zkevm", "A-polygon-zkevm",
        "hexens-polygonzkevm-1", "Unconstrained path bit let attackers bind arbitrary values to faked keys.",
        "include", "Bridge/state consumer credits balances on inclusion proofs the relation admits for wrong keys.",
        ("C_FIELD_MAPPING", "boundary",
         "Path-bit binary constraint missing; ROM treats any nonzero as 1; fix adds the binary constraint."),
        {"rel": "SMT inclusion check with free rkeyBit input.",
         "key": None, "stmt": "claimed (key, value) storage inclusion.",
         "interp": "Rollup/bridge treats verified inclusion as balance truth.",
         "policy": "Unreviewed balance policy; recorded as gap.",
         "effect": "Credited attacker balance (authorization).",
         "arg": "Non-binary rkeyBit values pass the JMPZ path and the permutation check.",
         "gaps": ["audit report not opened (tonight out of scope)", "fix commit not opened"]}))
    out.append(finding(
        "CF-22", "Polygon zkEVM CTX/global aliasing via identity precompile", "F-polygon-zkevm", "A-polygon-zkevm",
        "hexens-polygonzkevm-2", "CTX set to 0 aliased global/tx variables: sequencer paid oldStateRoot-sized gas.",
        "include", "Sequencer-payment accounting (consumer effect) computed over aliased context the relation does not separate.",
        ("C_CONTEXT_IDENTITY", "boundary",
         "Call-context identity collapsed to 0; fix saves originCTX before the jump."),
        {"rel": "identity-precompile ROM path with CTX:=0 on direct calls.",
         "key": None, "stmt": "claimed execution trace with gas accounting.",
         "interp": "Rollup treats the verified trace's sequencer payment as computed.",
         "policy": "Unreviewed fee policy; recorded as gap.",
         "effect": "Unbounded sequencer credit, bridgeable (authorization).",
         "arg": "Global/CTX variable offsets collide; txGasLimit reads oldStateRoot.",
         "gaps": ["audit report not opened (tonight out of scope)", "fix commit not opened"]}))
    out.append(finding(
        "CF-23", "Polygon zkEVM isNeg jump-destination hijack", "F-polygon-zkevm", "A-polygon-zkevm",
        "hexens-polygonzkevm-3", "Unconstrained jump flag allowed arbitrary zkPC: SSTORE gadget set balances.",
        "include", "Consumer settles state written by a program counter the relation leaves free.",
        ("C_ACTIVATION_EXTENT", "circuit",
         "Jump-condition flag not constrained to {0,1}; fix adds isNeg*(1-isNeg)=0."),
        {"rel": "JMPN path with free isNeg selecting zkPC.",
         "key": None, "stmt": "claimed execution trace.",
         "interp": "Rollup treats the verified trace as the executed program.",
         "policy": "Unreviewed execution policy; recorded as gap.",
         "effect": "Attacker-chosen balance write finalized.",
         "arg": "isNeg solved for arbitrary zkPC; CALL-chain gadget reaches SSTORE.",
         "gaps": ["audit report not opened (tonight out of scope)", "fix commit not opened"]}))
    out.append(finding(
        "CF-24", "Zendoo dense-polynomial normalization gap", "F-zendoo", "A-zendoo",
        "zendoo-polynomial-1", "Untrimmed zero coefficients broke degree assumptions: panics/DoS, no proof effect.",
        "exclude", "Backend library availability bug with no proof-consuming interpretation disagreement. No authorized/required-effect consequence.",
        None,
        {"rel": "DensePolynomial add/sub leaving trailing zero coefficients.", "key": None,
         "stmt": None, "interp": None, "policy": None, "effect": None,
         "arg": "Excluded: representation invariant break with panic/DoS impact only; no accepted-proof vs consumer disagreement.",
         "gaps": ["audit report not opened (tonight out of scope)", "fix commit not opened"]}))
    out.append(finding(
        "CF-25", "Aleo InputID::Private non-binding encryption", "F-snarkvm", "A-aleo",
        "aleo-encryption-1", "input_hash not binding on input across caller/callee: same id, different inputs.",
        "include", "Network verifier enforces input_id equality across circuits as argument binding; the relation admits equal ids for different inputs.",
        ("C_RELATION_GAP", "boundary",
         "Commitment dependency (tvk binding) omitted; fix uses committing encryption with tcm public."),
        {"rel": "Caller/callee circuits exposing input_hash over tvk-encrypted input.",
         "key": None, "stmt": "cross-circuit argument ids.",
         "interp": "Network treats matching input_ids as identical arguments.",
         "policy": "Unreviewed cross-circuit policy; recorded as gap.",
         "effect": "Callee executes on attacker-substituted input (authorization).",
         "arg": "Attacker-chosen ivk yields same ciphertext/hash for different input.",
         "gaps": ["audit report not opened (tonight out of scope)", "fix commit not opened"]}))
    out.append(finding(
        "CF-26", "Light Protocol non-atomic shared-state update", "F-light-protocol", "A-light-protocol",
        "light-protocol-1", "Same-signer concurrent tree updates interleaved: unpaid merge, no proof disagreement.",
        "exclude", "Concurrency/atomicity bug in the consumer with no accepted-relation vs interpretation disagreement. Pure consumer bug per protocol s2.",
        None,
        {"rel": "Poseidon Merkle update split across instructions with signer-keyed lock.", "key": None,
         "stmt": None, "interp": None, "policy": None, "effect": None,
         "arg": "Excluded: lock-scope flaw is a consumer concurrency bug; the entry shows no proof the relation admits what the consumer forbids or vice versa.",
         "gaps": ["audit report not opened (tonight out of scope)", "fix commits not opened"]}))
    out.append(finding(
        "CF-27", "ZK Email regex anchor bypass (0xff) sender spoofing", "F-zkemail", "A-zkemail",
        "zkemail-1", "^ anchor re-triggerable by 0xff bytes in mail: victim address extracted from subject as from.",
        "include", "On-chain contracts authorize transactions on the extracted sender the proof attests; the relation admits extraction from the wrong header.",
        ("C_ACTIVATION_EXTENT", "boundary",
         "Start-of-string activation re-triggerable mid-input; fix range-checks inputs below 255."),
        {"rel": "DFA regex circuits with injected 255 start marker and un ranged inputs.",
         "key": None, "stmt": "extracted sender address + DKIM validity.",
         "interp": "Contracts treat the extracted address as the DKIM-authenticated sender.",
         "policy": "Unreviewed sender-authorization policy; recorded as gap.",
         "effect": "Transactions authorized as the victim (authorization).",
         "arg": "0xff in subject re-arms ^; from-pattern matches victim string in subject.",
         "gaps": ["research report and review PDF not opened (tonight out of scope)", "fix commit not opened"]}))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tracker-readme", type=Path, required=True)
    ap.add_argument("--tracker-sha256", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    readme_bytes = args.tracker_readme.read_bytes()
    actual = hashlib.sha256(readme_bytes).hexdigest()
    if actual != args.tracker_sha256:
        raise SystemExit(f"tracker README hash mismatch: {actual} != {args.tracker_sha256}")

    findings = build_findings()
    assert len(findings) == 27, len(findings)
    anchors = sorted(f["_x_anchor"] for f in findings)
    assert len(set(anchors)) == 27, "anchors must be unique"

    fams, apps = {}, {}
    for fid, name, aid, aname, uri, prod, cons, anchor in APPS:
        fams[fid] = {"id": fid, "name": name, "aliases": [], "status": "provisional",
                     "application_ids": [aid], "organization_ids": [], "library_ids": [],
                     "relation_ids": [], "independence_group_id": f"IG-{fid[2:].lower()}",
                     "independence_rationale": "Conservative singleton: no lineage evidence reviewed among seed entries; merges require human review.",
                     "exposure_completeness": "partial",
                     "evidence": [ev(anchor)]}
        apps[aid] = {"id": aid, "name": aname, "family_id": fid, "organization_ids": [],
                     "library_uses": [], "repository_uri": uri, "revisions": [],
                     "producer_stack": prod, "consumer_stack": cons,
                     "development_scope_basis": [ev(anchor)]}

    inc = sum(1 for f in findings if f["relevance"]["decision"] == "include")
    exc = sum(1 for f in findings if f["relevance"]["decision"] == "exclude")
    unr = len(findings) - inc - exc

    ledger = {
        "schema_version": "0.2.0", "protocol_ref": "docs/taxonomy/protocol.md",
        "created_at": NOW, "updated_at": NOW,
        "protocol_states": {"design_frozen": False, "design_frozen_at": None,
                            "protocol_sha256": None, "search_plan_sha256": None,
                            "reservation_completed": False, "reservation_completed_at": None,
                            "annotation_round_completed": False, "annotation_round_completed_at": None},
        "planner_reviews": [], "reservation": {
            "commitment_scheme": "sha256-nonce-concat-canonical-manifest-v1",
            "commitment_sha256": None, "custodian_attestation": None,
            "commitment_limitations": [
                "The commitment can show consistency with a later opening.",
                "The commitment does not prove randomness or timing.",
                "Operational exclusion of reserved-family code, findings, and results from development is the essential protection."]},
        "search_plan": {
            "id": "lane-x-seed-only-v1", "protocol_sha256": None,
            "publication_start": "2018-01-01", "publication_end": "2026-10-27",
            "date_basis": "earliest_public_primary_disclosure", "languages": ["English"],
            "language_rationales": [{"language": "English",
                                     "reason": "Seed listing is English; no translation performed."}],
            "sampling_frame": "proof_consuming_zk_systems_across_languages_chains_and_proof_stacks",
            "claim_boundary": "these mechanisms recur across independent families in the sampled public disclosures",
            "source_class_order": ["snark_sok_bug_set", "zk_bug_tracker"],
            "seed_endpoint_ids": ["seed-snark-sok-bug-dataset", "seed-0xparc-zk-bug-tracker"],
            "source_endpoints": [
                {"id": "seed-0xparc-zk-bug-tracker", "tier": "seed", "source_class": "zk_bug_tracker",
                 "source_role": "seed", "organization": "0xPARC",
                 "endpoint": TRACKER_URI, "verification_status": "known_public_listing",
                 "hosting_kind": "git", "snapshot_rule": "git_ls_remote_head",
                 "snapshot_status": "pinned_commit", "revision_or_snapshot": PIN,
                 "snapshot_sha256": None, "listing_format_risk": "mixed_names_and_bug_descriptions",
                 "candidate_list_handling": "human_sanitized_required",
                 "agent_access_rule": "metadata_only_no_finding_report_body_or_bug_description_views",
                 "access_limitations": [
                     "Frozen plan agent_access_rule is metadata-only; tonight's task explicitly directed seed extraction, a documented deviation pending custodian review.",
                     "Remote HEAD equaled the pinned commit at retrieval; README bytes hashed at build.",
                     "Linked issues, commits, papers, and reports were NOT opened (tonight out of scope)."]},
                {"id": "seed-snark-sok-bug-dataset", "tier": "seed", "source_class": "snark_sok_bug_set",
                 "source_role": "seed", "organization": "SNARK SoK authors",
                 "endpoint": "unresolved: no standalone public dataset endpoint located under tonight's source constraint",
                 "verification_status": "to_verify_by_custodian", "hosting_kind": "web",
                 "snapshot_rule": "custodian_capture_immediately_after_freeze",
                 "snapshot_status": "capture_after_freeze", "revision_or_snapshot": None,
                 "snapshot_sha256": None, "listing_format_risk": "unknown",
                 "candidate_list_handling": "custodian_classify_before_agent_access",
                 "agent_access_rule": "metadata_only_no_finding_report_body_or_bug_description_views",
                 "access_limitations": [
                     "One bounded web search confirmed the SoK corpus (141 vulns across 107 audit reports, 16 disclosures, trackers) has no standalone agent-reachable dataset URL; the paper body and audit reports are out of scope tonight.",
                     "Custodian must identify the dataset listing per the frozen plan."]}],
            "traversal_steps_in_order": ["seed-only night: clone pinned tracker, screen 27 wild entries, attempt SoK locate; no backbone traversal"],
            "mechanism_keyword_groups": [],
            "maximum_results_per_endpoint": {"status": "PROPOSED", "value": 100,
                                             "unit": "returned results per supplemental keyword endpoint",
                                             "justification": "Unapproved placeholder; no supplement run.",
                                             "approved_by_planner_review_ids": []},
            "active_time_budget_minutes": {"status": "PROPOSED", "value": 1200,
                                           "unit": "active human or agent minutes across all endpoints",
                                           "justification": "Frozen value restated without approval claim.",
                                           "approved_by_planner_review_ids": []},
            "pagination_policy": "Single-file seed listing; no pagination.",
            "stop_rule": "Seed-only night completed: 27/27 tracker entries screened; SoK recorded unresolved.",
            "audit_report_completeness_rule": "screen_all_findings_in_any_selected_audit_report_used_for_percentages",
            "discovery_route_rule": "tag_seed_and_systematic_routes_before_deduplication_and_preserve_all_overlap_tags",
            "language_rationales": [{"language": "English",
                                     "reason": "Seed listing is English; no translation performed."}],
            "inclusion_boundary": "evidence supports a disagreement between what the accepted proof relation establishes and what the proof-consuming system interprets as authorized or required; relevance is independent of BindCheck support",
            "consecutive_irrelevant_pages_stop": {"status": "PROPOSED", "value": 3,
                                                  "unit": "pages",
                                                  "justification": "Unapproved placeholder; no supplement run.",
                                                  "approved_by_planner_review_ids": []},
            "candidate_list_rule": "output_only_application_or_project_name_repository_url_and_endpoint_id; mixed-description listings require human sanitization",
            "content_access_rule": PLAN_RULE},
        "actors": [{"id": ACTOR, "kind": "ai", "display_name": "Lane-X research engineer (Muse Code)",
                    "role": "seed-corpus extraction; AI-SUGGESTED labels only, never final annotation",
                    "provider": "Meta", "model": "Muse Spark", "model_version": None,
                    "session_id": "aqua-ophiuchus", "metadata_gap": None}],
        "search_runs": [
            {"id": "run-tracker-clone", "plan_id": "lane-x-seed-only-v1", "actor_id": ACTOR,
             "endpoint_id": "seed-0xparc-zk-bug-tracker", "application_ids": sorted(apps),
             "source_class": "zk_bug_tracker", "endpoint": TRACKER_URI,
             "retrieval_mode": "seed_import", "query_text": None, "traversal_instruction": "clone pinned commit; read README listing fully",
             "filters": [], "time": {"start": None, "end": None, "date_utc": "2026-10-28",
                                     "precision": "date_only", "basis": "retrieval date"},
             "pages_or_cursors": [], "total_hits_reported": 27, "hits_retrieved": 27,
             "returned_records": [{"source_id": "src-0xparc-tracker", "rank": 1}],
             "status": "completed", "stop_reason": "all 27 wild entries screened",
             "failure_detail": None, "log": None},
            {"id": "run-sok-locate", "plan_id": "lane-x-seed-only-v1", "actor_id": ACTOR,
             "endpoint_id": "seed-snark-sok-bug-dataset", "application_ids": [],
             "source_class": "snark_sok_bug_set", "endpoint": "unresolved-no-standalone-dataset-url",
             "retrieval_mode": "seed_import", "query_text": "SoK SNARK vulnerability dataset location",
             "traversal_instruction": "one bounded web search; open nothing else",
             "filters": [], "time": {"start": None, "end": None, "date_utc": "2026-10-28",
                                     "precision": "date_only", "basis": "retrieval date"},
             "pages_or_cursors": [], "total_hits_reported": None, "hits_retrieved": 0,
             "returned_records": [], "status": "failed",
             "stop_reason": "no standalone dataset endpoint locatable under tonight's source constraint",
             "failure_detail": "Corpus confirmed as paper plus 107 audit reports; both out of scope tonight; custodian identification still owed.",
             "log": None}],
        "source_records": [
            {"id": "src-0xparc-tracker", "source_class": "zk_bug_tracker",
             "title": "0xPARC ZK Bug Tracker README (27 Bugs in the Wild)",
             "publisher": "0xPARC", "uri": TRACKER_URI, "aliases": [],
             "primary": True, "disclosure_ids": [], "published_on": None,
             "incident_on": None, "audit_on": None, "patch_on": None,
             "retrieved": {"start": None, "end": None, "date_utc": "2026-10-28",
                           "precision": "date_only", "basis": "retrieval date"},
             "retrieved_by_actor_id": ACTOR, "sha256": None, "revision": PIN,
             "access_status": "full", "reported_status": None, "affected_revisions": [],
             "limitations": ["README bytes hashed at build; git revision pinned; remote HEAD equaled pin",
                             "section bodies read under task direction (see deviation note)",
                             "linked issues/commits/papers/reports NOT opened"],
             "related_source_ids": []}],
        "organizations": [{"id": "org-0xparc", "name": "0xPARC",
                           "evidence": [ev("zk-bug-tracker")]}],
        "libraries": [], "family_relations": [],
        "families": list(fams.values()), "applications": list(apps.values()),
        "findings": [{k: v for k, v in f.items() if not k.startswith("_x")} for f in findings],
        "exposure_events": [
            {"id": f"exp-{fid[2:].lower()}", "actor_id": ACTOR, "session_id": "aqua-ophiuchus",
             "family_id": fid, "application_ids": [aid], "material_kinds": ["finding", "metadata"],
             "materials": [ev(anchor)], "access": "direct",
             "purpose": "seed-corpus extraction under task direction; family henceforth exposed, never held-out",
             "occurred": {"start": None, "end": None, "date_utc": "2026-10-28",
                         "precision": "date_only", "basis": "retrieval date"},
             "logged_at": NOW, "recorded_by_actor_id": ACTOR, "logging_mode": "contemporaneous",
             "linked_event_ids": [], "corrects_event_id": None, "uncertainty": []}
            for fid, _, aid, _, _, _, _, anchor in APPS],
        "annotation_rounds": [], "agreement_reports": [],
        "summary": {"as_of": NOW, "raw_retrieval_hits": 27, "unique_source_records": 1,
                    "candidate_rows": 27, "duplicate_rows": 0, "canonical_findings": 27,
                    "disclosure_counts": {"screened": 27, "include": inc, "exclude": exc,
                                          "unresolved": unr},
                    "tool_counts": {"artifacts_available": {"screened": 0, "relevant": 0,
                                                            "artifacts_available": 0, "supported": 0,
                                                            "analyzed": 0, "validated": 0},
                                    "supported": {"screened": 0, "relevant": 0,
                                                  "artifacts_available": 0, "supported": 0,
                                                  "analyzed": 0, "validated": 0},
                                    "analyzed": {"screened": 0, "relevant": 0,
                                                 "artifacts_available": 0, "supported": 0,
                                                 "analyzed": 0, "validated": 0},
                                    "validated": {"screened": 0, "relevant": 0,
                                                  "artifacts_available": 0, "supported": 0,
                                                  "analyzed": 0, "validated": 0}},
                    "derived_by": ACTOR,
                    "derivation_version": "taxonomy_v1_corpus.py lane-x-seed-only-v1"},
        "change_log": [{"id": "chg-v1-create", "at": NOW, "actor_id": ACTOR,
                        "record_ids": ["v1-corpus-ledger"],
                        "action": "create",
                        "rationale": "Seed-only corpus v1: 27 tracker entries screened (19 include, 8 exclude), AI-SUGGESTED labels only, SoK endpoint unresolved.",
                        "previous_record_hashes": [], "evidence": [ev("zk-bug-tracker")]}],
    }
    args.out.write_text(json.dumps(ledger, indent=1) + "\n")
    meta = [{"id": f["id"], "anchor": f["_x_anchor"], "one_line": f["_x_one_line"],
             "decision": f["relevance"]["decision"],
             "ai_label": (f["facts"][0]["claim"] if f["facts"] else None)}
            for f in findings]
    (args.out.parent / "v1-corpus-entries.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(f"wrote {len(findings)} findings ({inc} include, {exc} exclude, {unr} unresolved)")


if __name__ == "__main__":
    main()


