from __future__ import annotations

import pathlib
from typing import Any

from slither.detectors.abstract_detector import AbstractDetector, DetectorClassification

from baselines.strong.solidity_scan import scan_effects, scan_interface, scan_replay


class _StrongDetector(AbstractDetector):
    IMPACT = DetectorClassification.HIGH
    CONFIDENCE = DetectorClassification.MEDIUM
    WIKI = "https://example.invalid/bindcheck-strong"
    WIKI_TITLE = "Proof-to-effect binding heuristic"
    WIKI_DESCRIPTION = "Checks a consuming Solidity path and generated verifier without circuit semantics."
    WIKI_EXPLOIT_SCENARIO = "A proof succeeds while an independently selected effect or replay key is committed."
    WIKI_RECOMMENDATION = "Bind effect and replay roles to the exact proof statement and enforce dominating guards."
    CODES: set[str] = set()

    def _source_texts(self) -> list[tuple[str, str]]:
        paths: set[pathlib.Path] = set()
        for contract in self.contracts:
            filename = getattr(contract.source_mapping.filename, "absolute", None)
            if filename:
                path = pathlib.Path(filename)
                if path.is_file():
                    paths.add(path)
        texts: list[tuple[str, str]] = []
        for path in sorted(paths):
            texts.append((str(path), path.read_text(encoding="utf-8", errors="replace")))
        return texts

    def _candidate_findings(self, texts: list[tuple[str, str]]) -> list[dict[str, Any]]:
        raise NotImplementedError

    def _detect(self):
        results = []
        texts = self._source_texts()
        for item in self._candidate_findings(texts):
            if item["code"] not in self.CODES:
                continue
            info = [f"{item['code']}: {item['message']}"]
            results.append(self.generate_result(info, additional_fields={"strong_finding": item}))
        return results


class EffectArgumentDetector(_StrongDetector):
    ARGUMENT = "strong-effect-binding"
    HELP = "Detect protected effect roles not tied to verifier public inputs"
    CODES = {
        "A_EFFECT_RECIPIENT_UNBOUND", "A_EFFECT_AMOUNT_UNBOUND",
        "A_EFFECT_IDENTITY_UNBOUND", "A_CALL_VALUE_UNBOUND",
        "A_STATE_WRITE_VALUE_UNBOUND", "A_EFFECT_ALIAS_UNBOUND",
        "A_CALLER_NOT_PROVED_IDENTITY",
    }

    def _candidate_findings(self, texts: list[tuple[str, str]]) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for path, text in texts:
            findings, _ = scan_effects(text, path)
            output.extend(findings)
        return output


class GuardDominanceDetector(_StrongDetector):
    ARGUMENT = "strong-guard-dominance"
    HELP = "Detect equality checks that do not dominate protected effects"
    CODES = {"A_GUARD_NOT_DOMINATING", "A_GUARD_AFTER_EFFECT"}

    def _candidate_findings(self, texts: list[tuple[str, str]]) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for path, text in texts:
            findings, _ = scan_effects(text, path)
            output.extend(findings)
        return output


class ReplayKeyDetector(_StrongDetector):
    ARGUMENT = "strong-replay-key-binding"
    HELP = "Detect consumed replay keys not derived from verifier public inputs"
    CODES = {"A_REPLAY_KEY_UNBOUND"}

    def _candidate_findings(self, texts: list[tuple[str, str]]) -> list[dict[str, Any]]:
        findings, _ = scan_replay(texts)
        return findings


class ReplayCanonicalityDetector(_StrongDetector):
    ARGUMENT = "strong-replay-position-canonicality"
    HELP = "Detect a missing scalar-field guard at the exact replay-key position"
    CODES = {"A_REPLAY_POSITION_FIELD_GUARD_MISSING"}

    def _candidate_findings(self, texts: list[tuple[str, str]]) -> list[dict[str, Any]]:
        findings, _ = scan_replay(texts)
        return findings


class VerifierInterfaceDetector(_StrongDetector):
    ARGUMENT = "strong-verifier-interface"
    HELP = "Detect consumer count or order disagreement with a generated verifier interface"
    CODES = {"A_VERIFIER_ARITY_MISMATCH", "A_VERIFIER_ORDER_MISMATCH"}

    def _candidate_findings(self, texts: list[tuple[str, str]]) -> list[dict[str, Any]]:
        findings, _ = scan_interface(texts)
        return findings


DETECTORS = [
    EffectArgumentDetector,
    GuardDominanceDetector,
    ReplayKeyDetector,
    ReplayCanonicalityDetector,
    VerifierInterfaceDetector,
]
