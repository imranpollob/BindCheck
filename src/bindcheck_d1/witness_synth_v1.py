"""Automatic attacker-witness construction for BindCheck v1 warnings.

Given a static warning (rule + semantic location + target identity) and a
frozen honest witness, synthesize a concrete attacker Prover.toml that
exercises the warning, then hand it to stock runners (nargo execute for E2,
bb.js UltraHonk for E3, Hardhat EDR replay for E4).

Synthesis plans are data (PLAN table), not hidden judgment: every plan names
the rule class, the mutated word(s), and the attacker values. Anything the
plan cannot construct (missing witness material) is reported as a blocked
stage with its missing prerequisite, never silently skipped.

Scope: WarpToad same-root EVM path (frozen honest witness D1P15_12R).
Payy aggregator witnesses are not constructible here; those warnings report
E1 with the missing harness named.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SCHEMA = "bindcheck.witness-synthesis.v1"

# Attacker constants (valid field elements, all != honest values in D1P15_12R).
ATTACKER = {
    "nullifier": "0x1111111111111111111111111111111111111111111111111111111111111111",
    "max_fee": "0x0",
    "chain_id": "0x1",
    "recipient_address": "0x0",
    "origin_local_root": "0x1234",
    "aztec_warptoad_address": "0xdeadbeef",
}


@dataclass
class SynthPlan:
    warning_id: str
    rule: str
    location: str
    kind: str  # bind-word | anchor-tree | aztec-branch | replay | unsupported
    word_updates: dict[str, str] = field(default_factory=dict)
    node_plan: dict[str, Any] | None = None
    differential_negative: str | None = None
    blocked_reason: str | None = None
    notes: list[str] = field(default_factory=list)


def plan_for(warning: dict[str, Any], target: str) -> SynthPlan:
    """Map a D1P-31 warning object to a synthesis plan. Pure function."""
    wid = warning.get("id", "?")
    rule = warning["rule"]
    loc = warning.get("location", "")
    if target.startswith("PY-"):
        return SynthPlan(wid, rule, loc, "unsupported",
                         blocked_reason="Payy aggregator needs a 2-proof witness harness (missing)",
                         notes=["tail warnings are valid reports of the known baseline defect, not new detections"])
    m = re.search(r"abi\.(\w+)", loc)
    word = m.group(1) if m else None

    if target == "WT-C04":
        # Two warnings, one plan: fabricated origin root carrying the
        # commitment (attacker tree), honest admitted destination. The
        # else branch runs; the mutant skips origin giga-membership.
        return SynthPlan(wid, rule, loc, "anchor-tree", {},
                         node_plan={"dest_override": "honest"},
                         differential_negative="pinned rejects: origin not in giga tree",
                         notes=["covers abi.giga_root + abi.destination_local_root jointly"])
    if target == "WT-C06":
        # Commitment binds amount=0 in the mutant: rebuild the tree over it.
        return SynthPlan(wid, rule, loc, "anchor-tree",
                         {"amount": "0x8AC7230489E80000"},
                         node_plan={"amount_override": "0x0"},
                         differential_negative="pinned binds the real amount",
                         notes=["attacker tree over the mutant commitment rule"])
    if target == "WT-C07":
        return SynthPlan(wid, rule, loc, "anchor-tree",
                         {"chain_id": ATTACKER["chain_id"]},
                         node_plan={"chain_override": "0x0"},
                         differential_negative="pinned binds the real chain id",
                         notes=["attacker tree over the mutant commitment rule"])

    if rule == "R-BIND" and word in ATTACKER:
        notes = []
        if word == "aztec_warptoad_address":
            return SynthPlan(wid, rule, loc, "aztec-branch", {},
                             differential_negative="pinned Aztec branch binds word 5 (D1P-15 foreign negative)",
                             notes=["honest witness is EVM-path; Aztec witness built by node plan"])
        return SynthPlan(wid, rule, loc, "bind-word", {word: ATTACKER[word]},
                         differential_negative=f"pinned constrains {word}",
                         notes=notes)
    if rule == "R-EFFECT":
        # WT-C08: recipient word unbound; attacker sets zero recipient.
        return SynthPlan(wid, rule, loc, "bind-word",
                         {"recipient_address": ATTACKER["recipient_address"]},
                         differential_negative="pinned asserts recipient != 0",
                         notes=["consumer ERC20 is expected to revert on mint(0); "
                                "E4 stage records the revert, E3 carries the proof"])
    if rule == "R-ANCHOR":
        if target == "WT-S02":
            # K1 (giga) removed, K2 kept: admitted local root, fabricated
            # giga root. Same-root path leaves the giga word unused in-circuit.
            return SynthPlan(wid, rule, loc, "bind-word",
                             {"giga_root": "0x1234"},
                             differential_negative="pinned K1 rejects the unadmitted giga root",
                             notes=["local root stays honest/admitted; K2 passes"])
        return SynthPlan(wid, rule, loc, "anchor-tree", {},
                         differential_negative="pinned K1/K2 rejects the unadmitted root",
                         notes=["attacker EVM tree built by node plan; "
                                "same-root shortcut skips in-circuit giga membership"])
    if rule == "R-POLARITY":
        return SynthPlan(wid, rule, loc, "replay", {},
                         differential_negative="pinned second mint reverts (nullifier spent)",
                         notes=["witness is the honest one; exploit is the second submission"])
    return SynthPlan(wid, rule, loc, "unsupported",
                     blocked_reason=f"no synthesis route for rule {rule} at {loc!r}",
                     notes=["Payy aggregator witnesses need a 2-proof harness (missing)"])


HONEST_TOML_NOTE = "# Generated from an existing frozen fixture by scripts/d1p15_prepare.py."


def apply_bind_word(honest_toml: str, updates: dict[str, str]) -> str:
    """Replace top-level `word = \"0x...\"` lines. Fails closed on mismatch."""
    out = honest_toml
    for word, value in updates.items():
        pattern = re.compile(rf"^({word} = )\"0x[0-9a-fA-F]+\"$", re.MULTILINE)
        matches = pattern.findall(out)
        if len(matches) != 1:
            raise ValueError(f"expected 1 match for {word}, found {len(matches)}")
        out = pattern.sub(rf'\g<1>"{value}"', out)
    return out


def toml_get(toml_text: str, key: str) -> str:
    m = re.search(rf"^{key} = \"([0-9a-fA-Fx]+)\"$", toml_text, re.MULTILINE)
    if not m:
        raise ValueError(f"key {key} not found")
    return m.group(1)


def write_toml(path: Path, text: str) -> None:
    path.write_text(text)
