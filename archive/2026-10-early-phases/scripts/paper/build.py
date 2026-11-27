#!/usr/bin/env python3
"""Build the sprint paper tables from local evidence using only the stdlib."""

import csv
import hashlib
import io
import json
import re
import sys
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path("paper/generated")
PATTERNS = ("P1", "P2", "P3", "P4", "P5")
VERDICTS = ("VIOLATION", "VERIFIED_WITHIN_SCOPE", "UNKNOWN")
APPLICABILITIES = ("APPLICABLE", "NOT_APPLICABLE", "UNKNOWN")
DEV = "DEV, not held-out"
SPENT = "Spent freeze-2 sample; " + DEV
INCIDENTS = "reports/R1/incidents.csv"
AUDIT_FINDINGS = "reports/R2/findings.csv"
AUDITS = "reports/R2/audits_read.csv"
AZ1 = "reports/AZ1/REPORT.md"
SET_H = "reports/labels/set-H-ledger.csv"
S2A = "reports/S2a/REPORT.md"
CANDIDATE_CARDS = "reports/S2a/revision1/set-h-recomputed-cards.csv"
SPENT_FAMILIES = "reports/S2a/revision1/spent-family-ledger-278.csv"
FREEZE_FAMILIES = "reports/heldout/measurement-family-ledger.csv"
SELECTED = "reports/heldout/selected-families.csv"
FREEZE = "docs/FREEZE-2.md"
FREEZE_DEV = "reports/freeze2/dev-ledger.csv"
S4 = "reports/S4/REPORT.md"
S4B = "reports/S4/REPORT-S4b.md"
S4C = "reports/S4/REPORT-S4c.md"
GENERATORS = "reports/S1/generators.csv"
CANONICALITY = "PUBLIC_INPUT_CANONICALITY_GUARD_NOT_FOUND"


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def match(pattern, text):
    found = re.findall(pattern, text, flags=re.MULTILINE)
    require(len(found) == 1, f"expected one match for {pattern!r}, got {len(found)}")
    return found[0]


def number_list(text):
    return [int(value) for value in re.findall(r"\d+", text)]


def percent(numerator, denominator):
    if not denominator:
        return None
    return f"{(Decimal(numerator) * 100 / denominator).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}%"


def ratio(numerator, denominator):
    return f"{numerator}/{denominator}" if denominator else "—"


class Evidence:
    """Read and hash the same snapshot of every input used by a table."""

    def __init__(self, root, sources):
        self.root = root
        self.sources = sources
        self.inputs = {}

    def read(self, path, parser):
        data = (self.root / path).read_bytes()
        entry = {"sha256": hashlib.sha256(data).hexdigest(), "parser": parser}
        self.inputs[path] = entry
        self.sources[path] = entry
        return data.decode("utf-8")

    def csv(self, path):
        text = self.read(path, "CSV")
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        headers = reader.fieldnames
        rows = list(reader)
        require(headers and all(headers) and len(headers) == len(set(headers)), f"{path}: invalid headers")
        require(all(None not in row and None not in row.values() for row in rows), f"{path}: invalid row width")
        return headers, rows

    def report(self, path, parser):
        return self.read(path, parser)


def markdown_table(text, headers):
    """Read the uniquely named pipe table. These evidence tables use plain cells."""
    def cells(line):
        return [cell.strip().replace("**", "").replace("`", "") for cell in line.strip()[1:-1].split("|")]

    lines = text.splitlines()
    starts = [
        i for i, line in enumerate(lines)
        if line.startswith("|") and tuple(cells(line)) == headers
    ]
    require(len(starts) == 1, f"expected one Markdown table with headers {headers}")
    start = starts[0]
    require(
        len(cells(lines[start + 1])) == len(headers)
        and all(re.fullmatch(r":?-+:?", cell) for cell in cells(lines[start + 1])),
        f"missing Markdown table separator for {headers}",
    )
    rows = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        row = cells(line)
        require(len(row) == len(headers), f"invalid Markdown table row width for {headers}")
        rows.append(row)
    require(rows, f"empty Markdown table with headers {headers}")
    return rows


