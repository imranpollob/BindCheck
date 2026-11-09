# ZKredential prior-report and deployment review

Review date: 2026-11-09. Passive public material only. No address was called, no transaction was broadcast, and no maintainer was contacted.

## Search log

| Source | Exact query or read | Observed result |
|---|---|---|
| GitHub issues/PR search | `gh api 'search/issues?q=repo%3Aethpanda-org%2FETHShanghai-2025+ZKredential'` | No term match in [raw response](../../results/raw/impact/prior-search/zkredential-issues-prs.json). |
| GitHub issue/PR listing | `gh api 'repos/ethpanda-org/ETHShanghai-2025/issues?state=all&per_page=100'` | [Raw listing](../../results/raw/impact/prior-search/zkredential-all-issues.json); [PR 68](https://github.com/ethpanda-org/ETHShanghai-2025/pull/68) is project submission, not a security report. |
| GitHub commit path history | `gh api 'repos/ethpanda-org/ETHShanghai-2025/commits?path=projects/ZKredential/packages/zk-contracts/contracts/core/ComplianceGateway.sol&per_page=100'` | [Raw path history](../../results/raw/impact/prior-search/zkredential-path-commits.json) shows the addition commit, without a described binding repair. |
| README keywords | `rg -n -i 'audit|security|vulnerab|replay|proof.*wallet|proof.*recipient|mintpass' .../projects/ZKredential/README.md` | No matching audit/write-up claim in [raw search](../../results/raw/impact/prior-search/readme-keyword-search.txt). |
| Web search | `"ZKredential" "ComplianceGateway" vulnerability OR audit OR mint`; `"ZKredential" "verifyAndExecute" security` | Search engine returned no results for these exact queries. |

This bounded search did not find a prior public report of this relation. It does not establish novelty or absence of private reports.

## Deployment status

The pinned [README deployment section](https://github.com/ethpanda-org/ETHShanghai-2025/blob/23917814522bac494150c7e99a123aa15a448155/projects/ZKredential/README.md) and [Sepolia deployment manifest](https://github.com/ethpanda-org/ETHShanghai-2025/blob/23917814522bac494150c7e99a123aa15a448155/projects/ZKredential/packages/zk-contracts/deployments/multi-platform-sepolia-1760808806623.json) list verifier, registry, and compliance-module testnet addresses. They do not supply a `ComplianceGateway`/`ZKRWATokenERC3643` pair for this mint path. Public explorer pages for the listed verifier and module were unavailable through the passive browser tool; balance and bytecode correspondence are **MISSING**. A live funded instance of the tested consumer was not established. The safest deployment status is `UNKNOWN`.
