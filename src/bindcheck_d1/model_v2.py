"""Explicit semantic domains and evidence boundaries for the v2 prototype."""
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path

FIELD_MODULUS = 21888242871839275222246405745257275088548364400416034343698204186575808495617


class Unsupported(ValueError):
    def __init__(self, reason, detail):
        self.reason = reason
        super().__init__(detail)


class Verdict(str, Enum):
    VIOLATION = 'VIOLATION'
    VERIFIED_WITHIN_SCOPE = 'VERIFIED_WITHIN_SCOPE'
    UNKNOWN = 'UNKNOWN'


class EvidenceGrade(str, Enum):
    EXTRACTED = 'EXTRACTED'
    ASSUMED = 'ASSUMED'
    POLICY = 'POLICY'
    SYNTHETIC = 'SYNTHETIC'


@dataclass(frozen=True)
class Artifact:
    path: str
    sha256: str

    @classmethod
    def read(cls, path):
        p = Path(path)
        return cls(str(p), sha256(p.read_bytes()).hexdigest())


@dataclass(frozen=True)
class Provenance:
    artifact: Artifact
    location: str
    grade: EvidenceGrade


@dataclass(frozen=True)
class FieldWord:
    value: int

    def __post_init__(self):
        if type(self.value) is not int or not 0 <= self.value < FIELD_MODULUS:
            raise Unsupported('NONCANONICAL_FIELD', repr(self.value))


@dataclass(frozen=True)
class EvmWord:
    value: int

    def __post_init__(self):
        if type(self.value) is not int or not 0 <= self.value < 2**256:
            raise Unsupported('INVALID_EVM_WORD', repr(self.value))

    def field(self):
        # Do not silently reduce modulo the field.
        return FieldWord(self.value)

    def address(self):
        return self.value % 2**160


@dataclass(frozen=True)
class Key:
    domain: str
    kind: str
    asset: str
    amount: int
    note_hash: int
    recipient: int | None

    def __post_init__(self):
        if self.kind not in ('mint', 'burn'):
            raise Unsupported('POLICY_KIND_UNSUPPORTED', self.kind)
        EvmWord(self.amount)
        EvmWord(self.note_hash)
        if self.kind == 'burn':
            if type(self.recipient) is not int or not 0 <= self.recipient < 2**160:
                raise Unsupported('INVALID_RECIPIENT', repr(self.recipient))
        elif self.recipient is not None:
            raise Unsupported('MINT_RECIPIENT_UNEXPECTED', repr(self.recipient))


@dataclass(frozen=True)
class Occurrence:
    identity: tuple[str, int]
    key: Key
    provenance: Provenance


@dataclass(frozen=True)
class Policy:
    permissions: tuple[Occurrence, ...]
    obligations: tuple[Occurrence, ...]
    rationale: str

    def __post_init__(self):
        for name, records in [('permissions', self.permissions), ('obligations', self.obligations)]:
            if len({x.identity for x in records}) != len(records):
                raise Unsupported('DUPLICATE_OCCURRENCE_ID', name)
            if any(x.provenance.grade not in (EvidenceGrade.POLICY, EvidenceGrade.SYNTHETIC) for x in records):
                raise Unsupported('POLICY_PROVENANCE_REQUIRED', name)
        if not self.rationale:
            raise Unsupported('POLICY_RATIONALE_REQUIRED', '')


@dataclass(frozen=True)
class GateResult:
    """Extraction gate results cannot be promoted to a security verdict."""
    scope: str
    reasons: tuple[str, ...]
    evidence: tuple[Provenance, ...]
    assumptions: tuple[str, ...]
    non_vacuity: str = 'NOT_ESTABLISHED'

    @property
    def verdict(self):
        return Verdict.UNKNOWN
