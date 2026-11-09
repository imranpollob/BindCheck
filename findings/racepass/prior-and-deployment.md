# RacePass prior-report and deployment review

Review date: 2026-11-09. Passive public material only. No address was called, no transaction was broadcast, and no maintainer was contacted.

## Search log

| Source | Exact query or read | Observed result |
|---|---|---|
| GitHub issues/PR search | `gh api 'search/issues?q=repo%3AServesh21%2FRacePass+mintPass'` | No term match in [raw response](../../results/raw/impact/prior-search/racepass-issues-prs.json). |
| GitHub issue/PR listing | `gh api 'repos/Servesh21/RacePass/issues?state=all&per_page=100'`; `gh api 'repos/Servesh21/RacePass/pulls?state=all&per_page=100'` | [Issues](../../results/raw/impact/prior-search/racepass-all-issues.json) and [PRs](../../results/raw/impact/prior-search/racepass-all-pulls.json) include [PR 1, “Credientals fix”](https://github.com/Servesh21/RacePass/pull/1). Its [file list](../../results/raw/impact/prior-search/racepass-credentials-pr-files.json) has no `EventPass.sol` change. |
| GitHub commit path history | `gh api 'repos/Servesh21/RacePass/commits?path=contracts/passes/EventPass.sol&per_page=100'` | [Raw path history](../../results/raw/impact/prior-search/racepass-path-commits.json) has feature/fix messages, but none documents the tested proof-to-credential relation. Commit message inspection is not a full patch audit. |
| README keywords | `rg -n -i 'audit|security|vulnerab|replay|proof.*wallet|proof.*recipient|mintpass' .../README.md` | [Raw search](../../results/raw/impact/prior-search/readme-keyword-search.txt) shows feature and security wording, not a published audit or report of this relation. |
| Web search | `"RacePass" "EventPass" vulnerability OR audit OR replay`; `"RacePass" "mintPass" credential proof replay` | Search engine returned no results for these exact queries. |

This bounded search did not find a prior public report of this relation. It does not establish novelty or absence of private reports.

## Deployment status

The pinned [README](https://github.com/Servesh21/RacePass/blob/abd54b5c541ac9d26f938a6bdbd78545526249e5/README.md) describes multiple target chains and has a testnet-deployment checklist item. The checked-in [address manifest](https://github.com/Servesh21/RacePass/blob/abd54b5c541ac9d26f938a6bdbd78545526249e5/deployed-addresses.json) lists verifiers, registries, and `PassFactory`, but no deployed `EventPass` instance. The manifest alone does not establish chain, current bytecode, funding, or a live pass instance. A live funded instance of the tested consumer was not established; deployment status is `UNKNOWN`.
