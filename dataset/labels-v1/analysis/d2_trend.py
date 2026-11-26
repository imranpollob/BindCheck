#!/usr/bin/env python3
"""D2: binding findings per year, normalized by in-scope ZK audit reports and by labeled findings.

Usage (from anywhere; stdlib only):
    python3 -I /home/pollmix/Coding/bc/BindCheck/dataset/labels-v1/analysis/d2_trend.py

Inputs (read-only):
    dataset/audit-sweep/merged/all_reports.csv   screen-1 decisions for every enumerated report
    dataset/labels-v1/LABELS-v1.csv              Pass 1 labels (report-only)
Output: prints a Markdown block (pasted into dataset/labels-v1/D2-TREND.md).

Unit of analysis: one in-scope report = one unique report_url among rows with screen1 == IN
(a URL with IN on one agent row and OUT on another counts as IN). Each report gets one year;
its labeled findings inherit that year.

Year resolution, per report: first 4-digit year 2015-2029 in the sweep rows' report_date;
else the labels' report_date for the same URL; else undated. Titles and URLs are NOT parsed
(they contain commit SHAs and file numbers that can match a year regex).

Primary denominator excludes IN reports whose finding text was not public, so they could not
contribute a numerator (sweep notes: "findings not public", "findings are not on the
competition page", "summary-only pdf"). Sensitivity: all IN reports.

Metrics (computed for all binding items and for core = binding with PSS != Y):
  A. share of in-scope reports with >= 1 binding finding (binomial; Wilson 95% CI)  [primary]
  B. binding findings per in-scope report (clustered count rate; 95% percentile CI from a
     seeded cluster bootstrap over reports; the largest single-report contribution is shown)
  C. binding findings / labeled findings (binding Y + N, duplicates and U removed; Wilson CI).
     Labeled findings are pre-screened candidates, not all ZK findings, and cluster in reports.
Pre-specified comparison window: 2023-2025 (the years with ~40+ reports). 2021-2022 pooled;
2026 partial. Trend test: Cochran-Armitage (scores 0,1,2) on metric A over 2023-2025.
"""
import collections as C, csv, hashlib, math, pathlib, random, re

ROOT = pathlib.Path(__file__).resolve().parents[2]
REPORTS = ROOT / "audit-sweep/merged/all_reports.csv"
LABELS = ROOT / "labels-v1/LABELS-v1.csv"
SEED = 20261125
NBOOT = 10000
YEAR_RE = re.compile(r"\b(20(?:1[5-9]|2\d))\b")
NONPUBLIC = ("findings not public", "findings are not on the competition", "summary-only pdf")
BINS = ["2021-2022", "2023", "2024", "2025", "2026 (partial)", "undated"]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def year_of(s):
    m = YEAR_RE.search(s or "")
    return m.group(1) if m else None


def bin_of(y):
    if y is None:
        return "undated"
    y = int(y)
    if y <= 2022:
        return "2021-2022"
    return "2026 (partial)" if y == 2026 else str(y)


def wilson(k, n, z=1.959964):
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def boot_rate(counts, rng):
    n = len(counts)
    if n == 0:
        return float("nan"), float("nan")
    s = sorted(sum(counts[rng.randrange(n)] for _ in range(n)) / n for _ in range(NBOOT))
    return s[int(0.025 * NBOOT)], s[int(0.975 * NBOOT) - 1]


def cochran_armitage(ks, ns, scores=(0, 1, 2)):
    N, K = sum(ns), sum(ks)
    p = K / N
    t = sum(s * (k - n * p) for s, k, n in zip(scores, ks, ns))
    v = p * (1 - p) * (sum(s * s * n for s, n in zip(scores, ns)) - sum(s * n for s, n in zip(scores, ns)) ** 2 / N)
    z = t / math.sqrt(v) if v > 0 else float("nan")
    return z, math.erfc(abs(z) / math.sqrt(2))