def incidents(ev, scalar):
    _, records = ev.csv(INCIDENTS)
    require(len({row["case_id"] for row in records}) == len(records), "duplicate R1 case ID")
    require(all(row["class"] in (*PATTERNS, "OUT") for row in records), "unknown R1 class")
    require(all(row["exploited"] in {"yes", "whitehat", "no"} for row in records), "unknown R1 exploitation label")
    fields = ("loss_claimed_usd", "loss_confirmed_usd", "recovered_usd", "value_at_risk_usd")
    rows = []
    groups = {}
    for label in (*PATTERNS, "Other", "All"):
        key = "OUT" if label == "Other" else label
        selected = [row for row in records if row["class"] == key or label == "All"]
        counts = {key: sum(row["exploited"] == key for row in selected) for key in ("yes", "whitehat", "no")}
        amounts = {}
        for field in fields:
            known = [int(row[field]) for row in selected if row[field] != "UNKNOWN"]
            amounts[field] = {"known_sum": sum(known), "unknown": len(selected) - len(known)}
        groups[label] = {"cases": len(selected), "exploitation": counts, "amounts": amounts}
        display = [
            f"{item['known_sum']:,}" + (f" (+{item['unknown']} U)" if item["unknown"] else "")
            for item in amounts.values()
        ]
        rows.append([label, len(selected), counts["yes"], counts["whitehat"], counts["no"], *display])

    aztec = [row for row in records if row["case_id"] == "R1-005"]
    require(len(aztec) == 1, "R1-005 must identify a single Aztec Connect case")
    scalar("RoneCases", len(records), INCIDENTS, "CSV case rows")
    scalar("RoneInClassCases", len(records) - groups["Other"]["cases"], INCIDENTS, "P1–P5 case rows")
    scalar("RoneClaimedLossUSD", groups["All"]["amounts"]["loss_claimed_usd"]["known_sum"],
           INCIDENTS, "sum of numeric loss_claimed_usd cells")
    scalar("RoneConfirmedLossUSD", groups["All"]["amounts"]["loss_confirmed_usd"]["known_sum"],
           INCIDENTS, "sum of numeric loss_confirmed_usd cells")
    scalar("AztecLossUSD", int(aztec[0]["loss_confirmed_usd"]), INCIDENTS, "R1-005 loss_confirmed_usd")
    scalar("AztecClaimedLossUSD", int(aztec[0]["loss_claimed_usd"]), INCIDENTS, "R1-005 loss_claimed_usd")
    return (
        ["Class", "Cases", "Yes", "Whitehat", "No", "Claimed USD", "Confirmed USD", "Recovered USD", "At risk USD"],
        rows,
        {"raw": groups, "caption_note": "USD sums use known amounts. +n U marks unknown amounts.",
         "notes": ["Other = R1 OUT. Yes/Whitehat/No describe exploitation.",
                                 "Monetary columns sum known USD cells. +n U counts unknown amounts."]},
    )


