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


def plan_for(warning: dict[str, Any], target: str = "") -> SynthPlan:
    """Map a warning object to a synthesis plan by SHAPE (rule + location +
    evidence path), never by mutant name. Pure function. ``target`` is kept
    only as a label for logs, not for dispatch."""
    wid = warning.get("id", "?")
    rule = warning["rule"]
    loc = warning.get("location", "")
    ev = warning.get("evidence", {}) or {}
    # v1.1 R-CONSUMER evidence carries the consumer word path + public index.
    cpath = ev.get("path", "") or ""
    m = re.search(r"abi\.(\w+)", loc)
    word = m.group(1) if m else None
    cword = re.search(r"(\w+)$", cpath).group(1) if cpath else None

    def unsupported(reason, notes=()):
        return SynthPlan(wid, rule, loc, "unsupported", blocked_reason=reason,
                         notes=list(notes))

    # ---- circuit words (WarpToad producer) ----
    if rule == "R-BIND" and word in ("giga_root", "destination_local_root"):
        # Fabricated origin carrying the commitment; honest admitted
        # destination. Covers both words with one plan.
        return SynthPlan(wid, rule, loc, "anchor-tree", {},
                         node_plan={"dest_override": "honest"},
                         differential_negative="pinned rejects: origin not in giga tree",
                         notes=["covers abi.giga_root + abi.destination_local_root jointly"])
    if rule == "R-BIND" and word == "aztec_warptoad_address":
        return SynthPlan(wid, rule, loc, "aztec-branch", {},
                         differential_negative="pinned Aztec branch binds word 5 (D1P-15 foreign negative)",
                         notes=["honest witness is EVM-path; Aztec witness built by node plan"])
    if rule == "R-BIND" and word == "chain_id":
        # Commitment binds chain 0 in the defective circuit: rebuild the
        # tree over it while the public word reads attacker-chosen.
        return SynthPlan(wid, rule, loc, "anchor-tree",
                         {"chain_id": ATTACKER["chain_id"]},
                         node_plan={"chain_override": "0x0", "burn_attacker_note": True},
                         differential_negative="pinned binds the real chain id",
                         notes=["attacker tree over the defective commitment rule",
                                "attacker note burned on-chain to pass admission"]) 
    if rule == "R-BIND" and word in ATTACKER:
        return SynthPlan(wid, rule, loc, "bind-word", {word: ATTACKER[word]},
                         differential_negative=f"pinned constrains {word}")
    # ---- consumer-shaped warnings ----
    if rule == "R-CONSUMER" and cword in ("destination_local_root", "local_root", "localRoot"):
        return SynthPlan(wid, rule, loc, "anchor-tree", {},
                         differential_negative="pinned admission rejects the unadmitted root",
                         notes=["attacker EVM tree; same-root shortcut skips in-circuit giga membership"])
    if rule == "R-CONSUMER" and cword in ("giga_root", "gigaRoot"):
        return SynthPlan(wid, rule, loc, "bind-word", {"giga_root": "0x1234"},
                         differential_negative="pinned admission rejects the unadmitted giga root",
                         notes=["local root stays honest/admitted"])
    if rule == "R-CONSUMER" and cword in ("nullifier",):
        return SynthPlan(wid, rule, loc, "replay", {},
                         differential_negative="pinned second mint reverts (nullifier spent)",
                         notes=["witness is the honest one; exploit is the second submission"])
    if rule == "R-CONSUMER" and cword in ("max_fee", "maxFee"):
        # Fee-cap admission removed: prove with max_fee=0 (circuit allows
        # amount >= 0), then mint while the formula fee exceeds it.
        return SynthPlan(wid, rule, loc, "bind-word", {"max_fee": "0x0"},
                         differential_negative="pinned fee-cap check reverts",
                         notes=["E4 expects relayer over-charge above the stated max"])
    if rule == "R-POLARITY":
        return SynthPlan(wid, rule, loc, "replay", {},
                         differential_negative="pinned second submission reverts (single-use)",
                         notes=["witness is the honest one; exploit is the second submission"])
    if rule == "R-EFFECT" and "WarpToadCore" in loc:
        return SynthPlan(wid, rule, loc, "bind-word",
                         {"recipient_address": ATTACKER["recipient_address"]},
                         differential_negative="pinned asserts recipient != 0",
                         notes=["consumer ERC20 is expected to revert on mint(0); "
                                "E4 stage records the revert, E3 carries the proof"])
    # ---- Payy shapes (consumer replay route; circuit needs inner proofs) ----
    if "RollupV1" in loc or "agg_agg" in loc:
        return unsupported("Payy route depends on warning sub-shape; see driver",
                           ["consumer replay route handles mint/replay shapes",
                            "circuit shapes need real inner proofs (Rust stack)"])
    return unsupported(f"no synthesis route for rule {rule} at {loc!r}")


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
