"""Policy schema. Policy states semantic roles and protocol rules; it must not assert the implementation binding
being tested, nor the expected verdict (research contract §6.3). It is hashed into the result's cache identity.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RecordGrammar:
    """kind value -> record length in words. A kind outside `lengths` reverts the consumer walk."""
    lengths: dict                       # {kind: length}
    mint_kind: int
    burn_kind: int
    pad_kind: int = 0
    burn_value_offset: int = 1
    burn_recipient_offset: int = 2
    mint_id_offset: int = 1

    @property
    def uniform(self):
        vals = set(self.lengths.values())
        return vals.pop() if len(vals) == 1 else None


@dataclass
class Policy:
    name: str
    messages_ref: str                   # ref into the producer ABI for the public message array (effects source)
    permission_ref: str                 # ref for the certified permission stream
    grammar: RecordGrammar
    n: int
    note: str = ""
    assumptions: list = field(default_factory=list)

    @classmethod
    def load(cls, path):
        d = json.loads(Path(path).read_text())
        g = d["grammar"]
        return cls(name=d["name"], messages_ref=d["messages_ref"], permission_ref=d["permission_ref"],
                   grammar=RecordGrammar(lengths={int(k): v for k, v in g["lengths"].items()},
                                         mint_kind=g["mint_kind"], burn_kind=g["burn_kind"],
                                         pad_kind=g.get("pad_kind", 0),
                                         burn_value_offset=g.get("burn_value_offset", 1),
                                         burn_recipient_offset=g.get("burn_recipient_offset", 2),
                                         mint_id_offset=g.get("mint_id_offset", 1)),
                   n=d["n"], note=d.get("note", ""), assumptions=d.get("assumptions", []))

    def sha256(self, path):
        import hashlib
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