def audits(ev, scalar):
    _, findings = ev.csv(AUDIT_FINDINGS)
    _, audit_rows = ev.csv(AUDITS)
    severity = ("C", "H", "M", "L", "I", "UNKNOWN")
    require(all(row["class"] in PATTERNS and row["severity"] in severity
                and row["needs_circuit_to_detect"] in {"yes", "no", "unclear"} for row in findings),
            "unexpected R2 class, severity or needs-circuit label")
    require(len({row["finding_id"] for row in findings}) == len(findings), "duplicate R2 finding ID")
    audit_urls = {row["report_url"] for row in audit_rows}
    require(len(audit_urls) == len(audit_rows) and {row["report_url"] for row in findings} <= audit_urls,
            "R2 findings must join to unique audit reports")
    binding = [row for row in findings if row["class"] != "P4"]
    rows = []
    groups = {}
    for label, items in [
        *((p, [row for row in findings if row["class"] == p]) for p in PATTERNS),
        ("Binding", binding),
        ("All", findings),
    ]:
        counts = Counter(row["severity"] for row in items)
        needs = Counter(row["needs_circuit_to_detect"] for row in items)
        share = percent(needs["yes"], len(items))
        groups[label] = {"severity": {s: counts[s] for s in severity}, "findings": len(items),
                         "needs_circuit": {v: needs[v] for v in ("yes", "no", "unclear")},
                         "needs_circuit_yes_share": share}
        rows.append([label, *(counts[s] for s in severity), len(items), needs["yes"], needs["no"],
                     needs["unclear"], share or "—"])

    high_critical = [row for row in binding if row["severity"] in {"C", "H"}]
    binding_audits = len({row["report_url"] for row in binding})
    high_critical_audits = len({row["report_url"] for row in high_critical})
    high_critical_protocols = len({row["protocol"] for row in high_critical})
    known_tvl = sum(row["protocol_tvl_usd_at_report"] != "UNKNOWN" for row in high_critical)
    triaged = sum(int(row["findings_reviewed"]) for row in audit_rows)
    all_high_critical_audits = len({row["report_url"] for row in findings if row["severity"] in {"C", "H"}})
    coverage = {"audits_read": len(audit_rows), "triaged": triaged, "audits_with_binding": binding_audits,
                "audits_with_high_critical_binding": high_critical_audits,
                "audits_with_high_critical_any_class": all_high_critical_audits,
                "high_critical_binding_protocols": high_critical_protocols,
                "high_critical_binding_findings_with_known_report_time_tvl": known_tvl}
    scalar("RtwoAudits", len(audit_rows), AUDITS, "audit CSV rows")
    scalar("RtwoTriagedFindings", triaged, AUDITS, "sum of findings_reviewed")
    scalar("RtwoFindings", len(findings), AUDIT_FINDINGS, "included finding rows")
    scalar("RtwoBindingFindings", len(binding), AUDIT_FINDINGS, "P1–P3 and P5")
    scalar("RtwoBindingAudits", binding_audits, AUDIT_FINDINGS, "distinct report_url values for binding findings")
    scalar("RtwoBindingAuditShare", percent(binding_audits, len(audit_rows)),
           (AUDIT_FINDINGS, AUDITS), "binding audits / all audits")
    scalar("RtwoHighCriticalBinding", len(high_critical), AUDIT_FINDINGS, "C or H in binding classes")
    scalar("RtwoHighCriticalBindingAudits", high_critical_audits, AUDIT_FINDINGS, "distinct reports with C/H binding findings")
    scalar("RtwoHighCriticalBindingProtocols", high_critical_protocols, AUDIT_FINDINGS, "distinct protocols with C/H binding findings")
    scalar("RtwoBindingReportTimeTVLKnown", known_tvl, AUDIT_FINDINGS, "C/H binding findings with known report-time TVL")
    scalar("RtwoNeedsCircuit", groups["All"]["needs_circuit"]["yes"], AUDIT_FINDINGS, "all needs_circuit_to_detect=yes rows")
    scalar("RtwoNeedsCircuitShare", groups["All"]["needs_circuit_yes_share"], AUDIT_FINDINGS, "yes / all included findings")
    scalar("RtwoBindingNeedsCircuit", groups["Binding"]["needs_circuit"]["yes"], AUDIT_FINDINGS, "yes in binding classes")
    scalar("RtwoBindingNeedsCircuitShare", groups["Binding"]["needs_circuit_yes_share"], AUDIT_FINDINGS, "yes / all binding findings")
    return (
        ["Class", *severity, "Total", "Yes", "No", "Unclear", "Yes share"], rows,
        {"raw": groups, "coverage": coverage, "caption_note": "Needs circuit = yes, no or unclear. Share uses all findings in the row.",
         "notes": ["Binding = P1–P3 and P5. Needs-circuit share = yes / all included findings in the row.",
                   "Audit convenience sample. Solodit was unavailable; funding at report time remains unresolved."]},
    )


def aztec_tools(ev, scalar):
    report = ev.report(AZ1, "Markdown table: Tool × target × verdict")
    records = markdown_table(report, ("tool", "target", "result", "reason"))
    matrix = []
    for tool, target, result, reason in records:
        if tool.startswith("BindCheck"):
            if target == "testbed fixed":
                require(result.startswith("identical to faulty"), "AZ1 fixed row no longer matches faulty")
                verdicts = next(cell["pattern_verdicts"] for cell in matrix if cell["target"] == "testbed faulty")
            elif target.startswith("real V3"):
                require(re.search(r"P1–P5 all UNKNOWN", result), "unrecognized AZ1 real target result")
                verdicts = dict.fromkeys(PATTERNS, "UNKNOWN")
            else:
                require("P2/P3 same" in result, "unrecognized AZ1 P2/P3 result")
                verdicts = {p: match(rf"\b{p} ({'|'.join(VERDICTS)})", result) for p in ("P1", "P4", "P5")}
                verdicts.update(P2=verdicts["P1"], P3=verdicts["P1"])
            abbreviations = dict(zip(VERDICTS, ("V", "VWS", "U")))
            summary = ", ".join(f"{p} {abbreviations[verdicts[p]]}" for p in PATTERNS)
            matrix.append({"tool": tool, "target": target, "pattern_verdicts": verdicts, "display": summary})
        elif tool.startswith("Slither"):
            count = int(match(r"(\d+) results", result))
            require("none about the fault" in result or "No detection." in reason,
                    "AZ1 Slither row needs review for binding diagnostics")
            matrix.append({"tool": tool, "target": target, "reports_per_variant": count,
                           "fault_reports": 0, "display": f"{count} reports each, 0 on fault" if "each" in result
                           else f"{count} reports, 0 on fault"})
        elif tool == "D1 R-EXTENT":
            require(result.startswith("not run: UNKNOWN"), "unrecognized AZ1 R-EXTENT result")
            matrix.append({"tool": tool, "target": target, "verdict": "UNKNOWN", "display": "UNKNOWN"})
        else:
            require(tool == "D1 R-EXTENT interface" and result.startswith("covered: true, status: EXACT, no warning"),
                    "unrecognized AZ1 interface result")
            matrix.append({"tool": tool, "target": "assumed case shape",
                           "recorded_status": "EXACT", "covered": True, "warning_count": 0,
                           "display": "No warning (assumed facts)"})

    scalar("AztecSlitherReports", next(row["reports_per_variant"] for row in matrix if
                                     row["tool"].startswith("Slither") and row["target"] == "real V3"),
           AZ1, "Tool × target × verdict table, real V3 Slither row")
    rows = [[row["tool"], row["target"].split(" (verified")[0], row["display"]] for row in matrix]
    return (
        ["Tool", "Target", "Reported result"], rows,
        {"raw": matrix, "caption_note": "U = UNKNOWN. VWS = VERIFIED WITHIN SCOPE for the individual check.",
         "notes": ["U = UNKNOWN. VWS = VERIFIED_WITHIN_SCOPE for the individual check.",
                                  "Slither counts are reported diagnostics. Assumed facts do not establish an AZ1 verdict."]},
    )


