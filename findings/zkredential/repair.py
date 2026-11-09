#!/usr/bin/env python3
"""Apply the narrowly scoped, explicit PropertyFy mint-authorization repair."""
from pathlib import Path
import sys

path = Path(sys.argv[1])
source = path.read_text()
edits = [
    (
        '    address public rwaTokenAddress;',
        '    address public rwaTokenAddress;\n'
        '    // Issuer-approved quantity, consumed by successful mints.\n'
        '    mapping(address => uint256) public mintAllowance;\n'
        '    function approveMint(address wallet, uint256 amount) external onlyOwner {\n'
        '        mintAllowance[wallet] = amount;\n'
        '    }',
    ),
    (
        '        if (targetAction == Action.MINT_RWA_TOKEN) {\n'
        '            IRWAToken(rwaTokenAddress).mint(msg.sender, amount);',
        '        if (targetAction == Action.MINT_RWA_TOKEN) {\n'
        '            require(keccak256(bytes(platform)) == keccak256(bytes("propertyfy")), "mint platform unsupported");\n'
        '            require(pubSignals[10] == uint256(uint160(msg.sender)), "proof wallet mismatch");\n'
        '            require(amount > 0 && mintAllowance[msg.sender] >= amount, "mint not approved");\n'
        '            mintAllowance[msg.sender] -= amount;\n'
        '            IRWAToken(rwaTokenAddress).mint(msg.sender, amount);',
    ),
]
for before, after in edits:
    if source.count(before) != 1:
        raise SystemExit(f"repair anchor count was {source.count(before)}: {before[:50]}")
    source = source.replace(before, after)
path.write_text(source)
