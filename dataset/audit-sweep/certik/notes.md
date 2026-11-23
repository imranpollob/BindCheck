# CertiK sweep notes
Date: 2026-11-23. Browser: author's Chrome on Linux (Browser 2), one tab, read-only, closed at end.

## Result
16 queries, 0 reports IN, 0 KEEP, 0 BORDERLINE. reports.csv and findings.csv hold headers only.

## Ambiguity / limitation
- PROTOCOL §6 says to use the terms in the "project/audit search". Skynet's search box matches project, quest, exchange and wallet *names* only. It does not search inside audit text, so the technical terms mostly return fuzzy name hits (e.g. 'halo2' -> Halo tokens). Result counts are visible dropdown entries plus 'Show more' counts and are approximate. 'public input' and 'public signals' showed identical, truncated dropdowns; 15 is a lower bound.
- The ZK-looking hits (zkSync, ZKNation, ZK Darkpool, ZK Email, Xsolla ZK) each show "CertiK Audit: No". zkSync lists 24 third-party audits (e.g. OpenZeppelin, 02/05/2025); those belong to other auditors' sources, were not screened here and are not CertiK reports.
- skynet.certik.com/projects/<slug> URLs were guessed from the project names; titles confirmed each page.
- Quest "Securing ZK: A Tale of Two Bugs" was opened by accident (Enter on a stale result). It is educational, login-gated content, not an audit, and I did not use it.
- No page text was quoted, so no .txt evidence files or hashes were needed.
- The CertiK audit list cannot be enumerated by keyword here. Finding CertiK ZK audits would need CertiK's public GitHub audit repo or certik.com/resources, which were out of scope for this task.
- No GitHub requests; the held-out guard was not needed.
- Time: about 15 minutes.
