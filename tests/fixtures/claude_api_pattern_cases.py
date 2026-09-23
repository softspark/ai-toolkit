# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Execute reviewed skill examples offline with fake Messages API clients."""

import ast
import json
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[2]


def examples(name):
    source = (ROOT / "app/skills" / name / "SKILL.md").read_text()
    blocks = re.findall(r"```python\n(.*?)\n```", source, re.DOTALL)
    namespace = {}
    for block in blocks:
        tree = ast.parse(block)
        # Examples may define helpers and constants, but never perform work on load.
        assert all(isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.Assign))
                   for node in tree.body)
        exec(compile(tree, f"{name}/SKILL.md", "exec"), namespace)
    return namespace


def fake_client(value, stop_reason="end_turn", extra_blocks=()):
    response = SimpleNamespace(
        stop_reason=stop_reason,
        content=[*extra_blocks, SimpleNamespace(type="text", text=json.dumps(value))],
    )
    return SimpleNamespace(messages=SimpleNamespace(create=Mock(return_value=response)))


class ClaudePatternExamples(unittest.TestCase):
    def test_explicit_model_never_falls_back_to_a_route(self):
        choose = examples("model-routing-patterns")["choose_model"]
        routes = {"extract": "approved-cheap"}
        allowed = {"approved-cheap", "user-selected"}
        self.assertEqual(choose("extract", routes, allowed, "user-selected"), "user-selected")
        self.assertEqual(choose("extract", routes, allowed), "approved-cheap")
        for task, explicit in (("extract", "unavailable"), ("unknown", None), ("extract", "")):
            with self.assertRaises(ValueError):
                choose(task, routes, allowed, explicit)

    def test_cache_example_preserves_budget_and_counts_writes(self):
        code = examples("prompt-caching-patterns")
        client = fake_client({})
        code["cached_answer"](client, "user-selected", "policy", "document", "question", 4321)
        request = client.messages.create.call_args.kwargs
        self.assertEqual(request["model"], "user-selected")
        self.assertEqual(request["max_tokens"], 4321)
        self.assertEqual(request["system"][0]["cache_control"], {"type": "ephemeral"})
        content = request["messages"][0]["content"]
        self.assertEqual(content[-1], {"type": "text", "text": "question"})
        self.assertIn("cache_control", content[0])
        usage = SimpleNamespace(cache_read_input_tokens=50, cache_creation_input_tokens=25, input_tokens=25)
        self.assertEqual(code["cache_read_fraction"](usage), 0.5)
        empty = SimpleNamespace(cache_read_input_tokens=0, cache_creation_input_tokens=0, input_tokens=0)
        self.assertEqual(code["cache_read_fraction"](empty), 0.0)

    def test_native_json_rejects_incomplete_and_invalid_semantics(self):
        code = examples("json-mode-patterns")
        good = {"sentiment": "POSITIVE", "confidence": 0.8, "themes": ["delivery"]}
        client = fake_client(good, extra_blocks=(SimpleNamespace(type="thinking"),))
        result = code["analyze"](client, "user-selected", "input", 987)
        self.assertEqual(result["sentiment"], "positive")
        request = client.messages.create.call_args.kwargs
        self.assertEqual(request["model"], "user-selected")
        self.assertEqual(request["max_tokens"], 987)
        schema = request["output_config"]["format"]["schema"]
        self.assertFalse(schema["additionalProperties"])
        self.assertNotIn("minimum", schema["properties"]["confidence"])
        for reason in ("refusal", "max_tokens", "tool_use"):
            with self.assertRaises(ValueError):
                code["analyze"](fake_client(good, reason), "user-selected", "input", 987)
        invalid = [{**good, "confidence": value} for value in (
            True, -0.1, 1.1, float("nan"), float("inf"), 10**400, -(10**400), "0.8",
        )]
        invalid += [{**good, "sentiment": "invented"}, {**good, "themes": []}, {**good, "extra": 1}]
        for value in invalid:
            with self.assertRaises(ValueError):
                code["validate_analysis"](value)

    def test_url_filter_rejects_lookalikes_and_userinfo(self):
        allowed = examples("content-moderation-patterns")["is_allowed_url"]
        hosts = {"allowed.example"}
        self.assertTrue(allowed("https://ALLOWED.example/path", hosts))
        for url in (
            "https://allowed.example.attacker.test/path",
            "https://allowed.example@attacker.test/path",
            "https://name@allowed.example/path",
            "http://allowed.example/path", "https://allowed.example:8443/",
            "https://allowed.example:invalid/", "https://[malformed",
        ):
            self.assertFalse(allowed(url, hosts), url)

    def test_moderation_never_allows_mixed_or_unknown_categories(self):
        route = examples("content-moderation-patterns")["route"]
        limits = {"spam": 0.9, "harassment": 0.95}
        def decision(categories, confidence=0.99):
            return route({"categories": categories, "confidence": confidence, "reason": "policy"}, limits, 0.8)
        self.assertEqual(decision(["clean"]), "pass")
        self.assertEqual(decision(["spam"]), "reject")
        for categories in (["clean", "spam"], ["needs_review"], ["unknown"], [], "clean", [None]):
            self.assertEqual(decision(categories), "human_review", categories)
        for confidence in (True, float("nan"), float("inf"), -1, 2, 10**400, -(10**400), "0.99", 0.7):
            self.assertEqual(decision(["clean"], confidence), "human_review")
        self.assertEqual(decision(["spam"], 0.8), "human_review")

    def test_moderation_uses_closed_schema_and_preserves_policy_and_budget(self):
        classify = examples("content-moderation-patterns")["classify"]
        good = {"categories": ["clean"], "confidence": 0.9, "reason": "policy"}
        client = fake_client(good)
        self.assertEqual(classify(client, "selected", "policy", "input", 555), good)
        request = client.messages.create.call_args.kwargs
        self.assertEqual((request["model"], request["max_tokens"], request["system"]), ("selected", 555, "policy"))
        schema = request["output_config"]["format"]["schema"]
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), {"categories", "confidence", "reason"})
        for reason in ("refusal", "max_tokens"):
            with self.assertRaises(ValueError):
                classify(fake_client(good, reason), "selected", "policy", "input", 555)


if __name__ == "__main__":
    unittest.main()