def aztec_testbed(ev, scalar):
    report = ev.report(AZ1, "Markdown table: Testbed; numeric observations from evidence prose")
    records = markdown_table(report, ("step", "consumer", "numRealRows", "observed"))
    steps, failed = map(int, match(r"steps=(\d+) fail=(\d+)", report))
    constraints, inputs, outputs = [
        int(cell.replace(",", ""))
        for cell in match(r"has ([\d,]+) constraints, (\d+) private inputs and (\d+) public outputs", report)
    ]
    names = {
        "tampered": "Tampered signal",
        "honest": "Honest control",
        "fault": "Coverage violation",
        "same": "Fixed coverage control",
    }
    rows = []
    observations = []
    for step, consumer, _, observed in records:
        if step.startswith("snarkjs:"):
            exits = number_list(match(r"^exit ([\d, ]+) \(as expected\)$", observed))
            observations.append({"check": "Proof and witness controls", "exit_codes": exits})
            rows.append(["Proof and witness controls", "—", ", ".join(map(str, exits)), "—", "—", "—"])
            continue
        name = names[step.split()[0]]
        status = int(match(r"\bstatus (\d+)\b", observed))
        amounts = {key: int(found.group(1)) if (found := re.search(rf"\b{key} (\d+)\b", observed)) else None
                   for key in ("credit", "backing", "gap", "pool tokens")}
        if name == "Fixed coverage control":
            name = "Fixed row check" if "state unchanged" in observed else "Fixed balance check"
        observations.append({"check": name, "consumer": consumer, "receipt_status": status, **amounts})
        rows.append([name, consumer, status, *(amounts[k] if amounts[k] is not None else "—"
                                                for k in ("credit", "backing", "gap"))])

    scalar("AztecTestbedSteps", steps, AZ1, "testbed run summary")
    scalar("AztecTestbedFailedSteps", failed, AZ1, "testbed run summary")
    scalar("AztecTestbedConstraints", constraints, AZ1, "reported circuit dimensions")
    scalar("AztecTestbedPrivateInputs", inputs, AZ1, "reported circuit dimensions")
    scalar("AztecTestbedPublicOutputs", outputs, AZ1, "reported circuit dimensions")
    scalar("AztecTestbedUnbackedGap", next(row["gap"] for row in observations if row["check"] == "Coverage violation"),
           AZ1, "synthetic testbed coverage-violation row, local token units")
    return (
        ["Check", "Consumer", "Status / exit", "Credit", "Backing", "Gap"], rows,
        {"scope": "Owned synthetic DEV fixture", "raw": observations,
         "run": {"steps": steps, "failed_steps": failed, "constraints": constraints,
                                      "private_inputs": inputs, "public_outputs": outputs},
         "notes": ["Status is the receipt status for consumer rows."]},
    )


