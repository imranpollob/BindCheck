# PP evidence inventory

Inventory from `sprint/PP` at `c82eac6`. SHA-256 digests cover complete files.
CSV counts exclude the header and use parsed records, including any multiline fields.
Markdown counts cover body rows across all pipe tables in a file. A count of zero
can still include prose or code-block evidence. JSON counts are top-level entries.
Inputs marked **Build** contribute values or identities directly. **Reference** entries
record supporting or historical material. Freeze-2 evaluation artifacts are spent
for the current comparison, which is labeled DEV.

| Path | Rows | Unit | Role | SHA-256 |
|---|---:|---|---|---|
| `docs/FREEZE-2.md` | 6 | Markdown table rows | Build | `3536be6c16c25da26436b41b5fb4d214e9e07d37426f9d8d524b8ac09a8e7c85` |
| `reports/AZ1/REPORT.md` | 29 | Markdown table rows | Build | `92c2f5f8662a82ea87e99f750ec41ee42cda5833378405984a58fd181d9460ed` |
| `reports/R1/REPORT.md` | 35 | Markdown table rows | Reference | `45f5851f64ca8963776b16cb14dc313f65dc494bad3b0b81b118883f48974763` |
| `reports/R1/incidents.csv` | 50 | CSV records | Build | `fbfa59a2d385c87e53d45e4a003c9d588cb47265f21cf7355f3918833a41009b` |
| `reports/R1/summarize.py` | 66 | lines | Reference | `b0ca78d3f57a130b5b15c057dbb2b41a6a8fcb355d7dc3f77cd2680f2f2feadd` |
| `reports/R2/REPORT.md` | 44 | Markdown table rows | Reference | `f1116584f31e3aa51ab15810eafebfe216af6dd7435200fe5f7e7bf95a3d6cba` |
| `reports/R2/audits_read.csv` | 68 | CSV records | Build | `e40360419c409451d9c9fdd59ce0d5d073d0b055345ff86996a9d16da57bd928` |
| `reports/R2/excluded-borderline.csv` | 29 | CSV records | Reference | `b3b88a6ff91aa245a959d9f086c142c8d19ea979c92a30ff1da75b479da0a004` |
| `reports/R2/findings.csv` | 54 | CSV records | Build | `bf56f9358633d0b21c94361c91cb276995741336f7eeba3f0decc85772a88ca2` |
| `reports/R2/r2tool.py` | 95 | lines | Reference | `a6332457bbaeecf9554a0ac8ed1d82f2a2b5b733ee99cbd646a3d6e11e596064` |
| `reports/S2a/REPORT.md` | 122 | Markdown table rows | Build | `d78a24d1d8ce96785d20815381f4c1a86462e5fbee496ca8c06fe7fffafe3fc9` |
| `reports/S2a/revision1/analysis.log` | 221 | lines | Reference | `866364cce67d906c6991957f299b3e7e01e6b999a01896b99e7b6c88fcfb96a4` |
| `reports/S2a/revision1/set-h-recomputed-cards.csv` | 55 | CSV records | Build | `f32ea5b87e15f0ededb6aa0f4242026d340204ae0fe8d913fa9777bc56322be3` |
| `reports/S2a/revision1/set-h-recomputed-summary.json` | 2 | top-level entries | Reference | `ef44b57ea91612db9488eef9d43a50db9cf0f5b246015596aef76cd738cf17d9` |
| `reports/S2a/revision1/spent-family-changed-verdicts.csv` | 91 | CSV records | Reference | `ba9a7f7a46dc67e2145f65be8e1bb8e2fb342624f92a3376e78d2665279296bd` |
| `reports/S2a/revision1/spent-family-delta-complete.json` | 5 | top-level entries | Reference | `ea0ba4c262844003d2f76f47a3e02818b7b040d4bebe71c722bdd638bd4e0e09` |
| `reports/S2a/revision1/spent-family-delta.json` | 5 | top-level entries | Reference | `86f09121b920d0bf1a8f6ef538aceb994898e45e3a6b4771618c5dab8fda4065` |
| `reports/S2a/revision1/spent-family-ledger-278.csv` | 278 | CSV records | Build | `2b0993034637b272eacf2784c90be0493cf1f14552f2ad2ebaac1f4514a2ea43` |
| `reports/S4/REPORT-S4b.md` | 4 | Markdown table rows | Build | `eba0d8a552a8c1eb744305cf24c3a58f4aa0c6fece42f219aa5767b7f8a38c6d` |
| `reports/S4/REPORT-S4c.md` | 2 | Markdown table rows | Build | `445471274fc371e91b4af884b6b044e5fd8ff212af2940eb271c2efad4275000` |
| `reports/S4/REPORT.md` | 13 | Markdown table rows | Build | `c03b14e28cb37eee2d262c10df101f0efdf7aa2f8cf206ff4996b4b5ad363147` |
| `reports/freeze2/REPORT.md` | 14 | Markdown table rows | Reference | `483d16d49a3351f746b35ec697fa8316d182f3d93cab553b50be997b2bcad753` |
| `reports/freeze2/changed-verdicts.csv` | 8 | CSV records | Reference | `79484fa17b35b3c2d3a9c793591d84383f12163651735cf193b33cea6ce2627c` |
| `reports/freeze2/dev-ledger.csv` | 280 | CSV records | Build | `d59def9de2d1d9577fe04558d60f48d26b92411b3a7b514e8822eb8c649cac3f` |
| `reports/freeze2/dev-summary.json` | 11 | top-level entries | Reference | `9633ecb5e285900bfc832d1ab28c33edfc20571257e6f28307c39a97b858dcd2` |
| `reports/heldout/AMENDMENT-ADJUDICATION-SAMPLE.md` | 7 | Markdown table rows | Reference | `d2506123af86b816fff0291e005dd665393b8c90d38dc1d908511736c996506f` |
| `reports/heldout/CENSUS-CORRECTION.md` | 0 | Markdown table rows | Reference | `c27cad30b55176e3c8f0afcf080691d00021fb90ca73e9a22dfa28dc59ddd7b6` |
| `reports/heldout/CENSUS.md` | 24 | Markdown table rows | Reference | `fee4b4e1c00ea35c078c1ee872cb1c836ebc6e008dc851f4e422fb668df4251f` |
| `reports/heldout/GATE-CHECK.md` | 0 | Markdown table rows | Reference | `994bf2d53e7d327ed019630949c956b1280de5097c525df80d85fde26de6a75c` |
| `reports/heldout/HARNESS.md` | 0 | Markdown table rows | Reference | `eee14c8235e1ac9bd59acf72a21a2003598d7e5a90c4aa1a41f385161cc32904` |
| `reports/heldout/PREBUILD-SETUP.md` | 0 | Markdown table rows | Reference | `852f72aadb39de8876e6860006aa7b6a923680419134248bc653f5baae7ea483` |
| `reports/heldout/PREBUILD-V3.md` | 5 | Markdown table rows | Reference | `c6580133416233caa9568a6475785aeb7426dff8e764e11968efae0c5d087f11` |
| `reports/heldout/PREBUILD-VENDOR-CORRECTION.md` | 0 | Markdown table rows | Reference | `009c8210d76ee52d99b4626028cc29b2cba66d97e7db9a574ee0d576854cb689` |
| `reports/heldout/PREBUILD.md` | 5 | Markdown table rows | Reference | `b5830d0fbeb6baff5b851f26a154fe9832ff7255a6d56c43ea60128e7cbaec84` |
| `reports/heldout/PREREG.md` | 0 | Markdown table rows | Reference | `ded8891c3d02cacf531673c1671a956871721b5437344d783157f8a1fcc920ec` |
| `reports/heldout/REPORT.md` | 41 | Markdown table rows | Reference | `af0c7ed9d382c2d3861af8c1575a80481a42e79e88454bd879f9eceb26ff652f` |
| `reports/heldout/TOOL-SETUP.md` | 4 | Markdown table rows | Reference | `174976aeee7ab57b6cccaffbbcb8982b4be1df650d83561d4c594f24e432160b` |
| `reports/heldout/card-audit.csv` | 793 | CSV records | Reference | `d0282e78a81382e607b43092518843b7467c316fdc745d325d47ac22f985a32f` |
| `reports/heldout/gamma-delta-ledger.csv` | 654 | CSV records | Reference | `f3567bbbfe3db6301c542a003801d89612c3bcbd5f016c32ae9044678fbeaba3` |
| `reports/heldout/measurement-family-ledger.csv` | 277 | CSV records | Build | `4db41b8f90e943ebe2ee05a911e2e1bdac476b29931bc55a3f62f5dc86c5e2a9` |
| `reports/heldout/measurement-runtime-ledger.csv` | 277 | CSV records | Reference | `fb5a9e42d675ec98426d2325334aabf7857b487b4c02bd2e5202f86ef0e20eda` |
| `reports/heldout/measurement-summary.json` | 22 | top-level entries | Reference | `73de55641901cef4ec2f464efcb05a4e8420222147f5dc3ef35ccefc58c97bba` |
| `reports/heldout/per-verifier.csv` | 12264 | CSV records | Reference | `198c877cdd82ac89a7f2e3752a6384a8502647af68a19a027c0058b345f03f85` |
| `reports/heldout/prebuild-status-v3.csv` | 278 | CSV records | Reference | `2fde8b4a21752568513b6eb35f7099a4c57ba86dab9e98d84072883033ec2053` |
| `reports/heldout/prebuild-status.csv` | 278 | CSV records | Reference | `a35cb1061393c5e625e39bf114fe64be910bfde64d995305424279bdd71bb6b1` |
| `reports/heldout/prebuild-summary-v3.json` | 13 | top-level entries | Reference | `0e43ae761ed074da5676b20b88348224d868b7917f596f066ff1aae2a2650b51` |
| `reports/heldout/prebuild-summary.json` | 13 | top-level entries | Reference | `12cfa6e2f49c15ad4a88405fc82f5f6b9b66469a5005072759d43b06f6f9a4a6` |
| `reports/heldout/selected-families.csv` | 278 | CSV records | Build | `cf1b64bc68d90a790e63d965a3e3c607dc6f27e5250ba58d5968d4f792972d8b` |
| `reports/heldout/verifier-census-summary.json` | 14 | top-level entries | Reference | `645a71142cecef14059f24d3c96d0750d7c7fb5cd212a78a291c49d616c3c1d6` |
| `reports/heldout/warning-unblind-key.csv` | 793 | CSV records | Reference | `2290d5e1248f7b2c45a6643c25082310d50a4089235e7b0d80a8b440ab98def6` |
| `reports/labels/LABEL-ANALYSIS.md` | 58 | Markdown table rows | Reference | `d2a73db8f84648022c6e770a01ba592a0c6f4bcca453501907349db94b615b0e` |
| `reports/labels/label-summary.json` | 2 | top-level entries | Reference | `e3e701637cd8bddccb4eb0242c44092e63dbd7809ccd5578c4394e5e222fbb70` |
| `reports/labels/set-H-ledger.csv` | 100 | CSV records | Build | `d7cd3bc345d2daea3f60df506ef49af460a33a6ab76bf3f69b042793c6a6eb50` |

`reports/S1/generators.csv` is absent. The generator table reports a TODO.
`dataset/onchain-census.csv` is private and outside the build and inventory.
