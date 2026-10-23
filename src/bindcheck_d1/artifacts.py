"""Versioned artifact identities. Missing correspondence is a limitation, never a guessed association."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Artifact:
    role: str          # e.g. producer-acir, producer-abi, decoder-acir, consumer-ast, policy, protocol
    path: str
    sha256: str
    source_revision: str = ""
    tool: str = ""     # compiler/tool identity that produced it

    @classmethod
    def of(cls, role, path, source_revision="", tool=""):
        return cls(role, str(path), sha256_file(path), source_revision, tool)


def identity_key(artifacts, policy_sha256, bounds, assumptions):
    """Cache identity: every artifact, the policy, bounds and assumptions. Any change gives a new key."""
    blob = json.dumps({"artifacts": sorted((a.role, a.sha256, a.source_revision, a.tool) for a in artifacts),
                       "policy": policy_sha256, "bounds": bounds, "assumptions": sorted(assumptions)},
                      sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()