def dev_precision(ev, scalar):
    _, labels = ev.csv(SET_H)
    _, rerun = ev.csv(CANDIDATE_CARDS)
    selected_strata = {"P1": "P1", "P3": "P3", f"P4/{CANONICALITY}": "P4 canonicality", "P5": "P5"}
    candidate = {row["card_id"]: row for row in rerun}
    originals = [row for row in labels if row["tool"] == "bindcheck-zk" and row["stratum"] in selected_strata]
    require(len(candidate) == len(rerun) == len(originals)
            and set(candidate) == {row["warning_id"] for row in originals}, "Set H comparison card IDs differ")
    require(all(row["final"] == candidate[row["warning_id"]]["final"] for row in originals), "Set H labels differ")
    require(all(row["final"] in {"TP", "FP"} for row in originals), "unresolved Set H comparison label")
    rows = []
    strata = {}
    for key, pattern in selected_strata.items():
        old = [row for row in originals if row["stratum"] == key]
        new = [candidate[row["warning_id"]] for row in old]
        analyzed = [row for row in new if row["family_status"] == "ANALYZED"]
        kept = [row for row in analyzed if row["still_warning"] == "YES"]
        require(all(row["still_warning"] in {"YES", "NO"} for row in new)
                and len(kept) == sum(row["still_warning"] == "YES" for row in new),
                f"invalid retained warning in {key}")
        old_tp = sum(row["final"] == "TP" for row in old)
        new_tp = sum(row["final"] == "TP" for row in kept)
        unavailable = len(old) - len(analyzed)
        strata[pattern] = {"freeze2_tp": old_tp, "freeze2_fp": len(old) - old_tp,
                           "candidate_tp": new_tp, "candidate_fp": len(kept) - new_tp,
                           "candidate_analyzed": len(analyzed), "candidate_coverage_unavailable": unavailable,
                           "candidate_tp_violation": sum(row["final"] == "TP" and row["new_verdict"] == "VIOLATION" for row in kept)}
        old_ratio = ratio(old_tp, len(old))
        new_ratio = ratio(new_tp, len(kept))
        rows.append([pattern, old_ratio, len(analyzed), unavailable, new_ratio])
        macro = {"P1": "POne", "P3": "PThree", "P4 canonicality": "PFourCanonicality", "P5": "PFive"}[pattern]
        scalar(f"SetH{macro}FreezePrecision", old_ratio, SET_H, f"{key} final TP / labelled TP+FP")
        scalar(f"SetH{macro}CandidatePrecision", new_ratio, CANDIDATE_CARDS, f"{key} retained TP / retained TP+FP")
    scalar("SetHCards", len(labels), SET_H, "all labelled cards (both tools)")
    scalar("SetHComparedCards", len(rerun), CANDIDATE_CARDS, "four re-scored BindCheck strata")
    scalar("SetHUnavailableCards", sum(row["candidate_coverage_unavailable"] for row in strata.values()),
           CANDIDATE_CARDS, "unavailable cards in four re-scored strata")
    return (
        ["Set H pattern", "Freeze 2 TP/all", "Analyzed", "Unavailable", "Candidate TP/retained"], rows,
        {"scope": DEV, "raw": strata,
         "notes": [DEV, "Freeze-2 final labels vs the S2a revision 1 candidate. Denominators differ.",
                   "P2 and P4 key equality have no candidate precision cell in this comparison."]},
    )


def pattern_counts(pairs):
    counts = Counter(pairs)
    out = {app: {v: counts[app, v] for v in VERDICTS} for app in APPLICABILITIES}
    require(sum(sum(block.values()) for block in out.values()) == sum(counts.values()), "invalid verdict/applicability")
    require(all(verdict == "UNKNOWN" or app == "APPLICABLE" for app, verdict in counts),
            "non-applicable or unresolved cells must remain UNKNOWN")
    return out


def applicable(counts):
    block = counts["APPLICABLE"]
    return [sum(block.values()), *(block[v] for v in VERDICTS)]


