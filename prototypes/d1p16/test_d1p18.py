#!/usr/bin/env python3
"""D1P-18 fail-closed and versioned-effect-model regressions."""

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from extract_relation import ExecState, Extractor, UnsupportedConstruct  # noqa: E402


PAPER = Path("/Users/imranpollob/Coding/bc/bindcheck-d1-paper")
BUILD = PAPER / "results/raw/D1P-12R/workspace/source/backend/artifacts/build-info/solc-0_8_29-a52609323fd0bce65aec2ea493681a10c5c96cfa.json"
OUTPUT = BUILD.with_suffix(".output.json")
SOURCE = PAPER / "results/raw/D1P-12R/workspace/source/backend/contracts/core/WarpToadCore.sol"
MODELS = HERE / "library_effect_models.v1.json"


class HardeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extractor = Extractor(BUILD, OUTPUT, SOURCE)
        cls.relation = cls.extractor.extract()
        cls.entry = cls.extractor.find_function(
            "project/contracts/core/WarpToadCore.sol", "WarpToadCore", "mint"
        )
        cls.src = cls.entry["src"]

    def assert_rejection(self, expected_code, thunk):
        with self.assertRaises(UnsupportedConstruct) as caught:
            thunk()
        self.assertEqual(expected_code, caught.exception.code)
        self.assertRegex(caught.exception.location, r"\.sol:[0-9]+$")

    def test_unresolved_callee_fails_closed(self):
        call = {
            "nodeType": "FunctionCall", "src": self.src, "arguments": [],
            "expression": {"nodeType": "Identifier", "name": "mystery", "referencedDeclaration": 999999},
        }
        self.assert_rejection(
            "UNSUPPORTED_UNRESOLVED_CALLEE",
            lambda: self.extractor.eval_expr(call, ExecState()),
        )
        self.assert_rejection(
            "UNSUPPORTED_UNRESOLVED_CALLEE",
            lambda: self.extractor.exec_function_call(call, ExecState(), checked=True),
        )

    def test_generic_member_and_index_fallbacks_are_rejected(self):
        member = {
            "nodeType": "MemberAccess", "src": self.src, "memberName": "unknownMember",
            "expression": {"nodeType": "Literal", "src": self.src, "kind": "number", "value": "1"},
        }
        index = {
            "nodeType": "IndexAccess", "src": self.src,
            "baseExpression": {"nodeType": "Literal", "src": self.src, "kind": "number", "value": "1"},
            "indexExpression": {"nodeType": "Literal", "src": self.src, "kind": "number", "value": "0"},
        }
        self.assert_rejection(
            "UNSUPPORTED_MEMBER_ACCESS",
            lambda: self.extractor.eval_expr(member, ExecState()),
        )
        self.assert_rejection(
            "UNSUPPORTED_INDEX_ACCESS",
            lambda: self.extractor.eval_expr(index, ExecState()),
        )

    def test_unmodeled_external_call_is_rejected(self):
        ref = next(
            ref for ref, node in self.extractor.nodes.items()
            if node.get("nodeType") == "FunctionDefinition"
            and node.get("visibility") == "external"
            and self.extractor.declaration_key(ref) not in self.extractor.external_boundaries
        )
        call = {
            "nodeType": "FunctionCall", "src": self.src, "arguments": [],
            "expression": {"nodeType": "Identifier", "name": "external", "referencedDeclaration": ref},
        }
        self.assert_rejection(
            "UNSUPPORTED_EXTERNAL_CALL",
            lambda: self.extractor.eval_expr(call, ExecState()),
        )
        self.assert_rejection(
            "UNSUPPORTED_EXTERNAL_CALL_STATEMENT",
            lambda: self.extractor.exec_function_call(call, ExecState(), checked=True),
        )

    def test_unresolved_event_is_rejected(self):
        statement = {
            "nodeType": "EmitStatement", "src": self.src,
            "eventCall": {
                "nodeType": "FunctionCall", "src": self.src, "arguments": [],
                "expression": {
                    "nodeType": "Identifier", "name": "Mystery",
                    "referencedDeclaration": 999999,
                },
            },
        }
        self.assert_rejection(
            "UNSUPPORTED_UNRESOLVED_EVENT",
            lambda: self.extractor.exec_statement(ExecState(), statement, checked=True),
        )

    def test_relation_contains_no_generic_fallback_terms(self):
        forbidden = {"call", "member", "index"}
        found = []

        def walk(value):
            if isinstance(value, dict):
                if value.get("op") in forbidden:
                    found.append(value["op"])
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(self.relation)
        self.assertEqual([], found)

    def test_effects_are_resolved_by_versioned_declaration_key(self):
        self.assertEqual("1.0.0", self.relation["pins"]["library_effect_models_version"])
        self.assertFalse(self.relation["pins"]["case_specific_effect_models"])
        successes = [path for path in self.relation["paths"] if path["status"] == "success"]
        for path in successes:
            for mint in path["committed"]["mints"]:
                self.assertEqual("erc20_mint", mint["effect_model"])
                self.assertIn("@openzeppelin/contracts@5.6.1", mint["declaration"])
            for event in path["committed"]["events"]:
                self.assertEqual("erc20_transfer_event", event["effect_model"])
            for write in path["committed"]["storage_writes"]:
                if "@openzeppelin/contracts@5.6.1" in write["declaration"]:
                    self.assertIn(write["effect_model"], {"erc20_balance_map", "erc20_total_supply"})

    def test_removing_resolved_mint_model_fails_closed(self):
        models = json.loads(MODELS.read_text())
        declarations = models["libraries"]["openzeppelin-contracts@5.6.1"]["declarations"]
        mint_key = next(key for key in declarations if "::_mint(" in key)
        del declarations[mint_key]
        with tempfile.TemporaryDirectory() as directory:
            model_path = Path(directory) / "models.json"
            model_path.write_text(json.dumps(models))
            extractor = Extractor(BUILD, OUTPUT, SOURCE, model_path=model_path)
            self.assert_rejection("UNSUPPORTED_LIBRARY_CALL", extractor.extract)


if __name__ == "__main__":
    unittest.main()
