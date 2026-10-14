#!/usr/bin/env python3
"""T09: test whether a .proof file parses EXACTLY as a Borsh `EvmProof::V1` wrapper (the layout written by the
Halo2-era Rust harness `create_or_load_agg_agg_final_evm_proof` at tag zk-circuits-v1.1.12):
  u8 enum tag(0=V1) | Vec<u8> proof (u32 LE len) | Vec<[u8;32]> agg_instances (u32 LE len) |
  [u8;32] old_root | [u8;32] new_root | Vec<[u8;32]> utxo_inputs (u32 LE len)
Reports the decoded structure and whether every byte is consumed. Words are shown big-endian, as the older
consumer reads bytes32; endianness of the Rust serialization is NOT independently verified here.
usage: python3 -I t09_decode_evm_proof.py <file.proof> <out.json>"""
import json, struct, sys

data = open(sys.argv[1], "rb").read()
off = 0
def take(n):
    global off
    if off + n > len(data):
        raise ValueError(f"truncated at offset {off}, need {n} more bytes")
    chunk = data[off:off + n]; off += n; return chunk
res = {"file_bytes": len(data), "layout": "Borsh EvmProof::V1 (hypothesis from the Halo2-era harness)"}
try:
    tag = take(1)[0]
    plen = struct.unpack("<I", take(4))[0]; take(plen)
    n1 = struct.unpack("<I", take(4))[0]; agg = [take(32) for _ in range(n1)]
    old = take(32); new = take(32)
    n2 = struct.unpack("<I", take(4))[0]; utxo = [take(32) for _ in range(n2)]
    res.update(enum_tag=tag, proof_bytes=plen, agg_instances=n1, utxo_inputs=n2, bytes_consumed=off,
               exact_fit=(off == len(data)),
               old_root_be="0x" + old.hex(), new_root_be="0x" + new.hex(),
               utxo_triples=[{"slot": i // 3, "root": "0x" + utxo[i].hex(), "mint_burn_hash": "0x" + utxo[i + 1].hex(),
                              "value_be": int.from_bytes(utxo[i + 2], "big"), "value_le": int.from_bytes(utxo[i + 2], "little")}
                             for i in range(0, n2 - n2 % 3, 3)])
    res["all_values_zero"] = all(t["value_be"] == 0 and t["value_le"] == 0 for t in res["utxo_triples"])
    res["all_mint_burn_hashes_zero"] = all(int(t["mint_burn_hash"], 16) == 0 for t in res["utxo_triples"])
except Exception as e:
    res.update(parse_error=str(e), exact_fit=False)
json.dump(res, open(sys.argv[2], "w"), indent=2); open(sys.argv[2], "a").write("\n")
print(json.dumps({k: v for k, v in res.items() if k != "utxo_triples"}, indent=1))
for t in res.get("utxo_triples", []):
    print(f"  slot {t['slot']}: mint/burn hash={t['mint_burn_hash'][:14]}.. value={t['value_be']}")