def spent_patterns(ev, scalar):
    _, selected = ev.csv(SELECTED)
    _, original = ev.csv(FREEZE_FAMILIES)
    _, records = ev.csv(SPENT_FAMILIES)
    old = {row["family_id"]: row for row in original}
    roster = {row["family_id"] for row in selected}
    require(len(roster) == len(selected) == len(records) and roster == {row["family_id"] for row in records},
            "spent rerun and preregistered selection differ")
    statuses = Counter(row["status"] for row in records)
    require(set(statuses) <= {"ANALYZED", "HARNESS_TIMEOUT", "ACQUISITION_FAILED", "EXCLUDED_BEFORE_ANALYSIS"},
            "unknown spent rerun status")
    attempted = [row for row in records if row["status"] != "EXCLUDED_BEFORE_ANALYSIS"]
    complete = [row for row in records if row["status"] == "ANALYZED"]
    require(len(old) == len(original) == len(attempted)
            and set(old) == {row["family_id"] for row in attempted}, "freeze-2 and spent rerun roster differ")
    for row in attempted:
        historic = old[row["family_id"]]
        for p in PATTERNS:
            require(row[f"old_{p}"] == f"{historic[f'{p}_verdict']}/{historic[f'{p}_applicability']}",
                    f"freeze-2 ledger disagrees with S2a old cell for rank {row['rank']} {p}")
            if row["status"] != "ANALYZED":
                require(row[f"new_{p}"] == "UNKNOWN/UNKNOWN", "unavailable candidate cell must remain UNKNOWN")

    rows = []
    groups = {}
    for scope, items in [("Attempted", attempted), ("Both analyzed", complete)]:
        group = {}
        for p in PATTERNS:
            group[p] = {}
            for phase, column in [("freeze2", "old"), ("candidate", "new")]:
                group[p][phase] = pattern_counts(
                    tuple(reversed(row[f"{column}_{p}"].split("/"))) for row in items
                )
            rows.append([scope, p, *applicable(group[p]["freeze2"]), *applicable(group[p]["candidate"])])
        groups[scope] = {"families": len(items), "patterns": group}

    scalar("SpentSelectedFamilies", len(selected), SELECTED, "selected family CSV rows")
    scalar("SpentAttemptedFamilies", len(attempted), SPENT_FAMILIES, "all except pre-analysis exclusion")
    scalar("SpentCompleteFamilies", len(complete), SPENT_FAMILIES, "ANALYZED rows")
    scalar("SpentTimeoutFamilies", statuses["HARNESS_TIMEOUT"], SPENT_FAMILIES, "HARNESS_TIMEOUT rows")
    scalar("SpentAcquisitionFailures", statuses["ACQUISITION_FAILED"], SPENT_FAMILIES, "ACQUISITION_FAILED rows")
    scalar("SpentExcludedFamilies", statuses["EXCLUDED_BEFORE_ANALYSIS"], SPENT_FAMILIES, "pre-analysis exclusions")
    return (
        ["Scope", "Pattern", "F2 app.", "F2 V", "F2 VWS", "F2 U", "Cand. app.", "Cand. V", "Cand. VWS", "Cand. U"],
        rows, {"scope": SPENT, "raw": groups, "candidate_family_status": dict(statuses),
               "notes": [SPENT, "Attempted includes acquisition failures and timeouts.",
                         "V = VIOLATION; VWS = VERIFIED_WITHIN_SCOPE; U = applicable UNKNOWN.",
                         "JSON preserves counts for each applicability category."]},
    )


def freeze_dev(ev, scalar):
    _, records = ev.csv(FREEZE_DEV)
    freeze = ev.report(FREEZE, "Markdown code block: analyzer content SHA-256")
    candidate = ev.report(S2A, "Markdown prose: S2a revision 1 candidate content SHA-256")
    freeze_hash = match(r"^BINDCHECK_ZK_CONTENT_SHA256=([0-9a-f]{64})$", freeze)
    candidate_hash = match(r"^  Recomputed value:\n  `BINDCHECK_ZK_CONTENT_SHA256=([0-9a-f]{64})`\.$", candidate)
    families = {row["row"] for row in records}
    require(len(records) == len(families) * len(PATTERNS) == len({(row["row"], row["pattern"]) for row in records})
            and all(row["pattern"] in PATTERNS for row in records), "invalid freeze-2 DEV grid")
    patterns = {p: pattern_counts((row["after_applicability"], row["after_verdict"])
                                  for row in records if row["pattern"] == p) for p in PATTERNS}
    total = pattern_counts((row["after_applicability"], row["after_verdict"]) for row in records)
    patterns["All"] = total
    rows = [[p, *applicable(counts)] for p, counts in patterns.items()]
    scalar("FreezeTwoDevFamilies", len(families), FREEZE_DEV, "distinct DEV row IDs")
    scalar("FreezeTwoDevApplicable", applicable(total)[0], FREEZE_DEV, "applicable freeze-2 pattern cells")
    scalar("FreezeTwoDevDecided", applicable(total)[1] + applicable(total)[2], FREEZE_DEV, "applicable V or VWS cells")
    return (
        ["Pattern", "Applicable", "VIOLATION", "VERIFIED WITHIN SCOPE", "UNKNOWN"], rows,
        {"scope": DEV, "raw": patterns, "dev_families": len(families),
         "identities": {"freeze2_analyzer_content_sha256": freeze_hash,
                        "s2a_revision1_candidate_content_sha256": candidate_hash},
         "notes": [DEV, "Original freeze-2 development corpus. The S2a spent rerun uses a different roster."]},
    )


