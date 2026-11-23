# blocked (firms-1)

| time (UTC) | source | url | type | note |
|---|---|---|---|---|
| 2026-11-23 ~02:00 | Veridise | https://veridise.com/audits-archive/company/<co>/<report>/ (167 URLs from audit-report-sitemap.xml) | rate-limit | HTTP 429 on 61/167 page fetches at 4 parallel connections. No login/CAPTCHA. Orchestrator notified. Plan: retry the 61 failed URLs serially at >=3 s spacing after other sources; not bypassed. |

## Update 2026-11-23 (orchestrator instruction)
- Retry policy now: strictly serial, ~10 s between requests, 60 s backoff on any new 429, no parallel requests to veridise.com. A 4 s-spacing serial retry loop was started before the instruction arrived and was stopped (TaskStop) on receipt; it fetched a few pages at 4 s spacing. If still throttled after one slow pass, stop and report.

## Guard slips (disclosed)
Held-out guard was run in the same shell command as the follow-up requests (output not read first) for these batches; all results were ALLOWED:
- Zellic: succinctlabs/blobstreamx, brevis-network/brevis-sdk, succinctlabs/telepathy-contracts, nocturne-xyz/protocol, portalgateme/darkpool-v1-zk-contracts.
- ToB: succinctlabs/telepathy, scroll-tech/zkevm-circuits, iden3/circuits, automata-network/automata-dcap-attestation, zkonduit/ezkl, alexander-camuto/halo2-solidity-verifier, zkonduit/halo2-solidity-verifier, scroll-tech/zkvm-prover, scroll-tech/scroll-contracts, AztecProtocol/AZTEC.
- Requests made BEFORE any guard run (later guarded, ALLOWED): AztecProtocol/aztec-v1 (redirect target of AZTEC commit URL and tree page), succinctlabs/telepathy-circuits (HTTP probes). Only HTTP status / directory listings were fetched; no code was read.

| 2026-11-23 ~01:25 | Consensys Diligence | https://diligence.consensys.io/audits/ -> https://diligence.security/audits/ (and /sitemap.xml) | captcha | HTTP 403, `cf-mitigated: challenge`, Cloudflare "Just a moment..." page. Not bypassed. Orchestrator notified; needs author browser. |
