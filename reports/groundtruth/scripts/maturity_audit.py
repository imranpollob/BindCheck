#!/usr/bin/env python3
"""Apply the pre-registered maturity rubric (reports/groundtruth/PLAN.md, C5) to the 278 sampled families.

Evidence: source-corpus-v2 metadata and the README fetched at the pinned commit
by fetch_readmes.py. No analyzer, no clone, no on-chain query. Explorer links
are constructed strings and are never requested.

Outputs:
  reports/groundtruth/maturity-audit.csv   one row per sampled family (proposal + evidence)
  reports/groundtruth/maturity-summary.json counts (agreement matrix, flags)
  review/maturity/MATURITY-REVIEW.csv      the same rows plus blank human decision columns

Usage: python3 -I reports/groundtruth/scripts/maturity_audit.py --sample <selected-families.csv>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import re
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[3]
READMES = ROOT / "results/raw/groundtruth/readmes"
ORDER = ["verified-deployed", "deployed-address-in-docs", "testnet-address-in-docs", "audited-production", "hackathon-student", "unclassified"]
PREREG_ORDER = ["verified-deployed", "deployed-address-in-docs", "audited-production", "hackathon-student", "unclassified"]

EXPLORERS = {
    "1": "https://etherscan.io/address/", "10": "https://optimistic.etherscan.io/address/",
    "137": "https://polygonscan.com/address/", "8453": "https://basescan.org/address/",
    "42161": "https://arbiscan.io/address/", "59144": "https://lineascan.build/address/",
    "324": "https://explorer.zksync.io/address/", "56": "https://bscscan.com/address/",
    "100": "https://gnosisscan.io/address/", "534352": "https://scrollscan.com/address/",
}
ADDR = re.compile(r"(?<![0-9a-fA-Fx])0x[0-9a-fA-F]{40}(?![0-9a-fA-F])")
TESTNET = re.compile(r"sepolia|goerli|g[oö]rli|holesky|hoodi|testnet|amoy|mumbai|fuji|devnet|chiado|alfajores|localhost|127\.0\.0\.1|anvil|hardhat node|ganache|local ?chain|local ?network", re.I)
MAINNET = re.compile(r"mainnet|\bethereum\b(?! sepolia)|arbitrum one|optimism(?! sepolia)|polygon pos|\bbsc\b|bnb chain|avalanche c-chain|gnosis chain|\blinea\b(?! sepolia)|zksync era|(?<!sepolia\.)(?<!goerli\.)(?<!holesky\.)(?<!-sepolia\.)(etherscan\.io|basescan\.org|arbiscan\.io|polygonscan\.com|lineascan\.build|scrollscan\.com|bscscan\.com|gnosisscan\.io|explorer\.zksync\.io)", re.I)
DEPLOY_CUE = re.compile(r"deploy|contract address|address(es)?\b|verifier at|mainnet|explorer|scan\.(io|org|com|build)", re.I)
EXPLORER_URL = re.compile(r"https?://[^\s)\]>'\"]*(?:scan|explorer|blockscout)[^\s)\]>'\"]*", re.I)
AUDIT_LINK = re.compile(r"https?://[^\s)\]>'\"]*audit[^\s)\]>'\"]*", re.I)
FIRMS = r"(trail ?of ?bits|openzeppelin|zellic|veridise|spearbit|cantina|code4rena|code ?arena|sherlock|consensys diligence|least ?authority|peckshield|certik|hacken|halborn|quantstamp|sigma ?prime|chainsecurity|nethermind|runtime verification|hexens|zksecurity|hashcloak|cyfrin|dedaub|guardian audits|pashov|ottersec|macro|yacademy|kudelski|ncc group|oak security|ackee|mixbytes|statemind|secure3|zokyo|three sigma|blocksec|salus|beosin|slowmist)"
AUDIT_PHRASE = re.compile(rf"(audited by|audit(?:ed)? (?:report )?(?:by|from)|security review by|reviewed by)\s+(?:the\s+)?{FIRMS}|{FIRMS}\s+(?:security\s+)?(audit|security review|audit report)", re.I)
NOT_AUDITED = re.compile(r"not (?:been |yet )?audited|unaudited|no audit|has not undergone (?:a |any )?(?:security )?audit|without (?:an? )?audit", re.I)
HACKATHON = re.compile(r"hackathon|ethglobal|eth ?global|devfolio|devpost|dorahacks|akindo|bootcamp|\bcourse\b|assignment|homework|\bstudent\b|university project|class project|capstone|eth ?india|eth ?denver|eth ?online|eth ?tokyo|eth ?bogota|eth ?lisbon|eth ?waterloo|eth ?seoul|eth ?bangkok|eth ?shanghai|encode club|buidlguidl|speedrun ethereum|hacker ?house|gitcoin", re.I)
DO_NOT_DEPLOY = re.compile(r"do not deploy|don'?t deploy|not for production|not production[- ]ready|do not use (?:it )?in production|not (?:intended|meant) for production|not (?:be )?used in production", re.I)
PROTOTYPE = re.compile(r"research prototype|proof[- ]of[- ]concept|\bpoc\b|\bdemo\b|\btoy\b|educational|experimental|prototype|for learning", re.I)


# Manual spot-check notes by the L4 lane (AI-assisted; not independent annotation).
# Covers every v1.1 deployed-address proposal and every v1 audited-production proposal.
SPOT_CHECK = {
    "39": "X Layer (OKX) explorer link; plausible mainnet deployment",
    "43": "Optimism mainnet explorer link, but README text says 'officially on the test networks for now' - conflicting",
    "51": "README lists separate Mainnet and Testnet contract addresses; repository name suggests a ZKU course project",
    "52": "Arc explorer link; whether the Arc network is a mainnet was not verified",
    "64": "README table states 'Arc Mainnet (5042)'",
    "65": "README log line 'Connected to Base Mainnet (Chain ID: 8453)'; the address is an oracle role, not necessarily the project verifier",
    "67": "Gnosis Chain explorer link for the deployed RealEmailVerifier",
    "71": "Mainnet chainId 177 and Testnet chainId 133 both listed",
    "80": "FALSE POSITIVE: third-party USDC token addresses in an env template",
    "82": "ThunderCore explorer link plus Kovan link; ETHBoston hackathon project",
    "94": "explorer host thesecurityteam.rocks; network unknown",
    "95": "FALSE POSITIVE: README heading 'XDC-testnet'; apothem is the XDC testnet",
    "217": "FALSE POSITIVE: coston2 is the Flare testnet",
    "103": "v1 audited FALSE POSITIVE: CI workflow URL 'seeded-bug-audit-lab'",
    "119": "v1 audited FALSE POSITIVE: self-declared shields.io 'Security-Audited' badge",
    "134": "v1 audited FALSE POSITIVE: localhost URL",
    "157": "v1 audited: link is to the upstream Tornado Cash ABDK review; README also says not audited",
}


def window(text: str, start: int, end: int, width: int = 300) -> str:
    return text[max(0, start - width): end + width]


def excerpt(text: str, start: int, end: int, width: int = 90) -> str:
    return re.sub(r"\s+", " ", text[max(0, start - width): end + width]).strip()[:260]


def analyse_readme(text: str) -> dict:
    ev: dict = {"addresses_mainnet": [], "addresses_testnet": [], "addresses_unqualified": [],
                "audit_links": [], "audit_phrases": [], "hackathon": [], "flags": set()}
    for m in ADDR.finditer(text):
        addr = m.group(0)
        if int(addr, 16) == 0:
            continue
        w = window(text, m.start(), m.end())
        if not DEPLOY_CUE.search(w):
            continue
        is_test, is_main = bool(TESTNET.search(w)), bool(MAINNET.search(w))
        urls = [u for u in EXPLORER_URL.findall(w) if addr.lower() in u.lower()]
        item = {"address": addr, "explorer_url_in_readme": urls[0] if urls else "", "excerpt": excerpt(text, m.start(), m.end())}
        if is_main:
            ev["addresses_mainnet"].append(item)
        elif is_test:
            ev["addresses_testnet"].append(item)
        else:
            ev["addresses_unqualified"].append(item)
    for m in AUDIT_LINK.finditer(text):
        url = m.group(0).rstrip(".,;")
        if re.search(r"npm[ -]audit|yarn audit|audit-ci|cargo-audit|/npm/", url, re.I):
            continue
        ev["audit_links"].append(url)
    for m in AUDIT_PHRASE.finditer(text):
        ev["audit_phrases"].append(excerpt(text, m.start(), m.end(), 60))
    for m in HACKATHON.finditer(text):
        ev["hackathon"].append(excerpt(text, m.start(), m.end(), 60))
    if DO_NOT_DEPLOY.search(text):
        ev["flags"].add("DO-NOT-DEPLOY")
    if PROTOTYPE.search(text):
        ev["flags"].add("PROTOTYPE/POC/DEMO")
    if NOT_AUDITED.search(text):
        ev["flags"].add("NOT-AUDITED")
    if TESTNET.search(text) and not MAINNET.search(text):
        ev["flags"].add("TESTNET-ONLY")
    return ev


# ---------------- v1.1 (post-hoc refinement, PLAN.md Addendum A) ----------------
TEST_HOST = re.compile(r"sepolia|goerli|holesky|hoodi|rinkeby|ropsten|kovan|mumbai|amoy|fuji|cardona|chiado|alfajores|devnet|testnet", re.I)
TESTNET11 = re.compile(TESTNET.pattern + r"|rinkeby|ropsten|kovan|cardona|testned", re.I)
MAINNET11 = re.compile(r"\bmain ?net\b|mainnet|\bethereum mainnet\b|\bL1 mainnet\b|production deployment", re.I)
DOUBT = re.compile(r"example|placeholder|\blocal\b|localhost|account ?#|private ?key|donat|\bUSDC\b|\bUSDT\b|\bWETH\b|\bDAI\b|token address|\.env|_ADDRESS=", re.I)
AUDIT_DOC = re.compile(r"\.pdf\b|/audits?(?:/|\b)|trailofbits|openzeppelin\.com/security|zellic\.io|veridise|spearbit|cantina\.xyz|code4rena|sherlock|consensys\.(?:net|io)/diligence|leastauthority|peckshield|certik|hacken|halborn|quantstamp|sigmaprime|chainsecurity|nethermind|zksecurity|hashcloak|cyfrin", re.I)
AUDIT_EXCLUDE = re.compile(r"shields\.io|badge|/actions/|localhost|127\.0\.0\.1|npm[ -]audit", re.I)
ACADEMIC = re.compile(r"universit|thesis|dissertation", re.I)


def placeholder_addr(addr: str) -> bool:
    body = addr[2:].lower()
    return len(set(body)) <= 4 or "deadbeef" in body or "abcd1234" in body or body.startswith("1234567890")


def analyse_readme_v11(text: str, extra_meta: str) -> dict:
    ev = {"main": [], "test": [], "mixed": [], "doubtful": [], "audit_links": [], "audit_phrases": [],
          "hackathon": [], "academic": [], "flags": set()}
    lines = text.split("\n")
    offsets, pos = [], 0
    for ln in lines:
        offsets.append(pos); pos += len(ln) + 1
    for m in ADDR.finditer(text):
        addr = m.group(0)
        if int(addr, 16) == 0 or placeholder_addr(addr):
            continue
        li = max(i for i, o in enumerate(offsets) if o <= m.start())
        ctx = "\n".join(lines[max(0, li - 1): li + 2])
        urls = [u for u in EXPLORER_URL.findall(ctx) if addr.lower() in u.lower()]
        item = {"address": addr, "explorer_url_in_readme": urls[0] if urls else "", "excerpt": re.sub(r"\s+", " ", ctx)[:260]}
        if DOUBT.search(ctx):
            ev["doubtful"].append(item); continue
        if urls:
            host = re.sub(r"^https?://", "", urls[0]).split("/")[0]
            (ev["test"] if TEST_HOST.search(host) else ev["main"]).append(item)
            continue
        if not DEPLOY_CUE.search(ctx):
            continue
        t, mn = bool(TESTNET11.search(ctx)), bool(MAINNET11.search(ctx))
        if t and mn:
            ev["mixed"].append(item)
        elif mn:
            ev["main"].append(item)
        elif t:
            ev["test"].append(item)
    not_audited = bool(NOT_AUDITED.search(text))
    for m in AUDIT_LINK.finditer(text):
        url = m.group(0).rstrip(".,;`")
        if AUDIT_EXCLUDE.search(url) or not AUDIT_DOC.search(url):
            continue
        ev["audit_links"].append(url)
    for m in AUDIT_PHRASE.finditer(text):
        ev["audit_phrases"].append(excerpt(text, m.start(), m.end(), 60))
    for src in (text, extra_meta):
        for m in HACKATHON.finditer(src):
            ev["hackathon"].append(excerpt(src, m.start(), m.end(), 60))
        for m in ACADEMIC.finditer(src):
            ev["academic"].append(excerpt(src, m.start(), m.end(), 60))
    if not_audited:
        ev["flags"].add("NOT-AUDITED")
    if DO_NOT_DEPLOY.search(text):
        ev["flags"].add("DO-NOT-DEPLOY")
    if PROTOTYPE.search(text):
        ev["flags"].add("PROTOTYPE/POC/DEMO")
    if ev["test"] and not ev["main"] and not ev["mixed"]:
        ev["flags"].add("TESTNET-ONLY")
    if ev["doubtful"]:
        ev["flags"].add("DOUBTFUL-ADDRESS-CONTEXT")
    if ev["mixed"]:
        ev["flags"].add("MIXED-NETWORK-CUES")
    return ev


def propose_v11(evs: list[dict], sourcify: list[str]) -> tuple[str, str, str]:
    if sourcify:
        return "verified-deployed", "high", "exact Sourcify/GitHub source match recorded in v2_sourcify_evidence"
    if any(ev["main"] for ev in evs):
        return "deployed-address-in-docs", "medium", "address in a mainnet explorer URL or on a line with an explicit mainnet cue"
    if any(ev["mixed"] for ev in evs):
        return "deployed-address-in-docs", "low", "address line carries both mainnet and testnet cues"
    if any(ev["test"] for ev in evs):
        return "testnet-address-in-docs", "low", "address only in testnet explorer URLs or testnet-cued lines"
    links = [l for ev in evs for l in ev["audit_links"]]
    phrases = [p for ev in evs for p in ev["audit_phrases"]]
    contradiction = any("NOT-AUDITED" in ev["flags"] for ev in evs)
    if (links or phrases) and contradiction:
        return "unclassified", "low", "audit evidence contradicted by a not-audited statement (AUDIT-CONTRADICTION)"
    if links:
        return "audited-production", "medium", "README links an audit document"
    if phrases:
        return "audited-production", "low", "README names an auditor in an audit phrase (no link)"
    if any(ev["hackathon"] for ev in evs):
        return "hackathon-student", "medium", "hackathon/course/student cue in README or corpus metadata excerpt"
    if any(ev["academic"] for ev in evs):
        return "hackathon-student", "low", "academic cue (university/thesis) only"
    return "unclassified", "low", "no rubric evidence"


def propose(member_evs: list[dict], sourcify: list[str]) -> tuple[str, str, str]:
    if sourcify:
        return "verified-deployed", "high", "exact Sourcify/GitHub source match recorded in v2_sourcify_evidence"
    main = [a for ev in member_evs for a in ev["addresses_mainnet"]]
    if main:
        return "deployed-address-in-docs", "medium", "README address within 300 chars of a mainnet cue"
    test = [a for ev in member_evs for a in ev["addresses_testnet"]]
    unq = [a for ev in member_evs for a in ev["addresses_unqualified"]]
    links = [l for ev in member_evs for l in ev["audit_links"]]
    phrases = [p for ev in member_evs for p in ev["audit_phrases"]]
    if test:
        return "testnet-address-in-docs", "low", "README address near deployment cue but only testnet/local cues"
    if links:
        return "audited-production", "medium", "README links an audit report"
    if phrases:
        return "audited-production", "low", "README names an auditor in an audit phrase (no link)"
    if any(ev["hackathon"] for ev in member_evs):
        return "hackathon-student", "medium", "README names a hackathon/course/student context"
    if unq:
        return "unclassified", "low", "README address near a deployment cue but no network stated (not counted as deployed)"
    return "unclassified", "low", "no rubric evidence"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", required=True, type=pathlib.Path)
    a = ap.parse_args()
    with a.sample.open(newline="") as h:
        sample = list(csv.DictReader(h))
    with (ROOT / "dataset/source-corpus-v2.csv").open(newline="") as h:
        corpus = [r for r in csv.DictReader(h) if r["split"] == "EVAL"]
    receipts = {(r["repository"], r["commit"]): r for r in json.loads((READMES / "receipts.json").read_text())}
    members: dict[str, list[dict]] = {}
    for r in corpus:
        members.setdefault(r["v2_family_id"], []).append(r)

    out, matrix, matrix_v1, flags_count = [], Counter(), Counter(), Counter()
    for s in sample:
        fam = members[s["family_id"]]
        evs, evs11, member_notes, sourcify, readme_flags = [], [], [], [], set()
        for r in fam:
            rec = receipts.get((r["repository"], r["commit"]), {})
            k = rec.get("key")
            path = READMES / f"{k}.md" if k else None
            if path and path.is_file():
                text = path.read_text(encoding="utf-8", errors="replace")
                ev = analyse_readme(text)
                ev11 = analyse_readme_v11(text, r["v2_maturity_basis"])
            else:
                ev = analyse_readme("")
                ev11 = analyse_readme_v11("", r["v2_maturity_basis"])
                missing = "README-MISSING" if rec.get("method") == "api-readme" and rec.get("error", "").find("404") >= 0 else "README-FETCH-FAILED"
                ev["flags"] = {missing}
                ev11["flags"] |= {missing}
            evs.append(ev)
            evs11.append(ev11)
            readme_flags |= ev11["flags"]
            if r["v2_sourcify_evidence"]:
                sourcify += [x for x in r["v2_sourcify_evidence"].split("|") if x]
            member_notes.append(f"{r['repository']}@{r['commit'][:10]} stars={r['stars'] or 'MISSING'} archived={r['archived'] or 'MISSING'} fork={r['is_fork'] or 'MISSING'}")
        label_v1, _, _ = propose(evs, sourcify)
        label, conf, basis = propose_v11(evs11, sourcify)
        if "AUDIT-CONTRADICTION" in basis:
            readme_flags.add("AUDIT-CONTRADICTION")
        prereg = s["stratum"]
        matrix[(prereg, label)] += 1
        matrix_v1[(prereg, label_v1)] += 1
        for f in readme_flags:
            flags_count[f] += 1
        sourcify_links = []
        for item in sourcify:
            parts = item.split(":")
            if len(parts) >= 2:
                base = EXPLORERS.get(parts[0])
                sourcify_links.append((base + parts[1]) if base else f"chain {parts[0]} (no explorer mapping) {parts[1]}")
        addr_items = [a for ev in evs11 for a in ev["main"] + ev["mixed"] + ev["test"]]
        doubtful = [a for ev in evs11 for a in ev["doubtful"]]
        addr_links = []
        for it in addr_items[:3]:
            addr_links.append(it["explorer_url_in_readme"] or f"https://blockscan.com/address/{it['address']}")
        canon = s["repository"]
        row_basis = next((r["v2_maturity_basis"] for r in fam if r["repository"] == canon), "")
        out.append({
            "rank": s["rank"], "family_id": s["family_id"], "repository": canon, "commit": s["commit"],
            "family_members": len(fam),
            "prereg_stratum": prereg, "prereg_basis_excerpt": row_basis[:220],
            "proposed_label_v1": label_v1,
            "proposed_label": label, "confidence": conf, "proposal_basis": basis,
            "agrees_with_prereg": int(label == prereg),
            "l4_spot_check_note": SPOT_CHECK.get(s["rank"], ""),
            "flags": ";".join(sorted(readme_flags)),
            "deployed_address_explorer_links": " | ".join(sourcify_links + addr_links),
            "readme_address_excerpt": " || ".join(it["excerpt"] for it in addr_items[:2]),
            "doubtful_address_excerpt": " || ".join(it["excerpt"] for it in doubtful[:1]),
            "audit_report_links": " | ".join(sorted({l for ev in evs11 for l in ev["audit_links"]})[:4]),
            "audit_phrase_excerpt": " || ".join([p for ev in evs11 for p in ev["audit_phrases"]][:2]),
            "hackathon_excerpt": " || ".join([p for ev in evs11 for p in ev["hackathon"] + ev["academic"]][:2]),
            "metadata": " ; ".join(member_notes[:4]) + (" ; …" if len(member_notes) > 4 else ""),
            "readme_urls": " | ".join(receipts.get((r["repository"], r["commit"]), {}).get("url", "MISSING") for r in fam[:3]),
        })

    out.sort(key=lambda r: int(r["rank"]))
    fields = list(out[0])
    with (ROOT / "reports/groundtruth/maturity-audit.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fields); w.writeheader(); w.writerows(out)
    review_dir = ROOT / "review/maturity"; review_dir.mkdir(parents=True, exist_ok=True)
    with (review_dir / "MATURITY-REVIEW.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fields + ["human_label", "human_confidence", "reviewer", "date", "notes"])
        w.writeheader()
        for r in out:
            w.writerow({**r, "human_label": "", "human_confidence": "", "reviewer": "", "date": "", "notes": ""})
    summary = {
        "generated_by": "reports/groundtruth/scripts/maturity_audit.py",
        "rubric": "reports/groundtruth/PLAN.md section C5 (committed c63cfa1 before READMEs were fetched)",
        "families": len(out),
        "prereg_counts": dict(Counter(r["prereg_stratum"] for r in out)),
        "proposed_counts_v1_preregistered_rubric": dict(Counter(r["proposed_label_v1"] for r in out)),
        "agreement_total_v1_preregistered_rubric": sum(1 for r in out if r["proposed_label_v1"] == r["prereg_stratum"]),
        "matrix_prereg_to_v1": {f"{p} -> {q}": n for (p, q), n in sorted(matrix_v1.items())},
        "proposed_counts": dict(Counter(r["proposed_label"] for r in out)),
        "note": "proposed_label is the post-hoc v1.1 refinement (PLAN.md Addendum A); its agreement figures are descriptive, not pre-registered.",
        "agreement_total": sum(r["agrees_with_prereg"] for r in out),
        "agreement_by_prereg_stratum": {p: {"agree": sum(1 for r in out if r["prereg_stratum"] == p and r["agrees_with_prereg"]),
                                             "of": sum(1 for r in out if r["prereg_stratum"] == p)} for p in PREREG_ORDER},
        "matrix_prereg_to_proposed": {f"{p} -> {q}": n for (p, q), n in sorted(matrix.items())},
        "families_with_flag": dict(flags_count),
        "confidence_counts": dict(Counter(r["confidence"] for r in out)),
        "maturity_audit_csv_sha256": hashlib.sha256((ROOT / "reports/groundtruth/maturity-audit.csv").read_bytes()).hexdigest(),
    }
    (ROOT / "reports/groundtruth/maturity-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in ("proposed_counts", "agreement_total", "agreement_by_prereg_stratum", "families_with_flag")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