def oracle_matrix(ev, scalar):
    report = ev.report(S4, "Markdown table: Operator × case")
    obligation = ev.report(S4C, "Markdown table: Operator × variant")
    base_ops = ("CALLER", "FREE_ARG", "ALIAS", "REPLAY", "DOMAIN")
    extra_ops = ("CALLER", "FREE_ARG(skipFee)", "ALIAS-0", "ALIAS-1", "REPLAY", "DOMAIN")
    base = markdown_table(report, ("Case / variant", *base_ops))
    extra = markdown_table(obligation, ("Variant", *extra_ops))
    operators = ("CALLER", "FREE_ARG", "ALIAS", "ALIAS-0", "ALIAS-1", "REPLAY", "DOMAIN")
    codes = {"E4": "E4-CONFIRMED", "NOT": "NOT_CONFIRMED", "UNKNOWN": "UNKNOWN"}
    short = {value: key for key, value in codes.items()}
    matrix = []
    rows = []
    for source, items, keys in [("S4", base, base_ops), ("S4c", extra, extra_ops)]:
        for case, *cells in items:
            if source == "S4c":
                case = f"Synthetic obligation ({case.split()[0]})"
            results = {operator.split("(")[0]: codes[cell.split()[0]] for operator, cell in zip(keys, cells)}
            matrix.append({"run": source, "case": case, "operators": results})
            rows.append([case, *(short[results[op]] if op in results else "—" for op in operators)])
    for source, path in [("S4", S4), ("S4c", S4C)]:
        subset = [row for row in matrix if row["run"] == source]
        confirmations = sum(list(row["operators"].values()).count("E4-CONFIRMED") for row in subset)
        name = "Sfour" if source == "S4" else "SfourC"
        scalar(f"{name}EfourCells", confirmations, path, "E4 cells in the reported operator matrix")
        scalar(f"{name}MatrixCases", len(subset), path, "case/variant rows in the reported operator matrix")
    return (
        ["Case / variant", *operators], rows,
        {"raw": matrix, "caption_note": "E4 = E4-CONFIRMED. NOT = NOT CONFIRMED for the recorded trials.",
         "notes": ["E4 = E4-CONFIRMED; NOT = NOT_CONFIRMED for the recorded trials.",
                                  "A dash marks an operator column absent from that report. S4b repeats S4's matrix."]},
    )


def oracle_runtimes(ev, scalar):
    base_report = ev.report(S4, "Markdown table: Runtimes")
    rerun_report = ev.report(S4B, "Markdown prose: runtimes")
    obligation_report = ev.report(S4C, "Markdown prose: runtimes")
    base = markdown_table(base_report, ("Run", "total wall", "per-trial (approx)"))
    wall_s4b = number_list(match(
        r"Runtimes \(wall, per full run\): ZKredential (\d+ s, RacePass \d+ s, synthetic\s+bound/alias/replay [\d /]+ s)\.",
        rerun_report,
    ))
    obligation_wall, obligation_trials = map(int, match(
        r"Runtimes \(wall\): full run (\d+) s \(two variants × (\d+) trials\)", obligation_report
    ))
    groups = ("ZKredential", "RacePass", "Synthetic bound", "Synthetic alias", "Synthetic replay")
    require(len(base) == 3 and len(wall_s4b) == len(groups), "unrecognized S4 runtime grouping")
    wall_s4 = [seconds for _, wall, _ in base for seconds in number_list(wall)]
    require(len(wall_s4) == len(groups), "unrecognized S4 wall times")
    rows = [[case, old, new, "—"] for case, old, new in zip(groups, wall_s4, wall_s4b)]
    rows.append(["Synthetic obligation", "—", "—", obligation_wall])
    raw = {
        "S4": {"wall_seconds": dict(zip(groups, wall_s4)),
               "per_trial_reported_approx": {run: approx for run, _, approx in base}},
        "S4b": {"wall_seconds": dict(zip(groups, wall_s4b))},
        "S4c": {"wall_seconds": {"Synthetic obligation": obligation_wall},
                "trials_per_variant": obligation_trials},
    }
    scalar("SfourBoundWallSeconds", wall_s4[2], S4, "reported synthetic bound wall time")
    scalar("SfourCWallSeconds", obligation_wall, S4C, "reported synthetic obligation wall time")
    return (
        ["Case", "S4 wall (s)", "S4b wall (s)", "S4c wall (s)"], rows,
        {"raw": raw, "notes": ["Reported full-run wall times. S4 real-case times include dependency install, proving and compile."]},
    )