def main():
    rows = [r for r in csv.DictReader(open(REPORTS)) if r["screen1"] in ("IN", "OUT")]
    labels_all = [r for r in csv.DictReader(open(LABELS))]
    labels = [r for r in labels_all if not r["dup_of"] and r["binding"] in ("Y", "N")]
    in_urls = {r["report_url"].strip() for r in rows if r["screen1"] == "IN"}
    assert all(r["report_url"].strip() for r in rows if r["screen1"] == "IN"), "blank URL among IN rows"
    by_url = C.defaultdict(list)
    for r in rows:
        if r["report_url"].strip() in in_urls:
            by_url[r["report_url"].strip()].append(r)
    lab_date = C.defaultdict(list)
    for r in labels_all:
        lab_date[r["report_url"].strip()].append(r["report_date"])

    rep = {}  # url -> dict(year, source, nonpublic)
    src_count = C.Counter()
    for u, rs in by_url.items():
        y = next((year_of(r["report_date"]) for r in rs if year_of(r["report_date"])), None)
        src = "sweep"
        if y is None:
            y = next((year_of(d) for d in lab_date.get(u, []) if year_of(d)), None)
            src = "labels" if y else "none"
        src_count[src] += 1
        txt = " ".join((r["notes"] + " " + r["screen1_reason"]).lower() for r in rs)
        rep[u] = dict(year=y, nonpublic=any(k in txt for k in NONPUBLIC))

    missing = [r["item_id"] for r in labels if r["report_url"].strip() not in rep]
    assert not missing, f"labels not in IN reports: {missing}"
    for r in labels:
        r["_bin"] = bin_of(rep[r["report_url"].strip()]["year"])
        r["_core"] = r["binding"] == "Y" and r["proof_system_soundness"] != "Y"
    Y = [r for r in labels if r["binding"] == "Y"]
    core = [r for r in Y if r["_core"]]
    assert len(Y) == 103 and len(core) == 87, (len(Y), len(core))

    out = []
    w = out.append
    w("<!-- generated by analysis/d2_trend.py; do not hand-edit this block -->")
    w(f"- Inputs: `all_reports.csv` sha256 `{sha(REPORTS)}`; `LABELS-v1.csv` sha256 `{sha(LABELS)}`")
    nin_rows = sum(1 for r in rows if r["screen1"] == "IN")
    npub = sum(1 for v in rep.values() if v["nonpublic"])
    w(f"- Reconciliation: {nin_rows} IN rows -> {len(rep)} unique report URLs (FUNNEL.md's 343 dedups on a different key; "
      f"its count is not reused). {npub} of these had no public finding text and are excluded from the primary denominator, "
      f"leaving **{len(rep) - npub}**.")
    w(f"- Year source per report: sweep date {src_count['sweep']}, labels date {src_count['labels']}, undated {src_count['none']}.")
    yb = C.Counter(r["_bin"] for r in Y)
    w(f"- Binding findings per bin under this year rule: {dict((b, yb[b]) for b in BINS)} "
      f"(CHARACTERIZATION.md, which reads the label's own date, has 2021-22: 6, 2023: 13, 2024: 20, 2025: 39, 2026: 9, n/a: 16).")
    w("")

    def table(items, denom_urls, title, rng):
        reps_bin = C.defaultdict(list)
        for u in denom_urls:
            reps_bin[bin_of(rep[u]["year"])].append(u)
        per_rep = C.Counter(r["report_url"].strip() for r in items)
        lab_bin = C.Counter(r["_bin"] for r in labels)
        w(f"#### {title}")
        w("")
        w("| year | in-scope reports | reports with >=1 binding | A: share [Wilson 95%] | binding findings | "
          "B: per report [bootstrap 95%] | max from one report | labeled findings | C: binding/labeled [Wilson 95%] |")
        w("|---|---|---|---|---|---|---|---|---|")
        res = {}
        for b in BINS:
            us = reps_bin[b]
            n = len(us)
            counts = [per_rep[u] for u in us]
            k = sum(1 for c in counts if c > 0)
            f = sum(counts)
            pa, la, ha = wilson(k, n)
            lb, hb = boot_rate(counts, rng)
            L = lab_bin[b]
            fb = sum(1 for r in items if r["_bin"] == b)
            pc, lc, hc = wilson(fb, L)
            res[b] = (k, n, f, fb, L)
            note = "" if f == fb else f" ({fb - f} more outside denominator)"
            w(f"| {b} | {n} | {k} | {pa:.2f} [{la:.2f}, {ha:.2f}] | {f}{note} | "
              f"{f / n:.2f} [{lb:.2f}, {hb:.2f}] | {max(counts) if counts else 0} | {L} | {pc:.2f} [{lc:.2f}, {hc:.2f}] |")
        win = ["2023", "2024", "2025"]
        zA, pA = cochran_armitage([res[b][0] for b in win], [res[b][1] for b in win])
        zC, pC = cochran_armitage([res[b][3] for b in win], [res[b][4] for b in win])
        w("")
        w(f"Cochran-Armitage trend over 2023-2025: metric A z = {zA:.2f}, p = {pA:.3f}; metric C z = {zC:.2f}, p = {pC:.3f}.")
        w("")
        return res

    primary = [u for u, v in rep.items() if not v["nonpublic"]]
    allin = list(rep)
    rng = random.Random(SEED)
    w("### Primary denominator (in-scope reports with public finding text)")
    w("")
    resP = table(Y, primary, "All binding findings (103)", rng)
    resC = table(core, primary, "Core binding findings (87; PSS = Y excluded)", rng)
    w("### Sensitivity: all in-scope reports (incl. those with no public finding text)")
    w("")
    table(Y, allin, "All binding findings (103), all IN reports", rng)

    # Undated-allocation bounds on metric A (all 103, primary denominator)
    w("### Sensitivity: allocating the undated reports adversarially (metric A, all 103, primary denominator)")
    w("")
    w("| undated reports assigned to | 2023 share | 2025 share | CA z (2023-2025) | p |")
    w("|---|---|---|---|---|")
    k_u, n_u = resP["undated"][0], resP["undated"][1]
    for tgt in ("2023", "2025"):
        ks = [resP[b][0] + (k_u if b == tgt else 0) for b in ("2023", "2024", "2025")]
        ns = [resP[b][1] + (n_u if b == tgt else 0) for b in ("2023", "2024", "2025")]
        z, p = cochran_armitage(ks, ns)
        w(f"| {tgt} | {ks[0] / ns[0]:.2f} | {ks[2] / ns[2]:.2f} | {z:.2f} | {p:.3f} |")
    w("")
    # undated reports by auditor (differential missingness)
    und = C.Counter(by_url[u][0]["auditor_or_platform"] for u in primary if rep[u]["year"] is None)
    w(f"Undated primary-denominator reports by source: {dict(und.most_common())}.")
    w("")
    w(f"Bootstrap: {NBOOT} resamples of reports within each bin, seed {SEED}.")
    print("\n".join(out))


if __name__ == "__main__":
    main()
