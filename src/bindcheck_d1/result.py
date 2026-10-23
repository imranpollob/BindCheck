"""Result envelope: three verdicts plus separate evidence grade, scope, assumptions and reasons."""
from dataclasses import dataclass, field, asdict
import json

VERDICTS = ("VIOLATION", "VERIFIED_WITHIN_SCOPE", "UNKNOWN")

# Evidence grades, weakest to strongest. A verdict never upgrades its grade implicitly.
GRADES = (
    "NONE",
    "ABSTRACT_MODEL",                 # solver model of the joint abstraction, not yet replayed
    "CONCRETE_MODEL_REPLAYED",        # actual ACIR executed (nargo) + unchanged consumer executed under assumed verification
    "REAL_PROOF_REPLAYED",            # real proof accepted by the real verifier and committed effects observed
)

REASONS = {
    "UNSUPPORTED_ACIR", "UNSUPPORTED_SOLIDITY", "MISSING_ASSUMPTION", "SOLVER_TIMEOUT", "SOLVER_RESOURCE",
    "SOLVER_UNKNOWN", "CANDIDATE_NOT_CONCRETIZED", "MATCHING_UNRESOLVED", "DEFERRAL_UNSUPPORTED",
    "NONVACUITY_UNRESOLVED", "LINK_NOT_ESTABLISHED", "SPECIFICATION_UNRESOLVED", "SCOPE_NOT_ATTEMPTED",
    "CERTIFICATION_CONDITIONAL",
}


@dataclass
class Result:
    case: str
    scope: str
    verdict: str
    evidence_grade: str = "NONE"
    reasons: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)
    bounds: dict = field(default_factory=dict)
    nonvacuity: str = "NOT_CHECKED"          # SAT_REPLAYED | SAT | UNSAT | UNKNOWN | NOT_CHECKED
    goals: dict = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)
    facts: dict = field(default_factory=dict)  # counts of EXTRACTED / PROVED / ASSUMED facts

    def __post_init__(self):
        if self.verdict not in VERDICTS:
            raise ValueError(f"verdict must be one of {VERDICTS}")
        if self.evidence_grade not in GRADES:
            raise ValueError(f"unknown evidence grade {self.evidence_grade}")
        bad = [r for r in self.reasons if r.split(":", 1)[0] not in REASONS]
        if bad:
            raise ValueError(f"unknown reason codes {bad}")
        if self.verdict == "UNKNOWN" and not self.reasons:
            raise ValueError("UNKNOWN requires a reason code")
        if self.verdict == "VERIFIED_WITHIN_SCOPE" and self.nonvacuity != "SAT_REPLAYED":
            raise ValueError("VERIFIED_WITHIN_SCOPE requires a replayed non-vacuity witness")
        if self.verdict == "VIOLATION" and self.evidence_grade in ("NONE", "ABSTRACT_MODEL"):
            raise ValueError("VIOLATION requires a concretized candidate")

    def to_json(self):
        return json.dumps(asdict(self), indent=2, sort_keys=True)


def unknown(case, scope, *reasons, **kw):
    return Result(case=case, scope=scope, verdict="UNKNOWN", reasons=list(reasons), **kw)