def generators(ev, scalar):
    if not (ev.root / GENERATORS).exists():
        return (
            ["Generator census"],
            [["TODO: tracked S1 generator census unavailable"]],
            {"status": "TODO", "missing_optional_sources": [GENERATORS],
             "notes": ["Generator results await a tracked S1 CSV."]},
        )
    headers, items = ev.csv(GENERATORS)
    scalar("SOneGeneratorRows", len(items), GENERATORS, "data rows (one row per recorded census entry)")
    return headers, [[row[key] for key in headers] for row in items], {"status": "AVAILABLE"}


# Escape values in a single pass, so the macro syntax introduced here is never re-escaped.
LATEX = str.maketrans({
    "\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "$": r"\$", "&": r"\&",
    "#": r"\#", "_": r"\_", "%": r"\%", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    "—": "---", "–": "--",
})


def tex_value(value):
    return str(value).replace("\r", " ").replace("\n", " ").translate(LATEX)


def tex_table(columns, rows, notes, sources, labels):
    preamble = ["% Generated by scripts/paper/build.py."]
    preamble.extend(f"% {path} sha256 {entry['sha256']}" for path, entry in sources.items())
    preamble.extend(f"% {note}" for note in notes)
    layout = "".join("r" if all(isinstance(row[i], int) for row in rows) else "l"
                     for i in range(len(columns)))
    body = [
        rf"\begin{{tabular}}{{{layout}}}",
        r"\toprule",
        " & ".join(map(tex_value, columns)) + r" \\",
        r"\midrule",
    ]
    body.extend(" & ".join(map(tex_value, row)) + r" \\" for row in rows)
    if labels:
        body.append(r"\midrule")
        body.extend(rf"\multicolumn{{{len(columns)}}}{{@{{}}l}}{{\footnotesize {tex_value(label)}}} \\"
                    for label in labels)
    body.extend([r"\bottomrule", r"\end{tabular}"])
    return "\n".join(preamble + body) + "\n"


TABLES = {
    "T-incidents": incidents,
    "T-audits": audits,
    "T-aztec-tools": aztec_tools,
    "T-aztec-testbed": aztec_testbed,
    "T-dev-precision": dev_precision,
    "T-spent-patterns": spent_patterns,
    "T-freeze-dev": freeze_dev,
    "T-oracle": oracle_matrix,
    "T-oracle-runtimes": oracle_runtimes,
    "T-generators": generators,
}


def render(root=ROOT):
    sources = {}
    scalars = {}
    outputs = {}

    def add_scalar(name, value, paths, definition):
        require(re.fullmatch("[A-Za-z]+", name) and name not in scalars, f"invalid or duplicate macro {name}")
        if isinstance(paths, str):
            paths = (paths,)
        scalars[name] = {"value": value, "sources": list(paths), "definition": definition}

    def emit(name, tex, payload):
        outputs[name + ".tex"] = tex.encode("utf-8")
        outputs[name + ".json"] = (json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")

    for name, function in TABLES.items():
        ev = Evidence(root, sources)
        columns, rows, details = function(ev, add_scalar)
        require(all(len(row) == len(columns) for row in rows), f"{name}: inconsistent table width")
        notes = details.get("notes", [])
        labels = [details[key] for key in ("scope", "caption_note") if key in details]
        emit(name, tex_table(columns, rows, notes, ev.inputs, labels),
             {"sources": ev.inputs, "columns": columns, "rows": rows, **details})

    macros = ["% Generated by scripts/paper/build.py."]
    for name, info in scalars.items():
        for path in info["sources"]:
            macros.append(f"% {path} sha256 {sources[path]['sha256']}")
        macros.append(f"% {info['definition']}")
        value = info["value"] if info["value"] is not None else "—"
        macros.append(rf"\newcommand{{\{name}}}{{{tex_value(value)}}}")
    emit("numbers", "\n".join(macros) + "\n", {"sources": sources, "macros": scalars})
    return outputs


def main():
    try:
        outputs = render()
        destination = ROOT / OUTPUT
        destination.mkdir(parents=True, exist_ok=True)
        for name, data in outputs.items():
            path = destination / name
            if not path.is_file() or path.read_bytes() != data:
                path.write_bytes(data)
    except (OSError, ValueError, IndexError, KeyError, csv.Error) as error:
        print(f"paper tables: {error}", file=sys.stderr)
        return 1
    print(f"Wrote or confirmed {len(outputs)} files in {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
