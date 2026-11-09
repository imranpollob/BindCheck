#!/usr/bin/env python3
"""Bind the linked credential to the proof and prevent local credential replay."""
from pathlib import Path
import sys

path = Path(sys.argv[1])
source = path.read_text()
edits = [
    (
        '    mapping(uint256 => bytes32) public linkedCredential; // tokenId → cred hash (for revocation check)',
        '    mapping(uint256 => bytes32) public linkedCredential; // tokenId → cred hash (for revocation check)\n'
        '    mapping(bytes32 => bool) public usedCredential;',
    ),
    (
        '        require(kycOk, "EventPass: KYC proof invalid");',
        '        require(kycOk, "EventPass: KYC proof invalid");\n'
        '        require(kyc_pub.length > 1 && bytes32(kyc_pub[1]) == credHash, "EventPass: credential mismatch");\n'
        '        require(recipient == msg.sender, "EventPass: recipient mismatch");\n'
        '        require(!usedCredential[credHash], "EventPass: credential used");',
    ),
    (
        '        uint256 tokenId = config.minted++;\n        _safeMint(recipient, tokenId);\n        linkedCredential[tokenId] = credHash;',
        '        usedCredential[credHash] = true;\n'
        '        uint256 tokenId = config.minted++;\n        _safeMint(recipient, tokenId);\n        linkedCredential[tokenId] = credHash;',
    ),
]
for before, after in edits:
    if source.count(before) != 1:
        raise SystemExit(f"repair anchor count was {source.count(before)}: {before[:50]}")
    source = source.replace(before, after)
path.write_text(source)
